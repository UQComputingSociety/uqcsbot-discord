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

        url = f"https://latex.codecogs.com/png.image?%5Cdpi%7B200%7D%5Cbg%7B36393f%7D%5Cfg%7Bwhite%7D{quote(input)}"

        await interaction.response.send_message(
            f"LaTeX render for \"{input}\"\n{url}",
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Latex(bot))

