"""Order Book module.

Secret: how authorized orders are represented, matched and kept locally.
Anticipated change: the order format from the hospital changes (e.g. adds a
dose time window). Orders are held locally so dispensing works offline (FR-COM-05).

Interface
  add(order_id, medication_id, quantity)    store an authorized order (FR-COM-06);
                                             Rejected if duplicate or quantity <= 0
  check(order_id, qty) -> dict              the order if it can cover qty, else
                                             Rejected (FR-DSP-02, FR-DSP-05)
  consume(order_id, qty)                    reduce the remaining quantity
  active() -> list[dict]                    orders with quantity remaining
"""
from .errors import Rejected


class OrderBook:
    def __init__(self, store):
        self._store = store
        self._orders = store.load("orders", {})

    def add(self, order_id, medication_id, quantity):
        if order_id in self._orders:
            raise Rejected(f"Order {order_id} already exists")
        if quantity <= 0:
            raise Rejected("Order quantity must be greater than 0")
        self._orders[order_id] = {"order_id": order_id, "medication_id": medication_id,
                                  "quantity": quantity, "remaining": quantity}
        self._store.save("orders", self._orders)

    def check(self, order_id, qty):
        o = self._orders.get(order_id)
        if o is None or o["remaining"] <= 0:
            raise Rejected("Unauthorized medication request: no matching order")
        if qty <= 0:
            raise Rejected("Quantity must be greater than 0")
        if qty > o["remaining"]:
            raise Rejected(f"Quantity exceeds authorized order ({o['remaining']} remaining)")
        return dict(o)

    def consume(self, order_id, qty):
        self._orders[order_id]["remaining"] -= qty
        self._store.save("orders", self._orders)

    def active(self):
        return [dict(o) for o in self._orders.values() if o["remaining"] > 0]
