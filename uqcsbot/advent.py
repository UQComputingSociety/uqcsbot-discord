import io
import logging
import os
from datetime import datetime, timedelta
from pytz import timezone
from random import choices
from typing import Any, Callable, Dict, Iterable, List, Optional, Literal
import requests
from requests.exceptions import RequestException
from sqlalchemy.sql.expression import and_

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.bot import UQCSBot
from uqcsbot.models import AOCRegistrations, AOCWinners
from uqcsbot.utils.err_log_utils import FatalErrorWithLog

# Leaderboard API URL with placeholders for year and code.
LEADERBOARD_URL = "https://adventofcode.com/{year}/leaderboard/private/view/{code}.json"

# UQCS leaderboard ID.
UQCS_LEADERBOARD = 989288

# Days in Advent of Code. List of numbers 1 to 25.
ADVENT_DAYS = list(range(1, 25 + 1))

# Puzzles are unlocked at midnight EST.
EST_TIMEZONE = timezone("US/Eastern")

# The time to cache results to limit requests to adventofcode.com. Note that 15 minutes is the recomended minimum time.
CACHE_TIME = timedelta(minutes=15)

# The maximum time in seconds that a person can complete a challenge in. Used as a maximum value to help with sorting when someone whas not attempted a day.
MAXIMUM_TIME_FOR_STAR = 365 * 24 * 60 * 60

# type aliases for documentation purposes.
Day = int  # from 1 to 25
Star = Literal[1, 2]
Seconds = int
Times = Dict[Star, Seconds]
Delta = Optional[Seconds]
Json = Dict[str, Any]


class InvalidHTTPSCode(Exception):
    def __init__(self, message, request_code):
        super().__init__(message)
        self.request_code = request_code


class Member:
    def __init__(self, id: int, name: str, local: int, star_total: int, global_: int):
        # The advent of code id
        self.id = id
        # The advent of code name
        self.name = name
        # The score of the user on the local leaderboard
        self.local = local
        # The total number of stars the user has collected
        self.star_total = star_total
        # The score of the user on the global leaderboard
        self.global_ = global_

        # All of the Times. If no stars are collected, the Times dictionary is empty.
        self.times: Dict[Day, Times] = {d: {} for d in ADVENT_DAYS}

    @classmethod
    def from_member_data(cls, data: Json, year: int) -> "Member":
        """
        Constructs a Member from the API response.

        Times and delta are calculated for the given year and day.
        """

        member = cls(
            data["id"],
            data["name"],
            data["local_score"],
            data["stars"],
            data["global_score"],
        )

        for d, day_data in data["completion_day_level"].items():
            day = int(d)
            times = member.times[day]

            # timestamp of puzzle unlock, rounded to whole seconds
            DAY_START = int(datetime(year, 12, day, tzinfo=EST_TIMEZONE).timestamp())

            for s, star_data in day_data.items():
                star = int(s)
                # assert is for type checking
                assert star == 1 or star == 2
                times[star] = int(star_data["get_star_ts"]) - DAY_START
                assert times[star] >= 0

        return member

    def get_time_delta(self, day: Day) -> Optional[Seconds]:
        """
        Returns the number of seconds between the completion of the second star from the first, or None if the second star have not been completed.
        """
        if len(self.times[day]) == 2:
            return self.times[day][2] - self.times[day][1]
        return None

    def attempted_day(self, day: Day) -> bool:
        """
        Returns if a member completed at least the first star in the day
        """
        return len(self.times[day]) >= 1

    def get_total_star1_time(self, default: int = 0) -> int:
        """
        Returns the total time working on just star 1 for all challenges in a year.
        The argument default determines the returned value if the total is 0.
        """
        total = sum(self.times[day].get(1, 0) for day in ADVENT_DAYS)
        return total if total != 0 else default

    def get_total_star2_time(self, default: int = 0) -> int:
        """
        Returns the total time working on just star 2 for all challenges in a year.
        The argument default determines the returned value if the total is 0.
        """
        total = sum(self.times[day].get(2, 0) for day in ADVENT_DAYS)
        return total if total != 0 else default

    def get_total_time(self, default: int = 0) -> int:
        """
        Returns the total time working on stars 1 and 2 for all challenges in a year.
        The argument default determines the returned value if the total is 0.
        """
        total = self.get_total_star1_time() + self.get_total_star2_time()
        return total if total != 0 else default

    def get_discord_userid(self, bot: UQCSBot) -> Optional[int]:
        """
        Return the discord userid of this AOC member if one is registered in the database.
        """
        db_session = bot.create_db_session()
        registration = (
            db_session.query(AOCRegistrations)
            .filter(AOCRegistrations.aoc_userid == self.id)
            .one_or_none()
        )
        db_session.close()
        if registration:
            return registration.discord_userid
        return None


# --- Sorting Methods & Related Leaderboards ---

# Star 1 Time: Time for just getting star 1. For the monthly leaderboard, this will be the total time spent on star 1 across all problems.
# Star 2 Time: Time for just getting star 2. Does not include the time to get star 1. For the monthly leaderboard, this will be the total time spent on star 2 across all problems.
# Star 1 & 2 Time: Time for getting both stars 1 and 2.
# Total Time: The total time spent on problems over the entire month. For the monthly leaderboard, this is the same as Star 1 & 2 Time.
# Total Stars: The total number of stars over the entire month.
# Global Rank: The users global rank over the month. This is not reasonable to be daily, as very few get a global ranking each day.
SortingMethod = Literal[
    "Star 1 Time",
    "Star 2 Time",
    "Star 1 & 2 Time",
    "Total Time",
    "Total Stars",
    "Global Rank",
]

