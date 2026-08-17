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
status: Rev B built and wired; bring-up outstanding
started: 2026-08-14
updated: 2026-08-16
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

## This is now the rev B procedure

Rev A was built, measured through Gate 5 and characterised in
[[Results - Sub Crossover Bring-up]]. Rev B is a new board with the panel
hardware wired. **Four things have never been powered**, so this is a fresh
bring-up rather than a re-test:

| New in rev B | Why it changes the procedure |
|---|---|
| `C1_1` fitted at **470 nF** | Rev A left it out. Its value is unverified, so position 1's corner gets a *band*, not a point |
| **`LK1` ground link** | The GND pour fills as two islands and this wire bridges them. Without it the board has no supply return at all — new Gate 0 check |
| **`D1`/`D2` status LEDs** | Adds ~2.13 mA each, so every current figure in Gate 1 moved |
| **Rotary switch on `JP1`/`JP2`** | Three ganged positions replace nine jumper combinations, and the loom is the most likely new source of hum |

Also now fitted, where rev A ran without them: the **10 kΩ pot** on `J6` (which
is why Gate 10 was deferred), and the **polarity switch** on `J5`, whose second
pole drives `D2`.

> [!warning] Two instructions elsewhere in this document are stale
> Gate 0 item 7 said *"JP1 pos 1 stays open for the whole run, C1_1 is not
> fitted."* That is no longer true. And Gate 2's long warning about `POT_TOP`
> floating to 6 V applied only while `J6` was empty. Both are corrected in place
> below; this note exists in case you are reading an older copy.

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
| **Panel hardware, already wired** | Rotary on `JP1`/`JP2`, polarity switch on `J5` + `J7`, 10 kΩ pot on `J6`. All fitted for rev B |
| 1 jumper shunt | `JP3` only. The rotary frees `JP1`/`JP2`, so the old third-shunt problem is gone |
| *(optional)* spare shunts | To fall back to jumper selection if the rotary misbehaves |

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
| `POT_TOP` — after C_out | J6 pin 1 | **0 V** (pot now fitted, so this is real) |
| `POT_W` — wiper | J6 pin 2 | 0 V |
| `OUT_TIP` / `OUT_RING` | J3 pin 1 / pin 2 | 0 V |
| `OUT_GND` | J3 pin 3 | 0 V |
| **`GND_LNK`** — power-corner ground | J4 pin 2 | 0 V, and **~0 Ω to J1 pin 2** |
| `PWR_A` — green LED anode | junction of R10 / D1 | ~2 V |
| `INV_K` — amber LED cathode | J7 pin 1 | 0 V inverted, ~10 V normal |

> [!important] JP1 and JP2 even pins are **not** the same net
> JP2 pins 2/4/6 are `VGND` — the 6 V reference, and the right place to clip a
> scope negative. JP1 pins 2/4/6 are `N1` — a live filter node. Clipping a scope
> ground to JP1 shorts the filter.

### Capacitor selection — now a rotary, not jumpers

- **JP1 selects C1.** Pin 1 ↔ `C1_1` **470n (fitted on rev B)**, pin 3 ↔ `C1_2`
  220n, pin 5 ↔ `C1_3` 150n. Even pins are `N1`.
- **JP2 selects C2.** Pin 1 ↔ `C2_1` 150n, pin 3 ↔ `C2_2` 120n, pin 5 ↔ `C2_3`
  68n. Even pins are `VGND`.
- **JP3 is the ground lift.** Shunt fitted = input and output grounds hard-tied.
  Removed = joined only through R7's 10 Ω. **Fit it for all bench testing.**

A 2-pole 3-position rotary now drives both headers, one pole each:

| Detent | `JP1` even ↔ | C1 | `JP2` even ↔ | C2 | Corner |
|---|---|---|---|---|---|
| 1 | pin 1 | 470n | pin 1 | 150n | ~94 Hz |
| 2 | pin 5 | 150n | pin 3 | 120n | 135.5 Hz |
| 3 | pin 3 | 220n | pin 5 | 68n | 189.2 Hz |

> [!danger] Never wire one header pin to two switch lugs
> Splitting a wire ties those lugs together permanently — the rotary isolates
> common from lugs, not lugs from each other. Every position then collapses to
> the same capacitance and you measure three identical curves. This is why
> `C1_1` is fitted rather than paralleling `C1_2 ∥ C1_3` on one lug, which is
> what rev A did with two shunts.

Jumper selection still works as a fallback if the rotary has to come off — with
`C1_1` fitted there are nine combinations again, but the values differ from
rev A's, so re-derive rather than reusing the old table.

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
7. **LED orientation.** Square pad is the cathode on both. `D1` green, `D2`
   amber.

### Gate 0b — the two rev B checks

> [!danger] `LK1` first, before anything else
> Meter **J4 pin 2 → J1 pin 2**. Must be **~0 Ω**.
>
> Those are `GND_LNK` and `GND`, two separate nets bridged only by the `LK1`
> wire link. Power enters the board at `J4.2` and the TL074's ground pin is on
> the other side, so with `LK1` open or cold-jointed the board has **no supply
> return at all**. It will look stone dead while measuring a healthy 12 V on the
> rail — the most confusing possible failure, and a five-second check.

