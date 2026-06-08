"""One-off: append the new-weigh-in push automation to HA's automations.yaml
(newer schema), then reload automations (Developer Tools -> Actions ->
automation.reload, no restart needed). Notifies the phone with the new weight."""
import shutil

PATH = r"\\192.168.50.203\config\automations.yaml"
BAK = PATH + ".bak-pre-s400"
AUTOMATION_ID = "s400_new_weighin"

BLOCK = """\
- id: s400_new_weighin
  alias: S400 - new weigh-in
  description: Notify the phone whenever the S400 scale reports a new weight.
  mode: single
  triggers:
  - trigger: state
    entity_id: sensor.s400_body_scale_weight
  conditions:
  - condition: template
    value_template: "{{ trigger.to_state.state not in ['unknown', 'unavailable'] }}"
  actions:
  - action: notify.mobile_app_sm_s928b
    data:
      title: New weigh-in
      message: "Weight: {{ states('sensor.s400_body_scale_weight') }} kg"
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

try:
    import yaml
    with open(PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    ids = [a.get("id") for a in data]
    assert AUTOMATION_ID in ids, "automation id missing after write"
    print(f"Validation OK - {len(data)} automations, '{AUTOMATION_ID}' present")
except ImportError:
    print("PyYAML not available - skipped parse validation (text append only)")
