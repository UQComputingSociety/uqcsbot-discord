import logging
from random import choice

import discord
from discord.ext import commands

from uqcsbot.bot import UQCSBot

GENERAL_CHANNEL = "general"


class WorkingOn(commands.Cog):
    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self.bot.schedule_task(
            self.workingon, trigger="cron", hour=17, timezone="Australia/Brisbane"
        )

    async def workingon(self):
        """5pm ping for 2 lucky server members to share what they have been working on."""
        members = list(self.bot.get_all_members())
        chosen_members = []

        while len(chosen_members) < 3:
            potential_member = choice(members)
            if not potential_member.bot:
                chosen_members.append(potential_member)

        message = "\n".join(
            [
                f"Hey {member.mention}! Tell us about something cool you are working on!"
                for member in chosen_members
            ]
        )

        general_channel = discord.utils.get(
            self.bot.uqcs_server.channels, name=GENERAL_CHANNEL
        )

        if general_channel is not None:
            await general_channel.send(
                message,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, users=True, roles=False
                ),
            )
        else:
            logging.warning(f"Could not find required channel #{GENERAL_CHANNEL}")


async def setup(bot: UQCSBot):
    cog = WorkingOn(bot)
    await bot.add_cog(cog)
