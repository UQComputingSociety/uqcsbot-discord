import discord
from discord.ext import commands

from uqcsbot.bot import UQCSBot


class Intros(commands.Cog):
    CHANNEL_NAME = "intros"

    def __init__(self, bot: UQCSBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if (
            not self.bot.user
            or not isinstance(msg.channel, discord.TextChannel)
            or msg.author.id == self.bot.user.id
            or msg.channel.name != self.CHANNEL_NAME
        ):
            return

        await msg.add_reaction("👋")


async def setup(bot: commands.Bot):
    await bot.add_cog(Intros(bot))
