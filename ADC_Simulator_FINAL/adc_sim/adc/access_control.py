"""Access Control module.

Secret: how credentials are checked, the lockout policy, and the role ->
permission table.
Anticipated change: badge + PIN is replaced by another login method, or the
hospital changes who may do what.

Interface
  authenticate(badge, pin) -> Session     Rejected on bad credentials or an
                                           active lockout (FR-AUT-01, FR-AUT-04);
                                           every failure is logged (FR-LOG-04)
  authorize(session, action)              Rejected if the role may not do the
                                           action (FR-AUT-02, FR-AUT-03)
  touch(session) / expired(session) -> bool   idle-session handling
"""
from dataclasses import dataclass

from .errors import Rejected


@dataclass
class Session:
    user_id: str
    role: str
    name: str
    started: float
    last_activity: float


class AccessControl:
    def __init__(self, users, permissions, clock, log, max_failed, lockout_s, session_timeout_s):
        self._users = users
        self._perm = permissions
        self._clock = clock
        self._log = log
        self._max = max_failed
        self._lockout = lockout_s
        self._timeout = session_timeout_s
        self._failed = {}         # badge -> consecutive failures
        self._locked_until = {}   # badge -> time

    def authenticate(self, badge, pin) -> Session:
        now = self._clock.now()
        until = self._locked_until.get(badge, 0)
        if now < until:
            mins = int((until - now) // 60) + 1
            self._log.record("AUTH_FAILED", user_id=badge, reason="account locked")
            raise Rejected(f"Account locked. Try again in {mins} min")
        u = self._users.get(badge)
        if u is None or u["pin"] != pin:
            n = self._failed.get(badge, 0) + 1
            self._failed[badge] = n
            self._log.record("AUTH_FAILED", user_id=badge, reason="invalid credentials", attempt=n)
            if n >= self._max:
                self._locked_until[badge] = now + self._lockout
                self._failed[badge] = 0
                self._log.record("ACCOUNT_LOCKED", user_id=badge, minutes=self._lockout // 60)
                raise Rejected(f"Invalid badge or PIN. Account locked for {self._lockout // 60} min")
            raise Rejected(f"Invalid badge or PIN ({self._max - n} attempt(s) left)")
        self._failed[badge] = 0
        self._log.record("LOGIN", user_id=badge, role=u["role"])
        return Session(badge, u["role"], u["name"], now, now)

    def authorize(self, session, action):
        if session is None:
            raise Rejected("Please log in first")
        if session.role not in self._perm.get(action, set()):
            self._log.record("ACCESS_DENIED", user_id=session.user_id, role=session.role, action=action)
            raise Rejected(f"Not permitted for your role ({session.role})")

    def touch(self, session):
        session.last_activity = self._clock.now()

    def expired(self, session) -> bool:
        return self._clock.now() - session.last_activity > self._timeout
