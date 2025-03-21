import json
import re
import time
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


class HTTPResponseException(Exception):
    """
    An exception for when a HTTP response is not requests.codes.ok
    """

    def __init__(self, http_code: int, url: str, *args: object) -> None:
        super().__init__(*args)
        self.http_code = http_code
        self.url = url


class Coupon:
    def __init__(self, code: str, expiry_date: str, description: str, method: str = None) -> None:
        self.code = code
        self.expiry_date = expiry_date
        self.description = description
        self.method = method

    def __repr__(self) -> str:
        return f"{self.code}: {self.description} (expires {self.expiry_date}, {self.method})"

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

    def method_matches(self, method: str) -> bool:
        return self.method is None or method in self.method


BASE_URL = "https://www.dominos.com.au"
STORE_LIST_URL = BASE_URL + "/dynamicstoresearchapi/getlimitedstores/10/"

MAX_RETRIES = 5


def retry_request(request_func, url: str, key: str = None, max_retries: int = MAX_RETRIES, **kwargs):
    """
    Retries a request function with exponential backoff.

    Args:
        request_func (function): The request function to call.
        url (str): The URL to request.
        key (str): The API key to use for the request.
        max_retries (int): The maximum number of retries.
        **kwargs: Additional arguments for the request.

    Returns:
        Response: The response object or None if all retries fail.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36',
        'Accept': 'application/json'
    }
    if key:
        headers['Authorization'] = f"Bearer {key}"
    for count in range(max_retries):
        try:
            response = request_func(url, headers=headers, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Attempt {count + 1} failed: {str(e)}")
            time.sleep(1 << count)
    return None


class Store:
    def __init__(self, store: Dict[str, str]) -> None:
        # I just threw anything useful looking in here
        self.name: str = store.get("Name")
        self.phone_no: str = store.get("PhoneNo")
        self.address: str = (store.get("Address", {}).get("FullAddress")
                        .replace("\r", "").replace("\n", ", ").replace(", , ", ", "))
        self.service_methods: dict[str, bool] = store.get("ServiceMethods")
        self.ordering_methods: dict[str, bool] = store.get("OrderingMethods")
        self.coordinates: dict[str, float] = store.get("GeoCoordinates")
        self.opening_hours: dict[dict] = store.get("OpeningHours")
        self.cook_time: str = store.get("PulseConfig", {}).get("CookTime")
        self.offers_url = store.get("Properties", {}).get("offersUrl")

    def __repr__(self) -> str:
        return f"{self.name} ({self.address})"

    def is_open(self, checking_time: datetime) -> bool:
        now = datetime.now()
        if (checking_time - now).days > 7:
            print("Checking time is more than 7 days in the future")
            raise ValueError("Checking time is more than 7 days in the future")
        return NotImplemented

    def available_method(self, method: str) -> bool:
        return self.service_methods.get(method, False)

    def has_coupons(self) -> bool:
        return bool(self.offers_url)

    def get_coupon_link(self) -> str:
        if self.offers_url:
            return BASE_URL + self.offers_url
        raise ValueError("No coupon link available")

    def get_coupons(self) -> List[Coupon]:
        url = self.get_coupon_link()
        if not url:
            return []
        http_response: requests.Response = retry_request(requests.get, url, timeout=10)
        if http_response.status_code != requests.codes.ok:
            raise HTTPResponseException(http_response.status_code, url)

        soup = BeautifulSoup(http_response.content, "html.parser")
        soup_coupons = soup.find_all(class_="special-offer-anz")

        coupons = []
        for coupon in soup_coupons:
            coupon_code = (coupon.find(class_="offer-code-anz").get_text(strip=True)
                           .replace('Offer Code:', '').strip())
            coupon_expiry = re.findall(r'\d{2}-\d{2}-\d{2,}',
                           coupon.find(class_="offer-disclaimer-anz").get_text())[0]
            coupon_description = coupon.find(class_="offer-title-anz").get_text(strip=True)
            coupon_method = coupon.find(class_="service-method-anz").get_text(strip=True)
            coupons.append(Coupon(coupon_code, coupon_expiry, coupon_description, coupon_method))

        return coupons


def get_stores(search_term) -> Optional[List[Store]]:
    url = STORE_LIST_URL + search_term

    response = retry_request(requests.get, url, timeout=10)
    if not response:
        print("Failed to get stores")
        return None
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {str(e)}")
        return None
    stores: List[Store] = []
    for store in data["Data"]:
        stores.append(Store(store))
    return stores


if __name__ == "__main__":
    s = get_stores("ST LUCIA")[0]
    print(s.name)
    print(s.address)
    print(s.phone_no)
    print(s.coordinates)
    print(s.service_methods)
    print(s.get_coupon_link())
    for coupon in s.get_coupons():
        # print(coupon)
        print(coupon.code)
        print(coupon.description)
        print(coupon.expiry_date)
        print(coupon.method)
        print()
    # print(s.get_coupons())
    # print(s.__dict__)
    print()
