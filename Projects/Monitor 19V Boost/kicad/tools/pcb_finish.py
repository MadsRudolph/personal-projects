#!/usr/bin/env python3
"""Close the links FreeRouting left open and write the production board.

    python3 kicad/tools/kpy.py kicad/tools/pcb_finish.py <routed.kicad_pcb>

FreeRouting (place_route.py, best ladder rung) closes nearly everything on this
placement.  What it leaves is listed in LINKS below and closed here by a small
grid search that keeps 0.85 mm (the mill's floor) from every other net's pads
and tracks, stays out of the two no-track strips (STRIP, OUTGND) and out of the
SW pour.  Then the pours are refilled.

One link is deliberately NOT on the copper side:

    CS -> R14   one insulated wire link on the component side.  It is forced:
                CS starts at the shunt, inside the power section, and CL+ is on
                U1's bottom row, walled off by the gate-drive and VCC_F runs.
                CS is a 50 mOhm node, so the wire picks up little, and R14/C17
                filter it at the pin.  Drawn as F.Cu, this process's convention
                for a wire bridge; the grid search keeps it clear of every pad.

Writes kicad/monitor-boost.kicad_pcb.
"""
import heapq
import math
import sys
from pathlib import Path

import pcbnew
from pcbnew import FromMM, ToMM, VECTOR2I

OX, OY = 20.0, 20.0
W, H = 148.0, 118.0
CLR = 0.85
STEP = 0.25
OUT = Path(__file__).resolve().parent.parent / "monitor-boost.kicad_pcb"

# (net, (ref, pad), (ref, pad), width mm, layer)
LINKS = [
    ("Net-(Q1-G)", ("R5", "1"), ("R4", "2"), 1.0, "B"),
    ("+12V", ("C2", "1"), ("R6", "2"), 1.5, "B"),
    ("/CS", ("R2", "1"), ("R14", "1"), 1.0, "F"),        # the wire link
]


def P(x, y):
    return VECTOR2I(FromMM(OX + x), FromMM(OY + y))


def loc(v):
    return (ToMM(v.x) - OX, ToMM(v.y) - OY)


def seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def pad_of(board, ref, num):
    fp = board.FindFootprintByReference(ref)
    for p in fp.Pads():
        if p.GetNumber() == num:
            return p
    raise SystemExit(f"no pad {ref}.{num}")


def obstacles(board, net, layer, w):
    """Other-net copper as circles (pads) and capsules (tracks), plus the
    rectangles a track may not enter."""
    circles, capsules, rects = [], [], []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net:
                continue
            sz = p.GetSize()
            r = max(ToMM(sz.x), ToMM(sz.y)) / 2
            circles.append((loc(p.GetPosition()), r + CLR + w / 2))
    if layer == "B":
        for t in board.GetTracks():
            if t.GetNetname() == net or t.GetLayer() != pcbnew.B_Cu:
                continue
            capsules.append((loc(t.GetStart()), loc(t.GetEnd()),
                             ToMM(t.GetWidth()) / 2 + CLR + w / 2))
        for z in board.Zones():
            if z.GetIsRuleArea() or (z.GetNetname() not in ("GND",) and z.GetNetname() != net):
                bb = z.GetBoundingBox()
                x0, y0 = loc(VECTOR2I(bb.GetLeft(), bb.GetTop()))
                x1, y1 = loc(VECTOR2I(bb.GetRight(), bb.GetBottom()))
                rects.append((x0 - w / 2, y0 - w / 2, x1 + w / 2, y1 + w / 2))
    return circles, capsules, rects


def search(board, net, a, b, w, layer):
    circles, capsules, rects = obstacles(board, net, layer, w)
    m = 1.5 + w / 2

    def free(x, y):
        if x < m or y < m or x > W - m or y > H - m:
            return False
        for (cx, cy), r in circles:
            if (x - cx) ** 2 + (y - cy) ** 2 < r * r:
                return False
        for s, e, r in capsules:
            if seg_dist((x, y), s, e) < r:
                return False
        for x0, y0, x1, y1 in rects:
            if x0 <= x <= x1 and y0 <= y <= y1:
                return False
        return True

    k = lambda p: (round(p[0] / STEP), round(p[1] / STEP))   # noqa: E731
    s, g = k(a), k(b)
    near_end = lambda q: (math.hypot(q[0] - s[0], q[1] - s[1]) * STEP < 1.2
                          or math.hypot(q[0] - g[0], q[1] - g[1]) * STEP < 1.2)   # noqa: E731
    openq, came, cost = [(0.0, s)], {s: None}, {s: 0.0}
    moves = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    while openq:
        _, cur = heapq.heappop(openq)
        if cur == g:
            break
        for dx, dy in moves:
            nk = (cur[0] + dx, cur[1] + dy)
            if not near_end(nk) and not free(nk[0] * STEP, nk[1] * STEP):
                continue
            c = cost[cur] + math.hypot(dx, dy) * STEP + (0.02 if (dx and dy) else 0)
            if c < cost.get(nk, 1e9):
                cost[nk], came[nk] = c, cur
                heapq.heappush(openq, (c + math.hypot(nk[0] - g[0], nk[1] - g[1]) * STEP, nk))
    if g not in came:
        return None, None
    path, q = [], g
    while q is not None:
        path.append((q[0] * STEP, q[1] * STEP))
        q = came[q]
    path.reverse()
    pts = [path[0]]
    for p0, p1, p2 in zip(path, path[1:], path[2:]):
        if (p1[0] - p0[0], p1[1] - p0[1]) != (p2[0] - p1[0], p2[1] - p1[1]):
            pts.append(p1)
    pts.append(path[-1])
    pts[0], pts[-1] = a, b
    return pts, cost[g]


def add(board, net, pts, w, layer):
    n = board.FindNet(net)
    for p0, p1 in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(P(*p0))
        t.SetEnd(P(*p1))
        t.SetWidth(FromMM(w))
        t.SetLayer(pcbnew.F_Cu if layer == "F" else pcbnew.B_Cu)
        t.SetNet(n)
        board.Add(t)


def main(routed, links=LINKS):
    board = pcbnew.LoadBoard(routed)
    for net, (r1, p1), (r2, p2), w, layer in links:
        a = loc(pad_of(board, r1, p1).GetPosition())
        b = loc(pad_of(board, r2, p2).GetPosition())
        pts, L = search(board, net, a, b, w, layer)
        if pts is None:
            raise SystemExit(f"no {layer}.Cu path for {net} {r1}.{p1} -> {r2}.{p2}")
        add(board, net, pts, w, layer)
        side = "wire link (component side)" if layer == "F" else "B.Cu"
        print(f"{net:14s} {r1}.{p1} -> {r2}.{p2}: {L:5.1f} mm, {len(pts) - 1} segments, {side}")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    # pcbnew.SaveBoard rewrites the sibling .kicad_pro with default netclasses
    # (0.2 mm), silently disarming DRC -- keep the real one.
    pro = OUT.with_suffix('.kicad_pro')
    keep = pro.read_text() if pro.exists() else None
    pcbnew.SaveBoard(str(OUT), board)
    if keep is not None:
        pro.write_text(keep)
    print("wrote", OUT)


if __name__ == "__main__":
    main(sys.argv[1])
