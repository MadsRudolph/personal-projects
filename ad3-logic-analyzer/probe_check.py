#!/usr/bin/env python3
"""Check that the AD3 probe wires are alive and not disturbing the target.

Run with the target powered and the probes connected, then wiggle whatever
should produce traffic (turn the KORAD voltage knob). Reports:

  * whether any DIO pin is enabled as an OUTPUT (would fight the target)
  * the pull-resistor and drive-strength settings (extra loading)
  * the distinct logic states actually seen on DIO0..2

Expected idle for the KORAD DAC tap: DS=1 STCP=0 SHCP=0.
Seeing only ONE state while the knob visibly changes the display means a
probe wire or the ground clip is off.

  python probe_check.py            # 10 s window
  python probe_check.py --seconds 20
"""

import argparse
import time

from pydwf import DwfLibrary
from pydwf.utilities import openDwfDevice

NAMES = {0: "SHCP", 1: "STCP", 2: "DS"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=10.0)
    a = ap.parse_args()

    with openDwfDevice(DwfLibrary()) as d:
        io = d.digitalIO

        oe = io.outputEnableGet()
        print(f"output-enable before reset : 0x{oe:04X}"
              f"{'   <-- PINS WERE DRIVING' if oe & 0b111 else ''}")
        io.reset()
        io.outputEnableSet(0)
        print(f"output-enable after  reset : 0x{io.outputEnableGet():04X}")

        try:
            print(f"pull setting               : {io.pullGet()}")
        except Exception as e:
            print(f"pull setting               : (unavailable: {e})")
        try:
            drive = ", ".join(f"DIO{ch}={io.driveGet(ch)}" for ch in (0, 1, 2))
            print(f"drive strength             : {drive}")
        except Exception as e:
            print(f"drive strength             : (unavailable: {e})")

        print(f"\nWatching DIO0..2 for {a.seconds:.0f}s -- TURN THE KNOB NOW\n")
        seen = {}
        t0 = time.time()
        while time.time() - t0 < a.seconds:
            io.status()
            v = io.inputStatus() & 0b111
            seen[v] = seen.get(v, 0) + 1
            time.sleep(0.002)

        total = sum(seen.values())
        print(f"{len(seen)} distinct state(s) over {total} samples:\n")
        for s, n in sorted(seen.items(), key=lambda kv: -kv[1]):
            bits = "  ".join(f"{NAMES[k]}={(s >> k) & 1}" for k in (2, 1, 0))
            print(f"  {bits}   seen {100.0 * n / total:5.1f}%")

        print()
        if len(seen) == 1:
            only = next(iter(seen))
            if only == 0:
                print("ALL LOW and static -> ground clip or all three signal "
                      "wires are off, or the board is unpowered.")
            elif only == 0b111:
                print("ALL HIGH and static -> probes likely floating "
                      "(ground clip off).")
            else:
                print("Static. If the knob visibly changed the display, at "
                      "least one probe wire is not connected.")
            print("Expected idle is DS=1 STCP=0 SHCP=0 with bursts on change.")
        else:
            print("Traffic seen -> wiring is alive. Polling is far too slow to "
                  "catch whole words; use trig_capture.py / sweep_dac.py for that.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
