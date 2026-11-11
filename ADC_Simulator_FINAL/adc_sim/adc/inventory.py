"""Inventory Manager module.

Secret: how medication and quantity per location are represented and saved.
Anticipated change: locations hold more than one medication, or counts are
tracked by lot/expiry.

Interface
  locations() -> list[str]
  medication_at(loc) -> dict {medication_id, name}
  location_of(medication_id) -> str          raises Rejected if not stocked
  quantity(loc) -> int
  add(loc, qty)        qty > 0, else Rejected                       (FR-INV-02)
  remove(loc, qty)     Rejected if the result would be negative     (FR-INV-04)
  snapshot() -> dict   {loc: {medication_id, name, quantity}}       (FR-INV-01)
Every change is saved immediately (NFR-REL-01, NFR-REL-03).
"""
from .errors import Rejected


class Inventory:
    def __init__(self, store, seed: dict):
        self._store = store
        self._inv = store.load("inventory", None) or {k: dict(v) for k, v in seed.items()}
        self._check_invariant()
        self._store.save("inventory", self._inv)

    def locations(self):
        return list(self._inv)

    def medication_at(self, loc):
        e = self._inv[loc]
        return {"medication_id": e["medication_id"], "name": e["name"]}

    def location_of(self, medication_id):
        for loc, e in self._inv.items():
            if e["medication_id"] == medication_id:
                return loc
        raise Rejected("Medication is not stocked in this cabinet")

    def quantity(self, loc):
        return self._inv[loc]["quantity"]

    def add(self, loc, qty):
        if loc not in self._inv:
            raise Rejected("Unknown storage location")
        if qty <= 0:
            raise Rejected("Quantity must be greater than 0")
        self._inv[loc]["quantity"] += qty
        self._check_invariant()
        self._store.save("inventory", self._inv)

    def remove(self, loc, qty):
        if qty <= 0:
            raise Rejected("Quantity must be greater than 0")
        if self._inv[loc]["quantity"] - qty < 0:
            raise Rejected("Not enough stock in the drawer")
        self._inv[loc]["quantity"] -= qty
        self._check_invariant()
        self._store.save("inventory", self._inv)

    def _check_invariant(self):
        # INV-7: no location ever holds a negative quantity
        assert all(e["quantity"] >= 0 for e in self._inv.values()), "INV-7 violated"

    def snapshot(self):
        return {k: dict(v) for k, v in self._inv.items()}
