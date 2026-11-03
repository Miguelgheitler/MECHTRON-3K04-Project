"""
Module: System Shell (UI Module)
Responsibility: Provides the terminal-based user interface, enforces session authentication 
via Access Control, and routes terminal commands to Inventory Supervision and Event Logging.
"""

from event_logger import EventLogger
from inventory_manager import InventoryManager
from comms_gateway import CommsGateway
from alarm_class import Alarm, AlarmType
from user_class import UserRole, User, load_user
from state_machine import StateMachine, SystemState
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
    print("  [Manage User Profiles (IT Admin)]")
    print("    hire           - Create user profile (IT Admin)")
    print("    retire/fire    - Delete user profile (IT Admin)")
    print("    modify_profile - Modify/update user profile (IT Admin)")
    print("  [Audit Logging & Alarms (IT Admin / System)]")
    print("    view_logs      - Display centralized system audit logs (IT Admin)")
    print("    clear_logs     - Reset and clear the system audit log (IT Admin)")
    print("    sim_adc        - Simulate an incoming hardware or inventory alarm")
    print("    sim_disconnect - Simulate a network timeout/lost connection for an ADC")
    print("    view_alarms    - List all active alarms in memory")
    print("    ack_alarm      - Acknowledge and resolve an active alarm")
    print("  [State Machine Demo]")
    print("    trigger_fault  - Inject a hardware fault to lock the system")
    print("    trigger_event  - Manually trigger a specific state machine event")
    print("  [General]")
    print("    help           - Display this command menu")
    print("    exit           - Shut down the terminal shell")
    print("==================================================================")

