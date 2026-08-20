# Build notes — what the brief got wrong, and what is still unknown

Written while drawing `hardware/kicad/classd.kicad_sch`. `DESIGN-BRIEF.md` has
been corrected in place; this file records *why*, so nobody re-derives it.

## Corrections that changed the schematic

**The HIP4082 is a 16-pin DIP with one dead-time pin, not a 20-pin DIP with
`HDEL`/`LDEL`.** The brief described the HIP4081. `HIP4082IPZ` is 16 Ld PDIP
(Renesas FN3676 ordering info, package E16.3), and pin 5 `DEL` is a single
shared pin that sets the dead time for both half-bridges. There is no second
resistor to fit. This is the item the brief marked as blocking, and it was
wrong in both directions — wrong package, wrong pin count, wrong pin names.

**The bootstrap diodes are external.** The brief's block E listed only the
bootstrap capacitors. The HIP4082 has no internal diode: the pin description
for `AHB`/`BHB` says outright that an external diode and capacitor are
required. `D2` and `D3`, `1N5817`, now sit between +12 V and the two `xHB`
pins. Omit them and the high sides never get a floating supply, so the bridge
does nothing at all — a build-stopping error that no amount of careful drawing
would have surfaced.

**`DIS` is active high.** It is now held down by `R13`, 10 kΩ. Left floating on
a switching board it would be free to drift high and silently disable the
driver.

**Dead time: `R12` = 3k3.** The datasheet publishes two points (10 kΩ → 0.5 µs
typ, 100 kΩ → 4.5 µs typ) and a curve, with no closed-form expression.
Interpolating gives ≈3.3 kΩ for 200 ns, and the resulting DEL current
(12 − 2)/3k3 ≈ 3.0 mA is inside the pin's −4 mA limit. **This number is read
off Figure 16, not specified.** Measure the dead time on a scope before fitting
any MOSFET — step 4 of the bring-up order exists precisely for this.

**The complements are generated with two inverters per channel, not one.** The
4049 runs `PWM → /PWM → PWM`, feeding `ALI` from the first stage and `AHI` from
the second. One inverter per channel would have worked, but then the driver's
high input would see the LM311's slow RC pull-up edge while the low input saw a
sharp CMOS edge. Both inputs now get CMOS edges, at the cost of one gate delay
of skew (~30 ns typ, ~60 ns worst case) between them, which the 200 ns dead
time absorbs. Four of the six sections are used; the spare two have their
inputs tied to ground, as CMOS requires.

## Corrections to the BOM

- Sockets: **2 × DIP16 + 2 × DIP8 + DIP14**. The brief asked for a DIP20 for
  the driver; the shop stocks DIP16, which is what the part actually needs. The
  4049 is also a 16-pin part.
- **No 1 µF film capacitor is stocked** — the shop's film series steps 820 n →
  1u5. `C3` is 1.5 µF. Input corner with the 10 kΩ pot is ~11 Hz either way.
- **22 Ω is not an E96 value.** The gate resistors are `22R1`. Functionally
  identical; it matters only when ordering.
- Bulk cap: take the `2200µF 50V` shop line specifically. There is a second
  plain `2200µF` entry with no stated voltage at all.

## Numbers the brief stated that check out

The arithmetic was verified independently and the brief is right:

- Output filter, L_total = 30 µH against 4 Ω with 820 nF: f_c = **32.1 kHz**
  (brief said ~32 kHz), Q = **0.661** (brief said 0.66). Q sits just below the
  0.707 Butterworth value, so there is no peaking.
- Attenuation at 250 kHz: exact second-order magnitude gives **−35.7 dB**, and
  the asymptotic −40 dB/decade estimate lands within 0.2 dB of it, which is
  legitimate here because Q < 0.707. The brief's ~36 dB is correct.
- BTL theoretical maximum, V²/(2R) = 144/8 = **18 W**. Correct.
- Conduction loss per FET: **60–180 mW**. "Modest" was an understatement.

Two figures are softer than the brief implies, and are worth reading as
estimates rather than results:

- **Residual ripple ~0.4 Vpp** reproduces only under a worst-case
  full-differential-swing assumption. At idle the two legs switch nearly in
  phase and the differential ripple partly cancels; the nominal figure is
  closer to 0.2–0.25 Vpp.
- **~2.5 A per board** is not the average draw. 12 W out at 85–90 % efficiency
  is ~1.1 A; even 18 W at 75 % is ~2.0 A. Read 2.5 A as the bench-supply
  current limit to set — headroom for programme-material crest factor and the
  pulsed current into the bulk cap — not as an operating current.

## Oscillator values, which the brief left blank

The brief specified the topology and the 250 kHz target but no R and C. Drawn:

    f = V_swing / (8 · R · C)

With the LM311 swinging ~±5.4 V about the 6 V virtual ground and a ±2 V window
set by `R5`/`R6` (10 k and 27k4 → 5.4 × 10/27.4 ≈ 1.97 V):

    R·C = 5.4 / (8 × 250 kHz) = 2.7 µs

