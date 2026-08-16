"""Generate subxo.kicad_sch -- the Bose sub crossover board schematic.

The design of record is ``HANDOFF - KiCad Schematic.md`` two directories up.
Every net table in that document is transcribed here verbatim (NETS below), so
the schematic can be diffed against the handoff row by row.

Topology: mono-summing 2nd-order Sallen-Key low-pass, single +12 V rail from an
on-board LM7812, TL074 quad op-amp with a 6 V virtual ground. No negative rail.

Wiring style: every pin that carries a net gets a short wire stub routed outward
from the pin, with a net label on the far end. Identical label names are one net.
This is the same technique used on the reflow board in this repo -- it keeps the
netlist unambiguous and machine-checkable. Pin geometry and electrical types come
from the real KiCad symbol libraries, copied into (lib_symbols) so ERC and the
netlist exporter see genuine pins rather than collapsing every pin on the origin.
"""

import math
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # hardware/kicad
SCH = ROOT / "subxo.kicad_sch"

KICAD_SYMBOL_DIR = Path(r"C:\Program Files\KiCad\9.0\share\kicad\symbols")
LIB_SOURCES = {
    "Device": KICAD_SYMBOL_DIR / "Device.kicad_sym",
    "Connector": KICAD_SYMBOL_DIR / "Connector.kicad_sym",
    "Connector_Generic": KICAD_SYMBOL_DIR / "Connector_Generic.kicad_sym",
    "Regulator_Linear": KICAD_SYMBOL_DIR / "Regulator_Linear.kicad_sym",
    "Amplifier_Operational": KICAD_SYMBOL_DIR / "Amplifier_Operational.kicad_sym",
}

PROJ_NAME = "subxo"
PROJ_UUID = "b05e5ub0-0001-0001-0001-000000000001"

# --- footprints -------------------------------------------------------------
FP_R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
FP_CER = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
# Pitches below are measured off the real parts (2026-08-16), not taken from the
# value. Caliper inside-to-inside and outside-to-outside average to the pitch and
# differ by the lead diameter; all three parts came out at 0.5 mm leads.
FP_FILM_5 = "Capacitor_THT:C_Rect_L7.2mm_W5.5mm_P5.00mm_FKS2_FKP2_MKS2_MKP2"
FP_FILM_5_TALL = "Capacitor_THT:C_Rect_L7.2mm_W7.2mm_P5.00mm_FKS2_FKP2_MKS2_MKP2"
FP_FILM_75 = "Capacitor_THT:C_Rect_L10.3mm_W5.7mm_P7.50mm_MKS4"
FP_FILM_10 = "Capacitor_THT:C_Rect_L13.0mm_W6.0mm_P10.00mm_FKS3_FKP3_MKS4"
FP_FILM_10_THIN = "Capacitor_THT:C_Rect_L13.0mm_W4.0mm_P10.00mm_FKS3_FKP3_MKS4"
# C_in is deliberately tri-pitch: 5.00 mm takes the 220n as built (or a 2u2
# non-polarised electrolytic), 10.00 mm the measured shop part, 15.00 mm a large
# 2u2 film. Rev A had a 220n splayed across a 15.00 mm footprint. Which value is
# right is a listening question that Gate 11 has not answered yet, so the board
# keeps every option. Same-number pads share a net, so the extra pairs cost
# nothing in isolation -- the tightest pad-1-to-pad-2 channel is still 3.0 mm.
FP_CIN_MULTI = ("energy_system:"
                "C_Rect_L18.0mm_W9.0mm_P5.00mm_P10.00mm_P15.00mm_MultiPitch")
FP_EL_100U = "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm"
FP_EL_10U = "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm"
FP_TERM2 = "TerminalBlock:TerminalBlock_bornier-2_P5.08mm"
FP_TERM3 = "TerminalBlock:TerminalBlock_bornier-3_P5.08mm"
FP_HDR2 = "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
FP_HDR6 = "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical"
FP_DIP14 = "Package_DIP:DIP-14_W7.62mm_LongPads"        # socket
FP_TO220 = "energy_system:TO-220-3_Vertical_LaserPads"
FP_LED3 = "LED_THT:LED_D3.0mm"

SYM_TERM2 = "Connector:Screw_Terminal_01x02"
SYM_TERM3 = "Connector:Screw_Terminal_01x03"

