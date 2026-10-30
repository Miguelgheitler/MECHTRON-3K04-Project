from user_class import User, UserRole

import csv

def login(userID: str, password: str):
    fromFile = load_user(userID)
    if fromFile != None:
        if password == fromFile.password:
            print(f"Access Granted. Welcome, {fromFile.name} ({fromFile.role})")
            return fromFile
    print("Access Denied")
    return None
    #SAMPLE call: activeUser=login("E-001","pswdEvan")

def logout(activeUser: User):
    if activeUser != None:
        print(f"Goodbye, {activeUser.name}")
        return None
    return None
    #SAMPLE call: activeUser=Logout(activeUser)

def load_user(targetUserID: str): #pulls user from users.csv to validate login
    with open("users.csv", mode = "r", newline = "", encoding = "utf-8") as file:
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

