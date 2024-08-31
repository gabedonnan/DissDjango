from collections import deque
from random import randint
from time import time
from sortedcontainers import SortedDict

from .limit_order_book import LimitLevel, Order, OrderType


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
        if isinstance(money_range, int):
            self.money = money_range
        else:
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

    def __repr__(self):
        return f"AuctionUser({self.username})"

    def __str__(self):
        return f"AuctionUser({self.username})"


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

        if account == self.auctioneer and (
            self.auction_price is None or 0 < price < self.auction_price
        ):
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
    auction_price: int | None = 0
    auction_leader: AuctionUser | None = None
    # Unix timestamp of last bid to calculate whether the auction has finished
    timestamp: float
    time_difference: int
    # Record the number of users that bid to end early if all users have bid
    num_bids: int = 0
    # A set of the users that have bid already (no double bidding!)
    users_seen: set[str]
    auction_over: bool = False
    bid_history: list[str, int, int]  # Username, price bid, limit price

    def __init__(
        self,
        users: list[str],
        limit_price_distribution: tuple[callable, int, int],
        money_range: tuple[int, int] = (1000, 2000),
        timer: int = 90,  # Default timer is 90 seconds
    ):
        super().__init__(users, limit_price_distribution, money_range)
        self.users_seen = set()
        self.time_difference = int(timer)
        self.bid_history = []

    def bid(self, account: str, amount: int) -> bool:
        try:
            amount = int(amount)
        except ValueError:
            return False

        made_bid = False
        # Can a user pay for the asset
        if (
            account != self.auctioneer
            and account in self.users.keys()
            and account not in self.users_seen
        ):
            current_user = self.users[account]
            self.num_bids += (
                1  # Always increase the number of bids even if it isnt the highest
            )
            self.users_seen.add(account)
            made_bid = True
            self.bid_history.append([account, amount, current_user.limit_price])
            # Can a user pay for the asset
            if (
                self.timestamp is None
                or self.timestamp + int(self.time_difference) >= time()
            ) and current_user.money >= amount > self.auction_price:
                # Transfer money from buyer to auctioneer
                self.auction_price = amount
                self.auction_leader = current_user
                print(
                    f"FPSB UPDATED: LEADER = {self.auction_leader}, PRICE = {self.auction_price}"
                )

        self.auction_over = (
            (  # indicate the auction is over if all users have bid when this is called
                self.num_bids >= len(self.users) - 1
            )
            or self.timestamp + int(self.time_difference) < time()
        )

        if self.auction_over:
            self.auction_leader.profits += (
                self.auction_leader.limit_price - self.auction_price
            )
            auctioneer = self.users[self.auctioneer]
            auctioneer.profits -= auctioneer.limit_price - self.auction_price

        print("FPSB FINISHED", self.auction_over)

        return made_bid
        # Only broadcast if all users have bid or the time is up (i.e. auction over)


class SecondPriceSealedBidAuction(FirstPriceSealedBidAuction):
    auction_leader: deque = deque([None, None])
    auction_price: deque = deque([0, 0])


    def bid(self, account: str, amount: int) -> bool:
        try:
            amount = int(amount)
        except ValueError:
            return False

        made_bid = False
        # Can a user pay for the asset
        if (
            account != self.auctioneer
            and account in self.users.keys()
            and account not in self.users_seen
        ):
            current_user = self.users[account]
            self.num_bids += (
                1  # Always increase the number of bids even if it isnt the highest
            )
            self.users_seen.add(account)
            self.bid_history.append([account, amount, current_user.limit_price])
            made_bid = True
            # Can a user pay for the asset
            if (
                self.timestamp is None
                or self.timestamp + int(self.time_difference) >= time()
            ) and current_user.money >= amount:
                # The highest price is on the right
                if len(self.auction_price) != 0 and (
                    amount > self.auction_price[-1] or self.auction_price[-1] is None
                ):
                    # The new bid is the highest
                    self.auction_price.popleft()
                    self.auction_price.append(amount)
                    self.auction_leader.popleft()
                    self.auction_leader.append(current_user)
                elif len(self.auction_price) > 1 and (
                    amount > self.auction_price[0] or self.auction_price[0] is None
                ):
                    # The new bid is the second highest
                    self.auction_price.popleft()
                    self.auction_price.appendleft(amount)
                    self.auction_leader.popleft()
                    self.auction_leader.appendleft(current_user)

        self.auction_over = (
            (  # indicate the auction is over if all users have bid when this is called
                self.num_bids >= len(self.users) - 1
            )
            or self.timestamp + int(self.time_difference) < time()
        )

        if self.auction_over:
            self.auction_leader[-1].profits += (
                self.auction_leader[-1].limit_price - self.auction_price[0]
            )
            auctioneer = self.users[self.auctioneer]
            auctioneer.profits -= auctioneer.limit_price - self.auction_price[0]

        return made_bid
        # Only broadcast if all users have bid or the time is up (i.e. auction over)


