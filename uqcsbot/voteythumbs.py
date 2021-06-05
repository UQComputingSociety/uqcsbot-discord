from discord.ext import commands

class VoteyThumbs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def voteythumbs(self, ctx: commands.Context):
        """ Echos back the text that you send. """
        # await ctx.send(text)
        await ctx.message.add_reaction("👍")
        await ctx.message.add_reaction("👎")

def setup(bot: commands.Bot):
    bot.add_cog(VoteyThumbs(bot))

