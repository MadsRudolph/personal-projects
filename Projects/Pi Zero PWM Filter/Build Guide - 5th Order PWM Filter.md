---
title: Build Guide - 5th Order PWM Filter
type: build-guide
tags:
  - electronics
  - raspberry-pi
  - audio
  - active-project
  - build-log
status: In Progress
started: 2026-02-23
updated: 2026-02-23
build-date:
parent: "[[Pi Zero 2W PWM Audio Filter]]"
---

# Build Guide - 5th Order PWM Filter

> [!summary] **Overview**
> Upgrade from the 3rd order filter to a 5th order design for better PWM rejection — especially through a preamp.
> - **Topology:** 1st order RC + 2x 2nd order Sallen-Key (Q=0.55, Q=1.29)
> - **Op-amp:** TL074 (quad) — all 4 op-amps used for stereo
> - **Output:** PCB-mount dual RCA jack (replaces screw terminals)
> - Build one channel first (Right), verify, then duplicate for Left

| | 3rd Order (old) | 5th Order (new) |
|---|---|---|
| **Roll-off** | -60 dB/decade | **-100 dB/decade** |
| **Op-amp** | TL072 (dual) | TL074 (quad) |
| **Output** | Screw terminals | RCA jack |
| **Stages** | RC + 1x SK | RC + 2x SK |

---

## Equipment Required

### Test Equipment
| Item | Purpose |
|------|---------|
| **Multimeter** | DC voltage checks, continuity, component verification |
| **Bench power supply** | 5.0V regulated supply with current limiting |

> [!note] No Oscilloscope Available
> AD3 is currently out of service. All verification uses DC voltage checks and continuity testing with a multimeter. Final audio verification is done by listening test with the Pi.

### Components (Single Channel)
| Component | Value | Qty | Notes |
|-----------|-------|-----|-------|
| R_in | 2.2 kΩ | 1 | Input RC stage |
| R_s2a, R_s2b | 910 Ω | 2 | Stage 2 Sallen-Key (design: 887 Ω) |
| R_s3a, R_s3b | 2 kΩ | 2 | Stage 3 Sallen-Key (design: 2.05 kΩ) |
| C_in | 1.5 nF | 1 | Film cap, input RC |
| C_s2a | 8.2 nF | 1 | Film cap, Stage 2 |
| C_s2b | 10 nF | 1 | Film cap, Stage 2 |
| C_s3a | 1.5 nF | 1 | Film cap, Stage 3 |
| C_s3b | 10 nF | 1 | Film cap, Stage 3 |
| C_out | 6.8 µF electrolytic | 1 | Output DC blocking |
| C_bypass | 100 nF ceramic | 1 | Op-amp power bypass (shared) |
| TL074 | Quad op-amp | 1 | Shared between both channels |

> [!note] Simplified Design
> The Vbias network (10kΩ resistors + 10µF cap) is **not needed** in this design.
> DC bias comes through the signal path via the input DC offset — same as the 3rd order build.

> [!note] Standard Value Substitutions
> The filter design calls for 887 Ω and 2.05 kΩ — these are not standard values.
> Using 910 Ω and 2 kΩ shifts the cutoff frequency slightly but is perfectly acceptable.

### Power Supply
- **Recommended:** Adjustable bench power supply set to 5.0V
- Current draw: ~20 mA (both channels)
- Set current limit to ~50 mA during testing (protects against shorts)

---

## Expected Frequency Response

Analytical simulation results — use these as reference when testing each build stage.

> [!info] Source: `sim/filter_comparison.py` — analytical transfer functions per TI SLOA024B

### Stage Parameters

| Stage | Components | f₀ / fc | Q |
|-------|-----------|---------|---|
| Input RC | R=2.2kΩ, C=1.5nF | 48.2 kHz | — |
| SK Stage 2 | R=910Ω, C₁=8.2nF, C₂=10nF | 19.3 kHz | 0.55 |
| SK Stage 3 | R=2kΩ, C₁=1.5nF, C₂=10nF | 20.5 kHz | 1.29 |
| **Combined** | — | **19.1 kHz (-3dB)** | — |

