# ESP32-WROOM-32 node board — handoff

Single-sided SMD board for a CNC-milled / xTool F1 Ultra fiber-laser build.
USB-C -> CH340C USB-UART -> ESP32-WROOM-32, AMS1117-3.3 regulator, auto-reset
(DTR/RTS -> two NPN transistors -> EN/IO0), EN/BOOT buttons, full GPIO
breakout on two 16-pin headers, I2C header (4k7 pull-ups), 1-Wire header
(4k7 pull-up), power + user LED.

## Repo layout

```
esp32-node/
  esp32node/
    esp32node_sch.py     the schematic layout script (kicad-schematic DSL) -- source of truth
    esp32node.kicad_sch   emitted from the script, do not hand-edit without updating the script too
    esp32node.kicad_pro   project file (netclass carries wire_width -- do not strip it)
    esp32node.erc         last ERC report: 0 violations
    esp32node.net         exported netlist (kicadsexpr)
    esp32node.pdf / sch_preview-1.png   rendered schematic
  esp32_coupon_negative.svg / esp32_coupon_outlines.svg / preview_negative.png / make_coupon.py
    a laser test coupon (unrelated side artifact from earlier fiber-laser research --
    ESP32 pad gaps + a clearance/trace-width ladder. Keep or delete, your call.)
```

Skills to load for this work (already installed, see `.claude/skills/`):
`kicad-schematic`, `kicad-place`, `kicad-laser-pcb`.

## Status: schematic drawn, PCB not started

### Done
- Netlist-first schematic, 32 parts / 57 nets / 164 nodes, drawn as real wires per
  block, not label-soup.
- Gates run and results:
  - `sch_score.py`: **FAIL** on two checks (see below) — not yet fixed.
  - `kicad-cli sch erc --severity-all`: 0 violations.
  - `sch_verify.py`-style netlist check: **matches intended topology** (verified
    in-script against the hand-written target netlist before emit).
  - PDF exported and visually checked once.

### Known problems to fix before moving to layout
Run first: `python3 <kicad-schematic>/scripts/sch_score.py esp32node.kicad_sch`

```
FAIL  wired      53% of pins wired to another part (want >=75%)
FAIL  stitching  37% of pins are stub+label only (want <=20%)
FAIL  floating   16 pins connected to nothing (no_connect them if deliberate)
```

The GPIO breakout headers (J2/J3) and the ESP32's own GPIO stubs are drawn as
individual labeled stubs rather than block-local wires — that's most of the
stitching/wired failures and is somewhat inherent to a "breakout everything"
board, but it's above the house threshold and should be tightened (route
J2/J3 pins straight to the matching ESP32 pin with real wire runs where they
sit close on the sheet, save labels for the long hauls).

The 16 floating pins need triage: some are deliberate no-connects already
marked with `sh.nc()` in the script (CH340 pins 7/8/R232/modem-control, ESP32
pins 17/18/19/20/21/22/32, USB-C SBU1/SBU2) — check whether the scorer wants
those flagged differently, and whether any of the 16 are *not* one of those
(i.e. an actual mistake). Don't just silence the checker; find out which pins
they are (`sch_score.py` should have a verbose/list mode, or diff the ERC
`global_label_dangling` / `pin_not_connected` warnings against the netlist).

**Do not run `kicad-cli sch upgrade`** on this file — see the kicad-schematic
skill's gotchas, it corrupts multi-instance symbol paths.

### Not started: PCB layout + routing

1. Bootstrap the board from the schematic (KiCad "Update PCB from Schematic",
   tick "re-link footprints... by reference designator" since this is script-built).
2. Board is single-sided, mill/laser process: fabrication profile **cnc**
   (0.85 mm clearance / 1.0 mm track from the `kicad-laser-pcb` skill), OR
   check with the user whether they want the **laser** profile (0.8/1.0) since
   this was originally an xTool-fiber-laser conversation — ask, don't assume.
3. Run `place_floor.py --pours --corridors` **before** placing anything, per
   `kicad-place`. This board has three planes worth pouring (+5V, +3V3, GND) —
   check the pour combination it recommends.
4. Watch pad-to-pad clearance on the ESP32 footprint itself: measured min
   gap is **0.37 mm**, well under the 0.85 mm mill netclass — this needs a
   `.kicad_dru` exception (see `kicad-laser-pcb/references/footprints.md`)
   the same way headers/TO-220s do.
5. The USB-C receptacle footprint used
   (`USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal`) has SMD pads
   0.20 mm apart between different nets (VBUS/CC/D+/D-/SBU) — that is *far*
   under any mill or laser clearance. This connector cannot be isolation-milled
   or fiber-lasered as drawn. Either accept it as a manual soldering
   exception (it's a fine-pitch part regardless of process) or swap to a
   through-hole USB-C breakout board wired in with a header, which is the
   more mill-friendly option — flag this decision to the user, it changes the
   BOM.
6. Freerouting 1.9.0 jar is required for `place_route.py route` /
   `kicad-laser-pcb`'s two-stage router; it is **not** in this repo, download
   fresh: `https://github.com/freerouting/freerouting/releases/download/v1.9.0/freerouting-1.9.0.jar`.
   Do not use 2.0.1 (see skill gotchas — its version-check throws and silently
   hangs the job).
7. Gates to clear before calling the board done, from `kicad-place`:
   `place_floor.py --strict`, `place_score.py --strict`,
   `place_route.py check` (needs KiCad's own `python.exe`/pcbnew — on Linux
   that's the system `python3` since `pcbnew` is importable here, confirmed
   working), then `place_view.py` and actually look at it.
8. Export production files with `kicad-laser-pcb/scripts/export_production.ps1`
   equivalent (the skill is written for PowerShell/Windows; this machine is
   Linux, so either run the underlying kicad-cli commands directly or port the
   script — check `references/routing.md` for the raw command sequence).

### Open questions for the user (don't guess)
- CNC mill or fiber laser as the actual etch process for this board? Changes
  the clearance profile and whether the USB-C connector survives as drawn.
- Board outline / size preference — none has been chosen yet.
- Keep the GPIO breakout as bare headers, or does this need a specific
  enclosure/pinout to match an existing project?
