# Tag Diagnostic Analyzer Design

## Problem

The card reader project currently implements MIFARE Classic read/write logic, but the target fobs (SALTO) likely use MIFARE DESFire with AES-128 encryption. The MFRC522 hardware cannot perform DESFire cryptographic handshakes. Before investing in write functionality, we need to identify what chip technology is inside the fob.

### Why the current write code fails

Beyond the SALTO/DESFire issue, the existing `mfrc522_write_block()` has implementation bugs:
- Missing SELECT command after anti-collision (card not in active state)
- Missing MIFARE authentication step
- Send/receive buffer aliasing (`cmd_buffer` used for both)
- `&status` passed as `back_len` parameter (variable aliasing)
- Duplicate `#define PICC_WRITE` in header

These bugs would prevent writing even to compatible MIFARE Classic cards.

## Solution: Phase 1 Diagnostic Tool

Build a "Tag Info" analyzer that identifies chip type before attempting any write operations.

### New driver functions (mfrc522.c/h)

**`mfrc522_select(uint8_t *uid, uint8_t *sak)`**
- Sends ISO 14443A SELECT CL1: `[0x93, 0x70, UID0, UID1, UID2, UID3, BCC, CRC_L, CRC_H]`
- Captures SAK byte from response (key diagnostic value)
- Handles cascade: if SAK bit 2 is set, UID is incomplete and CL2/CL3 needed
- Required for any post-anticollision communication

**Cascade level support**
- CL1: `0x93` - first 4 bytes (or cascade tag 0x88 + 3 bytes)
- CL2: `0x95` - next 4 bytes for 7-byte UIDs
- CL3: `0x97` - final 4 bytes for 10-byte UIDs
- DESFire typically uses 7-byte UIDs (CL1 + CL2)

**ATQA capture enhancement**
- `mfrc522_request()` already returns ATQA, but only tag_type[0] is used
- Preserve both bytes for diagnostic output

### Main application changes (main.c)

Replace cloner logic with diagnostic scan loop:

1. REQA (0x26) -> capture 2-byte ATQA
2. ANTICOLL CL1 -> capture first 4 UID bytes
3. SELECT CL1 -> capture SAK
4. If SAK cascade bit set -> ANTICOLL CL2 -> SELECT CL2 (7-byte UID)
5. Print diagnostic report over UART

### Diagnostic output format

```
--- RFID Tag Analyzer ---
Scanning...

Tag Detected!
ATQA: 03 44
UID:  04:A3:B2:4F:01:C7:80 (7 bytes)
SAK:  20

Chip Type: MIFARE DESFire EV1/EV2
ISO 14443-4 compliant: YES
Cloneable with RC522: NO
Note: DESFire uses AES-128 encryption. Consider PN532 or Proxmark3.
```

### SAK interpretation table

| SAK  | Chip Type              | RC522 Cloneable |
|------|------------------------|-----------------|
| 0x08 | MIFARE Classic 1K      | YES             |
| 0x18 | MIFARE Classic 4K      | YES             |
| 0x09 | MIFARE Mini            | YES             |
| 0x20 | MIFARE DESFire / Plus  | NO              |
| 0x00 | MIFARE Ultralight      | PARTIAL         |
| 0x01 | TNP3xxx (NFC)          | NO              |

### Files changed

- `src/mfrc522.c` - Add `mfrc522_select()`, fix ATQA handling
- `src/mfrc522.h` - Add SELECT/cascade constants, fix duplicate define, add select prototype
- `src/main.c` - Replace cloner with diagnostic loop

### What we keep

- SPI driver (unchanged)
- UART driver (unchanged)
- MFRC522 init, register access, request, anticoll, halt, CRC functions
- LED feedback for tag detection

### What we remove (for now)

- `mfrc522_write_block()` - bring back in Phase 2 if SAK confirms MIFARE Classic
- Cloner mode logic in main.c

## Phase 2 (future, conditional)

If diagnostic shows MIFARE Classic (SAK 0x08/0x18):
- Re-implement write with proper SELECT + AUTH flow
- Add `mfrc522_auth()` for MIFARE Crypto1
- Add Gen1A backdoor support for magic cards

If diagnostic shows DESFire (SAK 0x20):
- Document finding
- Evaluate hardware upgrade (PN532, Proxmark3)
- Potentially implement ISO 14443-4 protocol layer for basic DESFire communication (read-only info)
