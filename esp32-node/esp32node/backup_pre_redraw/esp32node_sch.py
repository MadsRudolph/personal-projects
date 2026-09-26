#!/usr/bin/env python3
"""ESP32-WROOM-32 ESPHome node: schematic layout script (kicad-schematic DSL).

Single-sided SMD board for the xTool F1 Ultra fiber laser. USB-C -> CH340C -> ESP32,
AMS1117-3.3 regulator, EN/BOOT buttons with auto-reset, full GPIO breakout,
I2C header with pull-ups, 1-Wire header with pull-up, power + user LEDs.
"""
import sys
sys.path.insert(0, "/home/mads/.claude/skills/kicad-schematic/scripts")
from schdraw import Sheet

G = lambda n: round(n * 1.27, 2)

FP_R   = "Resistor_SMD:R_0805_2012Metric"
FP_C   = "Capacitor_SMD:C_0805_2012Metric"
FP_LED = "LED_SMD:LED_0805_2012Metric"
FP_SW  = "Button_Switch_SMD:SW_SPST_PTS645Sx43SMTR92"
FP_Q   = "Package_TO_SOT_SMD:SOT-23"
FP_U3  = "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm"
FP_U2  = "Package_TO_SOT_SMD:SOT-223-3_TabPin2"
FP_U1  = "RF_Module:ESP32-WROOM-32"
FP_J1  = "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal"
FP_H16 = "Connector_PinHeader_2.54mm:PinHeader_1x16_P2.54mm_Vertical"
FP_H4  = "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"
FP_H3  = "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"

sh = Sheet(paper="A3", title="ESP32 node", project="esp32node")

def R(ref, at, val, rot=0):  return sh.place("Device:R", ref, at=at, rot=rot, value=val, footprint=FP_R)
def C(ref, at, val, rot=0):  return sh.place("Device:C", ref, at=at, rot=rot, value=val, footprint=FP_C)
def top(part):   # (top_pin, bottom_pin) of a two-pin vertical part
    a, b = part.pin(1), part.pin(2)
    return (a, b) if a.y < b.y else (b, a)

# ============================================================ band 1: power
sh.note((G(80), G(18)), "3.3 V regulator  (USB 5 V -> AMS1117-3.3 -> 3V3)", size=2)
u2 = sh.place("Regulator_Linear:AMS1117-3.3", "U2", at=(G(100), G(30)), value="AMS1117-3.3", footprint=FP_U2)
vi, vo, ug = u2.pin("VI"), u2.pin("VO"), u2.pin("GND")
sh.seg(vi, (G(84), vi.y)); sh.rail((G(84), vi.y), net="+5V")
c1 = C("C1", (G(88), G(33)), "10u"); sh.seg(top(c1)[0], top(c1)[0])
sh.seg(vo, (G(116), vo.y)); sh.rail((G(116), vo.y), net="+3V3")
c2 = C("C2", (G(112), G(33)), "10u")
RAIL1 = G(40)
for p in (top(c1)[1], ug, top(c2)[1]):
    sh.seg(p, (p.x, RAIL1))
sh.seg((G(88), RAIL1), (G(112), RAIL1)); sh.gnd((G(100), RAIL1))
# power LED
r7 = R("R7", (G(130), G(28)), "1k"); sh.rail(top(r7)[0], net="+3V3")
d1 = sh.place("Device:LED", "D1", at=(G(130), G(36)), rot=90, value="LED red", footprint=FP_LED)
da, dk = (d1.pin("A"), d1.pin("K"))
assert da.y < dk.y, "LED anode should be on top"
sh.seg(top(r7)[1], da); sh.gnd(dk)
sh.note((G(126), G(45)), "power", size=1.27)
# PWR_FLAGs
sh.power("power:+5V", (G(150), G(26))); sh.seg((G(150), G(26)), (G(150), G(28))); sh.seg((G(150), G(28)), (G(154), G(28)))
sh.power("power:PWR_FLAG", (G(154), G(28)))
sh.power("power:GND", (G(162), G(28))); sh.seg((G(162), G(28)), (G(166), G(28)))
sh.power("power:PWR_FLAG", (G(166), G(28)))

