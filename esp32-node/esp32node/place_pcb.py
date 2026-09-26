#!/usr/bin/env python3
"""Place esp32node.kicad_pcb: single-sided SMD board for the F1 Ultra fiber laser.

Copper is B.Cu only. Every SMD part sits on B.Cu (flipped); the THT headers sit
on top with their pins pointing away from the SMD side.

Floorplan (seen from the top, y down):

    +------------- antenna overhangs the top edge -------------+
    |  J3  |     fanout     |  U1 (ESP32)  |  fanout  |  J2   |
    | wall |  (pins 38..23) |              | (2..16)  | wall  |
    |------+-----------------------------------------+--------|
    | J4/J5 + pull-ups | U2 reg + caps | J1 USB-C | U3 CH340 + reset/boot |
    +------------------------ bottom edge -----------------------+

J2/J3 follow the module's own pin order (see the schematic's physical-order
ESP32 symbol), so each header fans out of its module column without a crossing.
The header pads are 2.54 mm pitch at 0.84 mm gaps: at 0.35/0.5 no track passes
between them, so the headers are walls and the router has to go round the ends.

Run with system python3 (pcbnew):  python3 place_pcb.py
"""
import json
import os
import shutil
import subprocess
import sys
import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "esp32node.kicad_pcb")
PRO = os.path.join(HERE, "esp32node.kicad_pro")
CLEARANCE, TRACK = 0.35, 0.5          # decided 2026-09-24: laser must hold the ESP32's 0.37 mm pad gaps anyway

# --- geometry anchors (mm) ---------------------------------------------------
MX, MY = 150.0, 100.0                 # module centre
TOP = MY - 9.8                        # board edge = start of the footprint's antenna keep-out
HDR_DX = 24.0                         # module centre -> header pin column (wide enough for the pocket below the module)
HDR_Y1 = MY - 7.0                     # header pin 1 row
LEFT, RIGHT = MX - HDR_DX - 9.0, MX + HDR_DX + 6.0
BOTTOM = 151.0


def board_from_netlist():
    subprocess.run([sys.executable, os.path.join(HERE, "bootstrap_pcb.py"),
                    os.path.join(HERE, "esp32node.net"), PCB,
                    "--clearance", str(CLEARANCE), "--track", str(TRACK), "--no-outline"], check=True)
    return pcbnew.LoadBoard(PCB)


def put(b, ref, x, y, rot=0.0):
    """rot is as seen from the top. KiCad mirrors a flipped (B.Cu) footprint
    about its x axis, so a bottom-side part gets +180 to read as an x-mirror:
    the module's antenna stays at the top edge."""
    fp = b.FindFootprintByReference(ref)
    fp.SetOrientationDegrees((rot + 180.0) % 360 if fp.IsFlipped() else rot)
    fp.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
    return fp


def pad_xy(b, ref, num):
    fp = b.FindFootprintByReference(ref)
    p = next(p for p in fp.Pads() if p.GetNumber() == num)
    return ToMM(p.GetPosition().x), ToMM(p.GetPosition().y)


