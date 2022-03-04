import logging
import os
import discord
from discord.ext import commands
from uqcsbot.bot import UQCSBot
from aiomcrcon import Client, IncorrectPasswordError, RCONConnectionError

RCON_ADDRESS = os.environ.get("MC_RCON_ADDRESS")
RCON_PORT = os.environ.get("MC_RCON_PORT")
RCON_PASSWORD = os.environ.get("MC_RCON_PASSWORD")

class Minecraft(commands.Cog):
    def __init__(self, bot: UQCSBot):
        self.bot = bot

    async def send_rcon_command(self, command: str):
        """ 
        Sends a command via RCON to the server defined in environment variables.
        
        Args:
        command: str - The command to send to the server.

        Returns:
        A tuple with the response message, and ID for the return message.
        An ID of -1 is returned if there was an issue connecting to the server.
        """
        try:
            async with Client(RCON_ADDRESS, RCON_PORT, RCON_PASSWORD) as client:
                response = await client.send_cmd(command)

        except RCONConnectionError:
            return ("An error occured whilst connecting to the configured server.", -1)
        except IncorrectPasswordError:
            return ("The configured password is incorrect.", -1)

        return response

    @commands.command()
    async def mcwhitelist(self, ctx: commands.Context, username: str):
        """ Adds a username to the whitelist for the UQCS server. """
        response = await self.send_rcon_command(f"whitelist add {username}")
        logging.info(response)

        await ctx.send(response[0])

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def mcadmin(self, ctx: commands.Context, *, command: str):
        """ Sends commands to the configured Minecraft server via RCON. """
        response = await self.send_rcon_command(command)
        logging.info(response)

        # As Discord has a 2000 character limit for messages, the message is split with space
        # for any additional items within request. Notably useful for the help command.
        split_response = [response[0][i:i+1900] for i in range(0, len(response[0]), 1900)]
        for split in split_response:
            await ctx.send(f"```{split}```")

def setup(bot: commands.Bot):
    bot.add_cog(Minecraft(bot))
