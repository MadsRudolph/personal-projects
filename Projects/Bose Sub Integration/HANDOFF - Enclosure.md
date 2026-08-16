---
title: HANDOFF - Enclosure
type: handoff
tags:
  - electronics
  - audio
  - subwoofer
  - crossover
  - enclosure
  - blender
status: Modelled in Blender; awaiting caliper confirmation before printing
started: 2026-08-16
updated: 2026-08-16
---

# HANDOFF — Enclosure for the sub crossover board

## Paste this into the new session

> I need an enclosure modelled in Blender for a small audio PCB I am
> fabricating right now. Use the Blender MCP (`mcp__blender__*`) — inspect the
> scene before you touch it, and do not destructively modify anything that is
> already there.
>
> Read `Projects/Bose Sub Integration/HANDOFF - Enclosure.md` in full first. It
> has the exact board dimensions, every connector position, and two hard
> constraints that will wreck the design if you miss them. The repo is
> `C:\Users\Mads2\personal-projects` on branch `main`.
>
> Ask me the open questions at the end before you start modelling — especially
> how it is going to be manufactured, because I have not decided.

---

## What this is

A `subxo` sub-crossover board: a mono-summing 2nd-order Sallen-Key low-pass
that lets a Bose Companion 5 bass module join a stereo hi-fi chain. It sits
between a Schiit Saga preamp and the Bose control pod. Design lives in
[[Design - Sub Crossover Board]]; the board itself in
[[HANDOFF - KiCad Schematic]].

It needs a box. The board is being milled now, so **its dimensions are fixed and
cannot be changed to suit the enclosure.**

---

## The board

| | |
|---|---|
| Outline | **101.0 × 104.0 mm** |
| Thickness | 1.6 mm FR4, single-sided |
| Copper | Bottom only. No vias, no top-side tracks |
| Components | All through-hole, all on the **top** face |
| Mounting holes | **None. Zero. See the constraint below** |

Source of truth is `hardware/kicad/subxo.kicad_pcb`. If you need a dimension I
have not given, read it from there with KiCad's Python rather than guessing:

```
"C:\Program Files\KiCad\10.0\bin\python.exe" -c "import pcbnew; b=pcbnew.LoadBoard('subxo.kicad_pcb'); ..."
```

### Connector and control positions

Coordinates are **millimetres from the top-left corner of the board outline,
X right, Y down** — KiCad's screen convention. Blender is Z-up and Y-forward, so
convert deliberately; getting this wrong mirrors the panel.

| Ref | What | X | Y | Panel |
|---|---|---|---|---|
| `J1` | IN L (screw terminal) | 26.5 | 10.9 | **rear** |
| `J2` | IN R (screw terminal) | 39.5 | 10.9 | **rear** |
| `J3` | OUT, 3.5 mm (screw terminal) | 58.3 | 10.9 | **rear** |
| `J4` | PWR IN 15 V (screw terminal) | 87.4 | 10.9 | **rear** |
| `J5` | polarity switch (off-board) | 44.8 | 92.0 | front |
| `J6` | level pot 10 kΩ (off-board) | 82.9 | 92.0 | front |
| `J7` | inverted LED feed (off-board) | 11.7 | 92.0 | front |
| `JP1` | C1 select, 6-pin header | 32.2 | 78.5 | interior |
| `JP2` | C2 select, 6-pin header | 22.0 | 57.2 | interior |
| `JP3` | ground lift, 2-pin header | 63.2 | 23.8 | interior |
| `U2` | LM7812, TO-220 vertical | 59.3 | 82.0 | interior, **tallest part** |
| `D1` | power LED, green 3 mm | 16.1 | 81.5 | see constraint |
| `D2` | inverted LED, amber 3 mm | 6.5 | 81.5 | see constraint |

**The layout is already panel-friendly.** All four external I/O terminals sit in
a row along the **Y ≈ 11 mm edge** — that is the rear panel. Both user controls
(`J5`, `J6`) sit along the **Y ≈ 92 mm edge** — that is the front panel. You did
not have to fight for that; work with it.

Note `J1`–`J4` are *screw terminals on the board*. The actual panel sockets are
separate parts wired to them (below), so the rear panel holes are for the
sockets, not for the terminals.

---

## Panel-mounted parts

