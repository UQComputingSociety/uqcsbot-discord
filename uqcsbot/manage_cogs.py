from typing import Literal, List, Dict

import discord
from discord import app_commands
from discord.ext import commands

COG_GROUPS: Dict[str, List[str]] = {
    "cron": ["working_on", "holidays"],
    "db": ["starboard", "remindme", "advent", "minecraft"],
}


class ManageCogs(commands.Cog):
    """
    Note that most of these commands can make the bot load files to execute. Care should be made to ensure only entrusted users have access.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="managecogs")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        cog='The cog (i.e. python file) to try to unload. Use python package notation, so no suffix of ".py" and "." between folders: e.g. "manage_cogs".',
    )
    async def manage_cogs(
        self,
        interaction: discord.Interaction,
        action: Literal[
            "load", "unload", "reload", "load-all", "unload-all", "reload-all"
        ],
        cog: str,
    ):
        """
        Trys to unload a cog (i.e. python file).
        Note that most of these commands can make the bot load files to execute. Care should be made to ensure only entrusted users have access.
        """
        try:
            match action:
                case "load":
                    await self.bot.load_extension(f"uqcsbot.{cog}")
                case "unload":
                    await self.bot.unload_extension(f"uqcsbot.{cog}")
                case "reload":
                    await self.bot.reload_extension(f"uqcsbot.{cog}")
                case "load-all":
                    if (cogs := COG_GROUPS.get(cog)) is not None:
                        for x in cogs:
                            await self.bot.load_extension(f"uqcsbot.{x}")
                    else:
                        raise RuntimeError(f"Unknown cog group {cog}")
                case "unload-all":
                    if (cogs := COG_GROUPS.get(cog)) is not None:
                        for x in cogs:
                            await self.bot.unload_extension(f"uqcsbot.{x}")
                    else:
                        raise RuntimeError(f"Unknown cog group {cog}")
                case "reload-all":
                    if (cogs := COG_GROUPS.get(cog)) is not None:
                        for x in cogs:
                            await self.bot.reload_extension(f"uqcsbot.{x}")
                    else:
                        raise RuntimeError(f"Unknown cog group {cog}")
        except Exception as error:
            # Many errors can be caught during loading/unloading/reloading the bot, so it would be painful to separate by exception type
            await interaction.response.send_message(
                f"Error occured {action}ing {cog}: {error}"
            )
            return
        await interaction.response.send_message(f"Successfully {action}ed {cog}")
        await self.bot.tree.sync()


async def setup(bot: commands.Bot):
    await bot.add_cog(ManageCogs(bot))
