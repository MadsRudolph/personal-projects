# Class D audio amplifier — design brief

**Target:** one mono Class D amplifier board driving a 4 Ω speaker, built **twice**
for stereo. Every part comes from the DTU component shop
(`components-inventory/dtu_component_shop(1).csv`, 1464 lines, verified against
this design). Board process is the existing CNC-milled single-sided
through-hole flow (see the `kicad-laser-pcb` skill).

| | |
|---|---|
| Supply | single **+12 V** from a bench PSU, ~2.5 A per board |
| Output | ~**12 W** into 4 Ω (18 W theoretical, derated for modulation depth and losses) |
| Topology | **BTL full bridge**, fixed-frequency PWM |
| Switching | ~**250 kHz** |
| Channels | mono per board; build two identical boards |

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

**Two boards rather than one stereo board.** On a single-sided milled board
with no ground plane, two switching bridges sharing one piece of copper is a
serious layout problem: crosstalk through the shared ground, and two carriers
beating against each other. Two identical mono boards remove that entirely and
halve the milling risk, at the cost of a second build.

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
- `10 Ω` gate resistors in series with each gate; `10 kΩ` gate-to-source
  pulldowns so nothing floats on at power-up.
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
| 4 | 10 Ω | Resistor / E96 | gate resistors |
| 2 | 2-pole screw terminal | Connector / Terminal | supply in, speaker out |
| 1 | 2-pole screw terminal | Connector / Terminal | line in |
| 4 | TO-220 heatsink + mica + bushing | Hardware | FET cooling |
| 1 | DIP20 + 2 × DIP8 + DIP14 + DIP16 sockets | Connector / IC Socket | never solder these ICs directly |

Everything above was checked against the shop CSV and exists.

## Risks — read before building

1. **Hand-wound inductors are the critical unknown.** Core material and A<sub>L</sub>
   are unspecified in the shop list. Wind, measure, and check for saturation at
   3 A before trusting the filter. Get this wrong and the amplifier distorts
   badly at high level or destroys the FETs.
2. **Single-sided milled copper has no ground plane.** This is the hardest part
   of the whole project. Keep the bridge's switching loop physically tiny, run
   wide (≥ 2 mm) power traces, and use a star ground with the analog section
   joined to power ground at exactly one point — the same `LK1` link idea as the
   sub crossover board.
3. **Dead-time must be verified from the datasheet, not assumed.** Shoot-through
   in a 12 V bridge will destroy MOSFETs quickly and quietly.
4. **Bring it up on a current-limited supply into a dummy load**, never a
   speaker. The shop's 5 W power resistors are too small for a 12 W dummy load;
   use an external load resistor.
5. **250 kHz on a milled board will radiate.** Expect to hear it on nearby AM
   radio. That is normal for this construction and not a fault.

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
