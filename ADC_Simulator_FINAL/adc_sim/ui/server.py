"""User-interface module (local touchscreen + demo panels), served as a web page.

Secret: how the screen is drawn and how input arrives (here: a browser page
talking JSON over HTTP on localhost).
Anticipated change: the screen is replaced or the UI is translated. Only this
module and index.html change; the ADC is reached only through ADCSystem.

The page has three areas:
  1. Cabinet screen    what nurses, pharmacy technicians and technicians use
  2. Hardware panel    simulates the physical world (open/close drawers, jam a
                       lock, kill a sensor, software hang, power cycle, time skip)
  3. Monitoring System stand-in for Part B (online/offline, send orders)
"""
import json
import os
import shutil
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from adc import config as cfg
from adc.clock import SimClock
from adc.hardware import SimulatedCabinet
from adc.system import ADCSystem
from monitoring.simulated_ms import SimulatedMonitoringSystem

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
TICK_S = 0.1

SEED_ORDERS = [("ORD-1001", "AMOX-500", 2), ("ORD-1002", "MORPH-10", 1), ("ORD-1003", "INSUL-100", 3)]


class Demo:
    def __init__(self):
        self.lock = threading.RLock()
        self.reset()

    def reset(self):
        shutil.rmtree(DATA, ignore_errors=True)
        self.clock = SimClock()
        self.hw = SimulatedCabinet(cfg.LOCATIONS)
        self.ms = SimulatedMonitoringSystem(cfg.SHARED_KEY)
        self.adc = ADCSystem(DATA, self.hw, self.ms, self.clock)
        for o in SEED_ORDERS:
            self.ms.send_order(*o)

    def power_cycle(self):
        # physical drawers keep their state; the ADC software restarts from saved data
        self.adc = ADCSystem(DATA, self.hw, self.ms, self.clock)

    def tick(self, dt):
        with self.lock:
            self.clock.advance(dt)
            self.adc.tick()

    def state(self):
        with self.lock:
            return {"adc": self.adc.snapshot(), "hw": self.hw.sim_state(), "ms": self.ms.view(),
                    "users": {k: {"pin": v["pin"], "role": v["role"]} for k, v in cfg.USERS.items()},
                    "medications": {k: v["medication_id"] for k, v in cfg.LOCATIONS.items()}}

    def act(self, name, a):
        with self.lock:
            adc, hw, ms = self.adc, self.hw, self.ms
            ok = lambda m: {"ok": True, "message": m}
            if name == "login":       return adc.login(a.get("badge", ""), a.get("pin", ""))
            if name == "logout":      return adc.logout()
            if name == "dispense":    return adc.dispense(a.get("order_id", ""), a.get("qty", 0))
            if name == "replenish":   return adc.replenish(a.get("location", ""), a.get("qty", 0))
            if name == "maint_enter": return adc.enter_maintenance()
            if name == "maint_exit":  return adc.exit_maintenance()
            if name == "clear_fault": return adc.clear_fault(a.get("fault_id", 0))
            if name == "shutdown":    return adc.shutdown()
            loc = a.get("location")
            if name == "hw_open":
                return ok(f"Drawer {loc} pulled open") if hw.sim_open_drawer(loc) else {"ok": False, "message": f"Drawer {loc} is locked and will not open"}
            if name == "hw_close":    hw.sim_close_drawer(loc); return ok(f"Drawer {loc} pushed closed")
            if name == "hw_jam":      hw.sim_jam_lock(loc, True); return ok(f"Lock {loc} jammed")
            if name == "hw_sensor":   hw.sim_kill_sensor(loc, True); return ok(f"Sensor {loc} disconnected")
            if name == "hw_repair":   hw.sim_repair(loc); return ok(f"{loc} repaired (lock + sensor)")
            if name == "hang":        adc.simulate_hang(1.5); return ok("Software frozen for 1.5 s")
            if name == "power":       self.power_cycle(); return ok("Power cycled: ADC restarted from saved data")
            if name == "skip":        self.clock.advance(float(a.get("seconds", 10))); adc.tick(); return ok(f"Skipped {a.get('seconds')} s")
            if name == "reset":       self.reset(); return ok("Demo reset")
            if name == "ms_online":   ms.online = bool(a.get("online")); return ok("Monitoring System " + ("online" if ms.online else "offline"))
            if name == "ms_order":    ms.send_order(a.get("order_id"), a.get("medication_id"), int(a.get("qty", 1))); return ok("Order sent")
            if name == "ms_dup":      ms.send_duplicate_of_last(); return ok("Last order re-sent with the same sequence number")
            if name == "ms_forged":   ms.send_forged_order(a.get("order_id"), a.get("medication_id"), int(a.get("qty", 1))); return ok("Forged order sent")
            return {"ok": False, "message": f"unknown action {name}"}


DEMO = Demo()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if self.path == "/favicon.ico":
            return self._send(204, b"", "image/x-icon")
        if self.path == "/api/state":
            return self._send(200, DEMO.state())
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self.path.startswith("/api/"):
            return self._send(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length", 0))
        args = json.loads(self.rfile.read(n) or b"{}")
        self._send(200, DEMO.act(self.path[5:], args))


def _ticker():
    last = time.monotonic()
    while True:
        time.sleep(TICK_S)
        now = time.monotonic()
        DEMO.tick(now - last)
        last = now


def serve(port=8000):
    threading.Thread(target=_ticker, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"ADC simulator running: open http://localhost:{port} in your browser (Ctrl+C to stop)")
    srv.serve_forever()
