from enum import Enum
from datetime import datetime
from typing import Optional, List
from event_logger import EventLogger

class TaskType(str, Enum):
    ROUTINE = "ROUTINE"
    SPECIAL = "SPECIAL"

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RETURNED = "RETURNED"
    ASSIGNED = "ASSIGNED"
    COMPLETED = "COMPLETED"

class Task:
    _logger = EventLogger("system_audit_log.txt")

    def __init__(
        self,
        task_id: str,
        sender_id: str,
        task_type: TaskType,
        details: str,
        assignee: str = "SUPERVISOR",  # Default queue owner if pending
        timestamp: Optional[datetime] = None,
        clarification_notes: Optional[List[str]] = None
    ):
        self.task_id = task_id
        self.sender_id = sender_id
        self.task_type = task_type
        self.details = details
        self.assignee = assignee  # Who currently owns/is assigned to this task
        self.timestamp = timestamp if timestamp is not None else datetime.now()

        # Routine tasks auto-delegate to assignee; Special tasks start PENDING with supervisor
        self.status: TaskStatus = TaskStatus.ASSIGNED if task_type == TaskType.ROUTINE else TaskStatus.PENDING
        self.clarification_notes: List[str] = clarification_notes if clarification_notes is not None else []

        self._logger.log_event(
            "TASK_CREATED",
            self.task_id,
            f"Task ({self.task_type.value}) created by {self.sender_id} -> Assignee: {self.assignee}. Details: {self.details}",
            self.sender_id
        )

    def assign(self, employee_id: str, supervisor_id: str, comment: str = "") -> None:
        """Supervisor assigns task to an employee (FR-TSK-02)."""
        self.assignee = employee_id.strip()
        if comment.strip():
            self.clarification_notes.append(comment.strip())
        self.status = TaskStatus.ASSIGNED
        self._logger.log_event("TASK_ASSIGNED", self.task_id, f"Assigned to {self.assignee} by Supervisor {supervisor_id}.", supervisor_id)

    def return_for_clarification(self, supervisor_id: str, comment: str = "") -> None:
        """Supervisor returns confusing task to sender (NFR-TSK-02)."""
        if comment.strip():
            self.clarification_notes.append(f"[SUPERVISOR NOTE]: {comment.strip()}")
        self.assignee = self.sender_id  # Return ownership back to sender
        self.status = TaskStatus.RETURNED
        self._logger.log_event("TASK_RETURNED", self.task_id, f"Returned to sender {self.sender_id} for clarification: {comment}", supervisor_id)

    def resubmit(self, updated_details: str, sender_id: str) -> None:
        """Sender refines and resubmits the returned task back to supervisor queue."""
        if sender_id != self.sender_id:
            raise PermissionError("Only the original sender can resubmit this task.")
        self.details = updated_details
        self.assignee = "SUPERVISOR"  # Route back to supervisor review queue
        self.status = TaskStatus.PENDING
        self._logger.log_event("TASK_RESUBMITTED", self.task_id, f"Resubmitted by {self.sender_id}.", self.sender_id)

    def add_note(self, comment: str, user_id: str) -> None:
        if comment.strip():
            self.clarification_notes.append(f"[{user_id}]: {comment.strip()}")

    def mark_complete(self, user_id: str) -> None:
        """Assignee marks task as completed (NFR-TSK-04)."""
        if user_id != self.assignee:
            raise PermissionError("Users can only complete tasks assigned directly to them.")
        self.status = TaskStatus.COMPLETED
        self._logger.log_event("TASK_COMPLETED", self.task_id, f"Task marked COMPLETED by {user_id}.", user_id)

    def __repr__(self) -> str:
        notes_count = len(self.clarification_notes)
        return (
            f"Task {self.task_id} [{self.status.value}] ({self.task_type.value}) "
            f"-> Owner/Assignee: {self.assignee} | Notes: {notes_count}"
        )
