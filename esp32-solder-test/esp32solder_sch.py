#!/usr/bin/env python3
"""ESP32 solder test board: schematic layout script (kicad-schematic DSL).

Smallest board that proves an ESP32-WROOM-32 hand-soldered to fiber-laser-etched
copper actually works: flash it over a USB-UART adapter and blink IO2.
Everything except the module is through-hole and in stock at the DTU component
shop (see ../components-inventory/dtu_component_shop(1).csv).

  J1   1x4 header      GND, +5V, TXD0 (ESP out), RXD0 (ESP in) -> USB-UART adapter
  U2   LM317T TO-220   5 V -> 3.27 V (the shop has no fixed 3.3 V regulator):
                       Vout = 1.25 * (1 + R2/R1) = 1.25 * (1 + 392/243)
  SW1  RESET (EN)      10k pull-up + 1 uF delay
  SW2  BOOT  (IO0)     hold while pressing RESET to enter the bootloader
  D1   user LED on IO2 (332 R), D2 power LED on +3V3 (1 k)

Run:  python3 esp32solder_sch.py esp32solder.kicad_sch
"""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, "/home/mads/.claude/skills/kicad-schematic/scripts")
from schdraw import Sheet

HERE = Path(__file__).resolve().parent
PRO = HERE / "esp32solder.kicad_pro"
G = lambda n: round(n * 1.27, 2)

FP_R   = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"
FP_CP  = "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm"
FP_C   = "Capacitor_THT:C_Disc_D3.0mm_W1.6mm_P2.50mm"
FP_LED = "LED_THT:LED_D3.0mm"
FP_SW  = "Button_Switch_THT:SW_PUSH_6mm"
FP_J   = "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"
FP_U2  = "Package_TO_SOT_THT:TO-220-3_Vertical"
FP_U1  = "esp32solder:ESP32-WROOM-32_NoVias"

sh = Sheet(paper="A4", title="ESP32 solder test", project="esp32solder",
           project_file=str(PRO) if PRO.exists() else None)

def R(ref, at, val, rot=0):  return sh.place("Device:R", ref, at=at, rot=rot, value=val, footprint=FP_R)
def CP(ref, at, val):        return sh.place("Device:C_Polarized", ref, at=at, value=val, footprint=FP_CP)
def top(part):
    a, b = part.pin(1), part.pin(2)
    return (a, b) if a.y < b.y else (b, a)

# ============================================================ header
sh.note((G(12), G(22)), "USB-UART adapter", size=2)
j1 = sh.place("Connector_Generic:Conn_01x04", "J1", at=(G(22), G(34)), mirror="y", value="UART / 5V", footprint=FP_J)
jg, j5, jt, jr = (j1.pin(i) for i in (1, 2, 3, 4))
assert jg.y < j5.y < jt.y < jr.y and jg.x > j1.x
j1.field_at = {"Reference": (j1.x - G(2), jg.y - G(5)), "Value": (j1.x - G(2), jr.y + G(3))}
# pin 1 GND: top row, so hook up and over to a ground symbol that hangs clear
sh.seg(jg, (G(28), jg.y)); sh.seg((G(28), jg.y), (G(28), jg.y - G(4))); sh.seg((G(28), jg.y - G(4)), (G(31), jg.y - G(4)))
sh.gnd((G(31), jg.y - G(4)), drop=0)
sh.seg(j5, (G(28), j5.y)); sh.label((G(28), j5.y), "+5V_IN")
sh.seg(jt, (G(28), jt.y)); sh.label((G(28), jt.y), "TXD0")
sh.seg(jr, (G(28), jr.y)); sh.label((G(28), jr.y), "RXD0")

# ============================================================ 3.3 V regulator
sh.note((G(40), G(22)), "3.3 V from LM317 (243 R / 392 R -> 3.27 V)", size=2)
UX, UY = G(62), G(32)
u2 = sh.place("Regulator_Linear:LM317_TO-220", "U2", at=(UX, UY), value="LM317T", footprint=FP_U2)
vi, vo, adj = u2.pin("VI"), u2.pin("VO"), u2.pin("ADJ")
XC1, XR1, XR2, XC2, XLED = G(48), G(74), G(68), G(82), G(90)
RAIL = UY + G(16)
c1 = CP("C1", (XC1, UY + G(3)), "10u"); assert top(c1)[0].xy == (XC1, vi.y)
sh.seg((G(40), vi.y), (G(44), vi.y)); sh.seg((G(44), vi.y), (XC1, vi.y)); sh.seg((XC1, vi.y), vi); sh.label((G(40), vi.y), "+5V_IN", rot=180)
sh.seg((G(44), vi.y - G(2)), (G(44), vi.y))   # PWR_FLAG stub (flag placed below)
r1 = R("R1", (XR1, UY + G(3)), "243"); assert top(r1)[0].xy == (XR1, vo.y)
c2 = CP("C2", (XC2, UY + G(3)), "10u"); assert top(c2)[0].xy == (XC2, vo.y)
r6 = R("R6", (XLED, UY + G(3)), "1k"); assert top(r6)[0].xy == (XLED, vo.y)
for xa, xb in ((vo.x, XR1), (XR1, XC2), (XC2, XLED), (XLED, G(96))):
    sh.seg((xa, vo.y), (xb, vo.y))
