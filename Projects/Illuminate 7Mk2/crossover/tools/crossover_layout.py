#!/usr/bin/env python3
"""Illuminate 7 Mk2 passive crossover -- schematic layout script.

One board per speaker.  Drawn with the kicad-schematic DSL so the sheet is a
textbook drawing (real wires, ground symbols, parallel groups drawn as
parallel groups) rather than a netlist rendered as a picture.

Topology follows the PrintYourSpeakers reference crossover exactly; only the
component VALUES are substituted for what the DTU component shop stocks.

    tweeter:  IN+ -[ 2u2 || 0.20mH || 9R4 ]- A -[ 5u5 ]- B -[ 10u1 ]- TW+
                                                          B -[ 0.25mH ]- GND
    woofer:   IN+ -[ 41u || 0.70mH || 20R ]- C -[ 2.0mH ]- D --------- WF+
                                                          D -[ 11u5 ]- GND

GND on this sheet is the amplifier's negative input terminal (IN-), the common
return for both drivers.  It is not chassis earth.

Run:  python3 crossover_layout.py
"""
import sys
import json
from pathlib import Path

SKILL = Path("/home/mads/.claude/skills/kicad-schematic/scripts")
sys.path.insert(0, str(SKILL))

from schdraw import Sheet  # noqa: E402

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
NAME = "illuminate7mk2-crossover"
SCH = PROJ / f"{NAME}.kicad_sch"
PRO = PROJ / f"{NAME}.kicad_pro"

G = lambda n: round(n * 1.27, 2)          # noqa: E731  one grid step

# ------------------------------------------------------- symbol field emission
# Two things schdraw's own dumper does not do, and both show up as unreadable
# text on the rendered sheet:
#
#   * KiCad ADDS the symbol's rotation to a field's own text angle, so a field
#     written at angle 0 on a rot=90 resistor renders as vertical text running
#     straight through the body.  Writing angle 90 cancels it out.
#   * Field text is centre-justified, so putting a field "to the right of the
#     bounding box" still draws half of it back over the part.  Offset by half
#     the estimated text width.
#
# The wrapper also injects the extra fields the brief asks for: the original
# reference-design value, and a free-text description.
CHAR_W = 1.15           # mm per character, KiCad stroke font at size 1.27
_orig_dump = Sheet._dump_symbol


def _prop(name, val, at, hide, size=1.27):
    return (
        f'\t\t(property "{name}" "{val}"\n'
        f"\t\t\t(at {round(at[0], 2)} {round(at[1], 2)} {int(at[2])})\n"
        + ("\t\t\t(hide yes)\n" if hide else "")
        + "\t\t\t(show_name no)\n"
        "\t\t\t(do_not_autoplace no)\n"
        f"\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size {size} {size})\n"
        "\t\t\t\t)\n\t\t\t)\n"
        "\t\t)"
    )


def _dump_with_fields(self, p):
    s = _orig_dump(self, p)
    if getattr(p, "is_power_port", False):
        return s
    head, _, tail = s.partition('\t\t(property "Reference"')
    _, _, rest = tail.partition("\t\t(instances")

    bb = p.bbox
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    if getattr(p, "field_pos", None):           # hand-placed (edge connectors)
        ref_at, val_at = p.field_pos
    elif p.rot % 180 == 90:                     # horizontal R / L / C
        ref_at = (p.x, bb[1] - 2.0, 90)
        val_at = (p.x, bb[3] + 2.0, 90)
    elif h >= w:                                # tall part: fields to the right
        ref_at = (bb[2] + 1.27 + CHAR_W * len(p.ref) / 2, p.y - 1.27, 0)
        val_at = (bb[2] + 1.27 + CHAR_W * len(str(p.value)) / 2, p.y + 1.27, 0)
    else:                                       # wide part: above and below
        ref_at = (p.x, bb[1] - 1.778, 0)
        val_at = (p.x, bb[3] + 1.778, 0)

    props = [_prop("Reference", p.ref, ref_at, False),
             _prop("Value", p.value, val_at, False),
             _prop("Footprint", p.footprint, (p.x, p.y, 0), True),
             _prop("Datasheet", "", (p.x, p.y, 0), True)]
    for name, val in getattr(p, "extra", {}).items():
        props.append(_prop(name, val, (p.x, p.y, 0), True))
    return head + "\n".join(props) + "\n\t\t(instances" + rest


Sheet._dump_symbol = _dump_with_fields

