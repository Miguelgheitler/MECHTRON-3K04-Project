"""Scenario tests. Run from the project folder:  python -m unittest -v

Each test names the D1 requirements it checks.
"""
import os
import shutil
import tempfile
import unittest

from adc import config as cfg
from adc.clock import SimClock
from adc.hardware import SimulatedCabinet
from adc.system import ADCSystem
from monitoring.simulated_ms import SimulatedMonitoringSystem


class Rig(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.clock = SimClock(1_000_000.0)
        self.hw = SimulatedCabinet(cfg.LOCATIONS)
        self.ms = SimulatedMonitoringSystem(cfg.SHARED_KEY)
        self.adc = ADCSystem(self.dir, self.hw, self.ms, self.clock)
        self.ms.send_order("ORD-1", "AMOX-500", 2)
        self.ms.send_order("ORD-2", "MORPH-10", 1)
        self.run_for(0.2)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_for(self, seconds, step=0.1):
        for _ in range(int(round(seconds / step))):
            self.clock.advance(step)
            self.adc.tick()

    def unlocked(self):
        return [l for l in self.hw.locations() if self.hw.read_lock(l) is False]

    def kinds(self, kind):
        return [r for r in self.adc.log.all() if r["kind"] == kind]

    def login(self, badge, pin):
        self.assertTrue(self.adc.login(badge, pin)["ok"])

    def ms_kinds(self, kind):
        return [m for m in self.ms.received if m["kind"] == kind]


class Dispensing(Rig):
    def test_SC1_R8_SC2_R2_normal_dispense(self):  # FR-DSP-02/03/04, FR-INV-03, NFR-SAF-04/05, FR-LOG-01, NFR-AUD-01, FR-COM-02/08
        self.login("N1001", "1234")
        r = self.adc.dispense("ORD-1", 1)
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.unlocked(), ["A1"])
        self.run_for(0.3)
        self.assertTrue(self.hw.sim_open_drawer("A1"))
        self.run_for(0.3)
        self.hw.sim_close_drawer("A1")
        self.run_for(0.3)
        self.assertEqual(self.unlocked(), [])
        self.assertEqual(self.adc.inventory.quantity("A1"), 19)
        self.assertEqual(self.adc.orders.check("ORD-1", 1)["remaining"], 1)
        rec = [r for r in self.kinds("DISPENSE") if r["result"] == "Completed"][-1]
        for f in ("user_id", "order_id", "medication_id", "quantity", "result", "time"):
            self.assertIn(f, rec)
        self.assertTrue(self.ms_kinds("INVENTORY"))
        self.assertTrue(any(m["payload"].get("result") == "Completed" for m in self.ms_kinds("EVENT")))

    def test_SC1_R4_no_order_rejected(self):  # FR-DSP-02, NFR-SAF-01, NFR-USB-03
        self.login("N1001", "1234")
        r = self.adc.dispense("ORD-999", 1)
        self.assertFalse(r["ok"])
        self.assertIn("Unauthorized", r["message"])
        self.assertEqual(self.unlocked(), [])
        self.assertEqual(self.kinds("DISPENSE")[-1]["result"], "Rejected")

    def test_SC1_R5_quantity_above_order(self):  # FR-DSP-05
        self.login("N1001", "1234")
        r = self.adc.dispense("ORD-1", 5)
        self.assertFalse(r["ok"])
        self.assertIn("exceeds", r["message"])
        self.assertEqual(self.unlocked(), [])

    def test_SC2_R4_never_opened_cancelled(self):  # NFR-SAF-05
        self.login("N1001", "1234")
        self.adc.dispense("ORD-1", 1)
        self.run_for(31)
        self.assertEqual(self.unlocked(), [])
        self.assertEqual(self.kinds("DISPENSE")[-1]["result"], "Cancelled")
        self.assertEqual(self.adc.inventory.quantity("A1"), 20)

    def test_SC2_R3_replenish(self):  # FR-INV-02, FR-LOG-02, NFR-AUD-02
        self.login("P2001", "2222")
        self.assertTrue(self.adc.replenish("B2", 4)["ok"])
        self.hw.sim_open_drawer("B2"); self.run_for(0.2)
        self.hw.sim_close_drawer("B2"); self.run_for(0.2)
        self.assertEqual(self.adc.inventory.quantity("B2"), 12)
        self.assertEqual(self.kinds("REPLENISH")[-1]["quantity_change"], 4)