| Panel | Part | Notes |
|---|---|---|
| Rear | 2 × RCA socket | L and R input from the preamp's Y-split |
| Rear | 1 × 3.5 mm jack | output to the Bose control pod |
| Rear | 1 × DC barrel jack | 15 V from a wall wart |
| Front | **2-pole 3-position rotary switch** | crossover corner: 94 / 135 / 189 Hz. Needs a knob |
| Front | 10 kΩ linear pot | level trim. Needs a knob |
| Front | 2-pole changeover toggle | polarity, normal/inverted |
| Front | 2 × 3 mm LED | green = power, amber = inverted |

The rotary switch is wired to `JP1`/`JP2` with an 8-wire loom — see
[[HANDOFF - Sub Crossover Bring-up]] for the lug map. **That loom is
noise-sensitive**: one of its wires carries node `N1` at about 3 kΩ to AC
ground, and it is the most pickup-prone conductor in the build. Keep the rotary
switch's panel position close to `JP1`/`JP2` at (32, 79) and (22, 57) so the
loom stays short. That argues for mounting it toward the **left of the front
panel**, not the right.

A metal panel or a conductive coating would help shielding. If the box is
plastic, say so in the design notes so the noise floor result (Gate 8) can be
interpreted later.

---

## Two hard constraints

> [!danger] The PCB has no mounting holes
> None were designed in, and the board is being milled right now, so none can be
> added. The enclosure has to retain a bare 101 × 104 mm rectangle by its edges.
> Options worth modelling: card guides / slots moulded into the side walls, a
> perimeter lip in the base with matching pressure pads in the lid, or corner
> clips. **Do not design anything that needs a screw through the board.**
>
> Whatever you choose, remember the copper is on the **bottom** face and is
> exposed — a milled board has no solder mask. Nothing conductive may touch it,
> and the retention scheme must not scrape it.

> [!danger] The LEDs point up, not forward
> `D1` and `D2` are board-mounted 3 mm LEDs on the top face, so they shine at
> the lid. They sit 22.5 mm behind the front panel edge, which is too far to
> simply bend the legs forward. Pick one and note the reasoning:
> - holes in the **lid** directly above (16.1, 81.5) and (6.5, 81.5)
> - light pipes from those positions to the front panel
> - de-populate `D1`/`D2` and mount panel LEDs on flying leads instead
>
> Ask the user — this is a visible design choice, not a detail.

---

## Clearances and heights

**These are estimates. Have the user confirm with calipers before you commit to
an internal height** — the board is in front of them.

| Part | Estimated height above board |
|---|---|
| `U2` LM7812, TO-220 vertical, no heatsink | ~18–19 mm — **the tallest** |
| `C10`/`C11`/`C15` 100 µF radial, D10 | ~13–16 mm |
| Film caps, 16 × 7 body standing | ~11–12 mm |
| Screw terminals, 5.08 mm | ~10 mm |
| DIP-14 socket + TL074 | ~10 mm |
| `JP1`/`JP2` headers **with Dupont sockets and loom fitted** | ~15 mm plus wire bend radius |

Budget for the loom, not just the parts. The rotary loom leaves `JP1`/`JP2`
vertically and has to turn toward the front panel — allow real bend radius above
those two headers rather than the bare header height.

The board's bottom face needs standoff from the base too, because the copper is
exposed there.

---

## What to deliver

1. A Blender model of base and lid, parametric enough that the internal height
   can be changed after the user measures.
2. Panel cut-outs positioned from the table above, not eyeballed.
3. A rendered preview of the assembly.
4. A short note in this file recording the decisions taken and any dimension
   that is still an assumption.

Model the PCB as a simple 101 × 104 × 1.6 mm slab with block stand-ins for the
tall parts, so clearances can be seen. It does not need to be a detailed board.

---

## Ask the user before modelling

1. **How is it being made?** 3D printed (FDM? what printer and bed size?),
   laser-cut sheet, or a bought project box that gets machined? This changes
   wall thickness, tolerances, fastening and draft entirely. **Do not assume.**
2. **LEDs** — lid holes, light pipes, or panel-mounted on flying leads?
3. **Board retention** — card guides, lip and pressure pads, or clips?
4. **Confirm the tall-part heights** above with calipers, especially `U2` and
   the electrolytics.
5. **Material and shielding** — plastic or metal? Affects hum pickup on the
   rotary loom.
6. Any constraint on external size or where it physically sits in the rack?

---

## Design notes — decisions taken 2026-08-16

### Files

