import logging
import discord
from discord.ext import commands
from random import choice, random
from typing import List, Tuple
import re
from datetime import datetime
from humanize import precisedelta 
from uqcsbot.bot import UQCSBot

class UpTime(commands.Cog):
    CHANNEL_ID = 836243768411160606

    def __init__(self, bot: UQCSBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        channel = self.bot.get_channel(self.CHANNEL_ID)

        if channel != None:
            await channel.send("I have rebooted!")
        else:
            logging.warning(f"bot-testing channel not found {self.CHANNEL_ID}") 

    @commands.command()
    async def uptime(self, ctx: commands.Context):
        """
            Defines the current uptime for UQCSBot
        """
        t = datetime.now() - self.bot.start_time
        message = ("The bot has been online for"
                   + f" {precisedelta(t, format='%.0f'):s}"
                   + (f" (`{round(t.total_seconds()):d}` seconds)" if t.total_seconds() >= 60 else "")
                   + f", since {self.bot.start_time.strftime('%H:%M:%S on %b %d'):s}"
                   # adds ordinal suffix
                   + f"{(lambda n: 'tsnrhtdd'[(n//10%10!=1)*(n%10<4)*n%10::4])(self.bot.start_time.day):s}.")
        await ctx.send(message)


def setup(bot: UQCSBot):
    bot.add_cog(UpTime(bot))

