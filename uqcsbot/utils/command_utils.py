from random import choice
from functools import wraps
from typing import Callable, List
from discord.ext import commands

LOADING_REACTS = ["⏰", "🕰️", "⏲️", "🕖", "🕔", "🕥"]


"""
async def loading_status(command_fn: Callable):
    @wraps(command_fn)
    async def wrapper(self, ctx: commands.Context):
        react = choice(LOADING_REACTS)
        await ctx.message.add_reaction(react)
        res = await command_fn(self, ctx)
        await ctx.message.remove_reaction(react)
        return res
    return wrapper
"""

def loading_status(coro):
    @wraps(coro)  # Important to preserve name because `command` uses it
    async def wrapper(self, ctx: commands.Context):
        react = choice(LOADING_REACTS)
        reaction = await ctx.message.add_reaction(react)
        res = await coro(self, ctx)
        await ctx.message.remove_reaction(react, ctx.bot.user)
        return res
    return wrapper
