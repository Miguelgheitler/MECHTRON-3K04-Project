"""Clock module.

Secret: where time comes from.
Anticipated change: switching from the demo's simulated clock to a hardware
real-time clock. Every other module only calls now().

Interface
  now() -> float        seconds since epoch
  advance(dt)           (SimClock only) move time forward; used by the demo's
                        fast-forward button and by the tests
  fmt(t) -> str         'HH:MM:SS' for display and records
"""
import time


class Clock:
    def now(self) -> float:
        return time.time()

    @staticmethod
    def fmt(t: float) -> str:
        return time.strftime("%H:%M:%S", time.localtime(t))


class SimClock(Clock):
    def __init__(self, start: float | None = None):
        self._t = time.time() if start is None else start

    def now(self) -> float:
        return self._t

    def advance(self, dt: float) -> None:
        if dt < 0:
            raise ValueError("time cannot go backwards")
        self._t += dt
