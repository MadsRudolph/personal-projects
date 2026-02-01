---
title: Build Guide - 3rd Order PWM Filter
type: build-guide
tags:
  - electronics
  - raspberry-pi
  - audio
  - active-project
  - build-log
status: In Progress
started: 2026-02-01
updated: 2026-02-01
parent: "[[Pi Zero 2W PWM Audio Filter]]"
---

# Build Guide - 3rd Order PWM Filter

> [!summary] **Overview**
> Step-by-step build and test guide for the 3rd order (RC + Sallen-Key) PWM filter.
> Each stage is tested with the **Analog Discovery 3** before proceeding.
> - Build one channel first (Left), verify, then duplicate for Right
> - Test at every stage to catch issues early

---

## Equipment Required

### Test Equipment
| Item | Purpose |
|------|---------|
| **Analog Discovery 3** | Waveform generator + oscilloscope |
| WaveForms software | AD3 control software |
| Breadboard | Prototyping |
| Jumper wires | Connections |
| Multimeter | DC voltage checks |

### Components (Single Channel)
| Component | Value | Qty |
|-----------|-------|-----|
| R1 | 2.2 kΩ | 1 |
| R2, R3 | 1 kΩ (or 1.05 kΩ) | 2 |
| R_bias | 10 kΩ | 2 |
| C1 | 2.2 nF | 1 |
| C2 | 4.7 nF | 1 |
| C3 | 10 nF | 1 |
| C_out | 6.8 µF electrolytic | 1 |
| C_bias | 10 µF electrolytic | 1 |
| C_bypass | 100 nF ceramic | 1 |
| TL072 | Dual op-amp | 1 |

### Power Supply
- **Recommended:** Adjustable bench power supply set to 5.0V
- Alternative: AD3 V+ supply (limited current)
- Current draw: ~10 mA per channel
- Set current limit to ~50 mA during testing (protects against shorts)

---

## AD3 Setup

### WaveForms Configuration

**Oscilloscope Settings:**
- CH1: Filter input (after R1)
- CH2: Filter output
- Trigger: CH1, rising edge
- Time base: Adjust per test (1ms/div for audio, 10µs/div for PWM)

**Waveform Generator Settings:**
- W1: Test signal source
- Output: 1 Vpp (start low to protect circuit)
- Load: High-Z

### AD3 Pinout Reference

| AD3 Pin | Function | Connect To |
|---------|----------|------------|
| W1 | Waveform out | Filter input |
| 1+ | Scope CH1+ | Test point |
| 1- | Scope CH1- | GND |
| 2+ | Scope CH2+ | Test point |
| 2- | Scope CH2- | GND |
| GND | Ground | Circuit GND (common with bench supply) |

### Bench Power Supply Setup

| Setting | Value |
|---------|-------|
| Voltage | 5.00 V |
| Current limit | 50 mA (protection) |
| Output | + to Vcc rail, - to GND rail |

> [!important] Common Ground
> Connect AD3 GND and bench supply GND to the same breadboard ground rail.

---

## Build Stages

---

### Stage 0: Power Supply & Bias Network

Build the bias network first - this creates the virtual ground (Vcc/2 = 2.5V) needed for single-supply op-amp operation.

#### Schematic
```
        +5V (from AD3 V+)
         |
        [10kΩ] R_bias1
         |
         +----[10µF]----GND    (C_bias, + toward Vbias)
         |
       Vbias (2.5V output)
         |
        [10kΩ] R_bias2
         |
        GND
```

#### Build Steps
1. [x] Insert two 10kΩ resistors in series on breadboard
2. [x] Connect top of R_bias1 to +5V rail
3. [x] Connect bottom of R_bias2 to GND rail
4. [x] Connect 10µF capacitor from Vbias junction to GND (observe polarity!)
5. [ ] Add 100nF bypass cap from +5V to GND near where op-amp will go

#### Test 0: Bias Voltage

| Test     | Method                         | Expected      | Actual | Pass |
| -------- | ------------------------------ | ------------- | ------ | ---- |
| Vcc      | Multimeter: +5V to GND         | 5.0V ± 0.1V   | check  | [ ]  |
| Vbias    | Multimeter: Vbias to GND       | 2.5V ± 0.1V   | check  | [ ]  |
| Vbias AC | Scope CH1 on Vbias, AC coupled | <10 mV ripple |        | [ ]  |

> [!warning] Stop if Vbias is not ~2.5V
> Check resistor values and connections before proceeding.

---

