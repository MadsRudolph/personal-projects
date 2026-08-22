#!/usr/bin/env python3
"""Guided bring-up session: tells you what to do, asks what the caliper reads.

Walks through the whole set of captures the bit map needs, one at a time. At
each step it says exactly what to set the caliper to, waits for you, then asks
what the display ACTUALLY reads -- because that typed number is what the
decoder solves against, and it matters more than hitting a round target. Set
the caliper to whatever is convenient and type what you see.

After each capture it checks the result immediately and offers a retry, so a
knocked probe or a drifting jaw is caught there and then rather than after
you have packed up.

    python caliper_session.py

At any prompt: [Enter] accepts, 's' skips the step, 'q' quits. Captures already
on disk are detected and offered for reuse.
"""

import argparse
import glob
import os
import subprocess
import sys

import numpy as np

import ad3
import caliper_capture as cap
import caliper_decode as dec

DEFAULT_CAPTURES = "../captures"

# Each step: filename, unit, what to do, and why it earns its place.
STEPS = [
    ("mm_0.npz", "mm",
     "Close the jaws fully, then press ZERO so the display reads 0.00.",
     "The baseline. On its own it cannot pin down any bit field, but it is "
     "the cross-check every candidate has to survive."),
    ("mm_1.npz", "mm",
     "Open the jaws to roughly 1 mm.",
     "Exercises the bottom of the magnitude field."),
    ("mm_10.npz", "mm",
     "Open the jaws to roughly 10 mm.",
     "A 10x step from the last one -- the count should scale exactly."),
    ("mm_100.npz", "mm",
     "Open the jaws to roughly 100 mm.",
     "Needs 14 bits of count, so it reaches bits the smaller readings "
     "never touch."),
    ("mm_max.npz", "mm",
     "Open the jaws AS FAR AS THEY GO, near full scale.",
     "THE IMPORTANT ONE. Only bits 1..11 have been exercised so far, so "
     "1..11 and 1..14 both still fit. This is what separates them."),
    ("mm_neg1.npz", "mm",
     "Open the jaws about 1 mm, press ZERO, then close them fully. "
     "The display should now show a NEGATIVE number.",
     "The only way to find the sign bit. It is currently a guess inherited "
     "from another caliper."),
    ("in_1.npz", "in",
     "Switch the caliper to INCHES and set roughly 1.0000 in.",
     "Finds the unit bit, if this caliper has one. Many newer ones dropped "
     "it."),
]


