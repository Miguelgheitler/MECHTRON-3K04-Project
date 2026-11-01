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
        adcID: int,
        alarmType: AlarmType,
        isCritical: bool,
        details: str = "",
        timestamp: Optional[datetime] = None
    ):
        self.adcID = adcID
        self.alarmType = alarmType
        self.isCritical = isCritical
        self.details = details
        if timestamp == None:
            self.timestamp = datetime.now()
        else:
            self.timestamp = timestamp

    def escalate(self):
        self.isCritical = True

    def __repr__(self):
        severity = "CRITICAL" if self.isCritical else "MINOR"
        return f"Alarm [{severity}]\n{self.alarmType} at ADC{self.adcID}"

# SAMPLE OBJECT CREATION
# alarm327 = Alarm(
#     adcID = 4,
#     alarmType = "CONNECTION_LOST",
#     isCritical = True
# )