### Expected Attenuation at Key Frequencies

| Frequency | RC Only | RC + SK1 (3rd order) | Full 5th Order |
|-----------|---------|---------------------|----------------|
| 1 kHz | 0 dB | 0 dB | 0 dB |
| 10 kHz | ~0 dB | ~0 dB | ~0 dB |
| 20 kHz | -1.5 dB | -3 dB | -3 dB |
| **31.25 kHz (PWM)** | -4 dB | ~-10 dB | **-16.9 dB** |
| 62.5 kHz | -9 dB | ~-24 dB | **-44.0 dB** |
| 93.75 kHz | -12 dB | ~-34 dB | **-60.6 dB** |

### Stage Contributions

![5th order individual stage contributions](../../Resources/Pi%20Zero%20PWM%20Filter/images/filter_5th_order_stages.png)

The Q=1.29 stage creates a slight resonance peak near cutoff — this is by design. When cascaded with the Q=0.55 stage and RC input, it produces a Butterworth-like flat passband with steep transition to the stopband (~100 dB/decade roll-off).

---

## Test Setup

### Bench Power Supply

| Setting | Value |
|---------|-------|
| Voltage | 5.00 V |
| Current limit | 50 mA (protection) |
| Output | + to Vcc, - to GND |

### Multimeter Checks Used in This Guide

| Check Type | How | What it Tells You |
|------------|-----|-------------------|
| **DC Voltage** | Red probe to test point, black to GND | Correct bias / power |
| **Continuity** | Probes across connection, listen for beep | Solder joints intact |
| **Resistance** | Probes across component (power OFF) | Correct component placed |

> [!tip] Always Measure Components Before Soldering
> Verify each resistor value with your multimeter before soldering. A 910Ω and 2kΩ are easy to mix up visually.

---

## Quick DC Voltage Reference

Use this table for fast verification at any point during the build.

### Bench Supply Only (no Pi connected)

| Test Point | Pin | Expected | Notes |
|------------|-----|----------|-------|
| V+ rail | 4 | 5.0V | Power supply |
| GND rail | 11 | 0V | Ground reference |
| 1OUT (R SK1) | 1 | ~0V or floating | No input signal |
| 2OUT (R SK2) | 7 | ~0V or floating | No input signal |
| 3OUT (L SK1) | 8 | ~0V or floating | No input signal |
| 4OUT (L SK2) | 14 | ~0V or floating | No input signal |
| After C_out (R) | — | 0V | DC blocked |
| After C_out (L) | — | 0V | DC blocked |

### With Pi Connected (PWM active, idle — no music playing)

| Test Point | Pin | Expected | Notes |
|------------|-----|----------|-------|
| 1OUT (R SK1) | 1 | ~2.5V | Mid-rail bias from PWM DC |
| 2OUT (R SK2) | 7 | ~2.5V | Mid-rail bias from PWM DC |
| 3OUT (L SK1) | 8 | ~2.5V | Mid-rail bias from PWM DC |
| 4OUT (L SK2) | 14 | ~2.5V | Mid-rail bias from PWM DC |
| After C_out (R) | — | ~0V | DC blocked by output cap |
| After C_out (L) | — | ~0V | DC blocked by output cap |

> [!important] If any output pin reads 0V or 5V (stuck at rail) with the Pi connected, there's a wiring problem.
> All op-amp outputs should sit at roughly half-supply (~2.5V) when receiving the PWM DC bias.

---

## Build Stages

---

### Stage 0: Power Supply

> [!important] Simplified Design
> The Vbias resistor divider network is **NOT needed**.
> DC bias comes from the Pi's PWM output through the signal path.

#### Build Steps
1. [x] Wire +5V from bench supply to TL074 pin 4 (V+)
2. [x] Wire GND from bench supply to TL074 pin 11 (V-)
3. [x] Solder 100nF bypass cap directly across pins 4 and 11 (short leads!)

