"""
Module: System Shell (UI Module)
Responsibility: Provides the terminal-based user interface, enforces session authentication 
via Access Control, and routes terminal commands to Inventory Supervision and Event Logging.
"""

from event_logger import EventLogger
from inventory_manager import InventoryManager
from comms_gateway import CommsGateway
from alarm_class import Alarm, AlarmType
import access_control

def print_help_menu():
    """Helper function to cleanly display available commands."""
    print("\n==================================================================")
    print("                 HOSPITAL MONITORING SYSTEM - COMMANDS           ")
    print("==================================================================")
    print("  [Authentication]")
    print("    login          - Authenticate with User ID and password")
    print("    logout         - Terminate current active session")
    print("  [Inventory Supervision (Pharmacist / Admin)]")
    print("    init_adc       - Initialize a new ADC cabinet (Format: ADC-##)")
    print("    add_med        - Add a medication and par levels to an ADC")
    print("    remove_med     - Remove a medication from an ADC inventory")
    print("    restock        - Update stock levels (clears low-inventory alarms)")
    print("    view_inventory - Display live multi-cabinet inventory status")
    print("  [Audit Logging & Alarms (IT Admin / System)]")
    print("    view_logs      - Display centralized system audit logs (IT Admin)")
    print("    clear_logs     - Reset and clear the system audit log (IT Admin)")
    print("    sim_adc        - Simulate an incoming hardware or inventory alarm")
    print("    view_alarms    - List all active alarms in memory")
    print("    ack_alarm      - Acknowledge and resolve an active alarm")
    print("  [General]")
    print("    help           - Display this command menu")
    print("    exit           - Shut down the terminal shell")
    print("==================================================================")

