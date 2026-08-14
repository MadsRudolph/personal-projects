---
title: Plan - Sub Crossover Board
type: implementation-plan
tags:
  - electronics
  - audio
  - crossover
  - active-project
status: Not started
started: 2026-08-13
updated: 2026-08-13
---

# Sub Crossover Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development`
> or `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a line-level mono-summing low-pass filter that lets the Bose
Companion 5 bass module join the Saga → Fosi → JBL 4412 chain as midbass
reinforcement, with switched crossover corner, polarity invert and level trim.

**Architecture:** Passive Y-split off the Saga's buffered output. Two of the
20 kΩ-class summing resistors double as the Sallen-Key R1, so a single TL074
provides filter, inverter and virtual-ground buffer. Verified on the Analog
Discovery 3 at every stage before committing to copper, then etched
single-sided on the xTool fiber laser.

**Tech Stack:** TL074 / LM7812 analog board · Analog Discovery 3 + pydwf +
WaveForms · KiCad 9 · Freerouting · xTool fiber laser (DTU 62768 process)

## Global Constraints

- **Filter R = 8.25 kΩ** (R1a ∥ R1b = 16.5 kΩ ∥ 16.5 kΩ; R2 = 8.25 kΩ)
- **Corner positions:** 330n/150n → 86.7 Hz · 220n/100n → 130.1 Hz · 150n/68n → 191.0 Hz
- **Q = 0.742 in all three positions** (C1/C2 ratio held at 2.2)
- **Single supply 12 V** from LM7812; virtual ground 6.0 V buffered by A3
- **Supply must be a Class II (double-insulated, no earth pin) wall wart** — this
  is the primary defence against a mains loop between Saga, Fosi and Bose
- **The main signal path is never modified.** Everything hangs off a passive
  Y-split and must remain removable by pulling one adapter
- **Board is single-sided**, through-hole, sized to the 104 × 104 mm laser jig
- Python is `py -3.13` on this machine. WaveForms GUI must be closed before any
  script run — the AD3 is claimed exclusively
- Reference documents: [[Design - Sub Crossover Board]] and
  [[Test Guide - Companion 5 Characterisation]]

---

## File Structure

| File | Responsibility |
|------|----------------|
| `tools/woofer_sweep.py` | *Modified.* Generic transfer-function sweep; gains a `--passband` option so it can analyse any filter, not just the 25–70 Hz woofer case |
| `tools/board_results/` | *Created.* CSV sweeps from each verification stage |
| `hardware/kicad/subxo.kicad_sch` | *Created.* Schematic |
| `hardware/kicad/subxo.kicad_pcb` | *Created.* Single-sided layout |
| `hardware/kicad/production/` | *Created.* DXF + Gerbers for the laser |
| `HANDOFF - KiCad Schematic.md` | *Created.* Self-contained brief for the KiCad session |
| `Plan - Sub Crossover Board.md` | This file. Check boxes as you go |

---

## Task 1: Generalise the sweep tool

The measurement harness comes first, and gets validated against a network whose
answer is known analytically. Everything downstream trusts it.

**Files:**
- Modify: `tools/woofer_sweep.py`
- Create: `tools/board_results/` (directory)

**Interfaces:**
- Produces: `woofer_sweep.py --passband LO HI` — analyses magnitude/phase between
  arbitrary band edges, reporting passband gain, −3 dB corner, and slope in
  dB/octave. Every later task calls this.

- [ ] **Step 1: Add the option**

In `main()`, alongside the existing arguments:

```python
    ap.add_argument("--passband", nargs=2, type=float, default=(25.0, 70.0),
                    metavar=("LO", "HI"),
                    help="band over which the reference gain is taken")
```

- [ ] **Step 2: Use it instead of the hardcoded band**

Replace the line `band = (hz >= 25) & (hz <= 70)` with:

```python
    band = (hz >= a.passband[0]) & (hz <= a.passband[1])
```

and replace the print that says `passband gain (25-70 Hz)` with:

```python
    print(f"passband gain ({a.passband[0]:.0f}-{a.passband[1]:.0f} Hz) : "
          f"{passband:+.2f} dB ({10 ** (passband / 20):.2f}x)")
```

Also change the corner search so it starts above the passband rather than above
a fixed 70 Hz — replace `above = hz > 70` with:

```python
    above = hz > a.passband[1]
