import logging
import re
import discord
from discord.ext import commands

from uqcsbot.bot import UQCSBot


class Haiku(commands.Cog):
    """
    Trys to find Haiku messages in certain channels, and respond "Nice haiku" if it finds one
    """

    ALLOWED_CHANNEL_NAMES = ["bot-testing",
                             "yelling", "dating", "banter", "memes"]
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

        haiku_lines = _find_haiku(message.content)
        if not haiku_lines:
            return

        haiku_lines = ["> " + line for line in haiku_lines]
        haiku = "\n".join(haiku_lines)
        if message.channel == discord.utils.get(self.bot.get_all_channels(), name=self.YELLING_CHANNEL_NAME):
            await message.reply(f"Nice haiku:\n{haiku}".upper())
        else:
            await message.reply(f"Nice haiku:\n{haiku}")


def _find_haiku(text):
    syllable_count = 0
    lines = []
    current_line = []
    haiku_syllable_count = [5, 7, 5]
    for word in text.split():
        if _number_of_syllables_in_word(word) == 0:
            continue
        if len(lines) == 3:
            return False
        
        current_line.append(word)
        syllable_count += _number_of_syllables_in_word(word)
        if syllable_count > haiku_syllable_count[len(lines)]:
            return False
        if syllable_count == haiku_syllable_count[len(lines)]:
            lines.append(" ".join(current_line))
            current_line = []
            syllable_count = 0

    if len(lines) != 3:
        return False
    return lines


def _number_of_syllables_in_word(word):
    """
    Estimate the number of syllables in a word. Based off the algorithm from this website: https://eayd.in/?p=232
    """

    
    word = word.lower()
    # Get rid of emotes. Stolen from https://www.freecodecamp.org/news/how-to-use-regex-to-match-emoji-including-discord-emotes/
    word = re.sub("<a?:.+?:\d+?>", " ", word)
    word = re.sub("[^a-zA-Z]+", " ", word)
    word = word.strip()
    if word == "":
        return 0

    # Try to keep these to a minimum by writing new rules, especially the dictionary exceptions.
    exceptions = {
        "ok": 2
        }
    prefixes_needing_extra_syllable = (
        "serious", "crucial", "doesnt", "isnt", "shouldnt", "couldnt", "wouldnt")
    prefixes_needing_one_less_syllable = ("facebook", "aisle")
    suffixes_to_remove = (
        "s", "ful", "fully", "ness", "ment", "ship", "ism", "ist", "ish", "less", "ly")

    
    if word in exceptions.keys():
        return exceptions[word]

    if len(word) <= 3:
        return 1

    number_of_syllables = len(re.findall("[aeiouy]+", word))

    for suffix in suffixes_to_remove:
        if word.endswith(suffix):
            word = word.removesuffix(suffix)

    if (
        number_of_syllables > 1
        and word.endswith(("es", "ed"))
        and not word.endswith(("ted", "tes", "ses", "ied", "ies"))
    ):
        number_of_syllables -= 1
    if (
        word.endswith("e")
        and not word.endswith(("ae", "ee", "ie", "oe", "ue"))
        and (
            not word.endswith("le")
            or word.endswith(("ale", "ele", "ile", "ole", "ule"))
        )
    ):
        number_of_syllables -= 1

    if word.startswith("mc"):
        number_of_syllables += 1
    if word.startswith(("tria", "trie", "trii", "trio", "triu", "bia", "bie", "bii", "bio", "biu")):
        number_of_syllables += 1
    if word.endswith("ian") and not word.endswith(("cian", "tian")):
        number_of_syllables += 1
    if word.startswith(("coapt", "coed", "coinci", "coop")):
        number_of_syllables += 1
    if word.startswith(("prea", "pree", "prei", "preo", "preu")) and not word.startswith("preach"):
        number_of_syllables += 1

    if word.startswith(prefixes_needing_extra_syllable):
        number_of_syllables += 1
    if word.startswith(prefixes_needing_one_less_syllable):
        number_of_syllables -= 1
    return number_of_syllables


async def setup(bot: UQCSBot):
    await bot.add_cog(Haiku(bot))
