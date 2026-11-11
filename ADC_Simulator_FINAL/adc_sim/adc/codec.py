"""Message Codec module.

Secret: the message format and how messages are authenticated (JSON with an
HMAC-SHA256 signature over the content, using a key shared with the paired
Monitoring System).
Anticipated change: the hospital mandates a different protocol or security
scheme. Only this file changes.

Interface
  encode(kind, payload, seq) -> dict   signed message {sender, seq, kind, payload, sig}
  verify(msg) -> bool                  True only if the signature matches (NFR-SEC-01)
"""
import hashlib
import hmac
import json


class MessageCodec:
    def __init__(self, key: bytes, sender: str):
        self._key = key
        self._sender = sender

    def _sig(self, body: dict) -> str:
        raw = json.dumps(body, sort_keys=True).encode()
        return hmac.new(self._key, raw, hashlib.sha256).hexdigest()

    def encode(self, kind, payload, seq) -> dict:
        body = {"sender": self._sender, "seq": seq, "kind": kind, "payload": payload}
        return {**body, "sig": self._sig(body)}

    def verify(self, msg) -> bool:
        body = {k: v for k, v in msg.items() if k != "sig"}
        return hmac.compare_digest(msg.get("sig", ""), self._sig(body))
