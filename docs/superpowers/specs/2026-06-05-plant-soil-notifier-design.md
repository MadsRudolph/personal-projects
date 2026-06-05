# Plant Soil Notifier — Design

**Date:** 2026-06-05
**Status:** Approved

## Goal

Repurpose the freed-up Plant Watering Tower ESP32 into a soil-moisture **notifier**: read one
capacitive soil-moisture sensor, expose the moisture % to Home Assistant, and notify when the
soil goes dry. No pump, no auto-watering.

## Hardware

| Part | Detail |
|---|---|
| MCU | Wemos/Lolin D1 Mini ESP32 (`wemos_d1_mini32`) — the ex-tower board |
| Sensor | Capacitive soil moisture sensor, analog `AOUT`, 3.3 V |
| Power | USB, always-on (v1) |

**Wiring**

- Sensor `VCC` → `3V3`, `GND` → `GND`.
- Sensor `AOUT` → **GPIO34**. This must be an **ADC1** pin (GPIO32–39). The ESP32's ADC2 pins
  stop working once WiFi is active, so a soil sensor on an ADC2 pin reads garbage — a classic trap.

## Firmware (`soil-notifier.yaml`, ESPHome, Arduino framework)

Standard skeleton matching `esp32-dht-sensor`: `wifi` + `captive_portal` + encrypted `api` +
`ota`, all values via `!secret`. Arduino framework (not ESP-IDF) so a folder name with spaces
doesn't trip the ESP-IDF whitespace build bug.

- **ADC sensor** on GPIO34, `update_interval: 60s` (soil changes slowly), `12db` attenuation.
- **`calibrate_linear`** maps raw voltage → 0–100 %, two-point: raw value *in dry air* and
  *in a glass of water*. Both live as `substitutions` placeholders until measured. Capacitive
  sensors read **higher voltage when dry**, so the calibration slope is negative (handled fine).
- A **`clamp`** filter pins the output to 0–100 %.
- **`Needs water`** template binary sensor (`device_class: problem`) with hysteresis: trips true
  below `dry_threshold` (default 30 %), clears only above `wet_reset_threshold` (default 40 %),
  holds in between so it doesn't flap.

### Exposed to Home Assistant

- `Soil moisture` (sensor, %)
- `Needs water` (binary sensor)

## Notification path

ESPHome can't push notifications itself — Home Assistant does. The device reports the data and
the `Needs water` flag; a small HA automation (`home-assistant.yaml`, like the tower's) calls
`notify.notify` when `Needs water` turns on, with a re-notify guard (fires once per dry episode,
not every minute).

## Files

| File | Purpose |
|---|---|
| `soil-notifier.yaml` | ESPHome config; all tunables in `substitutions:` |
| `secrets.yaml` | WiFi / API / OTA credentials (same network as the other devices) |
| `home-assistant.yaml` | Dry-soil notification automation snippet |
| `README.md` | Wiring, the ADC1 gotcha, calibration procedure, flash/OTA steps |

## Flashing

The board is already on WiFi running ESPHome, so flash **over OTA** (no USB):
`esphome run soil-notifier.yaml` → pick the wireless target. Keep the same OTA password so it
accepts the update. USB only as a fallback if OTA fails.

## Calibration procedure

1. Flash with placeholder calibration; watch the raw voltage in ESPHome logs.
2. Hold the probe **in dry air** — note the voltage → that's the `dry_voltage` (≈ 0 %).
3. Dip the probe **in a glass of water** to the normal insertion depth — note the voltage →
   that's the `wet_voltage` (≈ 100 %).
4. Put both into `substitutions:` and re-flash (OTA).
5. Sanity-check: in dry air ≈ 0 %, in soil somewhere in between, in water ≈ 100 %.

## Out of scope (future extensions)

- Battery + deep sleep (USB-only for now; deep sleep complicates OTA and needs a battery divider).
- Multiple sensors on the one ESP32.
- Re-adding the pump for closed-loop auto-watering.
