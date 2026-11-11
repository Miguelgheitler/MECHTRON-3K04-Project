"""Dispensing Controller module (D1 Figure 9, dispensing lifecycle).

Secret: the sequence of hardware steps in one drawer transaction (unlock,
wait for open, wait for close, relock) and when a transaction counts as done.
Anticipated change: a different drawer workflow (e.g. a two-step confirm on the
screen, or a drawer that must be scanned).

The state machine is the TRANSITIONS table below: one cell per state x event.
States: IDLE -> DRAWER_UNLOCKED -> IDLE, or DRAWER_UNLOCKED -> DRAWER_FAULT.
In DRAWER_FAULT the faulted transaction is closed, so healthy drawers can
still be used (NFR-AVL-03); the faulted drawer stays blocked by the Fault Monitor.
(The Authenticated state of Figure 9 is held by the session in ADCSystem.)

Interface
  request_dispense(user_id, order_id, qty) -> loc
      Pre:  no drawer transaction open, mode allows dispensing
      Post: order ok, location healthy, stock ok  => only that location unlocked,
                                                   state = DRAWER_UNLOCKED
            otherwise                            => nothing unlocked, attempt logged
                                                   'Rejected', raises Rejected(reason)
      (FR-DSP-01..03, FR-DSP-05, FR-MOD-03, FR-INV-04, NFR-SAF-01, NFR-SAF-04)
  request_replenish(user_id, loc, qty) -> loc        same lifecycle for restocking
  poll() -> dict | None
      Watches the open drawer. When it has been opened and is closed again:
      relock (FR-DSP-04), update inventory/order (FR-INV-02/03), log 'Completed'
      (NFR-SAF-05, NFR-AUD-01/02). Returns a summary of the finished transaction.
  on_fault(fault)       abort a transaction at the faulted location, log 'Faulted'
  fault_cleared()       DRAWER_FAULT -> IDLE
  in_progress() -> bool
  current() -> dict | None
Invariant (INV-1), checked after every public operation by _check_invariant():
  state = DRAWER_UNLOCKED  <=>  a transaction is open, and only that location is
  commanded unlocked. A violation locks every drawer (fail-safe) and is logged.
"""
from dataclasses import dataclass, asdict
from enum import Enum

from .errors import Rejected


class State(str, Enum):
    IDLE = "IDLE"
    DRAWER_UNLOCKED = "DRAWER_UNLOCKED"
    DRAWER_FAULT = "DRAWER_FAULT"


class Event(str, Enum):
    UNLOCK = "unlock"                # a request passed every check
    COMPLETE = "drawerClosed"        # drawer opened and closed again
    CANCEL = "neverOpened"           # drawer not opened within 30 s
    FAULT = "faultAtDrawer"          # fault at the open drawer
    FAULT_CLEARED = "faultCleared"


IGNORE = "IGNORE"
IDLE, DRAWER_UNLOCKED, DRAWER_FAULT = State.IDLE.value, State.DRAWER_UNLOCKED.value, State.DRAWER_FAULT.value

_I, _U, _F = State.IDLE, State.DRAWER_UNLOCKED, State.DRAWER_FAULT
TRANSITIONS = {
    (_I, Event.UNLOCK): _U,
    (_I, Event.COMPLETE): IGNORE,
    (_I, Event.CANCEL): IGNORE,
    (_I, Event.FAULT): IGNORE,
    (_I, Event.FAULT_CLEARED): IGNORE,
    (_U, Event.UNLOCK): Rejected("Another drawer transaction is in progress"),
    (_U, Event.COMPLETE): _I,
    (_U, Event.CANCEL): _I,
    (_U, Event.FAULT): _F,
    (_U, Event.FAULT_CLEARED): IGNORE,
    (_F, Event.UNLOCK): _U,          # healthy drawers stay usable (NFR-AVL-03)
    (_F, Event.COMPLETE): IGNORE,
    (_F, Event.CANCEL): IGNORE,
    (_F, Event.FAULT): IGNORE,
    (_F, Event.FAULT_CLEARED): _I,
}


@dataclass
class Transaction:
    kind: str            # 'dispense' | 'replenish'
    user_id: str
    location: str
    quantity: int
    order_id: str | None
    medication_id: str
    unlocked_at: float
    opened: bool = False


