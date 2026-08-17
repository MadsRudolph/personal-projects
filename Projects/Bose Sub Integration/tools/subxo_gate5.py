#!/usr/bin/env python3
"""Gate 5 for rev B: sweep all three rotary detents, hands-off between them.

Rev A's Gate 5 meant nine sweeps exported from WaveForms one at a time and fed
to ``subxo_compare.py`` by hand. The rotary reduces that to three settings, and
this drives the AD3 directly so the only manual step left is turning the knob.

Per detent it sweeps, extracts the corner and the 63 Hz level, scores them
against ``subxo_model``, writes a CSV, and prints a verdict. Then it waits for
you to click round one detent and does it again.

    python subxo_gate5.py                     # all three, prompting between
    python subxo_gate5.py --detents 1 3       # just those two
    python subxo_gate5.py --dry-run           # no hardware: exercise the maths

Rig -- identical to rev A's so the numbers stay comparable:

    W1  (yellow)     --- J1.1 AND J2.1      both inputs driven together
    GND (black)      --- J1.2, and AD3 GND
    1+  (orange)     --- J1.1               reference, taken AT the board
    1-  (orange/wht) --- J1.2
    2+  (blue)       --- J5.1  (OUT1)
    2-  (blue/wht)   --- JP2 even pin (VGND)   DIFFERENTIAL, not to ground

Channel 2 must reference VGND. OUT1 sits at 6 V DC and the AD3 has no AC
coupling, so referencing it to ground needs the +/-25 V range and throws away
about 20 dB of stopband resolution.

The AD3 cannot power this board -- its supplies are +/-5 V and the LM7812 needs
14 V in. Korad at 15.0 V.
Needs pydwf, which lives in the Python 3.14 install -- run this with
``python``, not ``py -3.13``. The pure-maths tools (subxo_model,
subxo_compare, plot_*) run under either.
"""

import argparse
import csv
import math
import sys
import time
from pathlib import Path

import numpy as np

import subxo_model as m
from subxo_compare import measured_corner, REF_HZ, SHAPE_LO, SHAPE_HI, SHAPE_TOL

BUFFER = 16384

# (detent, label, C1, C2, c1_is_unverified)
# C1_2/C1_3 and all three C2 come from rev A's five-parameter fit, residual
# 0.96 sigma. C1_1 is a new part nobody has measured, so detent 1 is scored
# against a +/-10% band instead of a point.
DETENTS = [
    (1, "470n / 150n", 470.0e-9, 150.7e-9, True),
    (2, "150n / 120n", 143.2e-9, 121.2e-9, False),
    (3, "220n / 68n", 221.7e-9, 63.8e-9, False),
]
C1_1_TOL = 0.10


def phasor(x, fs, f0):
    """Complex amplitude at f0 by windowed single-bin DFT."""
    x = np.asarray(x, float)
    x = x - x.mean()
    t = np.arange(len(x)) / fs
    w = np.hanning(len(x))
    return np.sum(x * w * np.exp(-2j * np.pi * f0 * t)) / np.sum(w) * 2


def sweep(device, freqs, amp, rng, cycles, max_window, settle):
    from pydwf import (DwfAnalogOutNode, DwfAnalogOutFunction,
                       DwfAcquisitionMode, DwfState)
    wavegen, scope = device.analogOut, device.analogIn

    wavegen.reset(-1)
    wavegen.nodeEnableSet(0, DwfAnalogOutNode.Carrier, True)
    wavegen.nodeFunctionSet(0, DwfAnalogOutNode.Carrier, DwfAnalogOutFunction.Sine)
    wavegen.nodeAmplitudeSet(0, DwfAnalogOutNode.Carrier, amp)
    wavegen.nodeOffsetSet(0, DwfAnalogOutNode.Carrier, 0.0)

    scope.reset()
    for ch in (0, 1):
        scope.channelEnableSet(ch, True)
        scope.channelOffsetSet(ch, 0.0)
        scope.channelRangeSet(ch, rng)
    scope.acquisitionModeSet(DwfAcquisitionMode.Single)

    rows, clipped = [], 0
    for hz in freqs:
        wavegen.nodeFrequencySet(0, DwfAnalogOutNode.Carrier, float(hz))
        wavegen.configure(0, True)

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

        if max(np.ptp(ch1), np.ptp(ch2)) > 0.9 * rng:
            clipped += 1

        v1, v2 = phasor(ch1, fs, float(hz)), phasor(ch2, fs, float(hz))
        h = v2 / v1 if abs(v1) > 1e-9 else complex(0)
        rows.append(dict(hz=float(hz),
                         mag_db=20 * math.log10(abs(h)) if abs(h) > 0 else -200.0,
                         phase=math.degrees(np.angle(h)),
                         v1=abs(v1), v2=abs(v2)))
    wavegen.configure(0, False)
    return rows, clipped


