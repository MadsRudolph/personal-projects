# ESP Device Handoff — flashing + Home Assistant onboarding

**Purpose:** give a fresh Claude Code session everything it needs to build a NEW ESPHome
device and get it fully into Home Assistant **without asking the user to flash or click
anything in HA**. The user will describe the new device; you do the rest using the facts below.

> ⚠️ This file contains the Wi-Fi password and HA details. It is gitignored — **do not commit it**
> and do not paste its secrets into any committed file. Real secrets only ever go in `secrets.yaml`
> (also gitignored).

A complete, working reference device lives in [`Projects/Plant Soil Notifier/`](Projects/Plant%20Soil%20Notifier/) —
copy its structure. Its helper scripts (`add_dashboard_card.py`, `setup_notifier_automation.py`,
`fix_display_precision.py`) are runnable examples for the HA-side steps.

---

## 0. Environment facts

| Thing | Value |
|---|---|
| OS | Windows. ESPHome is **not on PATH** → call it as `python -m esphome ...` |
| ESPHome version | 2025.12.4 |
| Framework | Use `arduino` (matches all existing projects) |
| Common board strings | `esp32dev` (generic ESP32 devkit / DHT / temp / IR), `wemos_d1_mini32` (D1 Mini ESP32), `lolin_d32`. If unsure, `esp32dev` works for most ESP32 devkits. |
| Project convention | One folder per device under `Projects/`, files: `<name>.yaml`, `secrets.yaml`, `README.md`, optional `home-assistant.yaml`. All tunables in a `substitutions:` block at the top of the yaml. |

### ADC pin rule (analog sensors only)
ESP32 **ADC2 dies when Wi-Fi is on.** Any analog sensor MUST use an **ADC1** pin:
**GPIO32, 33, 34, 35, 36, 39.** GPIO16/23/etc. have *no ADC* and will read garbage.
(GPIO34–39 are input-only; GPIO32/33 are ADC1 *and* output-capable.)

---

## 1. Wi-Fi credentials (shared across all the user's devices)

Put these in the new project's `secrets.yaml` (which is gitignored):

```yaml
wifi_ssid: "WutanLan"
wifi_password: "Tusser!2"
api_encryption_key: "<GENERATE PER DEVICE - see below>"
ota_password: "<GENERATE PER DEVICE - see below>"
fallback_password: "<any short string, e.g. generate>"
```

Wi-Fi SSID/password are the same on every device. **`api_encryption_key` and `ota_password`
should be unique per device** — generate fresh ones:

```powershell
# api_encryption_key (32 random bytes, base64):
python -c "import secrets,base64;print(base64.b64encode(secrets.token_bytes(32)).decode())"
# ota_password and fallback_password (random hex):
python -c "import secrets;print(secrets.token_hex(16))"
```

The standard ESPHome skeleton (copy from `Plant Soil Notifier/soil-notifier.yaml`):
`wifi` + `captive_portal` + `api:` (with `encryption: key: !secret api_encryption_key`) +
`ota:` (`platform: esphome`, `password: !secret ota_password`).

---

## 2. Flashing the board

### ⚠️ Whitespace-in-path gotcha (always applies on this machine)
The ESP32 toolchain (ESP-IDF under Arduino) **fails on paths containing spaces** with
`Detected a whitespace character in project paths`. Project folders here have spaces, so
**always build through a no-space directory junction:**

```powershell
New-Item -ItemType Junction -Path C:\esphome-build -Target "C:\Users\Mads2\Documents\Projects\Projects\<Folder With Spaces>"
python -m esphome run C:\esphome-build\<name>.yaml --device <target>
```
The junction points at the same real folder, so source/secrets/build output stay in place.
(Reuse or recreate `C:\esphome-build` per device; remove a stale one via PowerShell if needed.)

### Case A — brand-new / blank board (first flash): USB
A new board has no ESPHome yet, so the first flash must be over **USB**.

