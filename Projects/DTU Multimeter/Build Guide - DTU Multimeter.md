---
title: Build Guide - DTU Digital Multimeter
type: build-guide
tags:
  - electronics
  - avr
  - embedded
  - dtu
  - atmega2560
status: In Development
started: 2026-03-03
updated: 2026-03-04
parent: "[[DTU Multimeter - Digital Multimeter]]"
---

# Build Guide - DTU Digital Multimeter

> [!summary] **Overview**
> Step-by-step build, flash, and calibration guide for the DTU digital multimeter.
> Bare-metal AVR C on ATmega2560 — no Arduino framework, just registers and datasheets.
> - Build on breadboard, flash with PlatformIO, calibrate with known references
> - Test each subsystem before moving to the next
> - 22 measurement modes: DCV, ACV, resistance, capacitance, inductance, frequency, current, temperature, scope, and more

---

## :toolbox: Prerequisites

### Hardware

| Item | Purpose |
|------|---------|
| **Arduino Mega 2560** | ATmega2560 target board (16 MHz) |
| **SSD1306 OLED** (128x64, I2C) | Main display |
| **MCP3208** | 12-bit SPI ADC (8 channels) |
| **74HC4067** | 16-channel analog mux (resistance ranges) |
| **CD4053** | Triple 2:1 analog switch (current ranges) |
| **LM358** | Dual op-amp (current amplifier + AC rectifier) |
| **LM311** | Comparator (frequency input) |
| **DS1307** | RTC with 32.768 kHz crystal + backup battery |
| **LM35** | Temperature sensor |
| **NE555** | Constant current source (capacitance + low-ohm) |
| **Breadboard** (full-size) | Prototyping |
| **Jumper wires** | Connections |
| **USB-B cable** | Power + programming |
| **4x tactile buttons** | MODE, FUNC, RANGE, SELECT |
| **3x LEDs** (red, green, yellow) | Status indicators |
| **Piezo buzzer** | Continuity beep |
| **Resistors** | Reference resistors, voltage divider, shunts, pull-ups |

> [!note] Component Sourcing
> All ICs are available from the DTU component shop. Reference resistors should be the
> closest E96 values you can find — measure the actual values and update `config.h`.

### Software

| Tool | Purpose |
|------|---------|
| **PlatformIO** (VS Code extension or CLI) | Build toolchain for AVR |
| **Serial terminal** (PlatformIO monitor, PuTTY, etc.) | UART communication at 115200 baud |
| **Multimeter** (any) | Calibration reference measurements |

---

## :computer: PlatformIO Setup

### Install and Build

1. Install PlatformIO IDE (VS Code extension) or the CLI:
   ```
   pip install platformio
   ```

2. Clone or copy the `dtu-multimeter/` project folder. The project structure:
   ```
   dtu-multimeter/
   ├── platformio.ini
   ├── include/
   │   ├── config.h          ← Calibration constants live here
   │   ├── adc_mcp3208.h
   │   ├── display.h
   │   ├── measure.h
   │   └── ...
   └── src/
       ├── main.c
       ├── adc_mcp3208.c
       ├── display.c
       ├── measure.c
       └── ...
   ```

3. Compile to verify the toolchain:
   ```
   pio run
   ```

4. Connect the Arduino Mega via USB and flash:
   ```
   pio run -t upload
   ```

5. Open the serial terminal:
   ```
   pio device monitor
   ```
   Baud rate is **115200** (configured in `platformio.ini`).

> [!important] Bare-Metal AVR
> This project does **not** use the Arduino framework. The `platformio.ini` omits
> `framework = arduino` intentionally. All peripheral access is via direct AVR register
> manipulation. The AVR-GCC toolchain is pulled in by `platform = atmelavr`.

---

## :bread: Breadboard Assembly

Build each step in order. Test power and connectivity at each stage before continuing.

---

> [!note]- **Step 1: Power Rails**
> Connect the Arduino Mega power pins to the breadboard.
>
> | Arduino Pin | Breadboard Rail | Notes |
> |-------------|-----------------|-------|
> | 5V | + rail (red) | Main supply for all ICs |
> | GND | - rail (blue) | Common ground |
>
> Use short jumper wires. Bridge both sides of the breadboard if using a full-size board.
> Verify **5.0V** between the rails with a multimeter before connecting anything else.

---

