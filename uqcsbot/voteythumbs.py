import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.yelling import yelling_exemptor


class EmoteNotFoundError(Exception):
    def __init__(self, emote: str, *args: object) -> None:
        self.emote = emote
        super().__init__(*args)


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

    async def common_react(
        self,
        message: discord.Message,
        up_reaction: str = "👍",
        down_reaction: str = "👎",
        middle_reaction: str = "thumbsright",
    ):
        """Reactions for voteythumbs"""

        if len(up_reaction) > 1:
            up_emoji = discord.utils.get(self.bot.emojis, name=up_reaction)
            if not up_emoji:
                raise EmoteNotFoundError(up_reaction)
            up_reaction = str(up_emoji)

        if len(down_reaction) > 1:
            down_emoji = discord.utils.get(self.bot.emojis, name=down_reaction)
            if not down_emoji:
                raise EmoteNotFoundError(down_reaction)
            down_reaction = str(down_emoji)

        if len(middle_reaction) > 1:
            middle_emoji = discord.utils.get(self.bot.emojis, name=middle_reaction)
            if not middle_emoji:
                raise EmoteNotFoundError(middle_reaction)
            middle_reaction = str(middle_emoji)

        await message.add_reaction(up_reaction)
        await message.add_reaction(down_reaction)
        await message.add_reaction(middle_reaction)

    async def voteythumbs_context(
        self, interaction: discord.Interaction, message: discord.Message
    ):
        """Starts a 👍 👎 vote."""
        await interaction.response.defer(ephemeral=True)

        try:
            await self.common_react(message)
        except EmoteNotFoundError:
            await interaction.edit_original_response(
                content="The emotes for this vote don't seem to be available."
            )
            return
        await interaction.edit_original_response(content="Vote away!")

    @app_commands.command(name="voteythumbs")
    @app_commands.describe(question="The question that shall be voted upon")
    @yelling_exemptor(input_args=["question"])
    async def voteythumbs_command(
        self, interaction: discord.Interaction, question: str
    ):
        """Starts a 👍 👎 vote."""
        await interaction.response.defer()
        message = await interaction.original_response()

        try:
            await self.common_react(message)
        except EmoteNotFoundError:
            await interaction.edit_original_response(
                content="The emotes for this vote don't seem to be available."
            )
            return

        await interaction.edit_original_response(content=question)

    @app_commands.command(name="voteyrachels")
    @app_commands.describe(question="The question that shall be voted upon")
    async def voteyrachels_command(
        self, interaction: discord.Interaction, question: str
    ):
        """Starts a vote with Rachel faces."""
        await interaction.response.defer()
        message = await interaction.original_response()

        try:
            await self.common_react(
                message,
                up_reaction="presidentialpoggers",
                down_reaction="no",
                middle_reaction="lmao",
            )
        except EmoteNotFoundError:
            await interaction.edit_original_response(
                content="The emotes for this vote don't seem to be available."
            )
            return

        await interaction.edit_original_response(content=question)

    @app_commands.command(name="voteytoms")
    @app_commands.describe(question="The question that shall be voted upon")
    async def voteytoms_command(self, interaction: discord.Interaction, question: str):
        """Starts a vote with Tom faces."""
        await interaction.response.defer()
        message = await interaction.original_response()

        try:
            await self.common_react(
                message,
                up_reaction="expresident2",
                down_reaction="expresident",
                middle_reaction="big_if_true",
            )
        except EmoteNotFoundError:
            await interaction.edit_original_response(
                content="The emotes for this vote don't seem to be available."
            )
            return

        await interaction.edit_original_response(content=question)

    @app_commands.command(name="voteyjimmys")
    @app_commands.describe(question="The question that shall be voted upon")
    async def voteyjimmys_command(
        self, interaction: discord.Interaction, question: str
    ):
        """Starts a vote with Jimmy faces."""
        await interaction.response.defer()
        message = await interaction.original_response()

        try:
            await self.common_react(
                message,
                up_reaction="jimmytree",
                down_reaction="no",
                middle_reaction="ghostJimmy",
            )
        except EmoteNotFoundError:
            await interaction.edit_original_response(
                content="The emotes for this vote don't seem to be available."
            )
            return

        await interaction.edit_original_response(content=question)


async def setup(bot: commands.Bot):
    await bot.add_cog(VoteyThumbs(bot))
