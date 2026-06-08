"""Register / repurpose the s400-scale ESPHome device in HA from files (over Samba).

This board (MAC 70:4b:ca:4c:bf:44, host 192.168.50.148) was previously flashed as the
empty "IR Blaster D1 Mini". HA keys esphome config entries by MAC, so an entry for this
board ALREADY exists. We therefore UPDATE that entry in place to point at the S400
firmware (new noise_psk + name) rather than adding a duplicate (which HA would reject).
If no entry for the MAC exists, we append a fresh one.

After running this, RESTART HA. Within seconds of reconnect the S400 entities appear in
.storage/core.entity_registry.
"""
import json, shutil, time, os
from datetime import datetime

CFG = r"\\192.168.50.203\config\.storage\core.config_entries"
DEVICE_NAME = "s400-scale"
HOST = "192.168.50.148"                                    # ESP32 IP (DHCP-stable by MAC)
NOISE_PSK = "IDU1C2aLrkwhpg4G2flwdPZNij05idQybAXbF0S9dS4="  # = new api_encryption_key
MAC = "70:4b:ca:4c:bf:44"                                  # this board's MAC (lowercased)
TITLE = "S400 Body Scale"


def ulid():
    C = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    n = int.from_bytes(int(time.time() * 1000).to_bytes(6, "big") + os.urandom(10), "big")
    return "".join(C[(n >> (5 * i)) & 31] for i in range(25, -1, -1))


with open(CFG, encoding="utf-8") as f:
    data = json.load(f)

now = datetime.now().astimezone().isoformat()
entries = data["data"]["entries"]
existing = next((e for e in entries
                 if e["domain"] == "esphome" and e.get("unique_id") == MAC.lower()), None)

shutil.copy(CFG, CFG + ".bak-pre-s400")

if existing is not None:
    print(f"found existing entry: title={existing.get('title')!r} "
          f"device_name={existing['data'].get('device_name')!r} -> repurposing to S400")
    existing["data"]["device_name"] = DEVICE_NAME
    existing["data"]["host"] = HOST
    existing["data"]["noise_psk"] = NOISE_PSK
    existing["title"] = TITLE
    existing["modified_at"] = now
    print("updated in place; RESTART HA")
else:
    entries.append({
        "created_at": now, "modified_at": now,
        "data": {"device_name": DEVICE_NAME, "host": HOST, "noise_psk": NOISE_PSK,
                 "password": "", "port": 6053},
        "disabled_by": None, "discovery_keys": {}, "domain": "esphome", "entry_id": ulid(),
        "minor_version": 1, "options": {"allow_service_calls": False},
        "pref_disable_new_entities": False, "pref_disable_polling": False, "source": "user",
        "subentries": [], "title": TITLE, "unique_id": MAC.lower(), "version": 1,
    })
    print("no existing entry; appended new; RESTART HA")

with open(CFG, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)

with open(CFG, encoding="utf-8") as f:
    json.load(f)
print("valid JSON")
