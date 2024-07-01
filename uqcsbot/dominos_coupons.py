from datetime import datetime
from typing import List, Dict, Literal
import logging
import requests
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
import random

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.bot import UQCSBot
from uqcsbot.yelling import yelling_exemptor

MAX_COUPONS = 10  # Prevents abuse
NUMBER_WEBSITES = 2
COUPONESE_DOMINOS_URL = "https://www.couponese.com/store/dominos.com.au/"
FRUGAL_FEEDS_DOMINOS_URL = "https://www.frugalfeeds.com.au/dominos/"


class HTTPResponseException(Exception):
    """
    An exception for when a HTTP response is not requests.codes.ok
    """

    def __init__(self, http_code: int, url: str, *args: object) -> None:
        super().__init__(*args)
        self.http_code = http_code
        self.url = url


class DominosCoupons(commands.Cog):
    def __init__(self, bot: UQCSBot):
        self.bot = bot

    @app_commands.command()
    @app_commands.describe(
        number_of_coupons="The number of coupons to return. Defaults to 5 with max 10.",
        ignore_expiry="Indicates to include coupons that have expired. Defaults to True.",
        keywords="Words to search for within the coupon. All coupons descriptions will mention at least one keyword.",
        source="Website to source coupons from (couponese or frugalfeeds). Defaults to both.",
    )
    @yelling_exemptor(input_args=["keywords"])
    async def dominoscoupons(
        self,
        interaction: discord.Interaction,
        number_of_coupons: int = 5,
        ignore_expiry: bool = True,
        keywords: str = "",
        source: Literal["both", "couponese", "frugalfeeds"] = "both",
    ):
        """
        Returns a list of dominos coupons
        """

        website_urls: Dict[str, str] = {
            "couponese": COUPONESE_DOMINOS_URL,
            "frugalfeeds": FRUGAL_FEEDS_DOMINOS_URL,
            "both": FRUGAL_FEEDS_DOMINOS_URL,
        }

        if number_of_coupons < 1 or number_of_coupons > MAX_COUPONS:
            await interaction.response.send_message(
                content=f"You can't have that many coupons. Try a number between 1 and {MAX_COUPONS}.",
                ephemeral=True,
            )
            return

        if source != "both":
            if source != "couponese" and source != "frugalfeeds":
                await interaction.response.send_message(
                    content=f"That website isn't recognised. Try couponese or frugalfeeds.",
                    ephemeral=True,
                )
                return

        await interaction.response.defer(thinking=True)

        coupons: List[Coupon] = []
        stored_url: str = " "

        for tries in range(0, NUMBER_WEBSITES):
            try:
                coupons = _get_coupons(
                    number_of_coupons, ignore_expiry, keywords.split(), source
                )
                break
            except (RequestException, HTTPResponseException) as error:
                if isinstance(error, RequestException):
                    request_url: str = (
                        error.request.url
                        if error.request and error.request.url
                        else "Unknown site."
                    )
                    resp_content = (
                        error.response.content
                        if error.response
                        else "No response error given."
                    )
                    logging.warning(
                        f"Could not connect to dominos coupon site ({request_url}): {resp_content}"
                    )
                    stored_url = request_url

                if isinstance(error, HTTPResponseException):
                    logging.warning(
                        f"Received a HTTP response code {error.http_code}. Error information: {error}"
                    )
                    stored_url = error.url

                if source != "both" and tries == 0:
                    await interaction.edit_original_response(
                        content=f"Looks like that website ({stored_url}) isn't working. Try changing the website through the `source` command."
                    )
                    return

                elif source == "both" or tries > 0:
                    if tries == 0:
                        await interaction.edit_original_response(
                            content=f"Looks like that website ({stored_url}) didn't work.. trying another."
                        )
                        if stored_url == COUPONESE_DOMINOS_URL:
                            source = "frugalfeeds"
                        elif stored_url == FRUGAL_FEEDS_DOMINOS_URL:
                            source = "couponese"
                    else:
                        await interaction.edit_original_response(
                            content=f"Unfortunately, it looks like both coupon websites are down right now."
                        )
                        return

        if not coupons:
            await interaction.edit_original_response(
                content=f"Could not find any coupons matching the given arguments from {source}."
            )
            return

        embed = discord.Embed(
            title="Domino's Coupons",
            url=(website_urls.get(source)),
            description=f"Keywords: *{keywords}*" if keywords else None,
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


def _get_coupons(
    n: int, ignore_expiry: bool, keywords: List[str], source: str
) -> List[Coupon]:
    """
    Returns a list of n Coupons
    """

    coupons: List[Coupon] = _get_coupons_from_page(source)

    if not ignore_expiry:
        coupons = [coupon for coupon in coupons if coupon.is_valid()]

    if keywords:
        coupons = [
            coupon
            for coupon in coupons
            if any(coupon.keyword_matches(keyword) for keyword in keywords)
        ]

    random.shuffle(coupons)

    return coupons[:n]


def _get_coupons_from_page(source: str) -> List[Coupon]:
    """
    Strips results from html page and returns a list of Coupon(s)
    """
    urls: List[str] = []
    coupons: List[Coupon] = []

    website_coupon_classes: Dict[str, Dict[str, str]] = {
        COUPONESE_DOMINOS_URL: {
            "expiry": "ov-expiry",
            "description": "ov-desc",
            "code": "ov-code",
        },
        FRUGAL_FEEDS_DOMINOS_URL: {
            "expiry": "column-3",
            "description": "column-2",
            "code": "column-1",
        },
    }

    if source == "couponese":
        urls.append(COUPONESE_DOMINOS_URL)
    elif source == "frugalfeeds":
        urls.append(FRUGAL_FEEDS_DOMINOS_URL)
    else:
        urls = [FRUGAL_FEEDS_DOMINOS_URL, COUPONESE_DOMINOS_URL]

    for url in urls:
        http_response: requests.Response = requests.get(url)
        if http_response.status_code != requests.codes.ok:
            raise HTTPResponseException(http_response.status_code, url)

        soup = BeautifulSoup(http_response.content, "html.parser")
        soup_coupons: List[BeautifulSoup] = []

        if url == COUPONESE_DOMINOS_URL:
            soup_coupons = soup.find_all(class_="ov-coupon")
        elif url == FRUGAL_FEEDS_DOMINOS_URL:
            tables = soup.select('[class^="tablepress"]')
            for table in tables:
                # Headers have stuff we don't want
                rows = table.find_all("tr")[1:]
                soup_coupons.extend(rows)

        siteclass: Dict[str, str] = website_coupon_classes.get(url, {})

        for soup_coupon in soup_coupons:
            expiry_date_container = soup_coupon.find(class_=siteclass.get("expiry"))
            description_container = soup_coupon.find(
                class_=siteclass.get("description")
            )
            code_container = soup_coupon.find(class_=siteclass.get("code"))

            if (
                not expiry_date_container
                or not description_container
                or not code_container
            ):
                continue

            expiry_date_str: str = expiry_date_container.get_text(strip=True)
            description: str = description_container.get_text(strip=True)
            code: str = code_container.get_text(strip=True)

            coupon = Coupon(code, expiry_date_str, description)
            coupons.append(coupon)

    return coupons


async def setup(bot: UQCSBot):
    await bot.add_cog(DominosCoupons(bot))
