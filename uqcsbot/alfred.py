from discord.ext import commands

from uqcsbot.bot import UQCSBot

class Alfred(commands.Cog):
    def __init__(self, bot: UQCSBot):
        self.bot = bot

    @app_commands.command(name="alfred")
    async def alfred_command(
        self,
        interaction, discord.Interaction
    ) -> None:
        """
        Returns info about Cyclone Alfred and UQ recommendations.
        """

        response = f"""
        To track Cyclone Alfred, see the official Bureau of Meteorology webpage:
        <http://www.bom.gov.au/cyclone/index.shtml>

        For current informatino about UQ's response, see:
        <https://about.uq.edu.au/incident-response>

        To more information as to Brisbane City Council's flood zones, see:
        <https://fam.brisbane.qld.gov.au/>
        Moreton Bay Regional Council:
        <https://www.moretonbay.qld.gov.au/Services/Property-Ownership/Flooding>
        Logan City Council:
        <https://www.logan.qld.gov.au/floodimpacts>

        Please stay safe. And remember, if it's flooded, forget it.
        """

        await interaction.response.send_message(response)


async def setup(bot: UQCSBot):
    cog = Alfred(bot)
    await bot.add_cog(cog)
