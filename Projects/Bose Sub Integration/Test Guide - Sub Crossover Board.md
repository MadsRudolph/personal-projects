---
title: Test Guide - Sub Crossover Board
type: test-guide
tags:
  - electronics
  - audio
  - subwoofer
  - crossover
  - measurement
  - active-project
status: Board populated, not yet powered
started: 2026-08-14
updated: 2026-08-14
---

# Test Guide - Sub Crossover Board

> [!summary] **What this is**
> Bring-up and verification of the populated `subxo` board on the AD3, from
> first power-up to a measured transfer function per switch position.
> - Design intent: [[Design - Sub Crossover Board]]
> - What is actually soldered down: `hardware/kicad/bom-as-built.csv`
> - Measurement method reused from [[Test Guide - Companion 5 Characterisation]]
>
> Gates run in order. **A failed gate stops the run** — do not carry a fault
> forward into a measurement and then try to interpret the result.

---

## Read this before you measure anything

> [!danger] The board will not measure like any frequency written down so far
> Neither the design doc's 86.7 / 130.1 / 191.0 Hz nor the as-built BOM's
> 82 / 119 / 191 Hz is what a swept measurement will show. **Two separate things
> are in play**, and they have to be separated before you can judge a curve.

### 1. f0 is not the −3 dB point

Both documents quote **f0 = 1/(2π·R·√(C1·C2))** — the Sallen-Key *natural*
frequency. A network-analyser sweep gives a **−3 dB point**. Those two coincide
only at Q = 0.707, and Q across these nine settings runs 0.50 to 1.17.

The gap is **−16 to +30 Hz** depending on the setting. Nothing is wrong when
they disagree; they are different quantities.

### 2. The coupling capacitors are inside the filter

`C_in1`/`C_in2` are **220 nF**, not the designed 2.2 µF. The as-built BOM
attributes only a 7.2 Hz input high-pass to this. That is true and it is not the
whole effect.

Those capacitors sit in series with `R1_1`/`R1_2`, and **`R1_1`/`R1_2` are also
the filter's R1**. At 82 Hz a 220 nF cap is 8.8 kΩ — more than half of the 16k5
leg, and reactive rather than resistive. This is precisely the interaction the
design doc's *"Why 2.2 µF and not 1 µF"* callout warned about, at four times the
severity.

### Which effect owns which shift

From a model of the exported netlist, verified two independent ways — closed
form and a full nodal solve — agreeing to 1e-15 dB:

| Setting | Quoted f0 | −3 dB, designed C_in | −3 dB, as built | from definition | from C_in |
|---|---|---|---|---|---|
| 220n / 150n | 106.2 | 107.6 | **114.2** | +1.4 | +6.6 |
| 220n / 120n | 118.7 | 121.4 | **126.3** | +2.7 | +4.8 |
| 220n / 68n | 157.7 | 183.6 | **181.2** | +25.9 | −2.4 |
| 150n / 150n | 128.6 | 112.5 | **121.5** | −16.1 | +9.0 |
| 150n / 120n | 143.8 | 127.5 | **135.4** | −16.3 | +7.9 |
| 150n / 68n | 191.0 | 199.4 | **200.0** | +8.3 | +0.7 |
| 370n / 150n | 81.9 | 95.0 | **100.5** | +13.2 | +5.4 |
| 370n / 120n | 91.6 | 105.1 | **108.6** | +13.6 | +3.5 |
| 370n / 68n | 121.6 | 151.9 | **148.2** | +30.3 | −3.7 |

**On corner frequency the definitional term is usually the larger one.** The
capacitors move the corner by less than ±9 Hz, and on two settings they move it
*down*.

What the capacitors unambiguously do own:

- **Passband level: −1.3 to −3.1 dB at 63 Hz**, purely C_in, worst on 370n/150n.
- **Peaking on 370n / 68n: +1.86 dB → +0.86 dB** above the 20 Hz level. Halved,
  not eliminated.