def place(b):
    # module: flipped to B.Cu, so its pin-1 column lands on the RIGHT (x > MX)
    put(b, "U1", MX, MY)
    p2 = pad_xy(b, "U1", "2"); p38 = pad_xy(b, "U1", "38")
    assert p2[0] > MX and p38[0] < MX, (p2, p38)
    put(b, "J2", MX + HDR_DX, HDR_Y1)          # J2.1 = +3V3 <-> module pin 2
    put(b, "J3", MX - HDR_DX, HDR_Y1)          # J3.1 = GND  <-> module pin 38
    # decoupling at the module's supply pin, inside the right-hand fanout, top
    put(b, "C3", MX + 12.0, MY - 7.0, 90)      # 100n
    put(b, "C4", RIGHT - 2.6, HDR_Y1 + 3.0, 90)  # 10u, outside J2 on the +3V3 side

    # --- lane order decides the rest ------------------------------------------
    # At 0.35/0.5 a track cannot pass between 2.54 mm header pads, so J3's nets
    # leave down the strip outside J3, outermost first: IO23, IO22, TXD0, RXD0,
    # IO4, IO0, IO2. At the bottom the two outer lanes drop into J4 (I2C) at the
    # bottom-left; the inner five turn up into the pocket below the module:
    # IO2 -> LED, IO0 -> Q2/BOOT, IO4 -> 1-Wire, RXD0/TXD0 -> CH340.
    py = MY + 24.0
    # CH340 rot 270: pins 1..8 face down, UD+/UD- mid-row over J1; the UART
    # pads (2, 3) at the right end are reached from under the SOIC body.
    put(b, "U3", MX + 2.0, py, 270)
    assert pad_xy(b, "U3", "5")[1] > py
    put(b, "C7", MX + 9.0, py - 5.0, 90)       # VCC (pin 16, top right)
    put(b, "C5", MX + 6.5, py + 6.5, 90)       # V3 (pin 4, bottom row)
    put(b, "R3", MX + 10.5, py, 90); put(b, "Q1", MX + 14.5, py)       # DTR -> EN
    put(b, "R4", MX - 7.0, py - 3.0, 90); put(b, "Q2", MX - 11.0, py - 3.0)  # RTS -> IO0
    put(b, "SW2", MX, MY + 14.5)               # BOOT, under the module's NC pins
    put(b, "R6", MX + 8.0, MY + 12.5, 90)      # IO0 pull-up, where +3V3 reaches
    put(b, "R8", MX - 16.0, py + 2.0, 90); put(b, "D2", MX - 16.0, py + 6.0, 90)   # IO2 LED
    put(b, "J5", MX - 12.0, py + 3.0)          # 1-Wire (IO4 peels up here)
    put(b, "R11", MX - 8.5, py + 4.0, 90)
    # USB-C centred on the bottom edge under the CH340; CC pull-downs beside it
    put(b, "J1", MX, BOTTOM - 3.9)
    # (flipped, J1's CC2 pad is on the left and CC1 on the right)
    put(b, "R2", MX - 7.5, BOTTOM - 12.0, 90); put(b, "R1", MX + 7.5, BOTTOM - 12.0, 90)
    # bottom-left, under the lanes: I2C header + pull-ups, regulator (+5V from
    # J1's left VBUS pad, +3V3 straight into the pull-ups)
    put(b, "J4", LEFT + 2.8, BOTTOM - 7.0, 90)      # left->right 3V3 IO23 IO22 GND
    put(b, "R9", LEFT + 2.8 + 2.54, BOTTOM - 3.2, 90)
    put(b, "R10", LEFT + 2.8 + 5.08, BOTTOM - 3.2, 90)
    put(b, "C2", LEFT + 13.0, BOTTOM - 4.0, 90)
    put(b, "U2", MX - 13.0, BOTTOM - 5.0)
    put(b, "C1", MX - 13.0, BOTTOM - 11.5, 0)
    # bottom-right: EN network + RESET, power LED; +5V up to J2.15
    put(b, "SW1", MX + 17.0, BOTTOM - 4.5)
    put(b, "R5", RIGHT - 2.6, HDR_Y1 + 30.0, 90); put(b, "C6", RIGHT - 2.6, HDR_Y1 + 35.0, 90)
    put(b, "R7", RIGHT - 2.6, BOTTOM - 12.5, 90); put(b, "D1", RIGHT - 2.6, BOTTOM - 8.0, 90)


def track(b, net, pts, w):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        s = pcbnew.PCB_TRACK(b)
        s.SetStart(VECTOR2I(FromMM(x0), FromMM(y0))); s.SetEnd(VECTOR2I(FromMM(x1), FromMM(y1)))
        s.SetWidth(FromMM(w)); s.SetLayer(pcbnew.B_Cu)
        s.SetNetCode(b.FindNet(net).GetNetCode()); s.SetLocked(True)
        b.Add(s)


