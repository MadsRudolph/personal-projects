"""Fix C7 Pin 2 and U4 Unit B (last 3 ERC errors).

1. C7 Pin 2 at (65.00, 231.27) -- add ADC_CH2 label to connect to probe input
2. U4 Pin 5 (IN+_B) at (454.66, 106.68) -- add ADC_CH2 label for probe input
3. U4 Pin 6 (IN-_B) at (454.66, 111.76) -> Pin 7 (OUT_B) at (474.98, 109.22)
   Wire feedback loop for unity-gain buffer.
"""
import uuid, shutil
from pathlib import Path

SCH = Path(r"C:\Users\Mads2\Documents\Projects\Projects\DTU Multimeter\KiCad\Multimeter\Multimeter.kicad_sch")

def uid():
    return str(uuid.uuid4())

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

def label(name, x, y, angle, hjust="left", vjust="bottom"):
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

# ---------- Load ----------
shutil.copy2(SCH, SCH.with_suffix(".kicad_sch.bak"))
content = SCH.read_text(encoding="utf-8")

elements = []

# =========================================================
# Fix 1: C7 Pin 2 -- add ADC_CH2 label
# =========================================================
# C7 pin 2 at (65.00, 231.27). Add label pointing left (angle=180).
elements.append(label("ADC_CH2", 65, 231.27, 180, "right", "bottom"))
print("Added ADC_CH2 label at C7 pin 2 (65, 231.27)")

# =========================================================
# Fix 2: U4 Pin 5 (IN+_B) -- add ADC_CH2 label
# =========================================================
# Pin 5 at (454.66, 106.68). Add label pointing left (angle=180).
elements.append(label("ADC_CH2", 454.66, 106.68, 180, "right", "bottom"))
print("Added ADC_CH2 label at U4 pin 5 (454.66, 106.68)")

# =========================================================
# Fix 3: U4 Pin 6 -> Pin 7 feedback (unity-gain buffer)
# =========================================================
# Pin 6 (IN-_B) at (454.66, 111.76)
# Pin 7 (OUT_B) at (474.98, 109.22)
# Route: pin6 down -> right -> up -> pin7
#   (454.66, 111.76) -> (454.66, 114.30)  [down]
#   (454.66, 114.30) -> (477.52, 114.30)  [right]
#   (477.52, 114.30) -> (477.52, 109.22)  [up]
#   (477.52, 109.22) -> (474.98, 109.22)  [left to pin7]

elements.append(wire(454.66, 111.76, 454.66, 114.30))
print("Wire: pin6 (454.66, 111.76) -> (454.66, 114.30)")

elements.append(wire(454.66, 114.30, 477.52, 114.30))
print("Wire: (454.66, 114.30) -> (477.52, 114.30)")

elements.append(wire(477.52, 114.30, 477.52, 109.22))
print("Wire: (477.52, 114.30) -> (477.52, 109.22)")

elements.append(wire(477.52, 109.22, 474.98, 109.22))
print("Wire: (477.52, 109.22) -> pin7 (474.98, 109.22)")

# Junction at pin7 output where ADC_CH4 label already exists
elements.append(f'''
	(junction
		(at 474.98 109.22)
		(diameter 0)
		(color 0 0 0 0)
		(uuid "{uid()}")
	)''')
print("Junction at pin7 (474.98, 109.22)")

# =========================================================
# Inject before the final closing paren
# =========================================================
last_paren = content.rfind(')')
inject = ''.join(elements)
content = content[:last_paren] + inject + '\n' + content[last_paren:]

SCH.write_text(content, encoding="utf-8")
print("\nDone! Saved. Backup at .kicad_sch.bak")
