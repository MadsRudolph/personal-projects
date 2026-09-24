# Illuminate 7 Mk2 — crossover board

One passive crossover board per speaker, so **build two**. Single-sided,
through-hole only, CNC isolation-milled with an 0.8 mm end mill (the DTU 62768
process). The topology is the PrintYourSpeakers reference crossover, unchanged;
only the component **values** are substituted for what the DTU component shop
actually stocks.

| File | What it is |
|---|---|
| `illuminate7mk2-crossover.kicad_sch` / `.kicad_pro` | the schematic (KiCad 10) |
| `illuminate7mk2-crossover.pdf` / `.png` | rendered sheet |
| `illuminate7mk2-crossover-bom.csv` | BOM straight out of KiCad |
| `tools/crossover_layout.py` | the script that draws the sheet — edit this, not the `.kicad_sch` |
| `tools/make_coil_footprints.py` | generates the air-core coil footprints |
| `lib/crossover.pretty/` | those coil footprints |
| `sim/` | ngspice comparison of reference vs. substituted values |
| `illuminate7mk2-crossover.kicad_pcb` | the placed, unrouted board |
| `illuminate7mk2-crossover-pcb.png` | render of the placement |
| `tools/pcb_build.py` | builds and places the board from the netlist — re-run it after changing footprints |

Status: schematic done (ERC 0 violations), board placed (DRC 0 violations,
37 unconnected = the unrouted ratsnest). **Routing is by hand, next.** The
placement is on provisional footprints; see "Measurements still needed".

## Circuit

```
IN+ ─┬─[ C 2u2 ∥ L 0.20mH ∥ R 9R4 ]─ A ─[ C 5u5 ]─ B ─[ C 10u1 ]─ TWEETER +
     │                                             └─[ L 0.25mH ]─┐
     │                                                            │
     └─[ C 41u ∥ L 0.70mH ∥ R 20R ]─ C ─[ L 2.0mH ]─ D ───────────┼─ WOOFER +
                                                    └─[ C 11u5 ]──┤
IN− ─────────────────────────────────────────────────────────────┴─ both −
```

The `GND` symbol on the sheet **is IN−**, the amplifier's negative speaker
terminal and the common return for both drivers. It is not chassis earth, and
the left and right boards' returns must stay separate — the Fosi V3 is a
bridged (BTL) class-D amp and its negative outputs are not ground.

## BOM

### From the DTU component shop — per board

| Qty | Shop part number | Refs | Replaces (design value) |
|----:|---|---|---|
| 2 | `2u2` film cap | C101, C103 | C101 = 2.0 µF tank; C103 is half of the 5.6 µF |
| 3 | `3u3` film cap | C102, C105, C207 | halves of 5.6 µF, 10 µF and 12 µF |
| 1 | `6u8` film cap | C104 | half of the 10 µF |
| 6 | `8u2` film cap | C201–C205, C206 | 5 in parallel = 40 µF tank; C206 is half of the 12 µF |
| 2 | `4R7 5W` power resistor | R101, R102 | in series = 9.4 Ω / 10 W (design 10 Ω) |
| 2 | `10R 5W` power resistor | R201, R202 | in series = 20 Ω / 10 W (design 20 Ω) |
| 3 | `2 pol skrueterminal` | J1, J2, J3 | input, tweeter, woofer |

**For two boards: double every quantity** — 4 × `2u2`, 6 × `3u3`, 2 × `6u8`,
12 × `8u2`, 4 × `4R7 5W`, 4 × `10R 5W`, 6 × 2-pole screw terminals.

How the parallel groups add up:

| Group | Shop parts | Result | Design value | Error |
|---|---|---|---|---|
| C101 | 2u2 | 2.2 µF | 2.0 µF | +10 % |
| C102 ∥ C103 | 3u3 + 2u2 | 5.5 µF | 5.6 µF | −1.8 % |
| C104 ∥ C105 | 6u8 + 3u3 | 10.1 µF | 10 µF | +1 % |
| C201…C205 | 5 × 8u2 | 41 µF | 40 µF | +2.5 % |
| C206 ∥ C207 | 8u2 + 3u3 | 11.5 µF | 12 µF | −4.2 % |
| R101 + R102 | 2 × 4R7 5W | 9.4 Ω / 10 W | 10 Ω / 10 W | −6 % |
| R201 + R202 | 2 × 10R 5W | 20 Ω / 10 W | 20 Ω / 10 W | exact |

### Coils — buy these, the shop has nothing usable

The shop stocks only small ferrite chokes with no current rating and a few bare
toroid cores, and no magnet wire. All four coils are **air-core, 0.8 mm
(20 AWG) wire**. Per board:

