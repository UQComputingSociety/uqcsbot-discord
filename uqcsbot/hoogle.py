from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import requests
import json
import html
import re

class Hoogle(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    def get_endpoint(self, type_sig: str) -> str:
        unescaped = html.unescape(type_sig)
        return "https://www.haskell.org/hoogle/?mode=json&hoogle=" + unescaped + "&start=0&count=10"

    def pretty_hoogle_result(self, result: dict) -> str:
        url = result['url']
        type_sig = re.sub('<[^<]+?>', '', result['item']).replace('&gt;', '>')

        return f"`{type_sig}` <{url}|link>"
    
    @app_commands.command()
    @app_commands.describe(search="Function name or type signature to search for")
    async def hoogle(self, interaction: discord.Interaction, search: str):
        """
        Queries the Hoogle Haskell API search engine, searching Haskell libraries by either function name 
        or approximate type signature. Retrieves up to 10 results.
        """
        await interaction.response.defer(thinking=True)

        endpoint_url = self.get_endpoint(search)
        http_response = requests.get(endpoint_url)

        if http_response.status_code != requests.codes.ok:
            await interaction.edit_original_response(content="Problem fetching data")
            return
        
        results = json.loads(http_response.content)

        if len(results) == 0:
            await interaction.edit_original_response(content="No results found")
            return
        
        message = "\n".join(self.pretty_hoogle_result(result) for result in results)
        await interaction.edit_original_response(content=message)
    
async def setup(bot: commands.Bot):
    await bot.add_cog(Hoogle(bot))
    
