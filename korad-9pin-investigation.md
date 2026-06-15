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

## Phase 3 — Desk research (2026-06-15, multi-source, adversarially verified)
Sources: sigrok KAxxxxP wiki, official KORAD "KA Series Single Channel Remote Control
Syntax V2.0" PDF, profi-max KORAD_WiFi_USB_module + Modern_KORAD, EEVblog J9 thread,
libraries py-korad-serial / tenma-serial / ka3005p. 20/25 claims confirmed.

CONFIRMED:
- J9 = 4-pin header on main controller board: VSS / RX / TX / VDD. Empty on D, wired to
  USB daughterboard on P. Pins 1 & 4 = supply rail → middle pins 2 & 3 = RX/TX. (Matches
  our "ends=GND+VCC, middle=TX/RX" guess; exact order still needs the meter.)
- Protocol = custom NON-SCPI ASCII, 8N1, NO terminator, NO checksum. Poll-only (nothing
  unsolicited — our silent passive captures were correct, not a failure).
- Commands: *IDN?  VSET1:20.50 (2dp)  ISET1:2.225 (3dp)  VOUT1?  IOUT1?  OUT1/OUT0
  OVP1/0  OCP1/0  STATUS? (single status byte, bitfield)  SAV<n>/RCL<n> (slots 1-5)  BEEP.
- J9 rail = 5V OR 3.3V, unit-dependent → MEASURE pins 1↔4 first; that sets the dongle level.
- ISOLATION — MANDATORY (MEASURED ON THE CONNECTOR 2026-06-15): J9's reference (VSS) TRACKS
  THE SET OUTPUT VOLTAGE. The whole J9 UART domain is level-shifted by Vout: VSS sits at ~+Vout
  above the negative output terminal, VDD = VSS+3.3/5V, TX/RX swing locally between them.
  => Common-mode between the J9 domain and ANY external reference (earth or output-negative)
     = the output voltage, up to 30V, and it CHANGES with the knob.
  This is the originally-"refuted" research claim — the verification was a FALSE refutation;
  the bench meter is ground truth. (Both earlier log notes — "no isolation needed" AND the
  later "VSS = negative terminal, floats only vs earth" — were WRONG.)
  - This is exactly why every factory KA3005P USB daughterboard carries optocouplers: they
    bridge a common-mode that rides on Vout.
  - A BARE USB-TTL straight to a PC is DANGEROUS: clipping dongle GND to J9 VSS forces an
    internal +Vout node to earth → backfeeds the reference and/or puts Vout across the dongle
    RX → destroys the dongle and likely the laptop USB port. DO NOT do the "quick non-isolated
    go/no-go" — that earlier advice is retracted.
  - SAFE options (all tolerate the moving Vout common-mode):
    1. USB isolator (ADuM3160 module, ~$10-20) + USB-TTL dongle. Dongle GND on J9 VSS, dongle
       FLOATS up to Vout (sees normal 3.3/5V locally); barrier (~2.5kV) protects the PC.
       Insulate the floating dongle+cable — they sit at Vout.
    2. Factory-style optos on TX/RX (PC817 @9600; 6N137 if using 115200 fallback), PSU side
       powered from J9 VDD, host side from dongle 5V.
    3. WiFi ESP (profi-max) — no wired host, common-mode never leaves the floating domain.
  - J9 is STILL the UART: 3 lines idle-HIGH *relative to local VSS* = serial profile; the
    domain just rides on Vout.

CORRECTIONS to earlier plan in this log:
- BAUD: try **9600 FIRST**, 115200 only as fallback. (Earlier "115200 first" was wrong —
  that 115200 is profi-max's INTERNAL ESP<->MCU link; the user-facing KORAD port is 9600,
  verified across every library. Residual ambiguity: J9-internal *might* differ, hence
  115200 kept as fallback.)
- The "*IDN? answers only once per power-cycle" bug is LIKELY NOT REAL (single blog,
  refuted 1-2). Poll *IDN? freely. The REAL quirk: on protocol v2.0, ISET1? returns a
  spurious 6th byte (= 6th char of a prior *IDN? reply) — read and discard. Fixed in v2.1.

NEW CAUTIONS:
- A D unit having J9 populated/idle-HIGH does NOT guarantee a working UART. Some D firmware
  never responds (TX idle HIGH forever). "DP" = a D that happens to answer like a P. The
  LIVE POLL is still the only decider. One forum report needed a ~10k pulldown on TX to get
  a response — keep that trick in pocket if TX stays stuck high.
- Pace commands ~100-200ms apart (py-korad-serial sleeps 0.1s, tenma-serial 0.2s).

REUSE, don't rewrite: starforgelabs/py-korad-serial (Python, 9600 8N1, NULL-terminated
reads, 0.1s pacing) or kxtells/tenma-serial (handles Tenma/Velleman/RND rebadges).

## Notes / findings
- Pin 1 = GND.
- This 9-pin DOES carry a digital bus (active on output toggle). Earlier "all LOW idle"
  and "encoder=no traffic" (broken-cable) results superseded.
- Broken/breadboard cable caused C.C at 0V (series R in sense lines). Fixed now.
- AD3 single-buffer = 16384 samples (0.33ms @ 50MHz). Use record_capture.py (streaming) for events.
