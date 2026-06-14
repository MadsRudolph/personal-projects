#!/usr/bin/env python3
"""AD3 logic-analyzer capture + first-pass characterization.

Captures the AD3's digital inputs (DIO 0..15) and, for each channel in
--channels, reports: idle level, number of edges, estimated bit period /
bit rate, and a short symbol preview. This is the "what is even moving on
these lines?" tool — run it first, read the summary, THEN decide whether a
line is a clock, a data line, a chip-select, or idle.

Wiring: AD3 DIO 0..8 (the grey/striped flying leads, labelled on the AD3)
to the 9 pins under test. AD3 GND (black) to the target's GND — REQUIRED,
a floating ground gives garbage edges.

Logic level: AD3 digital inputs read 3.3 V-logic thresholds and tolerate
0..5 V. They do NOT drive — read-only here. For 1.8 V or lower logic,
levels may be marginal; say so in the report rather than trusting it.

Close the WaveForms GUI first — only one app can own the AD3.

Examples
--------
  # 100 MHz/divider sample rate, 1M samples, watch DIO0..8
  python logic_capture.py --channels 0-8 --rate 20e6 --samples 1000000

  # trigger on a falling edge of DIO7 (e.g. a chip-select) and capture around it
  python logic_capture.py --channels 0-8 --rate 50e6 --trigger 7:falling

  # dump raw samples to a .npy for offline decoding
  python logic_capture.py --channels 0-8 --rate 50e6 --save cap.npy
"""

import argparse
import sys
import time

from pydwf import (DwfLibrary, DwfAcquisitionMode, DwfState,
                   DwfTriggerSource)
from pydwf.utilities import openDwfDevice


def parse_channels(spec):
    """'0-8' or '0,1,4,7' -> sorted list of ints."""
    out = set()
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return sorted(out)


def configure_trigger(din, spec):
    """spec like '7:falling' / '3:rising' — trigger on one DIO edge."""
    ch_s, edge = spec.split(":")
    ch = int(ch_s)
    din.triggerSourceSet(DwfTriggerSource.DetectorDigitalIn)
    mask = 1 << ch
    # triggerSet(low, high, rising, falling): set the edge masks for this bit
    if edge.startswith("r"):
        din.triggerSet(0, 0, mask, 0)
    else:
        din.triggerSet(0, 0, 0, mask)
    din.triggerPositionSet(0)   # keep all post-trigger samples


def capture(device, channels, rate_hz, n_samples, trigger=None):
    din = device.digitalIn
    din.reset()

    base = din.internalClockInfo()          # 100 MHz on the AD3
    divider = max(1, round(base / rate_hz))
    actual_rate = base / divider
    din.dividerSet(divider)

    din.sampleFormatSet(16)                  # 16 bits/sample (all DIO in one word)
    n_max = din.bufferSizeInfo()
    n = min(n_samples, n_max)
    din.bufferSizeSet(n)

    if trigger:
        din.acquisitionModeSet(DwfAcquisitionMode.Single)
        configure_trigger(din, trigger)
    else:
        din.acquisitionModeSet(DwfAcquisitionMode.Single)
        din.triggerSourceSet(DwfTriggerSource.None_)

    din.configure(False, True)               # start acquisition
    t0 = time.time()
    while True:
        st = din.status(True)
        if st == DwfState.Done:
            break
        if time.time() - t0 > 10:
            print("!! capture timed out (waiting on trigger?) — grabbing what we have")
            break
        time.sleep(0.005)

    samples = din.statusData(n)              # array of uint16, one per sample
    return samples, actual_rate, n


def characterize(samples, rate_hz, channel):
    """Per-channel: idle level, edges, estimated bit rate, preview."""
    mask = 1 << channel
    bits = [(s & mask) >> channel for s in samples]
    n = len(bits)
    ones = sum(bits)
    # edges
    edges = 0
    runs = []          # run-lengths of constant level (in samples)
    run = 1
    for i in range(1, n):
        if bits[i] != bits[i - 1]:
            edges += 1
            runs.append(run)
            run = 1
        else:
            run += 1
    runs.append(run)

    if edges == 0:
        level = "HIGH" if ones else "LOW"
        return f"ch{channel:2d}: idle {level}  (no activity)"

    min_run = min(runs)                       # shortest pulse = fastest symbol
    # shortest run ~ one bit (or half a clock period)
    bit_period_s = min_run / rate_hz
    bit_rate = 1.0 / bit_period_s if bit_period_s else 0
    duty = 100.0 * ones / n
    # crude clock vs data heuristic: a clock has very regular runs
    regular = (max(runs) <= 3 * min_run)
    role = "clock?" if regular and edges > n / 50 else "data?"

    return (f"ch{channel:2d}: {edges:6d} edges  duty {duty:4.0f}%  "
            f"min-pulse {bit_period_s*1e9:7.0f} ns  "
            f"~{bit_rate/1e3:8.1f} kbit/s  [{role}]")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--channels", default="0-8", help="e.g. 0-8 or 0,1,4,7")
    p.add_argument("--rate", type=float, default=20e6, help="sample rate Hz (<=100e6)")
    p.add_argument("--samples", type=int, default=1_000_000)
    p.add_argument("--trigger", default=None, help="CH:edge, e.g. 7:falling")
    p.add_argument("--save", default=None, help="dump raw uint16 samples to .npy")
    args = p.parse_args()

    channels = parse_channels(args.channels)
    dwf = DwfLibrary()
    try:
        with openDwfDevice(dwf) as device:
            samples, rate, n = capture(device, channels, args.rate,
                                       args.samples, args.trigger)
    except Exception as e:
        msg = str(e).lower()
        if "another application" in msg or "djtgenable" in msg or "jtag init" in msg:
            print("FAIL: AD3 is in use — close the WaveForms GUI first.")
            return 2
        raise

    span_ms = 1000.0 * n / rate
    print(f"captured {n} samples @ {rate/1e6:.3f} MHz  ({span_ms:.2f} ms window)\n")
    for ch in channels:
        print(characterize(samples, rate, ch))

    if args.save:
        import numpy as np
        np.save(args.save, np.array(samples, dtype="uint16"))
        print(f"\nraw samples -> {args.save} (uint16, bit k = DIO k)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
