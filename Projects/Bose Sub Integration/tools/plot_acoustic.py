#!/usr/bin/env python3
"""Analyse and plot REW acoustic sweeps of the Companion 5 bass module.

Reads REW "Export measurement as text" files and reports, for each one, the
passband level, the -3 dB corners, and the slopes outside them. Then plots the
curves together with a difference panel, which is where the channel-summing
question is actually answered.

    py -3.13 plot_acoustic.py A.txt A_Sharp.txt B.txt --out acoustic.png \
        --labels "Left only" "Right only" "Both channels" --ref 0

--ref picks which curve the difference panel subtracts (index into the files).
"""

import argparse
import math
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

THEME = dict(surface="#1a1a19", page="#0d0d0d", ink="#ffffff", ink2="#c3c2b7",
             muted="#898781", grid="#2c2c2a", axis="#383835", band="#242422",
             series=("#3987e5", "#d95926", "#199e70"))

PASSBAND = (80.0, 180.0)     # where we take the reference level


def load_rew(path):
    f, spl = [], []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("*") or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    f.append(float(parts[0]))
                    spl.append(float(parts[1]))
                except ValueError:
                    continue
    return np.array(f), np.array(spl)


def smooth_octave(f, y, frac=6):
    """1/frac-octave running mean. f must be ascending."""
    lo = np.searchsorted(f, f / 2 ** (1 / (2 * frac)), side="left")
    hi = np.searchsorted(f, f * 2 ** (1 / (2 * frac)), side="right")
    csum = np.concatenate([[0.0], np.cumsum(y)])
    return (csum[hi] - csum[lo]) / np.maximum(hi - lo, 1)


def cross_below(f, y, level, lo, hi, rising):
    """Frequency where y crosses `level`, searching lo..hi."""
    m = (f >= lo) & (f <= hi)
    fs, ys = f[m], y[m]
    if fs.size < 2:
        return None
    if rising:                     # walking up from low frequency
        idx = np.where(ys >= level)[0]
        if idx.size == 0 or idx[0] == 0:
            return None
        i = idx[0]
    else:                          # walking up into the rolloff
        idx = np.where(ys <= level)[0]
        if idx.size == 0 or idx[0] == 0:
            return None
        i = idx[0]
    x0, x1, y0, y1 = fs[i - 1], fs[i], ys[i - 1], ys[i]
    if y1 == y0:
        return float(x1)
    return float(x0 + (level - y0) * (x1 - x0) / (y1 - y0))


def analyse(f, y, label):
    band = (f >= PASSBAND[0]) & (f <= PASSBAND[1])
    ref = float(np.median(y[band]))
    hp = cross_below(f, y, ref - 3, 20, PASSBAND[0], rising=True)
    lp = cross_below(f, y, ref - 3, PASSBAND[1], 2000, rising=False)

    print(f"\n--- {label} ---")
    print(f"passband level ({PASSBAND[0]:.0f}-{PASSBAND[1]:.0f} Hz) : "
          f"{ref:.1f} dB")
    print(f"high-pass corner (-3 dB)  : "
          f"{f'{hp:.1f} Hz' if hp else 'below sweep start'}")
    print(f"low-pass corner (-3 dB)   : "
          f"{f'{lp:.1f} Hz' if lp else 'not reached'}")

    if lp:
        m = (f >= lp * 1.15) & (f <= lp * 2.2)
        if m.sum() > 5:
            s = np.polyfit(np.log2(f[m]), y[m], 1)[0]
            print(f"slope above low-pass      : {s:.0f} dB/oct "
                  f"({abs(s) / 6:.1f}st order)")
    if hp:
        m = (f >= hp * 0.6) & (f <= hp * 0.9)
        if m.sum() > 5:
            s = np.polyfit(np.log2(f[m]), y[m], 1)[0]
            print(f"slope below high-pass     : {s:.0f} dB/oct "
                  f"({abs(s) / 6:.1f}st order)")
    if hp and lp:
        print(f"usable bandwidth          : {hp:.0f} - {lp:.0f} Hz "
              f"({math.log2(lp / hp):.1f} octaves)")
    return ref, hp, lp


