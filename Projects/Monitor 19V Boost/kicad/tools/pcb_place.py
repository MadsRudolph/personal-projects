#!/usr/bin/env python3
"""Build and place monitor-boost.kicad_pcb from the schematic's netlist.

Hand floorplan, because on a converter the hot loop decides where things go:

    top edge   L1 (vertical toroid) | Q1 | D1      <- one pad row, y = PAD_Y
               SW is a copper strip ABOVE that pad row joining L1.2, Q1.D, D1.A;
               Q1.G, Q1.S and D1.K all leave downwards.
    middle     J1 + C1/C2 (left) | Q2/Q3 totem pole | R1/R2 shunts (vertical,
               straight under Q1.S) | C4..C6 (+ on top, - below) | J2 (right edge)
    bottom     U1 SG3524 with its networks around the pins they serve

Coordinates are pad-1 anchors in board-local mm (origin = top-left of the
outline).  Rotation: 270 turns a horizontal footprint so pad 2 sits BELOW pad 1.

Run from the project root:  python3 kicad/tools/pcb_place.py
Needs pcbnew (KiCad 10's python module).
"""
import json
import subprocess
import sys
from pathlib import Path

import pcbnew
from pcbnew import VECTOR2I, FromMM

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
NAME = "monitor-boost"
SCH = PROJ / f"{NAME}.kicad_sch"
PCB = PROJ / f"{NAME}.kicad_pcb"
STOCK = Path("/usr/share/kicad/footprints")
LOCAL = PROJ / "lib"
NETJSON_TOOL = Path("/home/mads/.claude/skills/kicad-laser-pcb/scripts/pcb_netlist_json.py")

W, H = 148.0, 118.0            # board outline, mm (mill envelope is 203 x 152)
OX, OY = 20.0, 20.0            # outline origin on the KiCad sheet
PAD_Y = 10.0                   # the L1 / Q1 / D1 pad row

