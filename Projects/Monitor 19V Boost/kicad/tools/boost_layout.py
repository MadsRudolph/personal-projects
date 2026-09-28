#!/usr/bin/env python3
"""12 V -> 19 V / 3 A boost for the Samsung C27JG5x -- schematic layout script.

Drawn with the kicad-schematic DSL so the sheet reads as a textbook drawing.
Every value comes from calc/boost_design.py and is checked in sim/boost_tran.cir.

    power stage:  J1 12V -> C1..C3 -> L1 -> SW -> D1 -> VOUT -> C4..C7, D2, J2
                  SW -> Q1 (drain), Q1 source -> R1||R2 (CS) -> GND
    gate drive:   SG3524 emitters (DRV) -> Q2/Q3 totem pole -> R4 -> Q1 gate
    control:      U1 SG3524, type III network on IN-/COMP, IN+ = trimmed
                  VREF/2 with C13 soft start, RT/CT 100 kHz
    protection:   CS -> R14/R15/C17 -> CL+ (8 A peak);  VOUT -> D4 22 V zener
                  -> R16/R17 -> SHUTDOWN (~23 V);  D2 1.5KE24A across VOUT

Run from the project root:  python3 kicad/tools/boost_layout.py
"""
import json
import sys
from pathlib import Path

SKILL = Path("/home/mads/.claude/skills/kicad-schematic/scripts")
sys.path.insert(0, str(SKILL))

from schdraw import Sheet  # noqa: E402

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
NAME = "monitor-boost"
SCH = PROJ / f"{NAME}.kicad_sch"
PRO = PROJ / f"{NAME}.kicad_pro"

G = lambda n: round(n * 1.27, 2)          # noqa: E731  one grid step

# ------------------------------------------------------- symbol field emission
# Same wrapper as the Illuminate crossover: KiCad adds the symbol rotation to a
# field's text angle, and fields are centre-justified, so both are corrected
# here.  It also injects the Description field the BOM reads.
CHAR_W = 1.15
_orig_dump = Sheet._dump_symbol


def _prop(name, val, at, hide, size=1.27):
    return (
        f'\t\t(property "{name}" "{val}"\n'
        f"\t\t\t(at {round(at[0], 2)} {round(at[1], 2)} {int(at[2])})\n"
        + ("\t\t\t(hide yes)\n" if hide else "")
        + "\t\t\t(show_name no)\n"
        "\t\t\t(do_not_autoplace no)\n"
        f"\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size {size} {size})\n"
        "\t\t\t\t)\n\t\t\t)\n"
        "\t\t)"
    )


def _dump_with_fields(self, p):
    s = _orig_dump(self, p)
    if getattr(p, "is_power_port", False):
        return s
    head, _, tail = s.partition('\t\t(property "Reference"')
    _, _, rest = tail.partition("\t\t(instances")
    bb = p.bbox
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    a = p.rot % 180                             # cancels the symbol rotation
    if getattr(p, "field_pos", None):
        ref_at, val_at = p.field_pos
    elif h >= w:                                # tall part: fields to the right
        ref_at = (bb[2] + 1.0 + CHAR_W * len(p.ref) / 2, p.y - 1.27, a)
        val_at = (bb[2] + 1.0 + CHAR_W * len(str(p.value)) / 2, p.y + 1.27, a)
    else:                                       # wide part: above and below
        ref_at = (p.x, bb[1] - 1.5, a)
        val_at = (p.x, bb[3] + 1.5, a)
    props = [_prop("Reference", p.ref, ref_at, False),
             _prop("Value", p.value, val_at, False),
             _prop("Footprint", p.footprint, (p.x, p.y, 0), True),
             _prop("Datasheet", "", (p.x, p.y, 0), True)]
    for name, val in getattr(p, "extra", {}).items():
        props.append(_prop(name, val, (p.x, p.y, 0), True))
    return head + "\n".join(props) + "\n\t\t(instances" + rest


Sheet._dump_symbol = _dump_with_fields

