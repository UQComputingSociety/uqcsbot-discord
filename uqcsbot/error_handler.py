from discord.ext import commands
from discord.ext.commands.errors import MissingRequiredArgument
import logging
from typing import Any
from uqcsbot.bot import UQCSBot

"""
TODO: this is bundled with advent.py and should be removed.
"""


class ErrorHandler(commands.Cog):
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context[UQCSBot], err: Any):
        if isinstance(err, MissingRequiredArgument):
            await ctx.send(
                "Missing required argument. For further information refer to `!help`"
            )

        logging.error(err)


async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorHandler(bot))
