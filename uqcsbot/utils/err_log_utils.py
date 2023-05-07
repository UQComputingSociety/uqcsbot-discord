import discord
from discord.ext import commands

MODLOG_CHANNEL_NAME = "admin-alerts"


class FatalErrorWithLog(Exception):
    def __init__(
        self,
        client: commands.Bot,
        message: str,
        *args,
        **kwargs,
    ):
        modlog = discord.utils.get(client.get_all_channels(), name=MODLOG_CHANNEL_NAME)
        if modlog is not None:
            client.loop.create_task(modlog.send(message))
        else:
            message += f" ...And also, I couldn't find #{MODLOG_CHANNEL_NAME} to log this properly."

        super().__init__(message, *args, **kwargs)
