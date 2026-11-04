"""
Module: Access Control (access_control.py)
Responsibility: Manages user authentication, role-based authorization, 2-minute inactivity session timeouts, and user profile/notification persistence in users.csv.
"""
from user_class import User, UserRole, load_user
from event_logger import EventLogger
from datetime import datetime
from typing import Optional
import csv
import os

_logger = EventLogger("system_audit_log.txt")
_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.csv")

activeUser: Optional[User] = None
lastActivityTime: Optional[datetime] = None
SESSION_TIMEOUT_SECONDS = 120  # 2 minutes (FR-ADM-05, NFR-UIF-02)


def login(userID: str, password: str) -> Optional[User]:
    """
    SP-ADM-04 (Traces to FR-ADM-03, FR-ADM-06, FR-LOG-01, NFR-LOG-01..04, NFR-ADM-03):
    Grants access upon input of correct userID and password.
    Logs all login attempts and flags failed attempts FOR_REVIEW.
    """
    global activeUser, lastActivityTime
    fromFile = load_user(userID)

    if fromFile is not None:
        if password == fromFile.password:
            activeUser = fromFile
            lastActivityTime = datetime.now()
            print(f"Access Granted. Welcome, {fromFile.name} ({fromFile.role.value})")
            return fromFile
        else:
            # Failed login: wrong password (NFR-LOG-02, NFR-LOG-03, NFR-ADM-03)
            _logger.log_event(
                "SECURITY_REVIEW",
                "AUTH",
                f"FOR_REVIEW: Failed login for User '{userID}' - Reason: Incorrect password.",
                userID
            )
            print("Credentials invalid")
            return None

    # Failed login: non-existent user ID
    _logger.log_event(
        "SECURITY_REVIEW",
        "AUTH",
        f"FOR_REVIEW: Suspicious failed login - Reason: Unknown User ID '{userID}'.",
        userID
    )
    print("Credentials invalid")
    return None


def logout(current_user: Optional[User]) -> None:
    """SP-ADM-03: Terminates the current user session."""
    global activeUser, lastActivityTime
    if current_user is not None:
        print(f"Goodbye, {current_user.name}")
    activeUser = None
    lastActivityTime = None
    return None


def check_session_timeout(current_user: Optional[User]) -> bool:
    """
    SP-ADM-05 / SP-UI-03 (Traces to FR-ADM-05, NFR-UIF-02):
    Safety-critical inactivity monitor. Returns True if session timed out (>120s),
    otherwise resets the inactivity timer and returns False.
    """
    global lastActivityTime
    if current_user is None or lastActivityTime is None:
        return False

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

    # Reset timer on valid activity
    lastActivityTime = datetime.now()
    return False


def check_authorization(current_user: Optional[User], requiredRole: UserRole) -> bool:
    """
    Safety-critical RBAC gatekeeper (Traces to FR-PID-04, NFR-INV-02, FR-REQ-01).
    Authorizes the current user to perform an action restricted to requiredRole.
    """
    if current_user is None:
        # print("Login to perform this action")
        return False
    if current_user.role != requiredRole:
        # print("Account not authorized for this action")
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
    SP-ADM-01 (Traces to FR-ADM-01, NFR-ADM-01, NFR-ALM-05):
    Creates a new user profile in users.csv after validating completeness and invariants.
    """
    if not (name.strip() and userID.strip() and password.strip()):
        _logger.log_event("ADMIN_ALERT", "AUTH", f"Incomplete user profile creation blocked for '{userID}'.", "IT_ADMIN")
        return "Error: Incomplete user profile information (NFR-ALM-05)."

    if load_user(userID) is not None:
        return f"Error: User ID '{userID}' already exists."

    if not (smsNotifEnabled or emailNotifEnabled or appNotifEnabled):
        appNotifEnabled = True  # Enforce safety invariant

    role_val = role.value if hasattr(role, "value") else str(role)
    with open(_CSV_PATH, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([name.strip(), role_val, userID.strip(), password.strip(), smsNotifEnabled, emailNotifEnabled, appNotifEnabled])

    _logger.log_event("USER_CREATED", "AUTH", f"Created profile for {name} ({role_val}).", userID)
    return f"New profile created: {userID}"


def retire(userID: str) -> str:
    """SP-ADM-01 (Traces to FR-ADM-01): Deletes an existing user profile from users.csv."""
    rowsToKeep = []
    userFound = False

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

    with open(_CSV_PATH, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(rowsToKeep)

    _logger.log_event("USER_RETIRED", "AUTH", f"Retired profile {userID}.", "IT_ADMIN")
    return f"Profile retired: {userID}"


def modify_profile(userID: str, targetField: str, changedValue: str) -> str:
    """
    SP-ADM-02 & SP-ALM-04 (Traces to FR-ADM-02, FR-ALM-04, FR-DSH-03, US-ALM-02, NFR-UIF-03):
    Modifies profile details and alarm notification settings in users.csv while preserving
    the safety invariant that at least 1 notification channel remains enabled.
    """
    rowsToKeep = []
    userFound = False

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

                # Safety Invariant Check (SP-ALM-04): At least 1 notification channel must remain True
                notifStates = [row[i].strip().lower() == "true" for i in (4, 5, 6)]
                if not any(notifStates):
                    return "Cannot disable all notification methods"
            rowsToKeep.append(row)

    if not userFound:
        return f"User ID '{userID}' not found."

    with open(_CSV_PATH, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(rowsToKeep)

    _logger.log_event("USER_MODIFIED", "AUTH", f"Modified {userID}: set {targetField} = {changedValue}.", userID)
    return f"{userID} Profile modified: {targetField} changed to {changedValue}"