| File | What |
|---|---|
| `hardware/enclosure/enclosure_model.py` | The model. All dimensions live in the `P` dict at the top; re-run the file in Blender to rebuild |
| `hardware/enclosure/render_and_export.py` | Renders + STL export. Run after the model script |
| `hardware/enclosure/subxo-enclosure.blend` | Saved scene |
| `hardware/enclosure/stl/` | `subxo_base.stl`, `subxo_lid.stl` — 1 unit = 1 mm, verified by reading the exported files back |
| `hardware/enclosure/pcb3d/subxo_board.glb` | The real board, exported from KiCad. The model imports this — there is no stand-in geometry anywhere in the scene |
| `hardware/enclosure/pcb3d/make_model_shim.py` | Builds the 3D-model overlay the export needs. Run before re-exporting |
| `hardware/enclosure/pcb3d/models/` | The overlay. `TerminalBlock.3dshapes/` holds the two hand-placed substitutes |
| `hardware/enclosure/renders/` | Six previews, including `06_height_stack.png` |

### The board in the model is the real KiCad export

Not blocks. Regenerate it in two steps, from `hardware/kicad/`:

```
"C:/Program Files/KiCad/10.0/bin/python.exe" ../enclosure/pcb3d/make_model_shim.py
```

```
kicad-cli pcb export glb --force --subst-models --no-dnp -D "KICAD9_3DMODEL_DIR=<abs>/hardware/enclosure/pcb3d/models" --user-origin "82.975x35.975mm" -o ../enclosure/pcb3d/subxo_board.glb subxo.kicad_pcb
```

`--user-origin` is the outline's top-left in KiCad page coordinates. With it,
the export lands at 1 unit = 1 mm with the origin already on the model's
origin and Y already negated — the only correction the script applies is
lifting it onto the standoffs.

### Why J1–J7 need a shim, and what they actually are

`J1`–`J7` resolve their model through
`${KICAD9_3DMODEL_DIR}/TerminalBlock.3dshapes/..._bornier-N_P5.08mm.step`.

**That library does not exist anywhere.** Not in KiCad 9, not in KiCad 10, and
not in the official `kicad-packages3D` on GitLab either — only the four branded
`TerminalBlock_*` libraries are published. The bornier footprints point at a
path that has never been populated in a modern library. The `bornier` STEP
files survive only in third-party mirrors of a much older library.

> [!warning] J1–J7 in the render are substitutes, not the specified part
> They are genuine Phoenix **MKDS-1,5** 2-way and 3-way 5.08 mm blocks, copied
> out of the local KiCad install and renamed to the bornier filenames. Same
> pitch, same 2-way/3-way split, **different body**.
>
> They measure **13.88 mm tall** against roughly 10 mm for a generic bornier,
> so the substitution errs ~4 mm tall — conservative, which is the safe
> direction for a clearance check. Still well under `U2` at 18.86 mm, so it
> changes nothing about the box.

Redirecting the lookup with `-D` means **`subxo.kicad_pcb` is never edited** —
the board being milled is untouched. The shim has to be a *complete* overlay
rather than just the terminal blocks, because `U2`'s TO-220 resolves through
the same variable and overriding it breaks that too. `make_model_shim.py`
handles this: it copies the referenced models out of the install and leaves
the hand-placed `TerminalBlock.3dshapes` alone.

Still genuinely absent, no model anywhere: `D1`/`D2` (custom `energy_system`
laser-pad footprints, ~6 mm) and `LK1` (wire link, flat). Neither is close to
binding.

### Part heights, measured off the real models

| Part | Measured above board | Had assumed |
|---|---|---|
| `U2` TO-220 vertical | **18.86 mm** | 19.0 — confirmed |
| Film caps (largest, FKS3/FKP3) | **15.08 mm** | 12.0 — was 3 mm optimistic |
| Electrolytics ⌀10 radial | **10.08 mm** | 16.0 — was conservative |
| Bare `1x06` header | 8.62 mm | — (loom adds to this) |
| Bare DIP-14 | 3.76 mm | 10.0 incl. socket |

**None of this changes the box.** `U2` was the one that mattered and it was
right to within 0.14 mm. The loom still sets the height at 30.6 mm internal.

> [!note] The leads in the render pass through the floor
> KiCad's THT models carry full untrimmed leads — `U2`'s reach 8.15 mm below
> the board, so at a 4 mm standoff they poke through the base. That is the
> export being literal, not a modelling error. Real trimmed leads are 1–2 mm
> and clear the standoff easily. Just do trim them: the copper is on that face
> and it is bare.

### Decisions

