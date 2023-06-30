from datetime import datetime
from typing import List
import logging
import requests
from requests.exceptions import RequestException
from bs4 import BeautifulSoup

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.bot import UQCSBot


MAX_COUPONS = 10  # Prevents abuse
COUPONESE_DOMINOS_URL = "https://www.couponese.com/store/dominos.com.au/"


class DominosCoupons(commands.Cog):
    def __init__(self, bot: UQCSBot):
        self.bot = bot

    @app_commands.command()
    @app_commands.describe(
        number_of_coupons="The number of coupons to return. Defaults to 5 with max 10.",
        ignore_expiry="Indicates to include coupons that have expired. Defaults to True.",
        keywords="Words to search for within the coupon. All coupons descriptions will mention at least one keyword.",
    )
    async def dominoscoupons(
        self,
        interaction: discord.Interaction,
        number_of_coupons: int = 5,
        ignore_expiry: bool = True,
        keywords: str = "",
    ):
        """
        Returns a list of dominos coupons
        """
        await interaction.response.defer(thinking=True)

        if number_of_coupons < 1 or number_of_coupons > MAX_COUPONS:
            await interaction.edit_original_response(
                content=f"You can't have that many coupons. Try a number between 1 and {MAX_COUPONS}."
            )
            return
        try:
            coupons = _get_coupons(number_of_coupons, ignore_expiry, keywords.split())
        except RequestException as error:
            logging.warning(
                f"Could not connect to dominos coupon site ({COUPONESE_DOMINOS_URL}): {error.response.content}"
            )
            await interaction.edit_original_response(
                content=f"Sadly could not reach the coupon website (<{COUPONESE_DOMINOS_URL}>)..."
            )
            return
        except HTTPResponseException as error:
            logging.warning(
                f"Received a HTTP response code that was not OK (200), namely ({error.http_code}). Error information: {error}"
            )
            await interaction.edit_original_response(
                content=f"Could not find the coupons on the coupon website (<{COUPONESE_DOMINOS_URL}>)..."
            )
            return

        if not coupons:
            await interaction.edit_original_response(
                content=f"Could not find any coupons matching the given arguments from the coupon website (<{COUPONESE_DOMINOS_URL}>)."
            )
            return

        embed = discord.Embed(
            title="Domino's Coupons",
            url=COUPONESE_DOMINOS_URL,
            description=f"Keywords: {keywords}",
            timestamp=datetime.now(),
        )
        for coupon in coupons:
            embed.add_field(
                name=coupon.code,
                value=f"{coupon.description} *[Expires: {coupon.expiry_date}]*",
                inline=False,
            )
        await interaction.edit_original_response(embed=embed)


class Coupon:
    def __init__(self, code: str, expiry_date: str, description: str) -> None:
        self.code = code
        self.expiry_date = expiry_date
        self.description = description

    def is_valid(self) -> bool:
        try:
            expiry_date = datetime.strptime(self.expiry_date, "%Y-%m-%d")
            now = datetime.now()
            return all(
                [
                    expiry_date.year >= now.year,
                    expiry_date.month >= now.month,
                    expiry_date.day >= now.day,
                ]
            )
        except ValueError:
            return True

    def keyword_matches(self, keyword: str) -> bool:
        return keyword.lower() in self.description.lower()


class HTTPResponseException(Exception):
    """
    An exception for when a HTTP response is not requests.codes.ok
    """

    def __init__(self, http_code: int, *args: object) -> None:
        super().__init__(*args)
        self.http_code = http_code


def _get_coupons(n: int, ignore_expiry: bool, keywords: List[str]) -> List[Coupon]:
    """
    Returns a list of n Coupons
    """

    coupons = _get_coupons_from_page()

    if not ignore_expiry:
        coupons = [coupon for coupon in coupons if coupon.is_valid()]

    if keywords:
        coupons = [
            coupon
            for coupon in coupons
            if any(coupon.keyword_matches(keyword) for keyword in keywords)
        ]
    return coupons[:n]


def _get_coupons_from_page() -> List[Coupon]:
    """
    Strips results from html page and returns a list of Coupon(s)
    """
    http_response = requests.get(COUPONESE_DOMINOS_URL)
    if http_response.status_code != requests.codes.ok:
        raise HTTPResponseException(http_response.status_code)
    soup = BeautifulSoup(http_response.content, "html.parser")
    soup_coupons = soup.find_all(class_="ov-coupon")

    coupons: List[Coupon] = []

    for soup_coupon in soup_coupons:
        expiry_date_str = soup_coupon.find(class_="ov-expiry").get_text(strip=True)
        description = soup_coupon.find(class_="ov-desc").get_text(strip=True)
        code = soup_coupon.find(class_="ov-code").get_text(strip=True)
        coupon = Coupon(code, expiry_date_str, description)
        coupons.append(coupon)

    return coupons


async def setup(bot: UQCSBot):
    await bot.add_cog(DominosCoupons(bot))
