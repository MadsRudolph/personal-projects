#!/usr/bin/env python3
"""Redraw the Bose Companion 5 sub crossover as a readable schematic.

The electrical design is FROZEN -- validated through gate 10, board built.
This script changes only the drawing. verify_against() proves the netlist
partition is untouched, and net *names* are preserved exactly too, because the
existing .kicad_pcb matches on them.

    py -3.13 subxo_layout.py <out.kicad_sch> <subxo.json>

Layout: three bands, signal left to right.
  band 1  power in -> LM7812 -> rails | status LEDs | virtual ground | U1 supply
  band 2  L/R in -> DC block -> sum -> Sallen-Key low-pass -> polarity inverter
  band 3  polarity switch -> level pot -> output jack | spare section

Coordinates are taken from real pin positions rather than assumed, so moving a
part cannot silently produce a diagonal or a near-miss.
"""
import json
import sys

sys.path.insert(0, r"C:\Users\Mads2\.claude\skills\kicad-schematic\scripts")
from schdraw import Sheet  # noqa: E402

SUB = (r"C:\Users\Mads2\Documents\Projects\Projects\Bose Sub Integration"
       r"\hardware\kicad\subxo.kicad_sch")
MOT = (r"C:\Users\Mads2\DTU\4. Semester\Electrical Energy Systems\team"
       r"\hardware\kicad\boards\CompleteMotorCircuit\CompleteMotorCircuit"
       r"\CompleteMotorCircuit.kicad_sch")

G = lambda n: round(n * 1.27, 2)      # noqa: E731 - 1 unit = one 1.27 mm grid step
OP = "Amplifier_Operational:TL074"


