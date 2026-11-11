"""Hardware-hiding module.

Secret: how drawer locks are driven and how lock/drawer sensors are read
(wiring, signal levels, polling protocol).
Anticipated change: a different lock or sensor model is fitted. Only the
CabinetHardware implementation changes; the rest of the ADC uses the interface.

Interface (CabinetHardware)
  locations() -> list[str]
  command_lock(loc, locked: bool)   effect: asks the lock to engage/release.
                                     The lock may not obey (jammed); the Fault
                                     Monitor detects that (FR-FLT-01).
  read_lock(loc) -> bool | None      True = locked, None = sensor not responding
  read_drawer(loc) -> 'open' | 'closed' | None    None = sensor not responding
  self_test(loc) -> bool             True if lock and sensor respond and the
                                     drawer is closed (used by FR-FLT-07)

SimulatedCabinet also exposes sim_* methods. They stand in for the physical
world (a person opening a drawer, a lock jamming) and are only called by the
demo panel and the tests, never by the ADC modules.
"""


class CabinetHardware:
    def locations(self) -> list[str]: raise NotImplementedError
    def command_lock(self, loc: str, locked: bool) -> None: raise NotImplementedError
    def read_lock(self, loc: str) -> bool | None: raise NotImplementedError
    def read_drawer(self, loc: str) -> str | None: raise NotImplementedError
    def self_test(self, loc: str) -> bool: raise NotImplementedError


class SimulatedCabinet(CabinetHardware):
    def __init__(self, locations):
        self._d = {loc: {"locked": True, "drawer": "closed", "jammed": False, "sensor_dead": False}
                   for loc in locations}

    # --- interface used by the ADC ---
    def locations(self):
        return list(self._d)

    def command_lock(self, loc, locked):
        d = self._d[loc]
        if not d["jammed"]:
            d["locked"] = locked

    def read_lock(self, loc):
        d = self._d[loc]
        return None if d["sensor_dead"] else d["locked"]

    def read_drawer(self, loc):
        d = self._d[loc]
        return None if d["sensor_dead"] else d["drawer"]

    def self_test(self, loc):
        d = self._d[loc]
        return not d["jammed"] and not d["sensor_dead"] and d["drawer"] == "closed"

    # --- physical world, demo panel and tests only ---
    def sim_open_drawer(self, loc) -> bool:
        d = self._d[loc]
        if d["locked"]:
            return False          # a locked drawer cannot be pulled open
        d["drawer"] = "open"
        return True

    def sim_close_drawer(self, loc):
        self._d[loc]["drawer"] = "closed"

    def sim_jam_lock(self, loc, jammed=True):
        self._d[loc]["jammed"] = jammed

    def sim_kill_sensor(self, loc, dead=True):
        self._d[loc]["sensor_dead"] = dead

    def sim_repair(self, loc):
        self._d[loc]["jammed"] = False
        self._d[loc]["sensor_dead"] = False

    def sim_state(self):
        return {loc: dict(v) for loc, v in self._d.items()}
