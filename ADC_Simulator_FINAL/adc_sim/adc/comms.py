"""Comms Link module.

Secret: buffering, ordering and link-loss detection, and the transport behind
the Channel interface (Wi-Fi, wired network, serial...).
Anticipated change: the transport or the retry policy changes.

Channel (interface the transport must provide)
  transmit(msg) -> bool    True if the Monitoring System acknowledged it
  receive() -> list[dict]  messages waiting from the Monitoring System

CommsLink
  send(kind, payload)      queue a message; never blocks (FR-COM-03)
  tick()                   transmit queued messages oldest first until one is
                           not acknowledged (FR-COM-04, NFR-PRF-03)
  receive() -> (accepted, rejected, dropped)
                           rejected = bad signature (NFR-SEC-01);
                           dropped = duplicate or out-of-order sequence number
  available() -> bool      False when nothing has been acknowledged for
                           LINK_TIMEOUT_S (FR-COM-09)
  queued() -> int
The outbox is saved to disk so queued messages survive a restart (NFR-REL-02).
"""
from collections import deque


class Channel:
    def transmit(self, msg: dict) -> bool: raise NotImplementedError
    def receive(self) -> list[dict]: raise NotImplementedError


class CommsLink:
    def __init__(self, channel, codec, clock, store, link_timeout, capacity):
        self._ch, self._codec, self._clock, self._store = channel, codec, clock, store
        self._timeout, self._cap = link_timeout, capacity
        saved = store.load("outbox", {"seq": 0, "queue": [], "last_rx": 0})
        self._seq = saved["seq"]
        self._out = deque(saved["queue"])
        self._last_rx = saved.get("last_rx", 0)
        self._last_ack = clock.now()

    def _persist(self):
        self._store.save("outbox", {"seq": self._seq, "queue": list(self._out), "last_rx": self._last_rx})

    def send(self, kind, payload):
        self._seq += 1
        if len(self._out) >= self._cap:
            self._out.popleft()
        self._out.append(self._codec.encode(kind, payload, self._seq))
        self._persist()

    def tick(self):
        sent = False
        while self._out:
            if not self._ch.transmit(self._out[0]):
                break
            self._out.popleft()
            self._last_ack = self._clock.now()
            sent = True
        if sent:
            self._persist()

    def receive(self):
        ok, bad, dropped = [], [], []
        for m in self._ch.receive():
            if not self._codec.verify(m):
                bad.append(m)
            elif m["seq"] <= self._last_rx:
                dropped.append(m)
            else:
                self._last_rx = m["seq"]
                ok.append(m)
        if ok:
            self._last_ack = self._clock.now()
            self._persist()
        return ok, bad, dropped

    def available(self) -> bool:
        return self._clock.now() - self._last_ack <= self._timeout

    def queued(self) -> int:
        return len(self._out)
