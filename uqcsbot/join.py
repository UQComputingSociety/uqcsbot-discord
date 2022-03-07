import discord
from discord.ext import commands

from uqcsbot.bot import UQCSBot
from uqcsbot.models import Channel

JOINED_PERMISSIONS = discord.Permissions(read_messages=True)
SERVER_ID = 813324385179271168
# Testing Server
# SERVER_ID = 836589565237264415

EMOJIS = {"academic-advice": "📖", "adulting": "🧑", "banter": "💬", "bot-testing" : "🤖",
                "contests" : "⚔️", "covid" : "⚛️", "creative" : "🎨", "events" : "🗓️", "food" : "🍔",
                "games" : "🎮", "general" : "⚪", "hackathons" : "🍕", "hardware" : "💻", "jobs-bulletin" : "📌",
                "jobs-discussion" : "🔈", "lgbtqia" : "🏳️‍🌈", "media" : "📺", "memes" : "🎭", "politics" : "📮",
                "projects" : "🔨", "uqic-sport" : "🏅", "yelling" : "🗣️"}

class Join(commands.Cog):

    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self.message_id = None

    def _channel_query(self, channel: str):
        db_session = self.bot.create_db_session()
        channel_query = db_session.query(Channel).filter(Channel.name == channel,
                                                         Channel.joinable == True).one_or_none()
        db_session.close()
        return channel_query

    def get_key(self, map, value):
        for k, v in map.items():
            if v == value:
                return k
        return None

    def get_channel_map(self):
        db_session = self.bot.create_db_session()
        channel_query = db_session.query(Channel).filter(Channel.joinable == True).order_by(Channel.name)
        db_session.close()

        channel_emojis = {}
        for channel in channel_query:
            if channel.name in EMOJIS:
                channel_emojis[channel.name] = EMOJIS[channel.name]
        return channel_emojis

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """ Toggle adding/removing member from the corresponding channel. """
        if payload.message_id == self.message_id:
            channels = self.get_channel_map()
            guild = self.bot.get_guild(SERVER_ID)
            member = guild.get_member(payload.user_id)

            # Remove reaction if not a bot
            channel = self.bot.get_channel(payload.channel_id)
            msg = await channel.fetch_message(payload.message_id)
            if not member.bot:
                await msg.remove_reaction(payload.emoji, member)

            channel_name = self.get_key(channels, payload.emoji.name)
            channel_query = self._channel_query(channel_name)

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

    @commands.command(hidden=True)
    @commands.has_permissions(manage_channels=True)
    async def joinmessage(self, ctx: commands.Context):
        """ Create message to react to. """
        channels = self.get_channel_map()
        channel_list = list(channels.items())
        message = "**Channel Menu:**\nReact to join these channels.\n\n"

        for name, emoji in channel_list:
            message += f"{emoji} : ``{name}``\n\n"
        react_message = await ctx.send(message)
        self.message_id = react_message.id

        for emoji in channels.values():
            await react_message.add_reaction(emoji=emoji)

def setup(bot: commands.Bot):
    bot.add_cog(Join(bot))
    