sh.power("power:+3V3", (G(96), vo.y - G(2))); sh.seg((G(96), vo.y - G(2)), (G(96), vo.y))
YA = adj.y + G(2)
sh.seg(adj, (adj.x, YA)); sh.seg((adj.x, YA), (XR2, YA)); sh.seg((XR2, YA), (XR1, YA))
sh.seg(top(r1)[1], (XR1, YA))
r2 = R("R2", (XR2, YA + G(3)), "392"); assert top(r2)[0].xy == (XR2, YA)
d2 = sh.place("Device:LED", "D2", at=(XLED, top(r6)[1].y + G(3)), rot=90, value="LED red", footprint=FP_LED)
assert d2.pin("A").y < d2.pin("K").y
sh.seg(top(r6)[1], d2.pin("A"))
for p in (top(c1)[1], top(r2)[1], top(c2)[1], d2.pin("K")):
    sh.seg(p, (p.x, RAIL))
sh.seg((XC1, RAIL), (XR2, RAIL)); sh.seg((XR2, RAIL), (XC2, RAIL)); sh.seg((XC2, RAIL), (XLED, RAIL))
sh.gnd((G(62), RAIL))
sh.power("power:PWR_FLAG", (G(44), vi.y - G(2)))
sh.power("power:PWR_FLAG", (G(56), RAIL))

# ============================================================ ESP32
sh.note((G(116), G(22)), "ESP32-WROOM-32 (hand-soldered to the laser-etched copper)", size=2)
MX, MY = G(160), G(90)
u1 = sh.place("RF_Module:ESP32-WROOM-32", "U1", at=(MX, MY), value="ESP32-WROOM-32", footprint=FP_U1)
vdd, en, io0, txd, io2, rxd = (u1.pin(n) for n in ("VDD", "EN", "IO0", "TXD0/IO1", "IO2", "RXD0/IO3"))
TOP = round(vdd.y - G(10), 2)                  # high enough that C3's ground clears U1's body
sh.seg(vdd, (vdd.x, TOP)); sh.seg((vdd.x, TOP), (vdd.x + G(8), TOP)); sh.power("power:+3V3", (vdd.x, TOP - G(2)))
sh.seg((vdd.x, TOP - G(2)), (vdd.x, TOP))
c3 = sh.place("Device:C", "C3", at=(vdd.x + G(8), TOP + G(3)), value="100n", footprint=FP_C)
assert top(c3)[0].y == TOP; sh.gnd(top(c3)[1])
sh.gnd(u1.pin(1))
# EN: pull-up, delay cap, RESET button, left of the module
XE = round(en.x - G(26), 2)
XC4, XR3 = round(XE + G(9), 2), round(XE + G(16), 2)
r3 = R("R3", (XR3, en.y - G(3)), "10k"); assert top(r3)[1].xy == (XR3, en.y); sh.rail(top(r3)[0], net="+3V3")
c4 = CP("C4", (XC4, en.y + G(3)), "1u"); assert top(c4)[0].xy == (XC4, en.y); sh.gnd(top(c4)[1])
sw1 = sh.place("Switch:SW_Push", "SW1", at=(XE, en.y + G(4)), rot=90, value="RESET", footprint=FP_SW)
s1t, s1b = top(sw1); assert s1t.xy == (XE, en.y); sh.gnd(s1b)
for xa, xb in ((XE, XC4), (XC4, XR3), (XR3, en.x)):
    sh.seg((xa, en.y), (xb, en.y))
# UART + IO0: labels (the header sits across the sheet)
XL = io0.x + G(6)
for p, nm in ((io0, "IO0"), (txd, "TXD0"), (rxd, "RXD0")):
    sh.seg(p, (XL, p.y)); sh.label((XL, p.y), nm)