#### Test 0: Power Supply

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| Vcc at pin 4 | Multimeter: pin 4 to pin 11 | 5.0V ± 0.1V | | [ ] |
| Current draw | Bench supply reading | < 10 mA | | [ ] |

---

### Stage 1: Input RC Filter (1st Order) — Right Channel

This passive RC stage provides the first pole of the filter. The cutoff is higher than the 3rd order design (48 kHz vs 33 kHz) because the cascaded Sallen-Key stages provide the main filtering.

#### Schematic
```
    Input ----[R_in 2.2kΩ]----+---- Output (to Stage 2)
                               |
                             [C_in]
                             1.5nF
                               |
                              GND
```

#### Build Steps
1. [ ] Measure R_in with multimeter — confirm ~2.2kΩ
2. [ ] Solder R_in (2.2kΩ) — input side left open for now (will connect to Pi GPIO19)
3. [ ] Solder C_in (1.5nF) from R_in output to GND
4. [ ] Mark the junction of R_in and C_in as "TP1" (test point 1)

#### Test 1: Input RC Verification

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| R_in value | Multimeter resistance (power off) | 2.2 kΩ ± 5% | | [ ] |
| Continuity: input → TP1 | Continuity through R_in | Beep | | [ ] |
| Continuity: TP1 → GND | Continuity through C_in | Beep (may be brief) | | [ ] |
| No short: input → GND | Resistance across input to GND | > 1 kΩ (R_in value) | | [ ] |

---

### Stage 2: Op-Amp Installation

Install the TL074 (into the socket already soldered) and verify power connections.

#### TL074CN Pinout
```
        +---u---+
 1OUT  -| 1  14 |- 4OUT
 1IN-  -| 2  13 |- 4IN-
 1IN+  -| 3  12 |- 4IN+
 V+    -| 4  11 |- V- (GND)
 2IN+  -| 5  10 |- 3IN+
 2IN-  -| 6   9 |- 3IN-
 2OUT  -| 7   8 |- 3OUT
        +-------+

Channel Assignment:
  Op-amp 1 (pins 1,2,3)    = Right channel, Stage 2 (Q=0.55)
  Op-amp 2 (pins 5,6,7)    = Right channel, Stage 3 (Q=1.29)
  Op-amp 3 (pins 8,9,10)   = Left channel, Stage 2 (Q=0.55)
  Op-amp 4 (pins 12,13,14) = Left channel, Stage 3 (Q=1.29)

Unity Gain Feedback Bridges (IN- tied to OUT):
  Right channel:  pin 2 → pin 1    (op-amp 1)
                  pin 6 → pin 7    (op-amp 2)
  Left channel:   pin 9 → pin 8    (op-amp 3)
                  pin 13 → pin 14  (op-amp 4)
```

> [!important] 4 Bridged Pin Pairs
> Each op-amp needs its IN- pin wired directly to its OUT pin for unity gain. **All 4 bridges are required** — missing any one will cause that stage to have no output.
> - **Op-amp 1:** pin 2 → pin 1 (Right)
> - **Op-amp 2:** pin 6 → pin 7 (Right)
> - **Op-amp 3:** pin 9 → pin 8 (Left)
> - **Op-amp 4:** pin 13 → pin 14 (Left)

> [!warning] Pin 4 = V+, Pin 11 = V- (GND)
> Do NOT confuse with pin 14 (which is 4OUT, not Vcc).
> The TL074 power pins are in the middle of the IC, not at the corners like the TL072.

#### Build Steps
1. [ ] Insert TL074 into socket (check orientation — notch/dot = pin 1 end)
2. [ ] Wire pin 2 (1IN-) to pin 1 (1OUT) — unity gain feedback for op-amp 1

#### Test 2: Op-Amp Power

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| V+ at pin 4 | Multimeter | 5.0V | | [ ] |
| GND at pin 11 | Multimeter | 0V | | [ ] |
| Current draw | Bench supply reading | < 10 mA | | [ ] |
| No shorts | Check current doesn't spike | Stable, no heat | | [ ] |

