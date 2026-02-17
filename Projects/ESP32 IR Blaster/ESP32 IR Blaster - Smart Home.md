---
title: ESP32 IR Blaster - WiFi Smart Home IR Controller
type: project
tags:
  - electronics
  - esp32
  - home-assistant
  - smart-home
  - active-project
status: Planning
started: 2026-02-17
updated: 2026-02-17
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

### GPIO Pinout

| Function | GPIO | Description |
|----------|------|-------------|
| **IR Transmit** | GPIO4 | Remote transmitter output (via 2N2222) |
| **IR Receive** | GPIO5 | VS1838 demodulated signal input |

---

## 🛒 Bill of Materials

All components are through-hole parts from the DTU component shop unless noted.

| Qty | Component | Value / Part | Notes |
|-----|-----------|--------------|-------|
| 1 | ESP32 dev board | - | Own supply |
| 1 | IR emitter LED | SFH4546 | 940 nm, high radiant intensity |
| 1 | IR receiver module | VS1838 | 38 kHz demodulator built-in |
| 1 | NPN transistor | 2N2222 | IR LED driver |
| 1 | Resistor | 1 kΩ | Base resistor for 2N2222 |
| 1 | Resistor | 5–10 Ω (from 3.3V) or ~27 Ω (from 5V) | Current-limiting for SFH4546 (~100 mA pulsed) |
| 1 | Capacitor | 100 nF ceramic | Decoupling on VS1838 VCC |
| - | Breadboard / protoboard | - | For circuit assembly |
| - | Hookup wire | 22–24 AWG | Connections |

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
>                        3.3V (or 5V)
>                          |
>                       [R_led]
>                     (see BOM)
>                          |
>                      SFH4546
>                      (anode)
>                          |
>                      SFH4546
>                     (cathode)
>                          |
>                     Collector
>                          |
>     ESP32 GPIO4 ---[1kΩ]--- Base
>                               2N2222
>                          |
>                      Emitter
>                          |
>                         GND
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
>                        OUT VCC GND
>                         |   |   |
>                         |  3.3V GND
>                         |
>                    ESP32 GPIO5
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
>   carrier_duty_percent: 50%
>
> remote_receiver:
>   pin:
>     number: GPIO5
>     inverted: true
>     mode:
>       input: true
>       pullup: true
>   dump: all
>   tolerance: 25%
>   idle: 25ms
>
> # Example buttons — replace with learned codes from your remotes
> button:
>   - platform: template
>     name: "TV Power"
>     on_press:
>       - remote_transmitter.transmit_nec:
>           address: 0x4040
>           command: 0x12BF
>   - platform: template
>     name: "TV Volume Up"
>     on_press:
>       - remote_transmitter.transmit_nec:
>           address: 0x4040
>           command: 0x1AB5
> ```

---

## 🛠️ Build Phases

- [ ] **Research** — Component selection and circuit design
- [ ] **Components** — Acquire parts from DTU component shop
- [ ] **Breadboard prototype** — Assemble and test IR TX/RX circuit
- [ ] **ESPHome flash** — Flash firmware and connect to Home Assistant
- [ ] **Learn remote codes** — Capture IR codes from existing remotes
- [ ] **Configure buttons** — Add learned codes to ESPHome config
- [ ] **Final build** — Solder on protoboard
- [ ] **Enclosure** — 3D print or project box

---

## 🚀 Future Ideas & Improvements

- [ ] **KiCad PCB design** — Custom board with multiple IR LEDs for 360° coverage
- [ ] **3D printed enclosure** — Design and print on Prusa i3 MK2S
- [ ] **Multi-directional LEDs** — Multiple SFH4546 pointing in different directions
- [ ] **Status LED** — Visual feedback for IR transmit/receive activity
- [ ] **Voice assistant integration** — Control via Google/Alexa through Home Assistant
- [ ] **MQTT fallback** — Alternative communication if Home Assistant API is unavailable
- [ ] **Climate entity** — Full AC control with temperature/mode in Home Assistant

---

## 📚 References

- [ESPHome IR Remote Climate](https://esphome.io/components/climate/ir_climate.html)
- [ESPHome Remote Transmitter](https://esphome.io/components/remote_transmitter.html)
- [ESPHome Remote Receiver](https://esphome.io/components/remote_receiver.html)
- [SFH4546 Datasheet](https://www.osram.com/ecat/SFH%204546/com/en/class_pim_web_catalog_103489/prd_pim_device_2219540/)
- [VS1838 Datasheet](https://www.alldatasheet.com/view.jsp?Searchword=VS1838)
- [2N2222 Datasheet](https://www.onsemi.com/pdf/datasheet/p2n2222a-d.pdf)

---
