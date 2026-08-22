#!/usr/bin/env python3
"""Self-test: synthesise caliper waveforms and check the decoder recovers them.

No hardware needed. This exists so that when the decoder says something
surprising at the bench, you know whether to suspect the tool or the caliper.

It fabricates CLK/DATA traces for a known bit map (bit 0 always 1, magnitude
in bits 1..14 LSB first, sign in bit 21), writes them as .npz captures exactly
as caliper_capture.py would, runs the real decoder over them, and asserts the
bit map comes back out.

    python selftest_decode.py
"""

import os
import shutil
import sys
import tempfile

import numpy as np

import caliper_decode as dec

RATE = 200e3          # matches caliper_capture.py's default
CLOCK_HZ = 1200.0     # a plausible caliper clock
FRAME_HZ = 4.0        # frames per second
V_HIGH = 1.5          # the caliper's logic high
NOISE_V = 0.02

FIRST_BIT, LAST_BIT, SIGN_BIT, N_BITS = 1, 14, 21, 24


def make_frame_bits(value_mm):
    """Build the 24-bit frame this fake caliper would send."""
    count = int(round(abs(value_mm) / 0.01))
    bits = [0] * N_BITS
    bits[0] = 1                                    # always-1 marker
    for i in range(FIRST_BIT, LAST_BIT + 1):
        bits[i] = (count >> (i - FIRST_BIT)) & 1
    if value_mm < 0:
        bits[SIGN_BIT] = 1
    return bits


def synth_capture(value_mm, seconds=4.0, rng=None):
    """Render those bits as analog CLK/DATA traces.

    Clock idles high and pulses low once per bit, so the rising edge sits in
    the middle of a bit cell with DATA stable across it -- the ordinary
    arrangement, and what the decoder's default sample point assumes.
    """
    rng = rng or np.random.default_rng(0)
    n = int(seconds * RATE)
    clk = np.zeros(n, np.float32)
    dat = np.zeros(n, np.float32)

    bit_samples = int(round(RATE / CLOCK_HZ))
    half = bit_samples // 2
    frame_samples = int(round(RATE / FRAME_HZ))
    bits = make_frame_bits(value_mm)

    clk[:] = V_HIGH                                # idle high between frames
    for start in range(0, n - N_BITS * bit_samples, frame_samples):
        for k, b in enumerate(bits):
            s = start + k * bit_samples
            clk[s:s + half] = 0.0                  # low half, then rising edge
            clk[s + half:s + bit_samples] = V_HIGH
            dat[s:s + bit_samples] = V_HIGH if b else 0.0

    clk += rng.normal(0, NOISE_V, n).astype(np.float32)
    dat += rng.normal(0, NOISE_V, n).astype(np.float32)
    return clk, dat


def write_capture(path, value_mm, rng):
    clk, dat = synth_capture(value_mm, rng=rng)
    np.savez_compressed(path, clk=clk, data=dat,
                        rate=np.float64(RATE),
                        expect=np.float64(value_mm),
                        unit=np.str_("mm"))


def main():
    cases = [0.00, 1.00, 10.00, 100.00, -1.00, 150.25]
    tmp = tempfile.mkdtemp(prefix="caliper_selftest_")
    rng = np.random.default_rng(1234)
    failures = []
    try:
        paths = []
        for v in cases:
            path = os.path.join(tmp, f"v_{v:+.2f}.npz".replace(".", "_", 1))
            write_capture(path, v, rng)
            paths.append(path)

        caps = [dec.load_capture(p) for p in paths]

        # 1. every frame in a capture should be identical and decode correctly
        labelled = []
        for cap, v in zip(caps, cases):
            frames = dec.extract_frames(cap["clk"], cap["data"], cap["rate"],
                                        "rising", N_BITS)
            best, agree, total = dec.consensus(frames)
            ok = best is not None and agree == total and total >= 2
            print(f"{v:>8.2f} mm : {agree}/{total} frames agree   "
                  f"{dec.bits_to_str(best) if best else '(none)'}")
            if not ok:
                failures.append(f"{v} mm: frames inconsistent "
                                f"({agree}/{total})")
                continue
            if best != tuple(make_frame_bits(v)):
                failures.append(f"{v} mm: bits differ from what was sent")
            got = dec.field_value(best, FIRST_BIT, LAST_BIT) * 0.01
            if abs(got - abs(v)) > 1e-9:
                failures.append(f"{v} mm: magnitude decoded as {got}")
            labelled.append((best, v, "mm"))

        # 2. the bit-map search should recover the field that was encoded
        cands, _ = dec.search_bit_map(labelled, N_BITS)
        print(f"\nmagnitude field candidates: {cands}")
        if (FIRST_BIT, LAST_BIT) not in cands:
            failures.append(f"bit-map search missed bits "
                            f"{FIRST_BIT}..{LAST_BIT}, got {cands}")

        signs = dec.search_sign_bit(labelled, N_BITS)
        print(f"sign bit candidates       : {signs}")
        if not signs or SIGN_BIT not in signs:
            failures.append(f"sign search missed bit {SIGN_BIT}, got {signs}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS -- decoder recovers the injected bit map, sign and values.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
