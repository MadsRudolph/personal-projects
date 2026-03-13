"""
Strip RTC section from schematic.
Removes: U8 (DS1307), Y1 (crystal), BT1 (battery), associated power symbols,
wires, labels, junctions, no_connect, rectangle, and text annotation.

Elements removed by UUID:
  U8:       a6678106-4a24-48d3-bbf5-ffd0d59ff0dd
  Y1:       994d4673-9227-44b2-b693-482134052278
  BT1:      dbff15e4-5937-48e5-89a8-666edea3cabb
  #PWR008:  d41911b9-aad5-4f48-8511-833486277776  (VCC for U8)
  #PWR021:  69b9e19c-e585-4935-86b9-92a3e8bf2e31  (GND for U8)
  #PWR034:  c65e21ab-4261-4e8d-92d8-55e6afe5d5fc  (GND for BT1)
  #FLG02:   44a1116c-617e-4c0b-8eef-002e1a2d6a13  (PWR_FLAG for BT1)
  Junction: df616ea6-2303-4132-8525-29c07a4d4e20  (at 71.12, 337.82)
  no_conn:  55f54616-6d86-4d83-a3d8-dee02593e202  (SQW pin)
  I2C_SCL:  232f28d5-49ae-45ce-bb8e-25ea0777ab33  (label at U8)
  I2C_SDA:  62300da1-06ee-4008-aeb7-42bf9c234a47  (label at U8)
  RTC rect: 21904b29-ecf0-4733-9542-9ea24973f43f
  RTC text: 39602f12-6a6c-4ac4-be32-42a4beb9ae8b
  Wires (by UUID):
    5bcfbc33 - (71.12, 337.82) to (71.12, 302.26)
    9b04c00a - (71.12, 302.26) to (101.6, 302.26)
    e6f1a3d5 - (101.6, 302.26) to (101.6, 307.34)
    96c4b7d8 - (101.6, 330.2) to (101.6, 327.66)
    3dddf189 - (86.36, 317.5) to (88.9, 320.04)
    a08711df - (83.82, 325.12) to (88.9, 322.58)
    c642ad88 - (78.74, 325.12) to (83.82, 325.12)
    cda56ab0 - (78.74, 317.5) to (86.36, 317.5)
    f03a6e91 - (71.12, 340.36) to (71.12, 337.82)

Also removes lib_symbols: Timer_RTC:DS1307+, Device:Battery_Cell, Device:Crystal
(only if not used by other components)
"""

import re
import shutil
from pathlib import Path

sch_path = Path(r"C:\Users\Mads2\Documents\Projects\Projects\DTU Multimeter\KiCad\Multimeter\Multimeter.kicad_sch")

# Backup
shutil.copy2(sch_path, sch_path.with_suffix('.kicad_sch.bak_rtc'))

content = sch_path.read_text(encoding='utf-8')

# All UUIDs to remove (symbols, wires, labels, junctions, no_connect, rect, text)
uuids_to_remove = [
    # Symbols
    "a6678106-4a24-48d3-bbf5-ffd0d59ff0dd",  # U8
    "994d4673-9227-44b2-b693-482134052278",  # Y1
    "dbff15e4-5937-48e5-89a8-666edea3cabb",  # BT1
    "d41911b9-aad5-4f48-8511-833486277776",  # #PWR008 VCC
    "69b9e19c-e585-4935-86b9-92a3e8bf2e31",  # #PWR021 GND
    "c65e21ab-4261-4e8d-92d8-55e6afe5d5fc",  # #PWR034 GND
    "44a1116c-617e-4c0b-8eef-002e1a2d6a13",  # #FLG02 PWR_FLAG
    # Wires
    "5bcfbc33-f7bb-4ac8-878f-8f29c04b153c",  # BT1 to VBAT vertical
    "9b04c00a-20ac-46c0-a200-127619d73a1a",  # VBAT horizontal to U8
    "e6f1a3d5-aa3b-4946-bd9b-c6c259f01f80",  # U8 VCC vertical
    "96c4b7d8-bd9c-471c-a5a0-8b1e3581c957",  # U8 GND vertical
    "3dddf189-963b-42f8-902a-968ffb4580ba",  # crystal to U8 X1
    "a08711df-c5b8-424d-803a-ace4da5afedb",  # crystal to U8 X2
    "c642ad88-b82d-4c44-9462-8816002e4baa",  # crystal wire 1
    "cda56ab0-cba0-4aa6-aa48-ee2ca91df38e",  # crystal wire 2
    "f03a6e91-1995-4646-b369-f73be44359cf",  # BT1 to junction
    # Labels
    "232f28d5-49ae-45ce-bb8e-25ea0777ab33",  # I2C_SCL at U8
    "62300da1-06ee-4008-aeb7-42bf9c234a47",  # I2C_SDA at U8
    # Junction
    "df616ea6-2303-4132-8525-29c07a4d4e20",  # junction at BT1
    # No connect
    "55f54616-6d86-4d83-a3d8-dee02593e202",  # SQW pin
]

