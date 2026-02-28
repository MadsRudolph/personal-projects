# MIFARE Classic Clone Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add full card cloning: read all 64 blocks from a MIFARE Classic 1K, store in GUI, write to a target card.

**Architecture:** Firmware-driven dump/load. Single `R` command reads all sectors, streams `DATA:` lines. `W`/`W0` enters write mode, GUI sends `LOAD:` lines. GUI stores 1024-byte card image, supports save/load to `.bin` files.

**Tech Stack:** Bare-metal AVR C (ATmega328P), Python 3 + CustomTkinter + pyserial

---

### Task 1: Firmware - MFRC522 Driver Functions

Add auth, read, write, and stop_crypto to the MFRC522 driver.

**Files:**
- Modify: `Projects/RFID Card Reader/src/mfrc522.h`
- Modify: `Projects/RFID Card Reader/src/mfrc522.c`

**Step 1: Add new defines to mfrc522.h**

Add after the existing `PICC_HALT` define (line 71):

```c
#define PICC_READ    0x30  // Read block
#define PICC_WRITE   0xA0  // Write block
#define PICC_AUTHKA  0x60  // Auth with Key A
#define PICC_AUTHKB  0x61  // Auth with Key B
```

**Step 2: Add new function prototypes to mfrc522.h**

Add after `mfrc522_halt()` prototype (line 89):

```c
uint8_t mfrc522_auth(uint8_t auth_mode, uint8_t block, uint8_t *key, uint8_t *uid);
uint8_t mfrc522_read_block(uint8_t block, uint8_t *buffer);
uint8_t mfrc522_write_block(uint8_t block, uint8_t *data);
void    mfrc522_stop_crypto(void);
```

**Step 3: Implement mfrc522_auth() in mfrc522.c**

Add at end of file. This uses the MFRC522's built-in `PCD_MFAuthent` command which handles Crypto1 internally:

```c
uint8_t mfrc522_auth(uint8_t auth_mode, uint8_t block, uint8_t *key, uint8_t *uid) {
    uint8_t status;
    uint8_t buffer[12];
    uint8_t n;
    uint8_t i;

    // Build auth command: [auth_mode, block, key(6), uid(4)]
    buffer[0] = auth_mode;
    buffer[1] = block;
    for (i = 0; i < 6; i++) {
        buffer[2 + i] = key[i];
    }
    for (i = 0; i < 4; i++) {
        buffer[8 + i] = uid[i];
    }

    // PCD_MFAuthent does not use transceive - it's a special command
    mfrc522_write_reg(ComIEnReg, 0x12);  // IdleIRq and ErrIRq
    mfrc522_clear_bit(ComIrqReg, 0x80);
    mfrc522_set_bit(FIFOLevelReg, 0x80); // Flush FIFO
    mfrc522_write_reg(CommandReg, PCD_Idle);

    // Write data to FIFO
    for (i = 0; i < 12; i++) {
        mfrc522_write_reg(FIFODataReg, buffer[i]);
    }

    mfrc522_write_reg(CommandReg, PCD_MFAuthent);

    // Wait for completion
    i = 255;
    do {
        n = mfrc522_read_reg(ComIrqReg);
        i--;
    } while (i && !(n & 0x01) && !(n & 0x10));

    // Check Status2Reg - Crypto1On bit indicates successful auth
    if (mfrc522_read_reg(Status2Reg) & 0x08) {
        return MI_OK;
    }
    return MI_ERR;
}
```

**Step 4: Implement mfrc522_read_block() in mfrc522.c**

```c
uint8_t mfrc522_read_block(uint8_t block, uint8_t *buffer) {
    uint8_t status;
    uint8_t cmd[4];
    uint8_t back_len;

    cmd[0] = PICC_READ;
    cmd[1] = block;
    mfrc522_calculate_crc(cmd, 2, &cmd[2]);

    status = mfrc522_to_card(PCD_Transceive, cmd, 4, buffer, &back_len);
    if (status != MI_OK || back_len != 0x90) {
        // 0x90 = 144 bits = 18 bytes (16 data + 2 CRC)
        return MI_ERR;
    }
    return MI_OK;
}
```

**Step 5: Implement mfrc522_write_block() in mfrc522.c**

Two-phase MIFARE write: send WRITE command, wait for ACK (0x0A = 4 bits), then send 16 data bytes:

```c
uint8_t mfrc522_write_block(uint8_t block, uint8_t *data) {
    uint8_t status;
    uint8_t cmd[4];
    uint8_t back_data[16];
    uint8_t back_len;

    // Phase 1: Send WRITE command + block number
    cmd[0] = PICC_WRITE;
    cmd[1] = block;
    mfrc522_calculate_crc(cmd, 2, &cmd[2]);

    status = mfrc522_to_card(PCD_Transceive, cmd, 4, back_data, &back_len);
    // Expect 4-bit ACK (0x0A)
    if (status != MI_OK || back_len != 4 || (back_data[0] & 0x0F) != 0x0A) {
        return MI_ERR;
    }

    // Phase 2: Send 16 bytes of data + CRC
    uint8_t write_buf[18];
    for (uint8_t i = 0; i < 16; i++) {
        write_buf[i] = data[i];
    }
    mfrc522_calculate_crc(write_buf, 16, &write_buf[16]);

    status = mfrc522_to_card(PCD_Transceive, write_buf, 18, back_data, &back_len);
    if (status != MI_OK || back_len != 4 || (back_data[0] & 0x0F) != 0x0A) {
        return MI_ERR;
    }

    return MI_OK;
}
```

**Step 6: Implement mfrc522_stop_crypto() in mfrc522.c**

```c
void mfrc522_stop_crypto(void) {
    mfrc522_clear_bit(Status2Reg, 0x08);  // Clear MFCrypto1On bit
}
```

**Step 7: Build to verify compilation**

Run: `cd "Projects/RFID Card Reader" && pio run`
Expected: BUILD SUCCESS

**Step 8: Commit**

```bash
git add "Projects/RFID Card Reader/src/mfrc522.h" "Projects/RFID Card Reader/src/mfrc522.c"
git commit -m "feat: add MIFARE auth, read_block, write_block to MFRC522 driver"
```

---

### Task 2: Firmware - Read Dump Command

Add the `R` command to main.c that reads all 64 blocks and streams them over serial.

**Files:**
- Modify: `Projects/RFID Card Reader/src/main.c`

**Step 1: Add default key and dump function**

Add after `send_tag_protocol()` function (after line 78). The dump function:
1. Detects a card (REQA + anticoll + select to get UID)
2. Loops through sectors 0-15
3. Authenticates each sector with Key A (FFFFFFFFFFFF)
4. Reads all 4 blocks in that sector
5. Sends each block as `DATA:<block_hex>:<32_hex_chars>`
6. On auth fail, sends `ERR:AUTH_FAIL:<sector_hex>` and continues

```c
static const uint8_t default_key[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

static void send_block_data(uint8_t block, uint8_t *data) {
    uart_puts("DATA:");
    uart_put_hex(block);
    uart_putc(':');
    for (uint8_t i = 0; i < 16; i++) {
        uart_put_hex(data[i]);
    }
    uart_puts("\r\n");
}

static void do_dump(void) {
    uint8_t status;
    uint8_t atqa[2];
    uint8_t uid[5];
    uint8_t sak;
    uint8_t block_data[18]; // 16 data + 2 CRC from read

    // Detect card
    status = mfrc522_request(PICC_REQIDL, atqa);
    if (status != MI_OK) {
        uart_puts("ERR:NO_TAG\r\n");
        return;
    }

    status = mfrc522_anticoll(PICC_ANTICOLL1, uid);
    if (status != MI_OK) {
        uart_puts("ERR:ANTICOLL\r\n");
        return;
    }

    status = mfrc522_select(PICC_ANTICOLL1, uid, &sak);
    if (status != MI_OK) {
        uart_puts("ERR:SELECT\r\n");
        return;
    }

    // Read all 16 sectors
    for (uint8_t sector = 0; sector < 16; sector++) {
        uint8_t first_block = sector * 4;

        // Authenticate sector with Key A
        status = mfrc522_auth(PICC_AUTHKA, first_block, (uint8_t *)default_key, uid);
        if (status != MI_OK) {
            uart_puts("ERR:AUTH_FAIL:");
            uart_put_hex(sector);
            uart_puts("\r\n");
            continue;
        }

        // Read all 4 blocks in sector
        for (uint8_t b = 0; b < 4; b++) {
            uint8_t block = first_block + b;
            status = mfrc522_read_block(block, block_data);
            if (status == MI_OK) {
                send_block_data(block, block_data);
            } else {
                uart_puts("ERR:READ_FAIL:");
                uart_put_hex(block);
                uart_puts("\r\n");
            }
        }
    }

    mfrc522_stop_crypto();
    mfrc522_halt();
    uart_puts("OK:DUMP_COMPLETE\r\n");
}
```

