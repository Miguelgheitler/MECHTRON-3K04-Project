"""
Module: Access Control (access_control.py)
Parnas Category: Software Decision / Behaviour Hiding Module
Responsibility: Authenticates users, enforces role-based permissions, tracks 2-minute 
inactivity timeouts, and manages persistent user profile/notification records in users.csv.

Module Secret (Information Hiding):
Hides the credential verification logic, the session inactivity timeout counter 
implementation, and the underlying CSV file structure/I/O used for storing user records.

State Invariants Preserved:
1. INV_AUTH_1: executeCmd(currentUser, cmd) => (currentUser != None) ^ 
   (currentUser.role == requiredRole(cmd)) ^ (idleTime <= 120s)
   (Commands can only be executed by an authorized user who is logged in and not timed-out).
2. INV_AUTH_2: Every invocation of login(), successful or not, produces a corresponding 
   audit log entry in system_audit_log.txt.
3. INV_USER_1: (user.alarmChannel[sms] v user.alarmChannel[email] v user.alarmChannel[app]) = True
   (A user can never mute all notification channels).
"""

from user_class import User, UserRole, load_user
from event_logger import EventLogger
from datetime import datetime
from typing import Optional
import csv
import os

# =========================================================================
# HIDDEN IMPLEMENTATION DETAILS & MODULE STATE (Information Hiding)
# =========================================================================
# IMPLEMENTATION SECRET: Internal audit logger instance and persistent CSV file path.
# If the hospital transitions from users.csv to an SQL database, only this module 
# and load_user() change; external modules (system_shell.py) remain untouched.
_logger = EventLogger("system_audit_log.txt")
_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.csv")

# IMPLEMENTATION SECRET: Internal session tracking state variables and timeout constant.
activeUser: Optional[User] = None
lastActivityTime: Optional[datetime] = None
SESSION_TIMEOUT_SECONDS = 120  # 2 minutes


# =========================================================================
# PUBLIC INTERFACE (What other modules are allowed to call)
# =========================================================================

def login(userID: str, password: str) -> Optional[User]:
    """
    Public Interface method to authenticate a hospital employee.

    Pre-Condition:
        currentUser == None ^ type(userID) == String ^ type(password) == String
    Post-Condition:
        - If user exists in users.csv and password == user.password:
          result == user ^ logged("SECURITY") ^ lastActivityTime == t_now
        - Otherwise (unknown userID or mismatched password):
          result == None ^ logged("SECURITY_REVIEW")
    Effects:
        Updates module-level activeUser and lastActivityTime on success; writes 
        audit entry to system_audit_log.txt via EventLogger.
    Exceptions:
        Never halts the system; invalid credentials return None and print "Credentials invalid".
    """
    global activeUser, lastActivityTime
    
    # HIDDEN IMPLEMENTATION: Delegate CSV lookup to User ADT helper
    fromFile = load_user(userID)

    if fromFile is not None:
        # IMPLEMENTATION SECRET: Credential comparison logic
        if password == fromFile.password:
            activeUser = fromFile
            lastActivityTime = datetime.now()
            print(f"Access Granted. Welcome, {fromFile.name} ({fromFile.role.value})")
            return fromFile
        else:
            # Failed login: wrong password
            # Preserves Invariant INV_AUTH_2 (all login attempts are logged)
            _logger.log_event(
                "SECURITY_REVIEW",
                "AUTH",
                f"FOR_REVIEW: Failed login for User '{userID}' - Reason: Incorrect password.",
                userID
            )
            print("Credentials invalid")
            return None

    # Failed login: non-existent user ID (flagged as suspicious FOR_REVIEW)
    _logger.log_event(
        "SECURITY_REVIEW",
        "AUTH",
        f"FOR_REVIEW: Suspicious failed login - Reason: Unknown User ID '{userID}'.",
        userID
    )
    print("Credentials invalid")
    return None