# ------------------------------------------------------------------ footprints
# PROVISIONAL.  The shop CSV lists no body sizes for the film caps and the
# coils are bought parts, so every pitch below is a generous guess.  Measure
# the real parts and fix these before placement -- see README.md.
# Measured on DTU shop parts 2026-09-24 (recorded in DTU-EKB/KiCad-components)
FP_CAP_2U2 = "Capacitor_THT:C_Rect_L26.5mm_W7.0mm_P22.50mm_MKS4"   # 63 V, 25.7x6.2x15
FP_CAP_3U3 = "Capacitor_THT:C_Rect_L26.5mm_W8.5mm_P22.50mm_MKS4"   # 100 V, 25x8.2x17.8
FP_CAP_6U8 = "Capacitor_THT:C_Rect_L31.5mm_W11.0mm_P27.50mm_MKS4"  # 100 V, 31x11x21
FP_CAP_8U2 = "Capacitor_THT:C_Rect_L31.5mm_W13.0mm_P27.50mm_MKS4"  # 600 V, 31.5x13.3x28
FP_RES_4R7 = "Resistor_THT:R_Axial_Power_L25.0mm_W9.0mm_P27.94mm"  # 5 W, 24xD8.5
FP_RES_10R = "Resistor_THT:R_Axial_Power_L20.0mm_W6.4mm_P22.40mm"  # 5 W, 18x6x6
FP_TERM = "TerminalBlock:TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm"
FP_L020 = "crossover:L_OffBoard_P10.16mm"
FP_L025 = "crossover:L_OffBoard_P10.16mm"
FP_L070 = "crossover:L_OffBoard_P10.16mm"
FP_L200 = "crossover:L_OffBoard_P10.16mm"

SHEET_UUID = "7e3c1a90-0000-4000-8000-c0ffee000001"

sh = Sheet(paper="A4", title="Illuminate 7 Mk2 - passive crossover (one per speaker)",
           project=NAME, uuid=SHEET_UUID)


def part(lib, ref, at, rot=0, mirror="", value="", fp="", design="", descr=""):
    p = sh.place(lib, ref, at=at, rot=rot, mirror=mirror, value=value, footprint=fp)
    p.extra = {}
    if design:
        p.extra["Design value"] = design
    if descr:
        p.extra["Description"] = descr
    return p


# ------------------------------------------------------------------ geometry
XA = G(38)      # 48.26  IN+ rail / left side of both tank networks
XBT = G(72)     # 91.44  tweeter tank right rail  = node TW_A
XCT = G(116)    # 147.32 node TW_B
XDT = G(160)    # 203.20 node TW+
XBW = G(90)     # 114.30 woofer tank right rail   = node WF_C
XDW = G(154)    # 195.58 node WF_D
XJ_PIN = G(172)  # 218.44 driver connector pin column
XJ = XJ_PIN + 5.08

YT = G(32)      # 40.64  tweeter signal line
YT_CAP = G(22)  # 27.94  tank cap row
YT_RES = G(42)  # 53.34  tank resistor row
YT_P1 = G(26)   # 33.02  upper leg of each parallel cap pair
YT_P2 = G(38)   # 48.26  lower leg
YT_RET = G(58)  # 73.66  tweeter return rail

YW = G(94)      # 119.38 woofer signal line
YW_BT = G(82)   # 104.14 tank cap bank - top rail
YW_BB = G(88)   # 111.76 tank cap bank - bottom rail
YW_BC = G(85)   # 107.95 tank cap bank - cap centres
YW_RES = G(104)  # 132.08 tank resistor row
YW_SH = G(102)  # 129.54 shunt cap top rail
YW_SC = G(105)  # 133.35 shunt cap centres
YW_RET = G(116)  # 147.32 woofer return rail

YJ1 = G(62)     # 78.74  input terminal, between the two branches

# =========================================================== input terminal
J1 = part("Connector:Screw_Terminal_01x02", "J1", at=(G(12), YJ1), mirror="y",
          value="IN (amp)", fp=FP_TERM,
          descr="From Fosi V3 speaker output. Pin1 = IN+, Pin2 = IN- (common)")
J1.field_pos = ((G(12), G(57), 0), (G(14), G(70), 0))

sh.seg(J1.pin(1), (XA, YJ1))                      # IN+ across to the main rail
sh.label((G(28), YJ1), "IN+")
sh.seg(J1.pin(2), (G(20), YJ1 + 2.54))            # IN- sideways, then down
sh.seg((G(20), YJ1 + 2.54), (G(20), G(70)))
sh.gnd((G(20), G(70)), drop=0)

