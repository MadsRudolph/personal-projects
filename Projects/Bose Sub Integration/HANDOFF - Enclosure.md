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
status: Not started; PCB rev B is at the mill
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

## Related

- [[HANDOFF - KiCad Schematic]] — the board, rev B
- [[HANDOFF - Sub Crossover Bring-up]] — rotary switch lug map, Gate 8 noise
- [[Design - Sub Crossover Board]] — why the circuit is what it is
- [[Results - Sub Crossover Bring-up]] — measured performance
