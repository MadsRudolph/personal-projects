# Class D audio amplifier — design brief

**Target:** one mono Class D amplifier board driving a 4 Ω speaker, built **twice**
for stereo. Every part comes from the DTU component shop
(`components-inventory/dtu_component_shop(1).csv`, 1464 lines, verified against
this design). Board process is **double-sided CNC isolation milling** with a ground pour on
the top layer, built on the existing `kicad-laser-pcb` flow. The design is kept
within the mill's rules so the same files can be sent to a fab later without
rework.

| | |
|---|---|
| Supply | single **+12 V** from a bench PSU, ~2.5 A per board |
| Output | ~**12 W** into 4 Ω (18 W theoretical, derated for modulation depth and losses) |
| Topology | **BTL full bridge**, fixed-frequency PWM |
| Switching | ~**250 kHz** |
| Channels | mono per board; build two identical boards |
| Layers | 2 — routing on B.Cu, ground pour on F.Cu, hand-wired vias |

## Why this topology

**Full bridge (BTL) rather than half bridge.** A half bridge on a single 12 V
rail needs either a split supply or a large series output capacitor, and it
suffers *supply pumping* — the rail bounces as energy is pushed back at low
frequencies. A bridge avoids both: no output DC blocking cap, no pumping, and
it doubles the voltage across the load, giving four times the power from the
same rail. It costs four MOSFETs instead of two, and the shop stocks a driver
built precisely for it.

**Fixed-frequency carrier rather than self-oscillating.** A self-oscillating
design is fewer parts, but its switching frequency moves with signal level and
supply, which makes it far harder to measure, to filter, and to explain. A
triangle carrier and a comparator give a fixed, known switching frequency you
can point an oscilloscope at.

**Two boards rather than one stereo board.** Two switching bridges sharing one
piece of copper is a serious layout problem even with a ground pour: crosstalk
through the shared return, and two independent carriers beating against each
other. Two identical mono boards remove that entirely and halve the milling
risk, at the cost of a second build. It also makes each board small enough to
be cheap if you later have them fabbed.

## Signal chain

```
line in ─ AC couple ─ level pot ─ buffer ─┬─────────────► comparator A ─► PWM_A ─┐
                                          │                   ▲                  │
                                          └─ inverter ────► comparator B ─► PWM_B┤
                                                              │                  │
                              triangle oscillator ────────────┘                  │
                                                                                 ▼
                                                                    HIP4082 gate driver
                                                                                 │
                                                              4 × IRF540 full bridge
                                                                                 │
                                                          LC filter + Zobel ─► 4 Ω
```

## Blocks

### A — Power input and rails
- `J1` 2-pole screw terminal, +12 V DC in. **Mark polarity clearly**; there is
  no reverse-polarity protection in this version (an `IRF9540` P-MOSFET ideal
  diode is the cheap upgrade if you want one).
- Bulk: `2200 µF` electrolytic close to the bridge, plus `100 nF` ceramic at
  each half-bridge supply pin. The bulk cap is what supplies the switching
  current pulses; it must be physically close to the FETs, not near the input.
- `HIP4082` VDD runs directly from +12 V (its maximum is 16 V, so no regulator
  is needed at this rail voltage).
- Analog rail for the op-amps and comparators is the same +12 V, with a **6 V
  virtual ground** — two `10 kΩ` resistors, a `100 µF` reservoir, buffered by
  one `TL074` section. This is the same idiom as the Bose sub crossover in this
  repo; reuse that block's shape.

### B — Triangle oscillator (~250 kHz)
- `TL074` section as an integrator, `LM311` as the Schmitt trigger. The LM311
  does the fast edge work; the TL074 only has to integrate a square wave, which
  at 250 kHz and ~4 Vpp needs 2 V/µs against its 13 V/µs slew rate — comfortable.
- Amplitude ~4 Vpp centred on the 6 V virtual ground.
- Frequency set by the integrator R and C. **Make the timing resistor a trimmer**
  so the carrier can be tuned on the bench.
- Do *not* try to build this from a `NE555`: its output is too asymmetric and
  jittery to use as an audio PWM carrier.

### C — Input stage
- `J2` 2-pole screw terminal, line level in (~1 Vrms).
- `1 µF` film AC coupling, then a `10 kΩ` potentiometer as level control.
- `TL074` unity buffer biased to the 6 V virtual ground → **audio+**.
- `TL074` unity inverter (two `10 kΩ`) → **audio−**.
- The differential pair is what makes the bridge work: one comparator sees
  audio+, the other audio−, so the two half-bridges swing in opposite
  directions and the load sees twice the voltage.