> [!important] Two corrections to carry into the run
> **Expect ~100 Hz where the commit says 82 Hz** — mostly because it quotes f0.
> Without knowing that you will measure a healthy board and hunt a fault that
> is not there.
>
> **The "avoid 370nF against C2_3" warning is overstated, not obsolete.** It is
> still the most peaked of the nine settings, but the predicted bump is +0.86 dB
> — a broad shelf, not the resonance that Q = 1.17 implies. Whether it is
> audible is a listening question, not a measurement one.

The passband droop sits mostly *below* 63 Hz, where the module produces nothing
anyway, so it likely costs level rather than shape — and the pot absorbs level.
**Measure first. Decide after.** The fix, if wanted, is in
[After the run](#after-the-run).

---

## What you need on the bench

| Item | Note |
|---|---|
| **Working AD3** | Not the one in [[AD3 Repair]] — that unit's analog supply is still faulty |
| **Korad KD3005D** | Set to **15.0 V**, current limit **50 mA** for first power-up |
| DMM | Continuity and DC survey |
| 2× jumper leads with the 6-pin headers | JP1 / JP2 shunts |
| Short wire links | For J5 and J6 — the switch and pot are off-board |
| 10 kΩ pot, 2-pole changeover switch | Only needed from Gate 9 onward |

> [!danger] J4 has no reverse-polarity protection
> `VIN` goes straight from J4 pin 1 into `C10` (100 µF electrolytic) and the
> LM7812 input. There is no series diode and no bridge. **Meter the supply leads
> for polarity before they touch the board.** Backwards means a vented C10.

> [!warning] The AD3 cannot power this board
> Its programmable supplies are ±5 V. The LM7812 needs ≥14 V in. Use the Korad.
> Board ground and AD3 ground must be tied — the Korad's output floats, so this
> is one connection, not a loop.

---

## Test point map

Everything worth probing comes out to a screw terminal or a header pin. There is
no need to probe the DIP or the SMD-free copper anywhere.

| Signal | Where | DC level when healthy |
|---|---|---|
| `VIN` 15 V in | J4 pin 1 | 15.0 V |
| `GND` | J4 pin 2, J1 pin 2, J2 pin 2, J6 pin 3 | 0 V |
| `V12` rail | C12 / C13 / C14 positive leg | 12.0 V |
| `VG_DIV` | junction of R8 / R9 | 6.0 V |
| **`VGND` (6 V reference)** | **any free even pin of JP2 — 2, 4, 6** | 6.0 V |
| `N1` | any even pin of JP1 — 2, 4, 6 | 6.0 V |
| `N2` | C2 side of R2 | 6.0 V |
| `IN_L` / `IN_R` | J1 pin 1 / J2 pin 1 | 0 V |
| `A_L` / `A_R` | far leg of R_b1 / R_b2 | 6.0 V |
| **`OUT1` — filter output** | **J5 pin 1** | 6.0 V |
| `OUT2` — inverted | J5 pin 2 | 6.0 V |
| `SW_COM` | J5 pin 3 | 6.0 V (link fitted) |
| `POT_TOP` — after C_out | J6 pin 1 | **0 V** |
| `POT_W` — wiper | J6 pin 2 | 0 V |
| `OUT_TIP` / `OUT_RING` | J3 pin 1 / pin 2 | 0 V |
| `OUT_GND` | J3 pin 3 | 0 V |

> [!important] JP1 and JP2 even pins are **not** the same net
> JP2 pins 2/4/6 are `VGND` — the 6 V reference, and the right place to clip a
> scope negative. JP1 pins 2/4/6 are `N1` — a live filter node. Clipping a scope
> ground to JP1 shorts the filter.

### Jumper settings

- **JP1 selects C1.** Pin 1 ↔ `C1_1` (**not fitted — leave open**), pin 3 ↔
  `C1_2` 220n, pin 5 ↔ `C1_3` 150n. Shunt bridges the odd pin to its even
  neighbour. **Both pos2 and pos3 fitted = 220n ∥ 150n = 370 nF.**
- **JP2 selects C2.** Pin 1 ↔ `C2_1` 150n, pin 3 ↔ `C2_2` **120n** (as built),
  pin 5 ↔ `C2_3` 68n. Exactly one shunt.
- **JP3 is the ground lift.** Shunt fitted = input and output grounds hard-tied.
  Removed = joined only through R7's 10 Ω. **Fit it for all bench testing.**

---

## Gate 0 — Cold checks, no power

Nothing here needs the AD3. Five minutes, and it catches the failures that cost
parts.

1. **Supply short.** DMM in resistance across J4 pin 1 → pin 2. Expect a rising
   reading as C10 charges, settling **> 10 kΩ**. A dead short is the LM7812 in
   backwards or a solder bridge.
2. **Rail short.** `V12` → `GND`. Same story, settles high.
3. **Electrolytic orientation.** All four are + toward the higher potential:
   `C10` + to `VIN`, `C11` + to `V12`, `C15` + to `VG_DIV`, and **`C_out1` + to
   J5 pin 3 (`SW_COM`)**, stripe toward J6. C_out1 backwards means 6 V reverse
   and a slow death.
4. **U1 pin 1 orientation.** Notch toward the pin-1 end. If it is socketed, leave
   it **out** for Gate 1.
5. **U2 orientation.** LM7812 tab/back per the silkscreen — `VIN` on pin 1, `GND`
   pin 2, `V12` pin 3.
6. **Ground lift.** Continuity J3 pin 3 → J1 pin 2: **0 Ω with the JP3 shunt
   fitted, 10 Ω without.** Both readings prove R7 and JP3 are both real.
7. **JP1 pos 1 stays open** for the whole run. `C1_1` is not fitted.

> [!success] Gate 0 passes when
> No short on either rail, every electrolytic the right way round, and JP3
> switching cleanly between 0 Ω and 10 Ω.

---

## Gate 1 — Power up in stages

**U1 out of its socket.** Korad at **15.0 V, 50 mA limit**.

| Check | Expect |
|---|---|
| Supply current | **4–8 mA** (LM7812 quiescent + the 10k/10k divider) |
| `V12` | **12.0 V ± 0.25** |
| `VG_DIV` | **6.0 V ± 0.1** |
| LM7812 temperature | Cold. It drops 3 V at ~10 mA = 36 mW |

If the Korad current-limits, kill it. Something is shorted that Gate 0 missed.

Power down. **Insert U1**, notch correct. Power up again.

| Check | Expect |
|---|---|
| Supply current | **10–16 mA** |
| `V12` | unchanged, 12.0 V ± 0.25 |

> [!success] Gate 1 passes when
> Current lands in the 10–16 mA band and the rail holds 12 V. Anything above
> ~25 mA means an op-amp section is oscillating or a pin is shorted.

---

## Gate 2 — DC survey

No signal. DMM on every node in the test point map. The whole signal chain sits
at exactly 6.00 V because **no DC current flows through the filter** — `C1` and
`C2` block it, and the TL074's JFET inputs draw picoamps.

| Node | Expect | A wrong reading means |
|---|---|---|
| `VGND` (JP2 even pin) | 6.00 ± 0.05 V | A3 dead or the divider wrong |
| `A_L`, `A_R` | 6.00 ± 0.05 V | **`R_b1`/`R_b2` open — the fault the design doc predicted** |
| `N1`, `N2` | 6.00 ± 0.05 V | R1 or R2 open |
| `OUT1` (J5 pin 1) | 6.00 ± 0.05 V | **At a rail = A1 has no DC path. Check R_b.** |
| `OUT2` (J5 pin 2) | 6.00 ± 0.05 V | A2 or R3/R4 |
| `SPARE_OUT` (U1 pin 14) | 6.00 ± 0.05 V | A4 not terminated — it will oscillate into its neighbours |
| `POT_TOP` (J6 pin 1) | **0.00 ± 0.01 V** — *only with the pot fitted* | C_out leaky or backwards |

> [!warning] `POT_TOP` reads ~6 V, not 0 V, if J6 is empty
> That 0 V expectation assumes the 10 kΩ pot is on J6 holding the node down.
> With J6 unconnected, `POT_TOP` is a floating plate: `C_out` self-discharges
> through its own leakage, the capacitor voltage collapses, and the node drifts
> **up to `SW_COM` — about 6 V**. That is correct behaviour for an unloaded
> coupling cap, not a fault.
>
> Meter it and the DMM's own 10 MΩ becomes the load, so it will crawl toward
> 0 V with a **100 s time constant** — minutes to settle. Do not read a slow
> drift as a leaky capacitor.
>
> To get a real reading without the pot, put any **10 kΩ resistor from J6 pin 1
> to J6 pin 3**. That is the pot's bottom leg, it pins the node at 0 V, and
> `R3`/`R4`/`R8`/`R9` are all 10 kΩ so the value is already in stock.

> [!success] Gate 2 passes when
> Every signal node is 6.00 V and `POT_TOP` is 0 V. This single table proves the
> bias network, all four op-amp sections, and the output coupling cap.

---

## Gate 3 — Prove the instrument before you trust the board

Do not skip this. It takes thirty seconds and it is the difference between a
measurement and a number.

**Through-calibration.** Disconnect from the board entirely. Tie `1+`, `2+` and
`W1` together on one node; tie `1−`, `2−` and `GND` together on another.

Network Analyzer, 10 Hz → 2 kHz. Expect **0.00 dB ± 0.05 and 0.0° ± 0.5** at
every point. Anything else is the instrument, the leads, or a channel whose
negative is floating — the exact failure `rig_check.py` was written to catch.

Optional but sharper: a 10 kΩ + 100 nF RC, corner at 159 Hz, right in our band.
It should read −3.01 dB and −45.0° at 159 Hz.

---

## Gate 4 — Wiring for the sweeps

```
   Korad 15V (+) ──► J4.1        (POLARITY CHECKED)
   Korad 15V (−) ──► J4.2

   W1  (yellow) ──┬──► J1.1   IN_L
                  └──► J2.1   IN_R        both inputs driven together
   GND (black)  ──┬──► J1.2   board GND
                  └──► AD3 GND

   1+ (orange)     ──► J1.1                reference: drive AT the board
   1− (orange/wht) ──► J1.2                board GND

   2+ (blue)       ──► J5.1   OUT1         filter output
   2− (blue/wht)   ──► JP2 pin 6  VGND     the 6 V reference
```

Board links for the sweeps, standing in for the off-board hardware:

- **JP3 shunt fitted.**
- **J5 and J6 can both stay empty.** Gates 5–9 all probe `OUT1` at J5 pin 1,
  which is upstream of the switch, `C_out` and the pot. Nothing downstream loads
  it or changes it.
- Fit **J5 pin 1 ↔ pin 3** only when you want the signal to reach the output
  chain. (Pin 2 ↔ pin 3 selects the inverted output instead.)
- Fit **J6 pin 1 ↔ pin 2** only for Gate 10, to stand in for a pot at maximum.

> [!note] No pot yet? Run Gates 5–9 and defer Gate 10
> The nine transfer functions, the mono sum, the polarity check, the noise floor
> and the headroom test need nothing on J6. **Only Gate 10 does.** Come back to
> it when the pot arrives — or substitute a plain 10 kΩ resistor across J6 pins
> 1→3 plus a link 1→2, which reproduces "pot at maximum" exactly and lets Gate
> 10 run in full.

> [!important] Why channel 2 references `VGND`, not ground
> `OUT1` sits at 6 V DC and the AD3 has no AC coupling. Referenced to ground you
> would need the ±25 V range and throw away ~20 dB of stopband resolution.
> Differential against `VGND` cancels the 6 V, lets both channels run the ±2 V
> range, and rejects any wobble on the virtual ground at the same time.

**Driving both inputs in parallel is deliberate**, not convenience: it puts
16k5 ∥ 16k5 = the 8.25 kΩ the filter is designed around. Driving one leg alone
changes R1 and every corner frequency with it.

### Network Analyzer settings

| Setting | Value |
|---|---|
| Start / stop | 15 Hz → 2 kHz |
| Steps | 60–70 (≈30 per decade) |
| Amplitude | **1 V** (2 Vpp) |
| Offset | 0 V |
| Channel range | 2 V, both |
| Periods / settle | ≥ 8 periods, settle ≥ 50 ms — 15 Hz needs the time |

---

## Gate 5 — The nine transfer functions

For each JP1 × JP2 combination, sweep and record. **Reference each curve to its
own value at 63 Hz** — the bottom of the module's acoustic band, and a stable
reference given the as-built passband is not flat.

### Predicted corner, and the tolerance band it may legitimately land in

Corner = the frequency 3 dB below that setting's own 63 Hz level. Band is the
2.5–97.5 percentile over ±5% capacitors, ±2% R_b, ±0.5% resistors.

> [!note] Every number below is generated, not typed
> `tools/subxo_model.py` produces all three tables in this gate. Run it to
> regenerate them, `--designed` to see what 2.2 µF coupling caps would have
> given, or import `response()` to overlay the model on a measured sweep.
> ```
> py -3.13 tools/subxo_model.py
> ```

| JP1 | JP2 | Gain at 63 Hz | **Corner** | Acceptable |
|---|---|---|---|---|
| pos2 (220n) | pos1 (150n) | −4.04 dB | **114.2 Hz** | 110–120 |
| pos2 (220n) | pos2 (120n) | −2.95 dB | **126.3 Hz** | 120–134 |
| pos2 (220n) | pos3 (68n) | −1.15 dB | **181.2 Hz** | 168–197 |
| pos3 (150n) | pos1 (150n) | −4.14 dB | **121.5 Hz** | 117–128 |
| pos3 (150n) | pos2 (120n) | −3.12 dB | **135.4 Hz** | 129–144 |
| pos3 (150n) | pos3 (68n) | −1.39 dB | **200.0 Hz** | 186–217 |
| pos2+3 (370n) | pos1 (150n) | −4.07 dB | **100.5 Hz** | 97–105 |
| pos2+3 (370n) | pos2 (120n) | −2.79 dB | **108.6 Hz** | 103–115 |
| pos2+3 (370n) | pos3 (68n) | −0.71 dB | **148.2 Hz** | 137–161 |

### Full predicted shape, dB relative to each setting's own 63 Hz

| JP1 / JP2 | 20 | 30 | 50 | 63 | 80 | 100 | 125 | 160 | 200 | 250 | 400 | 800 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 220n / 150n | +1.01 | +0.99 | +0.51 | 0 | −0.85 | −2.05 | −3.75 | −6.25 | −9.02 | −12.15 | −19.51 | −31.16 |
| 220n / 120n | +0.44 | +0.54 | +0.31 | 0 | −0.57 | −1.49 | −2.92 | −5.23 | −7.93 | −11.08 | −18.53 | −30.28 |
| 220n / 68n | −0.45 | −0.21 | −0.04 | 0 | −0.01 | −0.14 | −0.61 | −1.91 | −4.09 | −7.14 | −14.91 | −27.00 |
| 150n / 150n | +1.04 | +1.01 | +0.49 | 0 | −0.77 | −1.80 | −3.20 | −5.22 | −7.49 | −10.15 | −16.75 | −27.92 |
| 150n / 120n | +0.55 | +0.61 | +0.32 | 0 | −0.54 | −1.33 | −2.48 | −4.28 | −6.43 | −9.04 | −15.69 | −26.96 |
| 150n / 68n | −0.27 | −0.05 | +0.02 | 0 | −0.08 | −0.27 | −0.65 | −1.54 | −3.00 | −5.24 | −11.92 | −23.56 |
| 370n / 150n | +1.16 | +1.17 | +0.65 | 0 | −1.19 | −2.96 | −5.39 | −8.72 | −12.11 | −15.72 | −23.62 | −35.56 |
| 370n / 120n | +0.41 | +0.55 | +0.37 | 0 | −0.83 | −2.27 | −4.50 | −7.78 | −11.21 | −14.87 | −22.88 | −34.88 |
| 370n / 68n | −0.79 | −0.48 | −0.15 | 0 | +0.07 | −0.21 | −1.32 | −3.99 | −7.42 | −11.29 | −19.70 | −31.94 |

> [!success] Gate 5 passes when
> Each measured corner is inside its band, **and** the measured curve tracks the
> predicted shape within ±0.5 dB from 30 Hz to 400 Hz. Corner alone is not
> enough — the shape is what the model is really claiming.

**Also check the ultimate slope.** 400 → 800 Hz should be **−11.2 to −12.2 dB**
(one octave of a 2nd-order roll-off). Shallower means a stray path around the
filter. Steeper means something is resonating.

**Settle the peaking question.** Measure the rise above each setting's 20 Hz
level. Predicted, as built:

| Setting | Peak above 20 Hz | Setting | Peak above 20 Hz |
|---|---|---|---|
| 220n / 150n | +0.03 dB | 150n / 68n | +0.29 dB |
| 220n / 120n | +0.09 dB | 370n / 150n | +0.04 dB |
| 220n / 68n | +0.46 dB | 370n / 120n | +0.14 dB |
| 150n / 150n | +0.02 dB | **370n / 68n** | **+0.86 dB** |
| 150n / 120n | +0.07 dB | | |

370n / 68n remains the most peaked, but at +0.86 dB rather than the +1.86 dB the
designed coupling caps would have given. Whatever the sweep shows, **update
`bom-as-built.csv`** — its warning currently reads as though that setting is
unusable, and the measurement will say whether it is.

---

## Gate 6 — Mono sum

Three sweeps at one setting (220n / 120n is fine):

1. **Both driven** — W1 to J1.1 and J2.1. Reference.
2. **L only, R grounded** — W1 to J1.1, and **short J2.1 to J2.2**.
3. Repeat with R driven, L grounded.

| Result | Verdict |
|---|---|
| **−6.02 dB, flat with frequency** | Correct. Both legs work, both R1 are in tolerance |
| −2.5 dB at 30 Hz rising to −5.4 dB at 200 Hz | **The undriven input is floating.** Ground it and repeat |
| One leg differs from the other by > 0.15 dB | R1_1 / R1_2 mismatch, or a cold joint |

> [!important] The undriven input must be **shorted to ground**, not left open
> Open, the leg presents 16k5 in series with (100k ∥ C_in) instead of 16k5 to
> ground. The sum is then frequency-dependent and reads like a fault. This is the
> single easiest way to mis-measure this board.

That the grounded case is flat at exactly −6.02 dB across the whole band is what
makes it a clean test — any tilt at all is diagnostic.

---

## Gate 7 — Polarity switch

Move `2+` from J5 pin 1 to **J5 pin 2** (`OUT2`) and re-sweep.

| Check | Expect |
|---|---|
| Magnitude vs `OUT1` | **0.00 dB ± 0.12** (R3/R4 are 1%) |
| Phase vs `OUT1` | **180.0° ± 0.5** across the whole band |

A2 is a unity inverter around `VGND`, so this should be near-perfect. Drift with
frequency means A2 is slewing or R3/R4 is wrong.

Then fit the real changeover switch to J5 and confirm it selects pin 1 in one
position and pin 2 in the other, with pin 3 as common.

---

## Gate 8 — Noise and hum floor

Short **both** inputs to ground (J1.1→J1.2, J2.1→J2.2). W1 off. Scope on `OUT1`
against `VGND`, ±2 V range, and run the Spectrum Analyzer 10 Hz – 1 kHz.

| Measure | Expect |
|---|---|
| Broadband RMS at `OUT1` | **< 1 mV rms** |
| 50 Hz component | < 100 µV on an open bench |
| 100 Hz and 150 Hz | Below the 50 Hz line |

Record the number. It is the baseline for the same measurement once the board is
in its enclosure — that comparison is what tells you whether the enclosure is
earning its keep, and whether the JP3 lift is ever needed.

> [!note] Denmark is 50 Hz
> The 100 k bias resistors make `A_L`/`A_R` the highest-impedance nodes on the
> board and the most likely pickup points. Some 50 Hz on an unshielded bench is
> expected, not a fault.

---

## Gate 9 — Headroom

Drive **40 Hz** (well inside the passband on every setting). Raise W1 from 0.5 V
amplitude to its **5 V maximum** while watching `OUT1` on the scope for
flat-topping, and the Spectrum Analyzer for harmonics rising out of the floor.

The prediction is interesting: at 40 Hz the passband gain is about −1 to −3.3 dB,
so W1 at full 5 V amplitude puts roughly **3.5 Vpk** at the output — right at the
edge of a worst-case TL074's swing on a 12 V rail (±3 V guaranteed, ±4.5 V
typical).