# IO2 user LED
r5 = R("R5", (io2.x + G(20), io2.y), "332", rot=90)
sh.seg(io2, r5.pin(1) if r5.pin(1).x < r5.pin(2).x else r5.pin(2))
rr = r5.pin(2) if r5.pin(1).x < r5.pin(2).x else r5.pin(1)
d1 = sh.place("Device:LED", "D1", at=(rr.x + G(3), io2.y + G(3)), rot=90, value="LED green", footprint=FP_LED)
sh.seg(rr, (d1.pin("A").x, rr.y)); sh.seg((d1.pin("A").x, rr.y), d1.pin("A")); sh.gnd(d1.pin("K"))
# BOOT button on IO0, with its pull-up
sh.note((G(178), G(106)), "BOOT: hold, tap RESET, release -> bootloader", size=1.5)
YB = G(116)
r4 = R("R4", (G(192), YB - G(3)), "10k"); assert top(r4)[1].xy == (G(192), YB); sh.rail(top(r4)[0], net="+3V3")
sw2 = sh.place("Switch:SW_Push", "SW2", at=(G(200), YB + G(4)), rot=90, value="BOOT", footprint=FP_SW)
s2t, s2b = top(sw2); assert s2t.xy == (G(200), YB); sh.gnd(s2b)
sh.seg((G(186), YB), (G(192), YB)); sh.seg((G(192), YB), (G(200), YB)); sh.label((G(186), YB), "IO0", rot=180)
USED = {"1", "2", "3", "15", "24", "25", "34", "35", "38", "39"}
sh.nc(*[p for p in u1.pins if p.number not in USED and p.name != "GND"])

# ============================================================ target netlist
T = {}
def net(name, *pins): T.setdefault(name, set()).update(pins)
net("+5V_IN", ("J1", "2"), ("U2", "3"), ("C1", "1"))
net("+3V3", ("U2", "2"), ("R1", "1"), ("C2", "1"), ("R6", "1"), ("U1", "2"), ("C3", "1"), ("R3", "1"), ("R4", "1"))
net("ADJ", ("U2", "1"), ("R1", "2"), ("R2", "1"))
net("GND", ("J1", "1"), ("C1", "2"), ("R2", "2"), ("C2", "2"), ("D2", "1"), ("U1", "1"), ("U1", "15"), ("U1", "38"), ("U1", "39"),
    ("C3", "2"), ("C4", "2"), ("SW1", s1b.number), ("SW2", s2b.number), ("D1", "1"))
net("PLED", ("R6", "2"), ("D2", "2"))
net("EN", ("U1", "3"), ("R3", "2"), ("C4", "1"), ("SW1", s1t.number))
net("IO0", ("U1", "25"), ("R4", "2"), ("SW2", s2t.number))
net("TXD0", ("U1", "35"), ("J1", "3")); net("RXD0", ("U1", "34"), ("J1", "4"))
net("IO2", ("U1", "24"), (r5.ref, r5.pin(1).number if r5.pin(1).x < r5.pin(2).x else r5.pin(2).number))
net("ULED", (r5.ref, rr.number), ("D1", "2"))
for p in u1.pins:
    if p.number not in USED and p.name != "GND":
        net(f"NC_{p.number}", ("U1", p.number))
print("check:", sh.check() or "clean")
print("verify:", sh.verify_against(T))
if len(sys.argv) > 1:
    sh.emit(sys.argv[1]); print("emitted", sys.argv[1])
    if not PRO.exists():
        cls = {"name": "Default", "clearance": 0.3, "track_width": 0.5, "via_diameter": 0.8, "via_drill": 0.4,
               "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2, "microvia_diameter": 0.3,
               "microvia_drill": 0.1, "wire_width": 6.0, "bus_width": 12.0, "line_style": 0,
               "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647}
        d = {"meta": {"filename": PRO.name, "version": 3}, "sheets": [[sh.uuid, "Root"]],
             "net_settings": {"classes": [cls], "meta": {"version": 4}, "net_colors": None,
                              "netclass_assignments": None, "netclass_patterns": []},
             "board": {"design_settings": {"rules": {"min_clearance": 0.3, "min_track_width": 0.3,
                       "min_copper_edge_clearance": 0.5, "min_hole_clearance": 0.25, "min_via_diameter": 0.6,
                       "min_via_annular_width": 0.15, "min_text_height": 0.8, "min_text_thickness": 0.08},
                       "defaults": {"copper_line_width": 0.5}}, "layer_presets": [], "viewports": []},
             "pcbnew": {"page_layout_descr_file": ""}, "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
             "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []}, "text_variables": {}}
        json.dump(d, open(PRO, "w"), indent=2); print("wrote", PRO)
