#!/usr/bin/env python3
"""AD3 single-buffer 50 MHz capture, triggered on ANY edge of ANY channel.

For a fast burst (SPI-like) triggered by a manual event (button press). The
on-device buffer fills at full speed (no USB streaming loss). Triggers on the
first edge on any selected channel, so you just have to make the event happen
within the wait window. 16384 samples @ 50 MHz = 0.33 ms at 20 ns resolution
— enough to resolve clock/data/CS bit timing and decode a few bytes.

Close the WaveForms GUI first.

  python trig_capture.py --channels 1-8 --rate 50e6 --wait 30 --save burst.npy
"""

import argparse
import sys
import time

import numpy as np
from pydwf import DwfLibrary, DwfAcquisitionMode, DwfState, DwfTriggerSource
from pydwf.utilities import openDwfDevice


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--channels", default="1-8")
    p.add_argument("--rate", type=float, default=50e6)
    p.add_argument("--wait", type=float, default=30.0, help="seconds to wait for the trigger")
    p.add_argument("--prefill", type=float, default=0.2, help="fraction of buffer kept BEFORE trigger")
    p.add_argument("--save", default=None)
    args = p.parse_args()

    chans = []
    for part in args.channels.split(","):
        if "-" in part:
            a, b = part.split("-"); chans += list(range(int(a), int(b) + 1))
        else:
            chans.append(int(part))
    mask = 0
    for ch in chans:
        mask |= (1 << ch)

    dwf = DwfLibrary()
    try:
        with openDwfDevice(dwf) as device:
            # A previous WaveForms session (Static I/O / Pattern Generator) can
            # leave DIO pins enabled as OUTPUTS. digitalIn.reset() does not
            # clear that, so they keep driving and fight the target. Force
            # every pin to high-Z input before touching the logic analyzer.
            device.digitalIO.reset()
            device.digitalIO.outputEnableSet(0)
            if device.digitalIO.outputEnableGet():
                print("WARNING: DIO pins still driving — disconnect before probing.")

            din = device.digitalIn
            din.reset()
            base = din.internalClockInfo()
            divider = max(1, round(base / args.rate))
            rate = base / divider
            din.dividerSet(divider)
            din.sampleFormatSet(16)
            n = min(16384, din.bufferSizeInfo())
            din.bufferSizeSet(n)
            din.acquisitionModeSet(DwfAcquisitionMode.Single)
            # trigger on ANY edge of ANY selected channel
            din.triggerSourceSet(DwfTriggerSource.DetectorDigitalIn)
            din.triggerSet(0, 0, mask, mask)        # rising-mask, falling-mask = all chans
            # keep some samples before the trigger so we see the burst start
            din.triggerPositionSet(int(n * (1.0 - args.prefill)))
            din.configure(False, True)

            print(f"Armed @ {rate/1e6:.1f} MHz, {n} samples. Waiting {args.wait:.0f}s for an edge...")
            print(">>> PRESS THE OUTPUT BUTTON NOW <<<")
            t0 = time.time()
            triggered = False
            while time.time() - t0 < args.wait:
                st = din.status(True)
                if st == DwfState.Done:
                    triggered = True
                    break
                time.sleep(0.005)
            if not triggered:
                print("!! no edge seen within wait window — nothing happened on the lines.")
                return 1
            samples = np.asarray(din.statusData(n), dtype=np.uint16)
    except Exception as e:
        msg = str(e).lower()
        if "another application" in msg or "djtgenable" in msg or "jtag init" in msg:
            print("FAIL: AD3 is in use — close the WaveForms GUI first.")
            return 2
        raise

    print(f"\ncaptured {samples.size} samples @ {rate/1e6:.3f} MHz  ({1000.0*samples.size/rate:.3f} ms)")
    print()
    for ch in chans:
        bit = ((samples >> ch) & 1).astype(np.int8)
        changes = np.flatnonzero(np.diff(bit))
        edges = changes.size
        if edges == 0:
            print(f"ch{ch:2d}: idle {'HIGH' if bit[0] else 'LOW'}  (flat)")
            continue
        bounds = np.concatenate(([0], changes + 1, [bit.size]))
        runs = np.diff(bounds)
        min_run = int(runs.min())
        print(f"ch{ch:2d}: idle {'HIGH' if bit[0] else 'LOW'}  {edges:5d} edges  "
              f"min-pulse {min_run/rate*1e9:6.0f} ns (~{rate/min_run/1e6:6.2f} MHz)  "
              f"duty {100.0*int(bit.sum())/bit.size:4.0f}%")
    if args.save:
        np.save(args.save, samples)
        # also stash the rate alongside for the decoder
        with open(args.save + ".rate", "w") as f:
            f.write(str(rate))
        print(f"\nraw -> {args.save} (uint16, bit k = DIO k, rate {rate:.0f} Hz)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