# ============================================================ band 2: USB-C
sh.note((G(26), G(92)), "USB-C input  (5 V + USB 2.0 data, CC pull-downs for C-to-C cables)", size=2)
j1 = sh.place("Connector:USB_C_Receptacle_USB2.0_16P", "J1", at=(G(36), G(112)), value="USB-C", footprint=FP_J1)
vb = j1.pin("A4"); sh.rail(vb, net="+5V")
cc1, cc2 = j1.pin("A5"), j1.pin("B5")
sh.seg(cc1, (G(68), cc1.y)); r1 = R("R1", (G(68), G(107)), "5.1k"); assert top(r1)[0].xy == (G(68), cc1.y)
sh.seg(cc2, (G(64), cc2.y)); r2 = R("R2", (G(64), G(109)), "5.1k"); assert top(r2)[0].xy == (G(64), cc2.y)
dm_a, dm_b = j1.pin("A7"), j1.pin("B7")       # D-
dp_a, dp_b = j1.pin("A6"), j1.pin("B6")       # D+
sh.seg(dm_a, dm_b); sh.seg(dm_b, (G(52), dm_b.y)); sh.label((G(52), dm_b.y), "USB_D-")
sh.seg(dp_a, dp_b); sh.seg(dp_b, (G(52), dp_b.y)); sh.label((G(52), dp_b.y), "USB_D+")
sh.nc(j1.pin("A8"), j1.pin("B8"))
RAIL2 = G(134)
jg, jsh = j1.pin("A1"), j1.pin("SH")
for p in (jg, jsh, top(r1)[1], top(r2)[1]):
    sh.seg(p, (p.x, RAIL2))
sh.seg((jsh.x, RAIL2), (G(68), RAIL2)); sh.gnd((G(52), RAIL2))

# ============================================================ band 2: CH340C
sh.note((G(78), G(88)), "USB-UART bridge  (CH340C, no crystal)", size=2)
u3 = sh.place("Interface_USB:CH340C", "U3", at=(G(92), G(112)), value="CH340C", footprint=FP_U3)
udp, udm = u3.pin("UD+"), u3.pin("UD-")
sh.seg(udp, (G(78), udp.y)); sh.label((G(78), udp.y), "USB_D+", rot=180)
sh.seg(udm, (G(78), udm.y)); sh.label((G(78), udm.y), "USB_D-", rot=180)
sh.nc(u3.pin("R232"), u3.pin(7), u3.pin(8), u3.pin("~{CTS}"), u3.pin("~{DSR}"), u3.pin("~{RI}"), u3.pin("~{DCD}"))
vcc, v3, u3g = u3.pin("VCC"), u3.pin("V3"), u3.pin("GND")
sh.seg(vcc, (vcc.x, G(96))); sh.seg((vcc.x, G(96)), (G(78), G(96)))
c7 = C("C7", (G(78), G(99)), "100n"); assert top(c7)[0].xy == (G(78), G(96)); sh.gnd(top(c7)[1])
sh.rail((G(84), G(96)), net="+5V")
sh.seg(v3, (v3.x, G(98))); sh.seg((v3.x, G(98)), (G(110), G(98)))
c5 = C("C5", (G(110), G(101)), "100n"); assert top(c5)[0].xy == (G(110), G(98)); sh.gnd(top(c5)[1])
sh.gnd(u3g)
txd, rxd = u3.pin("TXD"), u3.pin("RXD")
sh.seg(txd, (G(102), txd.y)); sh.label((G(102), txd.y), "RXD0")
sh.seg(rxd, (G(102), rxd.y)); sh.label((G(102), rxd.y), "TXD0")
dtr, rts = u3.pin("~{DTR}"), u3.pin("~{RTS}")

