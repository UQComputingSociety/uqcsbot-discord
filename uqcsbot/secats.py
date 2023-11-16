import re
import json
from bisect import bisect_left
import requests
import pandas as pd
from bs4 import BeautifulSoup


class SECaTs:
    url = "https://www.pbi.uq.edu.au/clientservices/SECaT/embedChart.aspx"

    def __init__(self):
        firstPage = requests.post(self.url).content
        self.soup = BeautifulSoup(firstPage, "html.parser")

        self.viewstategenerator = self.soup.find(
            "input", {"id": "__VIEWSTATEGENERATOR"}
        ).get("value")
        self.viewstate = self.soup.find("input", {"id": "__VIEWSTATE"}).get("value")

        self.pattern = re.compile(r"\s*var courseSECATData = (.*?);", re.S)

        # Caches
        self.viewstates = {"": self.viewstate}
        self.lvl2_eventargs = {}
        self.lvl3_eventargs = {}

    def get(self, index: list[str]) -> pd.DataFrame:
        assert 0 < len(index) <= 4

        vs = self.viewstate
        for i in range(1, len(index) + 1):
            eventarg = ":".join(index[:i])
            data = {
                "__EVENTTARGET": "RadTabStrip1",
                "__EVENTARGUMENT": f"""{{"type":0,"index":"{eventarg}"}}""",
                "__VIEWSTATE": vs,
                "__VIEWSTATEGENERATOR": self.viewstategenerator,
            }
            res = requests.post(self.url, data=data).content.decode("utf8")

            soup = BeautifulSoup(res, "html.parser")
            vs = soup.find("input", {"id": "__VIEWSTATE"}).get("value")

        for script in soup.find_all("script"):
            if script.string and (match := self.pattern.match(script.string)):
                return pd.DataFrame(json.loads(match.group(1)))

    def __get_vs(self, eventarg: str) -> str:
        """
        Get the viewstate for `index` recursively, adding new states to the cache.

        Returns the parsed page and viewstate.
        """
        print("Getting vs for:", eventarg)
        # Find the previous state
        prev_eventarg = eventarg[:eventarg.rfind(":")]
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
        res = requests.post(self.url, data=data).content.decode("utf8")

        soup = BeautifulSoup(res, "html.parser")
        vs = soup.find("input", {"id": "__VIEWSTATE"}).get("value")
        self.viewstates[eventarg] = vs
        return soup, vs

    def __get_lvl1_ea(self, letter: str) -> str:
        """
        Get the eventarg for the level 1 menu.

        This corropsonds the the first letter of the course code.

        Parsing the letters from the page isn't required since A-W exist
        already but can be done:
        [x.text for x in soup.find("div", "rtsLevel rtsLevel1").find_all("span", "rtsTxt")]

        Returns the parsed page and viewstate directly from `__get_vs` and the
        eventarg used.
        """
        print("Getting lvl1 vs for:", letter)
        assert len(letter) == 1 and "A" <= letter <= "W"

        eventarg = str(ord(letter) - ord("A"))
        return eventarg

    def __get_lvl2_ea(self, letters: str) -> str:
        """
        Get the eventarg for the level 2 menu.

        This corropsonds the first 4 letters of the course code.
        """
        print("Getting lvl2 vs for:", letters)
        assert len(letters) == 4

        eventarg = self.lvl2_eventargs.get(letters, None)
        if eventarg is None:
            print("Didn't find", letters, "in lvl2 cache")
            soup, vs, eventarg = self.__get_lvl1_vs(letters[0])

            codes = [
                x.text
                for x in soup.find("div", "rtsLevel rtsLevel2").find_all("span", "rtsTxt")
            ]
            eventarg = eventarg + ":" + str(bisect_left(codes, letters))
            self.lvl2_eventargs[letters] = eventarg

        return *self.__get_vs(eventarg), eventarg

    def __get_lvl3_vs(self, code: str) -> str:
        """
        Get the viewstate for the level 3 menu.

        This corropsonds the full course code.
        """
        print("Getting lvl3 vs for:", code)
        assert len(code) == 8

        eventarg = self.lvl3_eventargs.get(code, None)
        if eventarg is None:
            print("Didn't find", code, "in lvl3 cache")
            soup, vs, eventarg = self.__get_lvl2_vs(code[:4])

            # We specifically want the *unstyled* elements, otherwise we'll get all
            # the courses under code[:4]
            courses = [
                x.text
                for x in soup.find("div", "rtsLevel rtsLevel3")
                .find("ul", style=False)
                .find_all("span", "rtsTxt")
            ]
            eventarg = eventarg + ":" + str(bisect_left(courses, code))
            self.lvl3_eventargs[code] = eventarg

        return *self.__get_vs(eventarg), eventarg

    def get_latest(self, code: str) -> pd.DataFrame:
        """Get the latest SECaT corrosponding to the course code."""
        print("Getting latest for:", code)

        soup, _, _ = self.__get_lvl3_vs(code)

        for script in soup.find_all("script"):
            if script.string and (match := self.pattern.match(script.string)):
                return pd.DataFrame(json.loads(match.group(1)))
