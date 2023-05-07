import io
import logging
import os
from argparse import ArgumentParser, Namespace
from datetime import datetime, timedelta, timezone
from enum import Enum
from random import choices
from typing import Any, Callable, Dict, List, Optional, Tuple

import discord
import requests
from discord.ext import commands
from requests.exceptions import RequestException

from uqcsbot.bot import UQCSBot
from uqcsbot.models import AOCWinner
from uqcsbot.utils.command_utils import loading_status

# Leaderboard API URL with placeholders for year and code.
LEADERBOARD_URL = "https://adventofcode.com/{year}/leaderboard/private/view/{code}.json"
# Session cookie (will expire in approx 30 days).
# See: https://github.com/UQComputingSociety/uqcsbot-discord/wiki/Tokens-and-Environment-Variables#aoc_session_id
SESSION_ID = os.environ.get("AOC_SESSION_ID")
# UQCS leaderboard ID.
UQCS_LEADERBOARD = 989288

# Days in Advent of Code. List of numbers 1 to 25.
ADVENT_DAYS = list(range(1, 25 + 1))
# Puzzles are unlocked at midnight EST.
EST_TIMEZONE = timezone(timedelta(hours=-5))

# Reminder channel ID (Usually #contests)
REMINDER_CHANNEL = 813411377975918622
# REMINDER_CHANNEL = 859723630433665045

class SortMode(Enum):
    """Options for sorting the leaderboard."""
    PART_1 = "p1"
    PART_2 = "p2"
    DELTA = "delta"
    LOCAL = "local"  # SortMode.LOCAL is not shown to users
    GLOBAL = "global"  # SortMode.GLOBAL is not shown to users

    def __str__(self):
        return self.value  # needed so --help prints string values


# Map of sorting options to friendly name.
SORT_LABELS = {SortMode.PART_1: "part 1 completion",
               SortMode.PART_2: "part 2 completion",
               SortMode.DELTA: "time delta"}


def sort_none_last(key):
    """
    Given sort key function, returns new key function which can handle None.

    None values are sorted after non-None values.
    """
    return lambda x: (key(x) is None, key(x))


# type aliases for documentation purposes.
Day = int  # from 1 to 25
Star = int  # 1 or 2
Seconds = int
Times = Dict[Star, Seconds]
Delta = Optional[Seconds]
# TODO: make these types more specific with TypedDict and Literal when possible.

class Member:
    def __init__(self, id: int, name: str, local: int, stars: int, global_: int) -> None:
        self.id = id
        self.name = name
        self.local = local
        self.stars = stars
        self.global_ = global_

        self.all_times: Dict[Day, Times] = {d: {} for d in ADVENT_DAYS}
        self.all_deltas: Dict[Day, Delta] = {d: None for d in ADVENT_DAYS}

        self.day: Optional[Day] = None
        self.day_times: Times = {}
        self.day_delta: Delta = None

    @classmethod
    def from_member_data(cls, data: Dict, year: int, day: Optional[int] = None) -> "Member":
        """
        Constructs a Member from the API response.

        Times and delta are calculated for the given year and day.
        """

        member = cls(data["id"], data["name"], data["local_score"], data["stars"], data["global_score"])

        for d, day_data in data["completion_day_level"].items():
            d = int(d)
            times = member.all_times[d]

            # timestamp of puzzle unlock, rounded to whole seconds
            DAY_START = int(datetime(year, 12, d, tzinfo=EST_TIMEZONE).timestamp())

            for star, star_data in day_data.items():
                star = int(star)
                times[star] = int(star_data["get_star_ts"]) - DAY_START
                assert times[star] >= 0

            if len(times) == 2:
                part_1, part_2 = sorted(times.values())
                member.all_deltas[d] = part_2 - part_1

        # if day is specified, save that day's information into the day_ fields.
        if day:
            member.day = day
            member.day_times = member.all_times[day]
            member.day_delta = member.all_deltas[day]

        return member

    @staticmethod
    def sort_key(sort: SortMode) -> Callable[["Member"], Any]:
        """
        Given sort mode, returns a key function which sorts members
        by that option using the stored times and delta.
        """

        if sort == SortMode.LOCAL:
            # sorts by local score, then stars, descending.
            return lambda m: (-m.local, -m.stars)
        if sort == SortMode.GLOBAL:
            # sorts by global score, then local score, then stars, descending.
            return lambda m: (-m.global_, -m.local, -m.stars)

        # these key functions sort in ascending order of the specified value.
        # E731 advises using function definitions over lambdas which is unreasonable here
        if sort == SortMode.PART_1:
            key = lambda m: m.day_times.get(1)  # noqa: E731
        elif sort == SortMode.PART_2:
            key = lambda m: m.day_times.get(2)  # noqa: E731
        elif sort == SortMode.DELTA:
            key = lambda m: m.day_delta  # noqa: E731
        else:
            assert False

        return sort_none_last(key)