class Access(Rig):
    def test_SC5_R3_lockout_after_three(self):  # FR-AUT-04, FR-LOG-04
        for _ in range(3):
            self.assertFalse(self.adc.login("N1001", "0000")["ok"])
        r = self.adc.login("N1001", "1234")
        self.assertFalse(r["ok"]); self.assertIn("locked", r["message"])
        self.assertGreaterEqual(len(self.kinds("AUTH_FAILED")), 3)
        self.clock.advance(15 * 60 + 1)
        self.assertTrue(self.adc.login("N1001", "1234")["ok"])

    def test_SC1_R1_wrong_role(self):  # FR-AUT-02/03
        self.login("P2001", "2222")
        r = self.adc.dispense("ORD-1", 1)
        self.assertFalse(r["ok"]); self.assertIn("Not permitted", r["message"])

    def test_NFR_SEC_02_orders_hidden_before_login(self):  # NFR-SEC-02
        self.assertEqual(self.adc.snapshot()["orders"], [])
        self.login("N1001", "1234")
        self.assertEqual(len(self.adc.snapshot()["orders"]), 2)


class Faults(Rig):
    def test_SC3_drawer_open_SC4_R3_R5_clear(self):  # FR-FLT-02/03/06/07, FR-MOD-03/04/05, NFR-AVL-03, FR-COM-07, NFR-AUD-03
        self.login("N1001", "1234")
        self.adc.dispense("ORD-1", 1)
        self.hw.sim_open_drawer("A1")
        self.run_for(31)
        self.assertEqual(self.adc.modes.mode, "FAULT")
        self.assertTrue(self.adc.alarm)
        self.assertTrue(self.ms_kinds("ALARM"))
        self.assertEqual(self.kinds("DISPENSE")[-1]["result"], "Faulted")
        r = self.adc.dispense("ORD-2", 1)                    # healthy drawer still usable
        self.assertTrue(r["ok"], r)
        self.hw.sim_open_drawer("A2"); self.run_for(0.2); self.hw.sim_close_drawer("A2"); self.run_for(0.2)
        self.login("N1001", "1234")
        fid = self.adc.faults.active()[0].fault_id
        self.assertFalse(self.adc.clear_fault(fid)["ok"])     # nurse cannot clear
        self.login("T3001", "3333")
        self.assertFalse(self.adc.clear_fault(fid)["ok"])     # self-check fails: drawer open
        self.hw.sim_close_drawer("A1"); self.run_for(0.2)
        self.assertTrue(self.adc.clear_fault(fid)["ok"])
        self.assertEqual(self.adc.modes.mode, "NORMAL")
        rec = self.kinds("FAULT_CLEARED")[-1]
        self.assertEqual(rec["cleared_by"], "T3001")

    def test_SC3_lock_fault(self):  # FR-FLT-01, NFR-PRF-02
        self.hw.sim_jam_lock("A1")
        self.login("N1001", "1234")
        self.adc.dispense("ORD-1", 1)
        self.run_for(2.4)
        types = [f.fault_type for f in self.adc.faults.active()]
        self.assertIn("LOCK", types)

    def test_SC3_sensor_fault(self):  # FR-FLT-04
        self.hw.sim_kill_sensor("B1")
        self.run_for(2.4)
        self.assertTrue(self.adc.faults.is_faulted("B1"))
        self.assertFalse(self.adc.faults.is_faulted("A1"))

    def test_SC3_watchdog_fault(self):  # FR-FLT-05
        self.adc.simulate_hang(1.5)
        self.run_for(1.4)
        self.assertIn("WATCHDOG", [f.fault_type for f in self.adc.faults.active()])


