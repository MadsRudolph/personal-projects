#!/usr/bin/env python3
"""Score a WaveForms Network Analyzer export against the as-built model.

Gate 5 of [[Test Guide - Sub Crossover Board]] asks three things of every sweep:
the corner lands inside its tolerance band, the shape tracks the model within
+/-0.5 dB from 30 to 400 Hz, and the 400->800 Hz octave is a real second-order
slope. This does all three and prints a verdict, so the nine settings do not
have to be read off cursors one at a time.

Export from WaveForms: Export -> Comma Separated Values, magnitude in dB.
Either leave "Relative to Ref" on or off -- if both channel columns are
present, C2-C1 is computed here and the setting does not matter.

    py -3.13 subxo_compare.py sweep_150_150.csv --c1 150 --c2 150
    py -3.13 subxo_compare.py sweep.csv --c1 370 --c2 68 --plot

--c1 is the JP1 selection in nF (220, 150, or 370 for both shunts fitted).
--c2 is the JP2 selection in nF (150, 120, or 68).
"""

import argparse
import csv
import re
import sys

import numpy as np

import subxo_model as m

REF_HZ = 63.0
SHAPE_LO, SHAPE_HI = 30.0, 400.0
SHAPE_TOL = 0.5


def read_export(path):
    """Pull (freq, magnitude_dB, phase_deg) out of a WaveForms CSV.

    The export carries a few '#' comment lines, then a header. Column names
    have varied across WaveForms versions, so match them by pattern rather than
    by exact string, and say out loud which ones were used.
    """
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        lines = [ln for ln in fh if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        sys.exit(f"{path}: no data rows")

    dialect = csv.Sniffer().sniff(lines[0], delimiters=",;\t")
    rows = list(csv.reader(lines, dialect))
    head = [h.strip() for h in rows[0]]

    def find(*patterns, required=True):
        for pat in patterns:
            for i, h in enumerate(head):
                if re.search(pat, h, re.I):
                    return i
        if required:
            sys.exit(f"{path}: no column matching {patterns[0]!r}\n"
                     f"  header was: {head}")
        return None

    i_f = find(r"freq")
    i_m2 = find(r"channel\s*2.*magn", r"\bc2\b.*magn", r"magnitude")
    i_m1 = find(r"channel\s*1.*magn", r"\bc1\b.*magn", required=False)
    i_p2 = find(r"channel\s*2.*phase", r"\bc2\b.*phase", r"phase",
                required=False)

    print(f"  frequency column : {head[i_f]!r}")
    print(f"  magnitude column : {head[i_m2]!r}")
    if i_m1 is not None and i_m1 != i_m2:
        print(f"  reference column : {head[i_m1]!r}  (subtracted)")
    if i_p2 is not None:
        print(f"  phase column     : {head[i_p2]!r}")

    f, mag, ph = [], [], []
    for r in rows[1:]:
        try:
            fv = float(r[i_f])
            mv = float(r[i_m2])
        except (ValueError, IndexError):
            continue
        if i_m1 is not None and i_m1 != i_m2:
            try:
                mv -= float(r[i_m1])
            except (ValueError, IndexError):
                pass
        f.append(fv)
        mag.append(mv)
        if i_p2 is not None:
            try:
                ph.append(float(r[i_p2]))
            except (ValueError, IndexError):
                ph.append(np.nan)
    if len(f) < 5:
        sys.exit(f"{path}: only {len(f)} usable rows")
    order = np.argsort(f)
    return (np.array(f)[order], np.array(mag)[order],
            np.array(ph)[order] if ph else None)


def measured_corner(f, mag):
    """Frequency 3 dB below the measured 63 Hz level, linearly interpolated."""
    ref = np.interp(REF_HZ, f, mag)
    above = f > REF_HZ
    fa, ma = f[above], mag[above]
    hit = np.nonzero(ma < ref - 3.0)[0]
    if not hit.size:
        return None, ref
    i = hit[0]
    if i == 0:
        return float(fa[0]), ref
    # interpolate in log f, which is where the curve is closest to straight
    x0, x1 = np.log10(fa[i - 1]), np.log10(fa[i])
    y0, y1 = ma[i - 1], ma[i]
    t = (ref - 3.0 - y0) / (y1 - y0)
    return float(10 ** (x0 + t * (x1 - x0))), ref


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv")
    ap.add_argument("--c1", type=float, required=True, help="JP1 value in nF")
    ap.add_argument("--c2", type=float, required=True, help="JP2 value in nF")
    ap.add_argument("--plot", action="store_true", help="measured vs model")
    a = ap.parse_args()

    c1, c2 = a.c1 * 1e-9, a.c2 * 1e-9
    print(f"\n{a.csv}")
    f, mag, ph = read_export(a.csv)
    print(f"  {len(f)} points, {f[0]:.1f} Hz to {f[-1]:.0f} Hz\n")

    f3_pred, g63_pred = m.corner(c1, c2)
    lo, hi = m.tolerance_band(c1, c2)
    f3_meas, g63_meas = measured_corner(f, mag)

    print(f"JP1 {a.c1:.0f}n / JP2 {a.c2:.0f}n\n")
    print(f"{'':22s} {'measured':>10s} {'model':>10s}")
    print("-" * 45)
    print(f"{'gain at 63 Hz':22s} {g63_meas:+9.2f}  {g63_pred:+9.2f}")
    if f3_meas is None:
        print(f"{'corner':22s} {'not reached':>10s}  {f3_pred:9.1f}")
    else:
        print(f"{'corner (63Hz -3dB)':22s} {f3_meas:9.1f}  {f3_pred:9.1f}")

    fails = []
    if f3_meas is None:
        fails.append("the curve never falls 3 dB below its 63 Hz level")
    elif not lo <= f3_meas <= hi:
        fails.append(f"corner {f3_meas:.1f} Hz is outside the {lo:.0f}-{hi:.0f} Hz band")

    # Shape: compare the two curves after removing the level offset, because
    # a constant offset is a gain error, not a filter error, and Gate 5 judges
    # the shape separately from the level.
    band = (f >= SHAPE_LO) & (f <= SHAPE_HI)
    if band.sum() < 5:
        print("\n  too few points in 30-400 Hz to judge shape")
    else:
        model = m.db(m.response(f[band], c1, c2))
        err = (mag[band] - np.interp(REF_HZ, f, mag)) - (model - g63_pred)
        rms, worst = float(np.sqrt(np.mean(err ** 2))), float(np.abs(err).max())
        fw = float(f[band][np.argmax(np.abs(err))])
        print(f"\n{'shape error 30-400 Hz':22s} rms {rms:.2f} dB, "
              f"worst {worst:+.2f} dB at {fw:.0f} Hz")
        if worst > SHAPE_TOL:
            fails.append(f"shape deviates {worst:.2f} dB at {fw:.0f} Hz "
                         f"(tolerance {SHAPE_TOL} dB)")

    if f[-1] >= 800:
        oct_meas = np.interp(800.0, f, mag) - np.interp(400.0, f, mag)
        oct_pred = m.db(m.response(800.0, c1, c2) / m.response(400.0, c1, c2))
        print(f"{'octave 400->800 Hz':22s} {oct_meas:+9.2f}  {oct_pred:+9.2f}")
        if abs(oct_meas - oct_pred) > 1.5:
            why = ("shallower -- suspect a stray path carrying signal around "
                   "the filter" if oct_meas > oct_pred else
                   "steeper -- suspect cancellation against a leakage path, or "
                   "something resonating")
            fails.append(f"octave slope {oct_meas:+.2f} dB against "
                         f"{oct_pred:+.2f} expected, {why}")
    else:
        print(f"{'octave 400->800 Hz':22s} {'sweep ends too low':>10s}")

    peak_meas = float(mag.max() - mag[0])
    print(f"{'peak above first point':22s} {peak_meas:+9.2f}  "
          f"{m.peaking(c1, c2):+9.2f}")

    print()
    if fails:
        print("GATE 5 FAILS for this setting:")
        for why in fails:
            print(f"  - {why}")
    else:
        print("GATE 5 PASSES for this setting.")

    if a.plot:
        import matplotlib.pyplot as plt
        grid = np.logspace(np.log10(f[0]), np.log10(f[-1]), 800)
        model = m.db(m.response(grid, c1, c2))
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.semilogx(f, mag, "o", ms=3, label="measured")
        ax.semilogx(grid, model, "-", lw=1.2, label="as-built model")
        if f3_meas:
            ax.axvline(f3_meas, ls=":", lw=1, label=f"corner {f3_meas:.0f} Hz")
        ax.axvspan(lo, hi, alpha=0.12, label=f"band {lo:.0f}-{hi:.0f} Hz")
        ax.set_xlabel("Hz")
        ax.set_ylabel("dB")
        ax.set_title(f"subxo  JP1 {a.c1:.0f}n / JP2 {a.c2:.0f}n")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend()
        fig.tight_layout()
        plt.show()

    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
