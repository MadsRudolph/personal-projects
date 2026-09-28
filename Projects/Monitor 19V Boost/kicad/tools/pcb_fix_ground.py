"""Rework the hand layout's power section so the ground topology follows the
handoff rules (hot loop, input loop, star point).  Run with kpy.py:

    python3 kicad/tools/kpy.py kicad/tools/pcb_fix_ground.py kicad/monitor-boost.kicad_pcb

What it does, in order:
  1. Textually deletes the tracks that walled the ground in (board.Remove()
     segfaults this pcbnew build): all of +12V, /CS, /VOUT, gate and Q2-E, and
     the VCC_F / DRV segments around the old driver position.
  2. Flips C4..C6, C7 and D2 so VOUT sits on top and the minus / GND pads face
     the shunt; moves J2 up to match; moves C2 beside C1 so both bulk caps'
     plus pads are in one +12V pour; C3 sits under J1, fed by an edge stub.
  3. Puts R4 (gate) and R6 (+12V -> VCC_F) horizontally right of R2: their
     bodies straddle the output-return band, one pad either side.  C9 and R3
     move out of the band.
  4. Pours: +12V (J1, C1..C3, L1), SW (as before, notched for D1's cathode),
     VOUT (D1 cathode -> C7, C4..C6, D2, J2 along the top), CS (Q1 source,
     R5, shunt tops).  Two no-track rule areas protect the input and output
     return paths.  CS reaches R14 as one wire link (F.Cu).
  5. Fills, saves, and puts the original .kicad_pro back (SaveBoard resets it).
"""
import os
import re
import shutil
import sys
import tempfile

import pcbnew

PCB = os.path.abspath(sys.argv[1])
PRO = PCB.replace(".kicad_pcb", ".kicad_pro")
MM = pcbnew.FromMM

# -- 1. textual track deletion ------------------------------------------------
DROP_NETS = {"+12V", "/CS", "/VOUT", "Net-(Q1-G)", "Net-(Q2-E)"}
DROP_SEGS = {  # (net, (x1, y1), (x2, y2)) -- either direction
    ("/VCC_F", (139.81, 92.43), (139.81, 73.97)),
    ("/VCC_F", (139.79, 73.97), (139.81, 73.97)),
    ("/VCC_F", (141.13, 72.63), (139.79, 73.97)),
    ("/VCC_F", (144.25, 72.63), (141.13, 72.63)),
    ("/VCC_F", (144.25, 72.63), (147.71, 72.63)),
    ("/VCC_F", (147.71, 72.63), (149.75, 74.67)),
    ("/VCC_F", (149.75, 74.67), (149.75, 76.47)),
    ("/DRV", (147.21, 76.47), (143.89, 76.47)),
    ("/DRV", (143.89, 76.47), (143.89, 80.12)),
    ("/DRV", (143.89, 80.12), (143.79, 80.22)),
    ("/DRV", (143.79, 81.79), (143.79, 80.22)),
    ("/DRV", (144.47, 82.47), (143.79, 81.79)),
    ("/DRV", (147.21, 82.47), (144.47, 82.47)),
}


def near(a, b):
    return abs(a[0] - b[0]) < 0.02 and abs(a[1] - b[1]) < 0.02


def drop(net, s, e):
    if net in DROP_NETS:
        return True
    return any(n == net and ((near(s, a) and near(e, b)) or (near(s, b) and near(e, a)))
               for n, a, b in DROP_SEGS)


text = open(PCB).read()
seg_re = re.compile(r"\t\(segment\n\t\t\(start ([\d.-]+) ([\d.-]+)\)\n\t\t\(end ([\d.-]+) ([\d.-]+)\)\n"
                    r"(?:\t\t.*\n)*?\t\t\(net \"([^\"]*)\"\)\n(?:\t\t.*\n)*?\t\)\n")
dropped = 0


def repl(m):
    global dropped
    s = (float(m.group(1)), float(m.group(2)))
    e = (float(m.group(3)), float(m.group(4)))
    if drop(m.group(5), s, e):
        dropped += 1
        return ""
    return m.group(0)


text = seg_re.sub(repl, text)
want = len(DROP_SEGS)
print(f"deleted {dropped} segments")
tmp = os.path.join(tempfile.mkdtemp(), os.path.basename(PCB))
open(tmp, "w").write(text)
shutil.copy(PRO, tmp.replace(".kicad_pcb", ".kicad_pro"))

# -- 2./3. footprint moves -----------------------------------------------------
b = pcbnew.LoadBoard(tmp)
MOVES = {  # ref: (x, y, rot) -- anchor is pad 1
    "C4": (144.45, 46.15, -90), "C5": (161.95, 46.15, -90), "C6": (179.45, 46.15, -90),
    "C7": (132.95, 46.65, -90),
    "D2": (193.35, 38.29, -90),
    "J2": (202.95, 43.00, -90),
    "C2": (97.00, 56.65, -90),
    "C3": (62.90, 67.40, 0),
    "R4": (142.46, 62.00, 180),
    "R6": (142.46, 70.00, 180),
    "C9": (142.46, 75.00, 180),
    "R3": (147.21, 86.45, 180),
}
for ref, (x, y, r) in MOVES.items():
    fp = b.FindFootprintByReference(ref)
    fp.SetOrientationDegrees(r)
    fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))

# -- tracks --------------------------------------------------------------------
nets = b.GetNetsByName()


