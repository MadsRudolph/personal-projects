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

    pulse_counts = []
    durations = []
    for start, end in bursts:
        in_burst = np.count_nonzero((edges >= start) & (edges <= end))
        pulse_counts.append(in_burst)
        durations.append((end - start) / rate_hz)

    counts = np.array(pulse_counts)
    span_s = volts.size / rate_hz
    burst_rate = len(bursts) / span_s if span_s else 0.0
    details.append(
        f"{len(bursts)} bursts   {burst_rate:.1f} /s   "
        f"edges/burst {counts.min()}..{counts.max()} (median {int(np.median(counts))})   "
        f"burst length {1000*min(durations):.2f}..{1000*max(durations):.2f} ms")

    # Within a burst, a clock's pulse widths are all the same; a data line's
    # are multiples of the bit period. That ratio is the cleanest separator.
    first = bursts[0]
    burst_edges = edges[(edges >= first[0]) & (edges <= first[1])]
    if burst_edges.size >= 4:
        runs = np.diff(burst_edges)
        regularity = runs.max() / runs.min() if runs.min() else 999
        bit_period_s = float(np.median(runs)) / rate_hz
        details.append(
            f"first burst: shortest pulse {1e6*runs.min()/rate_hz:.1f} us   "
            f"max/min {regularity:.1f}x   implied clock "
            f"{1e-3/(2*bit_period_s):.2f} kHz")
        # ~24 bits per frame means ~48 clock edges; a data line has far fewer.
        if regularity < 2.5 and counts.max() >= 20:
            return "CLK", details
        return "DATA", details

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
