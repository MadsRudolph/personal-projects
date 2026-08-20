#!/usr/bin/env python3
"""Draw the Class D amplifier schematic and write the matching KiCad project.

Run:  py -3.13 tools/classd_layout.py

Sheet plan (A3, three bands, signal left to right):

    band 1   A power in + 6 V rail   B triangle oscillator   H indicator
    band 2   C input stage           D PWM comparators       E1 complement gen
    band 3   E2 gate driver          F output bridge         G filter + speaker

The root sheet uuid is fixed here and written into classd.kicad_pro as well.
Minting a fresh one while the project names the old one makes Eeschema resolve
every symbol against a path with no instance data, which drops them all out of
connectivity while kicad-cli still reads the netlist as perfect.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SKILL = Path(r"C:\Users\Mads2\.claude\skills\kicad-schematic\scripts")
sys.path.insert(0, str(SKILL))

from schdraw import Sheet          # noqa: E402
import idioms as I                 # noqa: E402

HERE = Path(__file__).resolve().parent
KICAD = HERE.parent
REPO = KICAD.parents[3]
TEMPLATE_PRO = REPO / "Projects" / "Bose Sub Integration" / "hardware" / "kicad" / "subxo.kicad_pro"

SHEET_UUID = "7f3a1c92-4d6b-4e18-9a52-0c8d1e5b3a77"
GRID = 1.27


def G(n):
    return round(n * GRID, 4)


sh = Sheet(paper="A2", title="Class D amplifier - mono BTL, 12 V, 4 ohm",
           project="classd", version=10, uuid=SHEET_UUID)

R = "Device:R"
C = "Device:C"
CP = "Device:C_Polarized"
OP = "Amplifier_Operational:TL074"
CMP = "Comparator:LM311"
INV = "4xxx:4049"
FET = "Transistor_FET:IRF540N"
TERM = "Connector:Screw_Terminal_01x02"
TP = "Connector:TestPoint"

# ===========================================================================
# A  Power input, +12 V rail, 6 V virtual ground
# ===========================================================================
sh.note((G(10), G(10)), "A  Power in and 6 V virtual ground", size=2)

J1 = sh.place(TERM, "J1", at=(G(14), G(26)), rot=180, value="PWR IN 12V")
# pin 2 = +12 V (upper), pin 1 = 0 V
sh.seg(J1.pin("2"), (G(26), G(24)))
sh.seg((G(26), G(24)), (G(26), G(18)))
sh.seg((G(26), G(18)), (G(44), G(18)))                  # +12 V bus of block A
sh.rail((G(30), G(18)), net="+12V", rise=G(4))
sh.seg((G(38), G(18)), (G(38), G(14)))
sh.power("power:PWR_FLAG", (G(38), G(14)))

sh.seg(J1.pin("1"), (G(20), G(26)))
sh.seg((G(20), G(26)), (G(20), G(34)))
sh.seg((G(20), G(34)), (G(30), G(34)))
sh.seg((G(30), G(34)), (G(30), G(30)))
sh.power("power:PWR_FLAG", (G(30), G(30)))
sh.gnd((G(20), G(34)), drop=G(4))

# half-rail divider, reservoir, buffer
R1 = sh.place(R, "R1", at=(G(44), G(24)), value="10k")
R2 = sh.place(R, "R2", at=(G(44), G(38)), value="10k")
C1 = sh.place(CP, "C1", at=(G(52), G(36)), value="100u")
sh.seg((G(44), G(18)), R1.pin("1"))
sh.seg(R1.pin("2"), R2.pin("1"))                        # the 6 V node
sh.seg((G(44), G(31)), (G(58), G(31)))
sh.seg((G(52), G(31)), C1.pin("1"))
I.gnd_rail(sh, [R2.pin("2"), C1.pin("2")], G(43))

U1A = sh.place(OP, "U1", unit=1, at=(G(64), G(33)), value="TL074")
sh.seg((G(58), G(31)), U1A.pin("+"))
sh.seg(U1A.pin("out"), (G(82), G(33)))                  # buffered 6 V out
sh.seg((G(74), G(33)), (G(74), G(42)))                  # follower loop, below
sh.seg((G(74), G(42)), (G(58), G(42)))
sh.seg((G(58), G(42)), U1A.pin("-"))
sh.label((G(82), G(33)), "VGND")
sh.note((G(14), G(72)), "6 V = 12 V / 2, buffered, so every stage shares "
                        "one quiet reference.", size=1.27)

# TL074 package supply (one per package, not per section)
U1P = sh.place(OP, "U1", unit=5, at=(G(64), G(60)), value="TL074")
C2 = sh.place(C, "C2", at=(G(76), G(60)), value="100n")
sh.seg(U1P.pin("V+"), (G(62), G(50)))
sh.seg((G(62), G(50)), (G(76), G(50)))
sh.seg((G(76), G(50)), C2.pin("1"))
sh.rail((G(68), G(50)), net="+12V", rise=G(4))
sh.seg(U1P.pin("V-"), (G(62), G(70)))
sh.seg((G(62), G(70)), (G(76), G(70)))
sh.seg(C2.pin("2"), (G(76), G(70)))
sh.gnd((G(68), G(70)), drop=G(4))

# ===========================================================================
# B  Triangle oscillator, ~250 kHz
# ===========================================================================
sh.note((G(88), G(10)), "B  Triangle carrier ~250 kHz  (LM311 Schmitt + "
                        "TL074 integrator)", size=2)

R4 = sh.place(R, "R4", at=(G(96), G(31)), rot=90, value="3k9")
RV1 = sh.place("Device:R_Trim", "RV1", at=(G(104), G(31)), rot=90, value="10k")
U1B = sh.place(OP, "U1", unit=2, at=(G(120), G(29)), value="TL074")
C12 = sh.place(C, "C12", at=(G(122), G(42)), rot=90, value="470p")

sh.seg(R4.pin("2"), RV1.pin("1"))
sh.seg(RV1.pin("2"), U1B.pin("-"))
sh.seg(U1B.pin("-"), (G(114), G(42)))                   # integrating cap, below
sh.seg((G(114), G(42)), C12.pin("1"))
sh.seg(U1B.pin("out"), (G(139), G(29)))                 # TRI run
sh.seg((G(130), G(29)), (G(130), G(42)))
sh.seg(C12.pin("2"), (G(130), G(42)))
sh.label((G(136), G(29)), "TRI")
TP1 = sh.place(TP, "TP1", at=(G(134), G(23)))
sh.seg((G(134), G(29)), TP1.pin("1"))

# comparator with hysteresis: R5 from TRI, R6 from SQ, both onto '+'
R5 = sh.place(R, "R5", at=(G(142), G(29)), rot=90, value="10k")
U2 = sh.place(CMP, "U2", at=(G(162), G(31)), value="LM311")
sh.seg(R5.pin("2"), U2.pin("+"))
R6 = sh.place(R, "R6", at=(G(150), G(48)), value="27k4")
sh.seg(R6.pin("1"), (G(150), G(29)))
R7 = sh.place(R, "R7", at=(G(176), G(26)), value="1k")
sh.seg(U2.pin("out"), (G(184), G(31)))                  # SQ run
sh.seg(R7.pin("2"), (G(176), G(31)))
sh.rail(R7.pin("1"), net="+12V", rise=G(4))
sh.seg((G(184), G(31)), (G(184), G(62)))                # SQ back along the bottom
sh.seg((G(184), G(62)), (G(88), G(62)))
sh.seg((G(88), G(62)), (G(88), G(31)))
sh.seg((G(88), G(31)), R4.pin("1"))
sh.seg(R6.pin("2"), (G(150), G(62)))
sh.label((G(118), G(62)), "SQ")
sh.nc(U2.pin("BAL"))
sh.nc(U2.pin("STRB"))
sh.rail(U2.pin("V+"), net="+12V", rise=G(4))
I.gnd_rail(sh, [U2.pin("V-"), U2.pin("GND")], G(44), x_sym=G(161))

C7 = sh.place(C, "C7", at=(G(198), G(24)), value="100n")
sh.rail(C7.pin("1"), net="+12V", rise=G(4))
sh.gnd(C7.pin("2"), drop=G(4))

# 6 V reference into both stages
sh.seg(U1B.pin("+"), (G(108), G(27)))
sh.label((G(108), G(27)), "VGND")
sh.seg(U2.pin("-"), (G(152), G(33)))
sh.seg((G(152), G(33)), (G(152), G(40)))
sh.label((G(152), G(40)), "VGND")

sh.note((G(90), G(68)), "f = Vsw / (8 R C):  R4+RV1 ~ 5k6 with C12 470p gives "
                        "250 kHz;  R5/R6 set the +/-2 V window about 6 V",
        size=1.27)

# ===========================================================================
# H  Power indicator
# ===========================================================================
sh.note((G(240), G(10)), "H  Indicator and bring-up", size=2)
R3 = sh.place(R, "R3", at=(G(248), G(24)), value="4k7")
D1 = sh.place("Device:LED", "D1", at=(G(248), G(36)), rot=90, value="PWR")
sh.rail(R3.pin("1"), net="+12V", rise=G(4))
sh.seg(R3.pin("2"), D1.pin("A"))
sh.gnd(D1.pin("K"), drop=G(4))

sh.note((G(262), G(20)),
        "Test points TP1..TP5 are solder lugs on TRI, PWM_A,", size=1.27)
sh.note((G(262), G(23)),
        "both switching nodes and the filtered output.", size=1.27)
sh.note((G(262), G(28)),
        "Bring up with NO MOSFETs fitted: check 12 V and 6 V,", size=1.27)
sh.note((G(262), G(31)),
        "then the triangle, then both PWM outputs, then the", size=1.27)
sh.note((G(262), G(34)),
        "HIP4082 dead time on a scope.  Only then fit Q1..Q4,", size=1.27)
sh.note((G(262), G(37)),
        "on a current-limited supply into a dummy load.", size=1.27)

# ===========================================================================
# C  Input stage: AC couple, level pot, buffer, inverter
# ===========================================================================
sh.note((G(10), G(78)), "C  Input stage  (level -> buffer -> inverter)",
        size=2)

J2 = sh.place(TERM, "J2", at=(G(14), G(102)), rot=180, value="LINE IN")
sh.seg(J2.pin("1"), (G(22), G(102)))
sh.seg((G(22), G(102)), (G(22), G(108)))
sh.gnd((G(22), G(108)), drop=G(4))

C3 = sh.place(C, "C3", at=(G(30), G(100)), rot=90, value="1u5")
sh.seg(J2.pin("2"), C3.pin("1"))
RV2 = sh.place("Device:R_Potentiometer", "RV2", at=(G(42), G(103)), value="10k")
sh.seg(C3.pin("2"), RV2.pin("1"))
sh.seg(RV2.pin("3"), (G(42), G(112)))
sh.label((G(42), G(112)), "VGND")

U1C = sh.place(OP, "U1", unit=3, at=(G(62), G(105)), value="TL074")
sh.seg(RV2.pin("2"), (G(56), G(103)))
sh.seg((G(56), G(103)), U1C.pin("+"))
sh.seg(U1C.pin("out"), (G(80), G(105)))
sh.seg((G(74), G(105)), (G(74), G(114)))
sh.seg((G(74), G(114)), (G(56), G(114)))
sh.seg((G(56), G(114)), U1C.pin("-"))
sh.label((G(78), G(105)), "AUDIO_P")

# unity inverter -> AUDIO_N
sh.seg((G(80), G(105)), (G(80), G(122)))
R8 = sh.place(R, "R8", at=(G(88), G(122)), rot=90, value="10k")
sh.seg((G(80), G(122)), R8.pin("1"))
U1D = sh.place(OP, "U1", unit=4, at=(G(106), G(120)), value="TL074")
sh.seg(R8.pin("2"), U1D.pin("-"))
R9 = sh.place(R, "R9", at=(G(106), G(132)), rot=90, value="10k")
sh.seg(U1D.pin("-"), (G(100), G(132)))
sh.seg((G(100), G(132)), R9.pin("1"))
sh.seg(U1D.pin("out"), (G(118), G(120)))
sh.seg((G(114), G(120)), (G(114), G(132)))
sh.seg(R9.pin("2"), (G(114), G(132)))
sh.label((G(118), G(120)), "AUDIO_N")
sh.seg(U1D.pin("+"), (G(92), G(118)))
sh.label((G(92), G(118)), "VGND")
sh.note((G(14), G(140)), "AUDIO_P and AUDIO_N are equal and opposite about "
                         "6 V - that is what swings the bridge both ways.",
        size=1.27)

# ===========================================================================
# D  PWM comparators
# ===========================================================================
sh.note((G(126), G(78)), "D  PWM comparators  (audio vs triangle)", size=2)

U3 = sh.place(CMP, "U3", at=(G(150), G(96)), value="LM311")
U4 = sh.place(CMP, "U4", at=(G(150), G(130)), value="LM311")

sh.seg((G(138), G(94)), U3.pin("+"))
sh.label((G(138), G(94)), "AUDIO_P")
sh.seg((G(138), G(128)), U4.pin("+"))
sh.label((G(138), G(128)), "AUDIO_N")

sh.seg(U3.pin("-"), (G(136), G(98)))                    # one triangle, both '-'
sh.seg((G(136), G(98)), (G(136), G(132)))
sh.seg((G(136), G(132)), U4.pin("-"))
sh.label((G(136), G(114)), "TRI")

for u, rref, y in ((U3, "R10", G(96)), (U4, "R11", G(130))):
    rp = sh.place(R, rref, at=(G(164), y - G(6)), value="1k")
    sh.seg(u.pin("out"), (G(182), y))
    sh.seg(rp.pin("2"), (G(164), y))
    sh.rail(rp.pin("1"), net="+12V", rise=G(4))
    sh.rail(u.pin("V+"), net="+12V", rise=G(4))
    I.gnd_rail(sh, [u.pin("V-"), u.pin("GND")], y + G(12), x_sym=G(149))
    sh.nc(u.pin("BAL"))
    sh.nc(u.pin("STRB"))

sh.label((G(182), G(96)), "PWM_A")
sh.label((G(182), G(130)), "PWM_B")
TP2 = sh.place(TP, "TP2", at=(G(176), G(88)))
sh.seg((G(176), G(96)), TP2.pin("1"))

C8 = sh.place(C, "C8", at=(G(196), G(90)), value="100n")
sh.rail(C8.pin("1"), net="+12V", rise=G(4))
sh.gnd(C8.pin("2"), drop=G(4))
C9 = sh.place(C, "C9", at=(G(196), G(124)), value="100n")
sh.rail(C9.pin("1"), net="+12V", rise=G(4))
sh.gnd(C9.pin("2"), drop=G(4))

# ===========================================================================
# E1  Complement generation, CD4049 (12 V CMOS - NOT 74HC)
# ===========================================================================
sh.note((G(214), G(78)), "E1  Complement generation  (CD4049)", size=2)

U5A = sh.place(INV, "U5", unit=1, at=(G(238), G(94)), value="CD4049UBE")
U5B = sh.place(INV, "U5", unit=2, at=(G(262), G(94)), value="CD4049UBE")
U5C = sh.place(INV, "U5", unit=3, at=(G(238), G(120)), value="CD4049UBE")
U5D = sh.place(INV, "U5", unit=4, at=(G(262), G(120)), value="CD4049UBE")
U5E = sh.place(INV, "U5", unit=5, at=(G(238), G(142)), value="CD4049UBE")
U5F = sh.place(INV, "U5", unit=6, at=(G(262), G(142)), value="CD4049UBE")

sh.seg((G(222), G(94)), U5A.pin("3"))
sh.label((G(222), G(94)), "PWM_A")
sh.seg(U5A.pin("2"), U5B.pin("5"))
sh.label((G(250), G(94)), "A_LO")
sh.seg(U5B.pin("4"), (G(282), G(94)))
sh.label((G(282), G(94)), "A_HI")

sh.seg((G(222), G(120)), U5C.pin("7"))
sh.label((G(222), G(120)), "PWM_B")
sh.seg(U5C.pin("6"), U5D.pin("9"))
sh.label((G(250), G(120)), "B_LO")
sh.seg(U5D.pin("10"), (G(282), G(120)))
sh.label((G(282), G(120)), "B_HI")

# the two spare sections: inputs tied off, outputs open
sh.seg(U5E.pin("11"), (G(226), G(142)))
sh.seg((G(226), G(142)), (G(226), G(148)))
sh.seg(U5F.pin("14"), (G(250), G(142)))
sh.seg((G(250), G(142)), (G(250), G(148)))
sh.seg((G(226), G(148)), (G(250), G(148)))
sh.gnd((G(238), G(148)), drop=G(4))
sh.nc(U5E.pin("12"))
sh.nc(U5F.pin("15"))

U5P = sh.place(INV, "U5", unit=7, at=(G(300), G(96)), value="CD4049UBE")
C10 = sh.place(C, "C10", at=(G(312), G(92)), value="100n")
sh.seg(U5P.pin("VCC"), (G(300), G(82)))
sh.seg((G(300), G(82)), (G(312), G(82)))
sh.seg((G(312), G(82)), C10.pin("1"))
sh.rail((G(306), G(82)), net="+12V", rise=G(4))
I.gnd_rail(sh, [U5P.pin("VSS"), C10.pin("2")], G(108))

# ===========================================================================
# E2  HIP4082 gate driver
# ===========================================================================
sh.note((G(10), G(154)), "E2  Gate driver  HIP4082IPZ", size=2)

U6 = sh.place("Driver_FET:HIP4082xP", "U6", at=(G(60), G(190)),
              value="HIP4082IPZ")

for pin, name in (("AHI", "A_HI"), ("ALI", "A_LO"),
                  ("BHI", "B_HI"), ("BLI", "B_LO")):
    p = U6.pin(pin)
    sh.seg((G(30), p.y), p)
    sh.label((G(30), p.y), name)

# dead time: one resistor, 3k3 ~ 200 ns
R12 = sh.place(R, "R12", at=(G(42), G(204)), value="3k3")
sh.seg(U6.pin("DEL"), (G(42), G(198)))
sh.seg((G(42), G(198)), R12.pin("1"))
sh.gnd(R12.pin("2"), drop=G(4))

# DIS is active high - hold it down
R13 = sh.place(R, "R13", at=(G(26), G(201)), value="10k")
sh.seg(U6.pin("DIS"), (G(26), G(182)))
sh.seg((G(26), G(182)), R13.pin("1"))
sh.gnd(R13.pin("2"), drop=G(4))

sh.seg(U6.pin("VSS"), (G(60), G(208)))
sh.gnd((G(60), G(208)), drop=G(4))

# +12 V bus feeding VDD, the decoupling and both bootstrap diodes
sh.seg(U6.pin("VDD"), (G(60), G(162)))
sh.seg((G(40), G(162)), (G(112), G(162)))
sh.rail((G(68), G(162)), net="+12V", rise=G(4))
C11 = sh.place(C, "C11", at=(G(40), G(168)), value="100n")
sh.seg((G(40), G(162)), C11.pin("1"))
sh.gnd(C11.pin("2"), drop=G(4))

D3 = sh.place("Device:D_Schottky", "D3", at=(G(100), G(168)), rot=90,
              value="1N5817")
D2 = sh.place("Device:D_Schottky", "D2", at=(G(112), G(168)), rot=90,
              value="1N5817")
sh.seg((G(100), G(162)), D3.pin("A"))
sh.seg((G(112), G(162)), D2.pin("A"))

# B channel bootstrap: BHB -> D3 / C6 -> BHS
C6 = sh.place(C, "C6", at=(G(100), G(186)), value="100n")
sh.seg(U6.pin("BHB"), (G(100), G(182)))
sh.seg((G(100), G(182)), D3.pin("K"))
sh.seg((G(100), G(182)), C6.pin("1"))
sh.seg(C6.pin("2"), (G(100), G(190)))
sh.seg(U6.pin("BHS"), (G(100), G(190)))
sh.label((G(88), G(190)), "SW_B")

# A channel bootstrap: AHB steps up over the BHB run, then D2 / C5 -> AHS
C5 = sh.place(C, "C5", at=(G(124), G(190)), value="100n")
sh.seg(U6.pin("AHB"), (G(74), G(184)))
sh.seg((G(74), G(184)), (G(74), G(180)))
sh.seg((G(74), G(180)), (G(124), G(180)))
sh.seg((G(112), G(180)), D2.pin("K"))
sh.seg((G(124), G(180)), C5.pin("1"))
sh.seg(C5.pin("2"), (G(124), G(198)))
sh.seg(U6.pin("AHS"), (G(136), G(198)))
sh.label((G(136), G(198)), "SW_A")

for pin, name in (("BHO", "G_BH"), ("BLO", "G_BL"),
                  ("ALO", "G_AL"), ("AHO", "G_AH")):
    p = U6.pin(pin)
    sh.seg(p, (G(86), p.y))
    sh.label((G(86), p.y), name)

sh.note((G(10), G(216)), "R12 = 3k3 on DEL gives ~200 ns dead time "
                         "(datasheet: 10k -> 0.5 us, 100k -> 4.5 us).",
        size=1.27)
sh.note((G(10), G(220)), "DIS is active high, so R13 holds it down.",
        size=1.27)

# ===========================================================================
# F  Output bridge
# ===========================================================================
sh.note((G(150), G(154)), "F  Output bridge  4 x IRF540N", size=2)

sh.seg((G(176), G(162)), (G(230), G(162)))              # +12 V across the top
sh.seg((G(166), G(208)), (G(230), G(208)))              # return across the bottom
sh.rail((G(190), G(162)), net="+12V", rise=G(4))
sh.gnd((G(190), G(208)), drop=G(4))

C4 = sh.place(CP, "C4", at=(G(230), G(185)), value="2200u")
sh.seg((G(230), G(162)), C4.pin("1"))
sh.seg(C4.pin("2"), (G(230), G(208)))

def leg(qh, ql, rgh, rgl, rph, rpl, x, xg, lbl_h, lbl_l, tp, tpx, netlbl):
    Qh = sh.place(FET, qh, at=(G(x), G(174)), value="IRF540N")
    Ql = sh.place(FET, ql, at=(G(x), G(194)), value="IRF540N")
    xs = Qh.pin("D").x                                   # the leg's own column
    sh.seg(Qh.pin("D"), (xs, G(162)))
    sh.seg(Qh.pin("S"), Ql.pin("D"))                     # switching node
    sh.seg(Ql.pin("S"), (xs, G(208)))

    Rh = sh.place(R, rgh, at=(G(xg), G(174)), rot=90, value="22R1")
    Rl = sh.place(R, rgl, at=(G(xg), G(194)), rot=90, value="22R1")
    sh.seg((G(xg - 8), G(174)), Rh.pin("1"))
    sh.label((G(xg - 8), G(174)), lbl_h)
    sh.seg(Rh.pin("2"), Qh.pin("G"))
    sh.seg((G(xg - 8), G(194)), Rl.pin("1"))
    sh.label((G(xg - 8), G(194)), lbl_l)
    sh.seg(Rl.pin("2"), Ql.pin("G"))

    Ph = sh.place(R, rph, at=(G(xg + 6), G(182)), value="10k")
    Pl = sh.place(R, rpl, at=(G(xg + 6), G(202)), value="10k")
    sh.seg((G(xg + 6), G(174)), Ph.pin("1"))
    sh.seg(Ph.pin("2"), (xs, G(185)))                    # high side: gate to source
    sh.seg((G(xg + 6), G(194)), Pl.pin("1"))
    sh.seg(Pl.pin("2"), (G(xg + 6), G(208)))             # low side: gate to 0 V

    T = sh.place(TP, tp, at=(G(tpx), G(182)))
    sh.seg((xs, G(182)), T.pin("1"))
    sh.label((G(tpx - 6), G(182)), netlbl)

leg("Q1", "Q2", "R14", "R15", "R18", "R19", 174, 160, "G_AH", "G_AL",
    "TP3", 186, "SW_A")
leg("Q3", "Q4", "R16", "R17", "R20", "R21", 212, 198, "G_BH", "G_BL",
    "TP4", 224, "SW_B")

# ===========================================================================
# G  Output filter, Zobel, speaker
# ===========================================================================
sh.note((G(242), G(154)), "G  Output filter + Zobel", size=2)

L1 = sh.place("Device:L", "L1", at=(G(254), G(172)), rot=90, value="15u")
L2 = sh.place("Device:L", "L2", at=(G(254), G(188)), rot=90, value="15u")
sh.seg((G(244), G(172)), L1.pin("1"))
sh.label((G(244), G(172)), "SW_A")
sh.seg((G(244), G(188)), L2.pin("1"))
sh.label((G(244), G(188)), "SW_B")

sh.seg(L1.pin("2"), (G(302), G(172)))
sh.seg(L2.pin("2"), (G(296), G(188)))

C13 = sh.place(C, "C13", at=(G(272), G(180)), value="820n")
sh.seg((G(272), G(172)), C13.pin("1"))
sh.seg(C13.pin("2"), (G(272), G(188)))

R22 = sh.place(R, "R22", at=(G(286), G(177)), value="10R 5W")
C14 = sh.place(C, "C14", at=(G(286), G(185)), value="100n")
sh.seg((G(286), G(172)), R22.pin("1"))
sh.seg(R22.pin("2"), C14.pin("1"))
sh.seg(C14.pin("2"), (G(286), G(188)))

TP5 = sh.place(TP, "TP5", at=(G(264), G(166)))
sh.seg((G(264), G(172)), TP5.pin("1"))
sh.label((G(264), G(169)), "OUT_P")

J3 = sh.place(TERM, "J3", at=(G(306), G(172)), value="SPEAKER 4R")
sh.seg((G(296), G(188)), (G(296), G(174)))
sh.seg((G(296), G(174)), J3.pin("2"))

sh.note((G(120), G(216)), "No output DC blocking cap and no speaker ground - "
                          "the load floats between the two legs.", size=1.27)
sh.note((G(120), G(220)), "L1/L2 are hand-wound on shop toroids: the stocked "
                          "radial chokes saturate below the 3 A peak.",
        size=1.27)

# ===========================================================================
# Spread the blocks over the A2 sheet.
#
# The eight blocks were composed to A3 proportions.  Rather than re-derive
# every coordinate for the larger sheet, each block is translated bodily into
# its place on A2: the geometry inside a block -- which is the part that was
# actually designed -- is untouched, and only the gaps between blocks grow.
#
# This is safe precisely because no wire crosses a block boundary; every
# cross-block connection on this sheet is a net label.  The transform asserts
# that (no wire may straddle a cut) and `verify_against()` re-checks the whole
# netlist afterwards, so a mis-drawn region cannot pass silently.
#
# How far it can go is capped by the drawing, not the sheet: 71 parts spread
# across the whole of A2 fall below sch_score's 0.05 parts/cm2 floor, which is
# the scorer correctly observing that A2 is a bigger sheet than this board
# needs.  These offsets take the parts from 36% to 57% of the page, which is
# as far as that gate allows.
# ===========================================================================
BAND_CUT = (95.0, 194.0)                     # y, between the three bands
COL_CUT = {                                   # x cuts within each band
    0: (110.0, 290.0),                        # A | B | H
    1: (160.0, 270.0),                        # C | D | E1
    2: (185.0, 302.0),                        # E2 | F | G
}
OFFSET = {                                    # (dx, dy) per (band, column)
    (0, 0): (0, 0),          (0, 1): (G(32), 0),        (0, 2): (G(66), 0),
    (1, 0): (0, G(25)),      (1, 1): (G(44), G(25)),    (1, 2): (G(35), G(25)),
    (2, 0): (0, G(50)),      (2, 1): (G(51), G(50)),    (2, 2): (G(42), G(50)),
}
GLOBAL = (G(52), G(26))                       # centre the result on the sheet


def spread_pt(x, y):
    """Where a pre-spread point ends up. Post-emit tweaks must go through this."""
    dx, dy = OFFSET[_region(x, y)]
    return (round(x + dx + GLOBAL[0], 4), round(y + dy + GLOBAL[1], 4))


def _region(x, y):
    band = 0 if y < BAND_CUT[0] else (1 if y < BAND_CUT[1] else 2)
    cuts = COL_CUT[band]
    col = 0 if x < cuts[0] else (1 if x < cuts[1] else 2)
    return band, col


def spread():
    """Translate each block into its place on A2. Raises if a wire straddles."""
    for i, (a, b) in enumerate(sh.wires):
        ra, rb = _region(*a), _region(*b)
        if ra != rb:
            raise SystemExit(f"wire {a} -> {b} straddles blocks {ra} and {rb}; "
                             f"move a cut or the wire")

    # Round every translated coordinate the same way. Wire endpoints are
    # stored rounded, so a pin left at 419.09999999999997 no longer lands on
    # the wire that ends at 419.1 and the connection silently comes apart.
    def shift(pt):
        return spread_pt(pt[0], pt[1])

    for part in sh.parts:
        ox, oy = part.x, part.y
        nx, ny = spread_pt(ox, oy)
        dx, dy = nx - ox, ny - oy
        part.x, part.y = nx, ny
        for pin in part._pins:
            pin.x, pin.y = round(pin.x + dx, 4), round(pin.y + dy, 4)

    sh.wires = [(shift(a), shift(b)) for a, b in sh.wires]
    sh.labels = [(t, *shift((x, y)), r, k) for (t, x, y, r, k) in sh.labels]
    sh.texts = [(t, *shift((x, y)), sz) for (t, x, y, sz) in sh.texts]
    sh.no_connects = [shift(pt) for pt in sh.no_connects]


# ===========================================================================
# Footprints.  Through-hole throughout, sized for isolation milling with an
# 0.8 mm end mill: DIP parts take the LongPads variants, and the TO-220s, the
# LED and the hand-wound toroids take the narrowed-pad footprints vendored in
# lib/.  Applied per refdes after the sheet is built, so every unit of a
# multi-unit package (U1 has five, U5 has seven) carries the same value --
# ERC treats a disagreement between units as an error.
# ===========================================================================
R_AXIAL = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
C_DISC = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"

FOOTPRINTS = {
    # resistors: all E96 1/4 W axial except the Zobel, which is a 5 W wirewound
    **{f"R{n}": R_AXIAL for n in range(1, 22)},
    "R22": "Resistor_THT:R_Axial_Power_L25.0mm_W9.0mm_P30.48mm",
    "RV1": "Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical",
    # the RK09K's 0.70 mm pin gap is below the 0.8 mm end mill and cannot be
    # isolated; the CA14V's 5 mm pitch clears it easily.  Measure the pot the
    # shop actually supplies before committing copper.
    "RV2": "Potentiometer_THT:Potentiometer_ACP_CA14V-15_Vertical",

    # ceramics: decoupling, both bootstraps, and the oscillator timing cap
    **{f"C{n}": C_DISC for n in (2, 5, 6, 7, 8, 9, 10, 11, 12)},
    "C1": "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm",
    "C4": "Capacitor_THT:CP_Radial_D18.0mm_P7.50mm",
    "C3": "Capacitor_THT:C_Rect_L13.0mm_W5.0mm_P10.00mm_FKS3_FKP3_MKS4",
    "C13": "Capacitor_THT:C_Rect_L16.5mm_W5.0mm_P15.00mm_MKT",
    "C14": "Capacitor_THT:C_Rect_L7.0mm_W3.5mm_P5.00mm",

    "D1": "energy_system:LED_D3.0mm_P5.08mm_LaserPads",
    **{f"D{n}": "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal" for n in (2, 3)},
    **{f"Q{n}": "energy_system:TO-220-3_Vertical_LaserPads" for n in range(1, 5)},
    **{f"L{n}": "energy_system:"
                "L_Toroid_Vertical_L34.5mm_W15.0mm_P28.20mm_LaserPads"
       for n in (1, 2)},

    # every IC is socketed - never solder these directly
    "U1": "Package_DIP:DIP-14_W7.62mm_LongPads",
    **{f"U{n}": "Package_DIP:DIP-8_W7.62mm_LongPads" for n in (2, 3, 4)},
    **{f"U{n}": "Package_DIP:DIP-16_W7.62mm_LongPads" for n in (5, 6)},

    **{f"J{n}": "TerminalBlock:TerminalBlock_bornier-2_P5.08mm"
       for n in (1, 2, 3)},
    # solder lugs (shop "Loddeflig 3MM")
    **{f"TP{n}": "TestPoint:TestPoint_THTPad_2.5x2.5mm_Drill1.2mm"
       for n in range(1, 6)},
}


def apply_footprints():
    missing = set()
    for part in sh.parts:
        if getattr(part, "is_power_port", False):
            continue
        fp = FOOTPRINTS.get(part.ref)
        if fp is None:
            missing.add(part.ref)
        else:
            part.footprint = fp
    return missing


# ===========================================================================
# Simulation index
#
# The testbenches are deliberately NOT hierarchical sheets of this schematic.
# A hierarchy is one electrical design: attaching sim_b_triangle as a sheet
# was tried, and the netlist showed the testbench's supply V1 welded straight
# onto the board's +12V rail, its sources landing in the BOM ready to be
# pushed onto the PCB, and -- worst -- its U1/R4/R5 silently merging with the
# board's parts of the same name, quietly rewiring real components.
#
# Each testbench is its own project instead, reached by the hyperlinks below.
# ===========================================================================
SIM_LINKS = [
    ("sim_a_vground", "A  rails and the 6 V virtual ground"),
    ("sim_b_triangle", "B  triangle carrier, ~250 kHz"),
    ("sim_c_input", "C  input stage, buffer and inverter"),
    ("sim_d_pwm", "D  PWM comparators"),
    ("sim_e_driver", "E  complement generation and gate driver"),
    ("sim_f_bridge", "F  output bridge, LC filter and Zobel"),
    ("sim_g_chain", "G  the whole chain, audio in to speaker out"),
]


def sim_index(sh):
    """A clickable index of the simulation testbenches.

    Seven lines at 3 grid steps: the block F notes end at x=226 and the A2
    frame's bottom margin starts around y=323, so this is the space there is.
    """
    x, y = G(250), G(295)
    sh.note((x, y), "SIMULATION  (separate projects - click to open)", size=2)
    links = {}
    for i, (name, desc) in enumerate(SIM_LINKS):
        text = f"{desc}   ->  sim/{name}.kicad_sch"
        sh.note((x, y + G(5) + G(3) * i), text, size=1.27)
        # Point at the SHEET, not the project. Windows opens .kicad_pro with
        # kicad.exe -- the project manager -- which lands you one click short
        # of the drawing. .kicad_sch opens eeschema.exe directly on it, which
        # is the behaviour a hierarchical sheet would have given us. Eeschema
        # still picks up the matching .kicad_pro beside it, so the netclass
        # and the simulator workbook come with it.
        links[text] = f"file:sim/{name}.kicad_sch"
    return links


def add_hrefs(path, links):
    """Turn chosen text items into hyperlinks.

    KiCad 10 carries a schematic hyperlink as (href "...") INSIDE the text
    item's (effects ...) block. It is not a sibling of (uuid ...), and it is
    not spelled (hyperlink ...) as it is on the PCB -- both of those make
    Eeschema refuse to load the file outright.
    """
    txt = Path(path).read_text(encoding="utf-8")
    for text, url in links.items():
        i = txt.index(f'(text "{text}"')
        e = txt.index("(effects", i)
        depth, j = 0, e
        while True:
            if txt[j] == "(":
                depth += 1
            elif txt[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        txt = txt[:j] + '\n\t\t\t(href "' + url + '")\n\t\t' + txt[j:]
    Path(path).write_text(txt, encoding="utf-8")


# ===========================================================================
# What the drawing is supposed to say, node by node.
# ===========================================================================
TARGET = {
    "+12V": {("J1", "2"), ("R1", "1"), ("U1", "4"), ("C2", "1"),
             ("U2", "8"), ("R7", "1"), ("C7", "1"),
             ("U3", "8"), ("R10", "1"), ("C8", "1"),
             ("U4", "8"), ("R11", "1"), ("C9", "1"),
             ("U5", "1"), ("C10", "1"),
             ("U6", "12"), ("C11", "1"), ("D2", "2"), ("D3", "2"),
             ("Q1", "2"), ("Q3", "2"), ("C4", "1"), ("R3", "1")},
    "GND": {("J1", "1"), ("R2", "2"), ("C1", "2"), ("U1", "11"), ("C2", "2"),
            ("U2", "1"), ("U2", "4"), ("C7", "2"),
            ("U3", "1"), ("U3", "4"), ("C8", "2"),
            ("U4", "1"), ("U4", "4"), ("C9", "2"),
            ("U5", "8"), ("U5", "11"), ("U5", "14"), ("C10", "2"),
            ("U6", "6"), ("C11", "2"), ("R12", "2"), ("R13", "2"),
            ("Q2", "3"), ("Q4", "3"), ("R19", "2"), ("R21", "2"),
            ("C4", "2"), ("D1", "1"), ("J2", "1")},
    "VG": {("R1", "2"), ("R2", "1"), ("C1", "1"), ("U1", "3")},
    "VGND": {("U1", "1"), ("U1", "2"), ("U1", "5"), ("U2", "3"),
             ("RV2", "3"), ("U1", "12")},
    "SQ": {("U2", "7"), ("R7", "2"), ("R4", "1"), ("R6", "2")},
    "RTMID": {("R4", "2"), ("RV1", "1")},
    "INT": {("RV1", "2"), ("U1", "6"), ("C12", "1")},
    "TRI": {("U1", "7"), ("C12", "2"), ("R5", "1"), ("TP1", "1"),
            ("U3", "3"), ("U4", "3")},
    "HYST": {("R5", "2"), ("R6", "1"), ("U2", "2")},
    "LEDA": {("R3", "2"), ("D1", "2")},
    "AUDIN": {("J2", "2"), ("C3", "1")},
    "POTTOP": {("C3", "2"), ("RV2", "1")},
    "POTW": {("RV2", "2"), ("U1", "10")},
    "AUDIO_P": {("U1", "8"), ("U1", "9"), ("R8", "1"), ("U3", "2")},
    "INVSUM": {("R8", "2"), ("R9", "1"), ("U1", "13")},
    "AUDIO_N": {("R9", "2"), ("U1", "14"), ("U4", "2")},
    "PWM_A": {("U3", "7"), ("R10", "2"), ("U5", "3"), ("TP2", "1")},
    "PWM_B": {("U4", "7"), ("R11", "2"), ("U5", "7")},
    "A_LO": {("U5", "2"), ("U5", "5"), ("U6", "4")},
    "A_HI": {("U5", "4"), ("U6", "7")},
    "B_LO": {("U5", "6"), ("U5", "9"), ("U6", "3")},
    "B_HI": {("U5", "10"), ("U6", "2")},
    "DELR": {("U6", "5"), ("R12", "1")},
    "DISR": {("U6", "8"), ("R13", "1")},
    "BOOTA": {("U6", "9"), ("D2", "1"), ("C5", "1")},
    "BOOTB": {("U6", "1"), ("D3", "1"), ("C6", "1")},
    "G_AH": {("U6", "10"), ("R14", "1")},
    "G_AL": {("U6", "13"), ("R15", "1")},
    "G_BH": {("U6", "16"), ("R16", "1")},
    "G_BL": {("U6", "14"), ("R17", "1")},
    "GQ1": {("R14", "2"), ("Q1", "1"), ("R18", "1")},
    "GQ2": {("R15", "2"), ("Q2", "1"), ("R19", "1")},
    "GQ3": {("R16", "2"), ("Q3", "1"), ("R20", "1")},
    "GQ4": {("R17", "2"), ("Q4", "1"), ("R21", "1")},
    "SW_A": {("Q1", "3"), ("Q2", "2"), ("R18", "2"), ("C5", "2"),
             ("U6", "11"), ("L1", "1"), ("TP3", "1")},
    "SW_B": {("Q3", "3"), ("Q4", "2"), ("R20", "2"), ("C6", "2"),
             ("U6", "15"), ("L2", "1"), ("TP4", "1")},
    "OUT_P": {("L1", "2"), ("C13", "1"), ("R22", "1"), ("J3", "1"),
              ("TP5", "1")},
    "OUT_N": {("L2", "2"), ("C13", "2"), ("C14", "2"), ("J3", "2")},
    "ZOB": {("R22", "2"), ("C14", "1")},
}
# pins deliberately left open (balance/strobe, spare inverter outputs)
for _ref, _pin in (("U2", "5"), ("U2", "6"), ("U3", "5"), ("U3", "6"),
                   ("U4", "5"), ("U4", "6"), ("U5", "12"), ("U5", "15")):
    TARGET[f"NC-{_ref}-{_pin}"] = {(_ref, _pin)}


def write_project(path: Path, uuid: str, name: str):
    pro = json.loads(TEMPLATE_PRO.read_text(encoding="utf-8"))

    # The template's netclass predates KiCad 7's schematic netclass properties
    # and carries no `wire_width`. KiCad 10 applies the netclass wire width to
    # every wire on the sheet, and a missing key resolves to ZERO: the wires
    # render as invisible hairlines and the junction dots -- whose size is
    # derived from the wire width -- disappear entirely. The netlist and ERC
    # are unaffected, so every headless check still passes while Eeschema
    # shows what looks exactly like a sheet full of unconnected wires.
    # Open the same file with no .kicad_pro beside it and it draws correctly.
    for cls in pro.get("net_settings", {}).get("classes", []):
        cls.setdefault("wire_width", 6.0)      # mils, as default_line_thickness
        cls.setdefault("bus_width", 12.0)
        cls.setdefault("line_style", 0)

    pro["meta"]["filename"] = f"{name}.kicad_pro"
    pro["schematic"]["top_level_sheets"] = [
        {"filename": f"{name}.kicad_sch", "name": name, "uuid": uuid}]
    pro["sheets"] = [[uuid, name]]
    pro["pcbnew"]["last_paths"]["plot"] = ""
    path.write_text(json.dumps(pro, indent=2) + "\n", encoding="utf-8")


def move_fields(path, ref, ref_at, val_at, n=0):
    """Park one symbol's Reference/Value where the auto-placement cannot.

    schdraw parks the fields beside a tall body. That is wrong in two places
    here: on U6 it lands on the four gate wires leaving the right-hand side,
    and on a part rotated 90 degrees KiCad rotates the field text too, so the
    2.54 mm offset between Reference and Value runs *along* the text and the
    two strings print on top of each other. `n` selects which occurrence of a
    multi-unit refdes to move.
    """
    txt = Path(path).read_text(encoding="utf-8")
    i = -1
    for _ in range(n + 1):
        i = txt.index(f'(property "Reference" "{ref}"', i + 1)
    j = txt.index('(property "Footprint"', i)
    head, seg, tail = txt[:i], txt[i:j], txt[j:]
    ats = [k for k in range(len(seg)) if seg.startswith("(at ", k)]
    assert len(ats) == 2, ats
    for k, (x, y) in zip(reversed(ats), (val_at, ref_at)):
        end = seg.index(")", k)
        seg = seg[:k] + f"(at {x} {y} 0" + seg[end:]
    Path(path).write_text(head + seg + tail, encoding="utf-8")


def main():
    spread()
    links = sim_index(sh)
    missing_fp = apply_footprints()
    if missing_fp:
        print("  NO FOOTPRINT for:", ", ".join(sorted(missing_fp)))
    problems = sh.check()
    for p in problems:
        print("  CHECK:", p)
    ok = sh.verify_against(TARGET)
    nets = sh.netlist()
    print(f"  {len(sh.parts)} symbols, {len(sh.wires)} wires, "
          f"{len(sh.labels)} labels, {len(nets)} nets")
    print(f"  {len({p.ref for p in sh.parts if p.footprint})} refdes "
          f"carry a footprint")
    out = KICAD / "classd.kicad_sch"
    sh.emit(str(out))
    add_hrefs(out, links)
    move_fields(out, "U6", spread_pt(G(46), G(171)),
                spread_pt(G(46), G(174)))
    move_fields(out, "U1", spread_pt(G(52), G(58)),
                spread_pt(G(52), G(61)), n=1)                     # power unit
    for _r, _x in (("D1", 248), ("D3", 100), ("D2", 112)):        # rotated 90
        _y = G(36) if _r == "D1" else G(168)
        move_fields(out, _r, spread_pt(G(_x + 3), _y),
                    spread_pt(G(_x + 6), _y))
    write_project(KICAD / "classd.kicad_pro", SHEET_UUID, "classd")
    print(f"  wrote {out}")
    return 0 if (ok and not problems and not missing_fp) else 1


if __name__ == "__main__":
    sys.exit(main())
