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
SIM_FET = {"Sim.Device": "NMOS", "Sim.Type": "VDMOS", "Sim.Library": VDMOS,
           "Sim.Name": "IRF540N", "Sim.Pins": "1=D 2=G 3=S"}
SIM_DIO = {"Sim.Device": "D", "Sim.Library": MODELS, "Sim.Name": "DSCH",
           "Sim.Pins": "1=K 2=A"}


def src(kind, params):
    """Sim fields for a voltage source. All four are required on the instance:
    with Sim.Params alone KiCad emits the raw parameters instead of PULSE(...)."""
    return {"Sim.Device": "V", "Sim.Type": kind, "Sim.Pins": "1=+ 2=-",
            "Sim.Params": params}


# --------------------------------------------------------------------- sheet
def new_sheet(title, project, uuid):
    sh = Sheet(paper="A3", title=title, project=project, version=10, uuid=uuid)
    sh.src._cache = SymCache(extra_dirs=[str(SIM / "lib")])
    return sh


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


BENCHES = []


def bench(name, title, uuid):
    def deco(fn):
        BENCHES.append((name, title, uuid, fn))
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
    sh.note((G(10), G(62)), ".tran 1m 3", size=1.6)
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
    sh.gnd(U2.pin("V-"), drop=G(4))
    sh.gnd(U2.pin("GND"), drop=G(4))
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
    sh.note((G(10), G(70)), ".tran 20n 200u uic", size=1.6)
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
    sh.gnd(U2.pin("V-"), drop=G(4))
    sh.label((G(136), G(46)), "AUDIO_N")

    sh.note((G(10), G(68)),
            "AUDIO_P and AUDIO_N must be equal and opposite about 6 V. Watch "
            "AUDIO_P against 4 V: that is the TL074 input common-mode floor.",
            size=1.27)
    sh.note((G(10), G(74)), ".tran 10u 5m", size=1.6)
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
        sh.gnd(U.pin("V-"), drop=G(4))
        sh.gnd(U.pin("GND"), drop=G(4))
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
    sh.note((G(10), G(78)), ".tran 50n 1m", size=1.6)
    return sim


# ===========================================================================
def main():
    bad = 0
    for name, title, uuid, fn in BENCHES:
        sh = new_sheet(title, name, uuid)
        sim = fn(sh)
        problems = sh.check()
        for p in problems:
            print(f"  {name}: CHECK {p}")
            bad += 1
        links = back_link(sh)
        out = SIM / f"{name}.kicad_sch"
        sh.emit(str(out))
        set_sim(out, sim)
        add_hrefs(out, links)
        write_project(SIM / f"{name}.kicad_pro", uuid, name)
        print(f"  {name:16s} {len(sh.parts):3d} symbols, {len(sh.wires):3d} "
              f"wires, {len(sim)} models")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
