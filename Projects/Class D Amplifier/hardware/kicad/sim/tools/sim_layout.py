#!/usr/bin/env python3
"""Generate the Class D simulation testbenches as KiCad schematics.

    py -3.13 tools/sim_layout.py

One sheet per block of the amplifier, each a self-contained testbench with its
own sources and its own analysis directive, drawn to be read the same way the
board is. Open any of them in Eeschema and run Inspect -> Simulator.

Each sheet is its own KiCad project so the simulator has somewhere to keep its
settings. The netclass in every generated .kicad_pro carries wire_width -- see
the comment in write_project() for why that is not optional.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SKILL = Path(r"C:\Users\Mads2\.claude\skills\kicad-schematic\scripts")
sys.path.insert(0, str(SKILL))

from schdraw import Sheet          # noqa: E402
from symcache import SymCache      # noqa: E402

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
KICAD = SIM.parent
REPO = KICAD.parents[3]
TEMPLATE_PRO = (REPO / "Projects" / "Bose Sub Integration" / "hardware" /
                "kicad" / "subxo.kicad_pro")

MODELS = "models/classd_sim.lib"
VDMOS = "models/IRF-Power-VDMOS.mod"
GRID = 1.27


def G(n):
    return round(n * GRID, 4)


# stock symbols
R = "Device:R"
C = "Device:C"
CP = "Device:C_Polarized"
L = "Device:L"
OPA = "Simulation_SPICE:OPAMP"
VDC = "Simulation_SPICE:VDC"
VSIN = "Simulation_SPICE:VSIN"
VPULSE = "Simulation_SPICE:VPULSE"
CMP = "Comparator:LM311"
INV = "classd_sim:CD4049_SIM"
DRV = "Driver_FET:HIP4082xP"
FET = "Transistor_FET:IRF540N"
DIO = "Device:D_Schottky"

# Sim.Pins maps a symbol's pin NUMBERS onto the subcircuit's node NAMES.
SIM_OPAMP = {"Sim.Device": "SUBCKT", "Sim.Library": MODELS,
             "Sim.Name": "OPAMP_TL074",
             "Sim.Pins": "1=inp 2=inn 3=vp 4=vn 5=out"}
SIM_LM311 = {"Sim.Device": "SUBCKT", "Sim.Library": MODELS,
             "Sim.Name": "CMP_LM311",
             "Sim.Pins": "2=inp 3=inn 7=out 1=oe 8=vp 4=vn"}
SIM_INV = {"Sim.Device": "SUBCKT", "Sim.Library": MODELS,
           "Sim.Name": "INV_CD4049",
           "Sim.Pins": "1=in 2=out 3=vcc 4=vss"}
SIM_DRV = {"Sim.Device": "SUBCKT", "Sim.Library": MODELS,
           "Sim.Name": "DRV_HIP4082", "Sim.Params": "tdead=200n",
           "Sim.Pins": ("1=bhb 2=bhi 3=bli 4=ali 5=del 6=vss 7=ahi 8=dis "
                        "9=ahb 10=aho 11=ahs 12=vdd 13=alo 14=blo 15=bhs "
                        "16=bho")}
# Transistor_FET:IRF540N numbers its pins 1=G 2=D 3=S, which is the TO-220
# pinout and NOT the D-G-S order a VDMOS card is written in. Get this mapping
# backwards and the bridge still simulates -- as four transistors wired gate to
# drain, conducting nothing.
SIM_FET = {"Sim.Device": "NMOS", "Sim.Type": "VDMOS", "Sim.Library": VDMOS,
           "Sim.Name": "IRF540N", "Sim.Pins": "1=G 2=D 3=S"}
SIM_DIO = {"Sim.Device": "D", "Sim.Library": MODELS, "Sim.Name": "DSCH",
           "Sim.Pins": "1=K 2=A"}


def src(kind, params):
    """Sim fields for a voltage source. All four are required on the instance:
    with Sim.Params alone KiCad emits the raw parameters instead of PULSE(...)."""
    return {"Sim.Device": "V", "Sim.Type": kind, "Sim.Pins": "1=+ 2=-",
            "Sim.Params": params}


# --------------------------------------------------------------------- sheet
def new_sheet(title, project, uuid, paper="A3"):
    sh = Sheet(paper=paper, title=title, project=project, version=10, uuid=uuid)
    sh.src._cache = SymCache(extra_dirs=[str(SIM / "lib")])
    return sh


# The analysis each sheet runs, and what to plot. One source of truth: the
# text drawn on the sheet, the .wbk workbook KiCad opens the simulator with,
# and run_sims.py all read this.
PALETTE = ["rgb(228, 26, 28)", "rgb(55, 126, 184)", "rgb(77, 175, 74)",
           "rgb(152, 78, 163)", "rgb(255, 127, 0)"]
WORKBOOK = {
    "sim_a_vground": (".tran 1m 3", ["V(/VGND)", "V(/VG)"]),
    "sim_b_triangle": (".tran 20n 200u uic", ["V(/TRI)", "V(/SQ)"]),
    "sim_c_input": (".tran 10u 5m", ["V(/AUDIO_P)", "V(/AUDIO_N)"]),
    "sim_d_pwm": (".tran 50n 1m", ["V(/PWM_A)", "V(/PWM_B)", "V(/TRI)"]),
    "sim_e_driver": (".tran 5n 150u uic",
                     ["V(/G_AH)", "V(/G_AL)", "V(/A_HI)"]),
    "sim_f_bridge": (".tran 20n 300u uic",
                     ["V(/OUT_P)", "V(/OUT_N)", "V(/SW_A)"]),
    "sim_g_chain": (".tran 20n 1.4m uic",
                    ["V(/OUT_P)", "V(/OUT_N)", "V(/AUDIO_P)", "V(/TRI)"]),
}


def write_workbook(path: Path, name: str):
    """The .wbk KiCad reads when the simulator opens, so Run just works."""
    cmd, signals = WORKBOOK[name]
    wb = {
        "last_sch_text_sim_command": cmd,
        "tabs": [{
            "analysis": "TRAN",
            "commands": [cmd, ".kicad adjustpaths", ".save all",
                         ".probe alli", ".probe allp"],
            "dottedSecondary": True,
            "margins": {"bottom": 45, "left": 70, "right": 70, "top": 30},
            "measurements": [],
            "showGrid": True,
            "traces": [{"color": PALETTE[i % len(PALETTE)], "signal": s,
                        "trace_type": 257}
                       for i, s in enumerate(signals)],
        }],
        "user_defined_signals": [],
        "version": 6,
    }
    path.write_text(json.dumps(wb, indent=2) + "\n", encoding="utf-8")


def write_project(path: Path, uuid: str, name: str):
    pro = json.loads(TEMPLATE_PRO.read_text(encoding="utf-8"))
    # KiCad 10 applies the netclass wire width to every wire; a missing key
    # resolves to zero and the whole sheet renders as invisible hairlines with
    # no junction dots, while ERC and the netlist stay perfectly correct.
    for cls in pro.get("net_settings", {}).get("classes", []):
        cls.setdefault("wire_width", 6.0)
        cls.setdefault("bus_width", 12.0)
        cls.setdefault("line_style", 0)
    pro["meta"]["filename"] = f"{name}.kicad_pro"
    pro["schematic"]["top_level_sheets"] = [
        {"filename": f"{name}.kicad_sch", "name": name, "uuid": uuid}]
    pro["sheets"] = [[uuid, name]]
    pro["pcbnew"]["last_paths"]["plot"] = ""
    path.write_text(json.dumps(pro, indent=2) + "\n", encoding="utf-8")


def write_sym_lib_table(path: Path):
    """Register the vendored simulation symbols with the project.

    Without this the sheets still load and still simulate -- the symbol
    definition is embedded in the .kicad_sch -- but ERC reports
    lib_symbol_issues for every CD4049_SIM and the library browser cannot
    find the part. One table serves all seven benches, because they share a
    directory and KiCad reads sym-lib-table from the project directory.
    """
    path.write_text(
        '(sym_lib_table\n'
        '  (version 7)\n'
        '  (lib (name "classd_sim")(type "KiCad")'
        '(uri "${KIPRJMOD}/lib/classd_sim.kicad_sym")(options "")'
        '(descr "Simulation-only symbols for the Class D testbenches"))\n'
        ')\n', encoding="utf-8")


def set_sim(path: Path, fields: dict):
    """Write Sim.* properties onto the placed symbols.

    schdraw emits Reference/Value/Footprint/Datasheet only, so anything the
    simulator needs has to be added here. Properties go immediately before the
    symbol's (instances ...) block, which is where KiCad writes its own.
    """
    txt = path.read_text(encoding="utf-8")
    for ref, props in fields.items():
        i = txt.index(f'(property "Reference" "{ref}"')
        j = txt.index("\t\t(instances", i)
        block = "".join(
            f'\t\t(property "{k}" "{v}"\n'
            f'\t\t\t(at 0 0 0)\n\t\t\t(hide yes)\n\t\t\t(show_name no)\n'
            f'\t\t\t(do_not_autoplace no)\n\t\t\t(effects\n\t\t\t\t(font\n'
            f'\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n'
            for k, v in props.items())
        txt = txt[:j] + block + txt[j:]
    path.write_text(txt, encoding="utf-8")


def back_link(sh, y=G(88)):
    """A hyperlink back to the board schematic.

    KiCad rejects an href that is a bare relative path or a ${KIPRJMOD}
    variable, but accepts a relative path carrying the file: scheme, which
    keeps the link working wherever the repository is checked out.
    """
    text = "<-  back to the board schematic   classd.kicad_pro"
    sh.note((G(10), y), text, size=1.6)
    return {text: "file:../classd.kicad_pro"}


def add_hrefs(path, links):
    """Attach hyperlinks to chosen text items (href lives inside (effects ...))."""
    txt = path.read_text(encoding="utf-8")
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
    path.write_text(txt, encoding="utf-8")


# ===========================================================================
# Blocks shared between sheets.
#
# E, F and G all carry the same gate driver, and F and G the same bridge and
# filter. Drawing each of them once and translating it means the three sheets
# agree with each other by construction -- and, more to the point, that they
# agree with the board, because the geometry below is lifted from the matching
# block of tools/classd_layout.py. A bootstrap that is wired one way on the
# board and another way in its own testbench proves nothing.
# ===========================================================================
def driver_block(sh, sim, x, y):
    """HIP4082 with its dead-time resistor, DIS pull-down and two bootstraps.

    (x, y) is the driver symbol's origin; every other part is placed relative
    to it, exactly as block E2 of the board places them around U6.
    """
    U6 = sh.place(DRV, "U6", at=(G(x), G(y)), value="HIP4082IPZ")
    sim["U6"] = dict(SIM_DRV)

    for pin, name in (("AHI", "A_HI"), ("ALI", "A_LO"),
                      ("BHI", "B_HI"), ("BLI", "B_LO")):
        p = U6.pin(pin)
        sh.seg((G(x - 30), p.y), p)
        sh.label((G(x - 30), p.y), name)

    R12 = sh.place(R, "R12", at=(G(x - 18), G(y + 14)), value="3k3")
    sh.seg(U6.pin("DEL"), (G(x - 18), G(y + 8)))
    sh.seg((G(x - 18), G(y + 8)), R12.pin("1"))
    sh.gnd(R12.pin("2"), drop=G(4))

    R13 = sh.place(R, "R13", at=(G(x - 34), G(y + 11)), value="10k")
    sh.seg(U6.pin("DIS"), (G(x - 34), G(y - 8)))
    sh.seg((G(x - 34), G(y - 8)), R13.pin("1"))
    sh.gnd(R13.pin("2"), drop=G(4))

    sh.seg(U6.pin("VSS"), (G(x), G(y + 18)))
    sh.gnd((G(x), G(y + 18)), drop=G(4))

    sh.seg(U6.pin("VDD"), (G(x), G(y - 28)))
    sh.seg((G(x - 20), G(y - 28)), (G(x + 52), G(y - 28)))
    sh.rail((G(x + 8), G(y - 28)), net="+12V", rise=G(4))
    C11 = sh.place(C, "C11", at=(G(x - 20), G(y - 22)), value="100n")
    sh.seg((G(x - 20), G(y - 28)), C11.pin("1"))
    sh.gnd(C11.pin("2"), drop=G(4))

    D3 = sh.place(DIO, "D3", at=(G(x + 40), G(y - 22)), rot=90, value="1N5817")
    D2 = sh.place(DIO, "D2", at=(G(x + 52), G(y - 22)), rot=90, value="1N5817")
    sim["D3"] = dict(SIM_DIO)
    sim["D2"] = dict(SIM_DIO)
    sh.seg((G(x + 40), G(y - 28)), D3.pin("A"))
    sh.seg((G(x + 52), G(y - 28)), D2.pin("A"))

    C6 = sh.place(C, "C6", at=(G(x + 40), G(y - 4)), value="100n")
    sh.seg(U6.pin("BHB"), (G(x + 40), G(y - 8)))
    sh.seg((G(x + 40), G(y - 8)), D3.pin("K"))
    sh.seg((G(x + 40), G(y - 8)), C6.pin("1"))
    sh.seg(C6.pin("2"), (G(x + 40), G(y)))
    sh.seg(U6.pin("BHS"), (G(x + 40), G(y)))
    sh.label((G(x + 28), G(y)), "SW_B")

    C5 = sh.place(C, "C5", at=(G(x + 64), G(y)), value="100n")
    sh.seg(U6.pin("AHB"), (G(x + 14), G(y - 6)))
    sh.seg((G(x + 14), G(y - 6)), (G(x + 14), G(y - 10)))
    sh.seg((G(x + 14), G(y - 10)), (G(x + 64), G(y - 10)))
    sh.seg((G(x + 52), G(y - 10)), D2.pin("K"))
    sh.seg((G(x + 64), G(y - 10)), C5.pin("1"))
    sh.seg(C5.pin("2"), (G(x + 64), G(y + 8)))
    sh.seg(U6.pin("AHS"), (G(x + 76), G(y + 8)))
    sh.label((G(x + 76), G(y + 8)), "SW_A")

    for pin, name in (("BHO", "G_BH"), ("BLO", "G_BL"),
                      ("ALO", "G_AL"), ("AHO", "G_AH")):
        p = U6.pin(pin)
        sh.seg(p, (G(x + 26), p.y))
        sh.label((G(x + 26), p.y), name)
    return U6


def inverters_block(sh, sim, x, y, feeds=None):
    """The four CD4049 sections that make the complements.

    Two inversions per channel, as the board does it: the driver's low input
    takes /PWM and its high input takes PWM again, so both see a CMOS edge
    rather than one of them seeing the comparator's slow RC pull-up.

    `feeds` wires the inputs to a point instead of hanging a label on them;
    on bench E the stimulus sources sit right there, so a wire says it better.
    """
    for tag, yy, (r1, r2) in (("A", y, ("U20", "U21")),
                              ("B", y + 28, ("U22", "U23"))):
        U1 = sh.place(INV, r1, at=(G(x), G(yy)), value="CD4049UBE")
        U2 = sh.place(INV, r2, at=(G(x + 24), G(yy)), value="CD4049UBE")
        sim[r1] = dict(SIM_INV)
        sim[r2] = dict(SIM_INV)
        if feeds:
            sh.seg(feeds[tag], U1.pin("IN"))
        else:
            sh.seg((G(x - 16), G(yy)), U1.pin("IN"))
            sh.label((G(x - 16), G(yy)), f"PWM_{tag}")
        sh.seg(U1.pin("OUT"), U2.pin("IN"))
        sh.label((G(x + 12), G(yy)), f"{tag}_LO")
        sh.seg(U2.pin("OUT"), (G(x + 44), G(yy)))
        sh.label((G(x + 44), G(yy)), f"{tag}_HI")
        sh.seg(U1.pin("VCC"), U2.pin("VCC"))
        sh.rail((G(x + 12), G(yy - 6)), net="+12V", rise=G(4))
        sh.seg(U1.pin("VSS"), U2.pin("VSS"))
        sh.gnd((G(x + 12), G(yy + 6)), drop=G(4))


def bridge_block(sh, sim, x0, y0):
    """Four IRF540N in a full bridge, with the bulk cap across the rails.

    x0 is the left leg's gate-resistor column and y0 the +12 V rail; the
    spacing is block F of the board, so the two drawings read the same.
    """
    top, bot = G(y0), G(y0 + 46)
    sh.seg((G(x0 + 16), top), (G(x0 + 78), top))
    sh.seg((G(x0 + 6), bot), (G(x0 + 78), bot))
    sh.rail((G(x0 + 30), top), net="+12V", rise=G(4))
    sh.gnd((G(x0 + 30), bot), drop=G(4))

    C4 = sh.place(CP, "C4", at=(G(x0 + 78), G(y0 + 23)), value="2200u")
    sh.seg((G(x0 + 78), top), C4.pin("1"))
    sh.seg(C4.pin("2"), (G(x0 + 78), bot))

    for dx, xg, qs, rgs, rps, lbl in ((14, x0, ("Q1", "Q2"), ("R14", "R15"),
                                       ("R18", "R19"), "SW_A"),
                                      (54, x0 + 40, ("Q3", "Q4"),
                                       ("R16", "R17"), ("R20", "R21"),
                                       "SW_B")):
        Qh = sh.place(FET, qs[0], at=(G(x0 + dx), G(y0 + 12)), value="IRF540N")
        Ql = sh.place(FET, qs[1], at=(G(x0 + dx), G(y0 + 32)), value="IRF540N")
        sim[qs[0]] = dict(SIM_FET)
        sim[qs[1]] = dict(SIM_FET)
        xs = Qh.pin("D").x
        sh.seg(Qh.pin("D"), (xs, top))
        sh.seg(Qh.pin("S"), Ql.pin("D"))
        sh.seg(Ql.pin("S"), (xs, bot))

        for ref, yy, name in ((rgs[0], y0 + 12, f"G_{lbl[-1]}H"),
                              (rgs[1], y0 + 32, f"G_{lbl[-1]}L")):
            Rg = sh.place(R, ref, at=(G(xg), G(yy)), rot=90, value="22R1")
            sh.seg((G(xg - 8), G(yy)), Rg.pin("1"))
            sh.label((G(xg - 8), G(yy)), name)
            sh.seg(Rg.pin("2"),
                   (Qh if yy == y0 + 12 else Ql).pin("G"))

        Ph = sh.place(R, rps[0], at=(G(xg + 6), G(y0 + 20)), value="10k")
        sh.seg((G(xg + 6), G(y0 + 12)), Ph.pin("1"))
        sh.seg(Ph.pin("2"), (xs, G(y0 + 23)))      # high side: gate to source
        Pl = sh.place(R, rps[1], at=(G(xg + 6), G(y0 + 40)), value="10k")
        sh.seg((G(xg + 6), G(y0 + 32)), Pl.pin("1"))
        sh.seg(Pl.pin("2"), (G(xg + 6), bot))      # low side: gate to 0 V

        sh.seg((xs, G(y0 + 20)), (xs + G(10), G(y0 + 20)))
        sh.label((xs + G(10), G(y0 + 20)), lbl)


def filter_block(sh, sim, x0, y0):
    """Both LC arms, the differential cap, the Zobel and a 4 ohm load."""
    L1 = sh.place(L, "L1", at=(G(x0 + 8), G(y0)), rot=90, value="15u")
    L2 = sh.place(L, "L2", at=(G(x0 + 8), G(y0 + 20)), rot=90, value="15u")
    sh.seg((G(x0), G(y0)), L1.pin("1"))
    sh.label((G(x0), G(y0)), "SW_A")
    sh.seg((G(x0), G(y0 + 20)), L2.pin("1"))
    sh.label((G(x0), G(y0 + 20)), "SW_B")
    sh.seg(L1.pin("2"), (G(x0 + 42), G(y0)))
    sh.seg(L2.pin("2"), (G(x0 + 42), G(y0 + 20)))

    C13 = sh.place(C, "C13", at=(G(x0 + 20), G(y0 + 10)), value="820n")
    sh.seg((G(x0 + 20), G(y0)), C13.pin("1"))
    sh.seg(C13.pin("2"), (G(x0 + 20), G(y0 + 20)))

    R22 = sh.place(R, "R22", at=(G(x0 + 30), G(y0 + 6)), value="10R")
    C14 = sh.place(C, "C14", at=(G(x0 + 30), G(y0 + 14)), value="100n")
    sh.seg((G(x0 + 30), G(y0)), R22.pin("1"))
    sh.seg(R22.pin("2"), C14.pin("1"))
    sh.seg(C14.pin("2"), (G(x0 + 30), G(y0 + 20)))

    RL = sh.place(R, "R1", at=(G(x0 + 42), G(y0 + 10)), value="4")
    sh.seg((G(x0 + 42), G(y0)), RL.pin("1"))
    sh.seg(RL.pin("2"), (G(x0 + 42), G(y0 + 20)))
    sh.label((G(x0 + 38), G(y0)), "OUT_P")
    sh.label((G(x0 + 38), G(y0 + 20)), "OUT_N")


def gnd_pair(sh, u, y):
    """An LM311's V- and GND pins onto one return rail with one symbol.

    The two pins are 2.54 mm apart, so a ground symbol hung off each of them
    lands on top of the other. House style wants a shared rail here anyway.
    """
    a, b = u.pin("V-"), u.pin("GND")
    sh.seg(a, (a.x, y))
    sh.seg(b, (b.x, y))
    sh.seg((a.x, y), (b.x, y))
    sh.gnd(((a.x + b.x) / 2, y))


def supply(sh, sim, x, y, volts="12"):
    """The 12 V bench supply, with the two PWR_FLAGs ERC insists on."""
    V1 = sh.place(VDC, "V1", at=(G(x), G(y)), value=volts)
    sim["V1"] = src("DC", f"dc={volts}")
    sh.rail(V1.pin("1"), net="+12V", rise=G(4))
    sh.gnd(V1.pin("2"), drop=G(4))
    sh.seg(V1.pin("1"), (G(x + 8), V1.pin("1").y))
    sh.power("power:PWR_FLAG", (G(x + 8), V1.pin("1").y))
    sh.seg(V1.pin("2"), (G(x + 8), V1.pin("2").y))
    sh.power("power:PWR_FLAG", (G(x + 8), V1.pin("2").y))
    return V1


BENCHES = []


def bench(name, title, uuid, paper="A3"):
    def deco(fn):
        BENCHES.append((name, title, uuid, paper, fn))
        return fn
    return deco


# ===========================================================================
# A  rails and the 6 V virtual ground
# ===========================================================================
@bench("sim_a_vground", "A - rails and the 6 V virtual ground",
       "a1000000-0000-4000-8000-000000000001")
def build_a(sh):
    sh.note((G(10), G(10)), "A  Rails and the 6 V virtual ground", size=2)
    sim = {}

    V1 = sh.place(VPULSE, "V1", at=(G(14), G(30)), value="")
    sim["V1"] = src("PULSE", "y1=0 y2=12 td=0 tr=1m tf=1m tw=10 per=20")
    sh.rail(V1.pin("1"), net="+12V", rise=G(4))
    sh.gnd(V1.pin("2"), drop=G(4))
    sh.seg(V1.pin("1"), (G(22), V1.pin("1").y))
    sh.power("power:PWR_FLAG", (G(22), V1.pin("1").y))
    sh.seg(V1.pin("2"), (G(22), V1.pin("2").y))
    sh.power("power:PWR_FLAG", (G(22), V1.pin("2").y))

    R1 = sh.place(R, "R1", at=(G(36), G(24)), value="10k")
    R2 = sh.place(R, "R2", at=(G(36), G(38)), value="10k")
    C1 = sh.place(CP, "C1", at=(G(48), G(38)), value="100u")
    sh.rail(R1.pin("1"), net="+12V", rise=G(4))
    sh.seg(R1.pin("2"), R2.pin("1"))
    sh.seg((G(36), G(31)), (G(58), G(31)))
    sh.seg((G(48), G(31)), C1.pin("1"))
    sh.gnd(R2.pin("2"), drop=G(4))
    sh.gnd(C1.pin("2"), drop=G(4))
    sh.label((G(54), G(31)), "VG")

    U1 = sh.place(OPA, "U1", at=(G(64), G(33)), value="TL074")
    sim["U1"] = dict(SIM_OPAMP)
    sh.seg((G(58), G(31)), U1.pin("+"))
    sh.seg(U1.pin("out"), (G(84), G(33)))
    sh.seg((G(78), G(33)), (G(78), G(42)))
    sh.seg((G(78), G(42)), (G(58), G(42)))
    sh.seg((G(58), G(42)), U1.pin("-"))
    sh.rail(U1.pin("V+"), net="+12V", rise=G(4))
    sh.gnd(U1.pin("V-"), drop=G(4))
    sh.label((G(84), G(33)), "VGND")

    R3 = sh.place(R, "R3", at=(G(92), G(40)), value="10k")
    sh.seg((G(84), G(33)), (G(92), G(33)))
    sh.seg((G(92), G(33)), R3.pin("1"))
    sh.gnd(R3.pin("2"), drop=G(4))

    sh.note((G(10), G(56)),
            "V1 ramps up in 1 ms like a bench supply being switched on. The "
            "divider is R1||R2 = 5k into C1 = 100u, so VGND then takes about "
            "2.5 s to settle -- that is why the run is 3 s long.", size=1.27)
    sh.note((G(10), G(62)), WORKBOOK["sim_a_vground"][0], size=1.6)
    return sim


# ===========================================================================
# B  triangle oscillator
# ===========================================================================
@bench("sim_b_triangle", "B - triangle carrier, ~250 kHz",
       "a1000000-0000-4000-8000-000000000002")
def build_b(sh):
    sh.note((G(10), G(10)), "B  Triangle carrier  (LM311 Schmitt + TL074 "
                            "integrator)", size=2)
    sim = {}

    V1 = sh.place(VDC, "V1", at=(G(14), G(26)), value="12")
    sim["V1"] = src("DC", "dc=12")
    sh.rail(V1.pin("1"), net="+12V", rise=G(4))
    sh.gnd(V1.pin("2"), drop=G(4))
    sh.seg(V1.pin("1"), (G(22), V1.pin("1").y))
    sh.power("power:PWR_FLAG", (G(22), V1.pin("1").y))
    sh.seg(V1.pin("2"), (G(22), V1.pin("2").y))
    sh.power("power:PWR_FLAG", (G(22), V1.pin("2").y))

    V2 = sh.place(VDC, "V2", at=(G(14), G(46)), value="6")
    sim["V2"] = src("DC", "dc=6")
    sh.seg(V2.pin("1"), (G(14), G(38)))
    sh.label((G(14), G(38)), "VGND")
    sh.gnd(V2.pin("2"), drop=G(4))

    # integrator: SQ -> R4 -> summing node, C12 across the amp
    R4 = sh.place(R, "R4", at=(G(38), G(31)), rot=90, value="5k6")
    U1 = sh.place(OPA, "U1", at=(G(56), G(29)), value="TL074")
    sim["U1"] = dict(SIM_OPAMP)
    C12 = sh.place(C, "C12", at=(G(58), G(42)), rot=90, value="470p")
    sh.seg(R4.pin("2"), U1.pin("-"))
    sh.seg(U1.pin("-"), (G(50), G(42)))
    sh.seg((G(50), G(42)), C12.pin("1"))
    R5 = sh.place(R, "R5", at=(G(80), G(29)), rot=90, value="10k")
    sh.seg(U1.pin("out"), R5.pin("1"))   # route TO the pin, never near it
    sh.seg((G(66), G(29)), (G(66), G(42)))
    sh.seg(C12.pin("2"), (G(66), G(42)))
    sh.seg(U1.pin("+"), (G(44), G(27)))
    sh.label((G(44), G(27)), "VGND")
    sh.rail(U1.pin("V+"), net="+12V", rise=G(4))
    sh.gnd(U1.pin("V-"), drop=G(4))
    sh.label((G(72), G(29)), "TRI")

    # Schmitt trigger: R5 from TRI and R6 from SQ meet at the + input
    U2 = sh.place(CMP, "U2", at=(G(100), G(31)), value="LM311")
    sim["U2"] = dict(SIM_LM311)
    sh.seg(R5.pin("2"), U2.pin("+"))
    R6 = sh.place(R, "R6", at=(G(88), G(48)), value="27k4")
    sh.seg(R6.pin("1"), (G(88), G(29)))
    sh.seg(U2.pin("-"), (G(90), G(33)))
    sh.seg((G(90), G(33)), (G(90), G(40)))
    sh.label((G(90), G(40)), "VGND")
    sh.rail(U2.pin("V+"), net="+12V", rise=G(4))
    gnd_pair(sh, U2, G(41))
    sh.nc(U2.pin("BAL"))
    sh.nc(U2.pin("STRB"))

    R7 = sh.place(R, "R7", at=(G(114), G(24)), value="1k")
    sh.rail(R7.pin("1"), net="+12V", rise=G(4))
    sh.seg(R7.pin("2"), (G(114), G(31)))
    sh.seg(U2.pin("out"), (G(122), G(31)))
    sh.seg((G(122), G(31)), (G(122), G(58)))
    sh.seg((G(122), G(58)), (G(32), G(58)))
    sh.seg((G(32), G(58)), (G(32), G(31)))
    sh.seg((G(32), G(31)), R4.pin("1"))
    sh.seg(R6.pin("2"), (G(88), G(58)))
    sh.label((G(70), G(58)), "SQ")

    sh.note((G(10), G(64)),
            "R5/R6 set a +/-2 V window about 6 V; R4 and C12 set the ramp. "
            "Expect ~250 kHz and ~4 Vpp on TRI.", size=1.27)
    sh.note((G(10), G(70)), WORKBOOK["sim_b_triangle"][0], size=1.6)
    return sim


# ===========================================================================
# C  input stage
# ===========================================================================
@bench("sim_c_input", "C - input stage, buffer and unity inverter",
       "a1000000-0000-4000-8000-000000000003")
def build_c(sh):
    sh.note((G(10), G(10)), "C  Input stage  (level -> buffer -> inverter)",
            size=2)
    sim = {}

    V1 = sh.place(VDC, "V1", at=(G(14), G(26)), value="12")
    sim["V1"] = src("DC", "dc=12")
    sh.rail(V1.pin("1"), net="+12V", rise=G(4))
    sh.gnd(V1.pin("2"), drop=G(4))
    sh.seg(V1.pin("1"), (G(22), V1.pin("1").y))
    sh.power("power:PWR_FLAG", (G(22), V1.pin("1").y))
    sh.seg(V1.pin("2"), (G(22), V1.pin("2").y))
    sh.power("power:PWR_FLAG", (G(22), V1.pin("2").y))

    V2 = sh.place(VDC, "V2", at=(G(14), G(46)), value="6")
    sim["V2"] = src("DC", "dc=6")
    sh.seg(V2.pin("1"), (G(14), G(38)))
    sh.label((G(14), G(38)), "VGND")
    sh.gnd(V2.pin("2"), drop=G(4))

    # 1 kHz, 1.4 V peak ~ 1 Vrms line level
    V3 = sh.place(VSIN, "V3", at=(G(30), G(46)), value="")
    sim["V3"] = src("SIN", "dc=0 ampl=1.4 f=1k ac=1")
    sh.gnd(V3.pin("2"), drop=G(4))
    C3 = sh.place(C, "C3", at=(G(38), G(34)), rot=90, value="1u5")
    sh.seg(V3.pin("1"), (G(30), G(34)))
    sh.seg((G(30), G(34)), C3.pin("1"))

    # the level pot, at half rotation
    R3 = sh.place(R, "R3", at=(G(48), G(40)), value="5k")
    R4 = sh.place(R, "R4", at=(G(48), G(52)), value="5k")
    sh.seg(C3.pin("2"), (G(48), G(34)))
    sh.seg((G(48), G(34)), R3.pin("1"))
    sh.seg(R3.pin("2"), R4.pin("1"))
    sh.seg(R4.pin("2"), (G(48), G(60)))
    sh.label((G(48), G(60)), "VGND")
    sh.seg((G(48), G(46)), (G(60), G(46)))
    sh.label((G(56), G(46)), "WIPER")

    U1 = sh.place(OPA, "U1", at=(G(66), G(48)), value="TL074")
    sim["U1"] = dict(SIM_OPAMP)
    sh.seg((G(60), G(46)), U1.pin("+"))
    sh.seg(U1.pin("out"), (G(88), G(48)))
    sh.seg((G(80), G(48)), (G(80), G(64)))
    sh.seg((G(80), G(64)), (G(60), G(64)))
    sh.seg((G(60), G(64)), U1.pin("-"))
    sh.rail(U1.pin("V+"), net="+12V", rise=G(4))
    sh.gnd(U1.pin("V-"), drop=G(4))
    sh.label((G(86), G(48)), "AUDIO_P")

    # unity inverter about the virtual ground
    R8 = sh.place(R, "R8", at=(G(98), G(48)), rot=90, value="10k")
    U2 = sh.place(OPA, "U2", at=(G(116), G(46)), value="TL074")
    sim["U2"] = dict(SIM_OPAMP)
    R9 = sh.place(R, "R9", at=(G(116), G(60)), rot=90, value="10k")
    sh.seg((G(88), G(48)), R8.pin("1"))
    sh.seg(R8.pin("2"), U2.pin("-"))
    sh.seg(U2.pin("-"), (G(110), G(60)))
    sh.seg((G(110), G(60)), R9.pin("1"))
    sh.seg(R9.pin("2"), (G(126), G(60)))
    sh.seg((G(126), G(60)), (G(126), G(46)))
    sh.seg(U2.pin("out"), (G(136), G(46)))
    sh.seg(U2.pin("+"), (G(104), G(44)))
    sh.label((G(104), G(44)), "VGND")
    sh.rail(U2.pin("V+"), net="+12V", rise=G(4))
    sh.gnd(U2.pin("V-"), drop=G(2))
    sh.label((G(136), G(46)), "AUDIO_N")

    sh.note((G(10), G(68)),
            "AUDIO_P and AUDIO_N must be equal and opposite about 6 V. Watch "
            "AUDIO_P against 4 V: that is the TL074 input common-mode floor.",
            size=1.27)
    sh.note((G(10), G(74)), WORKBOOK["sim_c_input"][0], size=1.6)
    return sim


# ===========================================================================
# D  PWM comparators
# ===========================================================================
@bench("sim_d_pwm", "D - PWM comparators, audio against the triangle",
       "a1000000-0000-4000-8000-000000000004")
def build_d(sh):
    sh.note((G(10), G(10)), "D  PWM comparators  (audio vs triangle)", size=2)
    sim = {}

    V1 = sh.place(VDC, "V1", at=(G(14), G(26)), value="12")
    sim["V1"] = src("DC", "dc=12")
    sh.rail(V1.pin("1"), net="+12V", rise=G(4))
    sh.gnd(V1.pin("2"), drop=G(4))
    sh.seg(V1.pin("1"), (G(22), V1.pin("1").y))
    sh.power("power:PWR_FLAG", (G(22), V1.pin("1").y))
    sh.seg(V1.pin("2"), (G(22), V1.pin("2").y))
    sh.power("power:PWR_FLAG", (G(22), V1.pin("2").y))

    # triangle: a pulse source with equal rise and fall and no flat top
    V2 = sh.place(VPULSE, "V2", at=(G(14), G(46)), value="")
    sim["V2"] = src("PULSE", "y1=4 y2=8 td=0 tr=2u tf=2u tw=1n per=4u")
    sh.seg(V2.pin("1"), (G(14), G(38)))
    sh.label((G(14), G(38)), "TRI")
    sh.gnd(V2.pin("2"), drop=G(4))

    # differential audio about 6 V
    V3 = sh.place(VSIN, "V3", at=(G(32), G(46)), value="")
    sim["V3"] = src("SIN", "dc=6 ampl=1.5 f=1k")
    sh.seg(V3.pin("1"), (G(32), G(38)))
    sh.label((G(32), G(38)), "AUDIO_P")
    sh.gnd(V3.pin("2"), drop=G(4))

    V4 = sh.place(VSIN, "V4", at=(G(50), G(46)), value="")
    sim["V4"] = src("SIN", "dc=6 ampl=-1.5 f=1k")
    sh.seg(V4.pin("1"), (G(50), G(38)))
    sh.label((G(50), G(38)), "AUDIO_N")
    sh.gnd(V4.pin("2"), drop=G(4))

    for tag, ref, y, aud in (("A", "U1", G(28), "AUDIO_P"),
                             ("B", "U2", G(60), "AUDIO_N")):
        U = sh.place(CMP, ref, at=(G(84), y), value="LM311")
        sim[ref] = dict(SIM_LM311)
        sh.seg((G(68), y - G(2)), U.pin("+"))
        sh.label((G(68), y - G(2)), aud)
        sh.seg((G(68), y + G(2)), U.pin("-"))
        sh.label((G(68), y + G(2)), "TRI")
        sh.rail(U.pin("V+"), net="+12V", rise=G(4))
        gnd_pair(sh, U, y + G(10))
        sh.nc(U.pin("BAL"))
        sh.nc(U.pin("STRB"))
        rp = sh.place(R, f"R{1 if tag == 'A' else 2}0", at=(G(98), y - G(7)),
                      value="1k")
        sh.rail(rp.pin("1"), net="+12V", rise=G(4))
        sh.seg(rp.pin("2"), (G(98), y))
        sh.seg(U.pin("out"), (G(112), y))
        sh.label((G(112), y), f"PWM_{tag}")

    sh.note((G(10), G(72)),
            "Duty on PWM_A should track the audio and PWM_B should mirror it. "
            "The two must stay complementary for the bridge to swing.",
            size=1.27)
    sh.note((G(10), G(78)), WORKBOOK["sim_d_pwm"][0], size=1.6)
    return sim


# ===========================================================================
# E  complement generation and gate driver
# ===========================================================================
@bench("sim_e_driver", "E - complement generation and gate driver",
       "a1000000-0000-4000-8000-000000000005")
def build_e(sh):
    sh.note((G(10), G(10)), "E  Complement generation and gate driver", size=2)
    sim = {}
    supply(sh, sim, 14, 20)

    # PWM_A / PWM_B: a complementary pair at the design carrier frequency,
    # wired straight into the two inverter chains that sit beside them.
    V2 = sh.place(VPULSE, "V2", at=(G(14), G(48)), value="")
    sim["V2"] = src("PULSE", "y1=0 y2=12 td=0 tr=20n tf=20n tw=2.4u per=4u")
    sh.gnd(V2.pin("2"), drop=G(4))
    V3 = sh.place(VPULSE, "V3", at=(G(14), G(76)), value="")
    sim["V3"] = src("PULSE", "y1=12 y2=0 td=0 tr=20n tf=20n tw=2.4u per=4u")
    sh.gnd(V3.pin("2"), drop=G(4))

    sh.note((G(44), G(26)), "E1  complement generation  (CD4049)", size=1.6)
    inverters_block(sh, sim, 44, 44,
                    feeds={"A": V2.pin("1"), "B": V3.pin("1")})

    sh.note((G(10), G(88)), "E2  gate driver  HIP4082IPZ", size=1.6)
    driver_block(sh, sim, 60, 124)

    # Each output drives the load it will really drive: the board's 22R1 into
    # roughly one IRF540N gate. The high-side caps return to the switch node,
    # because that is what a high-side gate is actually referenced to, and the
    # hold-down resistor sits on the same wire rather than on a second label.
    sh.note((G(150), G(88)), "gate loads  (22R1 into one IRF540N gate)",
            size=1.6)
    for ref, cref, yy, hold in (("R14", "C20", 100, ("R23", "SW_A")),
                                ("R15", "C21", 130, None),
                                ("R16", "C22", 156, ("R24", "SW_B")),
                                ("R17", "C23", 186, None)):
        name = {"R14": "G_AH", "R15": "G_AL",
                "R16": "G_BH", "R17": "G_BL"}[ref]
        Rg = sh.place(R, ref, at=(G(158), G(yy)), rot=90, value="22R1")
        sh.seg((G(150), G(yy)), Rg.pin("1"))
        sh.label((G(150), G(yy)), name)
        sh.seg(Rg.pin("2"), (G(170), G(yy)))
        Cg = sh.place(C, cref, at=(G(170), G(yy + 6)), value="1n5")
        sh.seg((G(170), G(yy)), Cg.pin("1"))
        if hold:
            href, net = hold
            Rs = sh.place(R, href, at=(G(170), G(yy + 16)), value="100R")
            sh.seg(Cg.pin("2"), Rs.pin("1"))
            sh.label((G(170), G(yy + 11)), net)
            sh.gnd(Rs.pin("2"), drop=G(4))
        else:
            sh.gnd(Cg.pin("2"), drop=G(4))

    sh.note((G(10), G(176)),
            "R23/R24 hold SW_A and SW_B near 0 V, standing in for the "
            "low-side FET being on. Leave them out and the switch nodes float "
            "up through the driver's own leakage until the bootstrap caps have "
            "barely a volt across them -- the bridge itself is bench F.",
            size=1.27)
    sh.note((G(10), G(184)),
            "The bootstrap caps start empty and take ~50 us to reach 11.7 V, "
            "so read the dead time from the far end of the run, not the start.",
            size=1.27)
    sh.note((G(10), G(192)),
            "Expect ~200 ns with both driver outputs low at every commutation, "
            "and G_AH about a quarter of a volt short of G_AL: that is the "
            "Schottky drop the high side runs on.", size=1.27)
    sh.note((G(10), G(200)), WORKBOOK["sim_e_driver"][0], size=1.6)
    return sim


# ===========================================================================
# F  output bridge, LC filter and Zobel
# ===========================================================================
@bench("sim_f_bridge", "F - output bridge, LC filter and Zobel",
       "a1000000-0000-4000-8000-000000000006")
def build_f(sh):
    sh.note((G(10), G(10)), "F  Output bridge, LC filter and Zobel", size=2)
    sim = {}
    supply(sh, sim, 14, 20)

    # A steady duty rather than an audio-modulated one: this sheet asks how
    # much power reaches 4 ohm and how much carrier survives the filter, and a
    # fixed duty answers both in a fifth of the run time. 79 % against 21 % is
    # what full output asks for. The complements still go through the real
    # CD4049 chain, so the drive the bridge sees is the drive the board makes.
    V2 = sh.place(VPULSE, "V2", at=(G(14), G(48)), value="")
    sim["V2"] = src("PULSE", "y1=0 y2=12 td=0 tr=20n tf=20n tw=3.12u per=4u")
    sh.gnd(V2.pin("2"), drop=G(4))
    V3 = sh.place(VPULSE, "V3", at=(G(14), G(76)), value="")
    sim["V3"] = src("PULSE", "y1=0 y2=12 td=0 tr=20n tf=20n tw=800n per=4u")
    sh.gnd(V3.pin("2"), drop=G(4))

    sh.note((G(44), G(26)), "PWM in at a fixed 79 % / 21 % duty", size=1.6)
    inverters_block(sh, sim, 44, 44,
                    feeds={"A": V2.pin("1"), "B": V3.pin("1")})

    sh.note((G(10), G(88)), "gate driver and bootstrap", size=1.6)
    driver_block(sh, sim, 60, 124)
    sh.note((G(152), G(96)), "output bridge", size=1.6)
    bridge_block(sh, sim, 160, 104)
    sh.note((G(250), G(104)), "filter, Zobel and a 4 ohm load", size=1.6)
    filter_block(sh, sim, 250, 112)

    sh.note((G(10), G(166)),
            "Watch OUT_P - OUT_N. At this duty the design should hold about "
            "6.8 V across 4 ohm, which is ~11.7 W, with the carrier residue "
            "well under half a volt peak to peak.", size=1.27)
    sh.note((G(10), G(174)),
            "The bridge is real IRF540N cards, body diode included, so the "
            "dead-time commutation and its recovery spike are in the result.",
            size=1.27)
    sh.note((G(10), G(182)), WORKBOOK["sim_f_bridge"][0], size=1.6)
    return sim


# ===========================================================================
# G  the whole chain
# ===========================================================================
@bench("sim_g_chain", "G - the whole chain, audio in to speaker out",
       "a1000000-0000-4000-8000-000000000007", paper="A2")
def build_g(sh):
    sh.note((G(10), G(10)),
            "G  The whole chain  -  audio in to speaker out", size=2)
    sim = {}
    supply(sh, sim, 14, 26)

    V2 = sh.place(VDC, "V2", at=(G(14), G(50)), value="6")
    sim["V2"] = src("DC", "dc=6")
    sh.seg(V2.pin("1"), (G(14), G(42)))
    sh.label((G(14), G(42)), "VGND")
    sh.gnd(V2.pin("2"), drop=G(4))

    # ---- input stage ----------------------------------------------------
    sh.note((G(44), G(22)), "input: level -> buffer -> inverter", size=1.6)
    V3 = sh.place(VSIN, "V3", at=(G(30), G(50)), value="")
    sim["V3"] = src("SIN", "dc=6 ampl=2.5 f=1k")
    sh.seg(V3.pin("1"), (G(30), G(34)))
    sh.gnd(V3.pin("2"), drop=G(4))

    # the level pot, wound to 80 % -- see the note at the foot of the sheet
    R2 = sh.place(R, "R2", at=(G(48), G(40)), value="2k")
    R3 = sh.place(R, "R3", at=(G(48), G(52)), value="8k")
    sh.seg((G(30), G(34)), (G(48), G(34)))
    sh.seg((G(48), G(34)), R2.pin("1"))
    sh.seg(R2.pin("2"), R3.pin("1"))
    sh.seg(R3.pin("2"), (G(48), G(60)))
    sh.label((G(48), G(60)), "VGND")

    U1 = sh.place(OPA, "U1", at=(G(66), G(48)), value="TL074")
    sim["U1"] = dict(SIM_OPAMP)
    sh.seg((G(48), G(46)), U1.pin("+"))
    sh.label((G(54), G(46)), "WIPER")
    sh.seg(U1.pin("out"), (G(88), G(48)))
    sh.seg((G(80), G(48)), (G(80), G(64)))
    sh.seg((G(80), G(64)), (G(60), G(64)))
    sh.seg((G(60), G(64)), U1.pin("-"))
    sh.rail(U1.pin("V+"), net="+12V", rise=G(4))
    sh.gnd(U1.pin("V-"), drop=G(4))
    sh.label((G(86), G(48)), "AUDIO_P")

    R8 = sh.place(R, "R8", at=(G(98), G(48)), rot=90, value="10k")
    U2 = sh.place(OPA, "U2", at=(G(116), G(46)), value="TL074")
    sim["U2"] = dict(SIM_OPAMP)
    R9 = sh.place(R, "R9", at=(G(116), G(60)), rot=90, value="10k")
    sh.seg((G(88), G(48)), R8.pin("1"))
    sh.seg(R8.pin("2"), U2.pin("-"))
    sh.seg(U2.pin("-"), (G(110), G(60)))
    sh.seg((G(110), G(60)), R9.pin("1"))
    sh.seg(R9.pin("2"), (G(126), G(60)))
    sh.seg((G(126), G(60)), (G(126), G(46)))
    sh.seg(U2.pin("out"), (G(136), G(46)))
    sh.seg(U2.pin("+"), (G(104), G(44)))
    sh.label((G(104), G(44)), "VGND")
    sh.rail(U2.pin("V+"), net="+12V", rise=G(4))
    sh.gnd(U2.pin("V-"), drop=G(2))
    sh.label((G(136), G(46)), "AUDIO_N")

    # ---- PWM comparators ------------------------------------------------
    sh.note((G(170), G(14)), "PWM comparators", size=1.6)
    for tag, ref, yy, aud, rp in (("A", "U7", 28, "AUDIO_P", "R10"),
                                  ("B", "U8", 60, "AUDIO_N", "R11")):
        U = sh.place(CMP, ref, at=(G(204), G(yy)), value="LM311")
        sim[ref] = dict(SIM_LM311)
        sh.seg((G(188), G(yy - 2)), U.pin("+"))
        sh.label((G(188), G(yy - 2)), aud)
        sh.seg((G(188), G(yy + 2)), U.pin("-"))
        sh.label((G(188), G(yy + 2)), "TRI")
        sh.rail(U.pin("V+"), net="+12V", rise=G(4))
        gnd_pair(sh, U, G(yy + 10))
        sh.nc(U.pin("BAL"))
        sh.nc(U.pin("STRB"))
        Rp = sh.place(R, rp, at=(G(218), G(yy - 7)), value="1k")
        sh.rail(Rp.pin("1"), net="+12V", rise=G(4))
        sh.seg(Rp.pin("2"), (G(218), G(yy)))
        sh.seg(U.pin("out"), (G(232), G(yy)))
        sh.label((G(232), G(yy)), f"PWM_{tag}")

    # ---- triangle oscillator --------------------------------------------
    sh.note((G(26), G(100)), "triangle carrier", size=1.6)
    R4 = sh.place(R, "R4", at=(G(38), G(111)), rot=90, value="5k6")
    U3 = sh.place(OPA, "U3", at=(G(56), G(109)), value="TL074")
    sim["U3"] = dict(SIM_OPAMP)
    C12 = sh.place(C, "C12", at=(G(58), G(122)), rot=90, value="470p")
    sh.seg(R4.pin("2"), U3.pin("-"))
    sh.seg(U3.pin("-"), (G(50), G(122)))
    sh.seg((G(50), G(122)), C12.pin("1"))
    R5 = sh.place(R, "R5", at=(G(80), G(109)), rot=90, value="10k")
    sh.seg(U3.pin("out"), R5.pin("1"))
    sh.seg((G(66), G(109)), (G(66), G(122)))
    sh.seg(C12.pin("2"), (G(66), G(122)))
    sh.seg(U3.pin("+"), (G(44), G(107)))
    sh.label((G(44), G(107)), "VGND")
    sh.rail(U3.pin("V+"), net="+12V", rise=G(4))
    sh.gnd(U3.pin("V-"), drop=G(4))
    sh.label((G(72), G(109)), "TRI")

    U4 = sh.place(CMP, "U4", at=(G(100), G(111)), value="LM311")
    sim["U4"] = dict(SIM_LM311)
    sh.seg(R5.pin("2"), U4.pin("+"))
    R6 = sh.place(R, "R6", at=(G(88), G(128)), value="27k4")
    sh.seg(R6.pin("1"), (G(88), G(109)))
    sh.seg(U4.pin("-"), (G(90), G(113)))
    sh.seg((G(90), G(113)), (G(90), G(120)))
    sh.label((G(90), G(120)), "VGND")
    sh.rail(U4.pin("V+"), net="+12V", rise=G(4))
    gnd_pair(sh, U4, G(121))
    sh.nc(U4.pin("BAL"))
    sh.nc(U4.pin("STRB"))

    R7 = sh.place(R, "R7", at=(G(114), G(104)), value="1k")
    sh.rail(R7.pin("1"), net="+12V", rise=G(4))
    sh.seg(R7.pin("2"), (G(114), G(111)))
    sh.seg(U4.pin("out"), (G(122), G(111)))
    sh.seg((G(122), G(111)), (G(122), G(138)))
    sh.seg((G(122), G(138)), (G(32), G(138)))
    sh.seg((G(32), G(138)), (G(32), G(111)))
    sh.seg((G(32), G(111)), R4.pin("1"))
    sh.seg(R6.pin("2"), (G(88), G(138)))
    sh.label((G(70), G(138)), "SQ")

    # ---- complements, driver, bridge, filter ----------------------------
    sh.note((G(150), G(96)), "complement generation", size=1.6)
    inverters_block(sh, sim, 176, 108)

    sh.note((G(26), G(176)), "gate driver", size=1.6)
    driver_block(sh, sim, 60, 200)
    sh.note((G(152), G(172)), "output bridge", size=1.6)
    bridge_block(sh, sim, 160, 180)
    sh.note((G(250), G(180)), "filter, Zobel and a 4 ohm load", size=1.6)
    filter_block(sh, sim, 250, 188)

    sh.note((G(10), G(240)),
            "U1 is the board's buffer U1C, U2 its inverter U1D, U3 the "
            "integrator U1B and U4 the oscillator's U2; U7/U8 are the PWM "
            "comparators U3/U4 and U20..U23 the four used sections of U5. "
            "One symbol per section, because a SPICE model has no units.",
            size=1.27)
    sh.note((G(10), G(246)),
            "R2/R3 are the level pot at 80 % of rotation. The 6 V virtual "
            "ground is an ideal source here: the real one is R1/R2/C1 and "
            "takes 2.5 s to settle, which is bench A's business, not a run "
            "that has to resolve a 250 kHz carrier.", size=1.27)
    sh.note((G(10), G(252)),
            "C3, the input DC block, is left out for the same reason -- with "
            "uic it would spend 15 ms charging. The source already sits at the "
            "virtual ground.", size=1.27)
    sh.note((G(10), G(260)),
            "This is the sheet that answers the design question. At 1.77 Vrms "
            "in it should make about 12 W across 4 ohm -- and AUDIO_P should "
            "reach exactly 4.0 V at the bottom of its swing, which is the "
            "TL074's input common-mode floor. Full output and the input "
            "stage's limit arrive together; there is no headroom in hand.",
            size=1.27)
    sh.note((G(10), G(268)), WORKBOOK["sim_g_chain"][0], size=1.6)
    return sim


# ===========================================================================
# Where the "back to the board" link goes on each sheet: clear of the drawing,
# which is not the same y once a sheet is more than a screenful tall.
BACKLINK_Y = {"sim_e_driver": 212, "sim_f_bridge": 192, "sim_g_chain": 276}


def main():
    bad = 0
    write_sym_lib_table(SIM / "sym-lib-table")
    for name, title, uuid, paper, fn in BENCHES:
        sh = new_sheet(title, name, uuid, paper=paper)
        sim = fn(sh)
        problems = sh.check()
        for p in problems:
            print(f"  {name}: CHECK {p}")
            bad += 1
        links = back_link(sh, y=G(BACKLINK_Y.get(name, 88)))
        out = SIM / f"{name}.kicad_sch"
        sh.emit(str(out))
        set_sim(out, sim)
        add_hrefs(out, links)
        write_project(SIM / f"{name}.kicad_pro", uuid, name)
        write_workbook(SIM / f"{name}.wbk", name)
        print(f"  {name:16s} {paper}  {len(sh.parts):3d} symbols, "
              f"{len(sh.wires):3d} wires, {len(sim)} models")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
