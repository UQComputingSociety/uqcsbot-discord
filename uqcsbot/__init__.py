import os

import discord
from discord.ext import commands
import logging

description = "The helpful and always listening, UQCSbot."

logging.basicConfig()

intents = discord.Intents.default()

# Here for future getting info about members stuff that requires that specific permission.
# This requires the privileged members intent. 
# Info here: https://discord.com/developers/docs/topics/gateway#privileged-intents
intents.members = True 

DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

bot = commands.Bot(command_prefix="!", description=description, intents=intents)


cogs = ["basic", "voteythumbs", "jobs_bulletin", "events"]
for cog in cogs:
    bot.load_extension(cog)

bot.run(DISCORD_TOKEN)
