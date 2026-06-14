#!/usr/bin/env python3
"""AD3 high-rate STREAMING capture, numpy-efficient, saves raw .npy.

For resolving a fast synchronous bus (SPI-like) where the 1 MHz record gave
min-pulse pinned at 1 sample (aliased). Streams in Record mode, accumulates
chunks as numpy arrays (cheap), saves the raw uint16 stream, and prints a
fast numpy characterization. Decode offline from the .npy.

Run it, then make the event happen during the window (press OUTPUT, turn an
encoder, etc.). Close the WaveForms GUI first.

  python hires_capture.py --channels 1-8 --rate 8e6 --seconds 5 --save tog.npy
"""

import argparse
import sys
import time

import numpy as np
from pydwf import DwfLibrary, DwfAcquisitionMode, DwfState
from pydwf.utilities import openDwfDevice


def record(device, rate_hz, seconds):
    din = device.digitalIn
    din.reset()
    base = din.internalClockInfo()
    divider = max(1, round(base / rate_hz))
    actual_rate = base / divider
    din.dividerSet(divider)
    din.sampleFormatSet(16)
    din.acquisitionModeSet(DwfAcquisitionMode.Record)
    din.configure(False, True)

    chunks = []
    lost_total = corrupt_total = 0
    t0 = time.time()
    while True:
        st = din.status(True)
        if st in (DwfState.Triggered, DwfState.Running, DwfState.Done):
            break
        if time.time() - t0 > 3:
            break
        time.sleep(0.001)

    t0 = time.time()
    while time.time() - t0 < seconds:
        din.status(True)
        available, lost, corrupt = din.statusRecord()
        lost_total += lost
        corrupt_total += corrupt
        if available == 0:
            time.sleep(0.0005)
            continue
        chunk = np.asarray(din.statusData(available), dtype=np.uint16)
        chunks.append(chunk)
    samples = np.concatenate(chunks) if chunks else np.empty(0, np.uint16)
    return samples, actual_rate, lost_total, corrupt_total


def characterize_np(samples, rate_hz, channel):
    bit = ((samples >> channel) & 1).astype(np.int8)
    n = bit.size
    if n == 0:
        return f"ch{channel:2d}: (no samples)"
    changes = np.flatnonzero(np.diff(bit))         # indices where level changes
    edges = changes.size
    if edges == 0:
        lvl = "HIGH" if bit[0] else "LOW"
        return f"ch{channel:2d}: idle {lvl}  (no activity)"
    # run lengths between edges (in samples)
    bounds = np.concatenate(([0], changes + 1, [n]))
    runs = np.diff(bounds)
    min_run = int(runs.min())
    bit_period_s = min_run / rate_hz
    bit_rate = 1.0 / bit_period_s if bit_period_s else 0
    duty = 100.0 * int(bit.sum()) / n
    idle = "HIGH" if bit[0] else "LOW"
    return (f"ch{channel:2d}: idle {idle}  {edges:7d} edges  duty {duty:4.0f}%  "
            f"min-pulse {bit_period_s*1e9:8.0f} ns  ~{bit_rate/1e3:9.1f} kbit/s")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--channels", default="1-8")
    p.add_argument("--rate", type=float, default=8e6)
    p.add_argument("--seconds", type=float, default=5.0)
    p.add_argument("--save", default=None)
    args = p.parse_args()

    chans = []
    for part in args.channels.split(","):
        if "-" in part:
            a, b = part.split("-"); chans += list(range(int(a), int(b) + 1))
        else:
            chans.append(int(part))

    print(f"Recording {args.seconds:.1f}s @ ~{args.rate/1e6:.3f} MHz on DIO {chans} ...")
    print(">>> MAKE THE EVENT HAPPEN NOW <<<")
    dwf = DwfLibrary()
    try:
        with openDwfDevice(dwf) as device:
            samples, rate, lost, corrupt = record(device, args.rate, args.seconds)
    except Exception as e:
        msg = str(e).lower()
        if "another application" in msg or "djtgenable" in msg or "jtag init" in msg:
            print("FAIL: AD3 is in use — close the WaveForms GUI first.")
            return 2
        raise

    n = samples.size
    print(f"\ncaptured {n} samples @ {rate/1e6:.3f} MHz  ({1000.0*n/rate:.1f} ms window)")
    if lost or corrupt:
        print(f"!! lost={lost} corrupt={corrupt} — lower --rate if large vs {n}")
    print()
    for ch in chans:
        print(characterize_np(samples, rate, ch))
    if args.save and n:
        np.save(args.save, samples)
        print(f"\nraw -> {args.save} (uint16, bit k = DIO k, rate {rate:.0f} Hz)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
