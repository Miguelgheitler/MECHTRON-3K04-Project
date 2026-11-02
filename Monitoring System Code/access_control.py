"""
Module: Access Control
Responsibility: Manages user authorization
"""

from user_class import User, UserRole, load_user
import csv

activeUser = None

def login(userID: str, password: str):
    """
        Grants access upon input of correct userID and password.
    """
    fromFile = load_user(userID)
    if fromFile != None:
        if password == fromFile.password:
            print(f"Access Granted. Welcome, {fromFile.name} ({fromFile.role})")
            return fromFile
    print("Access Denied")
    return None
    #SAMPLE call: activeUser=login("N-001","pswdEvan")

def logout(activeUser: User):
    """
        Log out current user
    """
    if activeUser != None:
        print(f"Goodbye, {activeUser.name}")
        return None
    return None
    #SAMPLE call: activeUser=Logout(activeUser)

def check_authorization(activeUser: User, requiredRole: UserRole):
    """
        Authorizes the current user to perform an action restricted to certain role(s)
    """
    if activeUser is None:
        print("Login to perform this action")
        return False
    if activeUser.role is not requiredRole:
        print("Account not authorized for this action")
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
    ):
    """
        Creates a new profile. Hidden writing to .csv file with profile information.
    """
    with open("users.csv", mode = "a", newline = "", encoding = "utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([name,role.value,userID,password,smsNotifEnabled,emailNotifEnabled,appNotifEnabled])    
    return f"New profile created: {userID}"
    # SAMPLE hire()

    # hire(name="New User", role=UserRole.NURSE, userID="N-002", password="pswdNew", smsNotifEnabled=True, emailNotifEnabled=True, appNotifEnabled=False)

def retire(userID: str):
    """
        Deletes an existing profile.
    """
    rowsToKeep = []
    userFound = False
    with open("users.csv", mode="r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            if row[2].strip() == userID.strip(): # userID is in index 2 (name, role, userID, ...)
                userFound = True
            else:
                rowsToKeep.append(row)
    if not userFound:
        return f"User ID '{userID}' not found."

    # Overwrite the file with the remaining rows
    with open("users.csv", mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(rowsToKeep)
    return f"Profile retired: {userID}"

def modify_profile(
    userID: str,
    targetField: str,
    changedValue: str
    ):
    """
        Modifies profile details. Hidden reading/writing from/to .csv file.
    """
    rowsToKeep = []
    userFound = False
    with open("users.csv", mode="r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        header = next(reader, None)
        if targetField not in header:
            return f"{targetField} does not exist as a field in user profile"
        targetIndex = header.index(targetField)
        rowsToKeep.append(header)
        for row in reader:
            if row[2].strip() == userID.strip(): # userID is in index 2 (name, role, userID, ...)
                userFound = True
                row[targetIndex] = changedValue

                notifStates = [row[i].strip().lower() == "true" for i in (4, 5, 6)]
                if not any(notifStates):
                    return "Cannot disable all notification methods"
            rowsToKeep.append(row)
    if not userFound:
        return f"User ID '{userID}' not found."

    # Overwrite the file with the changed value
    with open("users.csv", mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(rowsToKeep)
    return f"{userID} Profile modified: {targetField} changed to {changedValue}"
