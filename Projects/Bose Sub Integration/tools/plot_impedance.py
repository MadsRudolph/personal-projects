#!/usr/bin/env python3
"""Render the aux-input impedance sweeps as a publication-quality Bode plot.

Reads the CSVs written by aux_impedance.py and produces a two-panel figure:
magnitude on top (log-log), phase below (semilog). Never a dual y-axis -- two
measures of different scale get two panels sharing one x.

    py -3.13 plot_impedance.py ring_open.csv --out z_open.png
    py -3.13 plot_impedance.py ring_open.csv --theme dark --out z_open_dark.png
    py -3.13 plot_impedance.py ring_open.csv ring_grounded.csv --out z_compare.png

With ONE csv the top panel shows |Z| alongside the parallel-model resistance
Rp. That pairing is the argument: Rp stays flat across the whole sweep while
|Z| falls at high frequency, which shows the rolloff is a shunt capacitance
rather than the resistive part changing.

With TWO csvs it overlays |Z| for each condition instead, for the
channels-summed comparison.
"""

import argparse
import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator

# Validated categorical slots 1 and 2, per mode.
THEME = {
    "light": dict(surface="#fcfcfb", page="#f9f9f7", ink="#0b0b0b",
                  ink2="#52514e", muted="#898781", grid="#e1e0d9",
                  axis="#c3c2b7", band="#f0efec",
                  series=("#2a78d6", "#eb6834")),
    "dark": dict(surface="#1a1a19", page="#0d0d0d", ink="#ffffff",
                 ink2="#c3c2b7", muted="#898781", grid="#2c2c2a",
                 axis="#383835", band="#242422",
                 series=("#3987e5", "#d95926")),
}

SUB_BAND = (20.0, 120.0)   # the region this project actually cares about


def load(path):
    rows = []
    with open(path, newline="") as f:
        for d in csv.DictReader(f):
            hz, z, r, x = (float(d["hz"]), float(d["z"]),
                           float(d["r"]), float(d["x"]))
            rows.append(dict(
                hz=hz, z=z, phase=float(d["phase"]),
                # Parallel-equivalent resistance: Rp = |Z|^2 / Rs
                rp=(z * z / r) if abs(r) > 1e-9 else float("nan"),
            ))
    rows.sort(key=lambda d: d["hz"])
    return rows


def ohm_fmt(v, _pos):
    if v >= 1e6:
        return f"{v / 1e6:g} M"
    if v >= 1e3:
        return f"{v / 1e3:g} k"
    return f"{v:g}"


def hz_fmt(v, _pos):
    if v >= 1000:
        return f"{v / 1000:g}k"
    return f"{v:g}"


