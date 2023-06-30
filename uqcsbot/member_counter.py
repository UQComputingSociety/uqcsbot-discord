import logging
from datetime import datetime, timedelta
import asyncio
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.bot import UQCSBot
from typing import List


class MemberCounter(commands.Cog):
    MEMBER_COUNT_PREFIX = "Member Count: "
    RATE_LIMIT = timedelta(minutes=5)
    NEW_MEMBER_TIME = timedelta(days=7)

    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self.last_rename_time = datetime.now()
        self.waiting_for_rename = False

    @commands.Cog.listener()
    async def on_ready(self):
        member_count_channels: List[discord.VoiceChannel] = [
            channel
            for channel in self.bot.uqcs_server.channels
            if channel.name.startswith(self.MEMBER_COUNT_PREFIX) and isinstance(channel, discord.VoiceChannel)
        ]
        if len(member_count_channels) == 0:
            logging.warning(
                f'Found no channel starting with "{self.MEMBER_COUNT_PREFIX}". Could not determine which is the "correct" member count channel.'
            )
            self.member_count_channel = (
                None  # TODO maybe end this cog or something similar
            )
            return
        self.member_count_channel = member_count_channels[0]
        if len(member_count_channels) > 1:
            logging.warning(
                f'Found many channels starting with "{self.MEMBER_COUNT_PREFIX}". Could not determine which is the "correct" member count channel.'
            )
            self.member_count_channel = (
                None  # TODO maybe end this cog or something similar
            )
            return

        if (bot_member := self.bot.uqcs_server.get_member(self.bot.safe_user.id)) is None:
            logging.warning(
                f"Unable to determine bot permissions for managing #Member Count channel."
            )
            return
        
        permissions = self.member_count_channel.permissions_for(bot_member)
        if not permissions.manage_channels:
            logging.warning(
                f"Bot does not have the permission to manage the #Member Count channel. The current permissions are {permissions}. The bot user is {bot_member}."
            )
        await self.attempt_update_member_count_channel_name()

    @app_commands.describe(force="Infra-only arg to force updates.")
    @app_commands.command(name="membercount")
    async def member_count(self, interaction: discord.Interaction, force: bool = False):
        """Display the number of members"""
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            return
        
        new_members = [
            member
            for member in interaction.guild.members
            if member.joined_at is not None and member.joined_at
            > datetime.now(tz=ZoneInfo("Australia/Brisbane")) - self.NEW_MEMBER_TIME
        ]
        await interaction.response.send_message(
            f"There are currently {interaction.guild.member_count} members in the UQ Computing Society discord server, with {len(new_members)} joining in the last 7 days."
        )

        if interaction.user.guild_permissions.manage_guild and force:
            # this is dodgy, but the alternative is to restart the bot
            # if it gets caught in a loop of waiting for a broken rename
            self.waiting_for_rename = False
        await self.attempt_update_member_count_channel_name()

    @commands.Cog.listener()
    async def on_member_join(self, _):
        await self.attempt_update_member_count_channel_name()

    @commands.Cog.listener()
    async def on_raw_member_remove(self, _):
        await self.attempt_update_member_count_channel_name()

    async def attempt_update_member_count_channel_name(self):
        """Check if we have updated recently and update the "Member Count" channel name when next available (i.e. when not rate limited)"""
        if self.waiting_for_rename:
            # The awaited rename will fix everything
            return

        if datetime.now() - self.last_rename_time < self.RATE_LIMIT:
            self.waiting_for_rename = True
            time_to_wait = self.RATE_LIMIT - (datetime.now() - self.last_rename_time)
            logging.info(
                f"Waiting {time_to_wait.seconds} seconds until the next update to #Member Count channel"
            )
            await asyncio.sleep(time_to_wait.seconds)
            await self._update_member_count_channel_name()
        else:
            await self._update_member_count_channel_name()

    async def _update_member_count_channel_name(self):
        """Update the "Member Count" channel name. May be rate limited. Use attempt_update_member_count_channel_name() for most circumstances."""
        if not self.member_count_channel:
            return
        await self.member_count_channel.edit(
            name=self.MEMBER_COUNT_PREFIX + str(self.bot.uqcs_server.member_count)
        )
        self.last_rename_time = datetime.now()
        self.waiting_for_rename = False


async def setup(bot: UQCSBot):
    await bot.add_cog(MemberCounter(bot))
