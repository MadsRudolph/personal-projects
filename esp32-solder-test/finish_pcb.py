#!/usr/bin/env python3
"""Post-route finishing for esp32solder.kicad_pcb: copper orientation text + pour refill.

"ESP32 TEST" in B.Cu, mirrored (bottom-side text), so it reads normally only
when the board is seen from the copper side -- i.e. in the laser preview if
the negative is oriented right. Stroke 0.3 mm (coupon proved 0.15 mm clean).

Run once after routing:  PYTHONPATH=tools/pyshim python3 finish_pcb.py
"""
import os
import pcbnew
from pcbnew import VECTOR2I, FromMM

PCB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "esp32solder.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
if not any(isinstance(d, pcbnew.PCB_TEXT) and d.GetText() == "ESP32 TEST" for d in b.GetDrawings()):
    t = pcbnew.PCB_TEXT(b)
    t.SetText("ESP32 TEST")
    t.SetLayer(pcbnew.B_Cu)
    t.SetMirrored(True)
    t.SetTextSize(VECTOR2I(FromMM(1.5), FromMM(1.5)))
    t.SetTextThickness(FromMM(0.3))
    t.SetPosition(VECTOR2I(FromMM(167.0), FromMM(120.0)))
    b.Add(t)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print("text + refill done")