> As of this handoff the new blank board enumerates as **COM15** (Silicon Labs CP210x USB-UART).
> COM numbers can change with USB port — re-check with:
> `[System.IO.Ports.SerialPort]::GetPortNames()`. A CP210x/CH340 bridge means it's a standard
> ESP32 devkit; confirm the exact `board:` string from the board's markings (likely `esp32dev`
> or `lolin_d32`) before flashing.

1. Plug the board in. Find its COM port (Device Manager → Ports, or run `python -m esphome run ...`
   without `--device` and it lists serial ports).
2. `python -m esphome run C:\esphome-build\<name>.yaml --device COM<N>`
3. Watch logs for the line `MAC Address: XX:XX:XX:XX:XX:XX` — **save this MAC**, you need it for HA (§3).

### Case B — board already running ESPHome (re-flash): OTA, no USB
1. Find its current IP: `ping <current-name>.local`, or check HA / the router.
2. **The config's `ota_password` must match what's currently ON the device**, or OTA auth fails.
   If reusing a previously-flashed board, set `secrets.yaml` `ota_password` (and `api_encryption_key`)
   to that board's existing values first, flash, and it will adopt the new firmware. The other
   devices' real secrets are in their own (gitignored) `Projects/*/secrets.yaml` files.
3. `python -m esphome run C:\esphome-build\<name>.yaml --device <ip>`

After any flash, confirm the device is up: `ping <new-name>.local`.

---

## 3. Home Assistant — file access over Samba

HAOS is at **192.168.50.203**, exposed via Samba (no credentials prompted from this machine).
Shares: `config`, `addons`, `share`, `media`, `backup`. Everything below is under **`\\192.168.50.203\config`**.

Key files:
| Path | What |
|---|---|
| `.storage\core.config_entries` | Integrations (incl. ESPHome devices) |
| `.storage\core.entity_registry` | All entities + per-entity display options |
| `.storage\lovelace.dashboard_dash` | Main dashboard (storage-mode JSON, `sections` views) |
| `automations.yaml` | Automations (newer `triggers:`/`actions:` schema) |

**Editing rules (important):**
- Edit JSON `.storage` files with **Python's `json`**, never PowerShell `ConvertTo-Json` (its
  default depth silently truncates the big files). **Always back up first**, then re-`json.load`
  to validate.
- HA holds these in memory and only re-reads `.storage` on **restart**, and may overwrite your
  file edit if it saves first. So: make the edit, then **restart HA promptly** and don't touch
  the same thing in the UI in between.
- `automations.yaml` is lighter: append, then **Reload Automations** (Developer Tools → Actions →
  `automation.reload`) — no full restart needed.

### 3a. Register a NEW ESPHome device in HA (fully from files)
For a brand-new device at a new IP, HA doesn't know it yet. Add a config entry, then restart HA.
You need: `device_name` (from the yaml), `host` (IP), `noise_psk` (= the `api_encryption_key`
you put in secrets), and `mac` (from flash logs, §2 Case A). Run this script (adapt the values):

```python
import json, shutil, time, os
from datetime import datetime

CFG = r"\\192.168.50.203\config\.storage\core.config_entries"
DEVICE_NAME = "my-new-device"          # esphome name: in the yaml
HOST        = "192.168.50.xxx"          # device IP
NOISE_PSK   = "<api_encryption_key>"    # SAME value as secrets.yaml api_encryption_key
MAC         = "aa:bb:cc:dd:ee:ff"       # lowercase, from flash logs
TITLE       = "My New Device"

def ulid():
    CROCK = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    n = int.from_bytes(int(time.time()*1000).to_bytes(6,"big") + os.urandom(10), "big")
    return "".join(CROCK[(n >> (5*i)) & 31] for i in range(25, -1, -1))

with open(CFG, encoding="utf-8") as f:
    data = json.load(f)

if any(e["domain"]=="esphome" and e["data"].get("host")==HOST for e in data["data"]["entries"]):
    print("Entry for this host already exists - skipping")
else:
    now = datetime.now().astimezone().isoformat()
    data["data"]["entries"].append({
        "created_at": now, "modified_at": now,
        "data": {"device_name": DEVICE_NAME, "host": HOST,
                 "noise_psk": NOISE_PSK, "password": "", "port": 6053},
        "disabled_by": None, "discovery_keys": {}, "domain": "esphome",
        "entry_id": ulid(), "minor_version": 1,
        "options": {"allow_service_calls": False},
        "pref_disable_new_entities": False, "pref_disable_polling": False,
        "source": "user", "subentries": [], "title": TITLE,
        "unique_id": MAC.lower(), "version": 1,
    })
    shutil.copy(CFG, CFG + ".bak-pre-newdevice")
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print("Added. Backup written. RESTART HA to connect.")

with open(CFG, encoding="utf-8") as f: json.load(f)  # validate
print("core.config_entries is valid JSON")
```

