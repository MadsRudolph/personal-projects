#!/usr/bin/env python3
"""Decode captured caliper frames and work out the bit map automatically.

Feed it the captures made by caliper_capture.py at known displacements. Rather
than asking you to eyeball bit strings, it searches every possible magnitude
field for the one that reproduces every known reading at once. That is the
whole reason for capturing at several displacements.

    python caliper_decode.py ../captures/*.npz

Add --dump to print every frame rather than the per-capture consensus.

The clock polarity is not known in advance, so both are tried and reported;
only the correct one will produce a bit map consistent with all your captures.

Output ends with a config.h snippet to paste into firmware/include/config.h.
"""

import argparse
import glob
import sys
from collections import Counter

import numpy as np

import ad3

# Counts on these calipers are 0.01 mm / 0.0005 in (see docs/prior-art.md).
SCALE = {"mm": 0.01, "in": 0.0005}
POLARITIES = ("rising", "falling")


def load_capture(path, swap=False):
    """Load a capture, resolving which scope channel held which role.

    Captures store the raw channels plus the roles they were believed to have,
    so `swap` can correct a CLK/DATA mix-up across a whole set without
    re-capturing anything.
    """
    z = np.load(path, allow_pickle=False)
    if "ch0" in z:
        clk_ch = int(z["clk_channel"])
        dat_ch = int(z["data_channel"])
        if swap:
            clk_ch, dat_ch = dat_ch, clk_ch
        clk, dat = z[f"ch{clk_ch}"], z[f"ch{dat_ch}"]
    else:
        # Captures written before the raw-channel format.
        clk, dat = z["clk"], z["data"]
        if swap:
            clk, dat = dat, clk
    return {
        "path": path,
        "clk": clk,
        "data": dat,
        "rate": float(z["rate"]),
        "expect": float(z["expect"]),
        "unit": str(z["unit"]),
    }


def _sample_points(clk_bits, rate, polarity, frame_bits, sample_frac):
    """DATA sample indices for each burst, one array per frame.

    DATA is read `sample_frac` of a clock period BEFORE the active edge, where
    setup time guarantees it has settled.
    """
    bursts = ad3.find_bursts(clk_bits, rate, gap_s=0.003)
    diff = np.diff(clk_bits)
    all_edges = (np.flatnonzero(diff > 0) + 1 if polarity == "rising"
                 else np.flatnonzero(diff < 0) + 1)
    if all_edges.size < 2:
        return []

    out = []
    for start, end in bursts:
        edges = all_edges[(all_edges >= start) & (all_edges <= end)]
        if edges.size < 2:
            continue
        period = float(np.median(np.diff(edges)))
        back = max(1, int(round(sample_frac * period)))
        out.append(edges[:frame_bits] - back)
    return out


def extract_frames(clk, dat, rate, polarity, frame_bits, sample_frac=0.25):
    """One bit tuple per burst.

    Three neighbouring samples are majority-voted at each point, the trick
    docs/prior-art.md recommends for surviving slow shifter transitions.
    """
    clk_bits, _ = ad3.digitize(clk)
    dat_bits, _ = ad3.digitize(dat)
    if clk_bits.size == 0:
        return []

    frames = []
    for points in _sample_points(clk_bits, rate, polarity, frame_bits,
                                 sample_frac):
        bits = []
        for point in points:
            i = int(point)
            if i < 1 or i + 2 >= dat_bits.size:
                bits.append(0)
                continue
            bits.append(int(dat_bits[i - 1:i + 2].sum() >= 2))   # best of three
        frames.append(tuple(bits))
    return frames


def sample_margin_us(clk, dat, rate, polarity, frame_bits, sample_frac=0.25):
    """How close the WORST sample point gets to a DATA transition.

    This is the tie-breaker between clock polarities. Both can produce a
    self-consistent bit map -- they differ only by a uniform one-bit shift,
    which the known-value search cannot see -- but the wrong one samples where
    DATA is still moving.

    The statistic is the 5th percentile of the distances, not the median: a
    median is dominated by the long constant stretches between transitions and
    barely moves between a good sample point and a terrible one. What matters
    is the closest approach. Returns microseconds, or None if DATA never moves.
    """
    clk_bits, _ = ad3.digitize(clk)
    dat_bits, _ = ad3.digitize(dat)
    dat_edges = ad3.edge_indices(dat_bits)
    points = _sample_points(clk_bits, rate, polarity, frame_bits, sample_frac)
    if dat_edges.size == 0 or not points:
        return None

    pts = np.concatenate(points).astype(np.int64)
    # Sentinels so the nearest-edge lookup needs no bounds special-casing.
    ext = np.concatenate(([-(1 << 40)], dat_edges.astype(np.int64), [1 << 40]))
    idx = np.searchsorted(ext, pts)
    nearest = np.minimum(pts - ext[idx - 1], ext[idx] - pts)
    return float(np.percentile(nearest, 5)) / rate * 1e6


