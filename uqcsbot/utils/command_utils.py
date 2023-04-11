from random import choice
from functools import wraps
from typing import Callable
from discord.ext import commands

LOADING_REACTS = ["⏰", "🕰️", "⏲️", "🕖", "🕔", "🕥"]
HYPE_REACTS = ['blahaj', 'blobhajHeart', 'realheart', 'blobhajInnocent', 'keen',
               'bigsippin', 'pog_of_greed', 'blobhajHearts']

def loading_status(command_fn: Callable):
    @wraps(command_fn)  # Important to preserve name because `command` uses it
    async def wrapper(self, ctx: commands.Context, *args):
        if ctx.message is None or ctx.bot is None:
            return

        react = choice(LOADING_REACTS)
        reaction = await ctx.message.add_reaction(react)
        res = await command_fn(self, ctx, *args)
        await ctx.message.remove_reaction(react, ctx.bot.user)
        return res
    return wrapper
