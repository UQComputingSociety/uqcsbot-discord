import discord
from discord.ext import commands
from datetime import datetime
from uqcsbot.utils.command_utils import loading_status
from uqcsbot.utils.uq_course_utils import (get_course_assessment,
                                           get_course_assessment_page,
                                           HttpException,
                                           CourseNotFoundException,
                                           ProfileNotFoundException)

# Maximum number of courses supported by !whatsdue to reduce call abuse.
COURSE_LIMIT = 6

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

    @commands.command()
    @loading_status
    async def whatsdue(self, ctx: commands.Context, *args):
        """
        `!whatsdue [-f] [--full] [COURSE CODE 1] [COURSE CODE 2] ...` - Returns all
        the assessment for a given list of course codes that are scheduled to occur
        after today. If unspecified, will attempt to return the assessment for the
        channel that the command was called from. If -f/--full is provided, will
        return the full assessment list without filtering by cutoff dates.
        """
        if len(args) == 0:
            await ctx.send("Must provide argument/s")
            return 

        is_full_output = False
        if '--full' in args or '-f' in args:
            is_full_output = True

        # If we have any command args left, they're course names. If we don't,
        # attempt to instead use the channel name as the course name.
        course_names = [c for c in args if (c != '--full' and c != '-f')]

        if len(course_names) > COURSE_LIMIT:
            await ctx.send(f'Cannot process more than {COURSE_LIMIT} courses.')
            return

        # If full output is not specified, set the cutoff to today's date.
        cutoff = None if is_full_output else datetime.today()
        try:
            asses_page = get_course_assessment_page(course_names)
            assessment = get_course_assessment(course_names, cutoff, asses_page)
        except HttpException as e:
            # TODO bot.logger.error(e.message)
            await ctx.send(f'An error occurred, please try again.')
            return
        except (CourseNotFoundException, ProfileNotFoundException) as e:
            await ctx.send(e.message)
            return

        message = ('_*WARNING:* Assessment information may vary/change/be entirely'
                   + ' different! Use at your own discretion_\n> ')
        message += '\n> '.join(map(self.get_formatted_assessment_item, assessment))
        if not is_full_output:
            message += ('\n_Note: This may not be the full assessment list. Use -f'
                        + '/--full to print out the full list._')
        message += f'\nLink to assessment page <{asses_page}|here>'
        await ctx.send(message)

def setup(bot: commands.Bot):
    bot.add_cog(WhatsDue(bot))
