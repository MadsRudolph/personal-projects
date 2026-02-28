# Python GUI Control Panel Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a CustomTkinter desktop GUI that connects to the Arduino RFID analyzer over serial, controls scanning, and displays tag diagnostic info with scan history.

**Architecture:** Two-part implementation: (1) firmware adds UART receive + command handler with protocol output format, (2) Python GUI with threaded serial reader, tag data model, and CustomTkinter interface. The GUI parser only reads protocol lines (TAG:/OK:/ERR:/INFO:) and ignores human-readable text, so both formats coexist on the wire.

**Tech Stack:** Bare-metal C (ATmega328P, PlatformIO), Python 3.8+, CustomTkinter, pyserial, pytest

---

### Task 1: Add UART receive capability

**Files:**
- Modify: `Projects/RFID Card Reader/src/uart.h`
- Modify: `Projects/RFID Card Reader/src/uart.c`

**Step 1: Add prototypes to uart.h**

Add two new prototypes before `#endif`:

```c
uint8_t uart_available(void);
char    uart_getc(void);
```

**Step 2: Enable RX in uart_init and add receive functions to uart.c**

In `uart_init`, change the UCSR0B line to enable both TX and RX:

```c
UCSR0B = (1 << TXEN0) | (1 << RXEN0);  // enable transmitter and receiver
```

Add at the end of uart.c:

```c
uint8_t uart_available(void) {
    return (UCSR0A & (1 << RXC0)) ? 1 : 0;
}

char uart_getc(void) {
    while (!(UCSR0A & (1 << RXC0)))
        ;
    return UDR0;
}
```

**Step 3: Build firmware**

Run: `cd "Projects/RFID Card Reader" && python -m platformio run`
Expected: SUCCESS

**Step 4: Commit**

```bash
git add "Projects/RFID Card Reader/src/uart.h" "Projects/RFID Card Reader/src/uart.c"
git commit -m "feat(rfid): add UART receive (uart_available, uart_getc)"
```

---

### Task 2: Add command handler and protocol output to main.c

**Files:**
- Modify: `Projects/RFID Card Reader/src/main.c`

**Step 1: Replace main.c with command-driven firmware**

Replace the entire file with:

```c
#include <avr/io.h>
#include <util/delay.h>
#include "uart.h"
#include "spi.h"
#include "mfrc522.h"

#define MODE_IDLE       0
#define MODE_CONTINUOUS 1
#define MODE_ONESHOT    2

// Print chip type and cloneability based on SAK byte (human-readable)
static void print_chip_info(uint8_t sak) {
    uart_puts("Chip Type: ");

    if (sak & 0x04) {
        uart_puts("(incomplete UID, cascade error)\r\n");
        return;
    }

    switch (sak) {
    case 0x08:
        uart_puts("MIFARE Classic 1K\r\n");
        uart_puts("Cloneable with RC522: YES\r\n");
        break;
    case 0x18:
        uart_puts("MIFARE Classic 4K\r\n");
        uart_puts("Cloneable with RC522: YES\r\n");
        break;
    case 0x09:
        uart_puts("MIFARE Mini\r\n");
        uart_puts("Cloneable with RC522: YES\r\n");
        break;
    case 0x20:
        uart_puts("MIFARE DESFire or MIFARE Plus\r\n");
        uart_puts("ISO 14443-4: YES\r\n");
        uart_puts("Cloneable with RC522: NO\r\n");
        uart_puts("Note: AES-128 encryption. Need PN532 or Proxmark3.\r\n");
        break;
    case 0x00:
        uart_puts("MIFARE Ultralight or NTAG\r\n");
        uart_puts("Cloneable with RC522: PARTIAL (no crypto)\r\n");
        break;
    case 0x01:
        uart_puts("TNP3xxx (NFC Forum Type 2)\r\n");
        uart_puts("Cloneable with RC522: NO\r\n");
        break;
    case 0x10:
        uart_puts("MIFARE Plus (SL2)\r\n");
        uart_puts("Cloneable with RC522: NO\r\n");
        break;
    case 0x11:
        uart_puts("MIFARE Plus (SL3)\r\n");
        uart_puts("Cloneable with RC522: NO\r\n");
        break;
    default:
        uart_puts("Unknown (SAK=0x");
        uart_put_hex(sak);
        uart_puts(")\r\n");
        uart_puts("Cloneable with RC522: UNKNOWN\r\n");
        break;
    }
}

// Send tag data in protocol format: TAG:<atqa>:<uid>:<sak>:<uid_len>
static void send_tag_protocol(uint8_t *atqa, uint8_t *uid, uint8_t uid_len, uint8_t sak) {
    uart_puts("TAG:");
    uart_put_hex(atqa[0]);
    uart_put_hex(atqa[1]);
    uart_putc(':');
    for (uint8_t i = 0; i < uid_len; i++) {
        uart_put_hex(uid[i]);
    }
    uart_putc(':');
    uart_put_hex(sak);
    uart_putc(':');
    uart_putc('0' + uid_len);
    uart_puts("\r\n");
}

// Perform one scan cycle. Returns 1 if tag found, 0 otherwise.
static uint8_t do_scan(void) {
    uint8_t status;
    uint8_t atqa[2];
    uint8_t uid_cl1[5];
    uint8_t uid_cl2[5];
    uint8_t full_uid[10];
    uint8_t uid_len;
    uint8_t sak;

    status = mfrc522_request(PICC_REQIDL, atqa);
    if (status != MI_OK) return 0;

    status = mfrc522_anticoll(PICC_ANTICOLL1, uid_cl1);
    if (status != MI_OK) return 0;

    status = mfrc522_select(PICC_ANTICOLL1, uid_cl1, &sak);
    if (status != MI_OK) {
        uart_puts("ERR:SELECT CL1 failed\r\n");
        return 0;
    }

    uid_len = 4;
    if (sak & 0x04) {
        full_uid[0] = uid_cl1[1];
        full_uid[1] = uid_cl1[2];
        full_uid[2] = uid_cl1[3];

        status = mfrc522_anticoll(PICC_ANTICOLL2, uid_cl2);
        if (status != MI_OK) {
            uart_puts("ERR:ANTICOLL CL2 failed\r\n");
            return 0;
        }

        status = mfrc522_select(PICC_ANTICOLL2, uid_cl2, &sak);
        if (status != MI_OK) {
            uart_puts("ERR:SELECT CL2 failed\r\n");
            return 0;
        }

        full_uid[3] = uid_cl2[0];
        full_uid[4] = uid_cl2[1];
        full_uid[5] = uid_cl2[2];
        full_uid[6] = uid_cl2[3];
        uid_len = 7;

        if (sak & 0x04) {
            uart_puts("ERR:Triple-size UID not supported\r\n");
            mfrc522_halt();
            return 0;
        }
    } else {
        for (uint8_t i = 0; i < 4; i++) {
            full_uid[i] = uid_cl1[i];
        }
    }

    // LED on
    PORTC |= (1 << PC0);

    // Protocol line (for GUI)
    send_tag_protocol(atqa, full_uid, uid_len, sak);

    // Human-readable output (for terminal, ignored by GUI)
    uart_puts("ATQA: ");
    uart_put_hex(atqa[0]);
    uart_putc(' ');
    uart_put_hex(atqa[1]);
    uart_puts("  UID: ");
    for (uint8_t i = 0; i < uid_len; i++) {
        uart_put_hex(full_uid[i]);
        if (i < uid_len - 1) uart_putc(':');
    }
    uart_puts("  SAK: 0x");
    uart_put_hex(sak);
    uart_puts("\r\n");
    print_chip_info(sak);

    PORTC &= ~(1 << PC0);

    mfrc522_halt();
    return 1;
}

int main(void) {
    uint8_t scan_mode = MODE_IDLE;

    spi_init();
    uart_init(9600);
    mfrc522_init();

    DDRC |= (1 << PC0);

    uart_puts("INFO:RFID Tag Analyzer v1.0\r\n");

    while (1) {
        // Check for commands from GUI/terminal
        if (uart_available()) {
            char cmd = uart_getc();
            switch (cmd) {
            case 'S':
                scan_mode = MODE_CONTINUOUS;
                uart_puts("OK:Scanning\r\n");
                break;
            case 'P':
                scan_mode = MODE_IDLE;
                uart_puts("OK:Paused\r\n");
                break;
            case 'O':
                scan_mode = MODE_ONESHOT;
                uart_puts("OK:Single scan\r\n");
                break;
            case 'V':
                uart_puts("INFO:RFID Tag Analyzer v1.0\r\n");
                break;
            }
        }

        if (scan_mode == MODE_IDLE) {
            _delay_ms(100);
            continue;
        }

        if (do_scan()) {
            if (scan_mode == MODE_ONESHOT) {
                scan_mode = MODE_IDLE;
            }
            _delay_ms(1500);
        } else {
            _delay_ms(200);
        }
    }

    return 0;
}
```

