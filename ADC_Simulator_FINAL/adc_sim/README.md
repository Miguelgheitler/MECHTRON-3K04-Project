# ADC Simulator (SFWRENG 3K04, Part A, Subteam 45)

A working simulation of the Automated Dispensing Cabinet software. Pure Python 3.10+,
no packages to install.

## Run it
```
python run.py
```
Then open **http://localhost:8000**. (Use `python run.py 8080` for another port.)
Run the scenario tests with `python -m unittest -v` (19 tests, named after the spec rows they check).

Demo users: Nurse `N1001 / 1234` · Pharmacy Technician `P2001 / 2222` · Technician `T3001 / 3333`

## The screen
| Panel | What it is |
|---|---|
| 1 · Cabinet screen | The real ADC touchscreen: log in, request medication, restock, maintenance, clear faults |
| 2 · Cabinet hardware | The physical world, simulated: open/close drawers, jam a lock, kill a sensor, freeze the software, power cycle, skip time |
| 3 · Monitoring System | A stand-in for Part B: go offline/online, send orders, send a forged order, see what the ADC sends |
| Event log | Every record the ADC writes (append-only, saved to `data/`) |

## Modules (each hides one likely change)
| File | Module | Secret (what it hides) | Main requirements |
|---|---|---|---|
| `adc/config.py` | Configuration | timing values, policies, seed data | A5, FR-AUT-04, FR-FLT-01..05 |
| `adc/clock.py` | Clock | where time comes from | timestamps |
| `adc/hardware.py` | Hardware interface | how locks and sensors are driven/read | FR-DSP-03/04, FR-FLT-01/04 |
| `adc/storage.py` | Storage | file location and format | NFR-REL-01/03 |
| `adc/event_log.py` | Event Logger | record layout; no edit/delete | FR-LOG-01..05, NFR-AUD-01..04 |
| `adc/inventory.py` | Inventory Manager | how stock is represented | FR-INV-01..04 |
| `adc/orders.py` | Order Book | order format and matching | FR-DSP-02/05, FR-COM-05/06 |
| `adc/access_control.py` | Access Control | login method, lockout, role table | FR-AUT-01..04, FR-LOG-04 |
| `adc/mode_manager.py` | Mode Manager | modes and transitions (D1 Fig 8) | FR-MOD-01..07, FR-LOG-05 |
| `adc/fault_monitor.py` | Fault Monitor | how each fault is detected | FR-FLT-01..07, NFR-PRF-02 |
| `adc/dispensing.py` | Dispensing Controller | drawer transaction steps (D1 Fig 9) | FR-DSP-01..05, NFR-SAF-01/04/05, NFR-AVL-03 |
| `adc/codec.py` | Message Codec | message format and signature | NFR-SEC-01 |
| `adc/comms.py` | Comms Link | transport, buffering, ordering, link loss | FR-COM-01..09, NFR-AVL-01/02 |
| `adc/system.py` | ADC System | how modules are wired; the control cycle | coordination |
| `ui/` | User Interface | how the screen looks and takes input | NFR-USB-02/03, NFR-SEC-02 |
| `monitoring/simulated_ms.py` | (not ADC) Part B stand-in | — | — |

The USES hierarchy has no cycles: `ui -> ADCSystem -> {modules}`, and no lower module calls a higher one.

Both state machines are a `TRANSITIONS` table (`mode_manager.py` = D1 Figure 8, `dispensing.py` = D1 Figure 9).

## Demo script (what the TAs will ask for)
**1. Normal dispense: authenticate → dispense → log**
Log in N1001/1234 → pick ORD-1001 → Request medication → only drawer A1 unlocks →
hardware panel: A1 **Open**, then **Close** → A1 relocks, stock 20→19, log shows `DISPENSE result=Completed`,
Monitoring panel receives the event and the inventory update.

**2. Rejected request** · type a quantity above the order (e.g. 5) → "Quantity exceeds authorized order", nothing unlocks.

**3. Drawer left open (fault)** · dispense ORD-1001 → Open A1, don't close → **Skip +30 s** → FAULT mode,
red alarm + beep, ALARM at the Monitoring System. Other drawers still work (dispense ORD-1002 from A2).
Log in T3001/3333 → Clear → rejected (self-check fails, drawer open) → Close A1 → Clear → back to NORMAL.

**4. Communication loss** · Monitoring panel **Go offline** → **Skip +30 s** → link LOST, queued messages grow →
dispensing still works with stored orders, nothing unlocks on its own → **Go online** → queue empties in order.

**5. Other faults** · **Jam lock** on A1 then dispense (LOCK fault in 2 s) · **Kill sensor** on B1 (SENSOR fault in 2 s) ·
**Freeze software** (WATCHDOG fault in 1 s). **Repair** + technician Clear.

**6. Security** · wrong PIN 3 times → account locked 15 min · Pharmacy Tech trying to dispense → "Not permitted" ·
**Send forged order** → rejected, logged `NETWORK_COMMAND_REJECTED` · **Re-send last order** → dropped as a duplicate, logged `MESSAGE_DROPPED`.

**7. Maintenance** · Technician: Enter maintenance → nurse dispense rejected → Exit maintenance.

**8. Power loss** · start a dispense (drawer unlocked) → **Power cycle** → every drawer locked, log and orders still there.

**Reset demo** wipes `data/` and starts fresh.