> [!note] No Vbias Test Needed
> Pin 3 (1IN+) connects to the filter network, not to Vbias.
> DC bias comes through R_in → R_s2a → R_s2b from the input signal's DC offset.

---

### Stage 3: First Sallen-Key (Q = 0.55) — Right Channel

Build the first active 2nd-order low-pass filter around op-amp 1. This stage has Q=0.55 (slightly underdamped) — it rolls off gently without peaking.

#### Schematic
```
                                            +------ pin 1 (1OUT) ---> To Stage 4
                                            |
                                          [C_s2b]
                                          10nF
                                            |
TP1 ----[R_s2a 910Ω]----+----[R_s2b 910Ω]--+------ pin 3 (1IN+)
                         |
                       [C_s2a]                    pin 2 (1IN-) ---- pin 1 (1OUT)
                       8.2nF                      (direct wire for unity gain)
                         |
                        GND
```

#### Build Steps
1. [ ] Measure R_s2a and R_s2b — confirm both ~910Ω
2. [ ] Keep the unity-gain feedback wire (pin 2 to pin 1)
3. [ ] Solder R_s2a (910Ω) from TP1 to a new node "TP2"
4. [ ] Solder C_s2a (8.2nF) from TP2 to GND
5. [ ] Solder R_s2b (910Ω) from TP2 to pin 3 (1IN+)
6. [ ] Solder C_s2b (10nF) from pin 3 (1IN+) to pin 1 (1OUT)

> [!note] Sallen-Key Unity Gain Low-Pass
> - IN- connects directly to OUT (unity gain buffer)
> - C_s2b provides feedback from output to the IN+ node
> - The filter action comes from the R-R-C-C network
> - Pin 3 gets DC bias through R_s2a and R_s2b from the input signal

#### Test 3: First Sallen-Key Verification

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| R_s2a value | Multimeter (power off) | 910 Ω ± 5% | | [ ] |
| R_s2b value | Multimeter (power off) | 910 Ω ± 5% | | [ ] |
| Continuity: TP1 → pin 3 | Through R_s2a + R_s2b | Beep | | [ ] |
| Resistance: TP1 → pin 3 | Measure | ~1.82 kΩ (2× 910Ω) | | [ ] |
| Continuity: TP2 → GND | Through C_s2a | Beep (brief) | | [ ] |
| Continuity: pin 3 → pin 1 | Through C_s2b | Beep (brief) | | [ ] |
| Feedback: pin 2 → pin 1 | Continuity | Beep (direct wire) | | [ ] |
| No short: pin 3 → GND | Resistance | High (not shorted) | | [ ] |

---

### Stage 4: Second Sallen-Key (Q = 1.29) — Right Channel

Build the second active 2nd-order low-pass filter around op-amp 2. This stage has Q=1.29 — it creates a slight peak near the cutoff frequency that helps maintain a flat combined passband (Butterworth-like response when cascaded with the Q=0.55 stage).

The input comes from pin 1 (Stage 3 output / op-amp 1 output).

#### Schematic
```
                                                +------ pin 7 (2OUT) ---> Output
                                                |
                                              [C_s3b]
                                              10nF
                                                |
pin 1 (1OUT) ----[R_s3a 2kΩ]----+----[R_s3b 2kΩ]--+------ pin 5 (2IN+)
                                 |
                               [C_s3a]                    pin 6 (2IN-) ---- pin 7 (2OUT)
                               1.5nF                      (direct wire for unity gain)
                                 |
                                GND
```

#### Build Steps
1. [ ] Measure R_s3a and R_s3b — confirm both ~2kΩ
2. [ ] Solder unity gain feedback: pin 6 (2IN-) to pin 7 (2OUT)
3. [ ] Solder R_s3a (2kΩ) from pin 1 (Stage 3 output) to a new node "TP3"
4. [ ] Solder C_s3a (1.5nF) from TP3 to GND
5. [ ] Solder R_s3b (2kΩ) from TP3 to pin 5 (2IN+)
6. [ ] Solder C_s3b (10nF) from pin 5 (2IN+) to pin 7 (2OUT)

