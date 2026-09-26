#!/usr/bin/env python3
"""Laser production files for esp32solder.kicad_pcb (xTool F1 Ultra, XCS).

Writes to production/:
  esp32solder_copper_negative_MIRRORED.dxf
      Copper to REMOVE: board outline minus all B.Cu copper (pads, tracks, the
      GND pour), with every drill hole added back as an ablated dot so it is
      easy to centre the drill. Closed R12 polylines, mm, fill even-odd: this
      is the same structure as the test coupon that came out perfectly.
      Engrave with the `Traces` preset.
  esp32solder_drill_outline_MIRRORED.dxf
      Hole circles (layer HOLES) and the board outline (layer OUTLINE) for the
      `Cut/Drill` vector preset.

Both are ALREADY MIRRORED to the copper side (the side that faces the laser),
so do NOT mirror them again in XCS. Check: the copper text "ESP32 TEST"
must read normally in the XCS preview. If it reads backwards, something
mirrored it twice.

Run:  PYTHONPATH=tools/pyshim python3 export_laser.py
"""
import math
import os
import pcbnew
from pcbnew import ToMM

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "esp32solder.kicad_pcb")
OUT = os.path.join(HERE, "production")


def polys(ps):
    """SHAPE_POLY_SET -> [[outline_pts, hole_pts...], ...] in mm."""
    out = []
    for i in range(ps.OutlineCount()):
        rings = [ps.Outline(i)] + [ps.Hole(i, h) for h in range(ps.HoleCount(i))]
        out.append([[(ToMM(r.CPoint(k).x), ToMM(r.CPoint(k).y)) for k in range(r.PointCount())] for r in rings])
    return out


def dxf(layers, mirror_x):
    """layers: name -> list of closed rings. R12 POLYLINEs, mm, y-up."""
    o = ["0", "SECTION", "2", "HEADER", "9", "$INSUNITS", "70", "4", "0", "ENDSEC",
         "0", "SECTION", "2", "TABLES", "0", "TABLE", "2", "LAYER", "70", str(len(layers))]
    for i, name in enumerate(layers):
        o += ["0", "LAYER", "2", name, "70", "0", "62", str(i + 1), "6", "CONTINUOUS"]
    o += ["0", "ENDTAB", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
    n = 0
    for name, rings in layers.items():
        for ring in rings:
            o += ["0", "POLYLINE", "8", name, "66", "1", "70", "1"]
            for x, y in ring:
                xx = (mirror_x - x) if mirror_x is not None else x
                o += ["0", "VERTEX", "8", name, "10", f"{xx:.4f}", "20", f"{-y:.4f}"]
            o += ["0", "SEQEND", "8", name]
            n += 1
    o += ["0", "ENDSEC", "0", "EOF"]
    return "\n".join(o) + "\n", n


def circle(cx, cy, r, seg=48):
    return [(cx + r * math.cos(2 * math.pi * k / seg), cy + r * math.sin(2 * math.pi * k / seg)) for k in range(seg)]


def main():
    os.makedirs(OUT, exist_ok=True)
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    outline = pcbnew.SHAPE_POLY_SET()
    assert b.GetBoardPolygonOutlines(outline, False), "no closed Edge.Cuts outline"
    copper = pcbnew.SHAPE_POLY_SET()
    b.ConvertBrdLayerToPolygonalContours(pcbnew.B_Cu, copper)
    copper.Simplify()
    holes = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.HasHole():
                d = ToMM(min(p.GetDrillSize().x, p.GetDrillSize().y))
                holes.append((ToMM(p.GetPosition().x), ToMM(p.GetPosition().y), d / 2))
    hole_set = pcbnew.SHAPE_POLY_SET()
    for x, y, r in holes:
        hole_set.NewOutline()
        for px, py in circle(x, y, r):
            hole_set.Append(pcbnew.FromMM(px), pcbnew.FromMM(py))
    neg = pcbnew.SHAPE_POLY_SET(outline)
    neg.BooleanSubtract(copper)
    neg.BooleanAdd(hole_set)
    neg.Simplify()
    bb = b.GetBoardEdgesBoundingBox()
    mx = ToMM(bb.GetLeft()) + ToMM(bb.GetRight())     # mirror about the board's vertical centreline
    rings = [r for poly in polys(neg) for r in poly]
    txt, n = dxf({"ABLATE": rings}, mx)
    open(os.path.join(OUT, "esp32solder_copper_negative_MIRRORED.dxf"), "w").write(txt)
    edge = [r for poly in polys(outline) for r in poly]
    txt, m = dxf({"HOLES": [circle(x, y, r) for x, y, r in holes], "OUTLINE": edge}, mx)
    open(os.path.join(OUT, "esp32solder_drill_outline_MIRRORED.dxf"), "w").write(txt)
    sizes = sorted({round(2 * r, 2) for _, _, r in holes})
    print(f"negative: {n} closed rings; drill: {len(holes)} holes {sizes} mm + outline "
          f"{ToMM(bb.GetWidth()):.1f} x {ToMM(bb.GetHeight()):.1f} mm")


if __name__ == "__main__":
    main()
