# Plant Watering Tower

An ESPHome project for an ESP32 that drives a salvaged **mains-AC solenoid pump** via a
relay to water a vertical plant tower on a schedule. The pump is **on/off only** — flow
is controlled by **run time**, never by voltage or PWM. The firmware enforces safety
interlocks (dry-run lockout, max run time, cooldown) and integrates with Home Assistant
over the native ESPHome API.

## Files

| File | Purpose |
|---|---|
| `pump.yaml` | The ESPHome config. All tunables live in the `substitutions:` block at the top. |
| `secrets.yaml` | Template for WiFi / API / OTA / fallback credentials. Fill in before flashing. |
| `WIRING.md` | Standalone bench wiring reference — mains side, low-voltage side, full diagram. |
| `home-assistant.yaml` | Optional HA dashboard card + scheduling automation snippets. |
| `README.md` | This file — wiring, calibration, and the safety section. |

## ⚠️ Mains voltage warning

This project switches **220–240V AC**. Mains wiring can kill you and can start fires.
Do the high-voltage wiring with the plug **unplugged**, enclose all live conductors, bond
exposed metal to earth, and have the result checked if you are not competent with mains.
The relay module is **non-opto-isolated** — treat the entire low-voltage side as if it
could become live under a fault.

## Hardware inventory

| Part | Detail | Notes |
|---|---|---|
| Pump | Defond P500U solenoid pump | 220–240V AC 50Hz, 53W, 15 bar max, ~750 ml/min free flow |
| Pump duty | 2 min on / 1 min off rating | Intermittent only. **Must not run dry.** Self-priming, plastic (PA66) body |
| Pump protection | Thermal cutoff (the white part) | Refitted in series with the coil — **hardware**, not firmware |
| Relay | Tongling JQC-3FF-S-Z module | 5V coil, **non-opto-isolated**, contacts 10A/250VAC, SPDT |
| Relay drive | **active-low**, open-drain | Needs open-drain drive from 3.3V GPIO — see WIRING.md *Relay drive* |
| MCU | ESP32 (e.g. Wemos/Lolin D1 Mini ESP32) | Runs ESPHome |
| Float switch | Reservoir level sensor | For dry-run protection. Sense (NO/NC + orientation) is user-configurable |
| Supply | 5V rail | Powers ESP32 + relay coil (~70 mA). Use a clean source, not a marginal USB |

## Wiring

**Full wiring reference: [WIRING.md](WIRING.md)** — mains side, low-voltage side, the
pump's two leads, and a complete system diagram.

In short: the relay switches the **live conductor only**; the D1 Mini ESP32 drives the
relay coil over 5V with a single 3.3V signal (`GPIO16 → relay IN`) as the only connection
crossing between the low-voltage and mains sides. The float switch wires between `GPIO17`
and ground (internal pull-up, no resistor). All grounds (ESP32, relay coil, 5V return,
float) must be common.

### Confirm before/while building

- **ESP32 board:** Wemos/Lolin D1 Mini ESP32 (`wemos_d1_mini32`), relay on `GPIO16`,
  float on `GPIO17`. ✅ verified.
- **Relay drive:** this module is **active-low** and needs **open-drain** drive — see the
  *Relay drive* section in [WIRING.md](WIRING.md). ✅ verified working on mains.
- **Float switch sense:** still TODO with the real float — flip `inverted:` on the
  `reservoir_has_water` binary_sensor so **ON = water present** (tested so far with a
  IO17→GND jumper, which reads as water present).
- **Calibration:** `flow_ml_per_s` is still the placeholder `10` — measure it (below).
- **Schedule** (the `time:` `on_time:` block) and **default dose volume**.

## Calibration procedure

Dose time is computed as `seconds = desired_ml / flow_ml_per_s`, so the flow figure must
be measured at the **real tower head** with the final tubing.

1. Assemble the tower with final tubing/head.
2. Run the pump for a known time (e.g. 30 s) into a measuring jug.
3. `flow_ml_per_s = collected_ml / seconds`.
4. Set the `flow_ml_per_s` substitution in `pump.yaml`.
5. Re-measure if you change tubing, height, or head.

## Build & flash

```bash
esphome run pump.yaml
```

First flash over USB, then OTA thereafter.

> **Windows gotcha:** the ESP-IDF build fails with *"Detected a whitespace character
> in project paths"* because this folder name ("Plant Watering Tower") contains spaces.
> Work around it by building through a no-space directory junction:
> ```powershell
> cmd /c mklink /J C:\esphome-plant-pump "C:\Users\Mads2\Documents\Projects\Projects\Plant Watering Tower"
> python -m esphome run "C:\esphome-plant-pump\pump.yaml" --device COM7 --no-logs
> ```
> The junction points at the same real folder, so source, secrets, and build output stay
> in place. (`esphome` is invoked as `python -m esphome` here since it's not on PATH.) After it connects to WiFi, add the device in
Home Assistant (Settings → Devices & Services → ESPHome) and it exposes:

- **Water now** (button) — runs one interlocked dose at the current dose volume.
- **Dose volume** (number, ml) — adjustable dose size.
- **Manual run (override)** (button) — timed run that **ignores cooldown and the dry-run
  lockout** (for priming/flushing). Still capped by `max_run_seconds`.
- **Manual run time** (number, s) — how long the override runs (default 30 s, ≤ max-run).
- **Stop pump** (button) — emergency stop; forces the relay off and cancels any dose/override.
- **Reservoir has water** (binary sensor) — live float state.
- **Pump state** (text sensor) — `Running` / `Idle`.

> ⚠️ The **override bypasses dry-run protection** — it can run the pump with an empty
> reservoir. Use it deliberately (priming), not as the normal watering control.

The raw relay is `internal: true` and is intentionally **not** exposed to HA, so the
interlocks cannot be bypassed from the dashboard.

## Safety requirements — MUST be implemented in firmware

> Reproduced verbatim from the project handoff. Each item maps to a block in `pump.yaml`.

1. **Boot fail-safe:** relay defaults OFF on power-up / reboot (`restore_mode: ALWAYS_OFF`).
2. **Dry-run lockout:** refuse to start a dose if the float reads empty.
3. **Mid-dose abort:** a fast watchdog turns the pump off within ~250 ms if the reservoir empties while running.
4. **Hard max-run cap:** an independent timer forces the relay off after `max_run_seconds`, regardless of script state.
5. **Cooldown:** reject a new dose until `min_rest_seconds` has elapsed since the last one (respects duty cycle).
6. **Raw relay not user-exposed:** mark the GPIO switch `internal: true`; HA only gets the safe button/script, so the interlocks can't be bypassed from the dashboard.
7. Pick a **boot-safe GPIO** for the relay (not a strapping pin) so the pump can't pulse during reset.

### Implementation notes

- `millis()` rolls over at ~49 days; acceptable for a cooldown, but noted.
- The `on_turn_on` max-run delay is an intentional independent backstop to the script's own timing.
- Validate syntax against your installed ESPHome version (the `ota:` block and others have
  changed across releases).

## Scope

Single zone assumed (one pump → one tower). Per-plant zones and soil-moisture sensing are
future extensions, out of scope for v1.
