---
title: RFID Card Reader - Bare Metal AVR
type: project
tags:
  - electronics
  - avr
  - embedded
  - bare-metal
  - rfid
status: Proof of Concept
started: 2026-02-28
updated: 2026-02-28
aliases:
  - RFID Reader
  - MFRC522 Reader
---

# RFID Card Reader - Bare Metal AVR

> [!summary] **Project Goal**
> Bare-metal RFID card reader using an MFRC522 module and Arduino Uno. Reads 13.56 MHz MIFARE card UIDs and prints them over serial. Pure embedded C with direct ATmega328P register access — no Arduino framework, no HAL, no libraries.
> - SPI communication with MFRC522 via hardware SPI registers
> - UART serial output at 9600 baud
> - ISO 14443A anti-collision for UID retrieval

---

## System Overview

| Parameter | Specification |
|-----------|--------------|
| **MCU** | ATmega328P (Arduino Uno) |
| **Clock** | 16 MHz external crystal |
| **RFID Module** | MFRC522 RC522 (13.56 MHz, ISO 14443A) |
| **Interface** | SPI (hardware, ~1 MHz clock) |
| **Serial Output** | UART 9600 baud, 8N1 |
| **Framework** | None — bare-metal C (no Arduino core) |
| **Build System** | PlatformIO (`atmelavr` platform) |
| **Compiler Flags** | `-std=c11 -Os` |

---

## Wiring

| RC522 Pin | Arduino Pin | ATmega328P Port | Notes |
|-----------|-------------|-----------------|-------|
| SDA (SS)  | D10         | PB2             | SPI chip select (active low) |
| SCK       | D13         | PB5             | SPI clock |
| MOSI      | D11         | PB3             | SPI master out |
| MISO      | D12         | PB4             | SPI master in |
| RST       | D9          | PB1             | Hardware reset (active low) |
| GND       | GND         | ---               | Ground |
| 3.3V      | 3.3V        | ---               | Supply (3.3V only, do NOT use 5V) |

> [!warning] **3.3V Supply**
> The MFRC522 module runs at 3.3V. The Arduino Uno's 3.3V output pin can supply enough current for the module. Do not connect VCC to 5V.

---

## Software Architecture

The firmware is split into 4 modules, each handling a specific peripheral via direct register access:

### Module Overview

| Module | Files | Purpose |
|--------|-------|---------|
| **SPI** | `spi.c`, `spi.h` | Hardware SPI master init and byte transfer via `SPCR`/`SPDR` registers |
| **UART** | `uart.c`, `uart.h` | Serial TX at 9600 baud via `UBRR0`/`UDR0` registers, hex formatting |
| **MFRC522** | `mfrc522.c`, `mfrc522.h` | Full MFRC522 driver — register read/write, init sequence, REQA, anti-collision |
| **Main** | `main.c` | Init peripherals, poll for cards in a loop, print UIDs |

### SPI (`spi.c`)

Configures the ATmega328P hardware SPI peripheral as master:
- Sets `DDRB` for SS, MOSI, SCK as outputs; MISO as input
- Enables SPI master mode via `SPCR` with prescaler `/16` (~1 MHz clock)
- Provides `spi_transfer()` which writes `SPDR` and polls `SPIF` for completion
- `spi_select()` / `spi_deselect()` toggle the SS line (PB2)

### UART (`uart.c`)

Configures the USART0 peripheral for transmit-only serial output:
- Calculates `UBRR` from `F_CPU` and desired baud rate
- 8-bit data, 1 stop bit, no parity (`UCSR0C`)
- Provides `uart_putc()`, `uart_puts()`, and `uart_put_hex()` for formatted output
- Polls `UDRE0` flag before each byte transmission

### MFRC522 (`mfrc522.c`)

Complete driver for the NXP MFRC522 contactless reader IC:
- **Register access** via SPI using the MFRC522 address byte format (see Technical Notes)
- **Hardware + software reset** via RST pin toggle and `PCD_SoftReset` command
- **Init sequence**: configures timer (25 ms timeout), 100% ASK modulation, CRC preset `0x6363`, antenna on
- **`mfrc522_request()`**: sends REQA command (7-bit short frame) to detect cards, expects 16-bit ATQA response
- **`mfrc522_anticoll()`**: runs ISO 14443A anti-collision (cascade level 1), retrieves 4-byte UID + BCC, verifies checksum
- **`mfrc522_to_card()`**: core transceive function — loads FIFO, executes command, waits for IRQ, reads response

