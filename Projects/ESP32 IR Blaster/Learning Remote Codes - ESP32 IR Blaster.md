---
title: Learning Remote Codes - ESP32 IR Blaster
type: reference
tags:
  - electronics
  - esp32
  - home-assistant
  - smart-home
parent: "[[ESP32 IR Blaster - Smart Home]]"
updated: 2026-02-17
---

# Learning Remote Codes - ESP32 IR Blaster

Back to [[ESP32 IR Blaster - Smart Home]]

> [!summary] **Overview**
> How to capture IR codes from existing remotes using the VS1838 receiver and add them to the ESPHome configuration as controllable entities in Home Assistant.

---

## 📋 Prerequisites

- ESP32 flashed with the IR Blaster ESPHome config (see [[Setup Guide - ESP32 IR Blaster]])
- VS1838 receiver circuit wired and working
- Access to ESPHome logs (CLI or Home Assistant dashboard)
- The physical remote you want to learn from

---

## Step 1: Open ESPHome Logs

### Via Home Assistant

1. Go to **ESPHome Dashboard** (sidebar)
2. Click **LOGS** on the IR Blaster device card

### Via CLI

```bash
esphome logs ir-blaster.yaml
```

The log stream opens and waits for incoming IR signals.

---

## Step 2: Capture Remote Codes

1. Point your existing remote **directly at the VS1838 receiver** (within ~5 m)
2. Press a button on the remote
3. The ESPHome log will output the decoded signal:

```
[I][remote.nec:049]: Received NEC: address=0x4040, command=0x12BF
```

Or for raw protocols:

```
[I][remote.raw:041]: Received Raw: 9000, -4500, 560, -560, 560, -1690, ...
```

4. Note down the **protocol**, **address**, and **command** for each button

> [!tip] **Multiple Presses**
> Press each button 2–3 times to confirm the code is consistent. Some remotes alternate between two codes for toggle functions (e.g., power on/off).

---

## Step 3: Identify the Protocol

Common IR protocols and their typical devices:

| Protocol | Common Devices | ESPHome Action |
|----------|---------------|----------------|
| **NEC** | Most TVs (LG, Samsung, etc.) | `remote_transmitter.transmit_nec` |
| **Samsung** | Samsung TVs | `remote_transmitter.transmit_samsung` |
| **Sony** | Sony TVs, AV receivers | `remote_transmitter.transmit_sony` |
| **RC5** | Philips, some European brands | `remote_transmitter.transmit_rc5` |
| **Panasonic** | Panasonic TVs, ACs | `remote_transmitter.transmit_panasonic` |
| **Raw** | Unrecognized protocols | `remote_transmitter.transmit_raw` |

> [!info] **AC Units**
> Air conditioner remotes often use longer, more complex protocols that encode temperature, mode, fan speed, etc. in a single transmission. ESPHome has dedicated climate components for common AC brands — check the [ESPHome IR Climate docs](https://esphome.io/components/climate/ir_climate.html).

---

## Step 4: Add Codes to ESPHome Config

### Named Protocol (NEC Example)

```yaml
button:
  - platform: template
    name: "TV Power"
    on_press:
      - remote_transmitter.transmit_nec:
          address: 0x4040
          command: 0x12BF
```

### Raw Protocol (Fallback)

If the protocol is not recognized, use the raw data from the log:

```yaml
button:
  - platform: template
    name: "Device Power"
    on_press:
      - remote_transmitter.transmit_raw:
          carrier_frequency: 38kHz
          code: [9000, -4500, 560, -560, 560, -1690, 560, -560, ...]
```

### Switch (Toggle) Entity

For devices where you want on/off state tracking:

```yaml
switch:
  - platform: template
    name: "TV Power"
    turn_on_action:
      - remote_transmitter.transmit_nec:
          address: 0x4040
          command: 0x12BF
    turn_off_action:
      - remote_transmitter.transmit_nec:
          address: 0x4040
          command: 0x12BF
```

---

## Step 5: Flash and Test

1. Save the updated YAML config
2. OTA flash: `esphome run ir-blaster.yaml`
3. In Home Assistant, find the new button/switch entities
4. Press the button — the IR LED should transmit and the target device should respond

> [!important] **Line of Sight**
> The SFH4546 IR LED has a directional beam. Point it toward the target device's IR receiver. For wider coverage, consider adding multiple LEDs facing different directions.

---

## 📝 Code Reference Template

Use this template to document learned codes for each remote:

```
### [Device Name] Remote

| Button | Protocol | Address | Command |
|--------|----------|---------|---------|
| Power  | NEC      | 0x4040  | 0x12BF  |
| Vol+   | NEC      | 0x4040  | 0x1AB5  |
| Vol-   | NEC      | 0x4040  | 0x1EB1  |
| Mute   | NEC      | 0x4040  | 0x10EF  |
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| No log output when pressing remote | Check VS1838 wiring (pin order), ensure 3.3V and decoupling cap |
| Codes are inconsistent | Move remote closer, ensure no fluorescent lighting interference |
| `Raw` instead of named protocol | The protocol may not be in ESPHome's decoder — use raw transmit |
| Transmitted code doesn't work | Verify code matches exactly, check IR LED is emitting (phone camera test), ensure line of sight |
| AC remote codes are very long | Use ESPHome's dedicated climate components instead of raw buttons |

---
