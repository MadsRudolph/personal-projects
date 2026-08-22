#!/usr/bin/env python3
"""Prove the level shifter works BEFORE the ESP32 is in the picture.

Build the two transistor stages, then probe their OUTPUTS (the collectors --
the same nodes that will go to the ESP32 pins) with the AD3 instead of the
caliper pads. This script captures them, undoes the inversion, and checks the
frame still decodes to whatever the caliper display reads.

Doing it this way means that if something is wrong later you already know
which half is at fault. A shifter that passes here and a sniffer that still
reads rubbish is a firmware or pin problem, not a circuit one.

    python caliper_shifter_check.py

WIRING for this test

    AD3 GND (black) -----------> protoboard GND rail
    scope 1- and 2- (striped) -> protoboard GND rail
    scope 1+ (orange lead) ----> CLK stage collector   (ESP32 CLK pin node)
    scope 2+ (blue lead) ------> DATA stage collector  (ESP32 DATA pin node)

The protoboard needs 3.3 V on its rail for this, so keep the ESP32 powered
over USB -- you just do not need its pins connected yet.

WHAT IT CHECKS

  1. both outputs actually swing to the 3.3 V rail, not to some sagging level
  2. the stages invert, which is what SHIFTER_INVERTS in config.h assumes
  3. the frame still decodes to the displayed reading through the shifter
  4. how much data hold time is left for the ESP32's interrupt latency
"""

import argparse
import sys

import numpy as np

import ad3
import caliper_capture as cap
import caliper_decode as dec

FIRST_BIT, LAST_BIT, SIGN_BIT, N_BITS = 1, 14, 21, 24
SCALE = {"mm": 0.01, "in": 0.0005}


def ask(prompt):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\naborted")
        sys.exit(1)


def check_levels(volts, name, vcc=3.3):
    """Does this output reach both rails?"""
    lo, hi = ad3.swing(volts)
    ok = True
    print(f"  {name}: low {lo:+.2f} V   high {hi:+.2f} V   swing {hi-lo:.2f} V")
    if hi < 0.8 * vcc:
        print(f"     !! high side only reaches {hi:.2f} V, expected near "
              f"{vcc:.1f}. Collector resistor not tied to 3.3 V?")
        ok = False
    if lo > 0.5:
        print(f"     !! low side sits at {lo:.2f} V, expected near 0. The "
              f"transistor is not saturating -- base resistor too large, or "
              f"emitter not grounded?")
        ok = False
    if hi - lo < 2.0:
        print("     !! swing too small to drive a 3.3 V logic input")
        ok = False
    return ok


