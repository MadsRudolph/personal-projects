---
title: Setup Guide - ESP32 IR Blaster
type: build-guide
tags:
  - electronics
  - esp32
  - home-assistant
  - smart-home
  - active-project
status: Planning
started: 2026-02-17
updated: 2026-02-17
parent: "[[ESP32 IR Blaster - Smart Home]]"
---

# Setup Guide - ESP32 IR Blaster

Back to [[ESP32 IR Blaster - Smart Home]]

> [!summary] **Overview**
> Step-by-step guide for flashing ESPHome firmware to the ESP32 and integrating with Home Assistant.
> - Flash via USB on first install, then OTA for updates
> - ESP32 auto-discovers in Home Assistant

---

## 📋 Prerequisites

| Item | Purpose |
|------|---------|
| **ESP32 dev board** | Target hardware |
| **USB cable** | Micro-USB or USB-C (depends on board) |
| **Computer** | Running ESPHome CLI or Home Assistant |
| **Home Assistant** | With ESPHome add-on or standalone ESPHome |
| **WiFi network** | 2.4 GHz (ESP32 does not support 5 GHz) |

---

## Step 1: Install ESPHome

Choose one of two methods:

### Option A: Home Assistant Add-on (Recommended)

1. Open Home Assistant → **Settings** → **Add-ons**
2. Click **Add-on Store** → search for **ESPHome**
3. Install the ESPHome add-on and start it
4. Open the ESPHome dashboard from the sidebar

### Option B: ESPHome CLI

> [!note]- CLI Installation
> ```bash
> # Install ESPHome via pip
> pip install esphome
>
> # Verify installation
> esphome version
> ```

---

## Step 2: Create the YAML Configuration

1. In the ESPHome dashboard, click **New Device**
2. Name it `ir-blaster`
3. Replace the generated config with the full YAML from [[ESP32 IR Blaster - Smart Home#ESPHome Configuration|the project overview]]
4. Or use the standalone `ir-blaster.yaml` file in the project folder

> [!important] **Secrets**
> Create a `secrets.yaml` file in the same directory as your ESPHome config:
> ```yaml
> wifi_ssid: "YourNetworkName"
> wifi_password: "YourWiFiPassword"
> fallback_password: "YourFallbackPassword"
> api_key: "GeneratedAPIKey"
> ota_password: "YourOTAPassword"
> ```
> Generate the API key with: `esphome wizard ir-blaster.yaml` or let ESPHome auto-generate one.

---

## Step 3: First Flash (USB)

1. Connect the ESP32 to your computer via USB
2. Put the ESP32 into flash mode if needed (hold BOOT, press EN/RST, release BOOT)
3. Flash the firmware:

```bash
esphome run ir-blaster.yaml
```

4. Select the USB/serial port when prompted
5. Wait for compilation and upload to complete

> [!tip] **Driver Issues**
> If the ESP32 is not detected, install the CP2102 or CH340 USB-serial driver for your board. Check your board's documentation for the correct chip.

---

## Step 4: WiFi Connection & Home Assistant Discovery

1. After flashing, the ESP32 reboots and connects to your WiFi network
2. Open **Home Assistant** → **Settings** → **Devices & Services**
3. The IR Blaster should appear as a discovered ESPHome device
4. Click **Configure** → enter the API encryption key
5. The device is now available in Home Assistant

> [!success] **Verification**
> You should see the IR Blaster device with its button entities in Home Assistant. The ESPHome logs should show a successful API connection.

---

## Step 5: Learn Remote Codes

See [[Learning Remote Codes - ESP32 IR Blaster]] for the full workflow on capturing and adding IR codes from your existing remotes.

---

## Step 6: Add Learned Codes to Config

1. Open the ESPHome YAML config
2. Add button or switch entities for each learned code (see examples in the main config)
3. Save the config

---

## Step 7: OTA Update

After modifying the config, push updates wirelessly:

```bash
esphome run ir-blaster.yaml
```

ESPHome will automatically detect the device on the network and flash OTA — no USB needed.

> [!tip] **Fallback Hotspot**
> If the ESP32 cannot connect to WiFi (wrong credentials, network down), it creates a fallback AP named **IR-Blaster Fallback**. Connect to it and navigate to `192.168.4.1` to reconfigure.

---

## Step 8: Use in Home Assistant

Once configured with your remote codes, you can:

- **Dashboards** — Add buttons to Lovelace cards for TV power, volume, etc.
- **Automations** — Trigger IR commands based on time, sensor data, or other events
- **Voice assistants** — "Hey Google, turn on the TV" via Home Assistant
- **Scripts** — Chain multiple IR commands (e.g., TV on → switch to HDMI 2 → set volume)

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| ESP32 not detected on USB | Install CP2102/CH340 driver, try different cable |
| WiFi connection fails | Verify SSID/password, ensure 2.4 GHz network |
| Device not discovered in HA | Check API key matches, verify same network/VLAN |
| IR commands not working | Check LED polarity, verify transistor wiring, test with phone camera (IR is visible on camera) |
| IR receiver no output | Verify VS1838 pin order, check 3.3V supply and decoupling cap |

---
