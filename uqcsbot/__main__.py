import os
import logging

import discord
from discord.ext import commands
from uqcsbot.bot import UQCSBot
from uqcsbot.models import Base

from sqlalchemy import create_engine

description = "The helpful and always listening, UQCSbot."

def main():

    logging.basicConfig(level=logging.INFO)

    intents = discord.Intents.default()

    # Here for future getting info about members stuff that requires that specific permission.
    # This requires the privileged members intent.
    # Info here: https://discord.com/developers/docs/topics/gateway#privileged-intents
    intents.members = True

    DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

    # TODO: Handle if postgres URI is not defined.
    DATABASE_URI = os.environ.get("POSTGRES_URI_BOT")

    # If you need to override the allowed mentions that can be done on a per message basis, but default to off
    allowed_mentions = discord.AllowedMentions.none()
    allowed_mentions.replied_user = True

    bot = UQCSBot(command_prefix="!", description=description, intents=intents, allowed_mentions=allowed_mentions)

    cogs = [
            "advent",
            "basic", 
            "channels", 
            "events", 
            "gaming", 
            "intros", 
            "jobs_bulletin", 
            "latex", 
            "text", 
            "uptime",
            "voteythumbs", 
            "working_on", 
            "whatsdue", 
            "yelling" 
            ]
    for cog in cogs:
        bot.load_extension(f"uqcsbot.{cog}")

    db_engine = create_engine(DATABASE_URI, echo=True)
    Base.metadata.create_all(db_engine)
    bot.set_db_engine(db_engine)

    bot.run(DISCORD_TOKEN)

main()
