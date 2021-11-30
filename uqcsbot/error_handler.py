from discord.ext import commands
from discord.ext.commands.errors import MissingRequiredArgument
import logging

class ErrorHandler(commands.Cog):
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, err):
        if isinstance(err, MissingRequiredArgument):
            await ctx.send("Missing required argument. For further information refer to `!help`")

        logging.error(err)

def setup(bot: commands.Bot):
    bot.add_cog(ErrorHandler(bot))
