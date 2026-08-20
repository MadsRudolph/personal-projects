# SRM-20 via blank

A fab-made two-layer blank, sized to the Roland SRM-20's envelope, that you mill
your own boards out of. Solid copper on both faces, tied together by plated
1.0 mm holes.

`F.Cu` is the ground plane — you never route it, you only let KiCad's zone fill
relieve it. `B.Cu` is the layer the mill isolates into traces. Components mount on
top and solder on the bottom, exactly as on a single-sided milled board.

The point is that ground stops being work. A ground pin dropped into a hole is tied
to the plane through the plated barrel, with no top-side access needed — which is
the case that hurts today (`Class D Amplifier/docs/DESIGN-BRIEF.md:176`: you cannot
reach the top pad of anything with a body over it).

## Where the holes go

Not in a uniform lattice. A lattice puts an obstacle every pitch across the whole
board, including everywhere you will never need one, and the board ends up looking
and behaving like perfboard. Opulo's [viagrid](https://github.com/opulo-inc/viagrid)
does better: a dense ground fence in the border where it is never in the way, plus
a few tight clusters, leaving the field clear. These blanks are that idea at
190 × 140 mm.

| Pattern | Holes | Footprints | Layout |
|---|---|---|---|
| **Islands** (default) | 435 | 39 | 5.08 mm perimeter fence + 7 × 5 clusters of 3 × 3 @ 2.54 mm, on a 25.4 mm lattice |
| Blobs | 171 | 7 | 5.08 mm perimeter fence + 3 viagrid-style diamonds |

`Blobs` is viagrid's own arrangement scaled up, and it is kept mostly as a
reference: their 90 × 55 board is covered by three clusters, but at 190 × 140 the
same three leave most of the board more than 40 mm from a via. `Islands` keeps the
clear-field principle but spaces the clusters so nowhere is more than about 18 mm
from ground. Between clusters the channel is ~17 mm wide — around nine 1.0 mm
tracks — so routing is essentially unobstructed.

**A cluster is one ground terminal, not nine routable vias.** At 2.54 mm internal
pitch you cannot mill an isolation ring around a single hole: the ring would need
1.55 mm of radius and its neighbour's copper starts at 1.84 mm, leaving 0.29 mm of
web — well under the 0.8 mm end mill. So a cluster is all-or-nothing ground. Route
a block's ground to the cluster edge and stop. That is exactly the "group grounds
locally, then stitch once per group" rule from the Class D brief. Only ground pins
land in cluster holes; DRC enforces the rest, because every hole is a GND pad.

If you would rather each hole be individually usable — de-groundable by milling its
own relief ring, so it can serve as a plated hole for any net — set
`CLUSTER_PITCH = 3.81`. That leaves a 1.56 mm web between a ring and its neighbour,
which the mill can enter. Clusters grow from 5.08 to 7.62 mm across.

## The blank

| | |
|---|---|
| Size | 190 × 140 mm |
| Copper | 1 oz (35 µm), solid both faces, pulled back 0.5 mm from the routed edge |
| Finished hole | 1.0 mm, plated, tied to the `F.Cu` plane |
| Fence inset | 5 mm from the edge |
| Surface finish | OSP |
| Solder mask | none, both sides |
| Silkscreen | 10 mm ruler in the border, origin at the blank centre |

190 × 140 is the largest round size that still leaves the spindle ~6 mm of reach
past every edge of the 203.2 × 152.4 mm stroke, so the blank never has to be
positioned precisely on the bed. Every pattern is centred and symmetric, so the
blank has no right way round — rotate it 180° and every hole still lands.

Hold it down with screws through fence holes in the border, and take datums by
probing two diagonal holes. The blank is its own fixture.

## The KiCad plugin

`Tools → External Plugins → Import via blank…` in the PCB editor. Three choices:

| Choice | What it does |
|---|---|
| **islands** | The default blank: hole set + F.Cu ground plane, clipped to your outline and locked |
| **blobs** | Same, with viagrid's own sparse arrangement |
| **outlines** | Only the build-space rectangles — no holes, no plane |

`outlines` is for a board whose placement is already done and which does not
want holes, but still needs to show how far it can grow and still fit the
machine. It touches nothing electrical: on the Class D board it leaves DRC at
exactly the untouched 54 violations / 103 unconnected. It is also the one choice
that does **not** need an Edge.Cuts outline — with none, it centres on the placed
parts, which is when "how big can this get?" is most worth asking. If the board
is already too big for the blank it says by how much rather than refusing.

Ctrl+Z undoes any of them; running again replaces the previous import rather
than stacking a second copy.

Install by copying `plugin/plugins/` into KiCad's plugin directory and
restarting:

```bash
cp -r "plugin/plugins/." "$APPDATA/kicad/10.0/scripting/plugins/via_blank/"
```

**Do not use copy/paste to move the blank between boards.** pcbnew's copy obeys
the Selection Filter, which skips locked items — and the blank is locked
precisely so Autoplace will not move it — so a select-all brings the zone across
and silently leaves every footprint behind. `File → Append Board…` does work,
but drags the blank's own 190 × 140 outline in with it.

