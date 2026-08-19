# Handoff — build the Class D amplifier schematic

You are picking up a project that has been specified but not drawn. Everything
you need is in this folder. Read `docs/DESIGN-BRIEF.md` first, in full — it is
the spec, and this document is only the working instructions.

## What to build

A **mono Class D audio amplifier**, +12 V single rail, BTL full bridge into
4 Ω, ~12 W, fixed ~250 kHz carrier. One board, built twice for stereo. Every
part comes from the DTU component shop and has already been verified present.

Deliverable for this session: **a complete, readable KiCad 10 schematic** in a
new project in this repository. Not a PCB layout — that is a later job.

## Where it goes

Follow the convention already used by `Projects/Bose Sub Integration`:

```
Projects/Class D Amplifier/
  docs/DESIGN-BRIEF.md          the spec (exists)
  docs/HANDOFF.md               this file
  hardware/kicad/
    classd.kicad_pro            create
    classd.kicad_sch            create — the deliverable
    tools/classd_layout.py      the layout script that generates the sheet
```

The repo root is `C:\Users\Mads2\Documents\Projects`. It is a git repo; commit
as you go.

## Skills

- **`kicad-schematic`** — this is the one you will live in. Read its `SKILL.md`
  and `references/dsl.md` before writing anything. It has the drawing DSL
  (`schdraw.py`), an idiom library (`idioms.py`, 25 blocks, all fixture-tested),
  a readability scorer (`sch_score.py`) and a netlist verifier.
- **`kicad-laser-pcb`** — only for the later PCB stage. **Its routing flow does
  not apply to this board**: it treats `F.Cu` as wire bridges for
  single-sided crossings, and this board is two-layer with a ground pour on
  `F.Cu`. Do not reuse its two-stage router without rethinking it.

## Order of work

1. **Datasheet checks first.** `DESIGN-BRIEF.md` has a 25-item checklist with 9
   marked *critical*. The critical ones are drawn components, not just numbers
   — particularly the HIP4082 dead-time resistors and whether the bootstrap
   diodes are internal. **You cannot draw the gate-drive block without these.**
   Fill in the answers table in the brief and commit it.
2. **Confirm the derived values** the brief states: output filter L and C,
   triangle oscillator R and C for 250 kHz, gain of the input stage, the
   virtual-ground divider. Show the arithmetic. If any disagrees with the
   brief, say so and fix the brief rather than silently drawing something else.
3. **Create the project.** See "Creating the project files" below — the order
   matters.
4. **Write `tools/classd_layout.py`** using `schdraw`. Draw it in the eight
   blocks the brief lists, three bands, signal left to right.
5. **Verify** — the gates below.
6. **Commit**, and write a short `docs/BUILD-NOTES.md` recording anything you
   discovered that the brief got wrong.

## Creating the project files — order matters

A `.kicad_pro` records the root sheet's uuid in its `sheets` entry, and every
symbol in the schematic is keyed to that uuid via
`(instances (project ... (path "/<uuid>")))`. **If they disagree, KiCad resolves
the symbols against a path with no instance data, drops them out of
connectivity, and Eeschema reports dozens of unconnected pins — while
`kicad-cli` reads the netlist as perfect.** That failure cost a full morning on
the previous board.

So:

1. Pick one uuid. Generate it once and reuse it.
2. Emit the schematic with `Sheet(..., uuid="<that uuid>")`.
3. Write `classd.kicad_pro` with `"sheets": [["<that uuid>", "classd"]]`.
   Copy the rest of the structure from
   `Projects/Bose Sub Integration/hardware/kicad/subxo.kicad_pro` and change
   the name — do not invent a project file from scratch.
4. Confirm afterwards that **all symbols share exactly one instance path**.
   `sch_score.py`'s `sheet_paths` check does this; it must report 1.

## The gates — nothing is done until all of these pass

```bash
py -3.13 <skill>/scripts/sch_score.py classd.kicad_sch
kicad-cli sch erc --severity-all -o erc.txt classd.kicad_sch
kicad-cli sch export netlist --format kicadsexpr -o net.txt classd.kicad_sch
kicad-cli sch export pdf -o classd.pdf classd.kicad_sch
```

- **Scorer must PASS all checks.** The one that matters most is `stitching` —
  the fraction of pins whose only connection is a stub ending in a label. Under
  20 %. If it is high you have drawn a netlist, not a schematic.
- **ERC with `--severity-all`.** Never the narrower severity flags: run
  headless they ignore the project's settings and under-report badly. Only
  `lib_symbol_mismatch` is benign.
- **Read the netlist back and check the topology by hand.** This is the step
  people skip. The gates prove the drawing matches *the netlist you specified*;
  they cannot tell you the netlist is the circuit you meant. On the previous
  board a non-inverting amp was drawn with the output, both feedback resistor
  tops and the `-` input on one node — shorting the feedback resistor. It
  rendered beautifully and passed everything. For this board, explicitly
  verify: the bridge legs are complementary, no node ties a high-side gate to a
  low-side gate, and the two comparator outputs are genuinely opposite.
