from typing import Tuple, Dict, Literal

import discord
from discord import app_commands
from discord.ext import commands

UQCS_EMOJI_NAME = "uqcs"

UQCS_REPO_URL = "https://github.com/UQComputingSociety/"
RepoNameType = Literal[
    "CPG",
    "Conduct",
    "Constitution",
    "Cookbook",
    "Design",
    "Events",
    "Minutes",
    "Signup",
    "UQCSbot",
    "Website",
]
REPOS: Dict[RepoNameType, Tuple[str, str]] = {
    "CPG": ("cpg", "Resources for the UQCS competitive programming group"),
    "Conduct": (
        "code-of-conduct",
        "The UQCS Code of Conduct to be followed by all community members",
    ),
    "Constitution": ("constitution", "All the business details"),
    "Cookbook": ("cookbook", "A cookbook of recipes contributed by UQCS members"),
    "Design": ("design", "All UQCS design assets"),
    "Events": ("events", "A repository for events and talk materials"),
    "Minutes": ("minutes", "Minutes from UQCS general meetings"),
    "Signup": ("signup", "The UQCS membership signup system"),
    "UQCSbot": ("uqcsbot-discord", "Our friendly little Discord bot"),
    "Website": ("website", "The UQ Computing Society website"),
}


class Repos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def add_repo_to_embed(self, embed: discord.Embed, repo: str):
        """
        Finds a specific repo from the REPO dict and adds it to the given embed as a field.
        """
        if repo not in REPOS:
            embed.add_field(
                name=f'Unrecognised repo "{repo}"',
                value="Try using `/repo list` to see all UQCS repositories.",
            )
            return

        repo_description = REPOS[repo][1]
        repo_link = UQCS_REPO_URL + REPOS[repo][0]
        embed.add_field(name=repo, value=f"[{repo_description}]({repo_link})")

    repo_group = app_commands.Group(name="repo", description="Commands for UQCS repos")

    @repo_group.command(name="list")
    async def repo_list(self, interaction: discord.Interaction):
        """Lists the UQCS GitHub repositories"""
        embed = discord.Embed(
            title=f"Useful {discord.utils.get(self.bot.emojis, name=UQCS_EMOJI_NAME)} Github Repositories",
            url=UQCS_REPO_URL,
        )
        for repo in REPOS.keys():
            self.add_repo_to_embed(embed, repo)
        await interaction.response.send_message(embed=embed)

    @repo_group.command(name="find", description="Name of the repo to find")
    async def repo_find(self, interaction: discord.Interaction, repo: RepoNameType):
        """Finds a specific UQCS GitHub repository"""
        embed = discord.Embed(
            title=f"Useful UQCS{discord.utils.get(self.bot.emojis, name=UQCS_EMOJI_NAME)} Github Repositories",
            url=UQCS_REPO_URL,
        )
        self.add_repo_to_embed(embed, repo)
        await interaction.response.send_message(embed=embed)

        x
async def setup(bot: commands.Bot):
    await bot.add_cog(Repos(bot))