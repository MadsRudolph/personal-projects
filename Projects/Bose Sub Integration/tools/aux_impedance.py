#!/usr/bin/env python3
"""Sweep the input impedance of the Bose Companion 5 aux jack with the AD3.

Wiring (W1 -> R_ref -> DUT -> GND):

    W1 (yellow) ---+--- R_ref ---+--- AUX WHITE (tip)
                   |             |
              1+ (orange)   2+ (blue)
                   |             |
    GND (black) ---+-------------+--- AUX SHIELD (sleeve)
                   |             |
              1- (orange/wht) 2- (blue/wht)

BOTH scope negatives must go to ground. The AD3 inputs are differential; a
floating negative reads garbage.

This does NOT use the WaveForms built-in impedance analyser. The Bose input
sits on a mains-powered amplifier and injects tens of millivolts of hum onto
the node, which swamps a low-amplitude broadband measurement. Instead we drive
a sine at one frequency, capture both channels, and extract the complex phasor
at exactly that frequency with a windowed DFT. Everything that is not the test
tone -- hum, its harmonics, broadband noise -- is rejected.

    Z = R_ref * V2 / (V1 - V2)      as complex phasors

Usage:

    py -3.13 aux_impedance.py --ref 9800 --out ring_open.csv
    py -3.13 aux_impedance.py --ref 9800 --out ring_grounded.csv

What we are looking for: |Z| flat from 20 Hz to 1 kHz means no input coupling
capacitor, which is what we need. |Z| climbing toward low frequency with the
phase going capacitive (negative) means a series cap is high-passing the input,
and where |Z| has risen 3 dB is the corner. A corner above ~20 Hz fails gate 1.
"""

import argparse
import csv
import math
import time

import numpy as np
from pydwf import (DwfLibrary, DwfAnalogOutNode, DwfAnalogOutFunction,
                   DwfAcquisitionMode, DwfState)
from pydwf.utilities import openDwfDevice

BUFFER = 16384


def phasor(x, fs, f0):
    """Complex amplitude of x at exactly f0, rejecting everything else."""
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    t = np.arange(len(x)) / fs
    w = np.hanning(len(x))
    return np.sum(x * w * np.exp(-2j * np.pi * f0 * t)) / np.sum(w) * 2


def acquire(device, hz, amp, vrange, cycles, max_window):
    """Drive one frequency, return (V1, V2) phasors and residual noise."""
    wavegen, scope = device.analogOut, device.analogIn

    wavegen.nodeFrequencySet(0, DwfAnalogOutNode.Carrier, hz)
    wavegen.nodeAmplitudeSet(0, DwfAnalogOutNode.Carrier, amp)
    wavegen.configure(0, True)

    # Window long enough for `cycles` periods, but bounded so 10 Hz does not
    # take forever. Sample rate follows from the fixed buffer length.
    window = min(max(cycles / hz, 0.02), max_window)
    fs = BUFFER / window

    scope.frequencySet(fs)
    scope.bufferSizeSet(BUFFER)
    for ch in (0, 1):
        scope.channelRangeSet(ch, vrange)
    scope.configure(True, True)

    time.sleep(0.02 + window * 0.1)
    while scope.status(True) != DwfState.Done:
        time.sleep(0.002)

    ch1 = scope.statusData(0, BUFFER)
    ch2 = scope.statusData(1, BUFFER)

    v1, v2 = phasor(ch1, fs, hz), phasor(ch2, fs, hz)

    # How much of ch2 is NOT our tone -- the hum we are rejecting.
    resid = math.sqrt(max(np.var(ch2) - abs(v2) ** 2 / 2, 0.0))
    return v1, v2, resid


