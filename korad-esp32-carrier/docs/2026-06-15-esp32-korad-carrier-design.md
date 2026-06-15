# ESP32-WROOM-32 carrier for KORAD KD3005D remote control — design

Date: 2026-06-15

## REVISION — fiber-laser dev-board version (supersedes the bare-WROOM design below)

The bare ESP32-WROOM-32 is surface-mount (1.27 mm castellated) and **cannot be made on the
DTU 62768 single-sided fiber-laser THT process** (0.8 mm clearance) — proven by running it
through the pipeline (74 DRC violations, all U1). Redesigned to socket a **30-pin LoLin/DOIT
NodeMCU v3 (ESP8266)** — the module the user actually has, and the proven profi-max platform
for this KORAD mod — on two 1x15 header rows (**~28.4 mm** apart). The KORAD J9 UART goes
through the BS170 level shifter to the NodeMCU **hardware RX/TX (GPIO3/GPIO1)**. The dev board
brings its own USB flashing + 3.3 V regulator, so the LM317 power section, boot/reset buttons,
and pogo header were dropped. Kept: J9 tap (J1), BS170 level shifter (Q1/Q2 + R4–R7),
power-select (P1), bulk/decoupling (C4/C2). All through-hole. Firmware target: ESPHome
`esp8266` (or Arduino), 9600 8N1 to the KORAD.

Built with the `kicad-laser-pcb` skill: 104x104 jig outline, two-stage Freerouting (1.9.0),
track 1.0 / clearance 0.8. **Result: 0 unconnected pads, 0 real DRC errors** (2 benign
`track_dangling` micro-stubs). Production exported to `production/`: `*.dxf` (bottom copper —
mirror in xTool), `*_top_cu.dxf` (bridge plan), silk DXF, and `gerbers/` + drill. **Cut the
copper blank to 109x109 mm.**

Open items to verify on the bench:
- **NodeMCU row spacing = 28.4 mm** (from measured 29 mm pin outer-edge-to-outer-edge minus
  ~0.6 mm pin). Re-measure to confirm; change J4's x in the `korad-esp32-carrier` PLACE entry
  (`pcb_build.py`) if it differs.
- **Verify the 5 socket pins against the board silk** before etching: left pin14=GND,
  pin15=VIN; right pin12=RX(GPIO3), pin13=TX(GPIO1), pin15=3V3. One-line remap if off.
- J9 voltage (3.3/5 V) sets P1: J9_VDD → NodeMCU 3V3 pin (3.3 V) or VIN (5 V).
- BS170 legs must be formed to 2.54 mm (TO-92_Inline_Wide) to clear 0.8 mm.

Skill issues found + fixed (recommend committing to the team repo, developer-voice):
- `route_board.ps1:61` and `export_production.ps1:27` used `$b:` → parse error on any
  PowerShell; fixed to `${b}:` (patched team-repo copies too).
- TO-92 (BS170) needs the `_Wide` 2.54 mm footprint for 0.8 mm clearance — worth a line in
  `footprints.md` next to the TO-126 note.

---

Status (superseded bare-WROOM design): schematic built (ERC-clean, netlist-verified) + PCB built (footprints placed, fully
netted, Edge.Cuts outline, DRC-clean apart from the unrouted ratsnest + cosmetic silk). Copper
routing remains (do it in the KiCad GUI or freerouting).
Build:
- `kicad/build_schematic.py` -> `korad-esp32-carrier.kicad_sch` (+ `.kicad_pro`, `.pdf`/`.svg`).
  ERC: 0 errors, 3 harmless lib_symbol_mismatch warnings.
- `kicad/build_pcb.py` -> `korad-esp32-carrier.kicad_pcb` (uses the Multimeter PCB as a
  layer/setup template; nets parsed from the schematic netlist). DRC: 0 clearance/courtyard/
  drill errors; 58 unconnected = the ratsnest (routing pending); 29 cosmetic silk warnings.
Both run with `PYTHONUTF8=1`. Min-hole rule relaxed to 0.2 mm in `.kicad_pro` for the ESP
thermal vias.

## Goal

