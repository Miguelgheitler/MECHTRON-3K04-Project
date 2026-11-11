"""Mode Manager module (D1 Figure 8, operational modes).

Secret: the mode set and the rules for moving between modes.
Anticipated change: a new mode is added (e.g. a 'restocking' mode).

The state machine is the TRANSITIONS table below: one cell per mode x event.
Each cell is a next mode, IGNORE (no change) or a Reject (no change, logged).

Interface
  mode -> 'NORMAL' | 'MAINTENANCE' | 'FAULT'        exactly one at a time (FR-MOD-01)
  fault_detected()        NORMAL/MAINTENANCE -> FAULT                    (FR-MOD-04)
  all_faults_cleared()    FAULT -> NORMAL                                (FR-MOD-05)
  enter_maintenance(dispense_in_progress)   NORMAL -> MAINTENANCE; Rejected while a
                                             dispense is in progress (FR-MOD-06) or in FAULT
  exit_maintenance()      MAINTENANCE -> NORMAL                          (FR-MOD-07)
  dispensing_allowed() -> bool               False in MAINTENANCE
Every change is logged (FR-LOG-05); every rejected event is logged. The caller
checks the Technician role (FR-MOD-02).
"""
from enum import Enum

from .errors import Rejected


class Mode(str, Enum):
    NORMAL = "NORMAL"
    MAINTENANCE = "MAINTENANCE"
    FAULT = "FAULT"


class Event(str, Enum):
    FAULT_DETECTED = "faultDetected"
    LAST_FAULT_CLEARED = "lastFaultCleared"
    MAINT_REQUEST = "maintenanceRequested"            # guard: no dispense in progress
    MAINT_REQUEST_BUSY = "maintenanceRequested[busy]"  # guard: dispense in progress
    MAINT_EXIT = "maintenanceExited"


IGNORE = "IGNORE"
NORMAL, MAINTENANCE, FAULT = Mode.NORMAL.value, Mode.MAINTENANCE.value, Mode.FAULT.value

N, M, F = Mode.NORMAL, Mode.MAINTENANCE, Mode.FAULT
TRANSITIONS = {
    (N, Event.FAULT_DETECTED): F,
    (N, Event.LAST_FAULT_CLEARED): IGNORE,
    (N, Event.MAINT_REQUEST): M,
    (N, Event.MAINT_REQUEST_BUSY): Rejected("A dispense is in progress. Try again when it finishes"),
    (N, Event.MAINT_EXIT): Rejected("Not in maintenance mode"),
    (M, Event.FAULT_DETECTED): F,
    (M, Event.LAST_FAULT_CLEARED): IGNORE,
    (M, Event.MAINT_REQUEST): Rejected("Already in maintenance mode"),
    (M, Event.MAINT_REQUEST_BUSY): Rejected("Already in maintenance mode"),
    (M, Event.MAINT_EXIT): N,
    (F, Event.FAULT_DETECTED): IGNORE,
    (F, Event.LAST_FAULT_CLEARED): N,
    (F, Event.MAINT_REQUEST): Rejected("Clear active faults before entering maintenance"),
    (F, Event.MAINT_REQUEST_BUSY): Rejected("Clear active faults before entering maintenance"),
    (F, Event.MAINT_EXIT): Rejected("Not in maintenance mode"),
}


class ModeManager:
    def __init__(self, log):
        self._log = log
        self._mode = Mode.NORMAL

    @property
    def mode(self) -> str:
        return self._mode.value

    def _handle(self, event: Event, reason: str):
        cell = TRANSITIONS[(self._mode, event)]
        if cell == IGNORE:
            return
        if isinstance(cell, Rejected):
            self._log.record("MODE_EVENT_REJECTED", mode=self.mode, event=event.value, reason=cell.reason)
            raise Rejected(cell.reason)
        self._log.record("MODE_CHANGE", from_mode=self.mode, to_mode=cell.value, reason=reason)
        self._mode = cell

    def fault_detected(self):
        self._handle(Event.FAULT_DETECTED, "fault detected")

    def all_faults_cleared(self):
        self._handle(Event.LAST_FAULT_CLEARED, "last active fault cleared")

    def enter_maintenance(self, dispense_in_progress: bool):
        self._handle(Event.MAINT_REQUEST_BUSY if dispense_in_progress else Event.MAINT_REQUEST, "technician request")

    def exit_maintenance(self):
        self._handle(Event.MAINT_EXIT, "technician exit")

    def dispensing_allowed(self) -> bool:
        return self._mode != Mode.MAINTENANCE
