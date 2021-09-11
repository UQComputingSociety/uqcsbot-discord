import logging

import discord
from discord.ext import commands
from sqlalchemy.exc import NoResultFound

from uqcsbot.bot import UQCSBot
from uqcsbot.models import Channel

JOINED_PERMISSIONS = discord.Permissions(read_messages=True)
SERVER_ID = 813324385179271168
# Testing Server
# SERVER_ID = 836589565237264415

class Channels(commands.Cog):

    def __init__(self, bot: UQCSBot):
        self.bot = bot

    def _channel_query(self, channel: str):
        db_session = self.bot.create_db_session()
        channel_query = db_session.query(Channel).filter(Channel.name == channel,
                                                         Channel.joinable == True).one_or_none()
        db_session.close()

        return channel_query

    @commands.command()
    async def joinchannel(self, ctx: commands.Context, channel: str):
        """ Joins the channel that you specify. """
        channel_query = self._channel_query(channel)

        if channel_query == None:
            await ctx.send("Unable to join that channel.")
            return

        channel = self.bot.get_channel(channel_query.id)
        guild = self.bot.get_guild(SERVER_ID)
        member = guild.get_member(ctx.author.id)

        if channel == None:
            await ctx.send("Unable to join that channel.")
            return 

        # Don't let a user join the channel again if they are already in it.
        if channel.permissions_for(member).is_superset(JOINED_PERMISSIONS):
            await ctx.send("You're already a member of that channel.")
            return

        await channel.set_permissions(member, read_messages=True, reason="UQCSbot added.")
        join_message = await channel.send(f"{member.display_name} joined {channel.mention}")
        await join_message.add_reaction("👋")
        await ctx.send(f"You've joined {channel.mention}")

    @commands.command()
    async def joinchannels(self, ctx: commands.Context, channels: str):
        """ Joins the list of channels that you specify. """
        for channel in channels.split(" "):
            await self.joinchannel(self, ctx, channel)

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

        header_message = "Here is a list of the joinable channels"
        channel_list = "\n".join(channel.name for channel in channels_query)
        footer_messge = "To join or leave one of these channels, use the !joinchannel and !leavechannel commands."

        message = discord.Embed()
        message.title = "Joinable Channels"
        message.description = channel_list
        message.set_footer(text=footer_messge)

        await ctx.send(embed=message)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def addjoinchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """ Sets a channel to be joinable with UQCSbot. """
        db_session = self.bot.create_db_session()
 
        existing = db_session.query(Channel).filter(Channel.id == channel.id).one_or_none()
        if existing:
            existing.joinable = True
        else:
            db_session.add(Channel(id=channel.id, name=channel.name, joinable=True))

        db_session.commit()
        db_session.close()
        await ctx.send(f"{channel.mention} was added as a joinable channel.") 

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

    @addjoinchannel.error
    @removejoinchannel.error
    async def channel_manage_error(self, ctx: commands.context, error):
        """ Error handler for channel management commands. """
        if isinstance(error, commands.ChannelNotFound):
            await ctx.send("That channel was not found, make sure the channel exists.")
        else:
            logging.warning(error)

def setup(bot: commands.Bot):
    bot.add_cog(Channels(bot))