class Advent(commands.Cog):

    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self.bot.schedule_task(self.reminder_released, trigger='cron', timezone='Australia/Brisbane', hour=15, day='1-25', month=12)
        self.bot.schedule_task(self.reminder_fifteen_minutes, trigger='cron', timezone='Australia/Brisbane', hour=14, minute=45, day='1-25', month=12)

    def star_char(self, num_stars: int):
        """
        Given a number of stars (0, 1, or 2), returns its leaderboard
        representation.
        """
        return " .*"[num_stars]


    def format_full_leaderboard(self, members: List[Member]) -> str:
        """
        Returns a string representing the full leaderboard of the given list.

        Full leaderboard includes rank, points, stars (per day), and username.
        """

        #   3     4                        25
        # |-|  |--| |-----------------------|
        #   1)  751 ****************          Name
        def format_member(i: int, m: Member):
            stars = "".join(self.star_char(len(m.all_times[d])) for d in ADVENT_DAYS)
            return f"{i:>3}) {m.local:>4} {stars} {m.name}"

        left = " " * (3 + 2 + 4 + 1)  # chars before stars start
        header = (f"{left}         1111111111222222\n"
                f"{left}1234567890123456789012345\n")

        return header + "\n".join(format_member(i, m) for i, m in enumerate(members, 1))


    def format_global_leaderboard(self, members: List[Member]) -> str:
        """
        Returns a string representing the global leaderboard of the given list.

        Full leaderboard includes rank, global points, and username.
        """

        #   3     4
        # |-|  |--|
        #   1)  751 Name
        def format_member(i: int, m: Member):
            return f"{i:>3}) {m.global_:>4} {m.name}"

        return "\n".join(format_member(i, m) for i, m in enumerate(members, 1))


    def format_day_leaderboard(self, members: List[Member]) -> str:
        """
        Returns a string representing the leaderboard of the given members on
        the given day.

        Full leaderboard includes rank, points, stars (per day), and username.
        """

        def format_seconds(seconds: Optional[int]) -> str:
            if seconds is None:
                return ""
            delta = timedelta(seconds=seconds)
            if delta > timedelta(hours=24):
                return ">24h"
            return str(delta)

        #   3         8        8         8
        # |-|  |------| |------|  |------|
        #       Part 1   Part 2     Delta
        #   1)  0:00:00  0:00:00   0:00:00  Name 1
        #   2)     >24h     >24h      >24h  Name 2
        def format_member(i: int, m: Member) -> str:
            assert m.day is not None
            part_1 = format_seconds(m.day_times.get(1))
            part_2 = format_seconds(m.day_times.get(2))
            delta = format_seconds(m.day_delta)
            return f"{i:>3}) {part_1:>8} {part_2:>8}  {delta:>8}  {m.name}"

        header = "       Part 1   Part 2     Delta\n"
        return header + "\n".join(format_member(i, m) for i, m in enumerate(members, 1))


    def format_advent_leaderboard(self, members: List[Member],
                                is_day: bool, is_global: bool, sort: SortMode) -> str:
        """
        Returns a leaderboard for the given members with the given options.

        If full is True, leaderboard will show progress for all days, otherwise one
        specific day is shown.
        """

        if is_day:
            # filter to users who have at least one star on this day.
            members = [m for m in members if m.day_times]
            members.sort(key=Member.sort_key(sort))
            return self.format_day_leaderboard(members)

        if is_global:
            # filter to users who have global points.
            members = [m for m in members if m.global_]
            members.sort(key=Member.sort_key(SortMode.GLOBAL))
            return self.format_global_leaderboard(members)

        members.sort(key=Member.sort_key(SortMode.LOCAL))
        return self.format_full_leaderboard(members)


    def parse_arguments(self, argv: List[str]) -> Namespace:
        """
        Parses !advent arguments from the given list.

        Returns namespace with argument values or throws UsageSyntaxException.
        If an exception is thrown, its message should be shown to the user and
        execution should NOT continue.
        """
        parser = ArgumentParser("!advent", add_help=False)

        parser.add_argument("day", type=int, default=0, nargs="?",
                            help="Show leaderboard for specific day"
                            + " (default: all days)")
        parser.add_argument("-g", "--global", action="store_true", dest="global_",
                            help="Show global points")
        parser.add_argument("-y", "--year", type=int, default=datetime.now().year,
                            help="Year of leaderboard (default: current year)")
        parser.add_argument("-c", "--code", type=int, default=UQCS_LEADERBOARD,
                            help="Leaderboard code (default: UQCS leaderboard)")
        parser.add_argument("-s", "--sort", default=SortMode.PART_2, type=SortMode,
                            choices=(SortMode.PART_1, SortMode.PART_2, SortMode.DELTA),
                            help="Sorting method when displaying one day"
                            + " (default: part 2 completion time)")
        parser.add_argument("-h", "--help", action="store_true",
                            help="Prints this help message")

        # used to propagate usage errors out.
        # somewhat hacky. typically, this should be done by subclassing ArgumentParser
        def usage_error(message, *args, **kwargs):
            raise ValueError(message)
        parser.error = usage_error  # type: ignore

        args = parser.parse_args(argv)

        if args.help:
            raise ValueError("```\n" + parser.format_help() + "\n```")

        return args


    def get_leaderboard(self, year: int, code: int) -> Dict:
        """
        Returns a json dump of the leaderboard
        """
        try:
            response = requests.get(
                LEADERBOARD_URL.format(year=year, code=code),
                cookies={"session": SESSION_ID})
            return response.json()
        except ValueError as exception:  # json.JSONDecodeError
            # TODO: Handle the case when the response is ok but the contents
            # are invalid (cannot be parsed as json)
            raise exception
        except RequestException as exception:
            logging.error(exception.response.content)
            pass
        return None


    @commands.command()
    @loading_status
    async def advent(self, ctx: commands.Context, *args):
        """
        Prints the Advent of Code private leaderboard for UQCS. 
        
        !advent --help for additional help.
        """

        try:
            args = self.parse_arguments( args)
        except ValueError as error:
            await ctx.send(str(error))
            return

        try:
            leaderboard = self.get_leaderboard(args.year, args.code)
        except ValueError:
            await ctx.send("Error fetching leaderboard data. Check the leaderboard code, year, and day.")
            raise

        try:
            members = [Member.from_member_data(data, args.year, args.day)
                    for data in leaderboard["members"].values()]
        except Exception:
            await ctx.send("Error parsing leaderboard data.")
            raise

        # whether to show only one day
        is_day = bool(args.day)
        # whether to use global points
        is_global = args.global_

        # header message
        message = f":star: *Advent of Code Leaderboard {args.code}* :trophy:"
        if is_day:
            message += f"\n:calendar: *Day {args.day}* (sorted by {SORT_LABELS[args.sort]})"
        elif is_global:
            message += "\n:earth_asia: *Global Leaderboard Points*"


        scoreboardFile = io.StringIO(self.format_advent_leaderboard(members, is_day, is_global, args.sort))
        await ctx.send(file=discord.File(scoreboardFile, filename=f"advent_{args.code}_{args.year}_{args.day}.txt"))


    async def reminder_fifteen_minutes(self):
        await self.bot.get_channel(REMINDER_CHANNEL).send("Today's Advent of Code puzzle is released in 15 minutes.")


    async def reminder_released(self):
        await self.bot.get_channel(REMINDER_CHANNEL).send("Today's Advent of Code puzzle has been released. Good luck!")

    def _get_previous_winners(self, year: int):
        db_session = self.bot.create_db_session()
        prev_winners = db_session.query(AOCWinner).filter(AOCWinner.year == year)
        db_session.close()

        return [winner.aoc_userid for winner in prev_winners]

    def _add_winners(self, winners: List[Member], year: int):
        db_session = self.bot.create_db_session()

        for winner in winners:
            winner = AOCWinner(aoc_userid=winner.id, year=year)
            db_session.add(winner)

        db_session.commit()
        db_session.close()

    def random_choices_without_repition(self, population, weights, k):
        result = []
        for _ in range(k):
            if sum(weights) == 0:
                return None

            result.append(choices(population, weights)[0])
            index = population.index(result[-1])
            population.pop(index)
            weights.pop(index)

        return result

    @commands.command()
    @loading_status
    async def advent_winners(self, ctx: commands.Context, start: int, end: int, numberOfWinners: int, *args):
        """
        Determines winners for the AOC competition. Winners must be drawn by a member of the committee. 
        
        !advent --help for additional help.
        """
        if len([role for role in ctx.author.roles if role.name == "Committee"]) == 0:
            await ctx.send("Only committee can select the winners")
            return

        try:
            args = self.parse_arguments( args)
        except ValueError as error:
            await ctx.send(str(error))
            return

        try:
            leaderboard = self.get_leaderboard(args.year, args.code)
        except ValueError:
            await ctx.send("Error fetching leaderboard data. Check the leaderboard code, year, and day.")
            raise

        try:
            members = [Member.from_member_data(data, args.year, args.day)
                    for data in leaderboard["members"].values()]
        except Exception:
            await ctx.send("Error parsing leaderboard data.")
            raise

        previous_winners = self._get_previous_winners(args.year)
        potential_winners = [member for member in members if int(member.id) not in previous_winners]
        weights = [sum([1 for d in range(start, end + 1) if len(member.all_times[d]) > 0]) for member in potential_winners]

        winners = self.random_choices_without_repition(potential_winners, weights, numberOfWinners)
        
        if winners == None:
            await ctx.send(f"Insufficient participants to be able to draw {numberOfWinners} winners.")
            return

        self._add_winners(winners, args.year)

        await ctx.send("And the winners are:\n" + "\n".join([winner.name if (winner.name != None) else "anonymous user #" + str(winner.id) for winner in winners]))

async def setup(bot: UQCSBot):
    cog = Advent(bot)
    await bot.add_cog(cog)