def run_terminal():
    logger = EventLogger("system_audit_log.txt")
    inv_mgr = InventoryManager("system_inventory.txt", event_logger=logger)
    comms = CommsGateway(logger)

    state_machine = StateMachine(logger)
    
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
        # GLOBAL STATE GUARD: Block operational commands if in FAULT state
        # =====================================================================
        operational_commands = ["init_adc", "add_med", "remove_med", "restock"]
        if cmd in operational_commands and state_machine.current_state == SystemState.FAULT:
            print(f"[BLOCKED] System is in {SystemState.FAULT.value} state. Maintenance required.")
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
            
            # Strict check: ADC must be initialized first!
            if not inv_mgr.adc_exists(adc_id):
                print(f"[ERROR] ADC '{adc_id}' does not exist or has not been initialized. Run 'init_adc' first.")
                continue

            med_name = input("Enter Medication Name (e.g., Morphine): ").strip()
            try:
                stock = int(input("Initial Stock: "))
                min_par = int(input("Minimum Par Level: "))
                max_par = int(input("Maximum Par Level: "))
                inv_mgr.add_medication(adc_id, med_name, stock, min_par, max_par, operator_id=current_user.userID)
            except ValueError:
                print("[ERROR] Stock and par levels must be integers.")

        elif cmd == "remove_med":
            if not access_control.check_authorization(current_user, access_control.UserRole.PHARMACIST):
                print("[ACCESS DENIED] Only Pharmacists can remove medications from inventory.")
                continue

            adc_id = input("Enter ADC ID (e.g., ADC-03): ").strip()
            
            # 1. Validate Cabinet existence IMMEDIATELY before asking for medication name
            if not inv_mgr.adc_exists(adc_id):
                print(f"[ERROR] ADC Cabinet '{adc_id}' does not exist or has not been initialized. Removal cancelled.")
                continue

            med_name = input("Enter Medication Name to remove: ").strip()
            
            # 2. Validate Medication existence SECOND
            if not inv_mgr.medication_exists(adc_id, med_name):
                print(f"[ERROR] Medication '{med_name}' not found in '{adc_id}'. Removal cancelled.")
                continue

            inv_mgr.remove_medication(adc_id, med_name, operator_id=current_user.userID)

        elif cmd == "restock":
            if not access_control.check_authorization(current_user, access_control.UserRole.PHARMACIST):
                print("[ACCESS DENIED] Only Pharmacists can update stock levels.")
                continue

            adc_id = input("Enter ADC ID (e.g., ADC-03): ").strip()
            
            # 1. Validate Cabinet existence FIRST
            if not inv_mgr.adc_exists(adc_id):
                print(f"[ERROR] ADC Cabinet '{adc_id}' does not exist or has not been initialized. Restock cancelled.")
                continue

            med_name = input("Enter Medication Name: ").strip()
            
            # 2. Validate Medication existence SECOND
            if not inv_mgr.medication_exists(adc_id, med_name):
                print(f"[ERROR] Medication '{med_name}' not found in '{adc_id}'. Restock cancelled.")
                continue

            try:
                new_stock = int(input("New Stock Level: "))
                inv_mgr.update_stock_level(adc_id, med_name, new_stock, operator_id=current_user.userID)
            except ValueError:
                print("[ERROR] Stock level must be an integer.")

        elif cmd == "view_inventory":
            print("\n--- INVENTORY SUPERVISION STATUS ---")
            inv_mgr.get_inventory_status()
            print("------------------------------------")

        # =====================================================================
        # USER PROFILE COMMANDS (Strictly restricted to IT Admin)
        # =====================================================================
        elif cmd == "hire":
            if not access_control.check_authorization(current_user, access_control.UserRole.IT_ADMIN):
                print("[ACCESS DENIED] Only IT Admins can create user profiles.")
                continue

            name = input("Enter name of new hire: ").strip()
            userID = input("Enter user ID: ").strip()
            password = input("Enter password: ").strip()

            roles = list(UserRole)
            print("Select a role:")
            for idx, role in enumerate(roles, start=1):
                print(f"  {idx}. {role.value}")

            choice = input("Enter choice (1-4): ").strip()
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(roles):
                    selected_role: UserRole = roles[choice_idx]
                    print(f"Selected: {selected_role}")
                else:
                    print("Selection out of range.")
            except ValueError:
                print("Please enter a valid number.")

            sms = input("Turn on sms notifications? (y/n) ").strip() == "y"
            email = input("Turn on email notifications? (y/n) ").strip() == "y"
            if not sms and not email:
                print("Must have min. 1 notification method enabled; automatically enabled app notification.")
                app = True
            else:
                app = input("Turn on app notifications? (y/n) ").strip() == "y"

            access_control.hire(name,selected_role,userID,password,sms,email,app)
            print(f"New user profile created. Name: {name}. User ID: {userID}.")

        elif cmd == "retire/fire":
            if not access_control.check_authorization(current_user, access_control.UserRole.IT_ADMIN):
                print("[ACCESS DENIED] Only IT Admins can delete user profiles.")
                continue

            userID = input("Input user ID of profile to delete: ").strip()
            targetFire = load_user(userID)
            if not isinstance(targetFire, User):
                print("Invalid user ID.")
                continue
            print(f"Preparing to delete profile: {targetFire.userID} ({targetFire.name})")
            if input("Press 1 to confirm profile deletion.") == "1":
                access_control.retire(userID)
            else:
                print("Profile deletion cancelled.")
        
        elif cmd == "modify_profile":
            if not access_control.check_authorization(current_user, access_control.UserRole.IT_ADMIN):
                print("[ACCESS DENIED] Only IT Admins can modify user profiles.")
                continue
            userID = input("Enter the user ID of the profile to modify: " ).strip()
            targetField = input("Enter field to modify (name,role,password,smsNotifEnabled,emailNotifEnabled,appNotifEnabled): ").strip()
            if targetField not in ["name", "role", "password", "smsNotifEnabled", "emailNotifEnabled", "appNotifEnabled"]:
                print("Invalid input.")
                continue
            changedValue = input(f"Enter the desired new value of {targetField}: ").strip()

            print(access_control.modify_profile(userID,targetField,changedValue))

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
            
            if not inv_mgr.adc_exists(adc_id):
                print(f"[ERROR] ADC Cabinet '{adc_id}' does not exist or has not been initialized. Simulation cancelled.")
                continue

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

            if alarm_type == AlarmType.LOW_INVENTORY:
                med_name = input("Enter medication name affected by low inventory: ").strip()
                
                if not inv_mgr.medication_exists(adc_id, med_name):
                    print(f"[ERROR] Medication '{med_name}' not found in '{adc_id}'. Alarm simulation cancelled.")
                    continue
                
                payload = input("Enter message payload: ")
                is_crit = input("Is this critical? (y/n): ").strip().lower() == 'y'
                
                new_alarm = Alarm(adcID=adc_id, alarmType=alarm_type, isCritical=is_crit, details=payload)
                alarm_key = f"{adc_id}-{alarm_type.value}-{med_name}"
                active_alarms[alarm_key] = (new_alarm, med_name)
                
                # 1. Update inventory state and storage
                inv_mgr.process_incoming_alarm(new_alarm, med_name)
                
                # 2. Route the hardware telemetry message through CommsGateway for uniform logging
                severity_str = "critical" if is_crit else "routine"
                comms.receive_adc_message(adc_id, f"LOW_INVENTORY ({med_name}): {payload}", severity_str)
                
                print(f"Alarm simulated and logged: {alarm_key}")

            else:
                # Handles CONNECTION_LOST and CABINET_FAULT uniformly via CommsGateway
                payload = input("Enter message payload: ")
                is_crit = input("Is this critical? (y/n): ").strip().lower() == 'y'
                
                new_alarm = Alarm(adcID=adc_id, alarmType=alarm_type, isCritical=is_crit, details=payload)
                alarm_key = f"{adc_id}-{alarm_type.value}"
                active_alarms[alarm_key] = new_alarm
                
                severity_str = "critical" if is_crit else "routine"
                comms.receive_adc_message(adc_id, f"{alarm_type.value}: {payload}", severity_str)
                
                print(f"Alarm simulated and logged: {alarm_key}")

        elif cmd == "sim_disconnect":
            adc_id = input("Enter ADC ID to disconnect (e.g., ADC-03): ").strip()
            print(f"\n[SYSTEM] Simulating network timeout (30s threshold reached) for {adc_id}...")
            comms.drop_connection(adc_id)

        elif cmd == "view_alarms":
            if not active_alarms:
                 print("No active alarms.")
            else:
                 print("\n--- ACTIVE ALARMS ---")
                 for key, item in active_alarms.items():
                     alarm = item[0] if isinstance(item, tuple) else item
                     print(f"[{key}]: Alarm [CRITICAL]" if alarm.isCritical else f"[{key}]: Alarm [ROUTINE]")
                 print("---------------------")

        elif cmd == "ack_alarm":
            alarm_key = input("Enter the Alarm Key to acknowledge (e.g., ADC-04-LOW_INVENTORY-Insulin): ").strip()
            
            if alarm_key in active_alarms:
                item = active_alarms[alarm_key]
                
                # If it's a medication-specific low inventory alarm, clear its status via InventoryManager
                if isinstance(item, tuple):
                    alarm, med_name = item
                    if alarm.alarmType == AlarmType.LOW_INVENTORY:
                        inv_mgr.clear_alarm_status(alarm.adcID, med_name)
                
                logger.log_event("ALARM_ACK", current_user.userID, f"User {current_user.name} ({current_user.role.value}) acknowledged and cleared {alarm_key}", current_user.userID)
                del active_alarms[alarm_key]
                print(f"Alarm {alarm_key} acknowledged and cleared.")
            else:
                print("Error: Alarm key not found in active alarms.")
                
        # ==========================================
        # STATE MACHINE DEMO COMMANDS
        # ==========================================

        elif cmd == "trigger_fault":
            print("[SYSTEM] Simulating sudden hardware failure...")
            state_machine.trigger_event("hardwareFault", current_user.userID)
            print(f"Current State is now: {state_machine.current_state.value}")

        elif cmd == "trigger_event":
            print(f"Current State: {state_machine.current_state.value}")
            event_name = input("Enter event (testPassed, testFailed, hardwareFault, techLogin, exit): ").strip()

            # Enforce techLogin guard for IT Admins only
            if event_name == "techLogin":
                if not access_control.check_authorization(current_user, access_control.UserRole.IT_ADMIN):
                    print("[ACCESS DENIED] Only an IT_ADMIN can perform a techLogin.")
                    continue

            success = state_machine.trigger_event(event_name, current_user.userID)
            if success:
                print(f"State updated successfully. New State: {state_machine.current_state.value}")
            else:
                print(f"[REJECTED] The event '{event_name}' is invalid in the {state_machine.current_state.value} state.")

        else:
            print("Unknown command. Type 'help' for a list of valid commands.")

           

if __name__ == "__main__":
    run_terminal()