# Note that a tuple is used so that there can be multiple sorting criterial
sorting_functions_for_day: Dict[
    SortingMethod, Callable[[Member, Day], tuple[int, ...]]
] = {
    "Star 1 Time": lambda member, day: (
        member.times[day].get(1, MAXIMUM_TIME_FOR_STAR),
        member.times[day].get(2, MAXIMUM_TIME_FOR_STAR),
    ),
    "Star 2 Time": lambda member, day: (
        member.times[day][2] - member.times[day][1]
        if 2 in member.times[day]
        else MAXIMUM_TIME_FOR_STAR,
        member.times[day].get(1, MAXIMUM_TIME_FOR_STAR),
    ),
    "Star 1 & 2 Time": lambda member, day: (
        member.times[day].get(2, MAXIMUM_TIME_FOR_STAR),
        member.times[day].get(1, MAXIMUM_TIME_FOR_STAR),
    ),
    "Total Time": lambda member, dat: (
        member.get_total_time(default=MAXIMUM_TIME_FOR_STAR),
        -member.star_total,
    ),
    "Total Stars": lambda member, day: (
        -member.star_total,
        member.get_total_time(default=MAXIMUM_TIME_FOR_STAR),
    ),
    "Global Rank": lambda member, day: (
        -member.global_,
        member.get_total_time(default=MAXIMUM_TIME_FOR_STAR),
    ),
}

# Each sorting method has its own leaderboard to show the most relevant details
leaderboards_for_day: Dict[SortingMethod, str] = {
    "Star 1 Time": "# 1 2 3 ! @ T",
    "Star 2 Time": "# 1 2 3 ! @ T",
    "Star 1 & 2 Time": "# 1 2 3 ! @ T L",
    "Total Time": "# T ! @ 1 2 3",
    "Total Stars": "# * L 1 2 3",
    "Global Rank": "# G L * 1 2 3",
}

# These are used for the monthly leaderboard
sorting_functions_for_month: Dict[
    SortingMethod, Callable[[Member], tuple[int, ...]]
] = {
    "Star 1 Time": lambda member: (
        member.get_total_star1_time(default=MAXIMUM_TIME_FOR_STAR),
        member.get_total_star2_time(default=MAXIMUM_TIME_FOR_STAR),
    ),
    "Star 2 Time": lambda member: (
        member.get_total_star2_time(default=MAXIMUM_TIME_FOR_STAR),
        member.get_total_star1_time(default=MAXIMUM_TIME_FOR_STAR),
    ),
    "Star 1 & 2 Time": lambda member: (
        member.get_total_time(default=MAXIMUM_TIME_FOR_STAR),
        -member.star_total,
        member.get_total_star1_time(default=MAXIMUM_TIME_FOR_STAR),
    ),
    "Total Time": lambda member: (
        member.get_total_time(default=MAXIMUM_TIME_FOR_STAR),
        -member.star_total,
    ),
    "Total Stars": lambda member: (
        -member.star_total,
        member.get_total_time(default=MAXIMUM_TIME_FOR_STAR),
    ),
    "Global Rank": lambda member: (
        -member.global_,
        member.get_total_time(default=MAXIMUM_TIME_FOR_STAR),
    ),
}

# Each sorting method has its own leaderboard to show the most relevant details
leaderboards_for_month: Dict[SortingMethod, str] = {
    "Star 1 Time": "# ! @ T * L",
    "Star 2 Time": "# ! @ T * L",
    "Star 1 & 2 Time": "# L * T",
    "Total Time": "# L * T ! @",
    "Total Stars": "# L T B",
    "Global Rank": "# G L * T",
}