# ------------------------------------------------------------------ footprints
# THT only, every pad gap >= 0.8 mm for the CNC end mill.  Electrolytic, 5 W
# resistor and toroid footprints are PROVISIONAL: the shop CSV has no body
# sizes -- measure the real parts before placement (see README).
FP_R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"
FP_R5W = "Resistor_THT:R_Axial_Power_L25.0mm_W9.0mm_P27.94mm"
FP_CP_BIG = "Capacitor_THT:CP_Radial_D16.0mm_P7.50mm"
FP_CP_SMALL = "Capacitor_THT:CP_Radial_D5.0mm_P2.50mm"
FP_C_CER = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
FP_C_FILM = "Capacitor_THT:C_Rect_L7.2mm_W3.0mm_P5.00mm_FKS2_FKP2_MKS2_MKP2"
FP_C_FILM_L = "Capacitor_THT:C_Rect_L7.2mm_W5.5mm_P5.00mm_FKS2_FKP2_MKS2_MKP2"
FP_TRIM = "Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical"
FP_TO220_3 = "energy_system:TO-220-3_Vertical_LaserPads"
FP_TO220_2 = "Package_TO_SOT_THT:TO-220-2_Vertical"
FP_TO126 = "energy_system:TO-126-3_Vertical_P2.54_LaserPads"   # leads splayed: 0.84 mm gaps
FP_DO35 = "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"
FP_DO201 = "Diode_THT:D_DO-201AE_P15.24mm_Horizontal"
FP_LED = "energy_system:LED_D3.0mm_P5.08mm_LaserPads"
FP_TOROID = "energy_system:L_Toroid_Vertical_L34.5mm_W15.0mm_P28.20mm_LaserPads"
FP_TERM = "TerminalBlock:TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm"
FP_DIP16 = "Package_DIP:DIP-16_W7.62mm_Socket_LongPads"

SHEET_UUID = "b0057a19-0000-4000-8000-5a3524000001"

sh = Sheet(paper="A3", title="Monitor supply - 12 V to 19 V / 3 A boost (SG3524)",
           project=NAME, uuid=SHEET_UUID, lib_dirs=[PROJ / "lib"])


def part(lib, ref, at, rot=0, mirror="", value="", fp="", descr=""):
    p = sh.place(lib, ref, at=at, rot=rot, mirror=mirror, value=value, footprint=fp)
    p.extra = {"Description": descr} if descr else {}
    return p


R = lambda ref, at, val, rot=0, fp=FP_R, d="": part("Device:R", ref, at, rot, value=val, fp=fp, descr=d)  # noqa: E731
C = lambda ref, at, val, rot=0, fp=FP_C_CER, d="": part("Device:C", ref, at, rot, value=val, fp=fp, descr=d)  # noqa: E731
CP = lambda ref, at, val, fp=FP_CP_BIG, d="": part("Device:C_Polarized", ref, at, value=val, fp=fp, descr=d)  # noqa: E731


def title(x, y, text):
    sh.note((x, y), text, size=2)


# =================================================================== POWER STAGE
Y_RAIL = G(36)      # +12 V / SW / VOUT line
Y_RET_IN = G(48)    # input return rail
Y_RET_OUT = G(52)   # output return rail
SWX = G(70)         # switch node column

title(G(8), G(24), "Power stage and gate drive  (12 V -> L1 -> Q1 / D1 -> 19 V;  SG3524 DRV -> BD139/BD140 totem pole -> Q1)")

J1 = part("Connector:Screw_Terminal_01x02", "J1", (G(10), Y_RAIL), mirror="y",
          value="12V IN", fp=FP_TERM, descr="2-pole screw terminal, from the 12 V supply (>= 6 A)")
J1.field_pos = ((G(6), Y_RAIL - G(4), 0), (G(6), Y_RAIL + G(5), 0))
C1 = CP("C1", (G(24), Y_RAIL + G(6)), "1000u", d="Electrolytic 1000 uF 50 V, input bulk")
C2 = CP("C2", (G(34), Y_RAIL + G(6)), "1000u", d="Electrolytic 1000 uF 50 V, input bulk")
C3 = C("C3", (G(44), Y_RAIL + G(6)), "100n", d="Ceramic 100 nF 50 V, input HF bypass")
L1 = part("Device:L_Iron", "L1", (G(58), Y_RAIL), rot=90, value="22u 9A",
          fp=FP_TOROID, descr="22 uH hand-wound on a shop toroid, Isat >= 9 A, see README")

