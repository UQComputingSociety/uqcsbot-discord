from datetime import datetime
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.utils.uq_course_utils import (
    Offering,
    CourseNotFoundException,
    HttpException,
    ProfileNotFoundException,
    get_course_assessment,
    get_course_assessment_page,
)


class WhatsDue(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.describe(
        fulloutput="Display the full list of assessment. Defaults to False, which only "
        + "shows assessment due from today onwards.",
        semester="The semester to get assessment for. Defaults to what UQCSbot believes is the current semester.",
        campus="The campus the course is held at. Defaults to St Lucia. Note that many external courses are 'hosted' at St Lucia.",
        mode="The mode of the course. Defaults to Internal.",
        course1="Course code",
        course2="Course code",
        course3="Course code",
        course4="Course code",
        course5="Course code",
        course6="Course code",
    )
    async def whatsdue(
        self,
        interaction: discord.Interaction,
        course1: str,
        course2: Optional[str],
        course3: Optional[str],
        course4: Optional[str],
        course5: Optional[str],
        course6: Optional[str],
        fulloutput: bool = False,
        semester: Optional[Offering.SemesterType] = None,
        campus: Offering.CampusType = "St Lucia",
        mode: Offering.ModeType = "Internal",
    ):
        """
        Returns all the assessment for a given list of course codes that are scheduled to occur.
        Defaults to sending assessment due today onwards.
        """

        await interaction.response.defer(thinking=True)

        possible_courses = [course1, course2, course3, course4, course5, course6]
        course_names = [c.upper() for c in possible_courses if c != None]
        offering = Offering(semester=semester, campus=campus, mode=mode)

        # If full output is not specified, set the cutoff to today's date.
        cutoff = None if fulloutput else datetime.today()
        try:
            asses_page = get_course_assessment_page(course_names, offering)
            assessment = get_course_assessment(course_names, cutoff, asses_page)
        except HttpException as e:
            logging.error(e.message)
            await interaction.edit_original_response(
                content=f"An error occurred, please try again."
            )
            return
        except (CourseNotFoundException, ProfileNotFoundException) as e:
            await interaction.edit_original_response(content=e.message)
            return

        embed = discord.Embed(
            title=f"What's Due: {', '.join(course_names)}",
            url=asses_page,
            description="*WARNING: Assessment information may vary/change/be entirely different! Use at your own discretion*",
        )
        if assessment:
            for assessment_item in assessment:
                course, task, due, weight = assessment_item
                embed.add_field(
                    name=course,
                    value=f"`{weight}` {task} **({due})**",
                    inline=False,
                )
        elif fulloutput:
            embed.add_field(
                name="",
                value=f"No assessment items could be found",
            )
        else:
            embed.add_field(
                name="",
                value=f"Nothing seems to be due soon",
            )

        if not fulloutput:
            embed.set_footer(
                text="Note: This may not be the full assessment list. Set fulloutput to True for the full list."
            )

        await interaction.edit_original_response(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(WhatsDue(bot))