# ============================================================ band 2: auto-reset
sh.note((G(104), G(142)), "Auto-reset  (DTR/RTS -> EN/IO0, esptool style)", size=2)
r3 = R("R3", (G(110), dtr.y), "10k", rot=90)
sh.seg(dtr, r3.pin(1)); sh.label((G(104), dtr.y), "DTR")
q1 = sh.place("Transistor_BJT:Q_NPN_BEC", "Q1", at=(G(120), dtr.y), value="S8050", footprint=FP_Q)
sh.seg(r3.pin(2), q1.pin("B"))
q1c, q1e = q1.pin("C"), q1.pin("E"); assert q1c.y < q1e.y
sh.seg(q1c, (q1c.x, q1c.y - G(2))); sh.seg((q1c.x, q1c.y - G(2)), (G(126), q1c.y - G(2))); sh.label((G(126), q1c.y - G(2)), "EN")
sh.seg(q1e, (q1e.x, q1e.y + G(2))); sh.seg((q1e.x, q1e.y + G(2)), (G(126), q1e.y + G(2))); sh.label((G(126), q1e.y + G(2)), "RTS")
Y2 = G(132)
sh.seg(rts, (G(104), rts.y)); sh.seg((G(104), rts.y), (G(104), Y2)); sh.label((G(104), G(126)), "RTS")
r4 = R("R4", (G(110), Y2), "10k", rot=90); sh.seg((G(104), Y2), r4.pin(1))
q2 = sh.place("Transistor_BJT:Q_NPN_BEC", "Q2", at=(G(120), Y2), value="S8050", footprint=FP_Q)
sh.seg(r4.pin(2), q2.pin("B"))
q2c, q2e = q2.pin("C"), q2.pin("E")
sh.seg(q2c, (q2c.x, q2c.y - G(2))); sh.seg((q2c.x, q2c.y - G(2)), (G(126), q2c.y - G(2))); sh.label((G(126), q2c.y - G(2)), "IO0")
sh.seg(q2e, (q2e.x, q2e.y + G(2))); sh.seg((q2e.x, q2e.y + G(2)), (G(126), q2e.y + G(2))); sh.label((G(126), q2e.y + G(2)), "DTR")

# ============================================================ band 2: ESP32
sh.note((G(168), G(70)), "ESP32-WROOM-32  (EN/BOOT buttons, 3V3 decoupling)", size=2)
u1 = sh.place("RF_Module:ESP32-WROOM-32", "U1", at=(G(190), G(118)), value="ESP32-WROOM-32", footprint=FP_U1)
en, vdd, gnd1 = u1.pin("EN"), u1.pin("VDD"), u1.pin(1)
# EN network, left of the module
sh.seg(en, (G(156), en.y)); sh.label((G(156), en.y), "EN", rot=180)
r5 = R("R5", (G(172), en.y - G(3)), "10k"); assert top(r5)[1].xy == (G(172), en.y); sh.rail(top(r5)[0], net="+3V3")
c6 = C("C6", (G(166), en.y + G(3)), "1u"); assert top(c6)[0].xy == (G(166), en.y)
sw1 = sh.place("Switch:SW_Push", "SW1", at=(G(160), en.y + G(4)), rot=90, value="RESET", footprint=FP_SW)
s1t, s1b = top(sw1); assert s1t.xy == (G(160), en.y), s1t.xy
RAIL_EN = en.y + G(10)
sh.seg(top(c6)[1], (G(166), RAIL_EN)); sh.seg(s1b, (G(160), RAIL_EN)); sh.seg((G(160), RAIL_EN), (G(166), RAIL_EN)); sh.gnd((G(163), RAIL_EN))
for pn, nm in ((4, "SVP"), (5, "SVN")):
    p = u1.pin(pn); sh.seg(p, (G(176), p.y)); sh.label((G(176), p.y), nm, rot=180)