> [!note]- **Step 2: MCP3208 ADC — SPI Bus**
> The MCP3208 is the main 12-bit ADC. It connects via hardware SPI on the Mega.
>
> | MCP3208 Pin | Connect To | Arduino Pin |
> |-------------|------------|-------------|
> | VDD (pin 16) | +5V rail | — |
> | VREF (pin 15) | +5V rail | — |
> | AGND (pin 14) | GND rail | — |
> | DGND (pin 9) | GND rail | — |
> | CLK (pin 13) | SCK | D52 (PB1) |
> | DIN (pin 11) | MOSI | D51 (PB2) |
> | DOUT (pin 12) | MISO | D50 (PB3) |
> | CS (pin 10) | Chip Select | D53 (PB0) |
>
> **Channel assignments** (directly or via analog circuits):
>
> | MCP3208 CH | Signal | Source |
> |------------|--------|--------|
> | CH0 | Resistance (from mux COM) | 74HC4067 output |
> | CH1 | Voltage high range | Divider output (1M + 100k) |
> | CH2 | Voltage low range / mV | Direct probe input |
> | CH3 | Current | LM358 amplifier output |
> | CH4 | AC rectified | LM358 rectifier output |
> | CH5 | Temperature | LM35 output |
> | CH6 | Scope (external ADC) | Scope input |
> | CH7 | Auxiliary | Reserved |

---

> [!note]- **Step 3: SSD1306 OLED — I2C Bus**
> The 128x64 OLED display connects to the hardware I2C bus.
>
> | OLED Pin | Connect To | Arduino Pin |
> |----------|------------|-------------|
> | SDA | I2C data | D20 (SDA) |
> | SCL | I2C clock | D21 (SCL) |
> | VCC | +5V rail (or 3.3V if module has regulator) | — |
> | GND | GND rail | — |
>
> The default I2C address is **0x3C** (configured in `config.h` as `OLED_ADDR`).
> Most SSD1306 modules have an onboard voltage regulator and accept 5V.

---

> [!note]- **Step 4: 74HC4067 Mux — Resistance Range Selection**
> The 16-channel analog mux selects which reference resistor is in the measurement path.
>
> | 74HC4067 Pin | Connect To | Arduino Pin |
> |--------------|------------|-------------|
> | S0 | Address bit 0 | D22 (PA0) |
> | S1 | Address bit 1 | D23 (PA1) |
> | S2 | Address bit 2 | D24 (PA2) |
> | S3 | Address bit 3 | D25 (PA3) |
> | EN (active LOW) | Enable | D26 (PA4) |
> | COM | Analog common | MCP3208 CH0 |
> | VCC | +5V rail | — |
> | GND | GND rail | — |
>
> Connect reference resistors to mux channels 0-7:
>
> | Mux CH | Nominal | Measured | Range |
> |--------|---------|----------|-------|
> | 0 | 50 Ohm | **50.15 Ohm** | 50 Ohm range |
> | 1 | 499 Ohm | **497.0 Ohm** | 500 Ohm range |
> | 2 | 4.99 kOhm | **4.990 kOhm** | 5k range |
> | 3 | 48.7 kOhm | **48.536 kOhm** | 50k range (E96) |
> | 4 | 499 kOhm | **498.0 kOhm** | 500k range |
> | 5 | 4.7 MOhm | **4.755 MOhm** | 5M range |
> | 6 | 10 MOhm | **10.06 MOhm** | 50M range |
> | 7 | 10 MOhm | **10.03 MOhm** | Conductance |

---

> [!note]- **Step 5: Voltage Divider**
> Two-resistor divider for high-voltage range. Low range connects directly.
>
> ```
>   V_input ──[1M]──┬──[100k]── GND
>                    │
>                    └── MCP3208 CH1  (divided by 11:1)
>
>   V_input ──────────── MCP3208 CH2  (direct, low/mV range)
> ```
>
> | Component | Nominal | Measured | Connection |
> |-----------|---------|----------|------------|
> | R_high | 1 MOhm | **1.002 MOhm** | Input to divider node |
> | R_low | 100 kOhm | **100.0 kOhm** | Divider node to GND |
> | Divider output | — | — | MCP3208 CH1 |
> | Direct input | — | — | MCP3208 CH2 |
>
> **Divider ratio:** (1.002M + 100k) / 100k = **11.02:1** (`VDIV_RATIO` in config.h)

