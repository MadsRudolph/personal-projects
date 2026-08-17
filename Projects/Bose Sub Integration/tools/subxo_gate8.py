#!/usr/bin/env python3
"""Gate 8 for rev B: the noise and hum floor, with the rotary loom fitted.

This is the gate rev B actually needs. Rev A never ran it, so there is no prior
number -- only the targets. And the rotary put N1 on a flying lead: about 3 kohm
to AC ground at 50 Hz, the highest-impedance conductor in the build, where it
used to be a 2.54 mm shunt. If the switch made this board worse, it shows here.

Not a sweep. The generators are switched off and the output is recorded with
nothing driving it, then averaged into a power spectrum:

  * broadband RMS, 10 Hz to 1 kHz     want < 1 mV
  * the 50 Hz line                    want < 100 uV   (Denmark is 50 Hz)
  * 100 and 150 Hz                    want below the 50 Hz line

    python subxo_gate8.py --label frame-grounded
    python subxo_gate8.py --label frame-lifted
    python subxo_gate8.py --dry-run

Run it twice, once with the rotary's frame ground connected and once with it
lifted. The difference is what shielding that switch is worth, and it decides
whether the printed enclosure needs a conductive coating.

Wiring -- the Gate 6 rig with the inputs shorted:

    J1.1 --- J1.2      short the left input
    J2.1 --- J2.2      short the right input
    2+  (blue)     --- J5.1  OUT1
    2-  (blue/wht) --- JP2 even pin (VGND)    DIFFERENTIAL, never to ground

> Short the inputs with wire, not in software. An enabled generator sitting at
> 0 V has its own noise, and this measurement is the noise. Both generators are
> disabled here so they cannot contribute.

Needs pydwf, which lives in the Python 3.14 install -- run this with
``python``, not ``py -3.13``.
"""

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

from subxo_gate5 import pydwf_help

BUFFER = 16384
FS = 16384.0                 # 1 Hz bins over a 1 s record
BAND = (10.0, 1000.0)
WANT_RMS = 1.0e-3            # volts
WANT_MAINS = 100e-6          # volts, the 50 Hz line
MAINS = 50.0


def spectrum(records, fs):
    """Averaged one-sided amplitude spectrum, in volts RMS per bin.

    Hanning window, corrected so a pure tone reads its true RMS regardless of
    where it falls between bins -- which matters because mains is never exactly
    50.000 Hz and will straddle two.
    """
    w = np.hanning(len(records[0]))
    acc = None
    for x in records:
        x = np.asarray(x, float)
        X = np.fft.rfft((x - x.mean()) * w)
        p = (np.abs(X) ** 2) * 2.0 / (np.sum(w ** 2) * fs)   # V^2/Hz
        acc = p if acc is None else acc + p
    psd = acc / len(records)
    f = np.fft.rfftfreq(len(records[0]), 1.0 / fs)
    return f, psd


def band_rms(f, psd, lo, hi):
    m = (f >= lo) & (f <= hi)
    return float(np.sqrt(np.trapezoid(psd[m], f[m])))


def line_rms(f, psd, hz, halfwidth=2.0):
    """RMS in a narrow window, so a tone straddling two bins is not halved."""
    return band_rms(f, psd, hz - halfwidth, hz + halfwidth)


def capture(device, records, fs):
    from pydwf import DwfAcquisitionMode, DwfState
    scope = device.analogIn
    device.analogOut.reset(-1)          # generators OFF; this measures noise
    scope.reset()
    scope.channelEnableSet(0, False)
    scope.channelEnableSet(1, True)
    scope.channelOffsetSet(1, 0.0)
    scope.channelRangeSet(1, 0.5)       # smallest range: best resolution
    scope.acquisitionModeSet(DwfAcquisitionMode.Single)
    scope.frequencySet(fs)
    scope.bufferSizeSet(BUFFER)
    out = []
    for _ in range(records):
        scope.configure(True, True)
        time.sleep(BUFFER / fs * 0.05)
        while scope.status(True) != DwfState.Done:
            time.sleep(0.002)
        out.append(np.array(scope.statusData(1, BUFFER)))
    return out, float(scope.channelRangeGet(1))


