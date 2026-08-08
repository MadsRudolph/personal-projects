# KORAD KD3005D — 9-Pin Connector Investigation Log

Host: Windows 11 + Digilent AD3 (WaveForms). Logic level: 3.3V.
GND reference: **negative output banana terminal** (NOT chassis earth).

## Phase 1 — Continuity (PSU UNPLUGGED)
Beep each pin against the negative output terminal. 0Ω = GND.

| Pin # | Continuity to (–) terminal? |
|-------|-----------------------------|
| 1     |                             |
| 2     |                             |
| 3     |                             |
| 4     |                             |
| 5     |                             |
| 6     |                             |
| 7     |                             |
| 8     |                             |
| 9     |                             |

## Phase 1 — DC voltage map (PSU ON)
Measure each pin vs (–) terminal at two output settings.

| Pin # | V @ Vout=0V | V @ Vout=12V | Interpretation |
|-------|-------------|--------------|----------------|
| 1     |             |              |                |
| 2     |             |              |                |
| 3     |             |              |                |
| 4     |             |              |                |
| 5     |             |              |                |
| 6     |             |              |                |
| 7     |             |              |                |
| 8     |             |              |                |
| 9     |             |              |                |

Interpretation key:
- ~0V both → GND
- ~3.3V/5V stable both → VCC rail
- Tracks output voltage → analog sense (rule out UART)
- ~3.3V stable, not VCC → candidate digital/UART TX (idle high)

## AD3 wiring (logic capture)
Pin 1 = GND (confirmed continuity to (–) terminal). AD3 ⏚ on pin 1.
DIO k -> pin (k+1):
- DIO1=pin2, DIO2=pin3, DIO3=pin4, DIO4=pin5, DIO5=pin6, DIO6=pin7, DIO7=pin8, DIO8=pin9

## Phase 2 — AD3 idle levels (PSU on, idle, 2s window @ 1MHz, stable x2)
| Pin | AD3 ch | Idle level | Note |
|-----|--------|-----------|------|
| 2   | DIO1   | LOW       |      |
| 3   | DIO2   | LOW       |      |
| 4   | DIO3   | HIGH      | UART/comms candidate (idle high) |
| 5   | DIO4   | HIGH      | UART/comms candidate (idle high) |
| 6   | DIO5   | HIGH      | UART/comms candidate (idle high) |
| 7   | DIO6   | LOW       |      |
| 8   | DIO7   | LOW       |      |
| 9   | DIO8   | LOW       |      |

No activity on any line while idle. Pins 4/5/6 idle HIGH = prime digital/UART candidates.

## Phase 2 — Output ON/OFF toggle (fixed cable, 1MHz, 6s)
Pressing OUTPUT button => synchronous burst on MULTIPLE lines. Likely SPI-like digital bus.
min-pulse pinned at 1us (= 1 sample @1MHz) => real pulses FASTER, must sample faster.
Edge counts: pin8/ch7=165 (idle HIGH, top candidate clock/CS), pin3/ch2=114, pin7/ch6=110,
pin9/ch8=100, pin4/ch3=88, pin5/ch4=83, pin2/ch1=76, pin6/ch5=19.

## Phase 2 CONCLUSION (50MHz triggered burst capture, burst.npy)
- OUTPUT toggle => single localized ~60us burst (not noise: flat-zero outside burst).
- Channels switch SIMULTANEOUSLY => clocked synchronous bus (SPI/parallel), NOT UART.
- pin2/ch1 = fastest line (~20ns pulses) => likely CLOCK. Others = data/select.
- All 9 lines idle LOW, burst together => definitively NOT a UART (UART = 1 line, idle HIGH).
- => The 9-pin is the INTERNAL MCU<->power-board control bus (DAC set / ADC sense / out-enable),
  NOT the remote-control serial port.
- 1-sample glitches everywhere = crosstalk/ground-bounce from long breakout+breadboard taps.

## IMPLICATION FOR GOAL (remote control)
Remote *IDN? control will NOT come from this 9-pin bus. The KD3005P serial/USB interface
board attaches at the MCU UART on the FRONT-PANEL board. Next: find MCU UART TX/RX pins
near the KORAD01 chip (idle-HIGH line with intermittent bursts).

