1# Xiaomi S400 Body Scale → Home Assistant

Pulls weight + dual-frequency impedance (and derived body-composition metrics) off a
**Xiaomi Body Composition Scale S400 (MJTZC01YM)** locally — no Xiaomi cloud in the live
data path — and lands each weigh-in as Home Assistant sensor data.

A **LOLIN/Wemos D1 Mini ESP32** runs ESPHome's `xiaomi_miscale` platform as a passive BLE
listener. The S400 broadcasts **encrypted** advertisements, so a **bindkey** is required to
decrypt them. Keep the ESP32 near the scale.

## Files

| File | Purpose |
|------|---------|
| `s400-scale.yaml` | ESPHome config (BLE listener + weight/impedance/HR sensors) |
| `secrets.yaml` | Wi-Fi + device keys + **scale MAC & bindkey** (gitignored) |
| `register_device.py` | Repurpose/register the ESP32's HA entry from files (over Samba), then restart HA |
| `create_dashboard_page.py` | Build the dedicated "Body Scale" sidebar view (raw sensors + bodymiscale metrics) |
| `fix_display_precision.py` | Force explicit display precision on the raw sensors |
| `setup_weighin_automation.py` | Push a phone notification on each new weigh-in |

## Setup

1. **Mint the bindkey:** add the scale once in the official Xiaomi Home app.
2. **Extract bindkey + MAC:** run `tools/Xiaomi-cloud-tokens-extractor/token_extractor.py`
   (Mi account login). Put both into `secrets.yaml` (`bindkey`, `scale_mac`).
3. **Validate + flash** (paths with spaces break the ESP32 toolchain — build via a junction):
   ```powershell
   New-Item -ItemType Junction -Path C:\esphome-build -Target "C:\Users\Mads2\Documents\Projects\Projects\Xiaomi S400 Body Data"
   python -m esphome config C:\esphome-build\s400-scale.yaml
   python -m esphome run C:\esphome-build\s400-scale.yaml --device COM15   # first flash = USB
   ```
   Capture the `MAC Address:` and IP from the boot logs. Later flashes can be OTA
   (`--device <device-ip>`).
4. **Wire into HA:** fill HOST/MAC in `register_device.py`, run it, restart HA. Then run
   `fix_display_precision.py` and `setup_weighin_automation.py`; build the dashboard page
   with `create_dashboard_page.py` (run it after bodymiscale is configured so the derived
   metrics resolve). Each `.storage` edit needs an HA restart to show.
5. **Derived metrics:** install [bodymiscale](https://github.com/dckiller51/bodymiscale)
   into `\\192.168.50.203\config\custom_components\bodymiscale`, restart HA, then add the
   integration via the HA UI (First name, DOB, Gender, weight + both impedance sensors,
   **Impedance mode = Dual-frequency S400**). This exposes ~25 metrics including the
   S400-exclusive ECW, ICW, ECW/TBW, Body Cell Mass, Skeletal Muscle Mass.

## Entities

`sensor.s400_body_scale_weight`, `sensor.s400_body_scale_impedance_high`,
`sensor.s400_body_scale_impedance_low`, `sensor.s400_body_scale_heart_rate`,
plus `sensor.{firstname}_{metric}` from bodymiscale.

## Notes

- **S400 support comes from PR [#8524](https://github.com/esphome/esphome/pull/8524)**, pulled
  via `external_components: github://pr#8524` in `s400-scale.yaml`. It is **not in any released
  ESPHome** (the PR was closed as stale but is confirmed working) — stock `xiaomi_miscale` fails
  the S400 with *"couldn't identify scale version"*. The first build clones the PR (needs network).
- The **bindkey is mandatory** — the S400 has no unencrypted passive reads.
- The S400 can be **finicky on first connect**; keep the ESP32 close to the scale.
- bodymiscale's S400 engine is **experimental** (single-point calibration) — trends are
  more trustworthy than absolute body-fat/muscle numbers.
