#!/usr/bin/env python
"""Export each testbench through KiCad and check the result against the design.

    C:\\Users\\Mads2\\miniconda3\\python.exe run_sims.py [bench ...]

Verification harness only. The sheets themselves are ordinary KiCad schematics
that run in Eeschema's own simulator; this exports the same netlist KiCad would
hand ngspice and asserts the numbers the design is supposed to produce, so a
broken testbench is caught here rather than by eye.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PySpice.Spice.NgSpice.Shared import NgSpiceShared

KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
SIM = Path(__file__).resolve().parent.parent
NG = NgSpiceShared.new_instance(verbose=False)
RESULTS = []


def netlist(bench):
    out = SIM / "build" / f"{bench}.cir"
    out.parent.mkdir(exist_ok=True)
    r = subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format",
                        "spice", "-o", str(out), str(SIM / f"{bench}.kicad_sch")],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"{bench}: netlist export failed\n{r.stdout}{r.stderr}")
    return out.read_text(encoding="utf-8")


def simulate(deck):
    try:
        NG.remove_circuit()
    except Exception:  # noqa: BLE001
        pass
    NG.load_circuit(deck)
    NG.run()
    plot = NG.plot(None, NG.last_plot)
    return {k.lower(): np.asarray(v.to_waveform()) for k, v in plot.items()}


def check(name, got, lo, hi, unit=""):
    ok = got is not None and lo <= got <= hi
    RESULTS.append((ok, name))
    g = "None" if got is None else f"{got:.4g}"
    print(f"    {'PASS' if ok else 'FAIL'}  {name:46s} {g:>11}{unit}"
          f"  want {lo:g}..{hi:g}{unit}")


def freq_of(t, v):
    """Fundamental frequency from mean crossings."""
    v = v - v.mean()
    up = [t[i] for i in range(1, len(v)) if v[i - 1] < 0 <= v[i]]
    if len(up) < 3:
        return None
    return 1.0 / np.mean(np.diff(up))


def tail(t, v, frac=0.5):
    return v[t > t[-1] * frac]


# ---------------------------------------------------------------- benches ---
def bench_a():
    w = simulate(netlist("sim_a_vground"))
    t, vg = w["time"], w["/vgnd"]
    check("VGND settles to half rail (V)", float(vg[-1]), 5.9, 6.1, " V")
    check("VGND still rising at 0.5 s (V)",
          float(vg[np.searchsorted(t, 0.5)]), 3.0, 5.9, " V")


def bench_b():
    w = simulate(netlist("sim_b_triangle"))
    t, tri = w["time"], w["/tri"]
    sel = t > 50e-6                      # let it start
    tt, vv = t[sel], tri[sel]
    check("carrier frequency (kHz)",
          freq_of(tt, vv) / 1e3 if freq_of(tt, vv) else None, 200, 310, " kHz")
    check("triangle amplitude (Vpp)", float(vv.max() - vv.min()), 3.0, 5.5, " Vpp")
    check("triangle centred on 6 V (V)", float(vv.mean()), 5.5, 6.5, " V")
    sq = w["/sq"]
    check("square wave swings the rail (Vpp)",
          float(sq[sel].max() - sq[sel].min()), 10.0, 12.5, " Vpp")


def bench_c():
    w = simulate(netlist("sim_c_input"))
    t = w["time"]
    p, n = w["/audio_p"], w["/audio_n"]
    sel = t > 1e-3
    p, n = p[sel], n[sel]
    check("AUDIO_P centred on 6 V (V)", float(p.mean()), 5.9, 6.1, " V")
    check("AUDIO_N centred on 6 V (V)", float(n.mean()), 5.9, 6.1, " V")
    # equal and opposite: p + n should stay at 12 V
    check("AUDIO_P + AUDIO_N (V)", float((p + n).mean()), 11.8, 12.2, " V")
    check("worst mirror error (mV)", float(np.max(np.abs(p + n - 12.0))) * 1e3,
          0, 60, " mV")
    # the TL074's input common-mode floor is V- + 4 V; this is the design risk
    check("AUDIO_P stays above the 4 V CM floor (V)", float(p.min()), 4.0, 8.0,
          " V")


def bench_d():
    w = simulate(netlist("sim_d_pwm"))
    t = w["time"]
    a, b = w["/pwm_a"], w["/pwm_b"]
    check("PWM_A swings the rail (Vpp)", float(a.max() - a.min()), 10.5, 12.5,
          " Vpp")
    check("PWM_B swings the rail (Vpp)", float(b.max() - b.min()), 10.5, 12.5,
          " Vpp")
    # over a whole audio cycle the two duties must be mirror images
    da, db = float((a > 6).mean()), float((b > 6).mean())
    check("PWM_A mean duty (%)", da * 100, 35, 65, " %")
    check("PWM_A + PWM_B duty (%)", (da + db) * 100, 90, 110, " %")
    # duty must actually move with the audio, or nothing is being modulated
    half = len(t) // 2
    d1 = float((a[:half] > 6).mean())
    d2 = float((a[half:] > 6).mean())
    check("duty swing across the audio cycle (%)", abs(d1 - d2) * 100, 5, 60,
          " %")


def overlap_runs(t, a, b, thr=6.0, above=False):
    """Lengths of every interval where both signals are the same side of thr."""
    both = (a > thr) & (b > thr) if above else (a < thr) & (b < thr)
    out, start = [], None
    for i, f in enumerate(both):
        if f and start is None:
            start = t[i]
        elif not f and start is not None:
            out.append(t[i] - start)
            start = None
    return out


def audio_band(t, v, period=4e-6):
    """Average the carrier away with a boxcar one carrier period wide."""
    n = max(1, int(round(period / np.median(np.diff(t)))))
    return np.convolve(v, np.ones(n) / n, mode="valid")


def bench_e():
    w = simulate(netlist("sim_e_driver"))
    t = w["time"]
    sel = t > 100e-6                     # the bootstrap needs ~50 us to fill
    ah, al = w["/g_ah"][sel], w["/g_al"][sel]
    check("low-side gate drive (V)", float(al.max()), 11.5, 12.2, " V")
    check("high-side gate drive (V)", float(ah.max()), 10.8, 12.0, " V")
    # the high side runs off the bootstrap cap, one Schottky drop below VDD
    check("bootstrap drop, high vs low (V)",
          float(al.max() - ah.max()), 0.05, 0.6, " V")
    gaps = overlap_runs(t[sel], ah, al)
    check("dead time (ns)",
          float(np.median(gaps)) * 1e9 if gaps else None, 150, 320, " ns")
    # The thing dead time exists to prevent. Not "rarely" -- never.
    check("both gates driven at once (ns)",
          sum(overlap_runs(t[sel], ah, al, above=True)) * 1e9, 0, 0, " ns")
    # The two CD4049 stages differ by one gate delay, so a leg's two driver
    # inputs ARE briefly high together on every edge. That is harmless -- the
    # HIP4082 turns both outputs off for both-high -- but it has to stay well
    # under the dead time, or the gate skew and not R12 sets the timing.
    skew = overlap_runs(t[sel], w["/a_hi"][sel], w["/a_lo"][sel], above=True)
    check("input skew, both inputs high (ns)",
          float(np.median(skew)) * 1e9 if skew else None, 5, 80, " ns")


def bench_f():
    w = simulate(netlist("sim_f_bridge"))
    t = w["time"]
    sel = t > 150e-6
    sw = w["/sw_a"][sel]
    check("SW_A pulls to the bottom rail (V)", float(sw.min()), -1.5, 1.0, " V")
    check("SW_A pulls to the top rail (V)", float(sw.max()), 11.0, 13.0, " V")
    d = (w["/out_p"] - w["/out_n"])[sel]
    check("differential output (V)", float(d.mean()), 6.0, 7.5, " V")
    check("power into 4 ohm (W)", float(d.mean()) ** 2 / 4, 10.0, 14.0, " W")
    check("carrier left on the output (Vpp)",
          float(d.max() - d.min()), 0, 0.5, " Vpp")


def bench_g():
    w = simulate(netlist("sim_g_chain"))
    t = w["time"]
    sel = t > 0.4e-3                     # past the bootstrap and the start-up
    tt = t[sel]
    check("carrier frequency (kHz)",
          freq_of(tt, w["/tri"][sel]) / 1e3 if freq_of(tt, w["/tri"][sel])
          else None, 190, 270, " kHz")
    # THE design risk: at full output the buffer input reaches the TL074's
    # V- + 4 V common-mode floor. It should touch it, not go under it.
    check("AUDIO_P at the 4 V common-mode floor (V)",
          float(w["/audio_p"][sel].min()), 3.85, 4.25, " V")
    d = (w["/out_p"] - w["/out_n"])[sel]
    sm = audio_band(tt, d)
    check("output swing (V peak)", float(np.abs(sm).max()), 8.5, 12.0, " V")
    check("power into 4 ohm (W)",
          float((sm - sm.mean()).std()) ** 2 / 4, 10.0, 15.0, " W")
    check("residual carrier (Vpp)",
          float(np.max(np.abs(d[:len(sm)] - sm))) * 2, 0, 0.6, " Vpp")


BENCHES = {"a": ("sim_a_vground", bench_a), "b": ("sim_b_triangle", bench_b),
           "c": ("sim_c_input", bench_c), "d": ("sim_d_pwm", bench_d),
           "e": ("sim_e_driver", bench_e), "f": ("sim_f_bridge", bench_f),
           "g": ("sim_g_chain", bench_g)}

wanted = sys.argv[1:] or list(BENCHES)
for key in wanted:
    name, fn = BENCHES[key]
    print(f"\n{name}")
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        print(f"    ERROR {type(e).__name__}: {str(e)[:200]}")
        RESULTS.append((False, name))

ok = sum(1 for r, _ in RESULTS if r)
print(f"\n{ok}/{len(RESULTS)} checks passed")
sys.exit(0 if ok == len(RESULTS) else 1)