def hold_margin_us(clk_v, dat_v, rate):
    """Microseconds after the active edge before DATA moves.

    This is the ESP32's entire interrupt-latency budget: the ISR samples DATA
    when the edge fires, so if it is late by more than this it reads the next
    bit and the whole frame shifts by one.
    """
    # Negating flips the logic levels, undoing the shifter's inversion, so the
    # caliper's falling clock edge is a falling edge here too.
    clk = ad3.digitize(-clk_v)[0]
    dat_edges = ad3.edge_indices(ad3.digitize(-dat_v)[0])
    if dat_edges.size == 0:
        return None
    bursts = [b for b in ad3.find_bursts(clk, rate, gap_s=0.003)
              if (b[1] - b[0]) > 0.005 * rate]
    if not bursts:
        return None
    s, e = bursts[len(bursts) // 2]
    edges = np.flatnonzero(np.diff(clk) < 0) + 1
    edges = edges[(edges >= s) & (edges <= e)]
    holds = []
    for i in edges:
        nxt = dat_edges[dat_edges > i]
        if nxt.size:
            holds.append((nxt[0] - i) / rate * 1e6)
    return min(holds) if holds else None


def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--seconds", type=float, default=cap.DEFAULT_SECONDS)
    p.add_argument("--rate", type=float, default=cap.DEFAULT_RATE)
    p.add_argument("--vcc", type=float, default=3.3)
    p.add_argument("--unit", default="mm", choices=("mm", "in"))
    args = p.parse_args()

    print(__doc__.split("\n\n")[0])
    print("\n" + "=" * 72)
    print("Probe the two COLLECTORS -- the nodes that will feed the ESP32.")
    print("  1+ (orange lead) -> CLK stage collector")
    print("  2+ (blue lead)   -> DATA stage collector")
    print("  GND, 1- and 2-   -> protoboard GND rail")
    print("Keep the board powered so the 3.3 V rail is live.")
    print("=" * 72)
    if ask("\n[Enter] when connected ('q' quits) > ").lower() in ("q", "quit"):
        return 0

    raw = ask(f"What does the caliper display read, in {args.unit}? > ")
    try:
        expect = float(raw.replace(",", "."))
    except ValueError:
        print("not a number -- rerun and type the reading, e.g. 12.34")
        return 2

    print(f"\ncapturing {args.seconds:.0f} s -- hold the caliper still...")
    try:
        data, rate, lost, corrupt = cap.capture_pair(args.seconds, args.rate)
    except ad3.Ad3Busy as exc:
        print(f"FAIL: {exc}")
        return 2
    clk_v, dat_v = data[0], data[1]

    print("\n--- 1. output levels ---")
    ok_levels = (check_levels(clk_v, "CLK  out", args.vcc)
                 & check_levels(dat_v, "DATA out", args.vcc))

    print("\n--- 2. inversion ---")
    # Through an inverting stage the caliper's idle-high lines arrive idle-low.
    clk_bits, _ = ad3.digitize(clk_v)
    idle_high = bool(clk_bits[0])
    if idle_high:
        print("  CLK output idles HIGH -- the caliper's CLK idles high too, so")
        print("  this stage is NOT inverting. Set SHIFTER_INVERTS to 0, or")
        print("  check the transistor is wired as a common-emitter stage.")
    else:
        print("  CLK output idles LOW, so the stage inverts as expected.")
        print("  SHIFTER_INVERTS 1 in config.h is correct.")

    print("\n--- 3. decode through the shifter ---")
    frames = dec.extract_frames(-clk_v, -dat_v, rate, "falling", N_BITS)
    best, agree, total = dec.consensus(frames)
    ok_decode = False
    if best is None:
        print("  no frames -- is the caliper on, and are both stages built?")
    else:
        count = dec.field_value(best, FIRST_BIT, LAST_BIT)
        value = count * SCALE[args.unit] * (-1 if best[SIGN_BIT] else 1)
        print(f"  {agree}/{total} frames agree")
        print(f"  frame  {dec.bits_to_str(best)}")
        print(f"  decodes to {value:g} {args.unit}, display says "
              f"{expect:g} {args.unit}")
        if not best[0]:
            print("  !! bit 0 is not the always-1 marker -- the frame is "
                  "shifted, which usually means DATA and CLK are swapped")
        ok_decode = abs(value - expect) < 1e-9
        print("  " + ("MATCH" if ok_decode else "MISMATCH"))

    print("\n--- 4. timing margin for the ESP32 ---")
    hold = hold_margin_us(clk_v, dat_v, rate)
    if hold is None:
        print("  could not measure")
    else:
        print(f"  DATA holds for {hold:.0f} us after the active clock edge.")
        print(f"  That is the ISR's entire budget: interrupt latency plus the")
        print(f"  three digitalRead calls must fit inside it, or the frame")
        print(f"  shifts by one bit. The always-1 marker check in")
        print(f"  caliperDecode catches it if it does.")
        if hold < 30:
            print("  !! under 30 us is tight for an ESP32 with BLE running")

    print("\n" + "=" * 72)
    if ok_levels and ok_decode:
        print("SHIFTER GOOD -- wire the two collectors to the ESP32 and flash")
        print("the firmware with CALIPER_SNIFFER_MODE 1.")
        return 0
    print("NOT READY -- fix the points marked !! above before wiring the ESP32.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
