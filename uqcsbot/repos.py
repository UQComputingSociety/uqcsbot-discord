from typing import Tuple, Dict, Literal, Optional
from github import Github, Auth, Issue, PullRequest
import os
import logging

import discord
from discord import app_commands
from discord.ext import commands

UQCS_EMOJI_NAME = "uqcs"

UQCS_GITHUB_ORGANISATION = "UQComputingSociety"
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
MAX_NUMBER_OF_ISSUES = 10
MAX_NUMBER_OF_PRS = 10


class Repos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        github_auth_token = os.environ.get("REPOS_GITHUB_AUTH_TOKEN")
        if github_auth_token is None:
            logging.error(
                "GitHub Auth Token not found in '.env'. Repo commands may not work."
            )
            return
        self.github = Github(auth=Auth.Token(github_auth_token))

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

    def add_issue_to_embed(self, embed: discord.Embed, issue: Issue.Issue):
        """
        Adds an issue as a field to an embed.
        """
        labels = [f"({label.name})" for label in issue.labels]
        embed.add_field(
            name=f"{issue.title} #{issue.number}",
            value=f"*{issue.state.capitalize()} {' '.join(labels)}*\n By {issue.user.name} - Created {issue.created_at.strftime('%d %b %Y')} - [Go to GitHub]({issue.html_url})",
            inline=False,
        )

    def add_pr_to_embed(self, embed: discord.Embed, pr: PullRequest.PullRequest):
        """
        Adds an PR as a field to an embed.
        """
        labels = [f"({label.name})" for label in pr.labels]
        additional_flags = ""
        additional_flags += " Draft" if pr.draft else ""
        additional_flags += " Mergeable" if pr.mergeable else ""
        additional_flags += (
            f" Merged by {pr.merged_by.name} at {pr.merged_at.strftime('%d %b %Y')}"
            if pr.merged
            else ""
        )
        if additional_flags:
            additional_flags = "-" + additional_flags
        embed.add_field(
            name=f"{pr.title} #{pr.number}",
            value=f"*{pr.state.capitalize()} {' '.join(labels)} {additional_flags}*\n By {pr.user.name} - Created {pr.created_at.strftime('%d %b %Y')} - [Go to GitHub]({pr.html_url})",
            inline=False,
        )

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
            title=f"Requested UQCS Github repository",
            url=UQCS_REPO_URL,
        )
        self.add_repo_to_embed(embed, repo)
        await interaction.response.send_message(embed=embed)

    @repo_group.command(
        name="issues", description="List the issues of a UQCS GitHub repo"
    )
    @app_commands.describe(
        repo_name="The UQCS repo to list issues of",
        number_of_results="The maximum number of issues to display. Default of 7 and maximum of 15.",
        state='Only display issues of this state. Default of "open"',
        labels='Only display issues with these labels. For multiple lables, separate by ", ".',
        sort='The order to sort the issues by. Default of "created"',
        direction='The direction to sort by. Default of "desc"',
    )
    async def repo_issues(
        self,
        interaction: discord.Interaction,
        repo_name: RepoNameType,
        number_of_results: int = 7,
        state: Literal["open", "closed", "all"] = "open",
        labels: Optional[str] = None,
        sort: Literal["created", "updated", "comments"] = "created",
        direction: Literal["asc", "desc"] = "desc",
    ):
        """List the issues of a UQCS GitHub repository"""
        if number_of_results > MAX_NUMBER_OF_ISSUES:
            await interaction.response.send_message(
                "Cannot list that many issues.", ephemeral=True
            )
        if labels:
            label_list = labels.split(", ")
        else:
            label_list = []

        await interaction.response.defer(thinking=True)
        repo = self.github.get_repo(f"{UQCS_GITHUB_ORGANISATION}/{REPOS[repo_name][0]}")
        embed = discord.Embed(
            title=f"Issues for {repo_name}",
            url=f"{UQCS_REPO_URL}{REPOS[repo_name][0]}/issues",
        )
        issues = repo.get_issues(
            state=state, labels=label_list, sort=sort, direction=direction
        )
        for issue in issues[:number_of_results]:
            self.add_issue_to_embed(embed, issue)
        await interaction.edit_original_response(embed=embed)

    @repo_group.command(
        name="prs", description="List the PRs (pull requests) of a UQCS GitHub repo"
    )
    @app_commands.describe(
        repo_name="The UQCS repo to list PRs of",
        number_of_results="The maximum number of PRs to display. Default of 7 and maximum of 15.",
        state='Only display PRs of this state. Default of "open"',
        sort='The order to sort by. Default of "created"',
        direction='The direction to sort by. Default of "desc"',
    )
    async def repo_prs(
        self,
        interaction: discord.Interaction,
        repo_name: RepoNameType,
        number_of_results: int = 7,
        state: Literal["open", "closed", "all"] = "open",
        sort: Literal["created", "updated", "popularity", "long-running"] = "created",
        direction: Literal["asc", "desc"] = "desc",
    ):
        """List the PRs of a UQCS GitHub repository"""
        if number_of_results > MAX_NUMBER_OF_PRS:
            await interaction.response.send_message(
                "Cannot list that many PRs.", ephemeral=True
            )

        await interaction.response.defer(thinking=True)
        repo = self.github.get_repo(f"{UQCS_GITHUB_ORGANISATION}/{REPOS[repo_name][0]}")
        embed = discord.Embed(
            title=f"PRs for {repo_name}",
            url=f"{UQCS_REPO_URL}{REPOS[repo_name][0]}/pulls",
        )
        prs = repo.get_pulls(state=state, sort=sort, direction=direction)
        for pr in prs[:number_of_results]:
            self.add_pr_to_embed(embed, pr)
        await interaction.edit_original_response(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Repos(bot))
