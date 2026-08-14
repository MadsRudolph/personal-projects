"""Prepare subxo.kicad_pcb for KiCad-Autoplace.

The app needs three things that "Update PCB from Schematic" does not create:
  1. an Edge.Cuts outline -- it IS the placement boundary,
  2. a GND copper pour, so the router treats GND as a plane instead of routing
     it as traces (on a single-sided board that is the difference between a
     routable board and a pile of wire bridges),
  3. locked footprints for anything deliberately hand-placed (none here -- the
     whole board is up for placement).

Idempotent: re-running replaces the outline and the pour rather than stacking
duplicates. Writes a timestamped backup first.

Run with KiCad's own python:
  & "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" tools\\prep_board.py
"""

import shutil
import sys
import time
from pathlib import Path

import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "subxo.kicad_pcb"

BOARD_MM = 100.0          # 100 x 100 outline
CLEARANCE_MM = 0.85       # cnc fabrication profile
POUR_INSET_MM = 0.5       # keep the pour inside the edge cuts


def main() -> int:
    backup = PCB.with_suffix(f".kicad_pcb.bak_{time.strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(PCB, backup)
    print(f"backup: {backup.name}")

    board = pcbnew.LoadBoard(str(PCB))

    # --- drop any previous outline / pour so this stays idempotent ----------
    for d in list(board.GetDrawings()):
        if d.GetLayer() == pcbnew.Edge_Cuts:
            board.Remove(d)
    for z in list(board.Zones()):
        board.Remove(z)

    # --- centre the outline on the footprint cluster ------------------------
    # Placing it where the parts already are keeps the diff small and means
    # nothing starts outside the boundary.
    xs, ys = [], []
    for fp in board.GetFootprints():
        bb = fp.GetBoundingBox(False, False)
        xs += [ToMM(bb.GetLeft()), ToMM(bb.GetRight())]
        ys += [ToMM(bb.GetTop()), ToMM(bb.GetBottom())]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    x0, y0 = round(cx - BOARD_MM / 2, 2), round(cy - BOARD_MM / 2, 2)
    x1, y1 = round(x0 + BOARD_MM, 2), round(y0 + BOARD_MM, 2)
    print(f"parts bbox: x {min(xs):.1f}..{max(xs):.1f}  y {min(ys):.1f}..{max(ys):.1f}")
    print(f"outline   : ({x0}, {y0}) .. ({x1}, {y1})  = {BOARD_MM:.0f} x {BOARD_MM:.0f} mm")

    rect = pcbnew.PCB_SHAPE(board)
    rect.SetShape(pcbnew.SHAPE_T_RECT)
    rect.SetStart(VECTOR2I(FromMM(x0), FromMM(y0)))
    rect.SetEnd(VECTOR2I(FromMM(x1), FromMM(y1)))
    rect.SetLayer(pcbnew.Edge_Cuts)
    rect.SetWidth(FromMM(0.1))
    rect.SetFilled(False)
    board.Add(rect)

    # --- GND pour on B.Cu (the etched/milled side) --------------------------
    gnd = None
    for name in ("/GND", "GND"):
        n = board.FindNet(name)
        if n is not None and n.GetNetCode() != 0:
            gnd = n
            break
    if gnd is None:
        print("ERROR: no GND net on this board", file=sys.stderr)
        return 1

    z = pcbnew.ZONE(board)
    z.SetLayer(pcbnew.B_Cu)
    z.SetNetCode(gnd.GetNetCode())
    chain = pcbnew.SHAPE_LINE_CHAIN()
    i = POUR_INSET_MM
    for px, py in [(x0 + i, y0 + i), (x1 - i, y0 + i), (x1 - i, y1 - i), (x0 + i, y1 - i)]:
        chain.Append(FromMM(px), FromMM(py))
    chain.SetClosed(True)
    z.Outline().AddOutline(chain)
    z.SetLocalClearance(FromMM(CLEARANCE_MM))
    z.SetMinThickness(FromMM(0.25))
    z.SetFillMode(pcbnew.ZONE_FILL_MODE_POLYGONS)
    board.Add(z)

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(PCB), board)

    print(f"GND pour  : B.Cu, net '{gnd.GetNetname()}', clearance {CLEARANCE_MM} mm")
    print(f"saved     : {PCB.name}  ({len(list(board.GetFootprints()))} footprints, "
          f"{len(list(board.Zones()))} zone)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
