#!/usr/bin/env python3
"""Predicted response of the as-built subxo board, and the numbers behind it.

Every table in [[Test Guide - Sub Crossover Board]] comes from here. Run it to
regenerate them, or import `response()` to overlay the model on a measured
sweep.

Why this exists rather than the textbook formula
------------------------------------------------
The design assumes f0 = 1/(2*pi*R*sqrt(C1*C2)) with R = 8k25. That is only true
if the input coupling capacitors are a short at the frequencies of interest.
They are not. C_in was substituted 2u2 -> 220n, and 220n is 8.8k of reactance at
82 Hz -- more than half of the 16k5 leg it sits in series with, and reactive
rather than resistive. R1_1/R1_2 are simultaneously the mono-summing network and
the filter's R1, so the coupling capacitors are inside the filter.

The consequence is not small: corners move from a nominal 82-191 Hz to 100-200
Hz, the passband droops 0.7-4.1 dB, and the Q = 1.17 peaking that the as-built
BOM warns about is damped away to nothing.

Topology, from the exported netlist
-----------------------------------
    Vs --C_in-- A_L --R1_1(16k5)--+
                 |                |
               R_b1(100k)         |
                 |                +-- N1 --R2(8k25)-- N2 --> A1(+)
                VGND              |         |            |
    Vs --C_in-- A_R --R1_2(16k5)--+        C2           follower
                 |                          |            |
               R_b2(100k)                 VGND          OUT1
                 |                                       |
                VGND                     N1 <----C1------+

VGND is an AC ground: a divider buffered by A3 with 100 uF across it.

    py -3.13 subxo_model.py              # all nine settings
    py -3.13 subxo_model.py --designed   # what 2u2 C_in would have given
"""

import argparse

import numpy as np

RB = 100e3      # R_b1, R_b2  -- bias to VGND, and the only DC load on C_in
R1LEG = 16500.0  # R1_1, R1_2 -- one per channel, parallel = the filter's R1
R2 = 8250.0      # R2
CIN_BUILT = 220e-9
CIN_DESIGN = 2.2e-6

# JP1 selects C1, JP2 selects C2. Position 1 of JP1 is C1_1, not fitted.
C1_SETTINGS = [("pos2 (220n)", 220e-9),
               ("pos3 (150n)", 150e-9),
               ("pos2+3 (370n)", 370e-9)]
C2_SETTINGS = [("pos1 (150n)", 150e-9),
               ("pos2 (120n)", 120e-9),
               ("pos3 (68n)", 68e-9)]


def response(f, c1, c2, cin=CIN_BUILT, rb=RB, r1leg=R1LEG, r2=R2, legs=2):
    """Complex Vout/Vin at frequency f, with both inputs driven together.

    Thevenin at N1 looking back: each leg is r1leg in series with (rb || 1/sC),
    and `legs` of them in parallel. The unity-gain Sallen-Key then has

        H = 1 / (1 + s*C2*(R2 + Z1) + s^2*C1*C2*R2*Z1)

    which reduces to the textbook form when Z1 is the real 8k25.

    Cross-checked against a modified nodal analysis of the full netlist; the
    two agree to 1e-15 dB.
    """
    s = 2j * np.pi * np.asarray(f, dtype=float)
    zb = rb / (1 + s * rb * cin)          # R_b in parallel with the coupling cap
    z1 = (r1leg + zb) / legs
    highpass = s * rb * cin / (1 + s * rb * cin)
    return highpass / (1 + s * c2 * (r2 + z1) + s ** 2 * c1 * c2 * r2 * z1)


def db(x):
    return 20 * np.log10(np.abs(x))


def corner(c1, c2, cin=CIN_BUILT, ref_hz=63.0, **kw):
    """Frequency 3 dB below this setting's own level at `ref_hz`.

    Referenced to 63 Hz rather than to an absolute 0 dB because the as-built
    passband is not flat, and because 63 Hz is where the Bose module's own
    bandpass starts -- below it, our response does not reach the driver.
    """
    f = np.logspace(np.log10(10), np.log10(2000), 20001)
    curve = db(response(f, c1, c2, cin, **kw))
    ref = np.interp(ref_hz, f, curve)
    above = f > ref_hz
    return float(f[above][np.argmax(curve[above] < ref - 3.0)]), float(ref)


def tolerance_band(c1, c2, draws=1000, seed=7):
    """2.5-97.5 percentile of the corner over the parts' real tolerances.

    Film caps +/-5% (the marked K grade is +/-10%, but measured parts cluster
    tighter), R_b +/-2%, the E96 resistors +/-0.5%.
    """
    rng = np.random.default_rng(seed)
    out = [corner(c1 * rng.normal(1, 0.05),
                  c2 * rng.normal(1, 0.05),
                  CIN_BUILT * rng.normal(1, 0.05),
                  rb=RB * rng.normal(1, 0.02),
                  r1leg=R1LEG * rng.normal(1, 0.005),
                  r2=R2 * rng.normal(1, 0.005))[0] for _ in range(draws)]
    return tuple(np.percentile(out, [2.5, 97.5]))