**Step 2: Add 'R' command to the main loop switch**

In `main()`, inside the `switch (cmd)` block (around line 179), add after the `'V'` case:

```c
case 'R':
    do_dump();
    break;
```

**Step 3: Build**

Run: `cd "Projects/RFID Card Reader" && pio run`
Expected: BUILD SUCCESS

**Step 4: Commit**

```bash
git add "Projects/RFID Card Reader/src/main.c"
git commit -m "feat: add R command for full card dump"
```

---

### Task 3: Firmware - Write Mode Command

Add `W`, `W0`, and `D` commands plus LOAD: line parsing for writing blocks.

**Files:**
- Modify: `Projects/RFID Card Reader/src/main.c`

**Step 1: Add hex parsing helper and write state**

Add a helper function to parse hex characters from serial input. Add at top of main.c, after the mode defines:

```c
#define MODE_WRITE      3
#define MODE_WRITE_BLK0 4

static uint8_t hex_char_to_val(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return 0xFF;
}
```

**Step 2: Add write handler function**

This function is called when a full line is received during write mode. It parses `LOAD:<block_hex>:<32_hex_chars>` and writes the block.

Add after `do_dump()`:

```c
static uint8_t write_uid[5];  // UID of card in write mode
static uint8_t write_authenticated_sector;  // Currently authenticated sector (0xFF = none)

static uint8_t parse_hex_byte(const char *s) {
    uint8_t hi = hex_char_to_val(s[0]);
    uint8_t lo = hex_char_to_val(s[1]);
    if (hi == 0xFF || lo == 0xFF) return 0;
    return (hi << 4) | lo;
}

static void do_write_init(uint8_t allow_block0) {
    uint8_t status;
    uint8_t atqa[2];
    uint8_t sak;

    status = mfrc522_request(PICC_REQIDL, atqa);
    if (status != MI_OK) {
        uart_puts("ERR:NO_TAG\r\n");
        return;
    }

    status = mfrc522_anticoll(PICC_ANTICOLL1, write_uid);
    if (status != MI_OK) {
        uart_puts("ERR:ANTICOLL\r\n");
        return;
    }

    status = mfrc522_select(PICC_ANTICOLL1, write_uid, &sak);
    if (status != MI_OK) {
        uart_puts("ERR:SELECT\r\n");
        return;
    }

    write_authenticated_sector = 0xFF;
    uart_puts("OK:WRITE_READY\r\n");
}

static void handle_load_line(char *line, uint8_t len, uint8_t allow_block0) {
    // Expect: LOAD:<2 hex chars block>:<32 hex chars data>
    // Minimum length: 5 (LOAD:) + 2 + 1 + 32 = 40
    if (len < 40) {
        uart_puts("ERR:BAD_FORMAT\r\n");
        return;
    }

    // Parse block number
    uint8_t block = parse_hex_byte(&line[5]);

    // Skip block 0 unless allowed
    if (block == 0 && !allow_block0) {
        uart_puts("OK:SKIP_BLK0\r\n");
        return;
    }

    // Parse 16 data bytes
    uint8_t data[16];
    for (uint8_t i = 0; i < 16; i++) {
        data[i] = parse_hex_byte(&line[8 + i * 2]);
    }

    // Authenticate if needed (new sector)
    uint8_t sector = block / 4;
    if (sector != write_authenticated_sector) {
        uint8_t status = mfrc522_auth(PICC_AUTHKA, block, (uint8_t *)default_key, write_uid);
        if (status != MI_OK) {
            uart_puts("ERR:WRITE_AUTH:");
            uart_put_hex(block);
            uart_puts("\r\n");
            return;
        }
        write_authenticated_sector = sector;
    }

    // Write block
    uint8_t status = mfrc522_write_block(block, data);
    if (status == MI_OK) {
        uart_puts("OK:WROTE:");
        uart_put_hex(block);
        uart_puts("\r\n");
    } else {
        uart_puts("ERR:WRITE_FAIL:");
        uart_put_hex(block);
        uart_puts("\r\n");
    }
}
```

