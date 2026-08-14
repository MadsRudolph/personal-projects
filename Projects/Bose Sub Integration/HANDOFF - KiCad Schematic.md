---
title: HANDOFF - KiCad Schematic
type: handoff
tags:
  - electronics
  - audio
  - crossover
  - kicad
status: Ready for schematic capture
updated: 2026-08-13
---

# HANDOFF — KiCad schematic for the sub crossover board

> [!important] Read this whole file first, then invoke the `kicad-laser-pcb` skill
> This document is self-contained. You do not need the conversation that produced
> it. Background lives in [[Design - Sub Crossover Board]] and
> [[Test Guide - Companion 5 Characterisation]], but everything required to draw
> the schematic correctly is below.

---

## What this board is

A line-level **mono-summing 2nd-order low-pass crossover** that feeds a Bose
Companion 5 bass module from a hi-fi preamp, so the module can act as midbass
reinforcement alongside a pair of JBL 4412 monitors.

Signal chain: Schiit Saga preamp → passive RCA Y-split → **this board** → 3.5 mm
into the Bose control pod's aux input. The other leg of the split goes to the
existing power amp untouched.

**Deliverable for this session: the schematic only** (`subxo.kicad_sch`). Layout
is a separate task.

---

## Hard requirements

| Constraint | Value |
|---|---|
| Board process | Single-sided, through-hole, etched on an xTool fiber laser |
| Jig format | 104 × 104 mm (the DTU 62768 process the skill implements) |
| Copper | Bottom layer only — no vias, no top-side tracks |
| Supply | Single +12 V rail from an on-board LM7812; **no negative rail** |
| Op-amp | One TL074 in a DIP14 socket. All four sections used or terminated |
| Off-board parts | Potentiometer, polarity switch and all panel jacks connect via screw terminals |

---

## Complete netlist

Nets are named. Draw exactly this.

### Power

| Ref | Value | Connection |
|-----|-------|------------|
| J4 | 2-pole screw terminal | pin 1 = `VIN` (+15 V from wall wart), pin 2 = `GND` |
| C10 | 100 µF electrolytic | `VIN` → `GND` |
| U2 | LM7812 (TO-220) | IN = `VIN`, GND = `GND`, OUT = `V12` |
| C11 | 100 µF electrolytic | `V12` → `GND` |
| C12 | 100 nF ceramic | `V12` → `GND`, close to U2 |
| C13 | 100 nF ceramic | `V12` → `GND`, at U1 pin 4 |
| C14 | 100 nF ceramic | `V12` → `GND`, second decoupler at U1 |
| R8 | 10 kΩ | `V12` → `VG_DIV` |
| R9 | 10 kΩ | `VG_DIV` → `GND` |
| C15 | 100 µF electrolytic | `VG_DIV` → `GND` |

U1 is powered from `V12` (pin 4) and `GND` (pin 11). **There is no negative
supply** — this is a single-rail design with a mid-rail reference.

### TL074 section assignment

| Section | Pins (DIP14) | Role |
|---------|--------------|------|
| A1 | 1 out, 2 in−, 3 in+ | Sallen-Key filter, unity-gain follower configuration |
| A2 | 7 out, 6 in−, 5 in+ | Unity inverter for the polarity switch |
| A3 | 8 out, 9 in−, 10 in+ | Virtual-ground buffer |
| A4 | 14 out, 13 in−, 12 in+ | **Spare — must be terminated** |

- **A3:** pin 10 ← `VG_DIV`; pin 9 ← pin 8; pin 8 = net **`VGND`** (the 6 V
  virtual ground used as the AC reference throughout).
- **A4:** pin 12 ← `VGND`; pin 13 ← pin 14. An unterminated spare section can
  oscillate and couple into its neighbours through the shared supply.

### Signal path

| Ref | Value | From | To |
|-----|-------|------|-----|
| J1 | 2-pole screw terminal | pin 1 = `IN_L`, pin 2 = `GND` |
| J2 | 2-pole screw terminal | pin 1 = `IN_R`, pin 2 = `GND` |
| C_in1 | 2.2 µF film | `IN_L` | `A_L` |
| C_in2 | 2.2 µF film | `IN_R` | `A_R` |
| R_b1 | 100 kΩ | `A_L` | `VGND` |
| R_b2 | 100 kΩ | `A_R` | `VGND` |
| R1a | 16.5 kΩ | `A_L` | `N1` |
| R1b | 16.5 kΩ | `A_R` | `N1` |
| R2 | 8.25 kΩ | `N1` | `N2` |
| — | — | `N2` | U1 pin 3 (A1 in+) |
| — | — | U1 pin 1 (A1 out) | U1 pin 2 (A1 in−) — follower |
| — | — | U1 pin 1 | net `OUT1` |
| R3 | 10 kΩ | `OUT1` | U1 pin 6 (A2 in−) |
| R4 | 10 kΩ | U1 pin 6 | U1 pin 7 (A2 out) |
| — | — | U1 pin 5 (A2 in+) | `VGND` |
| — | — | U1 pin 7 | net `OUT2` |

