#!/usr/bin/env python3
"""Draw the protoboard prototype schematic.

This is the breadboard-stage circuit, not the PCB: a classic ESP32 DevKit
(WROOM-32) with two transistor level shifters between it and the caliper's
data port. Run it and open ../protoboard.kicad_sch.

    py -3.13 protoboard_layout.py

Two deliberate departures from the house style, both forced by the parts:

* U1 is mirrored. Every usable GPIO on the ESP32 module symbol sits on its
  right-hand edge, so an unmirrored symbol would need both signals routed
  around the outside of the box to get at them. Mirroring puts the GPIO bank
  on the left where the incoming signals already are. The rule against
  mirroring exists so op-amps stay recognisable at a glance; a rectangular
  MCU has no such canonical shape to destroy.

* U1 is the bare module symbol because KiCad ships no DevKit board symbol.
  The pin names are what matter here and they match the DevKit's silkscreen.
  Everything the module needs that the DevKit already provides -- the
  regulator, USB bridge, EN pull-up, boot strapping -- is marked no-connect.

The circuit itself, per line: caliper high turns the transistor on and pulls
the ESP32 pin to 0 V; caliper low leaves it off and the collector resistor
pulls the pin to 3V3. So it inverts, which is what SHIFTER_INVERTS 1 in
firmware/include/config.h accounts for.
"""

import os
import sys

SKILL = r"C:\Users\Mads2\.claude\skills\kicad-schematic\scripts"
sys.path.insert(0, SKILL)

from schdraw import Sheet                                    # noqa: E402

G = lambda n: round(n * 1.27, 2)                             # noqa: E731

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "protoboard.kicad_sch")
PRO = os.path.join(HERE, "..", "protoboard.kicad_pro")

# ---------------------------------------------------------------------------
# Floorplan. Signal flows left to right: caliper, shifter, ESP32.
# A4 rather than A3 -- the content is about 150 x 130 mm and on A3 it floated
# in a third of the sheet, which reads far worse than a full smaller page.
# ---------------------------------------------------------------------------
Y_CLK = G(40)          # CLK stage centreline
Y_DATA = G(78)         # DATA stage centreline, 48 mm below

X_J1 = G(14)           # caliper connector
X_RB = G(36)           # base resistors
X_Q = G(58)            # transistors
X_ESP = G(120)         # ESP32 centre; its GPIO edge lands 15.24 to the left

ESP_Y = G(46)          # puts IO25/IO26 between the two stage collectors

sh = Sheet(paper="A4", project="protoboard", project_file=PRO,
           title="BLE Digital Caliper -- protoboard prototype")


def stage(n, sig_y, cal_pin, fan_x, esp_pin, turn_x, name):
    """One inverting common-emitter level shifter, caliper -> ESP32."""
    rb = sh.place("Device:R", f"R{2*n-1}", at=(X_RB, sig_y), rot=90,
                  value="10k")
    q = sh.place("Transistor_BJT:BC547", f"Q{n}", at=(X_Q, sig_y),
                 value="BC547")
    col = q.pin("C")
    rc = sh.place("Device:R", f"R{2*n}", at=(col.x, sig_y - G(12)),
                  value="10k")

    # Caliper pins are on a 2.54 mm pitch and the two stages are 40 mm
    # apart, so each pin fans out horizontally to its own column before
    # turning -- a shared column would short them together.
    sh.seg(cal_pin, (fan_x, cal_pin.y))
    sh.seg((fan_x, cal_pin.y), (fan_x, sig_y))
    sh.seg((fan_x, sig_y), rb.pin(1))
    sh.seg(rb.pin(2), q.pin("B"))

    # collector pull-up straight up to its own 3V3 symbol
    sh.seg(col, rc.pin(2))
    sh.rail(rc.pin(1), net="+3V3")

    # emitter straight down to its own ground
    sh.gnd(q.pin("E"), drop=G(4))

    # collector out to the ESP32: right, then across to the pin's row
    sh.seg(col, (turn_x, col.y))
    sh.seg((turn_x, col.y), (turn_x, esp_pin.y))
    sh.seg((turn_x, esp_pin.y), esp_pin)

    sh.note((X_Q - G(14), sig_y - G(17)), name, size=1.6)
    return q, rb, rc


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------
# rot=180 faces the pins right and puts pin 1 (GND) at the bottom, so its
# ground drop does not have to cross the three signal rows above it.
j1 = sh.place("Connector_Generic:Conn_01x04", "J1",
              at=(X_J1, Y_CLK + G(12)), rot=180, value="CALIPER")

