from urllib.parse import quote

import discord
from discord import app_commands
from discord.ext import commands


class Latex(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(description="Renders the given LaTeX")
    @app_commands.describe(input="LaTeX to render")
    async def latex(self, interaction: discord.Interaction, input: str):
        if len(input) == 0:
            return

        url = f"http://latex.codecogs.com/gif.latex?\\bg_white&space;{quote(input)}"

        await interaction.response.send_message(
            f"LaTeX render for \"{input}\"\n{url}",
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Latex(bot))

