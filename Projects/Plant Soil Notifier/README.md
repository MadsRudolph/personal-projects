# Plant Soil Notifier

An ESPHome project that turns the freed-up **Plant Watering Tower** ESP32 into a soil-moisture
**notifier**. It reads one capacitive soil-moisture sensor, exposes the moisture % to Home
Assistant over the native ESPHome API, and trips a **Needs water** flag when the soil goes dry.
No pump, no auto-watering — Home Assistant sends the actual notification.

## Files

| File | Purpose |
|---|---|
| `soil-notifier.yaml` | The ESPHome config. All tunables live in the `substitutions:` block at the top. |
| `secrets.yaml` | WiFi / API / OTA credentials (same network as your other devices). |
| `home-assistant.yaml` | Optional HA dashboard card + dry-soil notification automation. |
| `README.md` | This file — wiring, calibration, and flashing. |

## Hardware

| Part | Detail |
|---|---|
| MCU | Wemos/Lolin D1 Mini ESP32 (`wemos_d1_mini32`) — the ex-tower board |
| Sensor | Capacitive soil moisture sensor, analog `AOUT`, 3.3 V |
| Power | USB, always-on |

## Wiring

| Sensor pin | ESP32 |
|---|---|
| `VCC` | `3V3` |
| `GND` | `GND` |
| `AOUT` | **`GPIO34`** |

> ⚠️ **Use an ADC1 pin (GPIO32–39).** The ESP32's ADC2 pins stop working the moment WiFi is
> active, so a soil sensor on an ADC2 pin just reads garbage. GPIO34 is ADC1 and input-only —
> perfect for an analog sensor.

## Calibration procedure

Capacitive sensors read a **higher voltage when dry**. You need two reference voltages.

1. Flash with the placeholder calibration (below) and open the ESPHome logs.
2. Hold the probe **in dry air** — note the raw voltage → set `dry_voltage` (maps to 0 %).
3. Dip the probe **in a glass of water** to the normal insertion depth — note the voltage →
   set `wet_voltage` (maps to 100 %).
4. Put both into the `substitutions:` block and re-flash (OTA).
5. Sanity-check: dry air ≈ 0 %, real soil somewhere in between, water ≈ 100 %.

The dry-alert thresholds (`dry_threshold` / `wet_reset_threshold`) also live in `substitutions:`;
the gap between them is hysteresis so the **Needs water** flag doesn't flap around the boundary.

## Build & flash

The board is already on WiFi running ESPHome, so flash it **over the air** — no USB needed:

```bash
esphome run soil-notifier.yaml
```

Pick the **wireless / OTA** target when prompted. It accepts the update because `secrets.yaml`
carries the same OTA password. The old tower entities disappear from Home Assistant and the new
`Soil moisture` + `Needs water` entities appear.

> If OTA ever fails, fall back to USB (`esphome run soil-notifier.yaml --device COMx`). Because
> this config uses the **Arduino** framework (not ESP-IDF), the folder name's spaces are fine —
> no directory-junction workaround needed.

## Exposed to Home Assistant

- **Soil moisture** (sensor, %) — live moisture reading.
- **Needs water** (binary sensor) — ON when moisture < `dry_threshold`, clears above
  `wet_reset_threshold`.

See `home-assistant.yaml` for the dashboard card and the notification automation.

## Scope

USB-powered single-sensor notifier. Future extensions, out of scope for v1:

- **Battery + deep sleep** — would need a battery, a voltage divider for monitoring, and a
  prevent-sleep switch so OTA still works during wake windows.
- **Multiple sensors** on the one ESP32 (other ADC1 pins are free).
- **Re-adding the pump** for closed-loop auto-watering.