### D — PWM comparators
- `LM311` × 2. Non-inverting inputs take audio+ and audio−, inverting inputs
  both take the triangle.
- LM311 outputs are **open collector** — each needs a `1 kΩ` pull-up to +12 V.
- **Do not substitute an `LM339`.** It is a quad comparator and would save a
  package, but its response time is around 1.3 µs against the LM311's ~200 ns.
  At a 4 µs switching period that destroys the modulation.

### E — Gate driver
- `HIP4082IPZ`, 20-pin DIP. Full-bridge N-channel driver with bootstrap
  high-side supplies, built-in shoot-through protection and dead-time set by
  resistors on `HDEL`/`LDEL`.
- Drive `AHI`/`ALI` from PWM_A and its complement, `BHI`/`BLI` from PWM_B and
  its complement. Generate the complements with a `4049` hex inverting buffer
  — **4000-series, not 74HC**, because 74HC parts are 6 V maximum and this
  logic runs at 12 V.
- Bootstrap capacitors `100 nF` ceramic per high side.
- **Verify against the datasheet before drawing:** whether the bootstrap diodes
  are internal or need external `1N5817`s, the exact `HDEL`/`LDEL` resistor
  values for ~200 ns dead-time, and the input logic thresholds at VDD = 12 V.
  Do not guess these — dead-time errors destroy MOSFETs.

### F — Output bridge
- 4 × `IRF540` (TO-220, 100 V, 33 A, ~44 mΩ). Enormously overrated for 12 V /
  3 A, which is exactly what you want: low conduction loss and easy drive.
  `IRL530` is the logic-level alternative but is unnecessary here, since the
  HIP4082 delivers a full 12 V gate drive.
- **`22 Ω` gate resistors** in series with each gate; `10 kΩ` gate-to-source
  pulldowns so nothing floats on at power-up. 22 Ω rather than 10 Ω slows the
  switching edges, which cuts radiated noise and gate ringing noticeably. At
  12 W the extra switching loss is irrelevant — this is the cheapest EMI lever
  on the board. Drop to 10 Ω only if you later measure efficiency and care.
- Each FET on a `TO-220 Heatsink` with a mica or silicon thermal pad and an
  isolation bushing — all in the shop. At 12 W output the dissipation is
  modest, but the tabs are at switching-node potential and **must not** share
  bare metal.

### G — Output filter and load
Second-order LC per side, differential capacitor across the load:

- **L = 15 µH per side**, **C = 820 nF film differential**
- → f<sub>c</sub> ≈ 32 kHz, Q ≈ 0.66 (slightly damped Butterworth) with
  L<sub>total</sub> = 30 µH against 4 Ω
- Carrier attenuation at 250 kHz ≈ 36 dB, leaving roughly 0.4 Vpp of residual
  ripple at the speaker. That is acceptable for a bench project; raising the
  carrier improves it at the cost of switching loss and EMI.
- Zobel across the output: `10 Ω 5 W` power resistor in series with `100 nF`
  film, to keep the filter damped when the speaker's impedance rises.

**The inductors must be hand-wound.** This is the single most important
practical finding: the shop's only inductor with a stated rating is
`100 µH @ 0.66 A`, and this amplifier needs ~3 A peak. The off-the-shelf radial
chokes will saturate. Wind them on shop **toroid cores** — the same approach as
the existing `L_Toroid_Vertical_L34.5mm_W15.0mm_P28.20mm_LaserPads` footprint
in the `kicad-laser-pcb` library, which documents a hand-wound 470 µH on a shop
core. At 15 µH the turn count is far lower and the job is easy; measure each
one on an LCR meter and match the pair.

### H — Indicators and test points
- Power LED with a `4k7` series resistor.
- Test points (solder lugs, in the shop as `Loddeflig 3MM`) on: triangle,
  PWM_A, both switching nodes, and the filtered output. On a milled board these
  cost nothing and make bring-up far easier.

## Board construction — two layers on the mill

**B.Cu carries all routing. F.Cu is a ground pour and nothing else.** Keeping
every signal and power trace on the bottom lets the top stay a near-solid
plane, which is the entire reason for going double-sided.

Why it matters for *this* circuit specifically: the `LM311`s compare a 4 Vpp
triangle against audio, so **any ground bounce beneath the comparator becomes a
PWM timing error**, which is distortion. The bridge switches ~3 A in tens of
nanoseconds, roughly 60 A/µs. A return path routed the long way round on one
layer can easily be 100 nH, which turns that into ~6 V of transient difference
between "ground" at the bridge and "ground" at the modulator. Over a pour the
same loop is nearer 10 nH. That order of magnitude is the whole argument.

