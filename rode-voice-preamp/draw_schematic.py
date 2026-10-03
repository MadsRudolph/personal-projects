#!/usr/bin/env python3
"""Draws rode-preamp.kicad_sch: VideoMic GO -> LM358 x564 -> Uno A0.

Re-run to regenerate the schematic (close KiCad first):
    python3 draw_schematic.py
Uses the kicad-schematic skill's schdraw/idioms.
"""
import os
import sys

sys.path.insert(0, os.path.expanduser("~/.claude/skills/kicad-schematic/scripts"))
from schdraw import Sheet  # noqa: E402
import idioms as I  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "rode-preamp.kicad_sch")
PRO = os.path.join(HERE, "rode-preamp.kicad_pro")


def G(n):
    return round(n * 1.27, 2)


OP = "Amplifier_Operational:LM358"
FP_R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
FP_C = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
FP_CP = "Capacitor_THT:CP_Radial_D5.0mm_P2.50mm"        # 10u 50V, leads bent 2.0 -> 2.5 mm
FP_DIP = "Package_DIP:DIP-8_W7.62mm_LongPads"
FP_J1 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal"
FP_J2 = "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"  # Molex KK male fits

sh = Sheet(paper="A4", title="RØDE VideoMic GO preamp for Arduino Uno A0",
           project="rode-preamp", project_file=PRO if os.path.exists(PRO) else None)


def offset(lib, pin, **kw):
    """Where `pin` sits relative to the part origin (measured on a scratch sheet)."""
    s = Sheet(paper="A4")
    p = s.place(lib, "X1", at=(G(100), G(100)), **kw)
    q = p.pin(pin)
    return q.x - G(100), q.y - G(100)


def place_pin(lib, ref, pin, target, **kw):
    dx, dy = offset(lib, pin, **{k: v for k, v in kw.items() if k in ("rot", "mirror", "unit")})
    return sh.place(lib, ref, at=(round(target[0] - dx, 2), round(target[1] - dy, 2)), **kw)


Y = G(48)                     # signal line into stage A
TY = Y - G(16)                # block titles

# ---------------------------------------------------------------- mic in + plug-in power
j1 = place_pin("Connector:Screw_Terminal_01x02", "J1", "1", (G(20), Y), mirror="y",
               value="MIC IN", footprint=FP_J1)
M = (G(34), Y)
sh.seg(j1.pin(1), M)
sh.gnd(j1.pin(2), drop=G(4))
r1 = sh.place("Device:R", "R1", at=(G(34), Y - G(7)), value="2.2k", footprint=FP_R)
sh.seg(r1.pin(2), M)
sh.rail(r1.pin(1), net="+3V3", rise=G(2))
sh.label((G(28), Y), "MIC")
c1 = sh.place("Device:C_Polarized", "C1", at=(G(44), Y), rot=90, value="10u", footprint=FP_CP)
sh.seg(M, c1.pin(1))
N = (G(54), Y)
sh.seg(c1.pin(2), N)
r2 = sh.place("Device:R", "R2", at=(G(54), Y + G(7)), value="100k", footprint=FP_R)
sh.seg(N, r2.pin(1))
sh.seg(r2.pin(2), (G(54), Y + G(14)))
sh.label((G(54), Y + G(14)), "BIAS", rot=270)
sh.note((G(14), TY), "Mic in + plug-in power", size=1.8)


# ---------------------------------------------------------------- gain stages
def stage(plus_x, y, refs, vals, unit, title):
    """Non-inverting stage, AC-coupled gain leg: gain = 1 + Rf/Rg above the Rg-C corner."""
    u = sh.place(OP, "U1", unit=unit, at=(plus_x + G(6), y + G(2)), value="LM358", footprint=FP_DIP)
    mx, out = plus_x, u.pin("out")
    yfb = y + G(13)
    yc = yfb + G(8)
    rx = out.x + G(4)
    rf = sh.place("Device:R", refs["Rf"], at=(mx + G(6), yfb), rot=90, value=vals["Rf"], footprint=FP_R)
    cf = sh.place("Device:C", refs["Cf"], at=(mx + G(6), yc), rot=90, value=vals["Cf"], footprint=FP_C)
    rg = sh.place("Device:R", refs["Rg"], at=(mx - G(7), yfb), rot=90, value=vals["Rg"], footprint=FP_R)
    cg = sh.place("Device:C_Polarized", refs["Cg"], at=(mx - G(14), yfb + G(5)), value="10u", footprint=FP_CP)
    sh.seg(u.pin("-"), (mx, yfb))
    sh.seg((mx, yfb), rf.pin(1))
    sh.seg((mx, yfb), (mx, yc))
    sh.seg((mx, yc), cf.pin(1))
    sh.seg(rf.pin(2), (rx, yfb))
    sh.seg(cf.pin(2), (rx, yc))
    sh.seg((rx, yc), (rx, yfb))
    sh.seg((rx, yfb), (rx, out.y))
    sh.seg(rg.pin(2), (mx, yfb))
    sh.seg(rg.pin(1), (mx - G(14), yfb))
    sh.seg((mx - G(14), yfb), cg.pin(1))
    sh.gnd(cg.pin(2), drop=G(3))
    sh.note((mx - G(16), TY), title, size=1.8)
    return u, out, rx


ua, outa, rxa = stage(G(84), Y, {"Rf": "R6", "Cf": "C4", "Rg": "R5", "Cg": "C3"},
                      {"Rf": "100k", "Cf": "220p", "Rg": "1.01k"}, 1, "Stage A  x100  (1 + 100k/1.01k)")
