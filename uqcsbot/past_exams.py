from typing import Optional, Literal
import logging
from random import choice

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.utils.uq_course_utils import (
    get_past_exams,
    get_past_exams_page_url,
    HttpException,
)

SemesterType = Optional[Literal["Sem 1", "Sem 2", "Summer"]]


class PastExams(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.describe(
        course_code="The course to find a past exam for.",
        year="The year to find exams for. Leave blank for all years.",
        semester="The semester to find exams for. Leave blank for all semesters.",
        random_exam="Whether to select a single random exam.",
    )
    async def pastexams(
        self,
        interaction: discord.Interaction,
        course_code: str,
        year: Optional[int] = None,
        semester: SemesterType = None,
        random_exam: bool = False,
    ):
        """
        Returns a list of past exams, or, if specified, a past exam for a specific year.
        """
        await interaction.response.defer(thinking=True)

        try:
            past_exams = get_past_exams(course_code)    
        except HttpException as exception:
            logging.warning(
                f"Received a HTTP response code {exception.status_code}. Error information: {exception.message}"
            )
            await interaction.edit_original_response(
                content=f"Could not successfully contact UQ for past exams."
            )
            return
        if not past_exams:
            await interaction.edit_original_response(
                content=f"No past exams could be found for {course_code}."
            )
            return

        if semester:
            past_exams = list(
                filter(lambda exam: exam.semester == semester, past_exams)
            )
        if year:
            past_exams = list(filter(lambda exam: exam.year == year, past_exams))

        if not past_exams:
            await interaction.edit_original_response(
                content=f"No past exams could be found for {course_code} matching your specifications."
            )
            return

        if random_exam:
            past_exams = [choice(past_exams)]

        if len(past_exams) == 1:
            exam = past_exams[0]
            embed = discord.Embed(
                title=f"Past exam for {course_code.upper()}",
                description=f"**{exam.year} {exam.semester}**: {exam.link}",
            )
            embed.set_footer(
                text = "The above link will require a UQ SSO login to access."
            )
            await interaction.edit_original_response(embed=embed)
            return

        description = ""
        if year is not None or semester is not None:
            description = "Only showing exams for " + " ".join(
                str(restriction)
                for restriction in [year, semester]
                if restriction is not None
            )
        embed = discord.Embed(
            title=f"Past exams for {course_code.upper()}",
            url=get_past_exams_page_url(course_code),
            description=description,
        )
        for exam in past_exams:
            embed.add_field(
                name=f"{exam.year} {exam.semester}",
                value=exam.link,
                inline=False,
            )
        embed.set_footer(
            text = "The above links will require a UQ SSO login to access."
        )
        await interaction.edit_original_response(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(PastExams(bot))
