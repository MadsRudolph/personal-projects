---
title: HANDOFF - Sub Crossover Bring-up
type: handoff
tags:
  - electronics
  - audio
  - subwoofer
  - crossover
  - handoff
status: Gates 0-5 pass; Gates 6-11 outstanding
started: 2026-08-15
updated: 2026-08-15
---

# HANDOFF - Sub Crossover Bring-up

## Paste this into the new session

> The `subxo` sub-crossover board is built and electrically verified. Read
> `Projects/Bose Sub Integration/HANDOFF - Sub Crossover Bring-up.md` in full,
> then `Results - Sub Crossover Bring-up.md` and
> `Test Guide - Sub Crossover Board.md`. Run `git pull` in
> `C:\Users\Mads2\Documents\Projects` first — the last session pushed commit
> `207f69d`.
>
> I am at school with access to the component shop. I have found a 3-position
> rotary switch and I can measure exact part footprints if we decide the board
> needs a respin. Start with the switch — tell me what to check on it and how
> to wire it. Do not start a PCB respin without talking it through first.

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

---

## Decision 1 — the 3-position rotary switch

This is what the design wanted all along and could not source:

> *"No 3-position rotary switch in stock. The board brings the capacitor
> selection out to a 6-pin header … The same header accepts flying leads to a
> panel-mounted rotary switch if one is bought later — worth doing, since
> by-ear tuning wants fast A/B comparison and jumpers mean opening the box."*

### First, establish what the switch actually is

- **How many poles?** 1 or 2 changes everything below.
- **How many positions, and does it have an adjustable end-stop?** Many rotary
  switches are 12-position with a limiter ring set to 3.
- **Break-before-make?** Almost certainly, and that is fine here — a momentary
  open just mutes the sub for a few ms.

### If it is 2-pole 3-position — the good case

One pole selects C1, the other selects C2, one knob picks a ganged pair. Wiring:

```
  pole A common  -> JP1 even pin (2, 4 or 6)   = N1
  pole B common  -> JP2 even pin (2, 4 or 6)   = VGND

  JP1 pin 3 = C1_2 220n      JP2 pin 1 = C2_1 150n
  JP1 pin 5 = C1_3 150n      JP2 pin 3 = C2_2 120n
  JP1 pin 1 = C1_1 NOT FITTED - never use     JP2 pin 5 = C2_3 68n
```

**Recommended three settings** — closest to the design's intent of even log
spacing across the module's usable band:

| Position | Corner | Pole A → JP1 | Pole B → JP2 |
|---|---|---|---|
| 1 | **100.7 Hz** | pins 3 **and** 5 | pin 1 |
| 2 | **135.5 Hz** | pin 5 | pin 3 |
| 3 | **189.2 Hz** | pin 3 | pin 5 |

Steps of 1.345× and 1.396× — 0.43 and 0.48 octave, near enough even.

A pin feeding two switch positions is fine: run one wire from the header pin
and split it at the switch. The rotary only ever connects the common to one
position, so there is no conflict.

*Alternative if perfectly even steps matter more than reaching 100 Hz:*
113.8 / 155.4 / 212.3 Hz gives **exactly 1.366× twice** (0.45 octave each).
Position 1 = JP1 pin 3, JP2 pin 1. Position 2 = JP1 pins 3+5, JP2 pin 5.
Position 3 = JP1 pin 5, JP2 pin 5.

### If it is 1-pole 3-position

Put it on **JP1** and keep JP2 on a jumper. Wire position 1 → pins 3+5,
position 2 → pin 3, position 3 → pin 5. That gives 370n / 220n / 150n, and the
JP2 jumper then picks which family of three you get.

### Two cautions

> [!warning] `N1` is a high-impedance node on long wires
> `N1` sits at 8.25 kΩ. Flying leads to a panel switch are an antenna. Keep
> them short, twist each signal wire with a ground return, and **re-run Gate 8
> after fitting** — the noise floor measured with jumpers is not the noise
> floor with a metre of loom. This is the single most likely way the switch
> makes the board worse.

> [!note] The capacitors do not have to stay on the board
> If the selection moves to a panel switch, capacitors can live *on the switch*
> instead. That sidesteps the board's footprint limits entirely and is the
> cheapest route to corners below 100 Hz — see Decision 2.

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
| Lowest corner is 100.7 Hz; the design wanted to reach ~87 Hz | Unknown until listened to | Add C1 in parallel. **87 Hz needs 640 nF** (+275 nF on the 364.9 nF pair); **95 Hz needs 451 nF** (+86 nF). Easiest if C1 lives on the switch |

**A respin is only worth it if** the listening test says the sub-100 Hz range
is genuinely needed *and* the panel switch wants board-side support. In that
case the things to fix are: a `C_in` footprint that takes a real 2.2 µF film
part, a `C1_1` footprint that clears `C1_3`, and possibly a connector for the
switch loom instead of flying leads to headers.

The `kicad-laser-pcb` skill covers the whole mill/laser pipeline if it comes to
that.

---

## What to measure at school

Only useful if a respin is on the table, so gather it but do not act on it yet:

1. **The switch** — poles, positions, terminal spacing, shaft diameter, and
   whether the position count is set by a limiter ring.
2. **A 2.2 µF film cap** — body L×W and lead pitch. The current `C_in`
   footprint is `C_Rect_L18.0mm_W9.0mm_P15.00mm_FKS3_FKP3`, and the part that
   would not fit was blocked by `J2` at 0.71 mm and `R5` at 1.01 mm.
3. **A 2.2 µF non-polarised electrolytic**, if the shop has one — likely much
   smaller and good enough here.
4. **A 270 nF or 330 nF film cap** — body size and pitch, for the low-corner
   option. The current C1 footprint is
   `C_Rect_L10.3mm_W5.7mm_P7.50mm_MKS4`.
5. **A third jumper shunt** — trivial, and it frees JP3.

---

## Repos, tooling, gotchas

**Repo:** `C:\Users\Mads2\Documents\Projects` → `MadsRudolph/personal-projects`,
branch `main`, at `207f69d`. Two submodules (`Pi Zero Room Sensor`,
`esp32-reflow-hotplate`) carry unrelated pointer drift — leave them alone.

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
