# Handoff prompt: single-sided ESP32 board for the xTool F1 Ultra fiber laser

Paste this into the session working on the other ESP board. Everything below was
learned the hard way on `~/Projects/esp32-node` (2026-09-24/25) and is either measured
on that board or verified with KiCad 10.0.6 on this Linux machine.

---

You are designing a single-sided SMD ESP32 board whose copper is etched on Mads's
**xTool F1 Ultra fiber laser**. A sibling project, `~/Projects/esp32-node/esp32node/`,
went through the whole flow first; read its `HANDOFF.md`, `esp32node_sch.py`,
`place_pcb.py` and `esp32node.kicad_dru` before you start. Load the
`kicad-schematic`, `kicad-place` and `kicad-laser-pcb` skills. Those skills were written
for **through-hole boards milled on a Windows PC**, so several defaults below override them.

## 0. Proven laser settings: xTool F1 Ultra, copper isolation (verified 2026-09-26)

Mads cut the esp32node test coupon (`esp32_coupon_negative.dxf`: the ESP32-WROOM-32 pad
pattern with its 0.37 mm gaps, plus 0.15-0.50 mm clearance and trace ladders) with the
preset below. **The negatives came out perfectly.** This is the known-good starting point
for any ESP32 board on this machine. The exact XCS preset export is in
`~/Projects/esp32-node/xtool/F1Ultra_PCB_presets.json`
(repo: `MadsRudolph/personal-projects`, `esp32-node/xtool/`), and you can import it into XCS as is.

**`Traces`**, fill engraving (Engrave tab), used for the copper isolation:

| Setting | Value |
|---|---|
| Laser | Fiber IR |
| Power | 100 % |
| Speed | 600 mm/s |
| Passes | 10 |
| Lines per cm (density) | 240 (about 0.042 mm line pitch) |
| Scan mode | One-way |
| Frequency | 30 kHz |
| Scan angle | 0, incremental, cross hatch on |

This is *not* the DTU guide's "PCB-V1" preset (650 mm/s, 140 lines/cm, bi-directional).
The finer 240 lines/cm is the one to use for fine SMD gaps: at 140 lines/cm a 0.15-0.2 mm
gap is only 2-3 lines wide.

The same export has two companion presets:
- **`Cut/Drill`**: vector cutting, 100 %, 100 mm/s, **160 passes**, 30 kHz, no kerf. Use it for
  cutting outlines and holes with the laser.
- **`RemoveSolderMask`**: fill engraving, 40 %, 800 mm/s, 6 passes, 300 lines/cm, 30 kHz, one-way,
  cross hatch. Use it only on solder-mask boards, to open pads.

**How the file has to be prepared** (this is what came out perfectly):
- Give XCS a **negative**: closed shapes marking the copper to *remove*. Use windows around
  pad rows or traces, with the pads and traces inside as holes. Import the DXF, **Make compound**,
  and check that the removed areas are black and the copper you keep is white before you run.
- Export DXF in mm as closed R12 POLYLINEs, with reference geometry on its own layer. See the
  `dxf()` writer in `~/Projects/esp32-node/make_coupon.py`; no ezdxf needed.
- Sand the copper lightly with 400 grit, then Framing, then Auto height adjustment, then Process.
- On a real board, mirror the bottom-copper design in XCS (not in the export) when it is
  etched from the component-less side. For a coupon it doesn't matter.

## 1. Ask Mads these before any layout (they change everything)

- **Laser or mill?** The kicad-laser-pcb default is the 0.8 mm CNC end mill. It
  physically can't cut an ESP32 board: gaps narrower than the tool are left as shorts.
  Measured minimum pad gaps:

  | Footprint | Min gap |
  |---|---|
  | ESP32-WROOM-32 | 0.37 mm |
  | SOT-23 | 0.53 mm |
  | SOIC-16 (CH340C) | 0.67 mm |
  | 0805, SOT-223 | 0.80 mm |
  | USB-C GCT USB4105 | 0.20 mm between different nets |
  | 2.54 mm header | 0.84 mm |

  With a bare module, the answer on esp32node was: fiber laser.
- **Laser rule.** The skill's `laser` profile (0.8/1.0) can't fan out of an ESP32. esp32node
  uses **0.35 mm clearance / 0.5 mm track**, because the laser has to isolate the module's
  0.37 mm pad gaps anyway. The test coupon has now been cut, with the settings in section 0,
  and came out cleanly, so the ESP32 footprint itself is proven etchable. Mads has not
  reported which ladder step is the smallest clean one. If your board needs anything finer
  than 0.35/0.5, ask for that number before using it.
- **USB-C:** keep a fine-pitch receptacle as a hand-solder exception, or use a through-hole
  breakout? (esp32node kept the GCT USB4105.)
