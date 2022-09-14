import requests
from collections import namedtuple
from typing import NamedTuple, List, Tuple
from datetime import datetime, timedelta
from math import ceil

from bs4 import BeautifulSoup
import discord
from discord.ext import commands

from uqcsbot.utils.command_utils import loading_status

# Endpoint that contains a table of semester dates
MARKUP_CALENDAR_URL: str = "https://systems-training.its.uq.edu.au/systems/student-systems/electronic-course-profile-system/design-or-edit-course-profile/academic-calendar-teaching-week"


class Semester(NamedTuple):
    name: str
    start_date: datetime
    end_date: datetime
    weeks: List[str]


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
        start_date: datetime = datetime.strptime(sem_start, "%d/%m/%Y")

        # We'll filter out the empty cells at the end of the term, say in case it ends on a Tuesday
        last_week_dates = [
            cell for cell in weeks[-1].find_all("td") if len(cell.text.strip())
        ]
        end_date: datetime = datetime.strptime(last_week_dates[-1].text, "%d/%m/%Y")

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
) -> Tuple[str, str, str]:
    """
    Gets the name of the semester, week and weekday of the date that's to be checked
        Parameters:
            checked_date: the given date that we'll be checking the semester and week for
        Returns:
            A tuple containing the semester, the name of the week we're in, and the weekday
            respectively. If we're past a given semester and not into the next one, semester will
            be set to the _last_ semester and week will be None.
    """
    semester_name = None
    week_name = None
    weekday = None

    for semester in semesters:
        # Check if the current date is within the semester range
        if semester.start_date <= checked_date <= semester.end_date:
            # If it is, we figure out what week it is
            days_since_start = (checked_date - semester.start_date).days
            week_index = days_since_start // 7

            weekday = checked_date.strftime("%A")
            week_name = semester.weeks[week_index]
            if "week" not in week_name.lower():
                week_name = "Week of " + week_name
            semester_name = semester.name

            break

    return semester_name, week_name, weekday


class WhatWeekIsIt(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    @loading_status
    async def whatweekisit(self, ctx: commands.Context, *args):
        """
        `!whatweekisit [SPECIFIED_DATE]` - Sends information about which semester, week and weekday
        it is on the specified date (in %d/%m/%Y format) -- if there's no specified date, it takes
        it to be the current one.
        """
        if len(args) > 1:
            await ctx.send("No more than one argument (specified date) is required/s")
            return
        elif len(args) == 1:
            check_date = datetime.strptime(args[0], "%d/%m/%Y")
        else:
            check_date = datetime.now()

        calendar_page = requests.get(MARKUP_CALENDAR_URL)
        semesters = get_semester_times(calendar_page.text)

        semester_name, week_name, weekday = get_semester_week(semesters, check_date)
        if not semester_name:
            date = check_date.strftime("%d/%m/%Y")
            message = f"University isn't in session on {date}, enjoy the break :)"
        else:
            message = "The week we're in is:\n> "
            message += f"{weekday}, {week_name} of {semester_name}"

        await ctx.send(message)


def setup(bot: commands.Bot):
    bot.add_cog(WhatWeekIsIt(bot))
