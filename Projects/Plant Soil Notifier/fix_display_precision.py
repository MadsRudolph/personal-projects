"""Force explicit 0-decimal display precision on the soil moisture sensor."""
import json, shutil

PATH = r"\\192.168.50.203\config\.storage\core.entity_registry"
BAK = PATH + ".bak-pre-soil-precision"
TARGET = "sensor.plant_soil_notifier_soil_moisture"

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)

ent = next(e for e in data["data"]["entities"] if e["entity_id"] == TARGET)
opts = ent.setdefault("options", {})
sensor_opts = opts.setdefault("sensor", {})
before = dict(sensor_opts)
sensor_opts["display_precision"] = 0

if before == sensor_opts:
    print("ALREADY SET - no change")
else:
    shutil.copy(PATH, BAK)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Backup: {BAK}")
    print(f"sensor options now: {sensor_opts}")

with open(PATH, encoding="utf-8") as f:
    json.load(f)
print("Validation OK - valid JSON")
