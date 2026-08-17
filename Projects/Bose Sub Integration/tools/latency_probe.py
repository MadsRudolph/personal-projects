#!/usr/bin/env python3
"""Test 0.3b -- measure DSP latency through the Companion 5, aux in -> phones out.

This is the gate that decides the architecture. If the Bose digitises the aux
input to run its processing, the delay shows up here and no analog polarity
switch can fix the crossover handoff.

Wiring (NO reference resistor -- W1 drives the aux jack directly):

    W1 (yellow) ---+--- AUX WHITE (tip)      [+ AUX RED too, if --both]
                   |
              1+ (orange)
                   |
    GND (black) ---+--- AUX SHIELD  ---  1- (orange/wht)

    PHONES TIP  ---+--- 2+ (blue)
                   |
                  47R           (dummy load)
                   |
    PHONES SLEEVE -+--- 2- (blue/wht)  --- GND

Delay is found by cross-correlating the two captures, which locates the
alignment to a fraction of a sample rather than by eye on a cursor.

    python latency_probe.py                  # tip only
    python latency_probe.py --label tip+ring # after tying red to tip

Verdict thresholds:
    < 0.2 ms   analog path, no DSP          -> gate 2 passes
    0.2-3 ms   borderline, 0.4 decides
    > 3 ms     digitiser present            -> gate 2 fails, pivot
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

WAVES = {"square": DwfAnalogOutFunction.Square,
         "sine": DwfAnalogOutFunction.Sine}


def coherent_amp(x, fs, f0):
    x = np.asarray(x, float)
    x = x - x.mean()
    t = np.arange(len(x)) / fs
    w = np.hanning(len(x))
    return abs(np.sum(x * w * np.exp(-2j * np.pi * f0 * t)) / np.sum(w) * 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hz", type=float, default=5.0,
                    help="drive frequency; the period must be much longer "
                         "than any delay we might find")
    ap.add_argument("--amp", type=float, default=0.2, help="volts")
    ap.add_argument("--wave", choices=tuple(WAVES), default="square")
    ap.add_argument("--maxlag", type=float, default=60.0,
                    help="largest delay to search for, ms")
    ap.add_argument("--rate", type=float, default=20e3)
    ap.add_argument("--samples", type=int, default=16384)
    ap.add_argument("--range", type=float, default=5.0)
    ap.add_argument("--label", default="tip only")
    a = ap.parse_args()

    with openDwfDevice(DwfLibrary()) as device:
        wavegen, scope = device.analogOut, device.analogIn

        wavegen.reset(-1)
        wavegen.nodeEnableSet(0, DwfAnalogOutNode.Carrier, True)
        wavegen.nodeFunctionSet(0, DwfAnalogOutNode.Carrier, WAVES[a.wave])
        wavegen.nodeFrequencySet(0, DwfAnalogOutNode.Carrier, a.hz)
        wavegen.nodeAmplitudeSet(0, DwfAnalogOutNode.Carrier, a.amp)
        wavegen.nodeOffsetSet(0, DwfAnalogOutNode.Carrier, 0.0)
        wavegen.configure(0, True)

        scope.reset()
        for ch in (0, 1):
            scope.channelEnableSet(ch, True)
            scope.channelRangeSet(ch, a.range)
            scope.channelOffsetSet(ch, 0.0)
        scope.acquisitionModeSet(DwfAcquisitionMode.Single)
        scope.frequencySet(a.rate)
        scope.bufferSizeSet(a.samples)
        scope.configure(True, True)

        time.sleep(0.2 + a.samples / a.rate)
        while scope.status(True) != DwfState.Done:
            time.sleep(0.005)

        ch1 = np.array(scope.statusData(0, a.samples))
        ch2 = np.array(scope.statusData(1, a.samples))
        wavegen.configure(0, False)

    window = a.samples / a.rate
    x = ch1 - ch1.mean()
    y = ch2 - ch2.mean()

    if np.std(y) < 1e-4:
        print("\nch2 is silent. Check the phones plug, the pod volume knob,")
        print("and that 2+ is on the headphone tip.")
        return 1

    # Cross-correlate to find the time alignment.
    #
    # A periodic drive correlates equally well at every period, so the search
    # MUST be restricted to a causally plausible window -- otherwise the peak
    # lands an arbitrary number of periods away. Keep the drive period well
    # longer than any delay we could plausibly find.
    xc = np.correlate(y / np.std(y), x / np.std(x), mode="full")
    lags = np.arange(-len(x) + 1, len(x)) / a.rate
    band = (lags >= -0.002) & (lags <= a.maxlag / 1000.0)
    if a.maxlag / 1000.0 > 0.4 / a.hz:
        print(f"\n!! --maxlag {a.maxlag:.0f} ms exceeds 40% of the "
              f"{1000 / a.hz:.0f} ms drive period.")
        print("   Lower --hz or --maxlag, or the search will alias.")
    k = int(np.argmax(np.abs(np.where(band, xc, 0.0))))
    delay = lags[k]
    quality = abs(xc[k]) / len(x)
    inverting = xc[k] < 0

    amp1 = coherent_amp(ch1, a.rate, a.hz)
    amp2 = coherent_amp(ch2, a.rate, a.hz)

    print(f"\n=== 0.3b  [{a.label}] ===")
    print(f"drive     : {a.wave} {a.hz:.0f} Hz, {a.amp * 1000:.0f} mV")
    print(f"window    : {window * 1000:.1f} ms at {a.rate / 1e3:.0f} kS/s"
          f"   ({1e6 / a.rate:.1f} us resolution)")
    print(f"\nch1 amp @ {a.hz:.0f} Hz : {amp1 * 1000:8.2f} mV")
    print(f"ch2 amp @ {a.hz:.0f} Hz : {amp2 * 1000:8.2f} mV")
    print(f"gain aux->phones : {20 * np.log10(amp2 / amp1):+.2f} dB"
          if amp1 > 0 else "")
    # Is the generator actually delivering what we asked for?
    expected = a.amp * (4 / np.pi if a.wave == "square" else 1.0)
    if amp1 < 0.8 * expected:
        print(f"\n!! ch1 is {amp1 * 1000:.0f} mV but the drive should give "
              f"{expected * 1000:.0f} mV.")
        print("   W1 is being loaded down. Something low-resistance is across")
        print("   the drive node -- check the dummy load is on the PHONES row,")
        print("   not on the W1 row. Fix before trusting anything below.")

    if amp2 < 0.005:
        print(f"\n!! ch2 is only {amp2 * 1000:.2f} mV. At this level, capacitive")
        print("   coupling between adjacent wires is as big as the real signal --")
        print("   and crosstalk has ZERO delay, so it fakes a clean PASS.")
        print("   Control test: unplug the PHONES plug from the pod and re-run.")
        print("   If ch2 still shows this level, you are measuring your wiring.")

    if a.wave != "square":
        print(f"\nNo delay verdict for a {a.wave} drive: cross-correlation of a")
        print("periodic signal is ambiguous -- it peaks once per period, so the")
        print("result is indistinguishable from a polarity inversion. Levels")
        print("above are valid; re-run with --wave square for timing.")
        return 0

    print(f"\ndelay ch1 -> ch2 : {delay * 1000:+.4f} ms"
          f"   (correlation {quality:.3f})")
    print(f"polarity         : {'INVERTING' if inverting else 'non-inverting'}"
          f"   (searched 0 to {a.maxlag:.0f} ms)")

    ms = abs(delay) * 1000
    print()
    if abs(delay) > 0.9 * a.maxlag / 1000.0:
        print("UNRELIABLE -- the peak sits against the edge of the search")
        print("window, which usually means the true peak is outside it or the")
        print("correlation is being driven by waveform shape, not timing.")
        return 1
    if quality < 0.8:
        print(f"UNRELIABLE -- correlation only {quality:.2f}. ch2 is not the")
        print("same shape as ch1, so the path is distorting the drive and the")
        print("lag is not a delay measurement. Most likely an AC-coupling")
        print("high-pass differentiating the square: remove the dummy load")
        print("across the output, or raise --hz above the coupling corner.")
        return 1
    if quality < 0.2:
        print("WEAK CORRELATION -- the delay figure is not trustworthy.")
        print("Raise --amp, or check that ch2 really is the phones output.")
    elif ms < 0.2:
        print(f"PASS  {ms:.3f} ms -- analog path, no DSP in the aux chain.")
        print("Gate 2 passes: an analog crossover with a polarity switch is viable.")
    elif ms < 3.0:
        print(f"BORDERLINE  {ms:.3f} ms. Note it; test 0.4 decides.")
        print(f"At 60 Hz that is {360 * 0.06 * ms:.0f} deg of phase rotation.")
    else:
        print(f"FAIL  {ms:.3f} ms -- a digitiser is in the path.")
        print(f"At 60 Hz that is {360 * 0.06 * ms:.0f} deg of rotation, which no")
        print("polarity switch can correct. Pivot to miniDSP or re-amping.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
