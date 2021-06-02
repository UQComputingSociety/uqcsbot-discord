import os

import discord
from discord.ext import commands

description = "The helpful and always listening, UQCSbot."

intents = discord.Intents.default()

# Here for future getting info about members stuff that requires that specific permission.
# This requires the privileged members intent. 
# Info here: https://discord.com/developers/docs/topics/gateway#privileged-intents
intents.members = True 

DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

bot = commands.Bot(command_prefix="!", description=description, intents=intents)

@bot.event
async def on_ready():
    print("Bot online and logged in")
    print(f"Name: {bot.user.name}")
    print(f"ID: {bot.user.id}")

@bot.command()
async def echo(ctx, *, text=""):
    """ Echos back the text that you send. """
    if text == "":
        await ctx.send("ECHO!")
    else:
        await ctx.send(text)

bot.run(DISCORD_TOKEN)
