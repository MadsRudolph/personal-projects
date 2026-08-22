#!/usr/bin/env python3
"""Step 3 of bring-up: capture caliper frames to a file for offline decoding.

Run this once per known displacement, telling it what the caliper display
reads. caliper_decode.py then uses those known values to work out the bit map
automatically, which beats squinting at bit strings.

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


def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True, help="output .npz path")
    p.add_argument("--expect", type=float, default=None,
                   help="what the caliper display reads right now, e.g. 10.00")
    p.add_argument("--unit", default="mm", choices=("mm", "in"),
                   help="unit shown on the display (default mm)")
    p.add_argument("--seconds", type=float, default=4.0,
                   help="capture window (default 4 -- several frames)")
    p.add_argument("--rate", type=float, default=200e3,
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
        with ad3.open_ad3() as device:
            data, rate, lost, corrupt = ad3.record(
                device, args.rate, args.seconds, channels=(0, 1))
    except ad3.Ad3Busy as exc:
        print(f"FAIL: {exc}")
        return 2

    clk = data[args.clk]
    dat = data[args.data]
    n = clk.size
    print(f"captured {n} samples/channel @ {rate/1e3:.1f} kS/s ({n/rate:.2f} s)")
    if lost or corrupt:
        print(f"!! lost={lost} corrupt={corrupt} -- lower --rate if large")

    # Immediate sanity feedback, so a bad probe is caught at the bench rather
    # than three captures later.
    bits, thr = ad3.digitize(clk)
    bursts = ad3.find_bursts(bits, rate, gap_s=0.003)
    if not bursts:
        print("\n!! NO FRAMES SEEN on the CLK channel.")
        print("   - is the caliper on, and are the probes on CLK/DATA?")
        print("   - some calipers only transmit while the reading changes;")
        print("     nudge the jaws during the window")
        print("   - re-run caliper_padscan.py to confirm the pad map")
    else:
        edges = ad3.edge_indices(bits)
        per = [np.count_nonzero((edges >= s) & (edges <= e)) for s, e in bursts]
        print(f"\n{len(bursts)} frames  ({len(bursts)/(n/rate):.1f} /s)  "
              f"clock edges per frame {min(per)}..{max(per)}")
        if max(per) < 20:
            print("!! fewer clock edges than a 24-bit frame needs -- CLK and "
                  "DATA may be swapped (try --clk/--data the other way round)")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    # Store the raw scope channels and record which role each was believed to
    # hold, rather than baking the roles into the arrays. If CLK and DATA turn
    # out to be the other way round, caliper_decode.py --swap fixes the whole
    # set instead of you re-capturing every displacement.
    np.savez_compressed(
        args.out,
        ch0=data[0], ch1=data[1],
        clk_channel=np.int32(args.clk),
        data_channel=np.int32(args.data),
        rate=np.float64(rate),
        expect=np.float64(args.expect if args.expect is not None else np.nan),
        unit=np.str_(args.unit),
    )
    print(f"\nsaved -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
