import discord
from typing import List, Dict, Callable, Any
from discord.ext import commands
from random import choice, random
import re

from uqcsbot.bot import UQCSBot
from uqcsbot.cog import UQCSBotCog
from uqcsbot.models import YellingBans

from datetime import timedelta
from functools import wraps


"""
This decorator that ensures that certain arguments of a command are checked if used in the #yelling channel.
Provide it with the list of names of keyword arguments that the #yelling check should be applied to.
Use after the decorator @app_commands.command().
"""


def yelling_exemptor(input_args: List[str] = ["text"]) -> Callable[..., Any]:
    def handler(func: Callable[..., Any]):
        @wraps(func)
        async def wrapper(
            cogself: UQCSBotCog, *args: List[Any], **kwargs: Dict[str, Any]
        ):
            bot = cogself.bot
            interaction = None
            text = "".join([str(kwargs.get(i, "") or "") for i in input_args])
            if text == "":
                await func(cogself, *args, **kwargs)
                return
            for a in args:
                if isinstance(a, discord.interactions.Interaction):
                    interaction = a
                    break
            if interaction is None:
                await func(cogself, *args, **kwargs)
                return
            if not hasattr(interaction, "channel"):
                await func(cogself, *args, **kwargs)
                return
            if interaction.channel is None:
                await func(cogself, *args, **kwargs)
                return
            if interaction.channel.type != discord.ChannelType.text:
                await func(cogself, *args, **kwargs)
                return
            if interaction.channel.name != "yelling":
                await func(cogself, *args, **kwargs)
                return
            if not Yelling.contains_lowercase(text):
                await func(cogself, *args, **kwargs)
                return

            await interaction.response.send_message(  # type: ignore
                str(discord.utils.get(bot.emojis, name="disapproval") or "")
            )
            if isinstance(interaction.user, discord.Member):
                await Yelling.external_handle_bans(bot, interaction.user)

        return wrapper

    return handler


