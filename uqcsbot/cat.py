import discord
from discord import app_commands
from discord.ext import commands

class Cat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command()
    async def cat(self, interaction: discord.Interaction):
        """
        Displays the moss cat. Brings torture to CSSE2310 students.
        """
        cat = "\n".join(("```",
                    "         __..--''``\\--....___   _..,_            ",
                    "     _.-'    .-/\";  `        ``<._  ``-+'~=.     ",
                    " _.-' _..--.'_    \\                    `(^) )    ",
                    "((..-'    (< _     ;_..__               ; `'   fL",
                    "           `-._,_)'      ``--...____..-'         ```"))
        await interaction.response.send_message(cat)

async def setup(bot: commands.Bot):
    await bot.add_cog(Cat(bot))