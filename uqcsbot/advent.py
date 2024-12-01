import io
import os
from datetime import datetime
from random import choices
from typing import Any, Callable, Dict, Iterable, List, Optional, Literal
import requests
from requests.exceptions import RequestException

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.bot import UQCSBot
from uqcsbot.models import AOCRegistrations, AOCWinners
from uqcsbot.utils.err_log_utils import FatalErrorWithLog
from uqcsbot.utils.advent_utils import (
    Leaderboard,
    Member,
    Day,
    Json,
    InvalidHTTPSCode,
    ADVENT_DAYS,
    CACHE_TIME,
    HL_COLOUR,
    parse_leaderboard_column_string,
    build_leaderboard,
    render_leaderboard_to_image,
    render_leaderboard_to_text,
)

# Leaderboard API URL with placeholders for year and code.
LEADERBOARD_VIEW_URL = "https://adventofcode.com/{year}/leaderboard/private/view/{code}"
LEADERBOARD_URL = LEADERBOARD_VIEW_URL + ".json"

# UQCS leaderboard ID.
UQCS_LEADERBOARD = 989288

# The maximum time in seconds that a person can complete a challenge in. Used as a maximum value to help with sorting when someone whas not attempted a day.
MAXIMUM_TIME_FOR_STAR = 365 * 24 * 60 * 60

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
    "Total Time": lambda member, day: (
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


class LeaderboardView(discord.ui.View):
    TRUNCATED_COUNT = 20
    TIMEOUT = 180  # seconds

    def __init__(
        self,
        bot: UQCSBot,
        inter: discord.Interaction,
        code: int,
        year: int,
        day: Optional[Day],
        members: list[Member],
        leaderboard_style: str,
        sortby: Optional[SortingMethod],
    ):
        super().__init__(timeout=self.TIMEOUT)

        # constant within one embed
        self.bot = bot
        self.inter = inter
        self.code = code
        self.year = year
        self.day = day
        self.all_members = members
        self.leaderboard_style = leaderboard_style
        self.sortby = sortby
        self.timestamp = datetime.now()
        self.basename = f"advent_{self.code}_{self.year}_{self.day}"

        # can be changed by interaction
        self._visible_members = members[: self.TRUNCATED_COUNT]

    @property
    def is_truncated(self):
        return len(self._visible_members) < len(self.all_members)

    def _build_leaderboard(self, members: List[Member]) -> Leaderboard:
        return build_leaderboard(
            parse_leaderboard_column_string(self.leaderboard_style, self.bot),
            members,
            self.day,
        )

    def make_message_arguments(self) -> Dict[str, Any]:
        view_url = LEADERBOARD_VIEW_URL.format(year=self.year, code=self.code)

        title = (
            "Advent of Code UQCS Leaderboard"
            if self.code == UQCS_LEADERBOARD
            else f"Advent of Code Leaderboard `{self.code}`"
        )
        title = f":star: {title} :trophy:"
        if self.day:
            title += f" \u2014 Day {self.day}"

        notes: List[str] = []
        if self.day:
            notes.append(f"sorted by {self.sortby}")
        if self.is_truncated:
            notes.append(
                f"top {len(self._visible_members)} shown out of {len(self.all_members)}"
            )
        body = f"({', '.join(notes)})" if notes else ""

        embed = discord.Embed(
            title=title,
            url=view_url,
            description=body,
            colour=discord.Colour.from_str(HL_COLOUR),
            timestamp=self.timestamp,
        )

        leaderboard = self._build_leaderboard(self._visible_members)
        scoreboard_image = render_leaderboard_to_image(leaderboard)
        file = discord.File(io.BytesIO(scoreboard_image), self.basename + ".png")
        embed.set_image(url=f"attachment://{file.filename}")

        self.show_all_interaction.disabled = (
            len(self.all_members) <= self.TRUNCATED_COUNT
        )
        self.show_all_interaction.label = (
            "Show all" if self.is_truncated else "Show less"
        )

        return {
            "attachments": [file],
            "embed": embed,
            "view": self,
        }

    @discord.ui.button(label="Show all", style=discord.ButtonStyle.gray)
    async def show_all_interaction(
        self, inter: discord.Interaction, btn: discord.ui.Button["LeaderboardView"]
    ):
        self._visible_members = (
            self.all_members
            if self.is_truncated
            else self.all_members[: self.TRUNCATED_COUNT]
        )
        await inter.response.edit_message(**self.make_message_arguments())

    @discord.ui.button(label="Export as text", style=discord.ButtonStyle.gray)
    async def get_text_interaction(
        self, inter: discord.Interaction, btn: discord.ui.Button["LeaderboardView"]
    ):
        """
        Sends the text leaderboard as a file attachment within a new reply.
        """
        leaderboard = self._build_leaderboard(self.all_members)
        text = render_leaderboard_to_text(leaderboard)
        file = discord.File(io.BytesIO(text.encode("utf-8")), self.basename + ".txt")
        await inter.response.send_message(file=file)

        btn.disabled = True
        await self.inter.edit_original_response(view=self)

    async def on_timeout(self) -> None:
        """
        Detach interactable view on timeout.
        """
        await self.inter.edit_original_response(view=None)


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

    @commands.Cog.listener()
    async def on_ready(self):
        channel = discord.utils.get(
            self.bot.uqcs_server.channels, name=self.bot.AOC_CNAME
        )
        if isinstance(channel, discord.TextChannel):
            self.channel = channel
        else:
            raise FatalErrorWithLog(
                self.bot,
                f"Could not find channel #{self.bot.AOC_CNAME} for advent of code cog.",
            )
        role = discord.utils.get(self.bot.uqcs_server.roles, name=self.bot.AOC_ROLE)
        if isinstance(role, discord.Role):
            self.role = role
        else:
            raise FatalErrorWithLog(
                self.bot,
                f"Could not find role @{self.bot.AOC_ROLE} for advent of code cog",
            )

    def _get_leaderboard_json(self, year: int, code: int) -> Json:
        """
        Returns a json dump of the leaderboard
        """
        try:
            response = requests.get(
                LEADERBOARD_URL.format(year=year, code=code),
                cookies={"session": self.session_id},
                allow_redirects=False,  # Will redirct to home page if session token is out of date
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

    def _get_registrations(self) -> Iterable[AOCRegistrations]:
        """
        Get all registrations linking an AOC id to a discord account.
        """
        db_session = self.bot.create_db_session()
        registrations = db_session.query(AOCRegistrations)
        db_session.commit()
        db_session.close()
        return registrations

    async def reminder_fifteen_minutes(self):
        """
        The function used within the AOC reminder 15 minutes before each challenge starts.
        """
        await self.channel.send(
            f"{self.role.mention} Today's Advent of Code puzzle is released in 15 minutes.",
            allowed_mentions=discord.AllowedMentions(
                everyone=False, users=False, roles=True
            ),
        )

    async def reminder_released(self):
        """
        The function used within the AOC reminder when each challenge starts.
        """
        await self.channel.send(
            f"{self.role.mention} Today's Advent of Code puzzle has been released. Good luck!",
            allowed_mentions=discord.AllowedMentions(
                everyone=False, users=False, roles=True
            ),
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
            db_session = self.bot.create_db_session()
            db_session.add(AOCWinners(aoc_userid=winner.id, year=year, prize=prize))
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
[Advent of Code](https://adventofcode.com/) is a yearly coding competition that occurs during the first 25 days of december. Coding puzzles are released at 3pm AEST each day, with two stars available for each puzzle. You can spend as long as you like on each puzzle, but UQCS also has a private leaderboard with prizes on offer.

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
 `weights                 ` - How the winners are selected. For "Equal", each eligible participant has an equal probability of winning. For "Stars", it is as if each user gets a "raffle ticket" for each star they completed within the timeframe, meaning more stars provides a greater chance of winning.
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
                content="Error fetching leaderboard data. Check the leaderboard code and year. If this keeps occurring, reach out to committee, as this may be due to an invalid session token."
            )
            return
        except AssertionError:
            await interaction.edit_original_response(
                content="Error parsing leaderboard data."
            )
            return

        if day:
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

        view = LeaderboardView(
            self.bot, interaction, code, year, day, members, leaderboard_style, sortby
        )
        await interaction.edit_original_response(**view.make_message_arguments())

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

        db_session = self.bot.create_db_session()
        year = datetime.now().year

        members = self._get_members(year)
        if aoc_name not in [member.name for member in members]:
            await interaction.edit_original_response(
                content=(
                    f"Could not find the Advent of Code name `{aoc_name}` within the UQCS leaderboard. Make sure your name appears at: "
                    + LEADERBOARD_VIEW_URL.format(code=UQCS_LEADERBOARD, year=year)
                )
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
            .filter(AOCRegistrations.aoc_userid == AOC_id)
            .one_or_none()
        )
        if query is not None:
            discord_user = self.bot.uqcs_server.get_member(query.discord_userid)
            is_self = False
            if discord_user:
                discord_ping = discord_user.mention
                is_self = discord_user.id == interaction.user.id
            else:
                discord_ping = f"someone who doesn't seem to be in the server (discord id = {query.discord_userid})"
            if not is_self:
                message = f"Advent of Code name `{aoc_name}` is already registered to {discord_ping}. Please contact committee if this is your Advent of Code name."
            else:
                message = f"Advent of Code name `{aoc_name}` is already registered to you ({discord_ping})! Please contact committee if this is incorrect."
            await interaction.edit_original_response(content=message)
            return

        discord_id = interaction.user.id
        query = (
            db_session.query(AOCRegistrations)
            .filter(
                AOCRegistrations.discord_userid == discord_id,
            )
            .one_or_none()
        )
        if query is not None:
            await interaction.edit_original_response(
                content=f"Your discord account ({interaction.user.mention}) is already registered to the Advent of Code name `{query.aoc_userid}`. You'll need to unregister to change name."
            )
            return

        db_session.add(
            AOCRegistrations(aoc_userid=AOC_id, discord_userid=discord_id, year=2024)
        )  # this is a quick fix unitl we drop the column in the database
        db_session.commit()
        db_session.close()

        await interaction.edit_original_response(
            content=f"Advent of Code name `{aoc_name}` is now registered to {interaction.user.mention}."
        )

    @app_commands.checks.has_permissions(manage_guild=True)
    @advent_command_group.command(name="register-force")
    @app_commands.describe(
        year="The year of Advent of Code this registration is for.",
        discord_id_str="The discord ID number of the user. Note that this is not their username.",
        aoc_name="The name shown on Advent of Code.",
        aoc_id="The AOC id of the user.",
    )
    async def register_admin_command(
        self,
        interaction: discord.Interaction,
        year: int,
        discord_id_str: str,  # str as discord can't handle integers this big
        aoc_name: Optional[str] = None,
        aoc_id: Optional[int] = None,
    ):
        """
        Forces a registration entry to be created. For admin use only. Either aoc_name or aoc_id should be given.
        """
        discord_id = int(discord_id_str)
        if (aoc_name is None and aoc_id is None) or (
            aoc_name is not None and aoc_id is not None
        ):
            await interaction.response.send_message(
                "Exactly one of `aoc_name` and `aoc_id` must be given.", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

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
            .filter(AOCRegistrations.aoc_userid == aoc_id)
            .one_or_none()
        )
        if query is not None:
            discord_user = self.bot.uqcs_server.get_member(query.discord_userid)
            if discord_user:
                discord_ping = discord_user.mention
            else:
                discord_ping = f"someone who doesn't seem to be in the server (discord id = {query.discord_userid})"
            await interaction.edit_original_response(
                content=f"Advent of Code name `{aoc_name}` is already registered to {discord_ping}."
            )
            return

        db_session.add(
            AOCRegistrations(aoc_userid=aoc_id, discord_userid=discord_id, year=2024)
        )  # this is a quick fix unitl we drop the column in the database
        db_session.commit()
        db_session.close()

        discord_user = self.bot.uqcs_server.get_member(discord_id)
        if discord_user:
            discord_ping = discord_user.mention
        else:
            discord_ping = f"someone who doesn't seem to be in the server (discord id = {discord_id})"
        await interaction.edit_original_response(
            content=f"Advent of Code name `{aoc_name}` is now registered to {discord_ping}."
        )

    @advent_command_group.command(name="unregister")
    async def unregister_command(self, interaction: discord.Interaction):
        """
        Remove your registration for Advent of code prizes.
        """
        await interaction.response.defer(thinking=True)

        db_session = self.bot.create_db_session()

        discord_id = interaction.user.id
        query = db_session.query(AOCRegistrations).filter(
            AOCRegistrations.discord_userid == discord_id,
        )
        if (query.one_or_none()) is None:
            await interaction.edit_original_response(
                content=f"Your discord account ({interaction.user.mention}) is already unregistered for this year."
            )
            return

        query.delete(synchronize_session=False)
        db_session.commit()
        db_session.close()

        await interaction.edit_original_response(
            content=f"{interaction.user.mention} is no longer registered to win Advent of Code prizes."
        )

    @app_commands.checks.has_permissions(manage_guild=True)
    @advent_command_group.command(name="unregister-force")
    @app_commands.describe(
        year="Year that the registration is for",
        discord_id_str="The discord id to remove. Note that this is not the username.",
    )
    async def unregister_admin_command(
        self, interaction: discord.Interaction, year: int, discord_id_str: str
    ):
        """
        Forces a registration entry to be removed.
        For admin use only; assumes you know what you are doing.
        """
        discord_id = int(discord_id_str)
        await interaction.response.defer(thinking=True)
        discord_user = self.bot.uqcs_server.get_member(discord_id)

        db_session = self.bot.create_db_session()
        query = db_session.query(AOCRegistrations).filter(
            AOCRegistrations.discord_userid == discord_id,
        )
        if (query.one_or_none()) is None:
            if discord_user:
                discord_ping = discord_user.mention
            else:
                discord_ping = (
                    f"who does not seem to be in the server; id = {discord_id}"
                )
            await interaction.edit_original_response(
                content=f"This discord account ({discord_ping}) is already unregistered for this year. Ensure that you enter the users discord id, not discord name or nickname."
            )
            return

        query.delete(synchronize_session=False)
        db_session.commit()
        db_session.close()

        if discord_user:
            discord_ping = discord_user.mention
        else:
            discord_ping = (
                f"A user who does not seem to be in the server (id = {discord_id})"
            )
        await interaction.edit_original_response(
            content=f"{discord_ping} is no longer registered to win Advent of Code prizes for {year}."
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

        registrations = self._get_registrations()
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
                discord_user = self.bot.uqcs_server.get_member(
                    [user.discord_userid for user in registrations][0]
                )
                discord_ping = f" ({discord_user.display_name})" if discord_user else ""
                # Don't actually ping as this may be called many times
                message += f"{name[0]}{discord_ping}  - {winner.prize}"
        db_session.commit()
        db_session.close()

        await interaction.edit_original_response(content=message)

    @app_commands.checks.has_permissions(manage_guild=True)
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

        registrations = self._get_registrations()
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
        number_of_potential_winners = len(
            potential_winners
        )  # potential winners will be changed ahead, so we store this value for the award message

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

        winners_message = ""
        for i, winner in enumerate(distinct_winners):
            discord_id = winner.get_discord_userid(self.bot)
            discord_user = (
                self.bot.uqcs_server.get_member(discord_id) if discord_id else None
            )
            discord_ping = f" ({discord_user.mention})" if discord_user else ""
            number_of_prizes = len(
                [member for member in winners if member.id == winner.id]
            )
            prize_multiplier = f" (x{number_of_prizes})" if number_of_prizes > 1 else ""
            winners_message += f"{winner.name}{discord_ping}{prize_multiplier}"
            if len(distinct_winners) == 1:
                pass
            elif i < len(distinct_winners) - 1:
                winners_message += ", "
            else:
                winners_message += " and "

        await interaction.edit_original_response(
            content=f"The results are in! Out of {number_of_potential_winners} potential participants, {winners_message} have recieved a prize from participating in Advent of Code: {prize}",
            allowed_mentions=discord.AllowedMentions(
                everyone=False, users=True, roles=False
            ),
        )

    @app_commands.checks.has_permissions(manage_guild=True)
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


async def setup(bot: UQCSBot):
    cog = Advent(bot)

    await bot.add_cog(cog)