### Stage 1: Input RC Filter (1st Order)

This passive RC stage provides the first pole of the filter.

#### Schematic
```
    Input ----[R1 2.2kΩ]----+---- Output (to Stage 2)
                            |
                          [C1]
                          2.2nF
                            |
                           GND
```

#### Build Steps
1. [x] Add R1 (2.2kΩ) - input side left open for now
2. [x] Add C1 (2.2nF) from R1 output to GND
3. [x] Mark the junction of R1 and C1 as "TP1" (test point 1)

#### Test 1: RC Filter Response

**Setup:**
- W1 → R1 input
- CH1 (1+) → TP1 (R1/C1 junction)
- GND connected

**WaveForms - Network Analyzer:**
1. Open Network Analyzer instrument
2. Set sweep: 100 Hz to 100 kHz
3. Set amplitude: 1 Vpp
4. Run sweep

| Test            | Method                  | Expected      | Actual | Pass |
| --------------- | ----------------------- | ------------- | ------ | ---- |
| fc (calculated) | 1/(2π × 2.2kΩ × 2.2nF)  | ~32.9 kHz     |        | [ ]  |
| fc (measured)   | -3dB point on Bode plot | ~33 kHz       | 28.5   | [ ]  |
| Passband        | Gain at 1 kHz           | 0 dB (unity)  |        | [ ]  |
| Roll-off        | Slope above fc          | -20 dB/decade |        | [ ]  |

**Quick Sine Test:**
- 1 kHz sine, 1 Vpp → Output should be ~1 Vpp
- 30 kHz sine, 1 Vpp → Output should be ~0.7 Vpp (-3dB)

> [!tip] Sanity Check
> If fc is way off, measure R1 and C1 with multimeter. Component tolerances matter!

---

### Stage 2: Op-Amp Installation

Install the TL072 and verify it's working before adding the Sallen-Key components.

#### TL072 Pinout
```
        +---u---+
 1OUT  -| 1   8 |- Vcc (+5V)
 1IN-  -| 2   7 |- 2OUT
 1IN+  -| 3   6 |- 2IN-
 Vcc-  -| 4   5 |- 2IN+
        +-------+

Note: Pin 4 connects to GND (single supply)
      We'll use op-amp 1 (pins 1,2,3) for left channel
```

#### Build Steps
1. [x] Insert TL072 into breadboard (straddle center groove)
2. [x] Connect pin 8 to +5V rail
3. [x] Connect pin 4 to GND rail
4. [ ] Place 100nF bypass cap directly across pins 4 and 8
5. [x] Connect pin 3 (IN+) to Vbias (2.5V)
6. [x] Connect pin 2 (IN-) to pin 1 (OUT) - unity gain buffer config

#### Test 2: Op-Amp DC Operating Point

| Test              | Method            | Expected    | Actual | Pass |
| ----------------- | ----------------- | ----------- | ------ | ---- |
| Vcc at pin 8      | Multimeter        | 5.0V        | pass   | [ ]  |
| GND at pin 4      | Multimeter        | 0V          | pass   | [ ]  |
| Output DC (pin 1) | Multimeter to GND | 2.5V ± 0.2V | pass   | [ ]  |
| IN+ (pin 3)       | Multimeter to GND | 2.5V        | pass   | [ ]  |

#### Test 2b: Op-Amp AC Response (Unity Buffer)

**Setup:**
- W1 → 10µF cap → pin 3 (AC couple into IN+)
- CH1 → pin 3
- CH2 → pin 1 (output)

**Test:**
- 1 kHz sine, 500 mVpp
- Output should match input (unity gain, 0° phase shift)

| Test           | Method           | Expected                | Actual | Pass |
| -------------- | ---------------- | ----------------------- | ------ | ---- |
| Gain at 1 kHz  | CH2/CH1          | 1.0 (0 dB)              | check  | [ ]  |
| Phase at 1 kHz | Phase difference | ~0°                     | 204 us | [ ]  |
| Output swing   | Scope CH2        | Clean sine, no clipping |        | [ ]  |

> [!warning] If output is stuck at 0V or 5V
> - Check power connections
> - Verify Vbias is connected to IN+
> - Check for shorts

---

### Stage 3: Sallen-Key Filter (2nd Order)

Now build the active 2nd-order low-pass filter around the op-amp.

