"""Wire U5 (LM311N Comparator) module -- string injection approach.

Uses raw string manipulation to preserve KiCad's formatting.
Injects new elements before the final closing paren.
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
# 1. Remove old FREQ_IN label at (118 208 0)
# =========================================================
# Find and remove the label block
pattern = r'\(label\s+"FREQ_IN"\s*\(at\s+118\s+208\s+0\).*?\(uuid\s+"[^"]+"\)\s*\)'
match = re.search(pattern, content, re.DOTALL)
if match:
    content = content[:match.start()] + content[match.end():]
    # Clean up any leftover blank lines
    content = re.sub(r'\n\t*\n\t*\n', '\n\n', content)
    print("Removed old FREQ_IN label at (118, 208)")
else:
    print("WARNING: Old FREQ_IN label not found")

# =========================================================
# Build new elements as KiCad S-expression strings
# =========================================================
elements = []

# --- Power: VCC at R22 pin1 (65, 191.19) ---
elements.append(f'''
	(symbol
		(lib_id "power:VCC")
		(at 65 191.19 0)
		(unit 1)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(fields_autoplaced yes)
		(uuid "{uid()}")
		(property "Reference" "#PWR030"
			(at 65 188.65 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Value" "VCC"
			(at 65 188.65 0)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Footprint" ""
			(at 65 191.19 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Datasheet" ""
			(at 65 191.19 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Description" ""
			(at 65 191.19 0)
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
					(reference "#PWR030")
					(unit 1)
				)
			)
		)
	)''')
print("Added #PWR030 VCC at (65, 191.19) -- R22 top")

# --- Power: GND at R23 pin2 (65, 215.81) ---
elements.append(f'''
	(symbol
		(lib_id "power:GND")
		(at 65 215.81 0)
		(unit 1)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(fields_autoplaced yes)
		(uuid "{uid()}")
		(property "Reference" "#PWR031"
			(at 65 218.35 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Value" "GND"
			(at 65 218.35 0)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Footprint" ""
			(at 65 215.81 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Datasheet" ""
			(at 65 215.81 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Description" ""
			(at 65 215.81 0)
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
					(reference "#PWR031")
					(unit 1)
				)
			)
		)
	)''')
print("Added #PWR031 GND at (65, 215.81) -- R23 bottom")

# --- Power: VCC at R24 pin1 (135, 191.19) ---
elements.append(f'''
	(symbol
		(lib_id "power:VCC")
		(at 135 191.19 0)
		(unit 1)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(fields_autoplaced yes)
		(uuid "{uid()}")
		(property "Reference" "#PWR032"
			(at 135 188.65 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Value" "VCC"
			(at 135 188.65 0)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Footprint" ""
			(at 135 191.19 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Datasheet" ""
			(at 135 191.19 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Description" ""
			(at 135 191.19 0)
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
					(reference "#PWR032")
					(unit 1)
				)
			)
		)
	)''')
print("Added #PWR032 VCC at (135, 191.19) -- R24 top")

# --- Wires ---
def wire_str(x1, y1, x2, y2):
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

# Threshold divider: R22 pin2 -> R23 pin1
elements.append(wire_str(65, 198.81, 65, 208.19))
print("Wire: R22 pin2 (65,198.81) -> R23 pin1 (65,208.19)")

# Divider midpoint -> U5 IN-
elements.append(wire_str(65, 204.47, 82.55, 204.47))
print("Wire: divider midpoint -> U5 pin3 IN- (82.55,204.47)")

# C7 pin1 right step
elements.append(wire_str(65, 226.19, 75, 226.19))
print("Wire: C7 pin1 (65,226.19) -> (75,226.19)")

# C7 route up
elements.append(wire_str(75, 226.19, 75, 207.01))
print("Wire: (75,226.19) -> (75,207.01)")

# C7 to U5 IN+
elements.append(wire_str(75, 207.01, 82.55, 207.01))
print("Wire: (75,207.01) -> U5 pin2 IN+ (82.55,207.01)")

# U5 pin7 OUT right to R24 junction
elements.append(wire_str(118.11, 204.47, 135, 204.47))
print("Wire: U5 pin7 (118.11,204.47) -> (135,204.47)")

# R24 pin2 down to junction
elements.append(wire_str(135, 198.81, 135, 204.47))
print("Wire: R24 pin2 (135,198.81) -> (135,204.47)")

# --- Junction at divider midpoint ---
elements.append(f'''
	(junction
		(at 65 204.47)
		(diameter 0)
		(color 0 0 0 0)
		(uuid "{uid()}")
	)''')
print("Junction at (65, 204.47)")

# --- FREQ_IN label ---
elements.append(f'''
	(label "FREQ_IN"
		(at 135 204.47 0)
		(effects
			(font
				(size 1.27 1.27)
			)
			(justify left bottom)
		)
		(uuid "{uid()}")
	)''')
print("Added FREQ_IN label at (135, 204.47)")

# --- No-connect flags ---
elements.append(f'''
	(no_connect
		(at 82.55 212.09)
		(uuid "{uid()}")
	)''')
print("No-connect pin 5 BAL")

elements.append(f'''
	(no_connect
		(at 82.55 217.17)
		(uuid "{uid()}")
	)''')
print("No-connect pin 6 STRB/OFS")

# =========================================================
# Inject before the final closing paren
# =========================================================
# Find the last ')' in the file
last_paren = content.rfind(')')
if last_paren < 0:
    raise ValueError("Could not find closing paren in schematic")

inject = ''.join(elements)
content = content[:last_paren] + inject + '\n' + content[last_paren:]

# =========================================================
# Save
# =========================================================
SCH.write_text(content, encoding="utf-8")
print(f"\nDone! Saved. Backup at .kicad_sch.bak")
