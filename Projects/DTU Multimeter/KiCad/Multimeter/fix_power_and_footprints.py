"""
Fix script: Add global power input block + assign footprints to J1/J2

Changes:
1. Assigns 'Connector:Banana_Jack_1Pin' footprint to J1 and J2
2. Adds a Conn_01x02_Pin lib_symbol for the power connector
3. Adds J3 (2-pin screw terminal) as the power input block at (25.4, 83.82)
4. Adds VCC power symbol connected to J3 pin 1
5. Adds GND power symbol connected to J3 pin 2
6. Adds wires connecting J3 to power symbols
7. Adds "POWER INPUT" text annotation
"""

import re
import uuid
import shutil
from pathlib import Path

sch_path = Path(r"C:\Users\Mads2\Documents\Projects\Projects\DTU Multimeter\KiCad\Multimeter\Multimeter.kicad_sch")

# Backup
shutil.copy2(sch_path, sch_path.with_suffix('.kicad_sch.bak_power'))

content = sch_path.read_text(encoding='utf-8')

def new_uuid():
    return str(uuid.uuid4())

# ============================================================
# 1. Assign footprints to J1 and J2: Banana_Jack_1Pin
# ============================================================
# J1 footprint is empty: (property "Footprint" "" at (25.4 38.1 ...
# J2 footprint is empty: (property "Footprint" "" at (25.4 60.96 ...

# Fix J1 footprint - find the Footprint property in J1's symbol block
# J1 uuid: 150b5f9e-bd77-4338-bdfb-d3945eaf998c
j1_fp_old = '''		(property "Footprint" ""
			(at 25.4 38.1 0)'''
j1_fp_new = '''		(property "Footprint" "Connector:Banana_Jack_1Pin"
			(at 25.4 38.1 0)'''

if j1_fp_old in content:
    content = content.replace(j1_fp_old, j1_fp_new, 1)
    print("OK: J1 footprint set to Connector:Banana_Jack_1Pin")
else:
    print("WARN: Could not find J1 footprint to replace")

# Fix J2 footprint
j2_fp_old = '''		(property "Footprint" ""
			(at 25.4 60.96 0)'''
j2_fp_new = '''		(property "Footprint" "Connector:Banana_Jack_1Pin"
			(at 25.4 60.96 0)'''

if j2_fp_old in content:
    content = content.replace(j2_fp_old, j2_fp_new, 1)
    print("OK: J2 footprint set to Connector:Banana_Jack_1Pin")
else:
    print("WARN: Could not find J2 footprint to replace")

# ============================================================
# 2. Add Conn_01x02_Pin lib_symbol (before closing of lib_symbols)
# ============================================================
conn_02_lib = '''		(symbol "Connector:Conn_01x02_Pin"
			(pin_names
				(offset 1.016)
				(hide yes)
			)
			(exclude_from_sim no)
			(in_bom yes)
			(on_board yes)
			(property "Reference" "J"
				(at 0 2.54 0)
				(effects
					(font
						(size 1.27 1.27)
					)
				)
			)
			(property "Value" "Conn_01x02_Pin"
				(at 0 -5.08 0)
				(effects
					(font
						(size 1.27 1.27)
					)
				)
			)
			(property "Footprint" ""
				(at 0 0 0)
				(effects
					(font
						(size 1.27 1.27)
					)
					(hide yes)
				)
			)
			(property "Datasheet" "~"
				(at 0 0 0)
				(effects
					(font
						(size 1.27 1.27)
					)
					(hide yes)
				)
			)
			(property "Description" "Generic connector, single row, 01x02, script generated"
				(at 0 0 0)
				(effects
					(font
						(size 1.27 1.27)
					)
					(hide yes)
				)
			)
			(property "ki_locked" ""
				(at 0 0 0)
				(effects
					(font
						(size 1.27 1.27)
					)
				)
			)
			(property "ki_keywords" "connector"
				(at 0 0 0)
				(effects
					(font
						(size 1.27 1.27)
					)
					(hide yes)
				)
			)
			(property "ki_fp_filters" "Connector*:*_1x??_*"
				(at 0 0 0)
				(effects
					(font
						(size 1.27 1.27)
					)
					(hide yes)
				)
			)
			(symbol "Conn_01x02_Pin_1_1"
				(rectangle
					(start 0.8636 0.127)
					(end 0 -0.127)
					(stroke
						(width 0.1524)
						(type default)
					)
					(fill
						(type outline)
					)
				)
				(rectangle
					(start 0.8636 -2.413)
					(end 0 -2.667)
					(stroke
						(width 0.1524)
						(type default)
					)
					(fill
						(type outline)
					)
				)
				(polyline
					(pts
						(xy 1.27 0) (xy 0.8636 0)
					)
					(stroke
						(width 0.1524)
						(type default)
					)
					(fill
						(type none)
					)
				)
				(polyline
					(pts
						(xy 1.27 -2.54) (xy 0.8636 -2.54)
					)
					(stroke
						(width 0.1524)
						(type default)
					)
					(fill
						(type none)
					)
				)
				(pin passive line
					(at 5.08 0 180)
					(length 3.81)
					(name "Pin_1"
						(effects
							(font
								(size 1.27 1.27)
							)
						)
					)
					(number "1"
						(effects
							(font
								(size 1.27 1.27)
							)
						)
					)
				)
				(pin passive line
					(at 5.08 -2.54 180)
					(length 3.81)
					(name "Pin_2"
						(effects
							(font
								(size 1.27 1.27)
							)
						)
					)
					(number "2"
						(effects
							(font
								(size 1.27 1.27)
							)
						)
					)
				)
			)
			(embedded_fonts no)
		)'''

