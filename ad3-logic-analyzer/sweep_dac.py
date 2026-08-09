#!/usr/bin/env python3
"""Guided DAC sweep for the KORAD KD3005D front board.

Walks you through a series of setpoints, capturing the 74HC595 DAC word the
MCU writes at each one, then works out which bits are the voltage field and
which are the current field and fits code -> setpoint.

Wiring (U14, the first 595 in the chain):
    pin 11 SHCP -> DIO0        pin 12 STCP -> DIO1
    pin 14 DS   -> DIO2        pin  8 GND  -> AD3 ground

The device is held open for the whole sweep. For each point you are told what
to do; the capture arms, you click the knob, and the word is decoded and shown
immediately so a bad capture can be retried on the spot.

Close the WaveForms GUI first.

  python sweep_dac.py                         # default V and I sweeps
  python sweep_dac.py --v 0,5,10,20,30        # custom voltage points
  python sweep_dac.py --i 0.5,2.5,5.0 --v ""  # current sweep only
  python sweep_dac.py --analyse-only          # re-analyse existing captures
"""

import argparse
import os
import sys
import time

import numpy as np
from pydwf import DwfLibrary, DwfAcquisitionMode, DwfState, DwfTriggerSource
from pydwf.utilities import openDwfDevice

from decode_595 import decode_array

EXPECT_CLOCKS = 24
CHANNELS = [0, 1, 2]


# ----------------------------------------------------------------- capture

def force_inputs(device):
    """Put every DIO pin in high-impedance INPUT mode.

    digitalIn.reset() only resets the logic analyzer. If a previous WaveForms
    GUI session (Static I/O, Pattern Generator) left pins enabled as outputs,
    they keep DRIVING — which fights whatever you are probing. On the KORAD
    DAC bus that corrupts every word the MCU writes. Always call this first.
    """
    dio = device.digitalIO
    dio.reset()
    dio.outputEnableSet(0)          # 0 = all pins are inputs
    still_driving = dio.outputEnableGet()
    if still_driving:
        print(f"  WARNING: DIO output-enable is still 0x{still_driving:04X} "
              f"— pins may be driving the target!")
    return still_driving


def arm(din, n, prefill):
    mask = 0
    for ch in CHANNELS:
        mask |= 1 << ch
    din.reset()
    base = din.internalClockInfo()
    divider = max(1, round(base / 50e6))
    rate = base / divider
    din.dividerSet(divider)
    din.sampleFormatSet(16)
    din.bufferSizeSet(n)
    din.acquisitionModeSet(DwfAcquisitionMode.Single)
    din.triggerSourceSet(DwfTriggerSource.DetectorDigitalIn)
    din.triggerSet(0, 0, mask, mask)
    din.triggerPositionSet(int(n * (1.0 - prefill)))
    din.configure(False, True)
    return rate