# --- placement --------------------------------------------------------------
# (ref, lib_id, value, footprint, x, y, angle, unit). A2 sheet = 594 x 420 mm.
# Blocks: power top-left, virtual ground top-right, input left, filter centre,
# jumper-selected caps around the filter, inverter lower-centre, output right.
COMPONENTS = [
    # =====================================================================
    # Blocks are grouped by CONNECTIVITY, not spread evenly over the sheet.
    # Each block is the set of parts that wire to each other, drawn tight,
    # with whitespace between blocks: at layout time you select one block in
    # the schematic, its footprints highlight together on the board, and you
    # place the board block by block. Blocks run in signal-flow order --
    # power along the top, inputs left, filter centre, output right.
    # =====================================================================

    # ---- A: power input -> LM7812 -> +12 V rail (top left) ----
    ("J4", SYM_TERM2, "PWR IN 15V", FP_TERM2, 55, 55, 180, 1),
    ("C10", "Device:C_Polarized", "100uF/50V", FP_EL_100U, 78, 63, 0, 1),
    ("U2", "Regulator_Linear:LM7812_TO220", "LM7812", FP_TO220, 105, 55, 0, 1),
    ("C11", "Device:C_Polarized", "100uF/50V", FP_EL_100U, 130, 63, 0, 1),
    ("C12", "Device:C", "100nF", FP_CER, 150, 63, 0, 1),
    ("R10", "Device:R", "4k7", FP_R, 170, 55, 0, 1),
    ("D1", "Device:LED", "PWR green", FP_LED3, 170, 72, 90, 1),

    # ---- B: TL074 supply pins + their decoupling (top centre) ----
    ("U1", "Amplifier_Operational:TL074", "TL074", FP_DIP14, 215, 55, 0, 5),
    ("C13", "Device:C", "100nF", FP_CER, 240, 63, 0, 1),
    ("C14", "Device:C", "100nF", FP_CER, 258, 63, 0, 1),

    # ---- C: 6 V virtual ground -- divider, reservoir, buffer, spare ----
    ("R8", "Device:R", "10k", FP_R, 315, 48, 0, 1),
    ("R9", "Device:R", "10k", FP_R, 315, 75, 0, 1),
    ("C15", "Device:C_Polarized", "100uF/50V", FP_EL_100U, 338, 75, 0, 1),
    ("U1", "Amplifier_Operational:TL074", "TL074", FP_DIP14, 390, 55, 0, 3),
    ("U1", "Amplifier_Operational:TL074", "TL074", FP_DIP14, 390, 105, 0, 4),

    # ---- D: left channel input -- couple, bias, sum resistor ----
    ("J1", SYM_TERM2, "IN L", FP_TERM2, 55, 160, 180, 1),
    ("C_in1", "Device:C", "220n or 2u2", FP_CIN_MULTI, 85, 160, 90, 1),
    ("R_b1", "Device:R", "100k", FP_R, 112, 180, 0, 1),
    ("R1_1", "Device:R", "16k5", FP_R, 140, 160, 90, 1),

    # ---- E: right channel input ----
    ("J2", SYM_TERM2, "IN R", FP_TERM2, 55, 235, 180, 1),
    ("C_in2", "Device:C", "220n or 2u2", FP_CIN_MULTI, 85, 235, 90, 1),
    ("R_b2", "Device:R", "100k", FP_R, 112, 255, 0, 1),
    ("R1_2", "Device:R", "16k5", FP_R, 140, 235, 90, 1),

    # ---- F: Sallen-Key low-pass -- C1 bank above, C2 bank below ----
    # Measured 5.0 mm pitch -- NOT the 10 mm a 470n usually wants. Body dims not
    # yet taken, so the envelope is the generous 7.2 x 7.2 of the P5.00 family.
    ("C1_1", "Device:C", "470nF film", FP_FILM_5_TALL, 215, 158, 90, 1),
    ("C1_2", "Device:C", "220nF film", FP_FILM_75, 215, 170, 90, 1),
    # Measured 9.5 mm -> 10.00 mm pitch. Rev A had it on 7.50 mm, which is why
    # its leads had to be bent inward. Body dims not yet taken; W6.0 clears the
    # 5.7 mm rev A assumed.
    ("C1_3", "Device:C", "150nF film", FP_FILM_10, 215, 182, 90, 1),
    ("JP1", "Connector_Generic:Conn_01x06", "C1 select", FP_HDR6, 262, 170, 0, 1),
    ("R2", "Device:R", "8k25", FP_R, 215, 205, 90, 1),
    ("U1", "Amplifier_Operational:TL074", "TL074", FP_DIP14, 265, 205, 0, 1),
    ("C2_1", "Device:C", "150nF film", FP_FILM_5, 215, 245, 90, 1),
    # The odd one out: measured 9.5 mm -> 10.00 mm pitch, body 12 x 4 mm, while
    # C2_1 and C2_3 are 5.00 mm parts. It was the substituted 120n, so the C2
    # bank is no longer three identical footprints in a row -- place accordingly.
    ("C2_2", "Device:C", "120nF film", FP_FILM_10_THIN, 215, 257, 90, 1),
    ("C2_3", "Device:C", "68nF film", FP_FILM_5, 215, 269, 90, 1),
    ("JP2", "Connector_Generic:Conn_01x06", "C2 select", FP_HDR6, 262, 257, 0, 1),

    # ---- G: unity inverter for the polarity switch ----
    ("R3", "Device:R", "10k", FP_R, 345, 205, 90, 1),
    ("R4", "Device:R", "10k", FP_R, 345, 230, 90, 1),
    ("U1", "Amplifier_Operational:TL074", "TL074", FP_DIP14, 398, 217, 0, 2),

    # ---- H: output -- polarity switch, DC block, level pot, jack ----
    ("J5", SYM_TERM3, "POLARITY SW", FP_TERM3, 478, 160, 0, 1),
    ("C_out1", "Device:C_Polarized", "10uF/50V", FP_EL_10U, 512, 178, 0, 1),
    ("J6", SYM_TERM3, "LEVEL POT 10k", FP_TERM3, 478, 210, 0, 1),
    ("R5", "Device:R", "100R", FP_R, 512, 240, 90, 1),
    ("R6", "Device:R", "100R", FP_R, 512, 262, 90, 1),
    ("R7", "Device:R", "10R", FP_R, 480, 292, 90, 1),
    ("JP3", "Connector_Generic:Conn_01x02", "GND lift", FP_HDR2, 480, 315, 0, 1),
    ("J3", SYM_TERM3, "OUT 3.5mm", FP_TERM3, 556, 250, 0, 1),

    # ---- I: status LEDs ----
    # D1 (power) lives in block A next to the regulator. D2 rides SW2's unused
    # second pole: the polarity switch is a 2-pole changeover and rev A used
    # only one pole, so lighting an "inverted" lamp costs a resistor, an LED and
    # a 2-way terminal. J7 goes to that spare pole -- pin 1 to its INVERTED lug,
    # pin 2 to its common, which returns the 2 mA to board GND.
    ("R11", "Device:R", "4k7", FP_R, 520, 300, 0, 1),
    ("D2", "Device:LED", "INV amber", FP_LED3, 520, 317, 90, 1),
    ("J7", SYM_TERM2, "INV LED", FP_TERM2, 556, 317, 0, 1),
]