def logout(current_user: Optional[User]) -> None:
    """
    Public Interface method to terminate the current active user session.

    Semantics:
        Clears the active session state (activeUser and lastActivityTime) and returns None.
    """
    global activeUser, lastActivityTime
    if current_user is not None:
        print(f"Goodbye, {current_user.name}")
    activeUser = None
    lastActivityTime = None
    return None


def check_session_timeout(current_user: Optional[User]) -> bool:
    """
    Public Interface safety-critical inactivity monitor.

    Semantics (4-Variable Model):
        - Monitored (M): User activity / unattended terminal duration.
        - Input (I): Elapsed seconds (datetime.now() - lastActivityTime).total_seconds().
        - Output (O): Boolean (True if timed out > 120s, False otherwise).
        - Controlled (C): Employee's ability to execute system commands.
    Effects:
        If elapsed > 120s, logs SESSION_TIMEOUT to EventLogger and returns True.
        If elapsed <= 120s, resets lastActivityTime to datetime.now() and returns False.
    """
    global lastActivityTime
    if current_user is None or lastActivityTime is None:
        return False

    # IMPLEMENTATION SECRET: Elapsed inactivity calculation
    elapsed = (datetime.now() - lastActivityTime).total_seconds()
    if elapsed > SESSION_TIMEOUT_SECONDS:
        _logger.log_event(
            "SESSION_TIMEOUT",
            "AUTH",
            f"Session auto-locked after {int(elapsed)}s of inactivity (>120s threshold).",
            current_user.userID
        )
        print("[SECURITY TIMEOUT] Session locked due to 2 minutes of inactivity. Please re-authenticate.")
        return True

    # Reset inactivity timer on valid activity within the 120-second window
    lastActivityTime = datetime.now()
    return False


def check_authorization(current_user: Optional[User], requiredRole: UserRole) -> bool:
    """
    Public Interface safety-critical Role-Based Access Control (RBAC) gatekeeper.

    Semantics:
        Enforces State Invariant INV_AUTH_1 by verifying that current_user != None 
        and current_user.role == requiredRole before restricted operations execute.
    """
    if current_user is None:
        return False
    if current_user.role != requiredRole:
        return False
    return True


