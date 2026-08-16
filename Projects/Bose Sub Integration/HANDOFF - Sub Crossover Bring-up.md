---
title: HANDOFF - Sub Crossover Bring-up
type: handoff
tags:
  - electronics
  - audio
  - subwoofer
  - crossover
  - handoff
status: Gates 0-5 pass; Gates 6-11 outstanding; rotary switch sourced and specified
started: 2026-08-15
updated: 2026-08-16
---

# HANDOFF - Sub Crossover Bring-up

## Paste this into the new session

> The `subxo` sub-crossover board is built and electrically verified. Read
> `Projects/Bose Sub Integration/HANDOFF - Sub Crossover Bring-up.md` in full,
> then `Results - Sub Crossover Bring-up.md` and
> `Test Guide - Sub Crossover Board.md`. Run `git pull` in
> `C:\Users\Mads2\personal-projects` first.
>
> I am at school with access to the component shop. I have found a 3-position
> rotary switch and I can measure exact part footprints if we decide the board
> needs a respin. Start with the switch — tell me what to check on it and how
> to wire it. Do not start a PCB respin without talking it through first.

*Session of 2026-08-16 answered this: the switch is 2-pole 3-position, the
wiring is in Decision 1 below, and the original wiring sketch in this document
was wrong — see "The wiring rule that governs everything below".*

---

## Where things stand

A mono-summing 2nd-order Sallen-Key low-pass that lets the Bose Companion 5
bass module join the main stereo chain. Design in
[[Design - Sub Crossover Board]]. Board is single-sided, milled, 185 tracks all
on B.Cu, zero vias, zero wire links.

**Gates 0–5 of [[Test Guide - Sub Crossover Board]] pass.** Nine transfer
functions swept on the AD3. A model of the as-built netlist reproduces all nine
within **0.80 % in corner and 0.037 dB in gain**.

### The board as measured

| Corner | JP1 | JP2 | Shunts | Level at 63 Hz | Peak |
|---|---|---|---|---|---|
| 100.7 Hz | pos2+3 | pos1 | 3 | −4.09 dB | +0.04 dB |
| 108.7 Hz | pos2+3 | pos2 | 3 | −2.84 dB | +0.13 dB |
| 113.8 Hz | pos2 | pos1 | 2 | −4.07 dB | +0.03 dB |
| 121.9 Hz | pos3 | pos1 | 2 | −4.18 dB | +0.02 dB |
| 125.4 Hz | pos2 | pos2 | 2 | −2.99 dB | +0.09 dB |
| 135.5 Hz | pos3 | pos2 | 2 | −3.18 dB | +0.06 dB |
| 155.4 Hz | pos2+3 | pos3 | 3 | −0.59 dB | +0.98 dB |
| 189.2 Hz | pos2 | pos3 | 2 | −1.02 dB | +0.55 dB |
| 212.3 Hz | pos3 | pos3 | 2 | −1.29 dB | +0.31 dB |

Two findings worth carrying forward:

- **The 220 nF coupling caps are inside the filter.** `C_in` is in series with
  `R1_1`/`R1_2`, which are also the filter's R1. Costs 1.3–3.1 dB of passband
  level and damps the peaking. Measured, not assumed — the sweep discriminates
  against both alternatives by 5.4 % and 7.8 % in opposite directions.
- **`C2_3` is 63.8 nF, not 68 nF** (−6.2 %, in tolerance). Confirmed
  out-of-sample: predicted a held-out setting to 0.66 % where nominal caps
  missed by 5.2 %.

### Outstanding

| Gate | Needs |
|---|---|
| 6 — mono sum | nothing new. Expect **exactly +6.02 dB, flat**, idle input **grounded** |
| 7 — polarity | nothing new. Expect 0.00 dB / 180.0° |
| 8 — noise floor | nothing new. Inputs shorted, want < 1 mV rms |
| 9 — headroom | nothing new. The AD3's ±5 V may not clip it at all |
| 10 — output chain | **the 10 kΩ pot, still not fitted** |
| 11 — in situ | the finished chain; reuse `tools/woofer_sweep.py` |

Also outstanding: **JP3's shunt is currently on JP1.** Put it back before the
board goes into service — without it the input and output grounds are joined
only through `R7`'s 10 Ω, which is the hum-lift configuration, not the default.
Fitting the rotary switch frees both `JP1` and `JP2` shunts and settles this
permanently.

---

## Decision 1 — the 3-position rotary switch

This is what the design wanted all along and could not source:

> *"No 3-position rotary switch in stock. The board brings the capacitor
> selection out to a 6-pin header … The same header accepts flying leads to a
> panel-mounted rotary switch if one is bought later — worth doing, since
> by-ear tuning wants fast A/B comparison and jumpers mean opening the box."*

**Sourced 2026-08-16.** A 2-pole 3-position wafer switch, commons `A0` and `B0`
on the inner ring, position lugs `A1`–`A3` and `B1`–`B3` on the outer ring.

### First, establish what the switch actually is

- **How many poles?** 1 or 2 changes everything below.
- **How many positions, and does it have an adjustable end-stop?** Many rotary
  switches are 12-position with a limiter ring set to 3.
- **Are the pole commons isolated from each other?** Meter `A0` → `B0` **in
  every detent**. Some cheap wafers bus the commons internally, which would tie
  `N1` to `VGND` and silence the filter. This is the check that matters — not
  `A1` → `B1`.
- **Break-before-make or shorting?** Either works here, and **shorting is
  actually preferable**: momentarily paralleling two C1s or two C2s is just
  another valid setting on this board.

> [!warning] Break-before-make does not mute the sub — it un-filters it
> An open on the C2 pole removes the low-pass entirely: modelled, the response
> is flat to within 0.01 dB out to 2 kHz, against −55 dB at 2 kHz normally. So
> the transient is a few ms of full-range signal into the woofer, not silence.
> Harmless — the module's own bandpass catches it — but switch with the level
> down rather than up.

### The wiring rule that governs everything below

Splitting one wire to two position lugs **ties those lugs together
permanently**. The rotary isolates common from lugs; it does not isolate lugs
from each other. So:

> **One wire per lug. A wire may serve two lugs only if both lugs want exactly
> the same capacitance.**

This kills the obvious-looking plan of feeding `JP1` pin 3 to lugs `A1` and
`A3` while `JP1` pin 5 feeds `A1` and `A2`, in order to get the `pos2+3`
parallel setting on one pole. `A1` then joins both wires, so `A2`—`A1`—`A3`
become one node and **all three positions collapse to 365 nF**. Three nearly
identical curves, and a long hunt for a fault in the switch.

Any setting needing `C1_2 ∥ C1_3` therefore cannot coexist on one pole with a
setting needing either cap alone. The parallel trick is retired.

### 2-pole 3-position — the wiring

Retire `pos2+3`. Instead put **one film capacitor on the switch itself**, from
lug `A1` to a wire running to **`J5` pin 1** — that is `OUT1`, the op-amp
output, which is the other end of C1 in the netlist. Every lug then gets one
distinct connection, and position 1's capacitance becomes a free choice rather
than the 364.9 nF the two board caps happen to make.

That is what finally reaches below 100 Hz, which the board has never done:

| Cap on the switch | Corner (with `JP2` pin 1) | Level at 63 Hz |
|---|---|---|
| 330 nF | 103.5 Hz | −4.06 dB |
| 390 nF | 98.9 Hz | −4.12 dB |
| **470 nF** | **94.0 Hz** | −4.29 dB |
| 560 nF | 89.8 Hz | −4.57 dB |
| 680 nF | 85.9 Hz | −5.07 dB |

Film (polyester/MKT), ≥50 V — not ceramic; class 2 ceramics are microphonic and
voltage-dependent. It is free-standing on the switch, so body size is
irrelevant.

**Recommended: 470 nF → 94.0 / 135.5 / 189.2 Hz**, steps 0.53 and 0.48 octave,
2.01× span. Wider *and* more even than anything the board can do on jumpers.

| Lug | Connect to | Gives |
|---|---|---|
| `A0` | `JP1` pin 2 (or 4 or 6) — **`N1`** | pole A common |
| `A1` | **470 nF cap** → wire → `J5` pin 1 (`OUT1`) | pos 1: C1 = 470n |
| `A2` | `JP1` pin **5** (`C1_3`, 143.2 nF) | pos 2 |
| `A3` | `JP1` pin **3** (`C1_2`, 221.7 nF) | pos 3 |
| `B0` | `JP2` pin 2 (or 4 or 6) — **`VGND`** | pole B common |
| `B1` | `JP2` pin **1** (`C2_1`, 150.7 nF) | pos 1 |
| `B2` | `JP2` pin **3** (`C2_2`, 121.2 nF) | pos 2 |
| `B3` | `JP2` pin **5** (`C2_3`, 63.8 nF) | pos 3 |

