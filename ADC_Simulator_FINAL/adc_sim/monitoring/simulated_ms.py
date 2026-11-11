"""Stand-in for the Part B Monitoring System, used for the demo and tests.

It is NOT part of the ADC. It implements the Channel interface the ADC needs,
so the real Monitoring System can replace it without changing any ADC module.
"""
import itertools

from adc.codec import MessageCodec
from adc.comms import Channel


class SimulatedMonitoringSystem(Channel):
    def __init__(self, key):
        self.online = True
        self._codec = MessageCodec(key, "MS-1")
        self._inbox = []
        self.received = []
        self._seq = itertools.count(1)
        self._last_sent = None

    # Channel interface (called by the ADC)
    def transmit(self, msg):
        if not self.online:
            return False
        if self._codec.verify(msg):
            self.received.append(msg)
        return True

    def receive(self):
        if not self.online:
            return []
        out, self._inbox = self._inbox, []
        return out

    # Monitoring-side actions (demo panel and tests)
    def send_order(self, order_id, medication_id, quantity):
        msg = self._codec.encode("ORDER", {"order_id": order_id, "medication_id": medication_id,
                                           "quantity": quantity}, next(self._seq))
        self._last_sent = msg
        self._inbox.append(msg)

    def send_duplicate_of_last(self):
        if self._last_sent:
            self._inbox.append(dict(self._last_sent))

    def send_forged_order(self, order_id, medication_id, quantity):
        msg = self._codec.encode("ORDER", {"order_id": order_id, "medication_id": medication_id,
                                           "quantity": quantity}, next(self._seq))
        msg["sig"] = "0" * 64
        self._inbox.append(msg)

    def view(self):
        last = {}
        for m in self.received:
            last[m["kind"]] = m
        return {"online": self.online, "count": len(self.received),
                "status": last.get("STATUS", {}).get("payload"),
                "inventory": last.get("INVENTORY", {}).get("payload"),
                "alarms": [m["payload"] for m in self.received if m["kind"] == "ALARM"][-5:][::-1],
                "recent": [{"seq": m["seq"], "kind": m["kind"],
                            "summary": _summary(m)} for m in self.received[-25:][::-1]]}


def _summary(m):
    p = m["payload"]
    if m["kind"] == "EVENT":
        bits = [p.get("kind", "")] + [f"{k}={p[k]}" for k in ("result", "user_id", "order_id", "location", "fault_type") if p.get(k)]
        return " ".join(str(b) for b in bits)
    if m["kind"] == "ALARM":
        return f"{p['fault_type']} at {p['location'] or 'cabinet'}"
    if m["kind"] == "STATUS":
        return f"mode={p['mode']} faults={len(p['faults'])}"
    return "inventory update"
