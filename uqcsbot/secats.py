import re
import json
from bisect import bisect_left
import requests
import pandas as pd
from bs4 import BeautifulSoup
import functools
from typing import Optional
import logging


def binsearch(a, x, key=None):
    """Binary search using bisect_left."""
    pos = bisect_left(a, x, key=key)
    if pos != len(a) and a[pos] == x:
        return pos
    else:
        raise ValueError(f"`{x}` is not present within `a`")


class SECaTs:
    """Small scrapper class for SECaTs."""

    URL = "https://www.pbi.uq.edu.au/clientservices/SECaT/embedChart.aspx"

    def __init__(self):
        self.session = requests.Session()
        firstPage = self.session.post(self.URL).content
        self.soup = BeautifulSoup(firstPage, "html.parser")

        self.viewstategenerator = self.soup.find(
            "input", {"id": "__VIEWSTATEGENERATOR"}
        ).get("value")
        self.viewstate = self.soup.find("input", {"id": "__VIEWSTATE"}).get("value")

        self.pattern = re.compile(r"\s*var courseSECATData = (.*?);", re.S)

        # Caches
        self.viewstates = {"": self.viewstate}
        self.secats = {}

    def __get_vs(self, eventarg: str) -> str:
        """
        Get the viewstate for `index` recursively, adding new states to the cache.

        Returns the parsed page and viewstate.
        """
        print("Getting vs for:", eventarg)
        # Find the previous state
        idx = eventarg.rfind(":")
        prev_eventarg = eventarg[:idx] if idx != -1 else ""
        vs = self.viewstates.get(prev_eventarg, None)
        if vs is None:
            print("Didn't find", prev_eventarg, "in cache")
            _, vs = self.__get_vs(prev_eventarg)

        # Make our new request
        data = {
            "__EVENTTARGET": "RadTabStrip1",
            "__EVENTARGUMENT": f"""{{"type":0,"index":"{eventarg}"}}""",
            "__VIEWSTATE": vs,
            "__VIEWSTATEGENERATOR": self.viewstategenerator,
        }
        print("Requesting:", eventarg)
        res = self.session.post(self.URL, data=data).content.decode("utf8")

        soup = BeautifulSoup(res, "html.parser")
        vs = soup.find("input", {"id": "__VIEWSTATE"}).get("value")
        self.viewstates[eventarg] = vs
        return soup, vs

    def __get_lvl1_ea(self, letter: str) -> str:
        """
        Get the eventarg for the level 1 menu for `letter`.

        This corropsonds the the first letter of the course code.

        Parsing the letters from the page isn't required since A-W exist
        already but can be done:
        [x.text for x in soup.find("div", "rtsLevel rtsLevel1").find_all("span", "rtsTxt")]

        Returns the parsed page and viewstate directly from `__get_vs` and the
        eventarg used.
        """
        # print("Getting lvl1 vs for:", letter)
        assert len(letter) == 1 and "A" <= letter <= "W"

        eventarg = str(ord(letter) - ord("A"))
        return eventarg

    @functools.cache
    def __get_lvl2_ea(self, letters: str) -> str:
        """
        Get the eventarg for the level 2 menu for `letters`.

        This corropsonds the first 4 letters of the course code.
        """
        print("Getting lvl2 vs for:", letters)
        assert len(letters) == 4

        eventarg = self.__get_lvl1_ea(letters[0])
        soup, vs = self.__get_vs(eventarg)

        codes = [
            x.text
            for x in soup.find("div", "rtsLevel rtsLevel2").find_all("span", "rtsTxt")
        ]
        return eventarg + ":" + str(binsearch(codes, letters))

    @functools.cache
    def __get_lvl3_ea(self, code: str) -> str:
        """
        Get the eventarg for the level 3 menu for `code`.

        This corropsonds the full course code.
        """
        print("Getting lvl3 vs for:", code)
        assert len(code) == 8

        eventarg = self.__get_lvl2_ea(code[:4])
        soup, vs = self.__get_vs(eventarg)

        # We specifically want the *unstyled* elements, otherwise we'll get all
        # the courses under code[:4]
        courses = [
            x.text
            for x in soup.find("div", "rtsLevel rtsLevel3")
            .find("ul", style=False)
            .find_all("span", "rtsTxt")
        ]
        return eventarg + ":" + str(binsearch(courses, code))

    @functools.cache
    def __get_lvl4_ea(self, code: str, semester: str) -> str:
        r"""
        Get the eventarg for the level 4 menu for `code` and `semester`.

        `semester` must be of the form "^Semester [12], 20\d{2}$".

        This corropsonds the full course code and semester pair.
        """
        print("Getting lvl4 vs for:", code, semester)
        assert len(code) == 8 and re.match(r"^Semester [12], 20\d{2}$", semester)

        eventarg = self.__get_lvl3_ea(code)
        soup, vs = self.__get_vs(eventarg)

        # We specifically want the *unstyled* elements, otherwise we'll get all
        # the semesters under code[:4]. Actually I'm not sure what we'll get
        # but we don't want the styled ones anyway (they are "display:none;")
        semesters = [
            x.text
            for x in soup.find("div", "rtsLevel rtsLevel4")
            .find("ul", style=False)
            .find_all("span", "rtsTxt")
        ]
        # Semesters are sorted in most recent to oldest, unfortunately thats
        # the same as decending colexicographic ordering, so we'll just use
        # .index()
        return eventarg + ":" + str(semesters.index(code + ": " + semester))

    def __extract(self, soup: BeautifulSoup) -> pd.DataFrame:
        for script in soup.find_all("script"):
            if script.string and (match := self.pattern.match(script.string)):
                return pd.DataFrame(json.loads(match.group(1)))

    def get(self, code: str, semester: Optional[str] = None) -> pd.DataFrame:
        r"""
        Get the latest SECaT or the semester corrosponding to the course code.

        `len(code)` must be 8.

        `semester` must be of the form "^Semester [12], 20\d{2}$".
        """
        assert len(code) == 8
        code = code.upper()

        try:
            if semester is None:
                soup, _ = self.__get_vs(self.__get_lvl3_ea(code))
            else:
                assert re.match(r"^Semester [12], 20\d{2}$", semester)
                soup, _ = self.__get_vs(self.__get_lvl4_ea(code, semester))
        except requests.RequestException as exception:
            logging.error(exception.response.content)

        return self.__extract(soup)



import asyncio

async def main():
    print('Hello ...')
    await asyncio.sleep(1)
    print('... World!')

asyncio.run(main())
