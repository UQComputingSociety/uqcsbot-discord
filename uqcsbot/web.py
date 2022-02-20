import asyncio
from discord.ext import commands
from aiohttp import web
from uqcsbot.bot import UQCSBot

class Web(commands.Cog):
    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self.bot.loop.create_task(self.web_server())

    async def web_server(self):
        def handle(request):
            return web.Response(text="UQCSbot is running")

        app = web.Application()
        app.router.add_get('/', handle)
        runner = web.AppRunner(app)
        await runner.setup()
        self.site = web.TCPSite(runner, '0.0.0.0', 8080)
        await self.bot.wait_until_ready()
        await self.site.start()

    def __unload(self):
        asyncio.ensure_future(self.site.stop())

def setup(bot: UQCSBot):
    bot.add_cog(Web(bot))
