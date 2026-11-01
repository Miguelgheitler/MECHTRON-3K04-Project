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
    COMPLETED = "COMPLETED"

class Task:
    def __init__(
        self,
        taskID: str,
        assignee: str, #userID
        taskType: TaskType,
        details: str,
        origin: str = "", #userID if taskType=SPECIAL
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

        # add TASK CREATION to event log, USES FROM event_logger.py

    def assign(self, userID: str, comment: str = ""):
        # supervisor assigns to employee
        self.assignee = userID
        if comment.strip():
            self.furtherNotes.append(comment.strip())
        self.status = TaskStatus.ASSIGNED

    def return_for_clarification(self, comment: str = ""):
        # if consusiong, supervisor returns request to sender
        if comment.strip():
            self.furtherNotes.append(comment.strip())
        self.status = TaskStatus.RETURNED
    
    def resubmit(self, comment: str = ""):
        # sender clarifies confusion
        self.furtherNotes.append(comment.strip())
        self.status = TaskStatus.PENDING
    
    def add_note(self, comment: str = ""):
        self.furtherNotes.append(comment.strip())

    def complete(self):
        self.status = TaskStatus.COMPLETED

        # add TASK COMPLETION to event log, USES FROM event_logger.py


    def __repr__(self):
        furtherNotes = ""
        for i in self.furtherNotes:
            furtherNotes += "\n\t-> "
            furtherNotes += i
        return (
            f"Task {self.taskID} [{self.status.value}] ({self.taskType.value}) "
            f"-> {self.assignee} | Notes: {len(self.furtherNotes)}"
            f"\n\t{self.details}"
            f"{furtherNotes}"
        )

# SAMPLE TASK CALLS

# task123 = Task(
#     taskID = "task123",
#     assignee = "S-001",
#     taskType = TaskType.SPECIAL,
#     details = "ADC 02 has cracked drawer handle",
#     origin = "N-001"
# )

# task123.assign("I-001", "please fix")

# task123.add_note("part has been ordered, expected to arrive Nov 4th")

# task123.complete()