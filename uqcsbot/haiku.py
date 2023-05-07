import re
import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.bot import UQCSBot


class Haiku(commands.Cog):
    """
    Trys to find Haiku messages in certain channels, and respond "Nice haiku" if it finds one
    """

    ALLOWED_CHANNEL_NAMES = [
        "banter",
        "bot-testing",
        "dating",
        "food",
        "general",
        "memes",
        "yelling",
    ]
    YELLING_CHANNEL_NAME = "yelling"

    def __init__(self, bot: UQCSBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # As channels aren't ready when __init__() is called
        self.allowed_channels = [
            discord.utils.get(self.bot.uqcs_server.channels, name=channel_name)
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
        if message.channel == discord.utils.get(
            self.bot.uqcs_server.channels, name=self.YELLING_CHANNEL_NAME
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

    # Try to keep these to a minimum by writing new rules, especially the dictionary exceptions.
    exceptions = {
        # Abbreviations
        "ok": 2,
<<<<<<< HEAD
        "bbq": 3,
=======
        "bsod": 4,
        "uq": 2,
        "uqcs": 4,
>>>>>>> 6ce7152bcf2777976527b540ea014b9967d772fa
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
        # The prefix "sci" often forms a separate syllable to the following vowel, as in "science" or "sciatic" 
        "scia", "scie", "scii", "scio", "sciu",

        # WORD-LIKE ENTRIES
        # These are exceptions to the usual rules. Treat as prefixes variations of the words such as "cereal-box" for "cereal".

        # Words ending in "Xial" where "X" is not "b", "d", "m", "n", "r", "v" or "x", but "Xial" consists of 2 syllables
        "celestial",
        # Words ending in "eal" where "eal" consists of 2 syllables
<<<<<<< HEAD
        "boreal",
        "cereal",
        "corneal",
        "ethereal",
        "montreal",
        # Words ending in "nt" due to contraction (after removing punctuation)
        "didn t",
        "doesn t",
        "isn t",
        "shouldn t",
        "couldn t",
        "wouldn t",
=======
        "boreal", "cereal", "corneal", "ethereal", "montreal",
>>>>>>> 6ce7152bcf2777976527b540ea014b9967d772fa
        # Words ending in "nt" due to contraction (user forgetting punctuation)
        "didnt",
        "doesnt",
        "isnt",
        "shouldnt",
        "couldnt",
        "wouldnt",
        # Words ending in "e" that is considered silent, when it is not.
<<<<<<< HEAD
        "maybe",
        "cafe",
        "naive",
    )
    prefixes_needing_one_less_syllable = (
        # Compound words with a silent "e" in the middle
        "facebook",
        # Words ending in "Xle" where "X" is a constant but with a silent "e" at the end
        "aisle",
        "isle",
=======
        "maybe", "cafe", "naive", "recipe", "abalone", "marscapone", "epitome",
        # Words starting with "real", "read", "reap", "rear", "reed", "reel", "reign" (see prefixes_needing_one_less_syllable) that use "re" as a prefix
        # Note that "realit" covers all words with root "reality"
        "realign", "realit", "reallocat", "readdres", "readjust", "reapp", "rearm", "rearrang", "rearrest", "reeducat", "reelect", "reignit", 
        # Words that have "ee" pronounced as two syllables
        "career",
        # Words that have "ie" pronounced as two syllables
        "audience", "plier", "societ", "quiet",
        # Words that have "ia" pronounced as two syllables
        "pliant",
        # Words that have "oe" pronounced as two syllables
        "poet",
        # Words that have "oi" pronounced as two syllables
        "heroic",
        # Words that have "oo" pronounced as two syllables
        "zoology",
        # Words that have "ue" pronounced as two syllables
        "silhouett",
        # Words that have "yo" pronounced as two syllables
        "everyone",
        # Words ending in "ed" that use "ed" as a syllable
        "biped", "daybed", "naked", "parallelepiped", "wretched",
    )
    # These are prefixes that contain "illegal" characters what are replaced (such as "é")
    prefixes_needing_extra_syllable_before_illegal_replacement = (
        # Words ending in "n't" due to contraction
        "didn't", "doesn't", "isn't", "shouldn't", "couldn't", "wouldn't",
        # Words with accents making a usually silent vowel spoken
        "pâté", "résumé",
    )

    prefixes_needing_one_less_syllable = (

        # WORD-LIKE ENTRIES
        # These are exceptions to the usual rules. Treat as prefixes variations of the words such as "preacher" for "preach".

        # Compound words with a silent "e" in the middle.
        # Note that "something" with the suffix "ing" removed
        "facebook", "forefather", "lovecraft", "someth", "therefore", "whitespace", "timezone",
        # Words starting with "triX" where "X" is a vowel that aren't using "tri" as a prefix
        # Note that "s" is removed for "tries, becoming "trie"
        "tried", "trie", 
>>>>>>> 6ce7152bcf2777976527b540ea014b9967d772fa
        # Words starting with "preX" where "X" is a vowel that aren't using "pre" as a prefix
        "preach",
        # Words that have been shortened in speech
        "every",
        # Words that start with "reX" where "X" is a vowel that aren't using "re" as a prefix
        "reach", "read", "reagan", "real", "realm", "ream", "reap", "rear", "reason", "reebok", "reed", "reef", "reek", "reel", "reich", "reign", "reindeer", "reovirus", "reuben", "reuter",
        # Words ending in "Xing" where "X" is a vowel that use "Xing" as a single syllable
        "boing",
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
        # The suffix "phe" is pronounced as a syllable, for example "apostrophe".
        "phe",
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
        # Words containing "ue" at the end acting as a silent "e"
        "tongue",
    )

    # REMOVED SUFFIXES
    # These are suffixes that may hide a root word and can be removed without changing the number of syllables in the root word
    suffixes_to_remove = (
<<<<<<< HEAD
        "ful",
        "fully",
        "ness",
        "ment",
        "ship",
        "ist",
        "ish",
        "less",
        "ly",
        "ing",
=======
        "ful", "fully", "ness", "ment", "ship", "ist", "ish", "less", "ly", "ing", "ising", "isation", "izing", "ization", "istic", "istically", "able", "ably", "ible", "ibly",
    )
    suffixes_to_remove_with_one_less_syllable = (
        "ise", "ize", "ised", "ized",
>>>>>>> 6ce7152bcf2777976527b540ea014b9967d772fa
    )
    suffixes_to_remove_with_extra_syllable = (
        "ism",
    )

    # SYLLABLE COUNTING PROCESS

    number_of_syllables = 0


    word = word.lower()
    # Get rid of emotes. Stolen from https://www.freecodecamp.org/news/how-to-use-regex-to-match-emoji-including-discord-emotes/
    word = re.sub("<a?:.+?:[0-9]+?>", " ", word)

    if word.startswith(prefixes_needing_extra_syllable_before_illegal_replacement):
        number_of_syllables += 1

    # Replace "illegals" (non-alphabetic characters)
    accents = {
        "à": "a", "á": "a", "â": "a", "ã": "a", "ä": "a", "å": "a", "æ": "ae",
        "ç": "c",
        "è": "e", "é": "e", "ê": "e", "ë": "e",
        "ì": "i", "í": "i", "î": "i", "ï": "i",
        "ñ": "n",
        "ò": "o", "ó": "o", "ô": "o", "õ": "o", "ö": "o", "ø": "o", "œ": "oe",
        "ù": "u", "ú": "u", "û": "u", "ü": "u",
        "ý": "y", "ÿ": "y"
    }
    for i, letter in enumerate(word):
        if letter in accents:
            unaccented_letter = accents[letter]
            # Note that unaccented letter may be more than one character (eg "æ" goes to "ae")
            word = word[:i] + unaccented_letter + word[i+len(unaccented_letter):]
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

    if word in exceptions.keys():
        return exceptions[word]

    # Deals with abbreviations with no vowels
    if _number_of_vowel_groups(word) == 0:
        return len(word.replace(" ", ""))

    # Remove suffixes so we can focus on the syllables of the root word, but only if it is a true suffix (checked by testing if there is another vowel without the suffix)
    for suffix in suffixes_to_remove:
        if (
            word.endswith((suffix, suffix + "s"))
<<<<<<< HEAD
            and _number_of_vowel_groups(
                word.removesuffix(suffix).removesuffix(suffix + "s")
            )
            >= 0
=======
            and _number_of_vowel_groups(word.removesuffix(suffix).removesuffix(suffix + "s")) > 0
        ):
            word = word.removesuffix(suffix).removesuffix(suffix + "s")
            number_of_syllables += _number_of_vowel_groups(suffix)
    for suffix in suffixes_to_remove_with_one_less_syllable:
        if (
            word.endswith((suffix, suffix + "s"))
            and _number_of_vowel_groups(word.removesuffix(suffix).removesuffix(suffix + "s")) > 0
>>>>>>> 6ce7152bcf2777976527b540ea014b9967d772fa
        ):
            word = word.removesuffix(suffix).removesuffix(suffix + "s")
            number_of_syllables += _number_of_vowel_groups(suffix)
            number_of_syllables -= 1
    for suffix in suffixes_to_remove_with_extra_syllable:
        if (
            word.endswith((suffix, suffix + "s"))
<<<<<<< HEAD
            and _number_of_vowel_groups(
                word.removesuffix(suffix).removesuffix(suffix + "s")
            )
            >= 0
=======
            and _number_of_vowel_groups(word.removesuffix(suffix).removesuffix(suffix + "s")) > 0
>>>>>>> 6ce7152bcf2777976527b540ea014b9967d772fa
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

    # Any exceptions to this need to be put in the exceptions dictionary
    if len(word) <= 3:
        # Root words of 3 letters or less tend to have only 1 syllable. Any extra vowel groups within the root word need to be disregarded. For example "ageless" turns into "age" which only has 1 syllable, so 3 - 2 + 1 = 2 syllables in total. Similarly "eyes" turns into "eye" has 2 - 2 + 1 = 1 syllables in total, and "manly" has 2 - 1 + 1 = 2 syllables in total.
        return number_of_syllables - _number_of_vowel_groups(word) + 1

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
    if word.endswith("e") and not word.endswith(("ae", "ee", "ie", "oe", "ue")):
        number_of_syllables -= 1
<<<<<<< HEAD
    # Words ending in "le" such as "apple" often have a "le" syllable. But if we have a vowel then "le", "e" is often silent, such as "whale".
    if word.endswith("le") and not word.endswith(("ale", "ele", "ile", "ole", "ule")):
        number_of_syllables += 1
    # Words ending in "Xate" where X is a vowel, such as "graduate", often have "ate" as a separate syllable. The only exception is words ending in "quate" such as "adequate".
    if word.endswith(("aate", "eate", "iate", "oate", "uate")) and not word.endswith(
        "quate"
    ):
        number_of_syllables += 1
    # Usually, the suffix "ious" is one syllable, but if it is preceeded by "b", "n", "p" or "r" it is two syllables. For example, "anxious" has 2 syllables, but "amphibious" has 4 syllables. Likewise, consider "harmonious", "copious" and "glorious". Note: "s" has already been removed.
    if word.endswith(("biou", "niou", "piou", "riou")):
        number_of_syllables += 1
    # Usually, the suffix "ial" is one syllable, but if it is preceeded by "b", "d", "l", "m", "n", "r", "v" or "x" it is two syllables. For example, "initial" has 3 syllables, but "microbial" has 4 syllables. Likewise, consider "radial", "familial", "polynomial", "millennial", "aerial", "trivial" and "axial".
    if word.endswith(("bial", "dial", "lial", "mial", "nial", "rial", "vial", "xial")):
        number_of_syllables += 1
    # The suffix "ual" consists of two syllables such as "contextual". (Enter debate about "actual", "casual" and "usual". We will assume all of these have 3 syllables. Note that "actually" also has 3 syllables by this classification (which matches google's recommended pronunciation). We also use the British pronunciation of "dual", which has 2 syllables.)
    if word.endswith("ual"):
        number_of_syllables += 1

    # PREFIXES
    # As "mc" is pronounced as its own syllable
    if word.startswith("mc"):
        number_of_syllables += 1
    # Account for the prefixes tri and bi, which for separate syllables from the following vowel. For example, "triangle" and "biology".
    if word.startswith(
        ("tria", "trie", "trii", "trio", "triu", "bia", "bie", "bii", "bio", "biu")
    ):
        number_of_syllables += 1
    # If not part of the "cian" or "tion" suffixes, "ian" often is pronounced as 2 syllables. For example, "Australian" (compared to "politician").
    if word.endswith("ian") and not word.endswith(("cian", "tian")):
        number_of_syllables += 1
    # The prefix "co-" often forms a separate syllable to the following vowel, as in "coincidence". The longer prefixes are to ensure it is a prefix, not just a word starting with "co" such as "cooking" or "coup".
    if word.startswith(("coapt", "coed", "coinci", "coop")):
        number_of_syllables += 1
    # The prefix "pre" often forms a separate syllable to the following vowel, as in "preamble" or "preempt")
    if word.startswith(("prea", "pree", "prei", "preo", "preu")):
=======

    # GENERAL PREFIX RULES
    # Do not move these to the prefix tuples, as these are more complex and are often are contained within larger suffixes (contained within the suffix tuple; at most one suffix tuple rule applies, so we should avoid overlap)

    # When "X" is a vowel, "reX" is often pronounced as two syllables (as "re" is used as a prefix).
    # Note that despite there being many exceptions, this approach was taken so that made up words (such as "reAppify") still work as intended
    if word.startswith(("rea", "ree", "rei", "reo", "reu")):
>>>>>>> 6ce7152bcf2777976527b540ea014b9967d772fa
        number_of_syllables += 1

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