def track(net, pts, w, layer=pcbnew.B_Cu):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1)))
        t.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
        t.SetWidth(MM(w))
        t.SetLayer(layer)
        t.SetNet(nets[net])
        b.Add(t)


# gate: Q1.1 -> R5.1 -> under the shunt bodies -> R4.2 (inside the band)
track("Net-(Q1-G)", [(108.45, 41.65), (108.45, 60.0), (110.45, 62.0), (132.30, 62.0)], 1.0)
# +12V to R6.2 (inside), below the gate, above the input-return path
track("+12V", [(104.0, 57.5), (104.0, 70.0), (132.30, 70.0)], 1.5)
# +12V stub down the left edge to C3 (input HF bypass across J1); dead end
track("+12V", [(62.35, 58.5), (62.35, 67.4), (62.90, 67.4)], 1.5)
# driver side of R4: Q2 / Q3 emitters
track("Net-(Q2-E)", [(142.46, 62.0), (152.29, 62.0), (152.29, 76.47), (152.29, 82.47)], 1.0)
# VCC_F: R6.1 -> Q2 collector from above; R6.1 -> C9.1 -> down to the U1 feed line
track("/VCC_F", [(142.46, 70.0), (147.08, 70.0), (149.75, 72.67), (149.75, 76.47)], 1.0)
track("/VCC_F", [(142.46, 70.0), (142.46, 92.43)], 1.0)
# DRV: Q2.3 - Q3.3 - R3.1 (the diagonal to U1.11 is kept from the hand layout)
track("/DRV", [(147.21, 76.47), (147.21, 86.45)], 1.0)
# VOUT sense along the right edge, clear of J2's return pad
track("/VOUT", [(206.40, 45.2), (206.40, 98.36), (204.29, 100.47), (204.29, 103.71),
                (201.55, 106.45), (197.99, 106.45)], 1.5)
track("/VOUT", [(206.40, 63.57), (198.65, 63.57), (189.43, 63.57), (182.29, 70.71),
                (182.29, 79.47)], 1.5)
# CS Kelvin tap: one wire link from the top of R2 to R14 (component side)
track("/CS", [(126.45, 51.65), (129.30, 54.50), (129.30, 122.70), (145.0, 122.70),
              (147.59, 120.11), (147.59, 120.0)], 1.5, pcbnew.F_Cu)

# -- 4. zones ------------------------------------------------------------------
def set_outline(z, pts):
    o = z.Outline()
    o.RemoveAllContours()
    o.NewOutline()
    for x, y in pts:
        o.Append(MM(x), MM(y))


def pour(name, net, prio, pts):
    z = pcbnew.ZONE(b)
    z.SetLayer(pcbnew.B_Cu)
    z.SetNet(nets[net])
    z.SetZoneName(name)
    z.SetAssignedPriority(prio)
    z.SetMinThickness(MM(0.8))
    z.SetLocalClearance(MM(0.85))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    set_outline(z, pts)
    b.Add(z)
    return z


def keepout(name, pts):
    z = pcbnew.ZONE(b)
    z.SetLayer(pcbnew.B_Cu)
    z.SetIsRuleArea(True)
    z.SetZoneName(name)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowZoneFills(False)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    set_outline(z, pts)
    b.Add(z)


zones = {z.GetZoneName(): z for z in b.Zones()}
gnd, sw, strip = zones["GND"], zones["SW"], zones["STRIP"]
gnd.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
# SW: over the top of Q1/D1, notched for Q1's source finger and D1's cathode
sw.SetAssignedPriority(1)
set_outline(sw, [(98.3, 33.0), (128.1, 33.0), (128.1, 42.0), (123.65, 42.0), (123.65, 39.8),
                 (112.4, 39.8), (112.4, 43.3), (98.3, 43.3)])
pour("CS", "/CS", 4, [(112.4, 39.8), (114.5, 39.8), (114.5, 46.8), (121.5, 46.8), (121.5, 49.6),
                      (128.5, 49.6), (128.5, 53.4), (112.4, 53.4)])
pour("VOUT", "/VOUT", 3, [(115.3, 39.8), (123.65, 39.8), (123.65, 42.85), (128.9, 42.85),
                          (128.9, 31.5), (208.5, 31.5), (208.5, 45.6), (199.5, 45.6),
                          (199.5, 48.75), (122.35, 48.75), (122.35, 45.95), (115.3, 45.95)])
pour("+12V", "+12V", 2, [(60.5, 31.5), (97.6, 31.5), (97.6, 46.0), (107.3, 46.0), (107.3, 58.8),
                         (69.2, 58.8), (69.2, 59.6), (60.5, 59.6)])
# output return: C4..C6 / C7 / D2 minus row -> band between R4/R6 pads -> R2.2
strip.SetZoneName("OUT_RETURN")
set_outline(strip, [(131.0, 49.8), (197.0, 49.8), (197.0, 60.4), (141.6, 60.4), (141.6, 79.0),
                    (127.5, 79.0), (127.5, 71.9), (133.95, 71.9), (133.95, 60.4), (131.0, 60.4)])
# input return: J1 / C1..C3 minus -> shunt bottoms
keepout("IN_RETURN", [(63.7, 60.3), (102.4, 60.3), (102.4, 71.9), (127.5, 71.9), (127.5, 84.0),
                      (63.7, 84.0)])

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
shutil.copy(tmp.replace(".kicad_pcb", ".kicad_pro"), PRO)  # SaveBoard rewrote it
print("saved", PCB)