# Which TL074 unit carries which DIP-14 pin (KiCad LM2902-derived geometry).
U1_PIN_UNIT = {
    "1": 1, "2": 1, "3": 1,
    "5": 2, "6": 2, "7": 2,
    "8": 3, "9": 3, "10": 3,
    "12": 4, "13": 4, "14": 4,
    "4": 5, "11": 5,
}

PIN_IDS = {
    "Device:R": ["1", "2"],
    "Device:C": ["1", "2"],
    "Device:C_Polarized": ["1", "2"],
    SYM_TERM2: ["1", "2"],
    SYM_TERM3: ["1", "2", "3"],
    "Device:LED": ["1", "2"],                        # 1 = K, 2 = A
    "Connector_Generic:Conn_01x02": ["1", "2"],
    "Connector_Generic:Conn_01x06": ["1", "2", "3", "4", "5", "6"],
    "Regulator_Linear:LM7812_TO220": ["1", "2", "3"],
    "Amplifier_Operational:TL074": None,   # per unit, see unit_pin_ids()
}

TL074_UNIT_PINS = {
    1: ["1", "2", "3"],
    2: ["5", "6", "7"],
    3: ["8", "9", "10"],
    4: ["12", "13", "14"],
    5: ["4", "11"],
}

# --- the netlist ------------------------------------------------------------
# Transcribed from the handoff tables. (net, ref, pin).
NETS = [
    # ---- power ----
    ("VIN", "J4", "1"), ("VIN", "C10", "1"), ("VIN", "U2", "1"),
    ("GND", "J4", "2"), ("GND", "C10", "2"), ("GND", "U2", "2"),
    ("V12", "U2", "3"), ("V12", "C11", "1"), ("V12", "C12", "1"),
    ("GND", "C11", "2"), ("GND", "C12", "2"),
    ("V12", "C13", "1"), ("GND", "C13", "2"),
    ("V12", "C14", "1"), ("GND", "C14", "2"),
    ("V12", "U1", "4"),                          # TL074 V+
    ("GND", "U1", "11"),                         # TL074 V- = GND (single supply)
    ("V12", "R8", "1"), ("VG_DIV", "R8", "2"),
    ("VG_DIV", "R9", "1"), ("GND", "R9", "2"),
    ("VG_DIV", "C15", "1"), ("GND", "C15", "2"),

    # ---- A3 virtual-ground buffer: VG_DIV -> follower -> VGND ----
    ("VG_DIV", "U1", "10"),                      # A3 in+
    ("VGND", "U1", "9"),                         # A3 in- tied to out
    ("VGND", "U1", "8"),                         # A3 out = VGND

    # ---- A4 spare, terminated as a follower on VGND ----
    ("VGND", "U1", "12"),                        # A4 in+
    ("SPARE_OUT", "U1", "13"), ("SPARE_OUT", "U1", "14"),

    # ---- inputs, coupling, bias ----
    ("IN_L", "J1", "1"), ("GND", "J1", "2"),
    ("IN_R", "J2", "1"), ("GND", "J2", "2"),
    ("IN_L", "C_in1", "1"), ("A_L", "C_in1", "2"),
    ("IN_R", "C_in2", "1"), ("A_R", "C_in2", "2"),
    ("A_L", "R_b1", "1"), ("VGND", "R_b1", "2"),
    ("A_R", "R_b2", "1"), ("VGND", "R_b2", "2"),

    # ---- summing + Sallen-Key ----
    ("A_L", "R1_1", "1"), ("N1", "R1_1", "2"),
    ("A_R", "R1_2", "1"), ("N1", "R1_2", "2"),
    ("N1", "R2", "1"), ("N2", "R2", "2"),
    ("N2", "U1", "3"),                           # A1 in+
    ("OUT1", "U1", "2"),                         # A1 in- tied to out: follower
    ("OUT1", "U1", "1"),                         # A1 out

    # ---- C1 group: OUT1 -> cap -> JP1 -> N1 (feedback, NOT N2) ----
    ("OUT1", "C1_1", "1"), ("C1A_SEL", "C1_1", "2"), ("C1A_SEL", "JP1", "1"),
    ("OUT1", "C1_2", "1"), ("C1B_SEL", "C1_2", "2"), ("C1B_SEL", "JP1", "3"),
    ("OUT1", "C1_3", "1"), ("C1C_SEL", "C1_3", "2"), ("C1C_SEL", "JP1", "5"),
    ("N1", "JP1", "2"), ("N1", "JP1", "4"), ("N1", "JP1", "6"),

    # ---- C2 group: N2 -> cap -> JP2 -> VGND ----
    ("N2", "C2_1", "1"), ("C2A_SEL", "C2_1", "2"), ("C2A_SEL", "JP2", "1"),
    ("N2", "C2_2", "1"), ("C2B_SEL", "C2_2", "2"), ("C2B_SEL", "JP2", "3"),
    ("N2", "C2_3", "1"), ("C2C_SEL", "C2_3", "2"), ("C2C_SEL", "JP2", "5"),
    ("VGND", "JP2", "2"), ("VGND", "JP2", "4"), ("VGND", "JP2", "6"),

    # ---- A2 unity inverter ----
    ("OUT1", "R3", "1"), ("INV_IN", "R3", "2"),
    ("INV_IN", "U1", "6"),                       # A2 in-
    ("INV_IN", "R4", "1"), ("OUT2", "R4", "2"),  # feedback around A2
    ("VGND", "U1", "5"),                         # A2 in+ = VGND
    ("OUT2", "U1", "7"),                         # A2 out

    # ---- output stage ----
    ("OUT1", "J5", "1"), ("OUT2", "J5", "2"), ("SW_COM", "J5", "3"),
    ("SW_COM", "C_out1", "1"),                    # + terminal at the 6 V node
    ("POT_TOP", "C_out1", "2"),
    ("POT_TOP", "J6", "1"), ("POT_W", "J6", "2"), ("GND", "J6", "3"),
    ("POT_W", "R5", "1"), ("OUT_TIP", "R5", "2"),
    ("POT_W", "R6", "1"), ("OUT_RING", "R6", "2"),
    ("GND", "R7", "1"), ("OUT_GND", "R7", "2"),
    ("GND", "JP3", "1"), ("OUT_GND", "JP3", "2"),
    ("OUT_TIP", "J3", "1"), ("OUT_RING", "J3", "2"), ("OUT_GND", "J3", "3"),

    # ---- status LEDs ----
    # Both run ~2 mA, so the LM7812 gains at most 4 mA on a 10-16 mA board and
    # still dissipates under 70 mW. Neither touches a signal node.
    ("V12", "R10", "1"), ("PWR_A", "R10", "2"),
    ("PWR_A", "D1", "2"), ("GND", "D1", "1"),        # D1 pin 2 = A, pin 1 = K
    ("V12", "R11", "1"), ("INV_A", "R11", "2"),
    ("INV_A", "D2", "2"), ("INV_K", "D2", "1"),
    ("INV_K", "J7", "1"), ("GND", "J7", "2"),
]