def fmt_ohms(z):
    if not math.isfinite(z):
        return "   ---   "
    if abs(z) >= 1e6:
        return f"{z / 1e6:8.3f}M"
    if abs(z) >= 1e3:
        return f"{z / 1e3:8.3f}k"
    return f"{z:9.1f}"


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", type=float, default=9800.0,
                    help="reference resistor in ohms (measure it)")
    ap.add_argument("--amp", type=float, default=0.5,
                    help="drive amplitude in volts (default 500 mV)")
    ap.add_argument("--start", type=float, default=10.0)
    ap.add_argument("--stop", type=float, default=20000.0)
    ap.add_argument("--steps", type=int, default=45)
    ap.add_argument("--cycles", type=float, default=24.0,
                    help="periods to integrate per point")
    ap.add_argument("--max-window", type=float, default=1.0,
                    help="cap on acquisition time per point, seconds")
    ap.add_argument("--range", type=float, default=2.0, help="scope range, volts")
    ap.add_argument("--out", help="write results to this CSV")
    a = ap.parse_args()

    freqs = np.logspace(math.log10(a.start), math.log10(a.stop), a.steps)
    rows = []

    with openDwfDevice(DwfLibrary()) as device:
        wavegen, scope = device.analogOut, device.analogIn

        wavegen.reset(-1)
        wavegen.nodeEnableSet(0, DwfAnalogOutNode.Carrier, True)
        wavegen.nodeFunctionSet(0, DwfAnalogOutNode.Carrier,
                                DwfAnalogOutFunction.Sine)
        wavegen.nodeOffsetSet(0, DwfAnalogOutNode.Carrier, 0.0)

        scope.reset()
        for ch in (0, 1):
            scope.channelEnableSet(ch, True)
            scope.channelOffsetSet(ch, 0.0)
        scope.acquisitionModeSet(DwfAcquisitionMode.Single)

        print(f"R_ref = {a.ref:.0f} ohm   drive = {a.amp * 1000:.0f} mV   "
              f"coherent DFT, {a.cycles:.0f} cycles/point")
        print(f"\n{'Hz':>9}  {'|Z|':>10}  {'phase':>9}  {'R':>10}  {'X':>10}  "
              f"{'V1mV':>7}  {'V2mV':>7}  {'hum':>6}")
        print("-" * 82)

        for hz in freqs:
            v1, v2, resid = acquire(device, float(hz), a.amp, a.range,
                                    a.cycles, a.max_window)
            denom = v1 - v2
            z = a.ref * v2 / denom if abs(denom) > 1e-9 else complex(float("inf"))
            rows.append(dict(hz=float(hz), z=abs(z),
                             phase=math.degrees(np.angle(z)),
                             r=z.real, x=z.imag,
                             v1=abs(v1), v2=abs(v2), hum=resid))
            print(f"{hz:9.2f}  {fmt_ohms(abs(z))}  "
                  f"{math.degrees(np.angle(z)):7.1f}deg  "
                  f"{fmt_ohms(z.real)}  {fmt_ohms(z.imag)}  "
                  f"{abs(v1) * 1000:7.1f}  {abs(v2) * 1000:7.1f}  "
                  f"{resid * 1000:6.1f}")

        wavegen.configure(0, False)

    if a.out:
        with open(a.out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["hz", "z", "phase", "r", "x",
                                              "v1", "v2", "hum"])
            w.writeheader()
            w.writerows(rows)
        print(f"\nwrote {a.out}")

    hz = np.array([r["hz"] for r in rows])
    z = np.array([r["z"] for r in rows])
    v1 = np.array([r["v1"] for r in rows])
    v2 = np.array([r["v2"] for r in rows])

    print("\n--- rig check ---")
    ratio = float(np.median(v2 / np.where(v1 == 0, np.nan, v1)))
    if np.nanmax(v1) < 0.01:
        print("!! ch1 sees nothing -- 1+ not on the W1 row, or 1- not grounded.")
        return 1
    if ratio > 0.99:
        print(f"!! V2/V1 = {ratio:.4f} -- DUT open. Only the scope's own ~2M")
        print("   input is on the node. Check the pin, the joint, the jack.")
        return 1
    if ratio < 0.01:
        print(f"!! V2/V1 = {ratio:.4f} -- DUT shorted.")
        return 1
    print(f"OK  V2/V1 = {ratio:.4f}, both channels alive.")

    z_1k = float(np.interp(1000.0, hz, z))
    print(f"\n|Z| at 1 kHz  : {fmt_ohms(z_1k).strip()}")
    for probe in (100.0, 20.0):
        if hz[0] <= probe <= hz[-1]:
            zp = float(np.interp(probe, hz, z))
            rise = 20 * math.log10(zp / z_1k) if z_1k > 0 else 0.0
            print(f"|Z| at {probe:5.0f} Hz : {fmt_ohms(zp).strip():>10}"
                  f"   ({rise:+.1f} dB vs 1 kHz)")

    # Where has |Z| risen 3 dB above its midband value? That is the corner.
    mid = float(np.median(z[(hz > 500) & (hz < 5000)]))
    low = hz < 500
    over = hz[low][z[low] > mid * math.sqrt(2)]
    print()
    if over.size:
        print(f"Series coupling cap present -- |Z| is +3 dB by {over.max():.1f} Hz.")
        print("GATE 1 FAILS" if over.max() > 20 else "Corner below 20 Hz: gate 1 passes.")
    else:
        print("|Z| flat to the bottom of the sweep -- no input coupling cap.")
        print("GATE 1 PASSES.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
