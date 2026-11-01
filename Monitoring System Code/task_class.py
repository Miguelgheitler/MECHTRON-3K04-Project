from enum import Enum
from datetime import datetime
from typing import Optional

class TaskType(str, Enum):
    ROUTINE = "ROUTINE"
    SPECIAL = "SPECIAL"

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RETURNED = "RETURNED"
    ASSIGNED = "ASSIGNED"

class Task:
    def __init__(
        self,
        taskID: str,
        assignee: str,
        origin: str,
        taskType: TaskType,
        details: str,
        timestamp: Optional[datetime] = None
    ):
        self.taskID = taskID
        self.assignee = assignee
        self.origin = origin
        self.taskType = taskType
        self.details = details
        self.timestamp = timestamp if timestamp is not None else datetime.now()

        self.status: TaskStatus = TaskStatus.PENDING
        self.furtherNotes: List[str] = []

    def reassign(self, employeeID: str)