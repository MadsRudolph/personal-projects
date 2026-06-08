"""Force explicit display precision on the S400 sensors (HA gauge ignores
suggested_display_precision). Weight -> 2 decimals; impedance/HR -> 0. Run after
the entities exist; restart HA (or it applies on next reload of the registry)."""
import json, shutil

PATH = r"\\192.168.50.203\config\.storage\core.entity_registry"
BAK = PATH + ".bak-pre-s400-precision"

PRECISION = {
    "sensor.s400_body_scale_weight": 2,
    "sensor.s400_body_scale_impedance_high": 0,
    "sensor.s400_body_scale_impedance_low": 0,
    "sensor.s400_body_scale_heart_rate": 0,
}

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)

changed = False
by_id = {e["entity_id"]: e for e in data["data"]["entities"]}
for entity_id, prec in PRECISION.items():
    ent = by_id.get(entity_id)
    if ent is None:
        print(f"  (skip, not found yet: {entity_id})")
        continue
    sensor_opts = ent.setdefault("options", {}).setdefault("sensor", {})
    if sensor_opts.get("display_precision") != prec:
        sensor_opts["display_precision"] = prec
        changed = True
        print(f"  set {entity_id} -> {prec}")

if changed:
    shutil.copy(PATH, BAK)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Backup: {BAK}")
else:
    print("ALREADY SET (or no target entities present) - no change")

with open(PATH, encoding="utf-8") as f:
    json.load(f)
print("Validation OK - valid JSON")
