import re
from typing import Final
from yaml import load, Loader
import random

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.bot import UQCSBot

SYLLABLE_RULES_PATH: Final[str] = "uqcsbot/static/syllable_rules.yaml"
ALLOWED_CHANNEL_NAMES: Final[list[str]] = [
    "banter",
    "bot-testing",
    "dating",
    "food",
    "general",
    "memes",
    "yelling",
]
YELLING_CHANNEL_NAME: Final[str] = "yelling"
HAIKU_BASE_PROBABILITY: float = 0.5
# How much "more likely" (as determined by _increase_probability) a haiku is if it has punctuation at the end of a line.
HAIKU_PUNCTUATION_PROBABILITY_INCREASE: float = 1.6
# Words that increase the probability of a haiku, and the amount they increase the probability by (as determined by _increase_probability)
HAIKU_FAVOURITE_WORD_LIST: dict[str, float] = {
    "haiku": 6,
    "haikus": 6,
    "syllable": 4,
    "word": 1.6,
    "words": 1.6,
    "poem": 2,
    "poems": 2,
}

SyllableRulesType = dict[str, dict[str, int] | tuple[str, ...]]
SYLLABLE_RULES: SyllableRulesType = {}
with open(SYLLABLE_RULES_PATH, "r", encoding="utf-8") as syllable_rules_file:
    SYLLABLE_RULES = load(syllable_rules_file, Loader=Loader)
# beginswith and endswith both require tuples, so turn all lists into tuples
for rule_name, rule_specification in SYLLABLE_RULES.items():
    if isinstance(rule_specification, list):
        SYLLABLE_RULES[rule_name] = tuple(rule_specification)


class Haiku(commands.Cog):
    """
    Trys to find Haiku messages in certain channels, and respond "Nice haiku" if it finds one
    """

    def __init__(self, bot: UQCSBot):
        self.bot = bot
        # TODO close cog if syllable rules is empty

    @commands.Cog.listener()
    async def on_ready(self):
        # As channels aren't ready when __init__() is called
        self.allowed_channels = [
            discord.utils.get(self.bot.uqcs_server.channels, name=channel_name)
            for channel_name in ALLOWED_CHANNEL_NAMES
        ]

    @commands.Cog.listener()
    async def on_message(self, message):
        if (
            message.channel not in self.allowed_channels
            or message.author.bot
            or "```" in message.content
        ):
            return

        haiku_lines, probability_of_showing_haiku = _find_haiku(message.content)
        if not haiku_lines or random.random() > probability_of_showing_haiku:
            return

        haiku_lines = ["> " + line for line in haiku_lines]
        haiku = "\n".join(haiku_lines)
        if message.channel == discord.utils.get(
            self.bot.uqcs_server.channels, name=YELLING_CHANNEL_NAME
        ):
            await message.reply(f"Nice haiku:\n{haiku}".upper())
        else:
            await message.reply(f"Nice haiku:\n{haiku}")

    @app_commands.command()
    @app_commands.describe(word="Word to syllable check")
    async def syllables(self, interaction: discord.Interaction, word: str):
        """Checks the number of syllables in a given word."""
        if " " not in word:
            pluralisation = (
                "syllables" if _number_of_syllables_in_word(word) != 1 else "syllable"
            )

            await interaction.response.send_message(
                f"{word} has {_number_of_syllables_in_word(word)} {pluralisation}."
            )
        else:
            await interaction.response.send_message(
                "I can only check one word at a time!"
            )


