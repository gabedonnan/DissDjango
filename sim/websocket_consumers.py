import json

from channels.generic.websocket import AsyncWebsocketConsumer

from .auctions import *


class SimConsumer(AsyncWebsocketConsumer):
    room_id: str
    room_group_id: str
    connection_counter: int = 0
    sim: Auction = EnglishAuction([], set())
    query_params: dict = None

    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_name"]

        if (
            self.query_params is None
            and self.scope["query_string"].decode("utf-8") != ""
        ):
            self.query_params = {
                elem.split("=")[0]: elem.split("=")[1]
                for elem in self.scope["query_string"].decode("utf-8").split("&")
            }

        print(self.query_params)

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
            self.sim = EnglishAuction([], set())

    async def receive(
        self, text_data: str | None = None, bytes_data: bytes | None = None
    ):
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

        if "register_user" in message and username not in self.sim.users:
            if self.sim.auctioneer is None:
                self.sim.auctioneer = username

                if self.query_params is not None:
                    # parse initial page arguments to augment auction
                    if "room_type" in self.query_params and self.query_params[
                        "room_type"
                    ] not in ["", None]:
                        room_type = self.query_params["room_type"]

                        match room_type:
                            case "english":
                                self.sim = EnglishAuction([], set())
                            case "dutch":
                                self.sim = DutchAuction([], set())
                            case "FPSB":
                                self.sim = FirstPriceSealedBidAuction([], set())
                            case "SPSB":
                                self.sim = SecondPriceSealedBidAuction([], set())
                            case "CDA":
                                self.sim = ContinuousDoubleAuction([], set())

                    if "time" in self.query_params and self.query_params[
                        "time"
                    ] not in ["", None]:
                        self.sim.time_difference = self.query_params["time"]

                    if "starting_money" in self.query_params and self.query_params[
                        "starting_money"
                    ] not in ["", None]:
                        self.sim.asset_range = self.query_params[
                            "starting_money"
                        ].split(",")

                    if "starting_bid" in self.query_params and self.query_params[
                        "starting_bid"
                    ] not in ["", None]:
                        self.sim.auction_price = self.query_params["starting_bid"]
                else:
                    print("Something's gone wrong!! Descriptive message innit")

            self.sim.add_user(username)
            broadcast_msg = True
            res["countdown_timer"] = int(
                (self.sim.timestamp + self.sim.time_difference) - time()
            )
            res["max_time"] = self.sim.time_difference
        elif "register_user" in message and username in self.sim.users:
            broadcast_msg = True
            res["countdown_timer"] = int(
                (self.sim.timestamp + self.sim.time_difference) - time()
            )
            res["max_time"] = self.sim.time_difference

        if "update_auction" in message:
            auction_updated = False
            # Instruction should be a tuple (instruction, [args])
            # Each instruction should return a boolean based on whether the auction has been updated
            # This can be used to determine whether a message should be broadcast
            instruction = message["update_auction"]
            if instruction["method"] == "ask" and hasattr(self.sim, "ask"):
                auction_updated = self.sim.ask(username, instruction["price"])
            elif instruction["method"] == "bid" and hasattr(self.sim, "bid"):
                if isinstance(self.sim, DutchAuction):
                    # Dutch auctions do not require a provided price to bid
                    auction_updated = self.sim.bid(username)
                else:
                    auction_updated = self.sim.bid(username, instruction["price"])
            elif (
                instruction["method"] == "initial_offer"
                and username == self.sim.auctioneer
                and hasattr(self.sim, "auctioneer_initial_offer")
            ):
                auction_updated = self.sim.auctioneer_initial_offer(
                    username,
                    instruction["asset"],
                    instruction["price"],
                    instruction["quantity"],
                )
            elif (
                instruction["method"] == "update_offer"
                and username == self.sim.auctioneer
                and hasattr(self.sim, "auctioneer_update_offer")
            ):
                auction_updated = self.sim.auctioneer_update_offer(
                    username, instruction["price"]
                )

            # if auction updated, make sure message is broadcast
            # But dont remove previous message broadcast approvals
            broadcast_msg = auction_updated or broadcast_msg

            if auction_updated and hasattr(self.sim, "auction_price"):
                res["price_update"] = self.sim.auction_price

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

    async def send_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "message": event["message"],
                    "username": event["username"],
                }
            )
        )
