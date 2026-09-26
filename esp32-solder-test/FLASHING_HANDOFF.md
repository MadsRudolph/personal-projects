# Handoff prompt: bring up and flash the ESP32 solder test board

Paste this into the Claude session on the machine that has the USB-UART adapter.

---

You are helping Mads bring up a hand-assembled **ESP32 solder test board** and flash it for the
first time. The board's whole point is to prove that an ESP32-WROOM-32, hand-soldered to copper
etched on an xTool F1 Ultra fiber laser, actually works. So treat every step as a test of specific
solder joints, and record what passed.

The board files are in the `personal-projects` repo under `esp32-solder-test/`. On Windows that's
usually `Documents\Projects\esp32-solder-test`. Read `README.md` there first; the schematic is
`esp32solder.pdf`. Mads has the board **fully assembled**; nothing has been powered or flashed yet.

## The board (facts, verified in the design)

- **ESP32-WROOM-32** module, soldered on the copper side. **No USB on the board**, no CH340, and
  **no auto-reset circuit**. Download mode is entered by hand with the two buttons.
- **Power:** 5 V in on J1 goes through an **LM317T** set to **3.27 V** (243 Ω / 392 Ω), then to the
  ESP32. **Red LED D2** = 3.3 V is present.
- **J1**, a 4-pin header. Pin 1 is the square pad, at the end nearest the antenna edge:

  | J1 pin | Signal | Connect to the USB-UART adapter |
  |---|---|---|
  | 1 | GND | GND |
  | 2 | 5V | 5V (VCC 5 V) |
  | 3 | TXD0 (ESP32 transmits) | adapter **RX** |
  | 4 | RXD0 (ESP32 receives) | adapter **TX** |

  The adapter must use **3.3 V logic**. Many CH340/CP2102/FT232 boards have a 3.3/5 V jumper;
  set it to 3.3 V. A 5 V TX line can damage the ESP32. The adapter's DTR/RTS pins are not used.
- **SW1 = RESET** (EN, 10 k pull-up, 1 µF delay). **SW2 = BOOT** (IO0 to GND, 10 k pull-up).
- **Green LED D1 on GPIO2**, active high (GPIO2 → 332 Ω → LED → GND).
- The big centre GND pad under the module was **not** meant to be soldered. GND reaches the module
  through pins 1, 15 and 38.

## Bring-up, in this order

Each step tests something specific. Don't skip ahead. If a step fails, stop and debug that step.

1. **Before any power, check with a multimeter** (have Mads do it and report the readings):
   - J1 5V to GND is **not** a short, and neither is 3.3 V (C2's + lead) to GND.
   - Neighbouring ESP32 pads aren't bridged. Check especially pins **1/2/3** (GND / 3V3 / EN) and
     **34/35** (RXD0 / TXD0), plus IO0 (pin 25) against its neighbours.
2. **Power only.** If there's a bench supply, use 5 V with a **~300 mA current limit**; otherwise
   use the adapter's 5 V.
   - The red LED should light, and C2's + lead should read **3.2–3.3 V**.
   - Idle current is typically well under 100 mA. If it sits at the limit, something is shorted:
     power off.
3. **ROM boot log.** This tests power, EN and the **TXD0** joint.
   - Connect the adapter as in the table and open a serial monitor at **115200 baud**, then tap RESET.
   - A healthy ESP32 prints its ROM banner, e.g. `rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)`.
     A brand-new module usually then prints the factory firmware's output.
   - **Garbage characters**: wrong baud or a marginal joint. **Nothing at all**: check TX/RX aren't
     swapped, the EN joint (pin 3), and 3.3 V.
4. **Download mode.** This tests the **IO0** joint and SW2.
   - Hold **BOOT**, tap **RESET**, then release BOOT.
   - The log should now say `boot:0x3 (DOWNLOAD_BOOT(UART0/UART1/SDIO_REI_REO_V2))` and `waiting for download`.
5. **esptool.** This tests **RXD0**, the first thing that talks *to* the chip.
   - Install with `pip install esptool`. The command is `esptool` (older versions use `esptool.py`).
   - Put the board in download mode (step 4), then run:
     ```
     esptool --port <PORT> --baud 115200 --before no_reset --after no_reset chip_id
     esptool --port <PORT> --baud 115200 --before no_reset --after no_reset flash_id
     ```
   - `<PORT>` is `COMx` on Windows (Device Manager → Ports) and `/dev/ttyUSB0` or `/dev/ttyACM0` on Linux.
   - `--before no_reset` matters: there's no auto-reset circuit, so the default DTR/RTS toggling does
     nothing useful. Re-enter download mode before each esptool command, because the chip may leave it.
   - Record the chip type/revision, the MAC and the flash size.
6. **Flash a blink on GPIO2.** This tests the **IO2** joint and the green LED.
   - Use whatever toolchain the machine has: Arduino IDE / arduino-cli ("ESP32 Dev Module" board,
     `LED_BUILTIN` is GPIO2), PlatformIO (`board = esp32dev`), or ESP-IDF.
   - Blink at ~1 Hz and also print a line over serial each blink, so TXD0 is proven again from
     *your* firmware.
   - Upload in download mode with auto-reset off. In arduino-cli / PlatformIO pass
     `--before no_reset --after no_reset` to esptool. Then tap RESET to run it.
   - If the upload fails partway, retry at 115200, and don't use 921600 until 115200 works.

## Known limits (don't mistake these for solder faults)

- **WiFi:** the LM317 needs about 1.7 V of headroom, and WiFi transmit bursts (~300–400 mA) can pull
  3.3 V down. `Brownout detector was triggered` in the log means **supply sag**, not a bad joint.
  Test WiFi only after blink works, and from a stiff 5 V supply.
- **GPIO2 is a strapping pin.** The LED holds it low, which is the correct state for download mode.
  It's fine.
- **The copper is bare** (no solder mask, laser-etched). A reading that changes when you press on the
  module means a cracked or starved joint: reflow that side.

## When you're done

Write the results into `esp32-solder-test/BRINGUP.md`:
- date
- each step passed or failed, with the readings (3.3 V value, idle current)
- chip ID, MAC and flash size
- which joints needed rework

Then commit it in the `personal-projects` repo (author Mads, no AI attribution in the message) and push.
It's the record of whether the F1 Ultra + hand-soldering process works for real ESP32 boards.
