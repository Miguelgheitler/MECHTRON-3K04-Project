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
    def _format_alarm_name(self, alarm_type) -> str:
        """Helper to strip Python enum prefixes like 'AlarmType.' for clean display."""
        val_str = str(alarm_type)
        if "." in val_str:
            return val_str.split(".")[-1]
        return val_str

    def clear_alarm_status(self, adc_id: str, med_name: str) -> bool:
        """
        Public Interface method to clear an active alarm status for a specific medication, 
        resetting its alarm status column back to NORMAL.
        """
        if not self.medication_exists(adc_id, med_name):
            return False
        
        med_data = self._inventory_cache[adc_id][med_name]
        med_data["alarm_msg"] = "NORMAL"
        self._sync_to_storage()
        
        print(f"[INVENTORY UPDATE] Alarm cleared for {adc_id} -> {med_name} (Status: NORMAL)")
        
        return True
    
    def init_adc(self, adc_id: str) -> None:
        """
        Initializes a new ADC cabinet in memory and writes a placeholder row to storage.
        """
        adc_id = adc_id.strip().upper()
        if not adc_id.startswith("ADC-"):
            print("[INVENTORY ERROR] Invalid ADC ID format. Must start with 'ADC-' (e.g., ADC-03).")
            return

        if adc_id in self._inventory_cache:
            print(f"[INVENTORY NOTICE] ADC '{adc_id}' is already initialized.")
            return

        # Initialize using '---' as a clean medication name placeholder
        self._inventory_cache[adc_id] = {
            "---": {
                "stock": 0,
                "min_par": 0,
                "max_par": 0,
                "alarm_msg": "No medications registered"
            }
        }
        self._sync_to_storage()
        print(f"[INVENTORY SUCCESS] ADC cabinet '{adc_id}' initialized with no medications registered.")
        
        if self._event_logger:
            self._event_logger.log_event("INVENTORY", adc_id, "Initialized new ADC cabinet.", "SYSTEM")
    def add_medication(self, adc_id: str, med_name: str, stock: int, min_par: int, max_par: int, operator_id: str = "PHARMACIST-01") -> bool:
        adc_id = adc_id.strip().upper()
        
        if adc_id not in self._inventory_cache:
            print(f"[INVENTORY ERROR] ADC '{adc_id}' has not been initialized. Please initialize it first using 'init_adc'.")
            return False

        cabinet = self._inventory_cache[adc_id]

        # Remove the '---' placeholder if it's the first real medication being added
        if "---" in cabinet:
            del cabinet["---"]

        if med_name in cabinet:
            print(f"[INVENTORY ERROR] Medication '{med_name}' already exists in '{adc_id}'.")
            return False

        cabinet[med_name] = {
            "stock": stock,
            "min_par": min_par,
            "max_par": max_par,
            "alarm_msg": "NORMAL"
        }
        self._sync_to_storage()
        print(f"[INVENTORY SUCCESS] Added {med_name} to {adc_id} (Stock: {stock}).")
        
        if self._event_logger:
            self._event_logger.log_event("INVENTORY", adc_id, f"Added medication {med_name} with stock {stock}.", operator_id)
        return True
    
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

    def update_stock_level(self, adc_id: str, med_name: str, new_stock: int, operator_id: str = "PHARMACIST-01") -> bool:
        if not self.medication_exists(adc_id, med_name):
            print(f"[INVENTORY ERROR] Medication '{med_name}' not found in '{adc_id}'.")
            return False

        med_data = self._inventory_cache[adc_id][med_name]
        old_stock = med_data["stock"]
        med_data["stock"] = new_stock

        if new_stock >= med_data["min_par"] and "LOW_INVENTORY" in med_data.get("alarm_msg", ""):
            med_data["alarm_msg"] = "NORMAL"

        self._sync_to_storage()
        print(f"[INVENTORY SUCCESS] {adc_id} - {med_name} stock updated: {old_stock} -> {new_stock}")
        
        if self._event_logger:
            self._event_logger.log_event("INVENTORY", adc_id, f"Updated stock for {med_name} from {old_stock} to {new_stock}.", operator_id)
        return True

    def adc_exists(self, adc_id: str) -> bool:
        """
        Public Interface method to check if an ADC cabinet has been initialized in inventory.
        """
        return adc_id in self._inventory_cache
    
    def medication_exists(self, adc_id: str, med_name: str) -> bool:
        """
        Public Interface method to check if a medication exists within a specific ADC cabinet.
        """
        return adc_id in self._inventory_cache and med_name in self._inventory_cache[adc_id]

    def process_incoming_alarm(self, alarm: Alarm, med_name: str) -> bool:
        """
        Applied when an alarm is transmitted by an ADC. Updates state and syncs to storage.
        """
        adc_id = alarm.adcID
        if not self.medication_exists(adc_id, med_name):
            print(f"[INVENTORY ERROR] Medication '{med_name}' not found in '{adc_id}'. Alarm ingestion rejected.")
            return False

        med_data = self._inventory_cache[adc_id][med_name]
        severity = "CRITICAL" if alarm.isCritical else "MINOR"
        
        clean_alarm_type = self._format_alarm_name(alarm.alarmType)
        med_data["alarm_msg"] = f"ACTIVE: {clean_alarm_type} ({severity})"
        
        self._sync_to_storage()
        print(f"[INVENTORY UPDATE] Applied alarm status to {adc_id} -> {med_name}")
        
        return True

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