class DispensingController:
    def __init__(self, hw, inventory, orders, faults, log, clock, drawer_timeout):
        self._hw, self._inv, self._orders = hw, inventory, orders
        self._faults, self._log, self._clock = faults, log, clock
        self._timeout = drawer_timeout
        self._state = State.IDLE
        self._txn: Transaction | None = None

    @property
    def state(self) -> str:
        return self._state.value

    def _cell(self, event):
        return TRANSITIONS[(self._state, event)]

    def _go(self, event):
        cell = self._cell(event)
        if isinstance(cell, Rejected):
            raise Rejected(cell.reason)
        if cell != IGNORE:
            self._state = cell

    def _check_invariant(self):
        unlocked_ok = (self._state == State.DRAWER_UNLOCKED) == (self._txn is not None)
        if not unlocked_ok:
            for loc in self._hw.locations():
                self._hw.command_lock(loc, True)
            self._log.record("INVARIANT_VIOLATION", invariant="INV-1", state=self.state)
            self._txn, self._state = None, State.DRAWER_FAULT

    def in_progress(self) -> bool:
        return self._state == State.DRAWER_UNLOCKED

    def current(self):
        return asdict(self._txn) if self._txn else None

    def _unlock(self, kind, user_id, loc, qty, order_id, med):
        self._hw.command_lock(loc, False)
        self._faults.expect_lock(loc, False)
        self._txn = Transaction(kind, user_id, loc, qty, order_id, med, self._clock.now())
        self._go(Event.UNLOCK)
        self._check_invariant()
        return loc

    def request_dispense(self, user_id, order_id, qty):
        med, loc = None, None
        try:
            cell = self._cell(Event.UNLOCK)
            if isinstance(cell, Rejected):
                raise Rejected(cell.reason)
            order = self._orders.check(order_id, qty)
            med = order["medication_id"]
            loc = self._inv.location_of(med)
            if self._faults.is_faulted(loc):
                raise Rejected(f"Drawer {loc} is unavailable: fault")
            if self._inv.quantity(loc) < qty:
                raise Rejected("Not enough stock in the drawer")
        except Rejected as r:
            self._log.record("DISPENSE", result="Rejected", reason=r.reason, user_id=user_id,
                             order_id=order_id, medication_id=med, location=loc, quantity=qty)
            raise
        return self._unlock("dispense", user_id, loc, qty, order_id, med)

    def request_replenish(self, user_id, loc, qty):
        try:
            cell = self._cell(Event.UNLOCK)
            if isinstance(cell, Rejected):
                raise Rejected(cell.reason)
            if loc not in self._inv.locations():
                raise Rejected("Unknown storage location")
            if qty <= 0:
                raise Rejected("Quantity must be greater than 0")
            if self._faults.is_faulted(loc):
                raise Rejected(f"Drawer {loc} is unavailable: fault")
        except Rejected as r:
            self._log.record("REPLENISH", result="Rejected", reason=r.reason, user_id=user_id,
                             location=loc, quantity=qty)
            raise
        return self._unlock("replenish", user_id, loc, qty, None, self._inv.medication_at(loc)["medication_id"])

    def _relock(self):
        loc = self._txn.location
        self._hw.command_lock(loc, True)
        self._faults.expect_lock(loc, True)

    def poll(self):
        if self._state != State.DRAWER_UNLOCKED:
            return None
        t = self._txn
        drawer = self._hw.read_drawer(t.location)
        if drawer == "open":
            t.opened = True
            return None
        if drawer == "closed" and t.opened:
            self._relock()
            if t.kind == "dispense":
                self._inv.remove(t.location, t.quantity)
                self._orders.consume(t.order_id, t.quantity)
                rec = self._log.record("DISPENSE", result="Completed", user_id=t.user_id, order_id=t.order_id,
                                       medication_id=t.medication_id, location=t.location, quantity=t.quantity)
            else:
                self._inv.add(t.location, t.quantity)
                rec = self._log.record("REPLENISH", result="Completed", user_id=t.user_id,
                                       medication_id=t.medication_id, location=t.location,
                                       quantity_change=+t.quantity)
            return self._finish(rec, Event.COMPLETE)
        if drawer == "closed" and self._clock.now() - t.unlocked_at > self._timeout:
            self._relock()
            rec = self._log.record(t.kind.upper(), result="Cancelled", reason="drawer never opened",
                                   user_id=t.user_id, order_id=t.order_id, location=t.location, quantity=t.quantity)
            return self._finish(rec, Event.CANCEL)
        return None

    def _finish(self, rec, event):
        self._txn = None
        self._go(event)
        self._check_invariant()
        return rec

    def on_fault(self, fault):
        if self._txn and fault.location in (self._txn.location, None):
            t = self._txn
            self._relock()
            self._log.record(t.kind.upper(), result="Faulted", reason=fault.fault_type, user_id=t.user_id,
                             order_id=t.order_id, medication_id=t.medication_id, location=t.location,
                             quantity=t.quantity)
            self._txn = None
            self._go(Event.FAULT)
            self._check_invariant()

    def fault_cleared(self):
        self._go(Event.FAULT_CLEARED)
