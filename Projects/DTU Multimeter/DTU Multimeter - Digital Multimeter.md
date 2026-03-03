---
title: DTU Digital Multimeter - Fluke 289-Class AVR Instrument
type: project
tags:
  - electronics
  - avr
  - embedded
  - active-project
  - dtu
  - atmega2560
status: In Development
started: 2026-03-03
updated: 2026-03-03
aliases:
  - DTU Multimeter
  - AVR Multimeter
links:
  - "[[Build Guide - DTU Multimeter]]"
---

# DTU Digital Multimeter - Fluke 289-Class AVR Instrument

> [!summary] **Project Goal**
> Build a Fluke 289-class auto-ranging digital multimeter as bare-metal embedded C on ATmega2560. 22 measurement modes, 128x64 OLED display, built-in oscilloscope, and EEPROM data logging. 3rd semester DTU Electrical Engineering project.
> - 22 measurement modes including True-RMS AC, capacitance, inductance, frequency, dBV/dBm
> - Fluke-style OLED UI with secondary functions (REL, HOLD, MIN/MAX)
> - Built-in oscilloscope with triggering and auto-measurements
> - UART serial interface for PC data logging and remote control

---

## 🔗 Quick Links

- [[Build Guide - DTU Multimeter|Build & Calibration Guide]]
- [[#Measurement Modes|All 22 Modes]]
- [[#Component List|Key ICs]]
- [[#Circuit Architecture|System Block Diagram]]
- [[#Pin Wiring Map|ATmega2560 Pinout]]
- [[#OLED Display Layout|Display Mockup]]
- [[#Firmware Architecture|Source Code Structure]]
- [[#Calibration Procedure|Calibration Steps]]
- [[#Build Phases|Build Checklist]]

---

## 📋 System Overview

| Parameter | Specification |
|-----------|--------------|
| **MCU** | ATmega2560, 16 MHz |
| **ADC** | MCP3208 12-bit SPI (8 channels) |
| **Display** | SSD1306 128x64 OLED (I2C, 0x3C) |
| **Modes** | 22 measurement modes |
| **Resolution** | ~32768 counts (12-bit + 3-bit oversampling) |
| **Oversampling** | 64 samples (4^3), 3 extra bits |
| **True-RMS** | Software engine, 400 samples @ 20 kHz |
| **Oscilloscope** | 1000-sample buffer, 10-bit internal ADC |
| **Data Logging** | 100 entries, circular EEPROM buffer |
| **RTC** | DS1307 (I2C) for timestamped logging |
| **Build System** | PlatformIO, bare-metal AVR C (no Arduino framework) |
| **Serial** | UART 115200 baud, command interface |

---

## ⚡ Measurement Modes

All 22 modes supported by the firmware. Auto-ranging with configurable manual range lock.

| # | Mode | Description | Ranges / Spec |
|---|------|-------------|---------------|
| 1 | **DC Voltage** | Direct voltage measurement via resistive divider | 0–500 V (11:1 divider) |
| 2 | **AC Voltage** | True-RMS AC measurement | 0–500 V RMS |
| 3 | **DC+AC Voltage** | Combined DC and AC components | DC + True-RMS AC |
| 4 | **mV DC** | Low-voltage DC (direct ADC input) | 0–5 V, mV resolution |
| 5 | **mV AC** | Low-voltage AC True-RMS | 0–5 V RMS |
| 6 | **Resistance** | Auto-ranging ohmmeter | 50 Ohm – 50 MOhm (8 ranges) |
| 7 | **Low-Ohm** | Constant-current 4-wire style | NE555 10 mA source |
| 8 | **Conductance** | Nano-siemens measurement | nS range |
| 9 | **Continuity** | Audible beep below threshold | < 25 Ohm buzzer |
| 10 | **Diode Test** | Forward voltage measurement | 0–2.5 V |
| 11 | **Capacitance** | RC charge timing | 3 ranges (100 Ohm / 10k / 1M) |
| 12 | **Inductance** | LC oscillation timing | uH – H range |
| 13 | **DC Current** | Shunt-based current measurement | 500 uA – 10 A (6 ranges) |
| 14 | **AC Current** | True-RMS AC current | 500 uA – 10 A RMS |
| 15 | **DC+AC Current** | Combined DC and AC current | DC + True-RMS AC |
| 16 | **Frequency** | Hardware counter on INT4 | Hz – MHz via Timer1 gate |
| 17 | **Duty Cycle** | Pulse width ratio | 0–100% |
| 18 | **Pulse Width** | High/low pulse duration | us – ms |
| 19 | **Temperature** | LM35 analog sensor | Celsius, 10 mV/C |
| 20 | **dBV** | Decibels relative to 1 V | 20*log10(V_rms / 1V) |
| 21 | **dBm** | Decibels relative to 1 mW | 50/75/600 Ohm impedance |
| 22 | **Oscilloscope** | Waveform capture and display | 1000 samples, auto-trigger |

### Secondary Functions

| Function | Button | Description |
|----------|--------|-------------|
| **REL** (Delta) | FUNC | Zero-reference relative measurement |
| **HOLD** | FUNC | Freeze display at current reading |
| **MIN/MAX** | FUNC | Track minimum, maximum, and average |
| **Range Lock** | RANGE | Lock current range, disable auto-range |
| **Low-Pass Filter** | SEL | Digital IIR filter (alpha = 0.1) |

---

## 🛒 Component List

### Key ICs

| Qty | Component | Part Number | Purpose |
|-----|-----------|-------------|---------|
| 1 | 12-bit SPI ADC | MCP3208 | 8-channel main ADC (voltage, current, resistance, temp) |
| 1 | 16-ch Analog Mux | 74HC4067 | Resistance range selection (8 reference resistors) |
| 1 | Triple 2:1 Mux | CD4053 | Current shunt range switching (6 shunt resistors) |
| 1 | Dual Op-Amp | LM358 | Current amplifier (x1 and x10 gain stages) |
| 1 | Dual Op-Amp | MCP6002 | Signal conditioning (AC coupling, buffer) |
| 1 | Comparator | LM311 | Frequency/duty cycle input conditioning (square wave shaping) |
| 1 | Temp Sensor | LM35 | Temperature measurement (10 mV/C analog output) |
| 1 | RTC | DS1307 | Real-time clock for timestamped data logging (I2C) |
| 1 | Timer IC | NE555 | Constant current source (~10 mA) for low-ohm / diode test |
| 1 | OLED Display | SSD1306 | 128x64 monochrome I2C display |
| 1 | MCU | ATmega2560 | Main controller (Arduino Mega 2560 board) |

### Passive Components

| Qty | Component | Values | Purpose |
|-----|-----------|--------|---------|
| 8 | Reference Resistors | 49.9, 499, 4.99k, 48.7k, 499k, 4.7M, 10M (x2) | Resistance measurement ranges (via 74HC4067) |
| 6 | Current Shunts | 0.1, 1, 10, 100, 1k, 10k Ohm | Current measurement ranges (via CD4053) |
| 2 | Voltage Divider | 1M + 100k (11:1 ratio) | High-voltage input attenuation |
| 3 | Charge Resistors | 100, 10k, 1M Ohm | Capacitance measurement RC timing |
| 4 | Buttons | Tactile switches | MODE (INT5), FUNC, RANGE, SEL |
| 3 | LEDs | Red, Green, Yellow | Status indicators |
| 1 | Buzzer | Piezo | Continuity beep |

---

## 🔧 Circuit Architecture

> [!note]- System Block Diagram
> ```
>  ┌─────────────────────────────────────────────────────────────┐
>  │                      INPUT TERMINALS                        │
>  │              V/Ohm    COM    mA    10A                      │
>  └──────┬────────┬────────┬──────┬──────┬──────────────────────┘
>         │        │        │      │      │
>    ┌────▼────┐   │   ┌────▼──────▼──┐   │
>    │  1M+100k│   │   │   CD4053     │   │
>    │  Divider│   │   │  Shunt Mux   │   │
>    │  (11:1) │   │   │  6 ranges    │   │
>    └────┬────┘   │   └──────┬───────┘   │
>         │        │          │            │
>         │   ┌────▼────┐  ┌─▼──────┐     │
>         │   │74HC4067 │  │ LM358  │     │
>         │   │ 16-ch   │  │ Gain   │     │
>         │   │  Mux    │  │ x1/x10 │     │
>         │   │ 8 R_ref │  └───┬────┘     │
>         │   └────┬────┘      │          │
>         │        │           │          │
>    ┌────▼────────▼───────────▼──────────▼───┐
>    │              MCP3208 (SPI)              │
>    │           12-bit 8-channel ADC          │
>    │  CH0:Res CH1:V_hi CH2:V_lo CH3:Cur     │
>    │  CH4:AC  CH5:Temp CH6:Scope CH7:Aux    │
>    └────────────────┬───────────────────────┘
>                     │ SPI (SCK/MOSI/MISO/CS)
>              ┌──────▼──────┐
>              │  ATmega2560 │
>              │   16 MHz    │
>              │             │──── UART (115200) ──── PC
>              │  INT4: Freq │
>              │  INT5: Mode │
>              │  A8/A9: Scope (internal 10-bit ADC)
>              └──┬────┬──┬──┘
>                 │    │  │
>          ┌──────▼┐ ┌─▼──▼──┐  ┌──────────┐
>          │SSD1306│ │DS1307 │  │ Buttons  │
>          │ OLED  │ │  RTC  │  │ LEDs     │
>          │128x64 │ │       │  │ Buzzer   │
>          │ (I2C) │ │ (I2C) │  └──────────┘
>          └───────┘ └───────┘
> ```

> [!tip] **Dual ADC Strategy**
> The MCP3208 (12-bit SPI) handles all precision measurements. The ATmega2560's internal 10-bit ADC (A8/A9) is used for the oscilloscope mode where speed matters more than resolution.

---

## 📌 Pin Wiring Map

### SPI Bus (MCP3208)

| Function | ATmega2560 Pin | Arduino Pin | Notes |
|----------|---------------|-------------|-------|
| SCK | PB1 | D52 | Hardware SPI clock |
| MOSI | PB2 | D51 | Hardware SPI data out |
| MISO | PB3 | D50 | Hardware SPI data in |
| ADC CS | PB0 | D53 | MCP3208 chip select |

### I2C Bus (Display + RTC)

| Function | ATmega2560 Pin | Arduino Pin | Notes |
|----------|---------------|-------------|-------|
| SDA | PD1 | D20 | SSD1306 + DS1307 |
| SCL | PD0 | D21 | SSD1306 + DS1307 |

### 74HC4067 Mux Control

| Function | ATmega2560 Pin | Arduino Pin | Notes |
|----------|---------------|-------------|-------|
| S0 | PA0 | D22 | Mux select bit 0 |
| S1 | PA1 | D23 | Mux select bit 1 |
| S2 | PA2 | D24 | Mux select bit 2 |
| S3 | PA3 | D25 | Mux select bit 3 |
| EN | PA4 | D26 | Enable (active LOW) |

### CD4053 Current Range

| Function | ATmega2560 Pin | Arduino Pin | Notes |
|----------|---------------|-------------|-------|
| A | PA5 | D27 | Shunt select A |
| B | PA6 | D28 | Shunt select B |
| C | PA7 | D29 | Shunt select C |
| INH | PC7 | D30 | Inhibit |

### Capacitance / Current Source

| Function | ATmega2560 Pin | Arduino Pin | Notes |
|----------|---------------|-------------|-------|
| Cap Charge | PC6 | D31 | RC charge control |
| Cap Discharge | PC5 | D32 | RC discharge control |
| NE555 Enable | PC4 | D33 | Constant current source on/off |

### User Interface

| Function | ATmega2560 Pin | Arduino Pin | Notes |
|----------|---------------|-------------|-------|
| MODE button | PE5 | D3 | INT5, interrupt-driven |
| FUNC button | PG5 | D4 | Polled |
| RANGE button | PE3 | D5 | Polled |
| SEL button | PH3 | D6 | Polled |
| Buzzer | PH4 | D7 | Continuity beep |
| Red LED | PH5 | D8 | Overload indicator |
| Green LED | PH6 | D9 | Normal operation |
| Yellow LED | PB4 | D10 | HOLD / Logging active |

### Frequency / Scope

| Function | ATmega2560 Pin | Arduino Pin | Notes |
|----------|---------------|-------------|-------|
| Freq Input | PE4 | D2 | INT4, hardware counter |
| Scope CH1 | ADC8 | A8 | Internal 10-bit ADC |
| Scope CH2 | ADC9 | A9 | Internal 10-bit ADC |

---

## 🖥️ OLED Display Layout

Fluke-style measurement display on the SSD1306 128x64 OLED.

> [!note]- Measurement Screen Layout
> ```
>  ┌────────────────────────────────────┐
>  │ DC V          AUTO    REL    5Hz  │  ← Row 0: Mode, range, func, rate
>  │────────────────────────────────────│
>  │                                    │
>  │        1 2 . 3 4   V              │  ← Rows 1-4: Primary reading (large)
>  │                                    │
>  │────────────────────────────────────│
>  │ Min: 11.89   Max: 13.01    Avg    │  ← Row 5: Secondary / MIN-MAX
>  │────────────────────────────────────│
>  │ ▮▮▮▮▮▮▮▮▮▮░░░░░░  62%           │  ← Row 7: Bar graph (% of range)
>  └────────────────────────────────────┘
> ```

> [!note]- Oscilloscope Screen Layout
> ```
>  ┌────────────────────────────────────┐
>  │ SCOPE  Auto  1ms/div  T:512      │  ← Trigger mode, timebase, level
>  │────────────────────────────────────│
>  │ 5V┤          ╱╲                   │
>  │   ┤        ╱    ╲       ╱╲        │  ← Waveform display area
>  │   ┤      ╱        ╲   ╱    ╲      │    (128 x 48 pixels)
>  │   ┤────╱            ╲╱      ╲──── │
>  │ 0V┤                               │
>  │────────────────────────────────────│
>  │ Vpp:3.2V  f:1kHz  Duty:50%       │  ← Auto-measurements
>  └────────────────────────────────────┘
> ```

---

## 📐 Full Schematic Description

> [!info] **KiCad Project**
> KiCad project folder: `KiCad/`. Build the schematic first in KiCad's schematic editor using the subcircuit descriptions and pin diagrams below, then export the netlist to the PCB editor.

### SnapEDA Symbol & Footprint Downloads

Download KiCad symbols + footprints for each IC from SnapEDA (select **KiCad** format). Use DIP packages — solder DIP sockets onto the PCB.

| Ref | Component    | Package      | SnapEDA Link                                                                                                                  |
| --- | ------------ | ------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| U1  | MCP3208-CI/P | DIP-16       | [MCP3208-CI/P (Microchip)](https://www.snapeda.com/parts/MCP3208-CI/P/Microchip/view-part/)                                   |
| U2  | CD74HC4067E  | DIP-24       | [CD74HC4067E (TI)](https://www.snapeda.com/parts/CD74HC4067E/Texas%20Instruments/view-part/)                                  |
| U3  | CD4053BE     | DIP-16       | [CD4053BE (TI)](https://www.snapeda.com/parts/CD4053BE/Texas%20Instruments/view-part/)                                        |
| U4  | LM358P       | DIP-8        | [LM358P (TI)](https://www.snapeda.com/parts/LM358P/Texas%20Instruments/view-part/)                                            |
| U5  | LM311N       | DIP-8        | [LM311N (TI)](https://www.snapeda.com/parts/LM311N/Texas%20Instruments/view-part/)                                            |
| U6  | NE555P       | DIP-8        | [NE555P (TI)](https://www.snapeda.com/parts/NE555P/Texas%20Instruments/view-part/)                                            |
| U7  | LM35DZ       | TO-92        | [LM35DZ (TI)](https://www.snapeda.com/parts/LM35DZ/Texas%20Instruments/view-part/)                                            |
| U8  | DS1307       | DIP-8        | [DS1307 (Analog Devices)](https://www.snapeda.com/parts/DS1307/Analog%20Devices/view-part/)                                   |
| J5  | SSD1306 OLED | 4-pin module | [OLED 128x64 I2C](https://www.snapeda.com/parts/OLED%20128x64%201.3%22%20I2C/UNIVERSAL-SOLDER%20Electronics%20Ltd/view-part/) |

> [!tip] **Passives**
> Resistors, capacitors, LEDs, switches, buzzer, crystal, battery holder, and banana jacks all use standard KiCad built-in THT footprints — no SnapEDA downloads needed for those.

### Library File Reference (SnapEDA → KiCad)

All SnapEDA files live in `KiCad/lib/`. Footprints are organized in `.pretty` folders (KiCad's footprint library format).

**Symbol → Footprint mapping:**

| Symbol File (in `lib/symbols/`) | Footprint Library (in `lib/footprints/`) | Footprint Name | Package | IC |
|---|---|---|---|---|
| `MCP3208-CI_P.kicad_sym` | `MCP3208-CI_P.pretty` | DIP254P762X432-16 | DIP-16 | U1 — 12-bit ADC |
| `CD74HC4067E.kicad_sym` | `CD74HC4067E.pretty` | DIP254P762X508-24 | DIP-24 | U2 — 16-ch Mux |
| `CD4053BE.kicad_sym` | `CD4053BE.pretty` | DIP794W45P254L1969H508Q16 | DIP-16 | U3 — Triple 2:1 Mux |
| `LM358P.kicad_sym` | `LM358P.pretty` | DIP794W45P254L959H508Q8 | DIP-8 | U4 — Dual Op-Amp |
| `LM311N.kicad_sym` | `LM311N.pretty` | DIP794W45P254L959H508Q8 | DIP-8 | U5 — Comparator |
| `NE555P.kicad_sym` | `NE555P.pretty` | DIP794W45P254L959H508Q8 | DIP-8 | U6 — Timer |
| `LM35DZ.kicad_sym` | `LM35DZ.pretty` | IC_LM35DZ | TO-92 | U7 — Temp Sensor |
| `DS1307N_.kicad_sym` | `DS1307N_.pretty` | DIP762W47P254L991H457Q8 | DIP-8 | U8 — RTC |
| `OLED_128X64_1.3_I2C.kicad_sym` | `OLED_128X64_1.3_I2C.pretty` | LCD_OLED_128X64_1.3_I2C | Module | J5 — OLED Display |
| `A000067.kicad_sym` | `A000067.pretty` | MODULE_A000067 | Board | A1 — Arduino Mega |

> [!done] **CD74HC4067E symbol created**
> The SnapEDA download was missing the symbol file. A DIP-24 variant was created from KiCad's built-in `74xx:CD74HC4067M` with the footprint reference updated to `CD74HC4067E:DIP254P762X508-24`. Same pinout (same IC), just DIP package instead of SOIC.
>
> **Important:** In your schematic you currently have the built-in `74xx:CD74HC4067M` placed (SOIC footprint). You should either:
> 1. **Swap it:** Delete U2 and re-place it from the project library `CD74HC4067E:CD74HC4067E` (already has DIP footprint), or
> 2. **Change footprint only:** Double-click U2 → Properties → Footprint → change to `CD74HC4067E:DIP254P762X508-24`

> [!example] **How to register libraries in KiCad (one-time setup)**
>
> **Symbols:**
> 1. KiCad → Preferences → **Manage Symbol Libraries**
> 2. Go to **Project Libraries** tab
> 3. Click **+** (add existing) → browse to `KiCad/lib/symbols/`
> 4. Add each `.kicad_sym` file (one per IC)
>
> **Footprints:**
> 1. KiCad → Preferences → **Manage Footprint Libraries**
> 2. Go to **Project Libraries** tab
> 3. Click **+** (add existing) → browse to `KiCad/lib/footprints/`
> 4. Add each `.pretty` folder (one per IC)
>
> Use **Project Libraries** (not Global) so paths travel with the project.

> [!note] **DS1307 footprint assignment**
> The DS1307 symbol has no embedded footprint reference. In KiCad, after placing U8, open its properties and manually assign footprint: `DS1307N_:DIP762W47P254L991H457Q8`

> [!done] **3D Models linked to footprints**
> All 9 `.step` files in `lib/3dmodels/` are now referenced from their corresponding `.kicad_mod` footprint files using `${KIPRJDIR}/../lib/3dmodels/` paths. They should appear automatically in KiCad's 3D viewer.
>
> | Footprint | 3D Model File | Status |
> |---|---|---|
> | MCP3208 (DIP-16) | `MCP3208-CI_P.step` | Linked |
> | CD74HC4067E (DIP-24) | `CD74HC4067E.step` | Linked |
> | CD4053BE (DIP-16) | `CD4053BE.step` | Linked |
> | LM358P (DIP-8) | `LM358P.step` | Linked |
> | LM311N (DIP-8) | `LM311N.step` | Linked |
> | NE555P (DIP-8) | `NE555P.step` | Linked |
> | LM35DZ (TO-92) | `LM35DZ.step` | Linked |
> | DS1307N (DIP-8) | `DS1307N_.step` | Linked |
> | Arduino Mega (Board) | `A000067.step` | Linked |
> | OLED Module | — | No 3D model available |
>
> **If a model appears misaligned** in the 3D viewer, open the footprint in Footprint Editor → Properties → 3D Models tab → adjust offset/rotation/scale values.

### Schematic Build Order (Block by Block)

> [!success] **How to use this guide**
> Work through each block in order. For each block:
> 1. Place the listed passive components from the KiCad built-in libraries
> 2. Wire them to the IC pins as shown
> 3. Add power flags / symbols where indicated
> 4. Check the block off when done
>
> **KiCad shortcuts:** `P` = place power symbol, `A` = place symbol, `W` = draw wire, `L` = place net label

---

#### Block 1: Power Rails & Bypass Caps

> [!abstract] **Goal:** Get all ICs powered and decoupled. No signal wiring yet.

**Place these components (KiCad built-in `Device` library):**

| Ref | Value | KiCad Symbol | Footprint |
|-----|-------|-------------|-----------|
| C1 | 100nF | Device:C | Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm |
| C2 | 100nF | Device:C | Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm |
| C3 | 100nF | Device:C | Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm |
| C5 | 10uF | Device:CP | Capacitor_THT:CP_Radial_D5.0mm_P2.50mm |
| C6 | 10uF | Device:CP | Capacitor_THT:CP_Radial_D5.0mm_P2.50mm |
| C7 | 10uF | Device:CP | Capacitor_THT:CP_Radial_D5.0mm_P2.50mm |

**Wiring checklist:**

- [ ] Place `+5V` and `GND` power symbols (KiCad `power` library)
- [ ] C1: between U1 pin 16 (VDD) and U1 pin 9 (DGND) — place physically close to U1
- [ ] C2: between U2 pin 24 (VCC) and U2 pin 12 (GND) — close to U2
- [ ] C3: between U3 pin 16 (VDD) and U3 pin 8 (VSS) — close to U3
- [ ] C5, C6, C7: between `+5V` and `GND` — bulk decoupling, place near power entry
- [ ] Wire `+5V` to: U1 pins 15+16, U2 pin 24, U3 pin 16, U4 pin 8, U5 pin 8, U6 pin 8, U7 pin 1, U8 pin 8
- [ ] Wire `GND` to: U1 pins 9+14, U2 pin 12, U3 pin 8, U4 pin 4, U5 pins 1+4, U6 pin 1, U7 pin 3, U8 pin 4
- [ ] Wire `+5V` and `GND` to Arduino Mega A1 power pins (5V_1, GND1, etc.)
- [ ] Add `PWR_FLAG` on both `+5V` and `GND` nets (prevents KiCad ERC errors)

---

#### Block 2: SPI Bus (U1 ↔ Arduino)

> [!abstract] **Goal:** Connect MCP3208 to Arduino Mega via SPI.

**No new components — just wires and net labels.**

**Wiring checklist:**

- [ ] U1 pin 12 (DOUT) → A1 pin D50 (MISO) — label: `SPI_MISO`
- [ ] U1 pin 11 (DIN) → A1 pin D51 (MOSI) — label: `SPI_MOSI`
- [ ] U1 pin 13 (CLK) → A1 pin D52 (SCK) — label: `SPI_SCK`
- [ ] U1 pin 10 (~CS) → A1 pin D53 (CS) — label: `SPI_CS`

> [!tip] Use **net labels** instead of long wires across the schematic. Place a label on each end — KiCad connects them by name.

---

#### Block 3: I2C Bus (U8 + OLED + Arduino)

> [!abstract] **Goal:** Connect DS1307 RTC and SSD1306 OLED to Arduino via shared I2C bus with pull-ups.

**Place these components:**

| Ref | Value | KiCad Symbol | Footprint |
|-----|-------|-------------|-----------|
| R23 | 10k | Device:R | Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal |
| R24 | 10k | Device:R | Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal |
| J5 | SSD1306_OLED | (from SnapEDA lib) | (from SnapEDA lib) |
| Y1 | 32.768kHz | Device:Crystal | Crystal:Crystal_C26-LF_D2.1mm_L6.5mm_Horizontal |
| BT1 | CR2032 | Device:Battery | Battery:BatteryHolder_Keystone_103_1x20mm |

**Wiring checklist:**

- [ ] Create net label `I2C_SDA` — connect to: U8 pin 5 (SDA), J5 pin 3 (SDA), A1 pin D20
- [ ] Create net label `I2C_SCL` — connect to: U8 pin 6 (SCL), J5 pin 4 (SCL), A1 pin D21
- [ ] R23: `+5V` → R23 pin 1, R23 pin 2 → `I2C_SDA` (pull-up)
- [ ] R24: `+5V` → R24 pin 1, R24 pin 2 → `I2C_SCL` (pull-up)
- [ ] J5 pin 1 → `+5V`, J5 pin 2 → `GND`
- [ ] Y1 pin 1 → U8 pin 1 (X1), Y1 pin 2 → U8 pin 2 (X2)
- [ ] BT1 pin 1 (+) → U8 pin 3 (VBAT), BT1 pin 2 (−) → `GND`

---

#### Block 4: Voltage Measurement (Divider → U1 CH1/CH2)

> [!abstract] **Goal:** Wire the 11:1 voltage divider and direct voltage input.

**Place these components:**

| Ref | Value | KiCad Symbol | Footprint |
|-----|-------|-------------|-----------|
| R15 | 1M | Device:R | Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal |
| R16 | 100k | Device:R | Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal |
| J3 | V_Ohm | Connector:Banana_Jack | Connector:Banana_Jack_1Pin |
| J4 | COM | Connector:Banana_Jack | Connector:Banana_Jack_1Pin |

**Wiring checklist:**

- [ ] J3 pin 1 → net label `PROBE_VOHM`
- [ ] J4 pin 1 → `GND`
- [ ] R15 pin 1 → `PROBE_VOHM`
- [ ] R15 pin 2 → R16 pin 1 (junction = divider midpoint) → net label `ADC_CH1_VDIV`
- [ ] R16 pin 2 → `GND`
- [ ] `ADC_CH1_VDIV` → U1 pin 2 (CH1)
- [ ] `PROBE_VOHM` → U1 pin 3 (CH2) — direct low-voltage path

---

#### Block 5: Resistance Measurement (U2 Mux + R1-R8)

> [!abstract] **Goal:** Wire 8 reference resistors through the 74HC4067 mux to MCP3208 CH0, plus mux control from Arduino.

**Place these components:**

| Ref | Value | KiCad Symbol | Footprint |
|-----|-------|-------------|-----------|
| R1 | 49.9 | Device:R | Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal |
| R2 | 499 | Device:R | (same) |
| R3 | 4.99k | Device:R | (same) |
| R4 | 48.7k | Device:R | (same) |
| R5 | 499k | Device:R | (same) |
| R6 | 4.7M | Device:R | (same) |
| R7 | 10M | Device:R | (same) |
| R8 | 10M | Device:R | (same) |

**Wiring checklist — Mux channels to reference resistors:**

- [ ] U2 pin 3 (COM) → U1 pin 1 (CH0) — label: `ADC_CH0_RES`
- [ ] U2 pin 1 (Y0) → R1 pin 1, R1 pin 2 → `PROBE_VOHM`
- [ ] U2 pin 2 (Y1) → R2 pin 1, R2 pin 2 → `PROBE_VOHM`
- [ ] U2 pin 4 (Y2) → R3 pin 1, R3 pin 2 → `PROBE_VOHM`
- [ ] U2 pin 5 (Y3) → R4 pin 1, R4 pin 2 → `PROBE_VOHM`
- [ ] U2 pin 7 (Y4) → R5 pin 1, R5 pin 2 → `PROBE_VOHM`
- [ ] U2 pin 10 (Y5) → R6 pin 1, R6 pin 2 → `PROBE_VOHM`
- [ ] U2 pin 13 (Y6) → R7 pin 1, R7 pin 2 → `PROBE_VOHM`
- [ ] U2 pin 15 (Y7) → R8 pin 1, R8 pin 2 → `PROBE_VOHM`

**Wiring checklist — Mux control lines:**

- [ ] U2 pin 9 (S0) → A1 pin D22 — label: `MUX_S0`
- [ ] U2 pin 6 (S1) → A1 pin D23 — label: `MUX_S1`
- [ ] U2 pin 11 (S2) → A1 pin D24 — label: `MUX_S2`
- [ ] U2 pin 14 (S3) → A1 pin D25 — label: `MUX_S3`
- [ ] U2 pin 8 (~E) → A1 pin D26 — label: `MUX_EN`

---

#### Block 6: Current Measurement (U3 Mux + R9-R14 + U4 Op-Amp)

> [!abstract] **Goal:** Wire 6 current shunt resistors through the CD4053 to the LM358 current amplifier, feeding MCP3208 CH3.

**Place these components:**

| Ref | Value | KiCad Symbol | Footprint |
|-----|-------|-------------|-----------|
| R9 | 10k | Device:R | Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal |
| R10 | 1k | Device:R | (same) |
| R11 | 100 | Device:R | (same) |
| R12 | 10 | Device:R | (same) |
| R13 | 1 | Device:R | (same) |
| R14 | 0.1 | Device:R | (same) |
| R25 | 9.09k | Device:R | (same) |
| R26 | 1k | Device:R | (same) |
| J1 | 10A | Connector:Banana_Jack | Connector:Banana_Jack_1Pin |
| J2 | mA | Connector:Banana_Jack | Connector:Banana_Jack_1Pin |

**Wiring checklist — CD4053 switch channels to shunts:**

- [ ] U3 pin 4 (Y0a) → R9 pin 1 (10k shunt, 500uA range)
- [ ] U3 pin 5 (Y0c) → R11 pin 1 (100 shunt, 50mA range)
- [ ] U3 pin 2 (Y1a) → R10 pin 1 (1k shunt, 5mA range)
- [ ] U3 pin 14 (Y1c) → R12 pin 1 (10 shunt, 400mA range)
- [ ] U3 pin 12 (Y2a) → R13 pin 1 (1 shunt, 5A range)
- [ ] U3 pin 9 (Y2c) → R14 pin 1 (0.1 shunt, 10A range)

**Wiring checklist — Shunt common nodes:**

- [ ] U3 pin 15 (Y0_COM) + U3 pin 1 (Y1b) + U3 pin 6 (Y2b) → all tie together → label: `SHUNT_NODE`
- [ ] `SHUNT_NODE` → U4 pin 3 (OpA non-inverting input)
- [ ] R9-R13 pin 2 (all 5) → label: `CURRENT_MA_INPUT` → J2 pin 1 (mA terminal)
- [ ] R14 pin 2 → label: `CURRENT_10A_INPUT` → J1 pin 1 (10A terminal)

**Wiring checklist — CD4053 control lines:**

- [ ] U3 pin 11 (A) → A1 pin D27 — label: `CD4053_A`
- [ ] U3 pin 10 (B) → A1 pin D28 — label: `CD4053_B`
- [ ] U3 pin 13 (C) → A1 pin D29 — label: `CD4053_C`
- [ ] U3 pin 7 (INH) → A1 pin D30 — label: `CD4053_INH`
- [ ] U3 pin 7 (VEE) → `GND`

**Wiring checklist — LM358 Op-Amp A (current amplifier):**

- [ ] U4 pin 1 (OpA output) → U1 pin 4 (CH3) — label: `ADC_CH3_CURRENT`
- [ ] R25 pin 2 → `ADC_CH3_CURRENT` (feedback from output)
- [ ] R25 pin 1 → U4 pin 2 (OpA inverting input)
- [ ] R26 pin 2 → U4 pin 2 (OpA inverting input) — same node as R25 pin 1
- [ ] R26 pin 1 → `GND`

---

#### Block 7: AC Measurement (U4 Op-Amp B + D4)

> [!abstract] **Goal:** Wire the precision rectifier for AC voltage measurement on MCP3208 CH4.

**Place these components:**

| Ref | Value | KiCad Symbol | Footprint |
|-----|-------|-------------|-----------|
| D4 | 1N4148 | Device:D | Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal |

**Wiring checklist:**

- [ ] U4 pin 7 (OpB output) → U1 pin 5 (CH4) — label: `ADC_CH4_AC`
- [ ] D4 pin 2 (cathode) → `ADC_CH4_AC` (connects to OpB output)
- [ ] D4 pin 1 (anode) → U4 pin 6 (OpB inverting input)
- [ ] U4 pin 5 (OpB non-inverting input) — leave as stub for now (AC signal input)

---

#### Block 8: Frequency / Comparator (U5 + Threshold Divider)

> [!abstract] **Goal:** Wire the LM311 comparator with 2.5V threshold and pull-up output to Arduino INT4.

**Place these components:**

| Ref | Value | KiCad Symbol | Footprint |
|-----|-------|-------------|-----------|
| R20 | 10k | Device:R | Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal |
| R21 | 10k | Device:R | (same) |
| R22 | 10k | Device:R | (same) |

**Wiring checklist:**

- [ ] R21 pin 1 → `+5V`
- [ ] R21 pin 2 → R22 pin 1 (junction = 2.5V threshold) → U5 pin 3 (IN−)
- [ ] R22 pin 2 → `GND`
- [ ] U5 pin 2 (IN+) — leave as stub (frequency signal input)
- [ ] U5 pin 7 (OUT) → R20 pin 2 → A1 pin D2 — label: `COMP_OUTPUT`
- [ ] R20 pin 1 → `+5V` (pull-up)

---

#### Block 9: NE555 Constant Current Source (U6 + C4)

> [!abstract] **Goal:** Wire the NE555 timer with enable control from Arduino D33.

**Place these components:**

| Ref | Value | KiCad Symbol | Footprint |
|-----|-------|-------------|-----------|
| C4 | 100nF | Device:C | Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm |

**Wiring checklist:**

- [ ] U6 pin 2 (TR) → U6 pin 6 (THR) — tie together, label: `NE555_TRIG`
- [ ] U6 pin 5 (CV) → C4 pin 1, C4 pin 2 → `GND` (control voltage bypass)
- [ ] U6 pin 4 (~R) → A1 pin D33 — label: `NE555_ENABLE`
- [ ] U6 pin 3 (Q) — output stub (constant current to probes)
- [ ] U6 pin 7 (DIS) — discharge stub (timing resistor connection)

---

#### Block 10: Temperature Sensor (U7 → U1 CH5)

> [!abstract] **Goal:** Wire LM35 output to MCP3208 CH5. Simplest block — 1 wire.

**No new components.**

**Wiring checklist:**

- [ ] U7 pin 2 (VOUT) → U1 pin 6 (CH5) — label: `ADC_CH5_TEMP`
- [ ] (U7 power already connected in Block 1)

---

#### Block 11: User Interface (Buttons + LEDs + Buzzer)

> [!abstract] **Goal:** Wire 4 buttons, 3 LED circuits, and piezo buzzer to Arduino.

**Place these components:**

| Ref | Value | KiCad Symbol | Footprint |
|-----|-------|-------------|-----------|
| SW1 | MODE | Switch:SW_Push | Button_Switch_THT:SW_PUSH_6mm |
| SW2 | FUNC | Switch:SW_Push | Button_Switch_THT:SW_PUSH_6mm |
| SW3 | RANGE | Switch:SW_Push | Button_Switch_THT:SW_PUSH_6mm |
| SW4 | SELECT | Switch:SW_Push | Button_Switch_THT:SW_PUSH_6mm |
| R17 | 330 | Device:R | Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal |
| R18 | 330 | Device:R | (same) |
| R19 | 330 | Device:R | (same) |
| D1 | LED_Red | Device:LED | LED_THT:LED_D3.0mm |
| D2 | LED_Green | Device:LED | LED_THT:LED_D3.0mm |
| D3 | LED_Yellow | Device:LED | LED_THT:LED_D3.0mm |
| BZ1 | Buzzer | Device:Buzzer | Buzzer_Beeper:Buzzer_12x9.5RM7.6 |

**Wiring checklist — Buttons (active LOW, internal pull-ups):**

- [ ] A1 pin D3 → SW1 pin 1, SW1 pin 2 → `GND`
- [ ] A1 pin D4 → SW2 pin 1, SW2 pin 2 → `GND`
- [ ] A1 pin D5 → SW3 pin 1, SW3 pin 2 → `GND`
- [ ] A1 pin D6 → SW4 pin 1, SW4 pin 2 → `GND`

**Wiring checklist — LEDs (Arduino → 330R → LED → GND):**

- [ ] A1 pin D8 → R17 pin 1, R17 pin 2 → D1 anode (pin 1), D1 cathode (pin 2) → `GND`
- [ ] A1 pin D9 → R18 pin 1, R18 pin 2 → D2 anode (pin 1), D2 cathode (pin 2) → `GND`
- [ ] A1 pin D10 → R19 pin 1, R19 pin 2 → D3 anode (pin 1), D3 cathode (pin 2) → `GND`

**Wiring checklist — Buzzer:**

- [ ] A1 pin D7 → BZ1 pin 1 (+), BZ1 pin 2 (−) → `GND`

---

#### Block 12: Capacitance Timing (R27-R29)

> [!abstract] **Goal:** Wire 3 selectable RC timing resistors for capacitance measurement.

**Place these components:**

| Ref | Value | KiCad Symbol | Footprint |
|-----|-------|-------------|-----------|
| R27 | 1M | Device:R | Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal |
| R28 | 10k | Device:R | (same) |
| R29 | 100 | Device:R | (same) |

**Wiring checklist:**

- [ ] A1 pin D31 → R27 pin 1 (1M — large caps)
- [ ] A1 pin D32 → R28 pin 1 (10k — medium caps)
- [ ] R29 pin 1 — connect to charge control (stub for now)
- [ ] R27 pin 2 + R28 pin 2 + R29 pin 2 → all tie together → label: `CAP_TIMING_NODE`

---

#### Block 13: Final Checks & ERC

> [!abstract] **Goal:** Run KiCad's Electrical Rules Check and fix any errors.

- [ ] Run **Inspect → Electrical Rules Check** in KiCad
- [ ] Fix any unconnected pin warnings (add `no_connect` flags on unused U2 pins Y8-Y15)
- [ ] Add `no_connect` flags on: U1 pins 7+8 (CH6/CH7 stubs), U8 pin 7 (SQW)
- [ ] Verify all power pins show connected (no ERC errors on VCC/GND)
- [ ] Assign footprints: **Tools → Assign Footprints** — verify all components have THT footprints
- [ ] Annotate schematic: **Tools → Annotate Schematic** — auto-assign ref designators if needed
- [ ] Export netlist: **Tools → Generate Netlist** → save for PCB editor

---

### Schematic Reference Designators

| Ref     | Component         | Package     | Description                            |
| ------- | ----------------- | ----------- | -------------------------------------- |
| U1      | MCP3208           | DIP-16      | 12-bit SPI ADC, 8 channels             |
| U2      | 74HC4067          | DIP-24      | 16-channel analog multiplexer          |
| U3      | CD4053B           | DIP-16      | Triple 2:1 analog multiplexer          |
| U4      | LM358             | DIP-8       | Dual operational amplifier             |
| U5      | LM311             | DIP-8       | Voltage comparator                     |
| U6      | NE555             | DIP-8       | Timer IC (constant current source)     |
| U7      | LM35              | TO-92       | Temperature sensor (10 mV/C)           |
| U8      | DS1307            | DIP-8       | Real-time clock (I2C)                  |
| J5      | SSD1306 OLED      | 1x4 Header  | 128x64 I2C display module              |
| J6      | Arduino Mega 2560 | 1x36 Header | MCU board (connector representation)   |
| R1-R8   | Ref resistors     | Axial       | Ohmmeter ranges (49.9 - 10M)           |
| R9-R14  | Shunt resistors   | Axial       | Current ranges (0.1 - 10k)             |
| R15-R16 | Voltage divider   | Axial       | 1M + 100k (11:1 ratio)                 |
| R17-R19 | 330 Ohm           | Axial       | LED current limiters                   |
| R20     | 10k               | Axial       | LM311 output pull-up                   |
| R21-R22 | 10k + 10k         | Axial       | Comparator threshold divider           |
| R23-R24 | 10k + 10k         | Axial       | I2C bus pull-ups                       |
| R25     | 9.09k             | Axial       | Op-amp feedback Rf                     |
| R26     | 1k                | Axial       | Op-amp gain Rg                         |
| R27-R29 | Timing resistors  | Axial       | Capacitance measurement (1M, 10k, 100) |
| C1-C4   | 100nF ceramic     | Disc 5mm    | IC bypass decoupling                   |
| C5-C7   | 10uF electrolytic | Radial 5mm  | Bulk power supply filtering            |
| D1      | LED Red           | 3mm         | Overload warning                       |
| D2      | LED Green         | 3mm         | Normal operation                       |
| D3      | LED Yellow        | 3mm         | HOLD / Logging active                  |
| D4      | 1N4148            | DO-35       | Precision rectifier diode              |
| SW1-SW4 | Tactile switch    | 6mm         | MODE, FUNC, RANGE, SELECT              |
| BZ1     | Piezo buzzer      | 12mm        | Continuity beep                        |
| Y1      | 32.768 kHz        | Crystal     | DS1307 oscillator                      |
| BT1     | CR2032            | Holder      | RTC backup battery                     |
| J1-J4   | Banana jack       | 4mm         | Input terminals: 10A, mA, V/Ohm, COM   |

### Arduino Mega Header Pin Mapping (J6)

The Arduino Mega 2560 is represented as connector J6 in the netlist. Each header pin maps to a specific Arduino digital pin:

| J6 Pin | Arduino Pin | Function | Connected To |
|--------|-------------|----------|-------------|
| 1 | D50 | SPI MISO | U1 pin 12 (MCP3208 DOUT) |
| 2 | D51 | SPI MOSI | U1 pin 11 (MCP3208 DIN) |
| 3 | D52 | SPI SCK | U1 pin 13 (MCP3208 CLK) |
| 4 | D53 | SPI CS | U1 pin 10 (MCP3208 CS) |
| 5 | D20 | I2C SDA | U8 pin 5, J5 pin 3 (+ R23 pull-up) |
| 6 | D21 | I2C SCL | U8 pin 6, J5 pin 4 (+ R24 pull-up) |
| 7 | D22 | MUX S0 | U2 pin 9 |
| 8 | D23 | MUX S1 | U2 pin 6 |
| 9 | D24 | MUX S2 | U2 pin 11 |
| 10 | D25 | MUX S3 | U2 pin 14 |
| 11 | D26 | MUX EN | U2 pin 8 |
| 12 | D27 | CD4053 A | U3 pin 11 |
| 13 | D28 | CD4053 B | U3 pin 10 |
| 14 | D29 | CD4053 C | U3 pin 13 |
| 15 | D30 | CD4053 INH | U3 pin 7 |
| 16 | D2 | Freq INT4 | U5 pin 7 (LM311 output + R20) |
| 17 | D3 | BTN MODE | SW1 pin 1 |
| 18 | D4 | BTN FUNC | SW2 pin 1 |
| 19 | D5 | BTN RANGE | SW3 pin 1 |
| 20 | D6 | BTN SELECT | SW4 pin 1 |
| 21 | D7 | Buzzer | BZ1 pin 1 |
| 22 | D8 | Red LED | R17 pin 1 |
| 23 | D9 | Green LED | R18 pin 1 |
| 24 | D10 | Yellow LED | R19 pin 1 |
| 25 | D33 | NE555 Enable | U6 pin 4 (Reset) |
| 26 | 5V | Power | +5V rail |
| 27 | GND | Ground | GND rail |
| 28 | D31 | Cap charge | R27 pin 1 (1M timing) |
| 29 | D32 | Cap discharge | R28 pin 1 (10k timing) |
| 30 | — | Cap timing | R29 pin 1 (100 timing) |

### Subcircuit 1: MCP3208 ADC (U1)

The MCP3208 is the central measurement engine. All analog signals are routed to its 8 channels via signal conditioning circuits.

```
                    MCP3208 (U1)
              ┌────────────────────┐
   ADC_CH0 ──┤ 1  CH0    VDD  16 ├── +5V
   ADC_CH1 ──┤ 2  CH1    VREF 15 ├── +5V
   ADC_CH2 ──┤ 3  CH2    AGND 14 ├── GND
   ADC_CH3 ──┤ 4  CH3    CLK  13 ├── D52 (SCK)
   ADC_CH4 ──┤ 5  CH4    DOUT 12 ├── D50 (MISO)
   ADC_CH5 ──┤ 6  CH5    DIN  11 ├── D51 (MOSI)
   ADC_CH6 ──┤ 7  CH6    CS   10 ├── D53 (CS)
   ADC_CH7 ──┤ 8  CH7    DGND  9 ├── GND
              └────────────────────┘
```

**Channel Assignments:**

| Channel | Net Name | Signal Source | Measurement |
|---------|----------|--------------|-------------|
| CH0 | ADC_CH0_RES | 74HC4067 COM (U2 pin 3) | Resistance via mux |
| CH1 | ADC_CH1_VDIV | Voltage divider midpoint (R15/R16) | High-range voltage (0-55V) |
| CH2 | PROBE_VOHM | Direct from V/Ohm terminal (J3) | Low-range voltage (0-5V) |
| CH3 | ADC_CH3_CURRENT | LM358 OpA output (U4 pin 1) | Current (amplified) |
| CH4 | ADC_CH4_AC | LM358 OpB output (U4 pin 7) | AC voltage (rectified) |
| CH5 | ADC_CH5_TEMP | LM35 output (U7 pin 2) | Temperature |
| CH6 | ADC_CH6_SCOPE | External scope input | Oscilloscope |
| CH7 | ADC_CH7_AUX | Reserved | Auxiliary / spare |

**Bypass:** C1 (100nF) between VDD (pin 16) and DGND (pin 9).

### Subcircuit 2: Resistance Measurement (U2 + R1-R8)

The 74HC4067 selects one of 8 precision reference resistors. The selected resistor forms a voltage divider with the unknown resistance connected to the V/Ohm terminal (J3). The MCP3208 reads the divided voltage on CH0.

```
                     74HC4067 (U2)
               ┌─────────────────────┐
  R1 (49.9) ──┤ 1  Y0     VCC   24 ├── +5V
  R2 (499)  ──┤ 2  Y1     Y15   23 ├── NC
  MCP3208 CH0─┤ 3  COM    Y14   22 ├── NC
  R3 (4.99k)──┤ 4  Y2     Y13   21 ├── NC
  R4 (48.7k)──┤ 5  Y3     Y12   20 ├── NC
  D23 (S1)  ──┤ 6  S1     Y11   19 ├── NC
  R5 (499k) ──┤ 7  Y4     Y10   18 ├── NC
  D26 (EN)  ──┤ 8  ~E     Y9    17 ├── NC
  D22 (S0)  ──┤ 9  S0     Y8    16 ├── NC
  R6 (4.7M) ──┤10  Y5     Y7    15 ├── R8 (10M)
  D24 (S2)  ──┤11  S2     S3    14 ├── D25
  GND       ──┤12  GND    Y6    13 ├── R7 (10M)
               └─────────────────────┘
```

**Reference Resistor Network:**
Each mux channel (Y0-Y7) connects to one end of a precision reference resistor. The other end of ALL reference resistors connects to the common `PROBE_VOHM` net (the V/Ohm terminal J3).

| Mux Ch | Resistor | Value | Measurement Range |
|--------|----------|-------|-------------------|
| Y0 | R1 | 49.9 Ohm | 50 Ohm range |
| Y1 | R2 | 499 Ohm | 500 Ohm range |
| Y2 | R3 | 4.99 kOhm | 5k range |
| Y3 | R4 | 48.7 kOhm | 50k range |
| Y4 | R5 | 499 kOhm | 500k range |
| Y5 | R6 | 4.7 MOhm | 5M range |
| Y6 | R7 | 10 MOhm | 50M range |
| Y7 | R8 | 10 MOhm | Conductance |

**Bypass:** C2 (100nF) between VCC (pin 24) and GND (pin 12).

### Subcircuit 3: Current Measurement (U3 + R9-R14 + U4)

The CD4053 triple 2:1 mux selects one of 6 current shunt resistors. The voltage across the selected shunt is amplified by the LM358 and read on MCP3208 CH3.

```
                     CD4053B (U3)
               ┌─────────────────────┐
  SHUNT_NODE──┤ 1  Y1b    VDD   16 ├── +5V
  R10 (1k)  ──┤ 2  Y1a    Y0_COM15 ├── SHUNT_NODE
  SHUNT_NODE──┤ 3  Y0b    Y1c   14 ├── R12 (10)
  R9 (10k)  ──┤ 4  Y0a    C     13 ├── D29
  R11 (100) ──┤ 5  Y0c    Y2a   12 ├── R13 (1)
  to OpA    ──┤ 6  Y2b    A     11 ├── D27
  D30 (INH) ──┤ 7  INH    B     10 ├── D28
  GND       ──┤ 8  VSS    Y2c    9 ├── R14 (0.1)
               └─────────────────────┘
```

**Shunt Selection:**
The three CD4053 switches (Y0, Y1, Y2) each select between two shunt resistors. All three common outputs (pins 1, 3/15, 6) are tied together at the `SHUNT_NODE` net, which feeds the LM358 Op-Amp A non-inverting input (U4 pin 3).

| Switch | A input | C input | Selection bits |
|--------|---------|---------|----------------|
| Y0 | R9 (10k) - 500uA | R11 (100) - 50mA | A bit |
| Y1 | R10 (1k) - 5mA | R12 (10) - 400mA | B bit |
| Y2 | R13 (1) - 5A | R14 (0.1) - 10A | C bit |

**Current Input Routing:**
- Shunts R9-R13: Other end connects to J2 (mA terminal) via `CURRENT_MA_INPUT` net
- Shunt R14 (0.1 Ohm): Other end connects to J1 (10A terminal) via `CURRENT_10A_INPUT` net
- All shunts return through J4 (COM terminal) to GND

**Bypass:** C3 (100nF) between VDD (pin 16) and VSS (pin 8).

### Subcircuit 4: LM358 Dual Op-Amp (U4)

```
                     LM358 (U4)
               ┌─────────────────────┐
  to CH3    ──┤ 1  OUT_A   V+    8 ├── +5V
  Feedback  ──┤ 2  IN-_A   OUT_B 7 ├── to CH4
  SHUNT_NODE──┤ 3  IN+_A   IN-_B 6 ├── D4 anode (feedback)
  GND       ──┤ 4  V-      IN+_B 5 ├── AC signal input
               └─────────────────────┘
```

**Op-Amp A (Current Amplifier):**
- Non-inverting input (pin 3): Receives voltage from `SHUNT_NODE` (CD4053 output)
- Inverting input (pin 2): Feedback network — R25 (9.09k) from output, R26 (1k) to GND
- Gain: 1 + (R25/R26) = 1 + (9.09k/1k) = **10.09x** (high gain mode)
- Output (pin 1): `ADC_CH3_CURRENT` → MCP3208 CH3

**Op-Amp B (AC Precision Rectifier):**
- Non-inverting input (pin 5): AC measurement signal
- Inverting input (pin 6): Precision rectifier feedback via D4 (1N4148)
- Output (pin 7): `ADC_CH4_AC` → MCP3208 CH4
- D4 cathode connects to output (pin 7), anode to inverting input (pin 6)

### Subcircuit 5: LM311 Comparator (U5)

Converts analog frequency signals into clean digital edges for the ATmega2560 INT4 hardware counter.

```
                     LM311 (U5)
               ┌─────────────────────┐
  GND       ──┤ 1  GND     V+    8 ├── +5V
  Signal in ──┤ 2  IN+     OUT   7 ├── D2 (INT4) + R20 pull-up
  2.5V ref  ──┤ 3  IN-     BAL/S 6 ├── NC
  GND       ──┤ 4  V-      BAL   5 ├── NC
               └─────────────────────┘
```

**Threshold Voltage:** 2.5V from R21/R22 divider (10k+10k from +5V to GND)
**Output:** Open-collector, pulled up to +5V via R20 (10k). Connects to Arduino D2 (INT4).

### Subcircuit 6: NE555 Constant Current Source (U6)

Provides a stable ~10mA current for low-ohm resistance measurement and diode forward-voltage testing.

```
                     NE555 (U6)
               ┌─────────────────────┐
  GND       ──┤ 1  GND     VCC   8 ├── +5V
  Timing    ──┤ 2  TR      DIS   7 ├── Timing resistor
  Output    ──┤ 3  Q       THR   6 ├── Timing (= pin 2)
  D33 (EN)  ──┤ 4  ~R      CV    5 ├── C4 (100nF to GND)
               └─────────────────────┘
```

- **Reset (pin 4):** Controlled by Arduino D33. HIGH = enabled, LOW = disabled.
- **Trigger/Threshold (pins 2,6):** Tied together for astable operation.
- **Control Voltage (pin 5):** Bypassed to GND through C4 (100nF) for noise rejection.
- **Output (pin 3):** Constant current to measurement probes.

### Subcircuit 7: Temperature Sensor (U7)

```
  +5V ── U7 pin 1 (VCC)
          U7 pin 2 (VOUT) ── MCP3208 CH5 (ADC_CH5_TEMP)
  GND ── U7 pin 3 (GND)
```

Output: 10 mV per degree Celsius. At 25C: ~250 mV.

### Subcircuit 8: DS1307 RTC (U8)

```
  Y1 pin 1 ── U8 pin 1 (X1)
  Y1 pin 2 ── U8 pin 2 (X2)     32.768 kHz crystal
  BT1 (+) ─── U8 pin 3 (VBAT)   CR2032 backup
  GND ─────── U8 pin 4 (GND)
  I2C_SDA ─── U8 pin 5 (SDA)    Shared I2C bus
  I2C_SCL ─── U8 pin 6 (SCL)    Shared I2C bus
  NC ───────── U8 pin 7 (SQW)
  +5V ──────── U8 pin 8 (VCC)
```

I2C Address: 0x68. Bus shared with SSD1306 OLED (0x3C).

### Subcircuit 9: SSD1306 OLED Display (J5)

4-pin I2C module connector:

| J5 Pin | Signal | Connection |
|--------|--------|------------|
| 1 | VCC | +5V |
| 2 | GND | GND |
| 3 | SDA | I2C_SDA (+ R23 10k pull-up) |
| 4 | SCL | I2C_SCL (+ R24 10k pull-up) |

### Subcircuit 10: Voltage Divider (R15 + R16)

```
  J3 (V/Ohm) ──── R15 (1M) ────┬──── MCP3208 CH1 (ADC_CH1_VDIV)
                                │
                            R16 (100k)
                                │
                               GND
```

Divider ratio: (1M + 100k) / 100k = **11:1**
Maximum input: 5V x 11 = 55V (single stage)

### Subcircuit 11: User Interface

**LED Circuits (x3):**
```
  Arduino pin ── R (330 Ohm) ── LED anode ──┤ LED cathode ── GND
```

| Arduino | Resistor | LED | Color | Function |
|---------|----------|-----|-------|----------|
| D8 (J6.22) | R17 | D1 | Red | Overload warning |
| D9 (J6.23) | R18 | D2 | Green | Normal operation |
| D10 (J6.24) | R19 | D3 | Yellow | HOLD / Logging |

**Buttons (x4, active LOW with internal MCU pull-ups):**
```
  Arduino pin ──── SW ──── GND
```

| Arduino | Switch | Function |
|---------|--------|----------|
| D3 (J6.17) | SW1 | MODE (INT5 interrupt) |
| D4 (J6.18) | SW2 | FUNC (polled) |
| D5 (J6.19) | SW3 | RANGE (polled) |
| D6 (J6.20) | SW4 | SELECT (polled) |

**Buzzer:**
```
  D7 (J6.21) ── BZ1 (+) ── BZ1 (-) ── GND
```

### Subcircuit 12: Capacitance Timing (R27-R29)

Three selectable RC timing resistors for capacitance measurement. The firmware selects one resistor by driving the corresponding Arduino pin, forming an RC circuit with the unknown capacitor. The charge time is measured to calculate capacitance.

| Arduino | Resistor | Value | Cap Range |
|---------|----------|-------|-----------|
| D31 (J6.28) | R27 | 1M | Large caps (uF-F) |
| D32 (J6.29) | R28 | 10k | Medium caps (nF-uF) |
| J6.30 | R29 | 100 | Small caps (pF-nF) |

All three resistor outputs connect to a common `CAP_TIMING_NODE` where the unknown capacitor is attached.

### Power Distribution

**+5V Rail** feeds:
- All IC VCC/VDD pins (U1-U8)
- OLED module VCC (J5 pin 1)
- Arduino 5V output (J6 pin 26)
- Pull-up resistor tops: R20, R21, R23, R24
- Bypass caps positive: C1, C2, C3
- Bulk caps positive: C5, C6, C7

**GND Rail** connects:
- All IC GND/VSS pins
- OLED GND, Arduino GND
- Voltage divider bottom (R16 pin 2)
- Threshold divider bottom (R22 pin 2)
- Op-amp gain Rg bottom (R26 pin 1)
- All capacitor negatives (C1-C7)
- LED cathodes (D1-D3 pin 2)
- Button returns (SW1-SW4 pin 2)
- Buzzer negative, Battery negative
- COM terminal (J4 pin 1)

### Complete Net Table

| Net | Name | Nodes | Description |
|-----|------|-------|-------------|
| 1 | GND | 32 | Ground rail |
| 2 | +5V | 21 | Power rail |
| 3 | SPI_MISO | 2 | U1.12 ↔ J6.1 |
| 4 | SPI_MOSI | 2 | U1.11 ↔ J6.2 |
| 5 | SPI_SCK | 2 | U1.13 ↔ J6.3 |
| 6 | SPI_CS | 2 | U1.10 ↔ J6.4 |
| 7 | I2C_SDA | 4 | U8.5, J5.3, J6.5, R23.2 |
| 8 | I2C_SCL | 4 | U8.6, J5.4, J6.6, R24.2 |
| 9 | ADC_CH0_RES | 2 | U1.1 ↔ U2.3 (mux COM) |
| 10 | ADC_CH1_VDIV | 3 | U1.2, R15.2, R16.1 |
| 11 | PROBE_VOHM | 11 | J3.1, U1.3, R15.1, R1-R8 pin 2 |
| 12 | ADC_CH3_CURRENT | 3 | U1.4, U4.1, R25.2 |
| 13 | ADC_CH4_AC | 3 | U1.5, U4.7, D4.2 |
| 14 | ADC_CH5_TEMP | 2 | U1.6 ↔ U7.2 |
| 15 | ADC_CH6_SCOPE | 1 | U1.7 (stub) |
| 16 | ADC_CH7_AUX | 1 | U1.8 (stub) |
| 17-21 | MUX_S0..EN | 2 each | U2 control ↔ J6 D22-D26 |
| 22-29 | MUX_Y0..Y7 | 2 each | U2 channels ↔ R1-R8 pin 1 |
| 30-33 | CD4053_A..INH | 2 each | U3 control ↔ J6 D27-D30 |
| 34 | SHUNT_NODE | 4 | U3 commons (1,3/15,6) + U4.3 |
| 35-40 | SHUNT_Y0..Y2 | 2 each | U3 switch pins ↔ R9-R14 pin 1 |
| 41 | CURRENT_MA_INPUT | 6 | J2.1, R9-R13 pin 2 |
| 42 | CURRENT_10A_INPUT | 2 | J1.1, R14.2 |
| 43 | OPA_FEEDBACK | 3 | U4.2, R25.1, R26.2 |
| 44 | OPB_NONINV | 1 | U4.5 (stub) |
| 45 | OPB_INV_FEEDBACK | 2 | U4.6, D4.1 |
| 46 | COMP_INPUT | 1 | U5.2 (stub) |
| 47 | COMP_THRESHOLD | 3 | U5.3, R21.2, R22.1 |
| 48 | COMP_OUTPUT | 3 | U5.7, R20.2, J6.16 |
| 49 | NE555_TRIG_THRESH | 2 | U6.2, U6.6 |
| 50 | NE555_OUTPUT | 1 | U6.3 (stub) |
| 51 | NE555_CONTROL | 2 | U6.5, C4.1 |
| 52 | NE555_DISCHARGE | 1 | U6.7 (stub) |
| 53 | NE555_ENABLE | 2 | U6.4, J6.25 |
| 54-55 | RTC_X1, X2 | 2 each | U8 pins 1-2 ↔ Y1 |
| 56 | RTC_VBAT | 2 | U8.3 ↔ BT1.1 |
| 57-60 | BTN_MODE..SELECT | 2 each | J6 D3-D6 ↔ SW1-SW4 |
| 61 | BUZZER_CTRL | 2 | J6.21 ↔ BZ1.1 |
| 62-67 | LED nets | 2 each | J6 D8-D10 → R17-R19 → D1-D3 |
| 68-71 | CAP_TIMING | 2-3 | J6 D31-D32 → R27-R29 → common node |

---

## 🛠️ Firmware Architecture

Bare-metal AVR C project using PlatformIO. No Arduino framework — all peripheral access is through direct register manipulation.

### Project Structure

```
dtu-multimeter/
├── platformio.ini          # PlatformIO config (ATmega2560, -Os, C11)
├── include/
│   ├── config.h            # Master config: pins, calibration, enums
│   ├── spi.h               # Hardware SPI driver
│   ├── i2c.h               # Hardware I2C (TWI) driver
│   ├── uart.h              # UART with TX/RX ring buffers
│   ├── timer.h             # Timer0 millis(), delay, PWM
│   ├── adc_mcp3208.h       # MCP3208 SPI ADC interface
│   ├── mux.h               # 74HC4067 + CD4053 mux control
│   ├── display.h           # SSD1306 low-level I2C driver
│   ├── display_render.h    # Fluke-style screen rendering
│   ├── font5x7.h           # 5x7 bitmap font (PROGMEM)
│   ├── trms.h              # True-RMS calculation engine
│   ├── rtc_ds1307.h        # DS1307 RTC driver (I2C)
│   ├── autorange.h         # Auto-ranging state machine
│   ├── measure.h           # 22-mode measurement dispatcher
│   ├── ui.h                # Button handling + serial commands
│   ├── scope.h             # Oscilloscope capture + rendering
│   └── logging.h           # EEPROM circular data logger
└── src/
    ├── main.c              # Super loop: init → measure → display → UI
    ├── spi.c               # SPI master init and transfer
    ├── i2c.c               # TWI start/stop/read/write
    ├── uart.c              # Interrupt-driven UART
    ├── timer.c             # Timer0 overflow ISR, millis()
    ├── adc_mcp3208.c       # MCP3208 single-ended read + oversampling
    ├── mux.c               # Mux channel select, enable/disable
    ├── display.c           # SSD1306 init, framebuffer flush
    ├── display_render.c    # render_measurement(), render_scope(), splash
    ├── font5x7.c           # ASCII font bitmap data
    ├── trms.c              # RMS accumulator (sum-of-squares, sqrt)
    ├── rtc_ds1307.c        # BCD time read/write
    ├── autorange.c         # Hysteresis-based range up/down
    ├── measure.c           # All 22 measurement functions
    ├── ui.c                # Button ISR/poll, serial command parser
    ├── scope.c             # ADC burst capture, triggering, auto-meas
    └── logging.c           # EEPROM write with circular pointer
```

### Key Design Decisions

> [!important] **No Arduino Framework**
> The firmware uses no Arduino libraries. All register access (`DDRB`, `PORTB`, `SPCR`, `TWCR`, etc.) is done directly. This gives full control over timing, interrupt priorities, and code size. PlatformIO compiles with `-Os` optimization and C11 standard.

> [!tip] **Super Loop Architecture**
> The main loop runs: poll buttons → dispatch measurement → apply secondary functions (REL/HOLD/MIN-MAX) → update display at 5 Hz → log data at 1 Hz. The oscilloscope mode takes a separate fast path for ADC burst capture.

---

## 🔬 Calibration Procedure

All calibration constants live in `config.h`. Measure actual values with a known-good meter and update before first use.

1. **V_REF** — Measure the Mega 5V pin with a reference meter. Update `V_REF` (default: 5.000 V)
2. **Reference Resistors** — Measure each of the 8 resistors on the 74HC4067 mux. Update `RREF_0` through `RREF_7`
3. **Voltage Divider** — Measure actual R1 and R2 in the 1M/100k divider. Update `VDIV_RATIO` (default: 11.0)
4. **Current Shunts** — Measure each of the 6 shunt resistors. Update `ISHUNT_0` through `ISHUNT_5`
5. **Op-Amp Gain** — Verify LM358 gain stages. Update `CUR_GAIN_LO` (1.0) and `CUR_GAIN_HI` (10.0, from 9.09k/1k feedback)
6. **NE555 Current** — Measure the constant current output with a mA meter. Update `I_SOURCE` (default: 10 mA)
7. **Temperature Offset** — Compare LM35 reading against a known temperature. Apply offset in `meas_temperature()`

> [!warning] **Calibrate Before Trusting Readings**
> The default constants are nominal/ideal values. Real component tolerances (especially the E96 resistors from the DTU component shop) will introduce errors. Calibration is required for accurate measurements.

---

## 🚀 Build Phases

- [x] **Research** — Fluke 289 feature analysis, component feasibility study
- [x] **Component selection** — ICs and passives from DTU component shop
- [x] **Firmware architecture** — 17 source files, modular C structure, PlatformIO project
- [ ] **Low-level drivers** — SPI, I2C, UART, Timer (register-level)
- [ ] **Peripheral drivers** — MCP3208 ADC, SSD1306 OLED, DS1307 RTC, mux control
- [ ] **Measurement modes** — All 22 modes with auto-ranging
- [ ] **UI + display** — Fluke-style OLED rendering, button handling, serial CLI
- [ ] **Scope mode** — ADC burst capture, triggering, waveform rendering
- [ ] **Breadboard prototype** — Full circuit on breadboard, end-to-end testing
- [ ] **Calibration** — Measure actual component values, update config.h
- [ ] **Final build** — Soldered protoboard or PCB, enclosure

---

## 📚 References

- [MCP3208 Datasheet (Microchip)](https://ww1.microchip.com/downloads/en/DeviceDoc/21298e.pdf)
- [SSD1306 Datasheet (Solomon Systech)](https://cdn-shop.adafruit.com/datasheets/SSD1306.pdf)
- [ATmega2560 Datasheet (Microchip)](https://ww1.microchip.com/downloads/en/devicedoc/atmel-2549-8-bit-avr-microcontroller-atmega640-1280-1281-2560-2561_datasheet.pdf)
- [74HC4067 Datasheet (TI)](https://www.ti.com/lit/ds/symlink/cd74hc4067.pdf)
- [CD4053 Datasheet (TI)](https://www.ti.com/lit/ds/symlink/cd4053b.pdf)
- [LM358 Datasheet (TI)](https://www.ti.com/lit/ds/symlink/lm358.pdf)
- [LM311 Datasheet (TI)](https://www.ti.com/lit/ds/symlink/lm311.pdf)
- [LM35 Datasheet (TI)](https://www.ti.com/lit/ds/symlink/lm35.pdf)
- [DS1307 Datasheet (Maxim)](https://datasheets.maximintegrated.com/en/ds/DS1307.pdf)
- [NE555 Datasheet (TI)](https://www.ti.com/lit/ds/symlink/ne555.pdf)
- [PlatformIO ATmega2560](https://docs.platformio.org/en/latest/boards/atmelavr/megaatmega2560.html)

---