sh.nc(*[u1.pin(n) for n in (17, 18, 19, 20, 21, 22, 32)])
# 3V3 + decoupling above
TOP = G(78)
sh.seg(vdd, (vdd.x, TOP)); sh.seg((vdd.x, TOP), (G(206), TOP)); sh.rail((vdd.x, TOP), net="+3V3")
c3 = C("C3", (G(198), TOP + G(3)), "100n"); c4 = C("C4", (G(206), TOP + G(3)), "10u")
RAIL3 = TOP + G(8)
for c in (c3, c4):
    assert top(c)[0].y == TOP; sh.seg(top(c)[1], (c.x, RAIL3))
sh.seg((G(198), RAIL3), (G(206), RAIL3)); sh.gnd((G(202), RAIL3))
sh.gnd(gnd1)
# IO0 network, right of the module
io0 = u1.pin("IO0")
sh.seg(io0, (G(220), io0.y)); sh.label((G(206), io0.y), "IO0")
r6 = R("R6", (G(214), io0.y - G(3)), "10k"); assert top(r6)[1].xy == (G(214), io0.y); sh.rail(top(r6)[0], net="+3V3")
sw2 = sh.place("Switch:SW_Push", "SW2", at=(G(220), io0.y + G(4)), rot=90, value="BOOT", footprint=FP_SW)
s2t, s2b = top(sw2); assert s2t.xy == (G(220), io0.y); sh.gnd(s2b)
# GPIO stubs with labels
IO_PINS = {35: "TXD0", 24: "IO2", 34: "RXD0", 26: "IO4", 29: "IO5", 14: "IO12", 16: "IO13", 13: "IO14",
           23: "IO15", 27: "IO16", 28: "IO17", 30: "IO18", 31: "IO19", 33: "IO21", 36: "IO22", 37: "IO23",
           10: "IO25", 11: "IO26", 12: "IO27", 8: "IO32", 9: "IO33", 6: "IO34", 7: "IO35"}
for pn, nm in IO_PINS.items():
    p = u1.pin(pn); sh.seg(p, (G(206), p.y)); sh.label((G(206), p.y), nm)

# ============================================================ band 2: headers
sh.note((G(236), G(82)), "GPIO breakout  (2 x 16, module pin order)", size=2)
J2 = ["+3V3", "EN", "SVP", "SVN", "IO34", "IO35", "IO32", "IO33", "IO25", "IO26", "IO27", "IO14", "IO12", "IO13", "+5V", "GND"]
J3 = ["GND", "IO23", "IO22", "TXD0", "RXD0", "IO21", "IO19", "IO18", "IO5", "IO17", "IO16", "IO4", "IO0", "IO2", "IO15", "GND"]
def header(ref, at, nets, fp, value):
    j = sh.place("Connector_Generic:Conn_01x%02d" % len(nets), ref, at=at, value=value, footprint=fp)
    for i, nm in enumerate(nets, 1):
        p = j.pin(i)
        if nm == "+3V3" or nm == "+5V":
            x = G(240) if i == 1 else G(230)
            sh.seg(p, (x, p.y)); sh.rail((x, p.y), net=nm)
        elif nm == "GND":
            x = G(240) if i == len(nets) else G(230)
            sh.seg(p, (x, p.y)); sh.gnd((x, p.y))
        else:
            sh.seg(p, (G(240), p.y)); sh.label((G(240), p.y), nm, rot=180)
    return j
j2 = header("J2", (G(250), G(104)), J2, FP_H16, "GPIO L")
j3 = header("J3", (G(250), G(142)), J3, FP_H16, "GPIO R")

# ============================================================ band 3: peripherals
sh.note((G(130), G(168)), "User LED (IO2)", size=2)
Y3 = G(178)
sh.seg((G(140), Y3), (G(146), Y3)); sh.label((G(140), Y3), "IO2", rot=180)
r8 = R("R8", (G(149), Y3), "1k", rot=90); assert r8.pin(1).xy == (G(146), Y3)
d2 = sh.place("Device:LED", "D2", at=(G(156), Y3 + G(3)), rot=90, value="LED blue", footprint=FP_LED)
sh.seg(r8.pin(2), d2.pin("A")); sh.gnd(d2.pin("K"))

