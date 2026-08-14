---
title: Test Guide - Companion 5 Characterisation
type: test-guide
tags:
  - electronics
  - audio
  - subwoofer
  - active-project
  - measurement
status: In Progress
started: 2026-08-13
updated: 2026-08-13
---

# Test Guide - Companion 5 Characterisation

> [!summary] **Overview**
> Bench characterisation of the **Bose Companion 5 bass module** before designing a
> line-level low-pass crossover to integrate it into the main stereo chain
> (Schiit Saga → Fosi amplifier → JBL 4412).
> - All measurements made with the **Analog Discovery 3** + WaveForms
> - Tests run in order; each one can kill the project cheaply before the next
> - Fill in the results tables as you go — the decision gate at the bottom
>   decides whether we build the analog board or pivot

---

## Why We Are Doing This

The plan is to split the Saga's output, send one leg to the Fosi as it is today,
and send the other leg through a low-pass filter into the Companion 5's aux
input on the control pod. The satellites stay unplugged; only the bass driver
is used. The pod knob becomes the sub level control and the pod mute becomes
the "off for vinyl" switch.

Three unknowns can sink that plan, and all three are measurable:

| # | Unknown | Why it would sink the plan |
|---|---------|----------------------------|
| 1 | A series coupling capacitor on the aux input | A high-pass sitting at 50 Hz on the **sub** feed removes exactly the band we want |
| 2 | DSP latency in the Bose signal path | 10 ms = 216° of phase rotation at 60 Hz; no analog polarity switch can fix that |
| 3 | Bose's internal low-pass corner | If it sits low, our own crossover has no authority over the handoff |

---

## Safety

> [!danger] **The amplifier output is bridged**
> Neither woofer terminal sits at ground potential. Scope channel 2 must be wired
> **truly differentially** in Test 0.4 — `2+` and `2−` both clipped to the driver,
> **neither one to AD3 ground**. Clipping `2−` to ground shorts an output stage
> through your PC's mains earth and will destroy the Bose amplifier, the AD3
> input, or both.

> [!warning] **Mains voltage inside the bass module**
> The Companion 5 has its mains supply inside the same enclosure.
> - **Unplug from the wall before opening it.** Wait 60 seconds before touching anything.
> - Identify the woofer terminals, clip your probe leads on, and **route the leads
>   out of the cabinet** so you can reassemble far enough to cover the supply
>   before you re-apply mains power.
> - Never reach into a powered, open enclosure.

> [!note] Signal levels
> Start every sweep at low amplitude and work up. The AD3 scope inputs survive
> ±25 V on the high range, which is comfortable headroom for what this amp
> produces at the drive levels used here — but only if you start low and check.

---

## Equipment Required

### Test Equipment
| Item | Purpose |
|------|---------|
| **Analog Discovery 3** + flywires | Wavegen, oscilloscope, network + impedance analyser |
| WaveForms software | AD3 control |
| Multimeter | Continuity checks on the test cables |
| Soldering iron (~350 °C) | Tinning the aux cable conductors |
| Phillips screwdriver / spudger | Opening the bass module (Test 0.4 only) |

### Components
| Component | Value | Qty | Notes |
|-----------|-------|-----|-------|
| R_ref | 10 kΩ 1% metal film | 1 | Impedance analyser reference |
| R_ref (alt) | 100 kΩ 1% metal film | 1 | Only if aux Z reads above ~40 kΩ |
| R_load | 47 Ω | 1 | Headphone-out dummy load |
| Hookup wire | solid core, ~0.5 mm | — | Pigtails on the cut aux cable |
| Header pins | male, 2.54 mm | 6 | Rigid grip points for flywires |

### AD3 Flywire Colour Code
Worth having in front of you — everything below refers to these names:

| Signal | Colour | Function |
|--------|--------|----------|
| `W1` | Yellow | Waveform generator 1 (the stimulus) |
| `1+` | Orange | Scope channel 1, positive |
| `1−` | Orange / white stripe | Scope channel 1, negative |
| `2+` | Blue | Scope channel 2, positive |
| `2−` | Blue / white stripe | Scope channel 2, negative |
| `⏚` | Black | Ground |

---

## Step 1 — Prepare the Test Cables

You have an aux cable cut in half: a **red** wire, a **white** wire, and the
shield braid twisted into a third conductor. Cutting it in half is convenient —
you get **two plugs**, so one can live in the aux jack and one in the headphone
jack without rewiring between tests.

### 1.1 Check the plug type