def fake_sweep(freqs, c1, c2, seed):
    """A measurement that never happened, for exercising the analysis path."""
    rng = np.random.default_rng(seed)
    h = m.response(freqs, c1, c2)
    mag = m.db(h) + rng.normal(0, 0.01, len(freqs))
    ph = np.degrees(np.angle(h))
    return [dict(hz=float(f), mag_db=float(mm), phase=float(pp), v1=1.0,
                 v2=float(10 ** (mm / 20)))
            for f, mm, pp in zip(freqs, mag, ph)], 0


def solve_c1(target_hz, c2, lo=100e-9, hi=2000e-9):
    """What C1 would put the corner exactly at target_hz? Bisection."""
    if m.corner(lo, c2)[0] < target_hz or m.corner(hi, c2)[0] > target_hz:
        return None
    for _ in range(60):
        mid = math.sqrt(lo * hi)
        if m.corner(mid, c2)[0] > target_hz:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)


def score(detent, label, c1, c2, unverified, rows):
    f = np.array([r["hz"] for r in rows])
    mag = np.array([r["mag_db"] for r in rows])

    f3_pred, g63_pred = m.corner(c1, c2)
    f3_meas, g63_meas = measured_corner(f, mag)

    if unverified:
        lo = m.corner(c1 * (1 + C1_1_TOL), c2)[0]
        hi = m.corner(c1 * (1 - C1_1_TOL), c2)[0]
        band_why = f"C1_1 unmeasured, +/-{C1_1_TOL:.0%}"
    else:
        lo, hi = m.tolerance_band(c1, c2)
        band_why = "part tolerances"

    print(f"\n  detent {detent}  ({label})")
    print(f"  {'':24s} {'measured':>10s} {'model':>10s}")
    print(f"  {'-' * 46}")
    print(f"  {'gain at 63 Hz':24s} {g63_meas:+9.2f}  {g63_pred:+9.2f}")
    if f3_meas is None:
        print(f"  {'corner':24s} {'not reached':>10s}  {f3_pred:9.1f}")
    else:
        print(f"  {'corner (63 Hz -3 dB)':24s} {f3_meas:9.1f}  {f3_pred:9.1f}")
    print(f"  {'accept band':24s} {lo:6.1f} - {hi:.1f} Hz   ({band_why})")

    fails = []
    if f3_meas is None:
        fails.append("the curve never falls 3 dB below its 63 Hz level")
    elif not lo <= f3_meas <= hi:
        fails.append(f"corner {f3_meas:.1f} Hz outside {lo:.1f}-{hi:.1f} Hz")

    band = (f >= SHAPE_LO) & (f <= SHAPE_HI)
    if band.sum() >= 5:
        model = m.db(m.response(f[band], c1, c2))
        err = (mag[band] - g63_meas) - (model - g63_pred)
        worst = float(np.abs(err).max())
        fw = float(f[band][np.argmax(np.abs(err))])
        print(f"  {'shape 30-400 Hz':24s} worst {worst:+.2f} dB at {fw:.0f} Hz")
        if worst > SHAPE_TOL:
            fails.append(f"shape off by {worst:.2f} dB at {fw:.0f} Hz")

    if f[-1] >= 800:
        oct_meas = float(np.interp(800.0, f, mag) - np.interp(400.0, f, mag))
        oct_pred = m.db(m.response(800.0, c1, c2) / m.response(400.0, c1, c2))
        print(f"  {'octave 400->800 Hz':24s} {oct_meas:+9.2f}  {oct_pred:+9.2f}")
        if abs(oct_meas - oct_pred) > 1.5:
            fails.append(f"octave {oct_meas:+.2f} dB vs {oct_pred:+.2f} expected")

    if unverified and f3_meas:
        got = solve_c1(f3_meas, c2)
        if got:
            dev = (got - c1) / c1
            print(f"  {'C1_1 implied by corner':24s} {got * 1e9:9.1f} nF "
                  f"({dev:+.1%} on 470n)")

    print(f"  -> {'PASS' if not fails else 'FAIL'}")
    for why in fails:
        print(f"       {why}")
    return dict(detent=detent, label=label, f3=f3_meas, g63=g63_meas,
                f3_pred=f3_pred, g63_pred=g63_pred, lo=lo, hi=hi,
                ok=not fails, fails=fails)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--detents", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--start", type=float, default=15.0)
    ap.add_argument("--stop", type=float, default=2000.0)
    ap.add_argument("--steps", type=int, default=70)
    ap.add_argument("--amp", type=float, default=1.0, help="volts amplitude")
    ap.add_argument("--range", type=float, default=2.0, help="scope range, V")
    ap.add_argument("--cycles", type=float, default=16.0)
    ap.add_argument("--max-window", type=float, default=1.0)
    ap.add_argument("--settle", type=float, default=0.05)
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--dry-run", action="store_true",
                    help="synthesise from the model, no AD3 needed")
    a = ap.parse_args()

    freqs = np.logspace(math.log10(a.start), math.log10(a.stop), a.steps)
    todo = [d for d in DETENTS if d[0] in a.detents]
    if not todo:
        sys.exit(f"no detents matching {a.detents}")
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"\nGate 5, rev B -- {len(todo)} detent(s), "
          f"{a.start:.0f} Hz to {a.stop:.0f} Hz, {a.steps} steps, "
          f"{a.amp:.1f} V drive")
    if a.dry_run:
        print("DRY RUN: curves come from the model, not the board.\n")
    else:
        print("Korad at 15.0 V. Channel 2 differential OUT1 -> VGND.\n")

    device = None
    if not a.dry_run:
        from pydwf import DwfLibrary
        from pydwf.utilities import openDwfDevice
        ctx = openDwfDevice(DwfLibrary())
        device = ctx.__enter__()

    results = []
    try:
        for i, (n, label, c1, c2, unverified) in enumerate(todo):
            print("=" * 58)
            print(f"  Set the rotary to DETENT {n}   ({label})")
            if unverified:
                print("  This is the 470n position -- C1_1's first measurement.")
            print("=" * 58)
            if not a.dry_run:
                try:
                    input("  press Enter when the knob is there (Ctrl-C to stop) ")
                except (EOFError, KeyboardInterrupt):
                    print("\n  stopped.")
                    break

            if a.dry_run:
                rows, clipped = fake_sweep(freqs, c1, c2, seed=100 + n)
            else:
                rows, clipped = sweep(device, freqs, a.amp, a.range,
                                      a.cycles, a.max_window, a.settle)
            if clipped:
                print(f"  !! {clipped} points near full scale -- raise --range")

            out = outdir / f"gate5_detent{n}.csv"
            with out.open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=["hz", "mag_db", "phase",
                                                   "v1", "v2"])
                w.writeheader()
                w.writerows(rows)

            results.append(score(n, label, c1, c2, unverified, rows))
            print(f"  wrote {out}")
            if i < len(todo) - 1:
                print()
    finally:
        if device is not None:
            ctx.__exit__(None, None, None)

    if not results:
        return 1
    print("\n" + "=" * 58)
    print("Gate 5 summary")
    print(f"{'detent':>7} {'setting':>14} {'corner':>9} {'expected':>9} "
          f"{'g(63)':>8} {'':>6}")
    print("-" * 58)
    for r in results:
        f3 = f"{r['f3']:.1f}" if r["f3"] else "none"
        print(f"{r['detent']:>7} {r['label']:>14} {f3:>9} "
              f"{r['f3_pred']:>9.1f} {r['g63']:>+8.2f} "
              f"{'PASS' if r['ok'] else 'FAIL':>6}")
    bad = [r for r in results if not r["ok"]]
    print()
    if bad:
        print(f"GATE 5 FAILS on {len(bad)} of {len(results)} detents.")
    elif len(results) == 3:
        print("GATE 5 PASSES -- all three detents.")
    else:
        print(f"{len(results)} of 3 detents pass. Run the rest for a full gate.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
