#!/usr/bin/env python3
"""Bootstrap esp32node.kicad_pcb from the exported netlist (Linux port of the
kicad-laser-pcb pcb_build.py step, which hardcodes Windows library paths).

Single-sided SMD board: the only copper layer is B.Cu, so every SMD footprint is
flipped to the bottom (the copper side). Through-hole headers stay on top and
solder on B.Cu. Parts land on a loose grid inside a temporary outline;
placement proper happens afterwards.

Run with the system python3 (pcbnew is importable on this machine):
    python3 bootstrap_pcb.py esp32node.net esp32node.kicad_pcb [--clearance C --track W]
"""
import argparse
import os
import sys
import sexpdata
from sexpdata import Symbol
import pcbnew
from pcbnew import VECTOR2I, FromMM

FPLIB = "/usr/share/kicad/footprints"


def netlist(path):
    t = sexpdata.loads(open(path, encoding="utf-8").read())
    v = lambda x: x.value() if isinstance(x, Symbol) else x
    head = lambda n: v(n[0]) if isinstance(n, list) and n else None
    comps, nets = {}, {}
    for it in t:
        if head(it) == "components":
            for c in it[1:]:
                f = {head(x): x[1] for x in c[1:] if isinstance(x, list) and len(x) > 1}
                comps[str(f["ref"])] = {"value": str(f.get("value", "")), "fp": str(f["footprint"]), "pads": {}}
        elif head(it) == "nets":
            for n in it[1:]:
                name = next(str(x[1]) for x in n[1:] if head(x) == "name")
                for node in (x for x in n[1:] if head(x) == "node"):
                    f = {head(x): x[1] for x in node[1:] if isinstance(x, list) and len(x) > 1}
                    comps[str(f["ref"])]["pads"][str(f["pin"])] = name
                nets[name] = None
    return comps, list(nets)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("net"); ap.add_argument("out")
    ap.add_argument("--size", default="80x70", help="temporary outline WxH mm")
    ap.add_argument("--clearance", type=float, required=True)
    ap.add_argument("--track", type=float, required=True)
    ap.add_argument("--no-outline", action="store_true", help="caller draws Edge.Cuts itself")
    a = ap.parse_args()
    comps, nets = netlist(a.net)
    board = pcbnew.NewBoard(a.out)
    netmap = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name); board.Add(ni); netmap[name] = ni

    W, H = (float(x) for x in a.size.split("x"))
    X0 = Y0 = 20.0
    col = row = 0
    for ref in sorted(comps, key=lambda r: (r.rstrip("0123456789"), int(r.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ") or 0))):
        c = comps[ref]
        lib, name = c["fp"].split(":")
        # project library first (fp-lib-table's ${KIPRJMOD}/<lib>.pretty), then stock
        here = os.path.dirname(os.path.abspath(a.out))
        base = here if os.path.isdir(os.path.join(here, lib + ".pretty")) else FPLIB
        fp = pcbnew.FootprintLoad(os.path.join(base, lib + ".pretty"), name)
        if fp is None:
            raise SystemExit(f"footprint not found: {c['fp']}")
        fp.SetReference(ref); fp.SetValue(c["value"])
        board.Add(fp)
        for pad in fp.Pads():
            net = c["pads"].get(pad.GetNumber())
            if net:
                pad.SetNet(netmap[net])
        if c["pads"] and all(p.GetNetCode() == 0 for p in fp.Pads()):
            raise SystemExit(f"{ref}: no pad got a net -- pin/pad number mismatch")
        # Any SMD pad means the part lives on the copper side. The USB-C
        # receptacle has plated shell legs as well, and still belongs there.
        smd = any(p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD for p in fp.Pads())
        if smd:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        fp.SetPosition(VECTOR2I(FromMM(X0 + 5 + col * 9), FromMM(Y0 + 5 + row * 9)))
        col += 1
        if col * 9 > W - 10:
            col, row = 0, row + 1

    rect = pcbnew.PCB_SHAPE(board)
    rect.SetShape(pcbnew.SHAPE_T_RECT)
    rect.SetStart(VECTOR2I(FromMM(X0), FromMM(Y0)))
    rect.SetEnd(VECTOR2I(FromMM(X0 + W), FromMM(Y0 + H)))
    rect.SetLayer(pcbnew.Edge_Cuts); rect.SetWidth(FromMM(0.1)); rect.SetFilled(False)
    if not a.no_outline:
        board.Add(rect)

    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    nc = board.GetAllNetClasses()["Default"]
    nc.SetTrackWidth(FromMM(a.track)); nc.SetClearance(FromMM(a.clearance))
    # Link each footprint to its library and schematic symbol (relink_pcb.py);
    # without it KiCad treats every part as unrelated to the schematic.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import relink_pcb
    relink_pcb.relink(board, relink_pcb.components(a.net))
    pcbnew.SaveBoard(a.out, board)
    print(f"wrote {a.out}: {len(comps)} footprints, {len(nets)} nets, {W:.0f}x{H:.0f} mm outline")


if __name__ == "__main__":
    main()
