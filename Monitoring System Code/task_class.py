"""
Module: Task ADT & Workflow (task_class.py)
Parnas Category: Behaviour Hiding / Abstract Data Type (ADT) Module
Responsibility: Represents clinical and routine hospital tasks, manages task lifecycle 
state transitions (PENDING, RETURNED, ASSIGNED, COMPLETED), enforces sender/assignee 
ownership guards, and maintains supervisor clarification notes.

Module Secret (Information Hiding):
Hides the internal task state machine transition logic, the automatic vs. manual 
delegation rules for routine vs. special tasks, and the internal list structure 
storing clarification notes.

State Invariants Preserved:
1. INV_TSK_1: Routine tasks (TaskType.ROUTINE) are auto-delegated immediately to 
   TaskStatus.ASSIGNED upon creation, whereas Special requests (TaskType.SPECIAL) 
   initialize as TaskStatus.PENDING in the Clinical Supervisor queue.
2. INV_TSK_2: Only the original sender (sender_id) may resubmit a returned task, and 
   only the current assignee (assignee) may mark a task COMPLETED.
"""

from enum import Enum
from datetime import datetime
from typing import Optional, List
from event_logger import EventLogger


# =========================================================================
# EXPORTED TYPES & ENUMERATIONS (Public Interface)
# =========================================================================

class TaskType(str, Enum):
    """Exported Enumeration distinguishing auto-delegated routine tasks from special requests."""
    ROUTINE = "ROUTINE"
    SPECIAL = "SPECIAL"


class TaskStatus(str, Enum):
    """Exported Enumeration representing the lifecycle states of a hospital task."""
    PENDING = "PENDING"
    RETURNED = "RETURNED"
    ASSIGNED = "ASSIGNED"
    COMPLETED = "COMPLETED"


# =========================================================================
# TASK ABSTRACT DATA TYPE & WORKFLOW (Public Interface & Hidden State)
# =========================================================================

