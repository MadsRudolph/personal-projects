"""Fix ERC errors in the DTU Multimeter schematic.

Fixes:
1. Relocate dangling TERM_10A / TERM_mA labels to exact fuse pin positions
2. Remove orphaned #PWR026 GND symbol (not connected to anything)
3. Add no-connect flags on ~57 unused Arduino A1 pins
4. Add PWR_FLAG symbols on VCC, GND, and VBAT nets
5. Add PWR_FLAG lib symbol definition to lib_symbols section
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

def remove_by_regex(content, pattern, description):
    """Remove first match of pattern from content."""
    m = re.search(pattern, content, re.DOTALL)
    if m:
        content = content[:m.start()] + content[m.end():]
        print(f"  Removed: {description}")
    else:
        print(f"  WARN: Not found: {description}")
    return content

def remove_balanced_block(content, search_str, description):
    """Remove a balanced S-expression block containing search_str.

    Finds search_str in content, walks backwards to find the opening '('
    of the enclosing top-level element, then counts balanced parens forward
    to find the matching closing ')'. Removes the entire block.
    """
    idx = content.find(search_str)
    if idx == -1:
        print(f"  WARN: Not found: {description}")
        return content

    # Walk backwards from search_str to find the '(symbol' that contains it
    # We look for a '(symbol' preceded by a newline+tab (top-level schematic element)
    search_back = content.rfind('\n\t(symbol', 0, idx)
    if search_back == -1:
        print(f"  WARN: Could not find enclosing (symbol for: {description}")
        return content
    start = search_back + 1  # skip the \n, point to \t(symbol

    # Count balanced parens from start to find matching close
    depth = 0
    i = start
    while i < len(content):
        if content[i] == '(':
            depth += 1
        elif content[i] == ')':
            depth -= 1
            if depth == 0:
                end = i + 1  # include the closing paren
                break
        i += 1
    else:
        print(f"  WARN: Unbalanced parens for: {description}")
        return content

    # Also consume trailing whitespace/newline
    while end < len(content) and content[end] in (' ', '\t', '\n', '\r'):
        end += 1

    removed = content[start:end]
    # Sanity check: count parens in removed block
    opens = removed.count('(')
    closes = removed.count(')')
    if opens != closes:
        print(f"  WARN: Removed block has unbalanced parens ({opens} opens, {closes} closes)")
    else:
        print(f"  Removed: {description} ({opens} balanced parens)")

    content = content[:start] + content[end:]
    return content

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

def no_connect(x, y):
    return f'''
	(no_connect
		(at {x} {y})
		(uuid "{uid()}")
	)'''

elements = []

# =========================================================
# Fix 1: Relocate TERM_10A and TERM_mA labels
# =========================================================
print("--- Fix 1: Relocate TERM labels ---")

# Remove old TERM_10A label at (29.21, 41.91, 180)
content = remove_by_regex(
    content,
    r'\(label\s+"TERM_10A"\s*\(at\s+29\.21\s+41\.91\s+180\).*?\(uuid\s+"[^"]+"\)\s*\)',
    "TERM_10A label at (29.21, 41.91)"
)

# Remove bridge wire from (29.21, 41.91) to (29.21, 44.45)
content = remove_by_regex(
    content,
    r'\(wire\s*\(pts\s*\(xy\s+29\.21\s+41\.91\)\s*\(xy\s+29\.21\s+44\.45\)\s*\).*?\(uuid\s+"[^"]+"\)\s*\)',
    "Bridge wire (29.21, 41.91)->(29.21, 44.45)"
)

# Add TERM_10A at F1 pin 1: (29.21, 44.45)
elements.append(label_str("TERM_10A", 29.21, 44.45, 180, "right", "bottom"))
print("  Added TERM_10A at (29.21, 44.45) = F1 pin 1")

# Remove old TERM_mA label at (30, 63.5, 180)
content = remove_by_regex(
    content,
    r'\(label\s+"TERM_mA"\s*\(at\s+30\s+63\.5\s+180\).*?\(uuid\s+"[^"]+"\)\s*\)',
    "TERM_mA label at (30, 63.5)"
)

# Remove horizontal bridge wire (29.21, 63.5) -> (30, 63.5)
content = remove_by_regex(
    content,
    r'\(wire\s*\(pts\s*\(xy\s+29\.21\s+63\.5\)\s*\(xy\s+30\s+63\.5\)\s*\).*?\(uuid\s+"[^"]+"\)\s*\)',
    "Bridge wire (29.21, 63.5)->(30, 63.5)"
)

# Remove vertical bridge wire (29.21, 63.5) -> (29.21, 64.77)
content = remove_by_regex(
    content,
    r'\(wire\s*\(pts\s*\(xy\s+29\.21\s+63\.5\)\s*\(xy\s+29\.21\s+64\.77\)\s*\).*?\(uuid\s+"[^"]+"\)\s*\)',
    "Bridge wire (29.21, 63.5)->(29.21, 64.77)"
)

# Add TERM_mA at F2 pin 1: (29.21, 64.77)
elements.append(label_str("TERM_mA", 29.21, 64.77, 180, "right", "bottom"))
print("  Added TERM_mA at (29.21, 64.77) = F2 pin 1")

# =========================================================
# Fix 2: Remove orphaned #PWR026 GND symbol
# =========================================================
print("\n--- Fix 2: Remove orphaned #PWR026 ---")

# Remove entire symbol block by UUID (balanced-paren approach)
content = remove_balanced_block(
    content,
    '(uuid "4233529d-95e4-4805-a08b-ce41303f385c")',
    "#PWR026 GND at (553.72, 231.14)"
)

# =========================================================
# Fix 3: Add no-connect flags on unused A1 pins
# =========================================================
print("\n--- Fix 3: Add A1 no-connect flags ---")

# Left side pins (x=443.23)
left_pins = [
    (443.23, 171.45, "NC"),
    (443.23, 173.99, "IOREF"),
    (443.23, 176.53, "RESET"),
    (443.23, 179.07, "3V3"),
    (443.23, 184.15, "GND1"),
    (443.23, 189.23, "VIN"),
    (443.23, 194.31, "AD0"),
    (443.23, 196.85, "AD1"),
    (443.23, 224.79, "AD11"),
    (443.23, 227.33, "AD12"),
    (443.23, 229.87, "AD13"),
    (443.23, 232.41, "AD14"),
    (443.23, 234.95, "AD15"),
    (443.23, 240.03, "5V_3"),
    (443.23, 257.81, "35"),
    (443.23, 260.35, "37"),
    (443.23, 262.89, "39"),
    (443.23, 265.43, "41"),
    (443.23, 267.97, "43"),
    (443.23, 270.51, "45"),
    (443.23, 273.05, "47"),
    (443.23, 275.59, "49"),
    (443.23, 283.21, "GND5"),
]

# Right side pins (x=483.87)
right_pins = [
    (483.87, 171.45, "AREF"),
    (483.87, 173.99, "GND3"),
    (483.87, 176.53, "13"),
    (483.87, 179.07, "12"),
    (483.87, 181.61, "11"),
    (483.87, 184.15, "10"),
    (483.87, 186.69, "9"),
    (483.87, 189.23, "8"),
    (483.87, 194.31, "7"),
    (483.87, 196.85, "6"),
    (483.87, 199.39, "5"),
    (483.87, 201.93, "4"),
    (483.87, 204.47, "3"),
    (483.87, 207.01, "2"),
    (483.87, 209.55, "1"),
    (483.87, 212.09, "0"),
    (483.87, 217.17, "21"),
    (483.87, 219.71, "20"),
    (483.87, 222.25, "19"),
    (483.87, 224.79, "18"),
    (483.87, 227.33, "17"),
    (483.87, 229.87, "16"),
    (483.87, 232.41, "15"),
    (483.87, 234.95, "14"),
    (483.87, 240.03, "5V_2"),
    (483.87, 257.81, "34"),
    (483.87, 260.35, "36"),
    (483.87, 262.89, "38"),
    (483.87, 265.43, "40"),
    (483.87, 267.97, "42"),
    (483.87, 270.51, "44"),
    (483.87, 273.05, "46"),
    (483.87, 275.59, "48"),
    (483.87, 283.21, "GND4"),
]

all_nc_pins = left_pins + right_pins
for x, y, name in all_nc_pins:
    elements.append(no_connect(x, y))

print(f"  Added {len(all_nc_pins)} no-connect flags on unused A1 pins")

# =========================================================
# Fix 4: Add PWR_FLAG lib symbol + 3 instances
# =========================================================
print("\n--- Fix 4: Add PWR_FLAG symbols ---")

# 4a. Add PWR_FLAG lib symbol definition to lib_symbols section
# Must be inserted inside (lib_symbols ...) before its closing paren
pwr_flag_lib = '''
		(symbol "power:PWR_FLAG"
			(power)
			(pin_numbers
				(hide yes)
			)
			(pin_names
				(offset 0)
				(hide yes)
			)
			(exclude_from_sim no)
			(in_bom yes)
			(on_board yes)
			(property "Reference" "#FLG"
				(at 0 1.905 0)
				(effects
					(font
						(size 1.27 1.27)
					)
					(hide yes)
				)
			)
			(property "Value" "PWR_FLAG"
				(at 0 3.81 0)
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
			(property "Datasheet" ""
				(at 0 0 0)
				(effects
					(font
						(size 1.27 1.27)
					)
					(hide yes)
				)
			)
			(property "Description" "Special symbol for telling ERC where power comes from"
				(at 0 0 0)
				(effects
					(font
						(size 1.27 1.27)
					)
					(hide yes)
				)
			)
			(property "ki_keywords" "flag power"
				(at 0 0 0)
				(effects
					(font
						(size 1.27 1.27)
					)
					(hide yes)
				)
			)
			(symbol "PWR_FLAG_0_0"
				(pin power_out line
					(at 0 0 90)
					(length 0)
					(name "~"
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
			)
			(symbol "PWR_FLAG_0_1"
				(polyline
					(pts
						(xy 0 0) (xy 0 1.27) (xy -1.016 1.905)
						(xy 0 2.54) (xy 1.016 1.905) (xy 0 1.27)
					)
					(stroke
						(width 0)
						(type default)
					)
					(fill
						(type none)
					)
				)
			)
			(embedded_fonts no)
		)'''

# Find the end of lib_symbols section -- it's before the first (rectangle or other schematic element
# The lib_symbols section closes with a pattern like:
#     (embedded_fonts no)
#   )
# )
# (rectangle ...
# Find the closing of the last lib symbol's section
# Actually, let me find the pattern: embedded_fonts no) followed by ) then ) before (rectangle
pat_lib_end = r'(\(embedded_fonts no\)\s*\)\s*\))\s*\n(\s*\(rectangle)'
m = re.search(pat_lib_end, content)
if m:
    # Insert BEFORE the final ) that closes lib_symbols, which is at the end of m.group(1)
    # m.group(1) is like "(embedded_fonts no)\n\t)\n)"
    # The last ) in group(1) closes lib_symbols
    # We want to insert the new symbol before that last )
    insert_pos = m.start(1) + len(m.group(1)) - 1  # position of the final )
    content = content[:insert_pos] + pwr_flag_lib + '\n\t' + content[insert_pos:]
    print("  Added PWR_FLAG lib symbol definition")
else:
    print("  WARN: Could not find lib_symbols section end")

# 4b. Add PWR_FLAG instances
flg_num = 1

def pwr_flag_sym(x, y, ref_num):
    ref = f"#FLG0{ref_num}"
    return f'''
	(symbol
		(lib_id "power:PWR_FLAG")
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
		(property "Value" "PWR_FLAG"
			(at {x} {round(y - 5.08, 2)} 0)
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

# PWR_FLAG on VCC net -- place at same position as #PWR001 VCC (100.33, 74.93)
elements.append(pwr_flag_sym(100.33, 74.93, flg_num)); flg_num += 1
print("  Added PWR_FLAG #FLG01 on VCC net at (100.33, 74.93)")

# PWR_FLAG on GND net -- place at same position as #PWR09 GND (60.96, 81.28)
elements.append(pwr_flag_sym(60.96, 81.28, flg_num)); flg_num += 1
print("  Added PWR_FLAG #FLG02 on GND net at (60.96, 81.28)")

# PWR_FLAG on VBAT net -- place on BT1+ wire at (72, 342.92)
elements.append(pwr_flag_sym(72, 342.92, flg_num)); flg_num += 1
print("  Added PWR_FLAG #FLG03 on VBAT net at (72, 342.92)")

# =========================================================
# Clean up extra blank lines
# =========================================================
content = re.sub(r'\n\t*\n\t*\n', '\n\n', content)

# =========================================================
# Inject new elements before final closing paren
# =========================================================
last_paren = content.rfind(')')
inject = ''.join(elements)
content = content[:last_paren] + inject + '\n' + content[last_paren:]

# =========================================================
# Save
# =========================================================
SCH.write_text(content, encoding="utf-8")

# Count
nc_count = len(all_nc_pins)
print(f"\nDone! Fixed:")
print(f"  - 2 TERM labels relocated to exact pin positions")
print(f"  - 1 orphaned #PWR026 removed")
print(f"  - {nc_count} no-connect flags added on unused A1 pins")
print(f"  - 3 PWR_FLAG symbols added (VCC, GND, VBAT)")
print(f"  - PWR_FLAG lib definition added")
print(f"Saved. Backup at .kicad_sch.bak")