| Position | Corner | Level vs pos 1 |
|---|---|---|
| 1 | 94.0 Hz | 0 dB |
| 2 | 135.5 Hz | +1.11 dB |
| 3 | 189.2 Hz | +3.27 dB |

`JP1` pin 1 stays unwired — `C1_1` is not fitted on this board. Both `JP1` and
`JP2` shunts come off, so **`JP3` gets its shunt back permanently** and the
third-shunt problem disappears.

Watch the name collision: switch lug `A1` is not op-amp `A1`. In these docs
`A1` is the follower whose output is `OUT1` / `J5` pin 1.

**Zero-parts fallback**, if the capacitor is not available: `A1` and `A3` both
to `JP1` pin 3, `A2` to `JP1` pin 5, B side unchanged. Legal because positions
1 and 3 then want the *same* C1. Gives 113.8 / 135.5 / 189.2 Hz — 1.66× span,
but lopsided steps (0.25 / 0.48 octave) and no sub-100 Hz. Worse on both
counts.

### If it is 1-pole 3-position

Put it on **JP2**, not JP1, and keep JP1 on a jumper. Two reasons: the common
is then `VGND`, which A3 buffers to a low impedance and is far safer on a loom
than `N1`; and the span is wider. With JP1 shunted at pin 3 you get
113.8 / 125.4 / 189.2 Hz, a 1.66× span. Putting the switch on JP1 instead gives
evener steps but only 1.21–1.37× — too narrow to be worth a knob.

### Level tracks the corner, and that confounds A/B

The passband level at 63 Hz is set almost entirely by which C2 is selected, so
any wide spread of corners also spreads level by ~3 dB. That matters because
the switch exists for fast A/B and the louder setting reliably wins a blind
comparison. The offsets are in the table above — nudge the pot when switching,
or mentally discount position 3.

### Three cautions

> [!warning] `N1` is a high-impedance node on long wires
> `N1` sits at about 3 kΩ to AC ground at 50 Hz — the highest-impedance thing
> on the loom, and the DC-path figure of 8.25 kΩ understates how exposed it is.
> Flying leads to a panel switch are an antenna. Keep them short, and **re-run
> Gate 8 after fitting** — the noise floor measured with jumpers is not the
> noise floor with a metre of loom. This is the single most likely way the
> switch makes the board worse.

> [!warning] Twist `A0` with the `J5.1` wire
> Those two are the C1 feedback loop, and now it leaves the board. Keeping the
> loop area small is what stops it picking up hum magnetically. Twist the
> B-side position wires with `B0` for the same reason. Better still, use short
> 2-core shielded audio cable with the shield to board `GND` (`J4` pin 2, not
> `VGND`), and bond the switch body to `GND` if it is metal.

> [!note] No DC sits across any switch contact
> Every node in the loom is at 6 V once settled, so there is no charge step and
> no click when turning the knob. Wire resistance and inductance are in series
> with C1/C2 but are nothing against tens of kΩ of reactance.

> [!note] The capacitors do not have to stay on the board
> If the selection moves to a panel switch, capacitors can live *on the switch*
> instead. That sidesteps the board's footprint limits entirely and is the
> cheapest route to corners below 100 Hz — which is exactly what the 470 nF on
> lug `A1` does. Note the asymmetry: extra **C1** is fully reachable from
> existing connectors (`JP1` even pin = `N1`, `J5` pin 1 = `OUT1`), but extra
> **C2** is not, because `N2` comes out nowhere except the leg of `R2`.

---

## Decision 2 — does the board need a respin?

**Default answer: no.** The board works, measures to 0.8 % of model, and is
fully single-sided with zero links. Do not respin before Gate 11 and a
listening session. The design doc's own position stands: *"Crossover point is a
guess until listened to."*

The two real limitations, and the cheap fixes:

| Limitation | Cost | Fix without a respin |
|---|---|---|
| `C_in` 220 nF costs 1.3–3.1 dB passband level | Level only, absorbed by the pot | Tack ~2 µF electrolytic across `C_in1`/`C_in2` on the copper side. Node sits at a steady 6 V DC with defined polarity, so a polarised part is fine, **+ toward the board's inside** |
| Lowest corner is 100.7 Hz; the design wanted to reach ~87 Hz | Unknown until listened to | **Solved by the switch, no board work.** A single cap from switch lug `A1` to `J5` pin 1 puts extra C1 in the feedback path: 470 nF → 94.0 Hz, 560 nF → 89.8 Hz, 680 nF → 85.9 Hz. Both ends are already on connectors |