# ERC power flag for the IN-/GND net, in its own spot clear of the signal area.
sh.seg((G(80), G(58)), (G(80), G(62)))
sh.power("power:PWR_FLAG", (G(80), G(58)))
sh.power("power:GND", (G(80), G(62)))
sh.note((G(88), G(61)), "ERC power flag: GND is driven by the amplifier", size=1.27)

# The single IN+ rail: one vertical wire feeding both branch tanks.
sh.seg((XA, YT_CAP), (XA, YW_RES))

# =========================================================== tweeter branch
C101 = part("Device:C", "C101", at=(G(55), YT_CAP), rot=90, value="2u2", fp=FP_CAP_2U2,
            design="2.0 uF", descr="Tank cap, tweeter notch")
L101 = part("Device:L", "L101", at=(G(55), YT), rot=90, value="0.20mH", fp=FP_L020,
            design="200 uH", descr="Air core 0.8 mm wire, target DCR 0.29 ohm")
R101 = part("Device:R", "R101", at=(G(47), YT_RES), rot=90, value="4R7 5W", fp=FP_RES_4R7,
            design="10 ohm 10 W (half)", descr="R101+R102 in series = 9.4 ohm / 10 W")
R102 = part("Device:R", "R102", at=(G(63), YT_RES), rot=90, value="4R7 5W", fp=FP_RES_4R7,
            design="10 ohm 10 W (half)", descr="R101+R102 in series = 9.4 ohm / 10 W")

for row, a, b in ((YT_CAP, C101.pin(1), C101.pin(2)),
                  (YT, L101.pin(1), L101.pin(2))):
    sh.seg((XA, row), a)
    sh.seg(b, (XBT, row))
sh.seg((XA, YT_RES), R101.pin(1))
sh.seg(R101.pin(2), R102.pin(1))
sh.seg(R102.pin(2), (XBT, YT_RES))
sh.seg((XBT, YT_CAP), (XBT, YT_RES))              # node TW_A rail
sh.label((XBT, YT_CAP), "TW_A")

C102 = part("Device:C", "C102", at=(G(94), YT_P1), rot=90, value="3u3", fp=FP_CAP_3U3,
            design="5.6 uF (half)", descr="C102 || C103 = 5.5 uF series cap")
C103 = part("Device:C", "C103", at=(G(94), YT_P2), rot=90, value="2u2", fp=FP_CAP_2U2,
            design="5.6 uF (half)", descr="C102 || C103 = 5.5 uF series cap")
C104 = part("Device:C", "C104", at=(G(138), YT_P1), rot=90, value="6u8", fp=FP_CAP_6U8,
            design="10 uF (half)", descr="C104 || C105 = 10.1 uF series cap")
C105 = part("Device:C", "C105", at=(G(138), YT_P2), rot=90, value="3u3", fp=FP_CAP_3U3,
            design="10 uF (half)", descr="C104 || C105 = 10.1 uF series cap")

for cc, left, right in ((C102, XBT, XCT), (C103, XBT, XCT),
                        (C104, XCT, XDT), (C105, XCT, XDT)):
    sh.seg((left, cc.y), cc.pin(1))
    sh.seg(cc.pin(2), (right, cc.y))

L102 = part("Device:L", "L102", at=(XCT, G(48)), value="0.25mH", fp=FP_L025,
            design="250 uH", descr="Air core 0.8 mm wire, target DCR 0.35 ohm")
sh.seg((XCT, YT_P1), L102.pin(1))                 # node TW_B rail, down into L102
sh.seg(L102.pin(2), (XCT, YT_RET))
sh.label((XCT, YT_P1), "TW_B")

sh.seg((XDT, YT_P1), (XDT, YT_P2))                # node TW+ rail
J2 = part("Connector:Screw_Terminal_01x02", "J2", at=(XJ, YT),
          value="TWEETER", fp=FP_TERM,
          descr="Dayton RST28F-4, 4 ohm. Pin1 = +, Pin2 = -")
sh.seg((XDT, YT), J2.pin(1))
sh.label((G(162), YT), "TW+")
sh.seg(J2.pin(2), (G(168), YT + 2.54))            # tweeter - back to the rail
sh.seg((G(168), YT + 2.54), (G(168), YT_RET))
sh.seg((XCT, YT_RET), (G(168), YT_RET))
sh.gnd((G(146), YT_RET))

# =========================================================== woofer branch
WCAPS = []
for i, x in enumerate((G(46), G(56), G(66), G(76), G(86))):
    c = part("Device:C", f"C20{i + 1}", at=(x, YW_BC), value="8u2", fp=FP_CAP_8U2,
             design="40 uF (fifth)", descr="C201..C205 in parallel = 41 uF tank cap")
    WCAPS.append(c)