# Also remove the rectangle and text by UUID
rect_uuid = "21904b29-ecf0-4733-9542-9ea24973f43f"
text_uuid = "39602f12-6a6c-4ac4-be32-42a4beb9ae8b"

removed_count = 0

for uid in uuids_to_remove:
    # Find the top-level element containing this UUID
    # Elements are: (symbol ...), (wire ...), (label ...), (junction ...), (no_connect ...)
    # They start with \t( and end with \t)
    pattern = re.compile(
        r'\t\((?:symbol|wire|label|junction|no_connect)\b[^)]*?'
        r'(?:\([^)]*\)|\n)*?'  # nested parens
        r'.*?' + re.escape(uid) + r'.*?\n\t\)\n',
        re.DOTALL
    )
    match = pattern.search(content)
    if match:
        content = content[:match.start()] + content[match.end():]
        removed_count += 1
        print(f"OK: Removed element with UUID {uid[:12]}...")
    else:
        print(f"WARN: Could not find element with UUID {uid[:12]}...")

# Remove rectangle
rect_pattern = re.compile(
    r'\t\(rectangle\n\t\t\(start 55 285\.46\).*?' + re.escape(rect_uuid) + r'.*?\n\t\)\n',
    re.DOTALL
)
match = rect_pattern.search(content)
if match:
    content = content[:match.start()] + content[match.end():]
    removed_count += 1
    print("OK: Removed RTC rectangle")
else:
    print("WARN: Could not find RTC rectangle")

# Remove text annotation
text_pattern = re.compile(
    r'\t\(text "RTC.*?' + re.escape(text_uuid) + r'.*?\n\t\)\n',
    re.DOTALL
)
match = text_pattern.search(content)
if match:
    content = content[:match.start()] + content[match.end():]
    removed_count += 1
    print("OK: Removed RTC text annotation")
else:
    print("WARN: Could not find RTC text annotation")

# Remove lib_symbols that are only used by RTC components
# Check if Device:Battery_Cell is used elsewhere
battery_uses = len(re.findall(r'lib_id "Device:Battery_Cell"', content))
if battery_uses == 0:
    lib_pattern = re.compile(
        r'\t\t\(symbol "Device:Battery_Cell".*?\n\t\t\)\n',
        re.DOTALL
    )
    match = lib_pattern.search(content)
    if match:
        content = content[:match.start()] + content[match.end():]
        print("OK: Removed Battery_Cell lib_symbol (unused)")

# Check if Timer_RTC:DS1307+ is used elsewhere
ds1307_uses = len(re.findall(r'lib_id "Timer_RTC:DS1307\+"', content))
if ds1307_uses == 0:
    lib_pattern = re.compile(
        r'\t\t\(symbol "Timer_RTC:DS1307\+".*?\n\t\t\)\n',
        re.DOTALL
    )
    match = lib_pattern.search(content)
    if match:
        content = content[:match.start()] + content[match.end():]
        print("OK: Removed DS1307+ lib_symbol (unused)")

# Check if Device:Crystal is used elsewhere
crystal_uses = len(re.findall(r'lib_id "Device:Crystal"', content))
if crystal_uses == 0:
    lib_pattern = re.compile(
        r'\t\t\(symbol "Device:Crystal".*?\n\t\t\)\n',
        re.DOTALL
    )
    match = lib_pattern.search(content)
    if match:
        content = content[:match.start()] + content[match.end():]
        print("OK: Removed Crystal lib_symbol (unused)")

# Write output
sch_path.write_text(content, encoding='utf-8')
print(f"\nDone! Removed {removed_count} elements.")
print("Open in KiCad and run ERC to verify.")
