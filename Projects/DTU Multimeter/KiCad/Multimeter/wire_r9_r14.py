"""Wire R9-R14 current shunt resistors -- fuse terminal side.

R9-R14 all centered at x=313.69:
  RIGHT pin (x=317.5) -- already wired to U3 channel pins
  LEFT pin  (x=309.88) -- needs connection to fuse nets

Resistor positions and angles:
  R9:  (313.69, 64.77,  90)  -- 10k,   500 uA shunt
  R10: (313.69, 67.31,  90)  -- 998,   5 mA shunt
  R11: (313.69, 80.01, 270)  -- 99.49, 50 mA shunt
  R12: (313.69, 82.55,  90)  -- 10.04, 400 mA shunt
  R13: (313.69, 74.93,  90)  -- 1.05,  5 A shunt
  R14: (313.69, 77.47,  90)  -- 0.145, 10 A shunt

Wiring guide:
  R9-R13 pin 2 -> mA terminal (via F2) -> FUSE_mA net
  R14 pin 2    -> 10A terminal (via F1) -> FUSE_10A net

Adds:
  - 5 FUSE_mA labels at R9, R10, R11, R12, R13 left pins
  - 1 FUSE_10A label at R14 left pin
"""
import uuid, shutil
from pathlib import Path

SCH = Path(r"C:\Users\Mads2\Documents\Projects\Projects\DTU Multimeter\KiCad\Multimeter\Multimeter.kicad_sch")

def uid():
    return str(uuid.uuid4())

# ---------- Load ----------
shutil.copy2(SCH, SCH.with_suffix(".kicad_sch.bak"))
content = SCH.read_text(encoding="utf-8")

# =========================================================
# Helpers
# =========================================================
def label_str(name, x, y, angle, hjust="left", vjust="bottom"):
    return f'''
	(label "{name}"
		(at {x} {y} {angle})
		(effects
			(font
				(size 1.27 1.27)
			)
			(justify {hjust} {vjust})
		)
		(uuid "{uid()}")
	)'''

elements = []

# =========================================================
# Left pin positions (x=309.88) for each resistor
# =========================================================
LEFT_X = 309.88

# R9-R13: connect to FUSE_mA net (mA terminal via F2)
fuse_ma_resistors = [
    ("R9",  64.77),
    ("R10", 67.31),
    ("R13", 74.93),
    ("R11", 80.01),
    ("R12", 82.55),
]

for ref, y in fuse_ma_resistors:
    # angle=180 -> text extends left, justify right
    elements.append(label_str("FUSE_mA", LEFT_X, y, 180, "right", "bottom"))
    print(f"Label: FUSE_mA at ({LEFT_X}, {y}) -- {ref} left pin")

# R14: connect to FUSE_10A net (10A terminal via F1)
elements.append(label_str("FUSE_10A", LEFT_X, 77.47, 180, "right", "bottom"))
print(f"Label: FUSE_10A at ({LEFT_X}, 77.47) -- R14 left pin")

# =========================================================
# Inject before final closing paren
# =========================================================
last_paren = content.rfind(')')
inject = ''.join(elements)
content = content[:last_paren] + inject + '\n' + content[last_paren:]

# =========================================================
# Save
# =========================================================
SCH.write_text(content, encoding="utf-8")
print(f"\nDone! 5x FUSE_mA + 1x FUSE_10A labels added. Saved.")
