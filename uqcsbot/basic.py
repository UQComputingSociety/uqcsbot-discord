from discord.ext import commands
import discord
from typing import List

UQCS_REPO_URL = "https://github.com/UQComputingSociety/"

REPOS = {
    "coc": ("code-of-conduct", "The UQCS Code of Conduct to be followed by all community members"),
    "constitution": ("constitution", "All the business details"),
    "design": ("design", "All UQCS design assets"),
    "events": ("events", "A repository for events and talk materials"),
    "inviter": ("slack-invite-automation", "Web application to invite users to our slack team"),
    "minutes": ("minutes", "Minutes from UQCS committee meetings and general meetings"),
    "signup": ("signup", "The UQCS membership signup system"),
    "uqcsbot-discord": ("uqcsbot", "Our friendly little Discord bot"),
    "website": ("website", "The UQ Computing Society website"),
}

class Basic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # TODO: This can be removed once the presence has a better home.
        await self.bot.change_presence(activity=discord.Streaming(name="UQCS Live Stream", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=43s", platform="YouTube"))

    @commands.command()
    async def echo(self, ctx: commands.Context, *, text=""):
        """ Echos back the text that you send. """
        if text == "":
            await ctx.send("ECHO!")
        elif text == "I have rebooted!":
            await ctx.send("No I haven't!")
        else:
            await ctx.send(text)

    @commands.command()
    async def conduct(self, ctx: commands.Context):
        await ctx.send("UQCS Code of Conduct")
        await ctx.send("https://github.com/UQComputingSociety/code-of-conduct")

    def format_repo_message(self, repos: List[str]) -> str:
        """
        Takes a list of repo names and matches them to REPOS keys, constructing a message from the
        relevant repo information.
        :param repos: list of strings of repo names
        :return: a single string with a formatted message containing repo info for the given names
        """
        repo_strings = []
        for potential_repo in repos:
            if potential_repo not in REPOS.keys():
                repo_strings.append(f"> Unrecognised repo \"{potential_repo}\"\n")
            else:
                repo_strings.append(f"> {UQCS_REPO_URL + REPOS[potential_repo][0]}"
                                    f": {REPOS[potential_repo][1]}\n")
        return "".join(repo_strings)

    @commands.command()
    async def repo(self, ctx: commands.Context, *args):
        # All repos
        if len(args) == 1 and args[0] in ["--list", "-l", "list", "full", "all"]:
            await ctx.send("_Useful :uqcs: Github repositories_:\n"
                + self.format_repo_message(list(REPOS.keys())))

        # List of specific repos
        elif len(args) > 0:
            await ctx.send("_Requested UQCS Github repositories_:\n"
                                    + self.format_repo_message(list(args)))

        # Default option: just uqcsbot link
        else:
            await ctx.send("_Have you considered contributing to the bot?_\n" +
                                    self.format_repo_message(["uqcsbot"]) +
                                    "\n _For more repositories, try_ `!repo list`")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = member.guild.system_channel
        # On user joining, a system join message will appear in the system channel
        # This should prevent the bot waving on a user message when #general is busy
        async for msg in channel.history(limit=5):
            # Wave only on new member system message
            if msg.type == discord.MessageType.new_member:
                await msg.add_reaction('👋')
                break

def setup(bot: commands.Bot):
    bot.add_cog(Basic(bot))
