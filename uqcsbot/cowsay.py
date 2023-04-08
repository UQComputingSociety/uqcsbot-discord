
from typing import Optional, Literal

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.bot import UQCSBot

# Type Alias for Cow Eyes 
CowsayMoodType = Literal['Normal', 'Borg', 'Dead', 'Greed', 'Paranoid', 'Stoned', 'Tired', 'Wired', 'Youthful']

class Cowsay(commands.Cog):

    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self._max_length = 40
        self._cow_eyes = dict(
            Normal = 'oo',
            Borg = '==',
            Dead = 'xx',
            Greed = '$$',
            Paranoid = '@@',
            Stoned = '**',
            Tired = '--',
            Wired = 'OO',
            Youthful = '..'
        )

    @app_commands.command(name="cowsay")
    @app_commands.describe(
        message="The message that the cow will say",
        mood="The mood of the cow (optional)",
        tongue="Whether the cow should show its tongue (optional, default to False)",
        tux="Display the Linux Tux instead of the cow. Tux doesn't show tongue. (optional, default to False)",
    )
    async def cowsay_command(self, interaction: discord.Interaction, 
            message: str, 
            mood: Optional[CowsayMoodType] = 'Normal', 
            tongue: Optional[bool] = False,
            tux: Optional[bool] = False) -> None:
        """
        Returns a cow or tux saying the given message.
        """

        ascii_art = self.draw_cow(mood, tongue) if not tux else self.draw_tux(mood)
        await interaction.response.send_message(f"```{self.construct_say_bubble(message)}{ascii_art}```")

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

    def construct_say_bubble(self, message: str) -> str:
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

    def draw_cow(self, 
            mood: Optional[CowsayMoodType] = 'Normal', 
            tongue: Optional[bool] = False) -> str:

        """
        Returns cow ascii art with different eyes based on the mood and sticks
        out its tongue when requested.
        """

        # Set the tongue if the cow is dead or if the tongue is set to True.
        tongue = 'U' if tongue or mood == 'Dead' else ' '

        # Draw the cow.
        cow  = f"        \   ^__^\n"
        cow += f"         \  ({self._cow_eyes[mood]})\_______\n"
        cow += f"            (__)\       )\/\ \n"
        cow += f"             {tongue}  ||----w |\n"
        cow += f"                ||     ||\n"
        return cow

    def draw_tux(self,
            mood: Optional[Literal['Normal', 'Borg', 'Dead', 'Greed', 'Paranoid', 'Stoned', 'Tired', 'Wired', 'Youthful']] = 'Normal') -> str:
        
        """
        Returns tux ascii art with different eyes based on the mood.
        """

        # Get the tux eyes.
        cow_eyes = self._cow_eyes[mood]
        tux_eyes = f"{cow_eyes[0]}_{cow_eyes[1]}"

        # Draw the tux.
        tux  = f"   \ \n"
        tux += f"    \ \n"
        tux += f"        .--. \n"
        tux += f"       |{tux_eyes} | \n"
        tux += f"       |:_/ | \n"
        tux += f"      //   \ \ \n"
        tux += f"     (|     | ) \n"
        tux += f"    /'\_   _/`\ \n"
        tux += f"    \___)=(___/ \n"
        return tux

async def setup(bot: UQCSBot):
    cog = Cowsay(bot)
    await bot.add_cog(cog)