> [!warning] Q = 1.29 Stage — Layout Sensitive
> This higher-Q stage is more sensitive to parasitic capacitance and layout.
> Keep lead lengths short and bypass cap close to the TL074 power pins.
> If oscillation occurs, check the 100nF bypass cap first.

#### Test 4: Second Sallen-Key Verification

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| R_s3a value | Multimeter (power off) | 2 kΩ ± 5% | | [ ] |
| R_s3b value | Multimeter (power off) | 2 kΩ ± 5% | | [ ] |
| Continuity: pin 1 → pin 5 | Through R_s3a + R_s3b | Beep | | [ ] |
| Resistance: pin 1 → pin 5 | Measure | ~4 kΩ (2× 2kΩ) | | [ ] |
| Continuity: TP3 → GND | Through C_s3a | Beep (brief) | | [ ] |
| Continuity: pin 5 → pin 7 | Through C_s3b | Beep (brief) | | [ ] |
| Feedback: pin 6 → pin 7 | Continuity | Beep (direct wire) | | [ ] |

#### DC Voltage Check (power on, no input signal)

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| Pin 1 (1OUT) | Multimeter to GND | ~0V (no bias yet) | | [ ] |
| Pin 7 (2OUT) | Multimeter to GND | ~0V (no bias yet) | | [ ] |
| Current draw | Bench supply | < 10 mA | | [ ] |

> [!tip] Don't worry if outputs float near 0V
> Without the Pi connected, there's no DC bias feeding through the signal path. The op-amp outputs may sit at 0V, near ground, or float unpredictably. This is normal — they'll settle at ~2.5V once the Pi's PWM signal provides the DC offset.

---

### Stage 5: Output Coupling Capacitor + RCA Jack

Add the DC blocking capacitor and wire the PCB-mount dual RCA jack.

#### Schematic
```
    pin 7 (2OUT) ----[C_out 6.8µF]----+---- RCA Jack (Right signal pin)
                      (+ toward op)    |
                                      GND ---- RCA Jack (Right ground pin)
```

#### RCA Jack Pin Identification

> [!important] Verify Pins with Multimeter
> Before soldering, use a multimeter in continuity mode to identify the RCA jack pins:
> 1. Touch one probe to the **center pin** inside an RCA socket
> 2. Touch the other probe to each solder pin on the bottom
> 3. The pin that beeps = **Signal** for that channel
> 4. Repeat for the other socket
> 5. Remaining pin(s) = **Ground** (verify by touching the outer shell of a socket)

```
    Dual RCA Jack (PCB-mount)
    Viewed from front:

    [White/Left]  [Red/Right]

    Viewed from solder side (pins facing you):

      GND   L-sig   R-sig   GND     (typical layout — verify!)
       |      |       |       |
       |      |       |       |

    L-sig  → Left C_out output
    R-sig  → Right C_out output
    GND    → Star ground point (both ground pins)
```

#### Build Steps
1. [ ] Identify RCA jack signal and ground pins with multimeter continuity test
2. [ ] Solder C_out (6.8µF electrolytic) from pin 7 output
3. [ ] Observe polarity: **+ side toward op-amp** (higher DC voltage)
4. [ ] Mount dual RCA jack on proto board edge
5. [ ] Connect C_out output to Right signal pin on RCA jack (Red)
6. [ ] Connect Right ground pin to star ground point

#### Test 5: Output Verification

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| Continuity: pin 7 → RCA R sig | Through C_out | Beep (brief) | | [ ] |
| Continuity: RCA R gnd → GND | Direct wire | Beep | | [ ] |
| No short: RCA R sig → GND | Resistance | High (not shorted) | | [ ] |
| C_out polarity | Visual check | + toward pin 7 | | [ ] |

---

### Stage 6: Left Channel — Input RC

Same as right channel: R_in (2.2kΩ) + C_in (1.5nF). This will connect to GPIO18 (Left PWM).

