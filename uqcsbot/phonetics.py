import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.yelling import yelling_exemptor

# X-SAMPA is basically a giant lookup table of symbols. It is split up into tables of
# length 4, 3, 2, and 1 for ease of decoding. This is not the most efficient way to
# convert X-SAMPA to Unicode, but it is definitely the simplest + easiest to understand.

XSAMPA_LOOKUP_4 = {
    "G\\_<": "ʛ",
    "J\\_<": "ʄ",
    "|\\|\\": "ǁ",
    "_B_L": " ᷅",
    "_H_T": " ᷄",
    "_R_F": " ᷈",
}

XSAMPA_LOOKUP_3 = {
    "b_<": "ɓ",
    "d_<": "ɗ",
    "g_<": "ɠ",
    "r\\`": "ɻ",
    "<F>": "↘",
    "<R>": "↗",
}

XSAMPA_LOOKUP_2 = {
    "d`": "ɖ",
    "h\\": "ɦ",
    "j\\": "ʝ",
    "l`": "ɭ",
    "l\\": "ɺ",
    "n`": "ɳ",
    "p\\": "ɸ",
    "r`": "ɽ",
    "r\\": "ɹ",
    "s`": "ʂ",
    "s\\": "ɕ",
    "t`": "ʈ",
    "v\\": "ʋ",
    "x\\": "ɧ",
    "z`": "ʐ",
    "z\\": "ʑ",
    "B\\": "ʙ",
    "G\\": "ɢ",
    "H\\": "ʜ",
    "I\\": "ᵻ",
    "J\\": "ɟ",
    "K\\": "ɮ",
    "L\\": "ʟ",
    "M\\": "ɰ",
    "N\\": "ɴ",
    "O\\": "ʘ",
    "R\\": "ʀ",
    "U\\": "ᵿ",
    "X\\": "ħ",
    "_j": "ʲ",
    ":\\": "ˑ",
    "@\\": "ɘ",
    "@`": "ɚ",
    "3\\": "ɞ",
    "?\\": "ʕ",
    "<\\": "ʢ",
    ">\\": "ʡ",
    "!\\": "ǃ",
    "|\\": "ǀ",
    "||": "‖",
    "=\\": "ǂ",
    "-\\": "‿",
    '_"': " ̈",
    "_+": " ̟",
    "_-": " ̠",
    "_/": " ̌",
    "_0": " ̥",
    "_=": " ̩",
    "_>": "ʼ",
    "_\\": " ̂",
    "_^": " ̯",
    "_}": " ̚",
    "_~": " ̃",
    "_A": " ̘",
    "_a": " ̺",
    "_B": " ̏",
    "_c": " ̜",
    "_d": " ̪",
    "_e": " ̴",
    "_f": " ̂",
    "_G": "ˠ",
    "_H": " ́",
    "_h": "ʰ",
    "_j": "ʲ",
    "_k": " ̰",
    "_L": " ̀",
    "_l": "ˡ",
    "_M": " ̄",
    "_m": " ̻",
    "_N": " ̼",
    "_n": "ⁿ",
    "_O": " ̹",
    "_o": " ̞",
    "_q": " ̙",
    "_R": " ̌",
    "_r": " ̝",
    "_T": " ̋",
    "_t": " ̤",
    "_v": " ̬",
    "_w": "ʷ",
    "_X": " ̆",
    "_x": " ̽",
}

XSAMPA_LOOKUP_1 = {
    "A": "ɑ",
    "B": "β",
    "C": "ç",
    "D": "ð",
    "E": "ɛ",
    "F": "ɱ",
    "G": "ɣ",
    "H": "ɥ",
    "I": "ɪ",
    "J": "ɲ",
    "K": "ɬ",
    "L": "ʎ",
    "M": "ɯ",
    "N": "ŋ",
    "O": "ɔ",
    "P": "ʋ",
    "Q": "ɒ",
    "R": "ʁ",
    "S": "ʃ",
    "T": "θ",
    "U": "ʊ",
    "V": "ʌ",
    "W": "ʍ",
    "X": "χ",
    "Y": "ʏ",
    "Z": "ʒ",
    ".": ".",
    '"': "ˈ",
    "%": "ˌ",
    "'": "ʲ",
    ":": "ː",
    "-": "",
    "@": "ə",
    "{": "æ",
    "}": "ʉ",
    "1": "ɨ",
    "2": "ø",
    "3": "ɜ",
    "4": "ɾ",
    "5": "ɫ",
    "6": "ɐ",
    "7": "ɤ",
    "8": "ɵ",
    "9": "œ",
    "&": "ɶ",
    "?": "ʔ",
    "^": "ꜛ",
    "!": "ꜜ",
    "|": "|",
    "~": " ̃",
}


class Phonetics(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.describe(input="X-SAMPA to convert")
    @yelling_exemptor(input_args=["input"])
    async def xsampa(self, interaction: discord.Interaction, input: str):
        """
        Converts X-SAMPA to IPA

        For example: /xsampa j}kj}sI(j)EsbQt

            `j}kj}sI(j)EsbQt`
            jʉkjʉsɪ(j)ɛsbɒt
        """
        remaining = input
        output = ""
        while len(remaining) > 0:
            if glyph := XSAMPA_LOOKUP_4.get(remaining[0:4], None):
                output += glyph
                remaining = remaining[4:]
            elif glyph := XSAMPA_LOOKUP_3.get(remaining[0:3], None):
                output += glyph
                remaining = remaining[3:]
            elif glyph := XSAMPA_LOOKUP_2.get(remaining[0:2], None):
                output += glyph
                remaining = remaining[2:]
            elif glyph := XSAMPA_LOOKUP_1.get(remaining[0:1], None):
                output += glyph
                remaining = remaining[1:]
            else:
                output += remaining[0]
                remaining = remaining[1:]
        await interaction.response.send_message(f"`{input}`\n{output}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Phonetics(bot))