Only instances that fall entirely inside your outline are placed. That one rule
does the right thing at both sizes: mill the full blank and you get the border
fence too; mill a smaller board out of one and the fence — which sits at the
blank's edge and gets cut away — drops out by itself, leaving the clusters. The
fence's real job is hold-down screws and datum probing on the blank.

`tools/apply_blank.py <board.kicad_pcb>` is the same operation from the command
line, for when the editor is closed.

### The build-space envelope

Every import also draws two reference rectangles on **User.Drawings**, centred
on your board, so you can see how far the outline could grow:

| Rectangle | Meaning |
|---|---|
| `via blank 190 x 140` | the stock edge — no board exists past this |
| `SRM-20 stroke 203.2 x 152.4` | how far the spindle centre reaches; only the binding limit when milling bare stock rather than a blank |

They are not Edge.Cuts on purpose: the outline is the placement boundary and
goes to the fab, and these are advisory. They are not a footprint either — one
spanning the machine envelope is exactly the giant bounding box that makes
`push_apart` shove every component into the border. They are plain graphics in
a named group (`via_blank_envelope`), which the placement engine never reads and
a re-import finds and replaces rather than stacking. Verified: they add nothing
to DRC.

## Using the template

`template/ViaBlank_Islands.kicad_pcb` is a ready board: outline, locked hole set,
`F.Cu` ground plane, and the `cnc` fabrication profile (0.85 mm clearance,
1.0 mm track). Copy it to a new project and start placing.

To drop the hole set into a board you already have, add `lib/via_blank.pretty` to
your footprint library table, place the footprint at the board centre, and assign
`GND` to any one of its pads — they all share pad number 1, so they take the net
together. Then lock it.

Regenerate after changing a parameter in `tools/make_blank.py`:

```bash
"C:/Program Files/KiCad/10.0/bin/python.exe" tools/make_blank.py
```

## You never draw a relief ring

Filling the `F.Cu` zone produces the antipad around every non-GND hole
automatically, so the `F.Cu` gerber *is* the top-side isolation toolpath. Every
gap the fill leaves is a cut the end mill has to make, which sets two rules the
import enforces on every GND zone it finds, new or pre-existing:

- **Clearance and minimum width at or above 0.8 mm.** KiCad's 0.5 mm defaults
  are narrower than the tool, and a gap the tool cannot enter comes off the
  machine as a short.
- **Solid pad connection — no thermal relief.** On the real blank the copper
  around a hole *is* the plane, one fabricated sheet, so a relief ring is a
  fiction of modelling holes as pads. Four spokes and a ring per hole is a lot
  of cutting for a tie that wants to be solid and low-inductance anyway.

## KiCad-Autoplace

Three things about the pipeline decided how the holes are modelled. All three
were found by reading the engine, not by running it.

**Pads, not free vias.** `strip.py` removes every top-level `(via …)` block
before routing, so a free-via lattice — which is what viagrid ships — would be
deleted by the pipeline. Footprints, pads and zones survive.

**Many small footprints, not one big one.** `metrics.overlaps` (`metrics.py:118`)
counts locked components, and `legalize.push_apart` (`legalize.py:25`) shifts the
free part by the *full* overlap when the other is locked. One footprint spanning
the board therefore overlaps every component and pushes them all outward until
`_clamp` pins them against the outline. Split up, each bounding box is local:
6.48 mm for a cluster, 1.4 mm across for a fence strip. Loaded through the
engine's own model, the template reads 39 components, 39 locked, 0 free,
0 overlaps.

**Single-sided mode will destroy the ground plane.** `_flip_to_bottom`
(`routing.py:40`) moves every zone on F.Cu down to B.Cu after routing, because a
normal single-sided board wants its pour on the copper side. Here that lands the
ground plane on top of the traces and leaves F.Cu empty. Until the engine can be
told to leave plane-net zones alone, move the GND zone back to F.Cu and refill
after the run.

Copy-paste between projects needs the **Locked items** box ticked in pcbnew's
Selection Filter — the lattice is locked (which is what stops Autoplace moving
it), and locked items are skipped by a plain select-all.

## Layout

`plugin/plugins/viablank/` is the single source of truth — `geometry.py` is pure
(patterns and positions, no pcbnew) and `merge.py` is the only thing that touches
the KiCad API. The plugin, `tools/make_blank.py` and `tools/apply_blank.py` all
import it, so the pattern is defined once. Same shape as KiCad-Autoplace's
`plugin/plugins/autoplace/`.

## Status

Not ordered or cut yet.

Merging the blank into the Class D board took its DRC from 59 violations to 472
— **60 shorting_items, 96 clearance, 15 hole_to_hole**. That is the expected
result of dropping a fixed hole pattern onto a layout done without it, and it is
what re-placing is for. Two more classes are noise rather than defects and want
a `.kicad_dru` exception: `solder_mask_bridge` (the blank has no mask) and
`pth_inside_courtyard` (holes under part bodies, harmless when unused).

Still open: the milling process (hole order, the flip, datum probing), the
`.kicad_dru` exceptions, whether the re-placed board routes cleanly, and the fab
order — which wants a quote and a check that the fab will accept a maskless
board with solid pours on both sides.