---

> [!note]- **Step 6: CD4053 Current Range Switches**
> The CD4053 triple 2:1 analog switch selects between current shunt resistors.
>
> | CD4053 Pin | Connect To | Arduino Pin |
> |------------|------------|-------------|
> | A (select) | Control A | D27 (PA5) |
> | B (select) | Control B | D28 (PA6) |
> | C (select) | Control C | D29 (PA7) |
> | INH (inhibit, active HIGH) | Inhibit | D30 (PC7) |
> | VEE | GND rail | — |
> | VDD | +5V rail | — |
> | VSS | GND rail | — |
>
> Connect current shunt resistors to the switch channels:
>
> | Range | Nominal | Measured | Full-Scale Current |
> |-------|---------|----------|-------------------|
> | 0 | 10 kOhm | **10.00 kOhm** | 500 uA |
> | 1 | 1 kOhm | **998.0 Ohm** | 5 mA |
> | 2 | 100 Ohm | **99.49 Ohm** | 50 mA |
> | 3 | 10 Ohm | **10.04 Ohm** | 400 mA |
> | 4 | 1 Ohm | **1.05 Ohm** | 5 A |
> | 5 | 0.1 Ohm | **0.145 Ohm** (4-wire) | 10 A |
>
> Route the selected shunt output to the LM358 current amplifier input.

---

> [!note]- **Step 7: LM358 Op-Amp — Current Amplifier + AC Rectifier**
> The LM358 dual op-amp handles two functions:
>
> **Op-amp A — Current amplifier** (gain switchable):
> - Low gain: unity (1x) for high-current ranges
> - High gain: 10x (9.09k / 1k feedback) for low-current ranges
> - Input from CD4053 shunt output
> - Output to MCP3208 CH3
>
> **Op-amp B — AC precision rectifier:**
> - Half-wave precision rectifier for AC voltage/current
> - Input from measurement signal
> - Output to MCP3208 CH4
>
> | LM358 Pin | Function | Connection |
> |-----------|----------|------------|
> | Pin 1 | Op-A output | MCP3208 CH3 |
> | Pin 2 | Op-A inverting input | Feedback network |
> | Pin 3 | Op-A non-inverting input | Shunt voltage |
> | Pin 4 | V- | GND rail |
> | Pin 5 | Op-B non-inverting input | AC signal |
> | Pin 6 | Op-B inverting input | Rectifier feedback |
> | Pin 7 | Op-B output | MCP3208 CH4 |
> | Pin 8 | V+ | +5V rail |

---

> [!note]- **Step 8: Buttons — MODE, FUNC, RANGE, SELECT**
> All buttons are active-LOW with internal pull-ups enabled in firmware.
>
> | Button | Arduino Pin | AVR Port | Mechanism |
> |--------|-------------|----------|-----------|
> | MODE | D3 | PE5 (INT5) | Interrupt-driven (falling edge) |
> | FUNC | D4 | PG5 | Polled with 50ms debounce |
> | RANGE | D5 | PE3 | Polled with 50ms debounce |
> | SELECT | D6 | PH3 | Polled with 50ms debounce |
>
> **Wiring each button:**
> ```
>   Arduino Pin ──── [Button] ──── GND
> ```
> Internal pull-ups are enabled by the firmware (`ui_init()`). No external resistors needed.
> Connect one side of each tactile button to the Arduino pin, the other side to GND.

---

> [!note]- **Step 9: LEDs + Buzzer**
> Status LEDs and continuity buzzer.
>
> | Indicator | Arduino Pin | AVR Port | Color/Type |
> |-----------|-------------|----------|------------|
> | Red LED | D8 | PH5 | Overload warning |
> | Green LED | D9 | PH6 | Normal operation |
> | Yellow LED | D10 | PB4 | HOLD / Logging active |
> | Buzzer | D7 | PH4 | Continuity beep |
>
> **LED wiring** (each LED):
> ```
>   Arduino Pin ──[330 Ohm]──[LED +]──[LED -]── GND
> ```
>
> **Buzzer wiring:**
> ```
>   Arduino Pin D7 ──[Piezo +]──[Piezo -]── GND
> ```
> Use an active (self-oscillating) piezo buzzer. Check polarity markings.

---