def _find_haiku(text: str):
    """
    Finds a haiku and a related "probability" that something is a haiku.
    The "probability" is a rough estimate based on the amount of punctuation and words contained.
    """
    probability: float = HAIKU_BASE_PROBABILITY
    syllable_count: int = 0
    lines: list[str] = []
    current_line: list[str] = []
    punctuation_at_end_of_previous_line = True  # Initially true so that any punctuation at the beginning does not increase the probability.
    haiku_syllable_count = [5, 7, 5]

    def _increased_probability(probability: float, index: float):
        """
        Calculates the probability of at least 1 success in index Bernoulli trials with given probability.
        """
        return 1 - (1 - probability) ** index

    for word in text.split():
        number_of_syllables = _number_of_syllables_in_word(word)

        # Remove all space-separated punctuation and emotes
        if number_of_syllables == 0:
            # If the last or first "word" is actually punctuation, keep it and increase the chance of it being a haiku
            if not current_line:
                if not punctuation_at_end_of_previous_line:
                    lines[-1] = lines[-1] + " " + word
                    punctuation_at_end_of_previous_line = True
                probability = _increased_probability(
                    probability, HAIKU_PUNCTUATION_PROBABILITY_INCREASE
                )
            continue

        if len(lines) == 3:
            return False, 0

        current_line.append(word)
        if word.lower() in HAIKU_FAVOURITE_WORD_LIST:
            probability = _increased_probability(
                probability, HAIKU_FAVOURITE_WORD_LIST[word.lower()]
            )

        syllable_count += number_of_syllables
        if syllable_count > haiku_syllable_count[len(lines)]:
            return False, 0
        if syllable_count == haiku_syllable_count[len(lines)]:
            # If the last character is punctuation, increase the chance of it being a haiku
            if not word[-1].isalnum():
                probability = _increased_probability(
                    probability, HAIKU_PUNCTUATION_PROBABILITY_INCREASE
                )

            lines.append(" ".join(current_line))
            current_line = []
            syllable_count = 0
            punctuation_at_end_of_previous_line = False

    if len(lines) != 3:
        return False, 0
    return lines, probability


def _number_of_vowel_groups(word: str):
    """
    Find the number of vowel groups within a word. A vowel group string of consecutive vowels.
    Each vowel can only be part of one vowel group and distinct vowel groups must be separated by a non-vowel character.
    The letter "y" is included as a vowel.
    """
    return len(re.findall("[aeiouy]+", word))


