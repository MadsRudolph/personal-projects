# Making the KORAD KD3005D programmable — design

Date: 2026-08-08
Status: design agreed; Phase 0 bench verification pending (2026-08-09)
Supersedes: the J9/UART approach in `korad-esp32-carrier/docs/2026-06-15-esp32-korad-carrier-design.md`

## Goal

PC control of a KORAD KD3005D bench supply — set voltage, set current, read back actual
V/I, and toggle the output — on a unit whose firmware has **no serial command interpreter**.

## 0. RESULT — the DAC protocol is solved (2026-08-09)

Phases 0 and 1 are complete. The setpoint bus was tapped, captured and decoded.

### Physical

Three chained `74HC595D` (U14 → U13 → U12) on the **front board**, driving 10K/20K
R-2R ladders. `OE` tied low, `MR` tied high. Tap U14 (first in chain):

| U14 pin | Signal | |
|---|---|---|
| 11 | `SHCP` shift clock | ~1.4 MHz, 720 ns bit period |
| 12 | `STCP` latch | one pulse per 24-bit word |
| 14 | `DS` data | idles HIGH |
| 8 | `GND` (**`GNDF` — floats at +Vout**) | |

**The MCU refreshes the bus continuously**, so the current setpoint can be read at
any moment — no need to catch a knob turn. A read takes ~3 ms.

### Frame

24 bits per word, one `STCP` pulse per word. The two DAC channels are
**interleaved bit by bit** in shift order:

- **odd bit indices (1,3,…,23)** = 12-bit **voltage** field, index 23 = LSB
- **even bit indices (0,2,…,22)** = 12-bit **current** field, index 22 = LSB

Data is shifted on `SHCP` rising, transferred on `STCP` rising (per datasheet).

### Mapping (measured against the front panel)

```
V code = 106.000 * Vset + 36.0      exact at 1.00 / 5.00 / 7.50 / 8.00 V
I code = 619.787 * Iset + 49.19     R^2 = 0.99999995, worst residual 0.7 mA
```

Resolution 9.43 mV/LSB and 1.61 mA/LSB; 4095 codes extrapolates to 38.3 V and
6.53 A — sensible headroom over the 30 V / 5 A rating. Occasional ±1 count
(0.00 V reads 35, not 36; 4 A and 5 A land one low) is the firmware interpolating
calibration constants from the `24C64` EEPROM. Below display resolution.

### Tooling (`ad3-logic-analyzer/`)

| Script | Purpose |
|---|---|
| `read_dac.py` | read the live setpoint off the bus, decoded |
| `cal_dac.py` | build a calibration set and fit both channels |
| `decode_595.py` | decode/diff raw `.npy` captures offline |
| `sweep_dac.py` | guided/free-run capture sweeps, holds the constants |
| `probe_check.py` | probe liveness; catches the analyzer driving the bus |

### Bench gotchas that cost real time

1. **`GNDF` floats at +Vout.** Grounding an earthed analyzer to it corrupts the
   DAC (supply stuck at 12 V, recovered on disconnect). Grounding to
   output-negative instead makes the 3.3 V swing ride +Vout, so captures work at
   0–1 V then read static HIGH from ~5 V up — which looks exactly like a broken
   wire. **Fix: capture with Vout ≈ 0** (CC into a short, or simply Vset = 0
   while sweeping current) so the common mode disappears.
2. **`digitalIn.reset()` does not clear static-IO output enables** left by the
   WaveForms GUI; force `digitalIO.outputEnableSet(0)` or the analyzer may drive
   the bus.
3. **Poll for a state other than `Done` after `configure()`** — otherwise the
   first status read returns the *previous* acquisition's buffer.
4. Probe with **1 kΩ series resistors** at the chip end; unterminated flying
   leads on `STCP` glitch the latch and commit half-shifted words.

### What remains

Writing to the bus rather than reading it — the interception question in §6,
now decidable with real timing data.

## 1. Established facts

### 1.1 J9 (the 4-pin header) is the serial port, and it is dead on this unit

