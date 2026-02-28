# Tag Diagnostic Analyzer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the broken cloner with a tag diagnostic analyzer that identifies chip type (MIFARE Classic vs DESFire) via ATQA/SAK before attempting any write operations.

**Architecture:** Add `mfrc522_select()` with cascade level support to the existing MFRC522 driver. Remove the broken write logic. Replace the cloner main loop with a diagnostic scan that prints ATQA, full UID (4/7/10-byte), SAK, and chip type interpretation over UART.

**Tech Stack:** Bare-metal C on ATmega328P, MFRC522 via SPI, UART 9600 baud, PlatformIO (no framework)

---

### Task 1: Clean up mfrc522.h

**Files:**
- Modify: `Projects/RFID Card Reader/src/mfrc522.h`

**Step 1: Remove duplicate PICC_WRITE and write-related prototypes**

Remove line 5 (`#define PICC_WRITE 0xA0`) and line 72 (`#define PICC_WRITE 0xA0`). Also remove the `mfrc522_write_block` prototype on line 76. These are not needed for the diagnostic tool and will be re-added in Phase 2 if needed.

The top of the file should go from:

```c
#ifndef MFRC522_H
#define MFRC522_H

#include <stdint.h>
#define PICC_WRITE 0xA0 // MIFARE Write command
```

to:

```c
#ifndef MFRC522_H
#define MFRC522_H

#include <stdint.h>
```

And remove the second `#define PICC_WRITE 0xA0` on line 72, and the `uint8_t mfrc522_write_block(...)` prototype on line 76.

**Step 2: Add cascade level constants and update UID length**

Replace the PICC commands section (lines 67-72 area) with:

```c
// PICC commands
#define PICC_REQIDL     0x26  // REQA - request idle cards
#define PICC_REQALL     0x52  // WUPA - request all cards
#define PICC_ANTICOLL1  0x93  // Anti-collision/Select CL1
#define PICC_ANTICOLL2  0x95  // Anti-collision/Select CL2
#define PICC_ANTICOLL3  0x97  // Anti-collision/Select CL3
#define PICC_HALT       0x50
#define PICC_CASCADE_TAG 0x88 // Indicates UID not complete, cascade to next level

// Max UID length (4, 7, or 10 bytes depending on chip)
#define MFRC522_UID_MAX 10
```

Note: `PICC_ANTICOLL` (0x93) is renamed to `PICC_ANTICOLL1` for clarity. The old name is removed.

**Step 3: Update function prototypes**

Replace the entire prototype section (from `mfrc522_calculate_crc` through end of file before `#endif`) with:

```c
// Function prototypes
void    mfrc522_init(void);
void    mfrc522_write_reg(uint8_t reg, uint8_t val);
uint8_t mfrc522_read_reg(uint8_t reg);
void    mfrc522_set_bit(uint8_t reg, uint8_t mask);
void    mfrc522_clear_bit(uint8_t reg, uint8_t mask);
void    mfrc522_antenna_on(void);
void    mfrc522_reset(void);
void    mfrc522_calculate_crc(uint8_t *data, uint8_t len, uint8_t *result);
uint8_t mfrc522_request(uint8_t req_mode, uint8_t *tag_type);
uint8_t mfrc522_anticoll(uint8_t cascade_level, uint8_t *uid);
uint8_t mfrc522_select(uint8_t cascade_level, uint8_t *uid, uint8_t *sak);
void    mfrc522_halt(void);
uint8_t mfrc522_to_card(uint8_t command, uint8_t *send_data, uint8_t send_len,
                        uint8_t *back_data, uint8_t *back_len);

#endif
```

Key changes: `mfrc522_anticoll` now takes `cascade_level` parameter. `mfrc522_select` is new. `mfrc522_write_block` is removed.

**Step 4: Build to verify header compiles**

Run: `cd "Projects/RFID Card Reader" && python -m platformio run 2>&1 | tail -5`
Expected: Build errors in mfrc522.c and main.c (they still use old signatures). That's expected — we fix those in Tasks 2 and 3.

**Step 5: Commit**

```bash
git add "Projects/RFID Card Reader/src/mfrc522.h"
git commit -m "refactor(rfid): clean up mfrc522.h for diagnostic analyzer

Remove broken write_block, add cascade level support constants,
update anticoll/select prototypes for multi-level UID resolution."
```

---

### Task 2: Update mfrc522.c — add select, fix anticoll, remove write_block

**Files:**
- Modify: `Projects/RFID Card Reader/src/mfrc522.c`

**Step 1: Update mfrc522_anticoll to accept cascade level**

Change the function signature and replace the hardcoded `PICC_ANTICOLL` with the parameter:

