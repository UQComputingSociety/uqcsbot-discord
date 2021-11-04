from random import choice
import discord
from discord.ext import commands
from uqcsbot.bot import UQCSBot

GENERAL_CHANNEL = 813325735620116490

class WorkingOn(commands.Cog):

    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self.bot.schedule_task(self.workingon, trigger='cron', hour=17, timezone='Australia/Brisbane')

    async def workingon(self):
        """ 5pm ping for 2 lucky server members to share what they have been working on. """
        members = list(self.bot.get_all_members())
        message = []

        while len(message) < 2:
            chosen = choice(members)

            if not chosen.bot:
                message.append(f"Hey {chosen.mention}! Tell us about something cool you are working on!")
        
        await self.bot.get_channel(GENERAL_CHANNEL).send("\n".join(message), allowed_mentions=discord.AllowedMentions(everyone=False, users=True, roles=False))

def setup(bot: UQCSBot):
    cog = WorkingOn(bot)
    bot.add_cog(cog)