def _number_of_syllables_in_word(word: str):
    """
    Estimate the number of syllables in a word.
    Inspired off the algorithm from this website: https://eayd.in/?p=232
    Also the tool https://www.dcode.fr/word-search-regexp is useful at finding words and counterexamples
    """

    number_of_syllables = 0

    word = word.lower()
    # Get rid of emotes. Stolen from https://www.freecodecamp.org/news/how-to-use-regex-to-match-emoji-including-discord-emotes/
    word = re.sub("<a?:.+?:[0-9]+?>", " ", word)

    if word.startswith(
        SYLLABLE_RULES["prefixes_needing_extra_syllable_before_illegal_replacement"]
    ):
        number_of_syllables += 1

    # Replace "illegals" (non-alphabetic characters)
    for i, letter in enumerate(word):
        if letter in SYLLABLE_RULES["accents"]:
            unaccented_letter = SYLLABLE_RULES["accents"][letter]
            # Note that unaccented letter may be more than one character (eg "æ" goes to "ae")
            word = word[:i] + unaccented_letter + word[i + len(unaccented_letter) :]
    # Words ending in "'s" are similar to pluralising a word. If the word ends in "ch", "s" or "sh" then we add "es", otherwise we just add "s"
    if word.endswith("'s"):
        word = word.removesuffix("'s")
        if word.endswith(("ch", "s", "sh")):
            word += "es"
        else:
            word += "s"
    word = re.sub("[^a-z]+", " ", word)
    word = word.strip()
    if word == "":
        return 0

    if word in SYLLABLE_RULES["exceptions"].keys():
        return SYLLABLE_RULES["exceptions"][word]

    # Deals with abbreviations with no vowels
    if _number_of_vowel_groups(word) == 0:
        return len(word.replace(" ", ""))

    # Remove suffixes so we can focus on the syllables of the root word, but only if it is a true suffix (checked by testing if there is another vowel without the suffix)
    for suffix in SYLLABLE_RULES["suffixes_to_remove"]:
        if (
            word.endswith((suffix, suffix + "s"))
            and _number_of_vowel_groups(
                word.removesuffix(suffix).removesuffix(suffix + "s")
            )
            > 0
        ):
            word = word.removesuffix(suffix).removesuffix(suffix + "s")
            number_of_syllables += _number_of_vowel_groups(suffix)
    for suffix in SYLLABLE_RULES["suffixes_to_remove_with_one_less_syllable"]:
        if (
            word.endswith((suffix, suffix + "s"))
            and _number_of_vowel_groups(
                word.removesuffix(suffix).removesuffix(suffix + "s")
            )
            > 0
        ):
            word = word.removesuffix(suffix).removesuffix(suffix + "s")
            number_of_syllables += _number_of_vowel_groups(suffix)
            number_of_syllables -= 1
    for suffix in SYLLABLE_RULES["suffixes_to_remove_with_extra_syllable"]:
        if (
            word.endswith((suffix, suffix + "s"))
            and _number_of_vowel_groups(
                word.removesuffix(suffix).removesuffix(suffix + "s")
            )
            > 0
        ):
            word = word.removesuffix(suffix).removesuffix(suffix + "s")
            number_of_syllables += _number_of_vowel_groups(suffix)
            number_of_syllables += 1

    number_of_syllables += _number_of_vowel_groups(word)

    # Before removing s, note that "s" adds a syllable to words ending in "ce", "ge", "se", "ches" or "shes" such as "sentences", "ages", "houses", "batches" and "hashes"
    # Note that this does not include all words ending in "thes", as we have words like "breathes"
    if word.endswith(("ces", "ges", "ses", "ches", "shes")):
        number_of_syllables += 1
    word = word.removesuffix("s")

    # GENERAL SUFFIX RULES
    # Do not move these to the suffixes tuples, as they often are contained within larger suffixes (contained within the suffix tuple; at most one suffix tuple rule applies, so we should avoid overlap)
    # Words like "flipped" and "asked" don't have a syllable for "ed"
    if (
        number_of_syllables > 1
        and word.endswith("ed")
        # Accounts for verbs such as "acted" with hard "t" or "amended" with "d"
        and not word.endswith(("aed", "eed", "ied", "oed", "ued", "ted", "ded"))
    ):
        number_of_syllables -= 1
    # Accounts for silent "e" at the ends of words
    if (
        word.endswith("e")
        and not word.endswith(("ae", "ee", "ie", "oe", "ue"))
        and _number_of_vowel_groups(word.removesuffix("e")) > 0
    ):
        number_of_syllables -= 1

    # GENERAL PREFIX RULES
    # Do not move these to the prefix tuples, as these are more complex and are often are contained within larger suffixes (contained within the suffix tuple; at most one suffix tuple rule applies, so we should avoid overlap)

    # When "X" is a vowel, "reX" is often pronounced as two syllables (as "re" is used as a prefix).
    # Note that despite there being many exceptions, this approach was taken so that made up words (such as "reAppify") still work as intended
    if word.startswith(("rea", "ree", "rei", "reo", "reu")):
        number_of_syllables += 1

    # Deal with exceptions from the given prefix and suffix lists
    if word.startswith(SYLLABLE_RULES["prefixes_needing_extra_syllable"]):
        number_of_syllables += 1
    if word.startswith(SYLLABLE_RULES["prefixes_needing_one_less_syllable"]):
        number_of_syllables -= 1
    if word.endswith(SYLLABLE_RULES["suffixes_needing_one_more_syllable"]):
        number_of_syllables += 1
    if word.endswith(SYLLABLE_RULES["suffixes_needing_one_less_syllable"]):
        number_of_syllables -= 1

    return number_of_syllables


async def setup(bot: UQCSBot):
    await bot.add_cog(Haiku(bot))
