from enum import Enum
from typing import Dict

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