# PWR_FLAGs. VIN and GND carry only power_INPUT and passive pins, so ERC has no
# driver for them without a flag. V12 is driven by the LM7812 output pin, and
# VGND by the A3 op-amp output, so neither needs one. (net, ref, pin) -- the flag
# lands on that pin's stub endpoint.
PWR_FLAGS = [
    ("VIN", "C10", "1"),     # C10's stubs are clear space; U2's are not
    ("GND", "C10", "2"),
]

# Symbol origins are snapped to the 2.54 mm grid. Every stock symbol places its
# pins at multiples of 1.27 mm from the origin, so an on-grid origin puts every
# pin endpoint on KiCad's 1.27 mm connection grid -- otherwise ERC fills up with
# endpoint_off_grid warnings and the GUI cannot cleanly attach a wire by hand.
COMPONENTS = [(r, l, v, f, round(round(x / 2.54) * 2.54, 2),
               round(round(y / 2.54) * 2.54, 2), a, u)
              for r, l, v, f, x, y, a, u in COMPONENTS]

# Sheet notes: design intent that must survive the next editor.
NOTES = [
    (30, 26, 2.2,
     "Bose Companion 5 sub crossover -- mono-summing 2nd-order Sallen-Key low-pass."),
    (30, 33, 1.5,
     "Single +12 V rail, no negative supply. All AC referenced to VGND = 6 V "
     "(A3 buffers the R8/R9 mid-rail divider)."),

    # Block titles: one per connectivity group, so a block can be selected in the
    # schematic and placed on the board as a unit.
    (40, 44, 2.0, "A  POWER IN -> +12 V"),
    (205, 44, 2.0, "B  U1 SUPPLY"),
    (305, 44, 2.0, "C  VIRTUAL GROUND 6 V"),
    (40, 148, 2.0, "D  INPUT L"),
    (40, 223, 2.0, "E  INPUT R"),
    (205, 146, 2.0, "F  SALLEN-KEY LOW-PASS"),
    (335, 193, 2.0, "G  POLARITY INVERTER"),
    (470, 148, 2.0, "H  OUTPUT STAGE"),
    (510, 288, 2.0, "I  STATUS LEDS"),

    # Design intent that must survive the next editor.
    (205, 92, 1.5, "U1 supply: pin 4 = V12, pin 11 = GND. No negative rail."),
    (305, 132, 1.5,
     "A4 is the spare section: + on VGND, out tied to in-.\n"
     "An unterminated spare oscillates and couples into\n"
     "its neighbours through the shared supply."),
    (40, 200, 1.5,
     "R_b1/R_b2 are the only DC path to A1's + input (C_in blocks DC,\n"
     "C2 is a capacitor). Without them A1 drifts to a rail. They sit\n"
     "after the coupling caps -- 100k at N1 would shift every corner by 8%."),
    (205, 300, 1.5,
     "C1 returns to N1 -- the Sallen-Key feedback path. Not N2.\n"
     "JP1 selects C1 (odd pin = cap, even pin = N1); JP2 selects C2 (odd = cap,\n"
     "even = VGND). They select INDEPENDENTLY -- nine corners, not three pairs.\n"
     "Corners below are MEASURED on the rev A board, not calculated: the quoted\n"
     "f0 = 1/(2*pi*R*sqrt(C1*C2)) is not a -3 dB point, and C_in sits inside the\n"
     "filter. See Results - Sub Crossover Bring-up.\n"
     "\n"
     "Intended use is a panel 2-pole 3-position rotary, one pole per header:\n"
     "   pos 1  94 Hz   A0->JP1 even, A1->JP1.1 (470n)   B0->JP2 even, B1->JP2.1\n"
     "   pos 2 136 Hz                 A2->JP1.5 (150n)                 B2->JP2.3\n"
     "   pos 3 189 Hz                 A3->JP1.3 (220n)                 B3->JP2.5\n"
     "NEVER wire one header pin to two switch lugs unless both lugs want the same\n"
     "capacitance -- the lugs are then tied together and every position collapses\n"
     "to the same value. This is why C1_1 is fitted rather than paralleling\n"
     "C1_2 || C1_3 on one lug.\n"
     "Shunts across a pin pair still work as a bench fallback."),
    (30, 340, 1.5,
     "C_in1/C_in2 use a dual-pitch footprint: 5.00 mm for the 220n as built (or a\n"
     "2u2 non-polarised electrolytic), 15.00 mm for a real 2u2 film part. Fit ONE\n"
     "pair. 220n puts ~8.8k of reactance in series with R1 at 82 Hz, so it is part\n"
     "of the filter, not just an input high-pass -- it costs 1.3-3.1 dB of passband\n"
     "level and damps the peaking. Whether that is a defect or a feature is a\n"
     "listening question; Gate 11 has not answered it, so both pitches are on the\n"
     "board and the envelope reserves room for the larger part either way."),
    (470, 355, 1.5,
     "D1 = power lamp on V12 (proves the LM7812, not just VIN).\n"
     "D2 = INVERTED lamp, fed from SW2's unused second pole via J7.\n"
     "Both ~2 mA. No LED touches a signal node."),
    (470, 335, 1.5,
     "C_out + faces SW_COM: that node sits at 6 V DC, the pot side at 0 V.\n"
     "J6 pin 3 = GND, not VGND -- C_out has already removed the 6 V bias;\n"
     "referencing the pot to VGND would thump the driver at power-on.\n"
     "JP3 shorts R7 (ground lift). Normally fitted."),

    (30, 372, 1.5,
     "Off-board: level pot (J6), polarity switch (J5), all panel jacks (J1/J2/J3).\n"
     "Process: single-sided THT, bottom copper only, board outline 100 x 100 mm.\n"
     "Copper is isolation-milled on the CNC with an 0.8 mm flat end mill; the fiber\n"
     "laser does the silkscreen only. Routing clearance 0.85 mm / track 1.0 mm.\n"
     "The 0.8 mm tool width is a hard floor on every copper-to-copper gap. Fixed-pitch\n"
     "pads sit below the 0.85 mm target and carry a .kicad_dru exception: DIP-14\n"
     "0.94 mm (passes), 2.54 mm headers and the TO-220 0.84 mm (do not).\n"
     "Drills: 0.8 mm x52, 1.0 x26, 1.1 x3, 1.2 x4, 1.5 x15."),
    (30, 406, 1.5,
     "Reference names vs the handoff document: KiCad treats a reference with no\n"
     "trailing digit as unannotated, so C1a/C1b/C1c -> C1_1/C1_2/C1_3,\n"
     "C2a/C2b/C2c -> C2_1/C2_2/C2_3, R1a/R1b -> R1_1/R1_2, C_out -> C_out1."),
]

