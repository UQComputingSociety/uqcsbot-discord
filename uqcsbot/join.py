import logging

import discord
from discord.ext import commands

from uqcsbot.bot import UQCSBot
from uqcsbot.models import Channel

JOINED_PERMISSIONS = discord.Permissions(read_messages=True)
SERVER_ID = 946610592649728040

MESSAGE_ID = ""

EMOJIS = {"academic-advice": "🎓", "adulting": "😐", "banter": "😐", "bot-testing": "😐", "contests": "😐",
                "covid": "😐", "creative": "😐", "events": "😐", "food": "😐", "games": "😐", "general": "😐",
                "hackathon": "😐", "hardware": "😐", "jobs-bulletin": "😐", "jobs-discussion": "😐", 
                "lgbtqia": "😐", "memes": "😐", "politics": "😐", "projects": "😐", "yelling": "😐"}

prefix = "-"
intents = discord.Intents.all()
bc = commands.Bot(command_prefix=prefix, intents=intents)

class Join(commands.Cog):

    def __init__(self, bot: UQCSBot):
        self.bot = bot

    def _channel_query(self, channel: str):
        db_session = self.bot.create_db_session()
        channel_query = db_session.query(Channel).filter(Channel.name == channel).one_or_none()
        db_session.close()
        return channel_query

    def get_key(map, value):
        for k, v in map.items():
            if v == value:
                return k
        return None

    def get_channel_map(self):
        db_session = self.bot.create_db_session()
        channel_query = db_session.query(Channel).order_by(Channel.name)
        db_session.close()

        channel_emojis = {}
        for channel in channel_query:
            channel_emojis[channel] = EMOJIS[channel] if channel in EMOJIS else "❓"
        return channel_emojis

    @bc.event
    async def on_raw_reaction_add(self, payload):
        """ Add member to the corresponding channel. """
        guild = self.bot.get_guild(SERVER_ID)
        channels = self.get_channel_map()
        member = guild.get_member(payload.user_id)

        if payload.emoji.name in channels.values() and payload.message_id == MESSAGE_ID:
            channel = self.get_key(channels, payload.emoji.name)
            channel_query = self._channel_query(channel)

            if channel_query == None:
                await member.send(f"Unable to join {channel}.")
                return

            channel = self.bot.get_channel(channel_query.id)

            if channel == None:
                await member.send(f"Unable to join {channel}.")
                return

            # Don't let a user join the channel again if they are already in it.
            if channel.permissions_for(member).is_superset(JOINED_PERMISSIONS):
                await member.send(f"You're already a member of {channel}.")
                return

            await channel.set_permissions(member, read_messages=True, reason="UQCSbot added.")
            await member.send(f"You've joined {channel.mention}.")
    
    @bc.event
    async def on_raw_reaction_remove(self, payload):
        """ Remove member from the corresponding channel. """
        guild = self.bot.get_guild(SERVER_ID)
        channels = self.get_channel_map()
        member = guild.get_member(payload.user_id)
        
        if payload.emoji.name in channels.values() and payload.message_id == MESSAGE_ID:
            channel = self.get_key(channels, payload.emoji.name)
            channel_query = self._channel_query(channel)

            if channel_query == None:
                await member.send(f"Unable to leave that channel.")
                return

            channel = self.bot.get_channel(channel_query.id)

            if channel == None:
                await member.send(f"Unable to join {channel}.")
                return

            # You can't leave a channel that doesn't exist or you're not in.
            if channel == None or channel.permissions_for(member).is_strict_subset(JOINED_PERMISSIONS):
                await member.send("Unable to leave that channel.")
                return

            await channel.set_permissions(member, read_messages=False, reason="UQCSbot removed.")
            await member.send(f"You've left {channel.mention}")

    @commands.command()
    async def join(self, ctx: commands.Context):
        """ Create a list of the channels available to join by reacting. """
        channels = self.get_channel_map()
        channel_list = list(channels.items())
        print(channel_list)
        channel_list = [" ".join(emoji, name) for name, emoji in channel_list]
        channel_list = "\n".join(channel_list)
        channel_list.append("Hello1")
               
        message = await ctx.send(channel_list)
        for emoji in channels.values(): await message.add_reaction(emoji=emoji)

    
def setup(bot: commands.Bot):
    bot.add_cog(Join(bot))