The KA3005P main-board schematic confirms J9 = "connecting communication board", 4 pins:
pin 1 = GND, pin 4 = DVDD, pins 2/3 = the MCU's UART0 (`RXD,P3.0` on MCU pin 5 and
`TXD,P3.1` on MCU pin 7).

So J9 is genuinely the serial port — and the exhaustive poll still returned nothing:

- all 6 ordered TX/RX pairings of pins {2,3,4} → 0 bytes
- baud sweep 4800 / 9600 / 19200 / 38400 / 57600 / 115200 / 128000 → 0 bytes
- terminators none / LF / CR / CRLF → 0 bytes
- cable proven good by TXD↔RXD loopback; PSU confirmed on

This is a known D-model behaviour, independently reported: *"the mainboard actually doesn't
respond to a correct serial input. TX pin always stays high."* profi-max's mod only works on
a "KORAD3005DP" — a D that happens to ship with the interpreter. This unit is not one.

**J9 is closed.** Phase 0 includes one final 2-minute test to formally bury it.

### 1.2 The DAC is discrete, and its control bus leaves the board on the display connector

Three chained 74HC595 shift registers (U8 → U11 → U9) drive 10K/20K R-2R ladders.
`OE` is tied permanently low and `MR` permanently high, so the ladders are always live.
The MCU drives the chain from three pins:

| MCU pin | Net | Function |
|---|---|---|
| 40 | `SD2` | serial data |
| 39 | `STCP2` | storage/latch clock |
| 38 | `SHCP2` | shift clock |

Those three nets are routed to **J4, "connecting display board" (CON12)**:

| Pin | Net | Pin | Net |
|---|---|---|---|
| 1 | DVDD | 7 | DVDD |
| 2 | GND | 8 | display1 |
| 3 | `STCP2` | 9 | display2 |
| 4 | `SHCP2` | 10 | display3 |
| 5 | — | 11 | display4 |
| 6 | `SD2` | 12 | display5 |

The DAC and the display share one clock and one data line; `STCP2` latches the DAC and
`display1–5` latch the display digits. **The full DAC control bus is therefore reachable on
an unpluggable ribbon connector — no main-board surgery required.**

### 1.3 The 9-pin connector on our unit is almost certainly this bus

Our June captures match J4's signature:

- one line with ~20 ns pulses (pin 2) — the shift clock `SHCP2`
- multiple lines switching **synchronously** with it — data and latches
- three lines idling HIGH (pins 4/5/6) — display latch lines
- a single localised ~60 µs burst when OUTPUT is pressed — one display/LED refresh
- **no traffic at all while idle** — the bus is event-driven, not continuously multiplexed

That last point is the gift: traffic appears only when something changes, so isolating a
setpoint write is straightforward.