**Step 3: Add line buffer and write mode logic to main loop**

Modify the `main()` function. Add a line buffer before the while loop, and modify the command handling to support write mode with line-based input:

```c
int main(void) {
    uint8_t scan_mode = MODE_IDLE;
    char line_buf[48];
    uint8_t line_pos = 0;

    spi_init();
    uart_init(9600);
    mfrc522_init();

    DDRC |= (1 << PC0);

    uart_puts("INFO:RFID Tag Analyzer v2.0\r\n");

    while (1) {
        if (uart_available()) {
            char c = uart_getc();

            if (scan_mode == MODE_WRITE || scan_mode == MODE_WRITE_BLK0) {
                // In write mode: buffer lines until \r or \n
                if (c == '\r' || c == '\n') {
                    if (line_pos > 0) {
                        line_buf[line_pos] = '\0';
                        if (line_buf[0] == 'D') {
                            mfrc522_stop_crypto();
                            mfrc522_halt();
                            uart_puts("OK:WRITE_DONE\r\n");
                            scan_mode = MODE_IDLE;
                        } else if (line_pos >= 5 && line_buf[0] == 'L') {
                            handle_load_line(line_buf, line_pos,
                                scan_mode == MODE_WRITE_BLK0 ? 1 : 0);
                        } else {
                            uart_puts("ERR:BAD_CMD\r\n");
                        }
                        line_pos = 0;
                    }
                } else if (line_pos < sizeof(line_buf) - 1) {
                    line_buf[line_pos++] = c;
                }
            } else {
                // Normal command mode (single char commands)
                switch (c) {
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
                    uart_puts("INFO:RFID Tag Analyzer v2.0\r\n");
                    break;
                case 'R':
                    do_dump();
                    break;
                case 'W':
                    scan_mode = MODE_WRITE;
                    do_write_init(0);
                    break;
                }
            }
        }

        // Handle W0 as two-char command: check if we just got 'W' and next is '0'
        // Actually, handle this differently - see note below

        if (scan_mode == MODE_IDLE || scan_mode == MODE_WRITE || scan_mode == MODE_WRITE_BLK0) {
            _delay_ms(10);
            if (scan_mode == MODE_IDLE) _delay_ms(90);
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

Note: For `W0`, we'll simplify - use `B` (block-0-write) as a single char command instead of the two-char `W0`. Update the switch:

```c
case 'B':
    scan_mode = MODE_WRITE_BLK0;
    do_write_init(1);
    break;
```

**Step 4: Build**

Run: `cd "Projects/RFID Card Reader" && pio run`
Expected: BUILD SUCCESS

**Step 5: Commit**

```bash
git add "Projects/RFID Card Reader/src/main.c"
git commit -m "feat: add write mode with LOAD: line parsing"
```

---

### Task 4: GUI - Serial Handler Updates + Tests

Update the serial handler to parse `DATA:` lines and send `LOAD:` lines.

**Files:**
- Modify: `Projects/RFID Card Reader/gui/serial_handler.py`
- Modify: `Projects/RFID Card Reader/gui/tests/test_serial_handler.py`

**Step 1: Write tests for DATA: line parsing**

Add to `test_serial_handler.py`:

```python
def test_parse_data_line():
    result = SerialHandler.parse_line("DATA:00:A1B2C3D4050607080910111213141516")
    assert result == {
        "type": "DATA",
        "block": 0,
        "data": "A1B2C3D4050607080910111213141516",
    }


def test_parse_data_line_high_block():
    result = SerialHandler.parse_line("DATA:3F:00112233445566778899AABBCCDDEEFF")
    assert result == {
        "type": "DATA",
        "block": 0x3F,
        "data": "00112233445566778899AABBCCDDEEFF",
    }


def test_parse_ok_dump_complete():
    result = SerialHandler.parse_line("OK:DUMP_COMPLETE")
    assert result == {"type": "OK", "message": "DUMP_COMPLETE"}


def test_parse_ok_write_ready():
    result = SerialHandler.parse_line("OK:WRITE_READY")
    assert result == {"type": "OK", "message": "WRITE_READY"}


