import discord
import logging
from discord.ext import commands


class JobsBulletin(commands.Cog):
    CHANNEL_NAME = "jobs-bulletin"
    DISCUSSION_CHANNEL_NAME = "jobs-discussion"
    FAIR_WORK_INFO = "https://www.fairwork.gov.au/pay/unpaid-work/work-experience-and-internships"
    EAIT_UNPAID_JOBS = "https://www.eait.uq.edu.au/engineering-professional-practice-unpaid-placements"
    EAIT_FACULTY = "https://www.eait.uq.edu.au/"
    CODE_OF_CONDUCT = "https://github.com/UQComputingSociety/code-of-conduct"
    UQCS_EMAIL = "contact@uqcs.org"
    WELCOME_MESSAGES = [    # Welcome messages sent to new members
        "#jobs-bulletin is a little different to your average"
        + " UQCS Discord channel and has a few extra rules:",
        "**Rules for Everyone** \n"
        "1. The _only_ posts allowed in this channel are job advertisements.\n"
        "2. All discussion about the posted jobs must take place in the #jobs-discussion "
        + " channel or by direct message with the person posting the advertisement."
        + " Please be respectful when interacting with companies and sponsors.\n",
        "**Additional Rules for Employers Posting Jobs/Internship Opportunities:**\n"
        "3. We take the rights of our members and associates seriously. If you are posting an unpaid"
        + " position, please be up front about the lack of remuneration and **mindful of**"
        + f" [**your obligations**]({FAIR_WORK_INFO}) under the"
        + " _Fair Work Act (2009)._ \n"
        "_ tldr: if an intern (whether called that or not) adds value to"
        + " (or 'does productive work' for) your business, they must be remunerated with a fair wage._\n"
        + " If you ignore these warnings, please expect to face criticism from the community"
        + " (we will protect our members from being exploited)."
        + f" Additionally, all [unpaid placements]({EAIT_UNPAID_JOBS}) for students in the"
        + f" [EAIT Faculty]({EAIT_FACULTY}) must be approved by the faculty placement advisers.",
        f"4. Job postings **must** conform to our [Code of Conduct]({CODE_OF_CONDUCT})"
        + " and must not discriminate against applicants based on race, religion,"
        + " sexual orientation, gender identity or age.",
        "If you have any questions, please get in touch with the committee in"
        + f" #uqcs-meta or by email at {UQCS_EMAIL}."
    ]

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        """ Detects if a message is sent in #jobs_bulletin and sends notification to channel and author. """
        if not self.bot.user or not isinstance(msg.channel, discord.TextChannel) or \
                msg.author.id == self.bot.user.id or msg.channel.name != self.CHANNEL_NAME:
            return

        jobs_bulletin = discord.utils.get(self.bot.uqcs_server.channels, name=self.CHANNEL_NAME)
        jobs_discussion = discord.utils.get(self.bot.uqcs_server.channels, name=self.DISCUSSION_CHANNEL_NAME)

        if jobs_bulletin is None or jobs_discussion is None:
            logging.warning(f"Could not find required channels #{self.CHANNEL_NAME} or #{self.DISCUSSION_CHANNEL_NAME}")
            return

        channel_message = (f"{msg.author.display_name} has posted a new job in {jobs_bulletin.mention}! :tada: \n"
                   f"Please ask any questions in {jobs_discussion.mention}"
                   + f" or in a private message to {msg.author.mention}")
        await msg.channel.send(channel_message, allowed_mentions=discord.AllowedMentions(everyone=False, users=True, roles=False))
        
        user_message = discord.Embed()
        user_message.title = "#jobs-bulletin reminder"
        user_message.description = (f"Hey {msg.author.display_name}, you've just posted in #jobs-bulletin! \n"
                f"Just a quick reminder of the conditions"
                + f" surrounding the use of this channel:\n\n" +
                f"\n".join(self.WELCOME_MESSAGES[1:] + [""]) + "\n" +
                f"**Broken one of these rules?**\n"
                f"It's not too late! Please go back ASAP and"
                + f" edit your message in #jobs-bulletin so it complies (or ask a committee"
                + f" member to delete it). Thanks!")
        await msg.author.send(embed=user_message)
            

async def setup(bot: commands.Bot):
    await bot.add_cog(JobsBulletin(bot))