> [!note]- **Step 10: LM311 Comparator — Frequency Input**
> The LM311 comparator squares up the input signal for frequency/duty/pulse measurement.
> The output connects to INT4 for hardware interrupt counting.
>
> | LM311 Pin | Connection |
> |-----------|------------|
> | Non-inverting input (+) | Signal input (via coupling cap) |
> | Inverting input (-) | Threshold voltage divider (2.5V) |
> | Output (open collector) | D2 (PE4, INT4) + 10k pull-up to 5V |
> | V+ | +5V rail |
> | V- / GND | GND rail |
>
> The firmware uses INT4 (Arduino D2, AVR PE4) for rising-edge interrupts.
> Timer1 gates the count over a known period for frequency measurement.

---

> [!note]- **Step 11: DS1307 RTC — Real-Time Clock**
> The DS1307 shares the I2C bus with the SSD1306 OLED.
>
> | DS1307 Pin | Connection |
> |------------|------------|
> | SDA | D20 (shared I2C bus) |
> | SCL | D21 (shared I2C bus) |
> | VCC | +5V rail |
> | GND | GND rail |
> | X1, X2 | 32.768 kHz crystal (across pins) |
> | VBAT | CR2032 coin cell (+ terminal) |
>
> The crystal must be a **32.768 kHz** watch crystal with short leads.
> Keep crystal traces/wires as short as possible. No load capacitors needed
> (DS1307 has internal oscillator capacitance).

---

> [!note]- **Step 12: LM35 Temperature Sensor**
> The LM35 outputs 10 mV/C directly to the ADC.
>
> | LM35 Pin | Connection |
> |----------|------------|
> | VCC | +5V rail |
> | VOUT | MCP3208 CH5 |
> | GND | GND rail |
>
> **Pinout** (flat side facing you, left to right): VCC, VOUT, GND.
>
> At room temperature (~25C), output is approximately 250 mV.
> The MCP3208 12-bit ADC with 5V reference gives about 0.2C resolution.

---

## :electric_plug: Input Terminal Wiring

The multimeter has four input terminals for external measurements:

```
  ┌─────────────────────────────────────────────────┐
  │                                                 │
  │   [10A]      [mA]      [V/Ohm]      [COM]      │
  │    red       red        red          black      │
  │                                                 │
  └─────────────────────────────────────────────────┘

  10A    → 0.1 Ohm shunt → CD4053 range 5
  mA     → CD4053 ranges 0-4 (shunt selection)
  V/Ohm  → Voltage divider (CH1/CH2) + Mux (CH0) + Frequency (INT4)
  COM    → Common ground reference
```

> [!warning] Current Protection
> The 10A terminal should have a high-current fuse (10A ceramic fuse).
> The mA terminal should have a lower fuse (500mA or 1A fast-blow).
> On breadboard prototypes, be extremely careful with current measurements.

---

## :zap: First Power-Up Test

1. Connect the Arduino Mega to USB
2. Open a serial terminal at **115200 baud**:
   ```
   pio device monitor
   ```
3. You should see the startup banner:
   ```
   === DTU Digital Multimeter v1.0 ===
   Initializing...
   Ready. Press ? for help.
   ```
4. The **OLED** should display a splash screen for 1.5 seconds, then switch to measurement view
5. The **green LED** (D9) should turn on — indicates normal operation
6. Press `?` in the serial terminal to see the command help menu

> [!warning] No Serial Output?
> - Check baud rate is **115200**
> - Check the correct COM port is selected
> - Try pressing the RESET button on the Mega
> - Make sure the firmware was flashed successfully (`pio run -t upload`)

---

## :straight_ruler: Calibration Walkthrough

All calibration constants are in `include/config.h`. Measure actual component values
with a known-good reference meter and update the `#define` values.

---

> [!note]- **Step 1: V_REF — Reference Voltage**
> Measure the actual voltage on the Arduino Mega **5V pin** with a precision multimeter.
>
> ```c
> #define V_REF  5.000f    /* Measure Mega 5V pin with a meter */
> ```
>
> Typical values are 4.95V to 5.10V depending on USB supply and regulator.
> This is the most important calibration constant — it affects every measurement.

---

