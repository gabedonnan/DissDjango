from collections import deque
from random import randint, choice
from time import time


class AuctionUser:
    money: int
    username: str
    limit_price: int
    profits: int = 0

    def __init__(
        self,
        username: str,
        limit_price_distribution: tuple[callable, int, int],
        money_range: tuple[int, int],
    ):
        self.username = username
        dist, min_range, max_range = limit_price_distribution
        self.limit_price = int(dist(min_range, max_range))
        self.money = randint(*money_range)

    def __eq__(self, other):
        if isinstance(other, AuctionUser):
            return self.username == other.username
        elif isinstance(other, str):
            return self.username == other
        elif other is None:
            return False
        else:
            raise TypeError(
                f"Invalid Equality Comparison Between: AuctionUser and {type(other)}"
            )


class Auction:
    users: dict[str, AuctionUser]
    auctioneer: str | None = None
    timestamp: int
    limit_price_distribution: tuple[callable, int, int]

    def __init__(
        self,
        users: list[str],
        limit_price_distribution: tuple[callable, int, int],
        money_range: tuple[int, int] = (1000, 2000),
    ):
        self.users = {
            username: AuctionUser(username, limit_price_distribution, money_range)
            for username in users
        }
        self.money_range = money_range
        self.timestamp = int(time())
        self.limit_price_distribution = limit_price_distribution

    def bid(self, *args) -> bool: ...

    def add_user(self, username, limit_price_distribution):
        if username not in self.users:
            self.users[username] = AuctionUser(
                username, limit_price_distribution, self.money_range
            )

    def remove_user(self, username):
        if username in self.users:
            del self.users[username]

    def __str__(self):
        return f"{type(self)},, {self.users},, {self.auctioneer},, {self.limit_price_distribution}"


class DutchAuction(Auction):
    auction_price: int | None = None
    # Username maps to money amount and quantity of items owned
    users: dict[str, AuctionUser]

    def __init__(
        self,
        users: list[str],
        limit_price_distribution: tuple[callable, int, int],
        money_range: tuple[int, int] = (1000, 2000),
    ):
        super().__init__(users, limit_price_distribution, money_range)

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
                current_user.profits += current_user.limit_price - self.auction_price
                auctioneer.profits -= auctioneer.limit_price - self.auction_price

                self.auction_price = None
                return True
        return False

    def auctioneer_update_offer(self, account: str, price: int) -> bool:
        try:
            price = int(price)
        except ValueError:
            return False

        if account == self.auctioneer and (self.auction_price is None or 0 < price < self.auction_price):
            self.auction_price = price
            return True
        return False


class EnglishAuction(Auction):
    auction_price: int | None = None
    auction_leader: AuctionUser | None = None
    # Username maps to money amount and quantity of items owned
    users: dict[str, AuctionUser]
    # Unix timestamp of last bid to calculate whether the auction has finished
    timestamp: float | None = None
    time_difference: int | None = None
    # List in order of bids, with sub tuples containing bidding username, bid amount and the bidding user's limit price
    bid_history: list[tuple[str, int, int]]

    def __init__(
        self,
        users: list[str],
        limit_price_distribution: tuple[callable, int, int],
        money_range: tuple[int, int] = (1000, 2000),
        timer: int = 30,  # Default timer is 10 seconds
    ):
        super().__init__(users, limit_price_distribution, money_range)
        self.bid_history = []
        self.time_difference = int(timer)

    def bid(self, account: str, amount: int) -> bool:
        try:
            amount = int(amount)
        except ValueError:
            return False

        if (
            account != self.auctioneer
            and account in self.users.keys()
            and self.users[account] != self.auction_leader
        ):
            current_user = self.users[account]
            # Can a user pay for the asset
            if (
                self.timestamp is None
                or self.timestamp + int(self.time_difference) >= time()
            ) and current_user.money >= amount:
                if self.auction_price is None or amount > self.auction_price:
                    self.bid_history.append((account, amount, current_user.limit_price))
                    # Transfer money from buyer to auctioneer
                    self.auction_price = amount
                    self.auction_leader = self.users[account]
                    self.timestamp = time()
                    # Broadcast this change to all participants of the room
                    return True

        return False

    def check_finished(self) -> bool:
        # Returns a boolean indicating whether the auction is finished, in this case only time can end it.
        return (
            self.timestamp is not None
            and self.timestamp + int(self.time_difference) < time()
        )


class FirstPriceSealedBidAuction(Auction):
    auction_price: int | None = None
    auction_leader: AuctionUser | None = None
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
        limit_price_distribution: tuple[callable, int, int],
        money_range: tuple[int, int] = (1000, 2000),
        timer: int = 90,  # Default timer is 90 seconds
    ):
        super().__init__(users, limit_price_distribution, money_range)
        self.time_difference = int(timer)

    def bid(self, account: str, amount: int) -> bool:
        # Can a user pay for the asset
        if account != self.auctioneer and account in self.users.keys():
            current_user = self.users[account]
            self.num_bids += (
                1  # Always increase the number of bids even if it isnt the highest
            )
            # Can a user pay for the asset
            if (
                self.timestamp is None
                or self.timestamp + int(self.time_difference) >= time()
            ) and current_user.money >= amount > self.auction_price:
                # Transfer money from buyer to auctioneer
                self.auction_price = amount
                self.auction_leader = current_user

        return (
            self.num_bids >= len(self.users)
            or self.timestamp + self.time_difference < time()
        )
        # Only broadcast if all users have bid or the time is up (i.e. auction over)


class SecondPriceSealedBidAuction(FirstPriceSealedBidAuction):
    auction_leader: deque = deque([None])
    auction_price: deque = deque([0])

    def bid(self, account: str, amount: int) -> bool:
        # Can a user pay for the asset
        if account != self.auctioneer and account in self.users.keys():
            current_user = self.users[account]
            self.num_bids += (
                1  # Always increase the number of bids even if it isnt the highest
            )
            # Can a user pay for the asset
            if (
                self.timestamp is None
                or self.timestamp + int(self.time_difference) >= time()
            ) and current_user.money >= amount:
                # The highest price is on the right
                if len(self.auction_price) != 0 and amount > self.auction_price[-1]:
                    # The new bid is the highest
                    self.auction_price.popleft()
                    self.auction_price.append(amount)
                    self.auction_leader.popleft()
                    self.auction_leader.append(account)
                elif len(self.auction_price) > 1 and amount > self.auction_price[0]:
                    # The new bid is the second highest
                    self.auction_price.popleft()
                    self.auction_price.appendleft(amount)
                    self.auction_leader.popleft()
                    self.auction_leader.appendleft(account)

        return (
                self.num_bids >= len(self.users)
                or self.timestamp + self.time_difference < time()
        )
        # Only broadcast if all users have bid or the time is up (i.e. auction over)

class ContinuousDoubleAuction(Auction): ...
