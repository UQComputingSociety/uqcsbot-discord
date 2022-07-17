import logging

import discord
from discord.ext import commands
from sqlalchemy.exc import NoResultFound

from uqcsbot.bot import UQCSBot
from uqcsbot.models import Channel, Message

from emoji import UNICODE_EMOJI_ENGLISH

JOINED_PERMISSIONS = discord.Permissions(read_messages=True)
SERVER_ID = 813324385179271168
# Testing Server
#SERVER_ID = 836589565237264415

class Channels(commands.Cog):

    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self.message_id = None

    def _channel_query(self, channel: str):
        db_session = self.bot.create_db_session()
        if len(channel) >= 2:
            channel = channel if channel[0] != "#" else channel[1 : ]
        channel_query = db_session.query(Channel).filter(Channel.name == channel,
                                                         Channel.joinable == True).one_or_none()
        db_session.close()

        return channel_query

    def _get_message_id(self):
        db_session = self.bot.create_db_session()
        message_query = db_session.query(Message).filter(Message.type == "react_message").one_or_none()
        db_session.close()

        return message_query.id

    def _valid_emoji(self, emoji):
        custom = set([f"<:{e.name}:{e.id}>" for e in self.bot.emojis])
        return emoji in UNICODE_EMOJI_ENGLISH or emoji in custom

    @commands.Cog.listener()
    async def on_ready(self):
        self.message_id = self._get_message_id()

    @commands.command()
    async def joinchannel(self, ctx: commands.Context, *channels: str):
        """ Joins the channel (or channels) that you specify. """
        for channel in channels:
            channel_query = self._channel_query(channel)

            if channel_query == None:
                await ctx.send(f"Unable to join {channel}.")
                continue

            channel = self.bot.get_channel(channel_query.id)
            guild = self.bot.get_guild(SERVER_ID)
            member = guild.get_member(ctx.author.id)

            if channel == None:
                await ctx.send(f"Unable to join {channel}.")
                continue

            # Don't let a user join the channel again if they are already in it.
            if channel.permissions_for(member).is_superset(JOINED_PERMISSIONS):
                await ctx.send(f"You're already a member of {channel}.")
                continue

            await channel.set_permissions(member, read_messages=True, reason="UQCSbot added.")
            join_message = await channel.send(f"{member.display_name} joined {channel.mention}")
            await join_message.add_reaction("👋")
            await ctx.send(f"You've joined {channel.mention}.")

    @commands.command(hidden=True)
    async def joinchannels(self, ctx: commands.Context, *channels: str):
        """ Alias for !joinchannel. """
        return await self.joinchannel(ctx, *channels)

    @commands.command()
    async def leavechannel(self, ctx: commands.Context, channel=""):
        """ Leaves the channel that you specify. """
        
        # If a channel is not specified, attempt to leave the current channel.
        if (channel == ""):
            channel = ctx.channel.name
            dm_notify = True

        channel_query = self._channel_query(channel)

        if channel_query == None:
            await ctx.send("Unable to leave that channel.")
            return

        channel = self.bot.get_channel(channel_query.id)
        guild = self.bot.get_guild(SERVER_ID)
        member = guild.get_member(ctx.author.id)

        # You can't leave a channel that doesn't exist or you're not in.
        if channel == None or channel.permissions_for(member).is_strict_subset(JOINED_PERMISSIONS):
            await ctx.send("Unable to leave that channel.")
            return

        await channel.set_permissions(member, read_messages=False, reason="UQCSbot removed.")
        if dm_notify:
            await ctx.author.send(f"You've left {channel.mention}")
        else:
            await ctx.send(f"You've left {channel.mention}")

    @commands.command()
    async def listchannels(self, ctx: commands.Context):
        """ Lists the channels that you can join. """
        db_session = self.bot.create_db_session()
        channels_query = db_session.query(Channel).filter(Channel.joinable == True).order_by(Channel.name)
        db_session.close()

        channel_list = "\n".join(channel.name for channel in channels_query)
        footer_messge = ("To join or leave one of these channels, use the !joinchannel and !leavechannel commands.\n"
                         "To join multiple channels, separate them with a space.")

        message = discord.Embed()
        message.title = "Joinable Channels"
        message.description = channel_list
        message.set_footer(text=footer_messge)

        await ctx.send(embed=message)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def addjoinchannel(self, ctx: commands.Context, channel: discord.TextChannel, emoji):
        """ Sets a channel to be joinable with UQCSbot. """
        if not self._valid_emoji(emoji):
            await ctx.send("Please select an emoji found within this server.")
            return

        db_session = self.bot.create_db_session()
        taken = db_session.query(Channel).filter(Channel.id != channel.id,
                                                 Channel.emoji == emoji).first()  
        if taken:
            db_session.close()
            await ctx.send("Please select an emoji that isn't already in use.") 
            return

        existing = db_session.query(Channel).filter(Channel.id == channel.id).one_or_none()
        if existing:
            existing.joinable = True
            existing.emoji = emoji
        else:
            db_session.add(Channel(id=channel.id, name=channel.name, joinable=True, emoji=emoji))
        db_session.commit()
        db_session.close()

        await ctx.send(f"{channel.mention} was added as a joinable channel.")
        react_message = await ctx.fetch_message(self.message_id)
        await self.update_message(react_message)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def removejoinchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """ Sets a channel to be not joinable with UQCSbot. """
        db_session = self.bot.create_db_session()
        try:
            existing = db_session.query(Channel).filter(Channel.id == channel.id).one()
            existing.joinable = False
        except NoResultFound:
            await ctx.send(f"There was no record for {channel.mention}. The channel is not currently joinable.")
            return
        db_session.commit()
        db_session.close()

        await ctx.send(f"{channel.mention} was removed as a joinable channel.")
        react_message = await ctx.fetch_message(self.message_id)
        await self.update_message(react_message)

    @commands.command(hidden=True)
    @commands.has_permissions(manage_channels=True)
    async def setmessageid(self, ctx: commands.Context, message_id):
        """ Changes the id of the react-joins message. """
        db_session = self.bot.create_db_session()
        query = db_session.query(Message).filter(Message.type == "react_message")
        if query.first():
            query.update({"id": message_id})
        else:
            db_session.add(Message(id=message_id, type="react_message"))
        db_session.commit()
        db_session.close()

        self.message_id = self._get_message_id()
        react_message = await ctx.fetch_message(self.message_id)
        await self.update_message(react_message)

    @addjoinchannel.error
    @removejoinchannel.error
    async def channel_manage_error(self, ctx: commands.context, error):
        """ Error handler for channel management commands. """
        if isinstance(error, commands.ChannelNotFound):
            await ctx.send("That channel was not found, make sure the channel exists.")
        else:
            logging.warning(error)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """ Toggle adding/removing member from the corresponding channel. """
        if payload.message_id == self.message_id:
            guild = self.bot.get_guild(SERVER_ID)
            member = guild.get_member(payload.user_id)

            # Remove the reaction if not a bot.
            channel = self.bot.get_channel(payload.channel_id)
            msg = await channel.fetch_message(payload.message_id)
            if member.bot:
                return
            await msg.remove_reaction(payload.emoji, member)
                
            # Covert to the correct format for custom emojis.
            emoji_name = f"<:{payload.emoji.name}:{payload.emoji.id}>" if payload.emoji.id else payload.emoji.name

            db_session = self.bot.create_db_session()
            channel_query = db_session.query(Channel).filter(Channel.joinable == True, 
                                                             Channel.emoji == emoji_name).one_or_none()
            db_session.close()

            if channel_query == None:
                await member.send(f"Unable to find that channel.")
                return

            channel = self.bot.get_channel(channel_query.id)

            if channel == None:
                await member.send(f"Unable to find that channel.")
                return

            # Leave the channel if the user is currently a member.
            if channel.permissions_for(member).is_superset(JOINED_PERMISSIONS):
                await channel.set_permissions(member, read_messages=False, reason="UQCSbot removed.")
                await member.send(f"You've left {channel.mention}")
                return

            # Otherwise, join the channel.
            await channel.set_permissions(member, read_messages=True, reason="UQCSbot added.")
            await member.send(f"You've joined {channel.mention}")

    async def update_message(self, react_message: discord.Message):
        """ Updates react-joins message. """
        db_session = self.bot.create_db_session()
        channel_query = db_session.query(Channel).filter(Channel.joinable == True).order_by(Channel.name)
        db_session.close()
        message = "**Channel Menu:**\nReact to join these channels.\n\n"

        for channel in channel_query:
            message += f"{channel.emoji} : ``{channel.name}``\n\n"
        await react_message.edit(content=message)
        
        await react_message.clear_reactions()
        for channel in channel_query:
            await react_message.add_reaction(channel.emoji)

def setup(bot: commands.Bot):
    bot.add_cog(Channels(bot))
