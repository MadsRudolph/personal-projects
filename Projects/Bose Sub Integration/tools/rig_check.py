#!/usr/bin/env python3
"""Confirm both AD3 scope channels are actually seeing the impedance rig.

Drives W1 with a 1 kHz sine and reports the RMS on each scope channel.
Expected with R_ref = 10k and a ~10k DUT:

    ch1  ~ the full drive amplitude   (across W1 node -> GND)
    ch2  ~ roughly half of ch1        (across the DUT only)

ch1 near zero  -> 1+ and 1- are at the same potential. Either 1+ is not in
                  the W1 row, or both leads ended up in the ground rail.
                  This produces a flat Z = -R_ref in the impedance sweep.
ch2 near ch1   -> DUT open (enamelled conductor, or wrong row).
ch2 near zero  -> DUT shorted.

    python rig_check.py
    python rig_check.py --hz 1000 --amp 0.5
Needs pydwf, which lives in the Python 3.14 install -- run this with
``python``, not ``py -3.13``. The pure-maths tools (subxo_model,
subxo_compare, plot_*) run under either.
"""

import argparse
import time

import numpy as np
from pydwf import (DwfLibrary, DwfAnalogOutNode, DwfAnalogOutFunction,
                   DwfAcquisitionMode, DwfState)
from pydwf.utilities import openDwfDevice


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hz", type=float, default=1000.0)
    ap.add_argument("--amp", type=float, default=0.5, help="volts, W1 amplitude")
    ap.add_argument("--range", type=float, default=5.0, help="scope range, volts")
    ap.add_argument("--ref", type=float, default=10000.0,
                    help="reference resistor in ohms")
    a = ap.parse_args()

    with openDwfDevice(DwfLibrary()) as device:
        wavegen = device.analogOut
        scope = device.analogIn

        wavegen.reset(-1)
        wavegen.nodeEnableSet(0, DwfAnalogOutNode.Carrier, True)
        wavegen.nodeFunctionSet(0, DwfAnalogOutNode.Carrier,
                                DwfAnalogOutFunction.Sine)
        wavegen.nodeFrequencySet(0, DwfAnalogOutNode.Carrier, a.hz)
        wavegen.nodeAmplitudeSet(0, DwfAnalogOutNode.Carrier, a.amp)
        wavegen.nodeOffsetSet(0, DwfAnalogOutNode.Carrier, 0.0)
        wavegen.configure(0, True)

        rate = 1e6
        n = 16384
        scope.reset()
        for ch in (0, 1):
            scope.channelEnableSet(ch, True)
            scope.channelRangeSet(ch, a.range)
            scope.channelOffsetSet(ch, 0.0)
        scope.acquisitionModeSet(DwfAcquisitionMode.Single)
        scope.frequencySet(rate)
        scope.bufferSizeSet(n)
        scope.configure(False, True)

        time.sleep(0.3)
        while True:
            if scope.status(True).name == "Done":
                break
            time.sleep(0.01)

        ch1 = scope.statusData(0, n)
        ch2 = scope.statusData(1, n)
        wavegen.configure(0, False)

    def coherent_amp(x, fs, f0):
        """Peak amplitude at exactly f0, rejecting hum and broadband noise."""
        x = x - np.mean(x)
        t = np.arange(len(x)) / fs
        w = np.hanning(len(x))
        phasor = np.sum(x * w * np.exp(-2j * np.pi * f0 * t)) / np.sum(w) * 2
        return np.abs(phasor), np.angle(phasor, deg=True)

    def total_rms(x):
        x = x - np.mean(x)
        return np.sqrt(np.mean(x ** 2))

    r1, ph1 = coherent_amp(ch1, rate, a.hz)
    r2, ph2 = coherent_amp(ch2, rate, a.hz)
    n1, n2 = total_rms(ch1), total_rms(ch2)

    print(f"\ndrive: {a.hz:.0f} Hz sine, {a.amp:.3f} V amplitude")
    print(f"R_ref = {a.ref:.0f} ohm\n")
    print(f"  ch1 (W1 node -> GND) : {r1 * 1000:8.2f} mV at {a.hz:.0f} Hz"
          f"   (total {n1 * 1000:7.2f} mV rms)")
    print(f"  ch2 (across DUT)     : {r2 * 1000:8.2f} mV at {a.hz:.0f} Hz"
          f"   (total {n2 * 1000:7.2f} mV rms)")
    print(f"  ch2/ch1 at drive freq: {r2 / r1:.4f}      "
          f"phase diff {ph2 - ph1:+.1f} deg")

    # Non-coherent content = hum and noise the DUT node is picking up.
    for name, coh, tot in (("ch1", r1, n1), ("ch2", r2, n2)):
        noise = max(tot ** 2 - (coh / np.sqrt(2)) ** 2, 0.0) ** 0.5
        if noise > 0.2 * coh:
            print(f"  NB {name} carries {noise * 1000:.1f} mV rms of "
                  f"non-{a.hz:.0f} Hz content (mains pickup)")

    print()
    if r1 < 0.005:
        print("  ch1 IS DEAD. 1+ and 1- are at the same potential.")
        print("  Fix: orange (1+) into the W1 / R_ref row, orange-white (1-)")
        print("  into the ground rail. Check they are not both in the rail.")
    elif r2 < 0.005:
        print("  ch2 reads nothing -> DUT shorted, or 2+ and 2- share a row.")
    elif (z_open := a.ref * r2 / max(r1 - r2, 1e-9)) > 1.2e6:
        print(f"  Implied Z = {z_open / 1e6:.2f} M -- that is the AD3's OWN input")
        print("  impedance (1M per terminal, ~2M differential). Nothing else is")
        print("  on the node: the DUT is open. Check, in this order:")
        print("    1. is the header pin actually seated in the R_ref row?")
        print("    2. is the solder joint on the wire real, or just a blob")
        print("       sitting on top of un-burnt enamel?")
        print("    3. is the plug fully home in the pod's aux jack?")
    else:
        z = a.ref * r2 / (r1 - r2)
        print(f"  Both channels alive. Implied DUT impedance ~ {z / 1000:.1f} k")
        if z > 4 * a.ref:
            print(f"  That is >>R_ref, so this number is imprecise. Re-run with")
            print(f"  --ref {min(1_000_000, round(z, -4)):.0f} for a real value.")
        else:
            print("  Rig is good -- rerun aux_impedance.py.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