# +12 V rail: J1 -> caps -> L1, stub + rail symbol
sh.seg(J1.pin(1), L1.pin(1))
for c in (C1, C2, C3):
    sh.seg((c.x, Y_RAIL), c.pin(1))
    sh.seg(c.pin(2), (c.x, Y_RET_IN))
sh.rail((G(50), Y_RAIL), net="+12V")
# input return
sh.seg(J1.pin(2), (G(18), J1.pin(2).y))
sh.seg((G(18), J1.pin(2).y), (G(18), Y_RET_IN))
sh.seg((G(18), Y_RET_IN), (C3.x, Y_RET_IN))
sh.gnd((G(28), Y_RET_IN))

# switch node, diode, output rail
D1 = part("Device:D", "D1", (G(78), Y_RAIL), rot=180, value="BYW29-100",
          fp=FP_TO220_2, descr="8 A 100 V ultrafast rectifier, TO-220AC, on a heatsink (2.6 W)")
sh.seg(L1.pin(2), D1.pin(2))
C4 = CP("C4", (G(88), Y_RAIL + G(6)), "1000u", d="Electrolytic 1000 uF 50 V, output (0.9 A ripple each)")
C5 = CP("C5", (G(98), Y_RAIL + G(6)), "1000u", d="Electrolytic 1000 uF 50 V, output")
C6 = CP("C6", (G(108), Y_RAIL + G(6)), "1000u", d="Electrolytic 1000 uF 50 V, output")
C7 = C("C7", (G(118), Y_RAIL + G(6)), "100n", d="Ceramic 100 nF 50 V, output HF bypass")
D2 = part("Device:D_Zener", "D2", (G(126), Y_RAIL + G(5)), rot=270, value="1.5KE24A",
          fp=FP_DO201, descr="24 V 1500 W unidirectional TVS, last-ditch over-voltage clamp")
R18 = R("R18", (G(134), Y_RAIL + G(5)), "3.32k", d="LED current limit, ~5 mA")
D3 = part("Device:LED", "D3", (G(134), Y_RAIL + G(12)), rot=90, value="LED",
          fp=FP_LED, descr="3 mm LED, output-on indicator")
J2 = part("Connector:Screw_Terminal_01x02", "J2", (G(148), Y_RAIL), value="19V OUT",
          fp=FP_TERM, descr="2-pole screw terminal, to the monitor's barrel plug lead")
J2.field_pos = ((G(150), Y_RAIL - G(4), 0), (G(150), Y_RAIL + G(5), 0))
sh.seg(D1.pin(1), J2.pin(1))
for c in (C4, C5, C6, C7, D2):
    top = c.pin(1)
    sh.seg((c.x, Y_RAIL), top)
    sh.seg(c.pin(2), (c.x, Y_RET_OUT))
sh.seg((R18.x, Y_RAIL), R18.pin(1))
sh.seg(R18.pin(2), D3.pin(2))
sh.seg(D3.pin(1), (D3.x, Y_RET_OUT))
sh.seg(J2.pin(2), (G(140), J2.pin(2).y))
sh.seg((G(140), J2.pin(2).y), (G(140), Y_RET_OUT))
sh.seg((C4.x, Y_RET_OUT), (G(140), Y_RET_OUT))
sh.gnd((G(113), Y_RET_OUT))
sh.label((G(84), Y_RAIL), "VOUT")

# MOSFET + shunt
Q1 = part("Transistor_FET:IRF540N", "Q1", (SWX - 2.54, G(58)), value="P36NF06",
          fp=FP_TO220_3, descr="STP36NF06 60 V 36 A 40 mOhm N-MOSFET, TO-220, on a heatsink (1.1 W)")
sh.seg((SWX, Y_RAIL), Q1.pin("D"))
sh.label((SWX, G(46)), "SW")
R1 = R("R1", (SWX, G(68)), "0R10 5W", fp=FP_R5W, d="0.10 Ohm 5 W, current shunt (paralleled with R2)")
R2 = R("R2", (SWX + G(10), G(68)), "0R10 5W", fp=FP_R5W, d="0.10 Ohm 5 W, current shunt (paralleled with R1)")
sh.seg(Q1.pin("S"), R1.pin(1))
sh.seg((SWX, G(64)), (R2.x, G(64)))
sh.seg((R2.x, G(64)), R2.pin(1))
sh.seg((R2.x, G(64)), (R2.x + G(6), G(64)))
sh.label((R2.x + G(6), G(64)), "CS")
sh.seg(R1.pin(2), (R1.x, G(73)))
sh.seg(R2.pin(2), (R2.x, G(73)))
sh.seg((R1.x, G(73)), (R2.x, G(73)))
sh.gnd(((R1.x + R2.x) / 2, G(73)))

