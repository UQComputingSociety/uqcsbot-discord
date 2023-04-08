import os
from threading import Timer
from typing import Tuple, List
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot import models


class BlacklistedMessageError(Exception):
    # always caught. used to differentiate "starboard message doesn't exist" and "starboard message is blacklisted"
    pass


class SomethingsFucked(Exception):
    # never caught. used because i don't trust myself and i want it to be clear that something's wrong.
    pass


class Starboard(commands.Cog):
    CHANNEL_NAME = "starboard"
    EMOJI_NAME = "starhaj"
    BRISBANE_TZ = ZoneInfo("Australia/Brisbane")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.base_threshold = int(os.environ.get("SB_BASE_THRESHOLD"))
        self.big_threshold = int(os.environ.get("SB_BIG_THRESHOLD"))
        self.ratelimit = int(os.environ.get("SB_RATELIMIT"))

        self.base_blocked_messages = (
            []
        )  # messages that are temp blocked from being resent to the starboard
        self.big_blocked_messages = (
            []
        )  # messages that are temp blocked from being re-pinned in the starboard

        self.whitelist_menu = app_commands.ContextMenu(
            name="Starboard Whitelist",
            callback=self.context_whitelist_sb_message,
        )
        self.bot.tree.add_command(self.whitelist_menu)

        self.blacklist_menu = app_commands.ContextMenu(
            name="Starboard Blacklist",
            callback=self.context_blacklist_sb_message,
        )
        self.bot.tree.add_command(self.blacklist_menu)

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Really this should be in __init__ but this stuff doesn't exist until the bot is ready.
        N.B. this does assume the bot only has access to one channel called "starboard" and one emoji called
        "starhaj". If this assumption stops holding, we may need to move back to IDs (cringe) or ensure we only get
        them from the correct guild (cringer).
        """
        self.starboard_emoji = discord.utils.get(self.bot.emojis, name=self.EMOJI_NAME)
        self.starboard_channel = discord.utils.get(
            self.bot.get_all_channels(), name=self.CHANNEL_NAME
        )

    async def _blacklist_log(
        self, message: discord.Message, user: discord.Member, blacklist: bool
    ):
        """Logs a blacklist/whitelist command to the modlog."""
        channels = self.bot.get_all_channels()
        modlog = discord.utils.get(channels, name="admin-alerts")
        state = "blacklisted" if blacklist else "whitelisted"

        embed = discord.Embed(
            color=message.author.top_role.color, description=message.content
        )
        embed.set_author(
            name=message.author.display_name, icon_url=message.author.display_avatar.url
        )
        embed.set_footer(
            text=message.created_at.astimezone(tz=self.BRISBANE_TZ).strftime(
                "%b %d, %H:%M:%S"
            )
        )

        log_item = await modlog.send(
            content=f"{str(user)} {state} message {message.id}", embeds=[embed]
        )

        await log_item.edit(
            view=discord.ui.View.from_message(log_item).add_item(
                discord.ui.Button(
                    label="Original Message",
                    style=discord.ButtonStyle.link,
                    url=message.jump_url,
                )
            )
        )

    @app_commands.default_permissions(manage_messages=True)
    async def context_blacklist_sb_message(
        self, interaction: discord.Interaction, message: discord.Message
    ):
        """Blacklists a message from being starboarded. If the message is already starboarded, also deletes it."""
        db_session = self.bot.create_db_session()
        # can't use the db query functions for this, they error out if a message hits the blacklist
        entry = db_session.query(models.Starboard).filter(
            models.Starboard.recv == message.id
        )
        query_val = entry.one_or_none()

        if query_val is not None:
            if query_val.sent is None:
                # if the table has (recv, none) then it's already blacklisted.
                return

            # otherwise the table has (recv, something), we should delete the something and then make it (recv, none)
            try:
                await (
                    await self.starboard_channel.fetch_message(query_val.sent)
                ).delete()
            except discord.NotFound():
                # if the message has already been deleted without a DB update, fetch may error out
                pass

            query_val.sent = None
        else:
            # other-otherwise the table doesn't have recv, so we add (recv, none)
            db_session.add(
                models.Starboard(
                    recv=message.id, recv_location=message.channel.id, sent=None
                )
            )

        db_session.commit()
        db_session.close()

        await self._blacklist_log(message, interaction.user, blacklist=True)
        await interaction.response.send_message(
            f"Blacklisted message {message.id}.", ephemeral=True
        )

    @app_commands.default_permissions(manage_messages=True)
    async def context_whitelist_sb_message(
        self, interaction: discord.Interaction, message: discord.Message
    ):
        """Removes a message from the starboard blacklist.
        N.B. Doesn't perform an 'update' of the message. This may result in messages meeting the threshold
        but not being starboarded if they don't get any more reacts."""
        db_session = self.bot.create_db_session()

        # if we find a (recv, none) for this message, delete it. otherwise the message is already not blacklisted.
        entry = db_session.query(models.Starboard).filter(
            models.Starboard.recv == message.id, models.Starboard.sent == None
        )
        if entry.one_or_none() is not None:
            entry.delete(synchronize_session=False)
            db_session.commit()
        db_session.close()

        await self._blacklist_log(message, interaction.user, blacklist=False)
        await interaction.response.send_message(
            f"Whitelisted message {message.id}.", ephemeral=True
        )

    def _rm_base_ratelimit(self, id: int) -> None:
        """Callback to remove a message from the base-ratelimited list"""
        self.base_blocked_messages.remove(id)

    def _rm_big_ratelimit(self, id: int) -> None:
        """Callback to remove a message from the big-ratelimited list"""
        self.big_blocked_messages.remove(id)

    def _starboard_db_add(self, recv: int, recv_location: int, sent: int) -> None:
        """Creates a starboard DB entry. Only called from _process_updates when the messages are not None, so doesn't
        need to handle any None-checks - we can just pass ints straight in."""
        db_session = self.bot.create_db_session()
        db_session.add(
            models.Starboard(recv=recv, recv_location=recv_location, sent=sent)
        )
        db_session.commit()
        db_session.close()

    def _starboard_db_remove(
        self, recv: (discord.Message | None), sent: (discord.Message | None)
    ) -> None:
        """Removes a starboard DB entry. Only called from process_updates, but no caller guarantees about recv being
        None, so we take Messages and only get ids if they're not-None."""
        recv_id = recv.id if recv is not None else None
        sent_id = sent.id if sent is not None else None

        db_session = self.bot.create_db_session()
        entry = db_session.query(models.Starboard).filter(
            models.Starboard.recv == recv_id and models.Starboard.sent == sent_id
        )
        entry.delete(synchronize_session=False)
        db_session.commit()
        db_session.close()

    async def _fetch_message_or_none(
        self, channel: (discord.TextChannel | None), id: (int | None)
    ) -> (discord.Message | None):
        """Translates a lot of None into much less None. Also translates NotFound exceptions."""
        if channel is None or id is None:
            return None
        else:
            try:
                return await channel.fetch_message(id)
            except discord.NotFound():
                return None

    async def _lookup_from_id(
        self, channel_id: int, message_id: int
    ) -> Tuple[discord.Message | None, discord.Message | None]:
        """Takes a channel ID and a message ID. These may be for a starboard message or a recieved message.

        Returns (Recieved Message, Starboard Message), or Nones, as applicable.
        """
        db_session = self.bot.create_db_session()

        entry = None
        if self.starboard_channel.id == channel_id:
            # we're primarily looking up a recieved message and a location.
            # first, get the entry, then the location, then _fetch_message_or_none the remaining IDs.
            entry = (
                db_session.query(models.Starboard)
                .filter(models.Starboard.sent == message_id)
                .one_or_none()
            )

            if entry.recv_location is not None:
                channel = self.bot.get_channel(entry.recv_location)

                return (
                    self._fetch_message_or_none(channel, entry.recv),
                    self._fetch_message_or_none(self.starboard_channel, entry.sent),
                )
            else:
                # if the recieved location is None, then the message won't exist either.
                # The only thing we can possibly return is a starboard message.
                return (
                    None,
                    self._fetch_message_or_none(self.starboard_channel, entry.sent),
                )

        else:
            # we're primarily looking up a starboard message.
            entry = (
                db_session.query(models.Starboard)
                .filter(models.Starboard.recv == message_id)
                .one_or_none()
            )

            if entry.recv_location != channel_id:
                # This also implies entry.recv_location is not None
                raise SomethingsFucked(
                    "Recieved message from different channel to DB lookup!"
                )
            elif entry.sent is None:
                raise BlacklistedMessageError()

            channel = self.bot.get_channel(channel_id)

            return (
                self._fetch_message_or_none(channel, entry.recv),
                self._fetch_message_or_none(self.starboard_channel, entry.sent),
            )

    async def _count_num_reacts(
        self, data: Tuple[discord.Message | None, discord.Message | None]
    ) -> int:
        """Takes _lookup_from_id data (two messages, maybe None).

        Returns the number of unique reactions across both messages, not including the authors of those messages.
        """
        users = []
        authors = []

        for message in data:
            if message is None:
                continue

            # store the message authors so we can discard their reacts later
            # grandfathering old messages where their reacts were not auto-deleted, also failsafes, etc
            authors += [message.author.id]
            reaction = discord.utils.get(message.reactions, emoji=self.starboard_emoji)
            if reaction is not None:
                # we use the user.id to describe the reaction so we can set() it and
                # eliminate duplicates (only count one reaction per person)
                users += [user.id async for user in reaction.users()]

        return len(set([user for user in users if user not in authors]))

    def _generate_message_text(
        self, reaction_count: int, recieved_msg: (discord.Message | None)
    ) -> str:
        return (
            f"{str(self.starboard_emoji)} {reaction_count} | "
            f"{('#' + recieved_msg.channel.name) if recieved_msg is not None else 'OoOoO... ghost message!'}"
        )

    def _generate_message_embeds(
        self, recieved_msg: discord.Message
    ) -> List[discord.Embed]:
        """Creates the starboard embed for a message, including author, colours, replies, etc."""
        embed = discord.Embed(
            color=recieved_msg.author.top_role.color, description=recieved_msg.content
        )
        embed.set_author(
            name=recieved_msg.author.display_name,
            icon_url=recieved_msg.author.display_avatar.url,
        )
        embed.set_footer(
            text=recieved_msg.created_at.astimezone(tz=self.BRISBANE_TZ).strftime(
                "%b %d, %H:%M:%S"
            )
        )

        if len(recieved_msg.attachments) > 0:
            embed.set_image(url=recieved_msg.attachments[0].url)
            # only takes the first attachment to avoid sending large numbers of images to starboard.

        if recieved_msg.reference is not None and not isinstance(
            recieved_msg.reference.resolved, discord.DeletedReferencedMessage
        ):
            # if the reference exists, add it. isinstance here just tightens race conditions; we check
            # that messages aren't deleted before calling this anyway.
            replied = discord.Embed(
                color=recieved_msg.reference.resolved.author.top_role.color,
                description=recieved_msg.reference.resolved.content,
            )

            replied.set_author(
                name=f"Replying to {recieved_msg.reference.resolved.author.display_name}",
                icon_url=recieved_msg.reference.resolved.author.display_avatar.url,
            )

            replied.set_footer(
                text=recieved_msg.reference.resolved.created_at.astimezone(
                    tz=self.BRISBANE_TZ
                ).strftime("%b %d, %H:%M:%S")
            )

            return [replied, embed]
        return [embed]

    async def _process_sb_updates(
        self,
        reaction_count: int,
        recieved_msg: (discord.Message | None),
        starboard_msg: (discord.Message | None),
    ) -> None:
        if (
            reaction_count >= self.base_threshold
            and recieved_msg is not None
            and recieved_msg.id not in self.base_blocked_messages
            and starboard_msg is None
            and (
                recieved_msg.reference is None
                or not isinstance(
                    recieved_msg.reference.resolved, discord.DeletedReferencedMessage
                )
            )
        ):
            # Above threshold, not blocked, not replying to deleted msg, no current starboard message? post it.
            new_sb_message = await self.starboard_channel.send(
                content=self._generate_message_text(),
                embeds=self._generate_message_embeds(),
            )

            await new_sb_message.edit(
                view=discord.ui.View.from_message(new_sb_message).add_item(
                    discord.ui.Button(
                        label="Original Message",
                        style=discord.ButtonStyle.link,
                        url=recieved_msg.jump_url,
                    )
                )
            )

            # recieved_msg isn't None and we just sent the sb message, so it also shouldn't be None
            self._starboard_db_add(recieved_msg, recieved_msg.channel, new_sb_message)

            # start the base ratelimit
            self.base_blocked_messages += [recieved_msg.id]
            Timer(self.ratelimit, self._rm_base_ratelimit, [recieved_msg.id]).start()
        elif reaction_count >= self.base_threshold and starboard_msg is not None:
            # Above threshold, existing message? update it.
            if reaction_count >= self.big_threshold:
                await starboard_msg.pin(
                    reason=f"Reached {self.big_threshold} starboard reactions."
                )

                # start the pin ratelimit
                self.big_blocked_messages += [starboard_msg.id]
                Timer(
                    self.ratelimit, self._rm_big_ratelimit, [starboard_msg.id]
                ).start()
            elif starboard_msg.pinned:
                await starboard_msg.unpin(
                    reason=f"Fell below starboard threshold ({self.big_threshold})."
                )

            await starboard_msg.edit(
                content=self._generate_message_text(reaction_count, recieved_msg)
            )
        else:
            # Below threshold, or blocked from sending. Might need to delete.
            if starboard_msg is not None:
                self._starboard_db_remove(recieved_msg, starboard_msg)
                await starboard_msg.delete()

    """
    The four handlers below here are more or less identical.
    The differences are just that `add` deletes :starhaj:'s that come from the author of the message,
    and `clear` doesn't need to check that the payload references :starhaj:.    
    """

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        if (
            payload.emoji != self.starboard_emoji
            or self.bot.get_guild(payload.guild_id) is None
        ):
            return

        try:
            recieved_msg, starboard_msg = await self._lookup_from_id(
                payload.channel_id, payload.message_id
            )
        except BlacklistedMessageError:
            return

        if recieved_msg is not None and recieved_msg.author.id == payload.user_id:
            # payload.member is guaranteed to be available because we're adding and we're in a server
            return await recieved_msg.remove_reaction(payload.emoji, payload.member)

        new_reaction_count = await self._count_num_reacts((recieved_msg, starboard_msg))
        await self._process_sb_updates(new_reaction_count, recieved_msg, starboard_msg)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        if (
            payload.emoji != self.starboard_emoji
            or self.bot.get_guild(payload.guild_id) is None
        ):
            return

        try:
            recieved_msg, starboard_msg = await self._lookup_from_id(
                payload.channel_id, payload.message_id
            )
        except BlacklistedMessageError:
            return

        new_reaction_count = await self._count_num_reacts((recieved_msg, starboard_msg))
        await self._process_sb_updates(new_reaction_count, recieved_msg, starboard_msg)

    @commands.Cog.listener()
    async def on_raw_reaction_clear(
        self, payload: discord.RawReactionClearEvent
    ) -> None:
        if self.bot.get_guild(payload.guild_id) is None:
            return

        try:
            recieved_msg, starboard_msg = await self._lookup_from_id(
                payload.channel_id, payload.message_id
            )
        except BlacklistedMessageError:
            return

        new_reaction_count = await self._count_num_reacts((recieved_msg, starboard_msg))
        await self._process_sb_updates(new_reaction_count, recieved_msg, starboard_msg)

    @commands.Cog.listener()
    async def on_raw_reaction_clear_emoji(
        self, payload: discord.RawReactionClearEmojiEvent
    ) -> None:
        if (
            payload.emoji != self.starboard_emoji
            or self.bot.get_guild(payload.guild_id) is None
        ):
            return

        try:
            recieved_msg, starboard_msg = await self._lookup_from_id(
                payload.channel_id, payload.message_id
            )
        except BlacklistedMessageError:
            return

        new_reaction_count = await self._count_num_reacts((recieved_msg, starboard_msg))
        await self._process_sb_updates(new_reaction_count, recieved_msg, starboard_msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(Starboard(bot))
