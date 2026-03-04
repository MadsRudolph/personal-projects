---
title: kicad-skip Schematic Scripting
type: reference
tags:
  - kicad
  - python
  - tooling
  - dtu
parent: "[[DTU Multimeter - Digital Multimeter]]"
created: 2026-03-04
---

# kicad-skip Schematic Scripting

> [!info] What is kicad-skip?
> Python library for reading and writing KiCad 9 `.kicad_sch` files programmatically. Uses `sexpdata` internally to parse S-expressions. Great for batch-placing components, net labels, and power symbols into a schematic that already has ICs placed manually.

---

## Installation

```bash
pip install kicad-skip sexpdata
```

---

## Basic Usage

### Open and save a schematic

```python
import skip
from sexpdata import Symbol as S

schem = skip.Schematic("Multimeter.kicad_sch")

# ... modify ...

schem.write("Multimeter.kicad_sch")
```

> [!warning] Close KiCad first
> KiCad creates `.lck` lock files. The script should check these don't exist, otherwise you'll corrupt data.

### Access existing symbols

```python
# Single-unit symbol
u1 = schem.symbol.U1

# Multi-unit (e.g. LM358 dual opamp)
u4a = schem.symbol.U4_A   # unit 1
u4b = schem.symbol.U4_B   # unit 2
```

### Read a symbol's position

```python
pos = u1.at.value   # returns [x, y, angle] — but it's a DEEP COPY!
```

---

## Injecting New Elements

Use `schem.new_from_list(data)` with raw S-expression lists:

```python
import uuid

def uid():
    return str(uuid.uuid4())

# Place a resistor
sym = [S("symbol"),
       [S("lib_id"), "Device:R"],
       [S("at"), 100, 80, 0],
       [S("unit"), 1],
       [S("exclude_from_sim"), S("no")],
       [S("in_bom"), S("yes")],
       [S("on_board"), S("yes")],
       [S("dnp"), S("no")],
       [S("fields_autoplaced"), S("yes")],
       [S("uuid"), uid()]]

# Add properties (Reference, Value, Footprint, ...)
sym.append([S("property"), "Reference", "R1",
            [S("at"), 100, 76.19, 0],
            [S("effects"), [S("font"), [S("size"), 1.27, 1.27]]]])

# Pin UUIDs (KiCad requires them)
sym.append([S("pin"), "1", [S("uuid"), uid()]])
sym.append([S("pin"), "2", [S("uuid"), uid()]])

# Instance path (use your project's UUID)
sym.append([S("instances"),
            [S("project"), "",
             [S("path"), "/ac1a6b26-...",
              [S("reference"), "R1"],
              [S("unit"), 1]]]])

schem.new_from_list(sym)
```

### Net labels

```python
label = [S("label"), "SPI_SCK",
         [S("at"), 118, 73, 0],
         [S("fields_autoplaced")],
         [S("effects"),
          [S("font"), [S("size"), 1.27, 1.27]],
          [S("justify"), S("left"), S("bottom")]],
         [S("uuid"), uid()]]
schem.new_from_list(label)
```

### Power symbols (VCC / GND)

```python
# VCC points up (angle=0), GND points down (angle=180)
pwr = [S("symbol"),
       [S("lib_id"), "power:GND"],
       [S("at"), 100, 112, 180],  # angle=180 for GND
       ...]
```

---

## Lib-symbols Injection

KiCad requires that all used symbols also exist in the `(lib_symbols ...)` section. Extract them from KiCad's system libraries:

```python
import sexpdata

KICAD_LIB = Path(r"C:\Program Files\KiCad\9.0\share\kicad\symbols")

def extract_lib_symbol(lib_path, symbol_name):
    with open(lib_path, "r", encoding="utf-8") as f:
        tree = sexpdata.loads(f.read())
    for item in tree:
        if isinstance(item, list) and len(item) > 1:
            if isinstance(item[0], S) and item[0].value() == "symbol":
                if item[1] == symbol_name:
                    return copy.deepcopy(item)
    raise ValueError(f"Symbol '{symbol_name}' not found")

# Rename top-level name only (sub-symbols keep original name!)
sym_data = extract_lib_symbol(KICAD_LIB / "Device.kicad_sym", "R")
sym_data[1] = "Device:R"   # ONLY top-level, NOT R_0_1 etc.

# Inject into schematic's raw tree
raw_tree = schem.lib_symbols._pv._sourceTree
for item in raw_tree:
    if isinstance(item, list) and item[0].value() == "lib_symbols":
        item.append(sym_data)
        break
```

> [!danger] Only rename the top-level symbol
> Sub-symbols like `R_0_1` must **not** get the `Device:` prefix. KiCad throws `Invalid symbol unit name prefix` if you do.

---

## Moving Existing Symbols (raw tree)