**Verify the rotary cold.** This catches every loom error before power is
applied. For each detent, probe a `JP1` even pin against each odd pin, then the
same on `JP2`:

| Detent | `JP1` even ↔ | `JP2` even ↔ |
|---|---|---|
| 1 | pin **1** only | pin **1** only |
| 2 | pin **5** only | pin **3** only |
| 3 | pin **3** only | pin **5** only |

**"Only" is the whole point.** Continuity to two odd pins in one detent means
lugs are tied together and all three positions will measure the same.

Also confirm **`A0` ↔ `B0` open in every detent** — a wafer that busses its
commons would tie `N1` to `VGND` and silence the filter. And if the switch frame
is grounded, confirm the frame reads open to all eight lugs first.

> [!success] Gate 0 passes when
> No short on either rail, every electrolytic the right way round, JP3 switching
> cleanly between 0 Ω and 10 Ω, **`LK1` reading ~0 Ω**, and the rotary selecting
> exactly one capacitor per pole per detent.

---

## Gate 1 — Power up in stages

**U1 out of its socket.** Korad at **15.0 V, 50 mA limit**.

> [!important] Every current figure below includes the new LEDs
> `D1` and `D2` each draw **(12 − 2.0) / 4700 = 2.13 mA**. `D1` is always lit;
> `D2` only in the inverted position. Rev A's 4–8 and 10–16 mA bands no longer
> apply.

| Check | Expect |
|---|---|
| Supply current, switch NORMAL | **6–10 mA** (LM7812 + divider + `D1`) |
| `V12` | **12.0 V ± 0.25** |
| `VG_DIV` | **6.0 V ± 0.1** |
| Green LED | Lit |
| LM7812 temperature | Cold. It drops 3 V at ~10 mA = 36 mW |

If the Korad current-limits, kill it. Something is shorted that Gate 0 missed.

Power down. **Insert U1**, notch correct. Power up again.

| Check | Expect |
|---|---|
| Supply current, NORMAL | **12–18 mA** |
| Supply current, INVERTED | **14–20 mA** |
| `V12` | unchanged, 12.0 V ± 0.25 |

**Flip the polarity switch and watch the current.** It should step by about
**2 mA** as the amber LED comes on. That one observation verifies `D2`, `R11`,
`J7` and the whole second pole of the switch at once.

> [!warning] If the amber lamp lights in the NORMAL position
> The lamp pole is phased backwards. Move the `J7` pin 1 wire from the bottom
> lug to the top lug of that pole. Harmless — the two poles are electrically
> independent, so the audio is unaffected either way. It just lies to you about
> which mode you are in.

> [!success] Gate 1 passes when
> Current lands in the 12–18 mA band, steps ~2 mA with the polarity switch, and
> the rail holds 12 V. Anything above ~30 mA means an op-amp section is
> oscillating or a pin is shorted.

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
| `POT_TOP` (J6 pin 1) | **0.00 ± 0.01 V** | C_out leaky or backwards, **or the pot is not connected** |
| `OUT_TIP` / `OUT_RING` (J3 pins 1, 2) | **0.00 V** | DC here thumps the driver at power-on |

> [!note] This is the first run where `POT_TOP` should genuinely read 0 V
> Rev A always measured ~6 V there and the old guide carried a long explanation
> of why: with `J6` empty, `POT_TOP` is a floating plate and drifts up to
> `SW_COM`. The 10 kΩ pot is fitted now, so it holds the node at 0 V and the
> reading is real.
>
> **If it still sits near 6 V, the pot is not connected** — check `J6` pin 3
> reaches the pot's bottom leg. That is now a wiring fault, not expected
> behaviour.

> [!success] Gate 2 passes when
> Every signal node is 6.00 V, `POT_TOP` is 0 V, and there is no DC at the
> output terminals. This single table proves the bias network, all four op-amp
> sections, the output coupling cap and the pot wiring.

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

Board state for the sweeps:

- **JP3 shunt fitted.**
- **Rotary fitted** on `JP1`/`JP2`, verified cold at Gate 0b.
- **Polarity switch on `J5` and `J7`**, pot on `J6` — all real hardware now, no
  stand-in links needed.
- Set the polarity switch to **normal** for Gates 5, 6, 8 and 9. Gate 7 is where
  it gets exercised.

> [!note] Gates 5–9 do not care what is downstream
> They all probe `OUT1` at `J5` pin 1, which is upstream of the polarity switch,
> `C_out` and the pot. Nothing below that point loads it or changes it, so the
> results are directly comparable with rev A's.

> [!important] The 3.5 mm jack is not needed for any electrical gate
> `J3` is a screw terminal, so **Gate 10 runs by clipping straight onto it** —
> `2+` on `J3` pin 1, `2−` on `J3` pin 3. Only Gate 11, the acoustic run into
> the module, needs the jack and cable.

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

## Gate 5 — The three rotary positions

