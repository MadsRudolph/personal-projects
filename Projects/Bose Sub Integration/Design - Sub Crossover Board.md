---
title: Design - Sub Crossover Board
type: design-spec
tags:
  - electronics
  - audio
  - subwoofer
  - crossover
  - active-project
status: Design approved, not yet built
started: 2026-08-13
updated: 2026-08-13
---

# Design - Sub Crossover Board

> [!summary] **What this is**
> A line-level mono-summing low-pass filter that lets the **Bose Companion 5
> bass module** join the main stereo chain (Schiit Saga → Fosi → JBL 4412) as a
> midbass reinforcement source, fed from the Saga's output and driven into the
> control pod's aux input.
> - Measured constraints come from [[Test Guide - Companion 5 Characterisation]]
> - **The main signal path is never modified** — the whole thing hangs off a
>   passive Y-split and can be removed by pulling one adapter

---

## Goal, stated honestly

Add midbass output and headroom in the **63–200 Hz** region, and give the system
a second bass source in a different room position so room modes average out.

**Not** low-end extension. The bass module was measured as a 63–203 Hz bandpass
and produces nothing below 63 Hz from any radiator; the JBL 4412 is specified to
45 Hz. This design cannot and does not extend the system's bottom end. It was
approved on the basis of listening experience with the module in the room, with
that limitation understood.

---

## Measured facts this design is built on

All from Phase 0. Each one changed the design.

| Measurement | Result | Design consequence |
|---|---|---|
| Aux input impedance | **8.9 kΩ**, flat 10 Hz–500 Hz, ∥ 2.4 nF | Easy to drive. The 2.4 nF is a capacitive load → series resistor on the output |
| Aux input high-pass | ~0.4 Hz (≈47 µF coupling cap) | Nothing lost at the bottom; no compensation needed |
| Aux → speaker latency | **0 ms** (< 0.5 µs, two methods) | Path is analog. A polarity switch is meaningful; no delay compensation possible or needed |
| Aux path polarity | non-inverting | Polarity switch default position = normal |
| Channel summing to woofer | **+5.4 dB** with both driven | Drive tip **and** ring. No make-up gain needed |
| Left vs right symmetry | within 0.1 dB | Either channel alone behaves identically; simple mono sum is valid |
| Module acoustic band | **63–203 Hz** (−3 dB) | Crossover must sit in 85–195 Hz, not the 50–60 Hz originally planned |
| Slope above 203 Hz | **−39 dB/oct** (~6th order) | **Our filter cannot improve this.** 2nd order is sufficient, not 4th |
| Slope below 63 Hz | +25 dB/oct (4th order, electronic) | A subsonic filter would be redundant — dropped from the design |

---

## Architecture

```
Sources → Schiit Saga (tube buffer, master volume)
              │
        RCA out ──┬───────────────────────────► Fosi → JBL 4412  (full range, untouched)
                  │
                  └──► CROSSOVER BOARD ──► 3.5 mm ──► Bose control pod AUX IN
                                                          │
                                              pod knob = sub level
                                              pod mute = off for vinyl
                                              rear Bass Compensation = coarse trim
                                                          │
                                                   Companion 5 bass module
                                                   (satellites unplugged)
```

Three properties worth preserving:

1. **The main path is never touched.** No high-pass on the 4412s, nothing
   inserted between Saga and Fosi. Pull one Y-adapter and the system is exactly
   as it was.
2. **Sub level tracks main volume automatically**, because both feeds come off
   the same point after the Saga's attenuator. Set the blend once.
3. **The pod remains the vinyl kill switch.**

---

## Circuit

> [!success] Every part below is in the DTU component shop inventory
> Values were chosen *around* what is stocked rather than picked first and
> sourced afterwards. Two substitutions drove the final numbers — see
> "Designing to the inventory".

```
 IN_L ──2µ2──16k5──┐
                   ├── N1 ──8k25── N2 ──►(+) A1 ──┬──► OUT1
 IN_R ──2µ2──16k5──┘   ▲            │       (−)◄──┘
                       │           C2      follower
                       └────C1──────┴── gnd (virtual, 6 V)

 OUT1 ──┬────────────────────────► SW2 ──► 10µF ──► VR1 10k ──┬──100R──► tip
        │                           ▲                   wiper └──100R──► ring
        └──10k──►(−) A2 ──10k───────┘
                     (unity inverter)
```

Netlist, so nothing is ambiguous:

| From | Through | To |
|------|---------|-----|
| IN_L | C_in1 2µ2 | A_L |
| A_L | **R_b1 100k** | virtual ground — DC bias |
| A_L | R1a 16k5 | N1 |
| IN_R | C_in2 2µ2 | A_R |
| A_R | **R_b2 100k** | virtual ground — DC bias |
| A_R | R1b 16k5 | N1 |
| N1 | R2 8k25 | N2 |
| N2 | C2 | virtual ground |
| N2 | — | A1 (+) |
| A1 out | — | A1 (−) — follower |
| A1 out | C1 | N1 — the Sallen-Key feedback |
| A1 out | R3 10k | A2 (−); A2 (+) to virtual ground; R4 10k A2(−)→A2 out |
| A1 out / A2 out | SW2 selects | C_out 10 µF → VR1 top |
| VR1 bottom | — | **signal ground (0 V), NOT virtual ground** |
| VR1 wiper | R5 100 Ω / R6 100 Ω | jack tip / jack ring |

> [!danger] Two errors caught in review — do not build without these
> **1. The bias resistors are mandatory.** The input coupling capacitors block
> DC, and C2 is a capacitor to virtual ground, so without `R_b1`/`R_b2` node N2
> has **no DC path at all** and A1 drifts to a supply rail. The board would
> appear dead.
>
> They belong *after* the coupling caps, one per channel. Biasing at N1 instead
> would put 100 kΩ in parallel with the filter's 8.25 kΩ R1 — 8.25k ∥ 100k =
> 7.62 kΩ, shifting every corner up by 8 %. At A_L and A_R they sit against the
> Saga's low output impedance and affect nothing, while forming a 0.72 Hz
> high-pass with the 2.2 µF coupling caps.
>
> **2. VR1's bottom goes to 0 V, not virtual ground.** `C_out` has already
> stripped the 6 V bias. Referencing the pot to virtual ground would put the
> output 6 V above the cable shield — the Bose's own 47 µF input capacitor would
> block it, but the step at power-on would thump the driver.

### Stage 1 — mono sum merged into the filter

`R1a` and `R1b` are **both** the summing network and the first resistor of the
Sallen-Key section: in parallel, 16.5 kΩ ∥ 16.5 kΩ = the 8.25 kΩ that the filter
needs. This saves an entire buffer stage. The Saga sees 16.5 kΩ per channel,
trivial for the tube buffer alongside the Fosi's input.

Input coupling capacitors of **2.2 µF** against 16.5 kΩ put a gentle high-pass at
**4.4 Hz**.

> [!important] Why 2.2 µF and not 1 µF
> These capacitors are in series with R1a/R1b, which are *also* the filter's R1.
> Their reactance therefore adds to the filter's own resistance and perturbs
> both the corner frequency and the phase response. At 87 Hz a 1 µF cap is
> 1.8 kΩ — over 10 % of a 16.5 kΩ leg, and reactive rather than resistive.
> 2.2 µF drops that to 830 Ω and puts the coupling corner well below the lowest
> filter setting, where it stops interacting.
>
> This is the general rule for a coupling cap feeding a filter input: it must be
> far enough below the filter's corner that it is not part of the filter.

### Stage 2 — 2nd-order Sallen-Key low-pass, switched corner

Unity-gain Sallen-Key with `R1 = R2 = 8.25 kΩ`:

- `f₀ = 1 / (2π·R·√(C1·C2))`
- `Q = 0.5·√(C1/C2)`

Three capacitor pairs, **all stocked film values**:

| Pos | C1 | C2 | f₀ | Q | Module then plays |
|-----|-----|-----|-----|-----|-------------------|
| 1 | 330 nF | 150 nF | **86.7 Hz** | 0.742 | 63–87 Hz, minimum overlap with the 4412s |
| 2 | 220 nF | 100 nF | **130.1 Hz** | 0.742 | 63–130 Hz, the expected default |
| 3 | 150 nF | 68 nF | **191.0 Hz** | 0.743 | 63–191 Hz, effectively wide open |

Steps are 1.50× and 1.47× — even spacing on a log scale, about 0.58 octave per
click. Q is 0.742 in all three positions, because the C1/C2 *ratio* is held at
2.2 throughout while the product scales.

> [!note] Why switching capacitors, not resistors, and not a dual-gang pot
> A ganged pot sweeping both resistors would vary the corner continuously, but
> its tracking error between sections directly skews Q — the filter's shape
> would change as you turn it, not just its frequency. Switched capacitor pairs
> hold Q constant and are exactly repeatable, which matters when tuning by ear
> and wanting to return to a setting that worked.