Then **restart HA** (Settings → System → Restart, or `ha core restart`). Within a few seconds of
reconnecting, the device's entities appear in `.storage\core.entity_registry`. Their IDs follow
the `friendly_name` you set, e.g. friendly_name "My New Device" → `sensor.my_new_device_<entity>`.

**Fallback if the file method misbehaves:** flash the device — HA auto-discovers ESPHome devices
via mDNS and shows a "discovered" prompt; the only manual step is pasting the `api_encryption_key`.
Tell the user that single step rather than leaving it broken.

### 3b. Add a dashboard card
The dashboard is **storage-mode**, views are `sections` type (cards live in `views[].sections[].cards`).
Copy [`Plant Soil Notifier/add_dashboard_card.py`](Projects/Plant%20Soil%20Notifier/add_dashboard_card.py):
back up, `json.load`, append a `{"type":"grid","cards":[...]}` section to the `home` view, `json.dump`,
re-validate. **Needs an HA restart** to show (storage-mode).

Decimals tip: HA's **gauge card ignores `suggested_display_precision`.** For whole-number gauges,
set explicit `display_precision` in `core.entity_registry` options (see `fix_display_precision.py`),
or tell the user to set it in the entity's UI (Settings → Entities → ⚙ → Display precision) for an
instant, no-restart change.

### 3c. Add a notification automation
Append to `automations.yaml` (newer schema), then reload automations. The user's push target is
**`notify.mobile_app_sm_s928b`** (their Galaxy) — use that, not `notify.notify`. Copy
[`Plant Soil Notifier/setup_notifier_automation.py`](Projects/Plant%20Soil%20Notifier/setup_notifier_automation.py).

---

## 4. Known devices on the network (for reference)

| Device | IP | Notes |
|---|---|---|
| HAOS | 192.168.50.203 | Samba host |
| DHT Sensor | 192.168.50.116 | esp32dev |
| IR Blaster | 192.168.50.120 | |
| IR Blaster D1 Mini | 192.168.50.148 | |
| Plant Soil Notifier | 192.168.50.164 | ex-"Temp Sensor" board, `wemos_d1_mini32`, GPIO32 capacitive sensor |

---

## 5. End-to-end checklist for a new device

1. Create `Projects/<New Device>/` — copy `Plant Soil Notifier` as a template.
2. Write `<name>.yaml` (substitutions: name, friendly_name, board, pins — ADC1 for analog).
3. Write `secrets.yaml` (shared Wi-Fi above + freshly generated api/ota keys).
4. Validate: `python -m esphome config C:\esphome-build\<name>.yaml`.
5. Flash: USB for a blank board (save the MAC), OTA for a re-used one (match its ota_password).
6. Confirm online: `ping <name>.local`.
7. Register in HA (§3a) → restart HA → confirm entities in `core.entity_registry`.
8. Dashboard card (§3b) + automation (§3c) as the device needs.
9. Commit the project files (NOT secrets.yaml, NOT this handoff). No "Claude"/AI mentions in commits.