- **Export the PDF and look at it.** Non-negotiable. No metric catches
  overlapping text or a block title sitting on a capacitor. Expect two visual
  passes after the numbers go green.

## Landmines — all of these have actually bitten

1. **Never run `kicad-cli sch upgrade`.** It rewrites every symbol onto its own
   instance path and Eeschema then connects nothing. It looks like a
   canonicalisation step; it is a corruption step.
2. **Close KiCad before writing any file.** Eeschema does not reload a
   `.kicad_sch` that changed underneath it, and saving from a stale session
   overwrites your file *and* drops junctions on the way. If a GUI report
   disagrees with `kicad-cli`, suspect a stale session first: check for a
   `kicad` process and a `~<project>.kicad_pro.lck` file.
3. **A wire must END at a pin, never run through it.** A wire passing over a
   pin with a junction dot nets up fine in `kicad-cli`, then Eeschema deletes
   the junction as redundant on save and the pin comes adrift. `schdraw.emit()`
   splits wires at pins for this reason; the scorer's `junction_tap` check
   enforces it.
4. **A label one grid step off the wire connects to nothing** and renders
   identically. `sh.check()` errors on it.
5. **Approach multi-pin headers horizontally**, one run per pin. A vertical run
   down the pin column shorts every pin it passes.
6. **`Device:R` and `Device:C` are vertical at `rot=0`**, horizontal at 90.
7. **Multi-unit parts**: a TL074 is 5 units — four amp sections plus a power
   section (pins 4/11) placed as its own symbol. Call `idioms.opamp_supply()`
   once per package or the op-amps have no supply pins.

## Unresolved — read this before you spend hours

On the previous board, generated schematics repeatedly passed **every**
headless check — netlist correct, ERC clean, every pin on a wire endpoint — and
still showed ~23 unconnected pins when opened in Eeschema. Three real bugs were
found and fixed along the way (uuid mismatch, `sch upgrade`, stale symbols) and
none fully explained it. It was never resolved.

If it happens here, **do not start theorising about the file**. Run this test
first, because it splits the problem in one step:

> Open the `.kicad_sch` **standalone, with no `.kicad_pro` beside it**, and run
> ERC. Then open it **inside the project** and run ERC again.

- Clean standalone, broken in-project → the project/uuid linkage, not the
  drawing.
- Broken both ways → the drawing; bisect it.
- Clean both ways → a stale KiCad session.

And take seriously that `kicad-cli` is blind to this class of fault. When the
GUI and the CLI disagree about identical bytes, the GUI is the authority,
because it is the thing that actually renders the sheet.

## Using sub-agents

Good candidates, genuinely independent:

- **One agent per datasheet** (HIP4082, IRF540, LM311, TL074, 4049) filling in
  its slice of the answers table. These are pure research and parallelise
  cleanly. Give each the exact questions from the checklist.
- **One agent to re-verify the BOM** against
  `components-inventory/dtu_component_shop(1).csv` — confirm every part exists
  and flag anything whose rating is marginal, the way the inductor issue was
  caught.
- **One agent to check the arithmetic** independently: filter f<sub>c</sub> and
  Q, oscillator frequency, power and current, dissipation per FET.
- **One agent to review the finished schematic** against the brief, block by
  block, reading the exported netlist rather than the drawing.

**Draw the schematic yourself, in the main session.** Layout is one coherent
act of judgement — which block goes where, how the feedback loop is shaped —
and splitting it across agents produces a sheet that reads like it was drawn by
a committee. The DSL does the geometry; the composition is yours.

**Verify what agents report.** On the previous project an agent reported all 22
idiom fixtures passing, which was true, and every idiom still collided on
refdes when two were placed on one sheet, because each fixture built a single
block on its own sheet. The claim was accurate and the conclusion was wrong.

## Conventions

- Commit messages: describe the change and why, in plain prose. **Do not
  mention Claude, AI, or co-authorship** anywhere in commits or PR text.
- Keep the layout script in `tools/` so the sheet is reproducible, and commit
  it alongside the schematic.
- Python is `py -3.13`; `sexpdata` is available, `yaml` is not.
- KiCad 10 lives at `C:\Program Files\KiCad\10.0`. Versions 8 and 9 are also
  installed — always use the 10.0 binaries explicitly.

## Definition of done

- [ ] Datasheet answers table filled in and committed
- [ ] Derived values confirmed with arithmetic shown
- [ ] `classd.kicad_pro` and `classd.kicad_sch` exist, uuid consistent, one
      instance path
- [ ] `sch_score.py` passes every check
- [ ] `kicad-cli sch erc --severity-all` clean apart from `lib_symbol_mismatch`
- [ ] Netlist read back and topology verified by hand against the brief
- [ ] PDF exported and visually reviewed
- [ ] Opened in Eeschema by the user and confirmed
- [ ] `tools/classd_layout.py` regenerates the sheet
- [ ] `docs/BUILD-NOTES.md` records what the brief got wrong
