"""Fix R18 pin 1 connection to DIS bus.

R18 was moved to (292.1, 207.01). Pin 1 is at (292.1, 203.2).
DIS bus runs vertically at x=287.02, with a junction at (287.02, 203.2).
Missing: horizontal wire from bus junction to R18 pin 1.
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
# Add wire from DIS bus to R18 pin 1
# =========================================================
wire = f'''
	(wire
		(pts
			(xy 287.02 203.2) (xy 292.1 203.2)
		)
		(stroke
			(width 0)
			(type default)
		)
		(uuid "{uid()}")
	)'''

# Inject before the final closing paren
last_paren = content.rfind(')')
content = content[:last_paren] + wire + '\n' + content[last_paren:]

# =========================================================
# Save
# =========================================================
SCH.write_text(content, encoding="utf-8")
print("Added wire: DIS bus (287.02, 203.2) -> R18 pin1 (292.1, 203.2)")
print("Done! Saved. Backup at .kicad_sch.bak")
