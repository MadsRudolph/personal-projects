---
title: Build Guide - 3rd Order PWM Filter
type: build-guide
tags:
  - electronics
  - raspberry-pi
  - audio
  - active-project
  - build-log
status: Left Channel Complete
started: 2026-02-01
updated: 2026-02-01
build-date: 2026-02-01
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
| Component | Value | Qty | Notes |
|-----------|-------|-----|-------|
| R1 | 2.2 kΩ | 1 | Input RC stage |
| R2, R3 | 1 kΩ | 2 | Sallen-Key filter |
| C1 | 2.2 nF | 1 | Film cap (marked 2n2) |
| C2 | 4.7 nF | 1 | Film cap (marked 4.7 or 472) |
| C3 | 10 nF | 1 | Film cap (marked 10n or 103) |
| C_out | 6.8 µF electrolytic | 1 | Output DC blocking |
| C_bypass | 100 nF ceramic | 1 | Op-amp power bypass |
| TL072 | Dual op-amp | 1 | TL072CP used |

> [!note] Simplified Design
> The Vbias network (10kΩ resistors + 10µF cap) is **not needed** in this design.
> DC bias comes through the signal path via the input DC offset.

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

### Stage 0: Power Supply

> [!important] Simplified Design
> The original Vbias resistor divider network is **NOT needed**.
> DC bias is provided via the waveform generator's DC offset (2.5V) through the signal path.

#### Build Steps
1. [x] Connect bench supply +5V to breadboard power rail
2. [x] Connect bench supply GND to breadboard ground rail
3. [x] Add 100nF bypass cap near where op-amp will be placed

#### Test 0: Power Supply

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| Vcc | Multimeter: +5V to GND | 5.0V ± 0.1V | 5.0V | [x] |

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

| Test            | Method                  | Expected      | Actual    | Pass |
| --------------- | ----------------------- | ------------- | --------- | ---- |
| fc (calculated) | 1/(2π × 2.2kΩ × 2.2nF)  | ~32.9 kHz     | 32.9 kHz  | [x]  |
| fc (measured)   | -3dB point on Bode plot | ~33 kHz       | 28.5 kHz  | [x]  |
| Passband        | Gain at 1 kHz           | 0 dB (unity)  | 0 dB      | [x]  |
| Roll-off        | Slope above fc          | -20 dB/decade | -20 dB/dec| [x]  |

> [!success] Stage 1 Complete
> Measured fc slightly lower than calculated due to component tolerances.

**Quick Sine Test:**
- 1 kHz sine, 1 Vpp → Output should be ~1 Vpp
- 30 kHz sine, 1 Vpp → Output should be ~0.7 Vpp (-3dB)

> [!tip] Sanity Check
> If fc is way off, measure R1 and C1 with multimeter. Component tolerances matter!

---

### Stage 2: Op-Amp Installation

Install the TL072 and verify power connections.

#### TL072CP Pinout
```
        +---u---+
 1OUT  -| 1   8 |- Vcc (+5V)
 1IN-  -| 2   7 |- 2OUT
 1IN+  -| 3   6 |- 2IN-
 Vcc-  -| 4   5 |- 2IN+
        +-------+

Note: Pin 4 connects to GND (single supply)
      Op-amp 1 (pins 1,2,3) = Left channel
      Op-amp 2 (pins 5,6,7) = Right channel
```

#### Build Steps
1. [x] Insert TL072 into breadboard (straddle center groove)
2. [x] Connect pin 8 to +5V rail
3. [x] Connect pin 4 to GND rail
4. [x] Place 100nF bypass cap directly across pins 4 and 8 (short leads!)
5. [x] Connect pin 2 (IN-) to pin 1 (OUT) - unity gain feedback

#### Test 2: Op-Amp Power

| Test         | Method     | Expected | Actual | Pass |
|--------------|------------|----------|--------|------|
| Vcc at pin 8 | Multimeter | 5.0V     | 5.0V   | [x]  |
| GND at pin 4 | Multimeter | 0V       | 0V     | [x]  |

