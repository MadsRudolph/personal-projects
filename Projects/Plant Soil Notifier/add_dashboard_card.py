"""One-off: add a Plant Soil Notifier section to the HA Home view (storage-mode lovelace)."""
import json, shutil

PATH = r"\\192.168.50.203\config\.storage\lovelace.dashboard_dash"
BAK = PATH + ".bak-pre-soil-notifier"

shutil.copy(PATH, BAK)

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)

views = data["data"]["config"]["views"]
home = next(v for v in views if v.get("path") == "home")

section = {
    "type": "grid",
    "cards": [
        {"type": "heading", "heading": "Plant Soil Notifier", "icon": "mdi:sprout"},
        {
            "type": "gauge",
            "entity": "sensor.plant_soil_notifier_soil_moisture",
            "name": "Soil moisture",
            "unit": "%",
            "min": 0,
            "max": 100,
            "needle": True,
            # low moisture = dry = red; recovers to green above the wet-reset threshold
            "severity": {"green": 40, "yellow": 30, "red": 0},
        },
        {
            "type": "tile",
            "entity": "binary_sensor.plant_soil_notifier_needs_water",
            "name": "Needs water",
        },
    ],
}

# Guard against double-insert if this is re-run.
already = any(
    c.get("heading") == "Plant Soil Notifier"
    for s in home.get("sections", [])
    for c in s.get("cards", [])
)
if already:
    print("ALREADY PRESENT - no change made")
else:
    home.setdefault("sections", []).append(section)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Backup written: {BAK}")
    print(f"Home view now has {len(home['sections'])} sections")

# Re-validate the file parses.
with open(PATH, encoding="utf-8") as f:
    json.load(f)
print("Validation OK - file is valid JSON")