Key changes from previous main.c:
- Command handler reads single bytes from UART (S/P/O/V)
- Three scan modes: idle, continuous, one-shot
- `do_scan()` extracted as a function returning success/fail
- `send_tag_protocol()` sends machine-parseable TAG: line
- Human-readable output follows TAG: line (GUI ignores it)
- Starts in IDLE mode (waits for command)

**Step 2: Build firmware**

Run: `cd "Projects/RFID Card Reader" && python -m platformio run`
Expected: SUCCESS

**Step 3: Commit**

```bash
git add "Projects/RFID Card Reader/src/main.c"
git commit -m "feat(rfid): add serial command handler and protocol output

Commands: S=scan, P=pause, O=one-shot, V=version.
Protocol: TAG:<atqa>:<uid>:<sak>:<len> for GUI parsing.
Human-readable output preserved for terminal use."
```

---

### Task 3: Create tag_info.py with tests

**Files:**
- Create: `Projects/RFID Card Reader/gui/tag_info.py`
- Create: `Projects/RFID Card Reader/gui/tests/test_tag_info.py`

**Step 1: Write the test file**

```python
from datetime import datetime
from tag_info import Tag

def test_chip_type_classic_1k():
    tag = Tag(atqa="0400", uid="A3B24F01", sak=0x08, uid_len=4, timestamp=datetime.now())
    assert tag.chip_type == "MIFARE Classic 1K"
    assert tag.cloneable == "YES"

def test_chip_type_desfire():
    tag = Tag(atqa="0344", uid="04A3B24F01C780", sak=0x20, uid_len=7, timestamp=datetime.now())
    assert tag.chip_type == "MIFARE DESFire or MIFARE Plus"
    assert tag.cloneable == "NO"

def test_chip_type_unknown():
    tag = Tag(atqa="0000", uid="AABBCCDD", sak=0xFF, uid_len=4, timestamp=datetime.now())
    assert "Unknown" in tag.chip_type
    assert tag.cloneable == "UNKNOWN"

def test_uid_formatted_4byte():
    tag = Tag(atqa="0400", uid="A3B24F01", sak=0x08, uid_len=4, timestamp=datetime.now())
    assert tag.uid_formatted == "A3:B2:4F:01"

def test_uid_formatted_7byte():
    tag = Tag(atqa="0344", uid="04A3B24F01C780", sak=0x20, uid_len=7, timestamp=datetime.now())
    assert tag.uid_formatted == "04:A3:B2:4F:01:C7:80"

def test_chip_type_ultralight():
    tag = Tag(atqa="4400", uid="01020304", sak=0x00, uid_len=4, timestamp=datetime.now())
    assert tag.chip_type == "MIFARE Ultralight or NTAG"
    assert tag.cloneable == "PARTIAL"
```

**Step 2: Run tests to verify they fail**

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_tag_info.py -v`
Expected: FAIL (tag_info module not found)

**Step 3: Write tag_info.py**

```python
from dataclasses import dataclass
from datetime import datetime

SAK_TABLE = {
    0x08: ("MIFARE Classic 1K", "YES"),
    0x18: ("MIFARE Classic 4K", "YES"),
    0x09: ("MIFARE Mini", "YES"),
    0x20: ("MIFARE DESFire or MIFARE Plus", "NO"),
    0x00: ("MIFARE Ultralight or NTAG", "PARTIAL"),
    0x01: ("TNP3xxx (NFC Forum Type 2)", "NO"),
    0x10: ("MIFARE Plus (SL2)", "NO"),
    0x11: ("MIFARE Plus (SL3)", "NO"),
}