def style(ax, t):
    ax.set_facecolor(t["surface"])
    ax.grid(True, which="major", color=t["grid"], lw=0.7, zorder=0)
    ax.grid(True, which="minor", color=t["grid"], lw=0.4, alpha=0.6, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(t["axis"])
    ax.tick_params(colors=t["muted"], which="both", labelsize=9)
    ax.set_axisbelow(True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--labels", nargs="*", default=None)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--ref", type=int, default=0,
                    help="index of the curve the delta panel subtracts")
    ap.add_argument("--smooth", type=int, default=6, help="1/N octave")
    ap.add_argument("--title", default="Bose Companion 5 bass module — "
                                       "nearfield acoustic response")
    ap.add_argument("--subtitle", default="AT2020 at 2 cm, REW 256k log sweep "
                                          "at −24 dBFS, uncalibrated SPL")
    a = ap.parse_args()

    labels = a.labels or [p.stem for p in a.files]
    t = THEME
    plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans", "sans-serif"]

    curves = []
    for path, label in zip(a.files, labels):
        f, y = load_rew(path)
        ys = smooth_octave(f, y, a.smooth)
        analyse(f, ys, label)
        curves.append((label, f, ys))

    fig, (ax1, ax2) = plt.subplots(
        2, 1, sharex=True, figsize=(9.5, 7.2),
        gridspec_kw=dict(height_ratios=[2.1, 1.0], hspace=0.12))
    fig.patch.set_facecolor(t["page"])
    for ax in (ax1, ax2):
        style(ax, t)

    for i, (label, f, y) in enumerate(curves):
        ax1.semilogx(f, y, color=t["series"][i % 3], lw=2.0, label=label,
                     zorder=3)

    ref_label, ref_f, ref_y = curves[a.ref]
    deltas = []
    for i, (label, f, y) in enumerate(curves):
        if i == a.ref:
            continue
        d = np.interp(ref_f, f, y) - ref_y
        deltas.append(d[(ref_f >= 40) & (ref_f <= 400)])
        ax2.semilogx(ref_f, d, color=t["series"][i % 3], lw=2.0,
                     label=f"{label} − {ref_label}", zorder=3)
    ax2.axhline(0, color=t["axis"], lw=1.0, zorder=2)
    ax2.axhline(6, color=t["muted"], lw=1.0, ls=(0, (4, 3)), zorder=2)
    ax2.text(1.005, 6, " +6 dB", transform=ax2.get_yaxis_transform(),
             va="center", fontsize=9, color=t["muted"])

    allspl = np.concatenate([y for _, _, y in curves])
    top = float(np.max(allspl))
    ax1.set_ylim(top - 60, top + 6)
    ax1.set_ylabel("relative SPL  (dB)", color=t["ink2"], fontsize=10)
    ax1.legend(frameon=False, loc="lower center", fontsize=10,
               labelcolor=t["ink2"], ncol=len(curves))

    # Scale the delta panel to the deltas actually present in the useful band,
    # always keeping 0 and the +6 dB summing reference visible.
    dall = np.concatenate(deltas) if deltas else np.array([0.0])
    lo = min(float(np.min(dall)) - 2, -2.0)
    hi = max(float(np.max(dall)) + 2, 7.5)
    ax2.set_ylim(lo, hi)
    ax2.set_ylabel("difference  (dB)", color=t["ink2"], fontsize=10)
    ax2.set_xlabel("frequency  (Hz)", color=t["ink2"], fontsize=10)
    ax2.legend(frameon=False, loc="upper left", fontsize=9,
               labelcolor=t["ink2"])

    ax1.set_xlim(20, 1000)
    for ax in (ax1, ax2):
        ax.xaxis.set_major_formatter(FuncFormatter(
            lambda v, p: f"{v / 1000:g}k" if v >= 1000 else f"{v:g}"))
        ax.xaxis.set_minor_formatter(FuncFormatter(lambda v, p: ""))

    fig.suptitle(a.title, x=0.055, ha="left", fontsize=14,
                 fontweight="bold", color=t["ink"], y=0.975)
    fig.text(0.055, 0.928, a.subtitle, ha="left", fontsize=10, color=t["muted"])
    fig.subplots_adjust(top=0.878, left=0.095, right=0.955, bottom=0.09)
    fig.savefig(a.out, dpi=200, facecolor=t["page"])
    print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
