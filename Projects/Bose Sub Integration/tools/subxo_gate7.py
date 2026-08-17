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
TOL_PHASE = 0.5              # degrees
BAND = (15.0, 400.0)         # phase is solid well past the corner

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
    """Magnitude and phase of one tap against another."""
    dmag = np.array([g["mag_db"] for g in got]) - np.array([r["mag_db"] for r in ref])
    dph = wrap180(np.array([g["phase"] for g in got])
                  - np.array([r["phase"] for r in ref]) - want_deg)
    mag_mean = float(np.mean(dmag[band]))
    mag_worst = float(np.max(np.abs(dmag[band] - mag_mean)))
    ph_mean = float(np.mean(dph[band]))
    # Drift is deviation from the mean, not from the target. A constant offset
    # is a wiring or gain error and is reported as such; only genuine
    # frequency-dependence means A2 is slewing.
    ph_worst = float(np.max(np.abs(dph[band] - ph_mean)))
    print(f"  {name:34s} {mag_mean:+7.3f} dB  {want_deg + ph_mean:8.2f} deg"
          f"   drift {mag_worst:.3f} dB / {ph_worst:.2f} deg")
    fails = []
    if abs(mag_mean) > TOL_MAG:
        fails.append(f"{name}: {mag_mean:+.3f} dB, want 0.00 +/- {TOL_MAG}")
    if abs(ph_mean) > TOL_PHASE:
        fails.append(f"{name}: {want_deg + ph_mean:.2f} deg, "
                     f"want {want_deg:.0f} +/- {TOL_PHASE}")
    if mag_worst > TOL_MAG or ph_worst > 2 * TOL_PHASE:
        fails.append(f"{name} drifts with frequency "
                     f"({mag_worst:.3f} dB, {ph_worst:.2f} deg) -- "
                     f"A2 slewing, or R3/R4 wrong")
    return fails


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--detent", type=int, default=2, choices=(1, 2, 3))
    ap.add_argument("--start", type=float, default=15.0)
    ap.add_argument("--stop", type=float, default=2000.0)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--amp", type=float, default=1.0)
    ap.add_argument("--range", type=float, default=2.0)
    ap.add_argument("--cycles", type=float, default=16.0)
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

    fails += compare("OUT2 against OUT1", got["out1"], got["out2"], 180.0, band)
    if "sw_normal" in got:
        fails += compare("SW_COM normal against OUT1", got["out1"],
                         got["sw_normal"], 0.0, band)
        fails += compare("SW_COM inverted against OUT2", got["out2"],
                         got["sw_inverted"], 0.0, band)

        # A switch wired backwards still measures 0 dB and 180 deg on the pair
        # -- it just does it in the wrong lever positions. Check the sense.
        dn = wrap180(np.array([g["phase"] for g in got["sw_normal"]])
                     - np.array([r["phase"] for r in got["out1"]]))
        if abs(float(np.mean(dn[band]))) > 90:
            fails.append("the switch is wired backwards -- SW_COM carries "
                         "OUT2 in the position labelled normal. Swap the two "
                         "throws on J5")

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
