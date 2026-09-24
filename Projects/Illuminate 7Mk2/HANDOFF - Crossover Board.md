---
title: HANDOFF - Crossover Board
type: handoff
tags:
  - Audio
  - Speakers
  - crossover
  - KiCad
  - CNC
  - handoff
parent: "[[Illuminate 7Mk2 - Speaker Build]]"
status: Routed and exported for the mill (production/); coils being wound
started: 2026-09-24
updated: 2026-09-24
---

# HANDOFF - Crossover Board

## Paste this into the new session

> I am continuing the Illuminate 7 Mk2 passive crossover board. Run `git pull`
> in `C:\Users\Mads2\personal-projects` first, then read
> `Projects/Illuminate 7Mk2/HANDOFF - Crossover Board.md` in full, then
> `Projects/Illuminate 7Mk2/crossover/README.md`. Do not redo the schematic
> or the placement; both are finished and verified. The circuit topology is
> frozen; only component footprints and the routing are open.
>
> I am at school with the DTU component shop, an LCR meter and the CNC
> (203 × 152 mm maximum board). Today I want to: (1) measure the real film
> caps, 5 W resistors and terminal blocks and put the right footprints in,
> (2) re-pack the board with `tools/pcb_build.py`, (3) route it by hand in
> KiCad on B.Cu only, (4) export Gerbers/drill for the mill. Ask me for the
> measurements before changing any footprint, and do not commit without
> asking.

---

## Where things stand

One passive 2-way crossover board per speaker, built twice, for the
PrintYourSpeakers Illuminate 7 Mk2 (Dayton RS180P-8 woofer, RST28F-4 tweeter,
Fosi V3 amp on 48 V). Everything lives in
`Projects/Illuminate 7Mk2/crossover/` and is pushed to `origin/main`
(last commit 3451232).

| Done | Evidence |
|---|---|
| Reference circuit redrawn in KiCad 10 with values from DTU shop stock | `illuminate7mk2-crossover.kicad_sch`, ERC 0 violations, readability score 13/13 |
| Substituted values proven adequate | ngspice in `sim/`: tweeter within +0.54 dB, woofer within +0.42 dB of the reference, 100 Hz–20 kHz |
| Board built from the netlist and placed | `illuminate7mk2-crossover.kicad_pcb`, 151 × 120 mm on measured footprints, DRC 0 violations, 37 unconnected = the unrouted ratsnest |
| Coils moved off the board | only lead-pad footprints (`crossover:L_OffBoard_P10.16mm`) at the board edges |

Not done: routing, Gerber export, measured footprints, enclosure mounting-hole
positions.

## The circuit (frozen)

Topology is the PYS reference unchanged. Only values differ, and every one is a
shop part or a series/parallel combination of shop parts:

| Ref | Shop part | Makes | Design value |
|---|---|---|---|
| C101 | 2u2 film | 2.2 µF | 2 µF tweeter tank |
| C102 ∥ C103 | 3u3 + 2u2 film | 5.5 µF | 5.6 µF |
| C104 ∥ C105 | 6u8 + 3u3 film | 10.1 µF | 10 µF |
| C201..C205 | 5 × 8u2 film | 41 µF | 40 µF woofer tank |
| C206 ∥ C207 | 8u2 + 3u3 film | 11.5 µF | 12 µF |
| R101 + R102 | 2 × 4R7 5W | 9.4 Ω / 10 W | 10 Ω |
| R201 + R202 | 2 × 10R 5W | 20 Ω / 10 W | 20 Ω |
| L101 / L102 / L201 / L202 | air-core, self-wound or bought | 0.20 / 0.25 / 0.70 / 2.0 mH | target DCR 0.29 / 0.35 / 0.60 / 1.06 Ω |
| J1 / J2 / J3 | 2-pole screw terminal | IN / TWEETER / WOOFER | |

`GND` on the sheet is IN−, the amplifier's negative speaker terminal. The Fosi
V3 is bridged, so it is not chassis ground and the two boards' returns must
stay separate.

The shop CSV lists no voltage rating for its film caps. **They must be ≥ 63 V,
100 V preferred**; read the printing on the actual parts. If they are 50 V
parts, buy proper crossover caps instead. This is the one substitution that
can fail loudly.

## Measured parts (2026-09-24)

All shop parts were measured and the board re-packed on the real footprints;
the table is in the crossover README and in `DTU-EKB/KiCad-components`. The 2u2
caps are only 63 V and were accepted as they are. The shop has no usable coils
(only small ferrite chokes; a 270 µH might do for L102 if its DCR is
≤ 0.35 Ω), so L101, L201 and L202 are being wound.

Still unknown: the positions of the enclosure's five M4 inserts. The board has
four placeholder M4 holes 6 mm in from each corner.

## How the files are generated (edit scripts, not outputs)

The schematic and the board are both written by scripts; editing the
`.kicad_sch` or `.kicad_pcb` by hand and then re-running a script will lose the
edit. Close KiCad before re-running either.

- `tools/crossover_layout.py` draws the schematic. Footprint assignments are
  the `FP_*` constants near the top; change them there.
