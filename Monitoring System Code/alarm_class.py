"""
Module: Alarm ADT & Routing (alarm_class.py)
Responsibility: Encapsulates alarm state, severity classification, 1-hour escalation logic, recipient routing, and PII-scrubbed personal device notifications.
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum
import re
from event_logger import EventLogger


class AlarmType(str, Enum):
    CONNECTION_LOST = "CONNECTION_LOST"
    CABINET_FAULT = "CABINET_FAULT"
    LOW_INVENTORY = "LOW_INVENTORY"
    MISSED_DOSE = "MISSED_DOSE"


class Alarm:
    """
    Hides internal alarm state representation, PII scrubbing regex, and recipient mapping tables.
    State Invariant: CONNECTION_LOST alarms are always critical (alarmType == CONNECTION_LOST => isCritical == True).
    """
    _logger = EventLogger("system_audit_log.txt")

    def __init__(
        self,
        adcID: str,
        alarmType: AlarmType,
        isCritical: bool,
        details: str = "",
        timestamp: Optional[datetime] = None
    ):
        self.adcID = adcID
        self.alarmType = AlarmType(alarmType) if not isinstance(alarmType, AlarmType) else alarmType
        # Enforce safety invariant: CONNECTION_LOST is always critical (US-COM-01)
        self.isCritical = True if self.alarmType == AlarmType.CONNECTION_LOST else bool(isCritical)
        self.details = details
        self.timestamp = timestamp if timestamp is not None else datetime.now()
        self.isAcknowledged: bool = False
        self.acknowledgedBy: Optional[str] = None
        self.isResolved: bool = False

    def escalate(self) -> None:
        """
        SP-ALM-05 (Traces to NFR-ALM-02, NFR-ALM-07, US-ALM-01):
        Escalates an unaddressed minor alarm to CRITICAL (e.g., after 1 hour) and logs it.
        """
        if not self.isResolved:
            self.isCritical = True
            self._logger.log_event(
                "ALARM_ESCALATED",
                self.adcID,
                f"{self.alarmType.value} at {self.adcID} escalated to CRITICAL. Routing to PROJECT_MANAGER & SUPERVISOR.",
                "SYSTEM"
            )

    def acknowledge(self, userID: str) -> None:
        """Marks the alarm as in-progress/acknowledged by an authorized staff member (FR-LOG-04)."""
        self.isAcknowledged = True
        self.acknowledgedBy = userID
        self._logger.log_event(
            "ALARM_ACK",
            self.adcID,
            f"Alarm {self.alarmType.value} acknowledged by {userID}.",
            userID
        )

    def find_recipient(self) -> List[str]:
        """
        SP-ALM-02 (Traces to FR-ALM-02, NFR-ALM-01):
        Determines target recipient roles based on alarm type and criticality.
        """
        recipients = []
        if self.alarmType == AlarmType.CONNECTION_LOST:
            recipients.extend(["IT_ADMIN", "SUPERVISOR"])
        elif self.alarmType == AlarmType.LOW_INVENTORY:
            recipients.extend(["PHARMACIST"])
        elif self.alarmType in (AlarmType.CABINET_FAULT, AlarmType.MISSED_DOSE):
            recipients.extend(["NURSE", "SUPERVISOR"])

        # Safety Rule (NFR-ALM-01): Critical alerts ALWAYS notify the Project Manager & Supervisor
        if self.isCritical:
            for role in ("PROJECT_MANAGER", "SUPERVISOR"):
                if role not in recipients:
                    recipients.append(role)
        return recipients

    def get_sanitized_personal_alert(self) -> str:
        """
        SP-ALM-03 / SP-PID-02 (Traces to FR-ALM-03, NFR-ALM-04, FR-PID-02):
        Scrubs Personally Identifiable Information (PII) before sending alert text
        to staff personal devices.
        """
        scrubbed_details = re.sub(r"(?i)(patient\s*(name|id)?\s*[:=-]?\s*[A-Za-z0-9_-]+)", "[REDACTED_PII]", self.details)
        severity_str = "CRITICAL" if self.isCritical else "MINOR"
        return f"[{severity_str} ALERT] ADC: {self.adcID} | Type: {self.alarmType.value} | Info: {scrubbed_details} (Log in on Hospital Device for full details)"

    def __repr__(self) -> str:
        severity = "CRITICAL" if self.isCritical else "MINOR"
        return f"Alarm [{severity}] {self.alarmType.value} at {self.adcID}"