_STUB = 2.54


def uid() -> str:
    return str(uuid.uuid4())


# --- symbol library plumbing ------------------------------------------------
_LIB_TEXT: dict[str, str] = {}


def _lib_text(lib: str) -> str:
    if lib not in _LIB_TEXT:
        _LIB_TEXT[lib] = LIB_SOURCES[lib].read_text(encoding="utf-8")
    return _LIB_TEXT[lib]


def _block(text: str, name: str) -> str | None:
    """The balanced ``(symbol "name" ...)`` s-expression, or None."""
    idx = text.find(f'(symbol "{name}"')
    if idx == -1:
        return None
    depth = 0
    for i in range(idx, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[idx:i + 1]
    return None


def lib_symbol_body(lib: str, name: str) -> str:
    """Self-contained symbol body for the (lib_symbols) cache.

    ``(extends "parent")`` is resolved by splicing the parent's graphic/pin
    sub-units onto the child's own properties -- KiCad resolves pin positions and
    electrical types from this cache, and an unresolved extends would leave the
    symbol pinless.
    """
    text = _lib_text(lib)
    block = _block(text, name)
    if block is None:
        raise SystemExit(f"symbol not found: {lib}:{name}")
    m = re.search(r'\(extends\s+"([^"]+)"\)', block)
    if not m:
        return block
    parent = m.group(1)
    pblock = _block(text, parent)
    if pblock is None:
        raise SystemExit(f"parent symbol not found: {lib}:{parent}")
    inner = block[block.index(f'"{name}"') + len(name) + 2: block.rindex(")")]
    inner = re.sub(r'\s*\(extends\s+"[^"]+"\)', "", inner, count=1)
    units = re.findall(
        r'\(symbol\s+"' + re.escape(parent) + r'_\d+_\d+".*?\n\t\t\)',
        pblock, re.DOTALL,
    )
    units = [u.replace(f'"{parent}_', f'"{name}_') for u in units]
    return (f'(symbol "{name}"\n' + inner.rstrip() + "\n"
            + "\n".join("\t\t" + u for u in units) + "\n\t)")


def parse_pins(lib: str, name: str, unit: int) -> list[dict]:
    """Pin geometry for one unit: number, electrical type, local x/y/angle."""
    text = _lib_text(lib)
    block = _block(text, name)
    m = re.search(r'\(extends\s+"([^"]+)"\)', block) if block else None
    geom_name = m.group(1) if m else name
    geom = _block(text, geom_name) if m else block
    subs = [s for s in re.findall(
        r'\(symbol\s+"' + re.escape(geom_name) + r'_\d+_\d+".*?\n\t\t\)',
        geom, re.DOTALL)
        if re.match(r'\(symbol\s+"[^"]+_(0|%d)_\d+"' % unit, s)]
    out: list[dict] = []
    for sub in subs:
        i = 0
        while True:
            j = sub.find("(pin ", i)
            if j == -1:
                break
            depth, k = 0, j
            while k < len(sub):
                if sub[k] == "(":
                    depth += 1
                elif sub[k] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            b, i = sub[j:k + 1], k + 1
            head = re.match(r"\(pin\s+(\w+)\s+(\w+)", b)
            at = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)", b)
            num = re.search(r'\(number\s+"([^"]+)"', b)
            if head and at:
                out.append(dict(num=num.group(1) if num else "?",
                                etype=head.group(1),
                                x=float(at.group(1)), y=float(at.group(2)),
                                ang=float(at.group(3))))
    return out