> [!note] No Vbias Test Needed
> In the simplified design, pin 3 (IN+) connects to the filter network, not to Vbias.
> DC bias comes through R1→R2→R3 from the input signal's DC offset.

---

### Stage 3: Sallen-Key Filter (2nd Order)

Now build the active 2nd-order low-pass filter around the op-amp.

#### Schematic
```
                                        +------ pin 1 (OUT) ---> Output
                                        |
                                      [C3]
                                      10nF
                                        |
TP1 ----[R2 1kΩ]----+----[R3 1kΩ]------+------ pin 3 (IN+)
                    |
                  [C2]                         pin 2 (IN-) ---- pin 1 (OUT)
                  4.7nF                        (direct wire for unity gain)
                    |
                   GND
```

#### Build Steps
1. [x] Keep the unity-gain feedback wire (pin 2 to pin 1)
2. [x] Connect R2 (1kΩ) from TP1 to a new node "TP2"
3. [x] Connect C2 (4.7nF) from TP2 to GND
4. [x] Connect R3 (1kΩ) from TP2 to pin 3 (IN+)
5. [x] Connect C3 (10nF) from pin 3 (IN+) to pin 1 (OUT)

> [!note] Sallen-Key Unity Gain Low-Pass
> - IN- connects directly to OUT (unity gain buffer)
> - C3 provides feedback from output to the IN+ node
> - The filter action comes from R2-R3-C2-C3 network
> - Pin 3 is no longer connected to Vbias (signal path provides DC bias through R2-R3)

#### Test 3: Complete Filter Response

**Setup:**
- W1 → R1 input (beginning of filter)
- W1 settings: 1 Vpp, **Offset: 2.5V** (critical!)
- CH1 → Input
- CH2 → pin 1 (output)