def test_parse_ok_wrote():
    result = SerialHandler.parse_line("OK:WROTE:0A")
    assert result == {"type": "OK", "message": "WROTE:0A"}


def test_parse_err_auth_fail():
    result = SerialHandler.parse_line("ERR:AUTH_FAIL:03")
    assert result == {"type": "ERR", "message": "AUTH_FAIL:03"}
```

**Step 2: Run tests to verify they fail**

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_serial_handler.py -v`
Expected: 6 new tests FAIL (DATA: parsing not implemented yet)

**Step 3: Update parse_line() in serial_handler.py**

Replace the `parse_line` method to also handle `DATA:` lines:

```python
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
    elif line.startswith("DATA:"):
        parts = line[5:].split(":")
        if len(parts) == 2 and len(parts[1]) == 32:
            return {
                "type": "DATA",
                "block": int(parts[0], 16),
                "data": parts[1],
            }
    elif line.startswith(("OK:", "ERR:", "INFO:")):
        prefix_end = line.index(":")
        return {
            "type": line[:prefix_end],
            "message": line[prefix_end + 1:],
        }
    return None
```

**Step 4: Add send_load_block() method to SerialHandler**

```python
def send_load_block(self, block, hex_data):
    """Send a LOAD:<block_hex>:<data_hex> line for writing."""
    cmd = f"LOAD:{block:02X}:{hex_data}\n"
    if self.ser and self.ser.is_open:
        self.ser.write(cmd.encode())
```

**Step 5: Run tests to verify they pass**

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/ -v`
Expected: ALL tests PASS

**Step 6: Commit**

```bash
git add "Projects/RFID Card Reader/gui/serial_handler.py" "Projects/RFID Card Reader/gui/tests/test_serial_handler.py"
git commit -m "feat: add DATA: parsing and LOAD: sending to serial handler"
```

---

### Task 5: GUI - Card Data Model + Tests

A simple class to hold and manage a full card dump (64 blocks of 16 bytes).

**Files:**
- Create: `Projects/RFID Card Reader/gui/card_data.py`
- Create: `Projects/RFID Card Reader/gui/tests/test_card_data.py`

**Step 1: Write tests**

```python
import os
import tempfile
from card_data import CardData


def test_empty_card():
    card = CardData()
    assert card.block_count == 0
    assert not card.has_data


def test_set_and_get_block():
    card = CardData()
    card.set_block(0, "A1B2C3D4050607080910111213141516")
    assert card.get_block(0) == "A1B2C3D4050607080910111213141516"
    assert card.block_count == 1
    assert card.has_data


def test_get_missing_block():
    card = CardData()
    assert card.get_block(5) is None


def test_sector_for_block():
    card = CardData()
    assert card.sector_for_block(0) == 0
    assert card.sector_for_block(3) == 0
    assert card.sector_for_block(4) == 1
    assert card.sector_for_block(63) == 15


def test_is_sector_trailer():
    card = CardData()
    assert card.is_sector_trailer(3)
    assert card.is_sector_trailer(7)
    assert card.is_sector_trailer(63)
    assert not card.is_sector_trailer(0)
    assert not card.is_sector_trailer(4)


def test_clear():
    card = CardData()
    card.set_block(0, "A1B2C3D4050607080910111213141516")
    card.clear()
    assert card.block_count == 0
    assert not card.has_data


def test_save_and_load_bin():
    card = CardData()
    for i in range(64):
        card.set_block(i, f"{i:02X}" * 16)

    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        path = f.name

    try:
        card.save_bin(path)
        assert os.path.getsize(path) == 1024

        card2 = CardData()
        card2.load_bin(path)
        assert card2.block_count == 64
        for i in range(64):
            assert card2.get_block(i) == f"{i:02X}" * 16
    finally:
        os.unlink(path)


def test_blocks_for_write_skips_block0():
    card = CardData()
    for i in range(8):
        card.set_block(i, "AA" * 16)
    blocks = card.blocks_for_write(allow_block0=False)
    assert 0 not in [b for b, _ in blocks]
    assert len(blocks) == 7


def test_blocks_for_write_includes_block0():
    card = CardData()
    for i in range(8):
        card.set_block(i, "AA" * 16)
    blocks = card.blocks_for_write(allow_block0=True)
    assert 0 in [b for b, _ in blocks]
    assert len(blocks) == 8
