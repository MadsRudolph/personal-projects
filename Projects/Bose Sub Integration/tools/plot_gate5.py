#!/usr/bin/env python3
"""Bode plot of the three rotary detents, for the test log.

Reads the CSVs ``subxo_gate5.py`` writes and draws magnitude and phase for all
three settings on one pair of axes, with the as-built model overlaid so the
agreement is visible rather than merely asserted. Each corner is marked where
the curve passes 3 dB below its own 63 Hz level -- the definition Gate 5 uses.

    python plot_gate5.py --out gate5_light.png
    python plot_gate5.py --out gate5_dark.png --theme dark

Runs under any interpreter with numpy and matplotlib -- no pydwf, no hardware.
Styling follows plot_impedance.py so the figures sit together in the log.
"""

import argparse
import csv
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

import subxo_model as m
from subxo_compare import measured_corner
from subxo_gate5 import DETENTS

# Slots 1 and 2 are plot_impedance.py's; slot 3 added for the third detent.
THEME = {
    "light": dict(surface="#fcfcfb", page="#f9f9f7", ink="#0b0b0b",
                  ink2="#52514e", muted="#898781", grid="#e1e0d9",
                  axis="#c3c2b7", band="#f0efec",
                  series=("#2a78d6", "#eb6834", "#1d9e75")),
    "dark": dict(surface="#1a1a19", page="#0d0d0d", ink="#ffffff",
                 ink2="#c3c2b7", muted="#898781", grid="#2c2c2a",
                 axis="#383835", band="#242422",
                 series=("#3987e5", "#d95926", "#2bb387")),
}

SUB_BAND = (20.0, 120.0)      # where the Bose module actually plays
REF_HZ = 63.0


def load(path):
    hz, mag, ph = [], [], []
    with open(path, newline="") as f:
        for d in csv.DictReader(f):
            hz.append(float(d["hz"]))
            mag.append(float(d["mag_db"]))
            ph.append(float(d["phase"]))
    o = np.argsort(hz)
    return np.array(hz)[o], np.array(mag)[o], np.array(ph)[o]


def hz_fmt(v, _pos):
    return f"{v / 1000:g}k" if v >= 1000 else f"{v:g}"


def style_axis(ax, t):
    ax.set_facecolor(t["surface"])
    ax.grid(True, which="major", color=t["grid"], linewidth=0.7, zorder=0)
    ax.grid(True, which="minor", color=t["grid"], linewidth=0.4, alpha=0.6,
            zorder=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(t["axis"])
        ax.spines[side].set_linewidth(1.0)
    ax.tick_params(colors=t["muted"], which="both", labelsize=9)
    ax.set_axisbelow(True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", type=Path, default=Path("."),
                    help="where the gate5_detent*.csv live")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--theme", choices=("light", "dark"), default="light")
    ap.add_argument("--dpi", type=int, default=200)
    a = ap.parse_args()

    t = THEME[a.theme]
    plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans", "sans-serif"]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, sharex=True, figsize=(9.0, 6.8),
        gridspec_kw=dict(height_ratios=[1.6, 1.0], hspace=0.10))
    fig.patch.set_facecolor(t["page"])
    for ax in (ax1, ax2):
        style_axis(ax, t)
        ax.axvspan(*SUB_BAND, color=t["band"], zorder=0, linewidth=0)

    grid = np.logspace(np.log10(15), np.log10(2000), 900)
    summary = []

    for i, (n, label, c1, c2, _unv) in enumerate(DETENTS):
        path = a.dir / f"gate5_detent{n}.csv"
        if not path.exists():
            continue
        hz, mag, ph = load(path)
        colour = t["series"][i % len(t["series"])]

        ax1.plot(grid, m.db(m.response(grid, c1, c2)), color=colour,
                 linewidth=1.1, alpha=0.55, zorder=2)
        ax1.plot(hz, mag, "o", ms=2.8, color=colour, zorder=3)
        ax2.plot(grid, np.degrees(np.angle(m.response(grid, c1, c2))),
                 color=colour, linewidth=1.1, alpha=0.55, zorder=2)
        ax2.plot(hz, ph, "o", ms=2.8, color=colour, zorder=3)

        f3, g63 = measured_corner(hz, mag)
        if f3:
            ax1.plot([f3], [g63 - 3.0], "o", ms=7, color=colour,
                     markeredgecolor=t["surface"], markeredgewidth=1.4,
                     zorder=5)
            ax1.annotate(f"{f3:.0f} Hz", xy=(f3, g63 - 3.0),
                         xytext=(10, -15), textcoords="offset points",
                         fontsize=9, color=colour, fontweight="bold",
                         zorder=6)
        summary.append((n, label, colour, f3, g63))

    ax1.axvline(REF_HZ, color=t["muted"], linewidth=0.8, linestyle=(0, (4, 3)),
                zorder=1)
    ax1.annotate("63 Hz", xy=(REF_HZ, 1.2), xytext=(-3, 0),
                 textcoords="offset points", ha="right", fontsize=9,
                 color=t["muted"], zorder=6)

    handles = [plt.Line2D([], [], color=c, marker="o", ms=5, linewidth=1.6,
                          label=f"detent {n}  ·  {lab}  ·  "
                                f"{f3:.1f} Hz  ·  {g63:+.2f} dB at 63 Hz")
               for n, lab, c, f3, g63 in summary]
    leg = ax1.legend(handles=handles, frameon=False, loc="lower left",
                     fontsize=9.5, labelcolor=t["ink2"],
                     handletextpad=0.7, borderaxespad=0.9)
    leg.set_zorder(7)

    ax1.set_xscale("log")
    ax1.set_xlim(15, 2000)
    ax1.set_ylim(-46, 3)
    ax1.set_yticks(range(-45, 3, 5))
    ax1.set_ylabel("magnitude  (dB)", color=t["ink2"], fontsize=10)

    ax2.set_ylim(-190, 10)
    ax2.set_yticks(range(-180, 1, 45))
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:g}°"))
    ax2.set_ylabel("phase", color=t["ink2"], fontsize=10)
    ax2.set_xlabel("frequency  (Hz)", color=t["ink2"], fontsize=10)
    ax2.xaxis.set_major_formatter(FuncFormatter(hz_fmt))
    ax2.xaxis.set_minor_formatter(FuncFormatter(
        lambda v, _p: hz_fmt(v, _p) if v in (30, 50, 300, 500) else ""))

    fig.text(0.5, 0.965, "subxo rev B — Gate 5, three rotary detents",
             ha="center", fontsize=13, color=t["ink"], fontweight="bold")
    fig.text(0.5, 0.933,
             "points measured on the AD3, lines are the as-built model  ·  "
             "corner = 3 dB below each curve's own 63 Hz level",
             ha="center", fontsize=9.5, color=t["muted"])
    fig.text(0.5, 0.028,
             f"shaded band {SUB_BAND[0]:.0f}–{SUB_BAND[1]:.0f} Hz is where the "
             "Companion 5 module plays  ·  15 Hz–2 kHz, 70 steps, 1 V drive",
             ha="center", fontsize=8.5, color=t["muted"])

    fig.subplots_adjust(left=0.085, right=0.975, top=0.905, bottom=0.135)
    fig.savefig(a.out, dpi=a.dpi, facecolor=t["page"])
    print(f"wrote {a.out}  ({a.theme}, {a.dpi} dpi)")
    for n, lab, _c, f3, g63 in summary:
        print(f"   detent {n}  {lab:14s} corner {f3:6.1f} Hz   "
              f"g(63) {g63:+.2f} dB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