- `tools/make_coil_footprints.py` writes `lib/crossover.pretty/`.
- `tools/pcb_build.py` builds and places the board from the exported netlist.
  The floorplan is the `ROW_A / ROW_C / ROW_B` trees near the top; sizes come
  from the real courtyards, so a footprint change re-packs automatically.

Full rebuild, from the crossover folder (Windows: use KiCad's own
`python.exe` for `pcb_build.py`, it needs `pcbnew`; the other two run on any
Python 3):

```bash
python3 tools/crossover_layout.py
kicad-cli sch erc --severity-all --exit-code-violations -o /tmp/erc.rpt illuminate7mk2-crossover.kicad_sch
kicad-cli sch export netlist --format kicadsexpr -o /tmp/xo.net illuminate7mk2-crossover.kicad_sch
python3 <kicad-laser-pcb skill>/scripts/pcb_netlist_json.py /tmp/xo.net /tmp/xo.json
python3 tools/pcb_build.py /tmp/xo.json illuminate7mk2-crossover.kicad_pcb
kicad-cli pcb drc --severity-error --format report -o /tmp/drc.rpt illuminate7mk2-crossover.kicad_pcb
```

`pcb_netlist_json.py` is in the `kicad-laser-pcb` skill. If that skill is not
on the school machine, the JSON it makes is trivial:
`{"nets": [names], "components": [{"ref", "value", "footprint", "pads": {padnum: net}}]}`,
readable from the `.net` s-expression.

**The routing is the one thing that must be done in KiCad by hand**, so once
the footprints are final, stop re-running `pcb_build.py`: it strips nothing,
but it re-places every part.

## Board rules

- Single-sided: copper on **B.Cu only**, zero vias, zero wire links. The circuit
  is series-parallel, so nothing forces a jumper.
- CNC profile: 0.85 mm clearance, 1.0 mm minimum track, **2.0 mm default
  track** set in the netclass. Use 2 mm or wider everywhere; the board carries
  amps. 0.8 mm end mill.
- A GND zone is defined on B.Cu and unfilled. Fill it after routing.
- IN+ is the big net, 11 pads: J1, the whole tweeter tank (C101, R101, L101)
  and the whole woofer tank (C201–C205, R201, L201). Run it as one wide bus
  down the left side and along the middle row.
- Coils mount off the board: overhanging the edge next to their pads, or glued
  to the enclosure beside the board. Keep any two coil bodies at least one coil
  diameter apart, never stacked.
- After routing: `kicad-laser-pcb` skill, `export_production` → Gerbers +
  Excellon for the mill. The CAM mirrors for the flipped board; do not
  pre-mirror.

## Layout as placed

```
 row A   L101 pads | C101 R101 R102 | C102 C103 | L102 pads | C104 C105 | J2 TWEETER   (top)
 row C   J1 IN, R201 R202 | C201 C202 C203 C204 C205 | L201 pads                     (middle)
 row B   L202 pads | C206 C207 | J3 WOOFER                                           (bottom)
```

Input on the left edge, tweeter out top right, woofer out bottom right. The
placement scorer passes rotation, spacing and alignment and fails cohesion
(0.43 vs 0.25) because the coil pads were pushed to the edges on purpose.

## Winding the coils (if not buying)

0.8 mm enamelled wire, air-core, LCR meter at 1 kHz. Starting points from the
Wheeler formula; wind ~5 % short, measure, add turns as
`N × sqrt(L_target / L_measured)`:

| Ref | Value | Bobbin core Ø × width | Turns | Wire | DCR |
|---|---|---|---|---|---|
| L101 | 0.20 mH | 20 × 10 mm | ~91 | 8.5 m | ≈0.29 Ω |
| L102 | 0.25 mH | 22 × 10 mm | ~96 | 9.6 m | ≈0.33 Ω |
| L201 | 0.70 mH | 28 × 12 mm | ~141 | 17.7 m | ≈0.60 Ω |
| L202 | 2.0 mH | 40 × 14 mm | ~195 | 33 m | ≈1.1 Ω |

The DCR is part of the design, not a parasitic. If a coil comes out lower than
target, add a shop 0.1–0.68 Ω 5 W resistor in series; if it is > 0.1 Ω higher,
rewind. Full procedure in the README.

## Decisions already made, do not reopen

1. Topology is the PYS reference; values are substituted, not redesigned.
2. Two 5 W resistors in series rather than one 5 W part, to keep the 10 W rating.
3. Coils off-board, because the mill envelope is 203 × 152 mm.
4. Woofer shunt caps sit between the two woofer coils' original positions to
   keep coil bodies apart; readability score is secondary to that.
5. Commits are by Mads, no AI attribution lines.

## Related

- [[Illuminate 7Mk2 - Speaker Build]] · [[Parts List - Illuminate 7Mk2]] · [[Build Log - Illuminate 7Mk2]]
- Reference schematic: `Resources/Illuminate 7Mk2/Illuminate_7_Mk2_Assembly_Guide.pdf`, page 5
- Shop stock: `components-inventory/dtu_component_shop(1).csv`