#### Schematic
```
    From TP1 ----[R2 1kΩ]----+----[R3 1kΩ]----+
                             |                 |
                           [C2]                |
                           4.7nF            [IN+]
                             |                 |    +-----+
                            GND    Vbias -----|+    |     |
                                              | OP  |-----+---> Output
                                   +----------|−    |
                                   |          +-----+
                                   |             |
                                  [C3]          Vcc/GND
                                  10nF
                                   |
                                  GND
```

#### Build Steps
1. [ ] Remove the unity-gain feedback wire (pin 2 to pin 1)
2. [ ] Connect R2 (1kΩ) from TP1 to a new node "TP2"
3. [ ] Connect R3 (1kΩ) from TP2 to pin 3 (IN+)
4. [ ] Connect C2 (4.7nF) from TP2 to GND
5. [ ] Connect C3 (10nF) from pin 1 (OUT) to pin 2 (IN-)
6. [ ] Connect pin 2 (IN-) to pin 1 (OUT) - this completes the Sallen-Key feedback
7. [ ] **Important:** Also connect pin 3 to Vbias through a high-value resistor (100kΩ) or remove direct Vbias connection and let the input signal bias the op-amp

> [!note] Sallen-Key Unity Gain Configuration
> In this topology, IN- connects directly to OUT (voltage follower in the feedback).
> The filter action comes from the RC network feeding IN+.

#### Revised Connections
```
TP1 ---[R2]---TP2---[R3]---+--- pin 3 (IN+)
               |           |
             [C2]      [Vbias via 100kΩ or input coupling]
               |
              GND

pin 1 (OUT) ---+--- Output
               |
             [C3]
               |
pin 2 (IN-) ---+
```

#### Test 3: Complete Filter Response

**Setup:**
- W1 → R1 input (beginning of filter)
- CH1 → TP1 (after 1st RC stage)
- CH2 → pin 1 (final output)

**WaveForms - Network Analyzer:**
1. Sweep: 100 Hz to 100 kHz
2. Amplitude: 1 Vpp
3. Compare response to Stage 1

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| fc (combined) | -3dB point | ~19 kHz | | [ ] |
| Roll-off | Slope above fc | -60 dB/decade (3rd order) | | [ ] |
| Passband gain | Gain at 1 kHz | 0 dB ± 1 dB | | [ ] |
| @ 31.25 kHz | Attenuation at PWM freq | ≥ -10 dB | | [ ] |

**Time Domain Test - PWM Simulation:**
- W1: Square wave, 31.25 kHz, 3.3 Vpp, 50% duty
- CH1: Input
- CH2: Output (should be heavily filtered, approaching triangle/sine)

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| PWM filtering | Visual on scope | Rounded waveform | | [ ] |
| Output amplitude | Measure Vpp | Reduced from input | | [ ] |

---

### Stage 4: Output Coupling Capacitor

Add the DC blocking capacitor for the final output.

#### Schematic
```
    pin 1 (OUT) ----[C_out 6.8µF]----+---- RCA Output
                     (+ toward op)   |
                                   [Load]
                                   10kΩ (simulated)
                                     |
                                    GND
```

#### Build Steps
1. [ ] Add C_out (6.8µF electrolytic) from pin 1 output
2. [ ] Observe polarity: + side toward op-amp (higher DC voltage)
3. [ ] Add 10kΩ load resistor to simulate amplifier input impedance

#### Test 4: Output Characteristics

**Setup:**
- W1 → Filter input (R1)
- CH2 → Final output (after C_out, across load)

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| DC offset | Multimeter at output | 0V ± 50mV | | [ ] |
| 1 kHz response | 1 kHz sine, measure output | ~1 Vpp (same as input) | | [ ] |
| 100 Hz response | 100 Hz sine, measure output | ~1 Vpp (check for bass loss) | | [ ] |
| 20 Hz response | 20 Hz sine, measure output | >0.9 Vpp (slight loss OK) | | [ ] |

> [!tip] Low Frequency Corner
> The output coupling cap + load forms a high-pass filter.
> fc = 1/(2π × 6.8µF × 10kΩ) ≈ 2.3 Hz - well below audio range.

---

### Stage 5: Full Audio Band Test

Verify the complete filter across the audio spectrum.

#### Test 5: Frequency Response Sweep

**WaveForms - Network Analyzer:**
- Sweep: 20 Hz to 50 kHz (log scale)
- Amplitude: 1 Vpp
- Reference: Input to R1
- Measure: Output after C_out

