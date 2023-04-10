from random import choice, randrange
from string import hexdigits
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands


class Text(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.zalgo_menu = app_commands.ContextMenu(
            name="Zalgo",
            callback=self.zalgo_context,
        )
        self.bot.tree.add_command(self.zalgo_menu)
        
        self.mock_menu = app_commands.ContextMenu(
            name="Mock",
            callback=self.mock_context,
        )
        self.bot.tree.add_command(self.mock_menu)

        self.scare_menu = app_commands.ContextMenu(
            name="Scare",
            callback=self.scare_context,
        )
        self.bot.tree.add_command(self.scare_menu)

    @app_commands.command()
    @app_commands.describe(message="Input string", encoding="Character encoding to use, defaults to UTF-8")
    async def binify(self, interaction: discord.Interaction, message: str, encoding: Optional[str] = "utf-8"):
        """
        Converts a binary string to text or vice versa.
        """
        if not message:
            response = "Please include string to convert."
        elif set(message).issubset(["0", "1"]) and len(message) > 2:
            if len(message) % 8 != 0:
                response = "Binary string contains partial byte."
            else:
                decoded_message = bytearray()
                for i in range(0, len(message), 8):
                    n = int(message[i:i+8], 2)
                    decoded_message.append(n)
                try:
                    response = decoded_message.decode(encoding)
                except UnicodeDecodeError as e:
                    response = e.reason
        else:
            try:
                encoded_message = message.encode(encoding)
                response = ''.join([
                    f"{byte:08b}" for byte in encoded_message
                ])
            except UnicodeEncodeError as e:
                response = e.reason

        await interaction.response.send_message(response)

    @app_commands.command()
    @app_commands.describe(message="Text to shift", distance="Distance to shift, defaults to 13")
    async def caesar(self, interaction: discord.Interaction, message: str, distance: Optional[int] = 13):
        """
        Performs caesar shift with a shift of N on given text.
        N defaults to 13 if not given.
        """
        result = ""
        for c in message:
            if ord("A") <= ord(c) <= ord("Z"):
                result += chr((ord(c) - ord("A") + distance) % 26 + ord("A"))
            elif ord("a") <= ord(c) <= ord("z"):
                result += chr((ord(c) - ord("a") + distance) % 26 + ord("a"))
            else:
                result += c

        await interaction.response.send_message(result)

    @app_commands.command()
    @app_commands.describe(message="Input string", encoding="Character encoding to use, defaults to UTF-8")
    async def hexify(self, interaction: discord.Interaction, message: str, encoding: Optional[str] = "utf-8"):
        """
        Converts a hexadecimal string to text or vice versa.
        """
        if not message:
            response = "Please include string to convert."
        elif all(c in hexdigits for c in message) and len(message) > 2:
            try:
                decoded_message = bytes.fromhex(message)
                response = decoded_message.decode(encoding)
            except ValueError:
                response = "Hexadecimal string contains partial byte."
            except UnicodeDecodeError as e:
                response = e.reason
        else:
            try:
                encoded_message = message.encode(encoding)
                response = encoded_message.hex()
            except UnicodeEncodeError as e:
                response = e.reason

        await interaction.response.send_message(response)

    @app_commands.command()
    @app_commands.describe(code="HTTP code")
    async def httpcat(self, interaction: discord.Interaction, code: int):
        """
        Posts an httpcat image.
        """
        if code in {100, 101, 200, 201, 202, 204, 206, 207, 300, 301, 302, 303, 304, 305, 307,
                    400, 401, 402, 403, 404, 405, 406, 408, 409, 410, 411, 412, 413, 414, 415,
                    416, 417, 418, 420, 421, 422, 423, 424, 425, 426, 429, 431, 444, 450, 451,
                    500, 502, 503, 504, 506, 507, 508, 509, 510, 511, 599}:
            await interaction.response.send_message(f"https://http.cat/{code}")
        else:
            await interaction.response.send_message(f"HTTP cat {code} is not available")
    
    async def mock_context(self, interaction: discord.Interaction, message: discord.Message):
        """ mOCkS tHis MEssAgE """

        await interaction.response.send_message("".join(choice((c.upper(), c.lower())) for c in message.content))

    @app_commands.command(name="mock")
    @app_commands.describe(text="Text to mock")
    async def mock_command(self, interaction: discord.Interaction, text: str):
        """ mOckS ThE pRovIdEd teXT. """

        await interaction.response.send_message("".join(choice((c.upper(), c.lower())) for c in text))

    async def scare_context(self, interaction: discord.Interaction, message: discord.Message):
        """ "adds" "scare" "quotes" "to" "this" "message" """

        await interaction.response.send_message(" ".join(f'"{w}"' for w in message.content.split(" ")))

    @app_commands.command(name="scare")
    @app_commands.describe(text="Text to \"scare\"")
    async def scare_command(self, interaction: discord.Interaction, text: str):
        """
        "adds" "scary" "quotes" "around" "the" "provided" "text"
        """

        await interaction.response.send_message(" ".join(f'"{w}"' for w in text.split(" ")))
    
    def zalgo_common(self, message: str) -> str:
        """ Zalgo-ifies a given string. """
        horror = ('\u0315', '\u0358', '\u0328', '\u034f', '\u035f', '\u0337', '\u031b',
                  '\u0321', '\u0334', '\u035c', '\u0360', '\u0361', '\u0340', '\u0322',
                  '\u0335', '\u035d', '\u0362', '\u0341', '\u0327', '\u0336', '\u035e', '\u0338')
        response = ""
        for c in " ".join(message):
            response += c
            for i in range(randrange(7)//3):
                response += choice(horror)
        return response
    
    async def zalgo_context(self, interaction: discord.Interaction, message: discord.Message):
        "á ̵d ̵d s̨  ̨͟ z ̛a l g o  ̸ e͝ ͘f f̵͠ e͢ c̷ ̸t  ́ ̡͟t o ̶ ̀ t̶͞ h́ ̡i͢ s  m ́͟e̶ ̢s s̢ a͝ ̨g e͞"
        
        await interaction.response.send_message(self.zalgo_common(message.content))
        
    @app_commands.command(name="zalgo")
    @app_commands.describe(text="Input text")
    async def zalgo_command(self, interaction: discord.Interaction, text: str):
        """
        Ȃd͍̋͗̃d͒̈́s̒͢ ̅̂̚͏̞̩ͅZͩ̆a̦̐ͭ́l̠̫̈́̐g̡͗ͯo̝̱̽ ̮̰͊c̢̞ͬh̩ͤ̑a̡̫̟͐̽̌r̪̭͇̓a̘͕̣c͓̐́t̠̂̈̓e̳̣̣͂̉r͓͗s͉̞͝ t̙͓̊ͨoͭ ̋̽͊t̛̖̮̊͋hͤ̂͏̯̺͚e̷͖̩̙̿ ͇̩̕ğ̵̟̘̼i̢͙̜v̲ͫ͘e͐͐͆̕n͟ ̭͋͢ͅt͐͆̀e̝̱͑͛x̝̲t͇͕
        """

        await interaction.response.send_message(self.zalgo_common(text))

async def setup(bot: commands.Bot):
    await bot.add_cog(Text(bot))