Count the black insulator bands on the metal plug:

- **2 bands = TRS** ✅ this is what the tests assume
- **3 bands = TRRS** ⚠️ a headset cable with a mic conductor; the ring
  assignments shift. Stop and note it in the results before continuing.

### 1.2 Ring out the conductors

Do not trust the colours. Multimeter on continuity, one probe on a wire, walk
the other probe along the plug:

```
       ┌──── TIP       expect WHITE   (Left)
     ┌─┴─┐
 ────┤   ├── RING      expect RED     (Right)
     └─┬─┘
       └──── SLEEVE    expect SHIELD  (Ground)
```

| Wire   | Continuity to | Expected | Actual |
| ------ | ------------- | -------- | ------ |
| White  |               | Tip      | tip    |
| Red    |               | Ring     | ring   |
| Shield |               | Sleeve   | sleeve |

> [!warning] **If red or white read open circuit, the cable is not broken**
> The inner conductors of thin aux cables are almost always **enamelled**. They
> look like bare copper strands but are lacquered and will not conduct through a
> clip or a probe tip.
> **Fix:** load the iron tip with a blob of solder at ~350 °C and hold it against
> the strands for 3–5 seconds. The enamel burns off and the strands tin in one
> motion. Re-test continuity afterwards.

### 1.3 Add grip points

Solder a short length of solid-core wire or a male header pin to each of the
three conductors. Stranded shield braid will fight the flywire clips, and
shorting shield to tip mid-sweep is an easy accident.

Label the two cables **AUX** and **PHONES** with tape.

---

## Step 2 — Pre-Flight Sanity Check

Before attributing any null reading to something subtle, prove the path is live.

1. Power on the Companion 5. USB stays **unplugged** throughout.
2. Set the pod volume knob to roughly 12 o'clock and **mark the position with
   tape**. Every measurement below is invalid if the knob moves between captures.
3. Plug the **AUX** cable into the pod's aux jack, nothing connected to the far end.
4. Touch the white and red wires with a fingertip.

You should hear mains hum from the woofer. That proves cable → jack → pod →
amplifier → driver is intact.

| Check                                    | Result |
| ---------------------------------------- | ------ |
| Hum audible when touching the conductors | x      |
| Pod knob changes the hum level           | x      |

---

## Step 3 — Test 0.3a: Aux Input Impedance

**Question:** what impedance does our output buffer have to drive, and is there
a coupling capacitor high-passing the input?

### Wiring

```
  W1 (yellow) ──────┬───── 10kΩ ─────┬───── AUX WHITE  (tip / L)
                    │                │
              1+ (orange)       2+ (blue)
                    │                │
                    │                │
  ⏚ (black) ────────┴────────────────┴───── AUX SHIELD (sleeve)
                    │                │
              1− (orange/wht)   2− (blue/wht)
```

Both scope negatives go to ground here — the AD3 inputs are differential, so
they must be explicitly tied, not left floating.

**Leave AUX RED unconnected for the first sweep.**

### WaveForms Setup

1. Open the **Impedance Analyzer** instrument.
2. Wiring mode: `W1-C1-R-C2-DUT-GND`
3. Reference resistor: **10 kΩ** (enter the measured value if you have it)
4. Amplitude: **100 mV**, Offset: **0 V**
5. Start: **10 Hz**, Stop: **20 kHz**, Steps: **100**, Scale: **Logarithmic**
6. Run the sweep. It will crawl at the bottom end — 10 Hz needs several cycles
   per point. Let it finish.

Then repeat the whole sweep with **AUX RED tied to AUX SHIELD**. If the two
results differ, the channels are summed through internal resistors, which
changes our level matching.

### Results — 0.3a

Measured with `tools/aux_impedance.py` (coherent DFT, 500 mV drive,
R_ref = 9.8 kΩ measured). Raw sweep in `tools/ring_open.csv`.

| Measurement | Ring open | Ring tied to sleeve |
|-------------|-----------|---------------------|
| \|Z\| at 1 kHz | 8.80 kΩ | 8.83 kΩ |
| \|Z\| at 100 Hz | 8.90 kΩ | 8.93 kΩ |
| \|Z\| at 20 Hz | 8.93 kΩ | 8.96 kΩ |
| Phase at 20 Hz | −1.1° | −1.14° |
| Reactance at 20 Hz | −177 Ω | −179 Ω |

![[0.3a-plot-compare.png]]

