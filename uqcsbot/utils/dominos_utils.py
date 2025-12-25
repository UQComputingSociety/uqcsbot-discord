import json
import logging
import random
import re
import time
from datetime import datetime
from typing import List, Dict, Optional, Callable, Any

import requests
from bs4 import BeautifulSoup

MAX_RETRIES = 5


def retry_request(
    request_func: Callable[..., requests.Response],
    url: str,
    key: Optional[str] = None,
    max_retries: int = MAX_RETRIES,
    **kwargs: Any,
) -> Optional[requests.Response]:
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
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36",
        "Accept": "application/json",
    }
    if key:
        headers["Authorization"] = f"Bearer {key}"
    for count in range(max_retries):
        try:
            return request_func(url, headers=headers, **kwargs)
        except requests.exceptions.RequestException as e:
            # Exponential backoff
            logging.warning(f"Attempt {count + 1} failed: {str(e)}")
            time.sleep(1 << count)
    logging.warning(f"Could not connect to dominos coupon site ({url})")
    return None


BASE_URL = "https://www.dominos.com.au"
STORE_LIST_URL = BASE_URL + "/dynamicstoresearchapi/getlimitedstores/10/"


class Coupon:
    """
    A class representing a Domino's coupon.
    """

    def __init__(
        self,
        code: str,
        expiry_date: str,
        description: str,
        method: Optional[str] = None,
    ) -> None:
        self.code = code
        self.expiry_date = expiry_date
        self.description = description
        self.method = method

    def __repr__(self) -> str:
        return f"{self.code}: {self.description} (expires {self.expiry_date}, {self.method})"

    def is_valid(self, checking_time: datetime) -> bool:
        """
        Check if the coupon is valid at the given time.
        Args:
            checking_time (datetime): The time to check if the coupon is valid.
        Returns:
            bool: True if the coupon is valid, False otherwise.
        """
        try:
            expiry_date = datetime.strptime(self.expiry_date, "%d-%m-%y")
            return expiry_date > checking_time
        except ValueError:
            # If the expiry date is not in the expected format, assume it is valid
            return True

    def keyword_matches(self, keyword: str) -> bool:
        """
        Check if the coupon description contains the given keyword.
        Args:
            keyword:
        Returns:
            bool: True if the keyword is in the description, False otherwise.
        """
        return keyword.lower() in self.description.lower().replace(" ", "")

    def method_matches(self, method: str) -> bool:
        """
        Check if the coupon method matches the given method.
        This is usually "Delivery Only", "Pick Up Only", or "Delivery or Pick Up".
        Uses loose matching.
        Args:
            method (str): The service method to check.
        Returns:
            bool: True if the method matches, False otherwise.
        """
        if not self.method:
            return True
        return method.lower().replace(" ", "") in self.method.lower().replace(" ", "")


