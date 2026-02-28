# Python GUI Control Panel Design

## Problem

The RFID tag analyzer currently outputs diagnostic data over UART to a serial terminal. We want a proper desktop GUI that provides a visual interface for connecting to the Arduino, controlling scans, displaying tag info, and logging scan history.

## Solution

A CustomTkinter desktop app that communicates with the Arduino over serial using a simple delimited protocol.

## Serial Protocol

### Firmware to PC (responses)

- `TAG:<atqa_hex>:<uid_hex>:<sak_hex>:<uid_len>\n` — tag scan result
  - Example: `TAG:0344:04A3B24F01C780:20:7`
- `OK:<message>\n` — command acknowledgement
  - Example: `OK:Scanning`
- `ERR:<message>\n` — error report
  - Example: `ERR:SELECT CL1 failed`
- `INFO:<message>\n` — status info
  - Example: `INFO:Ready`

### PC to Firmware (commands)

- `S` — start continuous scanning
- `P` — pause scanning
- `O` — single one-shot scan
- `V` — get firmware version/status

The firmware adds UART receive capability (currently TX-only). In idle state it waits for a command byte. When scanning, it sends TAG: lines for each detection.

## GUI Layout

### Top bar — Connection controls

- COM port dropdown (auto-detects via serial.tools.list_ports)
- Connect/Disconnect button
- Connection status indicator (green/red label)

### Center — Tag display card

- Large card showing last scanned tag:
  - UID in large monospace font
  - ATQA and SAK values
  - Chip type label (e.g. "MIFARE DESFire")
  - Cloneability badge (green YES / red NO / yellow PARTIAL)
- Below card: scan control buttons (Start Scan / Stop / Single Scan)

### Bottom — Scan log table

- Scrollable table: timestamp, UID, chip type, SAK
- Session-only (not persisted to disk)

### Window

- Size: ~800x600
- Dark theme (CustomTkinter dark mode)
- Title: "RFID Tag Analyzer"

## Architecture

### File structure

```
gui/
  app.py            — main entry point, CustomTkinter app window
  serial_handler.py — serial connection, send/receive, protocol parsing
  tag_info.py       — SAK to chip type lookup, Tag dataclass
  requirements.txt  — customtkinter, pyserial
```

### Threading model

- Serial reader runs in a background daemon thread
- Parsed data goes onto a queue.Queue
- GUI polls queue every 100ms via Tkinter after()
- No direct thread-to-GUI calls

### Data flow

1. User clicks "Start Scan" -> serial_handler sends `S` byte
2. Arduino scans, sends `TAG:0344:04A3B24F01C780:20:7\n`
3. Serial thread parses line, creates Tag dataclass, puts on queue
4. GUI after() callback polls queue, updates card display + log table

## Firmware Changes Required

### uart.c/h

- Enable RX in uart_init() (set RXEN0 bit in UCSR0B)
- Add uart_getc() — blocking read
- Add uart_available() — check if data in receive buffer (UCSR0A & RXC0)

### main.c

- Add command handler in main loop: check uart_available(), read command byte
- Add scan modes: idle (wait for command), continuous, one-shot
- Change output format from human-readable to protocol format (TAG:...)
- Keep human-readable output as fallback for direct terminal use

## Dependencies

- Python 3.8+
- customtkinter
- pyserial
