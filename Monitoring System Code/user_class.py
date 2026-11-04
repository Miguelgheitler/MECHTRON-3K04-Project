"""
Module: User ADT (user_class.py)
Parnas Category: Software Decision / Abstract Data Type (ADT) Module
Responsibility: Represents an authorized hospital employee's profile, including name, 
login credentials, role enumeration, and notification channel settings, plus CSV 
deserialization for user lookup.

Module Secret (Information Hiding):
Hides the role enumeration mapping, the internal dictionary data structure storing 
notification preferences (prefAlarmChannel), and the CSV row-to-object parsing logic.

State Invariant:
INV_USER_1: (user.prefAlarmChannel["sms"] v user.prefAlarmChannel["email"] v 
             user.prefAlarmChannel["app"]) == True
(A User object can never exist with all three notification channels muted).
"""

from enum import Enum
from typing import Dict, Optional
import csv
import os


# =========================================================================
# EXPORTED TYPES & ENUMERATIONS (Public Interface)
# =========================================================================

class UserRole(str, Enum):
    """
    Exported Enumeration representing the 4 valid hospital system actors.
    Inherits from str and Enum for type safety and seamless CSV serialization.
    """
    NURSE = "NURSE"
    PHARMACIST = "PHARMACIST"
    IT_ADMIN = "IT_ADMIN"
    SUPERVISOR = "SUPERVISOR"


# =========================================================================
# USER ABSTRACT DATA TYPE (Public Interface & Hidden State)
# =========================================================================

class User:
    """
    Hides the internal representation of user credentials and notification preference structures.
    State Invariant: At least one notification channel in prefAlarmChannel must be True at all times (US-ALM-02 / NFR-UIF-03).
    """
    def __init__(
        self,
        name: str,
        role: UserRole,
        userID: str,
        password: str,
        smsNotifEnabled: bool = True,
        emailNotifEnabled: bool = True,
        appNotifEnabled: bool = True
    ):
        """
        Public Interface Constructor for instantiating a User ADT.

        Assumptions:
            role passed to constructor is a valid UserRole enum or valid role string.
        Pre-Condition:
            (smsNotifEnabled v emailNotifEnabled v appNotifEnabled) == True
        Post-Condition:
            Initializes User attributes and establishes State Invariant INV_USER_1.
        Exceptions:
            Raises ValueError on construction if all three notification channels are False.
        """
        # SAFETY INVARIANT (INV_USER_1): At least 1 notification method must be enabled at creation
        if not (smsNotifEnabled or emailNotifEnabled or appNotifEnabled):
            raise ValueError("Safety Invariant Violation: At least one notification channel must be enabled.")

        self.name = name
        self.role = UserRole(role) if not isinstance(role, UserRole) else role
        self.userID = userID
        self.password = password

        # IMPLEMENTATION SECRET: Internal dictionary mapping notification avenues to booleans.
        # Hides how notification preferences are structured in memory from external callers.
        self.prefAlarmChannel: Dict[str, bool] = {
            "sms": bool(smsNotifEnabled),
            "email": bool(emailNotifEnabled),
            "app": bool(appNotifEnabled)
        }

    def __repr__(self) -> str:
        """Clean string representation of the User ADT for terminal inspection."""
        return f"<User {self.userID}: {self.name} ({self.role.value}) | Notifs: {self.prefAlarmChannel}>"


# =========================================================================
# PERSISTENCE DESERIALIZATION HELPER (Information Hiding Boundary)
# =========================================================================

def load_user(targetUserID: str) -> Optional[User]:
    """
    Public Interface helper that scans users.csv for targetUserID and returns a populated 
    User instance, or None if not found.

    HIDDEN IMPLEMENTATION:
    Encapsulates all CSV file path resolution, DictReader iteration, whitespace stripping,
    and string-to-boolean / string-to-UserRole type conversions.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "users.csv")

    if not os.path.exists(csv_path):
        return None

    # HIDDEN IMPLEMENTATION: Parse raw CSV strings into typed Python variables
    with open(csv_path, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row and row["userID"].strip() == targetUserID.strip():
                name = row["name"].strip()
                role = row["role"].strip()
                userID = row["userID"].strip()
                password = row["password"].strip()

                sms = row["smsNotifEnabled"].strip().lower() == "true"
                email = row["emailNotifEnabled"].strip().lower() == "true"
                app = row["appNotifEnabled"].strip().lower() == "true"

                # Guarantee State Invariant INV_USER_1 even if CSV was manually edited
                if not (sms or email or app):
                    app = True

                return User(
                    name=name,
                    role=UserRole(role),
                    userID=userID,
                    password=password,
                    smsNotifEnabled=sms,
                    emailNotifEnabled=email,
                    appNotifEnabled=app
                )
    return None


# =============================================================================
# TERMINAL COPY-PASTE TEST INSTRUCTIONS (Interactive Python Shell)
# =============================================================================
# Open your terminal inside your code directory, type `python3`, then paste:
#
#   from user_class import User, UserRole, load_user
#
#   # 1. Test valid User ADT creation
#   u1 = User("Sarah Jenkins", UserRole.NURSE, "N-101", "pass123", True, False, True)
#   print(u1)
#
#   # 2. Test Safety Invariant Enforcement (Should raise ValueError)
#   try:
#       bad_user = User("Bad Config", UserRole.NURSE, "N-999", "pass", False, False, False)
#   except ValueError as e:
#       print(f"Caught expected safety violation: {e}")
#
#   # 3. Test CSV Deserialization via load_user()
#   loaded = load_user("E-001")
#   print(loaded)