import discord, asyncio
from discord import app_commands, ui

from discord.ext import commands
from uqcsbot.bot import UQCSBot

import uqcsbot.utils.snailrace_utils as snail


# Trying out Discord buttons for Snail Race Interactions
class SnailRaceView(discord.ui.View):
    def __init__(self, raceState: snail.SnailRaceState):
        super().__init__(timeout=snail.SNAILRACE_OPEN_TIME)
        self.raceState = raceState
    
    async def on_timeout(self):
        """
        Called when the view times out. This will deactivate the buttons and
        begine the race.
        """
        for child in self.children:
            child.disabled = True
        await self.raceState.open_interaction.edit_original_response(content=snail.SNAILRACE_ENTRY_CLOSE, view=self)
        await self.raceState.race_start()

    @ui.button(label="Enter Race", style=discord.ButtonStyle.primary)
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        action = self.raceState.add_racer(interaction.user)

        if action == snail.SnailRaceJoinAdded:
            await interaction.response.send_message(snail.SNAILRACE_JOIN % interaction.user.mention)
            return
        
        if action == snail.SnailRaceJoinRaceFull:
            await interaction.response.send_message(snail.SNAILRACE_FULL % interaction.user.mention)
            return
        
        await interaction.response.send_message(snail.SNAILRACE_ALREADY_JOINED % interaction.user.mention)
        

class SnailRace(commands.Cog):
    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self.race = snail.SnailRaceState()

    @app_commands.command(name="snailrace")
    async def open_race(self, interaction: discord.Interaction):
        """Open a new race for racers"""

        # Check if there is a race on
        if self.race.is_racing():
            await interaction.response.send_message(snail.SNAILRACE_ENTRY_ERR)
            return

        # Open up a new race for racers
        self.race.open_race(interaction)
        await interaction.response.send_message(snail.SNAILRACE_ENTRY_MSG, view=SnailRaceView(self.race))


async def setup(bot: UQCSBot):
    await bot.add_cog(SnailRace(bot))