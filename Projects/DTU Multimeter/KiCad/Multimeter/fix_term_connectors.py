"""Add Conn_01x01_Pin connector symbols for input terminals.

TERM_10A label at (29.21, 36.83) -> needs connector above it
TERM_mA label at (29.21, 59.69) -> needs connector above it

Connector symbol: Connector:Conn_01x01_Pin
Pin 1 offset: (5.08, 0) at 180 degrees in symbol coords.
With symbol rotation 270 (pin pointing down): pin at (x, y+5.08)

Place connectors so their pin lands exactly on the TERM label coordinates.
Connector at (29.21, 31.75) rot=90 -> pin at (29.21, 36.83) = TERM_10A
Connector at (29.21, 54.61) rot=90 -> pin at (29.21, 59.69) = TERM_mA
"""
import uuid, shutil
from pathlib import Path

SCH = Path(r"C:\Users\Mads2\Documents\Projects\Projects\DTU Multimeter\KiCad\Multimeter\Multimeter.kicad_sch")
PROJ_UUID = "ac1a6b26-ab53-454a-b718-b2b6f7a3a514"

def uid():
    return str(uuid.uuid4())

# ---------- Load ----------
shutil.copy2(SCH, SCH.with_suffix(".kicad_sch.bak"))
content = SCH.read_text(encoding="utf-8")

# =========================================================
# Find next available PWR reference numbers (not needed for connectors)
# Find next available J reference numbers
# =========================================================
import re
j_refs = [int(m) for m in re.findall(r'"J(\d+)"', content)]
next_j = max(j_refs) + 1 if j_refs else 1

def connector_sym(x, y, rotation, ref_num, value_text):
    """Create a Conn_01x01_Pin symbol.

    rotation=90: pin points down (pin at x, y+5.08)
    """
    ref = f"J{ref_num}"
    # Property positions offset from symbol center
    return f'''
	(symbol
		(lib_id "Connector:Conn_01x01_Pin")
		(at {x} {y} {rotation})
		(unit 1)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(uuid "{uid()}")
		(property "Reference" "{ref}"
			(at {x + 2.54} {y} 0)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Value" "{value_text}"
			(at {x - 2.54} {y} 0)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Footprint" ""
			(at {x} {y} 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Datasheet" "~"
			(at {x} {y} 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Description" "Generic connector, single row, 01x01, script generated"
			(at {x} {y} 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(pin "1"
			(uuid "{uid()}")
		)
		(instances
			(project ""
				(path "/{PROJ_UUID}"
					(reference "{ref}")
					(unit 1)
				)
			)
		)
	)'''

elements = []

# J1: 10A terminal connector
# Place at (29.21, 31.75) rot=90 -> pin at (29.21, 36.83) = TERM_10A label
elements.append(connector_sym(29.21, 31.75, 90, next_j, "10A_Terminal"))
print(f"Added J{next_j} (10A Terminal) at (29.21, 31.75) rot=90, pin at (29.21, 36.83)")

# J2: mA terminal connector
# Place at (29.21, 54.61) rot=90 -> pin at (29.21, 59.69) = TERM_mA label
elements.append(connector_sym(29.21, 54.61, 90, next_j + 1, "mA_Terminal"))
print(f"Added J{next_j + 1} (mA Terminal) at (29.21, 54.61) rot=90, pin at (29.21, 59.69)")

# =========================================================
# Inject before the final closing paren
# =========================================================
last_paren = content.rfind(')')
inject = ''.join(elements)
content = content[:last_paren] + inject + '\n' + content[last_paren:]

# =========================================================
# Save
# =========================================================
SCH.write_text(content, encoding="utf-8")
print(f"\nDone! Saved. Backup at .kicad_sch.bak")