class Advent(commands.Cog):
    """
    All of the commands related to Advent of Code (AOC).
    Commands:
        /advent help             - Display help menu
        /advent leaderboard      - Display a leaderboard. Many sorting options and different leaderboard styles
        /advent register         - Register an AOC id to the current discord username. Used for registrating for prizes
        /advent register-force   - Force a registration between an AOC id and a discord user. Used for moderation and admin reasons
        /advent unregister       - Unregister an AOC id to the current discord username.
        /advent unregister-force - Force-remove a registration between an AOC id and a discord user. Used for moderation and admin reasons
        /advent previous-winners - Show the previous winners from a year
        /advent new-winner       - Add a discord user as a winner (chosen directly or by random selection) for prizes
        /advent remove-winner    - Remove a winner for the database
    """

    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self.bot.schedule_task(
            self.reminder_released,
            trigger="cron",
            timezone="Australia/Brisbane",
            hour=15,
            day="1-25",
            month=12,
        )
        self.bot.schedule_task(
            self.reminder_fifteen_minutes,
            trigger="cron",
            timezone="Australia/Brisbane",
            hour=14,
            minute=45,
            day="1-25",
            month=12,
        )

        # A dictionary from a year to the list of members
        self.members_cache: Dict[int, List[Member]] = {}
        self.last_reload_time = datetime.now()

        if isinstance((session_id := os.environ.get("AOC_SESSION_ID")), str):
            # Session cookie (will expire in approx 30 days).
            # See: https://github.com/UQComputingSociety/uqcsbot-discord/wiki/Tokens-and-Environment-Variables#aoc_session_id
            self.session_id: str = session_id
        else:
            raise FatalErrorWithLog(
                bot, "Unable to find AoC session ID. Not loading advent cog."
            )

    advent_command_group = app_commands.Group(
        name="advent", description="Commands for Advent of Code"
    )

    Command = Literal[
        "help",
        "leaderboard",
        "register",
        "register-force",
        "unregister",
        "unregister-force",
        "previous-winners",
        "new-winner",
        "remove-winner",
        "leaderboard_style",
    ]

    @advent_command_group.command(name="help")
    @app_commands.describe(command="The command you want to view help about.")
    async def help_command(
        self, interaction: discord.Interaction, command: Optional[Command] = None
    ):
        """
        Print a help message about advent of code.
        """
        match command:
            case None:
                await interaction.response.send_message(
                    """
[Advent of Code](https://adventofcode.com/) is a yearly coding competition that occurs during the first 25 days of december. Coding puzzles are released at 3pm AEST each day, with two stars available for each puzzle. You can spend as long as you like on each puzzle, but UQCS also has a provate leaderboard with prizes on offer.

To join, go to <https://adventofcode.com/> and sign in. The UQCS private leaderboard join code is `989288-0ff5a98d`. To be eligible for prizes, you will also have to link your discord account. This can be done by using the `/advent register` command. Reach out to committee if you are having any issues.

For more help, you can use `/advent help <command name>` to get information about a specific command.
                    """
                )
            case "help":
                await interaction.response.send_message(
                    """
`/advent help` is a help menu for all the Advent of Code commands. If you use `/advent help <command name>` you can see details of a particular command. Not much else to say here, try another command.
                    """
                )
            case "leaderboard":
                await interaction.response.send_message(
                    """
`/advent leaderboard` displays a leaderboard for the Advent of Code challenges. There are two types of leaderboard: for a single day, and for the entire month. These are selected by either providing the `day` option or not. You can also display the leaderboard for a past year or another leaderboard (say another private leaderboard that you have).

There are 6 different sorting options, which do slightly different things depending on whether the leaderboard is for a single day or an entire month. The default sorting method changes on which type of leaderboard you want.
 `Star 1 Time    ` - For single-day leaderboards, this sorts by the shortest time to get star 1 for the given problem. For monthly leaderboards, this sorts by the shortest total star 1 time for all problems.
 `Star 2 Time    ` - For single-day leaderboards, this sorts by the shortest time to get just star 2 for the given problem. For monthly leaderboards, this sorts by the shortest total star 2 time for all problems.
 `Star 1 & 2 Time` - For single-day leaderboards, this sorts by the shortest time to get both stars 1 and 2 for the given problem. For monthly leaderboards, this sorts by the shortest total time working on all the problems.
 `Total Time     ` - This sorts by the sortest total time working on all the problems. For monthly leaderboards, this is the same as `Star 1 & 2 Time`.
 `Total Stars    ` - This sorts by the largest number of total stars collected over the month.
 `Global         ` - This sorts by users global score. Note that this will only show users with global score.

You can also style the leaderboard (i.e. change the columns). The default style will change depending on whether the leaderboard is for a single-day or the entire month, and depending on the sorting method. Styles consist of a string, with each character representing a column. Use `/advent help leaderboard-style` to see the possoble characters.
                    """
                )
            case "leaderboard_style":
                await interaction.response.send_message(
                    """
Not a command, but an option given to the command `/advent leaderboard` controling the columns in the leaderboard. Each character in the given string represents a certain column. The possible characters are:
The characters in the string can be:
 `#    ` - Provides a column of the form "XXX)" telling the order for the given leaderboard
 `1    ` - The time for star 1 for the specific day (daily leaderboards only)
 `2    ` - The time for star 2 for the specific day (daily leaderboards only)
 `3    ` - The time for both stars for the specific day (daily leaderboards only)
 `!    ` - The total time spent on first stars for the whole competition
 `@    ` - The total time spent on second stars for the whole competition
 `T    ` - The total time spent overall for the whole competition
 `*    ` - The total number of stars for the whole competition
 `L    ` - The local ranking someone has within the UQCS leaderboard
 `G    ` - The global score someone has
 `B    ` - A progress bar of the stars each person has
 `space` - A padding column of a single character
All other characters will be ignored.
                    """
                )
            case "register":
                await interaction.response.send_message(
                    """
`/advent register` links an Advent of Code account and a discord user so that you are eligble for prizes. Each Advent of Code account and discord account can only be linked to one other account each year. Note that registrations last for only the current year. If you are having any issues with this, message committee to help.
                    """
                )
            case "register-force":
                await interaction.response.send_message(
                    """
`/advent register-force` is an admin-only command to force a registration (i.e. create a registration between any Advent of Code account and Discord user). This can be used for moderation, if someone is having difficulties registering or if you want to register someone for a previous year. This command can break things (such as creating duplicate registrations), so be careful. Exactly one of `aoc_name` or `aoc_id` should be given. Also note that you need to use the Discord ID, not the discord username. If you have developer options enables on your account, this can be found by right clicking on the user and selecting `Copy User ID`.
                    """
                )
            case "unregister":
                await interaction.response.send_message(
                    """
`/advent unregister` unlinks your discord account from the currently linked Advent of Code account. Message committee if you need any help.
                    """
                )
            case "unregister-force":
                await interaction.response.send_message(
                    """
`/advent unregister-force` is an admin-only command that removes a registration from the database. This can be used as a moderation tool, to remove someone who has registered to an Advent of Code account that isn't there. Note that you need to use the Discord ID, not the discord username. If you have developer options enables on your account, this can be found by right clicking on the user and selecting `Copy User ID`.
                    """
                )
            case "previous-winners":
                await interaction.response.send_message(
                    """
`/advent previous-winners` displays the previous winners for a particular year. Note that the records for year prior to 2022 may not be accurate, as the current system was not in use then.
                    """
                )
            case "new-winner":
                await interaction.response.send_message(
                    """
`/advent add-winner` is an admin-only command that allows you to either manually or randomly select winners. Participants will only be eligible to win if they have completed at least one star within the given times. For manual selection, provide an Advent of Code user ID (note that this is not the same as their Advent of Code name), otherwise a random winner will be drawn.
                    
The arguments for the command have a bit of nuance. They are as follow:
 `prize                   ` - A description of the prize to be given. This will be displayed when the winner is selected and if `/advent previous-winners` is used.
 `start` & `end           ` - The initial and final dates (inclusive) of the time range of the prize. To be eligible to win, participants need to get a star from ode of these days. The weights of the selected winner are determined from this range as well.
 `number_of_winners       ` - The number of winners to randomly select.
 `allow_repeat_winners    ` -  This allows participants to win multiple times from the same selection if `number_of_winners` is greater than 1. Note that regardless of this option, someone can win multiple times in a year, just not in a single selection.
 `allow_unregistered_users` - This allows Advent of Code accounts that do not have a linked discord account to win. Note that it can be difficult to give out prizes to users that do not have a linked discord.
 `year                    ` - The year the prize is for.
                    """
                )
            case "remove-winner":
                await interaction.response.send_message(
                    """
`/advent remove-winner` is an admin-only command that removes a winner from the database. It uses the database ID (which is distinct from the Advent of code user ID and the Discord user ID). You can find these ids by running `/advent previous-winners show_ids:True`.
                    """
                )

    @advent_command_group.command(name="leaderboard")
    @app_commands.describe(
        day="Day of the leaderboard [1-25]. If not given (default), the entire month leaderboard is given.",
        year="Year of the leaderboard. Defaults to this year.",
        code="The leaderboard code. Defaults to the UQCS leaderboard.",
        sortby="The method to sort the leaderboard.",
        leaderboard_style="The display format of the leaderboard. See the help menu for more information.",
    )
    async def leaderboard_command(
        self,
        interaction: discord.Interaction,
        day: Optional[Day] = None,
        year: Optional[int] = None,
        code: int = UQCS_LEADERBOARD,
        sortby: Optional[SortingMethod] = None,
        leaderboard_style: Optional[str] = None,
    ):
        """
        Display an advent of code leaderboard.
        """
        if (not day is None) and (day not in ADVENT_DAYS):
            await interaction.response.send_message(
                "The day given is not a valid advent of code day."
            )
            return

        await interaction.response.defer(thinking=True)

        if year is None:
            year = datetime.now().year
        if sortby is None:
            sortby = "Star 1 & 2 Time" if day else "Total Stars"
        if leaderboard_style is None:
            leaderboard_style = (
                leaderboards_for_day[sortby] if day else leaderboards_for_month[sortby]
            )

        try:
            members = self._get_members(year, code)
        except InvalidHTTPSCode:
            await interaction.edit_original_response(
                content="Error fetching leaderboard data. Check the leaderboard code and year."
            )
            return
        except AssertionError:
            await interaction.edit_original_response(
                content="Error parsing leaderboard data."
            )
            return

        if code == UQCS_LEADERBOARD:
            message = ":star: *Advent of Code UQCS Leaderboard* :trophy:"
        else:
            message = f":star: *Advent of Code Leaderboard {code}* :trophy:"

        if day:
            message += f"\n:calendar: *Day {day}* (Sorted By {sortby})"
            members = [member for member in members if member.attempted_day(day)]
            members.sort(key=lambda m: sorting_functions_for_day[sortby](m, day))
        else:
            members = [
                member
                for member in members
                if any(member.attempted_day(day) for day in ADVENT_DAYS)
            ]
            members.sort(key=sorting_functions_for_month[sortby])

        if not members:
            await interaction.edit_original_response(
                content="This leaderboard contains no people."
            )
            return

        scoreboard_file = io.BytesIO(
            bytes(
                _print_leaderboard(
                    _parse_leaderboard_column_string(leaderboard_style, self.bot),
                    members,
                    day,
                ),
                "utf-8",
            )
        )
        await interaction.edit_original_response(
            content=message,
            attachments=[
                discord.File(
                    scoreboard_file,
                    filename=f"advent_{code}_{year}_{day}.txt",
                )
            ],
        )

    @advent_command_group.command(name="register")
    @app_commands.describe(
        aoc_name="Your name shown on Advent of Code.",
    )
    async def register_command(self, interaction: discord.Interaction, aoc_name: str):
        """
        Register for prizes by linking your discord to an Advent of Code name.
        """
        # TODO: Check UQCS membership
        await interaction.response.defer(thinking=True)

        id = self._get_unused_registration_id()
        db_session = self.bot.create_db_session()
        year = datetime.now().year

        members = self._get_members(year)
        if aoc_name not in [member.name for member in members]:
            await interaction.edit_original_response(
                content=f"Could not find the Advent of Code name `{aoc_name}` within the UQCS leaderboard."
            )
            return
        member = [member for member in members if member.name == aoc_name]
        if len(member) != 1:
            await interaction.edit_original_response(
                content=f"Could not find a unique Advent of Code name `{aoc_name}` within the UQCS leaderboard."
            )
        member = member[0]
        AOC_id = member.id

        query = (
            db_session.query(AOCRegistrations)
            .filter(
                and_(
                    AOCRegistrations.year == year, AOCRegistrations.aoc_userid == AOC_id
                )
            )
            .one_or_none()
        )
        if query is not None:
            await interaction.edit_original_response(
                content=f"Advent of Code name `{aoc_name}` is already registered to <@{query.discord_userid}>. Please contact committee if this is your Advent of Code name."
            )
            return

        discord_id = interaction.user.id
        query = (
            db_session.query(AOCRegistrations)
            .filter(
                and_(
                    AOCRegistrations.year == year,
                    AOCRegistrations.discord_userid == discord_id,
                )
            )
            .one_or_none()
        )
        if query is not None:
            await interaction.edit_original_response(
                content=f"Your discord account (<@{discord_id}>) is already registered to the Advent of Code name `{query.aoc_userid}`. You'll need to unregister to change name."
            )
            return

        db_session.add(
            AOCRegistrations(
                id=id, aoc_userid=AOC_id, year=year, discord_userid=discord_id
            )
        )
        db_session.commit()
        db_session.close()

        await interaction.edit_original_response(
            content=f"Advent of Code name `{aoc_name}` is now registered to <@{discord_id}>."
        )

    @app_commands.default_permissions(manage_guild=True)
    @advent_command_group.command(name="register-force")
    @app_commands.describe(
        year="The year of Advent of Code this registration is for.",
        discord_id="The discord ID number of the user. Note that this is not their username.",
        aoc_name="The name shown on Advent of Code.",
        aoc_id="The AOC id of the user.",
    )
    async def register_admin_command(
        self,
        interaction: discord.Interaction,
        year: int,
        discord_id: int,
        aoc_name: Optional[str] = None,
        aoc_id: Optional[int] = None,
    ):
        """
        Forces a registration entry to be created. For admin use only. Either aoc_name or aoc_id should be given.
        """
        if (aoc_name is None and aoc_id is None) or (
            aoc_name is not None and aoc_id is not None
        ):
            await interaction.response.send_message(
                "Exactly one of `aoc_name` and `aoc_id` must be given.", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        id = self._get_unused_registration_id()
        db_session = self.bot.create_db_session()

        if aoc_name:
            members = self._get_members(year, force_refresh=True)
            if aoc_name not in [member.name for member in members]:
                await interaction.edit_original_response(
                    content=f"Could not find the Advent of Code name `{aoc_name}` within the UQCS leaderboard."
                )
                return
            member = [member for member in members if member.name == aoc_name]
            if len(member) != 1:
                await interaction.edit_original_response(
                    content=f"Could not find a unique Advent of Code name `{aoc_name}` within the UQCS leaderboard."
                )
            member = member[0]
            aoc_id = member.id

        query = (
            db_session.query(AOCRegistrations)
            .filter(
                and_(
                    AOCRegistrations.year == year, AOCRegistrations.aoc_userid == aoc_id
                )
            )
            .one_or_none()
        )
        if query is not None:
            await interaction.edit_original_response(
                content=f"Advent of Code name `{aoc_name}` is already registered to <@{query.discord_userid}>."
            )
            return

        db_session.add(
            AOCRegistrations(
                id=id, aoc_userid=aoc_id, year=year, discord_userid=discord_id
            )
        )
        db_session.commit()
        db_session.close()

        await interaction.edit_original_response(
            content=f"Advent of Code name `{aoc_name}` is now registered to <@{discord_id}> (for {year})."
        )

    @advent_command_group.command(name="unregister")
    async def unregister_command(self, interaction: discord.Interaction):
        """
        Remove your registration for Advent of code prizes.
        """
        await interaction.response.defer(thinking=True)

        db_session = self.bot.create_db_session()
        year = datetime.now().year

        discord_id = interaction.user.id
        query = db_session.query(AOCRegistrations).filter(
            and_(
                AOCRegistrations.year == year,
                AOCRegistrations.discord_userid == discord_id,
            )
        )
        if (query.one_or_none()) is None:
            await interaction.edit_original_response(
                content=f"Your discord account (<@{discord_id}>) is already unregistered for this year."
            )
            return

        query.delete(synchronize_session=False)
        db_session.commit()
        db_session.close()

        await interaction.edit_original_response(
            content=f"<@{discord_id}> is no longer registered to win Advent of Code prizes."
        )

    @app_commands.default_permissions(manage_guild=True)
    @advent_command_group.command(name="unregister-force")
    @app_commands.describe(
        year="Year that the registration is for",
        discord_id="The discord id to remove. Note that this is not the username.",
    )
    async def unregister_admin_command(
        self, interaction: discord.Interaction, year: int, discord_id: int
    ):
        """
        Forces a registration entry to be removed.
        For admin use only; assumes you know what you are doing.
        """
        await interaction.response.defer(thinking=True)

        db_session = self.bot.create_db_session()
        query = db_session.query(AOCRegistrations).filter(
            and_(
                AOCRegistrations.year == year,
                AOCRegistrations.discord_userid == discord_id,
            )
        )
        if (query.one_or_none()) is None:
            await interaction.edit_original_response(
                content=f"This discord account (<@{discord_id}>) is already unregistered for this year. Ensure that you enter the users discord id, not discord name or nickname."
            )
            return

        query.delete(synchronize_session=False)
        db_session.commit()
        db_session.close()

        await interaction.edit_original_response(
            content=f"<@{discord_id}> is no longer registered to win Advent of Code prizes for {year}."
        )

    @advent_command_group.command(name="previous-winners")
    @app_commands.describe(
        year="Year to find the previous listed winners for. Defaults to the current year.",
        show_ids="Whether to show the database ids. Mainly for debugging purposes. Defaults to false.",
    )
    async def previous_winners_command(
        self,
        interaction: discord.Interaction,
        year: Optional[int] = None,
        show_ids: bool = False,
    ):
        """
        List the previous winners of Advent of Code.
        """
        await interaction.response.defer(thinking=True)
        if year is None:
            year = datetime.now().year

        db_session = self.bot.create_db_session()
        prev_winners = list(
            db_session.query(AOCWinners).filter(AOCWinners.year == year)
        )

        if not prev_winners:
            await interaction.edit_original_response(
                content=f"No Advent of Code winners are on record for {year}."
            )
            return

        registrations = self._get_registrations(year)
        registered_AOC_ids = [member.aoc_userid for member in registrations]

        # TODO would an embed be appropriate?
        message = f"UQCS Advent of Code winners for {year}:"
        for winner in prev_winners:
            message += f"\n{winner.id} " if show_ids else "\n"

            name = [
                member.name
                for member in self._get_members(year)
                if member.id == winner.aoc_userid
            ]
            # There are three types of user:
            #  1) Those who are not on the downloaded members list from AOC (error case)
            #  2) Those who have not linked a discord account
            #  3) Those who have linked a discord account
            if len(name) != 1:
                message += f"Unknown User (AOC id {winner.aoc_userid}) - {winner.prize}"
            elif winner.aoc_userid not in registered_AOC_ids:
                message += f"{name[0]} (unregisted discord) - {winner.prize}"
            else:
                discord_user = await self.bot.fetch_user(
                    [user.discord_userid for user in registrations][0]
                )
                message += f"{name[0]} (@{discord_user.display_name}) - {winner.prize}"
        db_session.commit()
        db_session.close()

        await interaction.edit_original_response(content=message)

    @app_commands.default_permissions(manage_guild=True)
    @advent_command_group.command(name="add-winners")
    @app_commands.describe(
        prize="A description of the prize that is being awarded.",
        start="The initial date (inclusive) to base the weights on. Defaults to 1.",
        end="The final date (includive) to base the weights on. Defaults to 25.",
        number_of_winners="The number of winners to select. Defaults to 1.",
        weights='How to bias the winner selection. Defaults to "Equal"',
        allow_repeat_winners="Allow for winners to be selected multiple times. Defaults to False",
        allow_unregistered_users="Allow winners to be selected from unregistered users. Defaults to False.",
        year="The year the prize is for. Defaults to the current year.",
        aoc_id="The AOC id of the winner to add, if selecting a winner. Use only if manually selecting a winner.",
    )
    async def add_winners_command(
        self,
        interaction: discord.Interaction,
        prize: str,
        start: int = 1,
        end: int = 25,
        number_of_winners: int = 1,
        weights: Literal["Stars", "Equal"] = "Equal",
        allow_repeat_winners: bool = False,
        allow_unregistered_users: bool = False,
        year: Optional[int] = None,
        aoc_id: Optional[int] = None,
    ):
        """
        Randomly choose (or select) winners from those who have completed challenges.
        """

        await interaction.response.defer(thinking=True)
        if year is None:
            year = datetime.now().year

        if aoc_id:
            self._add_winners(
                [member for member in self._get_members(year) if member.id == aoc_id],
                year,
                prize,
            )
            # Note that this message is a bit more dull, as it should only be used for admin reasons.
            await interaction.edit_original_response(
                content=f"The user with AOC id {aoc_id} has been recorded as winning a prize: {prize}"
            )
            return

        registrations = self._get_registrations(year)
        registered_AOC_ids = [member.aoc_userid for member in registrations]

        potential_winners = [
            member
            for member in self._get_members(year)
            if any(member.attempted_day(day) for day in range(start, end + 1))
        ]
        if not allow_unregistered_users:
            potential_winners = [
                member
                for member in potential_winners
                if member.id in registered_AOC_ids
            ]

        if allow_repeat_winners:
            required_number_of_potential_winners = 1
        else:
            required_number_of_potential_winners = number_of_winners

        if len(potential_winners) < required_number_of_potential_winners:
            await interaction.edit_original_response(
                content=f"There were not enough eligible users to select winners (at least {required_number_of_potential_winners} needed; only {len(potential_winners)} found)."
            )
            return

        match weights:
            case "Stars":
                weight_values = [
                    sum(len(member.times[day]) for day in range(start, end + 1))
                    for member in potential_winners
                ]
            case "Equal":
                weight_values = [1 for _ in potential_winners]

        if allow_repeat_winners:
            winners = choices(potential_winners, weight_values, k=number_of_winners)
        else:
            winners = self._random_choices_without_repition(
                potential_winners, weight_values, number_of_winners
            )

        if not winners:
            await interaction.edit_original_response(
                content="There was some problem choosing the winners."
            )
            return

        self._add_winners(winners, year, prize)

        distinct_winners = set(winners)
        if len(distinct_winners) == 1:
            (winner,) = distinct_winners
            discord_id = winner.get_discord_userid(self.bot)
            discord_ping = f" (<@{discord_id})" if discord_id else ""
            await interaction.edit_original_response(
                content=f"The results are in! Out of {len(potential_winners)} potential participants, {winner.name}{discord_ping} has recieved a prize from participating in Advent of Code: {prize}"
            )
            return

        winners_message = ""
        for i, winner in enumerate(distinct_winners):
            discord_id = winner.get_discord_userid(self.bot)
            discord_ping = f" (<@{discord_id})" if discord_id else ""
            number_of_prizes = len(
                [member for member in winners if member.id == winner.id]
            )
            prize_multiplier = f" (x{number_of_prizes})" if number_of_prizes > 1 else ""
            winners_message += f"{winner.name}{discord_ping}{prize_multiplier}"
            winners_message += ", " if i < len(distinct_winners) - 1 else " and "

        await interaction.edit_original_response(
            content=f"The results are in! Out of {len(potential_winners)} potential participants, {winners_message} have recieved a prize from participating in Advent of Code: {prize}"
        )

    @app_commands.default_permissions(manage_guild=True)
    @advent_command_group.command(name="remove-winner")
    @app_commands.describe(
        id="The database entry id for the winners database that should be deleted."
    )
    async def remove_winner_command(self, interaction: discord.Interaction, id: int):
        """
        Remove an AOC winner from the database.
        The show_ids option for previous-winners can get the id.
        """
        await interaction.response.defer(thinking=True)

        db_session = self.bot.create_db_session()

        query = db_session.query(AOCWinners).filter(AOCWinners.id == id)
        if query.one_or_none() is None:
            await interaction.response.send_message(
                f"No Advent of Code winners could be found with a database id of {id}."
            )
            return

        query.delete(synchronize_session=False)
        db_session.commit()
        db_session.close()

        await interaction.edit_original_response(
            content=f"Removed the winners entry with id {id}."
        )

    def _get_leaderboard_json(self, year: int, code: int) -> Json:
        """
        Returns a json dump of the leaderboard
        """
        try:
            response = requests.get(
                LEADERBOARD_URL.format(year=year, code=code),
                cookies={"session": self.session_id},
            )
        except RequestException as exception:
            raise FatalErrorWithLog(
                self.bot,
                f"Could not get the leaderboard from Advent of Code. For more information {exception}",
            )
        if response.status_code != 200:
            raise InvalidHTTPSCode(
                "Expected a HTTPS status code of 200.", response.status_code
            )
        try:
            return response.json()
        except ValueError as exception:  # json.JSONDecodeError
            raise FatalErrorWithLog(
                self.bot,
                f"Could not interpret the JSON from Advent of Code (AOC). This suggests that AOC no longer provides JSON or something went very wrong. For more information: {exception}",
            )

    def _get_members(
        self, year: int, code: int = UQCS_LEADERBOARD, force_refresh: bool = False
    ):
        """
        Returns the list of members in the leaderboard for the given year and leaderboard code.
        It will attempt to retrieve from a cache if 15 minutes has not passed.
        This can be overriden by setting force refresh.
        """
        if (
            force_refresh
            or (datetime.now() - self.last_reload_time >= CACHE_TIME)
            or year not in self.members_cache
        ):
            leaderboard = self._get_leaderboard_json(year, code)
            self.members_cache[year] = [
                Member.from_member_data(data, year)
                for data in leaderboard["members"].values()
            ]
        return self.members_cache[year]

    def _get_registrations(self, year: int) -> Iterable[AOCRegistrations]:
        """
        Get all registrations linking an AOC id to a discord account.
        """
        db_session = self.bot.create_db_session()
        registrations = db_session.query(AOCRegistrations).filter(
            AOCRegistrations.year == year
        )
        db_session.commit()
        db_session.close()
        return registrations

    async def reminder_fifteen_minutes(self):
        """
        The function used within the AOC reminder 15 minutes before each challenge starts.
        """
        channel = discord.utils.get(
            self.bot.uqcs_server.channels, name=self.bot.AOC_CNAME
        )
        if channel is None:
            logging.warning(f"Could not find required channel #{self.bot.AOC_CNAME}")
            return
        if not isinstance(channel, discord.TextChannel):
            logging.warning(
                f"Channel #{self.bot.AOC_CNAME} was expected to be a text channel, but was not"
            )
            return
        await channel.send("Today's Advent of Code puzzle is released in 15 minutes.")

    async def reminder_released(self):
        """
        The function used within the AOC reminder when each challenge starts.
        """
        channel = discord.utils.get(
            self.bot.uqcs_server.channels, name=self.bot.AOC_CNAME
        )
        if channel is None:
            logging.warning(f"Could not find required channel #{self.bot.AOC_CNAME}")
            return
        if not isinstance(channel, discord.TextChannel):
            logging.warning(
                f"Channel #{self.bot.AOC_CNAME} was expected to be a text channel, but was not"
            )
            return
        await channel.send(
            "Today's Advent of Code puzzle has been released. Good luck!"
        )

    def _get_previous_winner_aoc_ids(self, year: int) -> List[int]:
        """
        Returns a list of all winner aoc ids for a year
        """
        db_session = self.bot.create_db_session()
        prev_winners = db_session.query(AOCWinners).filter(AOCWinners.year == year)
        db_session.commit()
        db_session.close()

        return [winner.aoc_userid for winner in prev_winners]

    def _add_winners(self, winners: List[Member], year: int, prize: str):
        """
        Add all members within the list to the database
        """
        for winner in winners:
            id = self._get_unused_winner_id()
            db_session = self.bot.create_db_session()
            db_session.add(
                AOCWinners(id=id, aoc_userid=winner.id, year=year, prize=prize)
            )
            db_session.commit()
            db_session.close()

    def _random_choices_without_repition(
        self, population: List[Member], weights: List[int], k: int
    ) -> List[Member]:
        """
        Selects k people from a list of members, weighted by weights.
        The weight of a person is like how many tickets they have for the lottery.
        """
        result: List[Member] = []
        for _ in range(k):
            if sum(weights) == 0:
                return []

            result.append(choices(population, weights)[0])
            index = population.index(result[-1])
            population.pop(index)
            weights.pop(index)

        return result

    def _get_unused_winner_id(self) -> int:
        """Returns a AOCWinner id that is not currently in use"""
        db_session = self.bot.create_db_session()
        prev_winners = db_session.query(AOCWinners)
        db_session.commit()
        db_session.close()
        winner_ids = [winner.id for winner in prev_winners]
        i = 1
        while (id := i) in winner_ids:
            i += 1
        return id

    def _get_unused_registration_id(self) -> int:
        """Returns a AOCRegistration id that is not currently in use"""
        db_session = self.bot.create_db_session()
        prev_registrations = db_session.query(AOCRegistrations)
        db_session.commit()
        db_session.close()
        registration_ids = [registration.id for registration in prev_registrations]
        i = 1
        while (id := i) in registration_ids:
            i += 1
        return id


class LeaderboardColumn:
    """
    A column in a leaderboard. The title is the name of the column as 2 lines and the calculation is a function that determines what is printed for a given member, index and day. The title and calculation should have the same constant width.
    """

    def __init__(
        self,
        title: tuple[str, str],
        calculation: Callable[[Member, int, Optional[Day]], str],
    ):
        self.title = title
        self.calculation = calculation

    @staticmethod
    def ordering_column():
        """
        A column used at the right of leaderboards to indicate the overall order. Of the format "XXX)" where XXX is a left padded number of 3 characters.
        """
        return LeaderboardColumn(
            title=(" " * 4, " " * 4),  # Empty spaces, as this does not need a heading
            calculation=lambda _, index, __: f"{index:>3})",
        )

    @staticmethod
    def star1_column():
        """
        A column indicating the time taken to achieve the first star. Of the format "hh:mm:ss" or ">24h". Only applicable for particular days.
        """
        return LeaderboardColumn(
            title=(" " * 8, " Star 1 "),
            calculation=lambda member, _, day: f"{_format_seconds(member.times[day].get(1, 0)) if day else '':>8}",
        )

    @staticmethod
    def star2_column():
        """
        A column indicating the time taken to achieve only the second star. Of the format "hh:mm:ss" or ">24h". Only applicable for particular days.
        """
        return LeaderboardColumn(
            title=(" " * 8, " Star 2 "),
            calculation=lambda member, _, day: f"{_format_seconds(member.get_time_delta(day)) if day else '':>8}",
        )

    @staticmethod
    def star1_and_2_column():
        """
        A column indicating the time taken to achieve both stars. Of the format "hh:mm:ss" or ">24h". Only applicable for particular days.
        """
        return LeaderboardColumn(
            title=(" " * 10, "Both Stars"),
            calculation=lambda member, _, day: f"{_format_seconds(member.times[day].get(2, 0)) if day else '':>10}",
        )

    @staticmethod
    def total_time_column():
        """
        A column indicating the total time the user has spent on all stars. Of the format "hhhh:mm:ss" or ">30 days".
        """
        return LeaderboardColumn(
            title=(" " * 10, "Total Time"),
            calculation=lambda member, _, __: f"{_format_seconds_long(member.get_total_time()):>10}",
        )

    @staticmethod
    def total_star1_time_column():
        """
        A column indicating the total time the user has spent on first stars. Of the format "hhhh:mm:ss" or ">30 days".
        """
        return LeaderboardColumn(
            title=("Total Star", "  1 Time  "),
            calculation=lambda member, _, __: f"{_format_seconds_long(member.get_total_star1_time()):>10}",
        )

    @staticmethod
    def total_star2_time_column():
        """
        A column indicating the total time the user has spent on second stars. Of the format "hhhh:mm:ss" or ">30 days".
        """
        return LeaderboardColumn(
            title=("Total Star", "  2 Time  "),
            calculation=lambda member, _, __: f"{_format_seconds_long(member.get_total_star2_time()):>10}",
        )

    @staticmethod
    def stars_column():
        """
        A column indicating the total number of stars a user has. Of the format of a 5 character right-padded number.
        """
        return LeaderboardColumn(
            title=("Total", "Stars"),
            calculation=lambda member, _, __: f"{member.star_total if member.star_total else '':>5}",
        )

    @staticmethod
    def local_rank_column():
        """
        A column indicating the members local rank (of the UQCS leaderboard). Of the format of a 5 character right-padded number.
        """
        return LeaderboardColumn(
            title=("Local", "Order"),
            calculation=lambda member, _, __: f"{member.local if member.local else '':>5}",
        )

    @staticmethod
    def global_score_column():
        """
        A column indicating the members global score. Of the format of a 5 character right-padded number.
        """
        return LeaderboardColumn(
            title=("Global", "Score "),
            calculation=lambda member, _, __: f"{member.global_ if member.global_ else '':>6}",
        )

    @staticmethod
    def star_bar_column():
        """
        A column with a progressbar of the stars that each person has.
        """
        return LeaderboardColumn(
            title=(" " * 9 + "1" * 10 + "2" * 6, "1234567890123456789012345"),
            calculation=lambda member, _, __: _get_member_star_progress_bar(member),
        )

    @staticmethod
    def name_column(bot: UQCSBot):
        """
        A column listing each name.
        """

        def format_name(member: Member, _: int, __: Optional[int]) -> str:
            if not (discord_userid := member.get_discord_userid(bot)):
                return member.name
            if not (discord_user := bot.get_user(discord_userid)):
                return member.name
            return f"{member.name} (@{discord_user.name})"

        return LeaderboardColumn(title=("", ""), calculation=format_name)

    @staticmethod
    def padding_column():
        """
        A column that is of a single space character.
        """
        return LeaderboardColumn(title=(" ", " "), calculation=lambda _, __, ___: " ")


def _parse_leaderboard_column_string(s: str, bot: UQCSBot) -> List[LeaderboardColumn]:
    """
    Create a list of columns corresponding to the given string. The characters in the string can be:
        #     - Provides a column of the form "XXX)" telling the order for the given leaderboard
        1     - The time for star 1 for the specific day (daily leaderboards only)
        2     - The time for star 2 for the specific day (daily leaderboards only)
        3     - The time for both stars for the specific day (dayly leaderboards only)
        !     - The total time spent on first stars for the whole competition
        @     - The total time spent on second stars for the whole competition
        T     - The total time spent overall for the whole competition
        *     - The total number of stars for the whole competition
        L     - The local ranking someone has within the UQCS leaderboard
        G     - The global score someone has
        B     - A progress bar of the stars each person has
        space - A padding column of a single character
        All other characters will be ignored
    """
    columns: List[LeaderboardColumn] = []
    for c in s:
        match c:
            case "#":
                columns.append(LeaderboardColumn.ordering_column())
            case "1":
                columns.append(LeaderboardColumn.star1_column())
            case "2":
                columns.append(LeaderboardColumn.star2_column())
            case "3":
                columns.append(LeaderboardColumn.star1_and_2_column())
            case "!":
                columns.append(LeaderboardColumn.total_star1_time_column())
            case "@":
                columns.append(LeaderboardColumn.total_star2_time_column())
            case "T":
                columns.append(LeaderboardColumn.total_time_column())
            case "*":
                columns.append(LeaderboardColumn.stars_column())
            case "L":
                columns.append(LeaderboardColumn.local_rank_column())
            case "G":
                columns.append(LeaderboardColumn.global_score_column())
            case "B":
                columns.append(LeaderboardColumn.star_bar_column())
            case " ":
                columns.append(LeaderboardColumn.padding_column())
            case _:
                pass
    columns.append(LeaderboardColumn.padding_column())
    columns.append(LeaderboardColumn.name_column(bot))
    return columns


def _star_char(num_stars: int):
    """
    Given a number of stars (0, 1, or 2), returns its leaderboard
    representation.
    """
    return " .*"[num_stars]


def _format_seconds(seconds: Optional[int]):
    """
    Format seconds into the format "hh:mm:ss" or ">24h".
    """
    if seconds is None or seconds == 0:
        return ""
    delta = timedelta(seconds=seconds)
    if delta > timedelta(hours=24):
        return ">24h"
    return str(delta)


def _format_seconds_long(seconds: Optional[int]):
    """
    Format seconds into the format "hhhh:mm:ss" or ">30 days".
    """
    if seconds is None or seconds == 0:
        return "-"
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours >= 30 * 24:
        return ">30 days"
    return f"{hours}:{minutes:02}:{seconds:02}"


def _get_member_star_progress_bar(member: Member):
    return "".join(_star_char(len(member.times[day])) for day in ADVENT_DAYS)


def _print_leaderboard(
    columns: List[LeaderboardColumn], members: List[Member], day: Optional[Day]
):
    """
    Returns a string of the leaderboard of the given format.
    """
    leaderboard = "".join(column.title[0] for column in columns)
    leaderboard += "\n"
    leaderboard += "".join(column.title[1] for column in columns)

    # Note that leaderboards start at 1, not 0
    for id, member in enumerate(members, start=1):
        leaderboard += "\n"
        leaderboard += "".join(
            column.calculation(member, id, day) for column in columns
        )

    return leaderboard


async def setup(bot: UQCSBot):
    cog = Advent(bot)

    await bot.add_cog(cog)
