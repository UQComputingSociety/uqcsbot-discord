import discord
from discord.ext import commands

class Channels(commands.Cog):
    # TODO: Move this to a database instead
    JOINABLE_CHANNELS = {
        "adulting": 836249085383671848,
        # different id for testing server
        # "adulting": 851113475127640114, 
        "blockchain": 836243744441237544,
        "covid": 836246942958092318,
        "food": 836244105947906048  
    }
    JOINED_PERMISSIONS = discord.Permissions(read_messages=True)

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def joinchannel(self, ctx: commands.Context, channel: str):
        """ Joins the channel that you specify. """
        
        channel_id = self.JOINABLE_CHANNELS.get(channel)
        channel = self.bot.get_channel(channel_id)

        if channel == None:
            await ctx.send("Unable to join that channel.")
            return 

        # Don't let a user join the channel again if they are already in it.
        if channel.permissions_for(ctx.author).is_superset(self.JOINED_PERMISSIONS):
            await ctx.send("You're already a member of that channel.")
            return

        await channel.set_permissions(ctx.author, read_messages=True, reason="UQCSbot added.")
        join_message = await channel.send(f"{ctx.author.name} joined {channel.mention}")
        await join_message.add_reaction("👋")
        await ctx.send(f"You've joined {channel.mention}")

    @commands.command()
    async def leavechannel(self, ctx: commands.Context, channel: str):
        """ Leaves the channel that you specify. """
        channel_id = self.JOINABLE_CHANNELS.get(channel)
        channel = self.bot.get_channel(channel_id)

        # You can't leave a channel that doesn't exist or you're not in.
        if channel == None or channel.permissions_for(ctx.author).is_strict_subset(self.JOINED_PERMISSIONS): 
            await ctx.send("Unable to leave that channel.")
            return 

        await channel.set_permissions(ctx.author, overwrite=None, reason="UQCSbot removed.")
        leave_message = await channel.send(f"{ctx.author.name} left {channel.mention}")
        await leave_message.add_reaction("👋")
        await ctx.send(f"You've left {channel.mention}")

def setup(bot: commands.Bot):
    bot.add_cog(Channels(bot))