> [!bug] kicad-skip's `.value` setter is broken
> `sym.at.value` returns a **deep copy** via `AtValue(copy.deepcopy(...))`. Even setter assignment (`sym.at.value = [x, y, 0]`) doesn't propagate to the underlying S-expression tree. **Workaround: manipulate the raw tree directly.**

```python
def move_symbol_raw(raw_tree, ref, new_x, new_y):
    """Move a symbol by editing the sexpdata list directly."""
    # Handle multi-unit: U4_A -> ref="U4", unit=1
    unit_filter = None
    actual_ref = ref
    if '_' in ref:
        parts = ref.rsplit('_', 1)
        suffix = parts[1]
        if len(suffix) == 1 and suffix.isalpha():
            actual_ref = parts[0]
            unit_filter = ord(suffix.upper()) - ord('A') + 1

    for item in raw_tree:
        if not isinstance(item, list) or len(item) < 2:
            continue
        if not (isinstance(item[0], S) and item[0].value() == 'symbol'):
            continue
        if isinstance(item[1], str):   # skip lib_symbol defs
            continue

        # Match Reference
        sym_ref = None
        for sub in item:
            if (isinstance(sub, list) and len(sub) >= 3
                    and sub[0].value() == 'property' and sub[1] == 'Reference'):
                sym_ref = sub[2]
                break
        if sym_ref != actual_ref:
            continue

        # Match unit
        if unit_filter is not None:
            for sub in item:
                if isinstance(sub, list) and sub[0].value() == 'unit':
                    if sub[1] != unit_filter:
                        break
            else:
                continue

        # Update (at x y angle) directly in the list
        for sub in item:
            if isinstance(sub, list) and sub[0].value() == 'at':
                old_x, old_y = sub[1], sub[2]
                dx, dy = new_x - old_x, new_y - old_y
                sub[1], sub[2] = new_x, new_y
                break

        # Shift all property positions by the same delta
        for sub in item:
            if isinstance(sub, list) and sub[0].value() == 'property':
                for child in sub:
                    if isinstance(child, list) and child[0].value() == 'at':
                        child[1] += dx
                        child[2] += dy
                        break
        return True
    return False
```

---

## Footprints (THT)

Standard footprints from KiCad 9's libraries:

| Component       | Footprint                                                                   |
| --------------- | --------------------------------------------------------------------------- |
| Resistor        | `Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal`           |
| Capacitor       | `Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P2.50mm`                               |
| Electrolytic    | `Capacitor_THT:CP_Radial_D5.0mm_P2.50mm`                                   |
| Crystal         | `Crystal:Crystal_C38-LF_D3.0mm_L8.0mm_Horizontal`                          |
| Battery CR2032  | `Battery:BatteryHolder_Keystone_3034_1x20mm`                                |
| Push button     | `Button_Switch_THT:SW_PUSH_6mm`                                            |
| LED 3mm         | `LED_THT:LED_D3.0mm`                                                       |
| Buzzer          | `Buzzer_Beeper:Buzzer_12x9.5RM7.6`                                         |
| Fuse holder     | `Fuse:Fuseholder_Clip-5x20mm_Keystone_3517_Inline_P23.11x6.76mm_D1.70mm_H` |

Footprints are set as `property "Footprint"` with `hide yes`:

```python
sym.append([S("property"), "Footprint",
            "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
            [S("at"), x, y, 0],
            [S("effects"), [S("font"), [S("size"), 1.27, 1.27]], S("hide")]])
```

---

## Group Annotations (rectangles + text)

```python
# Dashed rectangle
rect = [S("rectangle"),
        [S("start"), 75, 42], [S("end"), 130, 120],
        [S("stroke"), [S("width"), 0.2], [S("type"), S("dash")]],
        [S("fill"), [S("type"), S("none")]],
        [S("uuid"), uid()]]

# Bold title text
text = [S("text"), "ADC\n(U1 MCP3208)",
        [S("at"), 76, 41.5, 0],
        [S("effects"),
         [S("font"), [S("size"), 1.5, 1.5],
          [S("thickness"), 0.4], S("bold")],
         [S("justify"), S("left"), S("bottom")]],
        [S("uuid"), uid()]]
```

---

## Workflow Summary

1. **Place ICs manually** in KiCad (large symbols are easier to handle visually)
2. **Close KiCad**
3. **Run the Python script** which:
   - Injects lib_symbols from KiCad's standard libraries
   - Moves ICs to a spread-out layout (raw tree manipulation)
   - Places all passive components with footprints
   - Adds VCC/GND power symbols
   - Sets net labels for all bus connections
   - Draws group rectangles with titles
4. **Open in KiCad 9** → run ERC to check connectivity
5. **Draw wires** manually (or extend the script)

> [!tip] Backup
> The script copies `.kicad_sch` to `.kicad_sch.bak` automatically. Always restore from backup manually if something goes wrong.

---

## See also

- [[DTU Multimeter - Digital Multimeter]]
- [[Build Guide - DTU Multimeter]]
- [kicad-skip GitHub](https://github.com/psychogenic/kicad-skip)
