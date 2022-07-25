from discord.ext import commands
import discord
from uqcsbot.bot import UQCSBot

from http import HTTPStatus
from uqcsbot.utils.command_utils import loading_status
import json
import requests
import random
from typing import List, Tuple, Dict

CONTESTS_CHANNEL = 813411377975918622

LC_DIFFICULTY = ["easy", "medium", "hard"]  # leetcode difficulty is 1,2,3, need to map
LC_API_LINK = 'https://leetcode.com/api/problems/all/'

COLORS = {"easy": "#5db85b",
        "medium": "#f1ad4e",
        "hard": "#d9534f"}

class Leet(commands.Cog):
    """
    Provides daily leetcode question.
    """
    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self.bot.schedule_task(self.dailyleet, trigger='cron', hour=8, timezone='Australia/Brisbane')

    @commands.command()
    @loading_status
    async def leet(self, ctx: commands.Context, difficulty=None):
        """
        `!leet [`easy` | `medium` | `hard`] - Retrieves a set of questions from online coding
        websites, and posts in channel with a random question from this set. If a difficulty
        is provided as an argument, the random question will be restricted to this level of
        challenge. Else, a random difficulty is generated to choose.
        """

        if difficulty:
            if (difficulty not in {"easy", "medium", "hard"}):
                await ctx.send("Usage: !leet [`easy` | `medium` | `hard`]")
                return
        else:
            difficulty = random.choice(LC_DIFFICULTY)  # No difficulty specified, randomly generate

        # List to store questions collected
        questions: List[Tuple[str, str]] = []

        # Go fetch questions from APIs
        await self.collect_questions(questions, difficulty)
        selected_question = self.select_question(questions)  # Get a random question

        # If we didn't find any questions for this difficulty, try again, probably timeout on all 3
        if (selected_question is None):
            await ctx.send("Hmm, the internet pipes are blocked. Try that one again.")
            return

        # Leetcode difficulty colors
        color = COLORS[difficulty]

        difficulty = difficulty.title()  # If we haven't already (i.e. random question)

        message = discord.Embed()
        message.title = f"{difficulty} question generated!\n\n"
        msg = f"{selected_question[0]}\n{selected_question[1]}\n\n"
        message.description = msg
        await self.bot.get_channel(CONTESTS_CHANNEL).send(embed=message)

    def select_question(self, questions: list) -> Tuple[str, str]:
        """
        Small helper method that selects a question from a list randomly
        """
        if (len(questions) == 0):
            return None
        return random.choice(questions)


    async def collect_questions(self, questions: List[Tuple[str, str]], difficulty: str):
        """
        Helper method to send GET requests to various Leetcode and HackerRank APIs.
        Populates provided dict (urls) with any successfully retrieved data,
        in the form of (Question_Title, Question_Link) tuple pairs.
        """
        # TODO find add additional apis to fetch questions from
        options = [("Leetcode", LC_API_LINK)]
        
        results = []

        # Get all the questions off the internet: hr data struct, hr algo, all leetcode
        for name, url in options:
            try:
                results.append((name, requests.get(url, timeout=3)))
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout) as error:
                print(name + " API timed out!" + "\n" + str(error), flush=True)
                results.append((name, None))

        json_blobs: Dict[str, List[Dict]] = {}

        for name, response in results:
            if (response is None or response.status_code != HTTPStatus.OK):
                json_blobs["parsed_lc_all"] = []
            else:
                parsed_lc_data = json.loads(response.text)
                json_blobs["parsed_lc_all"] = parsed_lc_data["stat_status_pairs"]

        # Build leetcode question tuples from data, but only the free ones
        for question in json_blobs["parsed_lc_all"]:
            if (question["paid_only"] is False):
                question_data = (question["stat"]["question__title"], "https://leetcode.com/problems/"
                                + question["stat"]["question__title_slug"] + "/")

                question_difficulty = LC_DIFFICULTY[question["difficulty"]["level"] - 1]

                if (question_difficulty == difficulty):
                    questions.append(question_data)

    async def dailyleet(self):
        """ 8am daily leetcode question posted """
        questions = [[], [], []]
        for i, q in enumerate(questions):
            await self.collect_questions(q, LC_DIFFICULTY[i])

        selected_questions = dict(zip(LC_DIFFICULTY, [self.select_question(d) for d in questions]))
        points = ["5pts", "10pts", "15pts"]

        message = discord.Embed()
        message.title = "Today's Coding Challenges:\n\n"
        msg = ""

        for i, d in enumerate(LC_DIFFICULTY):
            msg += f"**{d.title()}:** {selected_questions[d][0]}\n{selected_questions[d][1]} ({points[i]})\n\n"
        message.description = msg
        await self.bot.get_channel(CONTESTS_CHANNEL).send(embed=message)

def setup(bot: UQCSBot):
    bot.add_cog(Leet(bot))