# ==================================================================== GATE DRIVE
XG = Q1.pin("G").x                         # gate pin tip
R4 = R("R4", (G(56), G(58)), "10", rot=90, d="Gate resistor")
R5 = R("R5", (G(61), G(61)), "10k", d="Gate-source pull-down, holds Q1 off while U1 starts")
sh.seg(R4.pin(2), Q1.pin("G"))
sh.seg((R5.x, G(58)), R5.pin(1))
sh.seg(R5.pin(2), (SWX, R5.pin(2).y))       # to Q1 source (CS)
XE = G(49)
Q2 = part("Transistor_BJT:BD139", "Q2", (G(47), G(52)), value="BD139",
          fp=FP_TO126, descr="NPN 80 V 1.5 A, totem-pole source")
Q3 = part("Transistor_BJT:BD140", "Q3", (G(47), G(64)), mirror="x", value="BD140",
          fp=FP_TO126, descr="PNP 80 V 1.5 A, totem-pole sink")
sh.seg(Q2.pin("E"), Q3.pin("E"))
sh.seg((XE, G(58)), R4.pin(1))
sh.seg(Q2.pin("C"), (Q2.pin("C").x, Q2.pin("C").y - G(2)))
sh.label((Q2.pin("C").x, Q2.pin("C").y - G(2)), "VCC_F")
sh.gnd(Q3.pin("C"))
XB = G(41)
sh.seg(Q2.pin("B"), (XB, Q2.pin("B").y))
sh.seg((XB, Q2.pin("B").y), (XB, Q3.pin("B").y))
sh.seg((XB, Q3.pin("B").y), Q3.pin("B"))
R3 = R("R3", (G(37), G(61)), "332", d="Pull-down for the paralleled SG3524 emitter outputs (30 mA)")
sh.seg((G(29), G(58)), (XB, G(58)))
sh.seg((R3.x, G(58)), R3.pin(1))
sh.gnd(R3.pin(2))
sh.label((G(29), G(58)), "DRV")

# ================================================================= CONTROLLER
U = (G(124), G(122))
title(G(26), G(90), "Controller  (SG3524, 100 kHz, voltage mode, type III compensation)")
U1 = part("boost:SG3524", "U1", U, value="SG3524", fp=FP_DIP16,
          descr="SG3524 PWM controller, DIP-16 in a socket")
U1.field_pos = ((U[0] - G(6), U[1] - G(15), 0), (U[0] + G(12), U[1] + G(15), 0))

# --- right side: outputs paralleled, protection inputs
XR1 = G(138)
sh.seg(U1.pin("C_A"), (XR1, U1.pin("C_A").y))
sh.seg(U1.pin("C_B"), (XR1, U1.pin("C_B").y))
sh.seg((XR1, U1.pin("C_A").y), (XR1, U1.pin("C_B").y))
sh.seg((XR1, U1.pin("C_A").y), (XR1, U1.pin("C_A").y - G(2)))
sh.label((XR1, U1.pin("C_A").y - G(2)), "VCC_F")
sh.seg(U1.pin("E_A"), (XR1, U1.pin("E_A").y))
sh.seg((XR1, U1.pin("E_A").y), (XR1, U1.pin("E_B").y))
sh.seg(U1.pin("E_B"), (G(146), U1.pin("E_B").y))
sh.label((G(146), U1.pin("E_B").y), "DRV")
sh.nc(U1.pin("OSC"))
sh.seg(U1.pin("SD"), (G(142), U1.pin("SD").y))
sh.label((G(142), U1.pin("SD").y), "OVP_SD")
sh.seg(U1.pin("CL+"), (G(142), U1.pin("CL+").y))
sh.label((G(142), U1.pin("CL+").y), "ISENSE")
sh.seg(U1.pin("CL-"), (G(137), U1.pin("CL-").y))
sh.gnd((G(137), U1.pin("CL-").y))