| Result | Meaning |
|---|---|
| No clipping at W1 = 5 V | **Headroom ≥ 3.5 Vrms input.** The AD3 cannot overdrive this board. Done — the Saga cannot either |
| Clips at some W1 < 5 V | Record it. Convert to max input volts and compare against the Saga's actual maximum output |

Either outcome is a pass; the point is to know the number, because the Saga in
active mode has gain and the board is on a single 12 V rail.

---

## Gate 10 — Output chain

**Needs hardware on J6.** Fit the 10 kΩ pot (pin 1 top, pin 2 wiper, pin 3
ground) and the changeover switch to J5. Probe `2+` on **J3 pin 1** (tip), `2−`
on **J3 pin 3** (`OUT_GND`).

Without the pot, a **10 kΩ resistor across J6 pins 1→3 and a link 1→2** gives
"pot at maximum" and covers every row below except the sweep test.

| Check | Expect |
|---|---|
| Pot at maximum, vs `OUT1` | **−0.03 dB at 20 Hz**, 0.00 dB above 60 Hz (C_out into 10k = 1.6 Hz) |
| Tip vs ring | Within **0.05 dB** and 0.0° — R5 and R6 are both 100 Ω |
| Pot sweep | Smooth to full attenuation, no crackle, no dead spot |
| DC at tip and ring | **0.00 V.** Any DC here thumps the driver at power-on |