### Stage 3 — polarity

`A2` is a unity-gain inverter (`R3`, `R4` = 10 kΩ). `SW2` selects A1's output
directly (normal) or A2's output (inverted).

The aux path measured non-inverting, so **normal is the correct default**. The
switch is retained because with two sources overlapping across 63–191 Hz,
polarity is the single largest audible variable when integrating by ear — it
determines whether the two sources add or partially cancel through the
crossover region.

### Stage 4 — level and output

`VR1` is a 10 kΩ linear pot. **No output buffer.** The pot driving the Bose's
8.9 kΩ input costs level, which the trim absorbs, and the resulting source
impedance (≤2.5 kΩ) against the 2.4 nF input capacitance puts that pole at
26 kHz — three decades above anything in this signal path.

The two 100 Ω resistors keep the op-amp stable into that capacitive load and
isolate tip from ring so a short on one doesn't kill the other. The wiper feeds
both, which is what earns the measured +5.4 dB of internal summing.

`C_out` 10 µF against the 10 kΩ pot gives a 1.6 Hz high-pass — it exists only to
block the 6 V bias, not to filter.

---

## Power and grounding

| Item | Choice | Reason |
|---|---|---|
| Supply | **15 V DC Class II wall wart** | Double-insulated, **no earth pin** — the box floats and cannot form a mains loop between the Saga and the Bose |
| Regulation | **LM7812** → clean 12 V rail | Wall warts are electrically noisy; a 78-series regulator costs one part and removes the problem rather than relying on op-amp PSRR |
| Rail splitting | 2× 10 kΩ divider + 100 µF, buffered by **A3** | No TLE2426 needed — the quad op-amp has a spare section, and a buffered divider is a better virtual ground than a bare one because it can sink and source |
| Op-amp | **TL074** (quad) | A1 filter, A2 inverter, A3 virtual ground, A4 spare. Noise is irrelevant on a path low-passed at ≤191 Hz. At 12 V, swing ≈ 2.5 Vrms — ample for line level |
| Ground lift | Footprint for **10 Ω** between input and output grounds, normally linked | Fitted only if hum appears |

> [!note] A4 is unused — terminate it
> Leaving a spare op-amp section floating invites oscillation, which couples into
> its neighbours through the shared supply. Wire A4 as a follower with its (+)
> input tied to virtual ground.

> [!warning] The hum risk is real and worth designing for
> Three mains-powered devices (Saga, Fosi, Bose) become connected through this
> box. The Class II supply is the primary defence. If hum still appears, fit the
> 10 Ω lift; if that is insufficient, a line-level isolation transformer on the
> output is the fallback.

---

## Bill of materials

### In stock — nothing to order

| Ref | Value | Inventory line |
|-----|-------|----------------|
| U1 | **TL074** quad JFET op-amp | `IC, Linear, TL074` |
| — | DIP14 socket | `Connector, IC Socket, DIP14` |
| U2 | **LM7812** | `IC, Voltage Regulator, LM7812` |
| R1a, R1b | 16.5 kΩ | `Resistor, E96, 16K5` |
| R2 | 8.25 kΩ | `Resistor, E96, 8K25` |
| R3, R4 | 10 kΩ | `Resistor, E96, 10K0` |
| R5, R6 | 100 Ω | `Resistor, E96, 100R` |
| R7 | 10 Ω | `Resistor, E96, 10R0` |
| R8, R9 | 10 kΩ | virtual-ground divider |
| R_b1, R_b2 | 100 kΩ | **DC bias — board is dead without these** |
| C_in1, C_in2 | 2.2 µF film | `Capacitor, Film, 2u2` |
| C1 set | 330n / 220n / 150n film | `Capacitor, Film` — all three stocked |
| C2 set | 150n / 100n / 68n film | `Capacitor, Film` — all three stocked |
| C_out | 10 µF electrolytic | `Capacitor, Electrolytic, 10µF 50V` |
| C_vg | 100 µF electrolytic | virtual-ground bypass |
| C_dec | 3× 100 nF ceramic, 2× 100 µF | supply decoupling |
| VR1 | 10 kΩ potentiometer | `Resistor, Potentiometer, 10K` |
| SW2 | 2-pole changeover | `Hardware, Switch, 2-pol omskifter` |
| J1–J4 | 2-pole screw terminals | `Connector, Terminal, 2 pol skrueterminal` |
| SW1 | 6-pin header + 2 jumper shunts | `Connector, Header` — see below |

