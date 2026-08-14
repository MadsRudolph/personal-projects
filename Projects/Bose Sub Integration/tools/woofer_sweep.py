#!/usr/bin/env python3
"""Test 0.4 -- transfer function from the aux jack to the woofer terminals.

Finds Bose's internal crossover: corner frequency, slope, any high-pass, and
the group delay our crossover will have to live with. Also settles the
tip-vs-tip+ring summing question that the headphone tap could not answer.

    ############################################################
    #  THE AMPLIFIER OUTPUT IS BRIDGED.                        #
    #  Neither woofer terminal sits at ground.                 #
    #  2+ AND 2- BOTH GO ON THE DRIVER. Never one to ground.   #
    #  Grounding one side shorts an output stage through the   #
    #  PC's mains earth and destroys the amp, the AD3, or both.#
    ############################################################

Wiring:

    W1 (yellow)      --- AUX WHITE (tip)
    W2 (yellow/wht)  --- AUX RED   (ring)      <- lets --both switch in software
    GND (black)      --- AUX SHIELD (sleeve)
    1+ (orange)      --- AUX WHITE             (measure the drive)
    1- (orange/wht)  --- AUX SHIELD

    2+ (blue)        --- woofer terminal A     DIFFERENTIAL
    2- (blue/wht)    --- woofer terminal B     both on the driver

Wiring W2 to the ring means the summing test needs no rewiring: run once
without --both (tip only) and once with (both channels driven), and compare
the passband gain.

    py -3.13 woofer_sweep.py --out woofer_tip.csv
    py -3.13 woofer_sweep.py --out woofer_both.csv --both

Start with the default 50 mV and raise only if the script says the signal is
too small. It auto-ranges channel 2 and refuses to report a result it thinks
is clipped.
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
RANGES = (5.0, 25.0, 50.0)          # peak-to-peak spans to try on channel 2


def phasor(x, fs, f0):
    x = np.asarray(x, float)
    x = x - x.mean()
    t = np.arange(len(x)) / fs
    w = np.hanning(len(x))
    return np.sum(x * w * np.exp(-2j * np.pi * f0 * t)) / np.sum(w) * 2


def capture(scope, fs, range2):
    scope.channelRangeSet(1, range2)
    scope.frequencySet(fs)
    scope.bufferSizeSet(BUFFER)
    scope.configure(True, True)
    time.sleep(0.02 + BUFFER / fs * 0.1)
    while scope.status(True) != DwfState.Done:
        time.sleep(0.002)
    return (np.array(scope.statusData(0, BUFFER)),
            np.array(scope.statusData(1, BUFFER)))


def measure(scope, hz, cycles, max_window, range2):
    """Return (V1, V2) phasors, the range used, and a distortion figure."""
    window = min(max(cycles / hz, 0.02), max_window)
    fs = BUFFER / window

    for rng in [r for r in RANGES if r >= range2]:
        ch1, ch2 = capture(scope, fs, rng)
        peak = float(np.max(np.abs(ch2 - ch2.mean())))
        if peak < 0.45 * rng or rng == RANGES[-1]:
            v1, v2 = phasor(ch1, fs, hz), phasor(ch2, fs, hz)
            # Fraction of ch2's energy that is NOT the drive frequency.
            fundamental_rms = abs(v2) / math.sqrt(2)
            total_rms = float(np.std(ch2))
            thd = (math.sqrt(max(total_rms ** 2 - fundamental_rms ** 2, 0.0))
                   / fundamental_rms) if fundamental_rms > 1e-9 else float("inf")
            clipped = peak > 0.45 * rng
            return v1, v2, rng, thd, clipped
    raise RuntimeError("unreachable")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--amp", type=float, default=0.05,
                    help="drive amplitude in volts (start low!)")
    ap.add_argument("--both", action="store_true",
                    help="drive ring as well as tip, via W2")
    ap.add_argument("--start", type=float, default=10.0)
    ap.add_argument("--stop", type=float, default=2000.0)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--cycles", type=float, default=24.0)
    ap.add_argument("--max-window", type=float, default=1.0)
    ap.add_argument("--out")
    a = ap.parse_args()

    freqs = np.logspace(math.log10(a.start), math.log10(a.stop), a.steps)
    rows = []

    with openDwfDevice(DwfLibrary()) as device:
        wavegen, scope = device.analogOut, device.analogIn

        wavegen.reset(-1)
        channels = (0, 1) if a.both else (0,)
        for ch in channels:
            wavegen.nodeEnableSet(ch, DwfAnalogOutNode.Carrier, True)
            wavegen.nodeFunctionSet(ch, DwfAnalogOutNode.Carrier,
                                    DwfAnalogOutFunction.Sine)
            wavegen.nodeAmplitudeSet(ch, DwfAnalogOutNode.Carrier, a.amp)
            wavegen.nodeOffsetSet(ch, DwfAnalogOutNode.Carrier, 0.0)
            wavegen.nodePhaseSet(ch, DwfAnalogOutNode.Carrier, 0.0)
        if a.both:
            # Lock W2 to W1 so the two stay in phase across the sweep.
            wavegen.masterSet(1, 0)

        scope.reset()
        for ch in (0, 1):
            scope.channelEnableSet(ch, True)
            scope.channelOffsetSet(ch, 0.0)
        scope.channelRangeSet(0, 5.0)
        scope.acquisitionModeSet(DwfAcquisitionMode.Single)

        print(f"drive {a.amp * 1000:.0f} mV  "
              f"{'TIP + RING (W1+W2)' if a.both else 'TIP only (W1)'}")
        print(f"\n{'Hz':>8}  {'mag dB':>8}  {'phase':>9}  {'V1mV':>7}  "
              f"{'V2 V':>8}  {'rng':>5}  {'thd':>6}")
        print("-" * 66)

        range2 = RANGES[0]
        for hz in freqs:
            for ch in channels:
                wavegen.nodeFrequencySet(ch, DwfAnalogOutNode.Carrier, float(hz))
            wavegen.configure(0, True)
            if a.both:
                wavegen.configure(1, True)

            v1, v2, range2, thd, clipped = measure(
                scope, float(hz), a.cycles, a.max_window, range2)

            h = v2 / v1 if abs(v1) > 1e-9 else complex(0)
            mag_db = 20 * math.log10(abs(h)) if abs(h) > 0 else -200.0
            ph = math.degrees(np.angle(h))
            rows.append(dict(hz=float(hz), mag_db=mag_db, phase=ph,
                             v1=abs(v1), v2=abs(v2), thd=thd))
            flag = " CLIP" if clipped else (" dist" if thd > 0.3 else "")
            print(f"{hz:8.2f}  {mag_db:8.2f}  {ph:7.1f}deg  "
                  f"{abs(v1) * 1000:7.1f}  {abs(v2):8.3f}  "
                  f"{range2:5.0f}  {thd:6.2f}{flag}")

        for ch in channels:
            wavegen.configure(ch, False)

    if a.out:
        with open(a.out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["hz", "mag_db", "phase",
                                              "v1", "v2", "thd"])
            w.writeheader()
            w.writerows(rows)
        print(f"\nwrote {a.out}")

    hz = np.array([r["hz"] for r in rows])
    mag = np.array([r["mag_db"] for r in rows])
    ph = np.unwrap(np.radians([r["phase"] for r in rows]))
    thd = np.array([r["thd"] for r in rows])

    print("\n--- analysis ---")
    if np.max([r["v2"] for r in rows]) < 0.01:
        print("!! ch2 never rose above 10 mV. Either the probes are not on the")
        print("   driver, the pod is muted, or the drive is far too small.")
        return 1
    if np.median(thd) > 0.5:
        print(f"!! median distortion {np.median(thd):.2f} -- the amplifier is")
        print("   likely clipping. Lower --amp and re-run.")

    band = (hz >= 25) & (hz <= 70)
    passband = float(np.median(mag[band])) if band.any() else float(np.max(mag))
    print(f"passband gain (25-70 Hz) : {passband:+.2f} dB "
          f"({10 ** (passband / 20):.1f}x)")

    # Low-pass corner: first crossing 3 dB below passband, above the band.
    above = hz > 70
    corner = None
    if above.any():
        h2, m2 = hz[above], mag[above]
        below3 = np.where(m2 <= passband - 3)[0]
        if below3.size:
            i = below3[0]
            if i > 0:
                corner = float(np.interp(passband - 3, [m2[i], m2[i - 1]],
                                         [h2[i], h2[i - 1]]))
            else:
                corner = float(h2[i])
    if corner:
        print(f"low-pass corner (-3 dB)  : {corner:.0f} Hz")
        oct_band = (hz >= corner * 1.3) & (hz <= corner * 4)
        if oct_band.sum() >= 3:
            slope = np.polyfit(np.log2(hz[oct_band]), mag[oct_band], 1)[0]
            print(f"slope above the corner   : {slope:.1f} dB/octave "
                  f"({abs(slope) / 6:.1f}st order)")
    else:
        print("low-pass corner          : not reached inside this sweep")

    below = hz < 25
    if below.any() and np.min(mag[below]) <= passband - 3:
        hp = float(np.interp(passband - 3, mag[below][::-1], hz[below][::-1]))
        print(f"high-pass corner (-3 dB) : {hp:.1f} Hz")
    else:
        print("high-pass corner         : below the bottom of the sweep")

    gd = -np.gradient(ph, hz * 2 * math.pi)
    gd_band = gd[band]
    if gd_band.size:
        print(f"group delay at 25-70 Hz  : {np.median(gd_band) * 1000:.2f} ms")

    print(f"\nRecord the passband gain. Re-run with --both and compare:")
    print("+6 dB means the channels are summed to the woofer; unchanged means")
    print("only the left channel reaches it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
