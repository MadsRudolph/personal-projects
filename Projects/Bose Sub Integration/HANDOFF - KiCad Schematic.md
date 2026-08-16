---
title: HANDOFF - KiCad Schematic
type: handoff
tags:
  - electronics
  - audio
  - crossover
  - kicad
status: Rev B captured and verified; layout outstanding
updated: 2026-08-16
---

# HANDOFF — KiCad schematic for the sub crossover board

> [!important] Read this whole file first, then invoke the `kicad-laser-pcb` skill
> This document is self-contained. You do not need the conversation that produced
> it. Background lives in [[Design - Sub Crossover Board]] and
> [[Test Guide - Companion 5 Characterisation]], but everything required to draw
> the schematic correctly is below.

> [!warning] This document is the design of record, and `verify_netlist.py`
> transcribes it independently
> The checker is written *from these tables*, not from `build_schematic.py`, so a
> generator bug shows up as a mismatch instead of being echoed back. If you
> change a net here, change it there too — and never by copying from the
> generator.

---

## What changed in rev B (2026-08-16)

Rev A was built, measured through Gate 5, and characterised in
[[Results - Sub Crossover Bring-up]]. Rev B is the respin that follows from
that, plus a panel rotary switch.

| Change | Why |
|---|---|
| **Capacitor values are the as-built ones**, not the drawn ones — `C2_2` is 120 nF | Every measured corner depends on the parts actually soldered. `C2_3` also measures −6.2 %, confirmed out-of-sample |
| **`C1_1` is fitted, at 470 nF** | Gives a 94.0 Hz corner — the first time the board reaches below 100 Hz. Rev A left it out and faked its setting by paralleling `C1_2 ∥ C1_3` on two jumpers |
| **The parallel trick is retired** | It cannot survive a rotary switch. Wiring one header pin to two lugs ties those lugs together, and every position collapses to the same value |
| **`C_in` is 220 nF on a dual-pitch footprint** | 220 n is what measured well; 2 µ2 is still arguable and Gate 11 has not run. The footprint takes either |
| **Every capacitor footprint comes from calipers** | Rev A had `C1_2`, `C1_3` and `C2_2` on footprints too short for them. `C1_2` is a 15 mm part that was squeezed into a 7.50 mm footprint — its leads were bent inward by 7.5 mm |
| **Two status LEDs** | `D1` power, `D2` inverted-polarity off SW2's unused second pole |

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
| C_in1 | 220 nF film (see note) | `IN_L` | `A_L` |
| C_in2 | 220 nF film (see note) | `IN_R` | `A_R` |
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

> [!note] `C_in` is 220 nF, and it is inside the filter
> Rev A substituted 220 nF for the drawn 2.2 µF. That is not merely an input
> high-pass: `C_in` sits in series with `R1_1`/`R1_2`, which are *also* the
> filter's R1, so 8.8 kΩ of reactance at 82 Hz lands inside the filter. It costs
> 1.3–3.1 dB of passband level and damps the peaking. Measured, and an
> alternative fit at 246 nF was tested against the sweep data and rejected.
>
> Whether 220 nF or 2.2 µF is the better *choice* is a listening question that
> Gate 11 has not answered. 2.2 µF would move the three switch corners to
> 88 / 127 / 192 Hz and cut the level spread between positions from 3.3 dB to
> 1.7 dB, which matters because loudness confounds an A/B comparison. So the
> footprint is dual-pitch and takes either. **Fit one pair of pads, not both.**

### Switched capacitors

Two 6-pin headers. Odd pins carry the capacitors, even pins carry the node. A
2.54 mm shunt across a pair selects that capacitor; the intended control is an
off-board rotary switch on the same pins (below).

`JP1` — selects C1 (the Sallen-Key feedback capacitor, returning to `N1`):