| Question | Decision |
|---|---|
| Manufacture | **FDM 3D print.** 2.4 mm walls / floor / lid (6 perimeters at 0.4 mm), 0.4 mm added to every panel hole, 0.3 mm lid-lip fit clearance |
| LEDs | **Holes in the lid** above `D1` and `D2`. See the caveat below |
| Retention | **Corner clips.** Rear two corners are rigid L-ledges, front two are flexing snap fingers |
| Material | **Plastic, unshielded.** Recorded here so the Gate 8 noise floor is read against an unshielded box |
| Rear panel | RCAs **opened out to 20 mm pitch** (X = 23.0 and 43.0) rather than aligned to `J1`/`J2`, which are only 13.0 mm apart |
| External size | Minimal. **117.8 × 137.8 × 35.4 mm** |
| Rotary switch | AliExpress 20 mm metal selector, M9×0.75, 18-tooth knurl shaft. **Order the 2P6T variant** |

### Verified against the board, not assumed

Read out of `hardware/kicad/subxo.kicad_pcb` with KiCad's Python. Outline is
101.0 × 104.0 mm and all 13 connector positions match this document exactly.

> [!warning] There is no copper-free rim
> The bottom-face GND pour fills **to 0.53 mm from every edge**, so any
> edge-gripping scheme lands on exposed unmasked copper. That is electrically
> harmless against plastic — it is all one net — but it caps how deep a grip
> can go, because signal copper starts shortly after:
>
> | Edge | Nearest signal copper | Net |
> |---|---|---|
> | Left | 4.22 mm | `/N1` — the noise-sensitive 3 kΩ node |
> | Right | 4.52 mm | `/POT_W` |
> | Rear | 2.52 mm | `/POT_W` |
> | Front | 2.52 mm | `/PWR_A` |
>
> Corner clips reach at most 3 mm over the board and only at the corners, so
> they stay on pour throughout. Had this been a metal box, a card guide on the
> **left** wall deeper than 4.2 mm would have shorted straight onto `N1`.

### The rotary switch, and what actually sets the box height

The switch is the AliExpress *20 mm Metal Rotary Switch Selector, M9×0.75,
18 teeth knurl shaft, solder terminals*, sold as 1P12T / 2P6T / 3P4T / 4P3T.

> [!danger] Order the 2P6T. The 1P12T will not work.
> This design needs **two poles** — one selects `C1` via `JP1`, the other
> selects `C2` via `JP2`. The 1P12T has a single pole and physically cannot do
> that. All four variants are the same single wafer, so they are the same size;
> only the pole/throw split differs.
>
> - **2P6T** — the right pick. Set its end-stop washer to **3 positions**
>   (these ship with a numbered stop washer under the mounting nut).
> - **4P3T** — also fine, and gives 3 detents natively with no stop to set.
>   Use two of the four poles.
> - **3P4T** — works, stop set to 3.
> - **1P12T** — **no.**
>
> 2 poles × 3 throws + 2 commons = the 8-wire loom this design already assumes.

**The 20 mm body is small enough that the switch no longer sets the height.**
An earlier draft of these notes assumed a chunky 28 mm body and concluded the
switch was the binding constraint. With the real part it needs only 23 mm
internal, so it drops to third place:

| Constraint | Internal height needed |
|---|---|
| Rotary switch body (⌀20 + 3) | 23.0 mm |
| `U2` / board parts | 26.6 mm |
| **`JP1`/`JP2` loom bend** | **30.6 mm ← binding** |

So the box is **30.6 mm internal**, and the thing setting it is the loom — 
exactly what this document warned about under *Clearances and heights*. `U2`
was never the real constraint.

> [!bug] This nearly went wrong silently
> The height formula originally summed only the board parts and the switch. The
> loom envelope was drawn but not included in the sum, and it only fitted
> because the assumed fat switch had forced the box tall. Dropping in the real
> 20 mm switch would have given 26.6 mm internal and pushed the loom **2 mm
> through the lid**, with no error and nothing obviously wrong in the render.
> `internal_h` is now `max()` over all three terms.

The internal stack as modelled, above the base floor:

| | z | Clear of the lid |
|---|---|---|
| Board underside | 4.0 | — |
| Board top | 5.6 | — |
| `U2` top | 24.6 | 6.0 mm |
| Rotary body top | 25.3 | 5.3 mm |
| **`JP1`/`JP2` loom bend — not drawn** | **28.6** | **2.0 mm — tightest** |

> [!important] The loom is not in the scene, but it still sizes the box
> Nothing in the model is invented geometry — the loom envelope was removed
> along with the component stand-ins. `loom_above_board` is still in the
> height sum, so the box is built around a loom you cannot see in any render.
> Do not "reclaim" that 4 mm by looking at the render and concluding there is
> spare space above the headers. There is not.