# Every part is hand-placed and LOCKED; the router only routes.
#
# Ground topology is what drives this.  On a TO-220 the gate pin sits beside
# the drain, so the gate line always starts INSIDE the input current loop
# (C_in -> L1 -> Q1 -> shunt -> GND -> C_in) and on one layer it must cross
# that loop's ground return.  So the return is a protected copper strip
# (STRIP keep-out: no tracks, pour allowed) and the only things that cross it
# are component BODIES: R4 (gate) and R6 (+12V -> VCC_F) straddle it.  The
# output loop's ground (C_out- -> shunt) is fenced off the same way (OUTGND),
# so VOUT sense has to go round the outside.  Everything below the strip is
# the control section; its ground joins the power ground at the strip.
PLACE = {
    # ---- power row along the top edge: one pad row, SW copper above it
    "L1": (12.0, PAD_Y, 0),          # pads 12.0 (+12V) and 40.2 (SW)
    "Q1": (48.0, PAD_Y, 0),          # G 48.0, D 50.54, S 53.08; tab to the edge
    "D1": (60.0, PAD_Y, 0),          # K 60.0, A 65.08
    # ---- input
    "J1": (5.0, 26.0, 270),          # +12V (5,26), GND (5,31)
    "C1": (19.0, 25.0, 270),         # + (19,25)  - (19,32.5)
    "C2": (27.0, 43.0, 270),         # + (27,43)  - (27,50.5)  <- on the strip
    "C3": (10.0, 40.0, 270),         # +12V (10,40) / GND (10,45)
    # ---- inside the input loop: gate line straight down x = 48
    "R5": (48.0, 16.0, 0),           # GATE (48,16) -> CS (58.16,16)
    # ---- the two straddles over the ground strip (y 49.6..56.4)
    "R6": (40.0, 58.5, 90),          # VCC_F (40,58.5) below / +12V (40,48.34) above
    "R4": (48.0, 58.5, 90),          # DRV_E (48,58.5) below / GATE (48,48.34) above
    # ---- shunts straight under Q1.S, GND ends on the strip
    "R1": (56.0, 20.0, 270),         # CS (56,20) -> GND (56,47.94)
    "R2": (66.0, 20.0, 270),
    # ---- output
    "C7": (72.5, 20.0, 270),         # VOUT (72.5,20) / GND (72.5,25)
    "C4": (84.0, 22.0, 270),         # + (84,22)  - (84,29.5)
    "C5": (101.5, 22.0, 270),
    "C6": (119.0, 22.0, 270),
    "J2": (133.0, 22.0, 270),        # VOUT (133,22), GND (133,27)
    "D2": (142.0, 16.0, 270),        # K VOUT (142,16), A GND (142,31.24)
    "R18": (138.0, 52.0, 270),       # VOUT (138,52) -> LEDA (138,62.16)
    "D3": (138.0, 72.0, 90),         # A (138,66.92), K GND (138,72)
    # ---- gate drive below the strip: Q2 over Q3, bases in the middle
    # two rows, same orientation: emitters in one column straight under R4,
    # bases in another (DRV), collectors between them -- Q2's leaves UP to
    # VCC_F, Q3's leaves DOWN to ground, so nothing has to cross.
    "Q2": (48.0, 64.0, 180),         # E (48,64)  C (45.46,64)  B (42.92,64)
    "Q3": (48.0, 70.0, 180),         # E (48,70)  C (45.46,70)  B (42.92,70)
    "R3": (39.5, 67.75, 180),        # DRV (39.5,67.75) -> GND (29.34,67.75)
    "C9": (35.5, 61.5, 180),         # VCC_F + (35.5,61.5) / GND (33,61.5), minus faces out
    "C10": (35.0, 81.0, 180),        # VCC_F (35,81) / GND (30,81), at U1's supply run
    # ---- controller: U1 on its side, pin 1 bottom-left
    #      top row  REF VCC E_B C_B C_A E_A SD COMP   (y 84.38)
    #      bottom   IN- IN+ OSC CL+ CL- RT  CT GND    (y 92)
    "U1": (40.0, 92.0, 90),
    # reference divider and soft start, left end
    "C11": (37.0, 84.38, 180),       # REF (37,84.38) / GND (32,84.38)
    "R8": (35.0, 88.0, 270),         # REF (35,88) -> POT_T (35,98.16)
    "RV1": (35.0, 102.0, 90),        # 1 (35,102)  wiper (35,104.54)  3 (35,107.08)
    "R9": (31.0, 107.08, 180),       # POT_B (31,107.08) -> GND (20.84,107.08)
    "C13": (33.0, 113.5, 0),         # IN+ (33,113.5) / GND (38,113.5), under RV1
    # current sense filter and oscillator under the bottom row
    "R15": (47.62, 96.0, 270),       # ISENSE (47.62,96) -> GND (47.62,106.16), under CL+
    "R14": (44.3, 108.0, 90),        # CS (44.3,108) [wire link lands here] -> ISENSE (44.3,97.84)
    "C17": (50.5, 103.0, 0),         # ISENSE (50.5,103) / GND (55.5,103)
    "R7": (60.0, 100.0, 270),        # RT (60,100) -> GND (60,110.16)
    "C12": (65.0, 97.0, 270),        # CT (65,97) / GND (65,102)
    # over-voltage shutdown, above the SD pin
    "R16": (59.24, 67.0, 270),       # OVP_Z (59.24,67) -> OVP_SD (59.24,77.16)
    "R17": (62.5, 80.16, 90),        # OVP_SD (62.5,80.16) -> GND (62.5,70)
    "C18": (66.0, 80.16, 90),        # OVP_SD (66,80.16) / GND (66,75.16)
    "D4": (78.0, 67.0, 180),         # K VOUT (78,67), A OVP_Z (70.38,67)
    # feedback network, right end (FB node on x = 78)
    "C16": (75.0, 84.38, 180),       # FB (75,84.38) / COMP (70,84.38)
    "C15": (75.0, 78.0, 180),        # NF (75,78) / COMP (70,78)
    "R13": (78.0, 84.38, 90),        # FB (78,84.38) -> NF (78,74.22)
    "R11": (78.0, 92.0, 270),        # FB (78,92) -> GND (78,102.16)
    "C14": (86.0, 88.0, 180),        # N3 (86,88) / FB (81,88)
    "R12": (100.0, 88.0, 180),       # VOUT (100,88) -> N3 (89.84,88)
    "R10": (92.0, 94.0, 180),        # VOUT (92,94) -> FB (81.84,94)
}
STRIP = (17.0, 49.6, 72.0, 56.4)     # input-loop ground return, x0 y0 x1 y1
OUTGND = (58.0, 27.5, 130.0, 50.0)   # output-loop ground (C_out- -> shunt)


def netlist():
    net = PROJ / "build" / f"{NAME}.net"
    js = PROJ / "build" / f"{NAME}.json"
    net.parent.mkdir(exist_ok=True)
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr",
                    "-o", str(net), str(SCH)], check=True, capture_output=True)
    subprocess.run([sys.executable, str(NETJSON_TOOL), str(net), str(js)], check=True,
                   capture_output=True)
    return json.loads(js.read_text())


