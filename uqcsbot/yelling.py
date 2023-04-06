import discord
from discord.ext import commands
from random import choice, random
import re


class Yelling(commands.Cog):
    CHANNEL_NAME = "yelling"

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        """ Detects if a user is not yelling in #yelling and responds accordingly """
        if not self.bot.user or not isinstance(msg.channel, discord.TextChannel) or \
                msg.author.id == self.bot.user.id or msg.channel.name != self.CHANNEL_NAME:
            return

        # ignore emoji and links
        text = re.sub(r":[\w\-\+\~]+:", lambda m: m.group(0).upper(), msg.content, flags=re.UNICODE)

        # slightly more permissive version of discord's url regex, matches absolutely anything between http(s):// and whitespace
        text = re.sub(r"https?:\/\/[^\s]+", lambda m: m.group(0).upper(), text, flags=re.UNICODE)

        text = text.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")

        response = choice(["WHAT’S THAT‽",
                   "SPEAK UP!",
                   "STOP WHISPERING!",
                   "I CAN’T HEAR YOU!",
                   "I THOUGHT I HEARD SOMETHING!",
                   "I CAN’T UNDERSTAND YOU WHEN YOU MUMBLE!",
                   "YOU’RE GONNA NEED TO BE LOUDER!",
                   "WHY ARE YOU SO QUIET‽",
                   "QUIET PEOPLE SHOULD BE DRAGGED OUT INTO THE STREET AND SHOT!",
                   "PLEASE USE YOUR OUTSIDE VOICE!",
                   "IT’S ON THE LEFT OF THE “A” KEY!",
                   "FORMER PRESIDENT THEODORE ROOSEVELT’S FOREIGN POLICY IS A SHAM!",
                   "#YELLING IS FOR EXTERNAL SCREAMING!",
                   f"DID YOU SAY \n>>>{self.mutate_minuscule(text)}".upper(),
                   f"WHAT IS THE MEANING OF THIS ARCANE SYMBOL “{self.random_minuscule(text)}”‽"
                   + " I RECOGNISE IT NOT!"]
                  # the following is a reference to both "The Wicker Man" and "Nethack"
                  + (['OH, NO! NOT THE `a`S! NOT THE `a`S! AAAAAHHHHH!']
                     if 'a' in text else []))

        # check if minuscule in message, and if so, post response
        if any(char.islower() for char in text):
            await msg.reply(response)


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
                result += choice('abcdefghijklmnopqrstuvwxyz')
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

async def setup(bot: commands.Bot):
    await bot.add_cog(Yelling(bot))

