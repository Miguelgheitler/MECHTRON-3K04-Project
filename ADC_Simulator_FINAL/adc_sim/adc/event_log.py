"""Event Logger module.

Secret: the record layout and how records are kept (via Storage).
Anticipated change: the hospital asks for extra fields or a different log store.

Interface
  record(kind, **fields) -> dict   append one record (adds id + timestamp) and
                                    return a copy. There is deliberately no
                                    update or delete operation (NFR-AUD-04).
  all() -> list[dict]              copies of every record, oldest first
  count() -> int
Records survive a restart (NFR-REL-03).
"""


class EventLog:
    def __init__(self, store, clock):
        self._store = store
        self._clock = clock
        self._records = store.read_all("event_log")

    def record(self, kind: str, **fields) -> dict:
        t = self._clock.now()
        rec = {"id": len(self._records) + 1, "time": t, "clock": self._clock.fmt(t), "kind": kind, **fields}
        self._records.append(rec)
        self._store.append("event_log", rec)
        return dict(rec)

    def all(self) -> list[dict]:
        return [dict(r) for r in self._records]

    def count(self) -> int:
        return len(self._records)
