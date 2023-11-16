import re
import json
from bisect import bisect_left
import requests
import pandas as pd
from bs4 import BeautifulSoup
import functools
from typing import Optional
import logging

# import discord
# from discord import app_commands
# from discord.ext import commands

# from uqcsbot.utils.uq_course_utils import (
#     Offering,
#     HttpException,
#     CourseNotFoundException,
# )
# from uqcsbot.yelling import yelling_exemptor


def binsearch(a, x, key=None):
    """Binary search using bisect_left."""
    pos = bisect_left(a, x, key=key)
    if pos != len(a) and a[pos] == x:
        return pos
    else:
        raise ValueError(f"`{x}` is not present within `a`")


class SECaTs():
    """Small scrapper class for SECaTs."""

    URL = "https://www.pbi.uq.edu.au/clientservices/SECaT/embedChart.aspx"
    RESPONSES = {
        "1 Strongly Agree": "#16AA16",
        "2 Agree": "#52D652",
        "3 Neither Agree/Disagree": "#F3AC32",
        "4 Disagree": "#DC4848",
        "5 Strongly Disagree": "#BE1212",
    }
    QUESTIONS = [
        "Q1: Understand Aims & Goals",
        "Q2: Intellectually Stimulating",
        "Q3: Well Structured",
        "Q4: Learning Materials Assisted",
        "Q5: Assessment Reqs Clear",
        "Q6: Received Helpful Feedback",
        "Q7: Learned a lot",
        "Q8: Overall Rating",
    ]

    def __init__(self):
        # self.bot = bot
        self.headers = {"User-Agent": "UQCS-rogue-testing"}
        self.session = requests.Session()
        firstPage = self.session.get(self.URL, headers=self.headers).content.decode(
            "utf8"
        )
        soup = BeautifulSoup(firstPage, "html.parser")

        self.viewstategenerator = soup.find(
            "input", {"id": "__VIEWSTATEGENERATOR"}
        ).get("value")
        self.viewstate = soup.find("input", {"id": "__VIEWSTATE"}).get("value")

        self.pattern = re.compile(r"\s*var courseSECATData = (.*?);", re.S)

        # Caches
        self.viewstates = {"": self.viewstate}

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
                summary = {
                    "Enrolled": int(soup.find("span", {"id": "lblNoEnrolled"}).text),
                    "Responses": int(soup.find("span", {"id": "lblNoResponses"}).text),
                }
                summary["Response rate"] = summary["Responses"] / summary["Enrolled"]
                return pd.DataFrame(json.loads(match.group(1))), summary

    @functools.cache
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


import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

s = SECaTs()
results, summary = s.get("CSSE2002")

fig, axs = plt.subplots(2, 4, sharey=True, figsize=(14, 8))

patches = [mpatches.Patch(color=v, label=k) for k, v in SECaTs.RESPONSES.items()]

pivot = results.pivot(index="QUESTION_NAME", columns="ANSWER", values="PERCENT_ANSWER").T
print(pivot.T)
for q, ax in zip(SECaTs.QUESTIONS, axs.reshape(-1)):
    pivot[q].plot.bar(ax=ax, legend=False, color=SECaTs.RESPONSES.values())
    ax.get_xaxis().set_visible(False)
    ax.set_title(q)
    ax.set_ylabel("%")

fig.legend(handles=patches, loc='upper center',
          fancybox=True, shadow=True, ncol=5)
fig.tight_layout()
fig.subplots_adjust(top=0.9)
plt.show()
