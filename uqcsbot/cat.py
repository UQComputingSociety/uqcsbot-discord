from random import randrange
from collections import deque

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

        # ansi colour codes
        pink = "\u001b[0;35m"
        red = "\u001b[0;31m"
        yellow = "\u001b[0;33m"
        green = "\u001b[0;32m"
        cyan = "\u001b[0;36m"
        blue = "\u001b[0;34m"

        order = deque([pink, red, yellow, green, cyan, blue])
        # randomly shifts starting colout
        shift = randrange(0, 5)
        for _ in range(shift):
            order.append(order.popleft())

        cat = "\n".join(
            (
                "```ansi",
                f"{order[0]}       {order[1]}  __..--{order[2]}''``\\-{order[3]}-....___{order[4]}   _..,_{order[5]}            ",
                f"{order[0]}     _.{order[1]}-'    .-{order[2]}/\";  `{order[3]}        {order[4]}``<._  `{order[5]}`-+'~=.     ",
                f"{order[0]} _.-' _{order[1]}..--.'_ {order[2]}   \\  {order[3]}        {order[4]}        {order[5]}  `(^) )    ",
                f"{order[0]}((..-' {order[1]}   (< _ {order[2]}    ;_.{order[3]}.__     {order[4]}        {order[5]}  ; `'   fL",
                f"{order[0]}       {order[1]}    `-._{order[2]},_)'   {order[3]}   ``--.{order[4]}..____..{order[5]}-'         ```",
            )
        )
        await interaction.response.send_message(cat)


async def setup(bot: commands.Bot):
    await bot.add_cog(Cat(bot))
