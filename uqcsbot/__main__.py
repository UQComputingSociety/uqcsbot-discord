import asyncio
import logging
import os

import discord
from sqlalchemy import create_engine

from uqcsbot.bot import UQCSBot
from uqcsbot.models import Base

description = "The helpful and always listening, UQCSbot."

async def main():

    logging.basicConfig(level=logging.INFO)

    intents = discord.Intents.default()

    # Here for future getting info about members stuff that requires that specific permission.
    # This requires the privileged members intent.
    # Info here: https://discord.com/developers/docs/topics/gateway#privileged-intents
    intents.members = True
    intents.message_content = True

    DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

    DATABASE_URI = os.environ.get("POSTGRES_URI_BOT")
    if DATABASE_URI == None:
        # If the database env variable is not defined, default to SQLite in memory db.
        DATABASE_URI = "sqlite:///"

    # If you need to override the allowed mentions that can be done on a per message basis, but default to off
    allowed_mentions = discord.AllowedMentions.none()
    allowed_mentions.replied_user = True

    bot = UQCSBot(command_prefix="!", description=description, intents=intents, allowed_mentions=allowed_mentions)

    cogs = [
            "advent",
            "basic", 
            "channels", 
            "cowsay",
            "error_handler",
            "events",
            "gaming",
            "haiku", 
            "holidays",
            "intros", 
            "jobs_bulletin", 
            "latex", 
            "member_counter",
            "remindme",
            "starboard",
            "text", 
            "uptime",
            "voteythumbs",
            "whatsdue", 
            "whatweekisit",
            "working_on", 
            "xkcd",
            "yelling" 
            ]
    for cog in cogs:
        await bot.load_extension(f"uqcsbot.{cog}")

    db_engine = create_engine(DATABASE_URI, echo=True)
    Base.metadata.create_all(db_engine)
    bot.set_db_engine(db_engine)

    await bot.start(DISCORD_TOKEN)

asyncio.run(main())
