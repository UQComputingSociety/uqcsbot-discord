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

        #ansi colour codes
        pink = "\u001b[0;35m"
        red = "\u001b[0;31m"
        yellow = "\u001b[0;33m"
        green = "\u001b[0;32m"
        cyan = "\u001b[0;36m"
        blue = "\u001b[0;34m"

        cat = "\n".join(("```ansi",
                    f"{pink}       {red}  __..--{yellow}''``\\-{green}-....___{cyan}   _..,_{blue}            ",
                    f"{pink}     _.{red}-'    .-{yellow}/\";  `{green}        {cyan}``<._  `{blue}`-+'~=.     ",
                    f"{pink} _.-' _{red}..--.'_ {yellow}   \\  {green}        {cyan}        {blue}  `(^) )    ",
                    f"{pink}((..-' {red}   (< _ {yellow}    ;_.{green}.__     {cyan}        {blue}  ; `'   fL",
                    f"{pink}       {red}    `-._{yellow},_)'   {green}   ``--.{cyan}..____..{blue}-'         ```"))
        await interaction.response.send_message(cat)

async def setup(bot: commands.Bot):
    await bot.add_cog(Cat(bot))