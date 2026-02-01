---
title: Pi Zero 2W PWM Audio Filter for Spotify Connect
type: project
tags:
  - electronics
  - raspberry-pi
  - audio
  - active-project
status: Ready to Build
started: 2026-02-01
updated: 2026-02-01
aliases:
  - Pi PWM Filter
  - Raspotify Audio
  - PWM to Line-Level
links:
  - "[[Illuminate 7Mk2/Illuminate 7Mk2 - Speaker Build]]"
  - "[[Build Guide - 3rd Order PWM Filter]]"
---

# Pi Zero 2W PWM Audio Filter for Spotify Connect

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

---

## System Overview

| Parameter | Specification |
|-----------|--------------|
| **Platform** | Raspberry Pi Zero 2W |
| **Software** | Raspotify (Spotify Connect) |
| **PWM Frequency** | 31.25 kHz |
| **Output** | Stereo RCA line-level |
| **Target** | Active speakers / amplifier input |

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

#### Bias Network (per channel)

| Component | Value | Purpose |
|-----------|-------|---------|
| R_bias1, R_bias2 | 10 kΩ | Voltage divider (Vcc/2) |
| C_bypass | 10 µF | Bias point stabilization |
| C_power | 100 nF | Power supply decoupling |

> [!note]- 3rd Order Schematic (Left Channel)
> ```
>                            +5V
>                             |
>                          [10kΩ]
>                             |
>      PWM Input             Vbias----[10µF]---GND
>      (GPIO18)               |
>         |                [10kΩ]
>         |                   |
>        [R1]                GND
>        2.2k
>         |
>         +---[C1]---GND
>         |   2.2nF
>         |
>        [R2]              +5V
>        1.05k              |
>         |            +----+----+
>         +-----+------|+   |    |
>         |     |      |  TL072  |[100nF]
>        [C2]  [R3]    |-   |    |
>        4.7nF 1.05k   |  +-+----+
>         |     |      |  |     GND
>        GND    +------+--+
>               |
>              [C3]
>              10nF
>               |
>              GND
>
>         Output---[C_out]---RCA Left
>                  6.8µF
> ```

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
>                                  +5V
>                                   |
>      PWM Input                 [10kΩ]
>      (GPIO18)                    |
>         |                      Vbias----[10µF]---GND
>         |                        |
>        [R_in]                 [10kΩ]
>        2.2kΩ                     |
>         |                       GND
>         +---[C_in]---GND
>         |   1.5nF
>         |
>    STAGE 2 (Q=0.55)
>        [R]
>        887Ω
>         |
>         +-----+------+
>         |     |      |          +5V
>        [C2]  [R]     |           |
>        8.2nF 887Ω    |      +----+----+
>         |     |      +------|+   |    |
>        GND    +------+      |  TL074  |[100nF]
>               |      +------|-   |    |
>              [C3]    |      |  +-+----+
>              10nF    |      |  |     GND
>               |      +------+--+
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
>        GND    +------+      TL074
>               |      +------[-]
>              [C3]    |        |
>              10nF    +--------+
>               |
>              GND
>
>         Output---[C_out]---RCA Left
>                  6.8µF
> ```

---

## Bill of Materials

### 3rd Order Filter (Stereo)

| Qty | Component | Value | DTU Part # | Notes |
|-----|-----------|-------|------------|-------|
| 2 | Resistor | 2.2 kΩ | - | 1% metal film |
| 4 | Resistor | 1.05 kΩ | - | 1% (or 1kΩ) |
| 4 | Resistor | 10 kΩ | - | Bias network |
| 2 | Capacitor | 2.2 nF | - | Film (C0G/NP0) |
| 2 | Capacitor | 4.7 nF | - | Film |
| 2 | Capacitor | 10 nF | - | Film |
| 2 | Capacitor | 6.8 µF | - | Electrolytic output |
| 2 | Capacitor | 10 µF | - | Electrolytic bias |
| 2 | Capacitor | 100 nF | - | Ceramic bypass |
| 1 | Op-Amp | TL072 | - | Dual JFET |

### 5th Order Filter (Stereo)

| Qty | Component | Value | DTU Part # | Notes |
|-----|-----------|-------|------------|-------|
| 2 | Resistor | 2.2 kΩ | - | Input RC |
| 4 | Resistor | 887 Ω | - | Stage 2 (use 910Ω) |
| 4 | Resistor | 2.05 kΩ | - | Stage 3 (use 2kΩ) |
| 4 | Resistor | 10 kΩ | - | Bias network |
| 4 | Capacitor | 1.5 nF | - | Film |
| 2 | Capacitor | 8.2 nF | - | Film |
| 4 | Capacitor | 10 nF | - | Film |
| 2 | Capacitor | 6.8 µF | - | Electrolytic output |
| 2 | Capacitor | 10 µF | - | Electrolytic bias |
| 2 | Capacitor | 100 nF | - | Ceramic bypass |
| 1 | Op-Amp | TL074 | - | Quad JFET |

### Common Parts

| Qty | Component | Description |
|-----|-----------|-------------|
| 1 | Raspberry Pi Zero 2W | Main board |
| 1 | MicroSD Card | 8GB+ for Raspbian Lite |
| 2 | RCA Jack | Panel mount female |
| 1 | Protoboard | For filter circuit |
| - | Hookup wire | 22-24 AWG |
| 1 | USB-C power supply | 5V 2.5A for Pi |

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
- [x] RCA jacks (×2)
- [x] Protoboard
- [x] USB-C power supply

---

## Raspberry Pi Configuration

### /boot/config.txt

> [!note]- config.txt additions
> ```ini
> # Enable PWM audio output
> dtoverlay=pwm-2chan,pin=18,func=2,pin2=19,func2=2
>
> # Disable onboard audio (optional, saves resources)
> # dtparam=audio=off
>
> # Disable HDMI audio
> hdmi_ignore_edid_audio=1
>
> # GPU memory (minimal for headless)
> gpu_mem=16
> ```

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
> # Device name shown in Spotify
> LIBRESPOT_NAME="Pi Zero Audio"
>
> # Audio backend (ALSA)
> LIBRESPOT_BACKEND="alsa"
>
> # Output device (default PWM)
> LIBRESPOT_DEVICE="default"
>
> # Bitrate (96, 160, or 320)
> LIBRESPOT_BITRATE="320"
>
> # Initial volume (0-100)
> LIBRESPOT_INITIAL_VOLUME="80"
>
> # Enable volume normalization
> LIBRESPOT_VOLUME_NORMALISATION="--enable-volume-normalisation"
>
> # Disable audio cache to save SD card writes
> LIBRESPOT_CACHE=""
> ```

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
- Consider 10µF electrolytic in parallel for low-frequency bypass

### Layout
- Keep input and output traces separated
- Short signal paths to minimize pickup
- Shield cable from Pi GPIO to filter input if noise is an issue

### Testing
1. Power up without Pi connected - verify Vbias = Vcc/2
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
- [ ] **Breadboard prototype** - Test filter response
- [ ] **Software setup** - Configure Pi and Raspotify
- [ ] **Final build** - Solder on protoboard
- [ ] **Enclosure** - 3D print or project box
- [ ] **Integration** - Connect to active speakers

---

## References

- [Raspberry Pi PWM Audio](https://learn.adafruit.com/adding-basic-audio-ouput-to-raspberry-pi-zero)
- [Raspotify GitHub](https://github.com/dtcooper/raspotify)
- [Sallen-Key Filter Design](https://www.ti.com/lit/an/sloa024b/sloa024b.pdf)
- [TL072 Datasheet](https://www.ti.com/product/TL072)
- [LM386 Datasheet](https://www.ti.com/product/LM386)

---
