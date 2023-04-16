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
        if self.raceState.add_racer(interaction.user):
            await interaction.response.send_message(snail.SNAILRACE_JOIN % interaction.user.mention)
            return
        
        await interaction.response.send_message(snail.SNAILRACE_ALREADY_JOINED % interaction.user.mention)
        

class SnailRace(commands.Cog):
    snailrace_group = app_commands.Group(name="snailrace", description="Snail Race Commands")

    def __init__(self, bot: UQCSBot):
        self.bot = bot
        self.race = snail.SnailRaceState(self.start_racing)

    @snailrace_group.command(name="open")
    async def open_race(self, interaction: discord.Interaction):
        """Open a new race for racers"""

        # Check if there is a race on
        if self.race.racing:
            await interaction.response.send_message(snail.SNAILRACE_ENTRY_ERR)
            return

        # Open up a new race for racers
        self.race.open_race(interaction)
        await interaction.response.send_message(snail.SNAILRACE_ENTRY_MSG, view=SnailRaceView(self.race))

    async def start_racing(self, interaction: discord.Interaction):
        """
        Start the race loop, this will be triggered after the entry has closed.
        """

        if not len(self.race.racers) > 0:
            await interaction.channel.send(snail.SNAILRACE_NO_START)
            self.race.close_race()
            return

        # Write the first message to the channel which will be edited later
        race_msg = await interaction.channel.send("BANG!")

        # Loop until all racers have finished
        while not all(r.position >= snail.SNAILRACE_TRACK_LENGTH for r in self.race.racers):
            for r in self.race.racers:
                r.step()
           
            # Build the board and edit the race message with the new board
            board = str(snail.SNAILRACE_BOARD % "\n".join(str(r) for r in self.race.racers))
            race_msg = await race_msg.edit(content=board)

            # Wait a second before the next step
            await asyncio.sleep(snail.SNAILRACE_STEP_TIME)
        
        # Find who won
        min_steps = snail.SNAILRACE_MIN_STEP * snail.SNAILRACE_TRACK_LENGTH
        for r in self.race.racers:
            if r.step_number < min_steps:
                min_steps = r.step_number

        # Compile all the winners
        winners = ""
        for r in self.race.racers:
            if r.step_number == min_steps:
                winners += r.member.mention + " "
    
        # Conclude the race and send the winner
        await interaction.channel.send(snail.SNAILRACE_WINNER % winners)
        self.race.close_race()


async def setup(bot: UQCSBot):
    await bot.add_cog(SnailRace(bot))