**A respin is only worth it if** the listening test says the panel switch wants
board-side support — a proper loom connector instead of flying leads to pin
headers, a `C1_1` footprint that clears `C1_3` so the low-corner cap can live
on the board, and a `C_in` footprint that takes a real 2.2 µF film part.

Note that neither of the two limitations above now *requires* one. The sub-100
Hz corner is reachable from existing connectors, and the `C_in` droop is a
tacked-on electrolytic. What a respin buys is tidiness and noise margin, not
capability.

The `kicad-laser-pcb` skill covers the whole mill/laser pipeline if it comes to
that.

---

## What to measure at school

1. ~~**The switch**~~ — **done**, 2-pole 3-position, see Decision 1. Still
   outstanding: `A0`→`B0` isolation in every detent, and whether fully-CCW
   selects position 1.
2. **A 470 nF film cap** — the low-corner part for switch lug `A1`. This is the
   one item that changes what the board can do.
3. **A 2.2 µF non-polarised electrolytic**, if the shop has one — for the
   `C_in` droop fix, tacked on the copper side. Small, and the polarity across
   `C_in` is defined anyway.
4. **A couple of jumper shunts** — cheap insurance if the switch does not work
   out.

Only if a respin is going ahead, additionally:

5. **A 2.2 µF film cap** — body L×W and lead pitch. The current `C_in`
   footprint is `C_Rect_L18.0mm_W9.0mm_P15.00mm_FKS3_FKP3`, and the part that
   would not fit was blocked by `J2` at 0.71 mm and `R5` at 1.01 mm.
6. **A 470–680 nF film cap** — body size and pitch, if the low-corner cap is to
   move onto the board as a fitted `C1_1`. The current C1 footprint is
   `C_Rect_L10.3mm_W5.7mm_P7.50mm_MKS4`.
7. **The switch's mechanicals** — terminal spacing, shaft diameter, bushing
   thread, panel depth.
4. **A 270 nF or 330 nF film cap** — body size and pitch, for the low-corner
   option. The current C1 footprint is
   `C_Rect_L10.3mm_W5.7mm_P7.50mm_MKS4`.
5. **A third jumper shunt** — trivial, and it frees JP3.

---

## Repos, tooling, gotchas

**Repo:** `C:\Users\Mads2\personal-projects` → `MadsRudolph/personal-projects`,
branch `main`. Two submodules (`Pi Zero Room Sensor`, `esp32-reflow-hotplate`)
carry unrelated pointer drift — leave them alone.

**Tools** in `Projects/Bose Sub Integration/tools/`:

- `subxo_model.py` — generates every predicted figure. `--designed` models the
  2.2 µF variant. Import `response()` to overlay on measurements.
- `subxo_compare.py` — scores a WaveForms CSV export against the model and
  prints a Gate 5 verdict.
- `woofer_sweep.py`, `plot_acoustic.py`, `rig_check.py`, `aux_impedance.py` —
  the Phase 0 acoustic rig, reused for Gate 11.

Measurement uses `pydwf` with coherent DFT. KiCad 10 CLI at
`C:\Program Files\KiCad\10.0\bin\`.

**Gotchas that cost time:**

- The AD3 **cannot power this board** — ±5 V supplies, and the LM7812 needs
  ≥14 V. Use the Korad at 15.0 V.
- **J4 has no reverse-polarity protection.** `VIN` goes straight to `C10` and
  the regulator. Meter the leads.
- **JP1 even pins are `N1`, JP2 even pins are `VGND`.** Clipping a scope ground
  to JP1 shorts the filter.
- Channel 2 must reference **`VGND`**, not ground — `OUT1` sits at 6 V and the
  AD3 has no AC coupling.
- **The idle input must be grounded, not floating**, for the mono-sum test.
  Floating gives +2.5 to +5.4 dB and reads like a fault.
- With J6 empty, `POT_TOP` floats to **~6 V**. That is an unloaded coupling
  cap, not a leaky one.
- The AD3 in [[AD3 Repair]] is **not** the working unit.

**Rules:** no AI attribution in commits or PRs — the user is the sole author.
Commit style is a short `Sub crossover: …` subject plus explanatory prose.

---

## Related

- [[Results - Sub Crossover Bring-up]]
- [[Test Guide - Sub Crossover Board]]
- [[Design - Sub Crossover Board]]
- [[Test Guide - Companion 5 Characterisation]]