def load_fp(fpid):
    lib, name = fpid.split(":")
    for base in (LOCAL, STOCK):
        d = base / f"{lib}.pretty"
        if d.is_dir():
            fp = pcbnew.FootprintLoad(str(d), name)
            if fp is not None:
                return fp
    raise SystemExit(f"footprint not found: {fpid}")


def mm(x, y):
    return VECTOR2I(FromMM(OX + x), FromMM(OY + y))


def main():
    data = netlist()
    board = pcbnew.NewBoard(str(PCB))
    nets = {}
    for name in data["nets"]:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni

    missing = []
    for c in data["components"]:
        fp = load_fp(c["footprint"])
        fp.SetReference(c["ref"])
        fp.SetValue(c["value"] or "")
        board.Add(fp)
        for pad in fp.Pads():
            n = c["pads"].get(pad.GetNumber())
            if n:
                pad.SetNet(nets[n])
        if c["ref"] in PLACE:
            x, y, rot = PLACE[c["ref"]]
            fp.SetOrientationDegrees(rot)
            fp.SetPosition(mm(x, y))
            fp.SetLocked(True)
        else:
            missing.append(c["ref"])
    if missing:
        raise SystemExit(f"no placement for {missing}")

    # outline
    pts = [(0, 0), (W, 0), (W, H), (0, H)]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(mm(*a))
        seg.SetEnd(mm(*b))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(FromMM(0.1))
        board.Add(seg)

    # SW is a copper ZONE, not tracks: a 3 mm-plus strip ABOVE the L1/Q1/D1 pad
    # row that reaches down into Q1's middle (drain) pad -- the only way in
    # between G and S.  (Pre-routed tracks of any kind, fix or protect, wedge
    # FreeRouting 1.9.0: measured, it never writes a .ses.)
    sw = pcbnew.ZONE(board)
    sw.SetLayer(pcbnew.B_Cu)
    sw.SetNet(nets["/SW"])
    sw.SetZoneName("SW")
    sw.SetAssignedPriority(1)
    sw.SetLocalClearance(FromMM(0.85))
    sw.SetMinThickness(FromMM(0.8))
    sw.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    o = sw.Outline()
    o.NewOutline()
    for x, y in [(38.0, 1.5), (67.5, 1.5), (67.5, PAD_Y + 1.5), (38.0, PAD_Y + 1.5)]:
        o.Append(FromMM(OX + x), FromMM(OY + y))
    board.Add(sw)

    # GND pour on the copper side: the floor analysis (place_floor.py --pours)
    # says GND poured -> no bridge is topologically forced.
    zone = pcbnew.ZONE(board)
    zone.SetLayer(pcbnew.B_Cu)
    zone.SetNet(nets["GND"])
    zone.SetZoneName("GND")
    zone.SetLocalClearance(FromMM(0.85))
    zone.SetMinThickness(FromMM(0.8))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    zone.SetThermalReliefGap(FromMM(0.85))
    zone.SetThermalReliefSpokeWidth(FromMM(1.0))
    ol = zone.Outline()
    ol.NewOutline()
    for x, y in [(0.5, 0.5), (W - 0.5, 0.5), (W - 0.5, H - 0.5), (0.5, H - 0.5)]:
        ol.Append(FromMM(OX + x), FromMM(OY + y))
    board.Add(zone)

    # keep-outs: no tracks, copper pour allowed
    for name, (x0, y0, x1, y1) in (("STRIP", STRIP), ("OUTGND", OUTGND)):
        ko = pcbnew.ZONE(board)
        ko.SetIsRuleArea(True)
        ko.SetZoneName(name)
        ko.SetLayer(pcbnew.B_Cu)
        ko.SetDoNotAllowTracks(True)
        ko.SetDoNotAllowVias(True)
        ko.SetDoNotAllowPads(False)
        ko.SetDoNotAllowZoneFills(False)
        ko.SetDoNotAllowFootprints(False)
        o = ko.Outline()
        o.NewOutline()
        for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
            o.Append(FromMM(OX + x), FromMM(OY + y))
        board.Add(ko)

    ds = board.GetDesignSettings()
    ds.m_MinClearance = FromMM(0.85)
    ds.m_TrackMinWidth = FromMM(0.8)
    board.SetCopperLayerCount(2)
    # pcbnew.SaveBoard rewrites the sibling .kicad_pro with default netclasses
    # (0.2 mm), silently disarming DRC -- keep the real one.
    pro = PCB.with_suffix('.kicad_pro')
    keep = pro.read_text() if pro.exists() else None
    pcbnew.SaveBoard(str(PCB), board)
    if keep is not None:
        pro.write_text(keep)
    print("wrote", PCB)


if __name__ == "__main__":
    main()
