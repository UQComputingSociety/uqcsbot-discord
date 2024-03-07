from bs4 import BeautifulSoup
import csv
from datetime import datetime
import discord
from discord.ext import commands
import logging
from random import choice
import requests
from requests.exceptions import RequestException
from typing import List
from zoneinfo import ZoneInfo

from uqcsbot.bot import UQCSBot

HOLIDAY_URL = "https://www.timeanddate.com/holidays/fun/"
HOLIDAY_CSV_PATH = "uqcsbot/static/geek_holidays.csv"
HOLIDAY_MESSAGE = "Today is {}!"
GENERAL_CHANNEL = "general"
HYPE_REACTS = [
    "blahaj",
    "blobhajHeart",
    "realheart",
    "blobhajInnocent",
    "keen",
    "bigsippin",
    "pog_of_greed",
    "blobhajHearts",
]

class Holiday:
    def __init__(self, date: datetime, description: str, url: str) -> None:
        self.date = date
        self.description = description
        self.url = url

    def is_today(self) -> bool:
        """
        Returns true if the holiday is celebrated today
        """
        now = datetime.now(tz=ZoneInfo("Australia/Brisbane"))
        return self.date.month == now.month and self.date.day == now.day


def get_holiday() -> Holiday | None:
    """Gets the holiday for a given day. If there are multiple holidays, choose a random one."""
    holiday_page = get_holiday_page()
    if holiday_page is None:
        return None

    geek_holidays = get_holidays_from_csv()
    holidays = get_holidays_from_page(holiday_page.decode("utf-8"))

    holidays_today = [
        holiday for holiday in holidays + geek_holidays if holiday.is_today()
    ]

    return choice(holidays_today) if holidays_today else None


def get_holidays_from_page(holiday_page: str) -> List[Holiday]:
    """Strips results from html page"""
    soup = BeautifulSoup(holiday_page, "html.parser")
    soup_holidays = (
        soup.find_all(class_="c0")
        + soup.find_all(class_="c1")
        + soup.find_all(class_="hl")
    )

    holidays: List[Holiday] = []

    for soup_holiday in soup_holidays:
        date_string = soup_holiday.find("th").get_text(strip=True)
        description = soup_holiday.find("a").get_text(strip=True)
        url = soup_holiday.find("a")["href"]
        date = datetime.strptime(date_string, "%d %b")
        holiday = Holiday(date, description, url)
        holidays.append(holiday)

    return holidays


def get_holidays_from_csv() -> List[Holiday]:
    """
    Returns list of holiday objects, one for each holiday in csv file
    csv rows in format: date,description,link
    """
    holidays: List[Holiday] = []
    with open(HOLIDAY_CSV_PATH, "r") as csvfile:
        for row in csv.reader(csvfile):
            date = datetime.strptime(row[0], "%d %b")
            holiday = Holiday(date, row[1], row[2])
            holidays.append(holiday)

    return holidays


def get_holiday_page() -> bytes | None:
    """
    Gets the holiday page HTML
    """
    try:
        response = requests.get(HOLIDAY_URL)
        return response.content
    except RequestException as e:
        logging.warning(e.response.content)


class Holidays(commands.Cog):
    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self.bot.schedule_task(
            self.holiday,
            trigger="cron",
            hour=9,
            minute=0,
            timezone="Australia/Brisbane",
        )

    async def holiday(self):
        """
        Posts a random celebratory day on #general from
        https://www.timeanddate.com/holidays/fun/
        """
        logging.info("Running daily holiday task")

        holiday = get_holiday()
        if holiday is None:
            logging.info("No holiday was found for today")
            return

        general_channel = discord.utils.get(
            self.bot.uqcs_server.channels, name=self.bot.GENERAL_CNAME
        )
        if general_channel is None:
            logging.warning(f"Could not find required channel #{GENERAL_CHANNEL}")
            return

        if isinstance(general_channel, discord.TextChannel):
            message = await general_channel.send(
                HOLIDAY_MESSAGE.format(holiday.description)
            )
            emoji = discord.utils.get(self.bot.emojis, name=choice(HYPE_REACTS))
            if emoji is not None:
                await message.add_reaction(emoji)


async def setup(bot: UQCSBot):
    await bot.add_cog(Holidays(bot))