def wait_trigger(din, n, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if din.status(True) == DwfState.Done:
            return np.asarray(din.statusData(n), dtype=np.uint16)
        time.sleep(0.005)
    return None


def capture_point(din, n, prefill, timeout, label, target, unit):
    """Guide one setpoint, return (raw, decoded) or (None, None) if skipped."""
    while True:
        print(f"\n--- {label} ---")
        input(f"  Set the {unit} to just BELOW {target}, then press Enter to arm... ")
        arm(din, n, prefill)
        print(f"  ARMED.  >>> now click UP onto {target} <<<")
        raw = wait_trigger(din, n, timeout)

        if raw is None:
            print("  !! no edge seen — nothing was written to the DAC.")
        else:
            d = decode_array(raw)
            full = [w for w in (d["words"] if d else []) if len(w) == EXPECT_CLOCKS]
            print(f"  captured: {d['clocks']} clocks, {d['latches']} latch pulse(s)")
            if len(full) == 1:
                s = "".join(str(b) for b in full[0])
                v = int(s, 2)
                print(f"  word: {s}  = 0x{v:06X}")
                print(f"  bytes: {s[0:8]} {s[8:16]} {s[16:24]}")
                return raw, s
            print(f"  !! expected one {EXPECT_CLOCKS}-bit word, got {len(full)}.")

        ans = input("  [r]etry, [s]kip, [a]bort? ").strip().lower() or "r"
        if ans.startswith("s"):
            return None, None
        if ans.startswith("a"):
            raise KeyboardInterrupt


# ---------------------------------------------------------------- analysis

def varying_bits(words):
    """Bit positions that are not identical across all words."""
    if len(words) < 2:
        return []
    return [i for i in range(len(words[0]))
            if len({w[i] for w in words}) > 1]


def field_value(word, positions, reverse=False):
    bits = "".join(word[i] for i in positions)
    if reverse:
        bits = bits[::-1]
    return int(bits, 2) if bits else 0


def fit(codes, values):
    """Least-squares fit codes -> values. Returns (slope, intercept, r2)."""
    if len(codes) < 2:
        return None
    x = np.asarray(codes, float)
    y = np.asarray(values, float)
    if np.allclose(x, x[0]):
        return None
    m, c = np.polyfit(x, y, 1)
    resid = y - (m * x + c)
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return m, c, r2


def analyse(series, name, unit):
    """series = list of (setpoint, 24-bit string)."""
    if len(series) < 2:
        print(f"\n{name}: need at least 2 captures to analyse.")
        return
    pts = [s for s, _ in series]
    words = [w for _, w in series]

    print(f"\n=== {name} sweep ===")
    for s, w in series:
        print(f"  {s:8.3f} {unit}   {w}  0x{int(w, 2):06X}")

    changing = varying_bits(words)
    mark = "".join("^" if i in changing else "." for i in range(24))
    print(f"  {'':8s}      {mark}")
    print(f"  bits that change: {changing if changing else 'none'}")

    if not changing:
        return

    best = None
    for rev in (False, True):
        codes = [field_value(w, changing, rev) for w in words]
        f = fit(codes, pts)
        if f and (best is None or f[2] > best[0][2]):
            best = (f, rev, codes)

    if best is None:
        print("  could not fit (codes constant)")
        return

    (m, c, r2), rev, codes = best
    order = "LSB-first" if rev else "MSB-first"
    print(f"\n  changing bits {changing[0]}..{changing[-1]} "
          f"({len(changing)} bits, best as {order})")
    print(f"  codes: {codes}")
    print(f"  fit:   {unit} = {m:.6g} * code + {c:.6g}     R^2 = {r2:.6f}")

    # Two points always fit a line exactly, and a field boundary cannot be
    # located from a single transition. Refuse to draw conclusions.
    if len(series) < 3:
        print("  -> ONLY 2 POINTS. The fit is degenerate (any 2 points are "
              "collinear) and the\n     field extent is unknown. Capture at "
              "least 3, ideally 5, before believing this.")
    elif r2 > 0.9999:
        print(f"  -> LINEAR. resolution {abs(m):.4g} {unit}/LSB, "
              f"full scale {abs(m) * (2 ** len(changing) - 1) + c:.3f} {unit}")
    else:
        print("  -> NOT clean-linear; field split or bit order may be wrong.")


# -------------------------------------------------------------------- main

def parse_points(s):
    return [float(x) for x in s.split(",") if x.strip()] if s.strip() else []


def load_series(outdir, prefix):
    out = []
    if not os.path.isdir(outdir):
        return out
    for fn in sorted(os.listdir(outdir)):
        if not (fn.startswith(prefix) and fn.endswith(".npy")):
            continue
        try:
            sp = float(fn[len(prefix):-4].replace("_", "."))
        except ValueError:
            continue
        d = decode_array(np.load(os.path.join(outdir, fn)))
        full = [w for w in (d["words"] if d else []) if len(w) == EXPECT_CLOCKS]
        if len(full) == 1:
            out.append((sp, "".join(str(b) for b in full[0])))
    return sorted(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--v", default="0,1,5,10,20,30", help="voltage setpoints (V)")
    p.add_argument("--i", default="0.5,2.5,5.0", help="current setpoints (A)")
    p.add_argument("--outdir", default="dac_captures")
    p.add_argument("--wait", type=float, default=60.0)
    p.add_argument("--prefill", type=float, default=0.1)
    p.add_argument("--analyse-only", action="store_true")
    a = p.parse_args()

    os.makedirs(a.outdir, exist_ok=True)

    if not a.analyse_only:
        vpts, ipts = parse_points(a.v), parse_points(a.i)
        print(f"Sweep: {len(vpts)} voltage points, {len(ipts)} current points.")
        print("Captures are validated as they land; you can retry any that fail.\n")
        print("IMPORTANT: leave the CURRENT knob alone during the voltage sweep,")
        print("and the VOLTAGE knob alone during the current sweep.")

        dwf = DwfLibrary()
        try:
            with openDwfDevice(dwf) as device:
                force_inputs(device)
                din = device.digitalIn
                n = min(16384, din.bufferSizeInfo())
                try:
                    for sp in vpts:
                        raw, word = capture_point(
                            din, n, a.prefill, a.wait,
                            f"VOLTAGE {sp:.2f} V", f"{sp:.2f} V", "voltage")
                        if raw is not None:
                            np.save(os.path.join(
                                a.outdir, f"v_{sp:.2f}".replace(".", "_") + ".npy"), raw)

                    if ipts:
                        print("\n" + "=" * 60)
                        print("Now the CURRENT sweep. Set the voltage to 5.00 V and")
                        print("leave it there for all remaining points.")
                        input("Press Enter when ready... ")
                    for sp in ipts:
                        raw, word = capture_point(
                            din, n, a.prefill, a.wait,
                            f"CURRENT {sp:.3f} A", f"{sp:.3f} A", "current")
                        if raw is not None:
                            np.save(os.path.join(
                                a.outdir, f"i_{sp:.3f}".replace(".", "_") + ".npy"), raw)
                except KeyboardInterrupt:
                    print("\naborted — analysing what was captured.")
        except Exception as e:
            msg = str(e).lower()
            if "another application" in msg or "djtgenable" in msg or "jtag init" in msg:
                print("FAIL: AD3 is in use — close the WaveForms GUI first.")
                return 2
            raise

    analyse(load_series(a.outdir, "v_"), "VOLTAGE", "V")
    analyse(load_series(a.outdir, "i_"), "CURRENT", "A")

    vs, is_ = load_series(a.outdir, "v_"), load_series(a.outdir, "i_")
    if vs and is_:
        vb = set(varying_bits([w for _, w in vs]))
        ib = set(varying_bits([w for _, w in is_]))
        print("\n=== field map ===")
        print("  " + "".join("V" if i in vb - ib else
                             "I" if i in ib - vb else
                             "?" if i in vb & ib else "." for i in range(24)))
        print("  V = voltage-only bits, I = current-only bits,")
        print("  ? = changes in both (suspicious), . = constant")
    return 0


if __name__ == "__main__":
    sys.exit(main())
