

def run_terminal():
    # examples of instances
    # logger = EventLogger()
    # auth = AccessControl(logger)

    print("=== Hospital Monitoring System Terminal ===")
    # commands might be like login, logout, view_logs, sim_adc, exit, etc
    print("Commands: 'sim_adc', 'exit'")

    while True:
        cmd = input("\nsystem> ").strip().lower()

        if cmd == "exit":
            print("Shutting down terminal...")
            break

        # elif cmd == "login":
        #     if auth.is_authenticated():
        #         print("You are already logged in!")
        #         continue
            
        #     user = input("Username: ")
        #     pwd = input("Password: ")
            
            
        #     if auth.login(user, pwd):
        #         print(f"Access Granted. Role: {auth.get_current_role()}")
        #     else:
        #         print("Access Denied. Credentials invalid.")

        # elif cmd == "logout":
        #     auth.logout()
        #     print("Logged out successfully.")

        

        elif cmd == "sim_adc":
            adcId = input("Enter ADC ID (e.g., ADC-01): ")
            payload = input("Enter message payload: ")
            isCrit = input("Is this critical? (y/n): ").strip().lower()
            
            severity = "critical" if isCrit == 'y' else "routine"
            # comms.receive_adc_message(adcId, payload, severity)

        else:
            print("Unknown command.")

if __name__ == "__main__":
    run_terminal()