def _rot(lx, ly, ang):
    """Rotate a symbol-local (already Y-flipped) offset by a placement angle.

    KiCad's placement angle turns the symbol counter-clockwise *on screen*, and
    screen Y grows downward, so the rotation applied to these coordinates is the
    negative one. Getting this backwards silently swaps pin 1 and pin 2 on every
    part placed at 90 deg -- harmless on a resistor, wrong on a polarised cap.
    """
    a = math.radians(-ang)
    return lx * math.cos(a) - ly * math.sin(a), lx * math.sin(a) + ly * math.cos(a)


# ref -> {unit: (lib_id, x, y, angle)}
PLACEMENT: dict[str, dict[int, tuple]] = {}
for _ref, _lib, _val, _fp, _x, _y, _a, _u in COMPONENTS:
    PLACEMENT.setdefault(_ref, {})[_u] = (_lib, _x, _y, _a)


def unit_of(ref: str, pin: str) -> int:
    if ref == "U1":
        return U1_PIN_UNIT[pin]
    return 1


def unit_pin_ids(lib_id: str, unit: int) -> list[str]:
    if lib_id == "Amplifier_Operational:TL074":
        return TL074_UNIT_PINS[unit]
    ids = PIN_IDS.get(lib_id)
    if ids is None:
        raise SystemExit(f"no pin map for {lib_id}")
    return ids


def endpoint_of(ref: str, pin: str):
    """Absolute schematic coords of a pin's connection point.

    Symbol-local Y is up while schematic Y is down, so local Y is negated before
    the placement rotation is applied.
    """
    unit = unit_of(ref, pin)
    lib_id, sx, sy, sang = PLACEMENT[ref][unit]
    lib, name = lib_id.split(":", 1)
    for p in parse_pins(lib, name, unit):
        if p["num"] == pin:
            rx, ry = _rot(p["x"], -p["y"], sang)
            return round(sx + rx, 4), round(sy + ry, 4)
    raise SystemExit(f"pin {pin} not found on {ref} ({lib_id} unit {unit})")