**Shape of the curve:** |Z| is flat within 0.1 dB from 10 Hz to ~500 Hz, then
falls above 1 kHz with increasingly capacitive phase, reaching 3.15 kΩ at
−65° by 20 kHz. That is a parallel RC: **R ≈ 8.99 kΩ in parallel with
≈ 2.4 nF**, corner around 7.4 kHz. Far too large to be cable or probe
capacitance (~100 pF and ~24 pF respectively), so it is a deliberate EMI
filter capacitor across the input.

The small negative reactance at the bottom of the sweep (−302 Ω at 10 Hz,
−177 Ω at 20 Hz) is consistent with a series coupling capacitor of roughly
**47 µF**, which against 9 kΩ puts the input high-pass corner near **0.4 Hz**.
There is a coupling cap, but it is a generously sized one and sits three
decades below anything we care about.

**Ring floating vs. ring grounded — the channels are independent.** The two
sweeps agree within 0.4 % across the whole band (8.93 vs 8.96 kΩ at 20 Hz),
and the reactance is identical (−177 vs −179 Ω). Grounding the right channel
does nothing measurable to the left. There is no resistive summing network
between the inputs; each channel presents its own ~8.9 kΩ load and any mono
summing happens further downstream.

> [!warning] A discarded measurement, kept as a note
> The first ring-grounded sweep was taken with the **bass module powered off**
> and read 10.30 kΩ with the low-frequency reactance nearly gone (−31.7 Ω).
> That looked like real cross-coupling and invited a long and completely wrong
> theory about the input topology. It was just a de-energised input stage.
> A powered-down amplifier presents a different impedance than a live one —
> when a comparison changes something you did not intend to change, suspect the
> setup before the device under test.

> [!note] Still to determine
> Whether driving tip **and** ring together yields more level than tip alone.
> Independent inputs still get summed somewhere downstream, so expect roughly
> +6 dB — but it sets the output stage gain, so it gets measured rather than
> assumed. Folded into 0.3b below.

**Interpretation:**

| Observation | Meaning |
|-------------|---------|
| \|Z\| flat from 20 Hz to 1 kHz | ✅ No input coupling cap. Ideal. |
| \|Z\| rises steeply below ~100 Hz, phase goes capacitive | ⚠️ Series coupling cap present. Note the frequency where \|Z\| has risen by 3 dB — that is the input high-pass corner. |
| Input high-pass corner above ~20 Hz | ❌ Gate 1 fails. The aux input cannot pass the band we need. |
| \|Z\| at 1 kHz above ~40 kΩ | Re-run with the **100 kΩ** reference resistor for better accuracy. |

| Derived value | Result |
|---------------|--------|
| Nominal input impedance | **8.9 kΩ** resistive, ∥ ~2.4 nF |
| Input high-pass corner (if any) | ~0.4 Hz (≈47 µF series cap) |
| **Gate 1 pass?** | ✅ **PASS** — +0.1 dB at 20 Hz vs 1 kHz |

> [!note] Design implication
> 8.9 kΩ is an easy load for any op-amp output buffer. The 2.4 nF shunt is
> irrelevant in the sub band but is a direct capacitive load, so the crossover
> board's output buffer gets a **100 Ω series resistor** to keep it
> unconditionally stable — standard practice, and it puts the resulting pole at
> 660 kHz where it does nothing.

### Reproducing 0.3a in the WaveForms GUI

The scripted measurement is the authoritative one, but the GUI produces a
plot worth keeping. Close any Python session first — the AD3 is claimed
exclusively by whichever process opens it.

Open **Welcome → Impedance**, then:

| Setting | Value | Why |
|---------|-------|-----|
| Wiring | `W1-C1-R-C2-DUT-GND` | Matches the physical rig: W1, C1 tap, reference resistor, C2 tap, DUT, ground |
| Resistor | **9800 Ω** | The *measured* value of R_ref, not the marked one |
| Amplitude | **500 mV** | The default 100 mV puts the signal at the same level as the mains hum this input injects. This is the single setting that decides whether the sweep is clean or noise |
| Offset | 0 V | |
| Start / Stop | 10 Hz / 20 kHz | |
| Steps | 100 | |
| Frequency scale | Logarithmic | |
| Settle | 50 ms | Lets each point stabilise before capture |
| Averaging | Maximum available | Trades sweep time for hum rejection |
| Traces | \|Z\| (log Ω) and θ (degrees) | Magnitude alone hides the coupling-cap evidence |
| Scope range | ±2.5 V or Auto | Signals are ~500 mV peak |