# --- VCC filter
Y_VCC = G(104)
sh.seg(U1.pin("VCC"), (U1.pin("VCC").x, Y_VCC))
R6 = R("R6", (G(160), Y_VCC), "10", rot=90, d="VCC filter")
C9 = CP("C9", (G(146), Y_VCC + G(4)), "10u", fp=FP_CP_SMALL, d="Electrolytic 10 uF 50 V, VCC")
C10 = C("C10", (G(154), Y_VCC + G(4)), "100n", d="Ceramic 100 nF, VCC")
sh.seg((U1.pin("VCC").x, Y_VCC), R6.pin(1))
for c in (C9, C10):
    sh.seg((c.x, Y_VCC), c.pin(1))
    sh.gnd(c.pin(2))
sh.seg(R6.pin(2), (G(166), Y_VCC))
sh.rail((G(166), Y_VCC), net="+12V")
sh.power("power:PWR_FLAG", (G(134), Y_VCC))
sh.label((G(141), Y_VCC), "VCC_F")

# --- reference, trimmer, soft start (IN+)
Y_REF = G(100)
XT = G(44)
sh.seg(U1.pin("REF"), (U1.pin("REF").x, Y_REF))
sh.seg((U1.pin("REF").x, Y_REF), (G(32), Y_REF))
C11 = C("C11", (G(32), Y_REF + G(4)), "100n", d="Ceramic 100 nF, VREF bypass")
sh.seg((G(32), Y_REF), C11.pin(1))
sh.gnd(C11.pin(2))
R8 = R("R8", (XT, Y_REF + G(3)), "9.09k", d="VREF divider, top")
RV1 = part("Device:R_Potentiometer_Trim", "RV1", (XT, G(112)), value="2k",
           fp=FP_TRIM, descr="2 kOhm multi-turn trimmer, sets VOUT 17.2..21.0 V (centre = 19.06 V)")
R9 = R("R9", (XT, G(119)), "9.09k", d="VREF divider, bottom")
sh.seg(R8.pin(2), RV1.pin(1))
sh.seg(RV1.pin(3), R9.pin(1))
sh.gnd(R9.pin(2))
Y_INP = G(112)
sh.seg(U1.pin("IN+"), (G(112), U1.pin("IN+").y))
sh.seg((G(112), U1.pin("IN+").y), (G(112), Y_INP))
sh.seg((G(112), Y_INP), RV1.pin(2))
C13 = C("C13", (G(54), Y_INP + G(4)), "470n", fp=FP_C_FILM_L, d="Film 470 nF, soft start (reference ramps in ~10 ms)")
sh.seg((C13.x, Y_INP), C13.pin(1))
sh.gnd(C13.pin(2))

# --- feedback divider + type III network (IN-, COMP)
XV, XN, XC = G(64), G(88), G(108)
Y_IN = U1.pin("IN-").y                     # G(116)
Y_R3 = Y_IN + G(6)
R10 = R("R10", (G(76), Y_IN), "205k", rot=90, d="Feedback divider, top")
sh.seg((XV, Y_IN), R10.pin(1))
sh.seg(R10.pin(2), U1.pin("IN-"))
R12 = R("R12", (G(70), Y_R3), "5.23k", rot=90, d="Type III: R3 (pole 9.2 kHz)")
C14 = C("C14", (G(81), Y_R3), "3.3n", rot=90, fp=FP_C_FILM, d="Film 3.3 nF, type III: C3 (zero 229 Hz)")
sh.seg((XV, Y_R3), R12.pin(1))
sh.seg(R12.pin(2), C14.pin(1))
sh.seg(C14.pin(2), (XN, Y_R3))
sh.seg((XV, Y_IN), (XV, Y_R3 + G(6)))
sh.label((XV, Y_R3 + G(6)), "VOUT")
Y_CP, Y_RF = G(130), G(138)
sh.seg(U1.pin("COMP"), (XC, U1.pin("COMP").y))
sh.seg((XC, U1.pin("COMP").y), (XC, Y_RF))
C16 = C("C16", (G(98), Y_CP), "1n", rot=90, fp=FP_C_FILM, d="Film 1 nF, type III: Cp (pole 12 kHz)")
sh.seg((XN, Y_CP), C16.pin(1))
sh.seg(C16.pin(2), (XC, Y_CP))
R13 = R("R13", (G(94), Y_RF), "13.0k", rot=90, d="Type III: Rf")
C15 = C("C15", (G(105), Y_RF), "47n", rot=90, fp=FP_C_FILM, d="Film 47 nF, type III: Cf (zero 260 Hz)")
sh.seg((XN, Y_RF), R13.pin(1))
sh.seg(R13.pin(2), C15.pin(1))
sh.seg(C15.pin(2), (XC, Y_RF))
sh.seg((XN, Y_IN), (XN, Y_RF))
R11 = R("R11", (XN, Y_RF + G(5)), "30.9k", d="Feedback divider, bottom")
sh.seg((XN, Y_RF), R11.pin(1))
sh.gnd(R11.pin(2))

