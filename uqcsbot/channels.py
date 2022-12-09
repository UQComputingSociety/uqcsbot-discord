import logging
from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands
from emoji import UNICODE_EMOJI_ENGLISH
from sqlalchemy.exc import NoResultFound

from uqcsbot.bot import UQCSBot
from uqcsbot.models import Channel, Message

JOINED_PERMISSIONS = discord.Permissions(read_messages=True)

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

    def _update_channel_name_cache(self):
        """ Updates the channel name cache. """
        db_session = self.bot.create_db_session()
        all_channel_query = db_session.query(Channel).filter(Channel.joinable == True).order_by(Channel.name)
        db_session.close()

        self.channel_names = [channel.name for channel in all_channel_query]
        print(self.channel_names)

    @commands.Cog.listener()
    async def on_ready(self):
        self._update_channel_name_cache()
        try: 
            self.message_id = self._get_message_id()
        except:
            logging.warning("Channel react message not found.")
        

    channel_group = app_commands.Group(name="channel", description="Commands for joining and leaving channels")

    @channel_group.command(name="join")
    @app_commands.describe(channel="Channel you would like to join")
    async def join_command(self, interaction: discord.Interaction, channel: str):
        """ Joins the channel (or channels) that you specify. """
        channel_query = self._channel_query(channel)

        if channel_query == None:
            await interaction.response.send_message(f"Unable to join {channel}.", ephemeral=True)
            return

        channel = self.bot.get_channel(channel_query.id)
        guild = self.bot.uqcs_server
        member = guild.get_member(interaction.user.id)

        if channel == None:
            await interaction.response.send_message(f"Unable to join {channel}.", ephemeral=True)
            return

        # Don't let a user join the channel again if they are already in it.
        if channel.permissions_for(member).is_superset(JOINED_PERMISSIONS):
            await interaction.response.send_message(f"You're already a member of {channel}.", ephemeral=True)
            return

        await channel.set_permissions(member, read_messages=True, reason="UQCSbot added.")
        join_message = await channel.send(f"{member.display_name} joined {channel.mention}")
        await join_message.add_reaction("👋")
        await interaction.response.send_message(f"You've joined {channel.mention}.", ephemeral=True)

    @channel_group.command(name="leave")
    @app_commands.describe(channel="Channel you would like to leave. Defaults to current")
    async def leave_command(self, interaction: discord.Interaction, channel: Optional[str]):
        """ Leaves the channel that you specify. """
        
        # If a channel is not specified, attempt to leave the current channel.
        if (channel == None):
            channel = interaction.channel.name

        channel_query = self._channel_query(channel)

        if channel_query == None:
            await interaction.response.send_message("Unable to leave that channel.", ephemeral=True)
            return

        channel = self.bot.get_channel(channel_query.id)
        guild = self.bot.uqcs_server
        member = guild.get_member(interaction.user.id)

        # You can't leave a channel that doesn't exist or you're not in.
        if channel == None or channel.permissions_for(member).is_strict_subset(JOINED_PERMISSIONS):
            await interaction.response.send_message("Unable to leave that channel.", ephemeral=True)
            return

        await channel.set_permissions(member, read_messages=False, reason="UQCSbot removed.")
        await interaction.response.send_message(f"You've left {channel.mention}", ephemeral=True)

    @channel_group.command(name="list")
    async def list_command(self, interaction: discord.Interaction):
        """ Lists the channels that you can join. """

        channel_list = "\n".join(channel for channel in self.channel_names)
        footer_messge = ("To join or leave one of these channels, use the /channel join and /channel leave commands.")

        message = discord.Embed()
        message.title = "Joinable Channels"
        message.description = channel_list
        message.set_footer(text=footer_messge)

        await interaction.response.send_message(embed=message)

    @channel_group.command(name="addjoinable")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(channelname="Channel to add as addable", emoji="Emoji to associate with channel")
    async def addjoinable_command(self, interaction: discord.Interaction, channelname: str, emoji: str):
        """ Sets a channel to be joinable with UQCSbot. """
        if not self._valid_emoji(emoji):
            await interaction.response.send_message("Please select an emoji found within this server.")
            return

        channel = discord.utils.get(self.bot.uqcs_server.channels, name=channelname)
    
        db_session = self.bot.create_db_session()
        taken = db_session.query(Channel).filter(Channel.id != channel.id,
                                                 Channel.emoji == emoji).first()  
        if taken:
            db_session.close()
            await interaction.response.send_message("Please select an emoji that isn't already in use.") 
            return

        existing = db_session.query(Channel).filter(Channel.id == channel.id).one_or_none()
        if existing:
            existing.joinable = True
            existing.emoji = emoji
        else:
            db_session.add(Channel(id=channel.id, name=channel.name, joinable=True, emoji=emoji))
        db_session.commit()
        db_session.close()

        self._update_channel_name_cache()

        await interaction.response.send_message(f"{channel.mention} was added as a joinable channel.")

        # TODO: This needs a rework due to no context
        # self.message_id = self._get_message_id()
        # react_message = await ctx.fetch_message(self.message_id)
        # await self.update_message(react_message)

    @channel_group.command(name="removejoinable")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(channelname="Channel to remove as joinable")
    async def removejoin_command(self, interaction: discord.Interaction, channelname: str):
        """ Sets a channel to be not joinable with UQCSbot. """
        channel = discord.utils.get(self.bot.uqcs_server.channels, name=channelname)
    
        db_session = self.bot.create_db_session()
        try:
            existing = db_session.query(Channel).filter(Channel.id == channel.id).one()
            existing.joinable = False
        except NoResultFound:
            await interaction.response.send_message(f"There was no record for {channel.mention}. The channel is not currently joinable.")
            return
        db_session.commit()
        db_session.close()

        self._update_channel_name_cache()

        await interaction.response.send_message(f"{channel.mention} was removed as a joinable channel.")

        # TODO: This needs a rework due to no context
        # self.message_id = self._get_message_id()
        # react_message = await ctx.fetch_message(self.message_id)
        # await self.update_message(react_message)

    @channel_group.command(name="setmessageid")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(message_id="ID of message to react to")
    async def setmessageid_command(self, interaction: discord.Interaction, message_id: int):
        """ Changes which message is used for react-joins given a new message id. """
        db_session = self.bot.create_db_session()
        query = db_session.query(Message).filter(Message.type == "react_message")
        if query.first():
            query.update({"id": message_id})
        else:
            db_session.add(Message(id=message_id, type="react_message"))
        db_session.commit()
        db_session.close()

        # TODO: This needs a rework due to no context
        # self.message_id = self._get_message_id()
        # react_message = await ctx.fetch_message(self.message_id)
        # await self.update_message(react_message)

    @join_command.autocomplete("channel")
    @leave_command.autocomplete("channel")
    @removejoin_command.autocomplete("channelname")
    async def channel_command_autocomplete(
        self,
        interaction: discord.Interaction, 
        current: str
    ) -> List[app_commands.Choice[str]]:
        """ Autocomplete handler for join command """
        return [ 
            app_commands.Choice(name=name, value=name) 
            for name in self.channel_names if current.lower() in name
        ]

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """ Toggle adding/removing member from the corresponding channel. """
        if payload.message_id == self.message_id:
            guild = self.bot.uqcs_server
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

async def setup(bot: commands.Bot):
    await bot.add_cog(Channels(bot))
