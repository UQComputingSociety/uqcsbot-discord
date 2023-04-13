import discord
from discord import app_commands
from discord.ext import commands


class VoteyThumbs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voteythumbs_menu = app_commands.ContextMenu(
            name="Votey Thumbs",
            callback=self.voteythumbs_context,
        )
        self.bot.tree.add_command(self.voteythumbs_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(
            self.voteythumbs_menu.name, type=self.voteythumbs_menu.type
        )

    async def common_react(self, message: discord.Message):
        """Reactions for voteythumbs"""
        await message.add_reaction("👍")
        await message.add_reaction("👎")

        # thumbsright is a custom server emoji, get the Discord emoji string for it.
        thumbsright = discord.utils.get(self.bot.emojis, name="thumbsright")
        await message.add_reaction(str(thumbsright))

    async def voteythumbs_context(
        self, interaction: discord.Interaction, message: discord.Message
    ):
        """Starts a 👍 👎 vote."""
        await self.common_react(message)
        await interaction.response.send_message("Vote away!", ephemeral=True)

    @app_commands.command(name="voteythumbs")
    @app_commands.describe(question="The question that shall be voted upon")
    async def voteythumbs_command(
        self, interaction: discord.Interaction, question: str
    ):
        """Starts a 👍 👎 vote."""
        await interaction.response.send_message(question)
        message = await interaction.original_response()

        await self.common_react(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(VoteyThumbs(bot))