| Ref | Value | One end | Other end |
|-----|-------|---------|-----------|
| C1_1 | **470 nF** film | `OUT1` | JP1 pin 1 |
| C1_2 | 220 nF film | `OUT1` | JP1 pin 3 |
| C1_3 | 150 nF film | `OUT1` | JP1 pin 5 |

JP1 pins 2, 4, 6 are all connected to `N1`.

`JP2` — selects C2 (from `N2` to virtual ground):

| Ref | Value | One end | Other end |
|-----|-------|---------|-----------|
| C2_1 | 150 nF film | `N2` | JP2 pin 1 |
| C2_2 | **120 nF** film | `N2` | JP2 pin 3 |
| C2_3 | 68 nF film | `N2` | JP2 pin 5 |

JP2 pins 2, 4, 6 are all connected to `VGND`.

> [!danger] JP1 and JP2 select **independently** — the old "same position, one
> jumper each" rule was wrong
> There is no ganging in hardware. Nine combinations exist, and rev A measured
> all nine: **100.7 to 212.3 Hz**. Nothing forces a matched pair, and a
> mismatched one is a legitimate setting rather than a fault.
>
> The silkscreen must **not** say `87 Hz / 130 Hz / 191 Hz`. Those came from
> `f0 = 1/(2π·R·√(C1·C2))`, which is the Sallen-Key natural frequency, not the
> −3 dB point a sweep reports. The two coincide only at Q = 0.707 and these
> settings run Q = 0.50 to 1.17. Label the headers `C1 SELECT` / `C2 SELECT`
> with the capacitor values, and put the corner table in the documentation
> where it can be corrected.

#### The rotary switch, and the wiring rule that constrains it

The intended control is a panel-mounted **2-pole 3-position rotary**: one pole
on JP1, one on JP2, commons isolated from each other. Lug map:

| Position | Corner | Pole A → JP1 | Pole B → JP2 |
|---|---|---|---|
| 1 | **94.0 Hz** | `A0` → even pin, `A1` → pin 1 (470 n) | `B0` → even pin, `B1` → pin 1 |
| 2 | **135.5 Hz** | `A2` → pin 5 (150 n) | `B2` → pin 3 |
| 3 | **189.2 Hz** | `A3` → pin 3 (220 n) | `B3` → pin 5 |

> [!danger] One wire per lug
> A wire split to two lugs **ties those lugs together permanently** — the rotary
> isolates common from lugs, not lugs from each other. A wire may serve two lugs
> only if both want the same capacitance. This is why `C1_1` is fitted rather
> than paralleling `C1_2 ∥ C1_3` on one lug: that scheme would have shorted all
> three positions to 365 nF and produced three identical curves.

Two checks on any candidate switch before wiring: `A0`→`B0` must read **open in
every detent** (a wafer that busses its commons would tie `N1` to `VGND` and
silence the filter), and note whether it is shorting or break-before-make.
Shorting is *preferable* here — momentarily paralleling two C1s or two C2s is
just another valid setting, whereas a break on the C2 pole removes the low-pass
entirely for a few milliseconds.

`N1` is the exposed net on the loom, about 3 kΩ to AC ground at 50 Hz. Twist it
with its pole's position wires, keep the run short, and **re-run Gate 8 after
fitting**.

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

### Status LEDs

Both run about 2 mA, so the LM7812 gains at most 4 mA on a 10–16 mA board and
still dissipates under 70 mW. Neither touches a signal node.

| Ref | Value | From | To |
|-----|-------|------|-----|
| R10 | 4.7 kΩ | `V12` | `PWR_A` |
| D1 | LED, green — **power** | anode (pin 2) = `PWR_A` | cathode (pin 1) = `GND` |
| R11 | 4.7 kΩ | `V12` | `INV_A` |
| D2 | LED, amber — **inverted** | anode (pin 2) = `INV_A` | cathode (pin 1) = `INV_K` |
| J7 | 2-pole screw terminal | pin 1 = `INV_K`, pin 2 = `GND` |

