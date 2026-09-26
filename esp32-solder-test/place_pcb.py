#!/usr/bin/env python3
"""Place esp32solder.kicad_pcb: single-sided, fiber-laser etched (B.Cu only).

The ESP32 sits on B.Cu (the copper side, flipped); every other part is
through-hole on top and solders on B.Cu. Rule 0.3 mm clearance / 0.5 mm track,
inside what the coupon proved (0.15 / 0.15 clean).

Floorplan, seen from the top (y down), derived from where the used module pads
land once the module is flipped:

    +---------- antenna overhangs the top edge ----------+
    | J1 (GND 5V TX RX) |   U1 ESP32   | C3   EN: R3 C4  |
    |  <- UART pins 35/34 on the left  | VDD/EN pins 2/3 |
    |                    |             |  SW1 RESET      |
    | SW2 BOOT + R4 | R5/D1 (IO2) |                 | R6/D2  |
    | C1 U2 LM317 C2 --R1-- R2    ... +3V3 along the bottom ... |
    +------------------------------------------------------------+

+5V comes down the left edge straight into U2's VI. +3V3 leaves VO along the
bottom and up the right edge to R6, R3, C3 and VDD; R4 taps it on the way.
ADJ leaves under the TO-220 body (on the copper side only pads block tracks),
so R1 sits between the +3V3 and ADJ runs and nothing crosses.

Run with system python3:  PYTHONPATH=tools/pyshim python3 place_pcb.py
"""
import json
import math
import os
import shutil
import subprocess
import sys
import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "esp32solder.kicad_pcb")
PRO = os.path.join(HERE, "esp32solder.kicad_pro")
CLEARANCE, TRACK = 0.3, 0.5

MX, MY = 150.0, 100.0                 # module centre
TOP = MY - 9.8                        # board edge = start of the antenna keep-out
LEFT, RIGHT, BOTTOM = 126.0, 180.0, 136.0


def pad_xy(b, ref, num):
    p = next(p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num)
    return ToMM(p.GetPosition().x), ToMM(p.GetPosition().y)


def put(b, ref, x, y, rot=0.0, anchor_pad=None):
    """Place so `anchor_pad` (or the footprint origin) lands on (x, y).
    rot is as seen from the top; a flipped part gets +180 so it reads as an x-mirror."""
    fp = b.FindFootprintByReference(ref)
    fp.SetOrientationDegrees((rot + 180.0) % 360 if fp.IsFlipped() else rot)
    fp.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
    if anchor_pad:
        px, py = pad_xy(b, ref, anchor_pad)
        fp.SetPosition(VECTOR2I(FromMM(2 * x - px), FromMM(2 * y - py)))
    return fp


def put2(b, ref, a, pa, bnum, pb):
    """Two-pad part: pad `a` lands on pa and pad `bnum` points at pb."""
    fp = b.FindFootprintByReference(ref)
    fp.SetOrientationDegrees(0)
    fp.SetPosition(VECTOR2I(0, 0))
    ax, ay = pad_xy(b, ref, a); bx, by = pad_xy(b, ref, bnum)
    want = math.degrees(math.atan2(pb[1] - pa[1], pb[0] - pa[0]))
    have = math.degrees(math.atan2(by - ay, bx - ax))
    # KiCad orientation is counter-clockwise with y down -> subtract
    fp.SetOrientationDegrees(round((have - want) % 360, 6))
    put(b, ref, pa[0], pa[1], fp.GetOrientationDegrees(), anchor_pad=a)
    got = pad_xy(b, ref, bnum)
    assert abs(math.atan2(got[1] - pa[1], got[0] - pa[0]) - math.radians(want)) < 1e-3, (ref, got, pb)
    return fp