```

- [ ] **Step 3: Build the known-answer test network**

On the breadboard, a first-order RC low-pass using stocked parts:

```
  W1 ──┬── 8k25 ──┬── ch2+
       │          │
      ch1+       220n
       │          │
      GND ───────┴── ch1- , ch2-
```

Analytically: `f₋₃dB = 1/(2π · 8250 · 220n) = 87.7 Hz`, slope −6 dB/octave,
phase −45° at the corner.

- [ ] **Step 4: Run it**

```bash
py -3.13 tools/woofer_sweep.py --passband 10 30 --amp 0.5 --start 10 --stop 2000 --out tools/board_results/rc_check.csv
```

Expected: `low-pass corner (-3 dB)` between **83 and 93 Hz**, and
`slope above the corner` between **−5.5 and −6.5 dB/octave**. If the corner is
right but the slope reads −12, you have built a second-order network by
accident; if both are wrong, check the scope negatives are on the ground rail.

- [ ] **Step 5: Commit**

```bash
git add "Projects/Bose Sub Integration/tools/woofer_sweep.py" "Projects/Bose Sub Integration/tools/board_results/rc_check.csv"
git commit -m "Generalise AD3 sweep tool to arbitrary passband, validate against RC network"
```

---

## Task 2: Power supply and virtual ground

Nothing else can be trusted until the rails are right. Build and verify this
alone, with no signal circuitry attached.

**Files:**
- Create: `tools/board_results/rails.md`

**Interfaces:**
- Produces: a 12.0 V rail and a 6.0 V virtual ground node used by every
  subsequent task.

- [ ] **Step 1: Build the supply section**

```
 15 V wall wart ──┬── LM7812 IN   OUT ──┬── +12 V rail
                  │           GND       │
                 100µF         │      100µF ∥ 100n
                  │            │        │
                 GND ──────────┴────────┴── GND

 +12V ──10k──┬──10k── GND        A3 (+) ← divider node
             │                   A3 (−) ← A3 out
            100µF                A3 out = VIRTUAL GROUND (6.0 V)
             │
            GND
