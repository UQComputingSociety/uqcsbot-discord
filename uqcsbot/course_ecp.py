from typing import Optional, Literal
import logging
from random import choice

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
        course_code="The course to find a past exam for.",
        year="The year to find the course ECP for. Defaults to what UQCSbot believes is the current semester.",
        semester="The semester to find the course ECP for. Defaults to what UQCSbot believes is the current semester.",
        campus="The campus the course is held at. Defaults to St Lucia. Defaults to St Lucia. Note that many external courses are 'hosted' at St Lucia.",
        mode="The mode of the course. Defaults to Internal.",
    )
    @yelling_exemptor(
        input_args=["course_code"]
    )    
    
    async def courseecp(
        self,
        interaction: discord.Interaction,
        course_code: str,
        year: Optional[int] = None,
        semester: Optional[Offering.SemesterType] = None,
        campus: Offering.CampusType = "St Lucia",
        mode: Offering.ModeType = "Internal",
    ):
        """
        Returns the URL of the ECPs for course codes given.

        """
        await interaction.response.defer(thinking=True)

        offering = Offering(semester=semester, campus=campus, mode=mode)
                
        try:
            course_url = get_course_profile_url(course_code, offering)
        except HttpException as exception:
            logging.warning(
                f"Received a HTTP response code {exception.status_code}. Error information: {exception.message}"
            )            
            await interaction.edit_original_response(
                content=f"Could not contact UQ, please try again."
            )
            return
        except (CourseNotFoundException, ProfileNotFoundException) as exception:     
            await interaction.edit_original_response(content=exception.message)
            return
        
        # Below needs to account for the year, semester, mode and campus offerings,
        # Currently it just defaults to current offering.
        embed = discord.Embed(
            title=f"Course ECP for {course_code.upper()}",
            url=course_url,
            # Make below considerate of offering.
            # description=f"[{course_code.upper()}]({course_url})",
        )

        if not course_url:
            await interaction.edit_original_response(
                content=f"No ECP could be found for {course_code}. The {course_code}'s ECP might not be available."
            )
            return

        embed.set_footer(
            text="The course ECP might be out of date, be sure to check the course on BlackBoard."
        )
        await interaction.edit_original_response(embed=embed)
        return

async def setup(bot: commands.Bot):
    await bot.add_cog(CourseECP(bot))