# --- oscillator
sh.seg(U1.pin("RT"), (U1.pin("RT").x, G(136)))
sh.seg((U1.pin("RT").x, G(136)), (G(114), G(136)))
R7 = R("R7", (G(114), G(139)), "3.92k", d="RT, 100 kHz with C12")
C12 = C("C12", (U1.pin("CT").x, G(139)), "3.3n", fp=FP_C_FILM, d="Film 3.3 nF, CT (timing)")
sh.seg(U1.pin("CT"), C12.pin(1))
sh.gnd(R7.pin(2))
sh.gnd(C12.pin(2))
sh.seg(U1.pin("GND"), (U1.pin("GND").x, U1.pin("GND").y + G(2)))
sh.seg((U1.pin("GND").x, U1.pin("GND").y + G(2)), (U1.pin("GND").x + G(4), U1.pin("GND").y + G(2)))
sh.gnd((U1.pin("GND").x + G(4), U1.pin("GND").y + G(2)))

# ================================================================== PROTECTION
title(G(176), G(98), "Over-voltage shutdown  (trips at ~23 V)")
Y_OV = G(104)
sh.label((G(176), Y_OV), "VOUT")
D4 = part("Device:D_Zener", "D4", (G(186), Y_OV), value="BZX79C22",
          fp=FP_DO35, descr="22 V 500 mW zener, OVP threshold")
R16 = R("R16", (G(198), Y_OV), "1k", rot=90, d="OVP series")
sh.seg((G(176), Y_OV), D4.pin(1))
sh.seg(D4.pin(2), R16.pin(1))
R17 = R("R17", (G(208), Y_OV + G(4)), "4.75k", d="OVP pull-down, holds SHUTDOWN low")
C18 = C("C18", (G(218), Y_OV + G(4)), "10n", d="Ceramic 10 nF, SHUTDOWN filter")
sh.seg(R16.pin(2), (G(226), Y_OV))
Y_OVR = Y_OV + G(9)
for p in (R17, C18):
    sh.seg((p.x, Y_OV), p.pin(1))
    sh.seg(p.pin(2), (p.x, Y_OVR))
sh.seg((R17.x, Y_OVR), (C18.x, Y_OVR))
sh.gnd(((R17.x + C18.x) / 2, Y_OVR))
sh.label((G(226), Y_OV), "OVP_SD")

title(G(176), G(126), "Current limit  (CL+ trips at 200 mV = 8 A peak in Q1)")
Y_CL = G(132)
sh.label((G(176), Y_CL), "CS")
R14 = R("R14", (G(186), Y_CL), "1k", rot=90, d="Current-sense divider, top")
sh.seg((G(176), Y_CL), R14.pin(1))
R15 = R("R15", (G(198), Y_CL + G(4)), "1k", d="Current-sense divider, bottom")
C17 = C("C17", (G(208), Y_CL + G(4)), "1n", d="Ceramic 1 nF, leading-edge filter")
sh.seg(R14.pin(2), (G(216), Y_CL))
Y_CLR = Y_CL + G(9)
for p in (R15, C17):
    sh.seg((p.x, Y_CL), p.pin(1))
    sh.seg(p.pin(2), (p.x, Y_CLR))
sh.seg((R15.x, Y_CLR), (C17.x, Y_CLR))
sh.gnd(((R15.x + C17.x) / 2, Y_CLR))
sh.label((G(216), Y_CL), "ISENSE")

