import discord
from discord.ext import commands
from typing import Optional
from random import choice, randrange

class Text(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def binify(self, ctx: commands.Context, *message: str):
        """
        `!binify (binary | ascii)` - Converts a binary string to an ascii string
        or vice versa
        """
        if not message:
            response = "Please include string to convert."
        elif set("".join(message)).issubset(["0", "1", " "]) and len("".join(message)) > 2:
            string = "".join(message)
            if len(string) % 8 != 0:
                response = "Binary string contains partial byte."
            else:
                response = ""
                for i in range(0, len(string), 8):
                    n = int(string[i:i+8], 2)
                    if n >= 128:
                        response = "Character out of ascii range (0-127)"
                        break
                    response += chr(n)
        else:
            response = ""
            for c in " ".join(message).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"):
                n = ord(c)
                if n >= 128:
                    response = "Character out of ascii range (0-127)"
                    break
                response += f"{n:08b}"

        await ctx.send(response)

    @commands.command()
    async def caesar(self, ctx: commands.Context, distance: Optional[int] = 13, *message: str):
        """
        `!caesar [N] <TEXT>` - Performs caesar shift with a shift of N on given text.
        N defaults to 13 if not given.
        """
        result = ""
        for c in " ".join(message):
            if ord("A") <= ord(c) <= ord("Z"):
                result += chr((ord(c) - ord("A") + distance) % 26 + ord("A"))
            elif ord("a") <= ord(c) <= ord("z"):
                result += chr((ord(c) - ord("a") + distance) % 26 + ord("a"))
            else:
                result += c

        await ctx.send(result)

    @commands.command()
    async def httpcat(self, ctx: commands.Context, code: int):
        """
        `!httpcat <code>` - posts a httpcat image
        """
        if code in {100, 101, 200, 201, 202, 204, 206, 207, 300, 301, 302, 303, 304, 305, 307,
                    400, 401, 402, 403, 404, 405, 406, 408, 409, 410, 411, 412, 413, 414, 415,
                    416, 417, 418, 420, 421, 422, 423, 424, 425, 426, 429, 431, 444, 450, 451,
                    500, 502, 503, 504, 506, 507, 508, 509, 510, 511, 599}:
            await ctx.send(f"https://http.cat/{code}")
        else:
            await ctx.send(f"HTTP cat {code} is not available")

    @httpcat.error
    async def httpcat_cat(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            ctx.command_failed = False
            await ctx.send("Code not an integer.")

    @commands.command()
    async def mock(self, ctx: commands.Context, *text: str):
        """
        `!mock <text>` - mOckS ThE pRovIdEd teXT
        """
        await ctx.send("".join(choice((c.upper(), c.lower())) for c in " ".join(text)))

    @commands.command()
    async def zalgo(self, ctx: commands.Context, *text: str):
        """
        `!zalgo TEXT` - Adds Zalgo characters to the given text.
        """
        horror = ('\u0315', '\u0358', '\u0328', '\u034f', '\u035f', '\u0337', '\u031b',
                  '\u0321', '\u0334', '\u035c', '\u0360', '\u0361', '\u0340', '\u0322',
                  '\u0335', '\u035d', '\u0362', '\u0341', '\u0327', '\u0336', '\u035e', '\u0338')
        response = ""
        for c in " ".join(text):
            response += c
            for i in range(randrange(7)//3):
                response += choice(horror)
        await ctx.send(response)

def setup(bot: commands.Bot):
    bot.add_cog(Text(bot))

