# ESP32-WROOM-32 node board: handoff (updated 2026-09-25)

The original handoff is in `backup_pre_redraw/HANDOFF.orig.md`.

Single-sided SMD board, copper etched on the **xTool F1 Ultra fiber laser**.
USB-C -> CH340C (3.3 V mode) -> ESP32-WROOM-32, AMS1117-3.3, auto-reset,
EN/BOOT buttons, 2x16 GPIO breakout in module pin order, I2C header, 1-Wire header.

## Decisions made by Mads (do not re-ask)

| Question | Answer |
|---|---|
| Etch process | Fiber laser, not the 0.8 mm CNC mill. The mill can't cut the ESP32's 0.37 mm pad gaps, the SOT-23's 0.53 mm or the SOIC-16's 0.67 mm |
| Laser rule | 0.35 mm clearance / 0.5 mm track. **Assumed, not measured**: the test coupon was never cut |
| USB-C J1 | Keep the GCT USB4105 (0.20 mm inter-net gaps) as a hand-solder/rework exception |
| CH340C supply | 3.3 V mode (VCC + V3 on +3V3). At 5 V its TXD drove 5 V into the ESP32 |
| Orientation | SMD parts on the copper side (B.Cu, flipped). Header plastic on the plain side, pins pointing away from the SMD parts |
| I2C pins | SDA = IO23, SCL = IO22. SDA was IO21, but that forced a single-layer crossing (see below) |
| Outline | Smallest that routes. Currently 63 x 60.8 mm |

## Status

### Schematic: DONE, all four gates pass
- `sch_score.py`: PASS. Wired 87%, stitched 4%, floating 0 (16 deliberate NCs, all marked).
- `kicad-cli sch erc --severity-all`: 0 violations.
- `sch_verify.py` against the pre-redraw backup: only the intended changes (CH340C rail, I2C SDA).
- PDF checked by eye, text collisions fixed. `esp32node.pdf`, `sch_preview-1.png`.

Source of truth is `esp32node_sch.py`. Run `python3 esp32node_sch.py esp32node.kicad_sch`,
then re-export the netlist. Project symbols come from `make_symbols.py` -> `esp32node.kicad_sym`:
- `ESP32-WROOM-32_Phys`: pins in module order, so J2/J3 wire straight across.
- `CH340C_3V3`: V3 typed power_in, so ERC accepts the 3.3 V mode.

Project footprint: `esp32node.pretty/ESP32-WROOM-32_NoVias` (the stock footprint minus its 0.2 mm thermal vias).

### PCB: placed, NOT routed
- `esp32node.kicad_pcb` = placement + GND pour + hand-drawn J1 escape (locked).
  Fully reproducible: `python3 place_pcb.py` (bootstraps from `esp32node.net`
  via `bootstrap_pcb.py`).
- Copper DRC on the placed board is clean (0 clearance violations at 0.35/0.5).
  Only silkscreen cosmetics and the expected unrouted items remain.
- `wip_route/` holds the best FreeRouting attempt. **It is not usable**: 20 missing links
  and one real GND/+5V short. Read `wip_route/README.md`.

## What still has to happen

1. **Power distribution is the blocker.** +3V3 ends up in 8 pieces. At 0.35/0.5 a track can't pass
   between 2.54 mm header pads (it needs 1.2 mm and the gap is 0.84), so J2/J3 are walls. The
   board splits into regions:
   - the J3 outside strip
   - the J2 outside strip
   - the pocket under the module
   - the bottom-left (J4, U2)
   - the bottom-right

   +3V3 is needed in all of them. Options, in the order I'd try them:
   - (a) Add +3V3 (and maybe +5V) pour **regions** as well as GND. `place_floor` at 0.2/0.3 said
     GND + +3V3 + +5V pours take the floor to 0. At 0.35/0.5 it never finished (it hit a 3000 s
     cap), so that number isn't proven at this rule.
   - (b) Accept 1-3 wire bridges for +3V3. Route two-layer with F.Cu as expensive jumpers, then
     keep only straight F.Cu runs.
   - (c) Narrow oval header pads (1.2 x 2.0 mm), so a 0.5 mm track fits between pins.
     Mads chose the pin move instead for I2C, but this is still an option for power.
2. **FreeRouting and the locked J1 stubs.** Even with `PLACE_ROUTE_KEEP_LOCKED=1` the stubs reach
   the DSN, but the router crossed one: a GND track from J1's right shell pad ran over the
   VBUS-right stub. Either route GND as a plane there (use the `planes=keep` rung), or add a keepout.
3. **Track width.** The router necks down to 0.375 mm in places, which is under the 0.5 mm rule.
   Add a `.kicad_dru` rule `(constraint track_width (min 0.5mm))` for everything outside J1's
   courtyard, then fix any violations.
4. Gates to pass:
   - `place_floor.py --strict`: it won't finish at 0.35/0.5 in under an hour, so document that
     instead of claiming it.
   - `place_score.py --strict`: currently fails on cohesion (0.347) plus the deliberate U1/J1
     edge overhangs.
   - `place_route.py check`.
   - `place_view.py`.
   - Then the production export (Gerbers + drill + silkscreen DXF for the laser).
5. **Usability note:** with SMD parts on the underside, the RESET/BOOT buttons and USB-C face
   the table. That follows from the orientation decision, but check Mads is fine with pressing
   buttons from underneath.

## How to run the tooling on this Linux machine
```
# pcbnew + Python 3.14: SWIG iterators are broken -> use the shim
PYTHONPATH=tools/pyshim python3 <script using pcbnew>
# kicad-place engine lives here, not in ~/KiCad-Autoplace
export KICAD_AUTOPLACE=/home/mads/Projects/KiCad-Autoplace/plugin/plugins
# router: FreeRouting 1.9.0 hangs here (see gotchas); use 2.4.1 headless
PLACE_ROUTE_KEEP_LOCKED=1 FREEROUTING_JAVA_OPTS="-Djava.awt.headless=true" \
PYTHONPATH=tools/pyshim python3 ~/.claude/skills/kicad-place/scripts/place_route.py route \
    esp32node.kicad_pcb --out <scratch> --passes 20 --jar ~/.freerouting/freerouting-2.4.1.jar --timeout 400
```
Never run `kicad-cli sch upgrade`. Close KiCad before any script writes these files.
