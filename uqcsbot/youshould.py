from typing import Final, List, Tuple, Set
import random
import logging

import discord
from discord.ext import commands

from uqcsbot.bot import UQCSBot

ALLOWED_CHANNEL_NAMES: Final[List[str]] = [
    "banter",
    "bot-testing",
    "dating",
    "food",
    "general",
    "memes",
    "yelling",
]
YELLING_CHANNEL_NAME: Final[str] = "yelling"

YOUSHOULD_WORDS: List[Tuple[Set[str], str, float]] = [
    ({"somebody should", "someone should"}, "**You** should", 2 / 3),
    ({"im", "i'm", "i am", 'i"m'}, "Hi", 1 / 3),
]


class YouShould(commands.Cog):
    """
    Replies to people who begins their message a certain way
    """

    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self.allowed_channels = []

    @commands.Cog.listener()
    async def on_ready(self):
        # As channels aren't ready when __init__() is called
        self.allowed_channels = [
            discord.utils.get(self.bot.uqcs_server.channels, name=channel_name)
            for channel_name in ALLOWED_CHANNEL_NAMES
        ]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if (
            message.channel not in self.allowed_channels
            or message.author.bot
            or "```" in message.content
            or "\n" in message.content
            or len(message.content) > 80
        ):
            return

        letter_case = (
            str.upper
            if (
                message.channel
                == discord.utils.get(
                    self.bot.uqcs_server.channels, name=YELLING_CHANNEL_NAME
                )
            )
            else str
        )

        for phrases, replace, probability in YOUSHOULD_WORDS:
            if probability <= random.random():
                continue
            for start in phrases:
                if message.content.lower().startswith(start + " "):
                    await message.reply(
                        letter_case(replace) + " " + message.content[len(start) + 1 :]
                    )
                    break


async def setup(bot: UQCSBot):
    try:
        await bot.add_cog(YouShould(bot))
    except RuntimeError as e:
        logging.error(e)
