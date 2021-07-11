from random import choice
import discord
from discord.ext import commands
from uqcsbot.bot import UQCSBot

GENERAL_CHANNEL = 836589565237264418

class WorkingOn(commands.Cog):

    def __init__(self, bot: UQCSBot):
        self.bot = bot

    async def workingon(self):
        """ 5pm ping for 2 lucky server members to share what they have been working on. """
        members = list(self.bot.get_all_members())
        message = []

        for i in range(2):
            chosen = choice(members).mention
            chosen = "me"
            message.append(f"Hey {chosen}! Tell us about something cool you are working on!")
        
        await self.bot.get_channel(GENERAL_CHANNEL).send("\n".join(message))

def setup(bot: UQCSBot):
    cog = WorkingOn(bot)
    bot.add_cog(cog)
    bot.schedule_task(cog.workingon, trigger='cron', hour=17, timezone='Australia/Brisbane')
