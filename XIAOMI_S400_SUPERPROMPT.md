# SUPERPROMPT — Xiaomi S400 scale → Home Assistant (autonomous build)

You are a fresh Claude Code session working in the `Projects` repo
(`C:\Users\Mads2\Documents\Projects`). This document is a **self-contained brief**:
the project spec + all operational knowledge you need to flash the ESP32 and wire it into
Home Assistant **without asking the user to flash anything or click around in HA**.

> ⚠️ This file contains the Wi-Fi password and HA access details. It is **gitignored — never
> commit it**, and never copy its secrets into a committed file. Real secrets live only in the
> project's `secrets.yaml` (also gitignored).
>
> A complete working reference device is [`Projects/Plant Soil Notifier/`](Projects/Plant%20Soil%20Notifier/) —
> copy its structure and its helper scripts (`add_dashboard_card.py`, `setup_notifier_automation.py`,
> `fix_display_precision.py`) for the HA-side steps. The generic device handoff is
> `ESP_NEW_DEVICE_HANDOFF.md` (same directory).

---

## HOW TO OPERATE

1. The spec is already defined (below) — **don't re-brainstorm it.** Confirm the few user inputs
   in §1, then build autonomously.
2. Do everything you can from files (flashing over USB/OTA, HA device registration over Samba,
   dashboard, component install). Only ask the user for the handful of things **only they can do**
   (bindkey extraction, physical scale steps, and the bodymiscale UI form — see §1 and §6).
3. Validate every ESPHome change with `python -m esphome config ...` before flashing.
4. Commit project files at the end (NOT `secrets.yaml`, NOT this superprompt). **No "Claude"/AI
   mentions in commit messages.**

---

## 1. INPUTS TO GET FROM THE USER (ask up front, then proceed)

| # | Input | Notes |
|---|---|---|
| 1 | **Scale MAC address** | `XX:XX:XX:XX:XX:XX`. From the Xiaomi Home app or the cloud-tokens extractor. |
| 2 | **Bindkey** (32 hex chars) | Extract with the bundled tool (§1a) — needs the user's Mi account login. Mandatory; the S400 broadcasts are encrypted. |
| 3 | **Single or multi-user?** | If multi, which scale **profile id(s)** to accept (`allowed_profile_ids`). If single, omit the filter. |
| 4 | **For bodymiscale (optional metrics):** height (cm), date of birth (YYYY-MM-DD), gender | Needed only if building the derived body-composition metrics (§6). Personal → ask. |
| 5 | **What is the data ultimately for?** | Trend graphs / health log / automations / export. Can defer the downstream piece (§7). |

Already known (do **not** ask): ESPHome **2025.12.4**; board **`wemos_d1_mini32`** (LOLIN D1 Mini
ESP32, has BLE); first-flash serial port **COM15** (Silicon Labs CP210x); HA push target
`notify.mobile_app_sm_s928b`.

### 1a. Extracting the bindkey (do this before flashing)
The **Xiaomi Cloud Tokens Extractor** is already cloned locally at
`tools/Xiaomi-cloud-tokens-extractor/` (gitignored). It logs into the user's Mi account and lists
every device with its token and — for BLE devices like the S400 — its **bindkey/beaconkey**.

