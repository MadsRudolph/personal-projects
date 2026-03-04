#!/usr/bin/env python3
"""
DTU Digital Multimeter — KiCad Schematic Generator
===================================================
Uses kicad-skip + sexpdata to inject all passive components, net labels,
power symbols, and wires into the existing Multimeter.kicad_sch file
(which already has the 10 main ICs placed).

Usage:
    1. Close KiCad (lock files must not exist)
    2. python generate_schematic.py
    3. Open Multimeter.kicad_sch in KiCad 9
"""

import os
import sys
import copy
import shutil
import uuid as _uuid
from pathlib import Path

import sexpdata
from sexpdata import Symbol as S

import skip

# ═══════════════════════════════════════════════════════════════════
#  Paths
# ═══════════════════════════════════════════════════════════════════

SCRIPT_DIR = Path(__file__).parent
SCHEMATIC_PATH = SCRIPT_DIR / "Multimeter" / "Multimeter.kicad_sch"
KICAD_LIB = Path(r"C:\Program Files\KiCad\9.0\share\kicad\symbols")

# ═══════════════════════════════════════════════════════════════════
#  Footprint constants
# ═══════════════════════════════════════════════════════════════════

FP_R      = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"
FP_C      = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P2.50mm"
FP_CP     = "Capacitor_THT:CP_Radial_D5.0mm_P2.50mm"
FP_XTAL   = "Crystal:Crystal_C38-LF_D3.0mm_L8.0mm_Horizontal"
FP_BATT   = "Battery:BatteryHolder_Keystone_3034_1x20mm"
FP_SW     = "Button_Switch_THT:SW_PUSH_6mm"
FP_LED    = "LED_THT:LED_D3.0mm"
FP_BUZZER = "Buzzer_Beeper:Buzzer_12x9.5RM7.6"
FP_FUSE   = "Fuse:Fuseholder_Clip-5x20mm_Keystone_3517_Inline_P23.11x6.76mm_D1.70mm_Horizontal"

# ═══════════════════════════════════════════════════════════════════
#  UUID helper
# ═══════════════════════════════════════════════════════════════════

def uid():
    return str(_uuid.uuid4())

# ═══════════════════════════════════════════════════════════════════
#  Library symbol extraction
# ═══════════════════════════════════════════════════════════════════

def extract_lib_symbol(lib_path, symbol_name):
    """Extract a symbol definition from a KiCad .kicad_sym library file."""
    with open(lib_path, "r", encoding="utf-8") as f:
        tree = sexpdata.loads(f.read())
    for item in tree:
        if isinstance(item, list) and len(item) > 1:
            if isinstance(item[0], S) and item[0].value() == "symbol":
                if isinstance(item[1], str) and item[1] == symbol_name:
                    return copy.deepcopy(item)
    raise ValueError(f"Symbol '{symbol_name}' not found in {lib_path}")


def prefix_lib_symbol(sym_data, lib_prefix):
    """
    Rename ONLY the top-level symbol name from 'Name' to 'lib_prefix:Name'.
    Sub-symbols (like R_0_1, R_1_1) keep their original names WITHOUT prefix.
    This matches how KiCad stores lib_symbols in schematics.
    e.g. parent: 'R' -> 'Device:R', sub-symbols: 'R_0_1' stays 'R_0_1'
    """
    original_name = sym_data[1]
    new_name = f"{lib_prefix}:{original_name}"
    sym_data[1] = new_name
    # Do NOT rename sub-symbols — they stay as original_name_X_Y
    return sym_data


# ═══════════════════════════════════════════════════════════════════
#  S-expression builders for placed components
# ═══════════════════════════════════════════════════════════════════

def _prop(name, value, x, y, angle=0, hide=False, size=1.27):
    """Build a property S-expression."""
    p = [S("property"), name, str(value),
         [S("at"), x, y, angle],
         [S("effects"),
          [S("font"), [S("size"), size, size]]]]
    if hide:
        p[4].append(S("hide"))
    return p


