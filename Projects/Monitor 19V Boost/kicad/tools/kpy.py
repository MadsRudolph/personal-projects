#!/usr/bin/env python3
"""Run a script with pcbnew patched for Python 3.14.

Arch's KiCad 10 pcbnew.py iterates tracks with `it.next()`, which SWIG no longer
generates under 3.14 (only `__next__`), so every GetTracks() raises. This
launcher adds the alias and then runs the target as __main__:

    python3 kicad/tools/kpy.py <script.py> [args...]
"""
import runpy
import sys

import pcbnew

if not hasattr(pcbnew.SwigPyIterator, "next"):
    pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__

script = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(script, run_name="__main__")
