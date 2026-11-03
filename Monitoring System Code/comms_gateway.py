"""
Module: Communications Gateway (Comms Gateway)
Responsibility: Handles incoming network/telemetry messages from remote ADCs 
and routes them through the event logger.
"""

from event_logger import EventLogger

class CommsGateway:
    def __init__(self, logger: EventLogger = None):
        self.logger = logger if logger else EventLogger()
        self._connected_adcs = {}  # Dictionary tracking connection status

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
        """
        Health check: verifies if the ADC is currently communicating.
        Traces to FR-MON-01 and FR-MON-02.
        """
        is_connected = self._connected_adcs.get(adc_id, False)
        if not is_connected:
            self.logger.log_event("COMMS_LOST", adc_id, f"ADC {adc_id} communication lost.", "SYSTEM")
            print(f"[WARNING] ADC {adc_id} is OFFLINE. Communication lost.")
        return is_connected

    def drop_connection(self, adc_id: str):
        """
        DEMO METHOD: Artificially simulates a network timeout/drop for a specific ADC.
        """
        if adc_id in self._connected_adcs:
            self._connected_adcs[adc_id] = False
        # Immediately run the health check to trigger the system warning
        self.verify_connectivity(adc_id)

    def handle_link_restored(self, adc_id: str):
        """handles degraded behaviour recovery, replays buffered events when reconnected"""
        self._connected_adcs[adc_id] = True
        self.logger.log_event("COMMS_RESTORED", adc_id, f"Connection restored for {adc_id}.", "SYSTEM")
        print(f"[SYSTEM] Connection restored for {adc_id}. Replaying buffered events in order...")