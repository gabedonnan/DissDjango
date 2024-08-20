import json
import random
import asyncio

import numpy as np

from channels.generic.websocket import AsyncWebsocketConsumer

from .auctions import *


# All auction instances are stored in this global variable and keyed by room ID
# This is because to serve multiple users an arbitrary number of SimConsumer objects will be created without my control
auction_instances: dict[str, Auction | None] = {

}


class SimConsumer(AsyncWebsocketConsumer):
    room_id: str
    room_group_id: str
    connection_counter: int = 0
    query_params: dict = None
    room_type: str

    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_name"]
        print("ROOM_ID", self.room_id)
        self.room_type = self.scope["path"][4:self.scope["path"][4:].find("/") + 4]
        print("room type", self.room_type)

        if self.room_id not in auction_instances:
            auction_instances[self.room_id] = None
        else:
            # A created room should never be none, reject connection if so
            if auction_instances[self.room_id] is None:
                await self.close()

        await self.channel_layer.group_add(
            self.room_id,
            self.channel_name,
        )
        await self.accept()
        self.connection_counter += 1

    async def disconnect(self, code: int):
        await self.channel_layer.group_discard(
            self.room_id,
            self.channel_name,
        )
        self.connection_counter -= 1
        if self.connection_counter == 0:
            del auction_instances[self.room_id]

    async def receive(
        self, text_data: str | None = None, bytes_data: bytes | None = None
    ):
        room_name = self.scope["url_route"]["kwargs"]["room_name"]
        sim = auction_instances[room_name]

        # Format {username: ..., message: {...}}
        parsed_data = json.loads(text_data)

        # By default, most server interactions will not cause a broadcast to connected browsers
        broadcast_msg = False

        # Interpret json data from web client
        username = parsed_data["username"]
        message = parsed_data["message"]

        # The final message to be broadcast
        res = {}

        # Room ID should be equal to the username code of the admin user
        # I.e. If username = room id the admin is making changes

        if (
            self.query_params is None
            and "window_search" in message
            and message["window_search"] != ""
        ):
            self.query_params = {
                elem.split("=")[0]: elem.split("=")[1]
                for elem in message["window_search"][1:].split("&")
                if len(elem) > 0
            }

        if "register_user" in message:
            if username not in sim.users:
                if sim is None and self.query_params is not None:
                    # parse initial page arguments to augment auction
                    room_type = self.room_type

                    limit_price_distribution = await self.get_limit_distribution()

                    await self.set_room_type(limit_price_distribution, room_type)

                    await self.set_initial_params_from_query()

                    sim.auctioneer = username

                sim.add_user(username, sim.limit_price_distribution)

            broadcast_msg = True
            res["countdown_timer"] = int(
                (sim.timestamp + int(sim.time_difference)) - time()
            )
            res["max_time"] = sim.time_difference
            res["set_price"] = sim.auction_price
            res["limit_price"] = sim.users[username].limit_price

        if "update_auction" in message:
            broadcast_msg = await self.try_update_auction(broadcast_msg, message, res, username)

        if broadcast_msg:
            print(res)
            # Should only be done if message is state-updating
            await self.channel_layer.group_send(
                self.room_id,
                {
                    "type": "send_message",
                    "message": res,
                    "username": username,
                },
            )

    async def try_update_auction(self, broadcast_msg, message, res, username):
        auction_updated = False
        sim = auction_instances[self.room_id]
        # Instruction should be a tuple (instruction, [args])
        # Each instruction should return a boolean based on whether the auction has been updated
        # This can be used to determine whether a message should be broadcast
        instruction = message["update_auction"]
        if instruction["method"] == "ask" and hasattr(sim, "ask"):
            auction_updated = sim.ask(username, instruction["price"])
        elif instruction["method"] == "bid" and hasattr(sim, "bid"):
            if isinstance(sim, DutchAuction):
                # Dutch auctions do not require a provided price to bid
                auction_updated = sim.bid(username)
            else:
                auction_updated = sim.bid(username, instruction["price"])
        elif (
                instruction["method"] == "initial_offer"
                and username == sim.auctioneer
                and hasattr(sim, "auctioneer_initial_offer")
        ):
            auction_updated = sim.auctioneer_initial_offer(
                username,
                instruction["asset"],
                instruction["price"],
                instruction["quantity"],
            )
        elif (
                instruction["method"] == "update_offer"
                and username == sim.auctioneer
                and hasattr(sim, "auctioneer_update_offer")
        ):
            auction_updated = sim.auctioneer_update_offer(
                username, instruction["price"]
            )
        # if auction updated, make sure message is broadcast
        # But dont remove previous message broadcast approvals
        broadcast_msg = auction_updated or broadcast_msg
        if auction_updated and hasattr(sim, "auction_price"):
            res["price_update"] = sim.auction_price
            res["profit_update"] = [sim.users[username].profits, username]
        return broadcast_msg

    async def set_initial_params_from_query(self):
        sim = auction_instances[self.room_id]
        if "time" in self.query_params and self.query_params[
            "time"
        ] not in ["", None]:
            sim.time_difference = self.query_params["time"]
        if "starting_money" in self.query_params and self.query_params[
            "starting_money"
        ] not in ["", None]:
            sim.asset_range = self.query_params[
                "starting_money"
            ].split(",")
        if "starting_bid" in self.query_params and self.query_params[
            "starting_bid"
        ] not in ["", None]:
            sim.auction_price = self.query_params["starting_bid"]

    async def get_limit_distribution(self):
        if (
                "limit_distribution" in self.query_params
                and "limit_min" in self.query_params
                and "limit_max" in self.query_params
        ):
            self.query_params["limit_min"] = int(self.query_params["limit_min"])
            self.query_params["limit_max"] = int(self.query_params["limit_max"])

            match self.query_params["limit_distribution"]:
                case "uniform":
                    limit_price_distribution = (
                        random.uniform,
                        self.query_params["limit_min"],
                        self.query_params["limit_max"],
                    )
                case "normal":
                    limit_price_distribution = (
                        np.random.normal,
                        self.query_params["limit_min"],
                        self.query_params["limit_max"],
                    )
                case _:
                    limit_price_distribution = (
                        random.uniform,
                        self.query_params["limit_min"],
                        self.query_params["limit_max"],
                    )
        else:
            limit_price_distribution = (
                random.uniform, 100, 1000
            )
        return limit_price_distribution

    async def set_room_type(self, limit_price_distribution, room_type):
        sim = None
        match room_type:
            case "english":
                sim = EnglishAuction(
                    [], limit_price_distribution
                )
            case "dutch":
                sim = DutchAuction(
                    [], limit_price_distribution
                )
            case "FPSB":
                sim = FirstPriceSealedBidAuction(
                    [], limit_price_distribution
                )
            case "SPSB":
                sim = SecondPriceSealedBidAuction(
                    [], limit_price_distribution
                )
            case "CDA":
                sim = ContinuousDoubleAuction(
                    [], limit_price_distribution
                )

        auction_instances[self.room_id] = sim

    async def send_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "message": event["message"],
                    "username": event["username"],
                }
            )
        )
