import re
import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.bot import UQCSBot


class Haiku(commands.Cog):
    """
    Trys to find Haiku messages in certain channels, and respond "Nice haiku" if it finds one
    """

    ALLOWED_CHANNEL_NAMES = ["banter", "bot-testing",
                             "dating", "food", "general", "memes", "yelling"]
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

    @app_commands.command()
    @app_commands.describe(word="Word to syllable check")
    async def syllables(self, interaction: discord.Interaction, word: str):
        """ Checks the number of syllables in a given word. """
        if (" " not in word):
            pluralisation = "syllables" if _number_of_syllables_in_word(word) != 1 else "syllable"

            await interaction.response.send_message(f"{word} has {_number_of_syllables_in_word(word)} {pluralisation}.")
        else:
            await interaction.response.send_message("I can only check one word at a time!")


def _find_haiku(text: str):
    syllable_count = 0
    lines = []
    current_line = []
    haiku_syllable_count = [5, 7, 5]
    for word in text.split():
        # Remove all space-separated punctuation and emotes
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


def _number_of_syllables_in_word(word: str):
    """
    Estimate the number of syllables in a word. Based off the algorithm from this website: https://eayd.in/?p=232
    Also the tool https://www.dcode.fr/word-search-regexp is useful at finding words and counterexamples
    """

    word = word.lower()
    # Get rid of emotes. Stolen from https://www.freecodecamp.org/news/how-to-use-regex-to-match-emoji-including-discord-emotes/
    word = re.sub("<a?:.+?:[0-9]+?>", " ", word)
    word = re.sub("[^a-zA-Z]+", " ", word)
    word = word.strip()
    if word == "":
        return 0

    # Try to keep these to a minimum by writing new rules, especially the dictionary exceptions.
    exceptions = {
        # Abbreviations
        "ok": 2,
        "bbq": 3
    }
    prefixes_needing_extra_syllable = (
        # Words ending in "Xial" where "X" is not "b", "d", "m", "n", "r", "v" or "x", but "Xial" consists of 2 syllables
        "celestial",
        # Words ending in "eal" where "eal" consists of 2 syllables
        "boreal", "cereal", "corneal", "ethereal", "montreal",
        # Words ending in "nt" due to contraction (after removing punctuation)
        "doesnt", "isnt", "shouldnt", "couldnt", "wouldnt",
        # Words ending in "e" that is considered silent, when it is not.
        "maybe")
    prefixes_needing_one_less_syllable = (
        # Compound words with a silent "e" in the middle
        "facebook",
        # Words ending in "Xle" where "X" is a constant but with a silent "e" at the end
        "aisle", "isle",
        # Words starting with "preX" where "X" is a vowel that aren't using "pre" as a prefix
        "preach"
    )
    suffixes_needing_one_less_syllable = (
        # Words ending in "Xle" where "X" is a constant but with a silent "e" at the end
        "ville"
    )
    suffixes_to_remove = (
        "ful", "fully", "ness", "ment", "ship", "ism", "ist", "ish", "less", "ly"
    )

    if word in exceptions.keys():
        return exceptions[word]

    number_of_syllables = len(re.findall("[aeiouy]+", word))

    # Remove suffixes so we can focus on the syllables of the root word
    for suffix in suffixes_to_remove:
        if word.endswith((suffix, suffix + "s")):
            word = word.removesuffix(suffix)
            word = word.removesuffix(suffix + "s")

    # Any exceptions to this need to be put in the exceptions dictionary
    if len(word) <= 3:
        # Root words of 3 letters or less tend to have only 1 syllable. Any extra vowel groups within the root word need to be disregarded. For example "ageless" turns into "age" which only has 1 syllable, so 3 - 2 + 1 = 2 syllables in total. Similarly "eyes" turns into "eye" has 2 - 2 + 1 = 1 syllables in total, and "manly" has 2 - 1 + 1 = 2 syllables in total.
        number_of_vowel_groups_in_root_word = len(
            re.findall("[aeiouy]+", word))
        return number_of_syllables - number_of_vowel_groups_in_root_word + 1

    # SUFFIXES
    # Words like "flipped" and "asked" don't have a syllable for "ed"
    if (
        number_of_syllables > 1
        and word.endswith("ed")
        # Accounts for verbs such as "acted" with hard "t". May need to be expanded upon in future
        and not word.endswith("ted")
    ):
        number_of_syllables -= 1
    # Accounts for silent "e" at the ends of words
    if (
        word.endswith("e")
        and not word.endswith(("ae", "ee", "ie", "oe", "ue"))
        and (
            # Words ending in "le" such as "apple" often have a "le" syllable.
            not word.endswith("le")
            # But if we have a vowel then "le", "e" is often silent, such as "whale".
            or word.endswith(("ale", "ele", "ile", "ole", "ule"))
        )
    ):
        number_of_syllables -= 1
    # Usually, the suffix "ious" is one syllable, but if it is preceeded by "b", "n", "p" or "r" it is two syllables. For example, "anxious" has 2 syllables, but "amphibious" has 4 syllables. Likewise, consider "harmonious", "copious" and "glorious".
    if word.endswith(("bious", "nious", "pious", "rious")):
        number_of_syllables += 1
    # Usually, the suffix "ial" is one syllable, but if it is preceeded by "b", "d", "l", "m", "n", "r", "v" or "x" it is two syllables. For example, "initial" has 3 syllables, but "microbial" has 4 syllables. Likewise, consider "radial", "familial", "polynomial", "millennial", "aerial", "trivial" and "axial".
    if word.endswith(("bial", "dial", "lial", "mial", "nial", "rial", "vial", "xial")):
        number_of_syllables += 1
    # The suffix "ual" consists of two syllables such as "contextual". (Enter debate about "actual", "casual" and "usual". We will assume all of these have 3 syllables. Note that "actually" also has 3 syllables by this classification (which matches google's recommended pronunciation). We lso use the British pronunciation of "dual", which has 2 syllables.)
    if word.endswith("ual"):
        number_of_syllables += 1

    # PREFIXES
    # As "mc" is pronounced as its own syllable
    if word.startswith("mc"):
        number_of_syllables += 1
    # Account for the prefixes tri and bi, which for separate syllables from the following vowel. For example, "triangle" and "biology".
    if word.startswith(("tria", "trie", "trii", "trio", "triu", "bia", "bie", "bii", "bio", "biu")):
        number_of_syllables += 1
    # If not part of the "cian" or "tion" suffixes, "ian" often is pronounced as 2 syllables. For example, "Australian" (compared to "politician").
    if word.endswith("ian") and not word.endswith(("cian", "tian")):
        number_of_syllables += 1
    # The prefix "co-" often forms a separate syllable to the following vowel, as in "coincidence". The longer prefixes are to ensure it is a prefix, not just a word starting with "co" such as "cooking" or "coup".
    if word.startswith(("coapt", "coed", "coinci", "coop")):
        number_of_syllables += 1
    # The prefix "pre" often forms a separate syllable to the following vowel, as in "preamble" or "preempt")
    if word.startswith(("prea", "pree", "prei", "preo", "preu")):
        number_of_syllables += 1

    # Deal with exceptions
    if word.startswith(prefixes_needing_extra_syllable):
        number_of_syllables += 1
    if word.startswith(prefixes_needing_one_less_syllable):
        number_of_syllables -= 1
    if word.endswith(suffixes_needing_one_less_syllable):
        number_of_syllables -= 1

    return number_of_syllables


async def setup(bot: UQCSBot):
    await bot.add_cog(Haiku(bot))