### Main Loop

1. Initialize SPI, UART, and MFRC522
2. Print startup banner and chip version as sanity check
3. Poll for cards every 200 ms using `mfrc522_request(PICC_REQIDL)`
4. On detection, run anti-collision to get the 4-byte UID
5. Print UID in hex format (`A3:B2:4F:01`)

---

## Building & Flashing

Uses PlatformIO with the `atmelavr` platform. No framework is specified — the code compiles as bare-metal C against avr-libc.

### Build

```bash
python -m platformio run
```

### Flash

Connect the Arduino Uno via USB and flash:

```bash
python -m platformio run -t upload
```

### Serial Monitor

Open the serial monitor at 9600 baud to see card UIDs:

```bash
python -m platformio device monitor
```

### Serial Output Format

```
RFID Card Reader - Bare Metal AVR
MFRC522 version: 0x92
Waiting for card...
UID: A3:B2:4F:01
UID: 7C:D1:88:22
```

The version byte confirms SPI communication is working: `0x91` = MFRC522 v1.0, `0x92` = v2.0. If you see `0x00` or `0xFF`, check wiring.

---

## Technical Notes

### SPI Address Byte Format

The MFRC522 uses a specific SPI framing for register access. Each transaction starts with an address byte:

```
Write: 0 | AAAAAA | 0    =>  (reg << 1) & 0x7E
Read:  1 | AAAAAA | 0    =>  ((reg << 1) & 0x7E) | 0x80
```

- Bit 7: direction (1 = read, 0 = write)
- Bits 6-1: register address (6 bits)
- Bit 0: always 0

For reads, a dummy byte (`0x00`) is sent after the address byte to clock in the response.

### MFRC522 Init Sequence

The initialization configures the chip for ISO 14443A operation:

1. **Hardware reset** — toggle RST pin low for 10 ms, then high, wait 50 ms
2. **Software reset** — write `PCD_SoftReset` (0x0F) to `CommandReg`, wait 50 ms
3. **Timer config** — auto-start mode, prescaler 169 (40 kHz tick), reload 1000 => 25 ms timeout
4. **Modulation** — 100% ASK modulation (`TxASKReg = 0x40`)
5. **CRC preset** — `ModeReg = 0x3D` sets CRC coprocessor initial value to `0x6363` (ISO 14443A standard)
6. **Antenna on** — enable TX1 and TX2 driver pins in `TxControlReg`

### ISO 14443A Anti-Collision Protocol

The card detection follows the ISO 14443A standard:

1. **REQA** (Request command A, `0x26`) — sent as a 7-bit short frame (`BitFramingReg = 0x07`). All idle PICCs in the field respond with a 16-bit ATQA (Answer To Request A)
2. **Anti-collision CL1** (`0x93`, `0x20`) — cascade level 1 anti-collision. The `0x20` NVB byte means "I'm sending 2 bytes (just the command), tell me your UID." If only one card is present, it responds with 4 UID bytes + 1 BCC (Block Check Character = XOR of the 4 UID bytes)
3. **BCC verification** — the firmware XORs the 4 UID bytes and compares against the received BCC to verify data integrity

> [!info] **Single-Card Limitation**
> This implementation handles the simple case of one card in the field. Full anti-collision with multiple simultaneous cards (bit-level collision resolution) is not implemented.

---

## PlatformIO Configuration

```ini
[env:uno]
platform = atmelavr
board = uno
; No framework - bare metal
upload_protocol = arduino
monitor_speed = 9600
build_flags = -std=c11 -Os
```

Key point: no `framework` line means PlatformIO compiles against avr-libc directly, with no Arduino core overhead.

---

## References

- [MFRC522 Datasheet (NXP)](https://www.nxp.com/docs/en/data-sheet/MFRC522.pdf)
- [ISO 14443A Standard Overview](https://www.nxp.com/docs/en/application-note/AN10834.pdf)
- [ATmega328P Datasheet (Microchip)](https://ww1.microchip.com/downloads/en/DeviceDoc/Atmel-7810-Automotive-Microcontrollers-ATmega328P_Datasheet.pdf)
- [PlatformIO Atmel AVR Platform](https://docs.platformio.org/en/latest/platforms/atmelavr.html)

---
