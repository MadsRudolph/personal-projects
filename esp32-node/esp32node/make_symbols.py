#!/usr/bin/env python3
"""Generate esp32node.kicad_sym, the project symbol library.

ESP32-WROOM-32_Phys -- ESP32-WROOM-32 with pins in module (physical) order.
CH340C_3V3          -- stock CH340C with V3 typed power_in: in the datasheet's
                       3.3 V mode V3 is tied to VCC and fed, not a regulator
                       output, and the stock power_out type makes ERC flag it
                       against the AMS1117's VO.

The stock RF_Module:ESP32-WROOM-32 symbol sorts the right-hand pins by GPIO
number. The breakout headers J2/J3 follow the module's physical pin order
(which is what keeps the single-sided route clean), so against the stock
symbol every header run crosses every other one and the sheet falls back to
labels. With the pins in physical order each header wires straight across.

Left side, top to bottom  = J2 pins 1..16 (module pins 2..16).
Right side, top to bottom = J3 pins 1..16 (module pins 38..23).
Pin numbers, names and electrical types are copied from the stock symbol.
"""
import re
from pathlib import Path

STOCK = Path("/usr/share/kicad/symbols/RF_Module.kicad_sym")
NAME = "ESP32-WROOM-32_Phys"
LEFT = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, None, 1]      # J2 order
RIGHT = [38, 37, 36, 35, 34, 33, 31, 30, 29, 28, 27, 26, 25, 24, 23, 39]  # J3 order
BOTTOM = [17, 18, 19, 20, 21, 22, 32]                                  # flash + NC
HIDDEN_ON = {15: 1}          # pin 15 stacks, hidden, under pin 1 (as in stock)

def stock_pins():
    t = STOCK.read_text()
    i = t.index('(symbol "ESP32-WROOM-32"')
    s = t[i:t.index('(symbol "ESP32-WROOM-32D"', i)] if '(symbol "ESP32-WROOM-32D"' in t else t[i:i + 12000]
    pins = {}
    for m in re.finditer(r'\(pin (\w+) (\w+)\s*\(at [^)]*\).*?\(name "([^"]*)".*?\(number "([^"]*)"', s, re.S):
        pins[int(m[4])] = (m[1], m[3])
    return pins

def pin(kind, name, num, x, y, ang, hide=False):
    h = "\n\t\t\t\t(hide yes)" if hide else ""
    return f'''\t\t\t(pin {kind} line
\t\t\t\t(at {x} {y} {ang})
\t\t\t\t(length 2.54){h}
\t\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27))))
\t\t\t)'''

def prop(k, v, x, y, hide=False, justify=""):
    j = f" (justify {justify})" if justify else ""
    h = " (hide yes)" if hide else ""
    return f'\t\t(property "{k}" "{v}" (at {x} {y} 0){h} (effects (font (size 1.27 1.27)){j}))'

def ch340c_3v3():
    t = Path("/usr/share/kicad/symbols/Interface_USB.kicad_sym").read_text()
    i = t.index('(symbol "CH340C"')
    d = 0
    for j in range(i, len(t)):
        d += (t[j] == "(") - (t[j] == ")")
        if d == 0:
            break
    s = t[i:j + 1].replace('"CH340C"', '"CH340C_3V3"', 1)
    s = s.replace('(symbol "CH340C_0_1"', '(symbol "CH340C_3V3_0_1"').replace('(symbol "CH340C_1_1"', '(symbol "CH340C_3V3_1_1"')
    s = s.replace('(property "Value" "CH340C_3V3"', '(property "Value" "CH340C"')
    k = s.index('(name "V3"')
    p = s.rfind("(pin power_out", 0, k)
    assert p != -1 and s.count("(pin ", p, k) == 1, "V3 pin not found as power_out"
    s = s[:p] + "(pin power_in" + s[p + len("(pin power_out"):]
    return "\t" + s

def main():
    sp = stock_pins()
    out, pos = [], {}
    for k, n in enumerate(LEFT):
        if n is not None:
            pos[n] = (-15.24, round(20.32 - 2.54 * k, 2), 0)
    for k, n in enumerate(RIGHT):
        pos[n] = (15.24, round(20.32 - 2.54 * k, 2), 180)
    for k, n in enumerate(BOTTOM):
        pos[n] = (round(-7.62 + 2.54 * k, 2), -35.56, 90)
    for n, on in HIDDEN_ON.items():
        pos[n] = pos[on]
    assert sorted(pos) == sorted(sp), set(sp) ^ set(pos)
    for n in sorted(pos):
        kind, name = sp[n]
        x, y, a = pos[n]
        if n in (38, 39):
            kind = "power_in"          # visible GND pins: power_in like pin 1
        out.append(pin(kind, name, n, x, y, a, hide=n in HIDDEN_ON))
    body = f'''\t\t(symbol "{NAME}_0_1"
\t\t\t(rectangle (start -12.7 22.86) (end 12.7 -33.02)
\t\t\t\t(stroke (width 0.254) (type default)) (fill (type background)))
\t\t)'''
    lib = "\n".join([
        '(kicad_symbol_lib',
        '\t(version 20241209)',
        '\t(generator "esp32node")',
        f'\t(symbol "{NAME}"',
        '\t\t(exclude_from_sim no) (in_bom yes) (on_board yes)',
        prop("Reference", "U", -12.7, 24.13, justify="left"),
        prop("Value", "ESP32-WROOM-32", 1.27, 24.13, justify="left"),
        prop("Footprint", "RF_Module:ESP32-WROOM-32", 0, -40.64, hide=True),
        prop("Datasheet", "https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32_datasheet_en.pdf", 0, 0, hide=True),
        prop("Description", "ESP32-WROOM-32, pins in module order (J2/J3 breakout)", 0, 0, hide=True),
        body,
        f'\t\t(symbol "{NAME}_1_1"',
        *out,
        '\t\t)',
        '\t)',
        ch340c_3v3(),
        ')',
    ])
    Path(__file__).with_name("esp32node.kicad_sym").write_text(lib + "\n")
    Path(__file__).with_name("sym-lib-table").write_text(
        '(sym_lib_table\n\t(version 7)\n\t(lib (name "esp32node") (type "KiCad") '
        '(uri "${KIPRJMOD}/esp32node.kicad_sym") (options "") (descr "project symbols"))\n)\n')
    print("wrote esp32node.kicad_sym: ESP32-WROOM-32_Phys (%d pins), CH340C_3V3" % len(out))

if __name__ == "__main__":
    main()