class Task:
    """
    Hides internal task state representation, delegation rules, and note history list structure.
    """
    # IMPLEMENTATION SECRET: Internal audit logger reference for task lifecycle events
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
        """
        Public Interface Constructor for instantiating a Task ADT.

        Assumptions:
            Caller supplies valid userID strings for sender_id and assignee.
        Post-Condition (INV_TSK_1):
            - If task_type == TaskType.ROUTINE: self.status == TaskStatus.ASSIGNED
            - If task_type == TaskType.SPECIAL: self.status == TaskStatus.PENDING
            - Writes TASK_CREATED entry to system_audit_log.txt via EventLogger.
        """
        self.task_id = task_id
        self.sender_id = sender_id
        self.task_type = task_type
        self.details = details
        self.assignee = assignee  # Who currently owns/is assigned to this task
        self.timestamp = timestamp if timestamp is not None else datetime.now()

        # IMPLEMENTATION SECRET: Auto-delegation rule
        # Routine tasks auto-delegate to assignee; Special tasks start PENDING with supervisor
        self.status: TaskStatus = TaskStatus.ASSIGNED if task_type == TaskType.ROUTINE else TaskStatus.PENDING
        
        # IMPLEMENTATION SECRET: Internal list structure preserving chronological clarification notes
        self.clarification_notes: List[str] = clarification_notes if clarification_notes is not None else []

        self._logger.log_event(
            "TASK_CREATED",
            self.task_id,
            f"Task ({self.task_type.value}) created by {self.sender_id} -> Assignee: {self.assignee}. Details: {self.details}",
            self.sender_id
        )

    # =========================================================================
    # PUBLIC INTERFACE METHODS (Exported Operations)
    # =========================================================================

    def assign(self, employee_id: str, supervisor_id: str, comment: str = "") -> None:
        """
        Public Interface method for a Clinical Supervisor to assign a task to an employee.

        Effects:
            Updates self.assignee = employee_id, transitions self.status to TaskStatus.ASSIGNED,
            appends optional supervisor comment to self.clarification_notes, and logs TASK_ASSIGNED.
        """
        self.assignee = employee_id.strip()
        if comment.strip():
            self.clarification_notes.append(comment.strip())
        self.status = TaskStatus.ASSIGNED
        self._logger.log_event("TASK_ASSIGNED", self.task_id, f"Assigned to {self.assignee} by Supervisor {supervisor_id}.", supervisor_id)

    def return_for_clarification(self, supervisor_id: str, comment: str = "") -> None:
        """
        Public Interface method for a Clinical Supervisor to return an ambiguous request to its sender.

        Effects:
            Appends supervisor clarification prompt to self.clarification_notes, routes ownership 
            back to self.sender_id, sets self.status = TaskStatus.RETURNED, and logs TASK_RETURNED.
        """
        if comment.strip():
            self.clarification_notes.append(f"[SUPERVISOR NOTE]: {comment.strip()}")
        self.assignee = self.sender_id  # Return ownership back to sender
        self.status = TaskStatus.RETURNED
        self._logger.log_event("TASK_RETURNED", self.task_id, f"Returned to sender {self.sender_id} for clarification: {comment}", supervisor_id)

    def resubmit(self, updated_details: str, sender_id: str) -> None:
        """
        Public Interface method for the original sender to refine and resubmit a returned task.

        Pre-Condition (INV_TSK_2):
            sender_id == self.sender_id
        Post-Condition:
            Updates self.details, routes self.assignee back to 'SUPERVISOR', transitions 
            self.status to TaskStatus.PENDING, and logs TASK_RESUBMITTED.
        Exceptions:
            Raises PermissionError if called by a user other than self.sender_id.
        """
        if sender_id != self.sender_id:
            raise PermissionError("Only the original sender can resubmit this task.")
        self.details = updated_details
        self.assignee = "SUPERVISOR"  # Route back to supervisor review queue
        self.status = TaskStatus.PENDING
        self._logger.log_event("TASK_RESUBMITTED", self.task_id, f"Resubmitted by {self.sender_id}.", self.sender_id)

    def add_note(self, comment: str, user_id: str) -> None:
        """Public Interface method to append a timestamped/attributed progress note to the task."""
        if comment.strip():
            self.clarification_notes.append(f"[{user_id}]: {comment.strip()}")

    def mark_complete(self, user_id: str) -> None:
        """
        Public Interface method for the assigned employee to mark the task as completed.

        Pre-Condition (INV_TSK_2):
            user_id == self.assignee
        Post-Condition:
            Transitions self.status to TaskStatus.COMPLETED and writes TASK_COMPLETED 
            to system_audit_log.txt via EventLogger.
        Exceptions:
            Raises PermissionError if user_id != self.assignee.
        """
        if user_id != self.assignee:
            raise PermissionError("Users can only complete tasks assigned directly to them.")
        self.status = TaskStatus.COMPLETED
        self._logger.log_event("TASK_COMPLETED", self.task_id, f"Task marked COMPLETED by {user_id}.", user_id)

    def __repr__(self) -> str:
        """Clean string summary of the Task ADT state, owner, and note count."""
        notes_count = len(self.clarification_notes)
        return (
            f"Task {self.task_id} [{self.status.value}] ({self.task_type.value}) "
            f"-> Owner/Assignee: {self.assignee} | Notes: {notes_count}"
        )


# =============================================================================
# TERMINAL COPY-PASTE TEST INSTRUCTIONS (Interactive Python Shell)
# =============================================================================
# Open your terminal inside your code directory, type `python3`, then paste:
#
#   from task_class import Task, TaskType
#
#   # 1. Create a Special Medication Request (Starts PENDING with SUPERVISOR - INV_TSK_1)
#   t1 = Task("TSK-101", sender_id="E-001", task_type=TaskType.SPECIAL, details="Need Morphine in ADC-03")
#   print(t1)
#
#   # 2. Supervisor returns task for clarification
#   t1.return_for_clarification(supervisor_id="S-001", comment="Please specify dosage required.")
#   print(t1, t1.clarification_notes)
#
#   # 3. Sender clarifies and resubmits, then Supervisor assigns to Pharmacist
#   t1.resubmit("Need Morphine 10mg in ADC-03", sender_id="E-001")
#   t1.assign(employee_id="G-001", supervisor_id="S-001", comment="Approved for restock.")
#   print(t1)
#
#   # 4. Assignee completes task (INV_TSK_2)
#   t1.mark_complete(user_id="G-001")
#   print(t1)