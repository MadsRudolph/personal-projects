"""
Remove the J3 power input block that was just added.
Keeps J1/J2 banana jack footprints.
Removes: J3 symbol, VCC #PWR040, GND #PWR041, 2 wires, text annotation,
         and the Conn_01x02_Pin lib_symbol.
"""

import shutil
from pathlib import Path

sch_path = Path(r"C:\Users\Mads2\Documents\Projects\Projects\DTU Multimeter\KiCad\Multimeter\Multimeter.kicad_sch")
shutil.copy2(sch_path, sch_path.with_suffix('.kicad_sch.bak_rmj3'))

content = sch_path.read_text(encoding='utf-8')

# Remove blocks by finding unique markers and deleting full s-expression blocks
removals = [
    # J3 connector - find by reference "J3" in property
    ('"Connector:Conn_01x02_Pin")\n\t\t(at 25.4 83.82', 'J3'),
    # VCC #PWR040
    ('"power:VCC")\n\t\t(at 30.48 81.28', '#PWR040'),
    # GND #PWR041
    ('"power:GND")\n\t\t(at 30.48 88.9', '#PWR041'),
    # Wire VCC to J3 pin1
    ('(xy 30.48 81.28) (xy 30.48 83.82)', 'wire VCC-J3'),
    # Wire J3 pin2 to GND
    ('(xy 30.48 86.36) (xy 30.48 88.9)', 'wire J3-GND'),
    # Text annotation
    ('POWER INPUT\\n(J3 Screw Terminal, 5V + GND)', 'text'),
]

def remove_sexp_block(text, marker, prefix='\t(symbol', alt_prefixes=None):
    """Remove an s-expression block containing the marker."""
    idx = text.find(marker)
    if idx == -1:
        return text, False

    # Search backwards for the block start
    prefixes = [prefix] if alt_prefixes is None else [prefix] + alt_prefixes
    start = -1
    for p in prefixes:
        s = text.rfind(p, 0, idx)
        if s != -1 and (start == -1 or s > start):
            start = s

    if start == -1:
        return text, False

    # Find matching closing paren
    depth = 0
    i = start
    while i < len(text):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                # Remove the block plus trailing newline
                end = i + 1
                while end < len(text) and text[end] in '\n\r':
                    end += 1
                text = text[:start] + text[end:]
                return text, True
        i += 1
    return text, False

for marker, name in removals:
    if 'wire' in name:
        content, ok = remove_sexp_block(content, marker, prefix='\t(wire', alt_prefixes=['\t(wire'])
    elif 'text' in name:
        content, ok = remove_sexp_block(content, marker, prefix='\t(text', alt_prefixes=['\t(text'])
    else:
        content, ok = remove_sexp_block(content, marker)
    print(f"{'OK' if ok else 'WARN'}: Remove {name}")

# Remove Conn_01x02_Pin lib_symbol
content, ok = remove_sexp_block(content, '"Connector:Conn_01x02_Pin"', prefix='\t\t(symbol')
print(f"{'OK' if ok else 'WARN'}: Remove Conn_01x02_Pin lib_symbol")

sch_path.write_text(content, encoding='utf-8')
print("\nDone! J3 power block removed. J1/J2 banana jack footprints kept.")
