import discord
from discord import app_commands
from discord.ext import commands

from typing import Any

# The unicode points for each number emoji starting from 0 to 10
EMOJI_NUMBERS = [
    "\u0030\u20E3",
    "\u0031\u20E3",
    "\u0032\u20E3",
    "\u0033\u20E3",
    "\u0034\u20E3",
    "\u0035\u20E3",
    "\u0036\u20E3",
    "\u0037\u20E3",
    "\u0038\u20E3",
    "\u0039\u20E3",
    "\U0001F51F",
]


class PollMenu(discord.ui.Modal, title="New Poll"):
    """The menu to create a new poll"""

    poll_question: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="A question of the poll",
        placeholder="Your question goes here (e.g. What does UQCS stand for?)",
        max_length=100,
    )
    poll_options: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="The options for the poll (one per line)",
        style=discord.TextStyle.long,
        placeholder="Option 1 (e.g. UQ Computing Society)\nOption 2 (e.g. UQ Caveman Society)\nOption 3...",
        max_length=3000,
    )

    async def on_submit(self, interaction: discord.Interaction):
        options = [option.strip() for option in self.poll_options.value.split("\n")]
        options = [option for option in options if option != ""]
        if len(options) < 2:
            await interaction.response.send_message(
                "Not enough options. Make sure each option is on a new line.",
                ephemeral=True,
            )
            return
        if len(options) > 10:
            await interaction.response.send_message(
                "Too many options. You can have at most 10 options.", ephemeral=True
            )
            return
        if any(len(option) > 75 for option in options):
            await interaction.response.send_message(
                "Your options are too long. Each option must be less than 75 characters.",
                ephemeral=True,
            )
            return

        options_string = "\n".join(
            f"{EMOJI_NUMBERS[number]}: {option}"
            for number, option in enumerate(options, start=1)
        )
        await interaction.response.send_message(
            content=f"{self.poll_question}\n{options_string}"
        )
        message = await interaction.original_response()
        print(message)
        for i, _ in enumerate(options, start=1):
            await message.add_reaction(EMOJI_NUMBERS[i])


class Poll(commands.Cog):
    @app_commands.command(
        name="poll",
        description="Create a poll with multiple options. Run the command for the set-up wizard.",
    )
    async def start_poll_menu(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PollMenu())


async def setup(bot: commands.Bot):
    await bot.add_cog(Poll(bot))
