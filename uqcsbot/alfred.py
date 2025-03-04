import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.bot import UQCSBot


class Alfred(commands.Cog):
    def __init__(self, bot: UQCSBot):
        self.bot = bot

    @app_commands.command(name="alfred")
    async def alfred_command(self, interaction: discord.Interaction) -> None:
        """
        Returns info about Cyclone Alfred and UQ recommendations.
        """

        response = (
            "To track Cyclone Alfred, see the official Bureau of Meteorology webpage:\n"
            + "<http://www.bom.gov.au/cyclone/index.shtml>\n"
            + ""
            + "For current information about UQ's response, see:\n"
            + "<https://about.uq.edu.au/incident-response>\n"
            + ""
            + "For more information as to Brisbane City Council's flood zones, see:\n"
            + "<https://fam.brisbane.qld.gov.au/>\n"
            + "Moreton Bay Regional Council:\n"
            + "<https://www.moretonbay.qld.gov.au/Services/Property-Ownership/Flooding>\n"
            + "Logan City Council:\n"
            + "<https://www.logan.qld.gov.au/floodimpacts>\n"
            + "Sunshine Coast Council:\n"
            + "<https://disasterhub.sunshinecoast.qld.gov.au/>\n"
            + "\n"
            + "Please stay safe. And remember, if it's flooded, forget it.\n"
            + "\n"
            + "This information is not official UQCS advice, but simply a list of useful links for students to stay updated."
        )

        await interaction.response.send_message(response)


async def setup(bot: UQCSBot):
    cog = Alfred(bot)
    await bot.add_cog(cog)
