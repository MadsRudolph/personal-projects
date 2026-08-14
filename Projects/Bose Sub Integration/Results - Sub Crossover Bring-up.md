---
title: Results - Sub Crossover Bring-up
type: measurement-log
tags:
  - electronics
  - audio
  - subwoofer
  - crossover
  - measurement
status: In progress
started: 2026-08-15
updated: 2026-08-15
---

# Results - Sub Crossover Bring-up

Measured on the AD3 against [[Test Guide - Sub Crossover Board]]. Predictions
from `tools/subxo_model.py`; scoring available via `tools/subxo_compare.py`.

Rig: W1 → J1.1 + J2.1 (both inputs driven), C1 ref at J1.1, C2 differential
across J5.1 (`OUT1`) → JP2 even pin (`VGND`). 15 Hz–2 kHz, 70 steps, 1 V, log.
Supply 15.0 V from the Korad. Pot not yet fitted — J6 left open, Gate 10
deferred.

---

## Gate 5 — the nine transfer functions

Corner = 3 dB below that setting's own 63 Hz level. Fill in as you go.

| JP1           | JP2           | g(63) pred | g(63) meas | corner pred | band        | **corner meas** | verdict  |
| ------------- | ------------- | ---------- | ---------- | ----------- | ----------- | --------------- | -------- |
| pos2 220n     | pos1 150n     | −4.04      | −4.08      | 114.2       | 110–120     | 113.59          | **PASS** |
| pos2 220n     | pos2 120n     | −2.95      | −3.00      | 126.3       | 120–134     | 124.4           | **PASS** |
| pos2 220n     | pos3 68n      | −1.15      | −1.03      | 181.2       | 168–197     | 189.5           | **PASS** |
| **pos3 150n** | **pos1 150n** | **−4.14**  | **−4.175** | **121.5**   | **117–127** | **122.02**      | **PASS** |
| pos3 150n     | pos2 120n     | −3.12      | −3.167     | 135.4       | 129–144     | 135.1           | **PASS** |
| pos3 150n     | pos3 68n      | −1.39      | −1.287     | 200.0       | 186–217     | 211.6           | **PASS** |
| pos2+3 370n   | pos1 150n     | −4.07      | −4.08      | 100.5       | 97–105      | 100.68          | **PASS** |
| pos2+3 370n   | pos2 120n     | −2.79      | −2.80      | 108.6       | 103–115     | 108.9           | **PASS** |
| pos2+3 370n   | pos3 68n      | −0.71      | −0.60      | 148.2       | 137–161     | 155.9           | **PASS** |

> [!success] Gate 5 complete — nine of nine pass
> Every corner inside its band, every gain within 0.13 dB of prediction.
> Last three measured after borrowing JP3's shunt.

### Out-of-sample test: the last three were predicted before they were measured

The `C2_3` hypothesis below was derived from the first six settings, then used
to predict the three 370n rows blind. Held-out result:

| Setting | Measured | Predicted from fit | Error | Nominal-cap model | Error |
|---|---|---|---|---|---|
| 370n / 150n | 100.68 | 100.42 | +0.26% | 100.5 | +0.18% |
| 370n / 120n | 108.90 | 108.18 | +0.66% | 108.6 | +0.28% |
| **370n / 68n** | **155.90** | **154.88** | **+0.66%** | 148.2 | **+5.20%** |

The 68n row is the one that discriminates: the fitted model predicts it to
0.66%, the nominal-capacitor model misses by 5.2%. **`C2_3` being ~6% low is
confirmed out-of-sample**, not just fitted in-sample.

### The errors are not random

Sorted by which C2 is fitted, the deviation from nominal concentrates entirely
in one part:

| C2 fitted | corner error | gain error |
|---|---|---|
| 150 nF | −0.08% | −0.036 dB |
| 120 nF | −0.86% | −0.047 dB |
| **68 nF** | **+5.17%** | **+0.114 dB** |

