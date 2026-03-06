import discord
from discord import app_commands
from typing import List, Tuple, Optional
from zoneinfo import ZoneInfo
from datetime import datetime
from random import choice
from dataclasses import dataclass

from bs4 import BeautifulSoup
from discord.ext import commands

from uqcsbot.yelling import yelling_exemptor


# Endpoint that contains a table of semester dates
ACADEMIC_CALENDAR_FILE = "uqcsbot/static/academic_calendar.html"
DATE_FORMAT = "%d/%m/%Y"


# Semester information
@dataclass
class Semester:
    name: str
    start_date: datetime
    end_date: datetime


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
    semesters: List[Semester] = []

    soup = BeautifulSoup(markup, "html.parser")
    years = soup.find_all("h3")  # All years are within <h3> tags

    for year in years:
        for element in year.find_all_next():
            if element.name == "h3":
                break  # Stop when to next semester

            if element.name == "div" and element.get("class") == ["uq-accordion__item"]:
                semester_name = element.find("h4").text  # Semesters are in <h4> tags

                if semester_name not in ("Semester 1", "Semester 2"):
                    break  # For other semesters (e.g. summer semesters)

                semester_content = element.find("div", class_="uq-accordion__content")

                start_date: datetime | None = None
                end_date: datetime | None = None

                for event in semester_content.find_all("li"):
                    text = event.get_text()

                    def get_date():
                        date_str = text.split("–", 1)[0].replace("\xa0", " ").strip()
                        dt = datetime.strptime(f"{date_str} {year.text}", "%d %b %Y")
                        return dt.replace(tzinfo=ZoneInfo("Australia/Brisbane"))

                    if "Classes start" in text:
                        start_date = get_date()

                    elif (
                        f"{semester_name} classes end" in text
                        or f"{semester_name} ends" in text
                    ):
                        end_date = get_date()

                if start_date and end_date:
                    semesters.append(Semester(semester_name, start_date, end_date))

    return semesters


def get_semester_week(
    semesters: List[Semester], checked_date: datetime
) -> Optional[Tuple[str, int, str]]:
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
            week_index = days_since_start // 7 + 1

            weekday = checked_date.strftime("%A")
            semester_name = semester.name
            return semester_name, week_index, weekday
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
            current_date = datetime.now(tz=ZoneInfo("Australia/Brisbane"))
            check_date = current_date
        else:
            try:
                check_date = string_to_date(date)
            except ValueError:
                await interaction.edit_original_response(
                    content=f"Specified date should be in format `{DATE_FORMAT}`"
                )
                return

        with open(ACADEMIC_CALENDAR_FILE, "r", encoding="utf-8") as file:
            calendar_page = file.read()

        semesters = get_semester_times(calendar_page)

        semester_tuple = get_semester_week(semesters, check_date)

        date = date_to_string(check_date)

        if not semester_tuple:
            years = BeautifulSoup(calendar_page, "html.parser").find_all("h3")
            year_numbers = [int(year.get_text(strip=True)) for year in years]

            if min(year_numbers) <= check_date.year <= max(year_numbers):
                message = f"University isn't in session on {date}, enjoy the break :)"
            else:
                message = f"Sorry, {date} is currently out of bounds."
        else:
            semester_name, week_index, weekday = semester_tuple
            week_name = "Week " + str(week_index)
            message = f"The week of {date} is in:\n> "
            message += choice(
                [
                    "The week we're in is:",
                    "The current week is:",
                    "Currently, the week is:",
                    "Hey, look at the time:",
                    "Can you believe that it's already:",
                    "Time flies when you're having fun:",
                    "Maybe time's just a construct of human perception:",
                    "Time waits for noone:",
                    "This week is:",
                    "It is currently:",
                    "The week is",
                    "The week we're currently in is:",
                    "Right now we are in:",
                    "Good heavens, would you look at the time:",
                    "What's the time, mister wolf? It's:",
                ]
            )

            message += f"\n> {weekday}, {week_name} of {semester_name}"

        await interaction.edit_original_response(content=message)


async def setup(bot: commands.Bot):
    await bot.add_cog(WhatWeekIsIt(bot))