def style_axis(ax, t):
    ax.set_facecolor(t["surface"])
    ax.grid(True, which="major", color=t["grid"], linewidth=0.7, zorder=0)
    ax.grid(True, which="minor", color=t["grid"], linewidth=0.4,
            alpha=0.6, zorder=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(t["axis"])
        ax.spines[side].set_linewidth(1.0)
    ax.tick_params(colors=t["muted"], which="both", labelsize=9)
    ax.set_axisbelow(True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="+", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--theme", choices=("light", "dark"), default="light")
    ap.add_argument("--title", default="Bose Companion 5 — aux input impedance")
    ap.add_argument("--subtitle",
                    default="AD3 coherent-DFT sweep, 500 mV drive, "
                            "R$_{ref}$ = 9.8 k$\\Omega$")
    a = ap.parse_args()

    t = THEME[a.theme]
    plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans", "sans-serif"]

    datasets = [(p.stem.replace("_", " "), load(p)) for p in a.csv]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, sharex=True, figsize=(9.0, 6.8),
        gridspec_kw=dict(height_ratios=[1.5, 1.0], hspace=0.12))
    fig.patch.set_facecolor(t["page"])
    for ax in (ax1, ax2):
        style_axis(ax, t)
        ax.axvspan(*SUB_BAND, color=t["band"], zorder=0, linewidth=0)

    if len(datasets) == 1:
        label, rows = datasets[0]
        hz = [r["hz"] for r in rows]
        ax1.plot(hz, [r["z"] for r in rows], color=t["series"][0],
                 lw=2.0, label="|Z|", zorder=3)
        ax1.plot(hz, [r["rp"] for r in rows], color=t["series"][1],
                 lw=2.0, ls=(0, (5, 2)), label="R$_p$  (parallel model)",
                 zorder=3)
        ax2.plot(hz, [r["phase"] for r in rows], color=t["series"][0],
                 lw=2.0, zorder=3)
        flat = [r["z"] for r in rows if 20 <= r["hz"] <= 200]
        mid = sum(flat) / len(flat)
        ax1.annotate(f"{mid / 1000:.2f} k$\\Omega$ — flat within 0.1 dB",
                     xy=(48, mid), xytext=(0, -20),
                     textcoords="offset points", ha="center", va="top",
                     color=t["ink"], fontsize=10, fontweight="bold", zorder=4)
    else:
        for i, (label, rows) in enumerate(datasets):
            hz = [r["hz"] for r in rows]
            ax1.plot(hz, [r["z"] for r in rows], color=t["series"][i],
                     lw=2.0, ls=[(0, ()), (0, (5, 2))][i], label=label, zorder=3)
            ax2.plot(hz, [r["phase"] for r in rows], color=t["series"][i],
                     lw=2.0, ls=[(0, ()), (0, (5, 2))][i], zorder=3)

    ax1.set_xscale("log")
    ax1.set_yscale("log")
    # Data lives inside one decade, so the automatic decade ticks land off the
    # plot and leave the axis unlabelled. Place ticks explicitly.
    lo = min(min(r["z"] for r in rows) for _, rows in datasets)
    hi = max(max(r["rp"] if math.isfinite(r["rp"]) else r["z"] for r in rows)
             for _, rows in datasets)
    ax1.set_ylim(lo * 0.75, hi * 1.35)
    ticks = [t_ for t_ in (1000, 1500, 2000, 3000, 4000, 5000, 7000,
                           10000, 15000, 20000, 30000)
             if lo * 0.75 <= t_ <= hi * 1.35]
    ax1.set_yticks(ticks)
    ax1.yaxis.set_major_formatter(FuncFormatter(ohm_fmt))
    ax1.yaxis.set_minor_formatter(FuncFormatter(lambda v, p: ""))
    ax1.set_ylabel("impedance  (Ω)", color=t["ink2"], fontsize=10)
    ax1.legend(frameon=False, loc="lower left", fontsize=10,
               labelcolor=t["ink2"])

    ax2.set_ylim(-90, 8)
    ax2.yaxis.set_major_locator(MultipleLocator(30))
    ax2.yaxis.set_minor_locator(MultipleLocator(15))
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:g}°"))
    ax2.set_ylabel("phase", color=t["ink2"], fontsize=10)
    ax2.set_xlabel("frequency  (Hz)", color=t["ink2"], fontsize=10)
    ax2.xaxis.set_major_formatter(FuncFormatter(hz_fmt))
    ax2.xaxis.set_minor_formatter(FuncFormatter(lambda v, p: ""))

    ax2.text(math.sqrt(SUB_BAND[0] * SUB_BAND[1]), 0.04,
             "crossover band\nof interest", transform=ax2.get_xaxis_transform(),
             ha="center", va="bottom", fontsize=9, color=t["muted"],
             linespacing=1.3, zorder=4)

    fig.suptitle(a.title, x=0.055, ha="left", fontsize=14,
                 fontweight="bold", color=t["ink"], y=0.975)
    fig.text(0.055, 0.925, a.subtitle, ha="left", fontsize=10, color=t["muted"])
    fig.subplots_adjust(top=0.875, left=0.10, right=0.975, bottom=0.095)

    fig.savefig(a.out, dpi=200, facecolor=t["page"])
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
