import discord
from discord import app_commands
from discord.ext import commands


class Basic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Sets the status for the bot"""
        # TODO: This can be removed once the presence has a better home.
        await self.bot.change_presence(
            activity=discord.Streaming(
                name="UQCS Live Stream",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=43s",
                platform="YouTube",
            )
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Member join listener"""
        if (channel := member.guild.system_channel) is None:
            return
        # On user joining, a system join message will appear in the system channel
        # This should prevent the bot waving on a user message when #general is busy
        async for msg in channel.history(limit=5):
            # Wave only on new member system message
            if msg.type == discord.MessageType.new_member:
                await msg.add_reaction("👋")
                break

    @app_commands.command()
    async def smoko(self, interaction: discord.Interaction):
        """For when you just need a break."""
        await interaction.response.send_message(
            "https://www.youtube.com/watch?v=j58V2vC9EPc"
        )

    @app_commands.command()
    async def conduct(self, interaction: discord.Interaction):
        """Returns the URL for the UQCS Code of Conduct."""
        await interaction.response.send_message(
            "UQCS Code of Conduct: https://uqcs.org/code-of-conduct"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Basic(bot))
