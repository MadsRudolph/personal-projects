---
title: LM386 Mini Amplifier
type: project
tags:
  - electronics
  - audio
  - amplifier
status: Planning
started: 2026-02-28
updated: 2026-03-02
aliases:
  - LM386 Amp
  - Mini Speaker Amp
links:
  - "[[Pi Zero 2W PWM Audio Filter]]"
---

# LM386 Mini Amplifier

> [!summary] **Project Goal**
> Build a standalone mini amplifier using the LM386N-1 to drive a salvaged 8Ω 1.5W passive speaker. Breadboard prototype powered from bench supply, minimal parts count.

---

## Specifications

| Parameter | Value |
|-----------|-------|
| **IC** | LM386N-1 (DIP-8) |
| **Gain** | 20 (26 dB) — default, pins 1 & 8 open |
| **Supply** | Bench PSU set to 9V (operating range: 4V–12V) |
| **Quiescent Current** | ~4 mA (typ.) |
| **Output Power** | ~325 mW into 8Ω @ 9V (datasheet typ.) |
| **Load** | 8Ω 1.5W salvaged speaker |
| **Bandwidth** | 300 kHz (pins 1 & 8 open) |
| **THD** | 0.2% @ 125 mW, 6V, 1 kHz |

---

## LM386N-1 Pinout

> [!note]- DIP-8 Top View
> ```
>          ┌───∪───┐
>    GAIN  │ 1   8 │  GAIN
>    -IN   │ 2   7 │  BYPASS
>    +IN   │ 3   6 │  Vs
>    GND   │ 4   5 │  VOUT
>          └───────┘
> ```

| Pin | Name | This Circuit |
|-----|------|--------------|
| 1 | GAIN | NC (gain = 20) |
| 2 | -INPUT | GND (bottom of volume pot) |
| 3 | +INPUT | Audio in via C1 + VR1 wiper |
| 4 | GND | Ground bus |
| 5 | VOUT | Speaker via C2 (2×100µF) |
| 6 | Vs | +9V with C4 bypass (100nF) |
| 7 | BYPASS | C5 (10µF) to GND |
| 8 | GAIN | NC (gain = 20) |

---

## Schematic

> [!note]- LM386 Amplifier Circuit (Gain = 20)
> Based on TI datasheet Figure 9-1 with volume control and bypass additions.
> ```
>                             +9V (Bench PSU)
>                              │
>                       ┌──────┤
>                       │      │
>                     [C4]    [6 Vs]
>                    100nF     │
>                       │    LM386N-1       [1]──NC
>                      GND     │            [8]──NC
>                              │
>                        [7]──[C5]──GND
>                       BYPASS 10µF
>                              │
>     Audio In                [5 VOUT]
>         │                    │
>       [C1]              ┌────┴────────┐
>       10µF              │             │
>       (+)→              │           [C3]
>         │              [C2]        100nF
>         │           2×100µF           │
>    ┌────┘              (+)          [R1]
>    │                    │            10Ω
>  ──┤wiper               │             │
>  [VR1]               Speaker         GND
>  10kΩ                  8Ω
>  (vol)                  │
>  ──┤                   GND
>    │
>   [3 +IN]
>    │
>   [2 -IN]
>    │
>   [4 GND]──────GND
> ```
>
> **Signal path:** Audio in → C1 (DC block) → VR1 wiper (volume) → Pin 3 (+IN) → LM386 → Pin 5 (VOUT) → C2 (DC block) → Speaker
>
> **Zobel note:** C3 is 100nF (substitution for 47nF — not in stock). Crossover shifts from 339 kHz to 159 kHz. Still well above audio, slightly more conservative against oscillation.
>
> **Zobel network:** C3 + R1 in series from pin 5 to GND — prevents high-frequency oscillation with inductive speaker loads.
>
> **Bypass (Pin 7):** Improves power supply rejection from ~10 dB to ~50 dB at 1 kHz (datasheet Figure 6-2). Strongly recommended even though listed as optional in many guides.
>
> **Vs bypass (C4):** 100nF ceramic directly at pin 6 — standard decoupling. Datasheet Section 10 recommends a cap to GND close to the power pin.

