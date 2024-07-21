import json

from channels.generic.websocket import AsyncWebsocketConsumer

from .auctions import *


class SimConsumer(AsyncWebsocketConsumer):
    room_id: str
    room_group_id: str
    admin: str | None = None
    sim: Auction = DutchAuction([], set())
    users: set[str] = set()

    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_name"]

        await self.channel_layer.group_add(
            self.room_id,
            self.channel_name,
        )
        await self.accept()

    async def disconnect(self, code: int):
        await self.channel_layer.group_discard(
            self.room_id,
            self.channel_name,
        )

    async def receive(
        self, text_data: str | None = None, bytes_data: bytes | None = None
    ):
        # Format {username: ..., message: {...}}
        parsed_data = json.loads(text_data)

        # By default most server interactions will not cause a broadcast to connected browsers
        broadcast_msg = False

        # Interpret json data from web client
        username = parsed_data["username"]
        message = parsed_data["message"]

        print(message)

        # The final message to be broadcast
        res = {"username": username, "message": {}}

        # Room ID should be equal to the username code of the admin user
        # I.e. If username = room id the admin is making changes

        if "register_user" in message and username not in self.sim.users:
            if self.admin is None:
                self.admin = username
                self.sim.auctioneer = username

            self.sim.add_user(username)

        if username == self.admin:
            if "rooom_type" in message:
                room_type = message["room_type"]
                cur_users = self.sim.users

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

                self.sim.users = cur_users

            if "timer" in message:
                self.sim.time_difference = message["timer"]

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
                res["message"]["price_update"] = self.sim.auction_price

        if broadcast_msg:
            # Should only be done if message is state-updating
            await self.channel_layer.group_send(
                self.room_id,
                {
                    "type": "send_message",
                    "message": res,
                    "username": parsed_data["username"],
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
