import logging
from datetime import datetime, timedelta
import os
import asyncio

import discord
from discord import app_commands
from discord.ext import commands


class MemberCounter(commands.Cog):
    # Checks for an Azure specific environment variable, if it exists we're running as prod.
    MEMBER_COUNT_PREFIX = "Member Count: "
    RATE_LIMIT = timedelta(minutes=5)
    NEW_MEMBER_TIME = timedelta(days=7)

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_rename_time = datetime.now()
        self.waiting_for_rename = False

    @commands.Cog.listener()
    async def on_ready(self):
        member_count_channels = [
            channel for channel in self.bot.get_all_channels()
            if channel.name.startswith(self.MEMBER_COUNT_PREFIX)
        ]
        if len(member_count_channels) == 0:
            logging.warning(
                f"Found no channel starting with \"{self.MEMBER_COUNT_PREFIX}\". Could not determine which is the \"correct\" member count channel.")
            self.member_count_channel = None # TODO maybe end this cog or something similar
            return
        self.member_count_channel = member_count_channels[0]
        if len(member_count_channels) > 1:
            logging.warning(
                f"Found many channels starting with \"{self.MEMBER_COUNT_PREFIX}\". Could not determine which is the \"correct\" member count channel.")
            self.member_count_channel = None # TODO maybe end this cog or something similar
            return

        await self.attempt_update_member_count_channel_name()

    @app_commands.command(name="membercount")
    async def member_count(self, interaction: discord.Interaction):
        """ Display the number of members """
        new_members = filter(
            lambda member: member.joined_at > datetime.now() - self.NEW_MEMBER_TIME,
            interaction.guild.members
        )
        await interaction.response.send_message(f"There are currently {interaction.guild.member_count} members in the UQCS discord server, with {len([new_members])} joining in the last 7 days.")
        await self.attempt_update_member_count_channel_name()

    @commands.Cog.listener()
    async def on_member_join(self, _):
        await self.attempt_update_member_count_channel_name()

    @commands.Cog.listener()
    async def on_raw_member_remove(self, _):
        await self.attempt_update_member_count_channel_name()

    async def attempt_update_member_count_channel_name(self):
        """ Check if we have updated recently and update the "Member Count" channel name when next available (i.e. when not rate limited) """
        if self.waiting_for_rename:
            # The awaited rename will fix everything
            return

        if datetime.now() - self.last_rename_time < self.RATE_LIMIT:
            self.waiting_for_rename = True
            time_to_wait = self.RATE_LIMIT - \
                (datetime.now() - self.last_rename_time)
            logging.info(
                f"Waiting {time_to_wait.seconds} seconds until the next update to #Member Count channel")
            await asyncio.sleep(time_to_wait.seconds)
            await self._update_member_count_channel_name()
        else:
            await self._update_member_count_channel_name()

    async def _update_member_count_channel_name(self):
        """ Update the "Member Count" channel name. May be rate limited. Use attempt_update_member_count_channel_name() for most circumstances. """
        if not self.member_count_channel:
            return
        await self.member_count_channel.edit(
            name=self.MEMBER_COUNT_PREFIX +
            str(self.bot.uqcs_server.member_count)
        )
        self.last_rename_time = datetime.now()
        self.waiting_for_rename = False


async def setup(bot: commands.Bot):
    await bot.add_cog(MemberCounter(bot))
