import os
import logging

import discord
from discord.ext import commands
from uqcsbot.bot import UQCSBot
from uqcsbot.models import Base

from sqlalchemy import create_engine

description = "The helpful and always listening, UQCSbot."

def main():

    logging.basicConfig()

    intents = discord.Intents.default()

    # Here for future getting info about members stuff that requires that specific permission.
    # This requires the privileged members intent.
    # Info here: https://discord.com/developers/docs/topics/gateway#privileged-intents
    intents.members = True

    DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

    # TODO: Handle if postgres URI is not defined.
    DATABASE_URI = os.environ.get("POSTGRES_URI_BOT")
    print(DATABASE_URI)

    bot = UQCSBot(command_prefix="!", description=description, intents=intents)

    cogs = ["basic", "channels", "events", "jobs_bulletin", "latex", "voteythumbs", "working_on", "yelling"]
    for cog in cogs:
        bot.load_extension(f"uqcsbot.{cog}")

    db_engine = create_engine(DATABASE_URI, echo=True)
    Base.metadata.create_all(db_engine)
    bot.set_db_engine(db_engine)

    bot.run(DISCORD_TOKEN)

main()