A small carrier PCB for a bare ESP32-WROOM-32 module that taps the KORAD KD3005D
internal **J9 UART** and bridges it to WiFi (Home Assistant / network), so the supply can
be controlled remotely. The ESP lives *inside* the supply's floating control domain and
uses WiFi as the isolation barrier — no optocouplers, no USB isolator.

See also: `../../korad-9pin-investigation.md` (the reverse-engineering log this builds on).

## Background facts this design depends on (from the investigation log)

- J9 is a 4-pin header: **VSS / RX / TX / VDD** (pins 1 & 4 = supply rail, middle = RX/TX).
  Exact pin order to be confirmed with a meter on the actual board.
- **J9 logic level / VDD = 3.3 V or 5 V, unit-dependent — MEASURE pins 1↔4 first.**
- The J9 domain **rides on the output voltage** (VSS sits ~+Vout above the negative
  terminal; common-mode up to 30 V). Therefore any wired host link must be isolated; WiFi
  sidesteps it because the ESP shares VSS and floats with the domain.
- Protocol: custom ASCII, **9600 8N1**, no terminator, no checksum, ~100–200 ms pacing.
  (115200 is a firmware-side fallback, not a hardware requirement.)

## Module decision

- **Target: ESP32-WROOM-32** (bare modules the user already has).
- Symbol/footprint: stock KiCad 9 `RF_Module:ESP32-WROOM-32` (no vendor lib needed).
- The downloaded `ESP32-S3-WROOM-1-N16R2` library is **not used** (different chip).

## Circuit design

### Power (supports both J9 voltages) — sourced from the component shop
- J9 `VDD` → `JP1` (1×3 header + jumper shunt) → `3V3` rail.
  - JP1 = direct (center–A): for 3.3 V units; regulator unused, WROOM runs straight off J9.
  - JP1 = via-regulator (center–B): J9 VDD → `U2 LM317T` (set ~3.27 V) → 3V3, for 5 V units.
- `U2 LM317T` set resistors: `R8 243R` (Vout↔ADJ) + `R9 392R` (ADJ↔GND) → 1.25·(1+392/243) ≈ 3.27 V.
- Decoupling: `C5 100nF` at LM317 in, `C6 10µF` at LM317 out; `C2 100nF` + `C3 10µF` at the
  WROOM 3V3 pin; `C4 1000µF` bulk reservoir on 3V3 for WiFi bursts (~500 mA peaks).
- Optional `D1 1N5817` Schottky in series on J9 VDD for reverse-polarity protection.
- All GND pins + the module center thermal pad → GND.
- ⚠ NO 3.3 V LDO exists in the shop, so the 5 V case uses LM317T. Its dropout from 5 V is
  marginal (~1.7 V headroom): the LM317 supplies the ~80–160 mA average; the 1000µF bulk cap
  carries the brief WiFi TX bursts. If it browns out, substitute an AMS1117-3.3 / MCP1700-3.3
  (cheap, not in shop). If J9 measures 3.3 V, JP1 bypasses all of this — the simplest case.
- LM317 in TO-220; dissipation < 0.3 W average, no heatsink needed (shop has one if wanted).

### Boot / strapping
- `EN`: `R1 10k` pull-up to 3V3 + `C1 1µF` to GND (power-on-reset delay); `SW1` to GND (reset).
- `IO0`: `R2 10k` pull-up to 3V3; `SW2` to GND (boot); also routed to pogo flash pad.
- `IO2`: `R3 10k` pull-down to GND (must not be high at boot).
- `IO12`: left floating (internal pulldown selects 3.3 V flash). `IO15`: default (no part).

### UART to KORAD (with level shifter)
- Level shifter `Q1, Q2` (2× BS170, the shop's logic-level TO-92 N-MOSFET; BSS138-style
  circuit) + `R4–R7 10k` pull-ups. HV side = J9 VDD, LV side = 3V3. Transparent when both
  sides are 3.3 V, so no bypass jumper needed. (BS170 typ Vgs(th) ~2 V works for 3.3/5 V
  shifting; a worst-case high-threshold unit is the only risk — swap that FET if so.)
- Crossover: ESP `IO17 (U2TXD)` → shifter → `J9.RX`; `J9.TX` → shifter → ESP `IO16 (U2RXD)`.
- Firmware baud 9600 8N1 (UART2 on IO16/IO17; UART0 reserved for flashing/logs).

