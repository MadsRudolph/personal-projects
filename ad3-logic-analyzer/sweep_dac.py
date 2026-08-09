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

# Measured 2026-08-09. The 24-bit word is TWO INTERLEAVED 12-bit DAC fields:
# odd bit indices (1,3,..,23) = voltage, even indices (0,2,..,22) = current,
# MSB first, so index 23 is the voltage LSB and index 22 the current LSB.
# Both channels measured 2026-08-09 against the front panel.
#
# VOLTAGE  code = 106.000 * V + 36.0    exact on 1.00/5.00/7.50/8.00 V
#                                       (codes 142/566/831/884, zero residual)
# CURRENT  code = 619.787 * I + 49.19   R^2 = 0.99999995 over 0.1..5.0 A,
#                                       worst residual 0.7 mA
#
# The odd +-1 count (0.00 V reads 35 rather than 36; 4 A and 5 A each land one
# low) is the firmware interpolating its own calibration constants out of the
# 24C64 EEPROM, so the true curve is piecewise around stored points. Well below
# the display's own resolution, so a single line is the right model here.
V_SCALE, V_OFFSET = 1.0 / 106.0, 36.0
I_SCALE, I_OFFSET = 1.0 / 619.787, 49.19


def deinterleave(word):
    """Return (v_code, i_code) from a 24-bit string in shift order."""
    odd = int("".join(word[i] for i in range(24) if i % 2 == 1), 2)
    even = int("".join(word[i] for i in range(24) if i % 2 == 0), 2)
    return odd, even


def to_units(word):
    """Return (volts, amps) implied by the word, using the measured mapping."""
    v, i = deinterleave(word)
    return (v - V_OFFSET) * V_SCALE, (i - I_OFFSET) * I_SCALE


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

    # The device walks Config -> Prefill -> Armed -> (trigger) -> Done. If we
    # start polling for Done immediately, we can still see the PREVIOUS
    # acquisition's Done state and read a stale buffer — which looks exactly
    # like "it triggered before I touched the knob" and silently returns the
    # previous setpoint's word. Block until it is genuinely armed.
    # Any state other than Done proves the device has actually restarted.
    t0 = time.time()
    while time.time() - t0 < 3.0:
        if din.status(True) != DwfState.Done:
            break
        time.sleep(0.002)
    else:
        print("  WARNING: device never left Done; capture may be stale.")
    return rate


def wait_trigger(din, n, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if din.status(True) == DwfState.Done:
            return np.asarray(din.statusData(n), dtype=np.uint16)
        time.sleep(0.005)
    return None


def free_run(din, n, prefill, timeout, outdir, count):
    """Race-free capture: catch a word, THEN ask what the display reads.

    The guided flow ('set below, arm, click up') races the operator against the
    trigger. Since the word is now decodable, invert it: arm, let the knob turn
    whenever, then label the capture from the front panel. Also cross-checks the
    decoded value against what you type, which validates the mapping live.
    """
    got = 0
    while got < count:
        print(f"\n--- capture {got + 1}/{count} ---")
        input("  Press Enter to arm, then turn either knob to any new value... ")
        arm(din, n, prefill)
        t0 = time.time()
        print("  ARMED. Turn a knob now.")
        raw = wait_trigger(din, n, timeout)
        dt = time.time() - t0

        if raw is None:
            print("  !! nothing captured.")
            continue

        d = decode_array(raw)
        full = [w for w in (d["words"] if d else []) if len(w) == EXPECT_CLOCKS]
        if len(full) != 1:
            print(f"  !! expected one {EXPECT_CLOCKS}-bit word, got {len(full)}"
                  f" ({d['clocks']} clocks). Retrying.")
            continue

        word = "".join(str(b) for b in full[0])
        vc, ic = deinterleave(word)
        vv, ia = to_units(word)
        print(f"  triggered after {dt:.2f}s")
        if dt < 0.30:
            print("  NOTE: that fired very fast — if you had not touched the knob")
            print("        yet, this is stale traffic. Discard it with 'x'.")
        print(f"  word: {word}  0x{int(word, 2):06X}")
        print(f"  decoded -> V code {vc:4d} = {vv:6.3f} V | "
              f"I code {ic:4d} = {ia:6.3f} A")

        ans = input("  Display reads (e.g. '5.00 0.100'), Enter to accept, "
                    "'x' to discard: ").strip().lower()
        if ans == "x":
            continue
        if ans:
            try:
                parts = [float(x) for x in ans.replace(",", " ").split()]
                vv = parts[0]
                if len(parts) > 1:
                    ia = parts[1]
            except ValueError:
                print("  (could not parse, keeping decoded values)")
        np.save(os.path.join(outdir, f"v_{vv:.2f}".replace(".", "_") + ".npy"), raw)
        print(f"  saved as {vv:.2f} V")
        got += 1


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
    """Parse "0,1,5" into floats. Empty / "none" / "skip" mean no points."""
    s = (s or "").strip()
    if not s or s.lower() in ("none", "skip", "-"):
        return []
    return [float(x) for x in s.split(",") if x.strip()]


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
    # nargs="?" so a bare `--i` means "skip the current sweep" — PowerShell
    # eats `--i ""` before argparse ever sees it.
    p.add_argument("--v", nargs="?", const="", default="0,1,5,10,20,30",
                   help="voltage setpoints (V), or bare --v / 'none' to skip")
    p.add_argument("--i", nargs="?", const="", default="0.5,2.5,5.0",
                   help="current setpoints (A), or bare --i / 'none' to skip")
    p.add_argument("--outdir", default="dac_captures")
    p.add_argument("--wait", type=float, default=60.0)
    p.add_argument("--prefill", type=float, default=0.1)
    p.add_argument("--analyse-only", action="store_true")
    p.add_argument("--free", type=int, metavar="N",
                   help="race-free mode: capture N words, label each afterwards "
                        "from the front panel")
    a = p.parse_args()

    os.makedirs(a.outdir, exist_ok=True)

    if not a.analyse_only:
        vpts, ipts = parse_points(a.v), parse_points(a.i)
        if a.free:
            vpts, ipts = [], []
            print(f"Free-run mode: {a.free} captures, labelled after the fact.")
        else:
            print(f"Sweep: {len(vpts)} voltage points, {len(ipts)} current points.")
            print("Captures are validated as they land; retry any that fail.\n")
            print("IMPORTANT: leave the CURRENT knob alone during the voltage "
                  "sweep,\nand the VOLTAGE knob alone during the current sweep.")

        dwf = DwfLibrary()
        try:
            with openDwfDevice(dwf) as device:
                force_inputs(device)
                din = device.digitalIn
                n = min(16384, din.bufferSizeInfo())
                try:
                    if a.free:
                        free_run(din, n, a.prefill, a.wait, a.outdir, a.free)
                        vpts, ipts = [], []
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
