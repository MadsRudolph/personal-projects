#!/usr/bin/env python3
"""Gate 7 for rev B: the polarity inverter, and the switch that selects it.

A2 is a unity inverter around VGND -- R3 and R4 are both 10k at 1% -- so OUT2
should be OUT1 turned upside down and nothing else: 0.00 dB and 180.0 deg at
every frequency. Drift with frequency means A2 is slewing or R3/R4 is wrong.

Rev A could only test the op-amp, because the changeover switch was never
fitted. Rev B has it, and its second pole drives the amber lamp, so this also
checks that SW_COM really does follow OUT1 in one lever position and OUT2 in
the other -- and that the lamp agrees with the audio.

Four sweeps. Only the blue 2+ lead moves, and only twice:

    1  2+ on J5.1  (OUT1)                    reference
    2  2+ on J5.2  (OUT2)                    expect 0.00 dB, 180 deg
    3  2+ on J5.3  (SW_COM), lever NORMAL    expect it to match OUT1
    4  2+ stays,             lever INVERTED  expect it to match OUT2

    python subxo_gate7.py
    python subxo_gate7.py --no-switch        # steps 1 and 2 only, op-amp alone
    python subxo_gate7.py --dry-run
    python subxo_gate7.py --dry-run-swapped  # switch wired backwards

Everything else is the Gate 6 rig, unchanged:

    W1 --- J1.1,  W2 --- J2.1,  GND --- J1.2 and AD3 GND
    1+ --- J1.1,  1- --- J1.2
    2- --- JP2 even pin (VGND)     DIFFERENTIAL, never to ground

Needs pydwf, which lives in the Python 3.14 install -- run this with
``python``, not ``py -3.13``.
"""

import argparse
import csv
import math
import sys
from pathlib import Path

import numpy as np

from subxo_gate5 import DETENTS, pydwf_help
from subxo_gate6 import sweep

TOL_MAG = 0.12               # dB, R3 and R4 are 1%
TOL_PHASE = 0.5              # degrees, the guide's figure
TOL_OUTLIER = 2.0            # degrees, individual points beyond this get named

# Judged over the passband only. Above ~200 Hz the output has fallen far enough
# that mains harmonics leaking into the measurement window move the answer more
# than the circuit does.
BAND = (15.0, 200.0)

STEPS = [
    ("out1", "2+ on J5.1  (OUT1)", "reference", False),
    ("out2", "2+ on J5.2  (OUT2)", "A2's inverted copy", False),
    ("sw_normal", "2+ on J5.3  (SW_COM), lever NORMAL", "switch, normal", True),
    ("sw_inverted", "leave 2+ on J5.3, lever INVERTED", "switch, inverted", True),
]


def fake(freqs, which, swapped, seed):
    rng = np.random.default_rng(seed)
    inverted = which in ("out2", "sw_inverted")
    if swapped and which.startswith("sw_"):
        inverted = not inverted
    mag = rng.normal(0, 0.008, len(freqs))
    ph = np.full(len(freqs), 180.0 if inverted else 0.0) \
        + rng.normal(0, 0.05, len(freqs))
    return [dict(hz=float(f), v1=1.0, v2=1.0, mag_db=float(a), phase=float(b))
            for f, a, b in zip(freqs, mag, ph)], 0


def wrap180(d):
    """Fold a phase difference into -180..180 so 179.9 and -179.9 agree."""
    return (np.asarray(d) + 180.0) % 360.0 - 180.0