> [!tip] If the bottom of the sweep still scatters
> Below ~20 Hz the GUI has few periods to work with and hum rejection gets
> hard. Raise Settle, raise averaging, or start the sweep at 20 Hz. The
> scripted sweep integrates 24 full cycles per point, which is why it stays
> clean all the way down to 10 Hz — worth mentioning alongside the screenshot,
> since the difference between the two is the interesting part.

**Screenshots**

Ring open:

<!-- ![[0.3a-waveforms-ring-open.png]] -->

Ring tied to sleeve:

<!-- ![[0.3a-waveforms-ring-grounded.png]] -->

### Plotted from the raw sweep

Rendered by `tools/plot_impedance.py` from `tools/ring_open.csv`:

![[0.3a-plot-ring-open.png]]

Magnitude and phase get their own panels sharing one frequency axis — never a
dual y-scale. The shaded region marks the band this project actually cares
about, which is the point of the figure: **the input is flat and resistive
right through it.**

The second trace is the argument rather than decoration. R$_p$, the
parallel-model resistance, stays at ~9 kΩ across the entire sweep while |Z|
falls above 1 kHz. That separation is what shows the high-frequency rolloff to
be a shunt capacitance and not the resistive part changing — otherwise the
2.4 nF figure would just be an inference from a curve shape.

```bash
py -3.13 tools/plot_impedance.py tools/ring_open.csv --out 0.3a-plot-ring-open.png --theme dark
```

---

## Step 4 — Test 0.3b: Latency Probe via the Headphone Jack

**Question:** is there a digitising DSP in the signal path?

This is the cheap version of the question — no disassembly. The headphone jack
carries the full-range signal after the input stage and whatever processing the
Bose does, so a digitiser will show up as delay here.

### Wiring

```
  W1 (yellow) ──────┬───── AUX WHITE (tip)
                    │
              1+ (orange)
                    │
  ⏚ (black) ────────┴───── AUX SHIELD  ──── 1− (orange/wht)


  PHONES TIP ───────┬───── 2+ (blue)
                    │
                   47Ω        (dummy load)
                    │
  PHONES SLEEVE ────┴───── 2− (blue/wht)
```

AUX RED stays unconnected. The 47 Ω is there in case the headphone amplifier
misbehaves unloaded.

> [!note]
> Inserting a plug into the headphone jack will probably mute the speakers.
> That is normal and harmless — this test only needs the electrical path.

### WaveForms Setup

1. **Wavegen:** Square wave, **50 Hz**, Amplitude **200 mV**, Offset **0 V**. Run.
2. **Scope:** Trigger source **Channel 1**, **Rising edge**, level ~0 V.
3. Timebase **1 ms/div** to start. Channel ranges on Auto.
4. Place cursors on the Ch1 rising edge and on the corresponding Ch2 response.

### Results — 0.3b

Measured with `tools/latency_probe.py`, which cross-correlates the two captures
rather than relying on cursor placement. **No dummy load** across the headphone
output — see the warning below.

| Measurement | 5 Hz square | 500 Hz square |
|-------------|-------------|---------------|
| Timing resolution | 50 µs | 0.5 µs |
| Δt, ch1 → ch2 | **0.0000 ms** | **−0.0005 ms** |
| Correlation quality | 0.804 | 0.903 |
| Polarity | non-inverting | non-inverting |

Two independent measurements three decades apart both put the delay at zero.
A digitiser would impose at minimum 1–2 ms of block latency and typically
5–20 ms; we are resolving to half a microsecond and seeing nothing.

**Aux → headphone gain is frequency-shaped**, which is worth recording:

| Frequency | Gain |
|-----------|------|
| 5 Hz | −9.16 dB |
| 100 Hz | −6.79 dB |
| 500 Hz | −16.74 dB |

A ~10 dB hump centred near 100 Hz. Bose is applying bass shaping to the aux
path — and since the latency is zero, that shaping has to be analog. It also
means the headphone jack is **not** a flat window onto the signal, so 0.4 at
the woofer terminals remains the measurement that decides the crossover design.

> [!warning] The dummy load was the mistake, not a safeguard
> The 68 Ω across the headphone output was included in case the amplifier
> misbehaved unloaded. It doesn't — and the resistor formed a high-pass with the
> output coupling capacitor, corner around 26 Hz. That differentiated the 5 Hz
> square into spikes, and cross-correlating a square against its own derivative
> returned a confident-looking 57.9 ms at the edge of the search window.
> Removing the load moved the gain from −14.4 dB to −9.2 dB and the delay to
> zero. **Do not load an AC-coupled output when measuring its low-frequency
> timing** — the scope's own 2 MΩ puts the same corner below 1 Hz.