def j1_escape(b):
    """Hand-drawn escape from the USB-C pad row, inside the J1 exception.

    Its signal pads are 0.30 mm on a 0.50 mm pitch (0.20 mm gaps), so no 0.5 mm
    track at 0.35 mm can reach them; the router takes over from these stubs'
    far ends, which are all >= 0.9 mm apart. On one layer the two D+ pads and
    two D- pads interleave, so one pair has to join UNDER the connector body:
      D+  joined under the body (pads 149.25 / 150.25), exits from the left pad
      D-  joined in front, looping round D+'s inner pad, exits upward
      VBUS left/right joined under the body, behind the D+ link, clear of the
           NPTH pegs; each side also exits outward
    Coordinates are read off the placed pads, never assumed.
    """
    P = {}
    fp = b.FindFootprintByReference("J1")
    for p in fp.Pads():
        if p.GetNumber():
            P[p.GetNumber()] = (ToMM(p.GetPosition().x), ToMM(p.GetPosition().y))
    y0 = P["A6"][1]                      # pad row
    x = lambda n: P[n][0]
    dp_l, dp_r = sorted((x("A6"), x("B6"))); dm_l, dm_r = sorted((x("A7"), x("B7")))
    assert dp_l < dm_l < dp_r < dm_r, "expected D+ D- D+ D- left to right"
    vb_l, vb_r = sorted((x("A4"), x("A9")))
    cc_l, cc_r = x("B5"), x("A5")        # CC2 left, CC1 right (flipped part)
    assert cc_l < dp_l and cc_r > dm_r
    top = y0 - 1.1                       # just above the pads' top edge, still inside J1's courtyard
    t = 0.2
    # D-: front link over D+'s inner pad, then up
    track(b, "/USB_D-", [(dm_l, y0), (dm_l, top), (dm_r, top), (dm_r, y0)], t)
    track(b, "/USB_D-", [(dm_r, y0), (dm_r, y0 - 3.6)], t)
    # D+: link under the body, exit from the left pad
    track(b, "/USB_D+", [(dp_l, y0), (dp_l, y0 + 1.13), (dp_r, y0 + 1.13), (dp_r, y0)], t)
    track(b, "/USB_D+", [(dp_l, y0), (dp_l, y0 - 3.0), (dp_l - 3.25, y0 - 3.0)], t)
    # CC pins out to their pull-downs
    track(b, "Net-(J1-CC2)", [(cc_l, y0), (cc_l, y0 - 2.0), (cc_l - 3.45, y0 - 2.0)], t)
    # CC1 sits 0.5 mm from D-: peel right before leaving the courtyard
    track(b, "Net-(J1-CC1)", [(cc_r, y0), (cc_r, y0 - 1.0), (cc_r + 0.9, y0 - 1.9), (cc_r + 3.95, y0 - 1.9)], t)
    # VBUS: exits both sides, joined under the body, 0.3 mm wide
    track(b, "+5V", [(vb_l, y0), (vb_l, y0 - 1.02), (vb_l - 2.8, y0 - 1.02)], 0.3)
    track(b, "+5V", [(vb_r, y0), (vb_r, y0 - 1.02), (vb_r + 2.8, y0 - 1.02)], 0.3)
    track(b, "+5V", [(vb_l + 0.15, y0), (vb_l + 0.15, y0 + 2.18), (vb_r - 0.15, y0 + 2.18), (vb_r - 0.15, y0)], 0.3)


def outline(b):
    # (the bootstrap draws none: iterating Drawings() breaks under Python 3.14's SWIG)
    r = pcbnew.PCB_SHAPE(b)
    r.SetShape(pcbnew.SHAPE_T_RECT)
    r.SetStart(VECTOR2I(FromMM(LEFT), FromMM(TOP))); r.SetEnd(VECTOR2I(FromMM(RIGHT), FromMM(BOTTOM)))
    r.SetLayer(pcbnew.Edge_Cuts); r.SetWidth(FromMM(0.1)); r.SetFilled(False)
    b.Add(r)


def pour(b, net, prio=0, rect=None):
    """Copper pour on B.Cu. Default outline = the whole board."""
    x0, y0, x1, y1 = rect or (LEFT, TOP, RIGHT, BOTTOM)
    z = pcbnew.ZONE(b)
    z.SetLayer(pcbnew.B_Cu)
    z.SetNetCode(b.FindNet(net).GetNetCode())
    z.SetAssignedPriority(prio)
    z.SetLocalClearance(FromMM(CLEARANCE))
    z.SetMinThickness(FromMM(0.3))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(FromMM(0.4)); z.SetThermalReliefSpokeWidth(FromMM(0.5))
    ol = z.Outline(); ol.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        ol.Append(FromMM(x), FromMM(y))
    b.Add(z)
    return z


def main():
    pro_before = open(PRO).read()
    shutil.copy(PRO, PRO + ".bak")
    b = board_from_netlist()
    place(b)
    outline(b)
    pour(b, "GND")
    j1_escape(b)
    pcbnew.SaveBoard(PCB, b)
    # SaveBoard may rewrite the project file; keep the schematic netclass keys.
    pro = json.load(open(PRO))
    cls = pro.get("net_settings", {}).get("classes", [])
    if not cls or "wire_width" not in cls[0]:
        open(PRO, "w").write(pro_before)
        print("restored .kicad_pro (SaveBoard dropped the schematic netclass keys)")
    print(f"placed {len(b.GetFootprints())} footprints, board {RIGHT-LEFT:.1f} x {BOTTOM-TOP:.1f} mm")


if __name__ == "__main__":
    main()
