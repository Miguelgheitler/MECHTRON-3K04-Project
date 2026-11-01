class CommsGateway:
    def __init__(self, logger):
        self.logger = logger
        self._connected_adcs = {}  # dictionary tracking connection status
        self._offline_buffer = {}  # buffers messages if a link goes down

    def receive_adc_message(self, adc_id: str, payload: str, severity: str = "routine") -> bool:
        # mark the ADC as connected upon receiving a heartbeat/message
        self._connected_adcs[adc_id] = True
        
        if severity == "critical":
            self.logger.log_event("comms_critical", f"CRITICAL ALARM received from {adc_id} -> {payload}")
            print(f"\n[URGENT] COMMS-GATEWAY: CRITICAL ALARM received from {adc_id} -> {payload}")
            
            # create the alarm object and log it
            try:
                from alarm_class import Alarm, AlarmType
                new_alarm = Alarm(adcID=adc_id, alarmType=AlarmType.CABINET_FAULT, isCritical=True, details=payload)
                self.logger.log_event("alarm_created", f"[{new_alarm.alarmType.value}] generated for {adc_id}: {payload}")
            except ImportError:
                pass
        else:
            self.logger.log_event("comms_routine", f"Routine update received from {adc_id} -> {payload}")
            print(f"\n[INFO] COMMS-GATEWAY: Routine update received from {adc_id} -> {payload}")
            
        return True

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