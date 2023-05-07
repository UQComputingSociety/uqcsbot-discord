from typing import Optional, Literal, List

import re

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.bot import UQCSBot

# Max length of the message to be displayed per line in the bubble.
CowsayWrapLength = 40

# Type Alias for Cow Eyes 
CowsayMoodType = Literal[
    "Normal",
    "Borg",
    "Dead",
    "Greed",
    "Paranoid",
    "Stoned",
    "Tired",
    "Wired",
    "Youthful",
]

# The cowsay eyes for each mood.
CowsayEyes = dict(
    Normal="oo",
    Borg="==",
    Dead="xx",
    Greed="$$",
    Paranoid="@@",
    Stoned="**",
    Tired="--",
    Wired="OO",
    Youthful="..",
)


class Cowsay(commands.Cog):
    def __init__(self, bot: UQCSBot):
        self.bot = bot

    @app_commands.command(name="cowsay")
    @app_commands.describe(
        message="The message that the cow will say (max 1000 chars)",
        mood="The mood of the cow (optional)",
        tongue="Whether the cow should show its tongue (optional, default to False)",
        tux="Display the Linux Tux instead of the cow. Tux doesn't show tongue. (optional, default to False)",
    )
    async def cowsay_command(
        self, 
        interaction: discord.Interaction, 
        message: str, 
        mood: Optional[CowsayMoodType] = "Normal", 
        tongue: Optional[bool] = False,
        tux: Optional[bool] = False
    ) -> None:
        """
        Returns a cow or tux saying the given message.
        """

        # Sanitise invalid characters from the message
        message = Cowsay.sanitise_illegals(message)

        # Sanitise message for discord emotes
        message = Cowsay.sanitise_emotes(message)

        # Check message length, if invalid send moo!
        if len(message) == 0 or len(message) > 1000:
            await interaction.response.send_message("moo?")
            return

        # Construct the ascii art + message
        ascii_art = self.draw_cow(mood, tongue) if not tux else self.draw_tux(mood)
        bubble = Cowsay.construct_bubble(message, CowsayWrapLength)

        # Format the response and check if it's too long
        response = f"```{bubble}{ascii_art}```"
        if len(response) > 2000:
            await interaction.response.send_message("moo!")
            return

        await interaction.response.send_message(response)
    
    @app_commands.command(name="cowthink")
    @app_commands.describe(
        message="The message that the cow will think (max 1000 chars)",
        mood="The mood of the cow (optional)",
        tongue="Whether the cow should show its tongue (optional, default to False)",
        tux="Display the Linux Tux instead of the cow. Tux doesn't show tongue. (optional, default to False)",
    )
    async def cowthink_command(
        self, 
        interaction: discord.Interaction, 
        message: str, 
        mood: Optional[CowsayMoodType] = "Normal", 
        tongue: Optional[bool] = False,
        tux: Optional[bool] = False
    ) -> None:
        """
        Returns a cow or tux thinking the given message.
        """

        # Sanitise invalid characters from the message
        message = Cowsay.sanitise_illegals(message)

        # Sanitise message for discord emotes
        message = Cowsay.sanitise_emotes(message)

        # Check message length, if invalid send moo!
        if len(message) == 0 or len(message) > 1000:
            await interaction.response.send_message("moo?")
            return

        # Construct the ascii art + message
        ascii_art = self.draw_cow(mood, tongue, True) if not tux else self.draw_tux(mood, True)
        bubble = Cowsay.construct_bubble(message, CowsayWrapLength, True)
        
        # Format the response and check if it's too long
        response = f"```{bubble}{ascii_art}```"
        if len(response) > 2000:
            await interaction.response.send_message("moo!")
            return

        await interaction.response.send_message(response)

    def draw_cow(
        self, 
        mood: Optional[CowsayMoodType] = "Normal", 
        tongue: Optional[bool] = False,
        thinking: bool = False
    ) -> str:
        """
        Returns cow ascii art with different eyes based on the mood and sticks
        out its tongue when requested.
        """

        # Set the tongue if the cow is dead or if the tongue is set to True.
        tongue = "U" if tongue or mood == "Dead" else " "

        # Set the bubble connection based on whether the cow is thinking or 
        # speaking.
        bubble_connect = "o" if thinking else "\\"

        # Double check the mood is valid, default to normal if not.
        if mood not in CowsayEyes:
            mood = "Normal"

        # Get the cow eyes.
        cow_eyes = CowsayEyes[mood]

        # Draw the cow.
        cow  = f"        {bubble_connect}   ^__^\n"
        cow += f"         {bubble_connect}  ({cow_eyes})\_______\n"
        cow += f"            (__)\       )\/\ \n"
        cow += f"             {tongue}  ||----w |\n"
        cow += f"                ||     ||\n"
        return cow

    def draw_tux(
        self,
        mood: Optional[CowsayMoodType] = "Normal",
        thinking: bool = False
    ) -> str:
        """
        Returns tux ascii art with different eyes based on the mood.
        """

        # Double check the mood is valid, default to normal if not.
        if mood not in CowsayEyes:
            mood = "Normal"

        # Get the tux eyes.
        cow_eyes = CowsayEyes[mood]
        tux_eyes = f"{cow_eyes[0]}_{cow_eyes[1]}"

        # Set the bubble connection based on whether the tux is thinking or 
        # speaking.
        bubble_connect = "o" if thinking else "\\"

        # Draw the tux.
        tux  = f"   {bubble_connect} \n"
        tux += f"    {bubble_connect} \n"
        tux += f"        .--. \n"
        tux += f"       |{tux_eyes} | \n"
        tux += f"       |:_/ | \n"
        tux += f"      //   \ \ \n"
        tux += f"     (|     | ) \n"
        tux += f"    /'\_   _/`\ \n"
        tux += f"    \___)=(___/ \n"
        return tux

    @staticmethod
    def sanitise_illegals(message: str) -> str:
        """
        Replaces all illegal characters in the message with their sanitised
        equivalent.
        """

        # Strip whitespace from either side of the message
        message = message.strip()

        # replace code blocks with their sanitised equivalent
        message = message.replace("```", "'''")
        
        return message

    @staticmethod
    def sanitise_emotes(message: str) -> str:
        """
        Replaces all emotes in the message with their emote name instead of
        their id.
        """

        # Regex to match emotes.
        emotes: List[str] = re.findall("<a?:\w+:\d+>", message)

        # Replace each emote with its name.
        for emote in emotes:
            emote_name: str = emote.split(":")[1].strip()
            message = message.replace(emote, f":{emote_name}:")
        
        return message

    @staticmethod
    def word_wrap(message: str, wrap: int) -> List[str]:
        """
        Word wraps the given message to a max length of 40 characters.
        """

        lines: List[str] = []
        line: str = ""
        words: List[str] = message.split()
        
        index: int = 0
        while index < len(words):
            word: str = words[index]
            index += 1

            # As requested by the audience, you can manually break lines by
            # adding "\n" anywhere in the message and it will be respected.
            if "\\n" in word:
                parts: str = word.split("\\n", 1)

                # The `\n` is by itself, so start a new line.
                if parts[0] == "" and parts[1] == "":
                    lines.append(line.rstrip())
                    line = ""
                    continue
                elif parts[1] == "":
                    # The `\n` was at the end of the word, so add the current 
                    # part to the current line and start a new line
                    lines.append((line + parts[0]).rstrip())
                    line = ""
                    continue
                else:
                    # The `\n` was in the middle of the word, or end. So add 
                    # the first part to the current line and start a new line.
                    # Then add the second part to the list of words to be 
                    # processed.
                    words.insert(index, parts[1])

                    # Add the part to the current line and start a new line.
                    lines.append((line + parts[0]).rstrip())
                    line = ""
                    continue
            
            # If the word is longer than the wrap length, cut it and add it to 
            # the list of words to be processed.
            if len(word) > wrap:
                # Cut the word to the remaining space on the line.
                cut_word: str = word[:(wrap - len(line))]

                # Add the rest of the word to the list of words to be processed.
                words.insert(index, word[len(cut_word):])
                
                # Add the cut word to the current line and start a new line.
                lines.append((line + cut_word).rstrip())
                line = ""
                continue

            # If the word is longer than the remaining space on the line, add
            # the current line to the list of lines and start a new line.
            if len(line) + len(word) > wrap:
                lines.append(line.rstrip())
                line = ""

            line += word + " "

        lines.append(line.rstrip())
        return lines

    @staticmethod
    def construct_bubble(message: str, wrap: int, thought: bool = False) -> str:
        """
        Constructs a speech bubble around the given message.
        """
        
        # Word wrap the message to max width.
        lines = Cowsay.word_wrap(message, wrap)

        # Get longest line
        width = max([len(line) for line in lines])

        # Build the body of the speech bubble.
        body = ""
        if thought:
            body = Cowsay.construct_thought_bubble_body(lines, width) 
        else:
            body = Cowsay.construct_say_bubble_body(lines, width)

        # Construct the speech bubble.
        bubble = f" _{width * '_'}_ \n"
        bubble += body
        bubble += f" -{width * '-'}- \n"

        return bubble

    @staticmethod
    def construct_say_bubble_body(lines: List[str], length: int) -> str:
        """
        Constructs a speech bubble body around the given message.
        """

        # Build the body of the speech bubble.
        body = ""
        if len(lines) == 1:
            body += f"< {lines[0]} >\n"
        else:
            body += f"/ {lines[0].ljust(length)} \\\n"
            for line in lines[1:-1]:
                body += f"| {line.ljust(length)} |\n"
            body += f"\\ {lines[-1].ljust(length)} /\n"
        
        return body
        
    @staticmethod
    def construct_thought_bubble_body(lines: List[str], length: int) -> str:
        """
        Constructs a thought bubble body around the given message.
        """

        # Build the body of the speech bubble.
        body = ""
        for line in lines:
            body += f"( {line.ljust(length)} )\n"

        return body

async def setup(bot: UQCSBot):
    cog = Cowsay(bot)
    await bot.add_cog(cog)