`D1` sits on `V12` rather than `VIN`, so it proves the regulator rather than
just that something is plugged in.

`D2` rides **SW2's second pole**. The polarity switch was always specified as a
2-pole changeover and rev A used only one pole, so the lamp costs a resistor, an
LED and a 2-way terminal. `J7` pin 1 goes to that spare pole's INVERTED lug and
pin 2 to its common, returning the 2 mA to board `GND`. The lamp therefore
lights only in the inverted position — worth knowing at a glance, because
polarity is the single largest audible variable when integrating by ear.

Note `Device:LED` pin numbering: **pin 1 is the cathode, pin 2 the anode.**

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

All through-hole.

> [!danger] Do not infer a film capacitor's footprint from its value
> Every one of rev A's fitting problems came from this. The pitches below are
> **measured** (2026-08-16), caliper inside-to-inside and outside-to-outside:
> those average to the pitch and differ by the lead diameter. No two capacitors
> in the C1 bank are the same part, and neither bank is a uniform row.

| Ref | Value | Pitch | Body | Footprint |
|---|---|---|---|---|
| `C1_1` | 470 n | 5 mm | 7.5 × 3.0 | `Capacitor_THT:C_Rect_L7.2mm_W3.0mm_P5.00mm_FKS2_FKP2_MKS2_MKP2` |
| `C1_2` | 220 n | **15 mm** | 16.0 × 7.0 | `Capacitor_THT:C_Rect_L18.0mm_W7.0mm_P15.00mm_FKS3_FKP3` |
| `C1_3` | 150 n | 10 mm | 10.0 × 4.0 | `Capacitor_THT:C_Rect_L11.0mm_W4.2mm_P10.00mm_MKT` |
| `C2_1` | 150 n | 5 mm | — | `Capacitor_THT:C_Rect_L7.2mm_W5.5mm_P5.00mm_FKS2_FKP2_MKS2_MKP2` |
| `C2_2` | 120 n | 10 mm | 12.0 × 4.0 | `Capacitor_THT:C_Rect_L13.0mm_W4.0mm_P10.00mm_FKS3_FKP3_MKS4` |
| `C2_3` | 68 n | 5 mm | — | `Capacitor_THT:C_Rect_L7.2mm_W5.5mm_P5.00mm_FKS2_FKP2_MKS2_MKP2` |
| `C_in1/2` | 220 n | 15 mm fitted | 16.0 × 7.0 | `energy_system:C_Rect_L18.0mm_W9.0mm_P5.00mm_P15.00mm_MultiPitch` |

`C1_2`, `C_in1` and `C_in2` are **the same physical capacitor** — 220 nF, 15 mm
pitch, 16 × 7 body. Three large parts wanting the same clearance. Place those
first and let the rest of the filter and input blocks fall around them.

`C1_2` is on `L18` rather than the tighter `L16.5`, because `L16.5` drills
1.1 mm and that is 0.1 mm of slack on a 1 mm lead. `L18` drills 1.2 mm, a size
already in the board's drill set.

The `C_in` footprint is dual-pitch: 5.00 mm and 15.00 mm pads on one part, both
centred at x = 7.5. Same-number pads share a net, so the unused pair needs no
isolation from its sibling and the tightest pad-1-to-pad-2 channel stays 3.0 mm
— clear for a 0.8 mm laser gap or a 1.2 mm endmill.

| Part | Package notes |
|------|---------------|
| U1 TL074 | DIP-14, fitted in a socket — footprint must be the socket's |
| U2 LM7812 | TO-220, vertical, no heatsink needed (~20 mA draw) |
| Electrolytics | Radial, 50 V parts from stock |
| Resistors | 1/4 W axial, E96 metal film |
| LEDs | 3 mm through-hole, `LED_THT:LED_D3.0mm` |
| Headers | 2.54 mm male pin header |
| Screw terminals | 5.08 mm pitch, 2- and 3-pole. **`bornier` lives in the project library** — KiCad 10 deleted it from stock |

