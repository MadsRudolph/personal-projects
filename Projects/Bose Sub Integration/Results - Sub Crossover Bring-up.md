---
title: Results - Sub Crossover Bring-up
type: measurement-log
tags:
  - electronics
  - audio
  - subwoofer
  - crossover
  - measurement
status: Rev A gates 0-5 complete; rev B bring-up outstanding
started: 2026-08-15
updated: 2026-08-16
---

# Results - Sub Crossover Bring-up

Measured on the AD3 against [[Test Guide - Sub Crossover Board]]. Predictions
from `tools/subxo_model.py`; scoring available via `tools/subxo_compare.py`.

Rig: W1 → J1.1 + J2.1 (both inputs driven), C1 ref at J1.1, C2 differential
across J5.1 (`OUT1`) → JP2 even pin (`VGND`). 15 Hz–2 kHz, 70 steps, 1 V, log.
Supply 15.0 V from the Korad. Pot not yet fitted — J6 left open, Gate 10
deferred.

> [!info] Everything below this line is **rev A**
> Rev B is a new board with the panel hardware wired. Its results go in the
> section at the end, so rev A's data stays intact as the reference the model
> was fitted against. Procedure: [[Test Guide - Sub Crossover Board]].

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

---

# Rev B — new board, panel hardware wired

Fill in as you go. Four things have never been powered: `C1_1` at 470 nF, the
`LK1` ground link, `D1`/`D2`, and the rotary on `JP1`/`JP2`. Pot and polarity
switch are fitted, so Gate 10 can finally run.

## Gate 0 — cold checks

| Check | Expect | Measured |
|---|---|---|
| `J4` 1→2 | rises, settles > 10 kΩ | \_\_ |
| `V12` → `GND` | settles high | \_\_ |
| **`LK1`: J4.2 → J1.2** | **~0 Ω** | \_\_ |
| Ground lift J3.3 → J1.2, JP3 in / out | 0 Ω / 10 Ω | \_\_ / \_\_ |
| Rotary detent 1 | `JP1` even↔1 only, `JP2` even↔1 only | \_\_ |
| Rotary detent 2 | `JP1` even↔5 only, `JP2` even↔3 only | \_\_ |
| Rotary detent 3 | `JP1` even↔3 only, `JP2` even↔5 only | \_\_ |
| `A0` ↔ `B0`, all detents | open | \_\_ |
| Switch frame ↔ all 8 lugs | open | \_\_ |

## Gate 1 — staged power-up

| Check | Expect | Measured |
|---|---|---|
| `U1` out, NORMAL | 6–10 mA | \_\_ |
| `V12` | 12.0 ± 0.25 V | \_\_ |
| `VG_DIV` | 6.0 ± 0.1 V | \_\_ |
| `U1` in, NORMAL | 12–18 mA | \_\_ |
| `U1` in, INVERTED | 14–20 mA | \_\_ |
| Step when switching | ~2 mA | \_\_ |
| Amber lights in | inverted | \_\_ |

## Gate 2 — DC survey

All signal nodes 6.00 ± 0.05 V. `POT_TOP` **0.00 V for the first time** — rev A
always read ~6 V because `J6` was empty.

| Node | Expect | Measured |
|---|---|---|
| `VGND`, `A_L`, `A_R`, `N1`, `N2` | 6.00 V | \_\_ |
| `OUT1`, `OUT2`, `SPARE_OUT` | 6.00 V | \_\_ |
| `POT_TOP` (J6.1) | **0.00 V** | \_\_ |
| `OUT_TIP` / `OUT_RING` | 0.00 V | \_\_ |

## Gate 5 — the three rotary positions

Detents 2 and 3 use capacitors measured to ±0.3 % on rev A, so they are the
verdict on the build. Detent 1 gets a band because `C1_1` is a new ±10 % part.

Swept 2026-08-17 with `tools/subxo_gate5.py`, 15 Hz–2 kHz, 70 steps, 1 V.

| Detent | C1 / C2 | Corner pred | **Corner meas** | g(63) pred | **g(63) meas** | Verdict |
|---|---|---|---|---|---|---|
| 1 | 470n / 150n | 94.0 | **94.9** | −4.29 | **−4.36** | PASS |
| 2 | 150n / 120n | 135.5 | **136.9** | −3.18 | **−3.05** | PASS |
| 3 | 220n / 68n | 189.2 | **179.0** | −1.02 | **−1.23** | *see below* |

Detent 3 initially failed on shape — 0.59 dB at 222 Hz against a 0.5 dB
tolerance — with the corner 5.4 % low and the 63 Hz level 0.2 dB down. Both
deviations point the same way, and one parameter explains them.

