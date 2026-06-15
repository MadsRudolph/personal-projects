"""Generate the ESP32 KORAD carrier schematic (KiCad 9) — dev-board version.

The carrier sockets a 30-pin LoLin/DOIT NodeMCU v3 (ESP8266; ~28.4 mm between the two
1x15 rows) and taps the KORAD J9 UART through a BS170 level shifter to the NodeMCU's
hardware RX/TX (GPIO3/GPIO1), the profi-max approach. The dev board brings its own USB
flashing + 3.3 V regulator, so the carrier is just: sockets + J9 connector + level
shifter + power-select + bulk/decoupling. All through-hole (laser process). Connectivity
is by net-name labels + power symbols on each pin's connection point.

Run with PYTHONUTF8=1:  PYTHONUTF8=1 python build_schematic.py
"""
import copy, os, uuid, math
from kiutils.schematic import Schematic
from kiutils.symbol import SymbolLib
from kiutils.items.schitems import (SchematicSymbol, LocalLabel, NoConnect,
    SymbolProjectInstance, SymbolProjectPath, Connection)
from kiutils.items.common import Position, Property, Effects, PageSettings, Stroke

SYM = r"C:/Program Files/KiCad/9.0/share/kicad/symbols"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "korad-esp32-carrier.kicad_sch")

_libcache = {}
def load_lib(fn):
    if fn not in _libcache:
        _libcache[fn] = SymbolLib.from_file(os.path.join(SYM, fn))
    return _libcache[fn]

def find_sym(fn, name):
    for s in load_lib(fn).symbols:
        nm = s.libId.split(":")[-1] if s.libId else s.entryName
        if nm == name:
            return s
    raise KeyError(name)

def resolve(fn, name, nick):
    s = find_sym(fn, name)
    ext = getattr(s, "extends", None)
    if ext:
        parent = copy.deepcopy(find_sym(fn, ext))
        parent.libId = f"{nick}:{name}"; parent.entryName = name; parent.extends = None
        return parent
    s2 = copy.deepcopy(s); s2.libId = f"{nick}:{name}"
    return s2

def pins_of(sym):
    out = {}
    for u in sym.units:
        for p in u.pins:
            out[p.number] = (p.position.X, p.position.Y, p.position.angle)
    for p in sym.pins:
        out[p.number] = (p.position.X, p.position.Y, p.position.angle)
    return out

sch = Schematic().create_new()
sch.paper = PageSettings(paperSize="A3")
if not sch.uuid:
    sch.uuid = str(uuid.uuid4())
ROOT = "/" + sch.uuid

LIBDEFS = {
    "Device:R":            ("Device.kicad_sym", "R", "Device"),
    "Device:C":            ("Device.kicad_sym", "C", "Device"),
    "Device:C_Polarized":  ("Device.kicad_sym", "C_Polarized", "Device"),
    "Transistor_FET:BS170": ("Transistor_FET.kicad_sym", "BS170", "Transistor_FET"),
    "Connector_Generic:Conn_01x03": ("Connector_Generic.kicad_sym", "Conn_01x03", "Connector_Generic"),
    "Connector_Generic:Conn_01x04": ("Connector_Generic.kicad_sym", "Conn_01x04", "Connector_Generic"),
    "Connector_Generic:Conn_01x15": ("Connector_Generic.kicad_sym", "Conn_01x15", "Connector_Generic"),
    "power:GND":           ("power.kicad_sym", "GND", "power"),
    "power:+3V3":          ("power.kicad_sym", "+3V3", "power"),
    "power:PWR_FLAG":      ("power.kicad_sym", "PWR_FLAG", "power"),
}
LIBPINS = {}
for libid, (fn, name, nick) in LIBDEFS.items():
    s = resolve(fn, name, nick)
    sch.libSymbols.append(s)
    LIBPINS[libid] = pins_of(s)

