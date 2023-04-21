import discord, random, datetime, asyncio

# Racer Icon
SNAILRACE_SNAIL_EMOJI = "🐌"

# Entry opening time
SNAILRACE_OPEN_TIME = 10
SNAILRACE_STEP_TIME = 1

# The number of characters in the track
SNAILRACE_TRACK_LENGTH_CHARS = 15

# The length of the track in steps
SNAILRACE_TRACK_LENGTH = 100

# The maximum and minimum number of steps a snail can take in a single turn
SNAILRACE_MAX_STEP = 15
SNAILRACE_MIN_STEP = 2

# Messages
SNAILRACE_ENTRY_ERR = "There is currently a race going on! Please wait until the current race finishes."
SNAILRACE_ENTRY_MSG = "The race is currently open for entry! Entry is open for the next %s seconds" % SNAILRACE_OPEN_TIME
SNAILRACE_ENTRY_CLOSE = "Entry is now closed. Let's Race!"
SNAILRACE_JOIN = "%s has Joined the Race!"
SNAILRACE_ALREADY_JOINED = "%s is already apart of the race."
SNAILRACE_BOARD = "And they're off...\n```\n%s\n```"
SNAILRACE_WINNER = "The race has finished! %s has won!"
SNAILRACE_NO_START = "Sorry, but there aren't enough racers to start the race!"

class SnailRacer:
    def __init__(self, member: discord.Member, racer_id: int):
        self.member = member
        self.racer_id = racer_id

        self.position = 0
        self.step_number = 0
    
    def step(self):
        # Calculate the number of positions the snail will take this step
        speed = random.randint(SNAILRACE_MIN_STEP, SNAILRACE_MAX_STEP)
        self.position = min(self.position + speed, SNAILRACE_TRACK_LENGTH)

        # If the snail has reached the end of the track, it can't move anymore
        if not self.position >= SNAILRACE_TRACK_LENGTH:
            self.step_number += 1

    def __str__(self):
        # Calculate the index of the snail emoji in the track
        index = min(
            int((self.position / SNAILRACE_TRACK_LENGTH) * SNAILRACE_TRACK_LENGTH_CHARS), 
            SNAILRACE_TRACK_LENGTH_CHARS - 1
        )

        # Create the track string
        track = SNAILRACE_TRACK_LENGTH_CHARS * [" "]
        track[:index] = ["."] * index
        track[index] = SNAILRACE_SNAIL_EMOJI
        track_str = "".join(track)

        return f"{str(self.racer_id).rjust(3)} |{track_str}| {self.member.display_name}"


class SnailRaceState:
    def __init__(self):
        self.race_start_time = datetime.datetime.now()
        self.racing = False
        
        self.racers = []
        self.open_interaction = None

    def is_racing(self) -> bool:

        # Calculate max race time with a 5 second bias
        max_race_len = SNAILRACE_OPEN_TIME + (SNAILRACE_STEP_TIME * SNAILRACE_TRACK_LENGTH) + 5
        if (datetime.datetime.now() - self.race_start_time).total_seconds() >= max_race_len:
            self.close_race()

        return self.racing

    def open_race(self, open_interaction: discord.Interaction):
        # Start the entry
        self.racing = True
        self.open_interaction = open_interaction

    def close_race(self):
        # Close the race for a new one to start
        self.racing = False
        self.racers = []
        self.open_interaction = None

    def add_racer(self, racer: discord.Member) -> bool:
        # Filter Unique Racers
        for r in self.racers:
            if r.member.id == racer.id:
                return False

        self.racers.append(SnailRacer(racer, len(self.racers) + 1))
        return True
    
    async def race_start(self):
        await self._start_racing(self.open_interaction)

    async def _start_racing(self, interaction: discord.Interaction):
        """
        Start the race loop, this will be triggered after the entry has closed.
        """

        if not len(self.racers) > 0:
            await interaction.channel.send(SNAILRACE_NO_START)
            self.close_race()
            return

        # Write the first message to the channel which will be edited later
        race_msg = await interaction.channel.send("BANG!")

        # Loop until all racers have finished
        while not all(r.position >= SNAILRACE_TRACK_LENGTH for r in self.racers):
            for r in self.racers:
                r.step()
           
            # Build the board and edit the race message with the new board
            board = str(SNAILRACE_BOARD % "\n".join(str(r) for r in self.racers))
            race_msg = await race_msg.edit(content=board)

            # Wait a second before the next step
            await asyncio.sleep(SNAILRACE_STEP_TIME)
        
        # Find who won
        min_steps = SNAILRACE_MIN_STEP *SNAILRACE_TRACK_LENGTH
        for r in self.racers:
            if r.step_number < min_steps:
                min_steps = r.step_number

        # Compile all the winners
        winners = ""
        for r in self.racers:
            if r.step_number == min_steps:
                winners += r.member.mention + " "
    
        # Conclude the race and send the winner
        await interaction.channel.send(SNAILRACE_WINNER % winners)
        self.close_race()