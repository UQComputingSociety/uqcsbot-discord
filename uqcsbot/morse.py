from typing import List

import re

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.bot import UQCSBot

# value of all valid ascii values in morse code
MorseCodeDict = {
    "A": ". - ",
    "B": "- . . . ",
    "C": "- . - . ",
    "D": "- . . ",
    "E": ". ",
    "F": ". . - . ",
    "G": "- - . ",
    "H": ". . . . ",
    "I": ". . ",
    "J": ". - - - ",
    "K": "- . - ",
    "L": ". - . . ",
    "M": "- - ",
    "N": "- . ",
    "O": "- - - ",
    "P": ". - - . ",
    "Q": "- - . - ",
    "R": ". - . ",
    "S": ". . . ",
    "T": "- ",
    "U": ". . - ",
    "V": ". . . - ",
    "W": ". - - ",
    "X": "- . . - ",
    "Y": "- . - - ",
    "Z": "- - . . ",
    "1": ". - - - - ",
    "2": ". . - - - ",
    "3": ". . . - - ",
    "4": ". . . . - ",
    "5": ". . . . . ",
    "6": "- . . . . ",
    "7": "- - . . . ",
    "8": "- - - . . ",
    "9": "- - - - . ",
    "0": "- - - - - ",
    ",": "- - . . - - ",
    ".": ". - . - . - ",
    "?": ". . - - . . ",
    "/": "- . . - . ",
    "-": "- . . . . - ",
    "(": "- . - - . ",
    ")": "- . - - . - ",
    " ": "  ",
    ";": "_ . _ . _ . ",
    ":": "_ _ _ . . .",
    "'": ". _ _ _ _ . ",
    '"': ". _ . . _ . ",
    "_": ". . _ _ . _ ",
    "=": "_ . . . _ ",
    "+": ". _ . _ . ",
}


class Morse(commands.Cog):
    def __init__(self, bot: UQCSBot):
        self.bot = bot

    @app_commands.command(name="morse")
    @app_commands.describe(message="The message to be converted to morse code")
    async def morse_command(
        self, interaction: discord.Interaction, message: str
    ) -> None:
        """
        Returns a string containing the argument converted to dots and dashes.
        """

        # Sanitise invalid characters from the message
        message = Morse.sanitise_illegals(message)

        # Sanitise message for discord emotes
        message = Morse.sanitise_emotes(message)

        # Convert all chars to lower case
        message = message.upper()

        # Then check they are valid morse code ascii
        invalid = Morse.check(message)
        if invalid != 0:
            await interaction.response.send_message(
                f"Invalid morse code character/s in string: {invalid}"
            )
            return

        # encrypt message
        response = Morse.encrypt_to_morse(message)

        # Check if response is too long
        if len(response) > 2000:
            await interaction.response.send_message("Resulting message too long!")
            return

        await interaction.response.send_message(response)

    @staticmethod
    def sanitise_illegals(message: str) -> str:
        """
        Replaces all illegal characters in the message with their sanitised
        equivalent.
        """

        # Strip whitespace from either side of the message
        message = message.strip()

        # replace code blocks with their sanitised equivalent
        message = message.replace("`", "")

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
    def check(message: str):
        ret = ""
        for letter in message:
            if letter not in MorseCodeDict:
                ret += letter
        if len(ret) != 0:
            return ret
        return 0

    @staticmethod
    def encrypt_to_morse(message: str):
        cipher = ""
        for letter in message:
            cipher += MorseCodeDict[letter] + "  "
        return cipher


async def setup(bot: UQCSBot):
    cog = Morse(bot)
    await bot.add_cog(cog)
