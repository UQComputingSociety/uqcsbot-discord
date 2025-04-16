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

    if (discord_token := os.environ.get("DISCORD_BOT_TOKEN")) is None:
        raise RuntimeError("Bot token is not set!")
    if (database_uri := os.environ.get("POSTGRES_URI_BOT")) is None:
        database_uri = "sqlite:///"

    # If you need to override the allowed mentions that can be done on a per message basis, but default to off
    allowed_mentions = discord.AllowedMentions.none()
    allowed_mentions.replied_user = True

    bot = UQCSBot(
        command_prefix="!",
        description=description,
        intents=intents,
        allowed_mentions=allowed_mentions,
    )

    cogs = [
        "advent",
        "basic",
        "cat",
        "cowsay",
        "course_ecp",
        "dominos_coupons",
        "error_handler",
        "events",
        "gaming",
        "hackathon",
        "haiku",
        "holidays",
        "hoogle",
        "intros",
        "jobs_bulletin",
        "latex",
        "manage_cogs",
        "member_counter",
        "minecraft",
        "morse",
        "past_exams",
        "phonetics",
        "remindme",
        "snailrace",
        "starboard",
        "text",
        "uptime",
        "voteythumbs",
        "whatsdue",
        "whatweekisit",
        "working_on",
        "xkcd",
        "yelling",
    ]
    for cog in cogs:
        await bot.load_extension(f"uqcsbot.{cog}")

    db_engine = create_engine(database_uri, echo=True)
    Base.metadata.create_all(db_engine)
    bot.set_db_engine(db_engine)

    await bot.start(discord_token)


asyncio.run(main())
