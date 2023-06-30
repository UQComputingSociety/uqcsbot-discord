import logging
import os
from typing import List, Optional, Tuple, Any, Callable, Coroutine

import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from aiohttp import web
from pytz import timezone

"""
TODO: TYPE ISSUES IN THIS FILE:
    - apscheduler has no stubs. They're planned for the 4.0 release... sometime.
    - aiohttp handler witchery
"""


class UQCSBot(commands.Bot):
    """An extended bot client to add extra functionality."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._scheduler = AsyncIOScheduler()
        self.start_time = datetime.now()

        # Important channel names & constants go here
        self.ADMIN_ALERTS_CNAME = "admin-alerts"
        self.GENERAL_CNAME = "general"
        self.BOT_CNAME = "bot-testing"
        self.STARBOARD_CNAME = "starboard"
        self.BOT_TIMEZONE = timezone("Australia/Brisbane")

        self.uqcs_server: discord.Guild

    def schedule_task(
        self, func: Callable[..., Coroutine[Any, Any, None]], *args: Any, **kwargs: Any
    ):
        """Schedule a function to be run at a later time. A wrapper for apscheduler add_job."""
        self._scheduler.add_job(func, *args, **kwargs)

    def set_db_engine(self, db_engine: Engine):
        """Creates a sessionmaker from the provided database engine which can be called from commands."""
        self.create_db_session = sessionmaker(bind=db_engine)

    async def setup_hook(self):
        await self.web_server()

    async def admin_alert(
        self,
        title: str,
        colour: discord.Colour,
        description: Optional[str] = None,
        footer: Optional[str] = None,
        fields: Optional[List[Tuple[str, str]]] = None,
        fields_inline: bool = True,
    ):
        """Sends an alert to the admin channel for logging."""
        admin_channel = discord.utils.get(
            self.uqcs_server.channels, name=self.ADMIN_ALERTS_CNAME
        )

        if admin_channel == None or not isinstance(admin_channel, discord.TextChannel):
            return

        admin_message = discord.Embed(title=title, colour=colour)
        if description:
            admin_message.description = description
        if fields:
            for field in fields:
                admin_message.add_field(
                    name=field[0], value=field[1], inline=fields_inline
                )
        if footer:
            admin_message.set_footer(text=footer)

        await admin_channel.send(embed=admin_message)

    # Web server binds to port 8080. This is a basic template to ensure
    # that Azure has something for a health check.
    async def web_server(self):
        def handle(request):
            return web.Response(text="UQCSbot is running")

        app = web.Application()
        app.router.add_get("/", handle)
        runner = web.AppRunner(app)
        await runner.setup()
        self.site = web.TCPSite(runner, "0.0.0.0", 8080)
        await self.site.start()

    async def on_ready(self):
        """Once the bot is loaded and has connected, run these commands first."""
        self._scheduler.start()

        if (user := self.user) is None:
            raise RuntimeError("Ready... but not logged in!")
        self.safe_user = user

        logging.info(
            f'Bot online and logged in: [Name="{self.safe_user.id}", ID={self.safe_user.id}]'
        )

        # Get the UQCS server object and store it centrally
        if (server_id := os.environ.get("SERVER_ID")) is None:
            raise RuntimeError("Server ID is not set!")
        if (server := self.get_guild(int(server_id))) is None:
            raise RuntimeError("Unable to find server with id {server_id}")
        self.uqcs_server: discord.Guild = server

        logging.info(f"Active in the {self.uqcs_server} server.")

        # Sync the app comamand tree with servers.
        await self.tree.sync()
        logging.info(f"Synced app command tree with guilds.")