sh.seg(N, ua.pin("+"))
YB = outa.y
ub, outb, rxb = stage(G(130), YB, {"Rf": "R8", "Cf": "C6", "Rg": "R7", "Cg": "C5"},
                      {"Rf": "46.4k", "Cf": "470p", "Rg": "10k"}, 2, "Stage B  x5.6  (1 + 46.4k/10k)")
sh.seg(outa, ub.pin("+"))
sh.label((rxa + G(4), outa.y), "OUT_A")

# ---------------------------------------------------------------- anti-alias RC + Uno header
r9 = sh.place("Device:R", "R9", at=(G(160), outb.y), rot=90, value="1.01k", footprint=FP_R)
sh.seg(outb, (rxb, outb.y))
sh.seg((rxb, outb.y), r9.pin(1))
sh.label((rxb + G(2), outb.y), "OUT_B")
O = (G(170), outb.y)
sh.seg(r9.pin(2), O)
c7 = sh.place("Device:C", "C7", at=(G(170), outb.y + G(7)), value="10n", footprint=FP_C)
sh.seg(O, c7.pin(1))
sh.gnd(c7.pin(2), drop=G(3))
# header order 3V3, 5V, A0, GND: 5V and A0 leave adjacent LM358 pins (8, 7), so they sit
# side by side on the header too and GND stays outside them -- keeps the board one-layer
j2 = place_pin("Connector_Generic:Conn_01x04", "J2", "3", (G(190), outb.y), value="TO UNO", footprint=FP_J2)
sh.seg(O, j2.pin(3))
sh.label((G(176), outb.y), "A0")
p1, p2, p4 = j2.pin(1), j2.pin(2), j2.pin(4)
top = p1.y - G(6)
sh.seg(p1, (G(183), p1.y)); sh.seg((G(183), p1.y), (G(183), top))
sh.rail((G(183), top), net="+3V3", rise=G(2))
sh.seg(p2, (G(178), p2.y)); sh.seg((G(178), p2.y), (G(178), top))
sh.rail((G(178), top), net="+5V", rise=G(2))
sh.seg(p4, (G(184), p4.y))
sh.gnd((G(184), p4.y), drop=G(3))
sh.note((G(158), TY), "Anti-alias RC + Uno header", size=1.8)

# connector-fed rails: tell ERC they are driven
FY = Y + G(62)
for i, net in enumerate(("+5V", "+3V3", "GND")):
    a = (G(180) + i * G(13), FY)
    b = (a[0] + G(5), FY)
    sh.seg(a, b)
    if net == "GND":
        sh.gnd(a, drop=G(2))
    else:
        sh.rail(a, net=net, rise=G(2))
    sh.power("power:PWR_FLAG", b)
sh.note((G(178), FY - G(9)), "Rails come in on J2", size=1.8)

# ---------------------------------------------------------------- bias + op-amp supply
vg = I.virtual_ground_divider(sh, (G(20), Y + G(30)), refs={"R1": "R3", "R2": "R4", "C": "C2"},
                              values={"R1": "100k", "R2": "56.2k", "C": "10u"}, rail="+5V",
                              title="Bias 1.8 V  (5V x 56.2k/156.2k)")
sh.label(vg["out"], "BIAS")
sup = I.opamp_supply(sh, (G(140), Y + G(54)), refs={"U": "U1", "Cp": "C8"}, values={"Cp": "100n"},
                     opamp=OP, unit=3, pos="+5V", title="LM358 supply, 100n at pin 8")
for p in sh.parts:
    if p.ref in ("R3", "R4"):
        p.footprint = FP_R
    elif p.ref == "C2":
        p.footprint = FP_CP
    elif p.ref == "C8":
        p.footprint = FP_C
    elif p.ref == "U1":
        p.footprint = FP_DIP

TARGET = {
    "MIC": {("J1", "1"), ("R1", "2"), ("C1", "1")},
    "+3V3": {("R1", "1"), ("J2", "1")},
    "IN_A": {("C1", "2"), ("R2", "1"), ("U1", "3")},
    "BIAS": {("R2", "2"), ("R3", "2"), ("R4", "1"), ("C2", "1")},
    "+5V": {("R3", "1"), ("U1", "8"), ("C8", "1"), ("J2", "2")},
    "GND": {("J1", "2"), ("R4", "2"), ("C2", "2"), ("C3", "2"), ("C5", "2"), ("C7", "2"),
            ("C8", "2"), ("U1", "4"), ("J2", "4")},
    "FB_A": {("U1", "2"), ("R5", "2"), ("R6", "1"), ("C4", "1")},
    "RG_A": {("R5", "1"), ("C3", "1")},
    "OUT_A": {("U1", "1"), ("R6", "2"), ("C4", "2"), ("U1", "5")},
    "FB_B": {("U1", "6"), ("R7", "2"), ("R8", "1"), ("C6", "1")},
    "RG_B": {("R7", "1"), ("C5", "1")},
    "OUT_B": {("U1", "7"), ("R8", "2"), ("C6", "2"), ("R9", "1")},
    "A0": {("R9", "2"), ("C7", "1"), ("J2", "3")},
}

if __name__ == "__main__":
    probs = sh.check()
    for p in probs:
        print("CHECK:", p)
    ok = sh.verify_against(TARGET)
    print("netlist", "OK" if ok else "MISMATCH")
    if ok:
        sh.emit(OUT)
        print("wrote", OUT)
