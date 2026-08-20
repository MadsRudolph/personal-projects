#!/usr/bin/env python
"""Prove each behavioural model behaves like the datasheet before any sheet uses it.

Run with the miniconda interpreter that has PySpice + ngspice:
    C:\\Users\\Mads2\\miniconda3\\python.exe test_models.py

This is a verification harness only. The deliverable schematics run in KiCad's
own built-in simulator; this just stops unverified models reaching them.
"""
import sys
from pathlib import Path

import numpy as np
from PySpice.Spice.NgSpice.Shared import NgSpiceShared

HERE = Path(__file__).resolve().parent
LIB = (HERE.parent / "models" / "classd_sim.lib").as_posix()

NG = NgSpiceShared.new_instance(verbose=False)


def run(deck):
    try:
        NG.remove_circuit()
    except Exception:  # noqa: BLE001 - nothing loaded on the first call
        pass
    NG.load_circuit(deck)
    NG.run()
    plot = NG.plot(None, NG.last_plot)
    return {k: np.asarray(v.to_waveform()) for k, v in plot.items()}


def edge_time(t, v, level, rising=True):
    """First time v crosses `level`, linearly interpolated."""
    for i in range(1, len(v)):
        a, b = v[i - 1], v[i]
        if (rising and a < level <= b) or (not rising and a > level >= b):
            f = (level - a) / (b - a) if b != a else 0.0
            return t[i - 1] + f * (t[i] - t[i - 1])
    return None


RESULTS = []


def check(name, got, lo, hi, unit=""):
    ok = got is not None and lo <= got <= hi
    RESULTS.append(ok)
    g = "None" if got is None else f"{got:.4g}"
    print(f"  {'PASS' if ok else 'FAIL'}  {name:44s} {g:>12}{unit}"
          f"   expected {lo:g}..{hi:g}{unit}")


# ---------------------------------------------------------------- op-amp ----
print("\nOPAMP_TL074")
w = run(f"""* open-loop gain, biased by DC feedback that is open at AC
.include "{LIB}"
Vp vp 0 12
Vn vn 0 0
Vin inp 0 DC 6 AC 1
X1 inp inn out vp vn OPAMP_TL074
* 1 GH closes the loop at DC only; 1 GF holds the - input at AC ground.
* Without this the open-loop bias sits on a clamp and .ac reports no gain.
Lf out inn 1e9
Cf inn 0 1e9
Rl out 0 10k
.ac dec 20 1 100meg
.end
""")
f = np.abs(w["frequency"])
g = np.abs(w["out"])
check("open-loop gain at 1 Hz (V/V)", float(g[0]), 5e4, 2e5)
# unity-gain crossing = GBW
idx = np.where(g < 1.0)[0]
check("gain-bandwidth product (Hz)", float(f[idx[0]]) if len(idx) else None,
      3.5e6, 7e6)

print("  (slew rate, as a follower driven by a 10 V step)")
w = run(f"""* slew, as a follower stepped well inside the rails
.include "{LIB}"
Vp vp 0 12
Vn vn 0 0
Vin inp 0 PULSE(3 9 1u 1n 1n 20u 40u)
X1 inp out out vp vn OPAMP_TL074
Rl out 0 10k
.tran 2n 6u
.end
""")
t, o = w["time"], w["out"]
t1 = edge_time(t, o, 4.0)
t2 = edge_time(t, o, 8.0)
check("slew rate 4->8 V (V/us)", (4.0 / (t2 - t1)) / 1e6 if t1 and t2 else None,
      12, 28, " V/us")

