"""Plot sim/boost_tran.dat (written by boost_tran.cir) to sim/boost_tran.png."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

d = np.loadtxt("sim/boost_tran.dat")
t = d[:, 0] * 1e3
series = ((d[:, 1], "VOUT [V]"), (d[:, 3], "I(L1) [A]"), (d[:, 5], "COMP [V]"), (d[:, 7], "IN+ (soft start) [V]"))
fig, ax = plt.subplots(4, 1, figsize=(11, 10), sharex=True)
for a, (y, label) in zip(ax, series):
    a.plot(t, y, lw=0.5)
    a.set_ylabel(label)
    a.grid(alpha=0.4)
ax[1].set_ylim(-1, 10)
ax[0].set_title("Vin 12 V: soft start into 1 A, 1 -> 3 A step at 15 ms, 3 -> 1 A at 25 ms")
ax[-1].set_xlabel("time [ms]")
fig.tight_layout()
fig.savefig("sim/boost_tran.png", dpi=90)
