import logging
from random import choice
from apscheduler.triggers.cron import CronTrigger

import discord
from discord.ext import commands

from uqcsbot.bot import UQCSBot

GENERAL_CHANNEL = "general"


class WorkingOn(commands.Cog):
    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self.bot.schedule_task(
            self.workingon, trigger=CronTrigger(hour=17, timezone=bot.BOT_TIMEZONE)
        )

    async def workingon(self):
        """5pm ping for 2 lucky server members to share what they have been working on."""
        members = list(self.bot.get_all_members())
        message: list[str] = []

        while len(message) < 2:
            chosen = choice(members)

            if not chosen.bot:
                message.append(
                    f"Hey {chosen.mention}! Tell us about something cool you are working on!"
                )

        general_channel = discord.utils.get(
            self.bot.uqcs_server.channels, name=GENERAL_CHANNEL
        )

        if isinstance(general_channel, discord.TextChannel):
            await general_channel.send(
                "\n".join(message),
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, users=True, roles=False
                ),
            )
        else:
            logging.warning(f"Could not find required channel #{GENERAL_CHANNEL}")


async def setup(bot: UQCSBot):
    cog = WorkingOn(bot)
    await bot.add_cog(cog)
