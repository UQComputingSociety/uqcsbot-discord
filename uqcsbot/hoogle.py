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
    
    def get_hoogle_page(self, type_sig: str) -> str:
        return f"https://hoogle.haskell.org/?hoogle={html.unescape(type_sig)}"

    def pretty_hoogle_result(self, result: dict) -> str:
        url = result['url']
        type_sig = re.sub('<[^<]+?>', '', result['item']).replace('&gt;', '>').replace('&#39;', "'")

        return f"`{type_sig}` [link]({url})"
    
    
    
    @app_commands.command()
    @app_commands.describe(search="Function name or type signature to search for")
    async def hoogle(self, interaction: discord.Interaction, search: str):
        """
        Queries the Hoogle Haskell API search engine, searching Haskell libraries by either function name 
        or approximate type signature. Retrieves up to 10 results.
        """
        # Note: verbose feature not implemented as it may exceed discord's message length limit
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

        #test out embed
        embed = discord.Embed(
            title = search,
            url = self.get_hoogle_page(search),
            description = message,
            color = 0x800080
        )
        await interaction.edit_original_response(embed=embed)
    
async def setup(bot: commands.Bot):
    await bot.add_cog(Hoogle(bot))
    
