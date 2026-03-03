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
