from user_class import User, UserRole

import csv

def load_user(targetUserID: str):
    with open("users.csv", mode = "r", newline = "", encoding = "utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row["userID"].strip() == targetUserID.strip():
                name = row["name"].strip()
                role = row["role"].strip()
                userID = row["userID"].strip()
                password = row["password"].strip()

                return User(
                    name = name,
                    role = UserRole(role),
                    userID = userID,
                    password = password
                )
    return None