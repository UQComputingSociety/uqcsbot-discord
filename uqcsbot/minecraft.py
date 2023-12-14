import logging
import os
from datetime import datetime

import discord
from aiomcrcon import Client, IncorrectPasswordError, RCONConnectionError  # type: ignore
from discord import Member, app_commands, Colour
from discord.ext import commands

from uqcsbot.bot import UQCSBot
from uqcsbot.models import MCWhitelist
from uqcsbot.utils.err_log_utils import FatalErrorWithLog
from uqcsbot.yelling import yelling_exemptor

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
            if RCON_ADDRESS is None or RCON_PORT is None or RCON_PASSWORD is None:
                raise FatalErrorWithLog(
                    self.bot, "Attempted to send RCON command but couldn't log in!"
                )

            async with Client(RCON_ADDRESS, int(RCON_PORT), RCON_PASSWORD) as client:
                response = await client.send_cmd(command)

        except RCONConnectionError:
            return ("An error occured whilst connecting to the configured server.", -1)
        except IncorrectPasswordError:
            return ("The configured password is incorrect.", -1)

        return response

    @app_commands.command()
    @app_commands.describe(username="Minecraft username to whitelist.")
    @yelling_exemptor(input_args=["username"])
    async def mcwhitelist(self, interaction: discord.Interaction, username: str):
        """Adds a username to the whitelist for the UQCS server."""
        db_session = self.bot.create_db_session()
        query = db_session.query(MCWhitelist).filter(
            MCWhitelist.discord_id == interaction.user.id
        )
        is_user_admin = (
            isinstance(interaction.user, Member)
            and interaction.user.guild_permissions.manage_guild
        )

        # If the user has already whitelisted someone, and they aren't an admin deny it.
        if not is_user_admin and query.count() > 0:
            await interaction.response.send_message(
                "You've already whitelisted an account."
            )
        else:
            response = await self.send_rcon_command(f"whitelist add {username}")
            logging.info(f"[MINECRAFT] whitelist {username}: {response}")

            # If the response contains "Added", assume that it was successful and add a database item for it
            if "Added" in response[0]:
                new_whitelist = MCWhitelist(
                    mc_username=username,
                    discord_id=interaction.user.id,
                    admin_whitelisted=is_user_admin,
                    added_dt=datetime.now(),
                )
                db_session.add(new_whitelist)
                db_session.commit()

                await self.bot.admin_alert(
                    title="Minecraft Server Whitelist",
                    description=response[0],
                    footer=f"Action performed by {interaction.user}",
                    colour=Colour.green(),
                )

            await interaction.response.send_message(response[0])

        db_session.close()
    
    @app_commands.command() 
    @app_commands.describe(username="Minecraft username to unwhitelist.")
    @yelling_exemptor(input_args=["username"])
    async def mcunwhitelist(self, interaction: discord.Interaction, username: str):
        """Removes a username from the whitelist for the UQCS server."""
        db_session = self.bot.create_db_session()
        query = db_session.query(MCWhitelist).filter(
            MCWhitelist.discord_id == interaction.user.id
        )
        is_user_admin = (
            isinstance(interaction.user, Member)
            and interaction.user.guild_permissions.manage_guild
        )

        # If the user has already whitelisted someone, and they aren't an admin deny it.
        if not is_user_admin and query.count() > 0:
            await interaction.response.send_message(
                "You've already whitelisted an account."
            )
        else:
            # Send the RCON command to remove the user from the whitelist
            response_remove = await self.send_rcon_command(f"whitelist remove {username}")
            logging.info(f"[MINECRAFT] whitelist remove {username}: {response_remove}")

            # Send the RCON command to kick the player from the server
            response_kick = await self.send_rcon_command(f"kick {username}")
            logging.info(f"[MINECRAFT] kick {username}: {response_kick}")

            # If the responses indicate successful removal and kick, remove the database item
            if "Removed" in response_remove[0] and "Kicked" in response_kick[0]:
                query.delete()
                db_session.commit()

                await self.bot.admin_alert(
                    title="Minecraft Server Unwhitelist",
                    description=f"{response_remove[0]}\n{response_kick[0]}",
                    footer=f"Action performed by {interaction.user}",
                    colour=Colour.red(),  # Use red to indicate removal
                )

            await interaction.response.send_message(f"{response_remove[0]}\n{response_kick[0]}")

        db_session.close()        

    mcadmin_group = app_commands.Group(
        name="mcadmin", description="Commands for managing the UQCS Minecraft server"
    )

    @mcadmin_group.command(name="run")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        command="Command to run on server. This will run exactly as input."
    )
    async def mcadmin(self, interaction: discord.Interaction, command: str):
        """Sends commands to the configured Minecraft server via RCON."""
        response = await self.send_rcon_command(command)
        logging.info(f"[MINECRAFT] {command}: {response}")

        # As Discord has a 2000 character limit for messages, the message is split with space
        # for any additional items within request. Notably useful for the help command.
        split_response = [
            response[0][i : i + 1900] for i in range(0, len(response[0]), 1900)
        ]
        await interaction.response.send_message(f"```{split_response[0]}```")

        # If we are over the character limit, send in follow up messages.
        if len(split_response[1:]) > 0:
            for split in split_response[1:]:
                await interaction.followup.send(f"```{split}```")

        await self.bot.admin_alert(
            title="Minecraft Server Admin Command",
            fields=[
                ("Command", command),
                (
                    "Response",
                    split_response[0][:1024],
                ),  # These fields can only be 1024 characters max
            ],
            footer=f"Action performed by {interaction.user}",
            colour=Colour.green(),
            fields_inline=False,
        )


async def setup(bot: UQCSBot):
    await bot.add_cog(Minecraft(bot))