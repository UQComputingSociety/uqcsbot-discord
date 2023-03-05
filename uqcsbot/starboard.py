import os
from typing import Optional
from threading import Timer

import discord
from discord.ext import commands

from uqcsbot import models
# needs to be models and not just starboard because of namespacing with this class

class Starboard(commands.Cog):
    CHANNEL_NAME = "starboard"
    EMOJI_NAME = "starhaj"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.base_threshold = int(os.environ.get("SB_BASE_THRESHOLD"))
        self.big_threshold = int(os.environ.get("SB_BIG_THRESHOLD"))
        self.ratelimit = int(os.environ.get("SB_RATELIMIT"))

        self.base_blocked_messages = [] # messages that are temp blocked from being resent to the starboard
        self.big_blocked_messages = [] # messages that are temp blocked from being re-pinned in the starboard
    
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
    
    def _query_sb_message(self, recv: int) -> Optional[int]:
        """ Get the starboard message ID corresponding to the recieved message """
        db_session = self.bot.create_db_session()
        id = db_session.query(models.Starboard).filter(models.Starboard.recv == recv).one_or_none()
        db_session.close()

        if id is not None:
            return id.sent
        return id

    def _update_sb_message(self, recv: int, sent: int):
        """ Sets the ID of the starboard message corresponding to the recieved message """
        db_session = self.bot.create_db_session()
        db_session.add(models.Starboard(recv=recv, sent=sent))
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
        embed = discord.Embed(color=recv.author.top_role.color, description=recv.content)
        embed.set_author(name=recv.author.display_name, icon_url=recv.author.display_avatar.url)
        embed.set_footer(text=recv.created_at.strftime('%b %d, %H:%M:%S'))

        if len(recv.attachments) > 0:
            embed.set_image(url = recv.attachments[0].url)
            # only takes the first attachment to avoid sending large numbers of images to starboard.
        
        if recv.reference is not None and not isinstance(recv.reference, discord.DeletedReferencedMessage):
            replied = discord.Embed(
                color=recv.reference.resolved.author.top_role.color,
                description=recv.reference.resolved.content
            )

            replied.set_author(
                name=f"Replying to {recv.reference.resolved.author.display_name}",
                icon_url=recv.reference.resolved.author.display_avatar.url
            )

            replied.set_footer(text=recv.reference.resolved.created_at.strftime('%b %d, %H:%M:%S'))

            return [replied, embed]
        
        return [embed]
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.emoji.id != self.starboard_emoji.id:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        
        channel = self.bot.get_channel(payload.channel_id)
        if channel == self.starboard_channel or channel.category.name.startswith("admin"):
            # TODO: "reaction count" for starboard could take into account (original + starboard)
            return
        
        recv_message = await channel.fetch_message(payload.message_id)
        reaction = discord.utils.get(recv_message.reactions, emoji=self.starboard_emoji)

        new_reaction_count = 0
        if reaction is not None:
            new_reaction_count = reaction.count
        
        sb_message_id = self._query_sb_message(recv_message.id)

        if new_reaction_count >= self.base_threshold and \
                sb_message_id is None and recv_message.id not in self.base_blocked_messages:
            new_sb_message = await self.starboard_channel.send(
                content=f"{str(self.starboard_emoji)} {new_reaction_count} | {recv_message.channel.mention}",
                embeds=self._create_sb_embed(recv_message)
                # note that the embed is never edited, which means the content of the starboard post is fixed as
                # soon as the 5th reaction is processed
            )
            await new_sb_message.edit(
                view=discord.ui.View.from_message(new_sb_message).add_item(discord.ui.Button(
                    label="Original Message",
                    style=discord.ButtonStyle.link,
                    url=recv_message.jump_url
                ))
            )

            self._update_sb_message(recv_message.id, new_sb_message.id)
            
            self.base_blocked_messages += [recv_message.id]
            Timer(self.ratelimit, self._rm_base_ratelimit, [recv_message.id]).start()
        elif new_reaction_count > self.base_threshold and \
                sb_message_id is not None and recv_message.id not in self.big_blocked_messages:
            old_sb_message = await self.starboard_channel.fetch_message(sb_message_id)

            await old_sb_message.edit(
                content=f"{str(self.starboard_emoji)} {new_reaction_count} | {recv_message.channel.mention}"
            )

            if new_reaction_count >= self.big_threshold and not old_sb_message.pinned:
                await old_sb_message.pin(reason=f"Reached {self.big_threshold} starboard reactions")
            
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
        if channel == self.starboard_channel or channel.category.name.startswith("admin"):
            # TODO: "reaction count" for starboard could take into account (original + starboard)
            return
        
        recv_message = await channel.fetch_message(payload.message_id)
        reaction = discord.utils.get(recv_message.reactions, emoji=self.starboard_emoji)

        new_reaction_count = 0
        if reaction is not None:
            new_reaction_count = reaction.count
        
        sb_message_id = self._query_sb_message(recv_message.id)
        if sb_message_id is None:
            return

        sb_message = await self.starboard_channel.fetch_message(sb_message_id)

        if new_reaction_count < self.base_threshold:
            await sb_message.delete() # delete will also unpin
            self._remove_sb_message(payload.message_id)
            return
        
        if new_reaction_count < self.big_threshold and sb_message.pinned:
            await sb_message.unpin()
        
        old_sb_message = await self.starboard_channel.fetch_message(sb_message_id)
        await old_sb_message.edit(
            content=f"{str(self.starboard_emoji)} {new_reaction_count} | {recv_message.channel.mention}"
        )


    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload: discord.RawReactionClearEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        
        channel = self.bot.get_channel(payload.channel_id)
        if channel == self.starboard_channel or channel.category.name.startswith("admin"):
            # TODO: "reaction count" for starboard could take into account (original + starboard)
            return
        
        recv_message = await channel.fetch_message(payload.message_id)
    
        sb_message_id = self._query_sb_message(recv_message.id)
        if sb_message_id is None:
            return
        
        sb_message = await self.starboard_channel.fetch_message(sb_message_id)

        # delete will also unpin
        await sb_message.delete()
        self._remove_sb_message(payload.message_id)


    @commands.Cog.listener()
    async def on_raw_reaction_clear_emoji(self, payload: discord.RawReactionClearEmojiEvent):
        if payload.emoji.id != self.starboard_emoji.id:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        
        channel = self.bot.get_channel(payload.channel_id)
        if channel == self.starboard_channel or channel.category.name.startswith("admin"):
            # TODO: "reaction count" for starboard could take into account (original + starboard)
            return
        
        recv_message = await channel.fetch_message(payload.message_id)
    
        sb_message_id = self._query_sb_message(recv_message.id)
        if sb_message_id is None:
            return
        
        sb_message = await self.starboard_channel.fetch_message(sb_message_id)

        # delete will also unpin
        await sb_message.delete()
        self._remove_sb_message(payload.message_id)

async def setup(bot: commands.Bot):
    await bot.add_cog(Starboard(bot))