class Modes(Rig):
    def test_INV5_maintenance(self):  # FR-MOD-02/06/07
        self.login("N1001", "1234")
        self.assertFalse(self.adc.enter_maintenance()["ok"])
        self.adc.dispense("ORD-1", 1)
        self.login("T3001", "3333")
        self.assertFalse(self.adc.enter_maintenance()["ok"])   # dispense in progress
        self.run_for(31)                                        # never opened: cancelled
        self.assertTrue(self.adc.enter_maintenance()["ok"])
        self.login("N1001", "1234")
        self.assertFalse(self.adc.dispense("ORD-1", 1)["ok"])
        self.login("T3001", "3333")
        self.assertTrue(self.adc.exit_maintenance()["ok"])
        self.assertEqual(self.adc.modes.mode, "NORMAL")
        self.assertTrue(self.kinds("MODE_CHANGE"))             # FR-LOG-05


class Communication(Rig):
    def test_SC6_link_loss_and_replay(self):  # FR-COM-03/04/05/09, NFR-SAF-03, NFR-PRF-03
        self.ms.online = False
        self.run_for(31)
        self.assertFalse(self.adc.comms.available())
        self.assertEqual(self.unlocked(), [])                   # link loss never unlocks
        self.login("N1001", "1234")
        self.assertTrue(self.adc.dispense("ORD-1", 1)["ok"])   # local order still works
        self.hw.sim_open_drawer("A1"); self.run_for(0.2); self.hw.sim_close_drawer("A1"); self.run_for(0.2)
        self.assertGreater(self.adc.comms.queued(), 0)
        before = len(self.ms.received)
        self.ms.online = True
        self.run_for(0.3)
        self.assertEqual(self.adc.comms.queued(), 0)
        seqs = [m["seq"] for m in self.ms.received[before:]]
        self.assertEqual(seqs, sorted(seqs))                    # original order
        self.assertTrue(self.adc.comms.available())

    def test_SC6_forged_order_rejected(self):  # NFR-SEC-01
        self.ms.send_forged_order("ORD-X", "MORPH-10", 5)
        self.run_for(0.2)
        self.assertTrue(self.kinds("NETWORK_COMMAND_REJECTED"))
        self.assertNotIn("ORD-X", [o["order_id"] for o in self.adc.orders.active()])

    def test_SC6_duplicate_message_dropped(self):  # Week 7: duplicated / out-of-order messages
        self.ms.send_order("ORD-3", "HEP-5K", 1)
        self.run_for(0.2)
        self.ms.send_duplicate_of_last()
        self.run_for(0.2)
        self.assertTrue(self.kinds("MESSAGE_DROPPED"))
        self.assertFalse(self.kinds("ORDER_REJECTED"))

    def test_FR_COM_01_status_every_10s(self):  # FR-COM-01
        n = len(self.ms_kinds("STATUS"))
        self.run_for(20.1)
        self.assertGreaterEqual(len(self.ms_kinds("STATUS")) - n, 2)


class Restart(Rig):
    def test_NFR_SAF_02_power_loss(self):  # NFR-SAF-02, NFR-REL-03
        self.login("N1001", "1234")
        self.adc.dispense("ORD-1", 1)
        self.assertEqual(self.unlocked(), ["A1"])
        n = self.adc.log.count()
        self.adc = ADCSystem(self.dir, self.hw, self.ms, self.clock)
        self.assertEqual(self.unlocked(), [])
        self.assertGreaterEqual(self.adc.log.count(), n)
        self.assertEqual(len(self.adc.orders.active()), 2)

    def test_INV6_log_is_append_only(self):  # NFR-AUD-04
        self.assertFalse(hasattr(self.adc.log, "delete"))
        self.assertFalse(hasattr(self.adc.log, "update"))
        rec = self.adc.log.all()[0]
        rec["kind"] = "TAMPERED"
        self.assertNotEqual(self.adc.log.all()[0]["kind"], "TAMPERED")


if __name__ == "__main__":
    unittest.main()
