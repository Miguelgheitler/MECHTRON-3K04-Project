"""
Module: Inventory Manager (Inventory Supervision)
Responsibility: Tracks live stock counts and par levels across multiple ADCs using medication 
names as primary keys, validates cabinet ID formatting (ADC-##), prevents duplicate medication 
entries per cabinet, allows medication removal, manages the dedicated inventory persistence file, 
and ingests external alarms.
"""

import os
import re
from typing import Dict, List, Optional
from datetime import datetime
from event_logger import EventLogger
from alarm_class import Alarm, AlarmType

class InventoryManager:
    """
    Hides the underlying inventory storage mechanism (file path, text record layout, 
    and dictionary caching structures) from the rest of the application.
    """
    def __init__(self, inventory_filepath: str = "system_inventory.txt", event_logger: Optional[EventLogger] = None):
        # IMPLEMENTATION SECRET: The file path and internal cache structures
        self._inventory_filepath = inventory_filepath
        self._event_logger = event_logger if event_logger else EventLogger()
        
        # In-memory cache structure: 
        # { adc_id: { med_name: { 'stock': int, 'min_par': int, 'max_par': int, 'alarm_msg': str } } }
        self._inventory_cache: Dict[str, Dict[str, dict]] = {}
        
        # Initialize or load storage file
        if not os.path.exists(self._inventory_filepath):
            self._write_default_storage()
        self._load_from_storage()

    def _write_default_storage(self) -> None:
        """HIDDEN IMPLEMENTATION: Creates the initial inventory text file layout with headers."""
        header = (
            "==================================================================\n"
            "                 ADC MULTI-CABINET INVENTORY SUPERVISION           \n"
            "             Hospital ABC - City, Province/State                 \n"
            "==================================================================\n"
            "ADC_ID | MEDICATION_NAME | STOCK | MIN_PAR | MAX_PAR | ALARM_STATUS\n"
            "------------------------------------------------------------------\n"
        )
        with open(self._inventory_filepath, "w", encoding="utf-8") as f:
            f.write(header)

    def _load_from_storage(self) -> None:
        """HIDDEN IMPLEMENTATION: Parses the inventory .txt file into the memory cache."""
        if not os.path.exists(self._inventory_filepath):
            return

        with open(self._inventory_filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self._inventory_cache = {}
        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("=") or line_str.startswith("-") or line_str.startswith("ADC_ID"):
                continue
            
            parts = [p.strip() for p in line_str.split("|")]
            if len(parts) >= 5:
                adc_id, med_name, stock, min_par, max_par = parts[0], parts[1], parts[2], parts[3], parts[4]
                alarm_msg = parts[5] if len(parts) > 5 else "NORMAL"
                
                if adc_id not in self._inventory_cache:
                    self._inventory_cache[adc_id] = {}
                
                self._inventory_cache[adc_id][med_name] = {
                    "stock": int(stock),
                    "min_par": int(min_par),
                    "max_par": int(max_par),
                    "alarm_msg": alarm_msg
                }

    def _sync_to_storage(self) -> None:
        """HIDDEN IMPLEMENTATION: Flushes the in-memory cache back to the dedicated text file."""
        header = (
            "==================================================================\n"
            "                 ADC MULTI-CABINET INVENTORY SUPERVISION           \n"
            "             Hospital ABC - City, Province/State                 \n"
            "==================================================================\n"
            "ADC_ID | MEDICATION_NAME | STOCK | MIN_PAR | MAX_PAR | ALARM_STATUS\n"
            "------------------------------------------------------------------\n"
        )
        
        lines = [header]
        for adc_id, meds in sorted(self._inventory_cache.items()):
            for med_name, data in sorted(meds.items()):
                status = data.get("alarm_msg", "NORMAL")
                line = f"{adc_id} | {med_name} | {data['stock']} | {data['min_par']} | {data['max_par']} | {status}\n"
                lines.append(line)

        with open(self._inventory_filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def _validate_adc_format(self, adc_id: str) -> bool:
        """HIDDEN IMPLEMENTATION: Enforces that ADC ID matches the required 'ADC-##' format."""
        pattern = r"^ADC-\d{2}$"
        return bool(re.match(pattern, adc_id))

    # =========================================================================
    # PUBLIC INTERFACE (What other modules are allowed to call)
    # =========================================================================

    def init_adc(self, adc_id: str) -> None:
        """
        Public Interface method to initialize a new ADC cabinet in the system.
        Enforces 'ADC-##' format validation.
        """
        if not self._validate_adc_format(adc_id):
            print(f"[INVENTORY ERROR] Invalid ADC ID format '{adc_id}'. Must follow format 'ADC-##' (e.g., ADC-03).")
            return

        if adc_id not in self._inventory_cache:
            self._inventory_cache[adc_id] = {}
            self._sync_to_storage()
            print(f"[INVENTORY SUCCESS] New ADC '{adc_id}' initialized.")
            if self._event_logger:
                self._event_logger.log_event("INVENTORY", adc_id, f"Initialized new ADC cabinet.", "SYSTEM")
        else:
            print(f"[INVENTORY NOTICE] ADC '{adc_id}' already exists.")

    def add_medication(self, adc_id: str, med_name: str, initial_stock: int, min_par: int, max_par: int) -> None:
        """
        Public Interface method to add a new medication name and its par levels to a specific ADC.
        Prevents duplicate medication entries of the same name within the same ADC.
        """
        if not self._validate_adc_format(adc_id):
            print(f"[INVENTORY ERROR] Cannot add medication to invalid ADC ID format '{adc_id}'.")
            return

        if adc_id not in self._inventory_cache:
            self.init_adc(adc_id)

        # Check if medication already exists in this ADC
        if med_name in self._inventory_cache[adc_id]:
            print(f"[INVENTORY NOTICE] Medication '{med_name}' already exists in '{adc_id}'. Duplicate entry prevented.")
            return

        self._inventory_cache[adc_id][med_name] = {
            "stock": initial_stock,
            "min_par": min_par,
            "max_par": max_par,
            "alarm_msg": "NORMAL"
        }
        self._sync_to_storage()
        print(f"[INVENTORY SUCCESS] Added medication '{med_name}' to {adc_id}.")
        
        if self._event_logger:
            self._event_logger.log_event("INVENTORY", adc_id, f"Added medication {med_name} with stock {initial_stock}.", "PHARMACIST")

    def remove_medication(self, adc_id: str, med_name: str, operator_id: str = "PHARMACIST-01") -> None:
        """
        Public Interface method to remove a medication from a specific ADC cabinet.
        Updates the in-memory cache, flushes the text file, and logs the action.
        """
        if adc_id not in self._inventory_cache or med_name not in self._inventory_cache[adc_id]:
            print(f"[INVENTORY ERROR] Medication '{med_name}' not found in '{adc_id}'.")
            return

        # Remove the medication from the dictionary
        del self._inventory_cache[adc_id][med_name]
        self._sync_to_storage()
        
        print(f"[INVENTORY SUCCESS] Removed medication '{med_name}' from {adc_id}.")
        
        if self._event_logger:
            self._event_logger.log_event("INVENTORY", adc_id, f"Removed medication {med_name} from cabinet inventory.", operator_id)

    def update_stock_level(self, adc_id: str, med_name: str, new_stock: int, operator_id: str = "PHARMACIST-01") -> None:
        """
        Public Interface method to update stock levels (e.g. during restocking or dispensing).
        If stock is restored to or above minimum par, any existing inventory alarm status is cleared.
        """
        if adc_id not in self._inventory_cache or med_name not in self._inventory_cache[adc_id]:
            print(f"[INVENTORY ERROR] Medication '{med_name}' not found in '{adc_id}'.")
            return

        med_data = self._inventory_cache[adc_id][med_name]
        old_stock = med_data["stock"]
        med_data["stock"] = new_stock

        # Automatically clear inventory alarm status if restocked to safe levels
        if new_stock >= med_data["min_par"] and "LOW_INVENTORY" in med_data.get("alarm_msg", ""):
            med_data["alarm_msg"] = "NORMAL"

        self._sync_to_storage()
        print(f"[INVENTORY SUCCESS] {adc_id} - {med_name} stock updated: {old_stock} -> {new_stock}")
        
        if self._event_logger:
            self._event_logger.log_event("INVENTORY", adc_id, f"Updated stock for {med_name} from {old_stock} to {new_stock}.", operator_id)

    def process_incoming_alarm(self, alarm: Alarm, med_name: str) -> None:
        """
        Public Interface method called when an alarm is transmitted over by an ADC.
        Automatically logs the alarm and updates the specific ADC/medication row in the 
        inventory manager file to reflect the active alarm message.
        """
        adc_id = alarm.adcID
        if adc_id in self._inventory_cache and med_name in self._inventory_cache[adc_id]:
            med_data = self._inventory_cache[adc_id][med_name]
            severity = "CRITICAL" if alarm.isCritical else "MINOR"
            med_data["alarm_msg"] = f"ACTIVE: {alarm.alarmType} ({severity})"
            self._sync_to_storage()
            
            print(f"[INVENTORY UPDATE] Applied alarm status to {adc_id} -> {med_name}")
        
        # Automatically log the alarm event via Event Logger
        if self._event_logger:
            self._event_logger.log_event("ALARM", adc_id, f"Alarm received from ADC: {alarm.alarmType} - {alarm.details}", "SYSTEM")

    def get_inventory_status(self) -> None:
        """
        Public Interface method to cleanly display the contents of the inventory file.
        """
        if not os.path.exists(self._inventory_filepath):
            print("Inventory file is missing.")
            return

        with open(self._inventory_filepath, "r", encoding="utf-8") as f:
            for line in f:
                print(line.strip())


# =============================================================================
# TERMINAL COPY-PASTE TEST INSTRUCTIONS (Interactive Python Shell)
# =============================================================================
# Open your terminal inside "Monitoring System Code", type `python3`, then paste:
#
#   from event_logger import EventLogger
#   from inventory_manager import InventoryManager
#   from alarm_class import Alarm, AlarmType
#   
#   logger = EventLogger("system_audit_log.txt")
#   inv_mgr = InventoryManager("system_inventory.txt", event_logger=logger)
#   
#   # 1. Test ADC Format Validation (Invalid vs Valid)
#   inv_mgr.init_adc("ADC-BAD")  # Should reject
#   inv_mgr.init_adc("ADC-03")   # Should succeed
#   
#   # 2. Add medication and test duplicate prevention
#   inv_mgr.add_medication("ADC-03", "Morphine", initial_stock=10, min_par=20, max_par=100)
#   inv_mgr.add_medication("ADC-03", "Morphine", initial_stock=50, min_par=20, max_par=100) # Should reject duplicate
#   
#   # 3. Simulate an incoming alarm packet sent over from ADC-03
#   incoming_alarm = Alarm(adcID="ADC-03", alarmType=AlarmType.LOW_INVENTORY, isCritical=True, details="Stock below minimum par")
#   inv_mgr.process_incoming_alarm(incoming_alarm, "Morphine")
#   
#   # 4. View inventory table (shows the active alarm status column updated)
#   inv_mgr.get_inventory_status()
#   
#   # 5. Test Medication Removal Function
#   inv_mgr.remove_medication("ADC-03", "Morphine")
#   inv_mgr.get_inventory_status()