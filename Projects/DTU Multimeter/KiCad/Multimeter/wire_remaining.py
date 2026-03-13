"""Wire all remaining modules:
1. R28/R29 I2C pull-ups
2. R15/R16 voltage divider
3. LEDs D1-D3 + R25-R27
4. Switches SW1-SW4
5. Buzzer BZ1
6. Fuses F1/F2
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

pwr_counter = [49]  # mutable counter starting after #PWR048

def vcc_sym(x, y):
    n = pwr_counter[0]; pwr_counter[0] += 1
    ref = f"#PWR0{n:02d}"
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
			(effects (font (size 1.27 1.27)) (hide yes))
		)
		(property "Value" "VCC"
			(at {x} {round(y - 2.54, 2)} 0)
			(effects (font (size 1.27 1.27)))
		)
		(property "Footprint" ""
			(at {x} {y} 0)
			(effects (font (size 1.27 1.27)) (hide yes))
		)
		(property "Datasheet" ""
			(at {x} {y} 0)
			(effects (font (size 1.27 1.27)) (hide yes))
		)
		(property "Description" ""
			(at {x} {y} 0)
			(effects (font (size 1.27 1.27)) (hide yes))
		)
		(pin "1" (uuid "{uid()}"))
		(instances (project "" (path "/{PROJ_UUID}" (reference "{ref}") (unit 1))))
	)'''

def gnd_sym(x, y):
    n = pwr_counter[0]; pwr_counter[0] += 1
    ref = f"#PWR0{n:02d}"
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
			(effects (font (size 1.27 1.27)) (hide yes))
		)
		(property "Value" "GND"
			(at {x} {round(y + 2.54, 2)} 0)
			(effects (font (size 1.27 1.27)))
		)
		(property "Footprint" ""
			(at {x} {y} 0)
			(effects (font (size 1.27 1.27)) (hide yes))
		)
		(property "Datasheet" ""
			(at {x} {y} 0)
			(effects (font (size 1.27 1.27)) (hide yes))
		)
		(property "Description" ""
			(at {x} {y} 0)
			(effects (font (size 1.27 1.27)) (hide yes))
		)
		(pin "1" (uuid "{uid()}"))
		(instances (project "" (path "/{PROJ_UUID}" (reference "{ref}") (unit 1))))
	)'''

def remove_label(content, name, x, y, angle):
    """Remove a label matching name and approximate position."""
    # Escape dots in coordinates for regex
    xs = str(x).replace('.', r'\.')
    ys = str(y).replace('.', r'\.')
    pat = rf'\(label\s+"{re.escape(name)}"\s*\(at\s+{xs}\s+{ys}\s+{angle}\).*?\(uuid\s+"[^"]+"\)\s*\)'
    m = re.search(pat, content, re.DOTALL)
    if m:
        content = content[:m.start()] + content[m.end():]
        print(f"  Removed {name} at ({x},{y},{angle})")
    else:
        print(f"  WARN: {name} at ({x},{y},{angle}) not found")
    return content

elements = []

# =========================================================
# 1. R28/R29 I2C Pull-Ups
# =========================================================
print("--- R28/R29 I2C Pull-Ups ---")
# VCC at R28 pin1 (180, 301.19)
elements.append(vcc_sym(180, 301.19))
# VCC at R29 pin1 (195, 301.19)
elements.append(vcc_sym(195, 301.19))
# Wire R28 pin2 (180, 308.81) -> I2C_SDA label (180, 312)
elements.append(wire(180, 308.81, 180, 312))
# Wire R29 pin2 (195, 308.81) -> I2C_SCL label (195, 312)
elements.append(wire(195, 308.81, 195, 312))
print("  VCC at R28/R29 pin1, wires to I2C labels")

# =========================================================
# 2. R15/R16 Voltage Divider
# =========================================================
print("--- R15/R16 Voltage Divider ---")
# ADC_CH2 label at R15 pin1 (60, 56.19) -- probe input
elements.append(label_str("ADC_CH2", 60, 56.19, 180, "right", "bottom"))
# Wire R15 pin2 (60, 63.81) -> R16 pin1 (60, 74.19) -- passes through ADC_CH1 at (60,68)
elements.append(wire(60, 63.81, 60, 74.19))
# GND at R16 pin2 (60, 81.81)
elements.append(gnd_sym(60, 81.81))
print("  ADC_CH2 at R15 top, wire R15-R16, GND at R16 bottom")

# =========================================================
# 3. LEDs D1-D3 + R25-R27
# =========================================================
print("--- LEDs D1-D3 + R25-R27 ---")

# Move LED labels from (521.72, y, 180) to R pin1 positions
led_labels = [
    ("LED_RED", 521.72, 189.14, 180, 531.72, 185.33),
    ("LED_GRN", 521.72, 204.14, 180, 531.72, 200.33),
    ("LED_YEL", 521.72, 219.14, 180, 531.72, 215.33),
]
for name, old_x, old_y, angle, new_x, new_y in led_labels:
    content = remove_label(content, name, old_x, old_y, angle)
    elements.append(label_str(name, new_x, new_y, 180, "right", "bottom"))

# Wire R pin2 -> D anode (route under LED: down, right, up)
# R25 pin2 (531.72,192.95) -> D1 anode (557.53,189.14)
elements.append(wire(531.72, 192.95, 531.72, 195))
elements.append(wire(531.72, 195, 557.53, 195))
elements.append(wire(557.53, 195, 557.53, 189.14))

# R26 pin2 (531.72,207.95) -> D2 anode (557.53,204.14)
elements.append(wire(531.72, 207.95, 531.72, 210))
elements.append(wire(531.72, 210, 557.53, 210))
elements.append(wire(557.53, 210, 557.53, 204.14))

# R27 pin2 (531.72,222.95) -> D3 anode (557.53,219.14)
elements.append(wire(531.72, 222.95, 531.72, 225))
elements.append(wire(531.72, 225, 557.53, 225))
elements.append(wire(557.53, 225, 557.53, 219.14))

# GND at LED cathodes via short stub wires (2.54mm down)
for cathode_y in [189.14, 204.14, 219.14]:
    stub_y = round(cathode_y + 2.54, 2)
    elements.append(wire(549.91, cathode_y, 549.91, stub_y))
    elements.append(gnd_sym(549.91, stub_y))

print("  Labels moved, wires routed, GND at cathodes")

# =========================================================
# 4. SW1-SW4 Switches
# =========================================================
print("--- SW1-SW4 Switches ---")

# Move BTN labels from (521.72, y, 180) to SW pin1 positions (531.64, y, 180)
sw_labels = [
    ("BTN_MODE",  521.72, 309.14, 180, 531.64, 309.14),
    ("BTN_FUNC",  521.72, 324.14, 180, 531.64, 324.14),
    ("BTN_RANGE", 521.72, 339.14, 180, 531.64, 339.14),
    ("BTN_SEL",   521.72, 354.14, 180, 531.64, 354.14),
]
for name, old_x, old_y, angle, new_x, new_y in sw_labels:
    content = remove_label(content, name, old_x, old_y, angle)
    elements.append(label_str(name, new_x, new_y, 180, "right", "bottom"))

# GND at SW pin2 via short stub wires (2.54mm down from pin2)
for sw_y in [309.14, 324.14, 339.14, 354.14]:
    pin2_x = 541.8
    stub_y = round(sw_y + 2.54, 2)
    elements.append(wire(pin2_x, sw_y, pin2_x, stub_y))
    elements.append(gnd_sym(pin2_x, stub_y))

print("  Labels moved, GND at pin2")

# =========================================================
# 5. BZ1 Buzzer
# =========================================================
print("--- BZ1 Buzzer ---")
# BUZZER label at pin1(+) (534.18, 281.6, angle=180)
elements.append(label_str("BUZZER", 534.18, 281.6, 180, "right", "bottom"))
# GND at pin2(-) (534.18, 286.68)
elements.append(gnd_sym(534.18, 286.68))
print("  BUZZER label at (+), GND at (-)")

# =========================================================
# 6. F1/F2 Fuses
# =========================================================
print("--- F1/F2 Fuses ---")
# F1 pin1 (30, 44.19): 10A terminal input
elements.append(label_str("TERM_10A", 30, 44.19, 180, "right", "bottom"))
# F1 pin2 (30, 51.81): connects to R14 shunt
elements.append(label_str("FUSE_10A", 30, 51.81, 0, "left", "bottom"))
# F2 pin1 (30, 64.19): mA terminal input
elements.append(label_str("TERM_mA", 30, 64.19, 180, "right", "bottom"))
# F2 pin2 (30, 71.81): connects to R9-R13 shunts
elements.append(label_str("FUSE_mA", 30, 71.81, 0, "left", "bottom"))
print("  Terminal + shunt labels on F1/F2")

# =========================================================
# Clean up blank lines and inject
# =========================================================
content = re.sub(r'\n\t*\n\t*\n', '\n\n', content)
last_paren = content.rfind(')')
inject = ''.join(elements)
content = content[:last_paren] + inject + '\n' + content[last_paren:]

# =========================================================
# Save
# =========================================================
SCH.write_text(content, encoding="utf-8")
total_pwr = pwr_counter[0] - 49
print(f"\nDone! {total_pwr} power symbols, labels moved/added. Saved.")
