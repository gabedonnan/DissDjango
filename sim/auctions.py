from collections import deque
from random import randint, choice
from time import time


class AuctionUser:
    objective_text: str
    objective: tuple[str, int]
    assets: dict[str, int]
    money: int
    username: str

    def __init__(
        self,
        username: str,
        assets: set[str],
        asset_range: tuple[int, int],
        money_range: tuple[int, int],
    ):
        self.username = username
        self.assets = {asset: randint(*asset_range) for asset in assets}
        self.money = randint(*money_range)
        if len(assets) > 0:
            self.generate_objective()

    def generate_objective(self) -> None:
        chosen_asset = choice(list(self.assets.keys()))
        self.objective = (chosen_asset, self.assets[chosen_asset] + randint(1, 10))
        self.objective_text = f"Own at least {self.objective[1]} {self.objective[0]}"


class Auction:
    users: dict[str, AuctionUser]
    auctioneer: str | None = None

    def __init__(
        self,
        users: list[str],
        assets: set[str],
        asset_range: tuple[int, int] = (5, 15),
        money_range: tuple[int, int] = (1000, 2000),
    ):
        self.users = {
            username: AuctionUser(username, assets, asset_range, money_range)
            for username in users
        }
        self.possible_assets = assets
        self.asset_range = asset_range
        self.money_range = money_range

    def bid(self, *args) -> bool: ...

    def add_user(self, username):
        if username not in self.users:
            self.users[username] = AuctionUser(
                username, self.possible_assets, self.asset_range, self.money_range
            )

    def remove_user(self, username):
        if username in self.users:
            del self.users[username]


class DutchAuction(Auction):
    auction_price: int | None = None
    auction_asset: str | None = None
    auction_quantity: int | None = None
    # Username maps to money amount and quantity of items owned
    users: dict[str, AuctionUser]

    def __init__(
        self,
        users: list[str],
        assets: set[str],
        asset_range: tuple[int, int] = (5, 15),
        money_range: tuple[int, int] = (1000, 2000),
    ):
        super().__init__(users, assets, asset_range, money_range)

    def bid(self, account: str) -> bool:
        if account != self.auctioneer and account in self.users.keys():
            current_user = self.users[account]
            auctioneer = self.users[self.auctioneer]
            # Can a user pay for the asset
            if current_user.money >= self.auction_price:
                # Transfer money from buyer to auctioneer
                current_user.money -= self.auction_price
                auctioneer.money += self.auction_price
                # Transfer assets to buyer
                current_user.assets[self.auction_asset] += self.auction_quantity
                auctioneer.assets[self.auction_asset] -= self.auction_quantity

                # Switch to a new auctioneer
                self.auctioneer = choice(list(self.users.keys()))
                self.auction_quantity = None
                self.auction_price = None
                self.auction_asset = None

                return True
        return False

    def auctioneer_initial_offer(
        self, account: str, asset: str, price: int, quantity: int
    ) -> bool:
        # Checking only that auction asset is none should be sufficient
        if (
            account == self.auctioneer
            and asset in self.possible_assets
            and self.auction_asset is None
        ):
            # We need to ensure the user actually has the correct amount of the asset to sell
            if self.users[account].assets[asset] >= quantity:
                self.auction_asset = asset
                self.auction_price = price
                self.auction_quantity = quantity
                return True
        return False

    def auctioneer_update_offer(self, account: str, price: int) -> bool:
        if account == self.auctioneer and 0 < price < self.auction_price:
            self.auction_price = price
            return True
        return False


class EnglishAuction(Auction):
    auction_price: int | None = None
    auction_leader: AuctionUser | None = None
    auction_asset: str | None = None
    auction_quantity: int | None = None
    # Username maps to money amount and quantity of items owned
    users: dict[str, AuctionUser]
    # Unix timestamp of last bid to calculate whether the auction has finished
    timestamp: float | None = None
    time_difference: int | None = None

    def __init__(
        self,
        users: list[str],
        assets: set[str],
        asset_range: tuple[int, int] = (5, 15),
        money_range: tuple[int, int] = (1000, 2000),
        timer: int = 100000000000000,  # Default timer is 10 seconds
    ):
        super().__init__(users, assets, asset_range, money_range)
        self.time_difference = timer

    def bid(self, account: str, amount: int) -> bool:
        try:
            amount = int(amount)
        except ValueError:
            return False

        if account != self.auctioneer and account in self.users.keys():
            current_user = self.users[account]
            print(current_user.money)
            # Can a user pay for the asset
            if (
                self.timestamp is None
                or self.timestamp + self.time_difference >= time()
            ) and current_user.money >= amount:
                if self.auction_price is None or amount >= self.auction_price:
                    # Transfer money from buyer to auctioneer
                    self.auction_price = amount
                    self.auction_leader = self.users[account]
                    self.timestamp = time()
                    # Broadcast this change to all participants of the room
                    return True

        return False

    def auctioneer_initial_offer(
        self, account: str, asset: str, price: int, quantity: int
    ) -> bool:
        # Checking only that auction asset is none should be sufficient
        if (
            account == self.auctioneer
            and asset in self.possible_assets
            and self.auction_asset is None
        ):
            # We need to ensure the user actually has the correct amount of the asset to sell
            if self.users[account].assets[asset] >= quantity:
                self.auction_asset = asset
                self.auction_price = price
                self.auction_quantity = quantity
                self.timestamp = time()
                return True
        return False

    # The event loop may call this every few seconds to check whether the auction is finished.
    def check_finished(self):
        if (
            self.timestamp + self.time_difference > time()
            and self.auctioneer is not None
            and self.auction_leader is not None
        ):
            auctioneer = self.users[self.auctioneer]
            # Transfer money from buyer to auctioneer
            self.auction_leader.money -= self.auction_price
            auctioneer.money += self.auction_price
            # Transfer assets to buyer
            self.auction_leader.assets[self.auction_asset] += self.auction_quantity
            auctioneer.assets[self.auction_asset] -= self.auction_quantity

            # Switch to a new auctioneer
            self.auctioneer = choice(list(self.users.keys()))
            self.auction_quantity = None
            self.auction_price = None
            self.auction_asset = None
            self.auction_leader = None

            # Broadcast this change to all participants of the room
            pass


