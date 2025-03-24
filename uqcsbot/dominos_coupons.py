from datetime import datetime
from typing import List, Dict, Tuple, Optional, Literal
import logging
from requests.exceptions import RequestException
import random

import discord
from discord import app_commands
from discord.ext import commands

from uqcsbot.bot import UQCSBot
from uqcsbot.yelling import yelling_exemptor
from uqcsbot.utils.dominos_utils import Coupon, Store, get_filtered_stores

MAX_COUPONS = 10  # Prevents abuse
MAX_STORES = 5


class StoreSelect(discord.ui.Select):
    def __init__(self, stores: List[Store]):
        # self.view = view
        options=[discord.SelectOption(label=store.name,description=store.address)for store in stores]
        super().__init__(placeholder="Select a store...", options=options)

    async def callback(self, interaction: discord.Interaction):
        # await interaction.response.send_message(content=f"Selected {self.values[0]}")
        self.view.selected_store = self.values[0]
        self.view.stop()

class StoreSelectView(discord.ui.View):
    def __init__(self, stores: List[Store], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_store = None
        self.add_item(StoreSelect(stores))

class StoreDetailsView(discord.ui.View):
    def __init__(self, store: Store, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.store = store
        self.state = None

    @discord.ui.button(label="Get Coupons", style=discord.ButtonStyle.primary)
    async def get_coupons(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.state = True
        self.stop()

order_method = Literal["Any", "Delivery", "Pickup", "Dine In"]

class DominosCoupons(commands.GroupCog, group_name='dominos'):
    def __init__(self, bot: UQCSBot):
        self.bot = bot

    @app_commands.command()
    @app_commands.describe(
        search_term="The name of the store to search for.",
        open_at="The time to check if the store is open. Defaults to now. Format: YYYY-MM-DD HH:MM:SS",
        service_method="Filter by supported service type. Defaults to any."
    )
    @yelling_exemptor(input_args=["search_term"])
    async def stores(
            self,
            interaction: discord.Interaction,
            search_term: str,
            open_at: str = None,
            service_method: Literal[order_method] = "Any",
    ):
        """
        Returns a list of dominos stores
        """
        await interaction.response.defer(thinking=True)

        if open_at:
            try:
                checking_time = datetime.strptime(open_at, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                await interaction.edit_original_response(
                    content="Invalid date format. Use YYYY-MM-DD HH:MM:SS."
                )
                return
        else:
            checking_time = datetime.now()

        stores: List[Store] = get_filtered_stores(search_term, service_method, checking_time, MAX_STORES)

        if stores is None:
            await interaction.edit_original_response(
                content=f"Something went wrong."
            )
            return
        if len(stores) == 0:
            response_text = f"Could not find any stores matching `{search_term}`"
            if service_method != "Any":
                response_text += f" with service method `{service_method}`"
            await interaction.edit_original_response(content=f"{response_text}.")
            return

        if stores[0].matches(search_term):
            # If exact match, proceed straight to the store details
            store_str = stores[0].name
        else:
            # Display a list of stores to choose from
            description_string = f"Searching for stores matching `{search_term}`"
            view = StoreSelectView(stores)
            await interaction.edit_original_response(content=description_string, view=view)
            await view.wait()

            store_str = view.selected_store

            if store_str is None:
                await interaction.edit_original_response(content="No store selected.")
                return

        store = next((store for store in stores if store.name == store_str), None)
        if store is None:
            await interaction.edit_original_response(content="Something went wrong.")
            return

        embed = discord.Embed(
            title=store.name,
            timestamp=checking_time,
        )
        embed.add_field(name="Address", value=store.address, inline=False)
        embed.add_field(name="Phone", value=store.phone_no, inline=False)
        try:
            store_open = store.is_open(checking_time)
            next_open_time = store.next_opening_time(checking_time)
            next_closed_time = store.next_closing_time(checking_time)
        except ValueError:
            pass
        else:
            if store_open is None:
                pass
            elif store_open and next_open_time:
                embed.add_field(name="Open", value=f"Until {next_closed_time}", inline=False)
            elif not store_open and next_closed_time:
                embed.add_field(name="Closed", value=f"Until {next_open_time}", inline=False)
            else:
                embed.add_field(name="Currently", value='Open' if store_open else "Closed", inline=False)

        view = StoreDetailsView(store) if store.has_coupons() else None
        await interaction.edit_original_response(content=None, embed=embed, view=view)
        if not view:
            return

        await view.wait()
        if not view.state:
            return

        embed = discord.Embed(
            title="Domino's Coupons",
            description=f"For {store.name} ({store.address})",
            timestamp=checking_time,
        )
        coupons = store.get_filtered_coupons(service_method=service_method,
                                             checking_time=checking_time,
                                             count=MAX_COUPONS)
        for coupon in coupons:
            embed.add_field(
                name=coupon.code,
                value=f"{coupon.description}\n*[Expires {coupon.expiry_date}, {coupon.method}]*",
                inline=False,
            )

        await interaction.edit_original_response(embed=embed, view=None)


    @app_commands.command()
    @app_commands.describe(
        store_search="Store to get coupons for. Defaults to St Lucia.",
        number_of_coupons=f"The number of coupons to return. Defaults to {MAX_COUPONS}.",
        service_method="Filter by supported service type. Defaults to any.",
        ignore_expiry="Indicates to include coupons that have expired. Defaults to False.",
        keywords="Words to search for within the coupon. All coupons descriptions will mention at least one keyword."
    )
    @yelling_exemptor(input_args=["keywords"])
    async def coupons(
        self,
        interaction: discord.Interaction,
        store_search: str = "St Lucia",
        number_of_coupons: app_commands.Range[int, 1, MAX_COUPONS] = MAX_COUPONS,
        service_method: order_method = "Any",
        ignore_expiry: bool = False,
        keywords: str = "",
    ):
        """
        Returns a list of dominos coupons
        """
        await interaction.response.defer(thinking=True)

        expiry_time = datetime.now() if not ignore_expiry else None

        # Get stores
        # Limit to 3 stores, hopefully including the one the user wants
        stores: List[Store] = get_filtered_stores(store_search,
                                                  service_method=service_method,
                                                  open_at_time=expiry_time,
                                                  count=3)
        if stores is None:
            await interaction.edit_original_response(content=f"Something went wrong.")
            return
        if len(stores) == 0:
            response_text = f"Could not find any stores matching `{store_search}`"
            if service_method != "Any":
                response_text += f" with service method `{service_method}`"
            await interaction.edit_original_response(
                content=f"{response_text}."
            )
            return

        # If exact match select just that store
        # Otherwise, choose the first three.
        if stores[0].matches(store_search):
            # If exact match, proceed straight to the store details
            stores = stores[:1]
        else:
            stores = stores[:3]
        print(stores)

        # Get coupons for each store
        coupons: List[Coupon] = []
        for store in stores:
            try:
                coupons.extend(store.get_filtered_coupons(service_method=service_method,
                                                          checking_time=expiry_time,
                                                          keywords=keywords))
            except RequestException:
                print("Error getting coupons for store:", store.name)
                continue


        if not coupons:
            await interaction.edit_original_response(content="No coupons found.")
            return

        description_string = ""
        if len(stores) == 1:
            description_string += f"For {stores[0].name} ({stores[0].address})"
        if keywords:
            description_string += f"\nKeywords: *{keywords}*"

        # Remove duplicates
        unique_coupons: List[Coupon] = []
        unique_codes: List[str] = []
        for coupon in coupons:
            if coupon.code not in unique_codes:
                unique_codes.append(coupon.code)
                unique_coupons.append(coupon)
        coupons = unique_coupons

        random.shuffle(coupons)
        coupons = coupons[:number_of_coupons]

        embed = discord.Embed(
            title="Domino's Coupons",
            description=description_string.strip(),
            timestamp=datetime.now(),
        )
        for coupon in coupons:
            embed.add_field(
                name=coupon.code,
                value=f"{coupon.description}\n*[Expires {coupon.expiry_date}, {coupon.method}]*",
                inline=False,
            )

        await interaction.edit_original_response(embed=embed, view=None)


async def setup(bot: UQCSBot):
    await bot.add_cog(DominosCoupons(bot))
