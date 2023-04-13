import logging
from datetime import datetime
import os

import discord
from discord import app_commands
from discord.ext import commands
from humanize import precisedelta

from uqcsbot.bot import UQCSBot


class UpTime(commands.Cog):
    CHANNEL_NAME = "bot-testing"

    def __init__(self, bot: UQCSBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        channel = discord.utils.get(self.bot.get_all_channels(), name=self.CHANNEL_NAME)

        if channel != None:
            await channel.send("I have rebooted!")
        else:
            logging.warning(f"#{self.CHANNEL_NAME} not found") 

    @app_commands.command()
    async def uptime(self, interaction: discord.Interaction):
        """
            Defines the current uptime for UQCSBot
        """
        t = datetime.now() - self.bot.start_time
        message = ("I've been online for"
                   + f" {precisedelta(t, format='%.0f'):s}"
                   + (f" (`{round(t.total_seconds()):d}` seconds)" if t.total_seconds() >= 60 else "")
                   + f", since {self.bot.start_time.strftime('%H:%M:%S on %b %d'):s}"
                   # adds ordinal suffix
                   + f"{(lambda n: 'tsnrhtdd'[(n//10%10!=1)*(n%10<4)*n%10::4])(self.bot.start_time.day):s}.")
        await interaction.response.send_message(message)

async def setup(bot: UQCSBot):
    await bot.add_cog(UpTime(bot))