```

**Step 2: Run tests to verify they fail**

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_card_data.py -v`
Expected: FAIL (module not found)

**Step 3: Implement CardData**

```python
class CardData:
    """Holds a complete MIFARE Classic 1K card dump (64 blocks, 16 bytes each)."""

    def __init__(self):
        self._blocks = {}

    @property
    def block_count(self):
        return len(self._blocks)

    @property
    def has_data(self):
        return len(self._blocks) > 0

    def set_block(self, block, hex_data):
        self._blocks[block] = hex_data.upper()

    def get_block(self, block):
        return self._blocks.get(block)

    def clear(self):
        self._blocks.clear()

    @staticmethod
    def sector_for_block(block):
        return block // 4

    @staticmethod
    def is_sector_trailer(block):
        return block % 4 == 3

    def blocks_for_write(self, allow_block0=False):
        result = []
        for block in sorted(self._blocks.keys()):
            if block == 0 and not allow_block0:
                continue
            result.append((block, self._blocks[block]))
        return result

    def save_bin(self, path):
        with open(path, "wb") as f:
            for block in range(64):
                data = self._blocks.get(block)
                if data:
                    f.write(bytes.fromhex(data))
                else:
                    f.write(b"\x00" * 16)

    def load_bin(self, path):
        self.clear()
        with open(path, "rb") as f:
            raw = f.read()
        for block in range(64):
            offset = block * 16
            if offset + 16 <= len(raw):
                self._blocks[block] = raw[offset : offset + 16].hex().upper()
```

**Step 4: Run tests to verify they pass**

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_card_data.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add "Projects/RFID Card Reader/gui/card_data.py" "Projects/RFID Card Reader/gui/tests/test_card_data.py"
git commit -m "feat: add CardData model with save/load bin support"
```

---

### Task 6: GUI - Read/Write UI and Hex Viewer

Add read/write buttons, hex viewer, save/load dump, and progress feedback to the GUI.

**Files:**
- Modify: `Projects/RFID Card Reader/gui/app.py`

**Step 1: Add imports and card_data to App.__init__**

Add import at top:
```python
from card_data import CardData
from tkinter import filedialog
```

Add to `__init__` after `self.serial = SerialHandler()`:
```python
self.card_data = CardData()
self._write_pending = []
self._writing = False
```

Add new build methods to `__init__` after existing ones:
```python
self._build_rw_buttons()
self._build_hex_viewer()
```

**Step 2: Add read/write button bar**

```python
def _build_rw_buttons(self):
    frame = ctk.CTkFrame(self, fg_color="transparent")
    frame.pack(pady=5)

    self.read_btn = ctk.CTkButton(
        frame,
        text="Read Card",
        fg_color="#1f6feb",
        hover_color="#1958c7",
        width=120,
        command=self._read_card,
    )
    self.read_btn.pack(side="left", padx=5)

    self.write_btn = ctk.CTkButton(
        frame,
        text="Write Card",
        fg_color="#d29922",
        hover_color="#b07d1a",
        width=120,
        command=self._write_card,
    )
    self.write_btn.pack(side="left", padx=5)

    self.blk0_var = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(
        frame, text="Write Block 0", variable=self.blk0_var
    ).pack(side="left", padx=10)

    ctk.CTkButton(
        frame, text="Save Dump", width=90, command=self._save_dump
    ).pack(side="left", padx=5)

    ctk.CTkButton(
        frame, text="Load Dump", width=90, command=self._load_dump
    ).pack(side="left", padx=5)

    self.progress_label = ctk.CTkLabel(frame, text="")
    self.progress_label.pack(side="left", padx=10)
```

**Step 3: Add hex viewer**

A scrollable textbox showing all 16 sectors with block data. Refreshed when card data changes.

```python
def _build_hex_viewer(self):
    frame = ctk.CTkFrame(self)
    frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

    ctk.CTkLabel(
        frame, text="Card Data", font=ctk.CTkFont(weight="bold")
    ).pack(anchor="w", padx=10, pady=(5, 0))

    self.hex_text = ctk.CTkTextbox(
        frame, font=ctk.CTkFont(family="Consolas", size=11)
    )
    self.hex_text.pack(fill="both", expand=True, padx=5, pady=5)
    self._refresh_hex_viewer()

