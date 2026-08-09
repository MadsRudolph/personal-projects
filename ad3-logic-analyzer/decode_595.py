#!/usr/bin/env python3
"""Decode a 74HC595 chain capture taken with trig_capture.py.

Wiring assumed (matches `--channels 0-2`):
    DIO0 = SHCP (shift clock)
    DIO1 = STCP (storage/latch clock)
    DIO2 = DS   (serial data in, first chip of the chain)

Per the 74HC595 datasheet: data is shifted on the LOW-to-HIGH transition of
SHCP; the shift register is transferred to the storage register on the
LOW-to-HIGH transition of STCP. So: sample DS on every SHCP rising edge, and
an STCP rising edge terminates a word.

  python decode_595.py dac_test.npy
  python decode_595.py dac_*.npy --diff
"""

import argparse
import glob
import sys

import numpy as np

SHCP, STCP, DS = 0, 1, 2


def rising(bits):
    """Indices where a 0/1 array goes 0 -> 1."""
    return np.flatnonzero((bits[1:] == 1) & (bits[:-1] == 0)) + 1


def decode_array(raw):
    """Decode a raw uint16 sample array into words. Returns None if no clock."""
    shcp = (raw >> SHCP) & 1
    stcp = (raw >> STCP) & 1
    ds = (raw >> DS) & 1

    clk = rising(shcp)
    lat = rising(stcp)
    if clk.size == 0:
        return None

    bits = ds[clk]                      # sample data on each rising clock

    # split the bit stream into words at each latch edge
    words = []
    start = 0
    for L in lat:
        n = int(np.searchsorted(clk, L))
        if n > start:
            words.append(bits[start:n])
            start = n
    if start < bits.size:
        words.append(bits[start:])      # trailing bits with no latch seen

    return {
        "clocks": clk.size, "latches": lat.size,
        "words": words, "bits": bits,
    }


def decode(path):
    r = decode_array(np.load(path))
    if r is not None:
        r["path"] = path
    return r


def show(r):
    print(f"\n=== {r['path']} ===")
    print(f"  {r['clocks']} clocks, {r['latches']} latch pulse(s)")
    for i, w in enumerate(r["words"]):
        s = "".join(str(b) for b in w)
        msb = int(s, 2) if s else 0
        lsb = int(s[::-1], 2) if s else 0
        print(f"  word {i}: {len(w):2d} bits  {s}")
        print(f"          MSB-first 0x{msb:06X} ({msb})   "
              f"LSB-first 0x{lsb:06X} ({lsb})")
        # split into the three chained bytes, in shift order
        if len(w) == 24:
            b = [s[0:8], s[8:16], s[16:24]]
            print("          bytes (shift order): " +
                  "  ".join(f"{x}=0x{int(x,2):02X}" for x in b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--diff", action="store_true",
                    help="compare words across files bit by bit")
    a = ap.parse_args()

    paths = []
    for f in a.files:
        paths.extend(sorted(glob.glob(f)) or [f])

    results = []
    for p in paths:
        r = decode(p)
        if r is None:
            print(f"{p}: no clock edges")
            continue
        results.append(r)
        show(r)

    if a.diff and len(results) > 1:
        print("\n=== diff (first full word of each file) ===")
        base = None
        for r in results:
            w = next((x for x in r["words"] if len(x) == 24), None)
            if w is None:
                continue
            s = "".join(str(b) for b in w)
            if base is None:
                base, bname = s, r["path"]
                print(f"  {bname:24s} {s}")
            else:
                mark = "".join("^" if x != y else "." for x, y in zip(base, s))
                print(f"  {r['path']:24s} {s}")
                print(f"  {'':24s} {mark}  (^ = differs from {bname})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
