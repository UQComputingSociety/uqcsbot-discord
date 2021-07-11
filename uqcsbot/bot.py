import logging
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class UQCSBot(commands.Bot):
    """ An extended bot client to add extra functionality. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scheduler = AsyncIOScheduler()

    def schedule_task(self, func, *args, **kwargs):
        """ Schedule a function to be run at a later time. A wrapper for apscheduler add_job. """
        self._scheduler.add_job(func, *args, **kwargs)

    async def on_ready(self):
        """ Once the bot is loaded and has connected, run these commands first. """
        self._scheduler.start()

        logging.info(f"Bot online and logged in: [Name=\"{self.user.name}\", ID={self.user.id}]")

