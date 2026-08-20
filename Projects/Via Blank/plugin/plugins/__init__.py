"""KiCad entry point. pcbnew imports this at startup and we register the plugin."""
import os
import sys

# Make the bundled 'viablank' package importable regardless of how KiCad loads
# this folder (relative-import behaviour varies across KiCad point releases).
sys.path.insert(0, os.path.dirname(__file__))

try:
    from action_via_blank import ViaBlankAction
    ViaBlankAction().register()
except Exception:      # never break PCB editor startup over a plugin error
    import traceback
    sys.stderr.write("Via Blank failed to register:\n")
    traceback.print_exc()