- **Which way the parts face.** On one copper layer every SMD part sits on the copper side
  (B.Cu), and THT headers solder there too. So the ESP32, buttons and USB-C face the table
  when the header pins point up.
- Board outline, and whether the GPIO pin mapping is fixed.

## 2. Schematic lessons

- **Check the CH340 supply.** A CH340C on +5V drives 5 V TXD into the ESP32's RXD0, which is not
  5 V tolerant. Use the datasheet's 3.3 V mode: VCC and V3 both on +3V3, 100 nF each.
  The stock KiCad symbol types V3 as `power_out`, so ERC then flags it against the
  regulator. esp32node generates a `CH340C_3V3` variant with V3 typed `power_in`; see
  `make_symbols.py`.
- **Use an ESP32 symbol with pins in module (physical) order** for a breakout board. With
  the stock symbol (GPIO-number order), header wiring crosses everywhere and the sheet
  falls back to labels (esp32node scored 53% wired and 37% stitched, a FAIL). With a
  physical-order symbol (`ESP32-WROOM-32_Phys`) the headers wire straight across: 87% / 4%, PASS.
  The same order is what makes the PCB fanout crossing-free.
- `sch_score.py`'s floating check now honours `no_connect` markers. Before that, 16 deliberate
  NCs (flash pins 17-22, pin 32, SBU, CH340 modem pins) read as "floating".
- The schematic script must pass `project_file=` to `Sheet()`, or each re-emit mints a new
  sheet uuid and Eeschema drops every symbol out of connectivity.
- Never run `kicad-cli sch upgrade`.

## 3. PCB lessons (ordered by how much time they cost)

1. **The clearance lives in `.kicad_pro`, not the board.** Setting the netclass on the board
   object from pcbnew does not reach DRC. esp32node's project still said 0.3 while
   the board said 0.35, and DRC checked 0.3. Edit `net_settings.classes[Default]` and
   `board.design_settings.rules` in the `.kicad_pro` JSON directly, keeping `wire_width`.
2. **`.kicad_dru` values need units in KiCad 10** (`0.15mm`, not `0.15`). kicad-cli silently
   ignores the entire rules file when it doesn't parse. Only
   `pcbnew.WriteDRCReport(board, path, pcbnew.EDA_UNITS_MM, False)` prints the parse error.
   To test that a rules file is loaded at all, add a deliberately strict rule and confirm the
   violation count moves. A custom rule also cannot go below the board-wide floors in
   `design_settings.rules`, so lower those floors and keep the netclass at the real value.
3. **Scope fine-pitch exceptions with `intersectsCourtyard`, not `memberOfFootprint`.**
   The latter only covers pad-to-pad. Hand-drawn escape tracks next to the pads need
   `A.intersectsCourtyard('J1') && B.intersectsCourtyard('J1')`.
4. **Flipping SMD parts to B.Cu.** KiCad's `Flip()` always mirrors about the x axis, whichever
   `FLIP_DIRECTION` you pass. Add 180 deg to the orientation of every flipped part so
   "rotation as seen from the top" means what you think, and keep the ESP32 antenna up.
   Assert pad sides from pad coordinates after placing; never assume.
   Flip any footprint with *any* SMD pad (the USB-C has plated shell legs as well).
5. **The ESP32 footprint carries a 48 x 21 mm antenna keep-out rule area** starting 9.8 mm
   above the module centre. Put the board edge exactly there, so the antenna overhangs and the
   keep-out is off-board. place_score then reports U1 "crossing Edge.Cuts" and bbox "overlaps"
   with the headers. Both are artefacts; KiCad DRC uses the real courtyard polygon.
6. **Remove the ESP32 thermal vias** (twelve 0.2 mm PTH in pad 39). They trip `drill_out_of_range`
   and are pointless on a one-layer board. esp32node has `esp32node.pretty/ESP32-WROOM-32_NoVias`.
7. **At 0.35/0.5, 2.54 mm headers are walls.** A track needs 0.35 + 0.5 + 0.35 = 1.2 mm between
   pads, and the gap is 0.84 mm. Every net on a header must leave down the strip *outside*
   the header, in pin order, so plan by **lane order**. Outermost is the top pin; at the bottom,
   outer lanes peel down and inner lanes peel up. Anything that needs two nets separated by
   another net's lane is a forced crossing. On esp32node, I2C on IO21 + IO22 trapped TXD0/RXD0
   between them. Mads moved SDA to IO23 (adjacent to IO22 on the header). Check your pin
   choices against the header order *before* committing the schematic. `place_floor.py` at
   0.2/0.3 missed this, because at that rule tracks fit between header pins.
