"""Wire R1-R8 reference resistors -- probe input side.

R1-R8 at angle=270, all centered at x=240.03:
  Pin 2 (LEFT,  x=236.22) -- already wired to U2 channels I0-I7
  Pin 1 (RIGHT, x=243.84) -- needs connection to probe input (ADC_CH2 net)

Resistor Y positions (same as U2 channel Y positions):
  R1: 62.23   R2: 64.77   R3: 67.31   R4: 69.85
  R5: 72.39   R6: 74.93   R7: 77.47   R8: 80.01

Adds:
  - 1 vertical bus wire at x=243.84 from R1 to R8 (y=62.23 to y=80.01)
  - 6 junctions at R2-R7 pin positions (intermediate taps on bus)
  - 1 ADC_CH2 label at the top of the bus (connects to probe input net)
"""
import uuid, shutil, re
from pathlib import Path

SCH = Path(r"C:\Users\Mads2\Documents\Projects\Projects\DTU Multimeter\KiCad\Multimeter\Multimeter.kicad_sch")
PROJ_UUID = "ac1a6b26-ab53-454a-b718-b2b6f7a3a514"

def uid():
    return str(uuid.uuid4())

# ---------- Load ----------
shutil.copy2(SCH, SCH.with_suffix(".kicad_sch.bak"))
content = SCH.read_text(encoding="utf-8")

# =========================================================
# Helpers
# =========================================================
def wire(x1, y1, x2, y2):
    return f'''
	(wire
		(pts
			(xy {x1} {y1}) (xy {x2} {y2})
		)
		(stroke
			(width 0)
			(type default)
		)
		(uuid "{uid()}")
	)'''

def junction(x, y):
    return f'''
	(junction
		(at {x} {y})
		(diameter 0)
		(color 0 0 0 0)
		(uuid "{uid()}")
	)'''

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
# Pin 1 (RIGHT side) positions at x=243.84
# =========================================================
PIN1_X = 243.84
r_ys = [62.23, 64.77, 67.31, 69.85, 72.39, 74.93, 77.47, 80.01]
r_names = ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"]

# =========================================================
# 1. Vertical bus wire connecting all pin 1's
# =========================================================
elements.append(wire(PIN1_X, r_ys[0], PIN1_X, r_ys[-1]))
print(f"Wire: vertical bus ({PIN1_X}, {r_ys[0]}) -> ({PIN1_X}, {r_ys[-1]})")

# =========================================================
# 2. Junctions at R2-R7 (intermediate pins on the bus)
# =========================================================
for i in range(1, 7):  # R2 through R7
    elements.append(junction(PIN1_X, r_ys[i]))
    print(f"Junction at ({PIN1_X}, {r_ys[i]}) -- {r_names[i]} pin1")

# =========================================================
# 3. ADC_CH2 label at top of bus (probe input net)
#    angle=0, text extends right
# =========================================================
elements.append(label_str("ADC_CH2", PIN1_X, r_ys[0], 0, "left", "bottom"))
print(f"Label: ADC_CH2 at ({PIN1_X}, {r_ys[0]})")

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
print(f"\nDone! Bus wire + 6 junctions + ADC_CH2 label. Saved.")