> [!warning] Two earlier method errors, recorded deliberately
> 1. A **sine** drive was used first. Cross-correlation of any periodic signal
>    peaks once per period, so the reported 10.54 ms was indistinguishable from
>    a polarity inversion. Only an edge-bearing waveform gives timing.
> 2. A **50 Hz square** was used next. A square is periodic too — the reported
>    −55.67 ms was 2.78 periods of aliasing, and being *negative* it was
>    non-causal and therefore impossible. The drive period must be much longer
>    than any delay being searched for, and the lag search must be restricted to
>    a causal window. Both are now enforced by the script.

**Interpretation:**

| Δt | Meaning |
|----|---------|
| Under ~0.2 ms | ✅ Analog path, no DSP. Everything in the design holds. |
| 0.2–3 ms | ⚠️ Borderline. Note it and continue; 0.4 decides. |
| Over ~3 ms | ❌ Gate 2 fails. Digitiser present. **Stop here** — pivot to miniDSP or re-amping rather than opening the box. |

**Tip only vs. tip + ring driven**, 100 Hz sine, measured at the headphone tip:

| Drive | ch2 level | Gain |
|-------|-----------|------|
| Tip only | 91.39 mV | −6.79 dB |
| Tip + ring | 95.97 mV | −6.36 dB |
| Difference | +4.58 mV | **+0.43 dB** |

> [!failure] Wrong probe point — this does not answer the summing question
> +0.43 dB, not the +6 dB that summing would produce. The headphone output is
> **stereo**: its tip carries the left channel only, so driving the right input
> can never add to it. The 4.58 mV that does appear is crosstalk, about −26 dB
> of channel separation.
>
> Whatever mono sum feeds the bass driver happens inside the amplifier,
> downstream of the headphone tap. The question is only answerable at the
> **woofer terminals in 0.4** — drive tip only, then tip and ring, and compare
> the level there.

| Derived value | Result |
|---------------|--------|
| Excess latency, aux → phones | 0 ms (< 0.5 µs) |
| Path polarity | non-inverting |
| Channel separation, aux → phones | ~26 dB |
| Tip vs tip+ring at the woofer | ⏳ carried to 0.4 |
| **Gate 2 pass?** | ✅ **PASS** — analog path, no digitiser |

> [!note] A clean result here is suggestive, not conclusive
> The headphone output could be an analog bypass around a DSP that still sits in
> the speaker path. Test 0.4 is the definitive answer. But a *bad* result here
> saves you the disassembly entirely, which is why it runs first.

---

## Step 5A — Test 0.4 (acoustic): Aux In → Nearfield SPL

> [!important] This replaces the electrical measurement below
> The electrical version of 0.4 was abandoned. The bass module's driver feed
> could not be identified with confidence from inside the enclosure: the only
> obvious candidate pair — two red wires with spade lugs — turned out to be
> **mains wiring to the rear-panel switch**, and a second candidate (a blue
> pair) measured 0 Ω once the meter leads were nulled, i.e. an amplifier output
> stage rather than a voice coil. Continuing to hunt for terminals inside a
> live enclosure was not worth the risk for a measurement we can take better
> another way.
>
> The acoustic measurement is also the more useful one. The electrical curve
> shows the filter Bose implemented; the acoustic curve shows that filter **plus
> the driver and cabinet**, and it is the combined acoustic slope that has to
> blend with the 4412s. This step therefore merges the old 0.4 and 0.5.

### Rig

- **AT2020** into the interface, 48 V phantom on, **~2 cm from the dust cap**,
  on-axis. Nearfield at this distance means direct output swamps the room, so
  the result is essentially driver + box, free of room modes.
- **Mark the mic position.** Every result here is a fixed-mic A/B; move the mic
  between captures and the comparison is worthless. Cardioid proximity effect
  shifts the bass by several dB per centimetre.
- Interface **line out → 3.5 mm → pod aux in**.
- Satellites unplugged. Pod volume and rear **Bass Compensation** both on their
  taped marks.

### REW settings

| Setting | Value |
|---------|-------|
| Input / output device | The same interface for both |
| Sweep range | 10 Hz – 1 kHz |
| Sweep length | 256k or longer (low-frequency resolution) |
| Output level | Start at −20 dBFS and work up |
| Timing reference | Not needed for magnitude. Use a loopback if you want phase |

