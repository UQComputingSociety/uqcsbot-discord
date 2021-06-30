import discord
from discord.ext import commands

class VoteyThumbs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def voteythumbs(self, ctx: commands.Context):
        """ Starts a 👍 👎 vote. """
        
        await ctx.message.add_reaction("👍")
        await ctx.message.add_reaction("👎")

        # thumbsright is a custom server emoji, get the Discord emoji string for it.
        thumbsright = discord.utils.get(self.bot.emojis, name="thumbsright")
        await ctx.message.add_reaction(str(thumbsright))

def setup(bot: commands.Bot):
    bot.add_cog(VoteyThumbs(bot))