sh.note((G(168), G(168)), "I2C header (IO21 SDA / IO22 SCL, 4k7 pull-ups)", size=2)
j4 = sh.place("Connector_Generic:Conn_01x04", "J4", at=(G(200), G(180)), value="I2C", footprint=FP_H4)
p1, p2, p3, p4 = (j4.pin(i) for i in (1, 2, 3, 4))
V3X, V3TOP = G(188), G(172)
sh.seg(p1, (V3X, p1.y)); sh.seg((V3X, p1.y), (V3X, V3TOP)); sh.power("power:+3V3", (V3X, V3TOP))
sh.seg(p2, (G(182), p2.y)); sh.label((G(182), p2.y), "IO21", rot=180)
r9 = R("R9", (G(184), p2.y - G(3)), "4.7k"); assert top(r9)[1].xy == (G(184), p2.y)
sh.seg(p3, (G(170), p3.y)); sh.label((G(170), p3.y), "IO22", rot=180)
r10 = R("R10", (G(174), p3.y - G(3)), "4.7k"); assert top(r10)[1].xy == (G(174), p3.y)
PU = G(174)
sh.seg(top(r10)[0], (G(174), PU)); sh.seg((G(174), PU), (V3X, PU)); sh.seg(top(r9)[0], (G(184), PU))
sh.seg(p4, (G(192), p4.y)); sh.gnd((G(192), p4.y))

sh.note((G(216), G(168)), "1-Wire header (DS18B20 pinout: GND, DQ, 3V3)", size=2)
j5 = sh.place("Connector_Generic:Conn_01x03", "J5", at=(G(236), G(180)), mirror="x", value="1-Wire", footprint=FP_H3)
g5, dq, v5 = (j5.pin(i) for i in (1, 2, 3))
assert g5.y > dq.y > v5.y, (g5.y, dq.y, v5.y)
sh.seg(v5, (G(226), v5.y)); sh.seg((G(226), v5.y), (G(226), V3TOP)); sh.power("power:+3V3", (G(226), V3TOP))
sh.seg(dq, (G(218), dq.y)); sh.label((G(218), dq.y), "IO4", rot=180)
r11 = R("R11", (G(222), dq.y - G(3)), "4.7k"); assert top(r11)[1].xy == (G(222), dq.y)
sh.seg(top(r11)[0], (G(226), top(r11)[0].y))
sh.seg(g5, (G(230), g5.y)); sh.gnd((G(230), g5.y))

# ============================================================ target netlist
T = {}
def net(name, *pins):
    T.setdefault(name, set()).update(pins)
net("+5V", ("J1","A4"),("J1","A9"),("J1","B4"),("J1","B9"),("U2","3"),("C1","1"),("U3","16"),("C7","1"),("J2","15"))
net("+3V3", ("U2","2"),("C2","1"),("R7","1"),("U1","2"),("C3","1"),("C4","1"),("R5","1"),("R6","1"),("J2","1"),
    ("J4","1"),("R9","1"),("R10","1"),("J5","3"),("R11","1"))
net("GND", ("J1","A1"),("J1","A12"),("J1","B1"),("J1","B12"),("J1","SH"),("R1","2"),("R2","2"),("U2","1"),("C1","2"),("C2","2"),
    ("D1","1"),("U3","1"),("C7","2"),("C5","2"),("U1","1"),("U1","15"),("U1","38"),("U1","39"),("C3","2"),("C4","2"),("C6","2"),
    ("SW1",s1b.number),("SW2",s2b.number),("J2","16"),("J3","1"),("J3","16"),("D2","1"),("J4","4"),("J5","1"))
