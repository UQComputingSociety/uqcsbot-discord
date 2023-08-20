import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.bot import UQCSBot

HACKATHON_START_TIME_STR = os.environ.get("HACKATHON_START_TIME")
HACKATHON_END_TIME_STR = os.environ.get("HACKATHON_END_TIME")

TIME_SUFFIXES = ["day", "hour", "minute", "second"]


class Hackathon(commands.Cog):
    def __init__(self, bot: UQCSBot):
        self.bot = bot
        try:
            self.start_time = datetime.strptime(
                HACKATHON_START_TIME_STR or "", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=ZoneInfo("Australia/Brisbane"))
            self.end_time = datetime.strptime(
                HACKATHON_END_TIME_STR or "", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=ZoneInfo("Australia/Brisbane"))
        except ValueError:
            logging.error("Unable to parse environment variable dates for hackathon")
            self.start_time = None
            self.end_time = None

    @app_commands.command(name="hackathon")
    async def countdown(self, interaction: discord.Interaction):
        """
        Provides the time until the start or end of the next hackathon.
        """
        now = datetime.now(tz=ZoneInfo("Australia/Brisbane"))
        print(self.start_time - now)
        if self.start_time == None or self.end_time == None:
            await interaction.response.send_message(
                "Could not process or find the time of the next/current hackathon."
            )
            return

        elif self.end_time + timedelta(days=1) < now:
            await interaction.response.send_message(
                "No exact date is given for the next hackathon just yet. Stay tuned for details to come."
            )
            return

        elif self.end_time < now:
            await interaction.response.send_message(
                f"Tools down for hackathon occurred {countdown_string(now - self.end_time)} ago."
            )
            return

        elif self.start_time < now <= self.end_time:
            await interaction.response.send_message(
                f"Tools down for hackathon in {countdown_string(self.end_time - now)}!"
            )
            return

        elif now <= self.start_time:
            await interaction.response.send_message(
                f"Hackathon starts in {countdown_string(self.start_time - now)}!"
            )
            return

        await interaction.response.send_message(
            "Time is just a construct of human perception."
        )


def countdown_string(time: timedelta):
    """
    Provides the time in a countdown format
    """
    days = time.days
    hours = time.seconds // 3600
    minutes = (time.seconds // 60) % 60
    seconds = time.seconds % 60

    time_values = [days, hours, minutes, seconds]
    time_suffixes_pluralised = [
        suffix + "s" if value != 1 else suffix
        for value, suffix in zip(time_values, TIME_SUFFIXES)
    ]
    time_strings = [
        str(value) + " " + suffix
        for value, suffix in zip(time_values, time_suffixes_pluralised)
        if value > 0
    ]

    if len(time_strings) == 0:
        return "0 seconds"
    elif len(time_strings) == 1:
        time_string = time_strings[0]
    else:
        time_string = ", ".join(time_strings[:-1]) + " and " + time_strings[-1]

    output = "only " if days == 0 else ""
    output += time_string

    return output


async def setup(bot: UQCSBot):
    await bot.add_cog(Hackathon(bot))