```

Fit the TL074 in its DIP14 socket. Wire **A4 as a follower with its (+) tied to
virtual ground** — an unterminated spare section can oscillate and couple into
its neighbours through the shared supply.

- [ ] **Step 2: Power up and measure with the multimeter**

| Node | Expected |
|------|----------|
| LM7812 output | 11.7 – 12.3 V |
| Divider node (unbuffered) | 5.9 – 6.1 V |
| A3 output (virtual ground) | within 50 mV of the divider node |
| Current draw | 10 – 25 mA |

If the LM7812 is hot to the touch, power down immediately — that is a short.

- [ ] **Step 3: Check the virtual ground can actually drive**

Hang a 1 kΩ resistor from the virtual ground to the +12 V rail and re-measure.
A **buffered** virtual ground shifts by less than 50 mV; a bare divider would
sag by hundreds. This is the check that proves A3 is doing its job.

- [ ] **Step 4: Record and commit**

Write the four measured values into `tools/board_results/rails.md`.

```bash
git add "Projects/Bose Sub Integration/tools/board_results/rails.md"
git commit -m "Verify crossover board supply rails and buffered virtual ground"
```

---

## Task 3: Sallen-Key filter, centre position

Build one position only. Get it right before adding switching.

**Files:**
- Create: `tools/board_results/filter_pos2.csv`

**Interfaces:**
- Consumes: +12 V and virtual ground from Task 2.
- Produces: node `OUT1` — the filter output, used by Tasks 4–7.

- [ ] **Step 1: Build the filter**

Position 2 values, single channel for now — drive `IN_L` only, leave `IN_R`
open:

| Part | Value | From | To |
|------|-------|------|-----|
| C_in1 | 2.2 µF film | IN_L | R1a |
| R1a | 16.5 kΩ | C_in1 | N1 |
| R2 | 8.25 kΩ | N1 | N2 |
| C2 | 100 nF film | N2 | virtual ground |
| C1 | 220 nF film | A1 out | N1 |
| — | — | N2 | A1 (+) |
| — | — | A1 out | A1 (−) |

With `IN_R` open, R1b is out of circuit and R1 = 16.5 kΩ, not 8.25 kΩ — so this
first sweep should land at **65 Hz**, not 130 Hz. That is expected and is itself
a useful check that the summing network is doing what we think.

- [ ] **Step 2: Sweep it**

```bash
py -3.13 tools/woofer_sweep.py --passband 15 35 --amp 0.5 --start 10 --stop 2000 --out tools/board_results/filter_pos2_single.csv
```

Expected: corner **62 – 69 Hz**, slope **−11 to −13 dB/octave**.

- [ ] **Step 3: Add the second input leg**

Fit C_in2 (2.2 µF) and R1b (16.5 kΩ) from `IN_R` to N1. Tie `IN_R` to `IN_L` so
both are driven together.

- [ ] **Step 4: Re-sweep and confirm the corner moved**

```bash
py -3.13 tools/woofer_sweep.py --passband 20 60 --amp 0.5 --start 10 --stop 2000 --out tools/board_results/filter_pos2.csv
```

| Quantity | Expected |
|----------|----------|
| −3 dB corner | **130 – 143 Hz** (design 136 Hz; the −3 dB point sits at 1.047 × f₀ because Q = 0.742) |
| Gain at 130 Hz | **−2.6 dB ± 0.5** — a 2nd-order section is down by exactly Q at f₀ |
| Gain at 260 Hz (2 × f₀) | **−12.1 dB ± 1** |
| Slope above corner | **−11 to −13 dB/octave** |
| Passband gain | **0 dB ± 0.3** |

If the corner is roughly right but the passband gain is −6 dB, `IN_R` is
grounded rather than driven — the summing network is averaging your signal with
silence.

- [ ] **Step 5: Commit**

```bash
git add "Projects/Bose Sub Integration/tools/board_results/filter_pos2*.csv"
git commit -m "Breadboard Sallen-Key section, verify 130 Hz corner and Q on AD3"
```

---

## Task 4: All three switched positions

**Files:**
- Create: `tools/board_results/filter_pos1.csv`, `filter_pos3.csv`
- Create: `tools/board_results/corners.md`

**Interfaces:**
- Consumes: the filter from Task 3.
- Produces: a verified 6-pin header selecting three C1/C2 pairs.

- [ ] **Step 1: Wire the select header**

Six pins: three C1 candidates to one row, three C2 candidates to the other, with
their common ends going to A1-out/N1 and N2/virtual-ground respectively. Two
jumper shunts select a pair.

| Pos | C1 | C2 |
|-----|-----|-----|
| 1 | 330 nF | 150 nF |
| 2 | 220 nF | 100 nF |
| 3 | 150 nF | 68 nF |

- [ ] **Step 2: Sweep position 1**

```bash
py -3.13 tools/woofer_sweep.py --passband 20 50 --amp 0.5 --start 10 --stop 2000 --out tools/board_results/filter_pos1.csv
```

Expected −3 dB corner **86 – 95 Hz** (design 90.8 Hz), slope −11 to −13 dB/oct.

- [ ] **Step 3: Sweep position 3**

```bash
py -3.13 tools/woofer_sweep.py --passband 30 90 --amp 0.5 --start 10 --stop 2000 --out tools/board_results/filter_pos3.csv
```

Expected −3 dB corner **190 – 210 Hz** (design 200 Hz), slope −11 to −13 dB/oct.

- [ ] **Step 4: Record all three and check Q consistency**

Write the three corners into `tools/board_results/corners.md`. The gain **at f₀**
(86.7 / 130.1 / 191.0 Hz) should be −2.6 dB ± 0.5 in every position. If one
position reads noticeably different, its C1/C2 *ratio* is wrong — a swapped or
mis-marked capacitor — even though its corner may look plausible.

- [ ] **Step 5: Commit**

```bash
git add "Projects/Bose Sub Integration/tools/board_results/"
git commit -m "Verify all three crossover corner positions, 87/130/191 Hz at Q 0.74"
```

---

## Task 5: Inverter and polarity switch

**Files:**
- Create: `tools/board_results/polarity.csv`

**Interfaces:**
- Consumes: `OUT1` from Task 3.
- Produces: node `SW2_COMMON`, either OUT1 or its inverse.

- [ ] **Step 1: Build the inverter**

R3 (10 kΩ) from `OUT1` to A2 (−). R4 (10 kΩ) from A2 (−) to A2 out. A2 (+) to
virtual ground. Wire the 2-pole changeover switch so its common selects `OUT1`
or `A2 out`.

- [ ] **Step 2: Sweep in the NORMAL position**

```bash
py -3.13 tools/woofer_sweep.py --passband 20 60 --amp 0.5 --start 10 --stop 2000 --out tools/board_results/polarity_normal.csv
```

Note the **phase at 50 Hz** from the printed table.

- [ ] **Step 3: Flip to INVERTED and sweep again**

```bash
py -3.13 tools/woofer_sweep.py --passband 20 60 --amp 0.5 --start 10 --stop 2000 --out tools/board_results/polarity_inverted.csv
```

Expected: phase at 50 Hz differs from Step 2 by **180° ± 5°**, and the magnitude
response is unchanged within **0.3 dB** at every frequency. A magnitude
difference means the inverter's two resistors are not equal.

- [ ] **Step 4: Commit**

```bash
git add "Projects/Bose Sub Integration/tools/board_results/polarity_*.csv"
git commit -m "Add polarity inverter stage, verify 180 degrees with flat magnitude"
```

---

## Task 6: Output stage and mono summing

**Files:**
- Create: `tools/board_results/summing.md`, `tools/board_results/noise.md`

- [ ] **Step 1: Build the output stage**

`SW2_COMMON` → C_out (10 µF electrolytic, **+ toward the op-amp side** — that node
sits at 6 V, the pot side at 0 V) → VR1 (10 kΩ) top. VR1 bottom to virtual
ground. Wiper → R5 (100 Ω) → tip, and → R6 (100 Ω) → ring.

Load the output with **8.2 kΩ** to ground to emulate the Bose input.

- [ ] **Step 2: Verify the mono sum**

Drive `IN_L` only, with `IN_R` tied to ground (not floating), and note the output
level at 50 Hz. Then drive both together and note it again.

```bash
py -3.13 tools/woofer_sweep.py --passband 40 60 --amp 0.5 --start 40 --stop 60 --steps 5
```

Expected: both-driven is **+6.0 dB ± 0.5** above L-only. Record in `summing.md`.

- [ ] **Step 3: Measure the noise floor**

Short both inputs to ground, VR1 at maximum, and capture with the wavegen off:

```bash
py -3.13 tools/rig_check.py --amp 0 --ref 8200
```

Read the `total` rms figure on ch2. Expected: **under 1 mV rms**. If you see
tens of millivolts at 50 Hz, that is mains hum — try the 10 Ω ground lift before
going further.

- [ ] **Step 4: Confirm the level range**

With VR1 at minimum the output should be below 1 mV; at maximum, roughly 0.75 ×
the filter output (the 10 kΩ pot against the 8.2 kΩ load). Record both.

- [ ] **Step 5: Commit**

```bash
git add "Projects/Bose Sub Integration/tools/board_results/summing.md" "Projects/Bose Sub Integration/tools/board_results/noise.md"
git commit -m "Complete output stage, verify +6 dB mono summing and noise floor"
```

---

## Task 7: In-system listening test on the breadboard

The last chance to abandon this before spending copper. Do not skip it.

**Files:**
- Create: `Listening Notes.md`

- [ ] **Step 1: Wire into the real chain**

RCA Y-splitters at the Saga output. One leg to the Fosi as now; the other to the
breadboard inputs. Breadboard output to the pod aux via the 3.5 mm cable.
Satellites unplugged. Pod knob and Bass Compensation on their tape marks.

- [ ] **Step 2: Set the level with the sub disconnected first**

Play familiar material at your normal volume with VR1 at **minimum**. Then bring
VR1 up until you can just hear the sub join. Back off slightly. The usual error
is setting it far too high because "more bass" is initially flattering.

- [ ] **Step 3: Work through the matrix**

For each of the three corner positions, try both polarity settings — six
combinations. Play the same 30 seconds of bass-heavy material each time.

Record in `Listening Notes.md` for each: corner, polarity, and whether the
midbass sounds fuller or hollow. **Polarity should produce an obvious
difference** in at least one position. If flipping polarity changes nothing
audible, the sub is either not connected or set so low it contributes nothing.

- [ ] **Step 4: Decide**

If no combination sounds better than the 4412s alone, stop here and record why.
That is a legitimate outcome given the measured 63–203 Hz band, and it is far
cheaper to discover now than after etching a board.

- [ ] **Step 5: Commit**

```bash
git add "Projects/Bose Sub Integration/Listening Notes.md"
git commit -m "Record in-system listening trial across corner and polarity settings"
```

---

## Task 8: KiCad schematic

**Files:**
- Create: `hardware/kicad/subxo.kicad_sch`
- Create: `HANDOFF - KiCad Schematic.md`

- [ ] **Step 1: Read the handoff**

The schematic work is specified in `HANDOFF - KiCad Schematic.md`, written to be
self-contained for a fresh session. It carries the full netlist, values,
footprint requirements and board constraints.

- [ ] **Step 2: Invoke the skill**

In a new Claude Code session, in this repository:

```
Read "Projects/Bose Sub Integration/HANDOFF - KiCad Schematic.md" and build the schematic using the kicad-laser-pcb skill.
```

- [ ] **Step 3: Check the schematic against the netlist**

Compare every row of the netlist table in the design spec against the drawn
schematic. Confirm specifically: C1 returns to **N1**, not to N2; A1 is wired as
a follower; A4 is terminated; VR1's bottom goes to **virtual ground**, not to
the 0 V of the supply.

- [ ] **Step 4: Run ERC and commit**

```bash
git add "Projects/Bose Sub Integration/hardware/kicad/subxo.kicad_sch"
git commit -m "Add sub crossover schematic"
```

---

## Task 9: PCB layout and production files

**Files:**
- Create: `hardware/kicad/subxo.kicad_pcb`
- Create: `hardware/kicad/production/`

- [ ] **Step 1: Assign footprints**

All through-hole. Film capacitors need generous pad pitch — the 330 nF and
2.2 µF parts are physically large. Use the skill's bundled footprint library.

- [ ] **Step 2: Place to the jig**

104 × 104 mm laser jig format, single-sided, tracks on the bottom copper.
Keep the two input legs symmetric and short; put the supply section away from
the filter section.

- [ ] **Step 3: Two-stage Freerouting**

Per the `kicad-laser-pcb` skill's routing procedure.

- [ ] **Step 4: Export DXF and Gerbers**

- [ ] **Step 5: Commit**

```bash
git add "Projects/Bose Sub Integration/hardware/kicad/"
git commit -m "Add single-sided crossover PCB layout and laser production files"
```

---

## Task 10: Etch, assemble, bring up

- [ ] **Step 1: Etch and drill per the laser process**

- [ ] **Step 2: Fit the supply section only, and repeat Task 2's rail checks**

Same expected values: 11.7–12.3 V rail, virtual ground within 50 mV of the
divider, under 50 mV sag with a 1 kΩ load.

- [ ] **Step 3: Fit everything else, socket the TL074 last**

- [ ] **Step 4: Repeat the full sweep set**

Run Tasks 3–6's sweeps again on the finished board and compare against the
breadboard CSVs. Corners should agree within **5 %**. A shifted corner on the
built board usually means a capacitor in the wrong position.

- [ ] **Step 5: Commit the as-built results**

```bash
git add "Projects/Bose Sub Integration/tools/board_results/"
git commit -m "Record as-built board verification against breadboard reference"
```

---

## Task 11: Final integration and documentation

- [ ] **Step 1: Install in the chain**

- [ ] **Step 2: Set corner, polarity and level by ear**

Start from whichever combination won in Task 7.

- [ ] **Step 3: Try three sub positions**

Placement matters more than any filter value. Try at least three locations and
keep the best. Note that moving the sub may change the best polarity setting.

- [ ] **Step 4: Measure the Bass Compensation range**

This is the open item from the design spec. With the mic at a fixed nearfield
position, sweep with the rear knob fully − and fully +. Record the dB range and
whether it changes level only or level and shape.

- [ ] **Step 5: Update the docs and commit**

Fill in the outstanding tables in [[Test Guide - Companion 5 Characterisation]]
and the Open Items in [[Design - Sub Crossover Board]].

```bash
git add "Projects/Bose Sub Integration/"
git commit -m "Complete sub crossover integration, record final settings and Bass Compensation range"
```

---

## Self-review notes

- **Spec coverage:** every section of [[Design - Sub Crossover Board]] maps to a
  task — supply and virtual ground → Task 2; filter → Tasks 3–4; polarity →
  Task 5; output, summing, hum → Task 6; schematic → Task 8; layout → Task 9;
  the Bass Compensation open item → Task 11 Step 4.
- **Known gap, deliberate:** the design spec's suggestion that a panel rotary
  switch may replace the jumper header is not planned. It is a later
  convenience, and the header supports it without a board change.
- **Expected values** are stated as ranges with the design figure named, so a
  reviewer can tell a tolerance stack from a wiring error.
