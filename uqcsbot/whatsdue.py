from datetime import datetime
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.utils.command_utils import loading_status
from uqcsbot.utils.uq_course_utils import (CourseNotFoundException,
                                           HttpException,
                                           ProfileNotFoundException,
                                           get_course_assessment,
                                           get_course_assessment_page)

class WhatsDue(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_formatted_assessment_item(self, assessment_item):
        """
        Returns the given assessment item in a pretty
        message format to display to a user.
        """
        course, task, due, weight = assessment_item
        return f'**{course}**: `{weight}` *{task}* **({due})**'

    @app_commands.command()
    @app_commands.describe(
        fulloutput="Display the full list of assessment. Defaults to False, which only " +
                   "shows assessment due from today onwards",
        course1="Course code",
        course2="Course code",
        course3="Course code",
        course4="Course code",
        course5="Course code",
        course6="Course code"
    )
    async def whatsdue(self, 
                        interaction: discord.Interaction, 
                        course1: str, 
                        course2: Optional[str], 
                        course3: Optional[str], 
                        course4: Optional[str],
                        course5: Optional[str],
                        course6: Optional[str],
                        fulloutput: Optional[bool] = False
                        ):
        """
        Returns all the assessment for a given list of course codes that are scheduled to occur.
        Defaults to sending assessment due today onwards.
        """
        
        await interaction.response.defer(thinking=True)

        possible_courses = [course1, course2, course3, course4, course5, course6]
        course_names = [c for c in possible_courses if c != None]
        

        # If full output is not specified, set the cutoff to today's date.
        cutoff = None if fulloutput else datetime.today()
        try:
            asses_page = get_course_assessment_page(course_names)
            assessment = get_course_assessment(course_names, cutoff, asses_page)
        except HttpException as e:
            logging.error(e.message)
            await interaction.edit_original_response(content=f'An error occurred, please try again.')
            return
        except (CourseNotFoundException, ProfileNotFoundException) as e:
            await interaction.edit_original_response(content=e.message)
            return

        message = ('_*WARNING:* Assessment information may vary/change/be entirely'
                   + ' different! Use at your own discretion_\n> ')
        message += '\n> '.join(map(self.get_formatted_assessment_item, assessment))
        if not fulloutput:
            message += ('\n_Note: This may not be the full assessment list. Set fulloutput'
                        + 'to True for the full list._')
        message += f'\nLink to assessment page <{asses_page}|here>'
        await interaction.edit_original_response(content=message)


async def setup(bot: commands.Bot):
    await bot.add_cog(WhatsDue(bot))