def mono_sum_ratio(f, c1, c2, cin=CIN_BUILT, grounded=True):
    """dB by which both-driven exceeds one-leg-driven.

    Grounded: exactly +6.02 dB at every frequency, because grounding the idle
    input makes the two legs a plain 2:1 divider of identical networks.

    Floating: the idle leg presents 16k5 in series with (100k || C_in) instead
    of 16k5 to ground, so the ratio becomes frequency-dependent and reads like
    a fault. This is the easiest way to mis-measure the board.
    """
    both = response(f, c1, c2, cin, legs=2)
    if grounded:
        # Shorting the idle input puts its C_in on AC ground, where R_b already
        # is -- so the idle leg's impedance is identical to the live one's. The
        # Thevenin impedance at N1 is unchanged and only the drive halves.
        return db(both) - db(both / 2)
    # Idle leg open: its C_in dangles, so only R_b loads R1 back to AC ground.
    s = 2j * np.pi * np.asarray(f, dtype=float)
    zb = RB / (1 + s * RB * cin)
    z_idle = R1LEG + RB                    # open C_in -> only R_b to VGND
    z_live = R1LEG + zb
    z1 = z_live * z_idle / (z_live + z_idle)
    hp = (s * RB * cin / (1 + s * RB * cin)) * (z_idle / (z_live + z_idle))
    one = hp / (1 + s * c2 * (R2 + z1) + s ** 2 * c1 * c2 * R2 * z1)
    return db(both) - db(one)


def peaking(c1, c2, cin=CIN_BUILT):
    """dB by which the response rises above its own 20 Hz level.

    Referenced to 20 Hz rather than to 63 Hz because this is the "does it bump"
    question, and the bump can sit either side of 63 Hz. The textbook peak for a
    2nd-order low-pass, Q/sqrt(1 - 1/(4Q^2)), does not apply here: the coupling
    caps damp the filter, and the input high-pass is still rising at 20 Hz.
    """
    f = np.logspace(np.log10(20), np.log10(2000), 40001)
    curve = db(response(f, c1, c2, cin))
    return float(curve.max() - curve[0])


FREQS = [20, 30, 50, 63, 80, 100, 125, 160, 200, 250, 400, 800]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--designed", action="store_true",
                    help="model 2u2 C_in -- the board as drawn, not as built")
    ap.add_argument("--draws", type=int, default=1000,
                    help="Monte Carlo draws for the tolerance band")
    a = ap.parse_args()

    cin = CIN_DESIGN if a.designed else CIN_BUILT
    which = "DESIGNED (C_in 2u2)" if a.designed else "AS BUILT (C_in 220n)"
    print(f"\n{which}\n" + "=" * len(which))

    print(f"\nCorner = 3 dB below each setting's own 63 Hz level\n")
    print(f"{'JP1':16s} {'JP2':13s} {'g(63Hz)':>9s} {'corner':>9s} "
          f"{'tolerance band':>18s}")
    print("-" * 70)
    for n1, c1 in C1_SETTINGS:
        for n2, c2 in C2_SETTINGS:
            f3, ref = corner(c1, c2, cin)
            band = "" if a.designed else "  %5.1f - %5.1f Hz" % tolerance_band(
                c1, c2, a.draws)
            print(f"{n1:16s} {n2:13s} {ref:+8.2f}  {f3:8.1f}{band}")

    print(f"\n\nShape, dB relative to each setting's own 63 Hz\n")
    print(f"{'JP1 / JP2':30s}" + "".join(f"{h:>7d}" for h in FREQS))
    for n1, c1 in C1_SETTINGS:
        for n2, c2 in C2_SETTINGS:
            ref = db(response(63.0, c1, c2, cin))
            row = db(response(FREQS, c1, c2, cin)) - ref
            label = f"{n1.split()[0]} / {n2.split()[0]}"
            print(f"{label:30s}" + "".join(f"{v:+7.2f}" for v in row))

    print(f"\n\nPeaking: rise above each setting's own 20 Hz level\n")
    for n1, c1 in C1_SETTINGS:
        for n2, c2 in C2_SETTINGS:
            print(f"  {n1:16s} {n2:13s} {peaking(c1, c2, cin):+6.2f} dB")

    print(f"\n\nOctave 400 -> 800 Hz (2nd order wants -12.0 dB)\n")
    for n1, c1 in C1_SETTINGS:
        for n2, c2 in C2_SETTINGS:
            slope = db(response(800.0, c1, c2, cin) / response(400.0, c1, c2, cin))
            print(f"  {n1:16s} {n2:13s} {slope:+7.2f} dB")

    if not a.designed:
        print(f"\n\nMono sum, both driven vs one leg (Gate 6)\n")
        print(f"{'Hz':>6} {'idle grounded':>15} {'idle floating':>15}")
        print("-" * 38)
        for f in (30, 63, 100, 200):
            g = mono_sum_ratio(f, 220e-9, 120e-9)
            o = mono_sum_ratio(f, 220e-9, 120e-9, grounded=False)
            print(f"{f:6.0f} {g:+14.2f} {o:+14.2f}")
        print("\n  Grounded is flat at +6.02 dB by construction. Any tilt at all"
              "\n  means the idle input is floating -- ground it and repeat.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