def _refresh_hex_viewer(self):
    self.hex_text.configure(state="normal")
    self.hex_text.delete("1.0", "end")

    if not self.card_data.has_data:
        self.hex_text.insert("end", "No card data. Use 'Read Card' or 'Load Dump'.\n")
    else:
        for sector in range(16):
            self.hex_text.insert("end", f"--- Sector {sector:2d} ---\n")
            for b in range(4):
                block = sector * 4 + b
                data = self.card_data.get_block(block)
                if data:
                    # Format as spaced hex pairs
                    spaced = " ".join(data[i:i+2] for i in range(0, 32, 2))
                    label = "T" if self.card_data.is_sector_trailer(block) else " "
                    self.hex_text.insert(
                        "end", f"  Blk {block:2d} [{label}]: {spaced}\n"
                    )
                else:
                    self.hex_text.insert(
                        "end", f"  Blk {block:2d}:      -- no data --\n"
                    )

    self.hex_text.configure(state="disabled")
```

**Step 4: Add command handlers**

```python
def _read_card(self):
    if not self.serial.is_connected:
        return
    self.card_data.clear()
    self.progress_label.configure(text="Reading...")
    self._send("R")

def _write_card(self):
    if not self.serial.is_connected or not self.card_data.has_data:
        return
    self._write_pending = self.card_data.blocks_for_write(
        allow_block0=self.blk0_var.get()
    )
    self._writing = True
    self.progress_label.configure(text="Waiting for card...")
    cmd = "B" if self.blk0_var.get() else "W"
    self._send(cmd)

def _save_dump(self):
    if not self.card_data.has_data:
        return
    path = filedialog.asksaveasfilename(
        defaultextension=".bin",
        filetypes=[("Binary dump", "*.bin"), ("All files", "*.*")],
    )
    if path:
        self.card_data.save_bin(path)
        self.progress_label.configure(text="Saved!")

def _load_dump(self):
    path = filedialog.askopenfilename(
        filetypes=[("Binary dump", "*.bin"), ("All files", "*.*")],
    )
    if path:
        self.card_data.load_bin(path)
        self._refresh_hex_viewer()
        self.progress_label.configure(text=f"Loaded {self.card_data.block_count} blocks")
```

**Step 5: Update _poll_serial to handle DATA: and write flow**

Replace `_poll_serial`:

```python
def _poll_serial(self):
    while not self.serial.queue.empty():
        msg = self.serial.queue.get_nowait()
        if isinstance(msg, Tag):
            self._update_tag_display(msg)
            self._add_log_entry(msg)
        elif isinstance(msg, dict):
            if msg["type"] == "DATA":
                self.card_data.set_block(msg["block"], msg["data"])
                sector = self.card_data.sector_for_block(msg["block"])
                self.progress_label.configure(
                    text=f"Reading sector {sector}/15..."
                )
            elif msg["type"] == "OK":
                if msg["message"] == "DUMP_COMPLETE":
                    self.progress_label.configure(
                        text=f"Read complete: {self.card_data.block_count} blocks"
                    )
                    self._refresh_hex_viewer()
                elif msg["message"] == "WRITE_READY":
                    self._send_next_write()
                elif msg["message"].startswith("WROTE:"):
                    self._send_next_write()
                elif msg["message"] == "WRITE_DONE":
                    self._writing = False
                    self.progress_label.configure(text="Write complete!")
            elif msg["type"] == "ERR":
                self.progress_label.configure(
                    text=f"Error: {msg['message']}"
                )
    self.after(100, self._poll_serial)

def _send_next_write(self):
    if self._write_pending:
        block, hex_data = self._write_pending.pop(0)
        total = self.card_data.block_count
        remaining = len(self._write_pending)
        written = total - remaining - 1
        self.progress_label.configure(
            text=f"Writing block {block} ({written}/{total})..."
        )
        self.serial.send_load_block(block, hex_data)
    else:
        self._send("D")
```

**Step 6: Build and manually test**

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/ -v`
Expected: ALL existing tests PASS

Run: `cd "Projects/RFID Card Reader/gui" && python app.py`
Expected: GUI launches with new Read Card, Write Card, Save Dump, Load Dump buttons and hex viewer

**Step 7: Commit**

```bash
git add "Projects/RFID Card Reader/gui/app.py"
git commit -m "feat: add read/write clone UI with hex viewer"
```