| Frequency | Expected Gain | Measured Gain | Pass |
|-----------|---------------|---------------|------|
| 20 Hz | ~0 dB | | [ ] |
| 100 Hz | 0 dB | | [ ] |
| 1 kHz | 0 dB | | [ ] |
| 10 kHz | 0 dB | | [ ] |
| 15 kHz | ~0 dB | | [ ] |
| 19 kHz | -3 dB | | [ ] |
| 31.25 kHz | ≤ -10 dB | | [ ] |
| 50 kHz | ≤ -20 dB | | [ ] |

#### Test 5b: THD Measurement

**WaveForms - Spectrum Analyzer:**
- Input: 1 kHz sine, 1 Vpp
- Measure output spectrum
- Look for harmonics (2 kHz, 3 kHz, etc.)

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| THD at 1 kHz | Spectrum analyzer | < 0.1% | | [ ] |
| Noise floor | No input, measure output | < 1 mVrms | | [ ] |

---

### Stage 6: PWM Audio Test

Test with actual PWM-like signals to verify filtering performance.

#### Test 6a: Simulated PWM (Square Wave)

**Setup:**
- W1: Square wave, 31.25 kHz, 3.3 Vpp (simulates Pi PWM)

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| Output waveform | Scope CH2 | Smooth, triangle-ish | | [ ] |
| Fundamental suppression | Spectrum | 31.25 kHz ≥ -10 dB down | | [ ] |

#### Test 6b: PWM with Audio Modulation

**Setup:**
- W1: PWM modulated signal (if WaveForms supports)
- Or: Use actual Pi PWM output

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| Audio recovery | Listen on headphones/amp | Clean audio | | [ ] |
| PWM whine | Listen for 31 kHz (may be inaudible) | Minimal/none | | [ ] |

---

## Build Second Channel

Once Left channel passes all tests, duplicate for Right channel:

1. [ ] Build identical bias network (or share with Left)
2. [ ] Build RC input stage (R1, C1)
3. [ ] Use second op-amp in TL072 (pins 5,6,7)
4. [ ] Build Sallen-Key stage
5. [ ] Add output coupling cap
6. [ ] Run abbreviated test suite

| Right Channel Test | Expected | Actual | Pass |
|--------------------|----------|--------|------|
| Vbias | 2.5V | | [ ] |
| fc | ~19 kHz | | [ ] |
| Passband gain | 0 dB | | [ ] |
| Channel match | L/R within 1 dB | | [ ] |

---

## Final Integration Test

### Test with Raspberry Pi

1. [ ] Configure Pi `/boot/config.txt` with PWM overlay
2. [ ] Install Raspotify
3. [ ] Connect GPIO18 → Left filter input
4. [ ] Connect GPIO19 → Right filter input
5. [ ] Connect filter outputs → RCA jacks → Active speakers

| Test | Method | Expected | Pass |
|------|--------|----------|------|
| Spotify Connect visible | Check Spotify app | "Pi Zero Audio" appears | [ ] |
| Audio playback | Play music | Clean audio from speakers | [ ] |
| No PWM whine | Listen carefully | No high-frequency noise | [ ] |
| Stereo separation | Play stereo test track | Correct L/R | [ ] |
| Volume control | Adjust in Spotify | Smooth volume change | [ ] |

---

## Troubleshooting

### No Output
- [ ] Check power supply connections
- [ ] Verify Vbias is 2.5V
- [ ] Check op-amp orientation (notch/dot = pin 1)
- [ ] Look for solder bridges or broken connections

### Distorted Output
- [ ] Input signal too hot (reduce amplitude)
- [ ] Clipping at op-amp (check headroom)
- [ ] Bad component (swap op-amp)

### High-Frequency Whine
- [ ] Filter not working - check component values
- [ ] Oscillation - add/check bypass caps
- [ ] Grounding issue - use star ground

### Hum or Buzz
- [ ] Ground loop - use single ground point
- [ ] Power supply noise - add more filtering
- [ ] Pickup from nearby electronics - shield or move

### Weak Bass
- [ ] Output coupling cap too small
- [ ] Load impedance too low
- [ ] Input coupling issue

---

## Notes & Observations

*Record your build notes here:*

```
Date:
Temperature:
Observations:


```

---

## References

- [[Pi Zero 2W PWM Audio Filter]] - Main project page
- [TL072 Datasheet](https://www.ti.com/product/TL072)
- [Analog Discovery 3 Reference Manual](https://digilent.com/reference/test-and-measurement/analog-discovery-3/start)
- [WaveForms Software](https://digilent.com/shop/software/digilent-waveforms/)

---
