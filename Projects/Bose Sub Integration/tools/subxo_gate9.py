#!/usr/bin/env python3
"""Gate 9 for rev B: headroom. How hard can this board be driven before it bends?

The board runs off a single 12 V rail with the signal sitting on a 6 V virtual
ground, so a TL074 has about +/-4.5 V typical to play with and only +/-3 V
guaranteed. At 40 Hz the passband gain is roughly -1 to -3.3 dB depending on
detent, so W1 at its 5 V maximum puts something near 3.5 V peak at OUT1 --
right at the edge. Either answer is a pass; the point is to know the number,
because the Saga in active mode has gain and this board does not.

Drive 40 Hz and walk the amplitude up, watching two things: the gain, which
should stay flat until it does not, and the harmonics, which climb out of the
floor as soon as the output starts to flatten.

    python subxo_gate9.py
    python subxo_gate9.py --hz 40 --detent 3     # widest setting, most output
    python subxo_gate9.py --dry-run              # a board that clips at 3.4 V
    python subxo_gate9.py --dry-run-clean        # one the AD3 cannot overdrive

Rig -- the Gate 6/7 one, with the input shorts removed:

    W1 --- J1.1,  W2 --- J2.1,  GND --- J1.2 and AD3 GND
    1+ --- J1.1,  1- --- J1.2
    2+ --- J5.1  (OUT1)
    2- --- JP2 even pin (VGND)     DIFFERENTIAL, never to ground

The scope auto-ranges: the output can reach 3.5 V peak, which does not fit the
+/-2.5 V range the earlier gates used.

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

RANGES = (5.0, 50.0)         # AD3 spans: +/-2.5 V and +/-25 V
HARMONICS = (2, 3, 4, 5)
TOL_COMPRESS = 0.5           # dB of gain droop that counts as clipping
TOL_THD = 0.01               # 1%
CYCLES = 64


def analyse(x, fs, hz):
    """Fundamental amplitude and THD from one capture."""
    fund = abs(phasor(x, fs, hz))
    harm = [abs(phasor(x, fs, hz * k)) for k in HARMONICS]
    thd = math.sqrt(sum(h * h for h in harm)) / fund if fund > 1e-9 else 0.0
    return fund, thd, harm


def step(device, hz, amp, rng_hint):
    from pydwf import (DwfAnalogOutNode, DwfAnalogOutFunction,
                       DwfAcquisitionMode, DwfState)
    wavegen, scope = device.analogOut, device.analogIn
    wavegen.reset(-1)
    for ch in (0, 1):
        wavegen.nodeEnableSet(ch, DwfAnalogOutNode.Carrier, True)
        wavegen.nodeFunctionSet(ch, DwfAnalogOutNode.Carrier,
                                DwfAnalogOutFunction.Sine)
        wavegen.nodeAmplitudeSet(ch, DwfAnalogOutNode.Carrier, amp)
        wavegen.nodeOffsetSet(ch, DwfAnalogOutNode.Carrier, 0.0)
        wavegen.nodePhaseSet(ch, DwfAnalogOutNode.Carrier, 0.0)
        wavegen.nodeFrequencySet(ch, DwfAnalogOutNode.Carrier, hz)
    wavegen.masterSet(1, 0)
    wavegen.configure(0, True)
    wavegen.configure(1, True)

    window = CYCLES / hz
    fs = BUFFER / window
    scope.reset()
    for ch in (0, 1):
        scope.channelEnableSet(ch, True)
        scope.channelOffsetSet(ch, 0.0)
    scope.acquisitionModeSet(DwfAcquisitionMode.Single)
    scope.frequencySet(fs)
    scope.bufferSizeSet(BUFFER)

    for rng in [r for r in RANGES if r >= rng_hint]:
        scope.channelRangeSet(0, RANGES[-1] if amp > 2.0 else RANGES[0])
        scope.channelRangeSet(1, rng)
        scope.configure(True, True)
        time.sleep(0.08 + window * 0.1)
        while scope.status(True) != DwfState.Done:
            time.sleep(0.002)
        ch1 = np.array(scope.statusData(0, BUFFER))
        ch2 = np.array(scope.statusData(1, BUFFER))
        peak = float(np.max(np.abs(ch2 - ch2.mean())))
        if peak < 0.45 * rng or rng == RANGES[-1]:
            for c in (0, 1):
                wavegen.configure(c, False)
            return ch1, ch2, fs, rng, peak
    raise RuntimeError("unreachable")


def fake(hz, amp, clip_at, seed, gain_db):
    """A board that soft-clips once the output passes clip_at volts peak."""
    rng = np.random.default_rng(seed)
    fs = BUFFER / (CYCLES / hz)
    t = np.arange(BUFFER) / fs
    drive = amp * np.sin(2 * np.pi * hz * t)
    # The AD3's generator is not clean either -- about 0.1% second harmonic,
    # which a linear filter passes straight through. Synthesising it here means
    # the dry run shows the same instrument floor a real run does.
    drive = drive + 0.001 * amp * np.sin(2 * np.pi * 2 * hz * t)
    want = drive * 10 ** (gain_db / 20)            # this detent's passband gain
    out = clip_at * np.tanh(want / clip_at) if clip_at else want
    out += rng.normal(0, 60e-6, BUFFER)
    return drive, out, fs, 50.0, float(np.max(np.abs(out)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--detent", type=int, default=2, choices=(1, 2, 3))
    ap.add_argument("--hz", type=float, default=40.0)
    ap.add_argument("--amps", type=float, nargs="+",
                    default=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0])
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--dry-run-clean", action="store_true",
                    help="synthesise a board the AD3 cannot overdrive")
    a = ap.parse_args()

    dry = a.dry_run or a.dry_run_clean
    n, label, c1, c2, _ = next(d for d in DETENTS if d[0] == a.detent)
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"\nGate 9, rev B -- headroom at {a.hz:.0f} Hz, detent {n} ({label})")
    if a.dry_run_clean:
        print("DRY RUN: a board that never clips.\n")
    elif dry:
        print("DRY RUN: a board that soft-clips at 3.4 V peak.\n")
    else:
        print("W1 and W2 on J1.1 and J2.1. Remove the Gate 8 input shorts.")
        print("2+ on J5.1, 2- on a JP2 even pin. Scope auto-ranges.\n")

    device = ctx = None
    if not dry:
        try:
            from pydwf import DwfLibrary
            from pydwf.utilities import openDwfDevice
        except ImportError:
            sys.exit(pydwf_help())
        try:
            input("  press Enter to sweep the amplitude ")
        except (EOFError, KeyboardInterrupt):
            return 1
        ctx = openDwfDevice(DwfLibrary())
        device = ctx.__enter__()

    rows, hint = [], RANGES[0]
    try:
        # Input THD is shown beside output THD because the AD3's own generator
        # has distortion of its own, and a linear filter passes it straight
        # through. Without the input column a floor that belongs to the
        # instrument reads as if it belonged to the board. h2 and h3 are split
        # out because they say different things: h3 with fundamental droop is
        # symmetric clipping, h2 alone is one rail being approached -- which is
        # what a single-supply board does first.
        print(f"  {'W1 V':>6} {'in V':>8} {'out Vpk':>9} {'gain dB':>9} "
              f"{'THDin %':>8} {'THD %':>8} {'h2 %':>7} {'h3 %':>7} "
              f"{'range':>6}")
        print("  " + "-" * 76)
        for amp in a.amps:
            if dry:
                ch1, ch2, fs, rng, peak = fake(
                    a.hz, amp, None if a.dry_run_clean else 3.4, seed=900,
                    gain_db=float(m.db(m.response(a.hz, c1, c2))))
            else:
                ch1, ch2, fs, rng, peak = step(device, a.hz, amp, hint)
                hint = rng
            vin, thd_in, _ = analyse(ch1, fs, a.hz)
            vout, thd, harm = analyse(ch2, fs, a.hz)
            gain = 20 * math.log10(vout / vin) if vin > 1e-9 else float("nan")
            h2, h3 = (harm[0] / vout, harm[1] / vout) if vout > 1e-9 else (0, 0)
            rows.append(dict(amp=amp, vin=vin, vout=vout, gain=gain,
                             thd_in=thd_in, thd=thd, h2=h2, h3=h3,
                             peak=peak, rng=rng))
            print(f"  {amp:6.2f} {vin:8.3f} {vout:9.3f} {gain:+9.2f} "
                  f"{thd_in * 100:8.3f} {thd * 100:8.3f} "
                  f"{h2 * 100:7.3f} {h3 * 100:7.3f} {rng:6.0f}")
    finally:
        if ctx is not None:
            ctx.__exit__(None, None, None)

    with (outdir / "gate9_headroom.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["amp", "vin", "vout", "gain",
                                           "thd_in", "thd", "h2", "h3",
                                           "peak", "rng"])
        w.writeheader()
        w.writerows(rows)

    # Small-signal gain from the lowest two drives, where nothing can be bending.
    ref = float(np.mean([r["gain"] for r in rows[:2]]))
    clip = next((r for r in rows
                 if r["gain"] < ref - TOL_COMPRESS or r["thd"] > TOL_THD), None)

    floor = float(np.median([r["thd"] for r in rows]))
    floor_in = float(np.median([r["thd_in"] for r in rows]))
    print(f"\n  small-signal gain      {ref:+.2f} dB")
    print(f"  largest output         {max(r['vout'] for r in rows):.3f} V peak")
    print(f"  THD floor, in / out    {floor_in * 100:.3f} / {floor * 100:.3f} %")
    print(f"  worst THD              {max(r['thd'] for r in rows) * 100:.3f} %")
    if floor_in > 0.5 * floor:
        print(f"    -- the floor is the generator, not the board: the input is "
              f"already at {floor_in * 100:.3f} %")

    # The script cannot see the knob, so it infers which detent was really
    # selected by scoring the small-signal gain against the model. Getting this
    # wrong is silent otherwise, and it matters here: the detents differ by over
    # a dB of passband gain, so the loudest one is the one that clips first.
    guess = min(DETENTS, key=lambda d: abs(
        float(m.db(m.response(a.hz, d[2], d[3]))) - ref))
    if guess[0] != n:
        want = float(m.db(m.response(a.hz, c1, c2)))
        print(f"\n  !! WRONG DETENT. {ref:+.2f} dB at {a.hz:.0f} Hz is detent "
              f"{guess[0]} ({guess[1]}); detent {n} would read "
              f"{want:+.2f} dB.")
        print(f"     The knob was not on {n}. Turn it and run again -- these "
              f"numbers describe detent {guess[0]}.")

    if clip is None:
        top = rows[-1]
        print(f"\nGATE 9 PASSES -- no clipping at W1 = {top['amp']:.1f} V.")
        print(f"  The AD3 cannot overdrive this board: {top['vout']:.2f} V peak "
              f"out at {top['thd'] * 100:.2f} % THD.")
        print(f"  Headroom is therefore at least {top['vin'] / math.sqrt(2):.2f} "
              f"V rms in, which the Saga will not reach.")
    else:
        print(f"\nGATE 9 PASSES -- clips at W1 = {clip['amp']:.2f} V "
              f"({clip['vout']:.2f} V peak out, {clip['thd'] * 100:.2f} % THD).")
        print(f"  Maximum input is {clip['vin'] / math.sqrt(2):.2f} V rms. "
              f"Compare that against the Saga's real output before")
        print(f"  deciding whether it matters -- in active mode it has gain.")
    print("\n  Either outcome is a pass. The number is the point.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