def build():
    # symcache supplies stock KiCad definitions, which keeps ERC's
    # lib_symbol_mismatch quiet; donors remain as a fallback only.
    # Inherit the root-sheet uuid the project already records, so the symbol
    # instance paths resolve when the sheet is opened as part of the project.
    PRO = SUB.replace("subxo.kicad_sch", "subxo.kicad_pro")
    sh = Sheet(paper="A3", title="Bose Companion 5 sub crossover",
               project="subxo", project_file=PRO)

    def R(ref, at, value, rot=0):
        return sh.place("Device:R", ref, at=at, rot=rot, value=value)

    def C(ref, at, value, pol=False, rot=0):
        return sh.place("Device:C_Polarized" if pol else "Device:C", ref,
                        at=at, rot=rot, value=value)

    def term(ref, at, value, ways=2, facing="right"):
        lib = f"Connector:Screw_Terminal_01x0{ways}"
        return sh.place(lib, ref, at=at, value=value,
                        mirror="y" if facing == "right" else "")

    def opamp(ref, unit, plus_at):
        """Place a TL074 section so its '+' pin lands exactly on plus_at.

        Corpus convention: signal arrives at the non-inverting input's exact Y,
        so the input run is a straight horizontal with no elbow.
        """
        u = sh.place(OP, ref, unit=unit,
                     at=(plus_at[0] + G(6), plus_at[1] + G(2)), value="TL074")
        return u, u.pin("+"), u.pin("-"), u.pin("out")

    def buffer_loop(out, im, depth=G(6), back=G(10)):
        """Unity gain: output wrapped back to '-' as a clean loop below."""
        y = out.y + depth
        sh.seg(out, (out.x, y))
        sh.seg((out.x, y), (out.x - back, y))
        sh.seg((out.x - back, y), (out.x - back, im.y))
        sh.seg((out.x - back, im.y), im)

    # =================================================== A: power input
    sh.note((G(12), G(20)), "A   POWER IN     +15 V -> LM7812 -> +12 V", size=2)
    j4 = term("J4", (G(14), G(32)), "PWR IN 15V")
    vin, vin_gnd = j4.pin(1), j4.pin(2)
    u2 = sh.place("Regulator_Linear:LM7812_TO220", "U2",
                  at=(G(44), vin.y), value="LM7812")
    c10 = C("C10", (G(30), vin.y + G(3)), "100uF/50V", pol=True)
    sh.seg(vin, u2.pin("VI"))
    sh.seg(c10.pin(1), (c10.x, vin.y))
    sh.label((G(21), vin.y), "VIN")

    v12 = u2.pin("VO")
    sh.seg(v12, (G(88), v12.y))                     # +12 V rail
    sh.label((G(88), v12.y), "V12")
    for ref, val, gx in (("C11", "100uF/50V", 52), ("C12", "100nF", 62),
                         ("C13", "100nF", 72), ("C14", "100nF", 82)):
        c = C(ref, (G(gx), v12.y + G(3)), val, pol=(ref == "C11"))
        sh.seg(c.pin(1), (c.x, v12.y))

    gl = u2.pin("GND").y                            # GND_LNK return rail
    sh.seg(vin_gnd, (vin_gnd.x + G(2), vin_gnd.y))
    sh.seg((vin_gnd.x + G(2), vin_gnd.y), (vin_gnd.x + G(2), gl))
    sh.seg((vin_gnd.x + G(2), gl), (G(82), gl))
    for gx in (30, 52, 62, 72, 82):                 # cap bottoms onto the rail
        sh.seg((G(gx), v12.y + G(6)), (G(gx), gl))
    sh.label((G(22), gl), "GND_LNK")
    # PWR_FLAG tells ERC these rails are driven (nothing else sources them)
    sh.power("power:PWR_FLAG", (G(42), gl))
    sh.power("power:PWR_FLAG", (G(26), vin.y))

    lk = R("LK1", (G(94), gl + G(3)), "0R wire link")
    sh.seg((G(82), gl), (G(94), gl))
    sh.seg((G(94), gl), lk.pin(1))
    gsym = sh.gnd(lk.pin(2))
    sh.power("power:PWR_FLAG", (lk.pin(2).x, lk.pin(2).y + G(2)))
    sh.note((G(10), gl + G(9)),
            "LK1 is the single tie between supply return and signal ground.")

    # =================================================== B: status LEDs
    sh.note((G(100), G(20)), "B   STATUS LEDS", size=2)
    led_rail = G(26)
    sh.seg((G(104), led_rail), (G(116), led_rail))
    sh.label((G(108), led_rail), "V12")
    r10 = R("R10", (G(104), led_rail + G(4)), "4k7")
    r11 = R("R11", (G(116), led_rail + G(4)), "4k7")
    sh.seg(r10.pin(1), (r10.x, led_rail))
    sh.seg(r11.pin(1), (r11.x, led_rail))
    # rot 90 puts the anode up and the cathode down: current flows downward
    d1 = sh.place("Device:LED", "D1", at=(G(104), G(38)), rot=90,
                  value="PWR green")
    d2 = sh.place("Device:LED", "D2", at=(G(116), G(38)), rot=90,
                  value="INV amber")
    sh.seg(r10.pin(2), d1.pin("A"))
    sh.label(d1.pin("A"), "PWR_A")
    sh.gnd(d1.pin("K"), drop=G(3))
    sh.seg(r11.pin(2), d2.pin("A"))
    sh.label(d2.pin("A"), "INV_A")
    j7 = term("J7", (G(126), G(45)), "INV LED", facing="left")
    sh.label(d2.pin("K"), "INV_K")
    sh.seg(d2.pin("K"), (d2.x, j7.pin(1).y))
    sh.seg((d2.x, j7.pin(1).y), j7.pin(1))
    sh.gnd(j7.pin(2), drop=G(3))
    sh.note((G(100), G(50)),
            "D2 is lit from J7 by the polarity switch's spare pole.")

    # =================================================== C: virtual ground
    sh.note((G(142), G(20)), "C   VIRTUAL GROUND     +6 V, buffered", size=2)
    vgd_y = G(34)                                   # the VG_DIV node line
    r8 = R("R8", (G(148), vgd_y - G(4)), "10k")
    r9 = R("R9", (G(148), vgd_y + G(4)), "10k")
    sh.seg(r8.pin(1), (r8.x, G(26)))
    sh.label((r8.x, G(26)), "V12")
    sh.seg(r8.pin(2), r9.pin(1))
    sh.label(r8.pin(2), "VG_DIV")
    sh.seg(r9.pin(2), (r9.x, G(42)))
    sh.label((r9.x, G(42)), "GND_LNK")
    c15 = C("C15", (G(158), vgd_y + G(4)), "100uF/50V", pol=True)
    sh.seg((r8.x, vgd_y), (c15.x, vgd_y))
    sh.seg(c15.pin(1), (c15.x, vgd_y))
    sh.gnd(c15.pin(2), drop=G(3))

    u1c, cp, cm, co = opamp("U1", 3, (G(170), vgd_y))
    sh.seg((c15.x, vgd_y), cp)
    buffer_loop(co, cm)
    sh.seg(co, (co.x + G(8), co.y))
    sh.label((co.x + G(8), co.y), "VGND")

    u1e = sh.place(OP, "U1", unit=5, at=(G(206), G(34)), value="TL074")
    sh.seg(u1e.pin("V+"), (u1e.pin("V+").x, G(24)))
    sh.label((u1e.pin("V+").x, G(24)), "V12")
    sh.gnd(u1e.pin("V-"), drop=G(4))
    sh.note((G(198), G(50)), "U1 supply: pin 4 = V12, pin 11 = GND.")

    # =================================================== D: inputs + summing
    sh.note((G(12), G(58)), "D   INPUTS     L + R, DC-blocked, summed", size=2)
    N1_X = G(64)
    ch = []
    for n, (jref, cref, rbref, r1ref, y, cap) in enumerate((
            ("J1", "C_in1", "R_b1", "R1_1", G(96), "IN L"),
            ("J2", "C_in2", "R_b2", "R1_2", G(112), "IN R"))):
        j = term(jref, (G(14), y - G(1)), cap)
        sig = j.pin(1)
        cin = C(cref, (G(28), sig.y), "220n or 2u2", rot=90)
        sh.seg(sig, cin.pin(1))
        sh.label((G(20), sig.y), "IN_L" if n == 0 else "IN_R")
        sh.gnd(j.pin(2), drop=G(3))
        a_x = G(40)
        sh.seg(cin.pin(2), (a_x, sig.y))
        sh.label((G(34), sig.y), "A_L" if n == 0 else "A_R")
        rb = R(rbref, (a_x, sig.y + G(6)), "100k")
        sh.seg((a_x, sig.y), rb.pin(1))
        sh.seg(rb.pin(2), (a_x, sig.y + G(10)))
        sh.label((a_x, sig.y + G(10)), "VGND")
        r1 = R(r1ref, (G(52), sig.y), "16k5", rot=90)
        sh.seg((a_x, sig.y), r1.pin(1))
        sh.seg(r1.pin(2), (N1_X, sig.y))
        ch.append(sig.y)
    sh.seg((N1_X, ch[0]), (N1_X, ch[1]))            # the two sum into N1
    sh.note((G(10), G(148)),
            "R_b1/R_b2 are the only DC path to U1A's + input -- without them "
            "the amp drifts to a rail.")

    # =================================================== E: Sallen-Key low-pass
    sh.note((G(72), G(58)), "E   SALLEN-KEY LOW-PASS   2nd order", size=2)
    N1_Y = G(104)
    sh.seg((N1_X, ch[0]), (N1_X, N1_Y))
    sh.label((G(68), N1_Y), "N1")
    r2 = R("R2", (G(82), N1_Y), "8k25", rot=90)
    sh.seg((N1_X, N1_Y), r2.pin(1))
    N2_X = G(92)
    sh.seg(r2.pin(2), (N2_X, N1_Y))
    sh.label((N2_X, N1_Y), "N2")

    u1a, ap, am, ao = opamp("U1", 1, (G(108), N1_Y))
    sh.seg((N2_X, N1_Y), ap)

    # C2 bank: N2 down through JP2 to VGND. The selector sits left of the
    # caps with its pins facing them; caps are ordered so the one nearest the
    # header takes the nearest pin, which keeps every run crossing-free.
    c2_top = G(114)
    sh.seg((N2_X, N1_Y), (N2_X, c2_top))
    jp2 = sh.place("Connector_Generic:Conn_01x06", "JP2", at=(G(66), G(136)),
                   value="C2 select", mirror="y")
    xs2 = [G(84), G(98), G(112)]
    sh.seg((xs2[0], c2_top), (xs2[-1], c2_top))
    for i, (ref, val) in enumerate((("C2_1", "150nF film"),
                                    ("C2_2", "120nF film"),
                                    ("C2_3", "68nF film"))):
        c = C(ref, (xs2[i], c2_top + G(5)), val)
        sh.seg(c.pin(1), (c.x, c2_top))
        pin = jp2.pin(2 * i + 1)
        sh.seg(c.pin(2), (c.x, pin.y))
        sh.label((c.x, pin.y), f"C2{'ABC'[i]}_SEL")
        sh.seg((c.x, pin.y), pin)
    for i in range(3):                              # even pins = common = VGND
        pin = jp2.pin(2 * i + 2)
        sh.seg(pin, (G(60), pin.y))
    sh.seg((G(60), jp2.pin(2).y), (G(60), jp2.pin(6).y))
    sh.seg((G(60), jp2.pin(4).y), (G(52), jp2.pin(4).y))
    sh.label((G(52), jp2.pin(4).y), "VGND")

    # C1 bank: output back to N1 -- the Sallen-Key feedback capacitor
    fb_y = G(84)
    sh.seg(ao, (G(136), ao.y))
    sh.seg((G(136), ao.y), (G(136), fb_y))
    jp1 = sh.place("Connector_Generic:Conn_01x06", "JP1", at=(G(66), G(70)),
                   value="C1 select", mirror="y")
    xs1 = [G(112), G(98), G(84)]                    # C1_1 farthest from JP1
    sh.seg((xs1[-1], fb_y), (G(136), fb_y))
    for i, (ref, val) in enumerate((("C1_1", "470nF film"),
                                    ("C1_2", "220nF film"),
                                    ("C1_3", "150nF film"))):
        # rot 180 so pin 1 (the OUT1 side) faces down onto the feedback rail
        c = C(ref, (xs1[i], fb_y - G(5)), val, rot=180)
        sh.seg(c.pin(1), (c.x, fb_y))
        pin = jp1.pin(2 * i + 1)
        sh.seg(c.pin(2), (c.x, pin.y))
        sh.label((c.x, pin.y), f"C1{'ABC'[i]}_SEL")
        sh.seg((c.x, pin.y), pin)
    for i in range(3):
        pin = jp1.pin(2 * i + 2)
        sh.seg(pin, (G(60), pin.y))
    sh.seg((G(60), jp1.pin(2).y), (G(60), jp1.pin(6).y))
    sh.seg((G(60), jp1.pin(4).y), (G(54), jp1.pin(4).y))
    sh.label((G(54), jp1.pin(4).y), "N1")
    sh.note((G(66), G(152)),
            "JP1/JP2 select C1 and C2 independently -- nine corners, not three.")

    buffer_loop(ao, am, depth=G(6), back=G(20))
    sh.label((G(136), ao.y), "OUT1")

    # =================================================== F: polarity inverter
    sh.note((G(150), G(58)), "F   POLARITY INVERTER   unity gain -1", size=2)
    r3 = R("R3", (G(154), ao.y), "10k", rot=90)
    sh.seg((G(136), ao.y), r3.pin(1))
    inv_x = G(164)
    sh.seg(r3.pin(2), (inv_x, ao.y))
    sh.label((inv_x, ao.y), "INV_IN")

    u1b, bp, bm, bo = opamp("U1", 2, (G(180), ao.y + G(4)))
    sh.seg((inv_x, ao.y), (inv_x, bm.y))
    sh.seg((inv_x, bm.y), bm)
    sh.seg(bp, (bp.x - G(6), bp.y))
    sh.label((bp.x - G(6), bp.y), "VGND")
    # feedback resistor below the amp, running right to left
    r4_y = bm.y + G(10)
    r4 = R("R4", (G(172), r4_y), "10k", rot=90)
    sh.seg(bo, (G(196), bo.y))
    sh.seg((G(196), bo.y), (G(196), r4_y))
    sh.seg((G(196), r4_y), r4.pin(2))
    sh.seg(r4.pin(1), (inv_x, r4_y))
    sh.seg((inv_x, r4_y), (inv_x, bm.y))
    sh.seg((G(196), bo.y), (G(204), bo.y))
    sh.label((G(204), bo.y), "OUT2")

    # =================================================== G: output stage
    sh.note((G(12), G(158)), "G   OUTPUT     polarity select -> level -> jack",
            size=2)
    j5 = term("J5", (G(34), G(168)), "POLARITY SW", ways=3)
    sh.seg(j5.pin(1), (G(24), j5.pin(1).y))
    sh.label((G(24), j5.pin(1).y), "OUT1")
    sh.seg(j5.pin(2), (G(24), j5.pin(2).y))
    sh.label((G(24), j5.pin(2).y), "OUT2")
    com = j5.pin(3)                      # pin 3 is the switch common
    cout = C("C_out1", (G(52), com.y), "10uF/50V", pol=True, rot=90)
    sh.seg(com, cout.pin(1))
    sh.label((G(40), com.y), "SW_COM")

    j6 = term("J6", (G(74), G(168)), "LEVEL POT 10k", ways=3)
    sh.seg(cout.pin(2), (G(64), com.y))
    sh.seg((G(64), com.y), (G(64), j6.pin(1).y))
    sh.seg((G(64), j6.pin(1).y), j6.pin(1))
    sh.label((G(64), j6.pin(1).y), "POT_TOP")
    sh.gnd(j6.pin(3), drop=G(4))

    w = j6.pin(2)
    r5 = R("R5", (G(100), w.y - G(6)), "100R", rot=90)
    r6 = R("R6", (G(100), w.y + G(6)), "100R", rot=90)
    sh.seg(w, (G(90), w.y))
    sh.seg((G(90), w.y), (G(90), r5.pin(1).y))
    sh.seg((G(90), r5.pin(1).y), r5.pin(1))
    sh.seg((G(90), w.y), (G(90), r6.pin(1).y))
    sh.seg((G(90), r6.pin(1).y), r6.pin(1))
    sh.label((G(90), w.y), "POT_W")

    j3 = term("J3", (G(128), G(168)), "OUT 3.5mm", ways=3, facing="left")
    sh.label(r5.pin(2), "OUT_TIP")
    sh.seg(r5.pin(2), (G(116), r5.pin(2).y))
    sh.seg((G(116), r5.pin(2).y), (G(116), j3.pin(1).y))
    sh.seg((G(116), j3.pin(1).y), j3.pin(1))
    sh.label(r6.pin(2), "OUT_RING")
    sh.seg(r6.pin(2), (G(112), r6.pin(2).y))
    sh.seg((G(112), r6.pin(2).y), (G(112), j3.pin(2).y))
    sh.seg((G(112), j3.pin(2).y), j3.pin(2))

    # output ground: R7 damps the shield, JP3 can lift it
    # R7 (damp) and JP3 (lift) sit in parallel between GND and OUT_GND, so
    # they are drawn as two rungs of a ladder between the same two rails
    og_y, GND_X, OG_X = G(188), G(80), G(108)
    sh.seg(j3.pin(3), (OG_X, j3.pin(3).y))
    sh.seg((OG_X, j3.pin(3).y), (OG_X, og_y))
    sh.label((OG_X, og_y), "OUT_GND")
    r7 = R("R7", (G(94), og_y), "10R", rot=90)
    sh.seg(r7.pin(2), (OG_X, og_y))
    sh.seg(r7.pin(1), (GND_X, og_y))
    jp3 = sh.place("Connector_Generic:Conn_01x02", "JP3", at=(G(72), G(196)),
                   value="GND lift", mirror="y")
    sh.seg(jp3.pin(2), (OG_X, jp3.pin(2).y))
    sh.seg((OG_X, jp3.pin(2).y), (OG_X, og_y))
    sh.seg(jp3.pin(1), (GND_X, jp3.pin(1).y))
    sh.seg((GND_X, jp3.pin(1).y), (GND_X, og_y))
    sh.gnd((GND_X, og_y), drop=G(4))
    sh.note((G(12), G(206)),
            "R7 + JP3 let the output shield be damped or lifted at the jack.")

    # =================================================== H: spare section
    sh.note((G(150), G(158)), "H   SPARE SECTION     tied off, not floating",
            size=2)
    u1d, dp, dm, do = opamp("U1", 4, (G(166), G(174)))
    sh.seg(dp, (dp.x - G(8), dp.y))
    sh.label((dp.x - G(8), dp.y), "VGND")
    buffer_loop(do, dm, depth=G(6), back=G(14))
    sh.label(do, "SPARE_OUT")
    sh.note((G(150), G(190)),
            "An unterminated spare section oscillates and couples into its "
            "neighbours through the shared supply.")
    return sh


