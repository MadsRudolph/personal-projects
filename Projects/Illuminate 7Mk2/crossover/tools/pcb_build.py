#!/usr/bin/env python3
"""
Build illuminate7mk2-crossover.kicad_pcb from the schematic's netlist and place it.

Single-sided, through-hole, CNC isolation-milled (copper on B.Cu). Placement is
a fixed floorplan that follows the signal flow of the schematic, packed from the
footprints' real courtyard sizes -- so when the provisional footprints are swapped
for measured ones, re-running this script re-packs the board and re-sizes the
outline. Routing is left to the user.

    kicad-cli sch export netlist --format kicadsexpr -o /tmp/xo.net illuminate7mk2-crossover.kicad_sch
    python3 ~/.claude/skills/kicad-laser-pcb/scripts/pcb_netlist_json.py /tmp/xo.net /tmp/xo.json
    python3 tools/pcb_build.py /tmp/xo.json illuminate7mk2-crossover.kicad_pcb

Floorplan (flow left -> right, margin/gap in mm below):

    row A  L101 pads | C101/R101/R102 | C102/C103 | L102 pads | C104/C105 | J2   tweeter
    row C  J1 over R201+R202 | C201..C205 (woofer tank caps) | L201 pads         input + woofer tank
    row B  L202 pads | C206/C207 | J3                                            woofer

The coils are NOT on the board (mill envelope is 203 x 152 mm): only their lead
pads are, at the edges, and the coil bodies overhang or sit beside the board.
Keep the bodies apart from each other when mounting them.
"""
import json, os, sys
import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
STOCK = "/usr/share/kicad/footprints"
LIBS = {"crossover": os.path.join(PROJ, "lib", "crossover.pretty")}

MARGIN = 4.0      # courtyard to Edge.Cuts
GAP = 4.0         # courtyard to courtyard (1 mm track + 2 x 0.85 clearance fits)
ROW_GAP = 4.0
CLEARANCE = 0.85  # cnc profile, 0.8 mm end mill
TRACK = 2.0       # default track: crossover carries amps, 1.0 is the process minimum
HOLE_INSET = 6.0  # M4 mounting holes, centre from each corner

# ---------------------------------------------------------------- footprints
def load_fp(fpid):
    lib, name = fpid.split(":")
    d = LIBS.get(lib) or os.path.join(STOCK, lib + ".pretty")
    fp = pcbnew.FootprintLoad(d, name)
    if fp is None:
        raise SystemExit(f"footprint not found: {fpid}")
    return fp

def crt_size(fp, rot):
    """Courtyard (w, h) in mm after rotation, from the footprint's own F.CrtYd."""
    fp.SetOrientationDegrees(rot)
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    if bb.GetWidth() == 0:
        bb = fp.GetBoundingBox(False)
    return ToMM(bb.GetWidth()), ToMM(bb.GetHeight())

def put(fp, cx, cy, rot):
    """Place the footprint so its COURTYARD centre lands at (cx, cy)."""
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(VECTOR2I(FromMM(cx), FromMM(cy)))
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    if bb.GetWidth() == 0:
        bb = fp.GetBoundingBox(False)
    c = bb.GetCenter()
    p = fp.GetPosition()
    fp.SetPosition(VECTOR2I(p.x + (FromMM(cx) - c.x), p.y + (FromMM(cy) - c.y)))

# ---------------------------------------------------------------- packer
# A layout node is ("h", [nodes]) / ("v", [nodes]) / (ref, rot). h packs left
# to right and centres children vertically; v packs top to bottom and centres
# children horizontally. Sizes come from the real courtyards.
def size(node, fps):
    if isinstance(node, tuple) and node[0] in ("h", "v"):
        kids = [size(k, fps) for k in node[1]]
        if node[0] == "h":
            return sum(w for w, _ in kids) + GAP * (len(kids) - 1), max(h for _, h in kids)
        return max(w for w, _ in kids), sum(h for _, h in kids) + GAP * (len(kids) - 1)
    ref, rot = node
    return crt_size(fps[ref], rot)

def place(node, fps, x0, y0, out):
    """Place node with its top-left at (x0, y0). Returns (w, h)."""
    w, h = size(node, fps)
    if isinstance(node, tuple) and node[0] in ("h", "v"):
        cur = x0 if node[0] == "h" else y0
        for k in node[1]:
            kw, kh = size(k, fps)
            if node[0] == "h":
                place(k, fps, cur, y0 + (h - kh) / 2, out)
                cur += kw + GAP
            else:
                place(k, fps, x0 + (w - kw) / 2, cur, out)
                cur += kh + GAP
    else:
        ref, rot = node
        out[ref] = (x0 + w / 2, y0 + h / 2, rot)
    return w, h

# Terminal blocks: rot 90 puts the pin row vertical so the block sits flat against
# a left/right edge. Which face the wire enters from is a property of the actual
# block -- check it on the part and flip 90 <-> 270 if it faces inwards.
#
# Coils are OFF-BOARD: only their lead pads (L_OffBoard_P10.16mm) are placed, at
# the board edges so the coil body can overhang or sit on the enclosure beside
# it. L101 left edge, L201 right edge, L202 left edge, L102 top-middle.
ROW_A = ("h", [("L101", 90),
               ("v", [("C101", 0), ("R101", 0), ("R102", 0)]),
               ("v", [("C102", 0), ("C103", 0)]),
               ("L102", 0),
               ("v", [("C104", 0), ("C105", 0)]),
               ("J2", 90)])