### Must be bought

| Item | Note |
|------|------|
| 15 V DC Class II wall wart | Must be double-insulated, **no earth pin** — this is the primary hum defence, not an optional nicety |
| 2× RCA panel sockets, 1× 3.5 mm panel socket, 1× DC barrel jack | Not stocked; board uses screw terminals with flying leads to panel jacks |
| 2× RCA Y-splitters | For the Saga output |
| Enclosure | Metal preferred — shields a high-impedance input |
| *Optional:* 2-pole 3-position rotary switch | See below |

### Designing to the inventory

Two stocked-parts problems drove the final values, and both improved the design:

**270 nF does not exist in the film range**, which killed the original 88 Hz
position. Rather than parallel two capacitors, the fix was to change the
*resistor*: at **R = 8.25 kΩ** instead of 10 kΩ, the stocked pairs 330n/150n,
220n/100n and 150n/68n land on 86.7 / 130.1 / 191.0 Hz — 1.5× spacing, and Q
identical at 0.742 in all three. E96 resistors give far more freedom than E12
capacitors, so when a filter value is awkward, **move the resistor**.

**No TLE2426 in stock.** Using the **TL074** instead of a TL072 provides a spare
section to buffer a simple resistive divider, which is a better virtual ground
anyway — it can sink and source current, where a bare divider with a bypass cap
only holds a level.

**No 3-position rotary switch in stock.** The board brings the capacitor
selection out to a **6-pin header**: two jumper shunts select a pair, which is
free and uses stocked parts. The same header accepts flying leads to a
panel-mounted rotary switch if one is bought later — worth doing, since by-ear
tuning wants fast A/B comparison and jumpers mean opening the box.

---

## Verification

Before it ever sees music, the board gets measured on the AD3 with the same
coherent-DFT tooling used in Phase 0:

1. **Transfer function per switch position** — network analyser sweep 10 Hz–2 kHz.
   Confirm corners at 86.7 / 130.1 / 191.0 Hz within tolerance and Q ≈ 0.742.
   Capacitor tolerance dominates: ±10 % parts shift f₀ by about ±5 %, since f₀
   depends on √(C1·C2) and the errors partly average. Q depends on the *ratio*
   C1/C2, so it is more exposed — measure it rather than assuming.
2. **Polarity switch** — confirm 180° between positions across the passband.
3. **Mono sum** — drive L only, R only, then both. Both should be +6 dB.
4. **Noise and hum floor** — measure output with inputs shorted.
5. **In situ** — sweep through the finished chain into the module and confirm
   the acoustic corner moves as the switch is turned.

---

## Rejected alternatives

| Option | Why not |
|---|---|
| 4th-order Linkwitz-Riley | Bose already provides −39 dB/oct above 203 Hz. Our filter cascades with theirs; 2nd order is sufficient and halves the parts count |
| Subsonic / rumble filter | Bose's own 4th-order high-pass at 63 Hz puts a 10 Hz warp signal ~65 dB down. Redundant here. Would matter on the 4412s, which this design deliberately does not touch |
| Passive RC dongle | No polarity switch, no level trim, no adjustable corner — and by-ear tuning needs all three |
| miniDSP 2x4 HD | Its advantage is delay, worth having, but ~€200 and not a build. Remains the escape hatch if by-ear integration proves impossible |
| Re-amping the driver | Would remove Bose's 63 Hz high-pass, but that filter is almost certainly excursion protection for a small driver in a small box. Also loses the pod's mute, which is wanted for vinyl |
| Dual-gang frequency pot | Tracking error skews Q; switched capacitors hold it constant and are repeatable |

---

## Open items

- **Bass Compensation range not measured.** Captures C and D (knob at each
  extreme) were never taken. Unknown whether it changes level or shape, and over
  what range. Worth measuring before finalising the level-trim range — if it
  already provides ±10 dB, VR1's job is smaller than assumed.
- **Crossover point is a guess until listened to.** 130 Hz is the expected
  default; the switch exists precisely because this cannot be predicted.
- **Sub placement** is untested and will matter more than any filter value.

---

## Related

- [[Test Guide - Companion 5 Characterisation]]
- [[Build Guide - 3rd Order PWM Filter]] — same Sallen-Key topology, same AD3 verification approach
- [[Amplifier - Fosi Audio V3]]