def compare(name, ref, got, want_deg, band):
    """One tap against another, judged on medians.

    The mean is the wrong statistic here. Mains harmonics leak into the
    measurement window at frequencies close to a multiple of 50 Hz and throw
    individual points by several degrees; a handful of those drags a mean that
    the median shrugs off. Outliers are named separately rather than hidden.
    """
    dmag = np.array([g["mag_db"] for g in got]) - np.array([r["mag_db"] for r in ref])
    dph = wrap180(np.array([g["phase"] for g in got])
                  - np.array([r["phase"] for r in ref]) - want_deg)
    mag = float(np.median(dmag[band]))
    ph = float(np.median(dph[band]))
    mag_sp = float(np.median(np.abs(dmag[band] - mag)))
    ph_sp = float(np.median(np.abs(dph[band] - ph)))
    hz = np.array([r["hz"] for r in ref])
    wi = int(np.argmax(np.abs(dph[band])))
    worst, worst_hz = float(dph[band][wi]), float(hz[band][wi])
    print(f"  {name:30s} {mag:+7.3f} dB  {want_deg + ph:8.2f} deg"
          f"   spread {ph_sp:5.2f} deg"
          f"   worst {worst:+6.2f} at {worst_hz:5.0f} Hz")
    return dict(name=name, mag=mag, ph=ph, mag_sp=mag_sp, ph_sp=ph_sp,
                dmag=dmag, dph=dph, hz=hz, band=band)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--detent", type=int, default=2, choices=(1, 2, 3))
    ap.add_argument("--start", type=float, default=15.0)
    ap.add_argument("--stop", type=float, default=2000.0)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--amp", type=float, default=1.0)
    ap.add_argument("--range", type=float, default=2.0)
    # 128 cycles, not 16. A 16-cycle window at 305 Hz is 19 Hz wide, so the
    # 300 Hz mains harmonic lands inside the measurement bin and shifts the
    # phase by degrees. Every bad point in the first run was within two bin
    # widths of a 50 Hz harmonic. Longer windows resolve them apart.
    ap.add_argument("--cycles", type=float, default=128.0)
    ap.add_argument("--max-window", type=float, default=1.0)
    ap.add_argument("--settle", type=float, default=0.05)
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--no-switch", action="store_true",
                    help="op-amp only, skip the two SW_COM sweeps")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--dry-run-swapped", action="store_true",
                    help="synthesise a backwards switch, to test the check")
    a = ap.parse_args()

    dry = a.dry_run or a.dry_run_swapped
    n, label, c1, c2, _ = next(d for d in DETENTS if d[0] == a.detent)
    freqs = np.logspace(math.log10(a.start), math.log10(a.stop), a.steps)
    todo = [s for s in STEPS if not (a.no_switch and s[3])]
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"\nGate 7, rev B -- polarity, at detent {n} ({label})")
    if a.dry_run_swapped:
        print("DRY RUN: synthesising a BACKWARDS switch -- expect a FAIL.\n")
    elif dry:
        print("DRY RUN: synthesising a healthy board.\n")

    device = ctx = None
    if not dry:
        try:
            from pydwf import DwfLibrary
            from pydwf.utilities import openDwfDevice
        except ImportError:
            sys.exit(pydwf_help())
        ctx = openDwfDevice(DwfLibrary())
        device = ctx.__enter__()

    got = {}
    try:
        for key, instruction, _desc, _sw in todo:
            print("=" * 58)
            print(f"  {instruction}")
            print("=" * 58)
            if not dry:
                try:
                    input("  press Enter when the lead and lever are set ")
                except (EOFError, KeyboardInterrupt):
                    print("\n  stopped.")
                    return 1
                rows, clip = sweep(device, freqs, a.amp, a.amp, a.range,
                                   a.cycles, a.max_window, a.settle)
                if clip:
                    print(f"  !! {clip} points near full scale")
            else:
                rows, _ = fake(freqs, key, a.dry_run_swapped, seed=300)
            got[key] = rows
            with (outdir / f"gate7_{key}.csv").open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=["hz", "v1", "v2",
                                                   "mag_db", "phase"])
                w.writeheader()
                w.writerows(rows)
    finally:
        if ctx is not None:
            ctx.__exit__(None, None, None)

    f = np.array([r["hz"] for r in got["out1"]])
    band = (f >= BAND[0]) & (f <= BAND[1])
    fails = []
    print(f"\n  band {BAND[0]:.0f}-{BAND[1]:.0f} Hz, "
          f"{int(band.sum())} of {len(f)} points")
    print(f"\n  {'':34s} {'magnitude':>10s} {'phase':>12s}")
    print("  " + "-" * 74)

    inv = compare("OUT2 against OUT1", got["out1"], got["out2"], 180.0, band)
    null = None
    if "sw_normal" in got:
        # SW_COM in NORMAL is OUT1 reached through a closed contact -- the same
        # node measured twice. Whatever it shows is the rig, not the circuit,
        # and it is the yardstick everything else is judged against.
        null = compare("SW_COM normal vs OUT1  (null)", got["out1"],
                       got["sw_normal"], 0.0, band)
        compare("SW_COM inverted vs OUT2", got["out2"],
                got["sw_inverted"], 0.0, band)

        # A switch wired backwards still measures 0 dB and 180 deg on the pair
        # -- it just does it in the wrong lever positions. Check the sense.
        if abs(null["ph"]) > 90:
            fails.append("the switch is wired backwards -- SW_COM carries "
                         "OUT2 in the position labelled normal. Swap the two "
                         "throws on J5")

    if abs(inv["mag"]) > TOL_MAG:
        fails.append(f"OUT2 is {inv['mag']:+.3f} dB against OUT1, "
                     f"want 0.00 +/- {TOL_MAG}")
    # The floor is whichever is larger: the guide's figure, or what the rig
    # demonstrably resolves. Demanding better than the null is meaningless.
    floor = TOL_PHASE if null is None else max(TOL_PHASE, abs(null["ph"]) + null["ph_sp"])
    if null is not None:
        print(f"\n  rig resolution, from the null: {floor:.2f} deg")
    if abs(inv["ph"]) > floor:
        fails.append(f"OUT2 is {180 + inv['ph']:.2f} deg against OUT1, "
                     f"want 180.00 +/- {floor:.2f}")
    if null is not None and inv["ph_sp"] > 3 * max(null["ph_sp"], 0.2):
        fails.append(f"OUT2's phase scatters {inv['ph_sp']:.2f} deg against the "
                     f"rig's own {null['ph_sp']:.2f} -- A2 slewing, or R3/R4 wrong")

    # Mains harmonics leak into the window when the drive sits close to a
    # multiple of 50 Hz. Name those points so they are visible, not hidden.
    bad = [(float(hz), float(d)) for hz, d in zip(inv["hz"][band], inv["dph"][band])
           if abs(d) > TOL_OUTLIER]
    if bad:
        print(f"\n  points beyond {TOL_OUTLIER:.1f} deg (informational):")
        for hz, d in bad:
            harm = round(hz / 50) * 50
            gap = abs(hz - harm)
            res = hz / a.cycles
            why = (f"{gap:.1f} Hz from the {harm:.0f} Hz mains harmonic, "
                   f"bin {res:.1f} Hz -> leaks in") if gap < 2 * res else \
                  "not near a mains harmonic"
            print(f"    {hz:7.1f} Hz   {d:+6.2f} deg   {why}")

    print()
    if fails:
        print("GATE 7 FAILS:")
        for why in fails:
            print(f"  - {why}")
    else:
        print("GATE 7 PASSES -- A2 inverts cleanly and the switch selects "
              "the right output.")
        if "sw_normal" in got:
            print("\n  Now confirm by eye: the amber lamp must be lit in the")
            print("  INVERTED position and dark in NORMAL. If it is the other")
            print("  way round, move the J7 pin 1 wire to the other throw --")
            print("  the audio is correct either way, only the lamp lies.")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
