from discord.ext import commands
import discord

class Basic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # TODO: This can be removed once the presence has a better home.
        await self.bot.change_presence(activity=discord.Streaming(name="UQCS Live Stream", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=43s", platform="YouTube"))

    @commands.command()
    async def echo(self, ctx: commands.Context, *, text=""):
        """ Echos back the text that you send. """
        if text == "":
            await ctx.send("ECHO!")
        else:
            await ctx.send(text)

def setup(bot: commands.Bot):
    bot.add_cog(Basic(bot))