8. **USB-C on one layer:** the two D+ and two D- pads alternate (D+ D- D+ D- at 0.5 mm pitch).
   One pair has to join under the connector body. The other joins in front, looping round the
   first pair's inner pad. VBUS left/right also join under the body, behind that link, clear of
   the NPTH pegs by at least 0.1 mm. The CC and VBUS pads are too fine for 0.5/0.35, so the
   escape must be hand-drawn in 0.2/0.3 mm tracks (`j1_escape()` in esp32node's `place_pcb.py`)
   until every exit is at least 0.9 mm from its neighbour. Remember the flip mirrors pad order:
   CC2 lands on the left.
9. **CH340C (SOIC) under-body trick:** rotate it so UD+/UD- face the USB-C, and reach the UART
   pads at the far end from *under* the body. There are 3.85 mm between the pad rows, which
   holds three 0.5 mm tracks at 0.35.
10. **Power is the hard part on one layer.** With the headers as walls, +3V3 is needed in every
    region (both header strips, the pocket under the module, both bottom corners). On esp32node
    FreeRouting left +3V3 in 8 pieces with only a GND pour. Plan +3V3/+5V pour regions or
    accept a few jumper wires from the start, and ask Mads which.
11. The pocket between the header walls, below the module, is where the CH340 and auto-reset
    belong. The lower header fanout diagonals eat its corners, so give the headers about
    24 mm from the module centre, not 20.

## 4. Tooling on this Linux machine (the skills assume Windows)

- **pcbnew + Python 3.14:** every `for x in board.GetTracks()/Drawings()/Zones()` dies with
  `'SwigPyIterator' object has no attribute 'next'`. Use the shim
  `~/Projects/esp32-node/esp32node/tools/pyshim/sitecustomize.py`:
  `PYTHONPATH=<that dir> python3 ...`. Copy it into your project.
- The KiCad-Autoplace engine is at `~/Projects/KiCad-Autoplace`, so
  `export KICAD_AUTOPLACE=/home/mads/Projects/KiCad-Autoplace/plugin/plugins`.
  Without it, `place_floor.py --netlist` "resolves" 0 footprints and happily prints a
  meaningless "floor 0". Always check the pads/nets count on its first line.
- `place_floor.py` at 0.35/0.5 on a 32-part ESP32 board did **not finish in 3000 s**;
  `--budget` doesn't bound it. At 0.2/0.3 it takes about 40 s.
- `pcb_build.py` (kicad-laser-pcb) and the kicad-schematic test harness hardcode Windows
  paths. esp32node's `bootstrap_pcb.py` is the Linux-safe replacement. For the tests:
  `KICAD_CLI=$(which kicad-cli) IDIOM_OUT=<scratch> python3 tests/run_all.py`.
- The DSL placement compiler (`place_dsl.py`) shells out to KiCad's Windows python.exe
  and has no model of flipped B.Cu parts. esp32node placed with a relational pcbnew script
  instead (`place_pcb.py`, every coordinate derived from pad geometry).
- **FreeRouting:**
  - 1.9.0 (what the skills and the old handoff prescribe) cannot run headless: it throws
    `HeadlessException`. Launched windowed from an agent session, it idled at 0% CPU for
    20 minutes after logging `layer name 'B.Cu' not found`.
  - Use the installed `~/.freerouting/freerouting-2.4.1.jar` with `-Djava.awt.headless=true`.
    It takes about a minute per rung.
  - `place_route.py` now takes `FREEROUTING_JAVA_OPTS="-Djava.awt.headless=true"`, finds
    `kicad-cli` on PATH, and with `PLACE_ROUTE_KEEP_LOCKED=1` keeps `(locked yes)` segments
    through its strip step. Without that flag it deletes all pre-routed copper before export.
  - FreeRouting 2.4.1 still crossed a locked stub once: DRC `shorting_items` caught it. Always
    run DRC on the routed board; the driver's own report doesn't show shorts.
  - It also necks tracks down to 0.375 mm. Enforce 0.5 mm with a `track_width` DRU rule.
- `pcbnew.SaveBoard` / `LoadBoard` from scripts can leave a stale `~<project>.kicad_pro.lck`.
  Check `pgrep` for a real KiCad before deleting it.

## 5. Gates (and what they miss)

- **Schematic:** `sch_score.py`, `kicad-cli sch erc --severity-all`, `sch_verify.py` against the
  previous revision, and a PDF you actually look at.
- **PCB:** `place_score.py`, `place_route.py check` (union-find plus DRC), `kicad-cli pcb drc
  --severity-all` **with the project's `.kicad_pro` and `.kicad_dru` beside the board**, and
  `place_view.py`.
- None of these check the circuit. Read the netlist back and trace the power path by hand.
  That's how the CH340 5 V bug was found; ERC had passed with 0 violations.