def pin_outward(ref: str, pin: str):
    """Unit vector pointing away from the symbol body (where the stub goes)."""
    unit = unit_of(ref, pin)
    lib_id, _sx, _sy, sang = PLACEMENT[ref][unit]
    lib, name = lib_id.split(":", 1)
    p = next(q for q in parse_pins(lib, name, unit) if q["num"] == pin)
    a = math.radians(p["ang"] + 180)               # (at .. ang) points inward
    dx, dy = _rot(math.cos(a), -math.sin(a), sang)
    if abs(dx) >= abs(dy):
        return (1.0 if dx > 0 else -1.0), 0.0
    return 0.0, (1.0 if dy > 0 else -1.0)


def stub_far(ref: str, pin: str):
    x, y = endpoint_of(ref, pin)
    dx, dy = pin_outward(ref, pin)
    return round(x + dx * _STUB, 4), round(y + dy * _STUB, 4)


# --- renderers --------------------------------------------------------------
def field_pos(x, y, angle):
    """Where the Reference/Value text goes so it clears the pin stubs.

    Wires and net labels leave along the pin axis, so the text has to sit off
    that axis: beside a vertically-placed part, above a horizontal one, and on
    the far side of a part rotated 180 deg (whose pins face right).
    """
    if angle in (90, 270):
        return (x, round(y - 7.62, 2)), (x, round(y - 5.08, 2)), ""
    if angle == 180:
        return ((round(x - 6.35, 2), round(y - 3.81, 2)),
                (round(x - 6.35, 2), round(y - 1.27, 2)), "\n\t\t\t\t(justify right)")
    return ((round(x + 6.35, 2), round(y - 3.81, 2)),
            (round(x + 6.35, 2), round(y - 1.27, 2)), "\n\t\t\t\t(justify left)")


def render_symbol(ref, lib_id, value, footprint, x, y, angle, unit) -> str:
    pins = "\n".join(f'\t\t(pin "{p}"\n\t\t\t(uuid "{uid()}")\n\t\t)'
                     for p in unit_pin_ids(lib_id, unit))
    (rx, ry), (vx, vy), just = field_pos(x, y, angle)
    return f'''\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x} {y} {angle})
\t\t(unit {unit})
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
\t\t(property "Reference" "{ref}"
\t\t\t(at {rx} {ry} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t){just}
\t\t\t)
\t\t)
\t\t(property "Value" "{value}"
\t\t\t(at {vx} {vy} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t){just}
\t\t\t)
\t\t)
\t\t(property "Footprint" "{footprint}"
\t\t\t(at {x} {y} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Datasheet" "~"
\t\t\t(at {x} {y} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Description" ""
\t\t\t(at {x} {y} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
{pins}
\t\t(instances
\t\t\t(project "{PROJ_NAME}"
\t\t\t\t(path "/{PROJ_UUID}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit {unit})
\t\t\t\t)
\t\t\t)
\t\t)
\t)'''


def render_wire(x1, y1, x2, y2) -> str:
    return (f'\t(wire\n\t\t(pts\n\t\t\t(xy {x1} {y1}) (xy {x2} {y2})\n\t\t)\n'
            f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n'
            f'\t\t(uuid "{uid()}")\n\t)')


def render_label(name, x, y, dx=1.0) -> str:
    """Net label at a stub end, reading away from the symbol.

    A left-pointing stub with left-justified text would run the net name back
    across the part it belongs to -- which is exactly where the 6-pin jumper
    headers get unreadable.
    """
    just = "right bottom" if dx < 0 else "left bottom"
    return (f'\t(label "{name}"\n\t\t(at {x} {y} 0)\n\t\t(effects\n'
            f'\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
            f'\t\t\t(justify {just})\n\t\t)\n\t\t(uuid "{uid()}")\n\t)')


def render_text(x, y, size, body) -> str:
    esc = body.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return (f'\t(text "{esc}"\n\t\t(exclude_from_sim no)\n\t\t(at {x} {y} 0)\n'
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {size} {size})\n\t\t\t)\n'
            f'\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "{uid()}")\n\t)')


def render_pwr_flag(x, y, idx) -> str:
    ref = f"#FLG{idx:03d}"
    return f'''\t(symbol
\t\t(lib_id "power:PWR_FLAG")
\t\t(at {x} {y} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
\t\t(property "Reference" "{ref}"
\t\t\t(at {x} {round(y - 2.54, 2)} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Value" "PWR_FLAG"
\t\t\t(at {x} {round(y - 5.08, 2)} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Footprint" ""
\t\t\t(at {x} {y} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Datasheet" ""
\t\t\t(at {x} {y} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(pin "1"
\t\t\t(uuid "{uid()}")
\t\t)
\t\t(instances
\t\t\t(project "{PROJ_NAME}"
\t\t\t\t(path "/{PROJ_UUID}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)'''


