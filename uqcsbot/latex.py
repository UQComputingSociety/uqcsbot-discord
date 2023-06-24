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
        # since bot prohibits empty prompts, checking len==0 seems redundant

        await interaction.response.defer(thinking=True)

        url = f"https://latex.codecogs.com/png.image?%5Cdpi%7B200%7D%5Cbg%7B36393f%7D%5Cfg%7Bwhite%7D{quote(input)}"
        embed = (discord.Embed(
                colour = discord.Colour.blue(),
                title=f"Latex render for \"{input}\"",
            ).set_image(url=f"{url}")
        )

        await interaction.edit_original_response(
            embed=embed
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Latex(bot))
