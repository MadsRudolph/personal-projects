# ESP32 solder test: bring-up record

**Date:** 2026-09-26
**Adapter:** FTDI TTL-232R-3V3 (`/dev/ttyUSB0`). Black → J1.1 GND, yellow (RXD) → J1.3 TXD0,
orange (TXD) → J1.4 RXD0. The cable has no 5 V wire, so J1.2 was fed from a bench supply.

**Verdict:** every joint on the board is proven, and the board runs WiFi. The F1 Ultra + hand-soldering process works
for an ESP32-WROOM-32. One cold joint needed a reflow.

| Step | Result | Readings / notes | Joints proven |
|---|---|---|---|
| 1. Shorts check | Pass | No short on 5V or 3V3 to GND | none |
| 2. Power | Pass after rework | LM317 OUT read **1.2 V** and the red LED stayed dark. OUT sits 1.25 V above ADJ, so ADJ was at 0 V. The cause was a **cold joint in the R1/ADJ path**, and a reflow fixed it: red LED on, ~0.12 A with the factory AT firmware running | LM317, R1, R2, D2, R6 |
| 3. ROM boot log | Pass | `rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)`, then the factory ESP-IDF v2.0 AT firmware | TXD0, EN, flash |
| 4. Download mode | Pass | BOOT + RESET gives download mode, ~0.02 A idle, ~0 A with RESET held | IO0, SW2, SW1 |
| 5. esptool | Pass | See chip data below | RXD0 |
| 6. Blink | Pass | `firmware/blink` flashed at 115200 with no-reset, hash verified. Green LED blinks at 1 Hz, with serial `blink N on/off` lines. One clean boot, no resets | IO2, D1, R5 |
| 7. WiFi dashboard | Pass | `firmware/dashboard` joins the WutanLan phone hotspot (2.4 GHz) with TX power at 8.5 dBm. Browser slider sets the LED blink frequency live. No resets in a 60 s watch, where the factory AT firmware had reset 22 times in 30 s | RF path, supply under WiFi load |

## Chip

- **Chip:** ESP32-D0WDQ6, revision v1.0, 40 MHz crystal
- **MAC:** `ec:94:cb:4b:43:8c`
- **Flash:** 4 MB (manufacturer `d8`, device `4016`), DIO, 40 MHz, 3.3 V

## Rework

- One cold joint on R1 / the LM317 ADJ path, reflowed. No other rework.

## Observed limit: WiFi supply sag

With the factory AT firmware the board **boot-looped**: 22 `POWERON_RESET`s in 30 s, most of them
right as the WiFi radio started. The blink firmware (no WiFi) runs without a single reset, so this is
the LM317 headroom/transient limit noted in the handoff, not a solder fault. 5 V in leaves only
~1.7 V across the LM317, and C2 is only 10 µF against 300–500 mA RF calibration peaks.
Mitigations: feed J1.2 with 6 V, raise the supply's current limit to ≥500 mA, lower the WiFi TX power,
and fit a bigger bulk cap on 3V3 for future revisions.

## Flashing

No auto-reset circuit. Hold BOOT, tap RESET, release BOOT, then `pio run -t upload` in a firmware
folder (the `platformio.ini` there already sets `no_reset` and 115200). Tap RESET to run.