class Store:
    """
    A class representing a Domino's store.
    """

    def __init__(self, store: Dict[str, Any]) -> None:
        # I just threw anything useful looking in here
        self.name: str = store.get("Name", "DOMINO'S")
        self.phone_no: Optional[str] = store.get("PhoneNo")
        self.address: Optional[str] = (
            store.get("Address", {})
            .get("FullAddress")
            .replace("\r", "")
            .replace("\n", ", ")
            .replace(", , ", ", ")
        )
        self.service_methods: Optional[dict[str, bool]] = store.get("ServiceMethods")
        self.ordering_methods: dict[str, bool] = store.get("OrderingMethods", {})
        self.coordinates: Optional[dict[str, float]] = store.get("GeoCoordinates")
        self.opening_hours: list[dict[str, str]] = store.get("OpeningHours", [])
        self.cook_time: Optional[str] = store.get("PulseConfig", {}).get("CookTime")
        self.offers_url: Optional[str] = store.get("Properties", {}).get("offersUrl")

    def __repr__(self) -> str:
        return f"{self.name} ({self.address})"

    def matches(self, search_term: str) -> bool:
        """
        Check if the store name matches the given name.

        Args:
            search_term (str): The name to match.

        Returns:
            bool: True if the names match, False otherwise.
        """
        return self.name.lower().strip() == search_term.lower().strip()

    def is_open(self, checking_time: datetime) -> bool:
        """
        Check if the store is open at the given time.

        Args:
            checking_time (datetime): The time to check.

        Returns:
            bool: True if the store is open, False otherwise. None if no opening hours are known.
        Raises:
            ValueError: If the checking_time is not a datetime object
                        or the checking_time is more than 7 days in the future.
        """
        if not self.opening_hours:
            raise ValueError("No opening hours available")
        now = datetime.now()
        if (checking_time - now).days > 7 or (checking_time - now).days < 0:
            raise ValueError("Checking time is more than 7 days in the future")
        for day in self.opening_hours:
            open_time: datetime = datetime.fromisoformat(day["Open"]).replace(
                tzinfo=None
            )
            close_time: datetime = datetime.fromisoformat(day["Close"]).replace(
                tzinfo=None
            )
            if open_time <= checking_time <= close_time:
                return True
        return False

    def next_opening_time(self, checking_time: datetime) -> Optional[datetime]:
        """
        Returns the next opening time for the store.

        Args:
            checking_time (datetime): The time to check.

        Returns:
            datetime: The next opening time for the store.
        """
        if not self.opening_hours:
            # No opening hours available
            return None
        now = datetime.now()
        if (checking_time - now).days > 7 or (checking_time - now).days < 0:
            # Checking time is more than 7 days in the future
            return None
        opening_times: list[datetime] = [
            datetime.fromisoformat(day["Open"]).replace(tzinfo=None)
            for day in self.opening_hours
        ]
        return min(
            [open_time for open_time in opening_times if open_time <= checking_time]
        )

    def next_closing_time(self, checking_time: datetime) -> Optional[datetime]:
        """
        Returns the next closing time for the store.

        Args:
            checking_time (datetime): The time to check.

        Returns:
            datetime: The next closing time for the store.
        """
        if not self.opening_hours:
            # No opening hours available
            return None
        now = datetime.now()
        if (checking_time - now).days > 7 or (checking_time - now).days < 0:
            # Checking time is more than 7 days in the future
            return None
        closing_times = [day["Close"] for day in self.opening_hours]
        closing_times = [
            datetime.fromisoformat(close_time).replace(tzinfo=None)
            for close_time in closing_times
        ]
        return min(
            [close_time for close_time in closing_times if close_time >= checking_time]
        )

    def available_method(self, method: str) -> Optional[bool]:
        """
        Check if the store has the given service method available.
        They are usually "Pickup", "Delivery" or "DineIn".

        Args:
            method: The service method to check.

        Returns:
            bool: Whether the store has the given method available. None otherwise.
        """
        if not self.service_methods:
            # No service methods available
            return None
        return self.service_methods.get(method)

    def has_coupons(self) -> bool:
        """
        Check if the store has coupons available.
        Not complete at the moment, but might be useful in the future.

        Returns:
            bool: True if the store has coupons available, False otherwise.
        """
        return bool(self.offers_url)

    def get_coupon_link(self) -> str:
        """
        Get link to the coupon page for the store.

        Returns:
            str: The coupon link for the store.
        """
        if self.offers_url:
            return BASE_URL + self.offers_url
        raise ValueError("No coupon link available")

    def _get_coupons(self) -> List[Coupon]:
        """
        Get the coupons for the store.

        Returns:
            list[Coupon]: A list of coupons for the store.
        """
        url = self.get_coupon_link()
        if not url:
            return []
        http_response: Optional[requests.Response] = retry_request(
            requests.get, url, timeout=10
        )
        if not http_response:
            # Failed to get coupons
            return []

        soup = BeautifulSoup(http_response.content, "html.parser")
        soup_coupons = soup.find_all(class_="special-offer-anz")

        coupons: list[Coupon] = []
        for coupon in soup_coupons:
            coupon_code = (
                coupon.find(class_="offer-code-anz")
                .get_text(strip=True)
                .replace("Offer Code:", "")
                .strip()
            )
            coupon_expiry = re.findall(
                r"\d{2}-\d{2}-\d{2,}",
                coupon.find(class_="offer-disclaimer-anz").get_text(),
            )[0]
            coupon_description = coupon.find(class_="offer-title-anz").get_text(
                strip=True
            )
            coupon_method = coupon.find(class_="service-method-anz").get_text(
                strip=True
            )
            coupons.append(
                Coupon(coupon_code, coupon_expiry, coupon_description, coupon_method)
            )

        return coupons

    def get_filtered_coupons(
        self,
        service_method: str = "Any",
        checking_time: Optional[datetime] = None,
        keywords: Optional[str] = None,
        count: Optional[int] = None,
    ) -> List[Coupon]:
        """
        Gets a list of coupons for the store that match the given filters.
        This is a wrapper for _get_coupons that filters the results based on the given parameters.
        If defaults are used, it will return all coupons.

        Args:
            service_method (str): Filter to coupons that support this service method.
                This is usually "Pickup", "Delivery" or "DineIn".
            checking_time (datetime): Filter to coupons that are valid at this time.
            keywords (str): Filter to coupons that match this keyword.
            count (int): The maximum number of coupons to return. Defaults to all coupons.

        Returns:
            List[Coupon]: A list of coupons that match the search term and filter, or None if there was an error.
        """
        coupons = self._get_coupons()
        if not coupons:
            return coupons
        if service_method != "Any":
            coupons = [
                coupon for coupon in coupons if coupon.method_matches(service_method)
            ]
        if checking_time:
            coupons = [coupon for coupon in coupons if coupon.is_valid(checking_time)]
        if keywords:
            matching_coupons: list[Coupon] = []
            for coupon in coupons:
                if any(coupon.keyword_matches(keyword) for keyword in keywords.split()):
                    matching_coupons.append(coupon)
            coupons = matching_coupons
        if count:
            random.shuffle(coupons)
            coupons = coupons[:count]
        return coupons