def consensus(frames):
    """Most common frame, plus how many of them agreed."""
    if not frames:
        return None, 0, 0
    counts = Counter(frames)
    best, n = counts.most_common(1)[0]
    return best, n, len(frames)


def bits_to_str(bits):
    """Index 0 first -- the order docs/protocol-notes.md asks for."""
    return "".join(str(b) for b in bits)


def field_value(bits, first, last):
    """LSB-first unsigned value of bits[first..last]."""
    v = 0
    for i in range(first, last + 1):
        if i < len(bits) and bits[i]:
            v |= 1 << (i - first)
    return v


def search_bit_map(labelled, frame_bits, max_field=20):
    """Every (first, last) magnitude field that explains all known readings.

    `labelled` is a list of (consensus_bits, expected_value, unit).
    """
    usable = [(b, e, u) for b, e, u in labelled if not np.isnan(e)]
    # A zero reading is satisfied by almost any field, so it cannot narrow
    # anything down on its own; keep it only as a cross-check.
    discriminating = [x for x in usable if abs(x[1]) > 1e-9]
    if not discriminating:
        return [], usable

    candidates = []
    for first in range(frame_bits):
        for last in range(first, min(frame_bits, first + max_field)):
            ok = True
            for bits, expect, unit in usable:
                target = int(round(abs(expect) / SCALE[unit]))
                if field_value(bits, first, last) != target:
                    ok = False
                    break
            if ok:
                candidates.append((first, last))
    return candidates, usable


def search_sign_bit(labelled, frame_bits):
    """Bits that are set exactly on the negative readings and clear otherwise."""
    neg = [b for b, e, _ in labelled if not np.isnan(e) and e < 0]
    pos = [b for b, e, _ in labelled if not np.isnan(e) and e >= 0]
    if not neg or not pos:
        return None
    out = []
    for i in range(frame_bits):
        if all(i < len(b) and b[i] for b in neg) and \
           all(i < len(b) and not b[i] for b in pos):
            out.append(i)
    return out


def print_config(pol, cands, signs, frame_bits, note=""):
    """Emit the config.h block implied by one (polarity, bit map) solution."""
    first, last = cands[0]
    sign_bit = str(signs[0]) if signs else "??   // needs a negative capture"
    print(f"=== paste into firmware/include/config.h{note} ===")
    print(f"// clock polarity: data sampled on the {pol} edge -- the firmware")
    print("// ISR must trigger on that edge or these bit numbers are wrong")
    print(f"#define CALIPER_FRAME_BITS       {frame_bits}")
    print(f"#define CALIPER_VALUE_FIRST_BIT  {first:2d}")
    print(f"#define CALIPER_VALUE_LAST_BIT   {last:2d}")
    print(f"#define CALIPER_SIGN_BIT         {sign_bit}")
    if len(cands) > 1:
        print(f"// {len(cands)} fields fit; the narrowest is shown. The wider "
              f"ones only fit")
        print("// because their extra top bits stayed 0 -- capture a larger")
        print("// displacement (near full scale) to separate them.")
    print()


