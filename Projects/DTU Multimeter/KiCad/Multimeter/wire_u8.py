"""Wire U8 (DS1307+ RTC) module with Y1 crystal and BT1 battery.

U8 at (100.33, 318.77, 0). Pin positions:
  Pin 1 (X1):   (87.63, 321.31)  -- left side
  Pin 2 (X2):   (87.63, 323.85)  -- left side
  Pin 3 (VBAT): (100.33, 308.61) -- top
  Pin 4 (GND):  (100.33, 328.93) -- bottom, has #PWR021 GND
  Pin 5 (SDA):  (87.63, 316.23)  -- left side
  Pin 6 (SCL):  (87.63, 313.69)  -- left side
  Pin 7 (SQW):  (113.03, 318.77) -- right side
  Pin 8 (VCC):  (97.79, 308.61)  -- top, has #PWR008 VCC

Y1 (Crystal) at (68, 328, 0):
  Pin 1: (64.19, 328)  Pin 2: (71.81, 328)

BT1 (CR2032) at (72, 348, 0):
  Pin 1 (+): (72, 342.92)  Pin 2 (-): (72, 350.54)

Adds:
  - 1 power symbol (GND at BT1-)
  - 7 wires (Y1->X1/X2, BT1->VBAT)
  - 1 no-connect (pin 7 SQW)
  - Moves I2C_SDA/SCL labels to pin positions
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
# 1. Move I2C_SDA label from (115, 318, 0) to (87.63, 316.23, 180)
# =========================================================
pattern_sda = r'\(label\s+"I2C_SDA"\s*\(at\s+115\s+318\s+0\).*?\(uuid\s+"[^"]+"\)\s*\)'
match = re.search(pattern_sda, content, re.DOTALL)
if match:
    content = content[:match.start()] + content[match.end():]
    print("Removed old I2C_SDA label at (115, 318)")
else:
    print("WARNING: I2C_SDA label at (115,318) not found")

# =========================================================
# 2. Move I2C_SCL label from (115, 322, 0) to (87.63, 313.69, 180)
# =========================================================
pattern_scl = r'\(label\s+"I2C_SCL"\s*\(at\s+115\s+322\s+0\).*?\(uuid\s+"[^"]+"\)\s*\)'
match = re.search(pattern_scl, content, re.DOTALL)
if match:
    content = content[:match.start()] + content[match.end():]
    print("Removed old I2C_SCL label at (115, 322)")
else:
    print("WARNING: I2C_SCL label at (115,322) not found")

# Clean up any extra blank lines
content = re.sub(r'\n\t*\n\t*\n', '\n\n', content)

# =========================================================
# Build new elements
# =========================================================
elements = []

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

def gnd_sym(x, y, ref_num):
    ref = f"#PWR0{ref_num:02d}"
    return f'''
	(symbol
		(lib_id "power:GND")
		(at {x} {y} 0)
		(unit 1)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(fields_autoplaced yes)
		(uuid "{uid()}")
		(property "Reference" "{ref}"
			(at {x} {y + 2.54} 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Value" "GND"
			(at {x} {y + 2.54} 0)
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
		(property "Datasheet" ""
			(at {x} {y} 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Description" ""
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

# =========================================================
# 3. New I2C labels at pin positions (left side, angle=180)
# =========================================================
elements.append(label("I2C_SDA", 87.63, 316.23, 180, "right", "bottom"))
print("Added I2C_SDA label at pin5 (87.63, 316.23, angle=180)")

elements.append(label("I2C_SCL", 87.63, 313.69, 180, "right", "bottom"))
print("Added I2C_SCL label at pin6 (87.63, 313.69, angle=180)")

# =========================================================
# 4. GND at BT1 pin2 (-)
# =========================================================
elements.append(gnd_sym(72, 350.54, 34))
print("Added #PWR034 GND at (72, 350.54) -- BT1 negative")

# =========================================================
# 5. Y1 crystal -> U8 X1/X2 wires
# =========================================================
# Y1 pin1 (64.19, 328) -> up to (64.19, 321.31) -> right to U8 pin1 X1 (87.63, 321.31)
elements.append(wire(64.19, 328, 64.19, 321.31))
print("Wire: Y1 pin1 (64.19,328) -> (64.19,321.31)")
elements.append(wire(64.19, 321.31, 87.63, 321.31))
print("Wire: (64.19,321.31) -> U8 X1 (87.63,321.31)")

# Y1 pin2 (71.81, 328) -> up to (71.81, 323.85) -> right to U8 pin2 X2 (87.63, 323.85)
elements.append(wire(71.81, 328, 71.81, 323.85))
print("Wire: Y1 pin2 (71.81,328) -> (71.81,323.85)")
elements.append(wire(71.81, 323.85, 87.63, 323.85))
print("Wire: (71.81,323.85) -> U8 X2 (87.63,323.85)")

# =========================================================
# 6. BT1+ -> U8 VBAT
# Route: up from BT1, left to avoid VCC at pin 8, then to VBAT
# BT1+ (72, 342.92) -> (72, 306) -> (100.33, 306) -> (100.33, 308.61)
# =========================================================
elements.append(wire(72, 342.92, 72, 306))
print("Wire: BT1+ (72,342.92) -> (72,306)")
elements.append(wire(72, 306, 100.33, 306))
print("Wire: (72,306) -> (100.33,306)")
elements.append(wire(100.33, 306, 100.33, 308.61))
print("Wire: (100.33,306) -> U8 VBAT (100.33,308.61)")

# =========================================================
# 7. No-connect on pin 7 (SQW)
# =========================================================
elements.append(f'''
	(no_connect
		(at 113.03 318.77)
		(uuid "{uid()}")
	)''')
print("No-connect at (113.03, 318.77) -- pin 7 SQW")

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
print(f"\nDone! Saved. Backup at .kicad_sch.bak")