#### Schematic
```
    Input ----[R_in 2.2kΩ]----+---- Output (to Stage 7)
                               |
                             [C_in]
                             1.5nF
                               |
                              GND
```

#### Build Steps
1. [ ] Solder R_in (2.2kΩ) — input side open (will connect to Pi GPIO18)
2. [ ] Solder C_in (1.5nF) from R_in output to GND
3. [ ] Mark this junction as "TP1-L"

---

### Stage 7: Left Channel — First Sallen-Key (Q = 0.55)

Same wiring pattern as the right channel Stage 3, but on **op-amp 3** (pins 8, 9, 10).

#### Schematic
```
                                              +------ pin 8 (3OUT) ---> To Stage 8
                                              |
                                            [C_s2b]
                                            10nF
                                              |
TP1-L ----[R_s2a 910Ω]----+----[R_s2b 910Ω]--+------ pin 10 (3IN+)
                           |
                         [C_s2a]                    pin 9 (3IN-) ---- pin 8 (3OUT)
                         8.2nF                      (direct wire for unity gain)
                           |
                          GND
```

#### Build Steps
1. [ ] Solder unity gain feedback: pin 9 (3IN-) to pin 8 (3OUT)
2. [ ] Solder R_s2a (910Ω) from TP1-L to new node "TP2-L"
3. [ ] Solder C_s2a (8.2nF) from TP2-L to GND
4. [ ] Solder R_s2b (910Ω) from TP2-L to pin 10 (3IN+)
5. [ ] Solder C_s2b (10nF) from pin 10 (3IN+) to pin 8 (3OUT)

---

### Stage 8: Left Channel — Second Sallen-Key (Q = 1.29)

Same wiring pattern as the right channel Stage 4, but on **op-amp 4** (pins 12, 13, 14).

Input comes from pin 8 (Stage 7 output / op-amp 3 output).

#### Schematic
```
                                                  +------ pin 14 (4OUT) ---> Output
                                                  |
                                                [C_s3b]
                                                10nF
                                                  |
pin 8 (3OUT) ----[R_s3a 2kΩ]----+----[R_s3b 2kΩ]--+------ pin 12 (4IN+)
                                 |
                               [C_s3a]                    pin 13 (4IN-) ---- pin 14 (4OUT)
                               1.5nF                      (direct wire for unity gain)
                                 |
                                GND
```

#### Build Steps
1. [ ] Solder unity gain feedback: pin 13 (4IN-) to pin 14 (4OUT)
2. [ ] Solder R_s3a (2kΩ) from pin 8 (3OUT) to new node "TP3-L"
3. [ ] Solder C_s3a (1.5nF) from TP3-L to GND
4. [ ] Solder R_s3b (2kΩ) from TP3-L to pin 12 (4IN+)
5. [ ] Solder C_s3b (10nF) from pin 12 (4IN+) to pin 14 (4OUT)

---

### Stage 9: Left Channel — Output Cap + RCA

#### Build Steps
1. [ ] Solder C_out (6.8µF electrolytic) from pin 14, **+ side toward pin 14**
2. [ ] Connect C_out output to Left signal pin on RCA jack (White)
3. [ ] Connect Left ground pin to star ground point

#### Left Channel Verification

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| Feedback: pin 9 → pin 8 | Continuity | Beep | | [ ] |
| Continuity: TP1-L → pin 10 | Through R_s2a + R_s2b | Beep | | [ ] |
| Resistance: TP1-L → pin 10 | Measure | ~1.82 kΩ | | [ ] |
| Continuity: TP2-L → GND | Through C_s2a | Beep (brief) | | [ ] |
| Continuity: pin 10 → pin 8 | Through C_s2b | Beep (brief) | | [ ] |
| Feedback: pin 13 → pin 14 | Continuity | Beep | | [ ] |
| Continuity: pin 8 → pin 12 | Through R_s3a + R_s3b | Beep | | [ ] |
| Resistance: pin 8 → pin 12 | Measure | ~4 kΩ | | [ ] |
| Continuity: TP3-L → GND | Through C_s3a | Beep (brief) | | [ ] |
| Continuity: pin 12 → pin 14 | Through C_s3b | Beep (brief) | | [ ] |
| Continuity: pin 14 → RCA L sig | Through C_out | Beep (brief) | | [ ] |
| No short: RCA L sig → GND | Resistance | High | | [ ] |

