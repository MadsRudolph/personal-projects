"""
Build a self-contained 3D-model shim for exporting subxo.kicad_pcb.

Why this exists
---------------
Every footprint on the board resolves its 3D model through
${KICAD9_3DMODEL_DIR}. Two problems:

1. J1-J7 want ${KICAD9_3DMODEL_DIR}/TerminalBlock.3dshapes/..._bornier-N_...
   That library does not exist. Not in KiCad 9, not in KiCad 10, and not in
   the official kicad-packages3D repo on GitLab either - only the four branded
   TerminalBlock_* libraries are shipped. The bornier footprints point at a
   path that was never populated.

2. Overriding KICAD9_3DMODEL_DIR to fix (1) redirects *every* lookup, so U2's
   TO-220 and everything else then fail to resolve.

So the shim has to be a complete overlay, not a patch. This script copies the
handful of model files the board actually references out of the KiCad install,
and leaves the hand-placed TerminalBlock.3dshapes substitutes alone.

Run with KiCad's Python:
    "C:/Program Files/KiCad/10.0/bin/python.exe" make_model_shim.py
"""

import os
import re
import shutil
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.abspath(os.path.join(HERE, "..", "..", "kicad", "subxo.kicad_pcb"))
SHIM = os.path.join(HERE, "models")
KICAD_3D = r"C:/Program Files/KiCad/10.0/share/kicad/3dmodels"

# Provided by hand, not copied from the install. See the README note: these are
# genuine Phoenix MKDS-1,5 5.08 mm blocks renamed to the bornier filenames the
# footprints ask for. A real part standing in for a different real part.
HAND_PROVIDED = "TerminalBlock.3dshapes"

board = pcbnew.LoadBoard(BOARD)

wanted = set()
for fp in board.GetFootprints():
    for m in fp.Models():
        p = str(m.m_Filename).replace(chr(92), "/")
        mm = re.search(r"\$\{KICAD9_3DMODEL_DIR\}/(.+)$", p)
        if mm:
            wanted.add(mm.group(1))

copied, skipped, missing = [], [], []
for rel in sorted(wanted):
    if rel.startswith(HAND_PROVIDED + "/"):
        skipped.append(rel)
        continue
    src = os.path.join(KICAD_3D, rel)
    dst = os.path.join(SHIM, rel)
    if not os.path.exists(src):
        missing.append(rel)
        continue
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    copied.append(rel)

print("shim: %s" % SHIM)
print("copied from KiCad install : %d" % len(copied))
for r in copied:
    print("    %s" % r)
print("hand-provided (left alone): %d" % len(skipped))
for r in skipped:
    print("    %s" % r)
if missing:
    print("STILL MISSING: %d" % len(missing))
    for r in missing:
        print("    %s" % r)
    sys.exit(1)
