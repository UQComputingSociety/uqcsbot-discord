import os
import logging

import discord
from discord.ext import commands
from uqcsbot.bot import UQCSBot

description = "The helpful and always listening, UQCSbot."

def main():

    logging.basicConfig(level=logging.INFO)

    intents = discord.Intents.default()

    # Here for future getting info about members stuff that requires that specific permission.
    # This requires the privileged members intent.
    # Info here: https://discord.com/developers/docs/topics/gateway#privileged-intents
    intents.members = True

    DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

    bot = UQCSBot(command_prefix="!", description=description, intents=intents)

    cogs = ["basic", "events", "jobs_bulletin", "latex", "voteythumbs", "working_on"]
    for cog in cogs:
        bot.load_extension(f"uqcsbot.{cog}")

    bot.run(DISCORD_TOKEN)

main()