---

### Stage 10: Final Integration with Raspberry Pi

> [!note] Prerequisites
> Ensure the Pi is already configured with `audremap` overlay and Raspotify.
> See [[Pi Zero 2W PWM Audio Filter#Raspberry Pi Configuration]] and [[Pi Zero 2W PWM Audio Filter#Raspotify Installation]].

#### Wiring

| Pi Pin | Function | Connect To |
|--------|----------|------------|
| Pin 12 (GPIO18) | Left PWM | Left filter R_in input (op-amps 3&4 side) |
| Pin 35 (GPIO19) | Right PWM | Right filter R_in input (op-amps 1&2 side) |
| Pin 2 (5V) | Power | TL074 pin 4 (V+) |
| Pin 6 (GND) | Ground | Star ground point |

```
    Pi Zero 2W                    5th Order Filter                    RCA Jack
    +--------+               +-------------------------+           +----------+
    | GPIO19 |---> R_in(R) --| SK1(Q=0.55) → SK2(Q=1.29) |--C_out--| R (red)  |
    |        |               |   (op-amps 1&2, pins 1-7)  |        |          |
    | GPIO18 |---> R_in(L) --| SK3(Q=0.55) → SK4(Q=1.29) |--C_out--| L (white)|
    |        |               |   (op-amps 3&4, pins 8-14)  |        |          |
    |   5V   |-------------->| TL074 V+ (pin 4)           |        |          |
    |   GND  |------★------->| TL074 V- (pin 11)          |------->| GND      |
    +--------+    star       +-------------------------+           +----------+
                  ground
```

#### Build Steps
1. [ ] Connect GPIO18 (pin 12) → Left filter input (R_in, op-amps 3&4 side)
2. [ ] Connect GPIO19 (pin 35) → Right filter input (R_in, op-amps 1&2 side)
3. [ ] Connect 5V (pin 2) → TL074 V+ (pin 4)
4. [ ] Connect GND (pin 6) → Star ground point
5. [ ] Connect RCA jack to speakers or preamp
6. [ ] Power on Pi and wait for Raspotify to start
7. [ ] Set ALSA volume: `amixer sset PCM 75%`

#### DC Voltage Check (Pi powered, no music playing)

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| Pin 4 (V+) | Multimeter to GND | 5.0V | | [ ] |
| Pin 1 (R SK1 out) | Multimeter to GND | ~2.5V | | [ ] |
| Pin 7 (R SK2 out) | Multimeter to GND | ~2.5V | | [ ] |
| Pin 8 (L SK1 out) | Multimeter to GND | ~2.5V | | [ ] |
| Pin 14 (L SK2 out) | Multimeter to GND | ~2.5V | | [ ] |
| After C_out (R) | Multimeter to GND | ~0V | | [ ] |
| After C_out (L) | Multimeter to GND | ~0V | | [ ] |

> [!important] Key Check: All Op-Amp Outputs at ~2.5V
> If any output reads 0V or 5V (stuck at rail), that channel has a wiring problem.
> Go back and check continuity of the signal path and feedback wires for that channel.

#### Listening Tests

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| Spotify Connect visible | Check Spotify app | "Pi Zero Audio" appears | | [ ] |
| Audio playback | Play music | Clean audio from speakers | | [ ] |
| No PWM whine | Listen carefully at idle | No high-frequency noise | | [ ] |
| Stereo separation | Play stereo test track | Correct L/R | | [ ] |
| Volume control | Adjust in Spotify | Smooth volume change | | [ ] |
| Bass response | Play bass-heavy track | Full, not thin | | [ ] |
| Preamp passthrough | Connect to Schiit Saga | Cleaner than 3rd order | | [ ] |

> [!tip] Quick Stereo Test
> SSH into the Pi and run:
> ```bash
> speaker-test -t sine -f 440 -c 2 -s 1  # Left channel only
> speaker-test -t sine -f 440 -c 2 -s 2  # Right channel only
> ```
> This confirms correct L/R channel mapping without needing Spotify.

#### Volume Calibration

Start at 75% (same as 3rd order optimal) and adjust if needed:

| ALSA PCM Level | Result |
|----------------|--------|
| 96% (0 dB) | |
| 85% (-12 dB) | |
| 80% (-17 dB) | |
| 75% (-22.6 dB) | |
| 70% (-28 dB) | |

**Set volume with:** `amixer sset PCM 75%`

#### Comparison vs 3rd Order

| Test | 3rd Order Result | 5th Order Result |
|------|-----------------|-----------------|
| Direct to speakers | Clean, minimal noise | |
| Through Schiit Saga (low gain) | Acceptable | |
| Through Schiit Saga (high gain) | Noticeable noise floor | |
| PWM attenuation @ 31.25 kHz | -40.6 dB | |

---

## Troubleshooting

> See also: [[Build Guide - 3rd Order PWM Filter#Troubleshooting]] for common issues (high-pass response, no output, distorted output, hum/buzz, weak bass).

### 5th Order Specific Issues

### No Audio Output
- [ ] Check all 4 unity-gain feedback wires: pin 2→1, pin 6→7, pin 9→8, pin 13→14
- [ ] Verify signal path continuity: GPIO → R_in → R_s2a → R_s2b → pin 3 (IN+)
- [ ] Confirm DC voltages at op-amp outputs (~2.5V with Pi connected)
- [ ] Check C_out polarity (+ toward op-amp)

### Audio on One Channel Only
- [ ] Check the silent channel's R_in connection to the correct GPIO
- [ ] Verify that channel's feedback wires and signal path
- [ ] Measure DC voltage at that channel's op-amp outputs

### Oscillation or Ringing
- [ ] **Most likely:** 100nF bypass cap too far from TL074 pins 4/11 — move it closer
- [ ] Lead lengths too long on Stage 3 (Q=1.29) — shorten connections
- [ ] Stray capacitance — keep component leads short on proto board

### Wrong Channel Mapping
- [ ] Verify TL074 pin numbering: op-amps 1&2 (pins 1-7) = Right, op-amps 3&4 (pins 8-14) = Left
- [ ] Pin 4 = V+ (power), NOT an op-amp pin
- [ ] Pin 11 = V- (GND), NOT an op-amp pin

### Stage 3 (Q=1.29) Instability
- [ ] Higher Q stage is more sensitive to parasitic effects
- [ ] Check that C_s3b (10nF) connects from pin 5 (2IN+) to pin 7 (2OUT), not to GND
- [ ] Ensure unity gain feedback (pin 6 to pin 7) is solid
- [ ] Try adding a small resistor (10Ω) in series with C_s3b to dampen oscillation

### Distorted / Clipped Audio
- [ ] Check ALSA volume: `amixer sset PCM 75%` (96% will clip)
- [ ] Verify 5V supply is stable under load (measure with multimeter during playback)
- [ ] Check for solder bridges between adjacent proto board pads

---

## Notes & Observations

### Build Session: 2026-02-23

**Equipment Used:**
- Multimeter
- Adjustable bench power supply (5.0V, 50mA limit)
- Proto board (direct solder, no breadboard prototyping)

**Key Observations:**

**Test Results Summary:**

---

## References

- [[Pi Zero 2W PWM Audio Filter]] — Main project page
- [[Build Guide - 3rd Order PWM Filter]] — 3rd order build reference
- [TL074 Datasheet](https://www.ti.com/product/TL074)
- [Sallen-Key Filter Design (TI SLOA024B)](https://www.ti.com/lit/an/sloa024b/sloa024b.pdf)

---