net("CC1", ("J1","A5"),("R1","1")); net("CC2", ("J1","B5"),("R2","1"))
net("USB_D-", ("J1","A7"),("J1","B7"),("U3","6")); net("USB_D+", ("J1","A6"),("J1","B6"),("U3","5"))
net("V3", ("U3","4"),("C5","1"))
net("RXD0", ("U3","2"),("U1","34"),("J3","5")); net("TXD0", ("U3","3"),("U1","35"),("J3","4"))
net("DTR", ("U3","13"),("R3","1"),("Q2","2")); net("RTS", ("U3","14"),("R4","1"),("Q1","2"))
net("Q1B", ("R3","2"),("Q1","1")); net("Q2B", ("R4","2"),("Q2","1"))
net("EN", ("Q1","3"),("U1","3"),("R5","2"),("C6","1"),("SW1",s1t.number),("J2","2"))
net("IO0", ("Q2","3"),("U1","25"),("R6","2"),("SW2",s2t.number),("J3","13"))
net("LEDP", ("R7","2"),("D1","2")); net("LEDU", ("R8","2"),("D2","2"))
net("IO2", ("U1","24"),("R8","1"),("J3","14"))
net("IO4", ("U1","26"),("J3","12"),("J5","2"),("R11","2"))
net("IO21", ("U1","33"),("J3","6"),("J4","2"),("R9","2"))
net("IO22", ("U1","36"),("J3","3"),("J4","3"),("R10","2"))
net("SVP", ("U1","4"),("J2","3")); net("SVN", ("U1","5"),("J2","4"))
simple = {"IO34":(6,"J2",5),"IO35":(7,"J2",6),"IO32":(8,"J2",7),"IO33":(9,"J2",8),"IO25":(10,"J2",9),"IO26":(11,"J2",10),
          "IO27":(12,"J2",11),"IO14":(13,"J2",12),"IO12":(14,"J2",13),"IO13":(16,"J2",14),
          "IO23":(37,"J3",2),"IO19":(31,"J3",7),"IO18":(30,"J3",8),"IO5":(29,"J3",9),"IO17":(28,"J3",10),
          "IO16":(27,"J3",11),"IO15":(23,"J3",15)}
for nm, (upin, j, jp) in simple.items():
    net(nm, ("U1", str(upin)), (j, str(jp)))

for ref, pins in (("J1", ("A8","B8")), ("U1", ("17","18","19","20","21","22","32")), ("U3", ("7","8","9","10","11","12","15"))):
    for pn in pins: net(f"NC_{ref}_{pn}", (ref, pn))
probs = sh.check()
print("check:", probs if probs else "clean")
ok = sh.verify_against(T)
print("verify:", ok)
if len(sys.argv) > 1:
    import json, os
    sh.emit(sys.argv[1]); print("emitted", sys.argv[1])
    pro = os.path.splitext(sys.argv[1])[0] + ".kicad_pro"
    if not os.path.exists(pro):
        cls = {"name": "Default", "clearance": 0.3, "track_width": 0.5, "via_diameter": 0.8, "via_drill": 0.4,
               "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2, "microvia_diameter": 0.3,
               "microvia_drill": 0.1, "wire_width": 6.0, "bus_width": 12.0, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)",
               "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647}
        d = {"meta": {"filename": os.path.basename(pro), "version": 3},
             "sheets": [[sh.uuid, "Root"]],
             "net_settings": {"classes": [cls], "meta": {"version": 4}, "net_colors": None, "netclass_assignments": None, "netclass_patterns": []},
             "board": {"design_settings": {"rules": {"min_clearance": 0.3, "min_track_width": 0.3, "min_copper_edge_clearance": 0.5,
                       "min_hole_clearance": 0.25, "min_via_diameter": 0.6, "min_via_annular_width": 0.15, "min_text_height": 0.8, "min_text_thickness": 0.08},
                       "defaults": {"copper_line_width": 0.5}}, "layer_presets": [], "viewports": []},
             "pcbnew": {"page_layout_descr_file": ""}, "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
             "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []}, "text_variables": {}}
        json.dump(d, open(pro, "w"), indent=2); print("wrote", pro)
