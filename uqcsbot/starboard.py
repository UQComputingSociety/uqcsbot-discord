import os
from threading import Timer
from typing import List
from datetime import timezone

import discord
from discord import app_commands
from discord.ext import commands
from pytz import timezone

from uqcsbot import models
# needs to be models and not just starboard because of namespacing with this class

class BlacklistedMessageError(Exception):
    pass
class ReferenceDeletedError(Exception):
    pass

class Starboard(commands.Cog):
    CHANNEL_NAME = "starboard"
    EMOJI_NAME = "starhaj"
    BRISBANE_TZ = timezone('Australia/Brisbane')

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
    
    @app_commands.default_permissions(manage_messages=True)
    async def context_blacklist_sb_message(self, interaction: discord.Interaction, message: discord.Message):
        """ Blacklists a message from being starboarded. If the message is already starboarded, also deletes it. """
        db_session = self.bot.create_db_session()
        entry = db_session.query(models.Starboard).filter(models.Starboard.recv == message.id)
        query_val = entry.one_or_none()

        if query_val is not None:
            if query_val.sent is None:
                return

            await (await self.starboard_channel.fetch_message(query_val.sent)).delete()
            query_val.sent = None
        else:
            db_session.add(models.Starboard(recv=message.id, recv_location=message.channel.id, sent=None))

        db_session.commit()
        db_session.close()

        await interaction.response.send_message(f"Blacklisted message {message.id}.")

    @app_commands.default_permissions(manage_messages=True)
    async def context_whitelist_sb_message(self, interaction: discord.Interaction, message: discord.Message):
        """ Removes a message from the starboard blacklist. Doesn't perform an 'update' of the message. """
        db_session = self.bot.create_db_session()
        entry = db_session.query(models.Starboard).filter(
            models.Starboard.recv == message.id,
            models.Starboard.sent == None
        )
        if entry.one_or_none() is not None:
            entry.delete(synchronize_session=False)
            db_session.commit()
        db_session.close()
        await interaction.response.send_message(f"Whitelisted message {message.id}.")
    
    async def _query_sb_message(self, recv: int) -> discord.Message:
        """ Get the starboard message corresponding to the recieved message.
        Handles messages no longer existing and cleans up the DB accordingly. """
        db_session = self.bot.create_db_session()
        entry = db_session.query(models.Starboard).filter(models.Starboard.recv == recv)
        query_val = entry.one_or_none()
        
        message = None
        if query_val is not None:
            try:
                if query_val.sent is None:
                    raise BlacklistedMessageError()

                message = await self.starboard_channel.fetch_message(query_val.sent)
            except discord.errors.NotFound:
                entry.delete(synchronize_session=False)
                db_session.commit()
            finally:
                db_session.close()
        
        return message

    async def _query_og_message(self, sent: int) -> discord.Message:
        """ Get the og message corresponding to this starboard message.
        Handles messages no longer existing. """
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
                        raise discord.errors.NotFound()
                    
                    message = await channel.fetch_message(entry.recv)
                except discord.errors.NotFound:
                    entry.recv_location = None
                    entry.recv = None
                    db_session.commit()
        
        db_session.close()
        return message
    
    async def _find_num_reactions(self, messages: List[discord.Message]) -> int:
        """ Find the total number of starboard_emoji reacts across this list of messages. """
        users = []
        authors = []

        for message in messages:
            if message is None:
                continue
            
            authors += [message.author.id]
            reaction = discord.utils.get(message.reactions, emoji=self.starboard_emoji)
            if reaction is not None:
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
        if recv.reference is not None and isinstance(recv.reference.resolved, discord.DeletedReferencedMessage):
            raise ReferenceDeletedError()

        embed = discord.Embed(color=recv.author.top_role.color, description=recv.content)
        embed.set_author(name=recv.author.display_name, icon_url=recv.author.display_avatar.url)
        embed.set_footer(text=recv.created_at.astimezone(tz=self.BRISBANE_TZ).strftime('%b %d, %H:%M:%S'))

        if len(recv.attachments) > 0:
            embed.set_image(url = recv.attachments[0].url)
            # only takes the first attachment to avoid sending large numbers of images to starboard.
        
        if recv.reference is not None and not isinstance(recv.reference.resolved, discord.DeletedReferencedMessage):
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

    @app_commands.command()
    @app_commands.default_permissions(manage_messages=True)
    async def cleanup_starboard(self, interaction: discord.Interaction):
        """ Cleans up the last 30 messages from the starboard.
        Removes any uqcsbot message that doesn't have a corresponding message id. """
        sb_messages = await self.starboard_channel.history(limit=30)
        db_session = self.bot.create_db_session()

        await interaction.defer(thinking=True)

        for message in sb_messages:
            query = db_session.query(models.Starboard).filter(models.Starboard.sent == message.id).one_or_none()
            if query is None and message.author.id == self.user.id:
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
            messages = [await channel.fetch_message(payload.message_id)]
            if channel == self.starboard_channel:
                messages += [await self._query_og_message(payload.message_id)]
                sb_message, recv_message = messages
            else:
                messages += [await self._query_sb_message(payload.message_id)]
                recv_message, sb_message = messages
        except (discord.errors.NotFound, BlacklistedMessageError):
            return
        
        new_reaction_count = await self._find_num_reactions(messages)

        if new_reaction_count >= self.base_threshold and \
                sb_message is None and recv_message.id not in self.base_blocked_messages and recv_message.content != "":
            try:
                new_sb_message = await self.starboard_channel.send(
                    content=f"{str(self.starboard_emoji)} {new_reaction_count} | #{recv_message.channel.name}",
                    embeds=self._create_sb_embed(recv_message)
                    # note that the embed is never edited, which means the content of the starboard post is fixed as
                    # soon as the 5th reaction is processed
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
            messages = [await channel.fetch_message(payload.message_id)]
            if channel == self.starboard_channel:
                messages += [await self._query_og_message(payload.message_id)]
                sb_message, recv_message = messages
            else:
                messages += [await self._query_sb_message(payload.message_id)]
                recv_message, sb_message = messages
        except (discord.errors.NotFound, BlacklistedMessageError):
            return
        
        if sb_message == None:
            return
        
        new_reaction_count = await self._find_num_reactions(messages)

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
            messages = [await channel.fetch_message(payload.message_id)]
            if channel == self.starboard_channel:
                messages += [await self._query_og_message(payload.message_id)]
                sb_message, recv_message = messages
            else:
                messages += [await self._query_sb_message(payload.message_id)]
                recv_message, sb_message = messages
        except (discord.errors.NotFound, BlacklistedMessageError):
            return
        
        if sb_message == None:
            return
        
        new_reaction_count = await self._find_num_reactions(messages)

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
            messages = [await channel.fetch_message(payload.message_id)]
            if channel == self.starboard_channel:
                messages += [await self._query_og_message(payload.message_id)]
                sb_message, recv_message = messages
            else:
                messages += [await self._query_sb_message(payload.message_id)]
                recv_message, sb_message = messages
        except (discord.errors.NotFound, BlacklistedMessageError):
            return
        
        if sb_message == None:
            return
        
        new_reaction_count = await self._find_num_reactions(messages)

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