@dataclass
class Tag:
    atqa: str
    uid: str
    sak: int
    uid_len: int
    timestamp: datetime

    @property
    def chip_type(self) -> str:
        info = SAK_TABLE.get(self.sak)
        return info[0] if info else f"Unknown (SAK=0x{self.sak:02X})"

    @property
    def cloneable(self) -> str:
        info = SAK_TABLE.get(self.sak)
        return info[1] if info else "UNKNOWN"

    @property
    def uid_formatted(self) -> str:
        return ":".join(self.uid[i : i + 2] for i in range(0, len(self.uid), 2))
```

**Step 4: Run tests to verify they pass**

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_tag_info.py -v`
Expected: 6 passed

**Step 5: Commit**

```bash
git add "Projects/RFID Card Reader/gui/tag_info.py" "Projects/RFID Card Reader/gui/tests/test_tag_info.py"
git commit -m "feat(gui): add Tag dataclass with SAK chip type lookup"
```

---

### Task 4: Create serial_handler.py with tests

**Files:**
- Create: `Projects/RFID Card Reader/gui/serial_handler.py`
- Create: `Projects/RFID Card Reader/gui/tests/test_serial_handler.py`

**Step 1: Write the test file**

```python
from serial_handler import SerialHandler
from tag_info import Tag

def test_parse_tag_line():
    result = SerialHandler.parse_line("TAG:0344:04A3B24F01C780:20:7")
    assert isinstance(result, Tag)
    assert result.atqa == "0344"
    assert result.uid == "04A3B24F01C780"
    assert result.sak == 0x20
    assert result.uid_len == 7

def test_parse_tag_4byte():
    result = SerialHandler.parse_line("TAG:0400:A3B24F01:08:4")
    assert isinstance(result, Tag)
    assert result.sak == 0x08
    assert result.uid_len == 4

def test_parse_ok():
    result = SerialHandler.parse_line("OK:Scanning")
    assert result == {"type": "OK", "message": "Scanning"}

def test_parse_err():
    result = SerialHandler.parse_line("ERR:SELECT CL1 failed")
    assert result == {"type": "ERR", "message": "SELECT CL1 failed"}

def test_parse_info():
    result = SerialHandler.parse_line("INFO:Ready")
    assert result == {"type": "INFO", "message": "Ready"}

def test_parse_empty():
    assert SerialHandler.parse_line("") is None

def test_parse_garbage():
    assert SerialHandler.parse_line("random text") is None

def test_parse_human_readable_ignored():
    assert SerialHandler.parse_line("ATQA: 03 44  UID: 04:A3") is None
    assert SerialHandler.parse_line("Chip Type: MIFARE DESFire") is None
    assert SerialHandler.parse_line("=== Tag Detected ===") is None
```

**Step 2: Run tests to verify they fail**

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_serial_handler.py -v`
Expected: FAIL

**Step 3: Write serial_handler.py**

```python
import queue
import threading

import serial
import serial.tools.list_ports

from datetime import datetime
from tag_info import Tag


