from datetime import datetime
import logging
from typing import Optional, Callable, Literal, Dict

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.utils.uq_course_utils import (
    DateSyntaxException,
    Offering,
    CourseNotFoundException,
    HttpException,
    ProfileNotFoundException,
    AssessmentItem,
    get_course_assessment,
    get_course_assessment_page,
    get_course_profile_id,
    get_current_exam_period,
)

AssessmentSortType = Literal["Date", "Course Name", "Weight"]
ECP_ASSESSMENT_URL = (
    "https://course-profiles.uq.edu.au/student_section_loader/section_5/"
)


def sort_by_date(item: AssessmentItem):
    """Provides a key to sort assessment dates by. If the date cannot be parsed, will put it with items occuring during exam block."""
    try:
        return item.get_parsed_due_date()[0]
    except DateSyntaxException:
        return get_current_exam_period()[0]


SORT_METHODS: Dict[
    AssessmentSortType, Callable[[AssessmentItem], int | str | datetime]
] = {
    "Date": sort_by_date,
    "Course Name": (lambda item: item.course_name),
    "Weight": (lambda item: item.get_weight_as_int() or 0),
}


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
        courses="Course codes seperated by spaces",
        sort_order="The order to sort courses by. Defualts to Date.",
        reverse_sort="Whether to reverse the sort order. Defaults to false.",
        show_ecp_links="Show the first ECP link for each course page. Defaults to false.",
    )
    async def whatsdue(
        self,
        interaction: discord.Interaction,
        courses: str,
        fulloutput: bool = False,
        semester: Optional[Offering.SemesterType] = None,
        campus: Offering.CampusType = "St Lucia",
        mode: Offering.ModeType = "Internal",
        sort_order: AssessmentSortType = "Date",
        reverse_sort: bool = False,
        show_ecp_links: bool = False,
    ):
        """
        Returns all the assessment for a given list of course codes that are scheduled to occur.
        Defaults to sending assessment due today onwards.
        """

        await interaction.response.defer(thinking=True)

        course_names = [c.upper() for c in courses.split()]
        offering = Offering(semester=semester, campus=campus, mode=mode)

        # If full output is not specified, set the cutoff to today's date.
        cutoff = None if fulloutput else datetime.today()
        try:
            assessment_page = get_course_assessment_page(course_names, offering)
            assessment = get_course_assessment(course_names, cutoff, assessment_page)
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
            url=assessment_page,
            description="*WARNING: Assessment information may vary/change/be entirely different! Use at your own discretion. Check your ECP for a true list of assessment.*",
        )
        if assessment:
            assessment.sort(key=SORT_METHODS[sort_order], reverse=reverse_sort)
            for assessment_item in assessment:
                embed.add_field(
                    name=assessment_item.course_name,
                    value=f"`{assessment_item.weight}` {assessment_item.task} **({assessment_item.due_date})**",
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

        if show_ecp_links:
            ecp_links = [
                f"[{course_name}]({ECP_ASSESSMENT_URL + str(get_course_profile_id(course_name))})"
                for course_name in course_names
            ]
            embed.add_field(
                name=f"Potential ECP {'Link' if len(course_names) == 1 else 'Links'}",
                value=" ".join(ecp_links)
                + "\nNote that these may not be the correct ECPs. Check the year and offering type.",
            )
        if not fulloutput:
            embed.set_footer(
                text="Note: This may not be the full assessment list. Set fulloutput to True to see a potentially more complete list, or check your ECP for a true list of assessment."
            )

        await interaction.edit_original_response(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(WhatsDue(bot))
