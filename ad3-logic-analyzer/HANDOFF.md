# Handoff — driving the Analog Discovery 3 as a logic analyzer

**You are a fresh Claude Code session.** Goal: help the user figure out **what data is
moving on 9 digital lines** by capturing them with a **Digilent Analog Discovery 3 (AD3)**
and characterizing each line (clock? data? chip-select? idle? what bit rate?).

This is the *digital* side of the AD3 (16 DIO logic-analyzer channels) — different from the
analog scope. A working, tested reference script ships next to this file:
**`logic_capture.py`**.

---

## 0. The one rule that wastes the most time

**Only one application can own the AD3 at a time.** If the **WaveForms GUI** is open, every
`openDwfDevice()` call fails with `JTAG init failed / device may be used by another
application / DjtgEnable failed`. The script already catches this and prints
*"close the WaveForms GUI first"* — but know it up front. Workflow:

- **You (Claude)** run the Python capture when WaveForms is **closed**.
- **The user** uses the WaveForms GUI (its built-in Logic + protocol decoders are excellent)
  when *they* want to eyeball — but then they must close it before handing the device back.

Decide with the user who holds the device, don't ping-pong it.

---

## 1. Environment (verified on this PC, 2026-06)

| Thing | Fact |
|---|---|
| Python | `python` = 3.14 on PATH |
| Driver | `dwf.dll` present (`C:\Windows\System32\dwf.dll`); WaveForms 3 + SDK installed |
| Binding | **`pydwf`** installed (`pip install pydwf` if a fresh machine) |
| Device | AD3, opens via `pydwf.utilities.openDwfDevice` |
| numpy | only needed for `--save` (raw dump); `pip install numpy` if used |

Quick liveness check (run this first — confirms device + that WaveForms is closed):

```python
from pydwf import DwfLibrary
from pydwf.utilities import openDwfDevice
with openDwfDevice(DwfLibrary()) as d:
    print("AD3 open OK:", d.digitalIn.internalClockInfo()/1e6, "MHz base clock")
```

---

## 2. Wiring (tell the user exactly this)

- **AD3 DIO 0..8** (the grey ribbon flying leads — each is labelled `DIO 0`, `DIO 1`, …)
  to the **9 pins under test**, one per line. Keep a note of which DIO → which physical pin.
- **AD3 GND (black ⏚ lead) → the target's GND.** **Mandatory.** A floating ground produces
  phantom edges and nonsense bit rates. If the 9 pins span two boards, tie both grounds.
- **Logic level:** AD3 digital inputs use ~3.3 V-logic thresholds, tolerant 0..5 V, read-only
  (they don't drive). For **1.8 V or lower** logic the thresholds are marginal — flag that to
  the user and don't over-trust the result.

---

## 3. The capture recipe (what `logic_capture.py` does)

The pydwf `DigitalIn` (logic analyzer) flow, with the **verified** method names:

```python
din = device.digitalIn
din.reset()
base = din.internalClockInfo()                 # 100 MHz on the AD3
din.dividerSet(round(base / rate_hz))          # sample rate = base / divider
din.sampleFormatSet(16)                         # 16 bits/sample: bit k = DIO k
din.bufferSizeSet(min(n, din.bufferSizeInfo()))
din.acquisitionModeSet(DwfAcquisitionMode.Single)
din.triggerSourceSet(DwfTriggerSource.None_)    # or DetectorDigitalIn to trigger on an edge
din.configure(False, True)                      # start
while din.status(True) != DwfState.Done: ...
samples = din.statusData(n)                     # list of uint16; (s >> k) & 1 = DIO k
```

Enum gotchas that bite (verified against this pydwf build):
- "no trigger" is **`DwfTriggerSource.None_`** (trailing underscore), *not* `NoneTrigger`.
- digital-edge trigger source is **`DwfTriggerSource.DetectorDigitalIn`**.
- edge masks go through **`triggerSet(low, high, rising, falling)`** as bitmasks, e.g.
  falling edge on DIO7 → `triggerSet(0, 0, 0, 1<<7)`.

### Sample-rate rule of thumb
Sample at **≥ 8–10× the fastest edge rate** you expect, or pulse-width readings alias. Don't
know the speed yet? Start fast (`--rate 50e6`) and short, read the `min-pulse` numbers, then
back off. AD3 max is 100 MHz; buffer is finite (`bufferSizeInfo()`), so fast rate = short
window — tune both together.

---

## 4. The investigation workflow (this is the actual job)

1. **Blind sweep.** `python logic_capture.py --channels 0-8 --rate 50e6 --samples 1000000`.
   Read the per-channel summary: idle level, edge count, min-pulse, estimated kbit/s, and the
   crude `clock?`/`data?` guess.
2. **Classify the lines** from that table:
   - *no activity* → unused / static select / power-strap.
   - very regular, high edge count → **clock**. Its rate sets everyone else's bit period.
   - bursts of edges that go quiet → **data** or **chip-select** (CS idles high, pulses low
     around a transaction).
3. **Re-capture triggered on the likely CS/clock** to frame one transaction:
   `--trigger 7:falling` (catch the burst that starts when DIO7 drops).
4. **Guess the protocol** from the line roles:
   - 1 clock + 1+ data + 1 CS, MSB-aligned to clock edges → **SPI** (note CPOL/CPHA from which
     edge data is stable on).
   - 2 lines, one clock one bidirectional data, start = data falls while clock high → **I²C**
     (then read the 7-bit address + R/W in the first 8 bits).
   - 1 line, idle high, start bit then 8 data bits at a fixed period, no clock → **UART**
     (bit rate = 1/min-pulse → nearest standard baud: 9600/115200/…).
5. **Decode.** Two routes:
   - **Hand the user to the WaveForms GUI** — it has SPI/I²C/UART/CAN decoders that overlay
     directly on the capture. Fastest for a human. (They close WaveForms when done.)
   - **Decode in Python** from a `--save cap.npy` dump — write a small per-protocol decoder
     once the roles are known. Good for automation / bulk captures.
6. **Report** which DIO mapped to which pin, each line's role, the protocol, bit rate, and any
   decoded bytes. Note explicitly anything uncertain (marginal levels, aliasing, ambiguous
   CPOL/CPHA) rather than asserting it.

---

## 5. Reference script

`logic_capture.py` (next to this file) — tested: imports clean, handles device-busy, prints a
characterization table. Examples:

```bash
python logic_capture.py --channels 0-8 --rate 50e6 --samples 1000000   # blind sweep
python logic_capture.py --channels 0-8 --rate 50e6 --trigger 7:falling # frame a transaction
python logic_capture.py --channels 0-8 --rate 50e6 --save cap.npy      # raw dump for decode
```

It's a starting point, not the finish — extend it with a protocol decoder once you know the
line roles. Keep the "no silent assumptions" discipline: if a level is marginal or a rate
aliases, say so.

---

## 6. If something's off

- `device may be used by another application` → WaveForms GUI is open. Close it.
- All lines read identical / impossibly fast edges → **ground not connected** between AD3 and
  target. Fix first, everything downstream is noise until you do.
- Edges only on capture start then flat → you're under-sampling a slow line over a tiny window;
  raise `--samples` or lower `--rate`.
- A line reads constant but you expect data → it may idle between bursts; use a trigger and
  wait, or capture a longer window.