def place(b):
    put(b, "U1", MX, MY)
    assert pad_xy(b, "U1", "2")[0] > MX and pad_xy(b, "U1", "35")[0] < MX   # pin-1 column on the right
    # UART header on the left, rows level with module pins 35/34
    put(b, "J1", 131.5, pad_xy(b, "U1", "35")[1] - 2.0, anchor_pad="1")
    # decoupling at VDD (pin 2), GND pad downward so the +3V3 row stays clear
    put2(b, "C3", "1", (162.5, pad_xy(b, "U1", "2")[1]), "2", (162.5, 99.0))
    # EN network right of the module
    put2(b, "R3", "2", (164.0, 100.5), "1", (175.0, 100.5))
    put2(b, "C4", "1", (164.0, 105.0), "2", (166.0, 105.0))
    put(b, "SW1", 169.5, 104.5, anchor_pad="1")
    # regulator block, bottom left, right under the +5V run down the left edge.
    # rot 180: VI (pin 3) leftmost, towards +5V; VO in the middle goes up into
    # the +3V3 run along the bottom; ADJ leaves under the TO-220 body.
    put(b, "U2", 138.08, 131.5, rot=180, anchor_pad="1")
    assert pad_xy(b, "U2", "3")[0] < pad_xy(b, "U2", "2")[0] < pad_xy(b, "U2", "1")[0]
    put2(b, "C1", "1", (128.5, 127.0), "2", (130.5, 127.0))      # +5V in, on the left-edge run
    put2(b, "C2", "1", (135.54, 125.5), "2", (137.54, 125.5))    # +3V3 out, above VO
    put2(b, "R1", "1", (142.0, 131.5), "2", (152.16, 131.5))     # VO(+3V3) -> ADJ, between the runs
    put2(b, "R2", "1", (155.5, 131.5), "2", (155.5, 121.34))     # ADJ -> GND
    # BOOT + pull-up, IO2 LED under module pin 24
    put(b, "SW2", 129.5, 112.0, anchor_pad="1")
    put2(b, "R4", "2", (141.0, 112.5), "1", (141.0, 122.66))
    io2 = pad_xy(b, "U1", "24")
    put2(b, "R5", "1", (io2[0], 112.5), "2", (io2[0], 122.66))
    put2(b, "D1", "2", (io2[0] + 3.0, 122.66), "1", (io2[0] + 5.54, 122.66))
    # power LED on the right, fed by the +3V3 run going up the right edge
    put2(b, "R6", "1", (177.0, 113.0), "2", (177.0, 123.5))
    put2(b, "D2", "2", (177.0, 126.5), "1", (177.0, 129.5))


def outline(b):
    r = pcbnew.PCB_SHAPE(b)
    r.SetShape(pcbnew.SHAPE_T_RECT)
    r.SetStart(VECTOR2I(FromMM(LEFT), FromMM(TOP))); r.SetEnd(VECTOR2I(FromMM(RIGHT), FromMM(BOTTOM)))
    r.SetLayer(pcbnew.Edge_Cuts); r.SetWidth(FromMM(0.1)); r.SetFilled(False)
    b.Add(r)


def pour(b, net):
    z = pcbnew.ZONE(b)
    z.SetLayer(pcbnew.B_Cu)
    z.SetNetCode(b.FindNet(net).GetNetCode())
    z.SetLocalClearance(FromMM(CLEARANCE))
    z.SetMinThickness(FromMM(0.3))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(FromMM(0.4)); z.SetThermalReliefSpokeWidth(FromMM(0.5))
    ol = z.Outline(); ol.NewOutline()
    for x, y in ((LEFT, TOP), (RIGHT, TOP), (RIGHT, BOTTOM), (LEFT, BOTTOM)):
        ol.Append(FromMM(x), FromMM(y))
    b.Add(z)


def main():
    pro_before = open(PRO).read()
    subprocess.run([sys.executable, os.path.join(HERE, "bootstrap_pcb.py"),
                    os.path.join(HERE, "esp32solder.net"), PCB,
                    "--clearance", str(CLEARANCE), "--track", str(TRACK), "--no-outline"], check=True)
    b = pcbnew.LoadBoard(PCB)
    place(b)
    outline(b)
    pour(b, "GND")
    pcbnew.SaveBoard(PCB, b)
    pro = json.load(open(PRO))
    if "wire_width" not in pro.get("net_settings", {}).get("classes", [{}])[0]:
        open(PRO, "w").write(pro_before)
        print("restored .kicad_pro (SaveBoard dropped the schematic netclass keys)")
    print(f"placed {len(b.GetFootprints())} footprints, board {RIGHT-LEFT:.1f} x {BOTTOM-TOP:.1f} mm")


if __name__ == "__main__":
    main()
