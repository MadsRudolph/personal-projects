#!/usr/bin/env python3
"""Read the KORAD DAC setpoint straight off the 74HC595 bus, right now.

Captures one 24-bit word from U14 (SHCP=DIO0, STCP=DIO1, DS=DIO2) and prints
the decoded voltage and current setpoints.

If the MCU refreshes the DAC periodically, this returns immediately with the
CURRENT setpoint and no knob-turning is needed — set the front panel to a
value, run this, and compare. That is the test for whether the bus is
continuously refreshed or only written on change.

  python read_dac.py               # one reading
  python read_dac.py --repeat 10   # ten in a row, to see if it is stable
  python read_dac.py --raw         # also print the raw word and clock counts
"""

import argparse
import time

import numpy as np
from pydwf import DwfLibrary, DwfAcquisitionMode, DwfState, DwfTriggerSource
from pydwf.utilities import openDwfDevice

from decode_595 import decode_array
from sweep_dac import deinterleave, to_units, EXPECT_CLOCKS

MASK = 0b111


def one_capture(din, n, timeout=5.0):
    din.reset()
    base = din.internalClockInfo()
    divider = max(1, round(base / 50e6))
    din.dividerSet(divider)
    din.sampleFormatSet(16)
    din.bufferSizeSet(n)
    din.acquisitionModeSet(DwfAcquisitionMode.Single)
    din.triggerSourceSet(DwfTriggerSource.DetectorDigitalIn)
    din.triggerSet(0, 0, MASK, MASK)
    din.triggerPositionSet(int(n * 0.9))
    din.configure(False, True)

    t0 = time.time()
    while time.time() - t0 < 3.0:          # wait until it really restarted
        if din.status(True) != DwfState.Done:
            break
        time.sleep(0.002)

    t0 = time.time()
    while time.time() - t0 < timeout:
        if din.status(True) == DwfState.Done:
            return np.asarray(din.statusData(n), dtype=np.uint16), time.time() - t0
        time.sleep(0.002)
    return None, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--raw", action="store_true")
    a = ap.parse_args()

    with openDwfDevice(DwfLibrary()) as dev:
        dev.digitalIO.reset()
        dev.digitalIO.outputEnableSet(0)
        din = dev.digitalIn
        n = min(16384, din.bufferSizeInfo())

        seen = []
        for k in range(a.repeat):
            raw, dt = one_capture(din, n)
            if raw is None:
                print(f"{k + 1:3d}: no trigger within timeout — bus is idle")
                continue
            d = decode_array(raw)
            full = [w for w in (d["words"] if d else []) if len(w) == EXPECT_CLOCKS]
            if len(full) != 1:
                print(f"{k + 1:3d}: {d['clocks']} clocks, "
                      f"{len(full)} full words — skipped")
                continue
            w = "".join(str(b) for b in full[0])
            vc, ic = deinterleave(w)
            v, i = to_units(w)
            seen.append(w)
            extra = f"  [{w} {d['clocks']}clk {dt*1000:.0f}ms]" if a.raw else ""
            print(f"{k + 1:3d}: V = {v:6.3f} V (code {vc:4d})   "
                  f"I = {i:6.3f} A (code {ic:4d}){extra}")
            time.sleep(0.05)

        if len(seen) > 1:
            print(f"\n{len(set(seen))} distinct word(s) across {len(seen)} reads.")
            if len(set(seen)) == 1:
                print("Stable -> the bus is refreshed continuously with the "
                      "current setpoint.\nYou can read the DAC any time; no "
                      "need to catch a knob turn.")
            else:
                print("Varying -> either the setpoint moved, or the word "
                      "carries something else too.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
