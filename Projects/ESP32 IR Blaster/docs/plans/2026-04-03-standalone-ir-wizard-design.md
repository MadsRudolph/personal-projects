# Standalone IR Wizard — Design

## Goal

Make the D1 Mini IR blaster work as a completely standalone appliance. No Home Assistant, no PC. The user connects to the ESP32's web UI, learns IR codes from physical remotes, saves them, and replays them.

## Architecture

- ESPHome custom component (`ir_wizard`) on ESP32 D1 Mini
- Single HTML+JS+CSS file served from LittleFS (`/www/index.html`)
- Learned codes stored as JSON on LittleFS (`/data/devices.json`)
- REST API endpoints for learn/send/save/list
- Uses ESPHome's `remote_transmitter` and `remote_receiver` for IR

## REST API

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Serves the wizard HTML |
| `/api/devices` | GET | List all saved device profiles |
| `/api/devices` | POST | Create a new device profile |
| `/api/devices/{id}` | DELETE | Delete a device profile |
| `/api/devices/{id}/buttons` | POST | Add a learned button |
| `/api/devices/{id}/buttons/{idx}` | DELETE | Remove a button |
| `/api/send` | POST | Send an IR code |
| `/api/learn/start` | POST | Start listening for IR |
| `/api/learn/result` | GET | Poll for captured IR code |
| `/api/learn/stop` | POST | Stop listening |

## Storage Format

```json
[
  {
    "id": "samsung-tv",
    "name": "Samsung TV",
    "buttons": [
      {
        "name": "Power",
        "protocol": "NEC",
        "address": "0x0E0E",
        "command": "0xF30C",
        "raw_data": null
      }
    ]
  }
]
```

## Web UI

Single `index.html` with two views:
1. **Home** — device cards with button grids, tap to send IR
2. **Learn Mode** — capture codes from physical remote, name buttons, test, save

## File Structure

```
Projects/ESP32 IR Blaster/
  ir-blaster-d1mini.yaml
  custom_components/ir_wizard/
    __init__.py
    ir_wizard.h
    ir_wizard.cpp
  data/www/
    index.html
```

## Decisions

- Remove `api:` section (no HA)
- Remove ESPHome `web_server:` (custom component handles HTTP)
- Protocols: NEC, Samsung, Samsung36, Sony, RC5, RC6, LG, Panasonic, Pioneer, JVC, Dish, Coolix, Pronto
- IR receiver callbacks forward decoded data to custom component
