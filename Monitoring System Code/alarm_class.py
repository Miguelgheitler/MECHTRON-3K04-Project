from datetime import datetime
from typing import Optional
from enum import Enum

class AlarmType(str, Enum):
    CONNECTION_LOST = "CONNECTION_LOST"
    CABINET_FAULT = "CABINET_FAULT"
    LOW_INVENTORY = "LOW_INVENTORY"

class Alarm:
    def __init__(
        self,
        adcID: str,
        alarmType: AlarmType,
        isCritical: bool,
        details: str = "",
        timestamp: Optional[datetime] = None
    ):
        self.adcID = adcID
        self.alarmType = alarmType
        self.isCritical = isCritical
        self.details = details
        self.timestamp = timestamp if timestamp is not None else datetime.now()

    def escalate(self):
        self.isCritical = True
    
    def add_to_log(self): # <USES> from event_logger.py

    def __repr__(self):
        severity = "CRITICAL" if self.isCritical else "MINOR"
        return f"Alarm [{severity}]\n{self.alarmType} at ADC{self.adcID}"

# SAMPLE OBJECT CREATION
# alarm327 = Alarm(
#     adcID = "ADC-4",
#     alarmType = "CONNECTION_LOST",
#     isCritical = True
# )