> [!important] `C2_3` is not the capacitor rev A measured
> Fitting the one unknown in each detent against its own 30–400 Hz shape:
>
> | Part | Rev A | Rev B fit | rms | Reading |
> |---|---|---|---|---|
> | `C1_3` | 143.2 nF | **145.2 nF** | 0.052 dB | +1.4 %, inside rev A's ±1.0σ — same part |
> | `C1_1` | never fitted | **451.6 nF** | 0.019 dB | −3.9 % on its marked 470n, an ordinary part |
> | `C2_3` | 63.8 nF ±0.3 % | **68.40 nF** | 0.043 dB | **+7.2 %** — far outside that confidence |
>
> `C1_3` agreeing to 1.4 % is what makes this conclusive: the measurement is not
> drifting, that one part has changed. And 68.40 nF is **+0.6 % of marked 68 nF**
> — so rev A's headline anomaly, the capacitor that sat 6.2 % low and was
> confirmed out-of-sample against a held-out setting, is simply no longer in the
> board. A different 68n went in during the rebuild.
>
> Rescored against 451.6 nF and 68.4 nF, **all three detents pass** with worst
> shape errors of 0.04, 0.17 and 0.09 dB. The board was never at fault; the
> model was wrong about one capacitor.

![[gate5-bode.png]]

*Points measured on the AD3, lines are the as-built model. Corners marked where
each curve passes 3 dB below its own 63 Hz level. Shaded band is the 20–120 Hz
the Companion 5 module actually plays. A dark version is at
`gate5-bode-dark.png`; regenerate either with:*

```
python tools/plot_gate5.py --dir tools --out gate5-bode.png
python tools/plot_gate5.py --dir tools --out gate5-bode-dark.png --theme dark
```

### Repeatability

Swept twice. Corners came back at 94.9 / 136.9 / 179.0 Hz and 94.9 / 136.9 /
178.9 Hz — **within 0.1 Hz** across the whole gate, which says the rotary
contacts and the loom are stable and that neither run was a fluke.

### The operating table, rev B

| Detent | Corner | Level at 63 Hz | Step |
|---|---|---|---|
| 1 | **94.9 Hz** | −4.36 dB | — |
| 2 | **136.9 Hz** | −3.05 dB | ×1.443, 0.53 oct |
| 3 | **179.0 Hz** | −1.23 dB | ×1.308, 0.39 oct |

Span 1.89×, against the 2.01× predicted before `C2_3` turned out to be nominal.
Slightly narrower and slightly less even, and not worth changing anything for.
Level spread across the three is 3.13 dB — the pot absorbs it, but it still
confounds A/B by ear, so nudge the level when comparing.

## Gates 6–11

| Gate | Want | Result |
|---|---|---|
| 6 — mono sum | +6.02 dB, flat. **Ground the idle input** | **PASS** — see below |
| 7 — polarity | 0.00 dB / 180.0°, amber on in inverted | **PASS** — see below |

### Gate 6 — mono sum, detent 2

Run with `tools/subxo_gate6.py`. Idle input grounded in software, so all three
sweeps ran off one keypress with nothing rewired.

| | L only | R only | Want |
|---|---|---|---|
| Mean ratio, 15–150 Hz | **−6.00 dB** | **−5.95 dB** | −6.02 |
| Median deviation from the flat model | **0.039 dB** | **0.047 dB** | < 0.15 |
| Channel balance, L − R | **−0.047 dB** | | < 0.15 |
| Drive left on `J1.1` when grounded | **0.1 %** | | < 5 % |

Both legs match the grounded model at 0.4 dB rms against 2.6 dB for the
floating one, so the software grounding is doing its job and the −6.02 dB is
the real 2:1 divider rather than a coincidence.

> [!note] Why the band is 15–150 Hz and not the whole sweep
> The first run scored the ratio out to 400 Hz and failed on a 1.7 dB tilt. It
> is not the board. The residual is **additive and about 2 mV**: subtract
> `both/2` from each one-driven sweep and the difference sits near 2 mV
> regardless of frequency, so as the filter attenuates the output the *fraction*
> grows and the ratio climbs toward 0 dB. By 550 Hz the output is 30 mV and the
> ratio reads +0.11 dB, which is meaningless.
>
> Two things prove it is the instrument. The drift is **identical on both legs**
> — −5.55 and −5.55 dB at 405 Hz — and it tracks 1/output. No fault in the
> summing network could do either, and a leg mismatch would show in the balance
> figure, which is 0.047 dB.
>
> There is also an isolated spike at **134.9 Hz**, 10.8 mV against a 2.6 mV
> local baseline and again the same on both legs (10.77 and 10.58). The script
> names points like that rather than hiding them, and judges the gate on the
> median so one glitch cannot fail it.
>
> Raising `--amp` to 2 V would halve the relative residual if the band ever
> needs to reach higher.

### Gate 7 — polarity, detent 2

`tools/subxo_gate7.py`, 128-cycle windows, judged over 15–200 Hz.

