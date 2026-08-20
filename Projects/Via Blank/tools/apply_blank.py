#!/usr/bin/env python3
"""Merge a via blank into an existing board, from the command line.

Same operation as the KiCad plugin's toolbar button, for when the editor is
closed or you want it in a script. Writes a .bak first.

  & "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" tools\\apply_blank.py ^
        path\\to\\board.kicad_pcb [--pattern islands]
"""
import argparse
import os
import shutil
import sys

import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "plugin", "plugins"))

from viablank import geometry as g                           # noqa: E402
from viablank import merge as m                              # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("board")
    ap.add_argument("--pattern", default="islands", choices=g.MODES)
    args = ap.parse_args()

    board = pcbnew.LoadBoard(args.board)
    try:
        stats = m.merge(board, args.pattern)
    except m.OutlineProblem as exc:
        raise SystemExit(str(exc))

    shutil.copy(args.board, args.board + ".bak")
    pcbnew.SaveBoard(args.board, board)
    print(m.summary(args.pattern, stats))
    print("Backup: %s.bak" % os.path.basename(args.board))


if __name__ == "__main__":
    main()
