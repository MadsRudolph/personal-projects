#!/usr/bin/env python3
"""Gate 6 for rev B: the mono sum, three sweeps, no rewiring at all.

R1_1 and R1_2 are both 16k5, one per input, meeting at N1 -- and the same pair
is the filter's R1, 16k5 || 16k5 = the 8k25 the Sallen-Key is built around.
Gate 6 checks that double duty by comparing both inputs driven against one
driven and the other grounded.

The answer is +6.02 dB and it is flat. Driving both, N1 sees V behind 8k25.
Driving one with the other grounded, it sees V/2 behind the same 8k25 -- half
the voltage, identical impedance, so the corner does not move and the ratio is
the same at every frequency. That flatness is the real test: a level ratio is
easy to hit by luck, a flat one proves both legs match in magnitude and phase.

Grounding the idle input happens in software. An enabled AD3 output sitting at
0 V is about 0.5 ohm, which against 16k5 is a short. The channel must stay
ENABLED at zero amplitude -- disabling it may leave the output high-impedance,
which is the floating case, and floating is the classic way to mis-measure this
board: the idle leg becomes 16k5 + R_b's 100k, the divider goes from 0.5 to
0.876, and the tilted result looks like a broken filter.

    python subxo_gate6.py                      # detent 2, three sweeps
    python subxo_gate6.py --detent 3
    python subxo_gate6.py --dry-run            # healthy board, from the model
    python subxo_gate6.py --dry-run-floating   # prove the detector catches it

Wiring -- one setup for all three sweeps:

    W1  (yellow)     --- J1.1   IN_L
    W2  (yellow/wht) --- J2.1   IN_R
    GND (black)      --- J1.2,  and AD3 GND
    1+  (orange)     --- J1.1   drive reference, taken AT the board
    1-  (orange/wht) --- J1.2
    2+  (blue)       --- J5.1   OUT1
    2-  (blue/wht)   --- JP2 even pin (VGND)   DIFFERENTIAL, never to ground

Channel 1 reads ~0 on the third sweep because J1.1 is then grounded -- that is
not a fault, it is the confirmation that the software grounding worked.

Needs pydwf, which lives in the Python 3.14 install -- run this with
``python``, not ``py -3.13``.
"""

import argparse
import csv
import math
import sys
import time
from pathlib import Path

import numpy as np

import subxo_model as m
from subxo_gate5 import BUFFER, DETENTS, phasor, pydwf_help

IDEAL = -6.0206              # 20*log10(1/2)
BAND = (15.0, 400.0)         # where the output is well above the noise
TOL_LEVEL = 0.25             # dB, mean ratio against ideal
TOL_FLAT = 0.30              # dB, worst deviation from that mean
TOL_BALANCE = 0.15           # dB, left leg against right leg
DRIVE_LEAK = 0.05            # ch1 on the L-grounded sweep, as a fraction


def sweep(device, freqs, amp1, amp2, rng, cycles, max_window, settle):
    """One sweep with the two generators at the given amplitudes.

    Both stay enabled throughout. W2 is slaved to W1 so they hold phase across
    the sweep -- out of phase they would partially cancel at N1 and the
    both-driven reference would be wrong.
    """
    from pydwf import (DwfAnalogOutNode, DwfAnalogOutFunction,
                       DwfAcquisitionMode, DwfState)
    wavegen, scope = device.analogOut, device.analogIn

    wavegen.reset(-1)
    for ch, amp in ((0, amp1), (1, amp2)):
        wavegen.nodeEnableSet(ch, DwfAnalogOutNode.Carrier, True)
        wavegen.nodeFunctionSet(ch, DwfAnalogOutNode.Carrier,
                                DwfAnalogOutFunction.Sine)
        wavegen.nodeAmplitudeSet(ch, DwfAnalogOutNode.Carrier, amp)
        wavegen.nodeOffsetSet(ch, DwfAnalogOutNode.Carrier, 0.0)
        wavegen.nodePhaseSet(ch, DwfAnalogOutNode.Carrier, 0.0)
    wavegen.masterSet(1, 0)

    scope.reset()
    for ch in (0, 1):
        scope.channelEnableSet(ch, True)
        scope.channelOffsetSet(ch, 0.0)
        scope.channelRangeSet(ch, rng)
    scope.acquisitionModeSet(DwfAcquisitionMode.Single)
    limit = 0.45 * float(scope.channelRangeGet(0))

    rows, clipped = [], 0
    for hz in freqs:
        for ch in (0, 1):
            wavegen.nodeFrequencySet(ch, DwfAnalogOutNode.Carrier, float(hz))
        wavegen.configure(0, True)
        wavegen.configure(1, True)

        window = min(max(cycles / hz, 0.02), max_window)
        fs = BUFFER / window
        scope.frequencySet(fs)
        scope.bufferSizeSet(BUFFER)
        scope.configure(True, True)
        time.sleep(settle + window * 0.1)
        while scope.status(True) != DwfState.Done:
            time.sleep(0.002)
        ch1 = np.array(scope.statusData(0, BUFFER))
        ch2 = np.array(scope.statusData(1, BUFFER))

        if max(float(np.max(np.abs(ch1 - ch1.mean()))),
               float(np.max(np.abs(ch2 - ch2.mean())))) > limit:
            clipped += 1
        rows.append(dict(hz=float(hz),
                         v1=abs(phasor(ch1, fs, float(hz))),
                         v2=abs(phasor(ch2, fs, float(hz)))))
    for ch in (0, 1):
        wavegen.configure(ch, False)
    return rows, clipped