That is with an 8 mm bend allowance above the 15 mm fitted header height. If
the real loom needs more, raise `loom_above_board` and re-run — do not squeeze
it, it is the most pickup-prone wiring in the build.

Box **length** is still set by the switch: its body must clear the board
entirely, because `C1_1` stands only 1.4 mm from the front edge. Front gap is
`switch depth + 3 mm` = 19 mm.

### Two things to check when the switch arrives

- **Shaft length.** It is 6 mm × 20 mm knurled, and the front panel is only
  2.4 mm thick, so roughly 17 mm of shaft will stand proud. That is more than
  many push-on knobs will swallow — check the knob's bore depth, or plan to
  shorten the shaft.
- **The body is metal, and the box is not.** Given the unshielded-plastic
  decision, fit a solder lug under the mounting nut and run it to board GND.
  That turns the switch frame into a local shield around exactly the wiring
  that carries `N1`. It is the cheapest noise mitigation available here and is
  worth doing before the Gate 8 measurement, not after.

### Panel positions as modelled

All panel parts share a 15.5 mm centre line above the internal floor.
X is measured the same way as the table above — from the board's left edge.

| Panel | Part | X | Hole ⌀ |
|---|---|---|---|
| Rear | RCA L | 23.0 | 10.4 |
| Rear | RCA R | 43.0 | 10.4 |
| Rear | 3.5 mm jack | 58.33 | 6.4 |
| Rear | DC barrel | 87.42 | 8.4 |
| Front | Rotary | 20.0 | 9.9 (M9×0.75 bushing) |
| Front | Toggle | 44.78 | 6.4 |
| Front | Level pot | 82.90 | 7.4 |
| Lid | `D1` window | 16.09 / 81.53 | 4.0, counterbored |
| Lid | `D2` window | 6.49 / 81.53 | 4.0, counterbored |

The rotary sits hard left at X = 20, right next to `JP2` (X = 22.0) and close
to `JP1` (X = 32.2), so the noise-sensitive 8-wire loom stays as short as the
board allows. That was the point of the argument in this document, and it is
the reason the rotary is not centred.

Note the rear and front panel positions are *choices*, not board constraints —
`J1`–`J4` are screw terminals and `J5`–`J7` are headers, all wired to separate
panel parts. They are aligned to their terminals wherever the parts fit.

`J7` is unpopulated: the inverted indicator is `D2` on the board, read through
the lid.

### Assumptions still open

Everything here is a parameter in the `P` dict. Measure, edit, re-run.

| Parameter | Assumed | Why it matters |
|---|---|---|
| **`loom_above_board`** | **23.0** (15 mm header + 8 mm bend) | **Sets the box height.** The only assumption still doing real work |
| `rotary_body_depth` | 16.0 | **Sets the box length.** Not published in any listing — measure when the switch arrives |
| `rca_hole` / `jack_hole` / `dc_hole` | 10 / 6 / 8 | Panel hole diameters |
| `pot_hole` / `toggle_hole` | 7 / 6 | Bushing diameters |
| Knob diameters | 25 (rotary) / 20 (pot) | Only affects whether the knobs foul each other; currently 4.3 mm apart |

### Two caveats to be aware of

> [!caution] The lid LED windows are 19.4 mm above the LEDs
> Because the rotary switch forced the box to 31 mm internal, `D1`/`D2` sit a
> long way below the lid. A plain 4 mm hole would read dim and only close to
> straight-on. The windows are therefore counterbored from the inside — 7 mm
> down to a 1.2 mm web, then 4 mm through — to widen the acceptance cone.
> If that still reads badly, the cheap fix is a 4 mm clear acrylic rod dropped
> into each window as a light pipe. That is a retrofit, not a reprint.

> [!caution] Corner clips are the weak point in FDM
> The two front snap fingers bend about their root, and on a base printed
> floor-down that stress runs across the layer lines — the classic way a
> printed clip snaps. They are 2.5 mm thick and 9 mm wide with only a 1.4 mm
> hook, so travel is small, but print the base with a few extra walls and
> expect the clips to be the first thing to fail. The rear two corners are
> deliberately rigid ledges so only two clips ever flex.
>
> Fitting: slide the board's rear edge under the two rear ledges first, then
> press the front down until it snaps. Nothing goes through the board.

---

## Related

- [[HANDOFF - KiCad Schematic]] — the board, rev B
- [[HANDOFF - Sub Crossover Bring-up]] — rotary switch lug map, Gate 8 noise
- [[Design - Sub Crossover Board]] — why the circuit is what it is
- [[Results - Sub Crossover Bring-up]] — measured performance