# ------------------------------------------------------------ comparator ----
print("\nCMP_LM311")
w = run(f"""* comparator: open collector with 1k pull-up, 165 ns delay
.include "{LIB}"
Vp vp 0 12
Vn vn 0 0
Vref inn 0 6
Vin inp 0 PULSE(5.9 6.1 1u 1n 1n 5u 10u)
X1 inp inn out 0 vp vn CMP_LM311
Rpu vp out 1k
.tran 2n 8u
.end
""")
t, o = w["time"], w["out"]
check("output HIGH level (V)", float(np.max(o)), 11.0, 12.1, " V")
check("output LOW level  (V)", float(np.min(o)), -0.1, 0.5, " V")
# Input rises through the reference at t=1 us. The LM311 is NON-inverting, so
# the pulled-up output must RISE 165 ns later. Asserting a fall here is what
# hid an inverted model until the oscillator testbench refused to oscillate.
tf = edge_time(t, o, 6.0, rising=True)
check("propagation delay (ns)", (tf - 1e-6) * 1e9 if tf else None, 140, 200, " ns")

# -------------------------------------------------------------- inverter ----
print("\nINV_CD4049")
w = run(f"""* cmos inverter at 12 V
.include "{LIB}"
Vcc vcc 0 12
Vin in 0 PULSE(0 12 1u 5n 5n 2u 4u)
X1 in out vcc 0 INV_CD4049
Rl out 0 100k
.tran 1n 6u
.end
""")
t, o = w["time"], w["out"]
check("output HIGH level (V)", float(np.max(o)), 11.5, 12.1, " V")
check("output LOW level  (V)", float(np.min(o)), -0.1, 0.5, " V")
tf = edge_time(t, o, 6.0, rising=False)
check("propagation delay (ns)", (tf - 1e-6) * 1e9 if tf else None, 15, 45, " ns")

# ----------------------------------------------------------- gate driver ----
print("\nDRV_HIP4082  (dead time, lockout, bootstrap)")
w = run(f"""* one leg driven complementary, bootstrap fed by a diode from 12 V
.include "{LIB}"
.include "C:/Program Files/KiCad/10.0/share/kicad/demos/simulation/power_supplies/buck_conv/IRF-Power-VDMOS.mod"
Vdd vdd 0 12
Vahi ahi 0 PULSE(0 12 1u 10n 10n 5u 10u)
Vali ali 0 PULSE(12 0 1u 10n 10n 5u 10u)
Vbhi bhi 0 0
Vbli bli 0 0
X1 ahi ali bhi bli ahb ahs aho alo bhb bhs bho blo vdd 0 ndel 0 DRV_HIP4082 tdead=200n
* bootstrap: diode from VDD plus the 100n cap, exactly as drawn on the board
Dboot vdd ahb DSCH
.model DSCH D(Is=1e-8 Rs=0.05 N=1.05)
Cboot ahb ahs 100n
* a half bridge so AHS is a real switching node
M1 vdd nga ahs ahs IRF540N
M2 ahs ngb 0 0 IRF540N
Rga aho nga 22
Rgb alo ngb 22
Rload ahs 0 100
* the unused B leg still needs its bootstrap cap and a DC path to ground
Cbb bhb bhs 100n
Rbb bhs 0 1meg
.tran 10n 25u
.end
""")
t = w["time"]
aho, alo, ahs = w["aho"], w["alo"], w["ahs"]
vah = aho - ahs                       # high-side gate drive, referenced to source
check("high-side drive amplitude (V)", float(np.max(vah)), 10.0, 12.5, " V")
check("low-side drive amplitude (V)", float(np.max(alo)), 10.0, 12.5, " V")
# never both on: with a real dead time the product stays near zero
overlap = float(np.max(np.minimum(vah, alo)))
check("worst simultaneous drive (V)", overlap, -1.0, 2.0, " V")

# measure the dead time on the second switching cycle
mask = (t > 10e-6) & (t < 20e-6)
tt, hh, ll = t[mask], vah[mask], alo[mask]
th = edge_time(tt, hh, 6.0, rising=True)
tl = edge_time(tt, ll, 6.0, rising=False)
check("dead time, low off -> high on (ns)",
      (th - tl) * 1e9 if (th and tl) else None, 150, 320, " ns")

print(f"\n{sum(RESULTS)}/{len(RESULTS)} checks passed")
sys.exit(0 if all(RESULTS) else 1)