def make_symbol(lib_id, ref, value, x, y, angle=0, footprint="", unit=1,
                mirror=None, extra_props=None):
    """Build a placed symbol (component) S-expression list."""
    sym = [S("symbol"),
           [S("lib_id"), lib_id],
           [S("at"), x, y, angle],
           [S("unit"), unit],
           [S("exclude_from_sim"), S("no")],
           [S("in_bom"), S("yes")],
           [S("on_board"), S("yes")],
           [S("dnp"), S("no")],
           [S("fields_autoplaced"), S("yes")],
           [S("uuid"), uid()]]

    if mirror:
        sym.insert(3, [S("mirror"), S(mirror)])

    # Properties
    sym.append(_prop("Reference", ref, x, y - 3.81, angle))
    sym.append(_prop("Value", value, x, y - 1.27, angle))
    sym.append(_prop("Footprint", footprint, x, y, angle, hide=True))
    sym.append(_prop("Datasheet", "", x, y, angle, hide=True))
    sym.append(_prop("Description", "", x, y, angle, hide=True))

    if extra_props:
        for ep in extra_props:
            sym.append(ep)

    # Pins — KiCad needs these with unique UUIDs
    # For 2-pin symbols (R, C, LED, etc.)
    sym.append([S("pin"), "1", [S("uuid"), uid()]])
    sym.append([S("pin"), "2", [S("uuid"), uid()]])

    # Instance path
    sym.append([S("instances"),
                [S("project"), "",
                 [S("path"), "/ac1a6b26-ab53-454a-b718-b2b6f7a3a514",
                  [S("reference"), ref],
                  [S("unit"), unit]]]])

    return sym


def make_power_symbol(lib_id, ref, x, y, angle=0):
    """Build a placed power symbol (VCC or GND)."""
    sym = [S("symbol"),
           [S("lib_id"), lib_id],
           [S("at"), x, y, angle],
           [S("unit"), 1],
           [S("exclude_from_sim"), S("no")],
           [S("in_bom"), S("yes")],
           [S("on_board"), S("yes")],
           [S("dnp"), S("no")],
           [S("fields_autoplaced"), S("yes")],
           [S("uuid"), uid()]]

    # Power symbols use #PWR references
    sym.append(_prop("Reference", ref, x, y - 2.54, angle, hide=True))

    net_name = "VCC" if "VCC" in lib_id else "GND"
    sym.append(_prop("Value", net_name, x, y + 2.54, angle))
    sym.append(_prop("Footprint", "", x, y, angle, hide=True))
    sym.append(_prop("Datasheet", "", x, y, angle, hide=True))
    sym.append(_prop("Description", "", x, y, angle, hide=True))

    sym.append([S("pin"), "1", [S("uuid"), uid()]])

    sym.append([S("instances"),
                [S("project"), "",
                 [S("path"), "/ac1a6b26-ab53-454a-b718-b2b6f7a3a514",
                  [S("reference"), ref],
                  [S("unit"), 1]]]])

    return sym


def make_wire(x1, y1, x2, y2):
    """Build a wire S-expression."""
    return [S("wire"),
            [S("pts"), [S("xy"), x1, y1], [S("xy"), x2, y2]],
            [S("stroke"), [S("width"), 0], [S("type"), S("default")]],
            [S("uuid"), uid()]]


def make_label(name, x, y, angle=0):
    """Build a net label S-expression."""
    justify = S("left")
    if angle == 180:
        justify = S("right")
    return [S("label"), name,
            [S("at"), x, y, angle],
            [S("fields_autoplaced")],
            [S("effects"),
             [S("font"), [S("size"), 1.27, 1.27]],
             [S("justify"), justify, S("bottom")]],
            [S("uuid"), uid()]]


def make_junction(x, y):
    """Build a junction S-expression."""
    return [S("junction"),
            [S("at"), x, y],
            [S("diameter"), 0],
            [S("color"), 0, 0, 0, 0],
            [S("uuid"), uid()]]


