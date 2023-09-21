import discord
from discord import app_commands
import requests
from typing import NamedTuple, List, Tuple, Optional
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from math import ceil
from random import choice

from bs4 import BeautifulSoup
from discord.ext import commands

from uqcsbot.yelling import yelling_exemptor

# Endpoint that contains a table of semester dates
MARKUP_CALENDAR_URL: str = "https://systems-training.its.uq.edu.au/systems/student-systems/electronic-course-profile-system/design-or-edit-course-profile/academic-calendar-teaching-week"
DATE_FORMAT = "%d/%m/%Y"


# Semester information
class Semester(NamedTuple):
    name: str
    start_date: datetime
    end_date: datetime
    weeks: List[str]


def date_to_string(date: datetime):
    """
    Formats date based on the format used for the command
        Returns:
            Stringified date
    """
    return date.strftime(DATE_FORMAT)


def string_to_date(date: str) -> datetime:
    """
    Returns datetime object from string based on the format used for the command
        Returns:
            Stringified date
    """
    return datetime.strptime(date, DATE_FORMAT).replace(
        tzinfo=ZoneInfo("Australia/Brisbane")
    )


def get_semester_times(markup: str) -> List[Semester]:
    """
    Parses the given HTML page to get a list of the names, dates & weeks of the semesters at UQ

        Dev: this relies on the calendar page for UQ staying relative sane and static
        Parameters:
            markup: HTML page from UQ's website in plaintext
        Returns:
            A list of the information about semesters at UQ

    """
    soup = BeautifulSoup(markup, "html.parser")
    semesters: List[Semester] = []

    for semester_title in soup.find_all("h2", "structured-page__step-title"):
        table = semester_title.parent.find("table")
        weeks = table.find("tbody").find_all("tr")

        # We assume the term starts on a Monday
        sem_start = weeks[0].find_all("td")[0].text
        start_date: datetime = string_to_date(sem_start)

        # We'll filter out the empty cells at the end of the term, say in case it ends on a Tuesday
        last_week_dates = [
            cell for cell in weeks[-1].find_all("td") if len(cell.text.strip())
        ]
        end_date: datetime = string_to_date(last_week_dates[-1].text)

        week_names = [week.text.strip() for week in table.find("tbody").find_all("th")]
        # Invariant
        assert len(week_names) == ceil(
            (end_date - start_date + timedelta(days=1)).days / 7
        )

        semesters.append(
            Semester(semester_title.text, start_date, end_date, week_names)
        )

    return semesters


def get_semester_week(
    semesters: List[Semester], checked_date: datetime
) -> Optional[Tuple[str, str, str]]:
    """
    Gets the name of the semester, week and weekday of the date that's to be checked
        Parameters:
            checked_date: the given date that we'll be checking the semester and week for
        Returns:
            If the date exists in one of the semesters: a tuple containing the semester,
            the name of the week we're in, and the weekday respectively; else, None.
    """

    for semester in semesters:
        # Check if the current date is within the semester range
        if semester.start_date <= checked_date <= semester.end_date:
            # If it is, we figure out what week it is
            days_since_start = (checked_date - semester.start_date).days
            week_index = days_since_start // 7

            weekday = checked_date.strftime("%A")
            week_name = semester.weeks[week_index]
            if "week" not in week_name.lower():
                # Accounts for & makes things like "Revision", "Exam", "Pause" a bit nicer
                week_name = week_name + " Week"
            semester_name = semester.name
            return semester_name, week_name, weekday

    return None


class WhatWeekIsIt(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.describe(
        date="Date to lookup in the format of %d/%m/%Y (defaults to today)"
    )
    @yelling_exemptor(input_args=["date"])
    async def whatweekisit(self, interaction: discord.Interaction, date: Optional[str]):
        """
        Sends information about which semester, week and weekday it is.
        If there's no specified date, it takes it to be the current one.
        """

        await interaction.response.defer(thinking=True)

        if date == None:
            check_date = datetime.now(tz=ZoneInfo("Australia/Brisbane"))
        else:
            try:
                check_date = string_to_date(date)
            except ValueError:
                await interaction.edit_original_response(
                    content=f"Specified date should be in format `{DATE_FORMAT}`"
                )
                return

        calendar_page = requests.get(MARKUP_CALENDAR_URL)
        if calendar_page.status_code != requests.codes.ok:
            await interaction.edit_original_response(
                content="An error occurred, please try again."
            )

        semesters = get_semester_times(calendar_page.text)

        semester_tuple = get_semester_week(semesters, check_date)
        if not semester_tuple:
            date = date_to_string(check_date)
            message = f"University isn't in session on {date}, enjoy the break :)"
        else:
            semester_name, week_name, weekday = semester_tuple

            if date != None:
                message = f"The week of {date} is in:"
            else:
                message = choice(
                    [
                        "The week we're in is:",
                        "The current week is:",
                        f"It's currently {week_name}:",
                        f"We're currently in {week_name}:",
                        "Currently, the week is:",
                        "Hey, look at the time:",
                        f"Can you believe that it's already {week_name}:",
                        "Time flies when you're having fun:",
                        "Maybe time's just a construct of human perception:",
                        "Time waits for noone:",
                        "This week is:",
                        "It is currently:",
                        "The week is",
                        "The week we're currently in is:",
                        f"Right now we are in {week_name}:",
                    ]
                )

            message += f"\n> {weekday}, {week_name} of {semester_name}"

        await interaction.edit_original_response(content=message)


async def setup(bot: commands.Bot):
    await bot.add_cog(WhatWeekIsIt(bot))