The 100 Ω resistors drop nothing into the AD3's 1 MΩ. They will drop about 1.1%
(−0.1 dB) into the Bose's real 8.9 kΩ, which is expected and harmless.

---

## Gate 11 — In situ

Only after Gates 0–10. Reuse the Phase 0 rig unchanged:

- `tools/woofer_sweep.py` — swept response through the finished chain into the
  module
- `tools/plot_acoustic.py` — plotting

Sweep at each JP setting and confirm the **acoustic** corner moves as predicted.
The module's own 63–203 Hz bandpass cascades with ours, so expect the acoustic
result to be narrower than the electrical one at every setting — that is the
design working, not an error.

Then set the crossover by ear. The design has always said the corner cannot be
predicted, only chosen.

---

## After the run

### If you want the design response back

Adding ~2 µF in parallel with `C_in1` and `C_in2` recovers the **designed
response** — it will not make the measured corners match the quoted f0 figures,
because those were never −3 dB points. What it buys is the 1.3–3.1 dB of
passband level, and it costs some of the damping that currently flattens
370n / 68n.

The as-built note says 2.2 µF film would not fit — true, and it is a film cap
that will not fit. But node `A_L`/`A_R` sits at a steady **6 V DC** with the
source side at 0 V, so the polarity across `C_in` is fixed and defined. A
**2.2 µF electrolytic, + toward the board's inside**, is a fraction of the size
and entirely legitimate here. It can be tacked across the existing pads on the
copper side; this is a single-sided milled board with through-hole parts, so
there is room underneath.

**Do not do this before Gate 5.** The measurement may well show the as-built
response is the better one — the peaking is gone, and the droop sits below where
the module plays.

### Update the record

Whatever the run shows, two files want correcting afterwards:

- **`bom-as-built.csv`** — the `C_in1`/`C_in2` note attributes only a 7.2 Hz
  high-pass to the substitution, and the `JP1`/`JP2` notes quote corner
  frequencies from the ideal formula. Both understate what actually changed.
- **[[Design - Sub Crossover Board]]** — the Verification section's expected
  corners (86.7 / 130.1 / 191.0 Hz) describe a board that was never built.

---

## Related

- [[Design - Sub Crossover Board]]
- [[Test Guide - Companion 5 Characterisation]] — the AD3 method this reuses
- [[AD3 Repair]] — do not use that unit
- [[Plan - Sub Crossover Board]]