def run_terminal():
    logger = EventLogger("system_audit_log.txt")
    inv_mgr = InventoryManager("system_inventory.txt", event_logger=logger)
    comms = CommsGateway(logger)
    
    # Active session state managed by Access Control module
    current_user = None
    
    # Track active alarms in memory
    active_alarms = {}

    print("=== Hospital Monitoring System Terminal ===")
    print("NOTE: You must log in first to execute any system commands.")
    print("Type 'help' to view available commands.")

    while True:
        cmd = input("\nsystem> ").strip().lower()

        if cmd == "exit":
            print("Shutting down terminal...")
            logger.log_event("SYSTEM", "SHELL", "System terminal shut down.", "SYSTEM")
            break

        elif cmd == "help":
            print_help_menu()
            continue

        # =====================================================================
        # AUTHENTICATION COMMANDS
        # =====================================================================
        elif cmd == "login":
            if current_user is not None:
                print(f"Already logged in as {current_user.name} ({current_user.role}). Logout first to switch users.")
                continue
            
            user_id = input("Enter User ID (e.g., L-001): ").strip()
            password = input("Enter Password: ").strip()
            
            # Calls login function from access_control module
            logged_in_user = access_control.login(user_id, password)
            if logged_in_user is not None:
                current_user = logged_in_user
                logger.log_event("SECURITY", "AUTH", f"User {current_user.name} ({current_user.role.value}) successfully logged in.", current_user.userID)
                print(f"Access Granted. Role: {current_user.role}")
                
                # Automatically print help menu upon successful login
                print_help_menu()
            continue

        elif cmd == "logout":
            if current_user is None:
                print("No user is currently logged in.")
                continue
            
            logger.log_event("SECURITY", "AUTH", f"User {current_user.name} logged out.", current_user.userID)
            current_user = access_control.logout(current_user)
            print("Logged out successfully.")
            continue

        # =====================================================================
        # GLOBAL SESSION GUARD: Block all other commands if not logged in
        # =====================================================================
        if current_user is None:
            print("[ACCESS DENIED] You must be logged in to execute system commands. Type 'login'.")
            continue

        # =====================================================================
        # INVENTORY COMMANDS (Restricted to Pharmacists or appropriate roles)
        # =====================================================================
        elif cmd == "init_adc":
            if not access_control.check_authorization(current_user, access_control.UserRole.PHARMACIST) and current_user.role != access_control.UserRole.IT_ADMIN:
                print("[ACCESS DENIED] Only Pharmacists or IT Admins can initialize new ADC cabinets.")
                continue
            
            adc_id = input("Enter ADC ID to initialize (e.g., ADC-03): ").strip()
            inv_mgr.init_adc(adc_id)

        elif cmd == "add_med":
            if not access_control.check_authorization(current_user, access_control.UserRole.PHARMACIST):
                print("[ACCESS DENIED] Only Pharmacists can add medications to ADC inventory.")
                logger.log_event("SECURITY_WARNING", current_user.userID, f"Unauthorized attempt by {current_user.role} to add medication.", current_user.userID)
                continue

            adc_id = input("Enter ADC ID (e.g., ADC-03): ").strip()
            med_name = input("Enter Medication Name (e.g., Morphine): ").strip()
            try:
                stock = int(input("Initial Stock: "))
                min_par = int(input("Minimum Par Level: "))
                max_par = int(input("Maximum Par Level: "))
                inv_mgr.add_medication(adc_id, med_name, stock, min_par, max_par)
            except ValueError:
                print("[ERROR] Stock and par levels must be integers.")

        elif cmd == "remove_med":
            if not access_control.check_authorization(current_user, access_control.UserRole.PHARMACIST):
                print("[ACCESS DENIED] Only Pharmacists can remove medications from inventory.")
                continue

            adc_id = input("Enter ADC ID (e.g., ADC-03): ").strip()
            med_name = input("Enter Medication Name to remove: ").strip()
            inv_mgr.remove_medication(adc_id, med_name, operator_id=current_user.userID)

        elif cmd == "restock":
            if not access_control.check_authorization(current_user, access_control.UserRole.PHARMACIST):
                print("[ACCESS DENIED] Only Pharmacists can update stock levels.")
                continue

            adc_id = input("Enter ADC ID (e.g., ADC-03): ").strip()
            med_name = input("Enter Medication Name: ").strip()
            try:
                new_stock = int(input("New Stock Level: "))
                inv_mgr.update_stock_level(adc_id, med_name, new_stock, operator_id=current_user.userID)
            except ValueError:
                print("[ERROR] Stock level must be integers.")

        elif cmd == "view_inventory":
            print("\n--- INVENTORY SUPERVISION STATUS ---")
            inv_mgr.get_inventory_status()
            print("------------------------------------")

        # =====================================================================
        # AUDIT LOG COMMANDS (Strictly restricted to IT Admin)
        # =====================================================================
        elif cmd == "view_logs":
            if not access_control.check_authorization(current_user, access_control.UserRole.IT_ADMIN):
                print("[ACCESS DENIED] Only IT Admins can view system audit logs.")
                logger.log_event("SECURITY_WARNING", current_user.userID, f"Unauthorized attempt by {current_user.role} to read logs.", current_user.userID)
                continue

            logger.read_logs()

        elif cmd == "clear_logs":
            if not access_control.check_authorization(current_user, access_control.UserRole.IT_ADMIN):
                print("[ACCESS DENIED] Only IT Admins can clear audit logs.")
                continue

            logger.clear_logs()

        # =====================================================================
        # ALARM & ADC SIMULATION COMMANDS
        # =====================================================================
        elif cmd == "sim_adc":
            adc_id = input("Enter ADC ID (e.g., ADC-03): ").strip()
            
            print("Alarm Types: 1) CONNECTION_LOST, 2) CABINET_FAULT, 3) LOW_INVENTORY")
            type_choice = input("Select alarm type (1-3): ").strip()
            
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
            
            # Create Alarm object
            new_alarm = Alarm(adcID=adc_id, alarmType=alarm_type, isCritical=is_crit, details=payload)
            alarm_key = f"{adc_id}-{alarm_type.value}"
            active_alarms[alarm_key] = new_alarm
            
            # If low inventory, automatically update inventory manager row and file
            if alarm_type == AlarmType.LOW_INVENTORY:
                med_name = input("Enter medication name affected by low inventory: ").strip()
                inv_mgr.process_incoming_alarm(new_alarm, med_name)
            else:
                comms.receive_adc_message(adc_id, payload, "critical" if is_crit else "routine")
                logger.log_event("ALARM", adc_id, f"Alarm simulated: {alarm_type.value} - {payload}", current_user.userID)

            print(f"Alarm simulated and logged: {alarm_key}")

        elif cmd == "view_alarms":
            if not active_alarms:
                 print("No active alarms.")
            else:
                 print("\n--- ACTIVE ALARMS ---")
                 for key, alarm in active_alarms.items():
                     print(f"[{key}]: {alarm}")
                 print("---------------------")

        elif cmd == "ack_alarm":
            alarm_key = input("Enter the Alarm Key to acknowledge (e.g., ADC-03-LOW_INVENTORY): ").strip()
            
            if alarm_key in active_alarms:
                logger.log_event("ALARM_ACK", current_user.userID, f"User {current_user.name} ({current_user.role.value}) acknowledged and cleared {alarm_key}", current_user.userID)
                del active_alarms[alarm_key]
                print(f"Alarm {alarm_key} acknowledged and cleared.")
            else:
                print("Error: Alarm key not found.")
                
        else:
            print("Unknown command. Type 'help' for a list of valid commands.")

if __name__ == "__main__":
    run_terminal()