# ================================================================== PWR_FLAGs
sh.note((G(8), G(160)), "Power flags", size=1.27)
for i, net in enumerate(("+12V", "GND")):
    x0, y0 = G(10 + 20 * i), G(166)
    sh.seg((x0, y0), (x0 + G(10), y0))
    if net == "GND":
        sh.power("power:GND", (x0, y0))
    else:
        sh.power("power:+12V", (x0, y0))
    sh.power("power:PWR_FLAG", (x0 + G(10), y0))

# ======================================================================= NOTES
NX, NY = G(176), G(24)
title(NX, NY, "Design notes")
NOTES = [
    "Brief: 19 V / 3 A for a Samsung C27JG5x (needs 19 V 2.53 A) from a 12 V supply of >= 6 A.",
    "Numbers: calc/boost_design.py.  Switching SPICE check: sim/boost_tran.cir (run sim/run_corners.sh).",
    "",
    "fsw = 1.30 / (R7 C12) = 100 kHz.  Both SG3524 outputs paralleled -> single-ended drive at fosc.",
    "D = 0.39..0.45 (Vin 12.6..11.4 V).  IL: 5.3 A avg, 6.7 A peak worst case.",
    "L1 22 uH, Isat >= 9 A: powdered-iron toroid (-26 / -52 mix), NOT plain ferrite.  Measure AL first.",
    "VOUT = V(IN+) x (1 + R10/R11) = 2.5 V x 7.63 = 19.06 V with RV1 centred; RV1 spans the VREF tolerance.",
    "Soft start: C13 on IN+ ramps the reference (tau 2.4 ms), so the loop tracks up with no overshoot.",
    "Type III: fz 229/260 Hz, fp 9.2/12.2 kHz; crossover ~0.7 kHz, PM >= 67 deg, GM >= 15 dB",
    "   over Vin 11.4..12.6 V, Iout 1..3 A and 30..150 mOhm ESR per output cap.",
    "Q2 and the SG3524 output collectors run from VCC_F (after R6); C9 supplies the gate-charge pulses.",
    "SG3524 error amp is a 2 mS OTA sourcing only ~200 uA: keep the network high-impedance (R12 >= 5k).",
    "Current limit: R1||R2 = 50 mOhm, R14/R15 halves it, CL+ threshold 200 mV -> 8 A peak.",
    "   A boost has no output short-circuit protection: fuse the 12 V lead (8 A slow).",
    "OVP: D4 + R16/R17 pull SHUTDOWN high above ~23 V.  D2 (1.5KE24A) clamps if everything else fails.",
    "",
    "Layout: Q1 / D1 / C4-C6 / R1-R2 loop as small as possible.  U1 GND and CL- go to the shunt's",
    "   ground end (star point), never through the power return.  Q1 and D1 on separate heatsinks,",
    "   or one heatsink with mica + bushings (both tabs are live: drain = SW, cathode = VOUT).",
    "Single-sided board, CNC isolation-milled with a 0.8 mm end mill.  THT only, all pad gaps >= 0.8 mm.",
    "All electrolytics 50 V.  Electrolytic, 5 W resistor and toroid footprints are provisional: measure the parts before placing.",
]
for i, line in enumerate(NOTES):
    sh.note((NX, NY + G(4) + i * G(2.6)), line, size=1.27)