> [!note]- **Step 2: Reference Resistors — RREF_0 through RREF_7**
> Measure each reference resistor with a precision meter and update `config.h`:
>
> ```c
> #define RREF_0   50.15f        /* Ch0: 50 Ohm range (measured)    */
> #define RREF_1   497.0f        /* Ch1: 500 Ohm range (measured)   */
> #define RREF_2   4990.0f       /* Ch2: 5k range (measured)        */
> #define RREF_3   48536.0f      /* Ch3: 50k range (measured)       */
> #define RREF_4   498000.0f     /* Ch4: 500k range (measured)      */
> #define RREF_5   4755000.0f    /* Ch5: 5M range (measured)        */
> #define RREF_6   10060000.0f   /* Ch6: 50M range (measured)       */
> #define RREF_7   10030000.0f   /* Ch7: conductance (measured)     */
> ```
>
> Even 1% resistors can be off enough to matter. Measure before soldering/inserting.

---

> [!note]- **Step 3: Voltage Divider — VDIV_RATIO**
> Apply a known DC voltage (e.g. a fresh 9V battery or bench supply) to the V/Ohm input.
> Compare the displayed reading to the actual voltage.
>
> ```c
> #define VDIV_RATIO  11.02f  /* (1.002M + 100k) / 100k = 11.02:1 (measured) */
> ```
>
> Calculate actual ratio: `VDIV_RATIO = V_applied / V_at_CH1`
>
> Adjust until the reading matches within 0.1%.

---

> [!note]- **Step 4: Current Shunts — ISHUNT_0 through ISHUNT_5**
> Measure each current shunt resistor and update:
>
> ```c
> #define ISHUNT_0  10000.0f   /* 10k   — 500 uA range (measured) */
> #define ISHUNT_1  998.0f     /* 1k    — 5 mA range (measured)   */
> #define ISHUNT_2  99.49f     /* 100   — 50 mA range (measured)  */
> #define ISHUNT_3  10.04f     /* 10    — 400 mA range (measured) */
> #define ISHUNT_4  1.05f      /* 1     — 5 A range (measured)    */
> #define ISHUNT_5  0.145f     /* 0.1   — 10 A range (4-wire measured) */
> ```
>
> Low-value shunts (1 Ohm, 0.1 Ohm) are hard to measure accurately.
> Use the 4-wire method or verify by passing a known current.

---

> [!note]- **Step 5: Op-Amp Gain — CUR_GAIN_HI**
> Verify the LM358 current amplifier high-gain setting.
>
> ```c
> #define CUR_GAIN_LO  1.0f    /* Unity (direct) */
> #define CUR_GAIN_HI  10.0f   /* 9.09k / 1k feedback */
> ```
>
> Apply a known small voltage to the amplifier input. Measure the output.
> `CUR_GAIN_HI = V_out / V_in`. Adjust feedback resistors or the constant.

---

> [!note]- **Step 6: NE555 Constant Current — I_SOURCE**
> The NE555 provides a constant current source for capacitance and low-ohm measurements.
>
> ```c
> #define I_SOURCE  0.010f     /* ~10 mA */
> ```
>
> Measure the actual current by enabling the source (serial command or firmware)
> and measuring with an ammeter in series. Update `I_SOURCE` with the measured value.

---

> [!note]- **Step 7: Temperature — LM35 Verification**
> Two-point calibration:
>
> 1. **Ice water test:** Submerge LM35 in ice water (0C).
>    Verify the reading is within +/- 1C.
>
> 2. **Boiling water test:** Hold LM35 above boiling water steam (~100C).
>    This is a rough check — the LM35 is only rated to 150C.
>
> If readings are consistently offset, you can add a software correction
> in the `meas_temperature()` function.

---

## :white_check_mark: Testing Checklist

Work through each test with known reference values. Mark off as you go.

### DC Voltage
- [ ] 0V (probes shorted) — should read < 1 mV
- [ ] 1.5V (AA battery)
- [ ] 5V (Mega 5V pin)
- [ ] 12V (bench supply or battery)

### Resistance
- [ ] 100 Ohm (known resistor)
- [ ] 1 kOhm
- [ ] 10 kOhm
- [ ] 100 kOhm
- [ ] 1 MOhm

### Continuity
- [ ] Short wire — buzzer should beep (< 25 Ohm threshold)
- [ ] Open probes — buzzer should be silent

### Diode
- [ ] 1N4148 — forward voltage ~0.6V
- [ ] LED — forward voltage ~1.8-3.3V depending on color

### Current
- [ ] LED + known resistor: measure current, verify against V/R calculation