> [!tip] Run it with `tools/subxo_gate5.py` rather than by hand
> The script drives the AD3 directly through `pydwf`, so the only manual step
> is turning the knob. Per detent it sweeps, extracts the corner and the 63 Hz
> level, scores both against the model, writes a CSV and prints a verdict —
> then waits for you to click round one position.
>
> ```
> python tools/subxo_gate5.py
> python tools/subxo_gate5.py --detents 1 3     # just those two
> python tools/subxo_gate5.py --dry-run         # no AD3, exercise the maths
> ```
>
> **Use the full path: `C:\Python314\python.exe`.** This machine has several
> Pythons — a conda base at `miniconda3`, the py launcher's 3.11 to 3.13, and a
> bare 3.14 — and `pydwf` is installed in **only** the 3.14 one. Which
> interpreter a bare `python` hits depends on whether conda is active in that
> shell, so spell it out rather than trusting the PATH. Every AD3 tool here is
> affected; the pure-maths tools (`subxo_model`, `subxo_compare`, the plotters)
> run under any of them.
>
> If you get it wrong the script now says so and names the interpreter that
> works, rather than dying on `ModuleNotFoundError`.
>
> It knows detent 1 is the unverified one and scores it against a ±10 % band
> rather than a point, and if the corner lands outside that band it **back-solves
> `C1_1`'s actual capacitance from the measured corner** so the part becomes a
> known quantity instead of a mystery.
>
> Defaults match the rig below exactly: 15 Hz–2 kHz, 70 steps, 1 V, 2 V range.
> `--dry-run` synthesises the curves from the model, which is how the analysis
> path was verified without hardware — including a deliberate −19 % part, which
> it correctly failed and then identified to 0.1 %.

Sweep each detent and record. **Reference each curve to its own value at 63 Hz**
— the bottom of the module's acoustic band, and a stable reference given the
as-built passband is not flat.

### What to expect, rev B

| Detent | C1 / C2 | Corner | Gain at 63 Hz | Confidence |
|---|---|---|---|---|
| 2 | 150n / 120n | **135.5 Hz** | −3.18 dB | tight — both caps measured |
| 3 | 220n / 68n | **189.2 Hz** | −1.02 dB | tight — both caps measured |
| 1 | 470n / 150n | **91.6 – 96.7 Hz** | −4.2 to −4.4 dB | **band, not a point** |

> [!important] Judge the build on detents 2 and 3, not detent 1
> Those two use capacitors already measured to ±0.3 % during rev A's fit, so
> they should land within a few tenths of a percent. They are the verdict on
> whether this build is sound.
>
> Detent 1 gets a band because `C1_1` is a **new part at ±10 % that nobody has
> measured**. 94.0 Hz is nominal; 91.6 Hz is +10 %, 96.7 Hz is −10 %. Anywhere
> in that span is a good capacitor, not a fault.
>
> If detent 1 lands outside the band, back the real value out from the measured
> corner — the model inverts cleanly, and this is exactly how `C2_3` was pinned
> down at −6.2 % out-of-sample during rev A.

Three settings, not nine: the rotary gangs `JP1` and `JP2` together. The nine
individual combinations below remain physically reachable with shunts if the
loom ever has to come off, but the values differ from rev A's now that `C1_1`
is fitted, so re-derive rather than reusing the numbers.

### Rev A reference — the nine jumper combinations

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

### Then the switch itself

The changeover is fitted on rev B, so test it rather than simulate it. Probe
`2+` on **`J5` pin 3** (`SW_COM`) and sweep in both lever positions:

| Lever | Expect at `SW_COM` | Amber LED |
|---|---|---|
| normal | matches `OUT1`, 0° | **off** |
| inverted | matches `OUT2`, 180° | **on** |

**The lamp is part of this test.** Its pole and the audio pole share one shaft,
so if the amber lights in the position that measures 0° the lamp pole is phased
backwards — move the `J7` pin 1 wire to the other throw. The audio is correct
either way; only the indication is wrong.

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

> [!important] On rev B this is the gate that matters most
> It is the first noise measurement with the **rotary loom** fitted, and that
> loom is by far the most likely way this build got worse than rev A. One of its
> wires carries `N1`, about 3 kΩ to AC ground at 50 Hz — the highest-impedance
> conductor in the whole thing, now on a flying lead instead of a 2.54 mm shunt.
>
> Measure it **twice**: once with the rotary's frame ground connected, once with
> it lifted. The difference is the value of shielding that switch, and it tells
> you whether the plastic enclosure needs a conductive coating. Record both.
>
> Rev A never measured this gate at all, so there is no prior number to compare
> against — the <1 mV rms and <100 µV at 50 Hz targets are the only reference.

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

**Deferred through all of rev A because the pot was never bought. It can finally
run.** The 10 kΩ pot is on `J6` (pin 1 top, pin 2 wiper, pin 3 ground) and the
changeover is on `J5`.

Probe `2+` on **J3 pin 1** (tip), `2−` on **J3 pin 3** (`OUT_GND`). `J3` is a
screw terminal, so **the 3.5 mm jack does not need to be fitted** — clip
directly onto it.

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