def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("captures", nargs="+",
                   help=".npz files from caliper_capture.py")
    p.add_argument("--bits", type=int, default=24,
                   help="frame length (default 24)")
    p.add_argument("--sample-frac", type=float, default=0.25,
                   help="sample DATA this fraction of a clock period before "
                        "the active edge (default 0.25)")
    p.add_argument("--dump", action="store_true", help="print every frame")
    p.add_argument("--swap", action="store_true",
                   help="treat the CLK and DATA channels as swapped")
    args = p.parse_args()

    paths = []
    for pattern in args.captures:
        hits = sorted(glob.glob(pattern))
        paths.extend(hits if hits else [pattern])
    if not paths:
        print("FAIL: no capture files matched")
        return 2

    caps = [load_capture(path, swap=args.swap) for path in paths]

    # ---- per-capture frames, both clock polarities --------------------------
    results = {pol: [] for pol in POLARITIES}
    margins = {pol: [] for pol in POLARITIES}
    for cap in caps:
        shown = ("unlabelled" if np.isnan(cap["expect"])
                 else f"{cap['expect']:g} {cap['unit']}")
        print(f"=== {cap['path']}   display {shown} ===")
        for pol in POLARITIES:
            frames = extract_frames(cap["clk"], cap["data"], cap["rate"],
                                    pol, args.bits, args.sample_frac)
            best, agree, total = consensus(frames)
            if best is None:
                print(f"  {pol:7s}: no frames found")
                results[pol].append((None, cap["expect"], cap["unit"]))
                continue
            margin = sample_margin_us(cap["clk"], cap["data"], cap["rate"],
                                      pol, args.bits, args.sample_frac)
            if margin is not None:
                margins[pol].append(margin)
            margin_txt = ("" if margin is None
                          else f"   margin {margin:.0f} us")
            print(f"  {pol:7s}: {agree}/{total} frames agree   "
                  f"{len(best)} bits{margin_txt}   {bits_to_str(best)}")
            if agree < total:
                print("           ^ frames disagree -- jaws moved, or the "
                      "sample point is on a transition (try --sample-frac)")
            if args.dump:
                for f in frames:
                    print(f"             {bits_to_str(f)}")
            results[pol].append((best, cap["expect"], cap["unit"]))
        print()

    # ---- bit-map search, per polarity ---------------------------------------
    labelled_count = sum(1 for c in caps if not np.isnan(c["expect"]))
    if labelled_count == 0:
        print("No captures carried a --expect value, so the bit map cannot be "
              "solved. Re-capture with --expect at known displacements.")
        return 0

    solutions = []
    for pol in POLARITIES:
        labelled = [(b, e, u) for b, e, u in results[pol] if b is not None]
        if not labelled:
            continue
        cands, usable = search_bit_map(labelled, args.bits)
        print(f"=== bit map search, {pol} edge "
              f"({len(usable)} labelled captures) ===")
        if not cands:
            print("  no magnitude field explains all readings on this "
                  "polarity\n")
            continue
        for first, last in cands:
            print(f"  magnitude bits {first}..{last}  "
                  f"({last - first + 1} bits)")
        signs = search_sign_bit(labelled, args.bits)
        if signs is None:
            print("  sign bit: needs both a negative and a positive capture")
        elif signs:
            print(f"  sign bit candidates: {signs}")
        else:
            print("  sign bit: no single bit tracks the sign -- capture more, "
                  "or the value may be two's complement")
        med_margin = (float(np.median(margins[pol])) if margins[pol] else 0.0)
        print(f"  worst-case sample margin: {med_margin:.0f} us clear of a "
              f"DATA edge")
        print()
        solutions.append((med_margin, pol, cands, signs, labelled))

    if not solutions:
        print("Nothing solved. Most likely causes, in order:")
        print("  1. CLK and DATA are swapped -- re-run caliper_padscan.py")
        print("  2. the frame is not 24 bits -- try --bits 20 / --bits 32")
        print("  3. the sample point is wrong -- try --sample-frac 0.5 or 0.1")
        print("  4. counts are not 0.01 mm on your caliper")
        return 1

    # ---- pick a polarity, then emit config ----------------------------------
    # Both polarities can fit, differing only by a uniform one-bit shift that
    # the known-value search cannot see. Prefer the one that samples furthest
    # from a DATA transition -- that is the genuinely settled one.
    solutions.sort(key=lambda x: -x[0])
    best_margin, pol, cands, signs, labelled = solutions[0]
    weak = len(solutions) > 1 and best_margin <= solutions[1][0] * 1.2
    if len(solutions) > 1:
        print("=== clock polarity ===")
        print(f"  both polarities fit. Picking {pol} on sample margin: "
              f"{best_margin:.0f} us vs {solutions[1][0]:.0f} us for "
              f"{solutions[1][1]}.")
        if weak:
            print("  those margins are close, so this pick is WEAK. Confirm "
                  "on a scope which")
            print("  clock edge DATA changes on before trusting it.")
        print()

    frames_only = [b for b, _, _ in labelled]
    print("=== bits constant across every capture ===")
    for i in range(args.bits):
        vals = {b[i] for b in frames_only if i < len(b)}
        if len(vals) == 1:
            print(f"  bit {i:2d} always {vals.pop()}")
    print()

    print_config(pol, cands, signs, args.bits,
                 note="  (preferred)" if weak else "")
    if weak:
        _, alt_pol, alt_cands, alt_signs, _ = solutions[1]
        if alt_cands:
            print("The other polarity fits almost as well. If the preferred "
                  "one gives wrong")
            print("readings on the bench, use this instead -- never a mix of "
                  "the two:")
            print()
            print_config(alt_pol, alt_cands, alt_signs, args.bits,
                         note="  (alternative)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