---

## Bill of Materials

| Ref | Qty | Component | Value | Notes |
|-----|-----|-----------|-------|-------|
| U1 | 1 | LM386N-1 | — | DIP-8. Use socket. |
| C1 | 1 | Electrolytic cap | 10 µF 25V | Input DC blocking. + toward audio source. |
| C2 | 2 | Electrolytic cap | 100 µF (×2 parallel = 200 µF) | Output DC blocking. **+ toward pin 5.** Substitution — no 220µF in stock. |
| C3 | 1 | Ceramic or film cap | 100 nF | Zobel network. Substitution — no 47nF in stock. |
| C4 | 1 | Ceramic cap | 100 nF | Vs bypass — close to pin 6 |
| C5 | 1 | Electrolytic cap | 10 µF 25V | Pin 7 bypass. + toward pin 7. |
| R1 | 1 | Resistor | 10 Ω | Zobel network |
| VR1 | 1 | Potentiometer | 10 kΩ linear | Volume control |
| — | 1 | Speaker | 8Ω 1.5W | Salvaged |
| — | 1 | Breadboard | — | For prototype |
| — | — | Bench power supply | 9V | Current limit ~200 mA |
| — | — | Jumper wires | — | For breadboard connections |

---

## Design Notes

### Output Coupling Cap (C2) — 2×100µF Parallel

The output cap + speaker impedance form a high-pass filter. The cutoff must be well below the audio band:

$$f_c = \frac{1}{2\pi \cdot R_{load} \cdot C_2}$$

| C2 Value | Cutoff (-3dB) | Result |
|----------|---------------|--------|
| 10 µF | **1990 Hz** | No bass — unusable |
| 100 µF | 199 Hz | Marginal — weak bass |
| **200 µF (2×100µF)** | **~100 Hz** | **This build** — close to datasheet 250µF |
| 220 µF | 90 Hz | Datasheet closest standard value |
| 470 µF | 42 Hz | Overkill for 8Ω 1.5W driver |

No 220µF in stock. Two 100µF electrolytic caps in parallel give 200µF — cutoff at ~100 Hz, close to the original 90 Hz target. For a small speaker that rolls off naturally around 100–150 Hz, this is perfectly adequate.

### Input Coupling Cap (C1)

$$f_c = \frac{1}{2\pi \cdot R_{in} \cdot C_1} = \frac{1}{2\pi \cdot 10\,\text{k}\Omega \cdot 10\,\mu\text{F}} \approx 1.6\,\text{Hz}$$

Well below the audio band — no signal loss.

### Output Power Estimate

With the internal output transistors having ~1V saturation on each rail:

$$V_{peak} \approx \frac{V_s}{2} - V_{sat} \approx 4.5 - 1.0 = 3.5\,\text{V}$$

$$P_{max} \approx \frac{V_{peak}^2}{2 \cdot R_L} = \frac{12.25}{16} \approx 0.77\,\text{W} \quad \text{(theoretical)}$$

Actual output is ~325 mW typical at 10% THD per datasheet (Vs = 9V, R_L = 8Ω). Well within the 1.5W speaker rating.

### Power Dissipation

| Parameter | Value |
|-----------|-------|
| Quiescent | 9V × 4 mA = 36 mW |
| At 325 mW output | ~0.5W total IC dissipation (datasheet Fig. 6-7) |
| DIP-8 package limit | 1.25W |

Plenty of thermal margin — no heatsink needed.

### Gain Options

| Pins 1 ↔ 8 | Gain | dB | Notes |
|-------------|------|----|-------|
| Open (NC) | 20 | 26 | **Default — this build** |
| 10µF cap | 200 | 46 | Max gain. Bypass pin 2 with 0.1µF to GND. |
| 1.2kΩ + 10µF series | 50 | 34 | Intermediate |

