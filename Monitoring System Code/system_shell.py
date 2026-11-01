from event_logger import EventLogger
#from access_control import AccessControl
from comms_gateway import CommsGateway
from alarm_class import Alarm, AlarmType 

class MockAuth:
    def is_authenticated(self): return True
    def get_current_role(self): return "IT Admin"
    def login(self, user, pwd): return True
    def logout(self): pass

def run_terminal():
    logger = EventLogger()
    #auth = AccessControl(logger)
    #mock auth for testing
    auth = MockAuth()
    comms = CommsGateway(logger)
    
    # used to keep track of active alarms in the system
    active_alarms = {}

    print("=== Hospital Monitoring System Terminal ===")
    print("Commands: 'login', 'logout', 'view_logs', 'sim_adc', 'view_alarms', 'ack_alarm', 'exit'")

    while True:
        cmd = input("\nsystem> ").strip().lower()

        if cmd == "exit":
            print("Shutting down terminal...")
            break

        elif cmd == "login":
            if auth.is_authenticated():
                print("You are already logged in!")
                continue
            
            user = input("Username: ")
            pwd = input("Password: ")
            
            if auth.login(user, pwd):
                print(f"Access Granted. Role: {auth.get_current_role()}")
            else:
                print("Access Denied. Credentials invalid.")

        elif cmd == "logout":
            auth.logout()
            print("Logged out successfully.")

        elif cmd == "view_logs":
            if not auth.is_authenticated():
                print("Error: You must be logged in to view system logs.")
                logger.log_event("security_warning", "Unauthorized attempt to view logs.")
                continue
            
            role = auth.get_current_role()
            if role != "IT Admin":
                print("Error: Only IT Admins can view detailed system logs.")
                continue

            print("\n--- SYSTEM EVENT LOGS ---")
            for log in logger.get_logs():
                print(log)
            print("-------------------------")

        elif cmd == "sim_adc":
            adc_id = input("Enter ADC ID (e.g., ADC-01): ")
            
            # map user input to AlarmType
            print("Alarm Types: 1) CONNECTION_LOST, 2) CABINET_FAULT, 3) LOW_INVENTORY")
            type_choice = input("Select alarm type (1-3): ")
            
            if type_choice == '1':
                alarm_type = AlarmType.CONNECTION_LOST
            elif type_choice == '2':
                alarm_type = AlarmType.CABINET_FAULT
            elif type_choice == '3':
                alarm_type = AlarmType.LOW_INVENTORY
            else:
                print("Invalid selection.")
                continue

            payload = input("Enter message payload: ")
            is_crit = input("Is this critical? (y/n): ").strip().lower() == 'y'
            
            # create and log alarm
            new_alarm = Alarm(adcID=adc_id, alarmType=alarm_type, isCritical=is_crit, details=payload)
            alarm_key = f"{adc_id}-{alarm_type.value}"
            active_alarms[alarm_key] = new_alarm
            
            # pass to comms gateway for processing
            severity = "critical" if is_crit else "routine"
            comms.receive_adc_message(adc_id, payload, severity)
            print(f"Alarm created: {alarm_key}")

        elif cmd == "view_alarms":
            # any authenticated user can view active alarms
            if not auth.is_authenticated():
                 print("Error: You must be logged in to view alarms.")
                 continue
                 
            if not active_alarms:
                 print("No active alarms.")
            else:
                 print("\n--- ACTIVE ALARMS ---")
                 for key, alarm in active_alarms.items():
                     print(f"[{key}]: {alarm}")
                 print("---------------------")

        elif cmd == "ack_alarm":
            if not auth.is_authenticated():
                 print("Error: You must be logged in to acknowledge alarms.")
                 continue
                 
            alarm_key = input("Enter the Alarm Key to acknowledge (e.g., ADC-01-CONNECTION_LOST): ")
            
            if alarm_key in active_alarms:
                # log resolution, and ack alarm
                logger.log_event("alarm_acknowledged", f"User {auth.get_current_role()} acknowledged and cleared {alarm_key}")
                del active_alarms[alarm_key]
                print(f"Alarm {alarm_key} acknowledged and cleared.")
            else:
                print("Error: Alarm key not found.")
                
        else:
            print("Unknown command. Valid commands: 'login', 'logout', 'view_logs', 'sim_adc', 'view_alarms', 'ack_alarm', 'exit'")

if __name__ == "__main__":
    run_terminal()