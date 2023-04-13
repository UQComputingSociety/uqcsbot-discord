import re
import discord
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
        if (
            message.channel not in self.allowed_channels
            or message.author.bot
            or "```" in message.content
        ):
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


def _number_of_vowel_groups(word: str):
    """
    Find the number of vowel groups within a word. A vowel group string of consecutive vowels. Each vowel can only be part of one vowel group and distinct vowel groups must be separated by a non-vowel character. The letter "y" is included as a vowel.
    """
    return len(re.findall("[aeiouy]+", word))


def _number_of_syllables_in_word(word: str):
    """
    Estimate the number of syllables in a word.
    Inspired off the algorithm from this website: https://eayd.in/?p=232
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
        "bbq": 3,
        "bsod": 4,
        "uq": 2,
        "uqcs": 4,
    }

    # PREFIXES
    prefixes_needing_extra_syllable = (
        # As "mc" is pronounced as its own syllable
        "mc",
        # Account for the prefixes tri and bi, which for separate syllables from the following vowel. For example, "triangle" and "biology".
        "tria", "trie", "trii", "trio", "triu", "bia", "bie", "bii", "bio", "biu",
        # The prefix "co-" often forms a separate syllable to the following vowel, as in "coincidence". The longer prefixes are to ensure it is a prefix, not just a word starting with "co" such as "cooking" or "coup".
        "coapt", "coed", "coinci", "coop",
        # The prefix "pre" often forms a separate syllable to the following vowel, as in "preamble" or "preempt")
        "prea", "pree", "prei", "preo", "preu",

        # WORD-LIKE ENTRIES
        # These are exceptions to the usual rules. Treat as prefixes variations of the words such as "cereal-box" for "cereal".

        # Words ending in "Xial" where "X" is not "b", "d", "m", "n", "r", "v" or "x", but "Xial" consists of 2 syllables
        "celestial",
        # Words ending in "eal" where "eal" consists of 2 syllables
        "boreal", "cereal", "corneal", "ethereal", "montreal",
        # Words ending in "nt" due to contraction (after removing punctuation)
        "didn t", "doesn t", "isn t", "shouldn t", "couldn t", "wouldn t",
        # Words ending in "nt" due to contraction (user forgetting punctuation)
        "didnt", "doesnt", "isnt", "shouldnt", "couldnt", "wouldnt",
        # Words ending in "e" that is considered silent, when it is not.
        "maybe", "cafe", "naive", "resume", "recipe",
    )

    prefixes_needing_one_less_syllable = (

        # WORD-LIKE ENTRIES
        # These are exceptions to the usual rules. Treat as prefixes variations of the words such as "preacher" for "preach".

        # Compound words with a silent "e" in the middle
        "facebook", "whitespace",
        # Words starting with "preX" where "X" is a vowel that aren't using "pre" as a prefix
        "preach",
        # Words that have been shortened in speech
        "every",
        # Words with vowel diphthongs that lead to two syllables
        "poet",
    )

    # SUFFIXES
    suffixes_needing_one_more_syllable = (
        # Words ending in "le" such as "apple" often have a "le" syllable. But if we have a vowel then "le", "e" is often silent, such as "whale".
        "le",
        # If not part of the "cian" or "tian" suffixes, "ian" often is pronounced as 2 syllables. For example, "Australian" (compared to "politician").
        "ian",
        # Usually, the suffix "ious" is one syllable, but if it is preceeded by "b", "n", "p" or "r" it is two syllables. For example, "anxious" has 2 syllables, but "amphibious" has 4 syllables. Likewise, consider "harmonious", "copious" and "glorious". Note: "s" has already been removed.
        "biou", "niou", "piou", "riou",
        # Usually, the suffix "ial" is one syllable, but if it is preceeded by "b", "d", "l", "m", "n", "r", "v" or "x" it is two syllables. For example, "initial" has 3 syllables, but "microbial" has 4 syllables. Likewise, consider "radial", "familial", "polynomial", "millennial", "aerial", "trivial" and "axial".
        "bial", "dial", "lial", "mial", "nial", "rial", "vial", "xial",
        # Words ending in "Xate" where X is a vowel, such as "graduate", often have "ate" as a separate syllable. The only exception is words ending in "quate" such as "adequate".
        "aate", "eate", "iate", "oate", "uate",
        # The suffix "ual" consists of two syllables such as "contextual". (Enter debate about "actual", "casual" and "usual". We will assume all of these have 3 syllables. Note that "actually" also has 3 syllables by this classification (which matches google's recommended pronunciation). We also use the British pronunciation of "dual", which has 2 syllables.) We exclude "qual" for words such as "equal".
        "ual",
        # The suffix "rior" contains two syllables in most words. For example "posterior" and "superior".
        "rior",
    )

    suffixes_needing_one_less_syllable = (
        # Usually words ending in "le" have "le" as a syllable, but this does not occur if a vowel is before the "e", as the "e" acts to change the other vowels sound. For example, consider "whale", "clientele", "pile", "hole" and "capsule"
        "ale", "ele", "ile", "ole", "ule",
        # The "cian" or "tian" suffixes have "ian" pronounced as 1 syllables. For example, "politician" (compared to "Australian").
        "cian", "tian",
        # Words ending in "Xate" where X is a vowel where "Xate" is a single syllable, for example "adequate".
        "quate",
        # Words ending in "Xual" where "Xual" is 1 syllable, such as "equal"
        "qual",
        # Words ending in "Xle" where "X" is a constant but with a silent "e" at the end
        "ville",

        # WORD-LIKE ENTRIES
        # These are exceptions to the usual rules.

        # Words ending in "Xle" where "X" is a constant but with a silent "e" at the end
        "aisle", "isle",
    )

    # REMOVED SUFFIXES
    # These are suffixes that may hide a root word and can be removed without changing the number of syllables in the root word
    suffixes_to_remove = (
        "ful", "fully", "ness", "ment", "ship", "ist", "ish", "less", "ly", "ing",
    )
    suffixes_to_remove_with_extra_syllable = (
        # "ism" is two syllables
        "ism",
    )

    # SYLLABLE COUNTING PROCESS

    if word in exceptions.keys():
        return exceptions[word]

    number_of_syllables = 0

    # Remove suffixes so we can focus on the syllables of the root word, but only if it is a true suffix (checked by testing if there is another vowel without the suffix)
    for suffix in suffixes_to_remove:
        if (
            word.endswith((suffix, suffix + "s"))
            and _number_of_vowel_groups(word.removesuffix(suffix).removesuffix(suffix + "s")) >= 0
        ):
            word = word.removesuffix(suffix).removesuffix(suffix + "s")
            number_of_syllables += _number_of_vowel_groups(suffix)
    for suffix in suffixes_to_remove_with_extra_syllable:
        if (
            word.endswith((suffix, suffix + "s"))
            and _number_of_vowel_groups(word.removesuffix(suffix).removesuffix(suffix + "s")) >= 0
        ):
            word = word.removesuffix(suffix).removesuffix(suffix + "s")
            number_of_syllables += _number_of_vowel_groups(suffix)
            number_of_syllables += 1

    number_of_syllables += _number_of_vowel_groups(word)

    # Before removing s, note that "s" adds a syllable to words ending in "ge", "se" such as "ages" and "sentences".
    if word.endswith(("ces", "ges")):
        number_of_syllables += 1
    word = word.removesuffix("s")

    # Any exceptions to this need to be put in the exceptions dictionary
    if len(word) <= 3:
        # Root words of 3 letters or less tend to have only 1 syllable. Any extra vowel groups within the root word need to be disregarded. For example "ageless" turns into "age" which only has 1 syllable, so 3 - 2 + 1 = 2 syllables in total. Similarly "eyes" turns into "eye" has 2 - 2 + 1 = 1 syllables in total, and "manly" has 2 - 1 + 1 = 2 syllables in total.
        return number_of_syllables - _number_of_vowel_groups(word) + 1

    # GENERAL SUFFIX RULES
    # Do not move these to the suffixes tuple, as they often are contained within larger suffixes (contained within the suffix tuple; at most one suffix tuple rule applies, so we should avoid overlap)
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
    ):
        number_of_syllables -= 1

    # Deal with exceptions from the given prefix and suffix lists
    if word.startswith(prefixes_needing_extra_syllable):
        number_of_syllables += 1
    if word.startswith(prefixes_needing_one_less_syllable):
        number_of_syllables -= 1
    if word.endswith(suffixes_needing_one_more_syllable):
        number_of_syllables += 1
    if word.endswith(suffixes_needing_one_less_syllable):
        number_of_syllables -= 1

    return number_of_syllables


async def setup(bot: UQCSBot):
    await bot.add_cog(Haiku(bot))
