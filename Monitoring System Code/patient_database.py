"""
Module: Patient Information Database (PID)
Responsibility: Stores patient profiles and medication schedules, enforces PII scrubbing 
(anonymization) for external requests, and links historical dispensing to specific patients.
"""

import os
from event_logger import EventLogger

class PatientDatabase:
    """
    Hides the storage mechanism for patient data (local text file) and ensures 
    strict adherence to privacy and anonymization requirements (FR-PID-02).
    """
    def __init__(self, filepath: str = "patient_records.txt", logger: EventLogger = None):
        self._filepath = filepath
        self._logger = logger if logger else EventLogger()
        self._patients = {} # Cache: { patient_id: { "name": str, "schedule": str } }
        
        if not os.path.exists(self._filepath):
            self._write_default_storage()
        self._load_from_storage()

    def _write_default_storage(self) -> None:
        """HIDDEN: Creates the initial file layout."""
        header = (
            "==================================================================\n"
            "                 PATIENT INFORMATION DATABASE (PID)               \n"
            "             WARNING: CONTAINS PROTECTED HEALTH INFO              \n"
            "==================================================================\n"
            "PATIENT_ID | NAME | MEDICATION_SCHEDULE\n"
            "------------------------------------------------------------------\n"
        )
        with open(self._filepath, "w", encoding="utf-8") as f:
            f.write(header)

    def _load_from_storage(self) -> None:
        """HIDDEN: Parses the text file into memory."""
        if not os.path.exists(self._filepath): return
        with open(self._filepath, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str or line_str.startswith("=") or line_str.startswith("-") or line_str.startswith("PATIENT_ID"):
                    continue
                parts = [p.strip() for p in line_str.split("|")]
                if len(parts) >= 3:
                    self._patients[parts[0]] = {"name": parts[1], "schedule": parts[2]}

    def _sync_to_storage(self) -> None:
        """HIDDEN: Saves current memory cache to the text file."""
        header = (
            "==================================================================\n"
            "                 PATIENT INFORMATION DATABASE (PID)               \n"
            "             WARNING: CONTAINS PROTECTED HEALTH INFO              \n"
            "==================================================================\n"
            "PATIENT_ID | NAME | MEDICATION_SCHEDULE\n"
            "------------------------------------------------------------------\n"
        )
        lines = [header]
        for pid, data in sorted(self._patients.items()):
            lines.append(f"{pid} | {data['name']} | {data['schedule']}\n")
            
        with open(self._filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)

    # =========================================================================
    # PUBLIC INTERFACE
    # =========================================================================

    def add_patient(self, patient_id: str, name: str, schedule: str, operator_id: str) -> None:
        """Adds a new patient to the database."""
        if patient_id in self._patients:
            print(f"[PID ERROR] Patient ID {patient_id} already exists.")
            return
            
        self._patients[patient_id] = {"name": name, "schedule": schedule}
        self._sync_to_storage()
        print(f"[PID SUCCESS] Patient {patient_id} added successfully.")
        self._logger.log_event("PID_UPDATE", "PID", f"New patient profile created: {patient_id}", operator_id)

    def get_patient_full(self, patient_id: str, operator_id: str) -> dict:
        """
        Securely retrieves a patient's FULL profile. 
        Logs this access for auditability (FR-PID-03 / NFR-PID-03).
        """
        if patient_id not in self._patients:
            print(f"[PID ERROR] Patient ID {patient_id} not found.")
            return None
            
        # Audit log for ethical privacy tracking
        self._logger.log_event("PID_ACCESS", "PID", f"Full profile accessed for {patient_id}", operator_id)
        return self._patients[patient_id]

    def get_anonymized_schedule(self, patient_id: str) -> str:
        """
        FR-PID-02: Scrubs Personally Identifiable Information (PII).
        Returns ONLY the schedule, stripping the patient's name entirely.
        """
        if patient_id not in self._patients:
            return "Patient not found."
            
        schedule = self._patients[patient_id]["schedule"]
        return f"[ANONYMIZED] Medication required: {schedule}"