class ContinuousDoubleAuction(Auction):
    bids: SortedDict[int, LimitLevel]
    asks: SortedDict[int, LimitLevel]
    orders: dict[int, Order]
    order_id: int
    bid_history: list[str, str, int, int]  # buyer, seller, quantity, price

    # Unix timestamp of last bid to calculate whether the auction has finished
    timestamp: float | None = None
    time_difference: int | None = None

    def __init__(
        self,
        users: list[str],
        limit_price_distribution: tuple[callable, int, int],
        money_range: tuple[int, int] = (1000, 2000),
        timer: int = 300,
    ):
        super().__init__(users, limit_price_distribution, money_range)
        self.bids = SortedDict()
        self.asks = SortedDict()
        self.orders = {}
        self.order_id = 0
        self.bid_history = []
        self.time_difference = int(timer)

    def get_side(self, is_bid: bool) -> SortedDict[int, LimitLevel]:
        return self.bids if is_bid else self.asks

    def add_order(self, order: Order | None):
        order_tree = self.get_side(order.is_bid)
        best_ask = self.get_best_ask()
        best_bid = self.get_best_bid()

        if order.is_bid and best_ask is not None and best_ask.price <= order.price:
            self.match_orders(order, best_ask)
            return
        elif (
            not order.is_bid and best_bid is not None and best_bid.price >= order.price
        ):
            self.match_orders(order, best_bid)
            return

        if order is not None:
            if order.quantity > 0 and order.order_type != OrderType.fill_and_kill:
                self.orders[order.id] = order

                if order.price in order_tree:
                    order_tree[order.price].append(order)
                else:
                    order_tree[order.price] = LimitLevel(order)

    def match_orders(self, order: Order | None, best_value: LimitLevel | None):
        if best_value is None:
            return

        while (
            best_value.quantity > 0
            and order.quantity > 0
            and best_value.get_length() > 0
        ):
            head_order: Order = best_value.get_head()

            if order.quantity <= head_order.quantity:
                self.bid_history.append(
                    [
                        order.trader_id if order.is_bid else head_order.trader_id,
                        head_order.trader_id if order.is_bid else order.trader_id,
                        order.quantity,
                        head_order.price,
                    ]
                )

                head_order.quantity -= order.quantity
                best_value.quantity -= order.quantity
                order.quantity = 0
            else:
                self.bid_history.append(
                    [
                        order.trader_id if order.is_bid else head_order.trader_id,
                        head_order.trader_id if order.is_bid else order.trader_id,
                        head_order.quantity,
                        head_order.price,
                    ]
                )
                order.quantity -= head_order.quantity
                best_value.quantity -= head_order.quantity
                head_order.quantity = 0

            if order.quantity == 0 and order.id in self.orders:
                self.cancel(order.id, order.trader_id)

            if head_order.quantity == 0:
                del self.orders[head_order.id]
                best_value.pop_left()

            if best_value.quantity == 0:
                order_tree = self.get_side(not order.is_bid)
                if best_value.price in order_tree:
                    del order_tree[best_value.price]

        if order is not None and order.quantity > 0:
            self.add_order(order)

    def get_best_ask(self) -> LimitLevel | None:
        if len(self.asks) != 0:
            return self.asks.peekitem(0)[1]
        else:
            return None

    def get_best_bid(self) -> LimitLevel | None:
        if len(self.bids) != 0:
            return self.bids.peekitem()[1]
        else:
            return None

    def cancel(self, id_: int, trader_id: str):
        if id_ in self.orders and self.orders[id_].trader_id == trader_id:
            current_order = self.orders[id_]
            order_tree = self.get_side(current_order.is_bid)

            if current_order.price in order_tree:
                price_level: LimitLevel = order_tree[current_order.price]
                price_level.remove(current_order)

                if price_level.quantity <= 0:
                    del order_tree[price_level.price]

            del self.orders[id_]

    def bid(
        self, quantity: int, price: int, order_type: OrderType, trader_id: str
    ) -> int:
        try:
            price = int(price)
            quantity = int(quantity)
        except ValueError:
            return -1

        if (
            trader_id != self.auctioneer
            and trader_id in self.users.keys()
            and price >= 0
            and quantity > 0
        ):
            order = Order(
                True, quantity, price, self.order_id, order_type, trader_id
            )
            self.order_id += 1
            self.add_order(order)
            return self.order_id - 1

        return -1

    def ask(
        self, quantity: int, price: int, order_type: OrderType, trader_id: str
    ) -> int:
        try:
            price = int(price)
            quantity = int(quantity)
        except ValueError:
            return -1

        if (
            trader_id != self.auctioneer
            and trader_id in self.users.keys()
            and price >= 0
            and quantity > 0
        ):
            order = Order(
                False, quantity, price, self.order_id, order_type, trader_id
            )
            self.order_id += 1
            self.add_order(order)
            return self.order_id - 1

        return -1

    def __repr__(self):
        return f"LimitOrderBook(bid count={len(self.bids)}, ask count={len(self.asks)})"

    def __str__(self):
        return self.__repr__()
