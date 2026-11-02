"""
Module: Event Logger (Historical Data & Storage)
Responsibility: Persists system events, alarms, maintenance orders, and user actions 
into an immutable local text-based audit trail with precise timestamps.
"""

from datetime import datetime
from typing import Optional, List
import os

class EventLogger:
    """
    Hides the storage mechanism (e.g., local file I/O formatting, file paths, 
    and write-once append routines) from the rest of the application.
    """
    def __init__(self, log_filepath: str = "system_audit_log.txt"):
        # IMPLEMENTATION SECRET: The file path and storage medium structure 
        self._log_filepath = log_filepath
        
        # Ensure log file exists on initialization with professional title & subtitle
        if not os.path.exists(self._log_filepath):
            self._write_header()

    def _write_header(self) -> None:
        """HIDDEN IMPLEMENTATION: Writes the professional title header and vague subtitle."""
        header = (
            "==================================================================\n"
            "             CENTRALIZED HOSPITAL AUDIT LOGGER & EVENT TRAIL     \n"
            "                 Hospital ABC - City, Province/State             \n"
            "==================================================================\n"
            "TIMESTAMP                   | LOG_TYPE   | SOURCE     | USER       | DETAILS\n"
            "--------------------------------------------------------------------------------\n"
        )
        with open(self._log_filepath, "w", encoding="utf-8") as f:
            f.write(header)

    # =========================================================================
    # PUBLIC INTERFACE (What other modules are allowed to call)
    # =========================================================================

    def log_event(self, event_type: str, source_id: str, description: str, user_id: Optional[str] = None) -> None:
        """
        Public Interface method called by Alarm Manager, Task Manager, Access Control, 
        or Inventory Supervision when an auditable event occurs.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] # Millisecond precision
        user_str = f" | User: {user_id}" if user_id else " | User: System"
        
        log_entry = f"[{timestamp}] [{event_type.upper()}] | Source: {source_id}{user_str} | Details: {description}\n"
        
        self._append_to_storage(log_entry)
        
        # Terminal notification print statement
        print(f"[LOG NOTIFICATION] An event from source '{source_id}' of type '{event_type.upper()}' has been logged.")

    def read_logs(self) -> None:
        """
        Public Interface method to open, retrieve, and automatically print 
        all log entries cleanly to the terminal without raw list formatting or \n.
        """
        if not os.path.exists(self._log_filepath):
            print("Log file is empty or missing.")
            return
            
        with open(self._log_filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Check if any actual event records exist (lines starting with '[')
        event_lines = [line for line in lines if line.strip().startswith("[")]

        print("\n" + "="*60)
        # Print the header lines cleanly without trailing newlines
        for line in lines:
            if not line.strip().startswith("["):
                # Avoid printing extra blank lines if they exist in header blocks
                if line.strip():
                    print(line.strip())

        # If no events exist, show the clean professional empty message
        if not event_lines:
            print("\nNo logs in audit trail.")
        else:
            print() # Spacer
            # Print actual event lines cleanly
            for line in event_lines:
                print(line.strip())
        print("="*60 + "\n")

    def clear_logs(self) -> None:
        """
        Public Interface method to clear/reset the audit log back to the initial header state.
        """
        self._write_header()
        
        # Terminal confirmation print statement
        print("[LOG NOTIFICATION] Logs have been cleared.")

    # =========================================================================
    # HIDDEN IMPLEMENTATION DETAILS (Information Hiding Boundaries)
    # =========================================================================

    def _append_to_storage(self, formatted_entry: str) -> None:
        """
        HIDDEN IMPLEMENTATION: Low-level file I/O operations. 
        If the team transitions from a local .txt file to a cloud database (like PostgreSQL) 
        for Deliverable 3 or production, ONLY this method and initialization change. 
        The public interface parameters remain identical.
        """
        try:
            with open(self._log_filepath, "a", encoding="utf-8") as f:
                f.write(formatted_entry)
        except IOError as e:
            print(f"CRITICAL STORAGE ERROR: Could not write log entry. Details: {e}")


# =============================================================================
# TERMINAL COPY-PASTE TEST INSTRUCTIONS (Interactive Python Shell)
# =============================================================================
# Open your terminal inside "Monitoring System Code", type `python3`, then copy and paste:
#
#   from event_logger import EventLogger
#   logger = EventLogger("system_audit_log.txt")
#   
#   # 1. Read fresh log file (shows header and "No logs in audit trail.")
#   for line in logger.read_logs():
#       print(line.strip())
#   
#   # 2. Log an event (prints notification and removes the "No logs" message)
#   logger.log_event("ALARM", "ADC-01", "Drawer 2 jammed", "NURSE-01")
#   
#   # 3. Read log file again (shows header + real event log)
#   for line in logger.read_logs():
#       print(line.strip())
#   
#   # 4. Clear logs (resets back to header and brings back "No logs in audit trail.")
#   logger.clear_logs()
#   
#   # 5. Verify via read_logs()
#   for line in logger.read_logs():
#       print(line.strip())
# =============================================================================