# Insert before the closing of lib_symbols section
# The lib_symbols section ends with a line containing just "	)"
# Find the end of the last lib_symbol and insert before closing
# Looking for the pattern: end of lib_symbols is marked by a standalone "\t)"
# that comes after all symbol definitions

# Find the closing of lib_symbols - it's the first standalone "\t)" after all symbols
lib_sym_end = content.find('\t)\n\t(rectangle')
if lib_sym_end == -1:
    # Try alternative: find the line "\t)" that ends lib_symbols
    # The lib_symbols section starts with "(lib_symbols" and ends with a matching ")"
    lib_sym_end = content.find('\t)\n\t(text ')
    if lib_sym_end == -1:
        lib_sym_end = content.find('\t)\n\t(label ')

if lib_sym_end != -1:
    content = content[:lib_sym_end] + conn_02_lib + '\n' + content[lib_sym_end:]
    print("OK: Added Conn_01x02_Pin lib_symbol")
else:
    print("ERROR: Could not find lib_symbols closing bracket")

# ============================================================
# 3. Add J3 power connector + VCC + GND + wires + text
# ============================================================
# J3 placed at (25.4, 83.82)
# Pin 1 (VCC) connects at absolute (30.48, 83.82)
# Pin 2 (GND) connects at absolute (30.48, 86.36)
# VCC symbol at (30.48, 81.28) - wire from 81.28 to 83.82
# GND symbol at (30.48, 88.9) - wire from 86.36 to 88.9

j3_uuid = new_uuid()
vcc_uuid = new_uuid()
gnd_uuid = new_uuid()
wire1_uuid = new_uuid()
wire2_uuid = new_uuid()
text_uuid = new_uuid()
j3_pin1_uuid = new_uuid()
j3_pin2_uuid = new_uuid()
vcc_pin_uuid = new_uuid()
gnd_pin_uuid = new_uuid()

new_elements = f'''
	(symbol
		(lib_id "Connector:Conn_01x02_Pin")
		(at 25.4 83.82 0)
		(unit 1)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(uuid "{j3_uuid}")
		(property "Reference" "J3"
			(at 26.035 78.74 0)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Value" "PWR_IN"
			(at 26.035 88.9 0)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Footprint" "TerminalBlock:TerminalBlock_bornier-2_P5.08mm"
			(at 25.4 83.82 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Datasheet" "~"
			(at 25.4 83.82 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Description" "Power input connector, 5V + GND"
			(at 25.4 83.82 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(pin "1"
			(uuid "{j3_pin1_uuid}")
		)
		(pin "2"
			(uuid "{j3_pin2_uuid}")
		)
		(instances
			(project ""
				(path "/ac1a6b26-ab53-454a-b718-b2b6f7a3a514"
					(reference "J3")
					(unit 1)
				)
			)
		)
	)
	(symbol
		(lib_id "power:VCC")
		(at 30.48 81.28 0)
		(unit 1)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(uuid "{vcc_uuid}")
		(property "Reference" "#PWR040"
			(at 30.48 77.47 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Value" "VCC"
			(at 30.48 77.724 0)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Footprint" ""
			(at 30.48 81.28 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Datasheet" ""
			(at 30.48 81.28 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Description" ""
			(at 30.48 81.28 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(pin "1"
			(uuid "{vcc_pin_uuid}")
		)
		(instances
			(project ""
				(path "/ac1a6b26-ab53-454a-b718-b2b6f7a3a514"
					(reference "#PWR040")
					(unit 1)
				)
			)
		)
	)
	(symbol
		(lib_id "power:GND")
		(at 30.48 88.9 0)
		(unit 1)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(uuid "{gnd_uuid}")
		(property "Reference" "#PWR041"
			(at 30.48 95.25 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Value" "GND"
			(at 30.48 92.71 0)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Footprint" ""
			(at 30.48 88.9 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Datasheet" ""
			(at 30.48 88.9 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Description" ""
			(at 30.48 88.9 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(pin "1"
			(uuid "{gnd_pin_uuid}")
		)
		(instances
			(project ""
				(path "/ac1a6b26-ab53-454a-b718-b2b6f7a3a514"
					(reference "#PWR041")
					(unit 1)
				)
			)
		)
	)
	(wire
		(pts
			(xy 30.48 81.28) (xy 30.48 83.82)
		)
		(stroke
			(width 0)
			(type default)
		)
		(uuid "{wire1_uuid}")
	)
	(wire
		(pts
			(xy 30.48 86.36) (xy 30.48 88.9)
		)
		(stroke
			(width 0)
			(type default)
		)
		(uuid "{wire2_uuid}")
	)
	(text "POWER INPUT\\n(J3 Screw Terminal, 5V + GND)"
		(exclude_from_sim no)
		(at 15.24 73.66 0)
		(effects
			(font
				(size 1.27 1.27)
			)
			(justify left)
		)
		(uuid "{text_uuid}")
	)'''

# Insert before (sheet_instances
sheet_inst_marker = '\t(sheet_instances'
idx = content.find(sheet_inst_marker)
if idx != -1:
    content = content[:idx] + new_elements + '\n' + content[idx:]
    print("OK: Added J3 power connector with VCC, GND, wires, and text")
else:
    print("ERROR: Could not find sheet_instances marker")

# ============================================================
# Write output
# ============================================================
sch_path.write_text(content, encoding='utf-8')
print("\nDone! Changes written to schematic.")
print("Open in KiCad and run ERC to verify.")
