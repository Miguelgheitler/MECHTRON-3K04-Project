from datetime import datetime
from typing import Optional
from enum import Enum
from event_logger import EventLogger 

class AlarmType(str, Enum):
    CONNECTION_LOST = "CONNECTION_LOST"
    CABINET_FAULT = "CABINET_FAULT"
    LOW_INVENTORY = "LOW_INVENTORY"

class Alarm:
    _logger = EventLogger()

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
        #escaltes alarm to critical and logs it 
        self.isCritical = True
        self._logger.log_event("alarm_escalated", f"{self.alarmType} at ADC {self.adcID} escalated to CRITICAL.")

    def __repr__(self):
        severity = "CRITICAL" if self.isCritical else "MINOR"
        return f"Alarm [{severity}]"

# sample alarm
# if __name__ == "__main__":
#     alarm327 = Alarm(
#         adcID="ADC-4",
#         alarmType=AlarmType.CONNECTION_LOST,
#         isCritical=True,
#         details="ADC failed 30-second heartbeat ping."
#     )
#     print(alarm327)
    
#     minor_alarm = Alarm(
#         adcID="ADC-1",
#         alarmType=AlarmType.LOW_INVENTORY,
#         isCritical=False,
#         details="Medication Y is below minimum threshold."
#     )
    
#     minor_alarm.escalate()
#     print(minor_alarm)