# ====================================================================== VERIFY
TARGET = {
    "+12V": {("J1", "1"), ("C1", "1"), ("C2", "1"), ("C3", "1"), ("L1", "1"),
             ("R6", "2")},
    "GND": {("J1", "2"), ("C1", "2"), ("C2", "2"), ("C3", "2"), ("R1", "2"), ("R2", "2"),
            ("C4", "2"), ("C5", "2"), ("C6", "2"), ("C7", "2"), ("D2", "2"), ("D3", "1"), ("J2", "2"),
            ("Q3", "2"), ("R3", "2"), ("U1", "5"), ("U1", "8"), ("C9", "2"), ("C10", "2"),
            ("C11", "2"), ("R9", "2"), ("C13", "2"), ("R11", "2"), ("R7", "2"), ("C12", "2"),
            ("R17", "2"), ("C18", "2"), ("R15", "2"), ("C17", "2")},
    "SW": {("L1", "2"), ("D1", "2"), ("Q1", "2")},
    "VOUT": {("D1", "1"), ("C4", "1"), ("C5", "1"), ("C6", "1"), ("C7", "1"), ("D2", "1"),
             ("R18", "1"), ("J2", "1"), ("R10", "1"), ("R12", "1"), ("D4", "1")},
    "LEDA": {("R18", "2"), ("D3", "2")},
    "CS": {("Q1", "3"), ("R1", "1"), ("R2", "1"), ("R14", "1"), ("R5", "2")},
    "GATE": {("Q1", "1"), ("R4", "2"), ("R5", "1")},
    "DRV_E": {("Q2", "1"), ("Q3", "1"), ("R4", "1")},
    "DRV": {("Q2", "3"), ("Q3", "3"), ("R3", "1"), ("U1", "11"), ("U1", "14")},
    "VCC_F": {("U1", "15"), ("R6", "1"), ("C9", "1"), ("C10", "1"), ("Q2", "2"), ("U1", "12"), ("U1", "13")},
    "REF": {("U1", "16"), ("C11", "1"), ("R8", "1")},
    "POT_T": {("R8", "2"), ("RV1", "1")},
    "POT_B": {("RV1", "3"), ("R9", "1")},
    "INP": {("RV1", "2"), ("U1", "2"), ("C13", "1")},
    "FB": {("R10", "2"), ("U1", "1"), ("C14", "2"), ("C16", "1"), ("R13", "1"), ("R11", "1")},
    "N3": {("R12", "2"), ("C14", "1")},
    "COMP": {("U1", "9"), ("C16", "2"), ("C15", "2")},
    "NF": {("R13", "2"), ("C15", "1")},
    "RT": {("U1", "6"), ("R7", "1")},
    "CT": {("U1", "7"), ("C12", "1")},
    "OVP_Z": {("D4", "2"), ("R16", "1")},
    "OVP_SD": {("R16", "2"), ("R17", "1"), ("C18", "1"), ("U1", "10")},
    "ISENSE": {("R14", "2"), ("R15", "1"), ("C17", "1"), ("U1", "4")},
    "OSC_NC": {("U1", "3")},
}

if __name__ == "__main__":
    problems = sh.check()
    for p in problems:
        print("CHECK:", p)
    ok = sh.verify_against(TARGET)
    sh.emit(SCH)
    print("wrote", SCH)

    pro = {
        "board": {"3dviewports": [], "design_settings": {"defaults": {}, "diff_pair_dimensions": [],
                  "drc_exclusions": [], "rules": {}, "track_widths": [], "via_dimensions": []},
                  "layer_presets": [], "viewports": []},
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "erc": {"erc_exclusions": [], "meta": {"version": 0}, "pin_map": [], "rule_severities": {},
                "severities": {}},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": f"{NAME}.kicad_pro", "version": 3},
        "net_settings": {
            "classes": [
                {"bus_width": 12.0, "clearance": 0.85, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
                 "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
                 "name": "Default", "pcb_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647,
                 "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": 1.0, "tuning_profile": "",
                 "via_diameter": 0.8, "via_drill": 0.4, "wire_width": 6.0},
                {"bus_width": 12.0, "clearance": 0.85, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
                 "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
                 "name": "Power", "pcb_color": "rgba(0, 0, 0, 0.000)", "priority": 0,
                 "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": 1.5, "tuning_profile": "",
                 "via_diameter": 0.8, "via_drill": 0.4, "wire_width": 6.0},
            ],
            "meta": {"version": 5},
            "net_colors": None,
            "netclass_assignments": None,
            "netclass_patterns": [{"netclass": "Power", "pattern": p}
                                  for p in ("+12V", "GND", "/SW", "/VOUT", "/CS")],
        },
        "pcbnew": {"last_paths": {}, "page_layout_descr_file": ""},
        "schematic": {"drawing": {"default_line_thickness": 6.0, "default_text_size": 50.0},
                      "legacy_lib_dir": "", "legacy_lib_list": [],
                      "meta": {"version": 1}, "net_format_name": "", "spice_external_command": ""},
        "sheets": [[SHEET_UUID, ""]],
        "text_variables": {},
        "tuning_profiles": [],
    }
    PRO.write_text(json.dumps(pro, indent=2) + "\n", encoding="utf-8")
    print("wrote", PRO)
    sys.exit(0 if ok and not problems else 1)
