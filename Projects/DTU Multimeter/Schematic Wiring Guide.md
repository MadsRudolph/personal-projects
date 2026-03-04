---
title: Schematic Wiring Guide
type: reference
tags:
  - kicad
  - electronics
  - dtu
parent: "[[DTU Multimeter - Digital Multimeter]]"
created: 2026-03-04
---

# Schematic Wiring Guide

> [!info] Purpose
> Pin-by-pin wiring reference for the KiCad schematic, organized per component. All reference designators match the `.kicad_sch` annotations. Click on any component in KiCad and use this to see every connection it needs.

---

## Contents

**ICs**
- [[#A1 -- Arduino Mega 2560|A1 -- Arduino Mega 2560]]
- [[#U1 -- MCP3208 (12-bit SPI ADC)|U1 -- MCP3208]]
- [[#U2 -- CD74HC4067E (16-ch Analog Mux)|U2 -- CD74HC4067E]]
- [[#U3 -- CD4053BE (Triple 2:1 Analog Switch)|U3 -- CD4053BE]]
- [[#U4 -- LM358P (Dual Op-Amp)|U4 -- LM358P]]
- [[#U5 -- LM311N (Comparator)|U5 -- LM311N]]
- [[#U6 -- NE555P (Timer)|U6 -- NE555P]]
- [[#U7 -- LM35DZ (Temperature Sensor)|U7 -- LM35DZ]]
- [[#U8 -- DS1307+ (Real-Time Clock)|U8 -- DS1307+]]
- [[#DS1 -- OLED 128x64 (I2C Display)|DS1 -- OLED]]

**Resistors**
- [[#R1-R8 -- Reference Resistors (Resistance Ranges)|R1-R8 -- Reference Resistors]]
- [[#R9-R14 -- Current Shunt Resistors|R9-R14 -- Current Shunts]]
- [[#R15, R16 -- Voltage Divider|R15-R16 -- Voltage Divider]]
- [[#R17, R18, R19 -- NE555 Timing Resistors|R17-R19 -- NE555 Timing]]
- [[#R20, R21 -- Op-Amp Feedback (U4 Unit A)|R20-R21 -- Op-Amp Feedback]]
- [[#R22, R23 -- LM311 Threshold Divider|R22-R23 -- Threshold Divider]]
- [[#R24 -- LM311 Output Pull-Up|R24 -- LM311 Pull-Up]]
- [[#R25, R26, R27 -- LED Current Limiters|R25-R27 -- LED Limiters]]
- [[#R28, R29 -- I2C Pull-Ups|R28-R29 -- I2C Pull-Ups]]

**Passives and Other**
- [[#C1-C8 -- Capacitors|C1-C8 -- Capacitors]]
- [[#D1, D2, D3 -- Status LEDs|D1-D3 -- LEDs]]
- [[#SW1-SW4 -- Push Buttons|SW1-SW4 -- Buttons]]
- [[#BZ1 -- Piezo Buzzer|BZ1 -- Buzzer]]
- [[#F1, F2 -- Fuses|F1-F2 -- Fuses]]
- [[#Y1 -- 32.768kHz Crystal|Y1 -- Crystal]]
- [[#BT1 -- CR2032 Battery|BT1 -- Battery]]
- [[#No-Connect Flags]]

---

## A1 -- Arduino Mega 2560

> [!abstract] Main controller. Every signal on the board routes back here.

| A1 Pin | Net Label | Connects To | Function |
|--------|-----------|-------------|----------|
| 5V_1 | `VCC` | Power rail | 5V supply out |
| GND1 | `GND` | Ground rail | Common ground |
| 2 | `FREQ_IN` | U5 pin 7 (via R24 pull-up) | Frequency input (INT4) |
| 3 | `BTN_MODE` | SW1 pin 1 | MODE button (INT5, interrupt) |
| 4 | `BTN_FUNC` | SW2 pin 1 | FUNC button (polled) |
| 5 | `BTN_RANGE` | SW3 pin 1 | RANGE button (polled) |
| 6 | `BTN_SELECT` | SW4 pin 1 | SELECT button (polled) |
| 7 | `BUZZER` | BZ1 pin (+) | Continuity buzzer |
| 8 | `LED_RED` | R25 pin 1 | Red LED (overload) |
| 9 | `LED_GRN` | R26 pin 1 | Green LED (normal) |
| 10 | `LED_YEL` | R27 pin 1 | Yellow LED (HOLD/log) |
| SDA | `I2C_SDA` | U8 pin 5, DS1 SDA, R28 | I2C data (dedicated pin) |
| SCL | `I2C_SCL` | U8 pin 6, DS1 SCL, R29 | I2C clock (dedicated pin) |
| 22 | `MUX_S0` | U2 pin 10 | Mux select bit 0 |
| 23 | `MUX_S1` | U2 pin 11 | Mux select bit 1 |
| 24 | `MUX_S2` | U2 pin 14 | Mux select bit 2 |
| 25 | `MUX_S3` | U2 pin 13 | Mux select bit 3 |
| 26 | `MUX_EN` | U2 pin 15 | Mux enable (active LOW) |
| 27 | `CUR_A` | U3 pin 11 | Current mux select A |
| 28 | `CUR_B` | U3 pin 10 | Current mux select B |
| 29 | `CUR_C` | U3 pin 9 | Current mux select C |
| 30 | `CUR_INH` | U3 pin 6 | Current mux inhibit |
| 31 | `CAP_CHG` | Capacitance timing circuit | RC charge control |
| 32 | `CAP_DIS` | Capacitance timing circuit | RC discharge control |
| 33 | `ISRC_EN` | U6 pin 4 | NE555 enable (reset) |
| 50 | `SPI_MISO` | U1 pin 12 | SPI data from ADC |
| 51 | `SPI_MOSI` | U1 pin 11 | SPI data to ADC |
| 52 | `SPI_SCK` | U1 pin 13 | SPI clock |
| 53 | `SPI_CS` | U1 pin 10 | SPI chip select |

---

## U1 -- MCP3208 (12-bit SPI ADC)

> [!abstract] 8-channel ADC. All analog measurements feed in here.

| U1 Pin | Name | Net / Connects To |
|--------|------|-------------------|
| 1 | CH0 | `MUX_COM` -- U2 pin 1 (resistance mux output) |
| 2 | CH1 | `ADC_CH1` -- R15/R16 divider midpoint (voltage high range) |
| 3 | CH2 | `ADC_CH2` -- Probe input direct (voltage low / mV range) |
| 4 | CH3 | `ADC_CH3` -- U4 pin 1, OpA output (current amplifier) |
| 5 | CH4 | `ADC_CH4` -- U4 pin 7, OpB output (AC rectifier) |
| 6 | CH5 | `ADC_CH5` -- U7 pin 2 (LM35 temperature) |
| 7 | CH6 | No connect (flag `X`) |
| 8 | CH7 | No connect (flag `X`) |
| 9 | DGND | `GND` |
| 10 | CS | `SPI_CS` -- A1 53 |
| 11 | DIN | `SPI_MOSI` -- A1 51 |
| 12 | DOUT | `SPI_MISO` -- A1 50 |
| 13 | CLK | `SPI_SCK` -- A1 52 |
| 14 | AGND | `GND` |
| 15 | VREF | `VCC` |
| 16 | VDD | `VCC` |

**Decoupling:** C1 (100n) + C4 (10u) across pins 16/15 and 9/14.

---

## U2 -- CD74HC4067E (16-ch Analog Mux)

> [!abstract] Resistance range selector. Routes one of 8 reference resistors to U1 CH0.

| U2 Pin | Name | Net / Connects To |
|--------|------|-------------------|
| 1 | COM | `MUX_COM` -- U1 pin 1 (CH0) |
| 2 | I7 | R8 pin 1 (10.03M -- conductance) |
| 3 | I6 | R7 pin 1 (10.06M -- 50M range) |
| 4 | I5 | R6 pin 1 (4.755M -- 5M range) |
| 5 | I4 | R5 pin 1 (498k -- 500k range) |
| 6 | I3 | R4 pin 1 (48.536k -- 50k range) |
| 7 | I2 | R3 pin 1 (4990 -- 5k range) |
| 8 | I1 | R2 pin 1 (497 -- 500 Ohm range) |
| 9 | I0 | R1 pin 1 (50.15 -- 50 Ohm range) |
| 10 | S0 | `MUX_S0` -- A1 22 |
| 11 | S1 | `MUX_S1` -- A1 23 |
| 12 | GND | `GND` |
| 13 | S3 | `MUX_S3` -- A1 25 |
| 14 | S2 | `MUX_S2` -- A1 24 |
| 15 | ~{E} | `MUX_EN` -- A1 26 (active LOW) |
| 16 | I15 | No connect (flag `X`) |
| 17 | I14 | No connect (flag `X`) |
| 18 | I13 | No connect (flag `X`) |
| 19 | I12 | No connect (flag `X`) |
| 20 | I11 | No connect (flag `X`) |
| 21 | I10 | No connect (flag `X`) |
| 22 | I9 | No connect (flag `X`) |
| 23 | I8 | No connect (flag `X`) |
| 24 | VCC | `VCC` |

**Ref resistors R1-R8:** other end of each resistor connects to probe input net.

**Decoupling:** C2 (100n) + C5 (10u) across pins 24 and 12.

---

## U3 -- CD4053BE (Triple 2:1 Analog Switch)

> [!abstract] Current range selector. Routes one of 6 shunt resistors to the amplifier.

| U3 Pin | Name | Net / Connects To |
|--------|------|-------------------|
| 1 | IN/OUT_BY | R14 pin 1 (0.145 -- 10A shunt) |
| 2 | IN/OUT_BX | R13 pin 1 (1.05 -- 5A shunt) |
| 3 | IN/OUT_CY | R12 pin 1 (10.04 -- 400 mA shunt) |
| 4 | OUT/IN_CX_OR_CY | `SHUNT_NODE` (C common, tied to pins 14 and 15) |
| 5 | IN/OUT_CX | R11 pin 1 (99.49 -- 50 mA shunt) |
| 6 | INH | `CUR_INH` -- A1 30 |
| 7 | VEE | `GND` |
| 8 | VSS | `GND` |
| 9 | C | `CUR_C` -- A1 29 |
| 10 | B | `CUR_B` -- A1 28 |
| 11 | A | `CUR_A` -- A1 27 |
| 12 | AX_IN/OUT | R9 pin 1 (10k -- 500 uA shunt) |
| 13 | AY_IN/OUT | R10 pin 1 (998 -- 5 mA shunt) |
| 14 | OUT/IN_AX_OR_AY | `SHUNT_NODE` (A common, tied to pins 4 and 15) |
| 15 | OUT/IN_BX_OR_BY | `SHUNT_NODE` (B common, tied to pins 4 and 14) |
| 16 | VDD | `VCC` |

**SHUNT_NODE** goes to U4 pin 3 (op-amp non-inverting input).

**Shunt other ends:**
- R9-R13 pin 2: all to mA terminal (via F2)
- R14 pin 2: to 10A terminal (via F1)

---

## U4 -- LM358P (Dual Op-Amp)

> [!abstract] Unit A = current amplifier (gain ~10x). Unit B = AC precision rectifier.

### Unit A -- Current Amplifier

| U4 Pin | Name | Net / Connects To |
|--------|------|-------------------|
| 1 | OUT_A | `ADC_CH3` -- U1 pin 4 (CH3), R20 pin 2 (feedback) |
| 2 | IN-_A | R20 pin 1 + R21 pin 1 (inverting, feedback junction) |
| 3 | IN+_A | `SHUNT_NODE` -- U3 common outputs (non-inverting) |

**Feedback network:**

```
                R20 (9.09k)
U4 pin 2 ---+---/\/\/---+--- U4 pin 1 (output) --> U1 CH3
            |
            +---/\/\/--- GND
                R21 (1k)

Gain = 1 + (9.09k / 1k) = ~10x
```

### Unit B -- AC Rectifier

| U4 Pin | Name | Net / Connects To |
|--------|------|-------------------|
| 5 | IN+_B | AC signal input (probe) |
| 6 | IN-_B | Rectifier feedback |
| 7 | OUT_B | `ADC_CH4` -- U1 pin 5 (CH4) |

### Power (Unit C)

| U4 Pin | Name | Net / Connects To |
|--------|------|-------------------|
| 4 | V- | `GND` |
| 8 | V+ | `VCC` |

**Decoupling:** C3 (100n) + C6 (10u) across pins 8 and 4.

---

## U5 -- LM311N (Comparator)

> [!abstract] Squares up AC signal for frequency/duty/pulse measurement. Output to A1 INT4.

| U5 Pin | Name | Net / Connects To |
|--------|------|-------------------|
| 1 | GND | `GND` |
| 2 | IN+ | Signal input (via C7 AC coupling cap) |
| 3 | IN- | R22/R23 midpoint (2.5V threshold) |
| 4 | V- | `GND` |
| 5 | BAL | No connect |
| 6 | BAL/STROBE | No connect |
| 7 | OUT | R24 pin 2 + `FREQ_IN` -- A1 2 (open collector) |
| 8 | V+ | `VCC` |

**Threshold divider:**

```
VCC ---[R22 10k]---+---[R23 10k]--- GND
                   |
                   +--- U5 pin 3 (IN-)
```

**Output pull-up:**

```
VCC ---[R24 10k]---+--- U5 pin 7 (OUT)
                   |
                   +--- A1 2 (FREQ_IN / INT4)
```

**AC coupling:** C7 (100n) in series with signal input to U5 pin 2.

---

## U6 -- NE555P (Timer)

> [!abstract] Constant current source for capacitance and low-ohm measurements.

| U6 Pin | Name  | Net / Connects To                        |
| ------ | ----- | ---------------------------------------- |
| 1      | GND   | `GND`                                    |
| 2      | TRIG  | Tied to pin 6 (THR)                      |
| 3      | OUT   | Current source output (to probe circuit) |
| 4      | RESET | `ISRC_EN` -- A1 33                       |
| 5      | CV    | C8 pin 1 (bypass to GND)                 |
| 6      | THR   | Tied to pin 2 (TRIG)                     |
| 7      | DIS   | Timing resistors R17/R18/R19             |
| 8      | VCC   | `VCC`                                    |

**Timing resistors** (selectable by firmware):

| Ref | Value | Capacitance Range |
|-----|-------|-------------------|
| R17 | 1.003M | Large caps (slow charge) |
| R18 | 10k | Medium caps |
| R19 | 99.48 | Small caps (fast charge) |

**Bypass:** C8 (100n) from pin 5 (CV) to GND.

---

## U7 -- LM35DZ (Temperature Sensor)

> [!abstract] Outputs 10 mV per degree C directly to ADC.

| U7 Pin | Name | Net / Connects To |
|--------|------|-------------------|
| 1 | VCC | `VCC` |
| 2 | VOUT | `ADC_CH5` -- U1 pin 6 (CH5) |
| 3 | GND | `GND` |

> [!warning] Pinout (flat side facing you, L to R): VCC, VOUT, GND. Swapping VCC/GND destroys the chip.

---

## U8 -- DS1307+ (Real-Time Clock)

> [!abstract] I2C RTC for timestamped data logging. Shares I2C bus with OLED.

| U8 Pin | Name | Net / Connects To |
|--------|------|-------------------|
| 1 | X1 | Y1 pin 1 (32.768kHz crystal) |
| 2 | X2 | Y1 pin 2 (32.768kHz crystal) |
| 3 | VBAT | BT1 pin (+) (CR2032 backup) |
| 4 | GND | `GND` |
| 5 | SDA | `I2C_SDA` -- A1 SDA, DS1 SDA, R28 |
| 6 | SCL | `I2C_SCL` -- A1 SCL, DS1 SCL, R29 |
| 7 | SQW | No connect (flag `X`) |
| 8 | VCC | `VCC` |

---

## DS1 -- OLED 128x64 (I2C Display)

> [!abstract] SSD1306 display module, I2C address 0x3C.

| DS1 Pin | Name | Net / Connects To |
|---------|------|-------------------|
| GND | GND | `GND` |
| VCC | VCC | `VCC` |
| SDA | SDA | `I2C_SDA` -- A1 SDA, U8 pin 5, R28 |
| SCL | SCL | `I2C_SCL` -- A1 SCL, U8 pin 6, R29 |

---

## R1-R8 -- Reference Resistors (Resistance Ranges)

> [!abstract] Each connects between a U2 mux channel and the probe input. U2 selects one at a time.

| Ref | Value | Pin 1 to | Pin 2 to | Measurement Range |
|-----|-------|----------|----------|-------------------|
| R1 | 50.15 | U2 pin 9 (I0) | Probe input | 50 Ohm |
| R2 | 497 | U2 pin 8 (I1) | Probe input | 500 Ohm |
| R3 | 4990 | U2 pin 7 (I2) | Probe input | 5k |
| R4 | 48.536k | U2 pin 6 (I3) | Probe input | 50k |
| R5 | 498k | U2 pin 5 (I4) | Probe input | 500k |
| R6 | 4.755M | U2 pin 4 (I5) | Probe input | 5M |
| R7 | 10.06M | U2 pin 3 (I6) | Probe input | 50M |
| R8 | 10.03M | U2 pin 2 (I7) | Probe input | Conductance |

---

## R9-R14 -- Current Shunt Resistors

> [!abstract] Each connects between a U3 switch channel and the current input terminal.

| Ref | Value | Pin 1 to | Pin 2 to | Current Range |
|-----|-------|----------|----------|---------------|
| R9 | 10k | U3 pin 12 (AX_IN/OUT) | mA terminal (via F2) | 500 uA |
| R10 | 998 | U3 pin 13 (AY_IN/OUT) | mA terminal (via F2) | 5 mA |
| R11 | 99.49 | U3 pin 5 (IN/OUT_CX) | mA terminal (via F2) | 50 mA |
| R12 | 10.04 | U3 pin 3 (IN/OUT_CY) | mA terminal (via F2) | 400 mA |
| R13 | 1.05 | U3 pin 2 (IN/OUT_BX) | mA terminal (via F2) | 5 A |
| R14 | 0.145 | U3 pin 1 (IN/OUT_BY) | 10A terminal (via F1) | 10 A |

---

## R15, R16 -- Voltage Divider

> [!abstract] 11:1 divider for high-voltage range.

```
Probe input ---[R15 1.002M]---+---[R16 100k]--- GND
                               |
                               +--- U1 pin 2 (CH1)
```

| Ref | Value | Pin 1 to | Pin 2 to |
|-----|-------|----------|----------|
| R15 | 1.002M | Probe input | Divider midpoint (R16 pin 1 + U1 CH1) |
| R16 | 100k | Divider midpoint | `GND` |

Divider ratio: (1.002M + 100k) / 100k = **11.02:1**

Probe input also connects directly to U1 pin 3 (CH2) for the mV range.

---

## R17, R18, R19 -- NE555 Timing Resistors

> [!abstract] Selectable charge resistors for capacitance measurement.

| Ref | Value | Pin 1 to | Pin 2 to |
|-----|-------|----------|----------|
| R17 | 1.003M | U6 timing circuit | Charge node |
| R18 | 10k | U6 timing circuit | Charge node |
| R19 | 99.48 | U6 timing circuit | Charge node |

---

## R20, R21 -- Op-Amp Feedback (U4 Unit A)

> [!abstract] Sets current amplifier gain to ~10x.

| Ref | Value | Pin 1 to | Pin 2 to |
|-----|-------|----------|----------|
| R20 | 9.09k | U4 pin 2 (IN-) | U4 pin 1 (OUT) / `ADC_CH3` |
| R21 | 1k | U4 pin 2 (IN-) | `GND` |

Gain = 1 + (R20 / R21) = 1 + 9.09 = **~10x**

---

## R22, R23 -- LM311 Threshold Divider

> [!abstract] Sets the 2.5V comparator threshold.

| Ref | Value | Pin 1 to | Pin 2 to |
|-----|-------|----------|----------|
| R22 | 10k | `VCC` | U5 pin 3 (IN-) + R23 pin 1 |
| R23 | 10k | R22 pin 2 / U5 pin 3 | `GND` |

Threshold = 5V x (10k / (10k + 10k)) = **2.5V**

---

## R24 -- LM311 Output Pull-Up

> [!abstract] Pull-up for LM311 open-collector output.

| Ref | Value | Pin 1 to | Pin 2 to |
|-----|-------|----------|----------|
| R24 | 10k | `VCC` | U5 pin 7 (OUT) + A1 2 (`FREQ_IN`) |

---

## R25, R26, R27 -- LED Current Limiters

> [!abstract] 330 Ohm series resistors for status LEDs.

| Ref | Value | Pin 1 to | Pin 2 to | LED |
|-----|-------|----------|----------|-----|
| R25 | 330 | A1 8 (`LED_RED`) | D1 anode (Red) | Overload |
| R26 | 330 | A1 9 (`LED_GRN`) | D2 anode (Green) | Normal |
| R27 | 330 | A1 10 (`LED_YEL`) | D3 anode (Yellow) | HOLD/Log |

LED cathodes all connect to `GND`.

---

## R28, R29 -- I2C Pull-Ups

> [!abstract] Required pull-ups for the shared I2C bus.

| Ref | Value | Pin 1 to | Pin 2 to |
|-----|-------|----------|----------|
| R28 | 10k | `VCC` | `I2C_SDA` (A1 SDA, U8 pin 5, DS1 SDA) |
| R29 | 10k | `VCC` | `I2C_SCL` (A1 SCL, U8 pin 6, DS1 SCL) |

---

## C1-C8 -- Capacitors

| Ref | Value | Pin 1 to | Pin 2 to | Purpose |
|-----|-------|----------|----------|---------|
| C1 | 100n | U1 VDD (pin 16) | U1 GND (pin 9) | Decoupling, near U1 |
| C2 | 100n | U2 VCC (pin 24) | U2 GND (pin 12) | Decoupling, near U2 |
| C3 | 100n | U4 V+ (pin 8) | U4 V- (pin 4) | Decoupling, near U4 |
| C4 | 10u | `VCC` | `GND` | Bulk, near U1 |
| C5 | 10u | `VCC` | `GND` | Bulk, near U2 |
| C6 | 10u | `VCC` | `GND` | Bulk, near U4 |
| C7 | 100n | Signal input | U5 pin 2 (IN+) | AC coupling, comparator input |
| C8 | 100n | U6 pin 5 (CV) | `GND` | NE555 control voltage bypass |

---

## D1, D2, D3 -- Status LEDs

| Ref | Color | Anode to | Cathode to | Function |
|-----|-------|----------|------------|----------|
| D1 | Red | R25 pin 2 | `GND` | Overload warning |
| D2 | Green | R26 pin 2 | `GND` | Normal operation |
| D3 | Yellow | R27 pin 2 | `GND` | HOLD / Logging |

---

## SW1-SW4 -- Push Buttons

> [!abstract] Active LOW, internal pull-ups enabled by firmware. No external pull-up resistors needed.

| Ref | Label | Pin 1 to | Pin 2 to | Input Type |
|-----|-------|----------|----------|------------|
| SW1 | MODE | A1 3 (`BTN_MODE`) | `GND` | INT5, interrupt |
| SW2 | FUNC | A1 4 (`BTN_FUNC`) | `GND` | Polled |
| SW3 | RANGE | A1 5 (`BTN_RANGE`) | `GND` | Polled |
| SW4 | SELECT | A1 6 (`BTN_SELECT`) | `GND` | Polled |

---

## BZ1 -- Piezo Buzzer

| Pin | Connects To |
|-----|-------------|
| (+) | A1 7 (`BUZZER`) |
| (-) | `GND` |

---

## F1, F2 -- Fuses

| Ref | Rating | Pin 1 to | Pin 2 to |
|-----|--------|----------|----------|
| F1 | 10A | 10A input terminal | R14 pin 2 (0.145 Ohm shunt) |
| F2 | 500mA | mA input terminal | R9-R13 pin 2 (shunt common) |

---

## Y1 -- 32.768kHz Crystal

| Pin | Connects To |
|-----|-------------|
| 1 | U8 pin 1 (X1) |
| 2 | U8 pin 2 (X2) |

Keep leads short. No external load caps needed (DS1307 has internal).

---

## BT1 -- CR2032 Battery

| Pin | Connects To |
|-----|-------------|
| (+) | U8 pin 3 (VBAT) |
| (-) | `GND` |

---

## No-Connect Flags

Place KiCad no-connect (`X`) flags on these unused pins to avoid ERC errors:

| Component | Pins |
|-----------|------|
| U1 MCP3208 | pin 7 (CH6), pin 8 (CH7) |
| U2 74HC4067 | pin 16 (I15), 17 (I14), 18 (I13), 19 (I12), 20 (I11), 21 (I10), 22 (I9), 23 (I8) |
| U8 DS1307 | pin 7 (SQW) |

---

## See also

- [[DTU Multimeter - Digital Multimeter]]
- [[Build Guide - DTU Multimeter]]
- [[kicad-skip Schematic Scripting]]
