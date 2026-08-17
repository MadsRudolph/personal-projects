#!/usr/bin/env python3
"""Gate 10 for rev B: the output chain. Deferred since bring-up; the pot exists now.

Everything after OUT1 -- the changeover, the 10 uF coupling cap, the 10k pot and
the two 100 ohm build-out resistors into the jack. Rev A could never run this
because the pot had not been bought, which is why the gate has sat empty in the
results log since August.

Three things get checked:

  * the pot at maximum against OUT1. C_out into 10k puts a high-pass at 1.6 Hz,
    so expect about -0.03 dB at 20 Hz and nothing at all above 60.
  * tip against ring. R5 and R6 are both 100 ohm, so they should match within
    0.05 dB and 0 degrees.
  * DC at tip and ring, which must be 0.00 V. Any DC there thumps the driver at
    power-on, and C_out is the only thing standing between 6 V and the jack.

    python subxo_gate10.py
    python subxo_gate10.py --dry-run
    python subxo_gate10.py --dry-run-dc      # a leaky C_out, to test the check

The 3.5 mm jack does NOT need to be fitted. J3 is a screw terminal -- clip
straight onto it.

    1  2+ on J5.1 (OUT1),  2- on JP2 even pin      reference
    2  2+ on J3.1 (tip),   2- on J3.3 (OUT_GND)    pot at MAXIMUM
    3  2+ on J3.2 (ring),  2- on J3.3

W1 and W2 stay on J1.1 and J2.1, 1+ and 1- on J1.1 and J1.2, as before.

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

from subxo_gate5 import BUFFER, DETENTS, pydwf_help
from subxo_gate6 import sweep
from subxo_gate7 import wrap180

TOL_TIPRING_MAG = 0.05       # dB, R5 and R6 are both 100R
TOL_TIPRING_PH = 0.5         # degrees, judged against the rig's own null
TOL_DC = 0.010               # volts at the jack
BAND = (15.0, 200.0)
LF_HZ = 20.0                 # where C_out's high-pass is just visible

STEPS = [
    ("out1", "2+ on J5.1 (OUT1),  2- on JP2 even pin"),
    ("tip", "2+ on J3.1 (tip),   2- on J3.3 (OUT_GND),  POT AT MAXIMUM"),
    ("ring", "2+ on J3.2 (ring),  2- on J3.3 (OUT_GND)"),
]


def read_dc(device, seconds=0.25):
    """Mean of channel 2 with both generators off -- the DC at the probe."""
    from pydwf import DwfAcquisitionMode, DwfState
    scope = device.analogIn
    device.analogOut.reset(-1)
    scope.reset()
    scope.channelEnableSet(0, False)
    scope.channelEnableSet(1, True)
    scope.channelOffsetSet(1, 0.0)
    scope.channelRangeSet(1, 5.0)
    scope.acquisitionModeSet(DwfAcquisitionMode.Single)
    fs = BUFFER / seconds
    scope.frequencySet(fs)
    scope.bufferSizeSet(BUFFER)
    scope.configure(True, True)
    time.sleep(seconds * 0.2)
    while scope.status(True) != DwfState.Done:
        time.sleep(0.002)
    return float(np.mean(np.array(scope.statusData(1, BUFFER))))


def fake(freqs, which, leaky, seed):
    rng = np.random.default_rng(seed)
    f = np.asarray(freqs)
    if which == "out1":
        mag = np.zeros(len(f))
    else:
        # C_out 10 uF into the 10k pot: a high-pass at 1.59 Hz.
        s = 1j * 2 * np.pi * f
        h = s * 10e-6 * 10e3 / (1 + s * 10e-6 * 10e3)
        mag = 20 * np.log10(np.abs(h))
    mag = mag + rng.normal(0, 0.004, len(f))
    ph = np.zeros(len(f)) + rng.normal(0, 0.05, len(f))
    dc = 0.35 if (leaky and which != "out1") else 0.0008
    return ([dict(hz=float(a), v1=1.0, v2=1.0, mag_db=float(b), phase=float(c))
             for a, b, c in zip(f, mag, ph)], 0), dc


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--detent", type=int, default=2, choices=(1, 2, 3))
    ap.add_argument("--start", type=float, default=15.0)
    ap.add_argument("--stop", type=float, default=2000.0)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--amp", type=float, default=1.0)
    ap.add_argument("--range", type=float, default=2.0)
    ap.add_argument("--cycles", type=float, default=128.0)
    ap.add_argument("--max-window", type=float, default=1.0)
    ap.add_argument("--settle", type=float, default=0.05)
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--dry-run-dc", action="store_true",
                    help="synthesise DC at the jack, to test that check")
    a = ap.parse_args()

    dry = a.dry_run or a.dry_run_dc
    n, label, _c1, _c2, _ = next(d for d in DETENTS if d[0] == a.detent)
    freqs = np.logspace(math.log10(a.start), math.log10(a.stop), a.steps)
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"\nGate 10, rev B -- output chain, detent {n} ({label})")
    if a.dry_run_dc:
        print("DRY RUN: synthesising DC at the jack -- expect a FAIL.\n")
    elif dry:
        print("DRY RUN: synthesising a healthy output chain.\n")
    else:
        print("J3 is a screw terminal -- the 3.5 mm jack need not be fitted.\n")

    device = ctx = None
    if not dry:
        try:
            from pydwf import DwfLibrary
            from pydwf.utilities import openDwfDevice
        except ImportError:
            sys.exit(pydwf_help())
        ctx = openDwfDevice(DwfLibrary())
        device = ctx.__enter__()

    got, dcs = {}, {}
    try:
        for key, instruction in STEPS:
            print("=" * 62)
            print(f"  {instruction}")
            print("=" * 62)
            if dry:
                (rows, _), dc = fake(freqs, key, a.dry_run_dc, seed=1000)
            else:
                try:
                    input("  press Enter when the leads are set ")
                except (EOFError, KeyboardInterrupt):
                    print("\n  stopped.")
                    return 1
                rows, clip = sweep(device, freqs, a.amp, a.amp, a.range,
                                   a.cycles, a.max_window, a.settle)
                if clip:
                    print(f"  !! {clip} points near full scale")
                dc = read_dc(device)
                print(f"  DC at this probe: {dc * 1000:+.1f} mV")
            got[key], dcs[key] = rows, dc
            with (outdir / f"gate10_{key}.csv").open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=["hz", "v1", "v2",
                                                   "mag_db", "phase"])
                w.writeheader()
                w.writerows(rows)
    finally:
        if ctx is not None:
            ctx.__exit__(None, None, None)

    f = np.array([r["hz"] for r in got["out1"]])
    band = (f >= BAND[0]) & (f <= BAND[1])
    m = {k: np.array([r["mag_db"] for r in v]) for k, v in got.items()}
    p = {k: np.array([r["phase"] for r in v]) for k, v in got.items()}
    fails = []

    d_tip = m["tip"] - m["out1"]
    lf = float(np.interp(LF_HZ, f, d_tip))
    hf = float(np.median(d_tip[(f >= 60) & (f <= 200)]))
    print(f"\n  {'pot at max vs OUT1, 20 Hz':32s} {lf:+7.3f} dB   "
          f"want about -0.03")
    print(f"  {'pot at max vs OUT1, 60-200 Hz':32s} {hf:+7.3f} dB   want 0.00")
    if hf < -0.20 or hf > 0.10:
        fails.append(f"the output chain loses {abs(hf):.2f} dB in the passband "
                     f"-- expected nothing above 60 Hz")
    if lf > 0.02:
        fails.append(f"no high-pass visible at 20 Hz ({lf:+.3f} dB) -- C_out "
                     f"may be shorted or far larger than 10 uF")

    d_mag = m["ring"] - m["tip"]
    d_ph = wrap180(p["ring"] - p["tip"])
    mm, pm = float(np.median(d_mag[band])), float(np.median(d_ph[band]))
    print(f"  {'ring vs tip':32s} {mm:+7.3f} dB  {pm:+6.2f} deg   "
          f"want 0.00 / 0.0")
    if abs(mm) > TOL_TIPRING_MAG:
        fails.append(f"tip and ring differ by {mm:+.3f} dB -- R5 or R6 is off "
                     f"value, or one has a cold joint")
    if abs(pm) > TOL_TIPRING_PH:
        fails.append(f"tip and ring differ by {pm:+.2f} deg")

    print()
    for k in ("tip", "ring"):
        print(f"  {'DC at ' + k:32s} {dcs[k] * 1000:+7.1f} mV   "
              f"want 0.0 +/- {TOL_DC * 1000:.0f}")
        if abs(dcs[k]) > TOL_DC:
            fails.append(f"{dcs[k] * 1000:+.0f} mV of DC at the {k} -- C_out is "
                         f"leaky or backwards. This thumps the driver at "
                         f"power-on; do not connect the module")

    print()
    if fails:
        print("GATE 10 FAILS:")
        for why in fails:
            print(f"  - {why}")
    else:
        print(f"GATE 10 PASSES -- {hf:+.3f} dB through the output chain, "
              f"tip and ring matched to {abs(mm):.3f} dB,")
        print(f"  no DC at the jack. The gate deferred since rev A is closed.")
        print("\n  One thing left, by hand: turn the pot end to end and listen")
        print("  for crackle or a dead spot. No instrument catches that.")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