Both 68n rows deviate, in the same direction, across *different* C1 values —
so it is the capacitor, not the setting. A low C2 raises f0 (∝1/√C2) **and**
raises Q (∝1/√C2), which shows up as less droop at 63 Hz. Both observed signs
match.

### Fitted capacitances

Five parameters against eighteen observations (nine corners, nine gains),
resistors held nominal. Residual **0.96σ**. Worst error across all nine
settings: **0.80% in corner, 0.037 dB in gain**.

| Part | Marked | From 6 settings | **Final, all 9** | Deviation | 1σ |
|---|---|---|---|---|---|
| C1_2 | 220n | 223.2n | **221.7n** | +0.8% | ±0.7% |
| C1_3 | 150n | 145.2n | **143.2n** | −4.5% | ±1.0% |
| C2_1 | 150n | 150.8n | **150.7n** | +0.5% | ±0.2% |
| C2_2 | 120n | 121.6n | **121.2n** | +1.0% | ±0.2% |
| **C2_3** | **68n** | 63.7n | **63.8n** | **−6.2%** | **±0.3%** |

All five are inside a ±10% film tolerance, so nothing here is a faulty part —
but `C2_3` is now a known quantity rather than an assumed one.

`C1_3` tightened from −3.2% to −4.5% when the 370n rows were added, because
those directly constrain `C1_2 + C1_3`. The parallel position is **364.9 nF**,
not 370.

> [!note] An alternative explanation was tested and rejected
> Fitting `C_in` instead of `C2_3` drives it to 246 nF and makes the fit *worse*
> — gain residual 0.224 dB against 0.074 dB at nominal, with corner barely
> improved. **C_in is confirmed at its marked 220 nF.** The 63 Hz gains are what
> reject it: they depend on Q, and a C_in error moves gain and corner in
> combinations the data does not show.

Caveat on attribution: these are *effective* values with the resistors assumed
nominal. A 1% resistor error would re-attribute some of the deviation without
changing the predictions below, since those use the same resistors.

---

## The board as measured — nine crossover settings

This is the operating table. Sorted by corner, which is how a setting gets
chosen by ear. "Level" is the gain at 63 Hz — a level offset the pot and the
pod's own knob absorb, not a defect.

| Corner | JP1 | JP2 | Shunts | Level at 63 Hz | Peak | Peak at |
|---|---|---|---|---|---|---|
| **100.7 Hz** | pos2+3 | pos1 | 3 | −4.09 dB | +0.04 dB | 25 Hz |
| **108.7 Hz** | pos2+3 | pos2 | 3 | −2.84 dB | +0.13 dB | 32 Hz |
| **113.8 Hz** | pos2 | pos1 | 2 | −4.07 dB | +0.03 dB | 24 Hz |
| **121.9 Hz** | pos3 | pos1 | 2 | −4.18 dB | +0.02 dB | 23 Hz |
| **125.4 Hz** | pos2 | pos2 | 2 | −2.99 dB | +0.09 dB | 29 Hz |
| **135.5 Hz** | pos3 | pos2 | 2 | −3.18 dB | +0.06 dB | 27 Hz |
| **155.4 Hz** | pos2+3 | pos3 | 3 | −0.59 dB | +0.98 dB | 83 Hz |
| **189.2 Hz** | pos2 | pos3 | 2 | −1.02 dB | +0.55 dB | 81 Hz |
| **212.3 Hz** | pos3 | pos3 | 2 | −1.29 dB | +0.31 dB | 53 Hz |

Range **100–212 Hz** in nine steps, against the 82–191 Hz the as-built BOM
predicts and the 87–191 Hz the design doc predicts. Spacing is close to even on
a log scale apart from the gap between 135 and 155 Hz.

> [!note] Only three settings need the JP3 shunt back
> The `pos2+3` rows want two shunts on JP1. Everything else runs on two shunts
> total, so **JP3 goes back on** for normal use and for Gate 10 — `OUT_GND` is
> in the output path even though it was irrelevant to these sweeps.
>
> If you settle on a `pos2+3` setting, buy a third shunt rather than leaving
> JP3 open permanently: without it the input and output grounds are joined only
> through `R7`'s 10 Ω, which is the hum-lift configuration, not the default.

