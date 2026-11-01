from user_class import User, UserRole, load_user

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