ROW_C = ("h", [("v", [("J1", 270), ("h", [("R201", 90), ("R202", 90)])]),
               ("h", [("C201", 90), ("C202", 90), ("C203", 90), ("C204", 90), ("C205", 90)]),
               ("L201", 90)])
ROW_B = ("h", [("L202", 90),
               ("v", [("C206", 0), ("C207", 0)]),
               ("J3", 90)])
FLUSH_RIGHT = ("J2", "L201", "J3")   # pushed to the right margin after packing
ROWS = [ROW_A, ROW_C, ROW_B]

# ---------------------------------------------------------------- build
def main(jsonf, outf):
    data = json.loads(open(jsonf, encoding="utf-8").read())
    board = pcbnew.NewBoard(outf)

    netmap = {}
    for name in data["nets"]:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netmap[name] = ni

    fps = {}
    for c in data["components"]:
        fp = load_fp(c["footprint"])
        fp.SetReference(c["ref"])
        fp.SetValue(c["value"] or "")
        board.Add(fp)
        for pad in fp.Pads():
            net = c["pads"].get(pad.GetNumber())
            if net:
                pad.SetNet(netmap[net])
        if c["pads"] and all(p.GetNetCode() == 0 for p in fp.Pads()):
            raise SystemExit(f"{c['ref']}: no pad got a net")
        fps[c["ref"]] = fp
    missing = set(fps) - {r for row in ROWS for r in refs_in(row)}
    if missing:
        raise SystemExit(f"floorplan does not mention: {sorted(missing)}")

    # pack the rows, widest row sets the board width; rows are left-aligned
    pos = {}
    y = MARGIN
    widths = []
    for row in ROWS:
        w, h = place(row, fps, MARGIN, y, pos)
        widths.append(w)
        y += h + ROW_GAP
    W = max(widths) + 2 * MARGIN
    H = y - ROW_GAP + MARGIN
    # right-edge parts: push flush to the right margin
    for ref in FLUSH_RIGHT:
        cx, cy, rot = pos[ref]
        w, _ = crt_size(fps[ref], rot)
        pos[ref] = (W - MARGIN - w / 2, cy, rot)
    for ref, (cx, cy, rot) in pos.items():
        put(fps[ref], cx, cy, rot)
    # a short bottom row can leave a part under a bottom corner hole: drop the
    # bottom edge until both bottom holes clear every courtyard by 1 mm
    hole_r = crt_size(load_fp("MountingHole:MountingHole_4.3mm_M4_DIN965"), 0)[0] / 2
    for hx in (HOLE_INSET, W - HOLE_INSET):
        for fp in fps.values():
            bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
            if ToMM(bb.GetLeft()) < hx + hole_r and ToMM(bb.GetRight()) > hx - hole_r:
                H = max(H, ToMM(bb.GetBottom()) + 1.0 + hole_r + HOLE_INSET)

    # outline
    def line(x1, y1, x2, y2):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(VECTOR2I(FromMM(x1), FromMM(y1)))
        s.SetEnd(VECTOR2I(FromMM(x2), FromMM(y2)))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(FromMM(0.1))
        board.Add(s)
    line(0, 0, W, 0); line(W, 0, W, H); line(W, H, 0, H); line(0, H, 0, 0)

    # M4 mounting holes in the corners (enclosure insert positions still unknown)
    for i, (hx, hy) in enumerate([(HOLE_INSET, HOLE_INSET), (W - HOLE_INSET, HOLE_INSET),
                                  (HOLE_INSET, H - HOLE_INSET), (W - HOLE_INSET, H - HOLE_INSET)], 1):
        h = load_fp("MountingHole:MountingHole_4.3mm_M4_DIN965")
        h.SetReference(f"H{i}")
        h.SetValue("M4")
        board.Add(h)
        h.SetPosition(VECTOR2I(FromMM(hx), FromMM(hy)))
        h.SetLocked(True)

    # netclass / design rules: the CNC profile
    ds = board.GetDesignSettings()
    ds.m_MinClearance = FromMM(CLEARANCE)
    ds.m_TrackMinWidth = FromMM(1.0)
    ds.m_CopperEdgeClearance = FromMM(1.0)
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(FromMM(CLEARANCE))
    nc.SetTrackWidth(FromMM(TRACK))
    nc.SetViaDiameter(FromMM(2.0)); nc.SetViaDrill(FromMM(1.0))
    ds.SetCopperLayerCount(2)
    ds.m_SolderMaskMinWidth = 0

    # GND pour on the copper side: the return for both drivers routes itself
    z = pcbnew.ZONE(board)
    z.SetLayer(pcbnew.B_Cu)
    z.SetNet(netmap["GND"])
    z.SetZoneName("GND")
    z.SetLocalClearance(FromMM(CLEARANCE))
    z.SetMinThickness(FromMM(1.0))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    ol = z.Outline()
    ol.NewOutline()
    for x, y2 in [(0, 0), (W, 0), (W, H), (0, H)]:
        ol.Append(FromMM(x), FromMM(y2))
    board.Add(z)

    pcbnew.SaveBoard(outf, board)
    print(f"wrote {outf}: {len(fps)} parts, outline {W:.1f} x {H:.1f} mm, rows {[round(w,1) for w in widths]}")
    for ref, (cx, cy, rot) in sorted(pos.items()):
        print(f"  {ref:5s} ({cx:6.1f}, {cy:6.1f}) rot {rot}")

def refs_in(node):
    if isinstance(node, tuple) and node[0] in ("h", "v"):
        return [r for k in node[1] for r in refs_in(k)]
    return [node[0]]

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
