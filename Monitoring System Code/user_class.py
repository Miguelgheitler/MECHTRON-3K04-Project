from enum import Enum
from typing import Dict
import csv
import os

class UserRole(str, Enum):
    NURSE = "NURSE"
    PHARMACIST = "PHARMACIST"
    IT_ADMIN = "IT_ADMIN"
    SUPERVISOR = "SUPERVISOR"

class User:
    def __init__(
        self,
        name: str,
        role: UserRole,
        userID: str,
        password: str,

        smsNotifEnabled: bool,
        emailNotifEnabled: bool,
        appNotifEnabled: bool
    ):

        self.name = name
        self.role = role
        self.userID = userID
        self.password = password

        self.prefAlarmChannel: Dict[str, bool] = {
            "sms": smsNotifEnabled,
            "email": emailNotifEnabled,
            "app": appNotifEnabled
        }

# SAMPLE OBJECT CREATION
# nurse = User(
#     name = "First Last",
#     role = UserRole.NURSE,
#     userID = "L-001",
#     password = "abcd1234"

#     smsNotifEnabled = True
#     emailNotifEnabled = True
#     appNotifEnabled = False
# )

def load_user(targetUserID: str): #pulls user from users.csv to validate login

    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "users.csv")


    with open(csv_path, mode = "r", newline = "", encoding = "utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row["userID"].strip() == targetUserID.strip():
                name = row["name"].strip()
                role = row["role"].strip()
                userID = row["userID"].strip()
                password = row["password"].strip()

                sms = row["smsNotifEnabled"].strip().lower() == "true"
                email = row["emailNotifEnabled"].strip().lower() == "true"
                app = row["appNotifEnabled"].strip().lower() == "true"

                return User(
                    name = name,
                    role = UserRole(role),
                    userID = userID,
                    password = password,

                    smsNotifEnabled = sms,
                    emailNotifEnabled = email,
                    appNotifEnabled = app
                )
    return None