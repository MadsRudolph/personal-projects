"""Fix the Arduino Mega A000067 footprint to use proper header pad/drill sizes.

Original:  size 1.358 x 1.358, drill 0.85  -> tiny annular ring, won't fit pins
Fixed:     size 1.7   x 1.7,   drill 1.0   -> standard female header pad

Also changes pin shape from `circle` to `oval` for a cleaner header look.
Keeps NC pin 1 as `rect` for orientation.
Keeps the np_thru_hole mounting holes (3.2mm) untouched.
"""

import re
from pathlib import Path

FP_PATH = Path(__file__).parent.parent / "lib" / "footprints" / "A000067.pretty" / "MODULE_A000067.kicad_mod"

OLD_SIZE = "(size 1.358 1.358) (drill 0.85)"
NEW_SIZE = "(size 1.7 1.7) (drill 1.0)"

text = FP_PATH.read_text()

# 1. Replace pad/drill size on all signal pads
new_text = text.replace(OLD_SIZE, NEW_SIZE)
n = text.count(OLD_SIZE)
print(f"Updated {n} pads from {OLD_SIZE} -> {NEW_SIZE}")

# 2. Change `circle` -> `oval` for signal pads (keep `rect` on pin 1, keep np_thru_hole)
#    Match: `(pad <name> thru_hole circle (at ... )`
def circle_to_oval(match):
    return match.group(0).replace("thru_hole circle", "thru_hole oval")

new_text2, n2 = re.subn(
    r"\(pad \S+ thru_hole circle \(at",
    circle_to_oval,
    new_text,
)
print(f"Changed {n2} pads from circle -> oval shape")

FP_PATH.write_text(new_text2)
print(f"Wrote updated footprint to {FP_PATH}")
