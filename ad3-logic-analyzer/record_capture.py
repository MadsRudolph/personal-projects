#!/usr/bin/env python3
"""AD3 logic-analyzer STREAMING capture (Record mode) + characterization.

The companion logic_capture.py is limited to one on-device buffer (16384
samples on the AD3) -> sub-millisecond windows at high sample rates. That is
useless for catching *intermittent* traffic: boot strings, a UART byte sent
when you press a button, an encoder turn, a periodic status poll.

This script uses DigitalIn Record mode, which streams samples over USB
continuously, so you can capture for SECONDS. Run it, and DURING the capture
make the event happen (power-cycle the PSU, turn an encoder, press output
on/off). Then read the per-channel summary.

Wiring + ground rules identical to logic_capture.py (AD3 GND mandatory).
Close the WaveForms GUI first — only one app can own the AD3.

Examples
--------
  # 1 MHz for 5 s on DIO1..8 (catches up to ~115200 baud cleanly)
  python record_capture.py --channels 1-8 --rate 1e6 --seconds 5

  # power-cycle catch: start it, then flip the PSU mains switch
  python record_capture.py --channels 1-8 --rate 1e6 --seconds 8 --save boot.npy
"""

import argparse
import sys
import time

from pydwf import DwfLibrary, DwfAcquisitionMode, DwfState
from pydwf.utilities import openDwfDevice


def parse_channels(spec):
    out = set()
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return sorted(out)


def record(device, rate_hz, seconds):
    """Stream DigitalIn for `seconds`, return (samples, actual_rate, lost, corrupt)."""
    din = device.digitalIn
    din.reset()

    base = din.internalClockInfo()
    divider = max(1, round(base / rate_hz))
    actual_rate = base / divider
    din.dividerSet(divider)
    din.sampleFormatSet(16)

    din.acquisitionModeSet(DwfAcquisitionMode.Record)
    # No recordLengthSet on digitalIn in this pydwf build; stream unbounded and
    # bound the capture by wall clock + draining statusRecord below.
    din.configure(False, True)

    samples = []
    lost_total = 0
    corrupt_total = 0
    t0 = time.time()
    # let the acquisition actually start before timing
    while True:
        st = din.status(True)
        if st in (DwfState.Triggered, DwfState.Running, DwfState.Done):
            break
        if time.time() - t0 > 3:
            break
        time.sleep(0.001)

    t0 = time.time()
    while time.time() - t0 < seconds:
        st = din.status(True)
        available, lost, corrupt = din.statusRecord()
        lost_total += lost
        corrupt_total += corrupt
        if available == 0:
            if st == DwfState.Done:
                break
            time.sleep(0.001)
            continue
        chunk = din.statusData(available)
        samples.extend(chunk)
    return samples, actual_rate, lost_total, corrupt_total


def characterize(samples, rate_hz, channel):
    mask = 1 << channel
    bits = [(s & mask) >> channel for s in samples]
    n = len(bits)
    if n == 0:
        return f"ch{channel:2d}: (no samples)"
    ones = sum(1 for b in bits if b)
    edges = 0
    runs = []
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
        return f"ch{channel:2d}: idle {level}  (no activity over whole window)"

    min_run = min(r for r in runs if r > 0)
    bit_period_s = min_run / rate_hz
    bit_rate = 1.0 / bit_period_s if bit_period_s else 0
    duty = 100.0 * ones / n
    regular = (max(runs) <= 3 * min_run)
    role = "clock?" if regular and edges > n / 50 else "data/burst?"
    idle = "HIGH" if bits[0] == 1 else "LOW"

    return (f"ch{channel:2d}: idle {idle}  {edges:7d} edges  duty {duty:4.0f}%  "
            f"min-pulse {bit_period_s*1e9:8.0f} ns  ~{bit_rate/1e3:9.1f} kbit/s  [{role}]")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--channels", default="1-8")
    p.add_argument("--rate", type=float, default=1e6, help="sample rate Hz")
    p.add_argument("--seconds", type=float, default=5.0)
    p.add_argument("--save", default=None, help="dump raw uint16 samples to .npy")
    args = p.parse_args()

    channels = parse_channels(args.channels)
    dwf = DwfLibrary()
    print(f"Recording {args.seconds:.1f}s @ ~{args.rate/1e6:.3f} MHz on DIO {channels} ...")
    print(">>> MAKE THE EVENT HAPPEN NOW (power-cycle / turn encoder / press button) <<<")
    try:
        with openDwfDevice(dwf) as device:
            samples, rate, lost, corrupt = record(device, args.rate, args.seconds)
    except Exception as e:
        msg = str(e).lower()
        if "another application" in msg or "djtgenable" in msg or "jtag init" in msg:
            print("FAIL: AD3 is in use — close the WaveForms GUI first.")
            return 2
        raise

    n = len(samples)
    span_ms = 1000.0 * n / rate if rate else 0
    print(f"\ncaptured {n} samples @ {rate/1e6:.3f} MHz  ({span_ms:.1f} ms window)")
    if lost or corrupt:
        print(f"!! lost={lost} corrupt={corrupt} samples — lower --rate if these are large")
    print()
    for ch in channels:
        print(characterize(samples, rate, ch))

    if args.save and n:
        import numpy as np
        np.save(args.save, np.array(samples, dtype="uint16"))
        print(f"\nraw samples -> {args.save} (uint16, bit k = DIO k)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
