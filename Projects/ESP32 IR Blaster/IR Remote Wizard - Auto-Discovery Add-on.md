---
title: IR Remote Wizard - Auto-Discovery Add-on
type: sub-project
tags:
  - electronics
  - esp32
  - home-assistant
  - smart-home
  - python
  - active-project
status: Initial Implementation
started: 2026-02-18
updated: 2026-02-18
parent: "[[ESP32 IR Blaster - Smart Home]]"
repo: https://github.com/MadsRudolph/ir-remote-wizard
---

# IR Remote Wizard - Auto-Discovery Add-on

Back to [[ESP32 IR Blaster - Smart Home]]

> [!summary] **Project Goal**
> A Home Assistant add-on that auto-discovers working IR codes for any device using the [Flipper-IRDB](https://github.com/Lucaslhm/Flipper-IRDB) database — no original remote needed. Walks the user through a guided wizard to identify which codes work, then generates a ready-to-flash ESPHome config.

---

## 🔗 Quick Links

- [GitHub Repository](https://github.com/MadsRudolph/ir-remote-wizard)
- [[#Architecture|Architecture Overview]]
- [[#Wizard Flow|Wizard Flow]]
- [[#Protocol Support|Supported Protocols]]
- [[ESP32 IR Blaster - Smart Home|Main Project Page]]

---

## 🏗️ Architecture

```
┌──────────────────────────┐      ┌─────────────────┐
│  HA Add-on               │      │  ESP32 IR Blaster│
│  ┌────────────────────┐  │      │                  │
│  │ Web UI (ingress)   │  │      │  Custom API      │
│  │ - Device wizard    │  │ ───> │  services:       │
│  │ - Code testing     │  │ API  │  - send_ir_nec   │
│  │ - Results/export   │  │      │  - send_ir_raw   │
│  └────────────────────┘  │      │  - send_ir_*     │
│  ┌────────────────────┐  │      │                  │
│  │ SQLite DB          │  │      └─────────────────┘
│  │ (Flipper-IRDB      │  │
│  │  pre-processed)    │  │
│  └────────────────────┘  │
│  ┌────────────────────┐  │      ┌─────────────────┐
│  │ YAML Generator     │──│──────│ /homeassistant/  │
│  │                    │  │write │ esphome/         │
│  └────────────────────┘  │      │ ir-blaster.yaml  │
└──────────────────────────┘      └─────────────────┘
```

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web app** | FastAPI + Jinja2 | Wizard UI via HA ingress |
| **IR database** | SQLite (built from Flipper-IRDB) | Thousands of known IR codes |
| **ESP32 client** | aioesphomeapi | Send test codes to the IR blaster |
| **YAML generator** | Python | Output ESPHome config with confirmed buttons |

---

## 🧙 Wizard Flow

### Phase 1: Identify (Power Code Search)

1. **Connect** — Enter ESP32 IP address and API encryption key
2. **Device type** — Select TV, AC, Soundbar, etc.
3. **Brand** — Select brand or "I don't know" (tries all)
4. **Power code search** — The wizard sends unique power codes one by one. User confirms "yes" (device responded) or "no" (try next). This locks in the protocol and device family

### Phase 2: Map Buttons

5. **Button discovery** — For the matched device, tests each button function: Volume, Channel, Navigation, Input, Playback, etc. User confirms each one

### Phase 3: Export

6. **Results** — Shows all confirmed working buttons. Generates an ESPHome YAML config and can save it directly to `/homeassistant/esphome/ir-blaster.yaml` for flashing from the ESPHome dashboard

---

## 📡 Protocol Support

Maps Flipper-IRDB protocol names to ESPHome transmitter actions:

| Flipper Protocol | ESPHome Service | Notes |
|---|---|---|
| NEC, NECext, NEC42, NEC42ext | `transmit_nec` | 16-bit LE address from first 2 bytes |
| Samsung32 | `transmit_samsung` | Address + command combined into data |
| RC5, RC5X | `transmit_rc5` | 8-bit address + command |
| RC6 | `transmit_rc6` | 8-bit address + command |
| SIRC, SIRC15, SIRC20 | `transmit_sony` | data + nbits (12/15/20) |
| Kaseikyo, RCMM, Pioneer | `transmit_raw` | Converted to raw timing data |
| raw | `transmit_raw` | Direct timing data from database |

> [!info] **Flipper Address Format**
> Flipper stores addresses as 4-byte space-separated hex in little-endian order:
> - `34 DB 00 00` → `0xDB34` (16-bit NEC extended)
> - `07 00 00 00` → `0x07` (8-bit Samsung)

---

## 📁 Repository Structure

```
ir-remote-wizard/
├── repository.yaml              # HA add-on repository metadata
├── ir-remote-wizard/
│   ├── config.yaml              # HA add-on config (ingress, options)
│   ├── Dockerfile               # Clones Flipper-IRDB at build time
│   ├── build.yaml               # Multi-arch (amd64, aarch64, armv7)
│   ├── run.sh                   # Builds DB on first run, starts uvicorn
│   ├── requirements.txt         # FastAPI, aioesphomeapi, Jinja2, etc.
│   │
│   ├── app/
│   │   ├── main.py              # FastAPI routes for wizard flow
│   │   ├── config.py            # Reads HA add-on options
│   │   ├── database.py          # SQLite access layer
│   │   ├── discovery.py         # Wizard state machine
│   │   ├── esphome_client.py    # aioesphomeapi wrapper
│   │   ├── protocol_map.py      # Flipper → ESPHome protocol conversion
│   │   ├── yaml_generator.py    # ESPHome YAML output
│   │   ├── templates/           # Jinja2 HTML (connect, device, brand, discovery, results)
│   │   └── static/              # CSS + JS
│   │
│   └── scripts/
│       └── build_database.py    # Parses Flipper-IRDB .ir files → SQLite
│
└── esphome/
    └── ir-blaster-discovery.yaml  # ESPHome config with dynamic IR API services
```

---

## 🔧 ESPHome Discovery Config

The wizard requires a special ESPHome config on the ESP32 that exposes API services for each IR protocol. This allows the add-on to send any IR code on demand without reflashing.

The config is at `esphome/ir-blaster-discovery.yaml` in the repo. Key difference from the standard config: it includes `api.services` entries for `send_ir_nec`, `send_ir_samsung`, `send_ir_sony`, `send_ir_rc5`, `send_ir_rc6`, and `send_ir_raw`.

> [!important] **Flash First**
> The ESP32 must be flashed with the discovery config before using the wizard. The standard config only has hardcoded button entities — the discovery config accepts dynamic IR codes via the API.

---

## 📊 Database

The SQLite database is built at first container startup from the [Flipper-IRDB](https://github.com/Lucaslhm/Flipper-IRDB) repository (cloned during Docker build).

**Schema:**

| Table | Purpose |
|-------|---------|
| `devices` | Device type, brand, model (inferred from directory structure) |
| `codes` | Button name, protocol, address, command, raw data per device |

**Indexes:** `(device_type, brand)`, `(device_id)`, `(button_name)`

The Flipper-IRDB has thousands of `.ir` files organized as `DeviceType/Brand/Model.ir`.

---

## 🛠️ Development Status

- [x] **Repository structure** — HA add-on scaffold with Dockerfile, config, run.sh
- [x] **Database builder** — Parses Flipper-IRDB `.ir` files into SQLite
- [x] **Protocol mapping** — Flipper hex → ESPHome int conversion for all major protocols
- [x] **ESPHome discovery config** — API services for dynamic IR transmission
- [x] **ESPHome client** — aioesphomeapi wrapper for sending IR codes
- [x] **Discovery engine** — Wizard state machine (identify → map → export)
- [x] **YAML generator** — Generates ESPHome config with confirmed buttons
- [x] **Web UI** — Full wizard flow (connect → device → brand → discover → results)
- [ ] **Test as local HA add-on** — Install and run through the full wizard flow
- [ ] **AC / climate entity support** — Handle AC units with temperature/mode codes
- [ ] **Hold button detection** — Auto-detect NEC repeat code buttons (volume, channel)
- [ ] **"Learn from remote" fallback** — Use the IR receiver if database codes don't match
- [ ] **Error handling & recovery** — Connection drops, timeouts, retry logic

---

## 📚 References

- [Flipper-IRDB](https://github.com/Lucaslhm/Flipper-IRDB) — Source database of IR codes
- [aioesphomeapi](https://github.com/esphome/aioesphomeapi) — Python library for ESPHome native API
- [Home Assistant Add-on Development](https://developers.home-assistant.io/docs/add-ons) — HA add-on architecture
- [ESPHome Remote Transmitter](https://esphome.io/components/remote_transmitter.html) — IR transmitter component docs

---