| Ref | Value | Target DCR | Dayton | Jantzen (Danish) |
|---|---|---|---|---|
| L101 | 0.20 mH | 0.29 Ω | AC20-20 | Air Core 0.20 mH / 0.80 mm |
| L102 | 0.25 mH | 0.35 Ω | AC20-25 | Air Core 0.25 mH / 0.80 mm |
| L201 | 0.70 mH | 0.60 Ω | AC20-70 | Air Core 0.70 mH / 0.80 mm |
| L202 | 2.0 mH | 1.06 Ω | AC202 | Air Core 2.0 mH / 0.80 mm |

Buy **eight** coils in total, two of each. Air-core only: an iron or ferrite
core saturates and distorts at woofer levels. Check the DCR on the datasheet —
it is part of the design, not a parasitic, and a coil with materially lower DCR
shifts the level of that branch.

### Or wind them yourself

Air-core coils are just wire on a bobbin, so with enamelled copper wire and an
LCR meter they can be wound at home. Use **0.8 mm** wire: it is what the Dayton
parts use, and it lands the DCR on the design value. Starting points (Wheeler
multilayer formula, 3D-printed bobbin, hand-wound with ~15 % slack):

| Ref | Value | Bobbin core Ø × width | Turns | Layers | OD | Wire | DCR |
|---|---|---|---|---|---|---|---|
| L101 | 0.20 mH | 20 × 10 mm | ~91 | 10 | ≈40 mm | 8.5 m | ≈0.29 Ω |
| L102 | 0.25 mH | 22 × 10 mm | ~96 | 10 | ≈42 mm | 9.6 m | ≈0.33 Ω |
| L201 | 0.70 mH | 28 × 12 mm | ~141 | 12 | ≈52 mm | 17.7 m | ≈0.60 Ω |
| L202 | 2.0 mH | 40 × 14 mm | ~195 | 14 | ≈68 mm | 33 m | ≈1.1 Ω |

Total wire for two boards: about 140 m of 0.8 mm. Procedure:

1. Print a bobbin with the core diameter above, flanges 2 mm taller than the
   expected winding depth, and a slot in one flange for the start lead.
2. Wind about 5 % fewer turns than the table, tight and in even layers, keeping
   the wire under tension. Count turns.
3. Measure L on the LCR meter at 1 kHz. Inductance goes with turns squared, so
   add turns as `N_new = N × sqrt(L_target / L_measured)`. Aim for ±3 %.
4. Measure DCR on the meter's DC-resistance range (or 4-wire if it has it) and
   compare with the target above. If the coil comes out *lower* than target,
   add a shop 5 W resistor in series to make up the difference (0.1–0.68 Ω are
   stocked); if it is more than ~0.1 Ω *higher*, the wire is thinner than
   0.8 mm or the coil is looser than assumed, and it is better to rewind.
5. Fix the winding with a few wraps of tape or a drop of glue, and keep the
   two coils of each branch at least one coil diameter apart, or at right
   angles, on the board so they do not couple.

Thicker wire (1.0 mm) gives about 30 % lower DCR than the design, so it needs
the series-resistor trim in step 4 on every coil; thinner wire (0.6 mm) makes
the DCR too high and should not be used for L202.

### Capacitor voltage rating — check this yourself

The shop CSV gives **no voltage rating** for the film caps. The Fosi V3 runs
from a 48 V supply and is bridged, so the peak across the input terminals can
approach ±45 V, and the caps inside a resonant tank can see more than the input.

**Every film cap must be rated ≥ 63 V, and 100 V is the sensible choice.**
Read the printing on the actual parts before you fit them. If the shop's caps
turn out to be 50 V or 63 V parts, buy proper 100 V/250 V MKP crossover caps
instead — this is the one substitution that can fail loudly.

## Does this make an adequate crossover?

Yes. `sim/crossover_ac.cir` runs both versions side by side in ngspice with the
drivers modelled as plain resistors (4 Ω tweeter, 8 Ω woofer) and the coil DCRs
included, and `sim/compare.py` reports the difference over 100 Hz – 20 kHz:

| Branch | Max deviation from the reference | RMS |
|---|---|---|
| Tweeter | **+0.54 dB** at 12.7 kHz | 0.23 dB |
| Woofer | **+0.42 dB** at 1.05 kHz | 0.23 dB |

Nowhere in the band does either branch move more than 0.54 dB, and the woofer
stays under 0.5 dB everywhere. That is below the tolerance of the drivers
themselves (Dayton quotes ±10 % on Thiele-Small parameters, and 5 % film caps
are already worth a few tenths of a dB), and well under what is audible on a
broad, smooth deviation like this. The substituted set is fine.

Reproduce it with:

```bash
cd sim && ngspice -b crossover_ac.cir && python3 compare.py
```

## Board layout

`tools/pcb_build.py` builds the `.kicad_pcb` from the schematic netlist and
places it on a fixed floorplan that follows the signal flow, packed from the
footprints' real courtyards. **167 × 144 mm** with the provisional cap
footprints, inside the mill's 203 × 152 mm envelope. Re-run after any footprint
change:

```bash
kicad-cli sch export netlist --format kicadsexpr -o /tmp/xo.net illuminate7mk2-crossover.kicad_sch
python3 ~/.claude/skills/kicad-laser-pcb/scripts/pcb_netlist_json.py /tmp/xo.net /tmp/xo.json
python3 tools/pcb_build.py /tmp/xo.json illuminate7mk2-crossover.kicad_pcb
```

```
 row A   L101 pads | C101 R101 R102 | C102 C103 | L102 pads | C104 C105 | J2 TWEETER   (top)
 row C   J1 IN, R201 R202 | C201 C202 C203 C204 C205 | L201 pads                     (middle)
 row B   L202 pads | C206 C207 | J3 WOOFER                                           (bottom)
```

- **The coils are not on the board.** They would not fit the mill envelope, so
  each coil has only its two lead pads (`crossover:L_OffBoard_P10.16mm`,
  10.16 mm pitch, 1.4 mm holes) at a board edge: L101 left edge top, L202 left
  edge bottom, L201 right edge middle, L102 top row between the tweeter caps.
  Mount the coil bodies overhanging the edge next to their pads, or glue them to
  the enclosure beside the board, and bring the leads to the pads. Keep any two
  coils at least one coil diameter apart, and never stack one on another.
- Input on the left edge, tweeter out top-right, woofer out bottom-right.
- Copper is **B.Cu only**, single-sided. A GND zone is defined on B.Cu (the
  return for both drivers) but not filled — fill it after routing.
- Design rules: 0.85 mm clearance, 1.0 mm minimum track, **2.0 mm default
  track**. Use 2 mm or wider for everything; this board carries amps.
- Four M4 holes in the corners, 6 mm in. The Illuminate enclosure has five M4
  inserts for its own crossover plate; match those positions once you have the
  printed part, by editing `HOLE_INSET` / the hole list in the build script.
- The terminal-block footprints show a small triangle on the wire-entry side.
  J1 faces left, J2/J3 face right; if the real blocks turn out to open the
  other way, flip the rotation (90 ↔ 270) in `ROW_A/B/C`.
- DRC: 0 violations. Placement score: rotation, spacing and alignment pass;
  cohesion is 0.43 against a 0.25 threshold, which is the price of pushing the
  coil pads to the edges.

Routing notes for the hand pass: IN+ is the big net (11 pads, J1 → L101 tank,
R101, C101, and the whole woofer tank). Run it as one wide bus along the left
side and the middle row. GND has only six pads and the pour carries it. The
circuit is series-parallel, so nothing forces a wire bridge: it routes on one
layer with zero jumpers if the placement is respected.

## Measurements still needed before milling

The board is placed on footprints that are **provisional guesses** for three
part types. Measure the real parts, fix the footprints, and re-run
`tools/pcb_build.py` before routing for real; otherwise the components will not fit.

1. **Film capacitor lead pitch and body size.** The shop lists no dimensions.
   Currently assigned:
   - ≤ 3.3 µF → `C_Rect_L29.0mm_W13.0mm_P27.50mm_MKT` (27.5 mm pitch)
   - 6.8 / 8.2 µF → `C_Rect_L41.5mm_W20.0mm_P37.50mm_MKS4` (37.5 mm pitch)

   Measure lead spacing, body length, width and height on one of each value and
   pick the matching stock footprint.
2. **Coil lead spacing.** The off-board pad pairs are 10.16 mm apart with
   1.4 mm holes, which suits 0.8–1.0 mm wire. If you wind with thicker wire,
   raise `DRILL` in `tools/make_coil_footprints.py` and re-run it. (The
   on-board `L_AirCore_D*` footprints are kept in the library for a bigger
   board, but nothing uses them now.)
3. **5 W resistor body.** Assigned
   `R_Axial_Power_L25.0mm_W9.0mm_P30.48mm` (30.48 mm pitch). If the shop's 5 W
   parts are the ceramic-block type, check the lead spacing — those are often
   shorter-bodied with the leads bent to a narrower pitch.

Plan how the coils are held down — glue, or a cable tie through a pair of
extra holes (add them to the coil footprint). After routing, `kicad-laser-pcb`
does the Gerber/drill export for the mill.

## Notes on manufacturability

Every footprint currently on the board clears the 0.8 mm mill floor with room
to spare — the smallest pad-to-pad gap is 2.2 mm on the screw terminals, so
**no `.kicad_dru` exceptions are needed**. The netclass is already set to the
CNC profile (1.0 mm track, 0.85 mm clearance).

The coil footprints live in a project library, registered in `fp-lib-table` as
`crossover`. KiCad reads that at project load, so open the project rather than
the bare `.kicad_sch` if a footprint shows up as missing.

To redraw the sheet after a change, edit `tools/crossover_layout.py` and run it —
it rewrites both the `.kicad_sch` and the `.kicad_pro`, and verifies the netlist
against the intended topology before it writes anything. **Close KiCad first**;
it does not notice a `.kicad_sch` changing underneath it and will overwrite your
file from its stale copy on save.