Set the level by ear first: the sweep should be clearly audible but nowhere near
the point where the driver sounds strained. Check for compression by running the
same sweep 6 dB louder — if the curve changes shape rather than just moving up,
back off.

### Captures — all at the identical mic position

| # | Condition | Answers |
|---|-----------|---------|
| A | Tip only, Bass Comp on mark | The reference curve: corner, slope, high-pass |
| B | Tip + ring driven | Are the channels summed to the woofer? (+6 dB if so) |
| C | Bass Comp fully − | Lower end of the trim range |
| D | Bass Comp fully + | Upper end of the trim range, and whether it is level or shape |

### Results — 0.4 acoustic

Analysed with `tools/plot_acoustic.py` (1/6-octave smoothed).

![[0.4-acoustic-nearfield-cone.png]]

| Quantity | Left only | Right only | Both |
|----------|-----------|------------|------|
| Passband level (80–180 Hz) | 109.1 dB | 109.2 dB | 114.5 dB |
| High-pass corner (−3 dB) | 62.7 Hz | 63.2 Hz | 60.7 Hz |
| Low-pass corner (−3 dB) | 202.7 Hz | 202.8 Hz | 201.6 Hz |
| Slope above low-pass | −39 dB/oct | −39 dB/oct | −39 dB/oct |
| Slope below high-pass | +25 dB/oct | +25 dB/oct | +22 dB/oct |
| Usable bandwidth | 63–203 Hz (1.7 oct) | same | same |

| Derived value | Result |
|---------------|--------|
| Left vs right symmetry | within 0.1 dB — inputs reach the woofer identically |
| **B − A (summing)** | **+5.4 dB, flat across the band** → channels ARE summed |
| Implied filter orders | ~4th-order high-pass, ~6th-order low-pass |
| Port tuning notch | ~22 Hz in the cone nearfield |

> [!failure] Gate 3 — the module is a 63–203 Hz bandpass, and that breaks the plan
> The Companion 5 bass module is not a subwoofer. It is a tightly bandpassed
> midbass driver spanning **1.7 octaves**, and it produces **nothing below
> 63 Hz** — falling at 25 dB/octave beneath that, which is an electronic
> protection filter, not a natural driver rolloff.
>
> The original design was a Linkwitz-Riley low-pass at 50–60 Hz on the sub
> feed. Against a module that is already −3 dB at 63 Hz, that filter would
> deliver **almost nothing**. The two filters would be fighting over an empty
> band.
>
> Two further consequences:
> - **Bose already supplies a −39 dB/octave low-pass at 203 Hz**, steeper than
>   the LR4 we planned to build. Our board cannot improve on that slope; it can
>   only move the corner down.
> - The JBL 4412 is specified to 45 Hz. The Bose therefore overlaps *entirely*
>   with what the mains already cover and extends the system nowhere. Its only
>   possible contribution is added output and headroom in the 63–200 Hz midbass,
>   plus room-mode smoothing from a second source position.
>
> Any usable crossover point now lies between roughly **80 and 150 Hz** — well
> up in the 4412's midbass, not below it.

### Capture E — port / vent mouth

Mic moved to the opening where air movement is felt, everything else identical.

![[0.4-acoustic-cone-vs-port.png]]

| Quantity | Cone | Port / vent |
|----------|------|-------------|
| Passband level (80–180 Hz) | 109.1 dB | 103.7 dB |
| High-pass corner (−3 dB) | 62.7 Hz | 60.7 Hz |
| Low-pass corner (−3 dB) | 202.7 Hz | 203.4 Hz |
| Slope above low-pass | −39 dB/oct | −39 dB/oct |
| Slope below high-pass | +25 dB/oct | +21 dB/oct |

**The port radiates the same bandpass as the cone.** Same corners, same slopes,
5.4 dB lower simply from mic coupling at that position. A ported enclosure
normally shows the port taking over *below* the cone's output; here it does
nothing of the kind.

That is the confirmation the cone measurement needed. Had the 63 Hz rolloff
been an acoustic artefact of measuring cone motion near the box tuning, the
port would have filled in beneath it. It doesn't. **The band limit is
electronic and applies to everything the enclosure radiates** — there is no
hidden low end anywhere on this box.

| Derived value | Result |
|---------------|--------|
| Output below 60 Hz, any radiator | none |
| Nature of the 63 Hz limit | electronic, 4th-order — confirmed by port agreement |
| **Gate 3** | ❌ **FAIL as specified** — usable band 63–203 Hz, no sub-bass |

