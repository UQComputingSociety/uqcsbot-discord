import requests
import re
import html

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.bot import UQCSBot

XKCD_BASE_URL = "https://xkcd.com/"

XKCD_FETCH_ERROR = (-1, "", "", "") # xkcd failed to fetch page
XKCD_PARSE_ERROR = (-2, "", "", "") # xkcd failed to parse page

class Xkcd(commands.Cog):

    def __init__(self, bot: UQCSBot):
        self.bot = bot

    @app_commands.command(name="xkcd")
    @app_commands.describe(
        number="The xkcd number to fetch (optional)",
    )
    async def xkcd_command(
        self, 
        interaction: discord.Interaction, 
        number: Optional[int] = None
    ) -> None:
        """
        Returns a random xkcd comic or the comic with the given number.
        """

        # If number is given, check if its a valid number
        if number is not None and number <= 0:
            await interaction.response.send_message("Invalid xkcd number (must be positive)")
            return

        # Create the url to fetch the xkcd data from
        url = ""
        if number is not None:
            url = f"{XKCD_BASE_URL}{number}/"
        else:
            url = "https://c.xkcd.com/random/comic/"

        # Get the xkcd data
        xkcd_num, xkcd_title, xkcd_desc, xkcd_img = self.get_xkcd_data(url)

        # Check if the xkcd data failed to fetch
        if xkcd_num == XKCD_FETCH_ERROR[0]:
            await interaction.response.send_message("Failed to fetch xkcd page")
            return
        elif xkcd_num == XKCD_PARSE_ERROR[0]:
            await interaction.response.send_message("Failed to parse xkcd page data")
            return

        # Create a custom embed for the xkcd comic
        message = discord.Embed()
        message.title = f"{xkcd_num}: {xkcd_title}"
        message.description = xkcd_desc
        message.url = f"{XKCD_BASE_URL}{xkcd_num}"
        message.set_image(url=xkcd_img)
        message.set_footer(text="xkcd.com")

        # Send it!
        await interaction.response.send_message(embed=message)

    def get_xkcd_data(self, url: str) -> (int, str, str, str):
        """
        Returns the xkcd data from the given url.

        :param url: The url to fetch the xkcd data from
        :return: A tuple containing the xkcd number, title, description and image url
        """

        # Get the xkcd page
        response = requests.get(url)
        if response.status_code != 200:
            return XKCD_FETCH_ERROR
        
        data = str(response.content)

        # Regexes to find the xkcd number, title, description and image url
        num_search = re.search(r"https:\/\/xkcd\.com\/([0-9]+)\/", data)
        title_search = re.search(r'(?<=<div id="ctitle">)(.*?)(?=</div>)', data)
        desc_search = re.search(r'(?<=<div id="comic">).*?title="(.*?)".*?(?=</div>)', data)
        img_search = re.search(r'(?<=Image URL \(for hotlinking\/embedding\): <a href= ")(.*?)(?=">)', data)

        # If any of the regexes failed, return an error
        if not num_search or not title_search or not desc_search or not img_search:
            return XKCD_PARSE_ERROR

        # Unescape the title and description from html entities
        title_str = html.unescape(title_search.group(1))
        desc_str = html.unescape(desc_search.group(1))

        return (int(num_search.group(1)), title_str, desc_str, img_search.group(1))


async def setup(bot: UQCSBot):
    cog = Xkcd(bot)
    await bot.add_cog(cog)
