"""Wire DS1 (OLED) + bypass capacitors C1-C6.

DS1 at (260, 320, 0):
  Pin 1 (VDD): (275.24, 312.38) -- right
  Pin 2 (GND): (275.24, 325.08) -- right
  Pin 3 (SCK): (244.76, 317.46) -- left
  Pin 4 (SDA): (244.76, 320)    -- left

Caps (Device:C pin offsets: pin1=top -3.81, pin2=bot +3.81):
  C1  (100n) at (95.25, 38.1):  VCC/GND -- decoupling near U1
  C2  (100n) at (193.93, 49.53): VCC/GND -- decoupling near U2
  C3  (100n) at (421.64, 52.07): VCC/GND -- decoupling near U4
  C4  (10u)  at (109.22, 38.1):  VCC/GND -- bulk near U1
  C5  (10u)  at (201.93, 49.53): VCC/GND -- bulk near U2
  C6  (10u)  at (425.45, 60.96): VCC/GND -- bulk near U4
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
# 1. Move DS1 I2C labels to exact pin positions
# =========================================================

# Move I2C_SDA from (245, 318, 180) to pin4 SDA (244.76, 320, 180)
pat = r'\(label\s+"I2C_SDA"\s*\(at\s+245\s+318\s+180\).*?\(uuid\s+"[^"]+"\)\s*\)'
m = re.search(pat, content, re.DOTALL)
if m:
    content = content[:m.start()] + content[m.end():]
    print("Removed old I2C_SDA at (245,318)")
else:
    print("WARN: I2C_SDA at (245,318) not found")

# Move I2C_SCL from (245, 322, 180) to pin3 SCK (244.76, 317.46, 180)
pat = r'\(label\s+"I2C_SCL"\s*\(at\s+245\s+322\s+180\).*?\(uuid\s+"[^"]+"\)\s*\)'
m = re.search(pat, content, re.DOTALL)
if m:
    content = content[:m.start()] + content[m.end():]
    print("Removed old I2C_SCL at (245,322)")
else:
    print("WARN: I2C_SCL at (245,322) not found")

content = re.sub(r'\n\t*\n\t*\n', '\n\n', content)

# =========================================================
# Build elements
# =========================================================
elements = []

def vcc_sym(x, y, ref_num):
    ref = f"#PWR0{ref_num:02d}"
    return f'''
	(symbol
		(lib_id "power:VCC")
		(at {x} {y} 0)
		(unit 1)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(fields_autoplaced yes)
		(uuid "{uid()}")
		(property "Reference" "{ref}"
			(at {x} {round(y - 2.54, 2)} 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Value" "VCC"
			(at {x} {round(y - 2.54, 2)} 0)
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
			(at {x} {round(y + 2.54, 2)} 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Value" "GND"
			(at {x} {round(y + 2.54, 2)} 0)
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

pwr_num = 35  # next available

# =========================================================
# DS1 OLED -- power + labels
# =========================================================
# VCC at pin 1 VDD (275.24, 312.38)
elements.append(vcc_sym(275.24, 312.38, pwr_num)); pwr_num += 1
print("Added VCC at DS1 pin1 VDD (275.24, 312.38)")

# GND at pin 2 (275.24, 325.08)
elements.append(gnd_sym(275.24, 325.08, pwr_num)); pwr_num += 1
print("Added GND at DS1 pin2 (275.24, 325.08)")

# I2C_SCL at pin 3 SCK (244.76, 317.46, angle=180)
elements.append(label_str("I2C_SCL", 244.76, 317.46, 180, "right", "bottom"))
print("Added I2C_SCL at DS1 pin3 (244.76, 317.46)")

# I2C_SDA at pin 4 SDA (244.76, 320, angle=180)
elements.append(label_str("I2C_SDA", 244.76, 320, 180, "right", "bottom"))
print("Added I2C_SDA at DS1 pin4 (244.76, 320)")

# =========================================================
# Bypass capacitors C1-C6 -- VCC top, GND bottom
# =========================================================
caps = [
    ("C1", 95.25,  38.1,  "100n decoupling near U1"),
    ("C2", 193.93, 49.53, "100n decoupling near U2"),
    ("C3", 421.64, 52.07, "100n decoupling near U4"),
    ("C4", 109.22, 38.1,  "10u bulk near U1"),
    ("C5", 201.93, 49.53, "10u bulk near U2"),
    ("C6", 425.45, 60.96, "10u bulk near U4"),
]

for ref, cx, cy, desc in caps:
    pin1_y = round(cy - 3.81, 2)  # top = VCC
    pin2_y = round(cy + 3.81, 2)  # bottom = GND

    elements.append(vcc_sym(cx, pin1_y, pwr_num)); pwr_num += 1
    elements.append(gnd_sym(cx, pin2_y, pwr_num)); pwr_num += 1
    print(f"Added VCC/GND to {ref} ({desc}): VCC@({cx},{pin1_y}) GND@({cx},{pin2_y})")

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
print(f"\nDone! {pwr_num - 35} power symbols added. Saved. Backup at .kicad_sch.bak")
