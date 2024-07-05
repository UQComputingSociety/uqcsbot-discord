from datetime import datetime
from typing import List, Dict, Literal, Tuple, Optional
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

SITE_URLS: Dict[str, str] = {
    "couponese": COUPONESE_DOMINOS_URL,
    "frugalfeeds": FRUGAL_FEEDS_DOMINOS_URL,
}

CouponSource = Literal["frugalfeeds", "couponese", "both"]

SingleSource = Literal[
    "frugalfeeds",
    "couponese",
]


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
        ignore_expiry="Indicates to include coupons that have expired. Defaults to False.",
        keywords="Words to search for within the coupon. All coupons descriptions will mention at least one keyword.",
        source="Website to source coupons from (couponese or frugalfeeds). Defaults to both.",
    )
    @yelling_exemptor(input_args=["keywords"])
    async def dominoscoupons(
        self,
        interaction: discord.Interaction,
        number_of_coupons: int = 5,
        ignore_expiry: bool = False,
        keywords: str = "",
        source: CouponSource = "both",
    ):
        """
        Returns a list of dominos coupons
        """

        switch_source: Dict[str, SingleSource] = {
            COUPONESE_DOMINOS_URL: "frugalfeeds",
            FRUGAL_FEEDS_DOMINOS_URL: "couponese",
        }

        coupons: List[Coupon] = []
        failed_urls: List[str] = []

        if number_of_coupons < 1 or number_of_coupons > MAX_COUPONS:
            await interaction.response.send_message(
                content=f"You can't have that many coupons. Try a number between 1 and {MAX_COUPONS}.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        coupons, failed_urls = _get_coupons(
            number_of_coupons, ignore_expiry, keywords.split(), source
        )

        if len(failed_urls) == NUMBER_WEBSITES:
            await interaction.edit_original_response(
                content=f"Unfortunately, it looks like both coupon websites are down right now."
            )
            return
        elif len(failed_urls) == 1:
            if source == "both":
                await interaction.edit_original_response(
                    content=f"Unfortunately, it looks like one website is down right now ({failed_urls[0]}). Trying another!"
                )
                # Switch source so user doesn't get misled in embed description or when coupon search turns up empty
                new_source: Optional[SingleSource] = switch_source.get(failed_urls[0])
                if new_source:
                    source = new_source
            else:
                await interaction.edit_original_response(
                    content=f"It looks like that website is down right now. Try changing site with the `source` command. ({failed_urls[0]})"
                )
                return

        if not coupons:
            if source == "both":
                content_str = "Could not find any coupons matching the given arguments from both websites."
            elif len(failed_urls) == 1:
                content_str = f"Searched {source} as the other website is down ({failed_urls[0]}) and could not find any coupons matching the given arguments."
            else:
                content_str = f"Could not find any coupons matching the given arguments from {source}. You can try changing the website through the `source` command."
            await interaction.edit_original_response(content=content_str)
            return

        if source == "both":
            description_string = f"Sourced from [FrugalFeeds]({FRUGAL_FEEDS_DOMINOS_URL}) and [Couponese]({COUPONESE_DOMINOS_URL})"
        elif source == "couponese":
            description_string = f"Sourced from [Couponese]({COUPONESE_DOMINOS_URL})"
        else:
            description_string = (
                f"Sourced from [FrugalFeeds]({FRUGAL_FEEDS_DOMINOS_URL})"
            )

        if keywords:
            description_string += f"\nKeywords: *{keywords}*"

        embed = discord.Embed(
            title="Domino's Coupons",
            description=description_string,
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
    n: int,
    ignore_expiry: bool,
    keywords: List[str],
    source: CouponSource,
) -> Tuple[List[Coupon], List[str]]:
    """
    Returns a list of n Coupons
    """

    failed_urls: List[str] = []
    coupons: List[Coupon] = []
    sources: List[SingleSource]

    if source == "both":
        sources = ["couponese", "frugalfeeds"]
    else:
        sources = [source]

    for source in sources:
        try:
            coupons.extend(_get_coupons_from_page(source))
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
                failed_urls.append(request_url)

            if isinstance(error, HTTPResponseException):
                logging.warning(
                    f"Received a HTTP response code {error.http_code}. Error information: {error}"
                )
                failed_urls.append(error.url)

    if not ignore_expiry:
        coupons = [coupon for coupon in coupons if coupon.is_valid()]

    # Remove duplicates
    unique_coupons: List[Coupon] = []
    unique_codes: List[str] = []
    for coupon in coupons:
        if coupon.code not in unique_codes:
            unique_codes.append(coupon.code)
            unique_coupons.append(coupon)
    coupons = unique_coupons

    if keywords:
        coupons = [
            coupon
            for coupon in coupons
            if any(coupon.keyword_matches(keyword) for keyword in keywords)
        ]

    random.shuffle(coupons)

    return coupons[:n], failed_urls


def _get_coupons_from_page(source: SingleSource) -> List[Coupon]:
    """
    Strips results from html page and returns a list of Coupon(s)
    """

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

    coupons: List[Coupon] = []
    url = SITE_URLS[source]

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
        description_container = soup_coupon.find(class_=siteclass.get("description"))
        code_container = soup_coupon.find(class_=siteclass.get("code"))

        if not expiry_date_container or not description_container or not code_container:
            continue

        expiry_date_str: str = expiry_date_container.get_text(strip=True)
        description: str = description_container.get_text(strip=True)
        code: str = code_container.get_text(strip=True)

        # Take separators out and check if we're getting a valid
        # code - intended to filter out unrelated
        # advertisements posted on FrugalFeeds coupons page
        temp_code: str = code.replace(",", "").replace(" ", "")
        if not temp_code.isdigit():
            continue

        # Keep formatting same for coupons with multiple codes
        if source == "frugalfeeds":
            code = code.replace(",", ", ")
        if source == "couponese":
            code = code.replace(" ", ", ")

        if url == FRUGAL_FEEDS_DOMINOS_URL:
            date_values: List[str] = expiry_date_str.split()
            try:
                # Convert shortened month to numerical value
                month: int = datetime.strptime(date_values[1], "%b").month
                expiry_date_str = "{year}-{month}-{day}".format(
                    year=int(date_values[2]), month=month, day=int(date_values[0])
                )
            except (ValueError, IndexError):
                pass

        coupon = Coupon(code, expiry_date_str, description)
        coupons.append(coupon)

    return coupons


async def setup(bot: UQCSBot):
    await bot.add_cog(DominosCoupons(bot))