### Consequence for the crossover design

The board no longer needs a 4th-order Linkwitz-Riley. Bose already supplies a
−39 dB/octave skirt above 203 Hz, which our filter cannot improve on. The only
job left for our low-pass is to bring the corner down from ~200 Hz to somewhere
around 100–120 Hz so the module stops competing with the 4412 midrange — and a
**2nd-order section is sufficient for that**, because it cascades with Bose's
own filter rather than replacing it. Simpler board, fewer parts, less to go
wrong.

Whether the module earns a place at all now depends on **0.6**: if the 4412s
hold up through 60–120 Hz at the listening seat, there is nothing here worth
adding.

---

## Step 5B — Test 0.4 (electrical): Aux In → Woofer Terminals

> [!note] Not performed — see Step 5A
> Retained for reference in case the driver terminals are ever identified
> safely, e.g. with the driver removed from the cabinet.

**Question:** where is Bose's internal crossover, how steep is it, and is there
excess group delay?

Only run this once 0.3b is clean.

### Disassembly

> [!danger] Identify the driver at the DRIVER, never from the board end
> The bass module contains **two red wires with copper spade lugs** running to
> the rear-panel rocker switch. They look exactly like a speaker connection —
> spade lugs, a matched pair, heading toward the bottom of the enclosure — and
> they are **mains wiring**. Clipping a mains-earthed instrument across them
> destroys the instrument and probably the computer attached to it.
>
> Do not identify the driver feed by tracing cables from the amplifier board or
> from photographs. Start at the loudspeaker itself, where the terminals cannot
> be anything else, and confirm with a resistance measurement before connecting
> any instrument.

1. **Unplug the bass module from the wall.** Wait 60 seconds.
2. Open the enclosure and find the **bass driver**. Locate its two terminals on
   the driver frame.
3. **Measure DC resistance directly across those terminals: expect 3–6 Ω.**
   That is the voice coil, and nothing else in the box reads like it. Mains
   wiring through a switch reads near-zero or open, never a few ohms. Do not
   proceed without this reading.
4. **Tape and mark both knobs** — the pod volume *and* the rear-panel **Bass
   Compensation** control. Either one moving invalidates every sweep.
5. Clip `2+` and `2−` onto the driver terminals themselves.
6. Route the probe leads out through the opening and reassemble far enough to
   cover the lower board, where the AC inlet and switch wiring live.
7. Only then reconnect mains.

> [!note] Rear-panel Bass Compensation
> The Companion 5 has a **Bass Compensation** knob (−/+) on the rear panel — an
> analog level control acting on the bass module alone, adjustable from outside
> the enclosure. It may serve as the coarse sub-level trim in the final build,
> with the crossover board handling fine adjustment. Its range gets measured as
> part of 0.4.

### Wiring

```
  W1 (yellow) ──────┬──── AUX WHITE (tip)
                    │
              1+ (orange)
                    │
  W2 (yellow/wht) ──┼──── AUX RED (ring)
                    │
  ⏚ (black) ────────┴──── AUX SHIELD ──── 1− (orange/wht)


  2+ (blue) ────────── woofer terminal A     DIFFERENTIAL
  2− (blue/wht) ────── woofer terminal B     both on the driver
```

W2 goes to the ring so the summing test needs no rewiring: `woofer_sweep.py`
drives tip only by default and adds the ring with `--both`, phase-locked to W1.
Comparing the two passband gains answers the question the headphone tap
could not.

> [!danger] Check this before powering on
> `2−` is on the **driver**, not on ground. Trace the blue/white lead with your
> finger and confirm it terminates at the speaker, not at the black flywire bundle.

### WaveForms Setup

1. Open the **Network Analyzer** instrument.
2. Reference: **Channel 1**. Measured: **Channel 2**.
3. Start **10 Hz**, Stop **2 kHz**, Steps **200**, Scale **Logarithmic**.
4. Amplitude: **25 mV** (≈50 mVpp) for the first sweep.
5. Run once. Check the Ch2 trace: not flat-topped (clipping), not buried in
   noise. Raise the amplitude in steps until the trace is clean, re-running
   each time.
6. Enable both **Magnitude (dB)** and **Phase (degrees)** displays.
7. Export the sweep (File → Export) and save it beside this note.

### Reading Group Delay Off the Phase Plot

Pure latency and filter phase look different, and the distinction is what
matters:

- A **minimum-phase filter** asymptotes. A 2nd-order low-pass settles toward
  −180° and stops; a 4th-order settles toward −360° and stops.
- **Pure latency** never stops. Phase keeps winding — past −360°, −720°, and on
  — increasing linearly with frequency.

So: look at the phase **well above** the low-pass corner. If it has flattened
out, there is no meaningful latency. If it is still winding, compute it:

```
τ = −Δφ / (360 × Δf)          φ in degrees, f in Hz, τ in seconds
```

**Worked example:** phase falls 36° between 100 Hz and 110 Hz
→ τ = 36 / (360 × 10) = **10 ms**. That would be a fail.

The high end of the sweep will be heavily attenuated by the internal low-pass
and may be noisy — raise the drive amplitude for a second sweep focused on
200 Hz–2 kHz if the phase trace is too ragged to read.

### Time-Domain Cross-Check (optional)

If the phase plot is ambiguous, switch to the Scope and Wavegen: a **50 Hz tone
burst** into the aux, triggered on Ch1, and measure the delay to the *onset of
the envelope* on Ch2. Crude — the filter's own ringing smears the edge — but it
confirms millisecond-scale latency independently.

### Results — 0.4

| Quantity | Value | Expected |
|----------|-------|----------|
| Low-pass corner (−3 dB) | | 150–200 Hz |
| Low-pass slope (dB/oct) | | 12 (2nd order) |
| High-pass corner, if any | | 35–50 Hz |
| Passband gain (aux V → woofer V) | | |
| Phase at 2 kHz | | |
| Excess group delay | | < 3 ms |
| Input level at onset of clipping | | |

Exported sweep file: `______________________`

| Derived value | Result |
|---------------|--------|
| **Gate 3 pass?** | |

---

## Step 6 — Acoustic Measurements (Later)

> [!note] Do not start these until the electrical gates have passed
> No point measuring acoustics for a design that might pivot.

Uses the **Audio-Technica AT2020** and your interface (48 V phantom required).
The mic is uncalibrated and cardioid, so absolute SPL is meaningless — but every
measurement here is a **comparison at a fixed mic position**, where the mic's own
error is identical in both captures and cancels out.

**Keep the mic distance identical between captures.** Cardioid proximity effect
will otherwise shift the bass by several dB and invalidate the comparison.

### 0.5 — Bose bass module, nearfield
Mic ~2 cm from the cone, then at the port mouth.

| Quantity | Value |
|----------|-------|
| Acoustic −3 dB low corner | |
| Port tuning frequency | |
| Usable upper limit | |

### 0.6 — JBL 4412 in room
Nearfield on woofer and port, then in-room at the listening seat.

| Quantity | Value |
|----------|-------|
| Nearfield −3 dB low corner | |
| In-room −3 dB point at the seat | |
| Room modes / nulls below 150 Hz | |
| **Chosen crossover frequency** | |

---

## Decision Gate

- [ ] **Gate 1** — no aux input high-pass above ~20 Hz *(0.3a)*
- [ ] **Gate 2** — excess group delay under ~3 ms *(0.3b, confirmed by 0.4)*
- [ ] **Gate 3** — internal low-pass well above the intended crossover point *(0.4)*

| Outcome | Next step |
|---------|-----------|
| All three clear | Build the active 4th-order Linkwitz-Riley board: mono sum → LR4 at 50/60/80 Hz switched → polarity invert → level trim |
| Gate 1 fails | Aux input unusable — re-amp the woofer with a plate amp |
| Gate 2 fails | DSP in the path — miniDSP 2x4 HD (has delay) or re-amp |
| Gate 3 fails | Internal filter too low — re-amp, or accept a lower crossover point |

---

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| No continuity on red or white | Enamelled conductors — tin them properly (Step 1.2) |
| Impedance sweep reads wildly noisy below 50 Hz | Normal — too few cycles per point. Increase settling time in the analyser settings |
| Ch2 shows nothing in 0.4 | Pod knob at zero, mute engaged, or `2±` on the wrong terminals |
| Ch2 flat-topped | Amplifier clipping — reduce W1 amplitude |
| Hum riding on every measurement | Ground loop between the mains-earthed Bose and the USB-earthed AD3. Harmless for swept measurements; ignore it |
| \|Z\| result changes when you touch the leads | Enamel not fully removed, or a cold joint on a pigtail |

---

## Related

- [[Amplifier - Fosi Audio V3]]
- [[Pi Zero 2W PWM Audio Filter]]
