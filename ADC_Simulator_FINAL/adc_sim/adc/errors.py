"""Shared exception type.

Rejected carries the human-readable reason shown on the cabinet screen (NFR-USB-03).
"""


class Rejected(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason
