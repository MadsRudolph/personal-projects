#!/usr/bin/env python3
"""Step 1 of bring-up: work out which of the four pads is which.

The data-port pads are GND, DATA, CLK and VDD (~1.5 V) in an order that is not
standardised, so they have to be measured. This probes two pads at a time with
the AD3's analog scope channels and tells you what each one looks like.

WIRING (see ad3.py for the full note)

    AD3 GND (black) ---------------> caliper battery NEGATIVE
    scope 1- (white/orange stripe) -> caliper battery NEGATIVE
    scope 2- (white/blue stripe) ---> caliper battery NEGATIVE
    scope 1+ (orange) -------------> pad A
    scope 2+ (blue) ---------------> pad B

Do NOT clip the black GND lead onto a pad until you know which pad is ground.
The scope inputs are high impedance and read-only, so probing with 1+ / 2+ is
safe on any pad.

WHAT YOU SHOULD SEE

    GND   flat at 0 V
    VDD   flat at ~1.5 V (this is also your logic-high reference)
    CLK   quiet, then a burst of ~24 regular pulses, a few times a second
    DATA  quiet, then an irregular pattern over the same burst window

Move the caliper's jaws during the scan -- some calipers only transmit when the
reading changes.

    python caliper_padscan.py                       # 3 s on pads A and B
    python caliper_padscan.py --seconds 5 --label "pads 1 and 2"
"""

import argparse
import sys

import numpy as np

import ad3

CH_NAMES = {0: "scope 1+ (orange)", 1: "scope 2+ (blue)"}


def classify(volts, rate_hz):
    """Describe one probed pad. Returns (verdict, list of detail lines)."""
    if volts.size == 0:
        return "NO DATA", ["capture returned no samples"]

    v_min = float(volts.min())
    v_max = float(volts.max())
    v_mean = float(volts.mean())
    # ad3.swing reaches into the tails rather than using 5/95 percentiles: the
    # caliper transmits only a few percent of the time, so a 95th percentile
    # would still be sitting on the idle level and report no swing at all.
    lo, hi = ad3.swing(volts)
    p2p = hi - lo

    details = [f"mean {v_mean:+.3f} V   range {v_min:+.3f} .. {v_max:+.3f} V"
               f"   swing {p2p:.3f} V ({lo:+.3f} -> {hi:+.3f})"]

    # A static line: no meaningful swing between its 5th and 95th percentile.
    if p2p < 0.20:
        if abs(v_mean) < 0.25:
            details.append("note: an UNCONNECTED probe also reads ~0 V -- "
                           "confirm the tip is really on the pad")
            return "GND (or open probe)", details
        if v_mean > 0.8:
            details.append(f"this is your logic-high reference: {v_mean:.3f} V")
            return f"VDD (~{v_mean:.2f} V)", details
        return "static, unexpected level", details

    bits, thr = ad3.digitize(volts)
    edges = ad3.edge_indices(bits)
    details.append(f"threshold {thr:.3f} V   {edges.size} edges   "
                   f"idle {'HIGH' if bits[0] else 'LOW'}")

    # Frames are separated by silence, not a preamble. 3 ms matches the gap the
    # firmware uses to resync (CALIPER_FRAME_GAP_US).
    bursts = ad3.find_bursts(bits, rate_hz, gap_s=0.003)
    if not bursts:
        return "active, but no burst structure", details

    # Split the bursts into real frames and one- or two-edge blips. The blips
    # come from noise and from frames clipped by the start or end of the
    # window, and they would otherwise drag every statistic down.
    real, blips = [], 0
    for start, end in bursts:
        in_burst = int(np.count_nonzero((edges >= start) & (edges <= end)))
        if in_burst >= 4:
            real.append((start, end, in_burst))
        else:
            blips += 1

    if not real:
        details.append(f"{len(bursts)} bursts, all under 4 edges -- noise, "
                       f"not frames")
        return "active, but no frame structure", details

    counts = np.array([c for _, _, c in real])
    durations = [(e - s) / rate_hz for s, e, _ in real]
    span_s = volts.size / rate_hz
    burst_rate = len(real) / span_s if span_s else 0.0
    details.append(
        f"{len(real)} frames   {burst_rate:.1f} /s   "
        f"edges/frame {counts.min()}..{counts.max()} "
        f"(median {int(np.median(counts))})   "
        f"length {1000*min(durations):.2f}..{1000*max(durations):.2f} ms"
        + (f"   [+{blips} noise blips ignored]" if blips else ""))

    # Analyse the fullest frame, not the first one -- the first is often a
    # fragment clipped by the start of the capture window.
    start, end, _ = max(real, key=lambda b: b[2])
    burst_edges = edges[(edges >= start) & (edges <= end)]
    runs = np.diff(burst_edges)
    if runs.size < 3:
        return "active", details

    unit = float(np.min(runs))                    # one half-clock, in samples
    regularity = float(runs.max()) / unit if unit else 999.0
    half_us = 1e6 * unit / rate_hz
    details.append(
        f"fullest frame: {burst_edges.size} edges   shortest pulse "
        f"{half_us:.1f} us   longest {regularity:.1f}x that   "
        f"implied clock {1e3/(2*half_us):.2f} kHz")

    # A clock's pulses are all one unit wide; a data line holds its level for
    # whole bit periods, so its runs come out as small integer multiples.
    mult = np.round(runs / unit).astype(int)
    spread = ", ".join(f"{m}x{int(np.count_nonzero(mult == m))}"
                       for m in sorted(set(mult.tolist())))
    details.append(f"pulse widths (as multiples of the shortest): {spread}")

    # Same-direction intervals: for a clock these are one period throughout,
    # give or take whatever gap separates groups of bits.
    rise = burst_edges[::2] if bits[int(burst_edges[0])] else burst_edges[1::2]
    if rise.size >= 3:
        periods = np.diff(rise)
        details.append(
            f"period between same-direction edges: "
            f"{1e6*periods.min()/rate_hz:.0f}..{1e6*periods.max()/rate_hz:.0f} us")

    details.append(
        "CLK vs DATA cannot be settled from one reading -- a data line whose "
        "bits happen to alternate looks exactly like a clock. Capture two "
        "different displacements: the clock's edges/frame does not change, "
        "DATA's does.")

    if regularity < 2.5 and counts.max() >= 20:
        return "signal -- looks clock-like", details
    return "signal -- looks data-like", details

    return "active", details


def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--seconds", type=float, default=3.0,
                   help="capture window (default 3)")
    p.add_argument("--rate", type=float, default=200e3,
                   help="sample rate Hz (default 200k -- ~100x a 2 kHz clock)")
    p.add_argument("--label", default="",
                   help="note which pads are on 1+ and 2+, e.g. 'pads 1 and 2'")
    args = p.parse_args()

    print(f"Probing for {args.seconds:.1f} s @ {args.rate/1e3:.0f} kS/s"
          f"{' -- ' + args.label if args.label else ''}")
    print(">>> MOVE THE CALIPER JAWS NOW so it transmits <<<\n")

    try:
        with ad3.open_ad3() as device:
            data, rate, lost, corrupt = ad3.record(
                device, args.rate, args.seconds, channels=(0, 1))
    except ad3.Ad3Busy as exc:
        print(f"FAIL: {exc}")
        return 2

    n = max(v.size for v in data.values())
    print(f"captured {n} samples/channel @ {rate/1e3:.1f} kS/s "
          f"({n/rate:.2f} s)")
    if lost or corrupt:
        print(f"!! lost={lost} corrupt={corrupt} -- lower --rate if large")
    print()

    for ch in (0, 1):
        verdict, details = classify(data[ch], rate)
        print(f"{CH_NAMES[ch]:22s} -> {verdict}")
        for line in details:
            print(f"{'':24s}{line}")
        print()

    print("Move the probes to the remaining pads and run again. Record the "
          "result in docs/protocol-notes.md section 2.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