### Vias are hand-soldered wire — so budget them

Milling gives no plated through-holes. Every layer-to-layer connection is a
short wire threaded through a hole and soldered on both faces. Two consequences:

- **A component lead is not a via.** You cannot reach the top pad of anything
  with a body over it — TO-220s, electrolytics, IC sockets. Place **dedicated
  via holes** (0.8–1.0 mm) with a short B.Cu trace from the pad, positioned in
  clear space where an iron can reach.
- **Group grounds locally, then stitch once or twice per group.** Connect the
  local ground net on B.Cu as you would on a single-sided board, and tie each
  group to the pour with its own via. That keeps the count to roughly:

| group | vias |
|---|---|
| power loop — bulk cap −, both low-side sources, driver `COM` | 2–3 (this one matters most) |
| driver decoupling | 1 |
| analog — TL074, both LM311s, virtual-ground divider | 2 |
| output filter / Zobel / speaker return | 1–2 |
| input connector ground | 1 |

**Around 8–12 wire vias per board.** That is an evening's fiddly work, not a
week's. Resist the temptation to via every ground pad individually.

**Do not split the pour.** With a solid plane, control return currents by
*placement*, not by cutting moats — a split plane usually makes mixed-signal
noise worse, not better, because it forces return current to detour. Put the
modulator physically away from the bridge and let the plane be continuous. This
replaces the single-point `LK1` star-ground idea used on the sub crossover
board, which is the right approach only when there is no plane.

### Registration

Milling both faces means the flip has to land within about 0.1 mm or the
top-layer clearances will not line up with the holes.

- Two 3 mm alignment holes outside the board outline, drilled in the first
  setup, with dowel pins in the spoilboard.
- Flip about the X axis so the pins re-enter the same holes.
- **Cut a test coupon first** — a few pads and holes — and check the clearances
  line up before committing the real board.

### Rules to design to

Design to the mill and the same files fab without rework. The reverse is not
true, so use the mill's numbers throughout:

- Track width ≥ 0.8 mm signal, **≥ 2.5 mm for the supply and bridge output**
  (~3 A peak).
- Clearance ≥ 0.8 mm everywhere, including pour-to-pad on F.Cu — the pour must
  clear every hole, or a lead will short to ground when you solder the bottom.
- Keep the **power loop** — bulk cap → high FET → low FET → back to the cap —
  physically as small as you can draw it. This single loop dominates radiated
  noise, more than anything else on the board.
- Bulk cap and the driver's decoupling go **at the bridge**, not near the input
  terminal.
- Gate traces short and paired with their return; the gate loop is the second
  worst offender after the power loop.

### If you later have it fabbed

Nothing in the design needs to change. You gain plated vias (the wire stitching
disappears, and you can stitch far more generously), solder mask, and silkscreen.
Two things become available that are worth taking:

- Stitch the pour liberally around the power stage, since vias are now free.
- Bare milled copper oxidises and bridges easily; a fabbed board with mask is
  markedly easier to solder and to rework.

If you fab, consider building one milled prototype first anyway — the bring-up
below will find the design errors, and it is much cheaper to find them before
paying for a panel.

## Bill of materials — per board

| Qty | Part | Shop reference | Role |
|---|---|---|---|
| 1 | HIP4082IPZ | IC / Linear | full-bridge gate driver |
| 4 | IRF540 | Transistor / N-MOSFET | output bridge |
| 2 | LM311 | IC / Linear | PWM comparators |
| 1 | TL074 | IC / Linear | virtual ground, integrator, buffer, inverter |
| 1 | 4049 | IC / 4000 CMOS | 12 V-capable complement generation |
| 2 | toroid core | Inductor / Toroid Core | hand-wound 15 µH output chokes |
| 1 | 820 nF film | Capacitor / Film | output filter |
| 1 | 100 nF film | Capacitor / Film | Zobel |
| 1 | 10 Ω 5 W | Resistor / Power | Zobel |
| 1 | 2200 µF | Capacitor / Electrolytic | bulk supply |
| 1 | 100 µF | Capacitor / Electrolytic | virtual-ground reservoir |
| ~8 | 100 nF ceramic | Capacitor / Ceramic | decoupling, bootstrap |
| 1 | 1 µF film | Capacitor / Film | input AC coupling |
| 1 | 10 kΩ pot | Resistor / Potentiometer | level |
| 1 | 10 kΩ trimmer | Resistor / Trimmer | carrier frequency |
| ~12 | E96 1/4 W | Resistor / E96 | gate, pull-up, bias, divider |
| 4 | 22 Ω | Resistor / E96 | gate resistors |
| 2 | 2-pole screw terminal | Connector / Terminal | supply in, speaker out |
| 1 | 2-pole screw terminal | Connector / Terminal | line in |
| 4 | TO-220 heatsink + mica + bushing | Hardware | FET cooling |
| 1 | DIP20 + 2 × DIP8 + DIP14 + DIP16 sockets | Connector / IC Socket | never solder these ICs directly |
| ~10 | offcut wire | — | hand-soldered vias between B.Cu and the F.Cu pour |

