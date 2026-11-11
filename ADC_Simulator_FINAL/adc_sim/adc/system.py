"""ADC System module (the coordinator).

Secret: how the modules are wired together and the order of one control cycle.
It holds no policy of its own; every rule lives in the module that hides it.
The user interface uses ONLY this module.

USES hierarchy (no cycles):
  ADCSystem -> AccessControl, ModeManager, DispensingController, FaultMonitor,
               CommsLink, OrderBook, Inventory, EventLog, Clock
  DispensingController -> CabinetHardware, Inventory, OrderBook, FaultMonitor, EventLog, Clock
  FaultMonitor -> CabinetHardware, Clock
  CommsLink -> Channel, MessageCodec, JsonStore, Clock
  AccessControl, ModeManager, EventLog, Inventory, OrderBook -> EventLog / JsonStore / Clock

Interface (every call returns {"ok": bool, "message": str})
  login(badge, pin), logout()
  dispense(order_id, qty)                 Nurse
  replenish(location, qty)                Pharmacy Technician
  enter_maintenance(), exit_maintenance(), clear_fault(fault_id), shutdown()   Technician
  tick()            one control cycle; called every 0.1 s
  simulate_hang(s)  demo/test only: stop kicking the watchdog for s seconds
  snapshot()        everything the screen may show (orders only after login, NFR-SEC-02)
"""
from . import config as cfg
from .access_control import AccessControl
from .codec import MessageCodec
from .comms import CommsLink
from .dispensing import DispensingController
from .errors import Rejected
from .event_log import EventLog
from .fault_monitor import FaultMonitor
from .inventory import Inventory
from .mode_manager import ModeManager, FAULT, MAINTENANCE
from .orders import OrderBook
from .storage import JsonStore