## 4-PIN connector (separate, was unconnected) — SERIAL CANDIDATE
Wiring: GND clip on 4-pin GND. DIO1/DIO2/DIO3 on the 3 signal pins.
Idle baseline (2MHz, 2s, PSU on @3V): ALL THREE lines idle HIGH.
=> Serial-port profile (VCC + TX + RX all idle high). Opposite of the 9-pin (idle LOW).
Next: power-cycle to catch boot UART TX burst; then USB-TTL *IDN? poll.

### 4-pin DC map CONFIRMED (multimeter vs neg terminal)
Pin1=GND. Pins 2,3,4 = 3.3V at BOTH output 0V and 12V (none tracks output => none analog).
=> Digital serial header, 3.3V logic. Likely: pin4=VCC (far end), pins 2&3 = TX/RX.
Dongle/Arduino must be 3.3V or level-shifted (Arduino Uno=5V => needs divider on its output line).

### POLL RESULT: NO RESPONSE (FTDI TTL-232R-3V3 on COM17)
Tested *IDN? / VOUT1? / STATUS? across ALL pin orientations and baud rates: SILENT.
- All 6 ordered TX/RX pairings of pins {2,3,4} (one is VCC) -> 0 bytes.
- Baud sweep 4800/9600/19200/38400/57600/115200/128000 -> 0 bytes.
- Terminators none/LF/CR/CRLF -> 0 bytes.
- Cable PROVEN GOOD via TXD<->RXD loopback (echoed correctly). PSU confirmed on.
- Also: during earlier AD3 captures (boot, dials) these lines NEVER transmitted unsolicited.
=> This unit does not respond to Korad serial on this header. Likely causes (ranked):
   1. D firmware lacks the serial command interpreter (documented: "only SOME D units respond").
   2. 4-pin may not be the UART header (idle-high 3.3V was inferred, never saw real TX traffic).
   3. Possible enable/detect condition for the interface board.
NEXT: board photos to ground-truth (which connector is serial / MCU UART pins / enable jumper),
re-read profi-max for J9 pinout + firmware-revision dependence. Fallbacks: encoder interception,
DAC injection, or control-board replacement (profi-max / Modern_KORAD).

### VERIFIED against Korad docs + profi-max KORAD_WiFi_USB_module (the D->P mod project)
- Korad programmable PSU serial = POLL-ONLY: device sends NOTHING unsolicited
  (no boot banner, no status-on-knob-turn). Our 3 silent passive tests = CORRECT/expected.
- The UART connector is documented as **J9** under the cover = our 4-pin header. Likely:
  END pins (1 & 4) = GND + VCC, MIDDLE pins (2 & 3) = TX + RX.
- BAUD: try **115200 first** (profi-max D-variant uses 115200), then 9600 (official P manual).
- Protocol: ASCII, 8N1, NO line terminator, no checksum. *IDN? VSET1: ISET1: VOUT1? OUT1/OUT0 STATUS?
- *IDN? FIRMWARE BUG: some firmware answers *IDN? only ONCE until power-cycled. So: power-cycle,
  send *IDN? ONCE, read. Don't spam it.
- D firmware: "some devices can work like KORAD3005P" => response NOT guaranteed, but the
  idle-high UART being present is a strong sign. Tomorrow's poll is the decider.
- Logic level: measure the idle-HIGH TX/RX pins -> 3.3V => 3.3V dongle; 5V => 5V dongle.
  (profi-max: measure pins 1&4 of J9; 5V or 3.3V supply both possible.)

## Notes / findings
- Pin 1 = GND.
- This 9-pin DOES carry a digital bus (active on output toggle). Earlier "all LOW idle"
  and "encoder=no traffic" (broken-cable) results superseded.
- Broken/breadboard cable caused C.C at 0V (series R in sense lines). Fixed now.
- AD3 single-buffer = 16384 samples (0.33ms @ 50MHz). Use record_capture.py (streaming) for events.
