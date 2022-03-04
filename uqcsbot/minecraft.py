import logging
import os
import aiomcrcon
import discord
from discord.ext import commands
from uqcsbot.bot import UQCSBot

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
        """
        client = aiomcrcon.Client(RCON_ADDRESS, RCON_PORT, RCON_PASSWORD)

        try:
            await client.connect()
        except aiomcrcon.RCONConnectionError:
            return ("An error occured whilst connecting to the configured server.", -1)
        except aiomcrcon.IncorrectPasswordError:
            return ("The configured password is incorrect.", -1)

        try:
            response = await client.send_cmd(command)
        except aiomcrcon.ClientNotConnectedError:
            return ("The bot has is not connected to the server, please try again", -1)

        await client.close()
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

        split_response = [response[0][i:i+1900] for i in range(0, len(response[0]), 1900)]
        for split in split_response:
            await ctx.send(f"```{split}```")

def setup(bot: commands.Bot):
    bot.add_cog(Minecraft(bot))
