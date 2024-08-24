# Translated from my own C++ implementation at https://github.com/gabedonnan/CPPLob/blob/main/limit_order_book.hpp

from .doubly_linked_list import *


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