Login is interactive and needs the user's Mi credentials (and possibly 2FA + server region), so
**run it together with the user** (or have them run it and paste back the scale's bindkey + MAC):
```powershell
cd "C:\Users\Mads2\Documents\Projects\tools\Xiaomi-cloud-tokens-extractor"
python -m pip install -r requirements.txt
python token_extractor.py
```
It prompts for username (e-mail/account ID) & password (or QR code), then a server region (`cn`,
`de`, `us`, `ru`, `sg`, … — leave empty to scan all). Find the **S400** in the output and take its
**bindkey** (→ input #2) and **MAC** (→ input #1). Prerequisite: the user must have added the scale
once in the **Xiaomi Home app** first (that mints the bindkey). The key is stable until the scale is
removed and re-added in the app. The HA integration's email/password re-auth is reported NOT to work
for the S400 — this extractor is the route that does.

---

## 2. THE PROJECT (spec)

**Goal:** Pull weight + dual-frequency impedance (and derived body-composition metrics) off a
**Xiaomi Body Composition Scale S400 (MJTZC01YM)** locally — no Xiaomi cloud in the live data path
— and land each weigh-in as Home Assistant sensor data (HAOS on a Raspberry Pi).

**Pipeline:**
1. **Mint bindkey:** user adds the scale once in the official Xiaomi Home app (generates a stable bindkey).
2. **Extract bindkey:** user runs the *Xiaomi Cloud Tokens Extractor* (the HA email/password re-auth
   reportedly does NOT work for the S400 — the extractor is the route that works).
3. **ESPHome on the D1 Mini ESP32:** `platform: xiaomi_miscale` with the scale MAC, bindkey, and the
   weight + dual impedance sensors. The ESP32 acts as a BLE listener; place it near the scale.
4. **Derive metrics:** feed weight + both impedance values into the **`bodymiscale`** HACS custom
   component in **Dual-frequency S400** mode (computes ~25 metrics locally).
5. **Downstream:** once it's HA sensor data, expose via graphs / REST / MQTT / InfluxDB+Grafana / etc.

**Why non-trivial:** unlike the Mi Scale 2, the **S400 broadcasts *encrypted* BLE advertisements** —
you need the bindkey to decrypt. Supported in a recent ESPHome `xiaomi_miscale` (S400 covers
encryption, dual-frequency impedance, heart rate, multi-user profiles).

---

## 3. HARDWARE & FLASHING

- **Board:** LOLIN/Wemos **D1 Mini ESP32** → `board: wemos_d1_mini32`. (ESP8266 D1 Mini would NOT
  work — no BLE.) Framework: **`arduino`** (matches all existing projects). If BLE proves unstable,
  `esp-idf` is a fallback, but try arduino first.
- ESPHome is **not on PATH** → call it as **`python -m esphome ...`**.

### ⚠️ Whitespace-in-path gotcha (always)
The ESP32 toolchain fails on paths with spaces (`Detected a whitespace character in project paths`).
Project folders here have spaces, so **build through a no-space junction**:
```powershell
New-Item -ItemType Junction -Path C:\esphome-build -Target "C:\Users\Mads2\Documents\Projects\Projects\Xiaomi S400 Body Data"
python -m esphome run C:\esphome-build\s400-scale.yaml --device <target>
```

### First flash (this is a NEW/blank board): USB on COM15
A blank board has no ESPHome yet, so OTA is impossible first time. Flash over USB:
```powershell
python -m esphome run C:\esphome-build\s400-scale.yaml --device COM15
```
- Re-check the port if it moved: `[System.IO.Ports.SerialPort]::GetPortNames()`.
- If the upload won't start, hold the board's **BOOT** button during connect.
- **Capture the `MAC Address: XX:XX:...` line from the boot logs — you need it for HA (§4).**
- After it joins Wi-Fi, all later flashes can be OTA: `--device <device-ip>`.

---

## 4. WI-FI & SECRETS

Create `Projects/Xiaomi S400 Body Data/secrets.yaml` (gitignored):
```yaml
wifi_ssid: "WutanLan"
wifi_password: "Tusser!2"
api_encryption_key: "<GENERATE>"   # unique per device
ota_password: "<GENERATE>"         # unique per device
fallback_password: "<GENERATE>"
```
Generate the per-device keys:
```powershell
python -c "import secrets,base64;print(base64.b64encode(secrets.token_bytes(32)).decode())"  # api_encryption_key
python -c "import secrets;print(secrets.token_hex(16))"                                       # ota_password / fallback_password
```

---

## 5. ESPHome CONFIG TO BUILD  (`s400-scale.yaml`)

Schema verified against ESPHome S400 docs PR (esphome.io#4801). **Note the key names:** the
high-frequency sensor key is **`impedance`**; the low-frequency one is **`impedance_low`**.

```yaml
substitutions:
  device_name: s400-scale
  friendly_name: "S400 Body Scale"
  board: wemos_d1_mini32
  scale_mac: "XX:XX:XX:XX:XX:XX"                  # USER INPUT (§1)
  bindkey: "0123456789abcdef0123456789abcdef"     # USER INPUT (§1) — 32 hex chars

esphome:
  name: ${device_name}
  friendly_name: ${friendly_name}

esp32:
  board: ${board}
  framework:
    type: arduino

logger:

api:
  encryption:
    key: !secret api_encryption_key
ota:
  - platform: esphome
    password: !secret ota_password
wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "S400-Scale Fallback"
    password: !secret fallback_password
captive_portal:

# BLE listener — the ESP32 passively receives the scale's encrypted advertisements.
esp32_ble_tracker:

sensor:
  - platform: xiaomi_miscale
    mac_address: ${scale_mac}
    bindkey: ${bindkey}                # required for S400 (decrypts the advertisement)
    weight:
      name: "Weight"
      unit_of_measurement: kg
      accuracy_decimals: 2
    impedance:                         # HIGH frequency (~250 kHz)
      name: "Impedance High"
      unit_of_measurement: "Ω"
      accuracy_decimals: 0
    impedance_low:                     # LOW frequency (~50 kHz)
      name: "Impedance Low"
      unit_of_measurement: "Ω"
      accuracy_decimals: 0
    heart_rate:                        # optional (static HR)
      name: "Heart rate"
    # Multi-user: accept only specific scale profile(s). Omit entirely for single-user / all.
    # allowed_profile_ids:
    #   - 1
```

Then:
1. `python -m esphome config C:\esphome-build\s400-scale.yaml` — if any S400 key is rejected, the
   component may differ from the PR; check the installed `xiaomi_miscale` source and adjust, and
   ensure ESPHome is current.
2. Flash (§3). Confirm online: `ping s400-scale.local`.
3. The scale **re-sends identical bursts every ~2 s** until you step off; the component publishes on
   a stabilized reading. If you see noisy repeats, add a `filters: [- throttle: 5s]` to `weight`.

Resulting entities (friendly_name "S400 Body Scale"):
`sensor.s400_body_scale_weight`, `sensor.s400_body_scale_impedance_high`,
`sensor.s400_body_scale_impedance_low`, `sensor.s400_body_scale_heart_rate`.

---

## 6. HOME ASSISTANT — file access over Samba

HAOS is at **192.168.50.203**, Samba (no creds prompted from this machine). Shares: `config`,
`addons`, `share`, `media`, `backup`. Everything below is under **`\\192.168.50.203\config`**.

**Editing rules:** edit `.storage\*` JSON with **Python's `json`** (NOT PowerShell `ConvertTo-Json`
— it truncates). **Back up first**, re-`json.load` to validate. HA caches these in memory and only
re-reads on **restart** (and may overwrite your edit if it saves first) — so edit, then **restart HA
promptly**, and don't touch the same thing in the UI in between. `automations.yaml` is lighter:
append, then Developer Tools → Actions → `automation.reload` (no restart).

### 6a. Register the ESPHome device in HA (from files)
HA won't know this new device yet. Append a config entry to
`\\192.168.50.203\config\.storage\core.config_entries`, then restart HA. You need: `device_name`
(`s400-scale`), `host` (its IP), `noise_psk` (= the `api_encryption_key` from secrets), and `mac`
(lowercased, from flash logs §3). Use this script (adapt values):

```python
import json, shutil, time, os
from datetime import datetime
CFG = r"\\192.168.50.203\config\.storage\core.config_entries"
DEVICE_NAME, HOST = "s400-scale", "192.168.50.xxx"
NOISE_PSK = "<api_encryption_key from secrets.yaml>"
MAC, TITLE = "aa:bb:cc:dd:ee:ff", "S400 Body Scale"
def ulid():
    C="0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    n=int.from_bytes(int(time.time()*1000).to_bytes(6,"big")+os.urandom(10),"big")
    return "".join(C[(n>>(5*i))&31] for i in range(25,-1,-1))
with open(CFG,encoding="utf-8") as f: data=json.load(f)
if any(e["domain"]=="esphome" and e["data"].get("host")==HOST for e in data["data"]["entries"]):
    print("host already present"); 
else:
    now=datetime.now().astimezone().isoformat()
    data["data"]["entries"].append({"created_at":now,"modified_at":now,
        "data":{"device_name":DEVICE_NAME,"host":HOST,"noise_psk":NOISE_PSK,"password":"","port":6053},
        "disabled_by":None,"discovery_keys":{},"domain":"esphome","entry_id":ulid(),
        "minor_version":1,"options":{"allow_service_calls":False},
        "pref_disable_new_entities":False,"pref_disable_polling":False,"source":"user",
        "subentries":[],"title":TITLE,"unique_id":MAC.lower(),"version":1})
    shutil.copy(CFG,CFG+".bak-pre-s400")
    with open(CFG,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False)
    print("added; RESTART HA")
with open(CFG,encoding="utf-8") as f: json.load(f)
print("valid JSON")
```
Then **restart HA**. Within seconds of reconnect the entities appear in `.storage\core.entity_registry`.
**Fallback if file method misbehaves:** flash → HA auto-discovers via mDNS → the only manual step is
the user pasting the `api_encryption_key`. Tell the user that one step rather than leaving it broken.

### 6b. Dashboard card
Storage-mode dashboard, `sections` views, cards in `views[].sections[].cards`. Copy the approach in
`Plant Soil Notifier/add_dashboard_card.py` (back up, `json.load`, append a grid section to the
`home` view, `json.dump`, validate). Add a weight gauge/tile + the impedance values. **Needs an HA
restart** to show. Decimals: HA's gauge card ignores `suggested_display_precision` — set explicit
`display_precision` in `core.entity_registry` (see `fix_display_precision.py`) or tell the user to
set it in the entity UI for an instant change.

### 6c. (Optional) automation
Append to `automations.yaml` (newer `triggers:`/`actions:` schema), then reload automations. Push
target is **`notify.mobile_app_sm_s928b`**. E.g. notify on each new weigh-in.

---

## 7. bodymiscale (derived body-composition metrics)

**Install (you can do this from files):** copy the component into HA, then restart.
- Download the latest release from https://github.com/dckiller51/bodymiscale/releases, unzip, and
  place the `custom_components/bodymiscale` folder at
  `\\192.168.50.203\config\custom_components\bodymiscale` (create `custom_components` if absent).
  Then restart HA. (Or, if HACS is preferred, the user installs via HACS → search "Bodymiscale".)

**Configure (UI step — bodymiscale has NO YAML config):** this requires a HA UI form you cannot fill
from files. After install + restart, tell the user to do exactly this:
> Settings → Devices & Services → **Add Integration** → "Bodymiscale" → enter **First name**,
> **Date of birth**, **Gender**, choose **Calculation mode**, set **User identification method**
> (single-user: "none"; multi-user: weight-range / profile id), pick the **Weight sensor**
> (`sensor.s400_body_scale_weight`), the **Impedance sensor** (`...impedance_high`) and the
> **low-frequency impedance** (`...impedance_low`), and select **Impedance mode = Dual-frequency S400**.

Dual-frequency S400 mode activates automatically once both impedance sensors are set and the mode is
selected. It then exposes (in addition to BMI, BMR, fat mass, water, muscle, bone, protein, etc.) the
S400-exclusive metrics: **ECW, ICW, ECW/TBW ratio, Body Cell Mass, Skeletal Muscle Mass**, as
`sensor.{firstname}_{metric}` entities — which you can then add to the dashboard (§6b).

---

## 8. GOTCHAS

- **Bindkey/encryption is mandatory** for the S400 — no passive unencrypted reads.
- **bodymiscale S400 engine is experimental** (formulas calibrated on a single reference point) —
  trends are more trustworthy than absolute body-fat/muscle numbers. Note this to the user.
- The S400 is **finicky on first connect** (flashing BT icon, odd sync) — expect some fiddling for a
  clean first read. Keep the ESP32 close to the scale.
- **Multi-user:** decide single vs multi early (it drives `allowed_profile_ids` in ESPHome and the
  user-identification method in bodymiscale).

---

## 9. EXECUTION CHECKLIST

1. Ask the user for the §1 inputs (at minimum MAC + bindkey before flashing is useful; bodymiscale
   personal data only when you reach §7).
2. Create `Projects/Xiaomi S400 Body Data/` — copy `Plant Soil Notifier` as the template.
3. Write `s400-scale.yaml` (§5) and `secrets.yaml` (§4, fresh keys).
4. `python -m esphome config ...` to validate; fix any schema drift.
5. Junction + **USB flash on COM15** (§3); capture the MAC; confirm `ping s400-scale.local`.
6. Register in HA over Samba (§6a) → restart HA → confirm entities in `core.entity_registry`.
7. Dashboard card (§6b) + optional automation (§6c).
8. Install bodymiscale from files (§7) → restart HA → hand the user the one UI config step.
9. Add the derived metrics to the dashboard.
10. Commit project files (NOT `secrets.yaml`, NOT this superprompt; no AI mentions in commits).

## References
- ESPHome xiaomi_miscale: https://esphome.io/components/sensor/xiaomi_miscale/
- S400 docs PR (exact keys): https://github.com/esphome/esphome.io/pull/4801
- bindkey / Obtaining the Bindkey: https://esphome.io/components/sensor/xiaomi_ble/
- bodymiscale (HACS, S400 dual-frequency): https://github.com/dckiller51/bodymiscale
- Xiaomi Cloud Tokens Extractor: https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor
