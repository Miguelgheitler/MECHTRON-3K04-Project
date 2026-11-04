"""
Module: System Shell (UI Module)
Responsibility: Provides the terminal-based user interface, enforces session authentication and 2-minute inactivity timeouts via Access Control, and routes terminal commands to Inventory Supervision, Alarm Management, Task Workflow, and Event Logging.
"""
from event_logger import EventLogger
from inventory_manager import InventoryManager
from comms_gateway import CommsGateway
from alarm_class import Alarm, AlarmType
from user_class import UserRole, User, load_user
from task_class import Task, TaskType, TaskStatus
from state_machine import StateMachine, SystemState
from patient_database import PatientDatabase
import access_control


def print_help_menu():
    """Helper function to cleanly display available commands."""
    print("\n==================================================================")
    print("                 HOSPITAL MONITORING SYSTEM - COMMANDS           ")
    print("==================================================================")
    print("  [Authentication]")
    print("    login          - Authenticate with User ID and password")
    print("    logout         - Terminate current active session")
    print("  [Patient Information (PID)]")
    print("    add_patient    - Create a new patient profile (Admin/Pharmacist)")
    print("    view_patient   - Securely view patient profile (Nurse/Pharmacist)")
    print("    dispense_med   - Dispense medication and link to a patient (Nurse)")
    print("  [Inventory Supervision (Pharmacist / Admin)]")
    print("    init_adc       - Initialize a new ADC cabinet (Format: ADC-##)")
    print("    add_med        - Add a medication and par levels to an ADC")
    print("    remove_med     - Remove a medication from an ADC inventory")
    print("    restock        - Update stock levels (clears low-inventory alarms)")
    print("    view_inventory - Display live multi-cabinet inventory status")
    print("  [Task Assignment & Workflow (Nurse / Pharmacist / Supervisor)]")
    print("    create_task    - Submit a routine or special task request")
    print("    view_tasks     - View tasks in the system queue")
    print("    assign_task    - Assign a pending task to staff (Supervisor)")
    print("    return_task    - Return task for clarification (Supervisor)")
    print("    resubmit_task  - Clarify and resubmit a returned task")
    print("    complete_task  - Mark an assigned task as complete")
    print("  [Manage User Profiles & Notification Settings]")
    print("    hire           - Create user profile (IT Admin)")
    print("    retire/fire    - Delete user profile (IT Admin)")
    print("    modify_profile - Modify user profile (IT Admin) or own notif settings")
    print("  [Audit Logging & Alarms (IT Admin / System)]")
    print("    view_logs      - Display centralized system audit logs (IT Admin)")
    print("    clear_logs     - Reset and clear the system audit log (IT Admin)")
    print("    sim_adc        - Simulate an incoming hardware, inventory, or dose alarm")
    print("    sim_disconnect - Simulate a network timeout/lost connection for an ADC")
    print("    view_alarms    - List all active alarms in memory")
    print("    escalate_alarm - Escalate an unresolved minor alarm to CRITICAL ")
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
    patient_db = PatientDatabase("patient_records.txt", logger=logger)

    # Active session state managed by Access Control module
    current_user = None

    # Track active alarms and tasks in memory
    active_alarms = {}
    active_tasks = {}

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
        # SAFETY-CRITICAL INACTIVITY TIMEOUT CHECK (FR-ADM-05 / NFR-UIF-02)
        # =====================================================================
        if current_user is not None and access_control.check_session_timeout(current_user):
            current_user = access_control.logout(current_user)
            continue

        # =====================================================================
        # AUTHENTICATION COMMANDS
        # =====================================================================
        if cmd == "login":
            if current_user is not None:
                print(f"Already logged in as {current_user.name} ({current_user.role.value}). Logout first to switch users.")
                continue

            user_id = input("Enter User ID (e.g., N-001): ").strip()
            password = input("Enter Password: ").strip()

            # Calls login function from access_control module
            logged_in_user = access_control.login(user_id, password)
            if logged_in_user is not None:
                current_user = logged_in_user
                logger.log_event("SECURITY", "AUTH", f"User {current_user.name} ({current_user.role.value}) successfully logged in.", current_user.userID)
                print(f"Access Granted. Role: {current_user.role.value}")
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
        # STATE MACHINE DEMO COMMANDS (Simulating internal hardware events)
        # =====================================================================
        elif cmd == "trigger_fault":
            uid = current_user.userID if current_user else "SYSTEM"
            state_machine.trigger_event("hardwareFault", uid)
            print(f"State: {state_machine.current_state.value}")
            continue
            
        elif cmd == "trigger_event":
            uid = current_user.userID if current_user else "SYSTEM"
            event_name = input("Event (testPassed, testFailed, hardwareFault, techLogin, exit): ").strip()
            
            # Enforce techLogin guard for IT Admins only
            if event_name == "techLogin":
                if current_user is None or not access_control.check_authorization(current_user, access_control.UserRole.IT_ADMIN):
                    print("[ACCESS DENIED] Only an logged-in IT_ADMIN can perform a techLogin.")
                    continue
                    
            success = state_machine.trigger_event(event_name, uid)
            print("Success." if success else "Rejected.")
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
        operational_commands = [
            "init_adc", "add_med", "remove_med", "restock",
            "create_task", "assign_task", "return_task", "resubmit_task", "complete_task"
        ]
        if cmd in operational_commands and state_machine.current_state == SystemState.FAULT:
            print(f"[BLOCKED] System is in {SystemState.FAULT.value} state. Maintenance required.")
            continue

        # --- PATIENT INFO DATABASE (PID) ---
        elif cmd == "add_patient":
            if current_user.role not in [access_control.UserRole.PHARMACIST, access_control.UserRole.IT_ADMIN]:
                print("[ACCESS DENIED] Only Pharmacists or Admins can add patients.")
                continue
            pid = input("Enter Patient ID (e.g., PT-103): ").strip()
            name = input("Enter Patient Name: ").strip()
            schedule = input("Enter Medication Schedule: ").strip()
            patient_db.add_patient(pid, name, schedule, current_user.userID)

        elif cmd == "view_patient":
            pid = input("Enter Patient ID to view: ").strip()
            # Demo showing PII Scrubbing vs Full Access
            if current_user.role == access_control.UserRole.IT_ADMIN:
                print("\n[IT ADMIN VIEW] Scrubbing PII for non-clinical staff...")
                print(patient_db.get_anonymized_schedule(pid))
            else:
                print("\n[CLINICAL VIEW] Pulling full secure profile...")
                profile = patient_db.get_patient_full(pid, current_user.userID)
                if profile:
                    print(f"Name: {profile['name']}\nSchedule: {profile['schedule']}")

        elif cmd == "dispense_med":
            if current_user.role not in [access_control.UserRole.NURSE, access_control.UserRole.PHARMACIST]:
                print("[ACCESS DENIED] Only Nurses or Pharmacists can dispense medication.")
                continue
            
            pid = input("Enter Patient ID receiving medication: ").strip()
            # Verify patient exists first
            if patient_db.get_anonymized_schedule(pid) == "Patient not found.":
                print("[ERROR] Cannot dispense. Patient ID does not exist.")
                continue
                
            adc_id = input("Enter ADC ID dispensing from (e.g., ADC-01): ").strip()
            med_name = input("Enter Medication Name: ").strip()
            
            try:
                new_stock = int(input("Enter New Stock Level after dispensing: "))
                # Update inventory
                if inv_mgr.update_stock_level(adc_id, med_name, new_stock, operator_id=current_user.userID) == True:
                    logger.log_event("DISPENSE", adc_id, f"Dispensed {med_name} to patient {pid}", current_user.userID)
                    print(f"[SUCCESS] Medication securely logged to Patient {pid}'s history.")
                
                # Traceability: Link the dispense event directly to the patient profile (FR-PID-03)
                
            except ValueError:
                print("[ERROR] Stock level must be an integer.")

        # =====================================================================
        # INVENTORY COMMANDS (Restricted to Pharmacists or appropriate roles)
        # =====================================================================
        elif cmd == "init_adc":
            if not access_control.check_authorization(current_user, UserRole.PHARMACIST) and current_user.role != UserRole.IT_ADMIN:
                print("[ACCESS DENIED] Only Pharmacists or IT Admins can initialize new ADC cabinets.")
                continue

            adc_id = input("Enter ADC ID to initialize (e.g., ADC-03): ").strip()
            inv_mgr.init_adc(adc_id)

        elif cmd == "add_med":
            if not access_control.check_authorization(current_user, UserRole.PHARMACIST):
                print("[ACCESS DENIED] Only Pharmacists can add medications to ADC inventory.")
                logger.log_event("SECURITY_WARNING", current_user.userID, f"Unauthorized attempt by {current_user.role.value} to add medication.", current_user.userID)
                continue

            adc_id = input("Enter ADC ID (e.g., ADC-03): ").strip()
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
            if not access_control.check_authorization(current_user, UserRole.PHARMACIST):
                print("[ACCESS DENIED] Only Pharmacists can remove medications from inventory.")
                continue

            adc_id = input("Enter ADC ID (e.g., ADC-03): ").strip()
            if not inv_mgr.adc_exists(adc_id):
                print(f"[ERROR] ADC Cabinet '{adc_id}' does not exist or has not been initialized. Removal cancelled.")
                continue

            med_name = input("Enter Medication Name to remove: ").strip()
            if not inv_mgr.medication_exists(adc_id, med_name):
                print(f"[ERROR] Medication '{med_name}' not found in '{adc_id}'. Removal cancelled.")
                continue

            inv_mgr.remove_medication(adc_id, med_name, operator_id=current_user.userID)

        elif cmd == "restock":
            if not access_control.check_authorization(current_user, UserRole.PHARMACIST):
                print("[ACCESS DENIED] Only Pharmacists can update stock levels.")
                continue

            adc_id = input("Enter ADC ID (e.g., ADC-03): ").strip()
            if not inv_mgr.adc_exists(adc_id):
                print(f"[ERROR] ADC Cabinet '{adc_id}' does not exist or has not been initialized. Restock cancelled.")
                continue

            med_name = input("Enter Medication Name: ").strip()
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
        # TASK ASSIGNMENT & WORKFLOW COMMANDS
        # =====================================================================
        elif cmd == "create_task":
            task_id = input("Enter Task ID (e.g., TSK-01): ").strip().upper()
            if task_id in active_tasks:
                print(f"[ERROR] Task '{task_id}' already exists.")
                continue

            t_choice = input("Task Type — 1) ROUTINE (auto-delegated), 2) SPECIAL (supervisor review): ").strip()
            if t_choice == "1":
                t_type = TaskType.ROUTINE
                assignee = input("Enter target employee User ID for routine task (e.g., N-001): ").strip()
            elif t_choice == "2":
                t_type = TaskType.SPECIAL
                assignee = "S-001"  # Default supervisor queue for review
            else:
                print("Invalid task type selection.")
                continue

            details = input("Enter task details: ").strip()
            new_task = Task(
                task_id=task_id,
                sender_id=current_user.userID,
                task_type=t_type,
                details=details,
                assignee=assignee
            )
            active_tasks[task_id] = new_task
            print(f"[TASK CREATED] {new_task}")

        elif cmd == "view_tasks":
            if not active_tasks:
                print("No tasks in the system.")
            else:
                print("\n--- SYSTEM TASKS ---")
                is_supervisor = current_user.role == access_control.UserRole.SUPERVISOR
                
                for t_id, task_obj in active_tasks.items():
                    # Supervisor views ALL tasks; regular staff view only tasks assigned to or created by them
                    if is_supervisor or task_obj.assignee == current_user.userID or task_obj.sender_id == current_user.userID:
                        print(task_obj)
                        print(f"   Details: {task_obj.details}")
                        for note in task_obj.clarification_notes:
                            print(f"     -> {note}")
                print("--------------------")

        elif cmd == "assign_task":
            if not access_control.check_authorization(current_user, access_control.UserRole.SUPERVISOR):
                print("[ACCESS DENIED] Only Clinical Supervisors can assign pending tasks.")
                continue

            task_id = input("Enter Task ID to assign: ").strip().upper()
            if task_id not in active_tasks:
                print(f"[ERROR] Task '{task_id}' not found.")
                continue

            target_user = input("Enter Assignee User ID (e.g., N-001, P-001): ").strip()
            comment = input("Optional supervisor note (press Enter to skip): ").strip()
            active_tasks[task_id].assign(target_user, current_user.userID, comment)
            print(f"[TASK ASSIGNED] {active_tasks[task_id]}")

        elif cmd == "return_task":
            if not access_control.check_authorization(current_user, access_control.UserRole.SUPERVISOR):
                print("[ACCESS DENIED] Only Clinical Supervisors can return tasks for clarification.")
                continue

            task_id = input("Enter Task ID to return: ").strip().upper()
            if task_id not in active_tasks:
                print(f"[ERROR] Task '{task_id}' not found.")
                continue

            reason = input("Enter reason for clarification: ").strip()
            active_tasks[task_id].return_for_clarification(current_user.userID, reason)
            print(f"[TASK RETURNED] Returned to sender {active_tasks[task_id].sender_id} for clarification.")

        elif cmd == "complete_task":
            task_id = input("Enter Task ID to mark complete: ").strip().upper()
            if task_id not in active_tasks:
                print(f"[ERROR] Task '{task_id}' not found.")
                continue

            task = active_tasks[task_id]
            # Enforce that only the assigned person can complete it
            if task.assignee != current_user.userID:
                print(f"[ACCESS DENIED] You cannot complete this task because it is assigned to '{task_id}', not you.")
                continue

            try:
                task.mark_complete(current_user.userID)
                print(f"[TASK COMPLETED] {task}")
            except PermissionError as e:
                print(f"[ERROR] {e}")

        # =====================================================================
        # USER PROFILE & NOTIFICATION COMMANDS (IT Admin or Self Notif Update)
        # =====================================================================
        elif cmd == "hire":
            if not access_control.check_authorization(current_user, UserRole.IT_ADMIN):
                print("[ACCESS DENIED] Only IT Admins can create user profiles.")
                continue

            name = input("Enter name of new hire: ").strip()
            userID = input("Enter user ID: ").strip()
            password = input("Enter password: ").strip()

            roles = list(UserRole)
            print("Select a role:")
            for idx, role in enumerate(roles, start=1):
                print(f"  {idx}. {role.value}")

            choice = input(f"Enter choice (1-{len(roles)}): ").strip()
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(roles):
                    selected_role: UserRole = roles[choice_idx]
                    print(f"Selected: {selected_role.value}")
                else:
                    print("Selection out of range. Hire cancelled.")
                    continue
            except ValueError:
                print("Please enter a valid number. Hire cancelled.")
                continue

            sms = input("Turn on sms notifications? (y/n) ").strip().lower() == "y"
            email = input("Turn on email notifications? (y/n) ").strip().lower() == "y"
            if not sms and not email:
                print("Must have min. 1 notification method enabled; automatically enabled app notification.")
                app = True
            else:
                app = input("Turn on app notifications? (y/n) ").strip().lower() == "y"

            result = access_control.hire(name, selected_role, userID, password, sms, email, app)
            print(result)

        elif cmd == "retire/fire":
            if not access_control.check_authorization(current_user, UserRole.IT_ADMIN):
                print("[ACCESS DENIED] Only IT Admins can delete user profiles.")
                continue

            userID = input("Input user ID of profile to delete: ").strip()
            targetFire = load_user(userID)
            if not isinstance(targetFire, User):
                print("Invalid user ID.")
                continue
            print(f"Preparing to delete profile: {targetFire.userID} ({targetFire.name})")
            if input("Press 1 to confirm profile deletion: ").strip() == "1":
                print(access_control.retire(userID))
            else:
                print("Profile deletion cancelled.")

        elif cmd == "modify_profile":
            # IT Admins can modify any profile/field (FR-ADM-02);
            # Non-admin staff can modify their own notification channels (FR-ALM-04 / SP-ALM-04)
            is_admin = current_user.role == UserRole.IT_ADMIN
            if is_admin:
                userID = input("Enter the user ID of the profile to modify: ").strip()
                targetField = input("Enter field to modify (name,role,password,smsNotifEnabled,emailNotifEnabled,appNotifEnabled): ").strip()
                allowed_fields = ["name", "role", "password", "smsNotifEnabled", "emailNotifEnabled", "appNotifEnabled"]
            else:
                userID = current_user.userID
                print(f"Modifying notification preferences for {current_user.name} ({current_user.userID}): {current_user.prefAlarmChannel}")
                targetField = input("Enter notification field to modify (smsNotifEnabled,emailNotifEnabled,appNotifEnabled): ").strip()
                allowed_fields = ["smsNotifEnabled", "emailNotifEnabled", "appNotifEnabled"]

            if targetField not in allowed_fields:
                print("Invalid or unauthorized field.")
                continue

            changedValue = input(f"Enter the desired new value of {targetField}: ").strip()
            result_msg = access_control.modify_profile(userID, targetField, changedValue)
            print(result_msg)

            # Refresh current_user in memory if they modified their own record
            if userID == current_user.userID:
                refreshed = load_user(current_user.userID)
                if refreshed is not None:
                    current_user = refreshed

        # =====================================================================
        # AUDIT LOG COMMANDS (Strictly restricted to IT Admin)
        # =====================================================================
        elif cmd == "view_logs":
            if not access_control.check_authorization(current_user, UserRole.IT_ADMIN):
                print("[ACCESS DENIED] Only IT Admins can view system audit logs.")
                logger.log_event("SECURITY_WARNING", current_user.userID, f"Unauthorized attempt by {current_user.role.value} to read logs.", current_user.userID)
                continue

            logger.read_logs()

        elif cmd == "clear_logs":
            if not access_control.check_authorization(current_user, UserRole.IT_ADMIN):
                print("[ACCESS DENIED] Only IT Admins can clear audit logs.")
                continue

            logger.clear_logs()

        # =====================================================================
        # ALARM & ADC SIMULATION COMMANDS
        # =====================================================================
        elif cmd == "sim_adc":
            adc_id = input("Enter ADC ID (e.g., ADC-03): ").strip().upper()

            if not inv_mgr.adc_exists(adc_id):
                print(f"[ERROR] ADC Cabinet '{adc_id}' does not exist or has not been initialized. Simulation cancelled.")
                continue

            print("Alarm Types: 1) CONNECTION_LOST, 2) CABINET_FAULT, 3) LOW_INVENTORY, 4) MISSED_DOSE")
            type_choice = input("Select alarm type (1-4): ").strip()

            if type_choice == '1':
                alarm_type = AlarmType.CONNECTION_LOST
            elif type_choice == '2':
                alarm_type = AlarmType.CABINET_FAULT
            elif type_choice == '3':
                alarm_type = AlarmType.LOW_INVENTORY
            elif type_choice == '4':
                alarm_type = AlarmType.MISSED_DOSE
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
                severity_str = "critical" if new_alarm.isCritical else "routine"
                comms.receive_adc_message(adc_id, f"LOW_INVENTORY ({med_name}): {payload}", severity_str)

                # 3. Show safety-critical routing & PII-scrubbed personal alert (SP-ALM-02 & SP-ALM-03)
                print(f"[ALARM ROUTER] Directed to roles: {new_alarm.find_recipient()}")
                print(f"[PERSONAL DEVICE DISPATCH] {new_alarm.get_sanitized_personal_alert()}")
                print(f"Alarm simulated and logged: {alarm_key}")

            else:
                payload = input("Enter message payload (e.g., Patient: John_Doe missed dose): ")
                is_crit = True if alarm_type == AlarmType.CONNECTION_LOST else (input("Is this critical? (y/n): ").strip().lower() == 'y')

                new_alarm = Alarm(adcID=adc_id, alarmType=alarm_type, isCritical=is_crit, details=payload)
                alarm_key = f"{adc_id}-{alarm_type.value}"
                active_alarms[alarm_key] = new_alarm

                severity_str = "critical" if new_alarm.isCritical else "routine"
                comms.receive_adc_message(adc_id, f"{alarm_type.value}: {payload}", severity_str)

                print(f"[ALARM ROUTER] Directed to roles: {new_alarm.find_recipient()}")
                print(f"[PERSONAL DEVICE DISPATCH] {new_alarm.get_sanitized_personal_alert()}")
                print(f"Alarm simulated and logged: {alarm_key}")

        elif cmd == "sim_disconnect":
            adc_id = input("Enter ADC ID to disconnect (e.g., ADC-03): ").strip().upper()
            print(f"\n[SYSTEM] Simulating network timeout (30s threshold reached) for {adc_id}...")
            comms.drop_connection(adc_id)

        elif cmd == "view_alarms":
            if not active_alarms:
                print("No active alarms.")
            else:
                print("\n--- ACTIVE ALARMS ---")
                for key, item in active_alarms.items():
                    alarm = item[0] if isinstance(item, tuple) else item
                    print(f"[{key}]: {alarm} -> Recipients: {alarm.find_recipient()}")
                print("---------------------")

        elif cmd == "escalate_alarm":
            alarm_key = input("Enter the Alarm Key to escalate (e.g., ADC-03-LOW_INVENTORY-Morphine): ").strip()
            if alarm_key in active_alarms:
                item = active_alarms[alarm_key]
                alarm = item[0] if isinstance(item, tuple) else item
                alarm.escalate()
                if isinstance(item, tuple):
                    inv_mgr.process_incoming_alarm(alarm, item[1])
                print(f"[ALARM ESCALATED] {alarm_key} is now CRITICAL. Updated recipients: {alarm.find_recipient()}")
            else:
                print("Error: Alarm key not found in active alarms.")

        elif cmd == "ack_alarm":
            alarm_key = input("Enter the Alarm Key to acknowledge (e.g., ADC-04-LOW_INVENTORY-Insulin): ").strip()

            if alarm_key in active_alarms:
                item = active_alarms[alarm_key]
                alarm = item[0] if isinstance(item, tuple) else item
                alarm.acknowledge(current_user.userID)

                # If it's a medication-specific low inventory alarm, clear its status via InventoryManager
                if isinstance(item, tuple):
                    _, med_name = item
                    if alarm.alarmType == AlarmType.LOW_INVENTORY:
                        inv_mgr.clear_alarm_status(alarm.adcID, med_name)

                del active_alarms[alarm_key]
                print(f"Alarm {alarm_key} acknowledged and cleared.")
            else:
                print("Error: Alarm key not found in active alarms.")


if __name__ == "__main__":
    run_terminal()
