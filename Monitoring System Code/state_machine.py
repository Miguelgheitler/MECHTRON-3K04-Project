"""
Module: State Machine (Behavior Hiding)
Responsibility: Tracks the system's high-level operational mode (Self-Test, Operational, 
Fault, Maintenance), enforces valid state transitions via a lookup table, and rejects 
invalid actions to satisfy the Completeness Property.
"""

from enum import Enum
from event_logger import EventLogger
from typing import Optional

class SystemState(str, Enum):
    SELF_TEST = "SELF_TEST"
    OPERATIONAL = "OPERATIONAL"
    FAULT = "FAULT"
    MAINTENANCE = "MAINTENANCE"

class StateMachine:
    def __init__(self, logger: EventLogger):
        # SECRET: 
        self.logger = logger
        self.current_state = SystemState.OPERATIONAL # starting in Operational
        
        # transition Table
        self._transitions = {
            (SystemState.SELF_TEST, "testPassed"): SystemState.OPERATIONAL,
            (SystemState.SELF_TEST, "testFailed"): SystemState.FAULT,
            (SystemState.OPERATIONAL, "hardwareFault"): SystemState.FAULT,
            (SystemState.OPERATIONAL, "techLogin"): SystemState.MAINTENANCE,
            (SystemState.FAULT, "techLogin"): SystemState.MAINTENANCE,
            (SystemState.MAINTENANCE, "exit"): SystemState.OPERATIONAL
        }

    def trigger_event(self, event: str, user_id: str = "SYSTEM") -> bool:
        """
        Attempts to transition the system state based on the provided event.
        Enforces the completeness property by logging invalid/ignored events.
        """
        transition_key = (self.current_state, event)
        
        if transition_key in self._transitions:
            new_state = self._transitions[transition_key]
            self.logger.log_event(
                "STATE_CHANGE", 
                "SYSTEM", 
                f"Transitioned from {self.current_state.value} to {new_state.value} via '{event}'", 
                user_id
            )
            self.current_state = new_state
            return True
        else:
            # completeness property
            self.logger.log_event(
                "INVALID_ACTION", 
                "SYSTEM", 
                f"Ignored invalid event '{event}' while in state {self.current_state.value}", 
                user_id
            )
            return False