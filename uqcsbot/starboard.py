import os
from threading import Timer
from typing import List
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot import models
# needs to be models and not just starboard because of namespacing with this class

class BlacklistedMessageError(Exception):
    pass
class ReferenceDeletedError(Exception):
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

        self.base_blocked_messages = [] # messages that are temp blocked from being resent to the starboard
        self.big_blocked_messages = [] # messages that are temp blocked from being re-pinned in the starboard

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
        self.starboard_channel = discord.utils.get(self.bot.get_all_channels(), name=self.CHANNEL_NAME)
    
    def _rm_base_ratelimit(self, id: int):
        """ Callback to remove a message from the base-ratelimited list """
        self.base_blocked_messages.remove(id)
    
    def _rm_big_ratelimit(self, id: int):
        """ Callback to remove a message from the big-ratelimited list """
        self.big_blocked_messages.remove(id)
    
    async def _blacklist_log(self, message: discord.Message, user: discord.Member, blacklist: bool):
        """ Logs a blacklist/whitelist command to the modlog. """
        channels = self.bot.get_all_channels()
        modlog = discord.utils.get(channels, name="admin-alerts")
        state = "blacklisted" if blacklist else "whitelisted"

        embed = discord.Embed(color=message.author.top_role.color, description=message.content)
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        embed.set_footer(text=message.created_at.astimezone(tz=self.BRISBANE_TZ).strftime('%b %d, %H:%M:%S'))

        if len(message.attachments) > 0:
            embed.set_image(url = message.attachments[0].url)
            # only takes the first attachment to avoid sending large numbers of images to starboard.

        log_item = await modlog.send(
            f"{str(user)} {state} message {message.id}",
            embeds=[embed])
        
        await log_item.edit(
                view=discord.ui.View.from_message(log_item).add_item(discord.ui.Button(
                    label="Original Message",
                    style=discord.ButtonStyle.link,
                    url=message.jump_url
                ))
            )
    
    @app_commands.default_permissions(manage_messages=True)
    async def context_blacklist_sb_message(self, interaction: discord.Interaction, message: discord.Message):
        """ Blacklists a message from being starboarded. If the message is already starboarded, also deletes it. """
        db_session = self.bot.create_db_session()
        # can't use the db query functions for this, they error out if a message hits the blacklist
        entry = db_session.query(models.Starboard).filter(models.Starboard.recv == message.id)
        query_val = entry.one_or_none()

        if query_val is not None:
            if query_val.sent is None:
                # if the table has (recv, none) then it's already blacklisted.
                return

            # otherwise the table has (recv, something), we should delete the something and then make it (recv, none)
            await (await self.starboard_channel.fetch_message(query_val.sent)).delete()
            query_val.sent = None
        else:
            # other-otherwise the table doesn't have recv, so we add (recv, none)
            db_session.add(models.Starboard(recv=message.id, recv_location=message.channel.id, sent=None))

        db_session.commit()
        db_session.close()

        await self._blacklist_log(message, interaction.user, blacklist=True)
        await interaction.response.send_message(f"Blacklisted message {message.id}.", ephemeral=True)

    @app_commands.default_permissions(manage_messages=True)
    async def context_whitelist_sb_message(self, interaction: discord.Interaction, message: discord.Message):
        """ Removes a message from the starboard blacklist.
            N.B. Doesn't perform an 'update' of the message. This may result in messages meeting the threshold
            but not being starboarded if they don't get any more reacts. """
        db_session = self.bot.create_db_session()

        # if we find a (recv, none) for this message, delete it. otherwise the message is already not blacklisted.
        entry = db_session.query(models.Starboard).filter(
            models.Starboard.recv == message.id,
            models.Starboard.sent == None
        )
        if entry.one_or_none() is not None:
            entry.delete(synchronize_session=False)
            db_session.commit()
        db_session.close()

        await self._blacklist_log(message, interaction.user, blacklist=False)
        await interaction.response.send_message(f"Whitelisted message {message.id}.", ephemeral=True)
    
    async def _query_sb_message(self, recv: int) -> discord.Message:
        """ Get the starboard message corresponding to the recieved message. Returns None if no sb message exists.
        Handles messages potentially being deleted and cleans up the DB accordingly. """
        db_session = self.bot.create_db_session()
        entry = db_session.query(models.Starboard).filter(models.Starboard.recv == recv)
        query_val = entry.one_or_none()
        
        message = None
        if query_val is not None:
            try:
                if query_val.sent is None:
                    # (recv, none) is a blacklist entry
                    raise BlacklistedMessageError()

                message = await self.starboard_channel.fetch_message(query_val.sent)
            except discord.errors.NotFound:
                # if we can't find the sb message anymore, then it's been deleted and we return None
                # but we also delete the SB entry to save future lookups.
                entry.delete(synchronize_session=False)
                db_session.commit()
            finally:
                db_session.close()
        
        return message

    async def _query_og_message(self, sent: int) -> discord.Message:
        """ Get the og message corresponding to this starboard message. Returns None if the message has been deleted.
        Handles messages no longer existing and cleans up the DB accordingly. """
        db_session = self.bot.create_db_session()
        entry = db_session.query(models.Starboard).filter(
            models.Starboard.sent == sent
        ).one_or_none()

        message = None
        if entry is not None:
            if entry.recv is not None and entry.recv_location is not None:
                try:
                    channel = self.bot.get_channel(entry.recv_location)
                    if channel is None:
                        # for some reason get_channel doesn't handle errors the same as fetch_message
                        # but we want to treat them the same anyway
                        raise discord.errors.NotFound()
                    
                    message = await channel.fetch_message(entry.recv)
                except discord.errors.NotFound:
                    # if we can't find the recv message anymore, then it's been deleted and we return None
                    # however, SB messages can still generate :starhaj:'s, so we don't necessarily delete the
                    # message - the caller will handle that.

                    entry.recv_location = None
                    db_session.commit()
        
        db_session.close()
        return message
    
    async def _find_num_reactions(self, recv: discord.Message, sent: discord.Message) -> int:
        """ Find the total number of starboard_emoji reacts across this list of messages. """
        users = []
        authors = []

        for message in (recv, sent):
            if message is None:
                continue
            
            # store the message authors so we can discard their reacts later
            authors += [message.author.id]
            reaction = discord.utils.get(message.reactions, emoji=self.starboard_emoji)
            if reaction is not None:
                # we use the user.id as a marker of the reaction so we can set() it and
                # eliminate duplicates (only count one reaction per person)
                users += [user.id async for user in reaction.users()]

        return len(set([user for user in users if user not in authors]))

    def _update_sb_message(self, recv: int, recv_location: int, sent: int):
        """ Sets the ID of the starboard message corresponding to the recieved message """
        db_session = self.bot.create_db_session()
        db_session.add(models.Starboard(recv=recv, recv_location=recv_location, sent=sent))
        db_session.commit()
        db_session.close()
    
    def _remove_sb_message(self, recv: int):
        """ Deletes the DB entry for the starboard message for this recieved message """
        db_session = self.bot.create_db_session()
        entry = db_session.query(models.Starboard).filter(models.Starboard.recv == recv)
        entry.delete(synchronize_session=False)
        db_session.commit()
        db_session.close()
    
    def _create_sb_embed(self, recv: discord.Message) -> discord.Embed:
        """ Creates the starboard embed for a message, including author, colours, replies, etc. """
        if recv.reference is not None and isinstance(recv.reference.resolved, discord.DeletedReferencedMessage):
            # we raise this exception and auto-blacklist replies to deleted messages on the logic that those
            # messages were probably deleted for a reason
            raise ReferenceDeletedError()

        embed = discord.Embed(color=recv.author.top_role.color, description=recv.content)
        embed.set_author(name=recv.author.display_name, icon_url=recv.author.display_avatar.url)
        embed.set_footer(text=recv.created_at.astimezone(tz=self.BRISBANE_TZ).strftime('%b %d, %H:%M:%S'))

        if len(recv.attachments) > 0:
            embed.set_image(url = recv.attachments[0].url)
            # only takes the first attachment to avoid sending large numbers of images to starboard.
        
        if recv.reference is not None and not isinstance(recv.reference.resolved, discord.DeletedReferencedMessage):
            # if the reference exists, add it. isinstance here prevents race conditions
            replied = discord.Embed(
                color=recv.reference.resolved.author.top_role.color,
                description=recv.reference.resolved.content
            )

            replied.set_author(
                name=f"Replying to {recv.reference.resolved.author.display_name}",
                icon_url=recv.reference.resolved.author.display_avatar.url
            )

            replied.set_footer(
                text=recv.reference.resolved.created_at.astimezone(tz=self.BRISBANE_TZ).strftime('%b %d, %H:%M:%S')
            )

            return [replied, embed]
        return [embed]

    async def _get_message_pair(self, channel, message_id: int) -> List[discord.Message]:
        """ Given some message ID, return the two Message objects relevant to it: 
        the starboard message (or None) and the original message (or None) """
        message = await channel.fetch_message(message_id)

        if channel == self.starboard_channel:
            sent = message
            recv = await self._query_og_message(message_id)
        else:
            recv = message
            sent = await self._query_sb_message(message_id)
        
        return [recv, sent]

    @app_commands.command()
    @app_commands.default_permissions(manage_messages=True)
    async def cleanup_starboard(self, interaction: discord.Interaction):
        """ Cleans up the last 100 messages from the starboard.
        Removes any uqcsbot message that doesn't have a corresponding message id in the db, regardless of recv. """
        sb_messages = self.starboard_channel.history(limit=100)
        db_session = self.bot.create_db_session()

        # in case it takes a while, we need to defer the interaction so it doesn't die
        await interaction.response.defer(thinking=True)

        async for message in sb_messages:
            query = db_session.query(models.Starboard).filter(models.Starboard.sent == message.id).one_or_none()
            if query is None and message.author.id == self.bot.user.id:
                # only delete messages that uqcsbot itself sent
                message.delete()

        
        db_session.close()
        await interaction.followup.send("Finished cleaning up.")
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.emoji.id != self.starboard_emoji.id:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        
        channel = self.bot.get_channel(payload.channel_id)
        
        try:
            recv_message, sb_message = await self._get_message_pair(channel, payload.message_id)
        except (discord.errors.NotFound, BlacklistedMessageError):
            # if the message has already been deleted, or is blacklisted, we're done here
            return

        # delete starhaj self-reacts instantly
        if recv_message.author.id == payload.user_id:
            # payload.member is guaranteed to be available because we're adding and we're in a server
            await recv_message.remove_reaction(payload.emoji, payload.member)
            return
        
        new_reaction_count = await self._find_num_reactions(recv_message, sb_message)

        # if above threshold, not yet sent, not ratelimited, and message has some text to starboard
        if new_reaction_count >= self.base_threshold and \
                sb_message is None and recv_message.id not in self.base_blocked_messages and recv_message.content != "":
            try:
                new_sb_message = await self.starboard_channel.send(
                    content=f"{str(self.starboard_emoji)} {new_reaction_count} | #{recv_message.channel.name}",
                    embeds=self._create_sb_embed(recv_message)
                    # note that the embed is never edited, which means the content of the starboard post is fixed as
                    # soon as the Nth reaction is processed
                )
            except ReferenceDeletedError:
                db_session = self.bot.create_db_session()
                db_session.add(models.Starboard(recv=recv_message.id, recv_location=recv_message.channel.id, sent=None))
                db_session.commit()
                db_session.close()
                return
            
            await new_sb_message.edit(
                view=discord.ui.View.from_message(new_sb_message).add_item(discord.ui.Button(
                    label="Original Message",
                    style=discord.ButtonStyle.link,
                    url=recv_message.jump_url
                ))
            )

            self._update_sb_message(recv_message.id, recv_message.channel.id, new_sb_message.id)
            
            self.base_blocked_messages += [recv_message.id]
            Timer(self.ratelimit, self._rm_base_ratelimit, [recv_message.id]).start()
        # elif above threshold and sent and not ratelimited. note that this means a big-blocked message won't see
        # message text updates for the duration of its ratelimit. in practice this is rare enough that i think we're
        # all good.
        elif new_reaction_count > self.base_threshold and \
                sb_message is not None and recv_message.id not in self.big_blocked_messages:

            await sb_message.edit(
                content=f"{str(self.starboard_emoji)} {new_reaction_count} | #{recv_message.channel.name}"
            )

            if new_reaction_count >= self.big_threshold and not sb_message.pinned:
                await sb_message.pin(reason=f"Reached {self.big_threshold} starboard reactions")
            
            self.big_blocked_messages += [recv_message.id]
            Timer(self.ratelimit, self._rm_big_ratelimit, [recv_message.id]).start()


    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.emoji.id != self.starboard_emoji.id:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        
        channel = self.bot.get_channel(payload.channel_id)
        
        try:
            recv_message, sb_message = await self._get_message_pair(channel, payload.message_id)
        except (discord.errors.NotFound, BlacklistedMessageError):
            # if the message has already been deleted, or is blacklisted, we're done here
            return
        
        if sb_message == None:
            return
        
        new_reaction_count = await self._find_num_reactions(recv_message, sb_message)

        if new_reaction_count < self.base_threshold:
            await sb_message.delete() # delete will also unpin
            self._remove_sb_message(payload.message_id)
            return
        
        if new_reaction_count < self.big_threshold and sb_message.pinned:
            await sb_message.unpin()

        await sb_message.edit(
            content=f"{str(self.starboard_emoji)} {new_reaction_count} | #{recv_message.channel.name}"
        )


    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload: discord.RawReactionClearEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        
        channel = self.bot.get_channel(payload.channel_id)
        try:
            recv_message, sb_message = await self._get_message_pair(channel, payload.message_id)
        except (discord.errors.NotFound, BlacklistedMessageError):
            # if the message has already been deleted, or is blacklisted, we're done here
            return
        
        if sb_message == None:
            return
        
        new_reaction_count = await self._find_num_reactions(recv_message, sb_message)

        if new_reaction_count < self.base_threshold:
            await sb_message.delete() # delete will also unpin
            self._remove_sb_message(payload.message_id)
            return
        
        if new_reaction_count < self.big_threshold and sb_message.pinned:
            await sb_message.unpin()

        await sb_message.edit(
            content=f"{str(self.starboard_emoji)} {new_reaction_count} | #{recv_message.channel.name}"
        )


    @commands.Cog.listener()
    async def on_raw_reaction_clear_emoji(self, payload: discord.RawReactionClearEmojiEvent):
        if payload.emoji.id != self.starboard_emoji.id:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        
        channel = self.bot.get_channel(payload.channel_id)
        try:
            recv_message, sb_message = await self._get_message_pair(channel, payload.message_id)
        except (discord.errors.NotFound, BlacklistedMessageError):
            # if the message has already been deleted, or is blacklisted, we're done here
            return
        
        if sb_message == None:
            return
        
        new_reaction_count = await self._find_num_reactions(recv_message, sb_message)

        if new_reaction_count < self.base_threshold:
            await sb_message.delete() # delete will also unpin
            self._remove_sb_message(payload.message_id)
            return
        
        if new_reaction_count < self.big_threshold and sb_message.pinned:
            await sb_message.unpin()

        await sb_message.edit(
            content=f"{str(self.starboard_emoji)} {new_reaction_count} | #{recv_message.channel.name}"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Starboard(bot))