from typing import (
    Any,
    DefaultDict,
    List,
    Literal,
    Dict,
    Optional,
    Callable,
    NamedTuple,
    Tuple,
)
from collections import defaultdict
from datetime import datetime, timedelta
from io import BytesIO
from pytz import timezone

import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import PIL.features

from uqcsbot.bot import UQCSBot
from uqcsbot.models import AOCRegistrations

# Days in Advent of Code. List of numbers 1 to 25.
ADVENT_DAYS = list(range(1, 25 + 1))

# type aliases for documentation purposes.
Day = int  # from 1 to 25
Star = Literal[1, 2]
Seconds = int
Times = Dict[Star, Seconds]
Delta = Optional[Seconds]
Json = Dict[str, Any]
Colour = str
ColourFragment = NamedTuple("ColourFragment", [("text", str), ("colour", Colour)])
Leaderboard = list[str | ColourFragment]

# Puzzles are unlocked at midnight EST.
EST_TIMEZONE = timezone("US/Eastern")

# The time to cache results to limit requests to adventofcode.com. Note that 15 minutes is the recomended minimum time.
CACHE_TIME = timedelta(minutes=15)

# Colours borrowed from adventofcode.com website
BG_COLOUR = "#0f0f23"
FG_COLOUR = "#cccccc"
HL_COLOUR = "#009900"
GOLD_COLOUR = "#ffff66"
SILVER_COLOUR = "#9999cc"


class InvalidHTTPSCode(Exception):
    def __init__(self, message: str, request_code: int):
        super().__init__(message)
        self.request_code = request_code


class Member:
    def __init__(self, id: int, name: str, local: int, star_total: int, global_: int):
        # The advent of code id
        self.id = id
        # The advent of code name
        self.name = name if name else "Anon"
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


def _star_char(num_stars: int):
    """
    Given a number of stars (0, 1, or 2), returns its leaderboard
    representation.
    """
    return ColourFragment(
        " .*"[num_stars], [FG_COLOUR, SILVER_COLOUR, GOLD_COLOUR][num_stars]
    )


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


def _get_member_star_progress_bar(member: Member) -> Leaderboard:
    return [_star_char(len(member.times[day])) for day in ADVENT_DAYS]


class LeaderboardColumn:
    """
    A column in a leaderboard. The title is the name of the column as 2 lines and the calculation is a function that determines what is printed for a given member, index and day. The title and calculation should have the same constant width.
    """

    def __init__(
        self,
        title: tuple[str, str],
        calculation: Callable[[Member, int, Optional[Day]], str | Leaderboard],
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

        def format_name(member: Member, _: int, __: Optional[int]) -> Leaderboard:
            if not (discord_userid := member.get_discord_userid(bot)):
                return [member.name]
            if not (discord_user := bot.uqcs_server.get_member(discord_userid)):
                return [member.name]
            # Don't actually ping as leaderboard is called many times
            return [
                ColourFragment(member.name, HL_COLOUR),
                f" (@{discord_user.display_name})",
            ]

        return LeaderboardColumn(title=("", ""), calculation=format_name)

    @staticmethod
    def padding_column():
        """
        A column that is of a single space character.
        """
        return LeaderboardColumn(title=(" ", " "), calculation=lambda _, __, ___: " ")


def parse_leaderboard_column_string(s: str, bot: UQCSBot) -> List[LeaderboardColumn]:
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


def render_leaderboard_to_text(leaderboard: Leaderboard) -> str:
    return "".join(x if isinstance(x, str) else x.text for x in leaderboard)


def _isolate_leaderboard_layers(
    leaderboard: Leaderboard,
) -> Tuple[str, Dict[Colour, str]]:
    """
    Given a leaderboard made up of coloured fragments, split the
    text into a number of layers. Each layer contains all the text
    which is coloured by one particular colour.

    Returns:
    - a string of the leaderboard, but with whitespace in the place of every character,
      for calculating bounding box size.
    - a dictionary mapping colours to the layer of that colour.
    """
    layers: DefaultDict[str | None, str] = defaultdict(lambda: layers[None])
    layers[None] = ""

    for frag in leaderboard:
        colour, text = (
            (FG_COLOUR, frag) if isinstance(frag, str) else (frag.colour, frag.text)
        )
        layers[colour] += text
        for k in layers:
            if k == colour:
                continue
            layers[k] += "".join(c if c.isspace() else " " for c in text)

    spaces = layers[None]
    del layers[None]
    return spaces, layers  # type: ignore


def render_leaderboard_to_image(leaderboard: Leaderboard) -> bytes:
    spaces, layers = _isolate_leaderboard_layers(leaderboard)

    font = PIL.ImageFont.truetype("./uqcsbot/static/NotoSansMono-Regular.ttf", 20)

    img = PIL.Image.new("RGB", (1, 1))
    draw = PIL.ImageDraw.Draw(img)

    PAD = 20
    # first, try to draw text to obtain required bounding box size
    _, _, right, bottom = draw.textbbox((PAD, PAD), spaces, font=font)  # type: ignore

    img = PIL.Image.new("RGB", (int(right) + PAD, int(bottom) + PAD), BG_COLOUR)
    draw = PIL.ImageDraw.Draw(img)

    # draw each layer. layers should be disjoint
    for colour, text in layers.items():
        draw.text((PAD, PAD), text, font=font, fill=colour)  # type: ignore

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()  # XXX: why do we need to getvalue()?


def print_leaderboard(
    columns: List[LeaderboardColumn], members: List[Member], day: Optional[Day]
):
    """
    Returns a string of the leaderboard of the given format.
    """
    header = "".join(column.title[0] for column in columns)
    header += "\n"
    header += "".join(column.title[1] for column in columns)

    leaderboard: Leaderboard = [ColourFragment(header, HL_COLOUR)]

    # Note that leaderboards start at 1, not 0
    for id, member in enumerate(members, start=1):
        leaderboard.append("\n")
        for column in columns:
            leaderboard.extend(column.calculation(member, id, day))

    return leaderboard