PWR_FLAG_LIB = '''\t\t(symbol "power:PWR_FLAG"
\t\t\t(power)
\t\t\t(pin_numbers
\t\t\t\t(hide yes)
\t\t\t)
\t\t\t(pin_names
\t\t\t\t(offset 0)
\t\t\t\t(hide yes)
\t\t\t)
\t\t\t(exclude_from_sim no)
\t\t\t(in_bom yes)
\t\t\t(on_board yes)
\t\t\t(property "Reference" "#FLG"
\t\t\t\t(at 0 1.905 0)
\t\t\t\t(effects
\t\t\t\t\t(font
\t\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t\t)
\t\t\t\t\t(hide yes)
\t\t\t\t)
\t\t\t)
\t\t\t(property "Value" "PWR_FLAG"
\t\t\t\t(at 0 3.81 0)
\t\t\t\t(effects
\t\t\t\t\t(font
\t\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t\t)
\t\t\t\t)
\t\t\t)
\t\t\t(property "Footprint" ""
\t\t\t\t(at 0 0 0)
\t\t\t\t(effects
\t\t\t\t\t(font
\t\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t\t)
\t\t\t\t\t(hide yes)
\t\t\t\t)
\t\t\t)
\t\t\t(property "Datasheet" ""
\t\t\t\t(at 0 0 0)
\t\t\t\t(effects
\t\t\t\t\t(font
\t\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t\t)
\t\t\t\t\t(hide yes)
\t\t\t\t)
\t\t\t)
\t\t\t(property "Description" "Special symbol for telling ERC where power comes from"
\t\t\t\t(at 0 0 0)
\t\t\t\t(effects
\t\t\t\t\t(font
\t\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t\t)
\t\t\t\t\t(hide yes)
\t\t\t\t)
\t\t\t)
\t\t\t(symbol "PWR_FLAG_0_0"
\t\t\t\t(pin power_out line
\t\t\t\t\t(at 0 0 90)
\t\t\t\t\t(length 0)
\t\t\t\t\t(name "~"
\t\t\t\t\t\t(effects
\t\t\t\t\t\t\t(font
\t\t\t\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t\t\t\t)
\t\t\t\t\t\t)
\t\t\t\t\t)
\t\t\t\t\t(number "1"
\t\t\t\t\t\t(effects
\t\t\t\t\t\t\t(font
\t\t\t\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t\t\t\t)
\t\t\t\t\t\t)
\t\t\t\t\t)
\t\t\t\t)
\t\t\t)
\t\t\t(symbol "PWR_FLAG_0_1"
\t\t\t\t(polyline
\t\t\t\t\t(pts
\t\t\t\t\t\t(xy 0 0) (xy 0 1.27) (xy -1.016 1.905)
\t\t\t\t\t\t(xy 0 2.54) (xy 1.016 1.905) (xy 0 1.27)
\t\t\t\t\t)
\t\t\t\t\t(stroke
\t\t\t\t\t\t(width 0)
\t\t\t\t\t\t(type default)
\t\t\t\t\t)
\t\t\t\t\t(fill
\t\t\t\t\t\t(type none)
\t\t\t\t\t)
\t\t\t\t)
\t\t\t)
\t\t\t(embedded_fonts no)
\t\t)'''


def render_lib_symbols() -> str:
    bodies = [PWR_FLAG_LIB]
    for lib_id in dict.fromkeys(c[1] for c in COMPONENTS):
        lib, name = lib_id.split(":", 1)
        body = lib_symbol_body(lib, name)
        body = body.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)
        bodies.append("\t\t" + body.replace("\n", "\n\t"))
    return "\t(lib_symbols\n" + "\n".join(bodies) + "\n\t)"


HEADER = f'''(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "9.0")
\t(uuid "{PROJ_UUID}")
\t(paper "A2")
\t(title_block
\t\t(title "Bose Companion 5 sub crossover")
\t\t(date "2026-08-16")
\t\t(rev "B")
\t\t(comment 1 "Mono-summing 2nd-order Sallen-Key low-pass, single +12 V rail")
\t\t(comment 2 "Single-sided THT, CNC isolation milling (0.8 mm end mill), laser silkscreen")
\t)'''

FOOTER = '''\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
'''


def main() -> None:
    parts = [HEADER, render_lib_symbols()]
    for comp in COMPONENTS:
        parts.append(render_symbol(*comp))

    wiring: list[str] = []
    for net, ref, pin in NETS:
        x, y = endpoint_of(ref, pin)
        fx, fy = stub_far(ref, pin)
        wiring.append(render_wire(x, y, fx, fy))
        wiring.append(render_label(net, fx, fy, pin_outward(ref, pin)[0]))
    for i, (_net, ref, pin) in enumerate(PWR_FLAGS, start=1):
        fx, fy = stub_far(ref, pin)
        wiring.append(render_pwr_flag(fx, fy, i))
    parts.extend(wiring)
    parts.extend(render_text(x, y, s, b) for x, y, s, b in NOTES)
    parts.append(FOOTER)

    SCH.write_text("\n".join(parts), encoding="utf-8")
    print(f"{SCH.name}: {len(COMPONENTS)} symbol blocks, {len(NETS)} pin "
          f"connections, {len(set(n for n, _, _ in NETS))} nets")


if __name__ == "__main__":
    main()
