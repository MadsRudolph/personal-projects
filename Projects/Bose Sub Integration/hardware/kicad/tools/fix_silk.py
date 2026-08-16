#!/usr/bin/env python3
"""Nudge footprint reference designators off the silkscreen they collide with.

The kicad-laser-pcb skill ships ``fix_text_collisions.py``, but that one only
looks at standalone ``PCB_TEXT`` on **F.Cu** -- the copper refdes the laser
etches. The warnings left on a hand-placed board are a different animal: they
are footprint *reference fields* on **F.SilkS** landing on a neighbour's silk
outline, or on a pad.

Same idea, different target. Each offending refdes spirals outward in 0.5 mm
steps until it finds a spot clear of every pad, every silk graphic and every
other refdes. Purely cosmetic -- no pad, track or footprint is touched, so the
placement and the netlist are untouched.

    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" tools/fix_silk.py subxo.kicad_pcb
"""
import sys

import pcbnew
from pcbnew import FromMM, VECTOR2I

SILK = FromMM(0.20)      # silk-to-silk breathing room
PAD = FromMM(0.25)       # silk-to-pad, a little more since copper is unforgiving
STEP = FromMM(0.5)
RINGS = 14


def main(path: str) -> int:
    board = pcbnew.LoadBoard(path)

    # Obstacles: every pad, and every piece of silk that is NOT a refdes.
    obstacles = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            bb.Inflate(PAD)
            obstacles.append(bb)
        for item in fp.GraphicalItems():
            if item.GetLayer() == pcbnew.F_SilkS:
                bb = item.GetBoundingBox()
                bb.Inflate(SILK)
                obstacles.append(bb)

    refs = [fp.Reference() for fp in board.GetFootprints()
            if fp.Reference().IsVisible()
            and fp.Reference().GetLayer() == pcbnew.F_SilkS]

    def clear(bb, me):
        if any(bb.Intersects(o) for o in obstacles):
            return False
        for other in refs:
            if other is me:
                continue
            ob = other.GetBoundingBox()
            ob.Inflate(SILK)
            if bb.Intersects(ob):
                return False
        return True

    moved = stuck = 0
    for ref in refs:
        bb = ref.GetBoundingBox()
        bb.Inflate(SILK)
        if clear(bb, ref):
            continue
        home = ref.GetPosition()
        home_rot = ref.GetTextAngle()
        placed = False
        # Try the text as it sits, then turned 90 deg. A rotated refdes has a
        # quite different bounding box and slips into vertical channels that the
        # horizontal one cannot -- which is the difference between fitting in a
        # crowded corner and giving up.
        for rot in (home_rot, pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T)):
            ref.SetTextAngle(rot)
            for ring in range(1, RINGS + 1):
                d = STEP * ring
                # straight up/down first: a refdes reads best above its part
                for dx, dy in ((0, -d), (0, d), (-d, 0), (d, 0),
                               (-d, -d), (d, -d), (-d, d), (d, d)):
                    ref.SetPosition(VECTOR2I(home.x + dx, home.y + dy))
                    nb = ref.GetBoundingBox()
                    nb.Inflate(SILK)
                    if clear(nb, ref):
                        placed = True
                        break
                if placed:
                    break
            if placed:
                break
        if not placed:
            ref.SetTextAngle(home_rot)
        if placed:
            moved += 1
        else:
            ref.SetPosition(home)
            stuck += 1
            print(f"  no free spot for {ref.GetText()} -- left where it was")

    pcbnew.SaveBoard(path, board)
    print(f"fix_silk: moved {moved} reference designators, {stuck} left alone")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
