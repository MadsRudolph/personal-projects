"""Create a dedicated 'Body Scale' view (sidebar page) in the storage-mode dashboard,
holding the raw S400 sensors + the bodymiscale (Mads) body-composition metrics. Also
removes the earlier S400 sections from the Home view so cards aren't duplicated.

Idempotent: re-running rebuilds the 'body-scale' view in place and re-strips Home.
Needs an HA restart to show. Supersedes add_dashboard_card.py + add_bodymiscale_cards.py.
"""
import json, shutil

PATH = r"\\192.168.50.203\config\.storage\lovelace.dashboard_dash"
BAK = PATH + ".bak-pre-bodyscale-view"
VIEW_PATH = "body-scale"
HOME_HEADINGS = {"S400 Body Scale", "Body Composition (Mads)"}
P = "sensor.mads_"

raw_section = {
    "type": "grid",
    "cards": [
        {"type": "heading", "heading": "Scale readings", "icon": "mdi:scale-bathroom"},
        {"type": "gauge", "entity": "sensor.s400_body_scale_weight", "name": "Weight",
         "unit": "kg", "min": 40, "max": 120, "needle": True},
        {"type": "tile", "entity": "sensor.s400_body_scale_impedance_high", "name": "Impedance (high)"},
        {"type": "tile", "entity": "sensor.s400_body_scale_impedance_low", "name": "Impedance (low)"},
        {"type": "tile", "entity": "sensor.s400_body_scale_heart_rate", "name": "Heart rate"},
    ],
}

body_section = {
    "type": "grid",
    "cards": [
        {"type": "heading", "heading": "Body composition", "icon": "mdi:human"},
        {"type": "gauge", "entity": P + "body_fat", "name": "Body fat", "unit": "%",
         "min": 0, "max": 45, "needle": True,
         "severity": {"green": 8, "yellow": 20, "red": 30}},
        {"type": "gauge", "entity": P + "body_score", "name": "Body score",
         "min": 0, "max": 100, "needle": True,
         "severity": {"green": 80, "yellow": 60, "red": 0}},
        {"type": "tile", "entity": P + "bmi", "name": "BMI"},
        {"type": "tile", "entity": P + "water", "name": "Water"},
        {"type": "tile", "entity": P + "muscle_mass", "name": "Muscle mass"},
        {"type": "tile", "entity": P + "skeletal_muscle_mass", "name": "Skeletal muscle"},
        {"type": "tile", "entity": P + "bone_mass", "name": "Bone mass"},
        {"type": "tile", "entity": P + "protein", "name": "Protein"},
        {"type": "tile", "entity": P + "visceral_fat", "name": "Visceral fat"},
        {"type": "tile", "entity": P + "lean_body_mass", "name": "Lean body mass"},
        {"type": "tile", "entity": P + "basal_metabolism", "name": "Basal metabolism"},
        {"type": "tile", "entity": P + "metabolic_age", "name": "Metabolic age"},
    ],
}

dualfreq_section = {
    "type": "grid",
    "cards": [
        {"type": "heading", "heading": "Dual-frequency (S400)", "icon": "mdi:sine-wave"},
        {"type": "tile", "entity": P + "extracellular_water", "name": "Extracellular water (ECW)"},
        {"type": "tile", "entity": P + "intracellular_water", "name": "Intracellular water (ICW)"},
        {"type": "tile", "entity": P + "ecw_tbw_ratio", "name": "ECW/TBW ratio"},
        {"type": "tile", "entity": P + "body_cell_mass", "name": "Body cell mass"},
        {"type": "tile", "entity": P + "last_measurement", "name": "Last measurement"},
    ],
}

new_view = {
    "title": "Body Scale",
    "path": VIEW_PATH,
    "icon": "mdi:scale-bathroom",
    "type": "sections",
    "sections": [raw_section, body_section, dualfreq_section],
    "cards": [],
}

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)

shutil.copy(PATH, BAK)
cfg = data["data"]["config"]

# 1) Strip the S400 sections from the Home view (avoid duplication).
home = next((v for v in cfg["views"] if v.get("path") == "home"), None)
if home and home.get("sections"):
    before = len(home["sections"])
    home["sections"] = [
        s for s in home["sections"]
        if not any(c.get("type") == "heading" and c.get("heading") in HOME_HEADINGS
                   for c in s.get("cards", []))
    ]
    print(f"home sections: {before} -> {len(home['sections'])}")

# 2) Replace-or-append the dedicated Body Scale view.
cfg["views"] = [v for v in cfg["views"] if v.get("path") != VIEW_PATH]
cfg["views"].append(new_view)
print(f"views now: {[v.get('title') for v in cfg['views']]}")

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

with open(PATH, encoding="utf-8") as f:
    json.load(f)
print(f"Backup: {BAK}")
print("Validation OK - valid JSON")