def hire(
    name: str,
    role: UserRole,
    userID: str,
    password: str,
    smsNotifEnabled: bool,
    emailNotifEnabled: bool,
    appNotifEnabled: bool
) -> str:
    """
    Public Interface method to create and persist a new employee profile.

    Assumptions:
        Caller (system_shell.py) has verified IT_ADMIN authorization via check_authorization().
    Semantics & Invariants:
        1. Rejects incomplete profiles and duplicate userIDs.
        2. Enforces Safety Invariant INV_USER_1: if all notification channels are False,
           automatically enables appNotifEnabled = True.
        3. Appends the serialized user record to users.csv and logs USER_CREATED.
    """
    # Validate profile completeness
    if not (name.strip() and userID.strip() and password.strip()):
        _logger.log_event("ADMIN_ALERT", "AUTH", f"Incomplete user profile creation blocked for '{userID}'.", "IT_ADMIN")
        return "Error: Incomplete user profile information (NFR-ALM-05)."

    # Prevent duplicate primary keys in users.csv
    if load_user(userID) is not None:
        return f"Error: User ID '{userID}' already exists."

    # SAFETY INVARIANT (INV_USER_1): User can never mute all notification channels
    if not (smsNotifEnabled or emailNotifEnabled or appNotifEnabled):
        appNotifEnabled = True  # Enforce safety invariant

    # HIDDEN IMPLEMENTATION: CSV row serialization and file append
    role_val = role.value if hasattr(role, "value") else str(role)
    with open(_CSV_PATH, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([name.strip(), role_val, userID.strip(), password.strip(), smsNotifEnabled, emailNotifEnabled, appNotifEnabled])

    _logger.log_event("USER_CREATED", "AUTH", f"Created profile for {name} ({role_val}).", userID)
    return f"New profile created: {userID}"


def retire(userID: str) -> str:
    """
    Public Interface method to delete an existing user profile from persistent storage.

    Assumptions:
        Caller (system_shell.py) has verified IT_ADMIN authorization via check_authorization().
    Effects:
        Filters out the row matching userID, rewrites users.csv preserving the header,
        and logs USER_RETIRED to system_audit_log.txt.
    """
    rowsToKeep = []
    userFound = False

    # HIDDEN IMPLEMENTATION: Read CSV and filter out the target userID (index 2)
    with open(_CSV_PATH, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            if not row:
                continue
            if row[2].strip() == userID.strip():
                userFound = True
            else:
                rowsToKeep.append(row)

    if not userFound:
        return f"User ID '{userID}' not found."

    # HIDDEN IMPLEMENTATION: Atomic rewrite of users.csv with remaining records
    with open(_CSV_PATH, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(rowsToKeep)

    _logger.log_event("USER_RETIRED", "AUTH", f"Retired profile {userID}.", "IT_ADMIN")
    return f"Profile retired: {userID}"


def modify_profile(userID: str, targetField: str, changedValue: str) -> str:
    """
    Public Interface method to modify user profile attributes or alarm notification preferences.

    State Invariant Preserved (INV_USER_1):
        (user.alarmChannel[sms] v user.alarmChannel[email] v user.alarmChannel[app]) = True
    Pre-Condition:
        targetField in users.csv header ^ userID exists in users.csv
    Post-Condition:
        - If disabling a notification channel results in sum(alarmChannel) == 0:
          No change is written to users.csv; returns "Cannot disable all notification methods".
        - Otherwise:
          Updates targetField to changedValue in users.csv and logs USER_MODIFIED.
    """
    rowsToKeep = []
    userFound = False

    # HIDDEN IMPLEMENTATION: Locate target column index from CSV header and update matching row
    with open(_CSV_PATH, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        header = next(reader, None)
        if header is None:
            return "Error: users.csv is empty."

        clean_header = [h.strip() for h in header]
        if targetField.strip() not in clean_header:
            return f"{targetField} does not exist as a field in user profile"

        targetIndex = clean_header.index(targetField.strip())
        rowsToKeep.append(header)

        for row in reader:
            if not row:
                continue
            if row[2].strip() == userID.strip():
                userFound = True
                row[targetIndex] = str(changedValue).strip()

                # Safety Invariant Check (INV_USER_1):
                # Inspect columns 4, 5, 6 (smsNotifEnabled, emailNotifEnabled, appNotifEnabled)
                notifStates = [row[i].strip().lower() == "true" for i in (4, 5, 6)]
                if not any(notifStates):
                    return "Cannot disable all notification methods"
            rowsToKeep.append(row)

    if not userFound:
        return f"User ID '{userID}' not found."

    # HIDDEN IMPLEMENTATION: Flush updated rows back to users.csv
    with open(_CSV_PATH, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(rowsToKeep)

    _logger.log_event("USER_MODIFIED", "AUTH", f"Modified {userID}: set {targetField} = {changedValue}.", userID)
    return f"{userID} Profile modified: {targetField} changed to {changedValue}"


# =============================================================================
# TERMINAL COPY-PASTE TEST INSTRUCTIONS (Interactive Python Shell)
# =============================================================================
# Open your terminal inside your code directory, type `python3`, then paste:
#
#   import access_control
#   from user_class import UserRole
#
#   # 1. Test Failed Login (Triggers SECURITY_REVIEW log entry - INV_AUTH_2)
#   access_control.login("E-001", "wrongPassword")
#
#   # 2. Test Valid Login & RBAC Authorization Check (INV_AUTH_1)
#   user = access_control.login("E-001", "pswdEvan")
#   access_control.check_authorization(user, UserRole.IT_ADMIN)  # False for NURSE
#
#   # 3. Test Notification Safety Invariant (INV_USER_1)
#   # Attempting to turn off the last remaining active channel is rejected
#   access_control.modify_profile("S-001", "appNotifEnabled", "False")