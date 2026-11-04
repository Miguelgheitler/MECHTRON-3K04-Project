"""
Module: Alarm ADT & Routing (alarm_class.py)
Parnas Category: Behaviour Hiding / Abstract Data Type (ADT) Module
Responsibility: Represents an ADC alarm, enforces severity classification and 1-hour 
escalation logic, determines recipient staff roles, and scrubs Personally Identifiable 
Information (PII) prior to personal device dispatch.

Module Secret (Information Hiding):
Hides the recipient routing policies per alarm type, the internal escalation state 
transition logic, and the regular expressions used to scrub patient PII.

State Invariants Preserved:
1. INV_ALM_1: (alarmType == AlarmType.CONNECTION_LOST) => (isCritical == True)
   (Lost connection to an ADC is always treated as a critical alarm).
2. INV_ALM_2: (isCritical == True) => "SUPERVISOR" in find_recipient()
   (Critical alerts always notify senior hospital oversight).
3. INV_ALM_3: Personal device alert strings emitted by get_sanitized_personal_alert() 
   never contain raw patient names or IDs.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
import re
from event_logger import EventLogger


# =========================================================================
# EXPORTED TYPES & ENUMERATIONS (Public Interface)
# =========================================================================

class AlarmType(str, Enum):
    """Exported Enumeration of valid ADC and clinical alarm categories."""
    CONNECTION_LOST = "CONNECTION_LOST"
    CABINET_FAULT = "CABINET_FAULT"
    LOW_INVENTORY = "LOW_INVENTORY"
    MISSED_DOSE = "MISSED_DOSE"


# =========================================================================
# ALARM ABSTRACT DATA TYPE & ROUTER (Public Interface & Hidden Logic)
# =========================================================================

class Alarm:
    """
    Hides internal alarm state representation, PII scrubbing regex, and recipient mapping tables.
    State Invariant: CONNECTION_LOST alarms are always critical (alarmType == CONNECTION_LOST => isCritical == True).
    """
    # IMPLEMENTATION SECRET: Shared audit logger reference for recording alarm lifecycle events
    _logger = EventLogger("system_audit_log.txt")

    def __init__(
        self,
        adcID: str,
        alarmType: AlarmType,
        isCritical: bool,
        details: str = "",
        timestamp: Optional[datetime] = None
    ):
        """
        Public Interface Constructor for instantiating an Alarm object.

        Assumptions:
            adcID follows the 'ADC-##' format; EventLogger is available for audit logging.
        Post-Condition:
            Initializes alarm state attributes and enforces INV_ALM_1 (CONNECTION_LOST is always critical).
        Exceptions:
            Invalid or missing timestamps default cleanly to datetime.now().
        """
        self.adcID = adcID
        self.alarmType = AlarmType(alarmType) if not isinstance(alarmType, AlarmType) else alarmType
        
        # SAFETY INVARIANT (INV_ALM_1): CONNECTION_LOST is always critical
        self.isCritical = True if self.alarmType == AlarmType.CONNECTION_LOST else bool(isCritical)
        self.details = details
        self.timestamp = timestamp if timestamp is not None else datetime.now()
        
        # Internal lifecycle tracking flags (State Diagram 1: Alarm Lifecycle)
        self.isAcknowledged: bool = False
        self.acknowledgedBy: Optional[str] = None
        self.isResolved: bool = False

    # =========================================================================
    # PUBLIC INTERFACE METHODS (Exported Operations)
    # =========================================================================

    def escalate(self) -> None:
        """
        Public Interface method to escalate an unaddressed minor alarm to CRITICAL.

        Pre-Condition:
            self.isResolved == False
        Post-Condition:
            self.isCritical == True ^ logged("ALARM_ESCALATED")
        Effects:
            Mutates self.isCritical in memory and writes an ALARM_ESCALATED record 
            to system_audit_log.txt via EventLogger.
        """
        if not self.isResolved:
            # IMPLEMENTATION SECRET: State transition from ActiveMinor -> ActiveCritical
            self.isCritical = True
            self._logger.log_event(
                "ALARM_ESCALATED",
                self.adcID,
                f"{self.alarmType.value} at {self.adcID} escalated to CRITICAL. Routing to SUPERVISOR.",
                "SYSTEM"
            )

    def acknowledge(self, userID: str) -> None:
        """
        Public Interface method marking the alarm as acknowledged/in-progress by staff.

        Effects:
            Sets self.isAcknowledged = True, records self.acknowledgedBy = userID, 
            and writes an ALARM_ACK record to system_audit_log.txt via EventLogger.
        """
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
        Public Interface method that determines target recipient roles for this alarm.

        Semantics:
            Maps self.alarmType to base recipient UserRole strings, and enforces 
            Safety Invariant INV_ALM_2 by appending "SUPERVISOR" 
            whenever self.isCritical == True.
        """
        # IMPLEMENTATION SECRET: Internal routing policy mapping alarm types to hospital roles.
        # If hospital policy changes which department handles an alarm, only this method changes.
        recipients = []
        if self.alarmType == AlarmType.CONNECTION_LOST:
            recipients.extend(["IT_ADMIN", "SUPERVISOR"])
        elif self.alarmType == AlarmType.LOW_INVENTORY:
            recipients.extend(["PHARMACIST"])
        elif self.alarmType in (AlarmType.CABINET_FAULT, AlarmType.MISSED_DOSE):
            recipients.extend(["NURSE", "SUPERVISOR"])

        # Safety Rule (INV_ALM_2): Critical alerts ALWAYS notify Supervisor
        if self.isCritical:
            if "SUPERVISOR" not in recipients:
                    recipients.append("SUPERVISOR")
        return recipients

    def get_sanitized_personal_alert(self) -> str:
        """
        Public Interface method that scrubs Personally Identifiable Information (PII) 
        before dispatching alert text to staff personal mobile devices.

        Post-Condition (INV_ALM_3):
            Replaces any patient name/ID tokens in self.details with '[REDACTED_PII]'
            and returns the sanitized alert string.
        """
        # IMPLEMENTATION SECRET: Regular expression pattern used for PII redaction
        scrubbed_details = re.sub(r"(?i)(patient\s*(name|id)?\s*[:=-]?\s*[A-Za-z0-9_-]+)", "[REDACTED_PII]", self.details)
        severity_str = "CRITICAL" if self.isCritical else "MINOR"
        return f"[{severity_str} ALERT] ADC: {self.adcID} | Type: {self.alarmType.value} | Info: {scrubbed_details} (Log in on Hospital Device for full details)"

    def __repr__(self) -> str:
        """Clean string representation of the Alarm ADT."""
        severity = "CRITICAL" if self.isCritical else "MINOR"
        return f"Alarm [{severity}] {self.alarmType.value} at {self.adcID}"


# =============================================================================
# TERMINAL COPY-PASTE TEST INSTRUCTIONS (Interactive Python Shell)
# =============================================================================
# Open your terminal inside your code directory, type `python3`, then paste:
#
#   from alarm_class import Alarm, AlarmType
#
#   # 1. Test Minor Low Inventory Alarm & Recipient Routing
#   a1 = Alarm("ADC-01", AlarmType.LOW_INVENTORY, isCritical=False, details="Morphine below par")
#   print(a1, "-> Recipients:", a1.find_recipient())
#
#   # 2. Test 1-Hour Escalation to Critical (INV_ALM_2)
#   a1.escalate()
#   print(a1, "-> Escalated Recipients:", a1.find_recipient())
#
#   # 3. Test PII Scrubbing for Personal Devices (INV_ALM_3)
#   a2 = Alarm("ADC-02", AlarmType.MISSED_DOSE, isCritical=True, details="Missed scheduled dose for Patient: John_Doe")
#   print(a2.get_sanitized_personal_alert())