class SerialHandler:
    def __init__(self):
        self.ser = None
        self.queue = queue.Queue()
        self._thread = None
        self._running = False

    @staticmethod
    def list_ports():
        return [p.device for p in serial.tools.list_ports.comports()]

    def connect(self, port, baud=9600):
        self.ser = serial.Serial(port, baud, timeout=1)
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def disconnect(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.ser = None

    def send_command(self, cmd):
        if self.ser and self.ser.is_open:
            self.ser.write(cmd.encode())

    @property
    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    def _read_loop(self):
        while self._running and self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode("ascii", errors="ignore").strip()
                if not line:
                    continue
                msg = self.parse_line(line)
                if msg:
                    self.queue.put(msg)
            except Exception:
                continue

    @staticmethod
    def parse_line(line):
        if not line:
            return None
        if line.startswith("TAG:"):
            parts = line[4:].split(":")
            if len(parts) == 4:
                return Tag(
                    atqa=parts[0],
                    uid=parts[1],
                    sak=int(parts[2], 16),
                    uid_len=int(parts[3]),
                    timestamp=datetime.now(),
                )
        elif line.startswith(("OK:", "ERR:", "INFO:")):
            prefix_end = line.index(":")
            return {
                "type": line[:prefix_end],
                "message": line[prefix_end + 1 :],
            }
        return None
```

**Step 4: Run tests to verify they pass**

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_serial_handler.py -v`
Expected: 8 passed

**Step 5: Commit**

```bash
git add "Projects/RFID Card Reader/gui/serial_handler.py" "Projects/RFID Card Reader/gui/tests/test_serial_handler.py"
git commit -m "feat(gui): add serial handler with protocol parsing and threading"
```

---

### Task 5: Create the CustomTkinter GUI app

**Files:**
- Create: `Projects/RFID Card Reader/gui/app.py`

**Step 1: Write app.py**

```python
import customtkinter as ctk

from serial_handler import SerialHandler
from tag_info import Tag


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("RFID Tag Analyzer")
        self.geometry("800x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.serial = SerialHandler()
        self._build_connection_bar()
        self._build_tag_card()
        self._build_scan_buttons()
        self._build_log_table()
        self._poll_serial()

    def _build_connection_bar(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(frame, text="Port:").pack(side="left", padx=(10, 5))

        self.port_var = ctk.StringVar()
        self.port_menu = ctk.CTkOptionMenu(
            frame, variable=self.port_var, values=[""], width=120
        )
        self.port_menu.pack(side="left", padx=5)

        ctk.CTkButton(
            frame, text="Refresh", width=70, command=self._refresh_ports
        ).pack(side="left", padx=5)

        self.connect_btn = ctk.CTkButton(
            frame, text="Connect", width=90, command=self._toggle_connect
        )
        self.connect_btn.pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(
            frame, text="Disconnected", text_color="red"
        )
        self.status_label.pack(side="right", padx=10)

        self._refresh_ports()

    def _build_tag_card(self):
        self.card = ctk.CTkFrame(self)
        self.card.pack(fill="x", padx=10, pady=5)

        self.uid_label = ctk.CTkLabel(
            self.card,
            text="No tag scanned",
            font=ctk.CTkFont(family="Consolas", size=28, weight="bold"),
        )
        self.uid_label.pack(pady=(20, 5))

        info = ctk.CTkFrame(self.card, fg_color="transparent")
        info.pack(pady=5)

        self.atqa_label = ctk.CTkLabel(info, text="ATQA: --", font=ctk.CTkFont(size=13))
        self.atqa_label.pack(side="left", padx=20)

        self.sak_label = ctk.CTkLabel(info, text="SAK: --", font=ctk.CTkFont(size=13))
        self.sak_label.pack(side="left", padx=20)

        self.chip_label = ctk.CTkLabel(
            self.card, text="", font=ctk.CTkFont(size=15)
        )
        self.chip_label.pack(pady=5)

        self.clone_label = ctk.CTkLabel(
            self.card, text="", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.clone_label.pack(pady=(0, 20))

    def _build_scan_buttons(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(pady=5)

        self.scan_btn = ctk.CTkButton(
            frame,
            text="Start Scan",
            fg_color="#2ea043",
            hover_color="#238636",
            width=120,
            command=lambda: self._send("S"),
        )
        self.scan_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(
            frame,
            text="Stop",
            fg_color="#da3633",
            hover_color="#b62324",
            width=90,
            command=lambda: self._send("P"),
        )
        self.stop_btn.pack(side="left", padx=5)

        self.single_btn = ctk.CTkButton(
            frame, text="Single Scan", width=110, command=lambda: self._send("O")
        )
        self.single_btn.pack(side="left", padx=5)

    def _build_log_table(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        ctk.CTkLabel(
            frame, text="Scan Log", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(5, 0))

        self.log_text = ctk.CTkTextbox(
            frame, font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        header = f"{'Time':<10} | {'UID':<22} | {'Chip Type':<30} | SAK\n"
        self.log_text.insert("end", header)
        self.log_text.insert("end", "-" * 78 + "\n")
        self.log_text.configure(state="disabled")

    def _refresh_ports(self):
        ports = SerialHandler.list_ports()
        values = ports if ports else ["No ports found"]
        self.port_menu.configure(values=values)
        if ports:
            self.port_var.set(ports[0])

    def _toggle_connect(self):
        if self.serial.is_connected:
            self.serial.disconnect()
            self.connect_btn.configure(text="Connect")
            self.status_label.configure(text="Disconnected", text_color="red")
        else:
            port = self.port_var.get()
            if not port or port == "No ports found":
                return
            try:
                self.serial.connect(port)
                self.connect_btn.configure(text="Disconnect")
                self.status_label.configure(
                    text=f"Connected: {port}", text_color="#2ea043"
                )
            except Exception as e:
                self.status_label.configure(
                    text=f"Error: {e}", text_color="red"
                )

    def _send(self, cmd):
        self.serial.send_command(cmd)

    def _poll_serial(self):
        while not self.serial.queue.empty():
            msg = self.serial.queue.get_nowait()
            if isinstance(msg, Tag):
                self._update_tag_display(msg)
                self._add_log_entry(msg)
        self.after(100, self._poll_serial)

    def _update_tag_display(self, tag):
        self.uid_label.configure(text=tag.uid_formatted)
        atqa = tag.atqa
        self.atqa_label.configure(
            text=f"ATQA: {atqa[:2]} {atqa[2:]}" if len(atqa) == 4 else f"ATQA: {atqa}"
        )
        self.sak_label.configure(text=f"SAK: 0x{tag.sak:02X}")
        self.chip_label.configure(text=tag.chip_type)

        colors = {"YES": "#2ea043", "NO": "#da3633", "PARTIAL": "#d29922", "UNKNOWN": "gray"}
        color = colors.get(tag.cloneable, "gray")
        self.clone_label.configure(
            text=f"Cloneable: {tag.cloneable}", text_color=color
        )

    def _add_log_entry(self, tag):
        time_str = tag.timestamp.strftime("%H:%M:%S")
        line = f"{time_str}  | {tag.uid_formatted:<22} | {tag.chip_type:<30} | 0x{tag.sak:02X}\n"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def destroy(self):
        self.serial.disconnect()
        super().destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
```

**Step 2: Verify it launches**

Run: `cd "Projects/RFID Card Reader/gui" && python app.py`
Expected: Window opens with dark theme, shows connection controls, tag card area, scan buttons, log table. Close it manually.

**Step 3: Commit**

```bash
git add "Projects/RFID Card Reader/gui/app.py"
git commit -m "feat(gui): add CustomTkinter control panel with tag display and scan log"
```

---

### Task 6: Create requirements.txt and __init__.py

**Files:**
- Create: `Projects/RFID Card Reader/gui/requirements.txt`
- Create: `Projects/RFID Card Reader/gui/tests/__init__.py`

**Step 1: Create requirements.txt**

```
customtkinter>=5.2.0
pyserial>=3.5
pytest>=7.0.0
```

**Step 2: Create empty __init__.py for tests package**

Empty file (allows pytest to find test modules with relative imports).

**Step 3: Install dependencies and run all tests**

Run: `pip install -r "Projects/RFID Card Reader/gui/requirements.txt"`
Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/ -v`
Expected: All 14 tests pass (6 from tag_info + 8 from serial_handler)

**Step 4: Commit**

```bash
git add "Projects/RFID Card Reader/gui/requirements.txt" "Projects/RFID Card Reader/gui/tests/__init__.py"
git commit -m "chore(gui): add requirements.txt and test package init"
```

---

### Task 7: Build firmware and run full verification

**Step 1: Build firmware**

Run: `cd "Projects/RFID Card Reader" && python -m platformio run`
Expected: SUCCESS

**Step 2: Run all Python tests**

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/ -v`
Expected: 14 passed

**Step 3: Launch GUI**

Run: `cd "Projects/RFID Card Reader/gui" && python app.py`
Expected: Window opens, COM port dropdown populates, dark theme, all controls visible.
