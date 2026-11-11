"""Configuration module.

Secret: the numeric values of the timing limits, policies and seed data.
Anticipated change: a regulator or the hospital changes a timeout, a lockout
policy, the drawer layout or the user list. Only this file changes.
"""

# Timing values (D1 Assumption A5)
LOCK_TIMEOUT_S = 2.0            # FR-FLT-01
DRAWER_CLOSE_TIMEOUT_S = 30.0   # FR-FLT-02
SENSOR_TIMEOUT_S = 2.0          # FR-FLT-04
WATCHDOG_TIMEOUT_S = 1.0        # FR-FLT-05
MAX_FAILED_LOGINS = 3           # FR-AUT-04
LOCKOUT_S = 15 * 60             # FR-AUT-04
STATUS_PERIOD_S = 10.0          # FR-COM-01
LINK_TIMEOUT_S = 30.0           # FR-COM-09
SESSION_TIMEOUT_S = 120.0       # D2 assumption: idle session ends after 2 min
OUTBOX_CAPACITY = 50_000        # NFR-AVL-01: > 24 h of status + event traffic

# Roles and the protected actions each may perform (FR-AUT-02)
PERMISSIONS = {
    "dispense": {"Nurse"},
    "replenish": {"PharmacyTechnician"},
    "maintenance": {"Technician"},
    "clear_fault": {"Technician"},
    "shutdown": {"Technician"},
}

# Users provisioned by the hospital, held locally (D1 Assumption A9)
USERS = {
    "N1001": {"pin": "1234", "role": "Nurse", "name": "Nurse"},
    "P2001": {"pin": "2222", "role": "PharmacyTechnician", "name": "Pharmacy Technician"},
    "T3001": {"pin": "3333", "role": "Technician", "name": "Technician"},
}

# One medication per storage location (D1 Assumption A6)
LOCATIONS = {
    "A1": {"medication_id": "AMOX-500", "name": "Amoxicillin 500 mg", "quantity": 20},
    "A2": {"medication_id": "MORPH-10", "name": "Morphine 10 mg", "quantity": 10},
    "B1": {"medication_id": "INSUL-100", "name": "Insulin 100 U", "quantity": 15},
    "B2": {"medication_id": "HEP-5K", "name": "Heparin 5000 U", "quantity": 8},
}

# Key shared with the paired Monitoring System (NFR-SEC-01)
SHARED_KEY = b"adc-subteam-45-demo-key"
