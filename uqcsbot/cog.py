from discord.ext import commands

from uqcsbot.bot import UQCSBot


class UQCSBotCog(commands.Cog):
    def __init__(self, bot: UQCSBot):
        self.bot = bot