def fake(freqs, c1, c2, amp, which, floating, seed):
    """Synthesise a sweep: 'both', 'left' or 'right'."""
    rng = np.random.default_rng(seed)
    both = np.abs(m.response(freqs, c1, c2)) * amp
    if which == "both":
        v2, v1 = both, np.full(len(freqs), amp)
    else:
        ratio = m.mono_sum_ratio(freqs, c1, c2, grounded=not floating)
        v2 = both / (10 ** (np.asarray(ratio) / 20))
        v1 = np.full(len(freqs), amp if which == "left" else amp * 0.004)
    n = rng.normal(1, 0.0015, len(freqs))
    return [dict(hz=float(f), v1=float(a), v2=float(b * g))
            for f, a, b, g in zip(freqs, v1, v2, n)], 0


def ratio_db(one, both):
    o = np.array([r["v2"] for r in one])
    b = np.array([r["v2"] for r in both])
    with np.errstate(divide="ignore", invalid="ignore"):
        return 20 * np.log10(np.where(b > 0, o / b, np.nan))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--detent", type=int, default=2, choices=(1, 2, 3))
    ap.add_argument("--start", type=float, default=15.0)
    ap.add_argument("--stop", type=float, default=2000.0)
    ap.add_argument("--steps", type=int, default=50)
    ap.add_argument("--amp", type=float, default=1.0)
    ap.add_argument("--range", type=float, default=2.0)
    ap.add_argument("--cycles", type=float, default=16.0)
    ap.add_argument("--max-window", type=float, default=1.0)
    ap.add_argument("--settle", type=float, default=0.05)
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--dry-run-floating", action="store_true",
                    help="synthesise a FLOATING idle input, to test the check")
    a = ap.parse_args()

    dry = a.dry_run or a.dry_run_floating
    n, label, c1, c2, _ = next(d for d in DETENTS if d[0] == a.detent)
    freqs = np.logspace(math.log10(a.start), math.log10(a.stop), a.steps)
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"\nGate 6, rev B -- mono sum at detent {n} ({label})")
    print(f"{a.start:.0f} Hz to {a.stop:.0f} Hz, {a.steps} steps, "
          f"{a.amp:.1f} V drive")
    if a.dry_run_floating:
        print("DRY RUN: synthesising a FLOATING idle input -- expect a FAIL.\n")
    elif a.dry_run:
        print("DRY RUN: synthesising a healthy board.\n")
    else:
        print("W1 -> J1.1, W2 -> J2.1. Idle input grounded in software, so")
        print("nothing is rewired between the three sweeps.\n")

    device = ctx = None
    if not dry:
        try:
            from pydwf import DwfLibrary
            from pydwf.utilities import openDwfDevice
        except ImportError:
            sys.exit(pydwf_help())
        print(f"  set the rotary to detent {n} ({label})")
        try:
            input("  press Enter to run all three sweeps ")
        except (EOFError, KeyboardInterrupt):
            return 1
        ctx = openDwfDevice(DwfLibrary())
        device = ctx.__enter__()

    plan = [("both", a.amp, a.amp), ("left", a.amp, 0.0), ("right", 0.0, a.amp)]
    got = {}
    try:
        for i, (which, w1, w2) in enumerate(plan):
            desc = {"both": "both inputs driven",
                    "left": "L driven, R grounded",
                    "right": "R driven, L grounded"}[which]
            print(f"  sweep {i + 1}/3  {desc:24s} W1={w1:.1f} W2={w2:.1f}")
            if dry:
                rows, clip = fake(freqs, c1, c2, a.amp, which,
                                  a.dry_run_floating, seed=200 + i)
            else:
                rows, clip = sweep(device, freqs, w1, w2, a.range, a.cycles,
                                   a.max_window, a.settle)
            if clip:
                print(f"    !! {clip} points near full scale -- raise --range")
            got[which] = rows
            with (outdir / f"gate6_{which}.csv").open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=["hz", "v1", "v2"])
                w.writeheader()
                w.writerows(rows)
    finally:
        if ctx is not None:
            ctx.__exit__(None, None, None)

    f = np.array([r["hz"] for r in got["both"]])
    band = (f >= BAND[0]) & (f <= BAND[1])
    rL, rR = ratio_db(got["left"], got["both"]), ratio_db(got["right"], got["both"])

    fails = []
    print(f"\n  {'':26s} {'L only':>9s} {'R only':>9s} {'want':>9s}")
    print("  " + "-" * 56)
    mL, mR = float(np.nanmean(rL[band])), float(np.nanmean(rR[band]))
    print(f"  {'mean ratio, 15-400 Hz':26s} {mL:+9.2f} {mR:+9.2f} {IDEAL:+9.2f}")
    devL = float(np.nanmax(np.abs(rL[band] - mL)))
    devR = float(np.nanmax(np.abs(rR[band] - mR)))
    print(f"  {'worst deviation from flat':26s} {devL:9.2f} {devR:9.2f} "
          f"{TOL_FLAT:9.2f}")
    print(f"  {'channel balance, L - R':26s} {mL - mR:+9.2f} {'':>9s} "
          f"{TOL_BALANCE:+9.2f}")

    for nm, mean, dev in (("L", mL, devL), ("R", mR, devR)):
        if abs(mean - IDEAL) > TOL_LEVEL:
            fails.append(f"{nm} ratio {mean:+.2f} dB, want {IDEAL:+.2f}")
        if dev > TOL_FLAT:
            fails.append(f"{nm} ratio tilts {dev:.2f} dB across the band")
    if abs(mL - mR) > TOL_BALANCE:
        fails.append(f"channels differ by {abs(mL - mR):.2f} dB -- "
                     f"R1_1/R1_2 mismatch or a cold joint")

    # Which hypothesis does the data actually match?
    pg = np.asarray(m.mono_sum_ratio(f[band], c1, c2, grounded=True)) * -1
    pf = np.asarray(m.mono_sum_ratio(f[band], c1, c2, grounded=False)) * -1
    for nm, r in (("L", rL), ("R", rR)):
        eg = float(np.sqrt(np.nanmean((r[band] - pg) ** 2)))
        ef = float(np.sqrt(np.nanmean((r[band] - pf) ** 2)))
        verdict = "grounded" if eg < ef else "FLOATING"
        print(f"  {nm} matches the {verdict} model  "
              f"(rms {min(eg, ef):.2f} dB vs {max(eg, ef):.2f} for the other)")
        if ef < eg:
            fails.append(f"{nm} sweep matches the FLOATING model -- the idle "
                         f"input is not grounded, this is not a board fault")

    v1b = np.array([r["v1"] for r in got["both"]])
    v1r = np.array([r["v1"] for r in got["right"]])
    leak = float(np.nanmedian(v1r) / np.nanmedian(v1b)) if np.nanmedian(v1b) else 1
    print(f"\n  ch1 on the L-grounded sweep: {leak:.1%} of the drive "
          f"(want < {DRIVE_LEAK:.0%})")
    if leak > DRIVE_LEAK:
        fails.append(f"W1 is not pulling J1.1 down -- {leak:.1%} of the drive "
                     f"is still there, so 'grounded' is not grounded")

    print()
    if fails:
        print("GATE 6 FAILS:")
        for why in fails:
            print(f"  - {why}")
    else:
        print(f"GATE 6 PASSES -- both legs at {IDEAL:+.2f} dB, flat, matched "
              f"to {abs(mL - mR):.2f} dB.")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
