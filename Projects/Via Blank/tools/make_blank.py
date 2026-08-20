#!/usr/bin/env python3
"""Generate the fabrication templates: one full-size board per pattern.

The KiCad plugin is the everyday path -- this exists to produce the boards you
actually send to the fab, at full blank size, plus a .pretty for anyone who
wants to place the footprints by hand. Geometry and the merge itself live in
``plugin/plugins/viablank`` so there is one source of truth.

Run with KiCad's own python:
  & "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" tools\\make_blank.py
"""
import os
import sys

import pcbnew
from pcbnew import VECTOR2I, FromMM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "plugin", "plugins"))

from viablank import geometry as g                           # noqa: E402
from viablank import merge as m                              # noqa: E402

ORIGIN = 20.0           # board outline origin on the sheet
LIBDIR = os.path.join(ROOT, "lib", "via_blank.pretty")
TPLDIR = os.path.join(ROOT, "template")


def add_outline(board):
    rect = pcbnew.PCB_SHAPE(board)
    rect.SetShape(pcbnew.SHAPE_T_RECT)
    rect.SetStart(VECTOR2I(FromMM(ORIGIN), FromMM(ORIGIN)))
    rect.SetEnd(VECTOR2I(FromMM(ORIGIN + g.BLANK_W),
                         FromMM(ORIGIN + g.BLANK_H)))
    rect.SetLayer(pcbnew.Edge_Cuts)
    rect.SetWidth(FromMM(0.1))
    rect.SetFilled(False)
    board.Add(rect)


def add_index(board):
    """A 10 mm ruler in the frame, so a hole can be named by coordinate."""
    cx, cy = ORIGIN + g.BLANK_W / 2, ORIGIN + g.BLANK_H / 2
    step = 10.0
    nx = int((g.BLANK_W / 2 - g.FENCE_INSET) / step)
    ny = int((g.BLANK_H / 2 - g.FENCE_INSET) / step)
    items = ([(cx + i * step, ORIGIN + 2.5, str(i * int(step)))
              for i in range(-nx, nx + 1)] +
             [(ORIGIN + 2.5, cy + j * step, str(j * int(step)))
              for j in range(-ny, ny + 1)])
    for x, y, label in items:
        t = pcbnew.PCB_TEXT(board)
        t.SetText(label)
        t.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(VECTOR2I(FromMM(1.0), FromMM(1.0)))
        t.SetTextThickness(FromMM(0.15))
        board.Add(t)


def save_library(board, pattern, io):
    for name, (pts, _) in sorted(g.runs(pattern).items()):
        io.FootprintSave(LIBDIR, m.make_footprint(board, "ViaBlank_" + name, pts))


def build(pattern, io):
    out = os.path.join(TPLDIR, "ViaBlank_%s.kicad_pcb" % pattern.capitalize())
    board = pcbnew.NewBoard(out)
    add_outline(board)

    # The outline is the full blank, so merge() clips nothing: the template
    # carries the whole pattern, fence included.
    stats = m.merge(board, pattern)
    add_index(board)
    save_library(board, pattern, io)

    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ds.m_TrackMinWidth = FromMM(g.ENDMILL)
    nc = board.GetAllNetClasses()["Default"]
    nc.SetTrackWidth(FromMM(g.TRACK))
    nc.SetClearance(FromMM(g.CLEARANCE))

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(out, board)
    print("%-10s %3d footprints, %4d holes  ->  %s"
          % (pattern, stats["placed"], stats["holes"], os.path.basename(out)))
    if stats["skipped"]:
        print("           WARNING clipped at full blank size: %s"
              % stats["skipped"])


if __name__ == "__main__":
    os.makedirs(LIBDIR, exist_ok=True)
    os.makedirs(TPLDIR, exist_ok=True)
    # FootprintSave()'s plugin guess needs a non-empty .pretty; name it outright.
    io = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)
    for pattern in sorted(g.PATTERNS):
        build(pattern, io)