def mkprop(key, value, x, y, hide=False):
    eff = Effects()
    if hide:
        eff.hide = True
    return Property(key=key, value=value, position=Position(x, y, 0), effects=eff)

def snap(v):
    return round(v / 1.27) * 1.27

def place(libid, ref, value, x, y, footprint="", angle=0):
    x, y = snap(x), snap(y)
    nick, name = libid.split(":")
    pins = {num: str(uuid.uuid4()) for num in LIBPINS[libid].keys()}
    is_power = nick == "power"
    props = [
        mkprop("Reference", ref, x, y - 3.5),
        mkprop("Value", value, x, y + 3.5),
        mkprop("Footprint", footprint, x, y, hide=True),
        mkprop("Datasheet", "~", x, y, hide=True),
    ]
    sy = SchematicSymbol(
        libraryNickname=nick, entryName=name, position=Position(x, y, angle),
        unit=1, inBom=not is_power, onBoard=not is_power, uuid=str(uuid.uuid4()),
        properties=props, pins=pins,
        instances=[SymbolProjectInstance(name="kicad_default",
            paths=[SymbolProjectPath(sheetInstancePath=ROOT, reference=ref, unit=1)])],
    )
    sch.schematicSymbols.append(sy)
    return sy

def pin_geo(sym, num):
    px, py, a = LIBPINS[f"{sym.libraryNickname}:{sym.entryName}"][num]
    x, y = sym.position.X + px, sym.position.Y - py
    out = (a or 0) + 180.0
    return x, y, round(math.cos(math.radians(out)), 6), round(-math.sin(math.radians(out)), 6)

def add_label(text, x, y):
    sch.labels.append(LocalLabel(text=text, position=Position(x, y, 0)))

def add_wire(x1, y1, x2, y2):
    sch.graphicalItems.append(Connection(type="wire",
        points=[Position(x1, y1), Position(x2, y2)], stroke=Stroke()))

def nc_unused(sym, used):
    """Put a no-connect flag on every pin of `sym` not in `used` (intentional sockets)."""
    for num in LIBPINS[f"{sym.libraryNickname}:{sym.entryName}"]:
        if num not in used:
            x, y, _, _ = pin_geo(sym, num)
            sch.noConnects.append(NoConnect(position=Position(x, y)))

POWER_NETS = {"GND": "power:GND", "+3V3": "power:+3V3"}
STUB = 2.54

def connect(sym, num, net):
    x, y, dx, dy = pin_geo(sym, num)
    ex, ey = x + dx * STUB, y + dy * STUB
    add_wire(x, y, ex, ey)
    if net in POWER_NETS:
        place(POWER_NETS[net], "#PWR", net, ex, ey)
    else:
        add_label(net, ex, ey)

def pwr_flag(net, x, y):
    p = place("power:PWR_FLAG", "#FLG", "PWR_FLAG", x, y)
    if net in POWER_NETS:
        connect(p, "1", net)
    else:
        fx, fy, _, _ = pin_geo(p, "1"); add_label(net, fx, fy)

FP = {
    # Laser-process picks (kicad-laser-pcb skill: footprints.md). THT only.
    "R":     "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    "Cc":    "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "Cbig":  "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm",
    "TO92":  "Package_TO_SOT_THT:TO-92_Inline_Wide",  # legs formed to 2.54mm so pad gap clears 0.8mm
    "H3":    "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
    "H4":    "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
    "SOCK15": "Connector_PinSocket_2.54mm:PinSocket_1x15_P2.54mm_Vertical",
}

