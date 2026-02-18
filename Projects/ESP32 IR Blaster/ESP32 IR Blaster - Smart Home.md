---
title: ESP32 IR Blaster - WiFi Smart Home IR Controller
type: project
tags:
  - electronics
  - esp32
  - home-assistant
  - smart-home
  - active-project
status: Proof of Concept Complete
started: 2026-02-17
updated: 2026-02-18
aliases:
  - IR Blaster
  - ESP32 IR
  - Smart IR Remote
links:
  - "[[Setup Guide - ESP32 IR Blaster]]"
  - "[[Learning Remote Codes - ESP32 IR Blaster]]"
---

# ESP32 IR Blaster - WiFi Smart Home IR Controller

> [!summary] **Project Goal**
> Build a WiFi-connected IR blaster/receiver using an ESP32 and ESPHome, integrating with Home Assistant to control any IR remote-controlled device (TV, AC, etc.) from dashboards, automations, and voice assistants.
> - Send and receive IR signals over WiFi
> - Learn existing remote codes via IR receiver
> - Full Home Assistant integration via ESPHome

---

## 🔗 Quick Links

- [[#Bill of Materials|Component List]]
- [[#Circuit Design|Schematic]]
- [[#ESPHome Configuration|ESPHome YAML]]
- [[Setup Guide - ESP32 IR Blaster|Setup & Flashing Guide]]
- [[Learning Remote Codes - ESP32 IR Blaster|Learning Remote Codes]]
- [[#Future Ideas & Improvements|Future Ideas]]

---

## 📋 System Overview

| Parameter | Specification |
|-----------|--------------|
| **Platform** | ESP32 Dev Board |
| **Firmware** | ESPHome |
| **Integration** | Home Assistant (native API) |
| **IR Transmitter** | SFH4546 IR LED (via 2N2222 driver) |
| **IR Receiver** | VS1838 (38 kHz demodulator) |
| **Connectivity** | WiFi 2.4 GHz |
| **OTA Updates** | Yes (ESPHome OTA) |
| **ESP32 Chip** | ESP32-D0WD-V3 (rev v3.1), 4 MB flash |
| **USB-Serial** | CP2102 (Silicon Labs driver required) |
| **MAC Address** | 94:51:DC:34:04:D4 |

### GPIO Pinout

| Function | GPIO | Description |
|----------|------|-------------|
| **IR Transmit** | GPIO4 | Remote transmitter output (via 2N2222) |
| **IR Receive** | GPIO14 | VS1838 demodulated signal input |
| **Status LED** | GPIO2 | Onboard LED — blinks during WiFi connect, solid when online |

---

## 🛒 Bill of Materials

All components are through-hole parts from the DTU component shop unless noted.

| Qty | Component               | Value / Part                          | Notes                                         |
| --- | ----------------------- | ------------------------------------- | --------------------------------------------- |
| 1   | ESP32 dev board         | -                                     | Own supply                                    |
| 1   | IR emitter LED          | SFH4546                               | 940 nm, high radiant intensity                |
| 1   | IR receiver module      | VS1838                                | 38 kHz demodulator built-in                   |
| 1   | NPN transistor          | 2N2222                                | IR LED driver                                 |
| 1   | Resistor                | 1 kΩ                                  | Base resistor for 2N2222                      |
| 1   | Resistor                | 22 Ω (from 3.3V) or 33 Ω (from 5V) | Current-limiting for SFH4546 (~89 mA / ~110 mA pulsed) |
| 1   | Capacitor               | 100 nF ceramic                        | Decoupling on VS1838 VCC                      |
| -   | Breadboard / protoboard | -                                     | For circuit assembly                          |
| -   | Hookup wire             | 22–24 AWG                             | Connections                                   |

### Optional Components

| Qty | Component | Value | Notes |
|-----|-----------|-------|-------|
| 1–3 | IR emitter LED | SFH4546 | Additional LEDs for wider coverage |
| 1 | Capacitor | 10 µF electrolytic | Power rail bulk decoupling |
| 1 | Status LED | 3mm green | Visual feedback (GPIO2) |

> [!tip] **Current-Limiting Resistor Calculation**
> The SFH4546 has a forward voltage of ~1.35 V at 100 mA.
> - **From 3.3V:** R = (3.3 − 1.35) / 0.1 = **19.5 Ω → use 22 Ω** (~89 mA)
> - **From 5V:** R = (5.0 − 1.35) / 0.1 = **36.5 Ω → use 33 Ω** (~110 mA)
>
> These are pulsed values — IR LEDs tolerate higher currents during short carrier bursts. Check the SFH4546 datasheet for absolute maximum pulsed current.

---

## ⚡ Circuit Design

### IR Transmitter

The ESP32 drives the IR LED through a 2N2222 NPN transistor to source sufficient current. The transistor acts as a low-side switch.

> [!note]- IR Transmitter Schematic
> ```
>                          3.3V
>                           |
>                        [22Ω]
>                           |
>                       SFH4546
>                       (anode)
>                           |
>                       SFH4546
>                      (cathode)
>                           |
>                      Collector
>                           |
>     ESP32 GPIO4 ---[1kΩ]--- Base
>                                2N2222
>                           |
>                       Emitter
>                           |
>                          GND
> ```

> [!important] **Signal Inversion**
> The NPN transistor inverts the logic — when GPIO goes HIGH, the transistor conducts and current flows through the LED. ESPHome's `remote_transmitter` component handles the 38 kHz carrier modulation automatically.

### IR Receiver

The VS1838 is a complete IR receiver module with built-in bandpass filter, demodulator, and AGC. The output is an active-low demodulated signal.

> [!note]- IR Receiver Schematic
> ```
>                    3.3V
>                      |
>                +-----+-----+
>                |            |
>             [100nF]      VS1838
>              (cap)         |
>                |       +---+---+
>               GND      |   |   |
>                        OUT GND VCC
>                         |   |   |
>                         |  GND 3.3V
>                         |
>                    ESP32 GPIO14
>                   (input, pullup)
> ```

> [!tip] **VS1838 Pin Order**
> Looking at the front (dome side): **OUT | GND | VCC** (left to right).
> Always verify with your specific module — some breakout boards differ.

---

## 🔧 ESPHome Configuration

The full ESPHome YAML config for the IR blaster. Also available as a standalone file: `ir-blaster.yaml`

> [!note]- ESPHome YAML Configuration
> ```yaml
> esphome:
>   name: ir-blaster
>   friendly_name: IR Blaster
>
> esp32:
>   board: esp32dev
>   framework:
>     type: arduino
>
> wifi:
>   ssid: !secret wifi_ssid
>   password: !secret wifi_password
>   ap:
>     ssid: "IR-Blaster Fallback"
>     password: !secret fallback_password
>
> captive_portal:
>
> web_server:
>   port: 80
>
> logger:
>
> api:
>   encryption:
>     key: !secret api_key
>
> ota:
>   - platform: esphome
>     password: !secret ota_password
>
> remote_transmitter:
>   pin: GPIO4
>   carrier_duty_percent: 33%
>   non_blocking: false
>
> remote_receiver:
>   pin:
>     number: GPIO14
>     inverted: true
>     mode:
>       input: true
>       pullup: true
>   dump: all
>   tolerance: 25%
>   idle: 25ms
>
> status_led:
>   pin: GPIO2
>
> # Add your learned remote codes as button entities below.
> # See "Proof of Concept Results" section for examples.
> button: []
> ```

---

## 🛠️ Build Phases

- [x] **Research** — Component selection and circuit design
- [x] **Components** — Acquired parts from DTU component shop
- [x] **ESPHome flash** — Firmware flashed via USB (COM14, CP2102), WiFi connected
- [x] **Breadboard prototype** — IR TX and RX circuits verified working
- [x] **Learn remote codes** — Captured NEC codes from PTZ camera remote
- [x] **Configure buttons** — Presets and pan controls added to ESPHome config
- [x] **Proof of concept** — Presets work, pan commands work (with NEC repeat codes)
- [ ] **Home network deploy** — Move to home WiFi, connect to Home Assistant
- [ ] **Home Assistant integration** — Add to HA dashboards and automations
- [ ] **Learn home device codes** — Capture codes from TV, AC, and other remotes
- [ ] **Final build** — Solder on protoboard
- [ ] **Enclosure** — 3D print or project box

### Build Log

| Date | Milestone | Notes |
|------|-----------|-------|
| 2026-02-17 | Project created | Component selection, circuit design, YAML config |
| 2026-02-18 | ESPHome flashed | First flash via USB at DTU. CP2102 driver installed. Connected to phone hotspot. ESPHome 2026.1.5 |
| 2026-02-18 | Breadboard wired | IR TX (SFH4546 + 2N2222 + 22Ω + 1kΩ) and IR RX (VS1838 + 100nF) |
| 2026-02-18 | IR receiver working | Captured all camera remote codes (NEC protocol, address 0xDB34) |
| 2026-02-18 | IR transmitter working | Debugged LED polarity and transistor orientation issues |
| 2026-02-18 | Proof of concept done | Preset commands work. Pan commands work using NEC repeat codes |

### Flashing Notes

> [!warning] **MINGW / Git Bash Compatibility**
> ESPHome compile fails under MINGW/Git Bash due to ESP-IDF `idf_tools.py` rejecting the environment. Workaround: run via PowerShell with MINGW env vars cleared:
> ```powershell
> $env:MSYSTEM=$null; $env:MSYSTEM_CARCH=$null; $env:MSYSTEM_CHOST=$null
> $env:MSYSTEM_PREFIX=$null; $env:MINGW_PREFIX=$null; $env:SHELL=$null
> cd C:\Users\Mads2\esphome-build
> py -3.13 -m esphome compile ir-blaster.yaml
> ```

> [!warning] **Python 3.14 Incompatible**
> ESPHome dependencies (`ruamel.yaml.clib`) fail to build on Python 3.14. Use Python 3.13 instead: `py -3.13 -m pip install esphome`

> [!tip] **Download Mode**
> If auto-reset fails during flash, use manual boot mode: unplug USB → hold BOOT → plug in USB → release BOOT. Then flash with `--before no-reset`.

---

## 🧪 Proof of Concept Results (2026-02-18 @ DTU)

Tested at school using a PTZ camera remote. The ESP32 successfully learned all IR codes via the VS1838 receiver and retransmitted them via the SFH4546 LED.

### Camera Remote — NEC Protocol (address 0xDB34)

| Button | Command | Type | Status |
|--------|---------|------|--------|
| Preset 1 | `0xFE01` | Single press | Working |
| Preset 2 | `0xFD02` | Single press | Working |
| Preset 3 | `0xFC03` | Single press | Working |
| Preset 4 | `0xFB04` | Single press | Working |
| Preset 5 | `0xFA05` | Single press | Working |
| Preset 6 | `0xF906` | Single press | Working |
| Pan Up | `0xEE11` | Hold button | Working (with NEC repeat codes) |
| Pan Down | `0xEB14` | Hold button | Working (with NEC repeat codes) |
| Pan Right | `0xED12` | Hold button | Working (with NEC repeat codes) |
| Pan Left | `0xEC13` | Hold button | Working (with NEC repeat codes) |
| Auto Track On | `0xE51A` | Single press | Untested |
| Auto Track Off | `0xE31C` | Single press | Untested |

### Key Finding: NEC Repeat Codes for Hold Buttons

> [!important] **NEC Repeat Codes vs Re-sending Commands**
> Some devices (like this PTZ camera) require proper **NEC repeat codes** to recognize a held button. This is different from simply re-sending the full NEC command multiple times.
>
> When you hold a button on an NEC remote:
> 1. The full NEC frame is sent once (~69 ms)
> 2. Every ~110 ms, a short **repeat code** is sent: `9 ms burst + 2.25 ms space + 562 µs stop`
> 3. The device pans/scrolls/etc. as long as repeat codes keep arriving
>
> **In ESPHome**, this is implemented by sending the initial NEC command, then sending raw repeat codes in a loop:
> ```yaml
> on_press:
>   - remote_transmitter.transmit_nec:
>       address: 0xDB34
>       command: 0xED12
>   - delay: 40ms
>   - repeat:
>       count: 15
>       then:
>         - remote_transmitter.transmit_raw:
>             carrier_frequency: 38000
>             code: [9000, -2250, 562]
>         - delay: 98ms
> ```
>
> ESPHome's `command_repeats` parameter re-sends the full frame (not repeat codes), which does NOT work for devices expecting hold behavior.

### ESPHome Settings That Matter

| Setting | Value | Why |
|---------|-------|-----|
| `carrier_duty_percent` | `33%` | Standard for consumer IR. 50% also works but 33% is spec-correct |
| `non_blocking` | `false` | Required for sequential NEC frame + repeat code timing |
| `web_server` | port 80 | Useful for testing buttons without Home Assistant |
| `framework: arduino` | Required | Arduino framework (not ESP-IDF) for this board/config |

---

## ⚠️ Hardware Lessons Learned

> [!warning] **SFH4546 LED Polarity**
> Our specific SFH4546 had **reversed polarity markings** compared to typical LEDs:
> - **Short leg = anode** (positive)
> - **Long leg = cathode** (negative)
>
> This is the opposite of most LEDs where long leg = anode. Always test with a multimeter or low-current direct test before assuming polarity.

> [!warning] **2N2222 Transistor Pinout**
> The 2N2222 pinout varies between manufacturers and packages (TO-92 vs TO-18). Our part needed to be physically **flipped** from the orientation suggested by one datasheet.
>
> **Always verify with a multimeter in diode mode:**
> - Base→Emitter should show ~0.6V forward drop
> - Base→Collector should show ~0.6V forward drop
> - Emitter→Collector should show no conduction (OL)

> [!tip] **IR LED Visibility Test**
> IR LEDs emit light invisible to the naked eye, but **phone cameras** can see it as a faint purple/white glow. Use this to quickly verify the LED is firing. The glow will be faint and pulsed (38 kHz carrier), so look carefully.

> [!tip] **GPIO Direct Test**
> To verify the ESP32 GPIO is outputting a signal, temporarily connect a visible green/red LED (with a 100Ω–1kΩ resistor) to the GPIO pin. A faint glow confirms the 38 kHz modulated signal is present — it appears dim because the LED is only on for 33% of each carrier cycle.

---

## 🏠 Home Network Deployment Checklist

When moving from the school proof-of-concept to the home setup:

- [ ] **Update WiFi credentials** — Change from hotspot to home network in `secrets.yaml`:
  ```yaml
  wifi_ssid: "YourHomeNetwork"
  wifi_password: "YourHomePassword"
  ```
- [ ] **Flash via USB** — First flash on new network must be USB (OTA needs WiFi connectivity)
- [ ] **Remove test buttons** — Clear the camera remote buttons, add home device codes instead
- [ ] **Verify Home Assistant discovery** — ESPHome device should auto-discover in HA (Settings → Devices & Services)
- [ ] **Enter API encryption key** — Use the key from `secrets.yaml` when HA prompts
- [ ] **Position the IR blaster** — Line-of-sight to target devices, consider multiple LEDs for coverage
- [ ] **Disable `dump: all`** — Once done learning codes, remove or set `dump: []` on the receiver to reduce log spam
- [ ] **Optional: disable `web_server`** — Not needed once Home Assistant is connected (saves resources)

> [!info] **Tailscale**
> If flashing remotely (e.g., from school), both the computer and the ESP32's Home Assistant must be on the same Tailscale network. OTA flash goes through the ESPHome device's IP, which must be reachable.

---

## 🚀 Future Ideas & Improvements

- [x] **Status LED** — Using onboard GPIO2 LED
- [ ] **Climate entity** — Full AC control with temperature/mode in Home Assistant
- [ ] **Voice assistant integration** — Control via Google/Alexa through Home Assistant
- [ ] **Multi-directional LEDs** — Multiple SFH4546 pointing in different directions for wider coverage
- [ ] **KiCad PCB design** — Custom board with multiple IR LEDs for 360° coverage
- [ ] **3D printed enclosure** — Design and print on Prusa i3 MK2S
- [ ] **MQTT fallback** — Alternative communication if Home Assistant API is unavailable
- [ ] **Automation recipes** — Time-based and sensor-triggered IR commands (e.g., turn AC off at night)

---

## 📚 References

- [ESPHome IR Remote Climate](https://esphome.io/components/climate/ir_climate.html)
- [ESPHome Remote Transmitter](https://esphome.io/components/remote_transmitter.html)
- [ESPHome Remote Receiver](https://esphome.io/components/remote_receiver.html)
- [SFH4546 Datasheet](https://www.osram.com/ecat/SFH%204546/com/en/class_pim_web_catalog_103489/prd_pim_device_2219540/)
- [VS1838 Datasheet](https://www.alldatasheet.com/view.jsp?Searchword=VS1838)
- [2N2222 Datasheet](https://www.onsemi.com/pdf/datasheet/p2n2222a-d.pdf)

---
