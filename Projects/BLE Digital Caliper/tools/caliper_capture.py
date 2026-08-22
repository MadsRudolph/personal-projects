#!/usr/bin/env python3
"""Capture caliper frames to a file for offline decoding.

One capture per known displacement, tagged with what the caliper display read.
caliper_decode.py then uses those known values to solve the bit map.

For a guided run that tells you what to do at each step and prompts for the
reading, use caliper_session.py instead -- it drives this module.

WIRING -- after caliper_padscan.py has told you which pad is which:

    AD3 GND (black) --------------> caliper battery NEGATIVE
    scope 1- and 2- (striped) ----> caliper battery NEGATIVE
    scope 1+ (orange) ------------> CLK pad
    scope 2+ (blue) --------------> DATA pad

Zero the caliper first, then work through the displacements in
docs/protocol-notes.md section 3:

    python caliper_capture.py --expect 0.00   --out ../captures/mm_0.npz
    python caliper_capture.py --expect 1.00   --out ../captures/mm_1.npz
    python caliper_capture.py --expect 10.00  --out ../captures/mm_10.npz
    python caliper_capture.py --expect 100.00 --out ../captures/mm_100.npz
    python caliper_capture.py --expect -1.00  --out ../captures/mm_neg1.npz

Hold the caliper still at the displacement for the whole window. If the jaws
drift the frames will disagree with each other and the decoder will say so.
"""

import argparse
import os
import sys

import numpy as np

import ad3

DEFAULT_RATE = 200e3
DEFAULT_SECONDS = 4.0


def capture_pair(seconds=DEFAULT_SECONDS, rate=DEFAULT_RATE):
    """Record both scope channels. Returns (data, actual_rate, lost, corrupt)."""
    with ad3.open_ad3() as device:
        return ad3.record(device, rate, seconds, channels=(0, 1))


def summarise_clock(clk, rate):
    """Frame count and clock edges per frame, for immediate bench feedback.

    Blips under 4 edges are noise or frames clipped by the window edge; they
    are counted separately rather than dragging the statistics down.
    """
    bits, _ = ad3.digitize(clk)
    bursts = ad3.find_bursts(bits, rate, gap_s=0.003)
    edges = ad3.edge_indices(bits)
    per = [int(np.count_nonzero((edges >= s) & (edges <= e)))
           for s, e in bursts]
    real = [p for p in per if p >= 4]
    return {"frames": len(real),
            "blips": len(per) - len(real),
            "edges_min": min(real) if real else 0,
            "edges_max": max(real) if real else 0}


def save_capture(path, data, rate, expect, unit, clk_ch, data_ch):
    """Write a capture.

    The raw scope channels are stored along with the roles each was believed
    to hold, rather than the roles being baked into the arrays. If CLK and
    DATA turn out to be the other way round, caliper_decode.py --swap fixes
    the whole set instead of you re-capturing every displacement.
    """
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    np.savez_compressed(
        path,
        ch0=data[0], ch1=data[1],
        clk_channel=np.int32(clk_ch),
        data_channel=np.int32(data_ch),
        rate=np.float64(rate),
        expect=np.float64(expect if expect is not None else np.nan),
        unit=np.str_(unit),
    )


def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True, help="output .npz path")
    p.add_argument("--expect", type=float, default=None,
                   help="what the caliper display reads right now, e.g. 10.00")
    p.add_argument("--unit", default="mm", choices=("mm", "in"),
                   help="unit shown on the display (default mm)")
    p.add_argument("--seconds", type=float, default=DEFAULT_SECONDS,
                   help="capture window (default 4 -- several frames)")
    p.add_argument("--rate", type=float, default=DEFAULT_RATE,
                   help="sample rate Hz (default 200k)")
    p.add_argument("--clk", type=int, default=0, choices=(0, 1),
                   help="scope channel on CLK (default 0 = 1+/orange)")
    p.add_argument("--data", type=int, default=1, choices=(0, 1),
                   help="scope channel on DATA (default 1 = 2+/blue)")
    args = p.parse_args()

    if args.clk == args.data:
        print("FAIL: --clk and --data must be different channels")
        return 2

    shown = (f"{args.expect} {args.unit}" if args.expect is not None
             else "(unlabelled)")
    print(f"Capturing {args.seconds:.1f} s @ {args.rate/1e3:.0f} kS/s  "
          f"display reads {shown}")
    print(">>> HOLD THE CALIPER STILL AT THAT READING <<<\n")

    try:
        data, rate, lost, corrupt = capture_pair(args.seconds, args.rate)
    except ad3.Ad3Busy as exc:
        print(f"FAIL: {exc}")
        return 2

    n = data[0].size
    print(f"captured {n} samples/channel @ {rate/1e3:.1f} kS/s ({n/rate:.2f} s)")
    if lost or corrupt:
        print(f"!! lost={lost} corrupt={corrupt} -- lower --rate if large")

    s = summarise_clock(data[args.clk], rate)
    if not s["frames"]:
        print("\n!! NO FRAMES SEEN on the CLK channel.")
        print("   - is the caliper on, and are the probes on CLK/DATA?")
        print("   - some calipers only transmit while the reading changes;")
        print("     nudge the jaws during the window")
        print("   - re-run caliper_padscan.py to confirm the pad map")
    else:
        print(f"\n{s['frames']} frames  ({s['frames']/(n/rate):.1f} /s)  "
              f"clock edges per frame {s['edges_min']}..{s['edges_max']}")
        if s["edges_max"] < 20:
            print("!! fewer clock edges than a 24-bit frame needs -- CLK and "
                  "DATA may be swapped (try --clk/--data the other way round)")

    save_capture(args.out, data, rate, args.expect, args.unit,
                 args.clk, args.data)
    print(f"\nsaved -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