---

## State, and how to re-verify

The schematic is generated, not hand-drawn: `tools/build_schematic.py` holds the
netlist as data and writes `subxo.kicad_sch`. Edit the generator, not the
`.kicad_sch` — *until* the board is hand-placed, after which the `.kicad_sch`
becomes the thing you edit and the generator is history.

```
py -3.13 tools/build_schematic.py
kicad-cli sch erc --severity-error subxo.kicad_sch
kicad-cli sch export netlist --format kicadsexpr -o b.net subxo.kicad_sch
py -3.13 <skill>/scripts/pcb_netlist_json.py b.net subxo.json
py -3.13 tools/verify_netlist.py
```

**Rev B passes at ERC 0 errors and 115 of 115 checks**, including all five
danger-list items. The only ERC warnings are `lib_symbol_mismatch`, which is the
KiCad 9 symbol cache differing cosmetically from KiCad 10's libraries — benign.
`verify_netlist.py` resolves footprints against **KiCad 10**, not 9; checking
against 9 is how the `bornier` terminal blocks got through, since 9 still ships
them and 10 does not.

---

## Layout

Rev B is captured, verified, and ready to place. Layout constraints:

- Single-sided, bottom copper only, no vias.
- **Clearance is a decision, not a default.** Rev A ran 0.85 mm with a 0.8 mm
  end mill — 0.05 mm of margin. Either keep 0.85 mm and cut with a 0.4 mm
  (1/64") bit, or rebuild at ≥1.2 mm via `LASERPCB_CLEARANCE_MM`.
- The 104 × 104 mm jig applies to the **laser** only. The SRM-20 sets its origin
  in VPanel, so a milled board can be its natural size.
- Rev A's copper is not reusable: five capacitor footprints changed pitch
  (`C1_1`, `C1_2`, `C1_3`, `C2_2`, `C_in1/2`) and five parts are new (`D1`,
  `D2`, `R10`, `R11`, `J7`). `C1_1` was already placed on rev A as a DNP
  footprint, so it is a swap rather than an addition — but it is now populated.
- **`J1`–`J5` are locked** on the rev A board; `pcb_build.py` pins the edge
  connectors. Unlock them before hand-placing.
- Importing rev B needs **Re-link footprints … based on their reference
  designators** ticked. `build_schematic.py` mints fresh UUIDs on every run, so
  every symbol association on the board is stale and matching has to fall back
  to refdes. Without it KiCad treats every existing footprint as orphaned and
  every symbol as new, and you get a duplicate of the whole board.
- Courtyards total **2731 mm² over 43 parts** — 27 % of a 100 × 100 board, 25 %
  of 104 × 104. Comfortable for single-sided routing, though wider clearance
  eats channel width rather than component area.

> [!warning] `energy_system` exists in two places and they can drift
> The KiCad GUI resolves it through the project's `fp-lib-table` to
> `hardware/kicad/lib/energy_system.pretty`. But `pcb_build.py` hardcodes
> `<skill>/lib/energy_system.pretty` and, for everything else, **KiCad 9's**
> stock footprints. A footprint added to the project lib only will work in the
> GUI and then fail a fresh `route_board.ps1 -Sch` with `footprint ikke fundet`.
> `C_Rect_L18.0mm_W9.0mm_P5.00mm_P15.00mm_MultiPitch` is currently copied into
> both. The skill directory is outside this repo, so that copy is not version
> controlled — re-copy it if the pipeline is ever run on another machine.
>
> `-KeepPlacement` never calls `pcb_build.py`, so hand-placing in the GUI and
> re-routing avoids this path entirely.

---

## Verification before you call it done

Walk the netlist tables above row by row against the drawn schematic. Then
confirm the five danger-list items individually. The board is small enough that
a full manual check is quick and far cheaper than re-etching.