def _get_stores(search_term: str) -> List[Store]:
    """
    Gets a list of stores from the Domino's API.

    Args:
        search_term: The term to search for. This can be a suburb, city, or postcode, or really anything.

    Returns:
        list[Store]: A list of stores that match the search term, or None if there was an error.
    """
    url: str = STORE_LIST_URL + search_term

    response = retry_request(requests.get, url, timeout=10)
    if not response:
        # Failed to get stores
        return []
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        logging.warning(f"Failed to parse JSON response from Domino's API: {e}")
        return []
    stores: List[Store] = []
    for store in data["Data"]:
        stores.append(Store(store))
    return stores


def get_filtered_stores(
    search_term: str,
    service_method: str = "Any",
    open_at_time: Optional[datetime] = None,
    has_coupons: bool = False,
    count: Optional[int] = None,
) -> List[Store]:
    """
    Get a list of stores that match the search term and filters.
    This is a wrapper for _get_stores that filters the results based on the given parameters.
    If defaults are used, it will return all stores that match the search term.

    Args:
        search_term (str): The term to search for.
        service_method (str): Filter to stores that support this service method.
            This is usually "Pickup", "Delivery" or "DineIn".
        open_at_time (datetime): Filter to stores that are open at this time.
        has_coupons (bool): Filter to stores that have coupons available.
        count (int): The maximum number of stores to return. Defaults to all stores.

    Returns:
        list[Store]: A list of stores that match the search term and filter, or None if there was an error.
    """
    stores = _get_stores(search_term)
    if not stores:
        return stores
    if service_method != "Any":
        stores = [store for store in stores if store.available_method(service_method)]
    if open_at_time:
        open_stores: list[Store] = []
        for store in stores:
            try:
                if store.is_open(open_at_time):
                    open_stores.append(store)
            except ValueError:
                # If the store has no opening hours, we assume it is open
                open_stores.append(store)
                continue
        stores = open_stores
    if has_coupons:
        stores = [store for store in stores if store.has_coupons()]
    if count:
        stores = stores[:count]
    return stores


if __name__ == "__main__":
    for s in get_filtered_stores("ST LUCIA"):
        # s = get_stores("ST LUCIA")[0]
        print(s.name)
        print(s.address)
        # print(s.phone_no)
        # print(s.coordinates)
        # print(s.service_methods)
        # print(s.opening_hours)
        print(s.is_open(datetime.now()))
        # print(s.get_coupon_link())
        # for coupon in s.get_coupons():
        #     # print(coupon)
        #     print(coupon.code)
        #     print(coupon.description)
        #     print(coupon.expiry_date)
        #     print(coupon.method)
        #     print()
        # print(s.get_coupons())
        # print(s.__dict__)
        print()