def fake(records, fs, seed, hum=40e-6, broadband=180e-6):
    rng = np.random.default_rng(seed)
    t = np.arange(BUFFER) / fs
    out = []
    for _ in range(records):
        x = rng.normal(0, broadband, BUFFER)
        x += hum * np.sqrt(2) * np.sin(2 * np.pi * MAINS * t + rng.uniform(0, 6))
        x += hum * 0.3 * np.sqrt(2) * np.sin(2 * np.pi * 150 * t)
        out.append(x)
    return out, 0.5


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--label", default="run",
                    help="e.g. frame-grounded / frame-lifted")
    ap.add_argument("--records", type=int, default=16,
                    help="1 s records to average")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    print(f"\nGate 8, rev B -- noise floor  [{a.label}]")
    print(f"{a.records} records of {BUFFER / FS:.1f} s at {FS:.0f} Hz, "
          f"{FS / BUFFER:.2f} Hz bins")

    if a.dry_run:
        print("DRY RUN: synthesising a quiet board.\n")
        recs, rng_used = fake(a.records, FS, seed=808)
    else:
        try:
            from pydwf import DwfLibrary
            from pydwf.utilities import openDwfDevice
        except ImportError:
            sys.exit(pydwf_help())
        print("\n  Short J1.1-J1.2 and J2.1-J2.2 with wire.")
        print("  2+ on J5.1, 2- on a JP2 even pin. Generators will be off.")
        try:
            input("  press Enter to record ")
        except (EOFError, KeyboardInterrupt):
            return 1
        with openDwfDevice(DwfLibrary()) as device:
            recs, rng_used = capture(device, a.records, FS)

    f, psd = spectrum(recs, FS)
    total = band_rms(f, psd, *BAND)
    mains = line_rms(f, psd, MAINS)
    h2 = line_rms(f, psd, 2 * MAINS)
    h3 = line_rms(f, psd, 3 * MAINS)
    peak_v = max(float(np.max(np.abs(r - r.mean()))) for r in recs)

    with (outdir / f"gate8_{a.label}.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["hz", "v_rms_per_rthz"])
        m = (f >= 5) & (f <= 2000)
        for hz, p in zip(f[m], psd[m]):
            w.writerow([f"{hz:.2f}", f"{np.sqrt(p):.4e}"])

    print(f"\n  {'':30s} {'measured':>12s} {'want':>12s}")
    print("  " + "-" * 58)
    print(f"  {'broadband RMS, 10-1000 Hz':30s} {total * 1e6:9.1f} uV "
          f"{WANT_RMS * 1e6:9.0f} uV")
    print(f"  {'50 Hz line':30s} {mains * 1e6:9.1f} uV "
          f"{WANT_MAINS * 1e6:9.0f} uV")
    print(f"  {'100 Hz':30s} {h2 * 1e6:9.1f} uV {'< 50 Hz':>12s}")
    print(f"  {'150 Hz':30s} {h3 * 1e6:9.1f} uV {'< 50 Hz':>12s}")
    print(f"  {'peak sample':30s} {peak_v * 1e3:9.2f} mV "
          f"{'(range ' + format(rng_used, '.1f') + ' V)':>12s}")

    fails = []
    if total > WANT_RMS:
        fails.append(f"broadband {total * 1e6:.0f} uV exceeds "
                     f"{WANT_RMS * 1e6:.0f} uV")
    if mains > WANT_MAINS:
        fails.append(f"50 Hz at {mains * 1e6:.0f} uV exceeds "
                     f"{WANT_MAINS * 1e6:.0f} uV -- N1 on the loom is the "
                     f"first suspect, then the switch frame ground")
    for nm, v in (("100 Hz", h2), ("150 Hz", h3)):
        if v > mains:
            fails.append(f"{nm} at {v * 1e6:.0f} uV is above the 50 Hz line "
                         f"({mains * 1e6:.0f} uV) -- that is not mains pickup, "
                         f"look for a supply or oscillation problem")

    # Name whatever else is sticking up, so a rogue tone cannot hide inside a
    # broadband figure that happens to pass.
    m = (f >= BAND[0]) & (f <= BAND[1])
    amp = np.sqrt(psd[m] * (FS / BUFFER))
    med = float(np.median(amp))
    tall = [(float(hz), float(v)) for hz, v in zip(f[m], amp)
            if v > max(8 * med, 15e-6)]
    tall.sort(key=lambda t: -t[1])
    if tall:
        print("\n  tallest lines:")
        for hz, v in tall[:6]:
            near = "  <- mains" if abs(hz % MAINS) < 2 or abs(hz % MAINS - MAINS) < 2 else ""
            print(f"    {hz:7.1f} Hz   {v * 1e6:7.1f} uV{near}")

    print()
    if fails:
        print(f"GATE 8 FAILS  [{a.label}]:")
        for why in fails:
            print(f"  - {why}")
    else:
        print(f"GATE 8 PASSES  [{a.label}] -- {total * 1e6:.0f} uV broadband, "
              f"{mains * 1e6:.0f} uV at 50 Hz.")
    print(f"\n  Run again with the other frame-ground state and compare.")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