sh.seg((XA, YW_BT), (WCAPS[-1].x, YW_BT))         # bank top rail = IN+
sh.seg((WCAPS[0].x, YW_BB), (XBW, YW_BB))         # bank bottom rail = node WF_C
for c in WCAPS:
    sh.seg(c.pin(1), (c.x, YW_BT))
    sh.seg(c.pin(2), (c.x, YW_BB))

L201 = part("Device:L", "L201", at=(G(64), YW), rot=90, value="0.70mH", fp=FP_L070,
            design="700 uH", descr="Air core 0.8 mm wire, target DCR 0.60 ohm")
R201 = part("Device:R", "R201", at=(G(56), YW_RES), rot=90, value="10R 5W", fp=FP_RES_10R,
            design="20 ohm 10 W (half)", descr="R201+R202 in series = 20 ohm / 10 W")
R202 = part("Device:R", "R202", at=(G(72), YW_RES), rot=90, value="10R 5W", fp=FP_RES_10R,
            design="20 ohm 10 W (half)", descr="R201+R202 in series = 20 ohm / 10 W")

sh.seg((XA, YW), L201.pin(1))
sh.seg(L201.pin(2), (XBW, YW))
sh.seg((XA, YW_RES), R201.pin(1))
sh.seg(R201.pin(2), R202.pin(1))
sh.seg(R202.pin(2), (XBW, YW_RES))
sh.seg((XBW, YW_BB), (XBW, YW_RES))               # node WF_C rail
sh.label((XBW, G(92)), "WF_C")

L202 = part("Device:L", "L202", at=(G(122), YW), rot=90, value="2.0mH", fp=FP_L200,
            design="2.0 mH", descr="Air core 0.8 mm wire, target DCR 1.06 ohm")
sh.seg((XBW, YW), L202.pin(1))
sh.seg(L202.pin(2), (XJ_PIN, YW))
sh.label((XDW, YW), "WF_D")

C206 = part("Device:C", "C206", at=(G(148), YW_SC), value="8u2", fp=FP_CAP_8U2,
            design="12 uF (half)", descr="C206 || C207 = 11.5 uF shunt cap")
C207 = part("Device:C", "C207", at=(G(160), YW_SC), value="3u3", fp=FP_CAP_3U3,
            design="12 uF (half)", descr="C206 || C207 = 11.5 uF shunt cap")
sh.seg((XDW, YW), (XDW, YW_SH))
sh.seg((C206.x, YW_SH), (C207.x, YW_SH))
for c in (C206, C207):
    sh.seg((c.x, YW_SH), c.pin(1))
    sh.seg(c.pin(2), (c.x, YW_RET))

J3 = part("Connector:Screw_Terminal_01x02", "J3", at=(XJ, YW),
          value="WOOFER", fp=FP_TERM,
          descr="Dayton RS180P-8, 8 ohm. Pin1 = +, Pin2 = -")
sh.seg(J3.pin(2), (G(168), YW + 2.54))
sh.seg((G(168), YW + 2.54), (G(168), YW_RET))
sh.seg((C206.x, YW_RET), (G(168), YW_RET))
sh.gnd((G(154), YW_RET))

# ------------------------------------------------------------------ captions
sh.note((G(30), G(13)), "TWEETER BRANCH - Dayton RST28F-4 (4 ohm)", size=2)
sh.note((G(30), G(73)), "WOOFER BRANCH - Dayton RS180P-8 (8 ohm)", size=2)
sh.note((G(10), G(52)), "IN from Fosi V3 amplifier", size=1.27)
sh.note((G(10), G(54)), "(TPA3255, 48 V rail)", size=1.27)
sh.note((G(36), G(48)), "series tank in the branch, not a shunt", size=1.27)
sh.note((G(96), G(105)), "series tank in the branch, not a shunt", size=1.27)

