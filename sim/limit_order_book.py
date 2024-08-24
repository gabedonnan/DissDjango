# Translated from my own C++ implementation at https://github.com/gabedonnan/CPPLob/blob/main/limit_order_book.hpp

from .doubly_linked_list import *
from sortedcontainers import SortedDict


class LimitLevel:
    price: int
    orders: DoublyLinkedList
    quantity: int

    def __init__(self, order: Order):
        self.orders = DoublyLinkedList()
        self.orders.append(order)
        self.price = order.price
        self.quantity = order.quantity

    def append(self, order: Order):
        self.quantity += order.quantity
        self.orders.append(order)

    def pop_left(self) -> Order | None:
        self.quantity -= self.get_head().quantity
        return self.orders.pop_left()

    def remove(self, order: Order):
        self.quantity -= order.quantity
        self.orders.remove(order)

    def get_head(self) -> Order | None:
        return self.orders.head

    def get_tail(self) -> Order | None:
        return self.orders.tail

    def get_length(self) -> int:
        return self.orders.length


class LimitOrderBook:
    bids: SortedDict[int, LimitLevel]
    asks: SortedDict[int, LimitLevel]
    orders: dict[int, Order]
    order_id: int
    executed_transactions: list[str, str, int, int]  # buyer, seller, quantity, price

    # Unix timestamp of last bid to calculate whether the auction has finished
    timestamp: float | None = None
    time_difference: int | None = None

    def __init__(self, timer: int):
        self.bids = SortedDict()
        self.asks = SortedDict()
        self.orders = {}
        self.order_id = 0
        self.executed_transactions = []
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
                self.executed_transactions.append(
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
                self.executed_transactions.append(
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
        if price >= 0 and quantity > 0:
            order = Order(True, int(quantity), int(price), self.order_id, order_type, trader_id)
            self.order_id += 1
            self.add_order(order)
            return self.order_id - 1
        else:
            return -1

    def ask(
        self, quantity: int, price: int, order_type: OrderType, trader_id: str
    ) -> int:
        if price >= 0 and quantity > 0:
            order = Order(False, int(quantity), int(price), self.order_id, order_type, trader_id)
            self.order_id += 1
            self.add_order(order)
            return self.order_id - 1
        else:
            return -1

    def __repr__(self):
        return f"LimitOrderBook(bid count={len(self.bids)}, ask count={len(self.asks)})"

    def __str__(self):
        return self.__repr__()