class FirstPriceSealedBidAuction(Auction):
    auction_price: int | None = None
    auction_leader: AuctionUser | None = None
    auction_asset: str | None = None
    auction_quantity: int | None = None
    # Username maps to money amount and quantity of items owned
    users: dict[str, AuctionUser]
    # Unix timestamp of last bid to calculate whether the auction has finished
    timestamp: float
    time_difference: int
    # Record the number of users that bid to end early if all users have bid
    num_bids: int = 0

    def __init__(
        self,
        users: list[str],
        assets: set[str],
        asset_range: tuple[int, int] = (5, 15),
        money_range: tuple[int, int] = (1000, 2000),
        timer: int = 90,  # Default timer is 90 seconds
    ):
        super().__init__(users, assets, asset_range, money_range)
        self.time_difference = timer

    def bid(self, account: str, amount: int) -> bool:
        if account != self.auctioneer and account in self.users.keys():
            current_user = self.users[account]
            # Can a user pay for the asset
            if (
                current_user.money >= amount >= self.auction_price
                and self.timestamp + self.time_difference <= time()
            ):
                # Transfer money from buyer to auctioneer
                self.auction_price = amount
                self.auction_leader = self.users[account]
                self.num_bids += 1
                # Broadcast this change to all participants of the room
                return True

        if (
            self.num_bids >= len(self.users)
            or self.timestamp + self.time_difference <= time()
        ):
            ...

        return False

    def auctioneer_initial_offer(
        self, account: str, asset: str, price: int, quantity: int
    ) -> bool:
        # Checking only that auction asset is none should be sufficient
        if (
            account == self.auctioneer
            and asset in self.possible_assets
            and self.auction_asset is None
        ):
            # We need to ensure the user actually has the correct amount of the asset to sell
            if self.users[account].assets[asset] >= quantity:
                self.auction_asset = asset
                self.auction_price = price
                self.auction_quantity = quantity
                self.timestamp = time()
                self.num_bids = 0
                return True
        return False

    # The event loop may call this every few seconds to check whether the auction is finished.
    def check_finished(self):
        if (
            (
                self.timestamp + self.time_difference > time()
                or self.num_bids >= len(self.users)
            )
            and self.auctioneer is not None
            and self.auction_leader is not None
        ):
            auctioneer = self.users[self.auctioneer]
            # Transfer money from buyer to auctioneer
            self.auction_leader.money -= self.auction_price
            auctioneer.money += self.auction_price
            # Transfer assets to buyer
            self.auction_leader.assets[self.auction_asset] += self.auction_quantity
            auctioneer.assets[self.auction_asset] -= self.auction_quantity

            # Switch to a new auctioneer
            self.auctioneer = choice(list(self.users.keys()))
            self.auction_quantity = None
            self.auction_price = None
            self.auction_asset = None
            self.auction_leader = None
            self.num_bids = 0

            # Broadcast this change to all participants of the room
            pass


class SecondPriceSealedBidAuction(FirstPriceSealedBidAuction):
    auction_leader: deque = deque([None])
    auction_price: deque = deque([0])

    def bid(self, account: str, amount: int) -> bool:
        if account != self.auctioneer and account in self.users.keys():
            current_user = self.users[account]
            # Can a user pay for the asset
            if (
                current_user.money >= amount >= self.auction_price[0]
                and self.timestamp + self.time_difference <= time()
            ):
                # Transfer money from buyer to auctioneer
                self.auction_price.appendleft(amount)
                self.auction_leader.appendleft(self.users[account])

                if len(self.auction_leader) >= 2:
                    self.auction_leader.pop()
                    self.auction_price.pop()

                self.num_bids += 1
                # Broadcast this change to all participants of the room
                return True

        if (
            self.num_bids >= len(self.users)
            or self.timestamp + self.time_difference <= time()
        ):
            ...

        return False


class ContinuousDoubleAuction(Auction): ...
