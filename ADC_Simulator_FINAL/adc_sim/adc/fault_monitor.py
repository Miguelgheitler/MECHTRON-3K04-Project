"""Fault Monitor module.

Secret: how each kind of fault is detected (what is polled, which timers run).
Anticipated change: a new fault type or a new detection rule is added.

Interface
  expect_lock(loc, locked)   tell the monitor a lock command was just sent
  kick_watchdog()            called every software cycle (FR-FLT-05)
  check() -> list[Fault]     run all detectors; returns NEW faults only
                             (FR-FLT-01..05, NFR-PRF-02: called every 0.1 s)
  active() -> list[Fault]
  is_faulted(loc) -> bool    True if the location, or the whole cabinet, has an
                             active fault (FR-FLT-03, FR-MOD-03)
  clear(fault_id, technician_id) -> Fault    Rejected unless the self-check
                             passes (FR-FLT-06, FR-FLT-07); records who cleared it
Fault types: LOCK, DRAWER_OPEN, SENSOR, WATCHDOG (WATCHDOG has no location and
blocks the whole cabinet).
"""
from dataclasses import dataclass, asdict
from itertools import count

from .errors import Rejected


@dataclass
class Fault:
    fault_id: int
    fault_type: str
    location: str | None
    raised_at: float
    cleared_at: float | None = None
    cleared_by: str | None = None

    def to_dict(self):
        return asdict(self)


class FaultMonitor:
    def __init__(self, hw, clock, lock_timeout, drawer_timeout, sensor_timeout, watchdog_timeout):
        self._hw = hw
        self._clock = clock
        self._lock_to, self._drawer_to = lock_timeout, drawer_timeout
        self._sensor_to, self._wd_to = sensor_timeout, watchdog_timeout
        now = clock.now()
        self._pending = {}                                 # loc -> (wanted_locked, sent_at)
        self._unlocked_at = {}                             # loc -> time of unlock command
        self._last_reply = {loc: now for loc in hw.locations()}
        self._last_kick = now
        self._active: list[Fault] = []
        self._ids = count(1)

    def expect_lock(self, loc, locked):
        now = self._clock.now()
        self._pending[loc] = (locked, now)
        if locked:
            self._unlocked_at.pop(loc, None)
        else:
            self._unlocked_at[loc] = now

    def kick_watchdog(self):
        self._last_kick = self._clock.now()

    def _has(self, ftype, loc):
        return any(f.fault_type == ftype and f.location == loc for f in self._active)

    def _raise(self, ftype, loc, new):
        if not self._has(ftype, loc):
            f = Fault(next(self._ids), ftype, loc, self._clock.now())
            self._active.append(f)
            new.append(f)

    def check(self) -> list[Fault]:
        now, new = self._clock.now(), []
        for loc in self._hw.locations():
            drawer = self._hw.read_drawer(loc)
            lock = self._hw.read_lock(loc)
            if drawer is None or lock is None:                      # FR-FLT-04
                if now - self._last_reply[loc] > self._sensor_to:
                    self._raise("SENSOR", loc, new)
                continue
            self._last_reply[loc] = now
            if loc in self._pending:                                  # FR-FLT-01
                wanted, sent = self._pending[loc]
                if lock == wanted:
                    del self._pending[loc]
                elif now - sent > self._lock_to:
                    self._raise("LOCK", loc, new)
                    del self._pending[loc]
            t = self._unlocked_at.get(loc)                            # FR-FLT-02
            if t is not None and drawer == "open" and now - t > self._drawer_to:
                self._raise("DRAWER_OPEN", loc, new)
                del self._unlocked_at[loc]
        if now - self._last_kick > self._wd_to:                       # FR-FLT-05
            self._raise("WATCHDOG", None, new)
        return new

    def active(self):
        return list(self._active)

    def is_faulted(self, loc) -> bool:
        return any(f.location in (loc, None) for f in self._active)

    def clear(self, fault_id, technician_id) -> Fault:
        f = next((x for x in self._active if x.fault_id == fault_id), None)
        if f is None:
            raise Rejected("No such active fault")
        if f.location is None:
            ok = self._clock.now() - self._last_kick <= self._wd_to
        else:
            ok = self._hw.self_test(f.location)
        if not ok:
            raise Rejected("Self-check failed. Fault stays active")
        f.cleared_at, f.cleared_by = self._clock.now(), technician_id
        self._active.remove(f)
        if f.location is not None:
            self._last_reply[f.location] = self._clock.now()
        return f
