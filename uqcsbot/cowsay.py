from random import choice

from typing import List, NamedTuple, Optional, Union, Literal

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.bot import UQCSBot


class Cowsay(commands.Cog):

    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self._max_length = 40

    @app_commands.command()
    @app_commands.describe(
        message="The message that the cow will say",
        mood="The mood of the cow (optional)",
        tongue="Whether the cow should show its tongue (optional, default to False)",
        tux="Display the Linux Tux instead of the cow (optional, default to False)",
    )
    async def cowsay(self, interaction: discord.Interaction, 
            message: str, 
            mood: Optional[Literal['Borg', 'Dead', 'Greed', 'Paranoid', 'Stoned', 'Tired', 'Wired', 'Youthful']], 
            tongue: Optional[bool] = False,
            tux: Optional[bool] = False) -> None:
        """
        Returns a cow saying the given message.
        """
        await interaction.response.send_message(f"```{self.construct_say_bubble(message)}```")

    def word_wrap(self, message: str) -> List[str]:
        """
        Word wraps the given message to a max length of 40 characters.
        """
        lines = []
        line = ""
        for word in message.split():
            if len(line) + len(word) > self._max_length:
                lines.append(line.rstrip())
                line = ""
            line += word + " "
        lines.append(line.rstrip())
        return lines

    def construct_say_bubble(self, message: str):
        """
        Constructs a speech bubble around the given message.
        """
        
        # Word wrap the message to max width.
        lines = self.word_wrap(message)

        # Get longest line
        bubble_length = max([len(line) for line in lines])

        # Build the body of the speech bubble.
        bubble_body = ""
        if len(lines) == 1:
            bubble_body += f"< {lines[0]} >\n"
        else:
            bubble_body += f"/ {lines[0].ljust(bubble_length)} \\\n"
            for line in lines[1:-1]:
                bubble_body += f"| {line.ljust(bubble_length)} |\n"
            bubble_body += f"\\ {lines[-1].ljust(bubble_length)} /\n"
        
        # Construct the speech bubble.
        bubble = f" _{bubble_length * '_'}_ \n"
        bubble += bubble_body
        bubble += f" -{bubble_length * '-'}- \n"

        return bubble


async def setup(bot: UQCSBot):
    cog = Cowsay(bot)
    await bot.add_cog(cog)
