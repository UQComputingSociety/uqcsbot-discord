from random import choice
from functools import wraps
from typing import Callable, List
from discord.ext import commands

LOADING_REACTS = ["clock", "alarm_clock", "clock1", "clock8", "clock830", "timer", "arrows_counterclockwise"]

def loading_status(command_fn: Callable):
    @wraps(command_fn)
    async def wrapper(self, ctx: commands.Context):
        react = choice(LOADING_REACTS)
        await ctx.message.add_reaction(react)
        res = command_fn(self, ctx)
        await ctx.message.remove_reaction(react)
        return res
        