def apply_fields(sh, ir_path):
    """Take Value and Footprint verbatim from the source board.

    Retyping these by hand is how a redraw silently loses the footprint
    assignments the PCB depends on -- so they are copied, never re-entered.
    """
    d = json.load(open(ir_path, encoding="utf-8"))
    fp = {p["ref"]: (p.get("footprint") or "") for p in d["parts"]}
    val = {p["ref"]: (p.get("value") or "") for p in d["parts"]}
    missing = []
    for part in sh.parts:
        if getattr(part, "is_power_port", False):
            continue
        if part.ref not in fp:
            missing.append(part.ref)
            continue
        part.footprint = fp[part.ref]
        part.value = val[part.ref]
    return missing


def target_nets(path):
    d = json.load(open(path, encoding="utf-8"))
    return {n["name"].lstrip("/"): {(a, b) for a, b in n["nodes"]}
            for n in d["nets"]}


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "subxo_new.kicad_sch"
    ir = sys.argv[2] if len(sys.argv) > 2 else "subxo.json"
    sh = build()
    missing = apply_fields(sh, ir)
    if missing:
        print("refs not in the source IR:", missing)
    probs = sh.check()
    print("geometry:", "clean" if not probs else f"{len(probs)} problems")
    for p in probs:
        print("   ", p)
    ok = sh.verify_against(target_nets(ir))
    sh.emit(out)
    print("wrote", out)
    sys.exit(0 if ok and not probs else 1)