| | Magnitude | Phase |
|---|---|---|
| `OUT2` against `OUT1` | **−0.002 dB** | **180.08°** |
| `SW_COM` normal against `OUT1` — *the null* | −0.017 dB | −0.25° |
| `SW_COM` inverted against `OUT2` | −0.005 dB | −0.09° |

A2 is a textbook inverter and the switch selects the right output in each lever
position.

> [!note] The null is what makes the number believable
> `SW_COM` in NORMAL is `OUT1` reached through a closed contact — the same node
> measured twice — so anything it shows is the rig. It scatters 0.32° with a
> worst point of 2.88°, which puts the guide's ±0.5° figure right at the edge of
> what this setup resolves between separate sweeps. `OUT2`'s 0.08° error is
> comfortably inside that, and the two remaining outliers at 126.6 and 162.7 Hz
> appear in the null too.

> [!warning] The first attempt failed, and the board was never the problem
> A 16-cycle window at 305 Hz is 19 Hz wide, so the 300 Hz mains harmonic landed
> inside the measurement bin. Every bad point — 52.6, 304.6, 391.5, 570, 831,
> 1211, 1556 Hz — sat within two bin widths of a multiple of 50 Hz. Lengthening
> the window to 128 cycles resolves them apart; the same change fixed Gate 6's
> lone 134.9 Hz outlier, which was 15 Hz from the 150 Hz harmonic with an 8.4 Hz
> bin.
>
> The mean was also wrong for this data: a few leaked points dragged `OUT2` to
> −1.23° while the median sat at −0.05°.

| 8 — noise, frame grounded | < 1 mV rms, 50 Hz < 100 µV | **PASS** — 58 µV / 39 µV |
| 8 — noise, frame lifted | for comparison | **PASS** — 75 µV / 56 µV |
### Gate 8 — noise floor, and what the frame ground is worth

Inputs shorted with wire, generators off, sixteen 1-second records averaged.
Detent 2, polarity normal.

| Band | Frame grounded | Frame lifted | Penalty |
|---|---|---|---|
| 5–10 Hz | 13.8 µV | 29.2 µV | **+6.5 dB** |
| 10–45 Hz | 20.1 µV | 28.6 µV | +3.1 dB |
| 45–55 Hz (mains) | **39.4 µV** | **56.5 µV** | **+3.1 dB** |
| 55–200 Hz | 21.1 µV | 24.0 µV | +1.1 dB |
| 200 Hz–1 kHz | 30.7 µV | 31.4 µV | +0.2 dB |
| 1–2 kHz | 29.9 µV | 28.8 µV | −0.4 dB |
| **10 Hz–1 kHz total** | **57.9 µV** | **74.7 µV** | **+2.2 dB** |

Both pass comfortably: the targets are < 1 mV broadband and < 100 µV at 50 Hz,
so even lifted there is a 22 dB margin on broadband.

> [!success] Ground the switch frame — it is worth 3 dB at mains
> The penalty for lifting it is concentrated exactly where a shield should
> matter: **+6.5 dB below 10 Hz and +3.1 dB at mains**, tapering to nothing by
> 200 Hz and vanishing above it. That is the signature of electric-field pickup
> on a high-impedance node, which is precisely what `N1` on a flying lead is.
> Above 200 Hz the two runs are identical, because there the floor is the
> instrument rather than the board.

> [!note] These numbers are an upper bound on the board, not a measurement of it
> The floor from 200 Hz upward is about **1.1 µV/√Hz** in both runs. The board's
> own output noise should be nearer 0.05 µV/√Hz — a TL074's 18 nV/√Hz plus
> 12 nV/√Hz of thermal noise from the 8k25 seen by the filter, through a
> unity-gain follower. So what is being measured up there is the AD3's own input
> noise, roughly twenty times the board's.
>
> The board is quieter than the instrument can see. Worth knowing before anyone
> tries to improve on 58 µV.

> [!warning] Ignore the peak-sample figure from the first run
> It read 366 mV against a 58 µV RMS signal, which is impossible — a transient
> that size would have put ~5.6 µV in every bin and the measured floor is
> 1.1 µV. It was the AD3 settling at the start of each acquisition: a Hanning
> window is nearly zero at the record edges, so the spectrum never saw it while
> a raw peak did. The script now measures the peak over the middle 80% and keeps
> one raw record so anything genuinely odd can be looked at.

| 9 — headroom | clips at W1 = \_\_ V, or not at 5 V | \_\_ |
| 10 — output chain at `J3` | −0.03 dB at 20 Hz, tip/ring within 0.05 dB, 0 V DC | \_\_ |
| 11 — in situ | acoustic corner moves as predicted | \_\_ |

---

## Related

- [[Test Guide - Sub Crossover Board]]
- [[Design - Sub Crossover Board]]
