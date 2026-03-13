"""Wire U6 (NE555P Timer) module -- string injection approach.

U6 at (248.92, 210.82, 0). Pin positions:
  Pin 1 (GND):   (266.7, 220.98) -- already has #PWR019 GND
  Pin 2 (TRIG):  (231.14, 213.36)
  Pin 3 (OUT):   (266.7, 208.28)
  Pin 4 (RESET): (231.14, 208.28)
  Pin 5 (CV):    (231.14, 205.74)
  Pin 6 (THR):   (231.14, 210.82)
  Pin 7 (DIS):   (266.7, 205.74)
  Pin 8 (VCC):   (266.7, 200.66) -- already has #PWR006 VCC

Components:
  R17 (1.003M) at (290, 198): pin1=(290,194.19) pin2=(290,201.81)
  R18 (10k)    at (290, 210): pin1=(290,206.19) pin2=(290,213.81)
  R19 (99.48)  at (290, 222): pin1=(290,218.19) pin2=(290,225.81)
  C8  (100n)   at (228, 230): pin1=(228,226.19) pin2=(228,233.81)

Adds:
  - 1 power symbol (GND at C8 bottom)
  - 12 wires (pin ties, C8 bypass, DIS bus, charge bus)
  - 3 junctions
  - 4 labels (ISRC_EN, CAP_CHG, TMR_CAP x2 to link pins 2&6 with charge node)
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

def junction(x, y):
    return f'''
	(junction
		(at {x} {y})
		(diameter 0)
		(color 0 0 0 0)
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
# 1. Power: GND below C8 pin2
# =========================================================
elements.append(gnd_sym(228, 233.81, 33))
print("Added #PWR033 GND at (228, 233.81) -- C8 bottom")

# =========================================================
# 2. Wires
# =========================================================

# Pin 2 (TRIG) tied to Pin 6 (THR) -- vertical on left side
elements.append(wire(231.14, 210.82, 231.14, 213.36))
print("Wire: pin6 THR (231.14,210.82) -> pin2 TRIG (231.14,213.36)")

# Pin 5 (CV) -> C8: horizontal left, then vertical down
elements.append(wire(231.14, 205.74, 228, 205.74))
print("Wire: pin5 CV (231.14,205.74) -> (228,205.74)")

elements.append(wire(228, 205.74, 228, 226.19))
print("Wire: (228,205.74) -> C8 pin1 (228,226.19)")

# Pin 7 (DIS) -> right to bus at x=285
elements.append(wire(266.7, 205.74, 285, 205.74))
print("Wire: pin7 DIS (266.7,205.74) -> (285,205.74)")

# DIS bus: vertical at x=285 from R17 pin1 y to R19 pin1 y
elements.append(wire(285, 194.19, 285, 218.19))
print("Wire: DIS bus (285,194.19) -> (285,218.19)")

# Horizontal branches from DIS bus to each R pin1
elements.append(wire(285, 194.19, 290, 194.19))
print("Wire: bus -> R17 pin1 (290,194.19)")

elements.append(wire(285, 206.19, 290, 206.19))
print("Wire: bus -> R18 pin1 (290,206.19)")

elements.append(wire(285, 218.19, 290, 218.19))
print("Wire: bus -> R19 pin1 (290,218.19)")

# R pin2 -> right to charge bus at x=295
elements.append(wire(290, 201.81, 295, 201.81))
print("Wire: R17 pin2 (290,201.81) -> (295,201.81)")

elements.append(wire(290, 213.81, 295, 213.81))
print("Wire: R18 pin2 (290,213.81) -> (295,213.81)")

elements.append(wire(290, 225.81, 295, 225.81))
print("Wire: R19 pin2 (290,225.81) -> (295,225.81)")

# Charge bus: vertical at x=295
elements.append(wire(295, 201.81, 295, 225.81))
print("Wire: charge bus (295,201.81) -> (295,225.81)")

# =========================================================
# 3. Junctions
# =========================================================
# Pin 7 horizontal meets DIS bus
elements.append(junction(285, 205.74))
print("Junction at (285, 205.74) -- pin7 meets DIS bus")

# R18 pin1 branch on DIS bus
elements.append(junction(285, 206.19))
print("Junction at (285, 206.19) -- R18 pin1 branch")

# R18 pin2 branch on charge bus
elements.append(junction(295, 213.81))
print("Junction at (295, 213.81) -- R18 pin2 branch")

# =========================================================
# 4. Labels
# =========================================================
# Pin 4 (RESET) -> ISRC_EN (angle=180, text extends left)
elements.append(label("ISRC_EN", 231.14, 208.28, 180, "right", "bottom"))
print("Label: ISRC_EN at pin4 (231.14, 208.28)")

# Pin 3 (OUT) -> CAP_CHG (angle=0, text extends right)
elements.append(label("CAP_CHG", 266.7, 208.28, 0, "left", "bottom"))
print("Label: CAP_CHG at pin3 (266.7, 208.28)")

# Pins 2&6 junction -> TMR_CAP (angle=180, text extends left)
elements.append(label("TMR_CAP", 231.14, 213.36, 180, "right", "bottom"))
print("Label: TMR_CAP at pins 2&6 (231.14, 213.36)")

# Charge bus -> TMR_CAP (angle=0, text extends right)
elements.append(label("TMR_CAP", 295, 213.81, 0, "left", "bottom"))
print("Label: TMR_CAP at charge bus (295, 213.81)")

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
