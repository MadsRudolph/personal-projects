"""Fix TERM label dangling errors by adding wire stubs at fuse pin 1 positions.

In KiCad, labels must sit on a wire to be "connected" -- placing them
directly at a pin position without a wire counts as dangling.

Adds a short wire stub at each fuse pin 1 so the TERM label is on a wire
endpoint that connects to the pin.

  F1 pin 1 at (29.21, 44.45): wire to (29.21, 41.91), label stays at pin
  F2 pin 1 at (29.21, 64.77): wire to (29.21, 62.23), label stays at pin
"""
import uuid, shutil
from pathlib import Path

SCH = Path(r"C:\Users\Mads2\Documents\Projects\Projects\DTU Multimeter\KiCad\Multimeter\Multimeter.kicad_sch")

def uid():
    return str(uuid.uuid4())

# ---------- Load ----------
shutil.copy2(SCH, SCH.with_suffix(".kicad_sch.bak"))
content = SCH.read_text(encoding="utf-8")

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

elements = []

# Wire stub for TERM_10A: from F1 pin 1 (29.21, 44.45) upward to (29.21, 41.91)
elements.append(wire(29.21, 44.45, 29.21, 41.91))
print("Wire: (29.21, 44.45) -> (29.21, 41.91) for TERM_10A")

# Wire stub for TERM_mA: from F2 pin 1 (29.21, 64.77) upward to (29.21, 62.23)
elements.append(wire(29.21, 64.77, 29.21, 62.23))
print("Wire: (29.21, 64.77) -> (29.21, 62.23) for TERM_mA")

# Inject before final closing paren
last_paren = content.rfind(')')
inject = ''.join(elements)
content = content[:last_paren] + inject + '\n' + content[last_paren:]

# Save
SCH.write_text(content, encoding="utf-8")
print(f"\nDone! 2 wire stubs added for TERM labels. Saved.")