### Flashing (pogo + buttons), done OFF the supply
- `J2` 1×6 pogo header/pads: `3V3, GND, EN, IO0, TXD0 (IO1), RXD0 (IO3)`.
- Pogo USB-TTL supplies 3V3 during flashing; with SW1/SW2 for manual boot-mode entry.
- **Never connect the pogo-USB and J9 simultaneously** (recreates the earth↔floating bridge
  + power conflict). Flash on the bench, then install powered from J9, comms over WiFi only.

### Mechanical / safety
- WROOM PCB-antenna end overhangs the board edge with a copper keep-out.
- Silkscreen warning: "Floats at +Vout — insulate. Never connect pogo-USB and J9 together."
- The board sits at up to Vout inside the case; mount insulated.

## Bill of materials (all from dtu_component_shop.csv except U1 and the noted LDO fallback)

| Ref | Shop part | Notes |
|---|---|---|
| U1 | ESP32-WROOM-32 | user's own bare module; `RF_Module:ESP32-WROOM-32` |
| U2 | LM317T (IC, Voltage Regulator) | adjustable, set to ~3.27 V; only used for 5 V J9 units |
| Q1, Q2 | BS170 (Transistor, N-MOSFET) | UART level shifter |
| JP1 | 1×3 male header + Jumper shunt | power select (direct / via-LM317) |
| J1 | 1×4 male header (or Molex 4-Pin) | to J9 on the PSU |
| J2 | 1×6 male header / pogo pads | pogo flash |
| SW1, SW2 | Pushbutton (Hardware, Switch) | EN (reset), IO0 (boot) |
| R1–R3 | 10k (10K0) | EN↑, IO0↑, IO2↓ |
| R4–R7 | 10k (10K0) | level-shifter pull-ups |
| R8, R9 | 243R, 392R | LM317 set divider (→3.27 V) |
| C1 | 1µF Electrolytic | EN POR |
| C2 | 100nF Ceramic | WROOM 3V3 decoupling |
| C3 | 10µF Electrolytic | WROOM 3V3 decoupling |
| C4 | 1000µF Electrolytic | bulk reservoir for WiFi bursts |
| C5 | 100nF Ceramic | LM317 input |
| C6 | 10µF Electrolytic | LM317 output |
| D1 (opt) | 1N5817 (Diode, Schottky) | reverse-polarity guard on J9 VDD |

Substitution note: the shop has **no 3.3 V LDO**; U2 uses the adjustable LM317T as a
through-hole stand-in (see Power section caveat). If J9 is 3.3 V, U2/R8/R9/C5/C6 are unpopulated.

## Deliverable & toolchain

- KiCad 9 project under `korad-esp32-carrier/kicad/`: `.kicad_pro`, `.kicad_sch`, `.kicad_pcb`.
- Generated with Python + **`kiutils`** (pip install), symbols/footprints from stock KiCad 9 libs.
- Footprints are **through-hole** to match the shop (resistors axial, caps radial/disc,
  LM317 TO-220, BS170 TO-92, pin headers 2.54 mm, pushbuttons THT) — except U1, which is the
  ESP32-WROOM-32 SMD module footprint (the only surface-mount part, soldered by its castellations).
- Validated with **`kicad-cli`** (`C:\Program Files\KiCad\9.0\bin`): ERC on the schematic,
  DRC on the board, and export of a schematic PDF/SVG for visual review.
- Scope realism:
  - **Schematic**: complete and fully wired — this is the primary "how to wire it" reference.
  - **PCB**: footprints placed, all nets assigned (ratsnest), board outline + antenna keep-out,
    design rules set, **best-effort straight-track routing**. Final routing/DRC cleanup is
    expected to be finished in the KiCad GUI (script-generated copper is the fragile part).

## Out of scope (tracked, not built here)

- ESPHome firmware (UART + KORAD command/sensor mapping, baud 9600). Documented separately.
- Enclosure/mounting hardware.

## Open items to confirm at the bench

- J9 exact pin order (signal set known: VSS/RX/TX/VDD).
- J9 voltage (3.3 V vs 5 V) → sets JP1 position and confirms shifter HV rail.
- Whether the specific KD3005D unit's firmware actually responds (the go/no-go poll).