> [!important] DC Offset Required
> The waveform generator MUST have 2.5V DC offset to bias the op-amp at mid-rail.
> Without this, the filter will not work correctly (op-amp can't output near 0V).

**WaveForms - Network Analyzer:**
1. Sweep: 100 Hz to 100 kHz
2. Amplitude: 1 Vpp
3. Offset: 2.5V

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| fc (combined) | -3dB point | ~19 kHz | ~15-20 kHz | [x] |
| Roll-off | Slope above fc | -60 dB/decade | ~60 dB/dec | [x] |
| Passband gain | Gain at 1 kHz | 0 dB ± 1 dB | 0 dB | [x] |
| @ 31.25 kHz | Attenuation at PWM freq | ≥ -10 dB | -40.6 dB | [x] |

> [!success] Stage 3 Complete
> Filter response verified with Network Analyzer sweep.

**Measured Filter Response:**
![Filter frequency response - Network Analyzer](../../Resources/Pi%20Zero%20PWM%20Filter/images/filter-response-working.png)
*Network Analyzer sweep showing flat passband and rolloff starting around 15-20 kHz*

**Time Domain Test - PWM Simulation:**
- W1: Square wave, 31.25 kHz, 3.3 Vpp, Offset 1.65V, 50% duty
- CH1: Input
- CH2: Output

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| PWM filtering | Visual on scope | Rounded waveform | Shark-fin shape | [x] |
| Input amplitude | Measure Vpp | 3.3 Vpp | 3.28 Vpp | [x] |
| Output amplitude | Measure Vpp | Reduced | 29.6 mVpp | [x] |
| Attenuation | 20×log10(out/in) | ≥ -10 dB | **-40.6 dB** | [x] |

> [!success] PWM Filtering Verified
> The 31.25 kHz PWM carrier is attenuated by over 40 dB - far exceeding the -10 dB target.
> Square wave input is converted to smooth rounded waveform at output.

**PWM Filtering - Time Domain:**
![PWM filtering test - oscilloscope](../../Resources/Pi%20Zero%20PWM%20Filter/images/pwm-filtering-test.png)
*Yellow: 31.25 kHz square wave input (3.28 Vpp). Cyan: Filtered output (29.6 mVpp) showing characteristic "shark-fin" shape.*

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

Once Left channel passes all tests, duplicate for Right channel using the second op-amp in the TL072.

#### Right Channel Pinout (Op-Amp 2)
```
Pin 5 = 2IN+  (connect to R3 and C3)
Pin 6 = 2IN-  (connect to pin 7)
Pin 7 = 2OUT  (filter output)
```

#### Build Steps
1. [ ] Build RC input stage (R1, C1) for right channel
2. [ ] Connect R2 from TP1 to TP2
3. [ ] Connect C2 from TP2 to GND
4. [ ] Connect R3 from TP2 to pin 5 (2IN+)
5. [ ] Connect C3 from pin 5 to pin 7 (2OUT)
6. [ ] Connect pin 6 (2IN-) to pin 7 (2OUT)
7. [ ] Add output coupling cap from pin 7

| Right Channel Test | Expected | Actual | Pass |
|--------------------|----------|--------|------|
| fc | ~19 kHz | | [ ] |
| Passband gain | 0 dB | | [ ] |
| PWM attenuation | ≥ -10 dB | | [ ] |
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

### High-Pass Response Instead of Low-Pass
- [ ] **Most likely:** Waveform generator has no DC offset - set to 2.5V
- [ ] Op-amp IN+ connected to a Vbias network with large bypass cap (remove Vbias connection)
- [ ] C3 connected to GND instead of to output

**Example - No DC Offset (shows high-pass response):**
![Troubleshooting - high-pass response without DC offset](../../Resources/Pi%20Zero%20PWM%20Filter/images/troubleshoot-highpass-no-offset.png)
*Signal is attenuated at low frequencies - op-amp cannot output near 0V without proper bias.*

### Cutoff Frequency Too Low (~300-400 Hz)
- [ ] Pin 3 (IN+) still connected to Vbias with 10µF bypass cap
- [ ] Wrong capacitor values (µF instead of nF)
- [ ] Extra capacitor in signal path

**Example - Vbias bypass cap in signal path:**
![Troubleshooting - cutoff too low due to Vbias](../../Resources/Pi%20Zero%20PWM%20Filter/images/troubleshoot-lowcutoff-vbias.png)
*10µF Vbias bypass cap shunts signal to ground, causing ~350 Hz cutoff instead of 19 kHz.*

### No Output
- [ ] Check power supply connections
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

### Build Session: 2026-02-01

**Key Lessons Learned:**

1. **Vbias Network Not Needed:** The original design included a resistor divider for Vbias. This is unnecessary - DC bias comes through the signal path when the input has a DC offset.

2. **DC Offset is Critical:** When testing with the AD3, the waveform generator MUST have 2.5V DC offset. Without this, the op-amp operates near the negative rail and produces incorrect results (high-pass response instead of low-pass).

3. **Bypass Cap Essential:** The 100nF bypass cap across the op-amp power pins is critical. Without it, strange phase shifts and instability can occur.

4. **Sallen-Key Topology:** The correct unity-gain Sallen-Key low-pass has C3 connected from IN+ to OUT (not to GND). This provides the feedback that creates the 2nd order response.

5. **Component Markings:**
   - 2n2 = 2.2 nF
   - 4.7K400 = 4.7 nF, 10%, 400V
   - 10nK63 = 10 nF, 10%, 63V

**Test Results Summary:**
- Stage 1 fc: 28.5 kHz (expected 33 kHz) - component tolerance
- Combined fc: ~15-20 kHz (expected 19 kHz) - acceptable
- PWM attenuation: **-40.6 dB** at 31.25 kHz (target was -10 dB) - excellent!

**Equipment Used:**
- Analog Discovery 3 with WaveForms
- Adjustable bench power supply (5.0V)
- Breadboard prototype

---

## References

- [[Pi Zero 2W PWM Audio Filter]] - Main project page
- [TL072 Datasheet](https://www.ti.com/product/TL072)
- [Analog Discovery 3 Reference Manual](https://digilent.com/reference/test-and-measurement/analog-discovery-3/start)
- [WaveForms Software](https://digilent.com/shop/software/digilent-waveforms/)

---