The June conclusion ("the 9-pin is the internal MCU↔power-board control bus — DAC set /
ADC sense") was half right, and the useful half: it *is* the DAC bus. It just reaches the
DAC by way of the display cable.

### 1.4 Other useful nodes

- `AD1`/`AD2`/`AD3` on MCU pins 43/44/45 — Vout/Iout analog sense, already scaled to 0–3.3 V.
- `U13` = 24C64 I²C EEPROM — factory calibration storage.
- `J6` = "connecting key board" (10-pin): `key_in1-3`, `key_out1-4`, `BkeyLift`, `BkeyRight`.
- `U12` = ULN2003-style driver for `REL1`/`REL2`/`REL3` (range relays), `FAN`, `BY` (buzzer).
- MCU: 8051-family, 8 MHz crystal (XT1), with `ICE_DAT`/`ICE_CLK` pins present.

### 1.5 Corrections to earlier conclusions

Three things in the June log are wrong and must not be carried forward:

1. **"J9's VSS rides on the output voltage; galvanic isolation is mandatory."** Wrong. The
   4-pin DC map measured pins 2/3/4 at 3.3 V at **both** Vout=0 V and Vout=12 V referenced to
   the negative terminal. If the domain rode on Vout, the second reading would have been
   ~15.3 V. The control domain is referenced to output-negative. There is no 30 V
   common-mode. (See §5 for the real, milder grounding caveat.)
2. **"The polled 4-pin was probably not J9."** Wrong. It is J9; the schematic confirms the
   pinout and the MCU UART0 behind it. The null result is a genuine negative on the right
   connector.
3. **"The 9-pin is the MCU↔power-board control bus."** Imprecise. It is the MCU↔display
   bus, which also carries the DAC's serial control lines.

## 2. Architecture

Three stages, each gating the next:

```
Phase 0  verify the connector identity on OUR board        (passive, no modification)
Phase 1  decode the DAC frames, build code → V/I mapping   (passive, no modification)
Phase 2  choose and build the interception mechanism       (modification)
Phase 3  ESP32 firmware + host control                     (software)
```

Phases 0 and 1 are entirely passive. Nothing is cut, soldered, or powered differently until
we have real decoded frames in hand.

## 3. Phase 0 — bench verification (next session)

**Equipment:** AD3 + WaveForms, DMM, 10 kΩ resistor, existing scripts in `ad3-logic-analyzer/`.

### 3.0 Close out J9 (2 minutes)

Hang a 10 kΩ resistor from J9's TX pin to J9 GND and measure the pin with the DMM.

- holds ~3.3 V → a real driven UART output (firmware has a UART that is simply mute)
- sags to ~1 V → an uninitialised GPIO on its weak internal pull-up (**firmware has no UART**)

Expected: sag. Either way, record it and stop revisiting J9.

### 3.1 Map the 9-pin against the J4 hypothesis

PSU **off**, DMM continuity, reference = negative output terminal:

| Pin | Continuity to (−)? | V (PSU on, Vout=0) | V (PSU on, Vout=12) | Predicted net |
|---|---|---|---|---|
| 1 | (known: 0 Ω) | | | GND |
| 2 | | | | `SHCP2` (clock) |
| 3 | | | | `SD2` or `STCP2` |
| 4 | | | | display latch |
| 5 | | | | display latch |
| 6 | | | | display latch |
| 7 | | | | |
| 8 | | | | |
| 9 | | | | DVDD (3.3 V both) |

Pass condition: exactly one pin reads a steady 3.3 V at both output settings (DVDD), one
reads 0 Ω to (−) (GND), and **no pin tracks the output voltage**. Any pin that tracks Vout
means the connector is not what we think — stop and re-assess.

### 3.2 Confirm the clock

Capture at ≥50 MHz while pressing OUTPUT. The fastest line with regular ~20 ns pulses is
`SHCP2`. Count edges per burst — a multiple of 8 strongly suggests shift-register traffic.

## 4. Phase 1 — decode the DAC frames

### 4.1 Capture method

Trigger on a **latch** edge (a line that pulses once at the end of a burst) with generous
pre-trigger, so each capture contains the complete preceding shift sequence. `trig_capture.py`
already does triggered capture; `record_capture.py` streams if bursts turn out to be longer
than one buffer.

### 4.2 The experiment

With current set to a fixed value, step the **voltage** setpoint through known values and
capture the bus at each step:

```
0.00, 1.00, 2.00, 5.00, 10.00, 15.00, 20.00, 25.00, 30.00 V
```

Then repeat holding voltage fixed and stepping **current**:

```
0.000, 0.100, 0.500, 1.000, 2.000, 3.000, 4.000, 5.000 A
```

### 4.3 What to extract

1. Sample `SD2` on `SHCP2` edges (test both polarities) to recover the bit stream.
2. Find the frame length. Three chained 595s = **24 bits** expected; a 24-bit shift followed
   by an `STCP2` pulse is the DAC word.
3. Distinguish DAC writes from display writes by **which** latch line pulses at the end.
4. Diff frames across setpoints. The bits that change monotonically with voltage are the
   V field; likewise for current.
5. Fit code → volts and code → amps. Expect a clean linear fit; note the resolution
   (a 12-bit field over 0–30 V ≈ 7 mV/LSB; 8-bit ≈ 118 mV/LSB — this determines how good
   the final product can be).

**Exit criterion for Phase 1:** a decoder that, given a target voltage, emits the exact bit
sequence the MCU would have sent — verified by replaying a captured frame's bits on paper
against a known setpoint.

## 5. Safety

- **Mains is exposed inside the case.** The primary side and the transformer are live with
  the lid off. Work on the low-voltage boards only, and keep probe leads away from the
  primary.
- **The AD3 earths the output-negative.** The control domain is referenced to output-negative,
  which floats with respect to earth; the AD3's ground is earthed through the PC's USB. Clipping
  AD3 GND to the 9-pin GND therefore ties output-negative to earth. That is fine on its own, but
  while probing: **connect no load, and never float or series-stack the output.**
- Single ground clip only — AD3 ⏚ on the 9-pin GND, nowhere else.
- The DAC bus is 3.3 V logic. Anything we later connect must be 3.3 V, not 5 V.

## 6. Phase 2 — interception (design deferred by intent)

The MCU keeps driving `SD2`/`SHCP2`/`STCP2`, so taking control means resolving bus contention.
Deciding this **before** seeing real frames would be guesswork, so it is deliberately left
open. The candidates:

| Option | Mechanism | Front panel after | Reversible |
|---|---|---|---|
| **A. Cut and drive** | Sever the three DAC lines at the ribbon; ESP32 drives the 595s | Displays stale values unless we also drive `display1–5` | Yes, via a changeover switch |
| **B. MITM pass-through** | ESP32 sits inline, forwards MCU traffic, substitutes on demand | Fully intact | Yes (unplug the board) |
| **C. Latch hijack** | Leave data/clock alone; gate only `STCP2` and inject between MCU bursts | Intact | Yes |

B is the most attractive on paper and the most timing-sensitive in practice. The captured
frame rate and inter-burst gaps from Phase 1 decide whether it is realistic.

## 7. Phase 3 — build (sketch)

- ESP32 on the display ribbon: drives `SD2`/`SHCP2`/`STCP2`, optionally `display1–5`.
- Readback: ADC on `AD1`/`AD2`/`AD3` (already 0–3.3 V scaled), or decode the display frames —
  the display frames are free once Phase 1 is done, and need no extra wiring.
- Output on/off: via the existing relay lines, or by commanding 0 V.
- Host side: WiFi (ESPHome / Home Assistant), or USB serial from the ESP32 exposing the
  standard Korad ASCII command set so existing tools (`py-korad-serial`, `tenma-serial`,
  `ka3005p`) work unmodified. **Emulating the Korad protocol is the preferred host interface** —
  it makes the D behave like a P to every tool that already exists.
- Reuse: the carrier PCB work and the KiCad → fiber-laser pipeline on
  `backup/main-pre-forcepush`.

## 8. Fallbacks

1. **Analog injection** at the R-2R ladder output / op-amp buffer node — if the digital bus
   proves undecodable or contention is unmanageable.
2. **Front-panel emulation** via J6 (`key_in`/`key_out`/`BkeyLift`/`BkeyRight`) with display
   decode for closed-loop feedback — slow but requires no analog surgery.
3. **Buy a KD3005P** and keep this unit manual — the honest baseline, ~€70–100.

## 9. Open questions

- Does our 9-pin actually map to the P's 12-pin J4, and which pins are dropped?
- DAC field width — sets the achievable resolution.
- Are V and I in one 24-bit frame, or separate writes distinguished by latch line?
- Do the range relays (`REL1-3`) need coordinated switching, or is the ladder full-range?
- What are the inter-burst gaps? (decides Phase 2 option B)

## 10. References

- KA3005P schematics (main / power / display / interface boards):
  https://github.com/profi-max/KORAD_WiFi_USB_module
- profi-max/Modern_KORAD — display replacement; documents J4 and the D vs DP vs P limits:
  https://github.com/profi-max/Modern_KORAD
- EEVblog — "Using a KORAD KA3005D with USB interface (like KA3005P)":
  https://www.eevblog.com/forum/testgear/using-a-korad-ka3005d-with-usb-interface-(like-ka3005p)/
- sigrok — Korad KAxxxxP series protocol: https://sigrok.org/wiki/Korad_KAxxxxP_series
- Local: `korad-9pin-investigation.md`, `korad_poll.py`, `ad3-logic-analyzer/`
- Prior design (superseded): `korad-esp32-carrier/` on `backup/main-pre-forcepush`
