from typing import Optional
import logging
from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.utils.uq_course_utils import (
    Offering,
    HttpException,
    CourseNotFoundException,
    ProfileNotFoundException,
    get_course_profile_url,
)
from uqcsbot.yelling import yelling_exemptor


class CourseECP(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.describe(
        course1="The course to find an ECP for.",
        course2="The second course to find an ECP for.",
        course3="The third course to find an ECP for.",
        course4="The fourth course to find an ECP for.",
        year="The year to find the course ECP for. Defaults to what UQCSbot believes is the current year.",
        semester="The semester to find the course ECP for. Defaults to what UQCSbot believes is the current semester.",
        campus="The campus the course is held at. Defaults to St Lucia. Defaults to St Lucia. Note that many external courses are 'hosted' at St Lucia.",
        mode="The mode of the course. Defaults to Internal.",
    )
    @yelling_exemptor(input_args=["course1, course2, course3, course4"])
    async def courseecp(
        self,
        interaction: discord.Interaction,
        course1: str,
        course2: Optional[str],
        course3: Optional[str],
        course4: Optional[str],
        year: Optional[int] = None,
        semester: Optional[Offering.SemesterType] = None,
        campus: Offering.CampusType = "St Lucia",
        mode: Offering.ModeType = "Internal",
    ):
        """
        Returns the URL of the ECPs for course codes given. Assumes the same semester and year for the course codes given.

        """
        await interaction.response.defer(thinking=True)

        possible_courses = [course1, course2, course3, course4]
        course_names = [c.upper() for c in possible_courses if c != None]
        course_name_urls: dict[str, str] = {}
        offering = Offering(semester=semester, campus=campus, mode=mode)

        try:
            for course in course_names:
                course_name_urls.update(
                    {course: get_course_profile_url(course, offering, year)}
                )
        except HttpException as exception:
            logging.warning(
                f"Received a HTTP response code {exception.status_code} when trying find the course url using get_course_profile_url in course_ecp.py . Error information: {exception.message}"
            )
            await interaction.edit_original_response(
                content=f"Could not contact UQ, please try again."
            )
            return
        except (CourseNotFoundException, ProfileNotFoundException) as exception:
            await interaction.edit_original_response(content=exception.message)
            return

        # If year is none assign it the current year
        if not year:
            year = datetime.today().year

        # If semester is none assign it the current estimated semester
        if not semester:
            semester = Offering.estimate_current_semester()

        # Create the embedded message with the course names and details
        embed = discord.Embed(
            title=f"Course ECP: {', '.join(course_names)}",
            description=f"For Semester {semester} {year}, {mode}, {campus}",
        )

        # Add the ECP urls to the embedded message
        if course_name_urls:
            for course in course_name_urls:
                embed.add_field(
                    name=f"",
                    value=f"[{course}]({course_name_urls.get(course)}) ",
                    inline=False,
                )
        else:
            await interaction.edit_original_response(
                content=f"No ECP could be found for the courses: {course_names}. The ECP(s) might not be available."
            )
            return

        embed.set_footer(
            text="The course ECP might be out of date, be sure to check the course on BlackBoard."
        )
        await interaction.edit_original_response(embed=embed)
        return


async def setup(bot: commands.Bot):
    await bot.add_cog(CourseECP(bot))
