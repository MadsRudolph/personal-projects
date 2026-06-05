"""One-off: append the dry-soil push automation to HA's automations.yaml (newer schema)."""
import shutil

PATH = r"\\192.168.50.203\config\automations.yaml"
BAK = PATH + ".bak-pre-soil-notifier"
AUTOMATION_ID = "plant_soil_dry_alert"

BLOCK = """\
- id: plant_soil_dry_alert
  alias: Plant soil - dry alert
  description: Notify the phone when the soil sensor reports the plant needs water.
  mode: single
  triggers:
  - trigger: state
    entity_id: binary_sensor.plant_soil_notifier_needs_water
    to: 'on'
    for:
      minutes: 5
  actions:
  - action: notify.mobile_app_sm_s928b
    data:
      title: Plant needs water
      message: "Soil moisture dropped to {{ states('sensor.plant_soil_notifier_soil_moisture') }}% - time to water."
"""

with open(PATH, encoding="utf-8") as f:
    current = f.read()

if AUTOMATION_ID in current:
    print("ALREADY PRESENT - no change made")
else:
    shutil.copy(PATH, BAK)
    sep = "" if current.endswith("\n") else "\n"
    with open(PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(current + sep + BLOCK)
    print(f"Backup written: {BAK}")
    print("Automation appended.")

# Validate the whole file still parses and our automation is present.
try:
    import yaml
    with open(PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    ids = [a.get("id") for a in data]
    assert AUTOMATION_ID in ids, "automation id missing after write"
    print(f"Validation OK - {len(data)} automations, '{AUTOMATION_ID}' present")
except ImportError:
    print("PyYAML not available - skipped parse validation (text append only)")
