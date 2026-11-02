"""
Module: Communications Gateway (Comms Gateway)
Responsibility: Handles incoming network/telemetry messages from remote ADCs 
and routes them through the event logger.
"""

from event_logger import EventLogger

class CommsGateway:
    def __init__(self, logger: EventLogger = None):
        self.logger = logger if logger else EventLogger()

    def receive_adc_message(self, adc_id: str, payload: str, severity: str = "routine"):
        """
        Receives messages/telemetry from an ADC and logs them securely.
        """
        if severity == "critical":
            # FIXED: Provide event_type, source_id, description, and user_id
            self.logger.log_event("ALARM", adc_id, f"Critical message received: {payload}", "SYSTEM")
        else:
            self.logger.log_event("COMMS", adc_id, f"Routine telemetry received: {payload}", "SYSTEM")
            
        print(f"[COMMS] Processed message from {adc_id} ({severity}): {payload}")

    def verify_connectivity(self, adc_id: str) -> bool:
        is_connected = self._connected_adcs.get(adc_id, False)
        if not is_connected:
            self.logger.log_event("comms_lost", f"ADC {adc_id} communication lost.")
            print(f"[WARNING] ADC {adc_id} is OFFLINE. Communication lost.")
        return is_connected

    def handle_link_restored(self, adc_id: str):
        # handles degraded behaviour recovery, replays buffered events when reconnected
        self._connected_adcs[adc_id] = True
        self.logger.log_event("comms_restored", f"Connection restored for {adc_id}.")
        print(f"[SYSTEM] Connection restored for {adc_id}. Replaying buffered events in order...")
        # implementation of buffer replay would go here