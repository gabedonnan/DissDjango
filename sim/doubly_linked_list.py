from enum import Enum

class OrderType(Enum):
    limit = "LIMIT"
    fill_and_kill = "FILL_AND_KILL"
    market = "MARKET"
    immediate_or_cancel = "IMMEDIATE_OR_CANCEL"
    post_only = "POST_ONLY"

class Order:
    is_bid: bool
    quantity: int
    price: int
    id: int
    order_type: OrderType
    trader_id: str
    prev: "Order | None"
    next: "Order | None"

    def __init__(self, is_bid, quantity, price, id_, order_type, trader_id):
        self.is_bid = is_bid
        self.quantity = quantity
        self.price = price
        self.id = id_
        self.order_type = order_type
        self.trader_id = trader_id
        self.prev = None
        self.next = None


class DoublyLinkedList:
    head: Order | None
    tail: Order | None
    length: int

    def __init__(self):
        self.head = None
        self.tail = None
        self.length = 0

    def append(self, order: Order):
        if self.tail is None:
            self.tail = order
            self.head = order
        else:
            order.prev = self.tail
            self.tail = order
            self.tail.prev.next = order

        self.length += 1

    def pop_left(self) -> Order | None:
        if self.head is None:
            return None

        res = self.head

        if self.head is self.tail:
            self.head = None
            self.tail = None
        else:
            self.head = self.head.next
            self.head.prev = None

        res.next = None
        self.length -= 1
        return res

    def remove(self, order: Order | None):
        if order is self.head:
            self.head = order.next
        else:
            order.prev.next = order.next

        if order is self.tail:
            self.tail = order.prev
        else:
            order.next.prev = order.prev

        self.length -= 1