class Yelling(commands.Cog):
    CHANNEL_NAME = "yelling"

    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self.bot.schedule_task(
            self.clear_bans, trigger="cron", hour=17, timezone="Australia/Brisbane"
        )

    @commands.Cog.listener()
    async def on_message_edit(self, old: discord.Message, new: discord.Message):
        """Detects if a message was edited, and call them out for it."""
        if (
            not self.bot.user
            or not isinstance(new.channel, discord.TextChannel)
            or new.author.id == self.bot.user.id
            or new.channel.name != self.CHANNEL_NAME
            or old.content == new.content
        ):
            return

        text = self.clean_text(new.content)

        if self.contains_lowercase(text):
            await new.reply(self.generate_response(text))
            if isinstance(new.author, discord.Member):
                banned = await self.handle_bans(new.author)
                if not banned:
                    await new.reply(
                        "<@&813325414302875669>! "
                        + new.author.mention
                        + " IS ABUSING THEIR DISCORD PRIVILEGES! NAUGHTY "
                        + new.author.mention
                        + "!"
                    )

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        """Detects if a user is not yelling in #yelling and responds accordingly"""
        if (
            not self.bot.user
            or not isinstance(msg.channel, discord.TextChannel)
            or msg.author.id == self.bot.user.id
            or msg.channel.name != self.CHANNEL_NAME
        ):
            return

        text = self.clean_text(msg.content)

        # check if minuscule in message, and if so, post response
        if self.contains_lowercase(text):
            await msg.reply(self.generate_response(text))
            if isinstance(msg.author, discord.Member):
                banned = await self.handle_bans(msg.author)
                if not banned:
                    await msg.reply(
                        "<@&813325414302875669>! "
                        + msg.author.mention
                        + " IS ABUSING THEIR DISCORD PRIVILEGES! NAUGHTY "
                        + msg.author.mention
                        + "!"
                    )

    @staticmethod
    async def external_handle_bans(bot: UQCSBot, author: discord.Member) -> bool:
        db_session = bot.create_db_session()
        yellingbans_query = (
            db_session.query(YellingBans)
            .filter(YellingBans.user_id == author.id)
            .one_or_none()
        )
        if yellingbans_query is None:
            value = 0
            db_session.add(YellingBans(user_id=author.id, value=1))
        else:
            value = yellingbans_query.value
            yellingbans_query.value += 1
        db_session.commit()
        db_session.close()

        try:
            await author.timeout(timedelta(seconds=(15 * 2**value)), reason="#yelling")
        except discord.Forbidden:
            return False
        return True

    async def handle_bans(self, author: discord.Member) -> bool:
        db_session = self.bot.create_db_session()
        yellingbans_query = (
            db_session.query(YellingBans)
            .filter(YellingBans.user_id == author.id)
            .one_or_none()
        )
        if yellingbans_query is None:
            value = 0
            db_session.add(YellingBans(user_id=author.id, value=1))
        else:
            value = yellingbans_query.value
            yellingbans_query.value += 1
        db_session.commit()
        db_session.close()

        try:
            await author.timeout(timedelta(seconds=(15 * 2**value)), reason="#yelling")
        except discord.Forbidden:
            return False
        return True

    async def clear_bans(self):
        db_session = self.bot.create_db_session()
        yellingbans_query = db_session.query(YellingBans)
        for i in yellingbans_query:
            if i.value <= 1:
                db_session.delete(i)
            else:
                i.value -= 1
        db_session.commit()
        db_session.close()

    def clean_text(self, message: str) -> str:
        """Cleans text of links, emoji, and any character escaping."""

        # ignore emoji and links
        text = re.sub(
            r"<(?P<animated>a?):(?P<name>\w{2,32}):(?P<id>\d{18,22})>",
            lambda m: m.group(0).upper(),
            message,
            flags=re.UNICODE,
        )

        # slightly more permissive version of discord's url regex, matches absolutely anything between http(s):// and whitespace
        for url in re.findall(r"https?:\/\/[^\s]+", text, flags=re.UNICODE):
            text = text.replace(url, url.upper())

        text = text.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")

        return text

    @staticmethod
    def contains_lowercase(message: str) -> bool:
        """Checks if message contains any lowercase characters"""
        return any(char.islower() for char in message)

    def generate_response(self, text: str) -> str:
        """Gives a random response for the bot to send back."""
        return choice(
            [
                "WHAT’S THAT‽",
                "SPEAK UP!",
                "STOP WHISPERING!",
                "I CAN’T HEAR YOU!",
                "I THOUGHT I HEARD SOMETHING!",
                "I CAN’T UNDERSTAND YOU WHEN YOU MUMBLE!",
                "YOU’RE GONNA NEED TO BE LOUDER!",
                "WHY ARE YOU SO QUIET‽",
                "PLEASE USE YOUR OUTSIDE VOICE!",
                "IT’S ON THE LEFT OF THE “A” KEY!",
                "FORMER PRESIDENT THEODORE ROOSEVELT’S FOREIGN POLICY IS A SHAM!",
                "#YELLING IS FOR EXTERNAL SCREAMING!",
                f"DID YOU SAY \n{self.mutate_minuscule(text)}".upper().replace(
                    "\n", "\n> "
                ),
                f"WHAT IS THE MEANING OF THIS ARCANE SYMBOL “{self.random_minuscule(text)}”‽"
                + " I RECOGNISE IT NOT!",
            ]
            # the following is a reference to both "The Wicker Man" and "Nethack"
            + (
                ["OH, NO! NOT THE `a`S! NOT THE `a`S! AAAAAHHHHH!"]
                if "a" in text
                else []
            )
        )

    def mutate_minuscule(self, message: str) -> str:
        """
        Randomly mutates 40% of minuscule letters to other minuscule letters and then inserts the
        original urls to their original places.
        :param message: the instigating message sent to !yelling
        :param urls: a list of pairs of starting indexes and urls to be inserted at those indexes
        :return: the original message modified as described above
        """
        result = ""
        for char in message:
            if char.islower() and random() < 0.4:
                result += choice("abcdefghijklmnopqrstuvwxyz")
            else:
                result += char

        return result

    def random_minuscule(self, message: str) -> str:
        """
        Returns a random minuscule letter from a string.
        :param message: the instigating message sent to !yelling
        :return: one lowercase character from the original message
        """
        possible = ""
        for char in message:
            if char.islower():
                possible += char
        return choice(possible) if possible else ""


async def setup(bot: UQCSBot):
    await bot.add_cog(Yelling(bot))
