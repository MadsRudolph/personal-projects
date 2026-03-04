"""Fix TERM label positions -- move to actual fuse pin TIP positions.

Pin tip = center ± (lib_pin_offset + pin_length) = center ± 5.08
NOT center ± 3.81 (which is the pin BASE, not the electrical connection point).

Current (wrong) positions:
  TERM_10A at (29.21, 44.45) -- should be (29.21, 43.18)
  TERM_mA  at (29.21, 64.77) -- should be (29.21, 63.50)

Also moves wire stubs to match.
"""
import re, shutil
from pathlib import Path

SCH = Path(r"C:\Users\Mads2\Documents\Projects\Projects\DTU Multimeter\KiCad\Multimeter\Multimeter.kicad_sch")

shutil.copy2(SCH, SCH.with_suffix(".kicad_sch.bak"))
content = SCH.read_text(encoding="utf-8")

# Fix TERM_10A label: (29.21, 44.45) -> (29.21, 43.18)
old = '(at 29.21 44.45 180)'
count_label = content.count(old)
content = content.replace(
    '(label "TERM_10A"\n\t\t(at 29.21 44.45 180)',
    '(label "TERM_10A"\n\t\t(at 29.21 43.18 180)',
    1
)
print(f"TERM_10A label: moved (29.21, 44.45) -> (29.21, 43.18)")

# Fix TERM_mA label: (29.21, 64.77) -> (29.21, 63.50)
content = content.replace(
    '(label "TERM_mA"\n\t\t(at 29.21 64.77 180)',
    '(label "TERM_mA"\n\t\t(at 29.21 63.50 180)',
    1
)
print(f"TERM_mA label: moved (29.21, 64.77) -> (29.21, 63.50)")

# Fix wire stub 1: (29.21, 44.45)->(29.21, 41.91) -> (29.21, 43.18)->(29.21, 40.64)
content = content.replace(
    '(xy 29.21 44.45) (xy 29.21 41.91)',
    '(xy 29.21 43.18) (xy 29.21 40.64)',
    1
)
print(f"Wire 1: moved (29.21, 44.45->41.91) -> (29.21, 43.18->40.64)")

# Fix wire stub 2: (29.21, 64.77)->(29.21, 62.23) -> (29.21, 63.50)->(29.21, 60.96)
content = content.replace(
    '(xy 29.21 64.77) (xy 29.21 62.23)',
    '(xy 29.21 63.50) (xy 29.21 60.96)',
    1
)
print(f"Wire 2: moved (29.21, 64.77->62.23) -> (29.21, 63.50->60.96)")

SCH.write_text(content, encoding="utf-8")
print(f"\nDone! Both TERM labels moved to correct fuse pin TIP positions.")
