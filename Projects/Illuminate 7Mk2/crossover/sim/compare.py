#!/usr/bin/env python3
"""Compare the reference crossover with the shop-substituted one.

Reads crossover_ac.dat (written by ngspice from crossover_ac.cir) and reports
how far each branch's transfer function moves, in dB, over 100 Hz - 20 kHz.

Run:  ngspice -b crossover_ac.cir  &&  python3 compare.py
"""
import math
from pathlib import Path

rows = []
for line in Path("crossover_ac.dat").read_text().split("\n"):
    v = line.split()
    if len(v) == 8:
        rows.append([float(x) for x in v])

BAND = [r for r in rows if 100.0 <= r[0] <= 20000.0]
print(f"{len(BAND)} points, {BAND[0][0]:.1f} Hz .. {BAND[-1][0]:.0f} Hz\n")

for label, iref, isub in (("tweeter", 1, 3), ("woofer", 5, 7)):
    dev = [(r[0], r[isub] - r[iref]) for r in BAND]
    f_max, d_max = max(dev, key=lambda t: abs(t[1]))
    rms = math.sqrt(sum(d * d for _, d in dev) / len(dev))
    over = [f for f, d in dev if abs(d) > 0.5]
    print(f"{label:8s} max deviation {d_max:+.3f} dB at {f_max:8.1f} Hz"
          f"   rms {rms:.3f} dB"
          f"   | >0.5 dB over {len(over)} of {len(dev)} points")

# Shape of the substituted response, as a sanity check on the model.
print("\n   f [Hz]   tweeter dB   woofer dB   (substituted values)")
for target in (100, 200, 500, 940, 1500, 2000, 3000, 5000, 7600, 10000, 15000, 20000):
    r = min(BAND, key=lambda x: abs(x[0] - target))
    print(f"{r[0]:9.0f}   {r[3]:9.2f}   {r[7]:9.2f}")