# Mirrored so the GPIO bank faces the incoming signals -- see the module note.
esp = sh.place("RF_Module:ESP32-WROOM-32", "U1", at=(X_ESP, ESP_Y),
               mirror="y", value="ESP32 DevKit")

sw1 = sh.place("Switch:SW_Push", "SW1", at=(G(96), G(88)), value="SEND")
sw2 = sh.place("Switch:SW_Push", "SW2", at=(G(96), G(98)), value="SEND+SP")

# ---------------------------------------------------------------------------
# The two shifter stages
# ---------------------------------------------------------------------------
q1, r1, r2 = stage(1, Y_CLK, j1.pin(3), G(21), esp.pin("IO25"), G(95),
                   "CLK stage  (caliper orange)")
q2, r3, r4 = stage(2, Y_DATA, j1.pin(2), G(24), esp.pin("IO26"), G(99),
                   "DATA stage  (caliper green)")

# ---------------------------------------------------------------------------
# Caliper ground and the unused VDD pad
# ---------------------------------------------------------------------------
sh.gnd(j1.pin(1), drop=G(6))

# Every deliberately unconnected pin, tracked so the netlist check can expect
# them as isolated nodes rather than reporting each one as a surprise.
NO_CONNECT = [("J1", "4")]
sh.nc(j1.pin(4))

# ---------------------------------------------------------------------------
# ESP32 supply and buttons
# ---------------------------------------------------------------------------
sh.rail(esp.pin(2), net="+3V3")
sh.gnd(esp.pin(1), drop=G(4))

for sw, esp_pin, turn_x in ((sw1, esp.pin("IO32"), G(103)),
                            (sw2, esp.pin("IO33"), G(106))):
    out = sw.pin(2)
    sh.seg(out, (turn_x, out.y))
    sh.seg((turn_x, out.y), (turn_x, esp_pin.y))
    sh.seg((turn_x, esp_pin.y), esp_pin)
    sh.gnd(sw.pin(1), drop=G(4))

# Nothing on this sheet drives either rail -- the DevKit's own regulator does
# -- so assert that to ERC rather than leaving it to complain.
for net, sym, at in (("+3V3", "power:+3V3", (G(150), G(14))),
                     ("GND", "power:GND", (G(160), G(18)))):
    sh.power(sym, at)
    tail = (at[0], at[1] + G(4)) if net == "+3V3" else (at[0], at[1] - G(4))
    sh.seg(at, tail)
    sh.power("power:PWR_FLAG", tail)

# Every module pin the DevKit already handles for us.
USED = {"2", "1", "15", "38", "39", "10", "11", "8", "9"}
for p in esp.pins:
    if p.number not in USED:
        sh.nc(p)
        NO_CONNECT.append(("U1", p.number))

# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------
sh.note((G(9), G(8)), "BLE Digital Caliper -- protoboard prototype", size=2.2)
sh.note((G(9), G(12)),
        "Two inverting common-emitter shifters lift the caliper's 0-1.1 V "
        "logic to 0-3.3 V.", size=1.5)
sh.note((G(9), G(14.5)),
        "Caliper high -> transistor on -> ESP32 pin pulled LOW. "
        "That is SHIFTER_INVERTS 1 in config.h.", size=1.5)

# Below the DATA stage: the caliper fan-out drops a wire at x = 30.5 down to
# y = 99, so anything higher than this gets a wire drawn through it.
sh.note((G(8), G(88)), "J1 = the four tails off the caliper data port.",
        size=1.5)
sh.note((G(8), G(90.5)), "Identify them by WIRE COLOUR, not by pin number.",
        size=1.5)
