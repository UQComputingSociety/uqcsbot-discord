from random import choice
from functools import wraps
from typing import Callable, Any
from discord.ext import commands
from uqcsbot.bot import UQCSBot

LOADING_REACTS = ["⏰", "🕰️", "⏲️", "🕖", "🕔", "🕥"]
HYPE_REACTS = [
    "blahaj",
    "blobhajHeart",
    "realheart",
    "blobhajInnocent",
    "keen",
    "bigsippin",
    "pog_of_greed",
    "blobhajHearts",
]


def loading_status(command_fn: Callable[..., Any]):
    @wraps(command_fn)  # Important to preserve name because `command` uses it
    # The use of Any in the following seems unavoidable. Using Any for *args is reasonable, as we want any type of arguments to be passed through. For self, it seems like the cleanest option at the moment: https://stackoverflow.com/a/69528375
    async def wrapper(self: Any, ctx: commands.Context[UQCSBot], *args: Any):
        # Check for the bot user before reacting to ensure that a loading react is not left on a message
        if ctx.bot.user is None:
            return
        react = choice(LOADING_REACTS)
        await ctx.message.add_reaction(react)
        res = await command_fn(self, ctx, *args)
        await ctx.message.remove_reaction(react, ctx.bot.user)
        return res

    return wrapper