### 150n / 150n — 2026-08-15

First powered sweep. Read off two X cursors, no export.

| | Measured | Model | Error |
|---|---|---|---|
| gain at 63 Hz | −4.1745 dB | −4.141 | −0.033 dB |
| phase at 63 Hz | −40.940° | −41.123 | +0.183° |
| corner | 122.024 Hz | 121.536 | +0.488 Hz (0.4%) |
| gain at corner | −7.1973 dB | −7.171 | −0.027 dB |
| phase at corner | −74.982° | −75.978 | +0.995° |

Reference channel flat to −0.011 / −0.015 dB across both cursors, so the drive
and through-path are clean — Gate 3 confirmed in situ.

> [!success] This settles the C_in question by measurement
> The sweep discriminates between three predictions that straddle each other:
>
> | Prediction | Says | Error |
> |---|---|---|
> | Ideal formula f0 (design doc) | 128.6 Hz | −6.6 Hz (5.4%) |
> | −3 dB if C_in were 2u2 as drawn | 112.5 Hz | +9.5 Hz (7.8%) |
> | **−3 dB with C_in 220n as built** | **121.5 Hz** | **+0.5 Hz (0.4%)** |
>
> The two wrong answers miss in **opposite directions** and the as-built model
> lands within 0.4%. The coupling capacitors being inside the filter is now
> measured, not argued.
>
> 0.03 dB agreement on gain also says C1 and C2 are close to nominal.

**Caveat on how much this proves.** C1 = C2 here, so Q = 0.50 — the most damped
of the nine and the least demanding on the model. The settings that actually
stress it are the **370n** ones, where the parallel combination is assumed, and
**370n / 68n**, the high-Q case carrying the peaking question.

---

## Remaining gates

| Gate | Status | Result |
|---|---|---|
| 0 — cold checks | | |
| 1 — staged power-up | | current \_\_ mA, V12 \_\_ V |
| 2 — DC survey | | *(`POT_TOP` reads ~6 V with J6 open — expected)* |
| 3 — instrument through-cal | implicitly confirmed | C1 flat to 0.015 dB |
| 5 — nine sweeps | **COMPLETE — 9 of 9 PASS** | corners 100–212 Hz, worst model error 0.80% |
| 6 — mono sum | | want +6.02 dB, flat |
| 7 — polarity | | want 0.00 dB / 180.0° |
| 8 — noise floor | | \_\_ mV rms, 50 Hz \_\_ µV |
| 9 — headroom | | clips at W1 = \_\_ V, or not at 5 V |
| 10 — output chain | **deferred** | no pot yet |
| 11 — in situ | | |

---

## Open questions this run should close

1. ~~**Does 370n / 68n peak?**~~ **Answered.** Corner measured at 155.9 Hz, gain
   at 63 Hz −0.60 dB, both matching the model to 0.66% and 0.02 dB. The implied
   peak is **+0.98 dB above 20 Hz** — the broadest, mildest kind of bump, at
   83 Hz. Nothing like the +1.86 dB that Q = 1.17 implies, and nowhere near
   "peaks audibly".
   **Action:** `bom-as-built.csv`'s warning against this setting is wrong and
   should be replaced with the measured numbers. It is currently steering you
   away from the second-widest setting on the board for no reason.
   *(To confirm the peak directly rather than by inference: cursor at 20 Hz
   should read −1.43 dB, cursor at 83 Hz should read −0.45 dB, ΔY +0.98 dB.)*
2. **Is the passband droop worth fixing?** −1.3 to −3.1 dB at 63 Hz, purely from
   C_in. Mostly below where the module plays, so it likely costs level rather
   than shape. Decide after Gate 11, not before.
3. **Headroom on a single 12 V rail.** The AD3 may not be able to clip it at all.

---

## Related

- [[Test Guide - Sub Crossover Board]]
- [[Design - Sub Crossover Board]]