Everything above was checked against the shop CSV and exists.

## Risks — read before building

1. **Hand-wound inductors are the critical unknown.** Core material and A<sub>L</sub>
   are unspecified in the shop list. Wind, measure, and check for saturation at
   3 A before trusting the filter. Get this wrong and the amplifier distorts
   badly at high level or destroys the FETs.
2. **Registration between the two milled sides is the new risk.** Isolation
   milling both faces needs the flip to land within ~0.1 mm, or the top-layer
   clearances will not line up with the holes. Cut a test coupon before
   committing the real board.
3. **Dead-time must be verified from the datasheet, not assumed.** Shoot-through
   in a 12 V bridge will destroy MOSFETs quickly and quietly.
4. **Bring it up on a current-limited supply into a dummy load**, never a
   speaker. The shop's 5 W power resistors are too small for a 12 W dummy load;
   use an external load resistor.
5. **250 kHz will still radiate**, even with the pour. Expect to hear it on a
   nearby AM radio. That is normal for this construction and not a fault — the
   pour reduces coupling *into your own modulator*, which is what protects the
   audio; it does not make the board quiet to the outside world.

## Bring-up order

1. Board with **no MOSFETs fitted**. Check +12 V, 6 V virtual ground.
2. Check the triangle on the scope: amplitude, symmetry, ~250 kHz. Trim.
3. Inject a small sine into the input; check both comparator outputs are
   complementary PWM with sensible duty at idle (~50 %).
4. Check HIP4082 outputs and **measure the dead-time on the scope** before
   fitting any FETs.
5. Fit the FETs. Supply through a current limit set to ~0.5 A, no load. Idle
   current should be small and stable.
6. Dummy load, then raise supply and level gradually while watching the
   switching nodes for ringing and the FET temperatures.
7. Only then a speaker.

## Notes for the session that draws this

Use the **`kicad-schematic`** skill. Its checklist applies in full: score first,
draw in blocks with real wires, and render the PDF and look at it before
claiming anything.

Suggested sheet layout — eight blocks, three bands, signal left to right,
which is exactly the shape that skill is built around:

```
band 1   A power in + rails      B triangle oscillator     H indicators / test points
band 2   C input stage           D PWM comparators         E gate driver
band 3   F output bridge         G output filter + Zobel + speaker
```

**The board is now 2-layer**, which the `kicad-laser-pcb` flow does not assume.
That skill's router treats `F.Cu` as *wire bridges for crossings that are
impossible single-sided*, and runs a two-stage route that pushes leftovers
there. For this board `F.Cu` is a ground pour instead, so that stage needs
rethinking rather than reusing: route everything on `B.Cu`, then pour `F.Cu` as
ground and place the stitching vias by hand. Read `references/routing.md`
before assuming the existing pipeline applies.

Two things to know before writing any file:

- **This is a new board, so there is no existing sheet to retrofit into.**
  `sch_retrofit.py` does not apply. Emit directly with `schdraw`, and make the
  root sheet uuid match whatever `.kicad_pro` the project ends up with
  (`Sheet(project_file=...)`).
- **Do not run `kicad-cli sch upgrade` on the result.** It rewrites every symbol
  onto its own instance path and Eeschema then refuses to connect anything. This
  cost hours on the sub crossover board. `sch_score.py`'s `sheet_paths` check
  catches it, so run the scorer and believe it.

There is also unresolved history worth knowing: generated schematics on this
machine have previously passed every `kicad-cli` check and still shown
unconnected pins in Eeschema. If that happens again, **open the file standalone
with no project beside it** — if it is clean that way and broken inside the
project, the problem is the project/uuid linkage, not the drawing.

Before drawing, confirm from the HIP4082 datasheet: bootstrap diode
requirement, HDEL/LDEL values for ~200 ns, and input thresholds at VDD = 12 V.