def make_text(text, x, y, size=2.0):
    """Build a bold text annotation S-expression (group title)."""
    return [S("text"), text,
            [S("at"), x, y, 0],
            [S("effects"),
             [S("font"), [S("size"), size, size],
              [S("thickness"), 0.4], S("bold")],
             [S("justify"), S("left"), S("bottom")]],
            [S("uuid"), uid()]]


def make_rectangle(x1, y1, x2, y2):
    """Build a dashed rectangle S-expression for grouping."""
    return [S("rectangle"),
            [S("start"), x1, y1],
            [S("end"), x2, y2],
            [S("stroke"), [S("width"), 0.2], [S("type"), S("dash")]],
            [S("fill"), [S("type"), S("none")]],
            [S("uuid"), uid()]]


# ═══════════════════════════════════════════════════════════════════
#  IC movement helper  (raw S-expression tree manipulation)
# ═══════════════════════════════════════════════════════════════════

def move_symbol_raw(raw_tree, ref, new_x, new_y):
    """Move a placed symbol by directly modifying the sexpdata tree in-place.

    kicad-skip's .value getter returns a deep copy and the setter chain
    doesn't propagate changes reliably. This function bypasses kicad-skip
    entirely and edits the raw list objects that sexpdata will serialize.

    Handles multi-unit refs: 'U4_A' → Reference='U4', unit=1.
    """
    # Parse multi-unit refs  (U4_A → ref=U4 unit=1, U4_B → ref=U4 unit=2)
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
        # Skip lib_symbol definitions (second element is a string name)
        if isinstance(item[1], str):
            continue

        # ── Match Reference property ──
        sym_ref = None
        for sub in item:
            if (isinstance(sub, list) and len(sub) >= 3
                    and isinstance(sub[0], S) and sub[0].value() == 'property'
                    and sub[1] == 'Reference'):
                sym_ref = sub[2]
                break
        if sym_ref != actual_ref:
            continue

        # ── Match unit (for multi-unit symbols) ──
        if unit_filter is not None:
            sym_unit = None
            for sub in item:
                if (isinstance(sub, list) and len(sub) >= 2
                        and isinstance(sub[0], S) and sub[0].value() == 'unit'):
                    sym_unit = sub[1]
                    break
            if sym_unit != unit_filter:
                continue

        # ── Found the target symbol ──
        # Get current (at x y angle) list
        at_list = None
        for sub in item:
            if (isinstance(sub, list) and len(sub) >= 3
                    and isinstance(sub[0], S) and sub[0].value() == 'at'):
                at_list = sub
                break
        if at_list is None:
            return False

        old_x, old_y = at_list[1], at_list[2]
        dx = new_x - old_x
        dy = new_y - old_y

        # Update symbol position in-place
        at_list[1] = new_x
        at_list[2] = new_y

        # Shift every property's (at) by the same delta
        for sub in item:
            if (isinstance(sub, list) and len(sub) >= 3
                    and isinstance(sub[0], S) and sub[0].value() == 'property'):
                for prop_child in sub:
                    if (isinstance(prop_child, list) and len(prop_child) >= 3
                            and isinstance(prop_child[0], S)
                            and prop_child[0].value() == 'at'):
                        prop_child[1] += dx
                        prop_child[2] += dy
                        break

        return True

    return False


# ═══════════════════════════════════════════════════════════════════
#  Main script
# ═══════════════════════════════════════════════════════════════════