sh.note((G(8), G(93)), "gray is caliper VDD, about 1.08 V: leave it OFF.",
        size=1.5)
sh.note((G(8), G(95.5)), "Tying gray to 3V3 drives 3.3 V into a 1.1 V rail",
        size=1.5)
sh.note((G(8), G(98)), "and can destroy the caliper.", size=1.5)

# Below the symbol (its body ends at y = 93.98) and right of the buttons,
# which occupy x 117-127.
sh.note((G(108), G(86)), "U1 is a classic ESP32 DevKit (WROOM-32).", size=1.5)
sh.note((G(108), G(88.5)), "Pin names match the board silkscreen.", size=1.5)
sh.note((G(108), G(91)), "The X marks are pins the DevKit already", size=1.5)
sh.note((G(108), G(93.5)), "handles for you -- do not wire them.", size=1.5)
sh.note((G(108), G(96)), "3V3 comes from the DevKit regulator, over USB.",
        size=1.5)

sh.note((G(74), G(108)), "SW1/SW2 are for BLE mode only -- not needed",
        size=1.5)
sh.note((G(74), G(110.5)), "for CALIPER_SNIFFER_MODE bring-up.", size=1.5)

sh.note((G(8), G(105)), "BC547: flat face toward you, legs down --", size=1.5)
sh.note((G(8), G(107.5)), "left = C = pin 1,  middle = B = pin 2,", size=1.5)
sh.note((G(8), G(110)), "right = E = pin 3.", size=1.5)
sh.note((G(8), G(113)), "A 2N3904 is the mirror image (E B C), so check", size=1.5)
sh.note((G(8), G(115.5)), "before soldering: diode mode, red on the middle", size=1.5)
sh.note((G(8), G(118)), "leg, both outer legs read ~0.7 V. The HIGHER of", size=1.5)
sh.note((G(8), G(120.5)), "the two is the EMITTER.", size=1.5)

# ---------------------------------------------------------------------------
# Verify, then emit
# ---------------------------------------------------------------------------
TARGET = {
    "GND": {("J1", "1"), ("Q1", "3"), ("Q2", "3"), ("SW1", "1"), ("SW2", "1"),
            ("U1", "1"), ("U1", "15"), ("U1", "38"), ("U1", "39")},
    "+3V3": {("R2", "1"), ("R4", "1"), ("U1", "2")},
    "CAL_CLK": {("J1", "3"), ("R1", "1")},
    "CLK_BASE": {("R1", "2"), ("Q1", "2")},
    "ESP_CLK": {("Q1", "1"), ("R2", "2"), ("U1", "10")},
    "CAL_DATA": {("J1", "2"), ("R3", "1")},
    "DATA_BASE": {("R3", "2"), ("Q2", "2")},
    "ESP_DATA": {("Q2", "1"), ("R4", "2"), ("U1", "11")},
    "BTN_SEND": {("SW1", "2"), ("U1", "8")},
    "BTN_ALT": {("SW2", "2"), ("U1", "9")},
}

for i, node in enumerate(NO_CONNECT):
    TARGET[f"NC{i}"] = {node}

problems = sh.check()
for p in problems:
    print("CHECK:", p)

print("\n--- pin positions used ---")
for label, pin in (("J1.1 GND black", j1.pin(1)), ("J1.2 DATA green", j1.pin(2)),
                   ("J1.3 CLK orange", j1.pin(3)), ("J1.4 VDD gray", j1.pin(4)),
                   ("U1 IO25", esp.pin("IO25")), ("U1 IO26", esp.pin("IO26")),
                   ("U1 IO32", esp.pin("IO32")), ("U1 IO33", esp.pin("IO33")),
                   ("U1 VDD", esp.pin(2)), ("U1 GND", esp.pin(1))):
    print(f"  {label:18s} ({pin.x:7.2f}, {pin.y:7.2f})")

ok = sh.verify_against(TARGET)
if not problems and ok:
    sh.emit(OUT)
    print(f"\nemitted {os.path.normpath(OUT)}")
else:
    print("\nNOT emitted -- fix the problems above")
    sys.exit(1)