### Capacitance
- [ ] 100 nF ceramic
- [ ] 10 uF electrolytic
- [ ] 100 uF electrolytic

### Frequency
- [ ] 555 oscillator — compare against scope/frequency counter

### Temperature
- [ ] Ice water (0C)
- [ ] Room temperature (~20-25C)

### Oscilloscope
- [ ] Square wave from 555 circuit — verify waveform on OLED and serial ASCII dump

---

## :wrench: Troubleshooting

### No OLED Display
- Check I2C address is **0x3C** (some modules use 0x3D — check the PCB jumper)
- Verify SDA (D20) and SCL (D21) wiring
- Check VCC/GND connections and that the module LED is on
- Try the I2C scanner: add a scan routine or check with another I2C device

### ADC Reads 0 on All Channels
- Check MCP3208 SPI wiring: SCK (D52), MOSI (D51), MISO (D50), CS (D53)
- Verify CS pin is correctly connected (PB0/D53)
- Check MCP3208 has power: VDD and VREF both to 5V
- Check AGND and DGND are both connected to GND

### No Serial Output
- Baud rate must be **115200** (not 9600)
- Check the COM port is correct in your terminal
- Try pressing RESET on the Mega
- Re-flash: `pio run -t upload`

### Resistance Reads Wrong
- Check the 74HC4067 mux wiring: S0-S3 (D22-D25), EN (D26)
- Verify the correct reference resistor is on the expected mux channel
- Measure reference resistors and update `RREF_x` values in `config.h`
- Check the mux COM output is connected to MCP3208 CH0

### Buzzer Doesn't Beep in Continuity Mode
- Check D7 (PH4) wiring to the buzzer
- Check buzzer polarity (+ to Arduino pin, - to GND)
- Verify you are in continuity mode (cycle MODE until "CONTIN" appears)
- Check the threshold: default is 25 Ohm (`CONTIN_THRESHOLD` in config.h)

### Frequency Reads 0
- Check the LM311 comparator output is connected to D2 (PE4, INT4)
- Verify the LM311 has power and the threshold divider is at ~2.5V
- Check the pull-up resistor (10k) on the LM311 open-collector output

### Display Shows OL (Overload)
- Input exceeds the current range — try a higher range or check auto-range
- Red LED should be on when overloaded
- Press RANGE to cycle ranges, or send `K` via serial to toggle range lock

### Temperature Reads -40C or 150C (Saturated)
- Check LM35 pinout: flat side facing you, left=VCC, middle=VOUT, right=GND
- **Swapped VCC/GND will damage the LM35** — check before powering on
- Verify VOUT is connected to MCP3208 CH5

---

## :keyboard: Serial Command Reference

All commands are single characters sent via UART at 115200 baud. Case-insensitive.

| Command | Function | Description |
|---------|----------|-------------|
| `R` | REL (Relative) | Toggle relative mode — stores current reading as zero reference |
| `H` | HOLD | Toggle hold — freezes the display on the current reading |
| `A` | Auto-Hold | Toggle auto-hold mode |
| `M` | Min/Max | Toggle min/max/avg recording — resets statistics on enable |
| `L` | Low-Pass Filter | Toggle software low-pass filter (alpha = 0.1) |
| `G` | Data Logging | Toggle CSV data logging to UART + EEPROM (1 sample/sec) |
| `K` | Range Lock | Toggle auto-range lock — holds the current range |
| `+` | Range Up | Step to the next higher range (manual range mode) |
| `-` | Range Down | Step to the next lower range (manual range mode) |
| `Z` | dBm Impedance | Cycle dBm reference impedance: 50 / 75 / 600 Ohm |
| `P` | Print Stats | Print current Min, Max, and Average values |
| `E` | EEPROM Dump | Print all stored EEPROM log entries via UART |
| `?` | Help | Print the command reference list |

---

## :link: References

- [[DTU Multimeter - Digital Multimeter]] — Main project page
- [MCP3208 Datasheet](https://www.microchip.com/en-us/product/MCP3208) — 12-bit SPI ADC
- [ATmega2560 Datasheet](https://www.microchip.com/en-us/product/ATmega2560) — Target MCU
- [SSD1306 Datasheet](https://cdn-shop.adafruit.com/datasheets/SSD1306.pdf) — OLED controller
- [PlatformIO Docs](https://docs.platformio.org/en/latest/) — Build system

---