> [!warning] Higher Gain Stability
> When using gain > 20 (cap between pins 1 & 8), the datasheet recommends bypassing pin 2 (-INPUT) with a 0.1µF cap or short to ground to prevent oscillation and gain degradation. Not needed at default gain = 20.

---

## Build Guide

### Wiring Steps

1. **Place LM386** — straddle the center channel of the breadboard, orient notch/dot (pin 1).
2. **Power rails** — connect bench PSU: +9V to the breadboard power rail, GND to the ground rail. Set current limit to ~200 mA.
3. **Ground (pin 4)** — jumper to ground rail.
4. **Power (pin 6)** — jumper to +9V rail. Place C4 (100nF) directly across pin 6 and adjacent ground rail — shortest leads possible.
5. **Bypass (pin 7)** — C5 (10µF, + to pin 7) to ground rail.
6. **Input stage:**
   - VR1 (10kΩ pot): one outer lug to ground rail, other outer lug receives audio through C1.
   - C1 (10µF, + toward audio source) from audio input to pot lug.
   - Pot wiper to pin 3 (+INPUT).
   - Pin 2 (-INPUT) to ground rail.
7. **Output stage:**
   - C2 (2×100µF in parallel, **+ toward pin 5**) from pin 5 to speaker positive terminal. Wire both caps between the same two points — pin 5 row and speaker positive row.
   - Speaker negative to ground rail.
   - Zobel: C3 (100nF) in series with R1 (10Ω) from pin 5 to ground rail. Keep leads short.
8. **Gain pins** — leave pins 1 and 8 unconnected (gain = 20).

### Layout Tips

- Keep input wiring (pins 2, 3) physically separated from output wiring (pin 5) to prevent oscillation feedback
- C4 bypass cap: absolute shortest leads, directly at pin 6 to ground rail
- Zobel network: close to pin 5 and speaker terminal
- Star grounding: all ground returns converge at a single point near pin 4
- Set bench PSU current limit to ~200 mA — protects the IC during wiring mistakes

---

## Testing

1. **Power check (no IC)** — set bench PSU to 9V with ~200 mA current limit, power on and verify with multimeter:
   - 9V at pin 6 row
   - 0V at pin 4 row
   - No short between power and ground (bench PSU should show only a few mA draw)
2. **Insert IC** — power off first. Observe notch/dot orientation (pin 1 = GAIN).
3. **No-signal test** — power on, no audio connected. Current draw should be ~4 mA. Listen for silence — any squealing means oscillation (check bypass caps and ground routing).
4. **Audio test** — connect phone or audio source via 3.5mm cable. Start with VR1 fully counter-clockwise (min volume), slowly increase. Should hear clean audio through speaker.
5. **If oscillation occurs:**
   - Verify C4 (100nF) is present and directly at pin 6
   - Verify Zobel (C3 100nF + R1 10Ω) is connected from pin 5 to ground
   - Add C5 on pin 7 if not already present
   - Shorten ground wires, especially from pin 4
   - Separate input and output wiring

---

## Bench PSU Settings

| Parameter | Value |
|-----------|-------|
| **Voltage** | 9V DC |
| **Current Limit** | 200 mA |
| **Expected Quiescent Draw** | ~4 mA |
| **Expected Draw During Playback** | ~50–100 mA |

> [!tip] The current limit on the bench PSU acts as protection during prototyping — if there's a wiring mistake the supply will current-limit instead of frying the IC.

---

## Build Phases

- [x] **Research** — IC selection, datasheet review, circuit design
- [x] **Components** — All parts confirmed in stock (2 substitutions: C2 2×100µF, C3 100nF)
- [ ] **Breadboard prototype** — Test circuit, verify no oscillation
- [ ] **Protoboard build** — Solder final circuit
- [ ] **Enclosure** — 3D print or project box

---

## References

- [LM386 Datasheet (TI SNAS545D)](https://www.ti.com/product/LM386)
- Datasheet PDF: `../Resources/Pi Zero PWM Filter/Datasheets/lm386.pdf`
