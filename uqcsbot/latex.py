import discord
from discord.ext import commands
from urllib.parse import quote

class Latex(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @classmethod
    async def _handle_latex_internal(cls, ctx: commands.Context, data):
        url = f"https://latex.codecogs.com/png.image?%5Cdpi%7B200%7D%5Cbg%7B36393f%7D%5Cfg%7Bwhite%7D{quote(data)}"

        await ctx.send(
            f"LaTeX render for \"{data}\"\n{url}",
        )

    @commands.command()
    async def latex(self, ctx: commands.Context, *args):
        if len(args) == 0:
            return

        await self._handle_latex_internal(ctx, " ".join(args))


def setup(bot: commands.Bot):
    bot.add_cog(Latex(bot))