def ask(prompt, default=""):
    """Prompt, returning a stripped string. Ctrl-C and Ctrl-D mean quit."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\naborted")
        sys.exit(1)


def ask_reading(unit):
    """Ask what the display shows. Returns a float, or None to skip."""
    while True:
        raw = ask(f"    What does the display read, in {unit}? "
                  f"(number, or 's' to skip) > ")
        if raw.lower() in ("s", "skip"):
            return None
        if raw.lower() in ("q", "quit"):
            print("stopping here -- captures so far are saved")
            sys.exit(0)
        # Accept a comma as the decimal separator; the caliper may show either.
        try:
            return float(raw.replace(",", "."))
        except ValueError:
            print("    ...that is not a number. Try again, e.g. 12.34 or -1.02")


def describe(clk, data, rate):
    """One-line verdict on a fresh capture, plus the decoded frame if any."""
    s = cap.summarise_clock(clk, rate)
    if not s["frames"]:
        return False, "NO FRAMES SEEN -- check the probes and that the "\
                      "caliper is on", None
    note = (f"{s['frames']} frames, clock edges per frame "
            f"{s['edges_min']}..{s['edges_max']}")
    if s["edges_max"] < 20:
        return False, note + "  -- too few for a 24-bit frame; CLK and DATA "\
                             "may be swapped", None

    # Falling edge is what was measured on this caliper (see
    # docs/protocol-notes.md). This is only the at-the-bench preview;
    # caliper_decode.py re-derives the polarity properly at the end.
    frames = dec.extract_frames(clk, data, rate, "falling", 24)
    best, agree, total = dec.consensus(frames)
    if best is None:
        return False, note + "  -- no frame decoded", None
    if agree < total * 0.8:
        return False, (f"{note}  -- only {agree}/{total} frames agree, the "
                       f"jaws probably moved"), dec.bits_to_str(best)
    return True, f"{note}, {agree}/{total} frames agree", dec.bits_to_str(best)


def do_step(idx, total, fname, unit, todo, why, args):
    """Run one capture step. Returns True if a usable capture now exists."""
    path = os.path.join(args.captures, fname)
    print(f"\n{'='*72}")
    print(f"STEP {idx}/{total}   ->  {fname}")
    print(f"{'='*72}")
    print(f"  {todo}")
    print(f"  Why: {why}")

    if os.path.exists(path):
        z = np.load(path)
        have = float(z["expect"])
        shown = "unlabelled" if np.isnan(have) else f"{have:g} {str(z['unit'])}"
        print(f"\n  Already captured, tagged {shown}.")
        choice = ask("    [Enter] keep it, 'r' redo, 'q' quit > ").lower()
        if choice in ("q", "quit"):
            sys.exit(0)
        if choice not in ("r", "redo"):
            return True

    while True:
        print()
        resp = ask("    Set the caliper as above, hold it steady, then press "
                   "[Enter] ('s' skip, 'q' quit) > ").lower()
        if resp in ("s", "skip"):
            print("    skipped")
            return False
        if resp in ("q", "quit"):
            sys.exit(0)

        reading = ask_reading(unit)
        if reading is None:
            print("    skipped")
            return False

        print(f"    capturing {args.seconds:.0f} s -- keep it still...")
        try:
            data, rate, lost, corrupt = cap.capture_pair(args.seconds,
                                                         args.rate)
        except ad3.Ad3Busy as exc:
            print(f"    FAIL: {exc}")
            ask("    Close it, then press [Enter] to retry > ")
            continue

        ok, note, bits = describe(data[args.clk], data[args.data], rate)
        print(f"    {note}")
        if bits:
            print(f"    frame: {bits}")
        if lost or corrupt:
            print(f"    !! lost={lost} corrupt={corrupt}")

        if ok:
            cap.save_capture(path, data, rate, reading, unit,
                             args.clk, args.data)
            print(f"    saved -> {path}  (tagged {reading:g} {unit})")
            return True

        again = ask("    That does not look right. [Enter] retry, 'k' keep "
                    "anyway, 's' skip > ").lower()
        if again in ("k", "keep"):
            cap.save_capture(path, data, rate, reading, unit,
                             args.clk, args.data)
            print(f"    saved anyway -> {path}")
            return True
        if again in ("s", "skip"):
            return False


def unit_bit_report(captures):
    """Compare an inch frame against the metric ones to find a unit bit."""
    metric = sorted(glob.glob(os.path.join(captures, "mm_*.npz")))
    inch = sorted(glob.glob(os.path.join(captures, "in_*.npz")))
    if not inch or not metric:
        return
    print(f"\n{'='*72}")
    print("UNIT BIT")
    print(f"{'='*72}")

    def frame_of(path):
        c = dec.load_capture(path)
        f = dec.extract_frames(c["clk"], c["data"], c["rate"], "falling", 24)
        best, _, _ = dec.consensus(f)
        return best

    mframes = [f for f in (frame_of(p) for p in metric) if f]
    iframes = [f for f in (frame_of(p) for p in inch) if f]
    if not mframes or not iframes:
        print("  could not decode enough frames to compare")
        return

    # A unit bit is constant across every metric reading and flipped on inch.
    candidates = []
    for i in range(24):
        mvals = {f[i] for f in mframes if i < len(f)}
        ivals = {f[i] for f in iframes if i < len(f)}
        if len(mvals) == 1 and len(ivals) == 1 and mvals != ivals:
            candidates.append(i)
    print(f"  metric frames: {len(mframes)}   inch frames: {len(iframes)}")
    if candidates:
        print(f"  unit bit candidates: {candidates}")
        print("  -> set CALIPER_HAS_UNIT_BIT 1 and CALIPER_UNIT_BIT to the "
              "one that holds up")
    else:
        print("  no bit is constant across metric AND flipped on inch.")
        print("  -> this caliper most likely has NO unit bit. Leave")
        print("     CALIPER_HAS_UNIT_BIT at 0 and pick the unit at boot.")
        print("     docs/prior-art.md saw exactly this on a newer unit.")


def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--seconds", type=float, default=cap.DEFAULT_SECONDS)
    p.add_argument("--rate", type=float, default=cap.DEFAULT_RATE)
    p.add_argument("--clk", type=int, default=0, choices=(0, 1),
                   help="scope channel on CLK (default 0 = 1+/orange lead)")
    p.add_argument("--data", type=int, default=1, choices=(0, 1),
                   help="scope channel on DATA (default 1 = 2+/blue lead)")
    p.add_argument("--captures", default=DEFAULT_CAPTURES,
                   help="where captures live (default ../captures). Point it "
                        "elsewhere when testing, so a throwaway run cannot "
                        "drop a mislabelled file into the real set.")
    args = p.parse_args()
    if args.clk == args.data:
        print("FAIL: --clk and --data must differ")
        return 2

    print(__doc__.split("\n\n")[0])
    print(f"\n{'='*72}")
    print("BEFORE YOU START -- check the wiring")
    print(f"{'='*72}")
    print("  AD3 GND (black)  -> caliper GND        (black wire)")
    print("  scope 1- and 2-  -> caliper GND        (same point)")
    print(f"  scope 1+ (orange lead) -> caliper CLK   "
          f"[currently --clk {args.clk}]")
    print(f"  scope 2+ (blue lead)   -> caliper DATA  "
          f"[currently --data {args.data}]")
    print("\n  On the caliper measured in docs/protocol-notes.md that means")
    print("  1+ on the ORANGE wire and 2+ on the GREEN wire.")
    print("  The WaveForms GUI must be closed.")
    if ask("\n  [Enter] when that is all connected ('q' quits) > ").lower() \
            in ("q", "quit"):
        return 0

    done = 0
    for i, (fname, unit, todo, why) in enumerate(STEPS, 1):
        if do_step(i, len(STEPS), fname, unit, todo, why, args):
            done += 1

    print(f"\n{'='*72}")
    print(f"CAPTURED {done}/{len(STEPS)} steps -- now solving the bit map")
    print(f"{'='*72}")

    metric = sorted(glob.glob(os.path.join(args.captures, "mm_*.npz")))
    if len(metric) < 2:
        print("Need at least two metric captures at different readings.")
        return 1
    # Shell out so the decoder's full report is used rather than reproduced.
    # Flush first: our prints are buffered when piped, the child's are not, and
    # without this the report lands above the header that introduces it.
    sys.stdout.flush()
    subprocess.run([sys.executable, "caliper_decode.py", *metric])
    sys.stdout.flush()
    unit_bit_report(args.captures)

    print(f"\n{'='*72}")
    print("Copy the config block above into firmware/include/config.h, and")
    print("fill in the tables in docs/protocol-notes.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
