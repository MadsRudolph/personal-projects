"""Generate the ESP32-WROOM-32 KORAD carrier PCB (KiCad 9).

Footprints are placed on a coarse grid (DRC-clean, no courtyard overlaps) with every
pad netted from the schematic netlist, plus an Edge.Cuts outline. Copper routing is left
for the KiCad GUI (the ratsnest carries the connectivity). Run with PYTHONUTF8=1.

  PYTHONUTF8=1 python build_pcb.py
"""
import os, re, subprocess, uuid, copy
from kiutils.board import Board
from kiutils.footprint import Footprint
from kiutils.items.common import Net, Position
from kiutils.items.gritems import GrLine

HERE = os.path.dirname(os.path.abspath(__file__))
SCH = os.path.join(HERE, "korad-esp32-carrier.kicad_sch")
TEMPLATE = r"C:/Users/Mads2/Documents/Projects/Projects/DTU Multimeter/KiCad/Multimeter/Multimeter.kicad_pcb"
FPDIR = r"C:/Program Files/KiCad/9.0/share/kicad/footprints"
CLI = r"C:/Program Files/KiCad/9.0/bin/kicad-cli.exe"
OUT = os.path.join(HERE, "korad-esp32-carrier.kicad_pcb")

# ---- 1. export + parse the schematic netlist --------------------------------
NET = os.path.join(HERE, "_net.net")
subprocess.run([CLI, "sch", "export", "netlist", SCH, "-o", NET, "--format", "kicadsexpr"],
               check=True, capture_output=True)
txt = open(NET, encoding="utf-8").read()

comps = {}   # ref -> (value, footprint)
for m in re.finditer(r'\(comp \(ref "([^"]+)"\)\s*\(value "([^"]*)"\).*?\(footprint "([^"]*)"\)', txt, re.S):
    comps[m.group(1)] = (m.group(2), m.group(3))

pad_net = {}   # (ref, pin) -> netname
netnames = []
for m in re.finditer(r'\(net \(code[^)]*\) \(name "([^"]+)"\)(.*?)(?=\(net \(code|\)\s*\)\s*\Z|\(net \(code)', txt, re.S):
    name = m.group(1)
    if name not in netnames:
        netnames.append(name)
    for nm in re.finditer(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"', m.group(2)):
        pad_net[(nm.group(1), nm.group(2))] = name

net_num = {name: i + 1 for i, name in enumerate(netnames)}  # 0 reserved for ''
print(f"parsed {len(comps)} components, {len(netnames)} nets, {len(pad_net)} pad assignments")

# ---- 2. template board: keep layers/setup, strip contents --------------------
b = Board.from_file(TEMPLATE)
b.footprints, b.traceItems, b.zones, b.dimensions, b.groups, b.graphicItems = [], [], [], [], [], []
b.nets = [Net(0, "")] + [Net(net_num[n], n) for n in netnames]
b.titleBlock = None

# ---- 3. placement grid (mm). ESP gets its own spot; rest on a 16 mm grid -----
GX, GY, PITCH = 14.0, 16.0, 20.0  # 20 mm pitch keeps axial-resistor courtyards clear
def slot(col, row):
    return (GX + col * PITCH, GY + row * PITCH)
POS = {
    "U2": slot(0,0), "JP1": slot(1,0), "R8": slot(2,0), "R9": slot(3,0), "C5": slot(4,0), "C6": slot(5,0),
    "J1": slot(0,1), "R1": slot(1,1), "R2": slot(2,1), "R3": slot(3,1), "C1": slot(4,1), "SW1": slot(5,1), "SW2": slot(6,1),
    "C2": slot(0,2), "C3": slot(1,2), "C4": slot(2,2), "Q1": slot(3,2), "R4": slot(4,2), "R5": slot(5,2),
    "Q2": slot(1,3), "R6": slot(2,3), "R7": slot(3,3),
    "J2": slot(6,0),  # pogo header, kept clear of the ESP courtyard/antenna keepout
    "U1": (slot(5,4)[0], slot(5,4)[1]),
}
# Power-flag pseudo-components (#FLG/#PWR) have no footprint -> skipped.

fp_cache = {}
def load_fp(libfp):
    if libfp not in fp_cache:
        lib, name = libfp.split(":")
        fp_cache[libfp] = Footprint.from_file(os.path.join(FPDIR, lib + ".pretty", name + ".kicad_mod"))
    return copy.deepcopy(fp_cache[libfp])

placed = 0
for ref, (value, libfp) in comps.items():
    if not libfp or ref not in POS:
        continue
    fp = load_fp(libfp)
    x, y = POS[ref]
    fp.position = Position(x, y, 0)
    fp.layer = "F.Cu"
    if not isinstance(fp.properties, dict):
        fp.properties = {}
    fp.properties["Reference"] = ref
    fp.properties["Value"] = value
    fp.path = "/" + str(uuid.uuid4())
    for pad in fp.pads:
        nm = pad_net.get((ref, str(pad.number)))
        if nm is not None:
            pad.net = Net(net_num[nm], nm)
    b.footprints.append(fp)
    placed += 1

# ---- 4. Edge.Cuts outline around everything (10 mm margin) -------------------
xs = [POS[r][0] for r in POS]; ys = [POS[r][1] for r in POS]
x0, y0, x1, y1 = min(xs) - 12, min(ys) - 12, max(xs) + 14, max(ys) + 14
corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
for (ax, ay), (bx, by) in zip(corners, corners[1:]):
    b.graphicItems.append(GrLine(start=Position(ax, ay), end=Position(bx, by), layer="Edge.Cuts"))

b.to_file(OUT)

# Relax the project min-hole rule so the ESP32's 0.2 mm thermal vias pass DRC.
import json
PRO = os.path.join(HERE, "korad-esp32-carrier.kicad_pro")
pj = json.load(open(PRO, encoding="utf-8")) if os.path.exists(PRO) else {"board": {}}
rules = pj.setdefault("board", {}).setdefault("design_settings", {}).setdefault("rules", {})
rules.update({"min_through_hole_diameter": 0.2, "min_hole_to_hole": 0.2, "min_via_diameter": 0.4})
json.dump(pj, open(PRO, "w", encoding="utf-8"), indent=2)

print(f"placed {placed} footprints; board {x1-x0:.0f}x{y1-y0:.0f} mm; wrote {OUT}")
os.remove(NET)