class ADCSystem:
    def __init__(self, data_dir, hardware, channel, clock):
        self.clock = clock
        self._hw = hardware
        store = JsonStore(data_dir)
        self.log = EventLog(store, clock)
        self.inventory = Inventory(store, cfg.LOCATIONS)
        self.orders = OrderBook(store)
        self.access = AccessControl(cfg.USERS, cfg.PERMISSIONS, clock, self.log,
                                    cfg.MAX_FAILED_LOGINS, cfg.LOCKOUT_S, cfg.SESSION_TIMEOUT_S)
        self.modes = ModeManager(self.log)
        self.faults = FaultMonitor(hardware, clock, cfg.LOCK_TIMEOUT_S, cfg.DRAWER_CLOSE_TIMEOUT_S,
                                   cfg.SENSOR_TIMEOUT_S, cfg.WATCHDOG_TIMEOUT_S)
        self.dispensing = DispensingController(hardware, self.inventory, self.orders, self.faults,
                                               self.log, clock, cfg.DRAWER_CLOSE_TIMEOUT_S)
        self.comms = CommsLink(channel, MessageCodec(cfg.SHARED_KEY, "ADC-1"), clock, store,
                               cfg.LINK_TIMEOUT_S, cfg.OUTBOX_CAPACITY)
        self.session = None
        self.message = "Welcome. Please scan your badge and enter your PIN."
        self.alarm = False
        self.halted = False
        self._hang_until = 0.0
        self._forwarded = self.log.count()
        self._last_status = -1e9
        self._link_up = True
        for loc in hardware.locations():                       # NFR-SAF-02
            hardware.command_lock(loc, True)
            self.faults.expect_lock(loc, True)
        self.log.record("STARTUP", note="all locations commanded locked")

    # ---------- helpers ----------
    def _reply(self, ok, msg):
        self.message = msg
        return {"ok": ok, "message": msg}

    def _guard(self, action):
        if self.halted:
            raise Rejected("Cabinet is shut down")
        if self.session is None:
            raise Rejected("Please log in first")
        self.access.authorize(self.session, action)
        self.access.touch(self.session)

    # ---------- user operations ----------
    def login(self, badge, pin):
        if self.halted:
            return self._reply(False, "Cabinet is shut down")
        try:
            self.session = self.access.authenticate(badge.strip(), pin.strip())
        except Rejected as r:
            return self._reply(False, r.reason)
        return self._reply(True, f"Logged in as {self.session.name} ({self.session.user_id})")

    def logout(self):
        if self.session:
            self.log.record("LOGOUT", user_id=self.session.user_id)
        self.session = None
        return self._reply(True, "Logged out")

    def dispense(self, order_id, qty):
        try:
            self._guard("dispense")
            if not self.modes.dispensing_allowed():
                self.log.record("DISPENSE", result="Rejected", reason="maintenance mode",
                                user_id=self.session.user_id, order_id=order_id, quantity=qty)
                raise Rejected("Dispensing is not available in maintenance mode")
            loc = self.dispensing.request_dispense(self.session.user_id, order_id, int(qty))
        except Rejected as r:
            return self._reply(False, r.reason)
        except ValueError:
            return self._reply(False, "Quantity must be a whole number")
        return self._reply(True, f"Authorized medication request. Drawer {loc} unlocked: take the medication and close the drawer")

    def replenish(self, loc, qty):
        try:
            self._guard("replenish")
            if not self.modes.dispensing_allowed():
                raise Rejected("Replenishment is not available in maintenance mode")
            loc = self.dispensing.request_replenish(self.session.user_id, loc, int(qty))
        except Rejected as r:
            return self._reply(False, r.reason)
        except ValueError:
            return self._reply(False, "Quantity must be a whole number")
        return self._reply(True, f"Drawer {loc} unlocked: add the stock and close the drawer")

    def enter_maintenance(self):
        try:
            self._guard("maintenance")
            self.modes.enter_maintenance(self.dispensing.in_progress())
        except Rejected as r:
            return self._reply(False, r.reason)
        return self._reply(True, "Cabinet in maintenance mode. Dispensing is blocked")

    def exit_maintenance(self):
        try:
            self._guard("maintenance")
            self.modes.exit_maintenance()
        except Rejected as r:
            return self._reply(False, r.reason)
        return self._reply(True, "Maintenance finished. Cabinet back in normal mode")

    def clear_fault(self, fault_id):
        try:
            self._guard("clear_fault")
            f = self.faults.clear(int(fault_id), self.session.user_id)
        except Rejected as r:
            self.log.record("FAULT_CLEAR_REJECTED", fault_id=fault_id, user_id=self.session.user_id if self.session else None, reason=r.reason)
            return self._reply(False, r.reason)
        self.log.record("FAULT_CLEARED", fault_id=f.fault_id, fault_type=f.fault_type, location=f.location,
                        time_raised=self.clock.fmt(f.raised_at), time_cleared=self.clock.fmt(f.cleared_at),
                        cleared_by=f.cleared_by)
        self.dispensing.fault_cleared()
        if not self.faults.active():
            self.modes.all_faults_cleared()
            self.alarm = False
        return self._reply(True, f"Fault {f.fault_id} cleared. Self-check passed")

    def shutdown(self):
        try:
            self._guard("shutdown")
            if self.modes.mode != MAINTENANCE:
                raise Rejected("Enter maintenance mode before shutting down")
        except Rejected as r:
            return self._reply(False, r.reason)
        for loc in self._hw.locations():
            self._hw.command_lock(loc, True)
        self.log.record("SHUTDOWN", user_id=self.session.user_id)
        self.halted, self.session = True, None
        return self._reply(True, "Cabinet shut down. All drawers locked")

    def simulate_hang(self, seconds):
        """Demo/test only: the software stops kicking the watchdog for `seconds`."""
        self._hang_until = self.clock.now() + seconds

    # ---------- control cycle ----------
    def tick(self):
        if self.halted:
            return
        now = self.clock.now()
        if now >= self._hang_until:
            self.faults.kick_watchdog()
        for f in self.faults.check():
            self.log.record("FAULT", fault_id=f.fault_id, fault_type=f.fault_type, location=f.location,
                            time_raised=self.clock.fmt(f.raised_at))
            self.modes.fault_detected()
            self.dispensing.on_fault(f)
            self.alarm = True
            self.comms.send("ALARM", f.to_dict())                     # FR-COM-07
            where = f"drawer {f.location}" if f.location else "cabinet software"
            self.message = f"FAULT: {f.fault_type} at {where}. Technician required"
        done = self.dispensing.poll()
        if done:
            self.comms.send("INVENTORY", self.inventory.snapshot())   # FR-COM-02
            if done["result"] == "Completed":
                self.message = f"{done['kind'].title()} complete. Drawer {done['location']} locked"
                if self.session:
                    self.log.record("LOGOUT", user_id=self.session.user_id, reason="transaction complete")
                    self.session = None
            else:
                self.message = f"Drawer {done['location']} relocked: {done.get('reason', '')}"
        self._incoming()                                              # FR-COM-06, NFR-SEC-01
        if self.session and self.access.expired(self.session) and not self.dispensing.in_progress():
            self.log.record("LOGOUT", user_id=self.session.user_id, reason="session timeout")
            self.session = None
            self.message = "Session timed out"
        if now - self._last_status >= cfg.STATUS_PERIOD_S:            # FR-COM-01
            self._last_status = now
            self.comms.send("STATUS", {"mode": self.modes.mode, "faults": [f.to_dict() for f in self.faults.active()]})
        records = self.log.all()[self._forwarded:]                     # FR-COM-08
        for r in records:
            self.comms.send("EVENT", r)
        self._forwarded += len(records)
        self.comms.tick()
        up = self.comms.available()
        if up != self._link_up:
            self._link_up = up
            self.log.record("LINK_RESTORED" if up else "LINK_LOST", queued=self.comms.queued())

    def _incoming(self):
        ok, bad, dropped = self.comms.receive()
        for m in dropped:
            self.log.record("MESSAGE_DROPPED", reason="duplicate or out-of-order", seq=m.get("seq"), message_kind=m.get("kind"))
        for m in bad:
            self.log.record("NETWORK_COMMAND_REJECTED", reason="bad signature", message_kind=m.get("kind"))
        for m in ok:
            if m["kind"] == "ORDER":
                p = m["payload"]
                try:
                    self.orders.add(p["order_id"], p["medication_id"], int(p["quantity"]))
                    self.log.record("ORDER_RECEIVED", order_id=p["order_id"], medication_id=p["medication_id"],
                                    quantity=p["quantity"])
                except Rejected as r:
                    self.log.record("ORDER_REJECTED", order_id=p.get("order_id"), reason=r.reason)
        return ok

    # ---------- view ----------
    def snapshot(self):
        s = self.session
        locs = {}
        for loc, e in self.inventory.snapshot().items():
            locs[loc] = {**e, "lock": self._hw.read_lock(loc), "drawer": self._hw.read_drawer(loc),
                         "faulted": self.faults.is_faulted(loc)}
        meds = {e["medication_id"]: e["name"] for e in self.inventory.snapshot().values()}
        orders = []
        if s and s.role == "Nurse":                                    # NFR-SEC-02
            orders = [{**o, "name": meds.get(o["medication_id"], o["medication_id"])} for o in self.orders.active()]
        return {
            "clock": self.clock.fmt(self.clock.now()),
            "mode": self.modes.mode,
            "halted": self.halted,
            "alarm": self.alarm,
            "message": self.message,
            "session": {"user_id": s.user_id, "role": s.role, "name": s.name} if s else None,
            "dispense_state": self.dispensing.state,
            "transaction": self.dispensing.current(),
            "locations": locs,
            "faults": [{**f.to_dict(), "raised": self.clock.fmt(f.raised_at)} for f in self.faults.active()],
            "orders": orders,
            "link_up": self.comms.available(),
            "queued": self.comms.queued(),
            "log": self.log.all()[-40:][::-1],
        }