def main():
    # ─── Check lock files ───
    lock1 = SCHEMATIC_PATH.parent / "~Multimeter.kicad_sch.lck"
    lock2 = SCHEMATIC_PATH.parent / "~Multimeter.kicad_pcb.lck"
    if lock1.exists() or lock2.exists():
        print("ERROR: KiCad lock files detected. Close KiCad first!")
        sys.exit(1)

    # ─── Backup ───
    backup = str(SCHEMATIC_PATH) + ".bak"
    shutil.copy2(SCHEMATIC_PATH, backup)
    print(f"Backup created: {backup}")

    # ─── Load schematic ───
    schem = skip.Schematic(str(SCHEMATIC_PATH))
    print(f"Loaded schematic: {SCHEMATIC_PATH}")

    # ─── Extract and inject lib_symbol definitions ───
    print("Extracting library symbol definitions...")

    lib_symbols_needed = {
        "Device:R":              (KICAD_LIB / "Device.kicad_sym", "R", "Device"),
        "Device:C":              (KICAD_LIB / "Device.kicad_sym", "C", "Device"),
        "Device:C_Polarized":    (KICAD_LIB / "Device.kicad_sym", "C_Polarized", "Device"),
        "Device:LED":            (KICAD_LIB / "Device.kicad_sym", "LED", "Device"),
        "Device:Crystal":        (KICAD_LIB / "Device.kicad_sym", "Crystal", "Device"),
        "Device:Buzzer":         (KICAD_LIB / "Device.kicad_sym", "Buzzer", "Device"),
        "Device:Fuse":           (KICAD_LIB / "Device.kicad_sym", "Fuse", "Device"),
        "Device:Battery_Cell":   (KICAD_LIB / "Device.kicad_sym", "Battery_Cell", "Device"),
        "power:VCC":             (KICAD_LIB / "power.kicad_sym", "VCC", "power"),
        "power:GND":             (KICAD_LIB / "power.kicad_sym", "GND", "power"),
        "Switch:SW_Push":        (KICAD_LIB / "Switch.kicad_sym", "SW_Push", "Switch"),
    }

    raw_tree = schem.lib_symbols._pv._sourceTree
    lib_sym_list = None
    for item in raw_tree:
        if isinstance(item, list) and len(item) > 0:
            if isinstance(item[0], S) and item[0].value() == "lib_symbols":
                lib_sym_list = item
                break

    if lib_sym_list is None:
        print("ERROR: Could not find lib_symbols in schematic tree")
        sys.exit(1)

    for full_name, (lib_path, sym_name, prefix) in lib_symbols_needed.items():
        sym_data = extract_lib_symbol(str(lib_path), sym_name)
        sym_data = prefix_lib_symbol(sym_data, prefix)
        lib_sym_list.append(sym_data)
        print(f"  Added lib_symbol: {full_name}")

    # ═══════════════════════════════════════════════════════════════
    #  SECTION 1: MOVE EXISTING ICs TO SPREAD-OUT LAYOUT
    # ═══════════════════════════════════════════════════════════════
    #
    #  Row 1 (y≈80):  Analog front end  U1 → U2 → U3 → U4
    #  Row 2 (y≈210): Measurement       U5, U6, U7
    #  Row 3 (y≈320): Comms / Display   U8, DS
    #  Right (x≈540): Arduino A1 + UI
    #
    #  Uses raw sexpdata tree manipulation (kicad-skip's setter is broken)
    #
    print("Moving ICs to new layout (raw tree)...")

    ic_moves = [
        ("U1",   100,  80),   # MCP3208
        ("U2",   220,  80),   # 74HC4067
        ("U3",   340,  80),   # CD4053
        ("U4_A", 440,  78),   # LM358 unit A (unit 1)
        ("U4_B", 440, 115),   # LM358 unit B (unit 2)
        ("U4_C", 440,  62),   # LM358 power  (unit 3)
        ("U5",   100, 210),   # LM311
        ("U6",   250, 210),   # NE555
        ("U7",   380, 210),   # LM35
        ("U8",   100, 320),   # DS1307
        ("DS1",  260, 320),   # OLED
        ("A1",   540, 190),   # Arduino Mega
    ]

    for ref, nx, ny in ic_moves:
        if move_symbol_raw(raw_tree, ref, nx, ny):
            print(f"  Moved {ref} -> ({nx}, {ny})")
        else:
            print(f"  WARNING: Could not move {ref}")

    # ═══════════════════════════════════════════════════════════════
    #  SECTION 2: PASSIVE COMPONENTS
    # ═══════════════════════════════════════════════════════════════

    print("Placing passive components...")
    pwr_idx = [0]

    def next_pwr():
        pwr_idx[0] += 1
        return f"#PWR{pwr_idx[0]:03d}"

    elements = []

    # --- Input Protection: Fuses (far left) ---
    elements.append(make_symbol("Device:Fuse", "F1", "10A",   30, 48, footprint=FP_FUSE))
    elements.append(make_symbol("Device:Fuse", "F2", "500mA", 30, 68, footprint=FP_FUSE))

    # --- Voltage Divider (R15-R16) left of U1 ---
    elements.append(make_symbol("Device:R", "R15", "1.002M", 60, 60, footprint=FP_R))
    elements.append(make_symbol("Device:R", "R16", "100k",   60, 78, footprint=FP_R))

    # --- Decoupling: C1/C4 near U1 ---
    elements.append(make_symbol("Device:C", "C1", "100n",  78, 55, footprint=FP_C))
    elements.append(make_symbol("Device:C_Polarized", "C4", "10u", 86, 55, footprint=FP_CP))

    # --- Reference Resistors R1-R8, column right of U2 (220,80) ---
    ref_resistors = [
        ("R1", "50.15",     262, 48),
        ("R2", "497",       262, 56),
        ("R3", "4990",      262, 64),
        ("R4", "48.536k",   262, 72),
        ("R5", "498k",      262, 80),
        ("R6", "4.755M",    262, 88),
        ("R7", "10.06M",    262, 96),
        ("R8", "10.03M",    262, 104),
    ]
    for ref, val, x, y in ref_resistors:
        elements.append(make_symbol("Device:R", ref, val, x, y, footprint=FP_R))

    # --- Decoupling: C2/C5 near U2 ---
    elements.append(make_symbol("Device:C", "C2", "100n",  198, 55, footprint=FP_C))
    elements.append(make_symbol("Device:C_Polarized", "C5", "10u", 206, 55, footprint=FP_CP))

    # --- Current Shunt Resistors R9-R14, column right of U3 (340,80) ---
    shunt_resistors = [
        ("R9",  "10k",    382, 52),
        ("R10", "998",    382, 62),
        ("R11", "99.49",  382, 72),
        ("R12", "10.04",  382, 82),
        ("R13", "1.05",   382, 92),
        ("R14", "0.145",  382, 102),
    ]
    for ref, val, x, y in shunt_resistors:
        elements.append(make_symbol("Device:R", ref, val, x, y, footprint=FP_R))

    # --- LM358 Feedback (R20-R21) right of U4 (440,78) ---
    elements.append(make_symbol("Device:R", "R20", "9.09k", 478, 72, footprint=FP_R))
    elements.append(make_symbol("Device:R", "R21", "1k",    478, 88, footprint=FP_R))

    # --- Decoupling: C3/C6 near U4 ---
    elements.append(make_symbol("Device:C", "C3", "100n",  418, 55, footprint=FP_C))
    elements.append(make_symbol("Device:C_Polarized", "C6", "10u", 426, 55, footprint=FP_CP))

    # --- LM311 Threshold (R22-R24) + AC coupling (C7), near U5 (100,210) ---
    elements.append(make_symbol("Device:R", "R22", "10k", 65, 195, footprint=FP_R))
    elements.append(make_symbol("Device:R", "R23", "10k", 65, 212, footprint=FP_R))
    elements.append(make_symbol("Device:R", "R24", "10k", 135, 195, footprint=FP_R))
    elements.append(make_symbol("Device:C", "C7", "100n", 65, 230, footprint=FP_C))

    # --- NE555 timing cap (C8), charge resistors (R17-R19), near U6 (250,210) ---
    elements.append(make_symbol("Device:C", "C8", "100n",  228, 230, footprint=FP_C))
    elements.append(make_symbol("Device:R", "R17", "1.003M", 290, 198, footprint=FP_R))
    elements.append(make_symbol("Device:R", "R18", "10k",    290, 210, footprint=FP_R))
    elements.append(make_symbol("Device:R", "R19", "99.48",  290, 222, footprint=FP_R))

    # --- Crystal + Battery near U8 (100,320) ---
    elements.append(make_symbol("Device:Crystal", "Y1", "32.768kHz", 68, 328, footprint=FP_XTAL))
    elements.append(make_symbol("Device:Battery_Cell", "BT1", "CR2032", 72, 348, footprint=FP_BATT))

    # --- I2C Pull-ups (between U8 and DS) ---
    elements.append(make_symbol("Device:R", "R28", "10k", 180, 305, footprint=FP_R))
    elements.append(make_symbol("Device:R", "R29", "10k", 195, 305, footprint=FP_R))

    # --- LED Resistors + LEDs, right of Arduino (540,190) ---
    elements.append(make_symbol("Device:R", "R25", "330", 590, 140, footprint=FP_R))
    elements.append(make_symbol("Device:R", "R26", "330", 590, 155, footprint=FP_R))
    elements.append(make_symbol("Device:R", "R27", "330", 590, 170, footprint=FP_R))
    elements.append(make_symbol("Device:LED", "D1", "Red",    612, 140, footprint=FP_LED))
    elements.append(make_symbol("Device:LED", "D2", "Green",  612, 155, footprint=FP_LED))
    elements.append(make_symbol("Device:LED", "D3", "Yellow", 612, 170, footprint=FP_LED))

    # --- Buzzer ---
    elements.append(make_symbol("Device:Buzzer", "BZ1", "Piezo", 595, 235, footprint=FP_BUZZER))

    # --- Buttons, right/below Arduino ---
    elements.append(make_symbol("Switch:SW_Push", "SW1", "MODE",   595, 260, footprint=FP_SW))
    elements.append(make_symbol("Switch:SW_Push", "SW2", "FUNC",   595, 275, footprint=FP_SW))
    elements.append(make_symbol("Switch:SW_Push", "SW3", "RANGE",  595, 290, footprint=FP_SW))
    elements.append(make_symbol("Switch:SW_Push", "SW4", "SELECT", 595, 305, footprint=FP_SW))

    # ═══════════════════════════════════════════════════════════════
    #  SECTION 3: POWER SYMBOLS
    # ═══════════════════════════════════════════════════════════════

    print("Placing power symbols...")

    vcc_positions = [
        (100, 55),     # U1 MCP3208
        (220, 50),     # U2 74HC4067
        (340, 52),     # U3 CD4053
        (440, 52),     # U4 LM358
        (100, 182),    # U5 LM311
        (250, 182),    # U6 NE555
        (380, 192),    # U7 LM35
        (100, 295),    # U8 DS1307
        (260, 295),    # DS OLED
        (540, 110),    # A1 Arduino
        (60, 48),      # Voltage divider R15 top
        (187, 295),    # I2C pull-ups top
        (262, 40),     # Ref resistors top
    ]
    for x, y in vcc_positions:
        elements.append(make_power_symbol("power:VCC", next_pwr(), x, y))

    gnd_positions = [
        (100, 112),    # U1 MCP3208
        (220, 115),    # U2 74HC4067
        (340, 115),    # U3 CD4053
        (440, 128),    # U4 LM358
        (100, 240),    # U5 LM311
        (250, 240),    # U6 NE555
        (380, 228),    # U7 LM35
        (100, 350),    # U8 DS1307
        (540, 270),    # A1 Arduino
        (60, 88),      # Voltage divider R16 bottom
        (65, 240),     # LM311 threshold bottom
        (595, 315),    # Buttons GND
        (612, 182),    # LEDs GND
    ]
    for x, y in gnd_positions:
        elements.append(make_power_symbol("power:GND", next_pwr(), x, y, angle=180))

    # ═══════════════════════════════════════════════════════════════
    #  SECTION 4: NET LABELS
    # ═══════════════════════════════════════════════════════════════

    print("Placing net labels...")

    # SPI: U1 right side → Arduino left side
    spi_labels_u1 = [
        ("SPI_SCK",  118, 73, 0),
        ("SPI_MOSI", 118, 78, 0),
        ("SPI_MISO", 118, 83, 0),
        ("SPI_CS",   118, 68, 0),
    ]
    spi_labels_a1 = [
        ("SPI_SCK",  522, 222, 180),
        ("SPI_MOSI", 522, 220, 180),
        ("SPI_MISO", 522, 224, 180),
        ("SPI_CS",   522, 226, 180),
    ]

    # I2C
    i2c_labels = [
        ("I2C_SDA", 522, 192, 180),   # Arduino
        ("I2C_SCL", 522, 194, 180),
        ("I2C_SDA", 115, 318, 0),     # U8 DS1307
        ("I2C_SCL", 115, 322, 0),
        ("I2C_SDA", 245, 318, 180),   # DS OLED
        ("I2C_SCL", 245, 322, 180),
        ("I2C_SDA", 180, 312, 0),     # Pull-up R28
        ("I2C_SCL", 195, 312, 0),     # Pull-up R29
    ]

    # 74HC4067 Mux control
    mux_ctrl_labels = [
        ("MUX_S0", 558, 200, 0),      # Arduino side
        ("MUX_S1", 558, 202, 0),
        ("MUX_S2", 558, 204, 0),
        ("MUX_S3", 558, 206, 0),
        ("MUX_EN", 558, 208, 0),
        ("MUX_S0", 205, 70, 180),     # U2 side
        ("MUX_S1", 205, 73, 180),
        ("MUX_S2", 205, 76, 180),
        ("MUX_S3", 205, 79, 180),
        ("MUX_EN", 205, 82, 180),
    ]

    # MUX_COM: U2 COM → U1 CH0
    mux_com_labels = [
        ("MUX_COM", 238, 85, 0),      # U2 COM output
        ("MUX_COM", 82, 68, 180),     # U1 CH0 input
    ]

    # CD4053 current mux control
    cur_ctrl_labels = [
        ("CUR_A",   558, 210, 0),     # Arduino side
        ("CUR_B",   558, 212, 0),
        ("CUR_C",   558, 214, 0),
        ("CUR_INH", 558, 216, 0),
        ("CUR_A",   325, 70, 180),    # U3 side
        ("CUR_B",   325, 73, 180),
        ("CUR_C",   325, 76, 180),
        ("CUR_INH", 325, 79, 180),
    ]

    # ADC channels
    adc_ch_labels = [
        ("ADC_CH1", 82, 73, 180),     # U1 CH1
        ("ADC_CH2", 82, 76, 180),     # U1 CH2
        ("ADC_CH3", 82, 79, 180),     # U1 CH3
        ("ADC_CH4", 82, 82, 180),     # U1 CH4
        ("ADC_CH5", 82, 85, 180),     # U1 CH5
        ("ADC_CH1", 60, 68, 0),       # Voltage divider mid
        ("ADC_CH2", 35, 55, 0),       # Direct voltage input
        ("ADC_CH3", 458, 76, 0),      # LM358-A output
        ("ADC_CH4", 458, 113, 0),     # LM358-B output
        ("ADC_CH5", 395, 210, 0),     # LM35 output
    ]

    # Capacitance / current source control
    cap_ctrl_labels = [
        ("CAP_CHG",  558, 218, 0),
        ("CAP_DIS",  558, 220, 0),
        ("ISRC_EN",  558, 222, 0),
    ]

    # Frequency input
    freq_labels = [
        ("FREQ_IN", 118, 208, 0),     # LM311 output
        ("FREQ_IN", 522, 180, 180),   # Arduino D2
    ]

    # Buttons
    btn_labels = [
        ("BTN_MODE",  580, 260, 180), # Button side
        ("BTN_FUNC",  580, 275, 180),
        ("BTN_RANGE", 580, 290, 180),
        ("BTN_SEL",   580, 305, 180),
        ("BTN_MODE",  522, 182, 180), # Arduino side D3
        ("BTN_FUNC",  522, 184, 180),
        ("BTN_RANGE", 522, 186, 180),
        ("BTN_SEL",   522, 188, 180),
    ]

    # LEDs
    led_labels = [
        ("LED_RED", 580, 140, 180),   # R25 input
        ("LED_GRN", 580, 155, 180),
        ("LED_YEL", 580, 170, 180),
        ("LED_RED", 558, 228, 0),     # Arduino D8
        ("LED_GRN", 558, 230, 0),
        ("LED_YEL", 558, 232, 0),
    ]

    # Buzzer
    buzzer_labels = [
        ("BUZZER", 580, 235, 180),    # Buzzer side
        ("BUZZER", 558, 226, 0),      # Arduino D7
    ]

    all_labels = (spi_labels_u1 + spi_labels_a1 + i2c_labels +
                  mux_ctrl_labels + mux_com_labels + cur_ctrl_labels +
                  adc_ch_labels + cap_ctrl_labels + freq_labels +
                  btn_labels + led_labels + buzzer_labels)

    for name, x, y, angle in all_labels:
        elements.append(make_label(name, x, y, angle))

    # ═══════════════════════════════════════════════════════════════
    #  SECTION 5: GROUP ANNOTATIONS (text titles + dashed rectangles)
    # ═══════════════════════════════════════════════════════════════

    print("Adding group annotations...")

    groups = [
        ("INPUT PROTECTION\n(Fuses F1-F2 + Voltage Divider R15-R16)",
            15, 32, 75, 98),

        ("ADC\n(U1 MCP3208)",
            75, 42, 130, 120),

        ("ANALOG MUX\n(U2 74HC4067 + Ref R1-R8)",
            185, 35, 285, 115),

        ("CURRENT MUX\n(U3 CD4053 + Shunts R9-R14)",
            310, 38, 405, 115),

        ("SIGNAL CONDITIONING\n(U4 LM358 + R20-R21)",
            410, 42, 498, 130),

        ("DECOUPLING\n(C1-C6 near each IC)",
            75, 42, 130, 58),     # small tag at U1 decoupling

        ("FREQUENCY COUNTER\n(U5 LM311 + R22-R24, C7)",
            50, 175, 150, 248),

        ("CURRENT SOURCE\n(U6 NE555 + C8, R17-R19)",
            215, 175, 310, 240),

        ("TEMPERATURE\n(U7 LM35)",
            365, 185, 410, 235),

        ("RTC\n(U8 DS1307 + Crystal Y1 + Battery BT1)",
            55, 288, 140, 360),

        ("I2C BUS\n(Pull-ups R28-R29)",
            168, 292, 210, 320),

        ("DISPLAY\n(OLED 128x64, DS)",
            240, 300, 290, 340),

        ("USER INTERFACE\n(Buttons SW1-SW4, LEDs D1-D3, Buzzer BZ1)",
            570, 125, 632, 320),
    ]

    for title, x1, y1, x2, y2 in groups:
        elements.append(make_text(title, x1 + 1, y1 - 0.5, size=1.5))
        elements.append(make_rectangle(x1, y1, x2, y2))

    # ═══════════════════════════════════════════════════════════════
    #  SECTION 6: INJECT ALL ELEMENTS INTO SCHEMATIC TREE
    # ═══════════════════════════════════════════════════════════════

    print(f"Injecting {len(elements)} elements into schematic tree...")
    for elem in elements:
        schem.new_from_list(elem)

    # ═══════════════════════════════════════════════════════════════
    #  SECTION 7: SAVE
    # ═══════════════════════════════════════════════════════════════

    output_path = str(SCHEMATIC_PATH)
    schem.write(output_path)
    print(f"\nSchematic saved to: {output_path}")
    print(f"Backup at: {backup}")
    print(f"\nTotal new elements added: {len(elements)}")
    print(f"  - ICs moved: {len(ic_moves)}")
    print(f"  - Resistors: 29, Capacitors: 8")
    print(f"  - Crystal: 1, Battery: 1")
    print(f"  - Switches: 4, LEDs: 3, Buzzer: 1, Fuses: 2")
    print(f"  - Power symbols: {pwr_idx[0]}")
    print(f"  - Net labels: {len(all_labels)}")
    print(f"  - Group annotations: {len(groups)} (text + rectangles)")
    print("\nOpen in KiCad 9 and run ERC to verify connectivity.")


if __name__ == "__main__":
    main()
