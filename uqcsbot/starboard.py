from typing import Optional

import discord
from discord.ext import commands

from uqcsbot import models
# needs to be models and not just starboard because of namespacing with this class

class SBView(discord.ui.View):
    def __init__(self, button: discord.ui.Button):
        self.add_item(button)
        self.timeout = None

class Starboard(commands.Cog):
    CHANNEL_NAME = "starboard"
    EMOJI_NAME = "neat"

    STARBOARD_BASE_THRESHOLD = 5
    STARBOARD_BIG_THRESHOLD = 20

    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        """ Really this should be in __init__ but this stuff doesn't exist until the bot is ready """
        self.starboard_emoji = discord.utils.get(self.bot.emojis, name=self.EMOJI_NAME)
        self.starboard_channel = discord.utils.get(self.bot.get_all_channels(), name=self.CHANNEL_NAME)
    
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
        # TODO: embed replies, embed images, timestamp, link to original, link to channel
        embed = discord.Embed(color=recv.author.top_role.color, description=recv.content)
        embed.set_author(name=recv.author.display_name, icon_url=recv.author.display_avatar.url)
        embed.set_footer(text=recv.created_at.strftime('%b %d, %H:%M:%S'))

        if len(recv.attachments) > 0:
            embed.set_image(url = recv.attachments[0].url)
        
        if recv.reference is not None:
            replied = discord.Embed(color=recv.reference.resolved.author.top_role.color, description=recv.reference.resolved.content)
            replied.set_author(name=f"Replying to {recv.reference.resolved.author.display_name}", icon_url=recv.reference.resolved.author.display_avatar.url)
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
            # TODO: "reaction count" for starboard should take into account (original + starboard)
            return
        
        recv_message = await channel.fetch_message(payload.message_id)
        reaction = discord.utils.get(recv_message.reactions, emoji=self.starboard_emoji)

        new_reaction_count = 0
        if reaction is not None:
            new_reaction_count = reaction.count
        
        sb_message_id = self._query_sb_message(recv_message.id)

        if new_reaction_count == self.STARBOARD_BASE_THRESHOLD or (new_reaction_count > self.STARBOARD_BASE_THRESHOLD and sb_message_id is None):
            new_sb_message = await self.starboard_channel.send(
                content=f"{str(self.starboard_emoji)} {new_reaction_count} | {recv_message.channel.mention}",
                embeds=self._create_sb_embed(recv_message)
            )
            await new_sb_message.edit(view=discord.ui.View.from_message(new_sb_message).add_item(discord.ui.Button(label="Original Message", style=discord.ButtonStyle.link, url=recv_message.jump_url)))

            self._update_sb_message(recv_message.id, new_sb_message.id)
        elif new_reaction_count > self.STARBOARD_BASE_THRESHOLD:
            old_sb_message = await self.starboard_channel.fetch_message(sb_message_id)

            await old_sb_message.edit(content=f"{str(self.starboard_emoji)} {new_reaction_count} | {recv_message.channel.mention}")

            if new_reaction_count == self.STARBOARD_BIG_THRESHOLD:
                await old_sb_message.pin(reason="Reached 20 starboard reactions")


    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.emoji.id != self.starboard_emoji.id:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        
        channel = self.bot.get_channel(payload.channel_id)
        if channel == self.starboard_channel or channel.category.name.startswith("admin"):
            # TODO: "reaction count" for starboard should take into account (original + starboard)
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

        if new_reaction_count < self.STARBOARD_BASE_THRESHOLD:
            await sb_message.delete()
            self._remove_sb_message(payload.message_id)
            return
        
        if new_reaction_count < self.STARBOARD_BIG_THRESHOLD and sb_message.pinned:
            await sb_message.unpin()
        
        old_sb_message = await self.starboard_channel.fetch_message(sb_message_id)
        await old_sb_message.edit(content=f"{str(self.starboard_emoji)} {new_reaction_count} | {recv_message.channel.mention}")


    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload: discord.RawReactionClearEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        
        channel = self.bot.get_channel(payload.channel_id)
        if channel == self.starboard_channel or channel.category.name.startswith("admin"):
            # TODO: "reaction count" for starboard should take into account (original + starboard)
            return
        
        recv_message = await channel.fetch_message(payload.message_id)
    
        sb_message_id = self._query_sb_message(recv_message.id)
        if sb_message_id is None:
            return
        
        sb_message = await self.starboard_channel.fetch_message(sb_message_id)

        if sb_message.pinned:
            await sb_message.unpin()
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
            # TODO: "reaction count" for starboard should take into account (original + starboard)
            return
        
        recv_message = await channel.fetch_message(payload.message_id)
    
        sb_message_id = self._query_sb_message(recv_message.id)
        if sb_message_id is None:
            return
        
        sb_message = await self.starboard_channel.fetch_message(sb_message_id)

        if sb_message.pinned:
            await sb_message.unpin()
        await sb_message.delete()
        self._remove_sb_message(payload.message_id)

async def setup(bot: commands.Bot):
    await bot.add_cog(Starboard(bot))