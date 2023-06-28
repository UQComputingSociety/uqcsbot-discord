from typing import List, Any
from mypy_extensions import VarArg, KwArg

import discord
from discord import app_commands
from discord.ext import commands

UQCS_REPO_URL = "https://github.com/UQComputingSociety/"

REPOS = {
    "cpg": ("cpg", "Resources for the UQCS competitive programming group"),
    "conduct": (
        "code-of-conduct",
        "The UQCS Code of Conduct to be followed by all community members",
    ),
    "constitution": ("constitution", "All the business details"),
    "cookbook": ("cookbook", "A cookbook of recipes contributed by UQCS members"),
    "design": ("design", "All UQCS design assets"),
    "events": ("events", "A repository for events and talk materials"),
    "minutes": ("minutes", "Minutes from UQCS general meetings"),
    "signup": ("signup", "The UQCS membership signup system"),
    "uqcsbot": ("uqcsbot-discord", "Our friendly little Discord bot"),
    "website": ("website", "The UQ Computing Society website"),
}


class Basic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Sets the status for the bot"""
        # TODO: This can be removed once the presence has a better home.
        await self.bot.change_presence(
            activity=discord.Streaming(
                name="UQCS Live Stream",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=43s",
                platform="YouTube",
            )
        )

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Member join listener"""
        channel = member.guild.system_channel
        # On user joining, a system join message will appear in the system channel
        # This should prevent the bot waving on a user message when #general is busy
        async for msg in channel.history(limit=5):
            # Wave only on new member system message
            if msg.type == discord.MessageType.new_member:
                await msg.add_reaction("👋")
                break

    @app_commands.command()
    async def smoko(self, interaction: discord.Interaction):
        """For when you just need a break."""
        await interaction.response.send_message(
            "https://www.youtube.com/watch?v=j58V2vC9EPc"
        )

    @app_commands.command()
    async def conduct(self, interaction: discord.Interaction):
        """Returns the URL for the UQCS Code of Conduct."""
        await interaction.response.send_message(
            "UQCS Code of Conduct: https://uqcs.org/code-of-conduct"
        )

    def find_repo(self, repo: str) -> str:
        """
        Finds a specific repo from the REPO dict and constructs a single string for it.
        :param repo: name of the repo to find.
        :return: single string containing the info for the given repo.
        """
        if repo not in REPOS.keys():
            return f'> Unrecognised repo "{repo}"\n'
        else:
            return f"> {UQCS_REPO_URL + REPOS[repo][0]}: {REPOS[repo][1]}\n"

    def format_repo_message(self, repos: List[str]) -> str:
        """
        Takes a list of repo names and matches them to REPOS keys, constructing a message from the
        relevant repo information.
        :param repos: list of strings of repo names
        :return: a single string with a formatted message containing repo info for the given names
        """
        repo_strings = []
        for potential_repo in repos:
            repo_strings.append(self.find_repo(potential_repo))
        return "".join(repo_strings)

    repo_group = app_commands.Group(name="repo", description="Commands for UQCS repos")

    @repo_group.command(name="list")
    async def repo_list(self, interaction: discord.Interaction):
        """Lists the UQCS GitHub repositories"""
        await interaction.response.send_message(
            "_Useful :uqcs: Github repositories_:\n"
            + self.format_repo_message(list(REPOS.keys()))
        )

    @repo_group.command(name="find", description="Name of the repo to find")
    async def repo_find(self, interaction: discord.Interaction, name: str):
        """Finds a specific UQCS GitHub repository"""
        await interaction.response.send_message(
            "_Requested UQCS Github repository_:\n" + self.find_repo(name)
        )

    @repo_find.autocomplete("name")
    async def repo_search_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete handler for repo_find command"""
        repo_names = REPOS.keys()
        return [
            app_commands.Choice(name=name, value=name)
            for name in repo_names
            if current.lower() in name
        ]


async def setup(bot: commands.Bot):
    await bot.add_cog(Basic(bot))