NOTE_X = G(10)
NOTES = [
    "NOTES  -  one board per speaker, build two.   Value field = DTU component shop part number.",
    "1. GND = IN- , the amplifier's negative speaker terminal and the common return for both drivers.",
    "   It is NOT chassis earth, and the two boards' returns must not be tied to each other.",
    "2. All capacitors are FILM and must be rated >= 63 V, 100 V preferred. The shop lists no voltage",
    "   rating, so CHECK THE PRINTING ON THE ACTUAL PARTS before fitting them.",
    "3. Series pairs:   R101+R102 = 9.4 ohm / 10 W (design 10 ohm).   R201+R202 = 20 ohm / 10 W (20).",
    "4. Parallel caps:  C102||C103 = 5.5uF (5.6).  C104||C105 = 10.1uF (10).  C201..C205 = 41uF (40).",
    "                   C206||C207 = 11.5uF (12).  Each part's 'Design value' field holds the original.",
    "5. L101/L102/L201/L202 are air-core coils, 0.8 mm (20 AWG) wire - self-wound or bought (Dayton",
    "   AC20-20 / AC20-25 / AC20-70 / AC202 or Jantzen Audio equivalents. Target DCR is in Description.",
    "6. FOOTPRINTS ARE PROVISIONAL: measure cap lead pitch before routing. Coils mount OFF the board (lead pads only).",
    "7. Single-sided board, CNC isolation-milled with a 0.8 mm end mill. Through-hole only.",
]
for i, line in enumerate(NOTES):
    sh.note((NOTE_X, G(115) + i * G(3.3)), line, size=1.27)

# ------------------------------------------------------------------ verify
TARGET = {
    "IN+": {("J1", "1"), ("C101", "1"), ("L101", "1"), ("R101", "1"),
            ("C201", "1"), ("C202", "1"), ("C203", "1"), ("C204", "1"),
            ("C205", "1"), ("L201", "1"), ("R201", "1")},
    "TW_R": {("R101", "2"), ("R102", "1")},
    "TW_A": {("C101", "2"), ("L101", "2"), ("R102", "2"), ("C102", "1"), ("C103", "1")},
    "TW_B": {("C102", "2"), ("C103", "2"), ("C104", "1"), ("C105", "1"), ("L102", "1")},
    "TW+": {("C104", "2"), ("C105", "2"), ("J2", "1")},
    "WF_R": {("R201", "2"), ("R202", "1")},
    "WF_C": {("C201", "2"), ("C202", "2"), ("C203", "2"), ("C204", "2"),
             ("C205", "2"), ("L201", "2"), ("R202", "2"), ("L202", "1")},
    "WF_D": {("L202", "2"), ("C206", "1"), ("C207", "1"), ("J3", "1")},
    "GND": {("J1", "2"), ("L102", "2"), ("J2", "2"), ("C206", "2"), ("C207", "2"),
            ("J3", "2")},
}

problems = sh.check()
for p in problems:
    print("CHECK:", p)
ok = sh.verify_against(TARGET)
sh.emit(SCH)
print("wrote", SCH)

# ------------------------------------------------------------------ project
pro = {
    "board": {"3dviewports": [], "design_settings": {"defaults": {}, "diff_pair_dimensions": [],
              "drc_exclusions": [], "rules": {}, "track_widths": [], "via_dimensions": []},
              "layer_presets": [], "viewports": []},
    "boards": [],
    "cvpcb": {"equivalence_files": []},
    "erc": {"erc_exclusions": [], "meta": {"version": 0}, "pin_map": [], "rule_severities": {},
            "severities": {}},
    "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
    "meta": {"filename": f"{NAME}.kicad_pro", "version": 3},
    "net_settings": {
        "classes": [{
            "bus_width": 12.0,
            "clearance": 0.85,          # CNC isolation-mill profile
            "diff_pair_gap": 0.25,
            "diff_pair_via_gap": 0.25,
            "diff_pair_width": 0.2,
            "line_style": 0,
            "microvia_diameter": 0.3,
            "microvia_drill": 0.1,
            "name": "Default",
            "pcb_color": "rgba(0, 0, 0, 0.000)",
            "priority": 2147483647,
            "schematic_color": "rgba(0, 0, 0, 0.000)",
            "track_width": 1.0,
            "tuning_profile": "",
            "via_diameter": 0.8,
            "via_drill": 0.4,
            "wire_width": 6.0,
        }],
        "meta": {"version": 5},
        "net_colors": None,
        "netclass_assignments": None,
        "netclass_patterns": [],
    },
    "pcbnew": {"last_paths": {}, "page_layout_descr_file": ""},
    "schematic": {"drawing": {"default_line_thickness": 6.0, "default_text_size": 50.0},
                  "legacy_lib_dir": "", "legacy_lib_list": [],
                  "meta": {"version": 1}, "net_format_name": "", "spice_external_command": ""},
    "sheets": [[SHEET_UUID, ""]],
    "text_variables": {},
    "tuning_profiles": [],
}
PRO.write_text(json.dumps(pro, indent=2) + "\n", encoding="utf-8")
print("wrote", PRO)
sys.exit(0 if ok and not problems else 1)
