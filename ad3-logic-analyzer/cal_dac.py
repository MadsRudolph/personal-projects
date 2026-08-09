#!/usr/bin/env python3
"""Calibrate the KORAD DAC: front-panel setpoint <-> 74HC595 code.

The bus is refreshed continuously, so no trigger timing is needed: set the
front panel to a value, tell this script what the display reads, and it
captures the current DAC word immediately. Repeat across the range, and it
fits both channels and reports the residuals.

Vary ONE knob at a time where you can, but it does not matter much — both
fields are read from every word, so every point contributes to both fits.

  python cal_dac.py                     # interactive, Ctrl-C or blank to stop
  python cal_dac.py --out cal.csv       # also append to a CSV
  python cal_dac.py --fit-only cal.csv  # re-fit an existing CSV
"""

import argparse
import csv
import os

import numpy as np
from pydwf import DwfLibrary
from pydwf.utilities import openDwfDevice

from decode_595 import decode_array
from read_dac import one_capture
from sweep_dac import deinterleave, EXPECT_CLOCKS


def read_codes(din, n):
    """Return (v_code, i_code, word) or None."""
    raw, _ = one_capture(din, n)
    if raw is None:
        return None
    d = decode_array(raw)
    full = [w for w in (d["words"] if d else []) if len(w) == EXPECT_CLOCKS]
    if len(full) != 1:
        return None
    w = "".join(str(b) for b in full[0])
    vc, ic = deinterleave(w)
    return vc, ic, w


def fit_channel(setpoints, codes, name, unit):
    if len(setpoints) < 3:
        print(f"\n{name}: only {len(setpoints)} point(s) — need 3+ to fit.")
        return None
    x = np.asarray(codes, float)
    y = np.asarray(setpoints, float)
    if np.allclose(x, x[0]):
        print(f"\n{name}: code never varied — nothing to fit.")
        return None

    m, c = np.polyfit(x, y, 1)
    pred = m * x + c
    resid = y - pred
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - float(np.sum(resid ** 2)) / ss_tot if ss_tot > 0 else 1.0

    print(f"\n=== {name} ===")
    print(f"  {unit} = {m:.8g} * code + {c:.8g}")
    print(f"  inverse: code = {1/m:.6f} * {unit} + {-c/m:.3f}")
    print(f"  R^2 = {r2:.8f}   resolution {abs(m)*1000:.3f} m{unit}/LSB")
    print(f"  code at 0 {unit}: {(-c/m):.1f}   "
          f"full-scale (4095): {m*4095 + c:.3f} {unit}")
    print(f"\n  {'set':>9}  {'code':>6}  {'predicted':>10}  {'error':>9}")
    for sp, cd, pr, rs in zip(setpoints, codes, pred, resid):
        print(f"  {sp:9.3f}  {cd:6d}  {pr:10.3f}  {rs:+9.4f}")
    worst = float(np.max(np.abs(resid)))
    print(f"\n  worst error {worst:.4f} {unit}"
          f"  ({'LINEAR - good' if worst < 3*abs(m) else 'NOT linear - look at the residuals'})")
    return m, c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="cal.csv")
    ap.add_argument("--fit-only", metavar="CSV")
    ap.add_argument("--fix-v", type=float, metavar="V",
                    help="hold voltage at this value; only type the current")
    ap.add_argument("--fix-i", type=float, metavar="A",
                    help="hold current at this value; only type the voltage")
    ap.add_argument("--fresh", action="store_true",
                    help="ignore any existing CSV instead of appending to it")
    a = ap.parse_args()

    rows = []
    src = a.fit_only or (None if a.fresh
                         else (a.out if os.path.exists(a.out) else None))
    if src and os.path.exists(src):
        with open(src, newline="") as f:
            for r in csv.DictReader(f):
                rows.append({k: float(v) if k != "word" else v
                             for k, v in r.items()})
        print(f"loaded {len(rows)} existing point(s) from {src}")

    if not a.fit_only:
        with openDwfDevice(DwfLibrary()) as dev:
            dev.digitalIO.reset()
            dev.digitalIO.outputEnableSet(0)
            din = dev.digitalIn
            n = min(16384, din.bufferSizeInfo())

            if a.fix_v is not None:
                print(f"\nVoltage held at {a.fix_v:.2f} V — type only the "
                      f"CURRENT, e.g. '0.500'")
            elif a.fix_i is not None:
                print(f"\nCurrent held at {a.fix_i:.3f} A — type only the "
                      f"VOLTAGE, e.g. '12.34'")
            else:
                print("\nSet the front panel, then type what it reads: 'V I'")
                print("e.g.  12.34 0.500")
            print("(blank line or Ctrl-C to finish)\n")

            prompt = ("  current > " if a.fix_v is not None else
                      "  voltage > " if a.fix_i is not None else
                      "  display reads > ")
            try:
                while True:
                    s = input(prompt).strip()
                    if not s:
                        break
                    try:
                        parts = [float(x) for x in s.replace(",", " ").split()]
                        if a.fix_v is not None:
                            v_set, i_set = a.fix_v, parts[0]
                        elif a.fix_i is not None:
                            v_set, i_set = parts[0], a.fix_i
                        else:
                            v_set, i_set = parts[0], parts[1]
                    except (ValueError, IndexError):
                        print("    need a number"
                              if (a.fix_v is not None or a.fix_i is not None)
                              else "    need two numbers, e.g. '12.34 0.500'")
                        continue
                    # A missing decimal point ('0499' for 0.499) silently
                    # poisons the regression, so reject implausible values.
                    if not 0.0 <= v_set <= 35.0:
                        print(f"    {v_set} V is out of range for this supply "
                              f"— check the decimal point.")
                        continue
                    if not 0.0 <= i_set <= 6.0:
                        print(f"    {i_set} A is out of range for this supply "
                              f"— check the decimal point.")
                        continue
                    got = read_codes(din, n)
                    if got is None:
                        print("    capture failed — try again")
                        continue
                    vc, ic, w = got
                    print(f"    -> V code {vc:4d}   I code {ic:4d}   {w}")
                    rows.append({"v_set": v_set, "i_set": i_set,
                                 "v_code": vc, "i_code": ic, "word": w})
            except KeyboardInterrupt:
                print("\n  stopped.")

        if rows:
            with open(a.out, "w", newline="") as f:
                wcsv = csv.DictWriter(
                    f, fieldnames=["v_set", "i_set", "v_code", "i_code", "word"])
                wcsv.writeheader()
                wcsv.writerows(rows)
            print(f"\nsaved {len(rows)} point(s) -> {a.out}")

    if rows:
        fit_channel([r["v_set"] for r in rows],
                    [int(r["v_code"]) for r in rows], "VOLTAGE", "V")
        fit_channel([r["i_set"] for r in rows],
                    [int(r["i_code"]) for r in rows], "CURRENT", "A")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
