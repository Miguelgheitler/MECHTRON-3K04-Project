"""
Module: User ADT (user_class.py)
Responsibility: Encapsulates user profile state, role definitions, and notification channel invariants, plus CSV deserialization for user lookup.
"""
from enum import Enum
from typing import Dict, Optional
import csv
import os


class UserRole(str, Enum):
    NURSE = "NURSE"
    PHARMACIST = "PHARMACIST"
    IT_ADMIN = "IT_ADMIN"
    SUPERVISOR = "SUPERVISOR"
    PROJECT_MANAGER = "PROJECT_MANAGER"


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
        # SAFETY INVARIANT: At least 1 notification method must be enabled
        if not (smsNotifEnabled or emailNotifEnabled or appNotifEnabled):
            raise ValueError("Safety Invariant Violation: At least one notification channel must be enabled.")

        self.name = name
        self.role = UserRole(role) if not isinstance(role, UserRole) else role
        self.userID = userID
        self.password = password

        self.prefAlarmChannel: Dict[str, bool] = {
            "sms": bool(smsNotifEnabled),
            "email": bool(emailNotifEnabled),
            "app": bool(appNotifEnabled)
        }

    def __repr__(self) -> str:
        return f"<User {self.userID}: {self.name} ({self.role.value}) | Notifs: {self.prefAlarmChannel}>"


def load_user(targetUserID: str) -> Optional[User]:
    """Pulls user from users.csv to validate login or lookup profile."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "users.csv")

    if not os.path.exists(csv_path):
        return None

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

                # Guarantee invariant even if CSV was manually edited
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

# from enum import Enum
# from typing import Dict
# import csv
# import os

# class UserRole(str, Enum):
#     NURSE = "NURSE"
#     PHARMACIST = "PHARMACIST"
#     IT_ADMIN = "IT_ADMIN"
#     SUPERVISOR = "SUPERVISOR"

# class User:
#     def __init__(
#         self,
#         name: str,
#         role: UserRole,
#         userID: str,
#         password: str,

#         smsNotifEnabled: bool,
#         emailNotifEnabled: bool,
#         appNotifEnabled: bool
#     ):

#         self.name = name
#         self.role = role
#         self.userID = userID
#         self.password = password

#         self.prefAlarmChannel: Dict[str, bool] = {
#             "sms": smsNotifEnabled,
#             "email": emailNotifEnabled,
#             "app": appNotifEnabled
#         }

# # SAMPLE OBJECT CREATION
# # nurse = User(
# #     name = "First Last",
# #     role = UserRole.NURSE,
# #     userID = "L-001",
# #     password = "abcd1234"

# #     smsNotifEnabled = True
# #     emailNotifEnabled = True
# #     appNotifEnabled = False
# # )

# def load_user(targetUserID: str): #pulls user from users.csv to validate login

#     current_dir = os.path.dirname(os.path.abspath(__file__))
#     csv_path = os.path.join(current_dir, "users.csv")


#     with open(csv_path, mode = "r", newline = "", encoding = "utf-8") as file:
#         reader = csv.DictReader(file)

#         for row in reader:
#             if row["userID"].strip() == targetUserID.strip():
#                 name = row["name"].strip()
#                 role = row["role"].strip()
#                 userID = row["userID"].strip()
#                 password = row["password"].strip()

#                 sms = row["smsNotifEnabled"].strip().lower() == "true"
#                 email = row["emailNotifEnabled"].strip().lower() == "true"
#                 app = row["appNotifEnabled"].strip().lower() == "true"

#                 return User(
#                     name = name,
#                     role = UserRole(role),
#                     userID = userID,
#                     password = password,

#                     smsNotifEnabled = sms,
#                     emailNotifEnabled = email,
#                     appNotifEnabled = app
#                 )
#     return None