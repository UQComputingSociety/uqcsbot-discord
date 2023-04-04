import logging
import re
import discord
from discord.ext import commands

from uqcsbot.bot import UQCSBot


class Haiku(commands.Cog):
    """
    Trys to find Haiku messages in certain channels, and respond "Nice haiku" if it finds one
    """

    ALLOWED_CHANNEL_NAMES = ["bot-testing", "yelling"]
    YELLING_CHANNEL_NAME = "yelling"

    def __init__(self, bot: UQCSBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # As channels aren't ready when __init__() is called
        self.allowed_channels = [
            discord.utils.get(self.bot.get_all_channels(), name=channel_name)
            for channel_name in self.ALLOWED_CHANNEL_NAMES
        ]

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel not in self.allowed_channels:
            return
        if message.author.bot:
            return

        syllable_count = 0
        lines = []
        current_line = []
        haiku_syllable_count = [5, 7, 5]
        for word in message.content.split():
            if len(lines) == 3:
                return
            current_line.append(word)
            syllable_count += _number_of_syllables_in_word(word)
            if syllable_count > haiku_syllable_count[len(lines)]:
                return
            if syllable_count == haiku_syllable_count[len(lines)]:
                lines.append(" ".join(current_line))
                current_line = []
                syllable_count = 0

        if len(lines) != 3:
            return

        lines = ["> " + line for line in lines]
        haiku = "\n".join(lines)
        if message.channel == discord.utils.get(self.bot.get_all_channels(), name=self.YELLING_CHANNEL_NAME):
            await message.reply(f"Nice haiku:\n{haiku}".upper())
        else:
            await message.reply(f"Nice haiku:\n{haiku}")


def _number_of_syllables_in_word(word):
    """
    The number of vowel groups in a word, ignoring 'e' on the end of a word as it is usually silent.
    """
    vowel_groups = re.findall("[aAeEiIoOuUyY]+", word)
    if word.endswith(("e", "E", "es", "ES")) and len(vowel_groups) > 1:
        return len(vowel_groups) - 1
    return len(vowel_groups)


async def setup(bot: UQCSBot):
    await bot.add_cog(Haiku(bot))
