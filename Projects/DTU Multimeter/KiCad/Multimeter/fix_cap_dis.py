"""Fix CAP_DIS dangling label by adding matching label near timing circuit.

CAP_DIS exists on A1 pin 32 at (487.68, 252.73).
Add a matching CAP_DIS label near the NE555 timing area with a stub wire
for future connection when capacitance measurement is implemented.

Place below R19 at the charge bus area: label at (298, 228.6) with a
short wire stub going up to (298, 226.06) to connect to the charge bus.
The charge bus ends at (295.91, 223.52) for R19 pin2, so we extend it
down slightly.
"""
import uuid, shutil
from pathlib import Path

SCH = Path(r"C:\Users\Mads2\Documents\Projects\Projects\DTU Multimeter\KiCad\Multimeter\Multimeter.kicad_sch")

def uid():
    return str(uuid.uuid4())

# ---------- Load ----------
shutil.copy2(SCH, SCH.with_suffix(".kicad_sch.bak"))
content = SCH.read_text(encoding="utf-8")

elements = []

# Wire: extend charge bus down from (295.91, 223.52) to (295.91, 228.6)
elements.append(f'''
	(wire
		(pts
			(xy 295.91 223.52) (xy 295.91 228.6)
		)
		(stroke
			(width 0)
			(type default)
		)
		(uuid "{uid()}")
	)''')

# CAP_DIS label at bottom of stub, angle=180 so text extends left
elements.append(f'''
	(label "CAP_DIS"
		(at 295.91 228.6 180)
		(effects
			(font
				(size 1.27 1.27)
			)
			(justify right bottom)
		)
		(uuid "{uid()}")
	)''')

# Inject before the final closing paren
last_paren = content.rfind(')')
inject = ''.join(elements)
content = content[:last_paren] + inject + '\n' + content[last_paren:]

SCH.write_text(content, encoding="utf-8")
print("Added wire: charge bus (295.91, 223.52) -> (295.91, 228.6)")
print("Added CAP_DIS label at (295.91, 228.6)")
print("Done! Saved. Backup at .kicad_sch.bak")