### Switched capacitors

Two 6-pin headers, each arranged as **three adjacent pairs** so a standard
2.54 mm jumper shunt bridges one pair.

`JP1` — selects C1 (the Sallen-Key feedback capacitor, returning to `N1`):

| Ref | Value | One end | Other end |
|-----|-------|---------|-----------|
| C1a | 330 nF film | `OUT1` | JP1 pin 1 |
| C1b | 220 nF film | `OUT1` | JP1 pin 3 |
| C1c | 150 nF film | `OUT1` | JP1 pin 5 |

JP1 pins 2, 4, 6 are all connected to `N1`.

`JP2` — selects C2 (from `N2` to virtual ground):

| Ref | Value | One end | Other end |
|-----|-------|---------|-----------|
| C2a | 150 nF film | `N2` | JP2 pin 1 |
| C2b | 100 nF film | `N2` | JP2 pin 3 |
| C2c | 68 nF film | `N2` | JP2 pin 5 |

JP2 pins 2, 4, 6 are all connected to `VGND`.

**Silkscreen must label the three positions `87 Hz`, `130 Hz`, `191 Hz` and warn
that JP1 and JP2 must be in the same position, one jumper each.** A mismatched
pair produces a wrong Q rather than an obviously broken board, which is the hard
kind of fault to find.

### Output stage

| Ref | Value | From | To |
|-----|-------|------|-----|
| J5 | 3-pole screw terminal | pin 1 = `OUT1`, pin 2 = `OUT2`, pin 3 = `SW_COM` — external polarity switch |
| C_out | 10 µF electrolytic | `SW_COM` (**+ terminal**) | `POT_TOP` |
| J6 | 3-pole screw terminal | pin 1 = `POT_TOP`, pin 2 = `POT_W`, pin 3 = `GND` — external 10 kΩ pot |
| R5 | 100 Ω | `POT_W` | `OUT_TIP` |
| R6 | 100 Ω | `POT_W` | `OUT_RING` |
| R7 | 10 Ω | `GND` | `OUT_GND` |
| JP3 | 2-pin header + shunt | across R7 | ground lift, **normally shorted** |
| J3 | 3-pole screw terminal | pin 1 = `OUT_TIP`, pin 2 = `OUT_RING`, pin 3 = `OUT_GND` |

---

## Things that are easy to get wrong here

> [!danger] Five specific checks
> 1. **C1 returns to `N1`, not `N2`.** This is the Sallen-Key feedback path. If
>    it lands on N2 you have built a different filter entirely.
> 2. **`R_b1` and `R_b2` are mandatory.** The coupling caps block DC and C2 is a
>    capacitor, so without these the op-amp's + input has no DC path and A1
>    drifts to a rail. The board will look dead. They must sit *after* the
>    coupling caps, not at N1 — 100 kΩ at N1 would parallel the 8.25 kΩ R1 and
>    shift every corner by 8 %.
> 3. **`VR1`'s bottom (J6 pin 3) goes to `GND`, not `VGND`.** C_out has already
>    removed the 6 V bias; referencing the pot to VGND would put 6 V on the
>    output cable and thump the driver at power-on.
> 4. **C_out's positive terminal faces `SW_COM`.** That node sits at 6 V DC; the
>    pot side sits at 0 V.
> 5. **U1 pin 11 goes to `GND`, not to a negative rail.** Single supply.

---

## Component packages

All through-hole. The film capacitors are physically large — 330 nF and 2.2 µF
especially — so allow generous pad pitch and body clearance rather than the
default small footprints.

| Part | Package notes |
|------|---------------|
| U1 TL074 | DIP-14, fitted in a socket — footprint must be the socket's |
| U2 LM7812 | TO-220, vertical, no heatsink needed (~20 mA draw) |
| Film capacitors | Boxed film, 5 mm or 7.5 mm lead pitch. Check 2.2 µF and 330 nF bodies specifically |
| Electrolytics | Radial, 50 V parts from stock |
| Resistors | 1/4 W axial, E96 metal film |
| Headers | 2.54 mm male pin header |
| Screw terminals | 5.08 mm pitch, 2- and 3-pole |

---

## What to produce

1. `hardware/kicad/subxo.kicad_sch` — complete schematic, all nets named as above
2. Clean ERC — no unconnected pins, no power-input conflicts. If ERC complains
   about `VGND` not being driven by a power source, that is expected for an
   op-amp-generated reference; resolve it with a PWR_FLAG rather than by
   rewiring
3. Footprints assigned for every symbol

**Do not start the PCB layout in this session.** Layout is a separate task with
its own constraints (104 × 104 mm jig, single-sided, two-stage Freerouting).

---

## Verification before you call it done

Walk the netlist tables above row by row against the drawn schematic. Then
confirm the five danger-list items individually. The board is small enough that
a full manual check is quick and far cheaper than re-etching.
