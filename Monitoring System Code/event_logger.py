import datetime

class EventLogger:
    def __init__(self):
        self._logs = [] 

    def log_event(self, event_type: str, details: str):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {event_type.upper()}: {details}"
        self._logs.append(entry)

    def get_logs(self):
        return self._logs