`C12` = 470 pF, `R4` = 3k9 fixed in series with `RV1` = 10 kΩ trimmer. At the
nominal 5k6 the arithmetic gives 256 kHz, and the trimmer covers roughly
103–368 kHz, so 250 kHz sits comfortably mid-range. The fixed 3k9 is there so
the trimmer cannot be wound to zero. Integrator ramp rate is 2.05 V/µs against
the TL074's 8 V/µs guaranteed minimum — ample.

## The one unresolved electrical risk in the modulator

**The TL074's input common-mode range is tight on a single 12 V rail, and the
brief's proposed fallback does not work.**

The classic TL07x die is specified for inputs no closer than 4 V to V−, so on
12 V the usable window is 4–12 V. The buffer and inverter sit at 6 V with the
audio riding on top, which puts the bottom of the swing right on that limit.
TL07x parts are known to misbehave — crossover glitches, phase reversal — when
common-mode approaches V−.

Two things follow:

1. The brief suggests moving those stages to an `MCP6002`. **That part is rated
   1.8–6.0 V, ~7 V absolute maximum. It cannot run on this rail at all.** If a
   rail-to-rail input part is needed, it has to be one rated for 12 V.
2. The newer **TL07xH** die needs only 1.5 V of headroom from V−, which clears
   the 4–8 V window with room to spare. Check the suffix on the part actually
   pulled from the shop.

The practical mitigation, and the reason the schematic was left on the TL074:
the level pot sets how far the audio swings, and at the design level (~1 Vrms
in, wiper well below full) the buffer input stays within roughly 4.6–7.4 V.
Watch for distortion that appears only at high level — that is this limit, not
the filter or the bridge.

**The simulation has since put a number on how tight that is.** In
`hardware/kicad/sim/sim_g_chain`, the whole chain reaches 13 W across 4 Ω at
the level where AUDIO_P bottoms out at **4.00 V** — the common-mode floor
itself. The 12 W target and the input stage's limit are not merely close; they
coincide. There is no margin to trade, so the level control is not a "turn it
up until it clips" control on this board: past that point the buffer goes
before the bridge does. `run_sims.py` asserts that number explicitly rather
than treating it as incidental.

The integrator is unaffected: its input sits at the virtual ground and does not
track the audio.

## Footprints

All through-hole, sized for isolation milling with an 0.8 mm end mill. Every
footprint was audited for its smallest pad-to-pad gap before being assigned,
because a gap the tool cannot enter is never isolated and ships as a short.

Two results worth keeping:

- **The stock `Potentiometer_Alps_RK09K_Single_Vertical` is unbuildable here**
  at 0.70 mm pad-to-pad. `RV2` uses `Potentiometer_ACP_CA14V-15_Vertical`
  instead, which has a 5 mm pin pitch and 7.66 mm of clearance. The shop's
  pot is not specified beyond "10k", so **measure the real part** before
  committing copper — this is a plausible stand-in, not a confirmed match.
- **The stock TO-220 footprint is 0.64 mm and also unbuildable.** `Q1..Q4` use
  the vendored `energy_system:TO-220-3_Vertical_LaserPads`, whose pads are
  narrowed to 1.7 mm to reach 0.84 mm. That still clears the tool but sits
  under the 0.85 mm netclass clearance, so `classd.kicad_dru` carries a
  per-footprint exception for those four parts and nothing else.

Everything else clears comfortably: DIP-8/14/16 LongPads at 0.94 mm, the
Bourns 3296W trimmer at 1.10 mm, the bornier terminals at 2.08 mm, and every
axial or radial passive at 1.9 mm or wider.

Two libraries are vendored into `hardware/kicad/lib/` and registered in
`fp-lib-table`, because KiCad 10 does not ship them: the `bornier` screw
terminals it deleted from the stock `TerminalBlock` library, and the
mill-specific `energy_system` parts (narrowed TO-220 and LED, and the measured
hand-wound toroid).

Values still taken on trust and worth checking against the physical parts: the
2200 uF bulk cap footprint (D18 mm / 7.5 mm pitch), the 820 nF film filter cap
(15 mm pitch), and the 10R 5 W Zobel resistor (30.48 mm pitch).

## Still unknown, and it is the same one the brief flagged

**The toroid cores.** The shop CSV lists three toroid sizes with no material
and no A_L, so 15 µH cannot be designed on paper. Wind them, measure on an LCR
meter, match the pair, and confirm they do not saturate at 3 A. This is
unchanged from the brief and remains the single largest practical risk.

Two smaller ones the shop data cannot answer: **no film capacitor in the shop
list carries a voltage rating** (the 820 nF filter cap sees the full
differential swing and wants ≥63 V), and **no electrolytic states a ripple
current** (the bulk cap takes the bridge's pulsed current). Read the markings
on the physical parts.

## One thing to know about the drawing

The IRF540N's body-diode recovery is **marginal, not comfortable**: Q_rr
505 nC typ / 760 nC max with t_rr 115–170 ns, against a 200 ns dead time. Each
commutation will produce a recovery current spike, and it will be a significant
share of the EMI. At 12 W this is a noise problem rather than a reliability
one, and the 22 Ω gate resistors already slow the edges deliberately. If the
board turns out noisier than wanted, a faster-body-diode MOSFET is a cheaper
fix than anything on the layout.