```c
uint8_t mfrc522_anticoll(uint8_t cascade_level, uint8_t *uid) {
    uint8_t status;
    uint8_t i;
    uint8_t uid_check = 0;
    uint8_t back_bits;
    uint8_t send[2];

    mfrc522_write_reg(BitFramingReg, 0x00);
    send[0] = cascade_level;
    send[1] = 0x20;

    status = mfrc522_to_card(PCD_Transceive, send, 2, uid, &back_bits);

    if (status == MI_OK) {
        for (i = 0; i < 4; i++) uid_check ^= uid[i];
        if (uid_check != uid[4]) status = MI_ERR;
    }
    return status;
}
```

Only change: parameter `cascade_level` replaces hardcoded `PICC_ANTICOLL`.

**Step 2: Add mfrc522_select function**

Add this function after `mfrc522_anticoll`:

```c
uint8_t mfrc522_select(uint8_t cascade_level, uint8_t *uid, uint8_t *sak) {
    uint8_t status;
    uint8_t buffer[9];
    uint8_t back_data[3];
    uint8_t back_len;

    // Build SELECT command: [CL, NVB=0x70, UID0, UID1, UID2, UID3, BCC, CRC_L, CRC_H]
    buffer[0] = cascade_level;
    buffer[1] = 0x70;  // NVB: all 40 UID bits complete
    for (uint8_t i = 0; i < 5; i++) {
        buffer[2 + i] = uid[i];  // 4 UID bytes + BCC from anticoll
    }
    mfrc522_calculate_crc(buffer, 7, &buffer[7]);

    mfrc522_write_reg(BitFramingReg, 0x00);  // Full byte framing

    status = mfrc522_to_card(PCD_Transceive, buffer, 9, back_data, &back_len);
    if (status == MI_OK) {
        *sak = back_data[0];
    }
    return status;
}
```

How it works:
- `uid` is the 5-byte buffer from `mfrc522_anticoll` (4 UID bytes + 1 BCC)
- NVB `0x70` means "I'm sending all 40 bits, this is a complete SELECT not partial"
- CRC is computed over the first 7 bytes (CL + NVB + 4 UID + BCC)
- Card responds with SAK + 2-byte CRC (3 bytes total, 24 bits)
- SAK bit 2 (0x04): if set, UID is not complete — cascade to next level

**Step 3: Remove mfrc522_write_block**

Delete the entire `mfrc522_write_block` function (lines 53-71 in the current file). This function has multiple bugs and is not needed for the diagnostic tool.

**Step 4: Build to verify driver compiles**

Run: `cd "Projects/RFID Card Reader" && python -m platformio run 2>&1 | tail -10`
Expected: Build errors only in main.c (still uses old API). The driver itself should compile cleanly.

**Step 5: Commit**

```bash
git add "Projects/RFID Card Reader/src/mfrc522.c"
git commit -m "feat(rfid): add SELECT with cascade support, remove broken write_block

Add mfrc522_select() for ISO 14443A SELECT with SAK capture.
Parameterize mfrc522_anticoll() with cascade level for CL1/CL2/CL3.
Remove buggy mfrc522_write_block() (had buffer aliasing, missing auth)."
```

---

### Task 3: Rewrite main.c — diagnostic scan loop

**Files:**
- Modify: `Projects/RFID Card Reader/src/main.c`

**Step 1: Replace main.c with diagnostic analyzer**

Replace the entire file contents with:

```c
#include <avr/io.h>
#include <util/delay.h>
#include "uart.h"
#include "spi.h"
#include "mfrc522.h"

// Print chip type and cloneability based on SAK byte
static void print_chip_info(uint8_t sak) {
    uart_puts("Chip Type: ");

    if (sak & 0x04) {
        // Cascade bit set — should not reach here after full resolution
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

int main(void) {
    uint8_t status;
    uint8_t atqa[2];
    uint8_t uid_cl1[5];  // 4 UID bytes + BCC from CL1
    uint8_t uid_cl2[5];  // 4 UID bytes + BCC from CL2
    uint8_t full_uid[10];
    uint8_t uid_len;
    uint8_t sak;

    spi_init();
    uart_init(9600);
    mfrc522_init();

    // LED pins: PC0 = detection indicator
    DDRC |= (1 << PC0);

    uart_puts("\r\n--- RFID Tag Analyzer ---\r\n");
    uart_puts("Present a tag to scan...\r\n\r\n");

    while (1) {
        // Step 1: REQA — detect card, get ATQA
        status = mfrc522_request(PICC_REQIDL, atqa);
        if (status != MI_OK) {
            _delay_ms(200);
            continue;
        }

        // Step 2: Anti-collision CL1 — get first 4 UID bytes + BCC
        status = mfrc522_anticoll(PICC_ANTICOLL1, uid_cl1);
        if (status != MI_OK) {
            _delay_ms(200);
            continue;
        }

        // Step 3: SELECT CL1 — activate card, get SAK
        status = mfrc522_select(PICC_ANTICOLL1, uid_cl1, &sak);
        if (status != MI_OK) {
            uart_puts("SELECT CL1 failed\r\n");
            _delay_ms(500);
            continue;
        }

        // Step 4: Check if cascade needed (SAK bit 2)
        uid_len = 4;
        if (sak & 0x04) {
            // CL1 UID starts with cascade tag (0x88) — real UID bytes are [1..3]
            full_uid[0] = uid_cl1[1];
            full_uid[1] = uid_cl1[2];
            full_uid[2] = uid_cl1[3];

            // Anti-collision CL2
            status = mfrc522_anticoll(PICC_ANTICOLL2, uid_cl2);
            if (status != MI_OK) {
                uart_puts("ANTICOLL CL2 failed\r\n");
                _delay_ms(500);
                continue;
            }

            // SELECT CL2
            status = mfrc522_select(PICC_ANTICOLL2, uid_cl2, &sak);
            if (status != MI_OK) {
                uart_puts("SELECT CL2 failed\r\n");
                _delay_ms(500);
                continue;
            }

            full_uid[3] = uid_cl2[0];
            full_uid[4] = uid_cl2[1];
            full_uid[5] = uid_cl2[2];
            full_uid[6] = uid_cl2[3];
            uid_len = 7;

            // Check for triple cascade (10-byte UID, very rare)
            if (sak & 0x04) {
                uart_puts("Triple-size UID (10 bytes) — not supported yet\r\n");
                mfrc522_halt();
                _delay_ms(1000);
                continue;
            }
        } else {
            // Simple 4-byte UID
            for (uint8_t i = 0; i < 4; i++) {
                full_uid[i] = uid_cl1[i];
            }
        }

        // LED blink: tag detected
        PORTC |= (1 << PC0);

        // Print diagnostic report
        uart_puts("=== Tag Detected ===\r\n");

        uart_puts("ATQA: ");
        uart_put_hex(atqa[0]);
        uart_putc(' ');
        uart_put_hex(atqa[1]);
        uart_puts("\r\n");

        uart_puts("UID:  ");
        for (uint8_t i = 0; i < uid_len; i++) {
            uart_put_hex(full_uid[i]);
            if (i < uid_len - 1) uart_putc(':');
        }
        uart_puts(" (");
        uart_putc('0' + uid_len);  // works for 4, 7
        uart_puts(" bytes)\r\n");

        uart_puts("SAK:  0x");
        uart_put_hex(sak);
        uart_puts("\r\n");

        print_chip_info(sak);

        uart_puts("====================\r\n\r\n");

        PORTC &= ~(1 << PC0);

        // Halt card, wait before next scan
        mfrc522_halt();
        _delay_ms(2000);
    }

    return 0;
}
```

Key design decisions:
- `atqa[2]` is passed to `mfrc522_request` which fills both bytes via `mfrc522_to_card`
- Cascade detection: if SAK bit 2 is set after CL1, we run CL2 anticoll+select
- 10-byte UIDs (triple cascade) are detected but not supported — extremely rare
- 2-second delay after each scan prevents rapid re-reading of the same tag
- Only one LED used (PC0) for tag detection — removed PC1 error LED since there's no write operation to fail

**Step 2: Build the complete project**

Run: `cd "Projects/RFID Card Reader" && python -m platformio run`
Expected: Clean build with 0 errors. Warnings are acceptable.

**Step 3: Commit**

```bash
git add "Projects/RFID Card Reader/src/main.c"
git commit -m "feat(rfid): replace cloner with tag diagnostic analyzer

Scan tags and report ATQA, full UID (4/7-byte), SAK, and chip type.
Identifies MIFARE Classic, DESFire, Ultralight, Plus, and others.
Reports whether the tag is cloneable with the RC522 hardware."
```

---

### Task 4: Flash and verify on hardware

**Step 1: Flash the firmware**

Run: `cd "Projects/RFID Card Reader" && python -m platformio run -t upload`
Expected: Successful upload to Arduino Uno.

**Step 2: Open serial monitor**

Run: `cd "Projects/RFID Card Reader" && python -m platformio device monitor`

**Step 3: Verify output**

Present a tag to the reader. Expected output format:

```
--- RFID Tag Analyzer ---
Present a tag to scan...

=== Tag Detected ===
ATQA: XX XX
UID:  XX:XX:XX:XX (4 bytes)
SAK:  0xXX
Chip Type: MIFARE Classic 1K
Cloneable with RC522: YES
====================
```

Or for a SALTO fob (likely):

```
=== Tag Detected ===
ATQA: 03 44
UID:  04:XX:XX:XX:XX:XX:XX (7 bytes)
SAK:  0x20
Chip Type: MIFARE DESFire or MIFARE Plus
ISO 14443-4: YES
Cloneable with RC522: NO
Note: AES-128 encryption. Need PN532 or Proxmark3.
====================
```

This tells you definitively whether your SALTO fobs can be cloned with the RC522.