# ---- Dev-board sockets: LoLin/DOIT NodeMCU v3 (ESP8266), 30-pin, two 1x15 rows.
# Left row  (pin1=A0 top .. pin15=VIN): pin14=GND, pin15=VIN.
# Right row (pin1=D0 top .. pin15=3V3): pin12=RX(GPIO3), pin13=TX(GPIO1), pin15=3V3.
# VERIFY these 5 positions against the board silk before etching (one-line remap if off).
j3 = place("Connector_Generic:Conn_01x15", "J3", "NODEMCU_L", 130, 80, FP["SOCK15"])
connect(j3, "14", "GND")       # left pin 14 = GND
connect(j3, "15", "VIN_DEV")   # left pin 15 = VIN (5 V in)
j4 = place("Connector_Generic:Conn_01x15", "J4", "NODEMCU_R", 175, 80, FP["SOCK15"])
connect(j4, "12", "ESP_RX")    # right pin 12 = RX / GPIO3  <- KORAD TX
connect(j4, "13", "ESP_TX")    # right pin 13 = TX / GPIO1  -> KORAD RX
connect(j4, "15", "+3V3")      # right pin 15 = 3V3
nc_unused(j3, {"14", "15"})    # remaining socket positions are mechanical only
nc_unused(j4, {"12", "13", "15"})

# ---- J9 tap on the PSU
j1 = place("Connector_Generic:Conn_01x04", "J1", "J9_to_PSU", 50, 95, FP["H4"])
for num, net in {"1": "GND", "2": "J9_RX", "3": "J9_TX", "4": "J9_VDD"}.items():
    connect(j1, num, net)

# ---- Power select: J9_VDD -> dev-board VIN (5 V unit) or 3V3 pin (3.3 V unit)
p1 = place("Connector_Generic:Conn_01x03", "P1", "PWR_SEL", 90, 60, FP["H3"])
for num, net in {"1": "VIN_DEV", "2": "J9_VDD", "3": "+3V3"}.items():
    connect(p1, num, net)

# ---- BS170 level shifter (HV = J9_VDD, LV = 3V3). Crossover ESP<->J9.
for ref, x, y, dnet, snet in [("Q1", 110, 150, "J9_RX", "ESP_TX"), ("Q2", 110, 185, "J9_TX", "ESP_RX")]:
    q = place("Transistor_FET:BS170", ref, "BS170", x, y, FP["TO92"])
    connect(q, "1", dnet)     # D
    connect(q, "2", "+3V3")   # G
    connect(q, "3", snet)     # S

rdef = [("R4", "+3V3", "ESP_TX", 90, 150), ("R5", "J9_VDD", "J9_RX", 130, 150),
        ("R6", "+3V3", "ESP_RX", 90, 185), ("R7", "J9_VDD", "J9_TX", 130, 185)]
for ref, n1, n2, x, y in rdef:
    r = place("Device:R", ref, "10k", x, y, FP["R"])
    connect(r, "1", n1); connect(r, "2", n2)

# ---- Bulk + decoupling
c4 = place("Device:C_Polarized", "C4", "470uF", 50, 150, FP["Cbig"])
connect(c4, "1", "J9_VDD"); connect(c4, "2", "GND")
c2 = place("Device:C", "C2", "100nF", 210, 110, FP["Cc"])
connect(c2, "1", "+3V3"); connect(c2, "2", "GND")

# ---- PWR_FLAGs so ERC sees a source on connector-/devboard-fed supply nets
pwr_flag("J9_VDD", 40, 120)
pwr_flag("VIN_DEV", 40, 60)
pwr_flag("+3V3", 250, 60)
pwr_flag("GND", 265, 60)

sch.to_file(OUT)

import json
pro = {
    "board": {}, "boards": [], "cvpcb": {"equivalence_files": []},
    "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
    "meta": {"filename": "korad-esp32-carrier.kicad_pro", "version": 3},
    "net_settings": {}, "pcbnew": {},
    "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
    "sheets": [[sch.uuid, "Root"]],
    "text_variables": {},
}
with open(os.path.join(HERE, "korad-esp32-carrier.kicad_pro"), "w", encoding="utf-8") as f:
    json.dump(pro, f, indent=2)

print("wrote", OUT)
print("symbols:", len(sch.schematicSymbols), "labels:", len(sch.labels))
