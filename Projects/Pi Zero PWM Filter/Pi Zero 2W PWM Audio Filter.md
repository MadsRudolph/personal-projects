---
title: Pi Zero 2W PWM Audio Filter for Spotify Connect
type: project
tags:
  - electronics
  - raspberry-pi
  - audio
  - active-project
status: Working Prototype
started: 2026-02-01
updated: 2026-02-23
aliases:
  - Pi PWM Filter
  - Raspotify Audio
  - PWM to Line-Level
links:
  - "[[Illuminate 7Mk2/Illuminate 7Mk2 - Speaker Build]]"
  - "[[Build Guide - 3rd Order PWM Filter]]"
---

# Pi Zero 2W PWM Audio Filter for Spotify Connect

![Proto board build - Pi Zero 2W with 3rd order PWM filter](../../Resources/Pi%20Zero%20PWM%20Filter/images/proto-board-build.jpg)

> [!summary] **Project Goal**
> Build a filtered PWM audio output circuit for Raspberry Pi Zero 2W running Raspotify, converting PWM to stereo line-level output for active speakers via RCA.
> - Wireless Spotify Connect endpoint
> - Clean analog output from digital PWM
> - Two filter complexity options: 3rd or 5th order

---

## Quick Links

- [[#3rd Order Filter (RC + Sallen-Key)|3rd Order Design]]
- [[#5th Order Filter (RC + 2× Sallen-Key)|5th Order Design]]
- [[#Bill of Materials|Component List]]
- [[#Raspberry Pi Configuration|Pi Setup]]
- [[#Raspotify Installation|Raspotify]]
- [[Build Guide - 3rd Order PWM Filter|Build & Test Guide (3rd Order)]]
- [[Build Guide - 5th Order PWM Filter|Build & Test Guide (5th Order)]]

---

## System Overview

| Parameter | Specification |
|-----------|--------------|
| **Platform** | Raspberry Pi Zero 2W |
| **Software** | Raspotify (Spotify Connect) |
| **PWM Frequency** | 31.25 kHz |
| **Output** | Stereo line-level via RCA jack or screw terminal blocks |
| **Target** | Active speakers / amplifier input |
| **Optimal Volume** | ALSA PCM at 75% (-22.6 dB) |

### GPIO Pinout

| Function | GPIO | Pin | Description |
|----------|------|-----|-------------|
| **Left Channel** | GPIO18 | Pin 12 | PWM0 |
| **Right Channel** | GPIO19 | Pin 35 | PWM1 |
| **Ground** | GND | Pin 6, 9, 14, 20, 25, 30, 34, 39 | Common ground |
| **5V Power** | 5V | Pin 2, 4 | Op-amp supply (if using 5V tolerant) |

---

## Filter Design Options

### 3rd Order Filter (RC + Sallen-Key)

A simpler design using a passive RC stage followed by an active 2nd-order Sallen-Key low-pass filter.

| Parameter | Value |
|-----------|-------|
| **Topology** | 1st order RC + 2nd order Sallen-Key |
| **Cutoff Frequency** | ~19 kHz |
| **PWM Attenuation** | -10 dB @ 31.25 kHz |
| **Op-Amp** | TL072 (dual) |
| **Supply** | Single 5V with virtual ground |

#### Component Values

| Component | Value | Purpose |
|-----------|-------|---------|
| R1 | 2.2 kΩ | Input RC filter |
| R2, R3 | 1.05 kΩ | Sallen-Key resistors |
| C1 | 2.2 nF | Input RC filter |
| C2 | 4.7 nF | Sallen-Key capacitor |
| C3 | 10 nF | Sallen-Key capacitor |
| C_out | 6.8 µF | DC blocking output cap |

> [!note]- 3rd Order Schematic (Left Channel)
> ```
>      PWM Input              +5V
>      (GPIO18)                |
>         |              +-----+-----+
>        [R1]            |           |
>        2.2k            |         [100nF]
>         |              |           |
>         +---[C1]---GND |          GND
>         |   2.2nF
>         |
>        [R2]
>        1.05k
>         |
>         +-----+------+
>         |     |      |
>        [C2]  [R3]    |
>        4.7nF 1.05k   |
>         |     |      +------[+]
>        GND    +------+      TL072
>               |      +------[-]
>              [C3]    |        |
>              10nF    +--------+
>               |
>              GND
>
>         Output---[C_out]---RCA Left
>                  6.8µF
> ```
>
> **Note:** Vbias network not needed — DC bias comes through the signal path.
> See [[Build Guide - 3rd Order PWM Filter]] for full wiring details.

---

### 5th Order Filter (RC + 2× Sallen-Key)

Higher complexity design with superior PWM rejection. Uses cascaded Sallen-Key stages with optimized Q factors.

| Parameter | Value |
|-----------|-------|
| **Topology** | 1st order RC + 2× 2nd order Sallen-Key |
| **Cutoff Frequency** | ~18 kHz |
| **PWM Attenuation** | -17 dB @ 31.25 kHz |
| **Op-Amp** | TL074 (quad) |
| **Supply** | Single 5V with virtual ground |

#### Stage 1 - Input RC

| Component | Value |
|-----------|-------|
| R_in | 2.2 kΩ |
| C_in | 1.5 nF |

#### Stage 2 - Sallen-Key (Q ≈ 0.55)

| Component | Value |
|-----------|-------|
| R | 887 Ω |
| C2 | 8.2 nF |
| C3 | 10 nF |

#### Stage 3 - Sallen-Key (Q ≈ 1.29)

| Component | Value |
|-----------|-------|
| R | 2.05 kΩ |
| C2 | 1.5 nF |
| C3 | 10 nF |

> [!note]- 5th Order Schematic (Left Channel)
> ```
>      PWM Input              +5V
>      (GPIO18)                |
>         |              +-----+-----+
>         |              |           |
>        [R_in]          |         [100nF]
>        2.2kΩ           |           |
>         |              |          GND
>         +---[C_in]---GND
>         |   1.5nF
>         |
>    STAGE 2 (Q=0.55)
>        [R]
>        887Ω
>         |
>         +-----+------+
>         |     |      |
>        [C2]  [R]     |
>        8.2nF 887Ω    |
>         |     |      +------[+]
>        GND    +------+      TL074 (op-amp 1)
>               |      +------[-]
>              [C3]    |        |
>              10nF    +--------+
>               |
>              GND
>         |
>    STAGE 3 (Q=1.29)
>        [R]
>        2.05kΩ
>         |
>         +-----+------+
>         |     |      |
>        [C2]  [R]     |
>        1.5nF 2.05kΩ  |
>         |     |      +------[+]
>        GND    +------+      TL074 (op-amp 2)
>               |      +------[-]
>              [C3]    |        |
>              10nF    +--------+
>               |
>              GND
>
>         Output---[C_out]---RCA Left
>                  6.8µF
> ```
>
> **Note:** Vbias network not needed — DC bias comes through the signal path.
> See [[Build Guide - 5th Order PWM Filter]] for full wiring details.

---

### Simulation Analysis

Analytical frequency response comparison using the standard Sallen-Key transfer function from TI SLOA024B.

> [!note]- Simulation Script
> Source: `sim/filter_comparison.py` — uses analytical transfer functions (not SPICE), since unity-gain Sallen-Key topology collapses to 1st order with ideal VCVS models in SPICE.

#### Bode Plot Comparison

![Filter comparison Bode plot](../../Resources/Pi%20Zero%20PWM%20Filter/images/filter_comparison_bode.png)

#### Stage Parameters

| Stage | Parameter | 3rd Order | 5th Order |
|-------|-----------|-----------|-----------|
| Input RC | fc | 32.9 kHz | 48.2 kHz |
| Sallen-Key 1 | f₀ / Q | 23.2 kHz / 0.73 | 19.3 kHz / 0.55 |
| Sallen-Key 2 | f₀ / Q | — | 20.5 kHz / 1.29 |

#### Attenuation Comparison

| Metric | 3rd Order | 5th Order | Improvement |
|--------|-----------|-----------|-------------|
| **-3 dB cutoff** | 20.0 kHz | 19.1 kHz | Similar passband |
| **@ 31.25 kHz (PWM)** | -8.9 dB | -16.9 dB | +8.0 dB |
| **@ 62.5 kHz (2nd harmonic)** | -23.9 dB | -44.0 dB | +20.1 dB |
| **@ 93.75 kHz (3rd harmonic)** | -33.8 dB | -60.6 dB | +26.8 dB |
| **Roll-off rate** | -58 dB/dec | -97 dB/dec | Steeper transition |

#### Audio Band Detail

![Audio band passband detail](../../Resources/Pi%20Zero%20PWM%20Filter/images/filter_comparison_audioband.png)

Both filters are flat within ±1 dB across the audio band (20 Hz – 15 kHz). The 5th order is slightly flatter thanks to the Q=1.29 stage compensating for the early roll-off of the Q=0.55 stage.

#### 5th Order Stage Contributions

![5th order individual stage contributions](../../Resources/Pi%20Zero%20PWM%20Filter/images/filter_5th_order_stages.png)

The RC input (fc=48 kHz) provides gentle initial roll-off. The Q=0.55 stage gives the main filtering knee, while the Q=1.29 stage adds a slight resonance peak before steep attenuation — this is what produces the sharp transition band and ~100 dB/decade ultimate roll-off.

---

## Bill of Materials

### 3rd Order Filter (Stereo)

| Qty | Component | Value | DTU Part # | Notes |
|-----|-----------|-------|------------|-------|
| 2 | Resistor | 2.2 kΩ | - | 1% metal film |
| 4 | Resistor | 1.05 kΩ | - | 1% (or 1kΩ) |
| 2 | Capacitor | 2.2 nF | - | Film (C0G/NP0) |
| 2 | Capacitor | 4.7 nF | - | Film |
| 2 | Capacitor | 10 nF | - | Film |
| 2 | Capacitor | 6.8 µF | - | Electrolytic output |
| 1 | Capacitor | 100 nF | - | Ceramic bypass |
| 1 | Op-Amp | TL072 | - | Dual JFET |

### 5th Order Filter (Stereo)

| Qty | Component | Value | DTU Part # | Notes |
|-----|-----------|-------|------------|-------|
| 2 | Resistor | 2.2 kΩ | - | Input RC |
| 4 | Resistor | 887 Ω | - | Stage 2 (use 910Ω) |
| 4 | Resistor | 2.05 kΩ | - | Stage 3 (use 2kΩ) |
| 4 | Capacitor | 1.5 nF | - | Film |
| 2 | Capacitor | 8.2 nF | - | Film |
| 4 | Capacitor | 10 nF | - | Film |
| 2 | Capacitor | 6.8 µF | - | Electrolytic output |
| 1 | Capacitor | 100 nF | - | Ceramic bypass |
| 1 | Op-Amp | TL074 | - | Quad JFET |
| 1 | Dual RCA jack | PCB-mount | - | Red/white stereo output |

### Common Parts

| Qty | Component | Description |
|-----|-----------|-------------|
| 1 | Raspberry Pi Zero 2W | Main board |
| 1 | MicroSD Card | 8GB+ for Raspbian Lite |
| 2 | Screw terminal block | 2-pin, for audio output (3rd order) |
| 1 | Dual RCA jack | PCB-mount, red/white stereo (5th order) |
| 1 | Protoboard | For filter circuit |
| - | Hookup wire | 22-24 AWG |
| 1 | USB-C power supply | 5V 2.5A for Pi |
| 2 | RCA cable | Cut and stripped for screw terminals to speakers |

---

## Component Checklist

### Resistors
- [x] 2.2 kΩ (×2)
- [x] 1.05 kΩ or 1 kΩ (×4) - for 3rd order
- [x] 887 Ω or 910 Ω (×4) - for 5th order
- [x] 2.05 kΩ or 2 kΩ (×4) - for 5th order
- [x] 10 kΩ (×4)

### Capacitors
- [x] 1.5 nF film (×4)
- [x] 2.2 nF film (×2)
- [x] 4.7 nF film (×2)
- [x] 8.2 nF film (×2)
- [x] 10 nF film (×4)
- [x] 6.8 µF electrolytic (×2)
- [x] 10 µF electrolytic (×2)
- [x] 100 nF ceramic (×2)

### ICs & Hardware
- [x] TL072 or TL074
- [x] Raspberry Pi Zero 2W
- [x] MicroSD card
- [x] RCA jacks (×2) or dual RCA jack (PCB-mount)
- [x] Protoboard
- [x] USB-C power supply

---

## Raspberry Pi Configuration

### /boot/config.txt

> [!note]- config.txt additions
> ```ini
> # Enable onboard audio driver (required for PWM output)
> dtparam=audio=on
>
> # Remap audio PWM to GPIO 18 (left) and GPIO 19 (right)
> dtoverlay=audremap,pins_18_19
>
> # Disable HDMI audio
> hdmi_ignore_edid_audio=1
>
> # GPU memory (minimal for headless)
> gpu_mem=16
> ```
>
> **Important:** The `audremap` overlay is used instead of `pwm-2chan`. The `pwm-2chan` overlay only enables raw PWM hardware and does NOT create an ALSA audio device. The `audremap` overlay remaps the bcm2835 audio output to GPIO 18/19, providing a proper ALSA device (`bcm2835 Headphones`) that Raspotify can use.

### cmdline.txt

Ensure `console=serial0,115200` is removed if using GPIO for audio only.

---

## Raspotify Installation

> [!note]- Installation Commands
> ```bash
> # Update system
> sudo apt update && sudo apt upgrade -y
>
> # Install Raspotify
> curl -sL https://dtcooper.github.io/raspotify/install.sh | sh
>
> # Edit configuration
> sudo nano /etc/raspotify/conf
> ```

### Configuration (/etc/raspotify/conf)

> [!note]- Raspotify Config
> ```bash
> # Raspotify Configuration for PWM Audio
> LIBRESPOT_NAME="Pi Zero Audio"
> LIBRESPOT_BACKEND=alsa
> LIBRESPOT_BITRATE=320
> LIBRESPOT_DEVICE_TYPE=speaker
> LIBRESPOT_FORMAT=S16
> LIBRESPOT_DISABLE_AUDIO_CACHE=
> LIBRESPOT_DISABLE_CREDENTIAL_CACHE=
> LIBRESPOT_ENABLE_VOLUME_NORMALISATION=
> LIBRESPOT_QUIET=
> TMPDIR=/tmp
> ```
>
> **Volume setting:** After installation, set ALSA PCM volume to 75% to avoid distortion:
> ```bash
> amixer sset PCM 75%
> ```
> At 96% (default) the output clips/distorts. At 50% the signal is too quiet. 75% (-22.6 dB) is the sweet spot for both direct speaker connection and preamp use.

### Service Management

```bash
# Start service
sudo systemctl start raspotify

# Enable on boot
sudo systemctl enable raspotify

# Check status
sudo systemctl status raspotify

# View logs
journalctl -u raspotify -f
```

---

## Construction Tips

### Grounding
- Use **star grounding** - all ground connections meet at a single point
- Keep analog and digital grounds separate until star point
- Ground plane on protoboard helps reduce noise

### Component Selection
- Use **film capacitors** (C0G/NP0 or polyester) in audio signal path
- Metal film resistors (1%) for consistent filter response
- Electrolytic caps acceptable for DC blocking and bias bypass

### Bypass Capacitors
- Place 100nF ceramic **directly** at op-amp power pins
- Short leads, minimal trace length
- **Do NOT add bulk electrolytic caps on the Pi's 5V rail** — tested a 10µF 50V cap and it caused audio distortion (likely due to inrush current / interaction with Pi's internal regulation). The 100nF ceramic on the TL072 is sufficient.

### Layout
- Keep input and output traces separated
- Short signal paths to minimize pickup
- Shield cable from Pi GPIO to filter input if noise is an issue

### Testing
1. Power up without Pi connected - verify Vcc at op-amp power pins
2. Connect function generator, sweep 100Hz-50kHz
3. Verify -3dB point near design frequency
4. Connect Pi and test with Spotify

---

## Bonus: LM386 Mini Amplifier

> [!info] Separate Project
> This is a standalone mini amplifier for driving a salvaged 8Ω 1.5W passive speaker. Not connected to the Pi project - just a fun side build with spare parts.

### Specifications

| Parameter | Value |
|-----------|-------|
| **IC** | LM386N-1 |
| **Gain** | 20 (default) |
| **Supply** | 9V battery |
| **Output** | 0.5W @ 8Ω |
| **Load** | 8Ω 1.5W speaker |

### Schematic

> [!note]- LM386 Circuit
> ```
>                    +9V
>                     |
>                     +--------+--------+
>                     |        |        |
>                    [6]      [4]     [10µF]
>         Input       |        |        |
>           |        LM386     |       GND
>          [10µF]     |        |
>           |--[3]    |      [0.05µF]
>           |        [5]-------+
>     [10kΩ POT]      |        |
>           |        [10µF]   [10Ω]
>          [2]        |        |
>           |         +--------+
>          GND        |
>                   Speaker
>                     8Ω
>                     |
>                    GND
>
>     Pin 1 & 8: Leave open for gain=20
>     Pin 7: Bypass (optional 10µF to GND)
> ```

### Components

| Qty | Component | Value | Notes |
|-----|-----------|-------|-------|
| 1 | LM386N-1 | - | DIP-8 |
| 1 | Capacitor | 10 µF | Input coupling |
| 1 | Capacitor | 10 µF | Output coupling |
| 1 | Capacitor | 47 nF (0.047 µF) | Zobel network |
| 1 | Resistor | 10 Ω | Zobel network |
| 1 | Potentiometer | 10 kΩ | Volume control |
| 1 | Battery clip | 9V | Power |
| 1 | Speaker | 8Ω 1.5W | Salvaged |

### Zobel Network
The 47nF + 10Ω in series across the output provides high-frequency stability and prevents oscillation with inductive speaker loads.

---

## Build Phases

- [x] **Research** - Filter design and component selection
- [x] **Components** - Acquire all parts
- [x] **Breadboard prototype (3rd order)** - Test filter response with Analog Discovery 3
- [x] **Software setup** - Configure Pi and Raspotify
- [x] **Proto board build (3rd order)** - Soldered 3rd order filter on proto board
- [x] **Integration** - Working with active speakers and Schiit Saga preamp
- [ ] **Breadboard prototype (5th order)** - Test 5th order filter with AD3
- [ ] **Proto board build (5th order)** - Solder with TL074 and RCA output
- [ ] **Enclosure** - 3D print or project box
- [ ] **PCB design** - Proper PCB layout for cleaner signal

---

## References

- [Raspberry Pi PWM Audio](https://learn.adafruit.com/adding-basic-audio-ouput-to-raspberry-pi-zero)
- [Raspotify GitHub](https://github.com/dtcooper/raspotify)
- [Sallen-Key Filter Design (TI SLOA024B)](https://www.ti.com/lit/an/sloa024b/sloa024b.pdf)
- [TL072 Datasheet](https://www.ti.com/product/TL072)
- [TL074 Datasheet](https://www.ti.com/product/TL074)
- [LM386 Datasheet](https://www.ti.com/product/LM386)
- Simulation script: `sim/filter_comparison.py`

---
