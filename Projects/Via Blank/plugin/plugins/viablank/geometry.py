"""Where the holes go. Pure geometry -- no pcbnew, so it is testable anywhere.

A uniform lattice puts an obstacle every pitch across the whole board,
including everywhere you will never need one, and the board ends up looking and
behaving like perfboard. Opulo's viagrid does better: a dense ground fence in
the border where it is never in the way, plus a few tight clusters, leaving the
field clear. These are that idea at 190 x 140 mm.

A cluster is not a set of independently routable vias -- at 2.54 mm you cannot
mill an isolation ring between them. It is one local ground terminal: route a
block's ground to its edge and stop.
"""

# --- the blank ------------------------------------------------------------
# SRM-20 operation strokes are 203.2 x 152.4 mm (spindle centre), on a
# 232.2 x 156.6 mm table. 190 x 140 is the largest round size that still leaves
# the spindle ~6 mm of reach past every edge, so the blank never has to be
# positioned precisely and an outline can be cut flush around it if needed.
BLANK_W, BLANK_H = 190.0, 140.0

# The machine itself, for the reference envelope drawn on User.Drawings: how far
# the spindle centre can travel. Bigger than the blank, so it is only the
# binding limit when milling bare stock rather than a blank.
SRM20_X, SRM20_Y = 203.2, 152.4
HOLE = 1.0              # finished hole; takes a standard THT lead
PAD = 1.4               # 0.2 mm annular ring -> what DRC reserves per hole
EDGE_PULLBACK = 0.5     # plane held off the routed edge, as a fab would
OUTLINE_SLOP = 0.5      # Edge.Cuts stroke width counted into the bbox

# Same numbers as the kicad-laser-pcb skill's `cnc` profile and
# KiCad-Autoplace's fabrication.py. 0.8 mm is the endmill diameter, and an
# absolute floor on every copper-to-copper gap.
CLEARANCE, TRACK = 0.85, 1.0
ENDMILL = 0.8

FENCE_INSET = 5.0       # ring held this far in from the routed edge
FENCE_PITCH = 5.08

CLUSTER_PITCH = 2.54    # 3.81 instead would let each hole be isolated singly
ISLAND_MARGIN = 10.0    # keeps clusters clear of the fence

PATTERNS = {
    # 3x3 terminals on a coarse lattice: nowhere on the board is far from one.
    "islands": {
        "shape": "3x3",
        "cells": [(i, j) for i in (-1, 0, 1) for j in (-1, 0, 1)],
        "lattice": 25.4,
        "blurb": "Border fence + 7x5 clusters of 3x3. The default: nowhere is "
                 "more than ~18 mm from ground, ~17 mm of clear channel between "
                 "clusters.",
    },
    # Faithful to viagrid: a few big diamonds at the quarter points.
    "blobs": {
        "shape": "Diamond",
        "cells": [(i, j) for j, w in ((-1, 2), (0, 3), (1, 2))
                  for i in range(-w, w + 1)],
        "lattice": 63.0,
        "blurb": "Border fence + 3 viagrid-style diamonds. Faithful to Opulo's "
                 "own arrangement; sparse at this board size.",
    },
}


def fence_runs():
    """The border ring, as four thin strips.

    Four strips rather than one ring because KiCad-Autoplace's push_apart works
    on bounding boxes: a ring's box is the whole board, which would shove every
    component into the border.
    """
    w, h = BLANK_W / 2 - FENCE_INSET, BLANK_H / 2 - FENCE_INSET
    nx, ny = int(2 * w / FENCE_PITCH), int(2 * h / FENCE_PITCH)
    xs = [-w + i * (2 * w / nx) for i in range(nx + 1)]
    # corners belong to the horizontal strips, so drop them here
    ys = [-h + j * (2 * h / ny) for j in range(ny + 1)][1:-1]
    return {"Fence_H": ([(round(x, 3), 0.0) for x in xs],
                        [(0.0, -h), (0.0, h)]),
            "Fence_V": ([(0.0, round(y, 3)) for y in ys],
                        [(-w, 0.0), (w, 0.0)])}


def cluster_run(pattern):
    """One cluster footprint, and the lattice of places it gets dropped."""
    spec = PATTERNS[pattern]
    lat = spec["lattice"]
    cells = [(round(i * CLUSTER_PITCH, 3), round(j * CLUSTER_PITCH, 3))
             for i, j in spec["cells"]]

    def centres(span):
        n = int(span / lat) + 1
        n = n if n % 2 else n - 1      # odd: symmetric about the blank centre
        return [(k - (n - 1) / 2.0) * lat for k in range(n)]

    at = [(cx, cy)
          for cx in centres(BLANK_W - 2 * ISLAND_MARGIN)
          for cy in centres(BLANK_H - 2 * ISLAND_MARGIN)]
    return {"Cluster_" + spec["shape"]: (cells, at)}


def runs(pattern):
    """{footprint name: (pad offsets, instance positions)} for a pattern.

    Positions are relative to the blank centre, so the caller decides where the
    blank sits on the target board.
    """
    r = dict(fence_runs())
    r.update(cluster_run(pattern))
    return r


# Not a pattern: draw the reference envelope and nothing else. For a board whose
# placement is already done and does not want holes, but still needs to show how
# far it can grow and still fit the machine.
OUTLINES = "outlines"

# Dialog order; the first is the default.
MODES = ["islands", "blobs", OUTLINES]


def hole_count(pattern):
    return sum(len(pts) * len(at) for pts, at in runs(pattern).values())


def describe(mode):
    if mode == OUTLINES:
        return ("outlines  -  no holes, no plane.  Just the via blank and "
                "SRM-20 reference rectangles on User.Drawings, so you can see "
                "how far the board can grow.")
    return "%s  -  %d holes.  %s" % (mode, hole_count(mode),
                                     PATTERNS[mode]["blurb"])
