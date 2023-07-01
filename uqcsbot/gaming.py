from difflib import SequenceMatcher
from json import loads
from typing import Optional, Dict, Any, Set, TypedDict, Union
from urllib.error import HTTPError
from urllib.request import urlopen
from xml.etree.ElementTree import fromstring

import discord
from discord import app_commands
from discord.ext import commands
from requests import get

from uqcsbot.bot import UQCSBot


class Parameters(TypedDict):
    categories: Set[str]
    mechanics: Set[str]
    subranks: Dict[Any, Any]
    identity: str
    min_players: int
    max_players: int
    name: str
    score: Union[str, None]
    users: Union[str, None]
    rank: str
    description: Union[str, None]
    image: Union[str, None]
    min_time: str
    max_time: str


class Gaming(commands.Cog):
    """
    Various gaming related commands
    """

    def __init__(self, bot: UQCSBot):
        self.bot = bot

    def get_bgg_id(self, search_name: str) -> Optional[str]:
        """
        returns the bgg id, searching by name
        """
        query = get(
            f"https://www.boardgamegeek.com/xmlapi2/"
            + f"search?type=boardgame,boardgameexpansion&query={search_name:s}"
        )
        if query.status_code != 200:
            return None
        results = fromstring(query.text)
        if results.get("total", "0") == "0":
            return None

        # filters for the closest name match
        match: Any = {}
        for item in results:
            if item.get("id") is None:
                continue
            for element in item:
                if element.tag == "name":
                    match[item.get("id")] = SequenceMatcher(
                        None,
                        search_name,
                        (x if (x := element.get("value")) is not None else ""),
                    ).ratio()
        return max(match, key=match.get)

    def get_board_game_parameters(self, identity: str) -> Optional[Parameters]:
        """
        returns the various parameters of a board game from bgg
        """
        query = get(
            f"https://www.boardgamegeek.com/xmlapi2/thing?stats=1&id={identity:s}"
        )
        if query.status_code != 200:
            return None
        result = fromstring(query.text)[0]
        parameters: Parameters = {
            "categories": set(),
            "mechanics": set(),
            "subranks": {},
            "identity": identity,
            "min_players": -1,
            "max_players": -1,
            "name": "",
            "score": None,
            "users": None,
            "rank": "",
            "description": None,
            "image": None,
            "min_time": "",
            "max_time": "",
        }

        for element in result:
            tag = element.tag
            tag_name = element.attrib.get("name")
            tag_value = element.attrib.get("value", "")
            tag_type = element.attrib.get("type")
            tag_text = element.text

            # sets the range of players
            if tag == "poll" and tag_name == "suggested_numplayers":
                players: Set[int] = set()
                for option in element:
                    numplayers = option.attrib.get("numplayers", "0")
                    votes = 0

                    for result in option:
                        numvotes = int(result.attrib.get("numvotes", "0"))
                        direction = (
                            -1 if result.attrib.get("value") == "Not Recommended" else 1
                        )
                        votes += numvotes * direction

                    if votes > 0:
                        try:
                            players.add(int(numplayers))
                        except ValueError:
                            pass

                if players:
                    parameters["min_players"] = min(players)
                    parameters["max_players"] = max(players)

            # sets the backup min players
            if tag == "minplayers" and parameters["min_players"] == -1:
                parameters["min_players"] = int(tag_value)

            # sets the backup max players
            if tag == "maxplayers" and parameters["max_players"] == -1:
                parameters["max_players"] = int(tag_value)

            # sets the name of the board game
            elif tag == "name" and tag_type == "primary":
                parameters["name"] = tag_value

            # adds a category
            elif tag == "link" and tag_type == "boardgamecategory":
                parameters["categories"].add(tag_value)

            # adds a mechanic
            elif tag == "link" and tag_type == "boardgamemechanic":
                parameters["mechanics"].add(tag_value)

            # sets the user ratings
            elif tag == "statistics":
                for statistic in element[0]:
                    stat_tag = statistic.tag
                    stat_value = statistic.attrib.get("value", "")
                    if stat_tag == "average":
                        try:
                            parameters["score"] = str(round(float(stat_value), 2))
                        except ValueError:
                            parameters["score"] = stat_value
                    if stat_tag == "usersrated":
                        parameters["users"] = stat_value
                    if stat_tag == "ranks":
                        for genre in statistic:
                            genre_name = genre.attrib.get("name")
                            genre_value = genre.attrib.get("value", "")
                            if genre_name == "boardgame" and genre_value.isnumeric():
                                position = int(genre_value)
                                # gets the ordinal suffix
                                suffix = "tsnrhtdd"[
                                    (position / 10 % 10 != 1)
                                    * (position % 10 < 4)
                                    * position
                                    % 10 :: 4
                                ]
                                parameters["rank"] = f"{position:d}{suffix:s}"
                            elif genre_value.isnumeric():
                                friendlyname = genre.attrib.get("friendlyname", "")
                                # removes "game" as last word
                                friendlyname = " ".join(friendlyname.split(" ")[:-1])
                                position = int(genre_value)
                                # gets the ordinal suffix
                                suffix = "tsnrhtdd"[
                                    (position / 10 % 10 != 1)
                                    * (position % 10 < 4)
                                    * position
                                    % 10 :: 4
                                ]
                                parameters["subranks"][
                                    friendlyname
                                ] = f"{position:d}{suffix:s}"

            # sets the discription
            elif tag == "description":
                parameters["description"] = tag_text
            # sets the thumbnail
            elif tag == "image":
                parameters["image"] = tag_text
            # sets the minimum playing time
            elif tag == "minplaytime":
                parameters["min_time"] = tag_value
            elif tag == "maxplaytime":
                parameters["max_time"] = tag_value

        return parameters

    def format_board_game_parameters(self, parameters: Parameters) -> discord.Embed:
        embed = discord.Embed(title=parameters.get("name", ":question:"))
        embed.add_field(
            name="Summary",
            inline=False,
            value=(
                f"A board game for {parameters.get('min_players', ':question:')}"
                + (
                    f" to {parameters.get('max_players', ':question:')}"
                    if parameters.get("min_players") != parameters.get("max_players")
                    else ""
                )
                + " players, with a playing time of "
                + f" {parameters.get('min_time', ':question:'):s} minutes"
                + (
                    ""
                    if parameters.get("min_time") == parameters.get("max_time")
                    else f" to {parameters.get('max_time', ':question:'):s} minutes"
                )
                + ".\n"
                f"Rated {parameters.get('score', ':question:'):s}/10 by"
                + f" {parameters.get('users', ':question:'):s} users.\n"
                f"Ranked {parameters.get('rank', ':question:'):s} overall "
                + "on _Board Game Geek_.\n"
                + "".join(
                    f"• Ranked {value:s} in the {key:s} genre.\n"
                    for key, value in parameters.get("subranks", {}).items()
                )
                + f"Categories: {', '.join(parameters['categories']):s}\n"
                + f"Mechanics: {', '.join(parameters['mechanics']):s}\n"
            ),
        )
        max_message_length = 1000
        description: str = (
            x if (x := parameters["description"]) is not None else ":question:"
        )
        if len(description) > max_message_length:
            description = description[:max_message_length] + "\u2026"
        embed.add_field(name="Description", inline=False, value=description)
        embed.add_field(
            name="Board Game Geek Link",
            inline=False,
            value=f"https://boardgamegeek.com/boardgame/{parameters.get('identity'):s}",
        )
        embed.set_thumbnail(url=parameters.get("image"))
        return embed

    @app_commands.command()
    @app_commands.describe(board_game="Board game to search for")
    async def bgg(self, interaction: discord.Interaction, board_game: str):
        """
        Gets the details of the provided board game from Board Game Geek
        """
        await interaction.response.defer(thinking=True)

        identity = self.get_bgg_id(board_game)
        if identity is None:
            await interaction.edit_original_response(
                content="Could not find board game with that name."
            )
            return

        parameters = self.get_board_game_parameters(identity)
        if parameters is None:
            await interaction.edit_original_response(
                content="Something has gone wrong."
            )
            return

        embed = self.format_board_game_parameters(parameters)
        await interaction.edit_original_response(embed=embed)

    @app_commands.command()
    @app_commands.describe(card="Card to search for")
    async def scry(self, interaction: discord.Interaction, card: Optional[str]):
        """
        Returns the Magic: the Gathering card that matches (partially or
        fully) the given argument (or a random card if no argument given)
        """
        await interaction.response.defer(thinking=True)

        # random card if no argument
        if card:
            request = "https://api.scryfall.com/cards/named?fuzzy=" + card.replace(
                " ", "+"
            )
        else:
            request = "https://api.scryfall.com/cards/random"

        # try find card
        try:
            response = urlopen(request)
        except HTTPError as e:
            # will 404 if cannot find a unique result
            if e.code == 404:
                fault = loads(e.read())
                if fault.get("type") == "ambiguous":
                    await interaction.edit_original_response(
                        content="Request 404'd; Multiple Possible Cards"
                    )
                else:
                    await interaction.edit_original_response(
                        content="Request 404'd; No Cards Found"
                    )
                return
            await interaction.edit_original_response(content=str(e))
            return

        card_obj: Any = loads(response.read())
        if "image_uris" in card_obj:
            # single faced cards
            await interaction.edit_original_response(
                content=card_obj["image_uris"]["png"]
            )
        else:
            # double faced cards
            await interaction.edit_original_response(
                content="\n".join(
                    face["image_uris"]["png"] for face in card_obj["card_faces"]
                )
            )


async def setup(bot: UQCSBot):
    await bot.add_cog(Gaming(bot))
