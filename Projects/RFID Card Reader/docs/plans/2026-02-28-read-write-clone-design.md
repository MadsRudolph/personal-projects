# MIFARE Classic Clone (Read/Write) Design

## Goal

Add full card cloning capability: read all sectors from a source MIFARE Classic 1K card, store the dump in the GUI, and write it to a target card.

## Architecture

Firmware-driven approach. Single commands trigger full card operations. Data streams through serial to/from the GUI which stores the complete card image (1024 bytes). Default Key A (FFFFFFFFFFFF) for authentication.

## Firmware Changes

### New MFRC522 Driver Functions (mfrc522.c/h)

1. **`mfrc522_auth(key_type, block, key, uid)`** - Crypto1 authentication via `PCD_MFAuthent`
2. **`mfrc522_read_block(block, buffer)`** - Read 16 bytes from a block (`PICC_READ` 0x30)
3. **`mfrc522_write_block(block, data)`** - Two-phase write: send `PICC_WRITE` (0xA0), wait for ACK, send 16 bytes
4. **`mfrc522_stop_crypto()`** - Clear Crypto1 flag in `Status2Reg` after operations

### New PICC Command Defines

- `PICC_READ  0x30`
- `PICC_WRITE 0xA0`
- `PICC_AUTHKA 0x60` (Auth with Key A)
- `PICC_AUTHKB 0x61` (Auth with Key B)

### New Main Loop Commands

| Command | Action |
|---------|--------|
| `R` | Read/dump entire card (16 sectors, 64 blocks) |
| `W` | Enter write mode, wait for LOAD: lines |
| `W0` | Enter write mode with block 0 write enabled (for Chinese clones) |
| `D` | Done writing (exit write mode) |

### Serial Protocol - Read

Firmware sends after `R` command:
```
DATA:<block_hex>:<32_hex_data_chars>
```
Example: `DATA:00:A1B2C3D4050607080910111213141516`

On completion: `OK:DUMP_COMPLETE`
On auth failure: `ERR:AUTH_FAIL:<sector_hex>`

### Serial Protocol - Write

1. GUI sends `W` (or `W0` for block 0)
2. Firmware responds `OK:WRITE_READY`
3. GUI sends `LOAD:<block_hex>:<32_hex_data_chars>` for each block
4. Firmware responds `OK:WROTE:<block_hex>` or `ERR:WRITE_FAIL:<block_hex>`
5. GUI sends `D` when done
6. Firmware responds `OK:WRITE_DONE`

### Safety Rules

- Block 0 skipped during write unless `W0` command used
- Sector trailers written as-is (preserves source keys/access bits)
- Auth failure on a sector skips that sector, continues with next

## GUI Changes

### New UI Elements

- **Read Card** button (blue) - triggers full dump, shows progress
- **Write Card** button (orange) - writes stored dump to new card
- **Write w/ Block 0** checkbox - enables `W0` for Chinese clones
- **Save Dump** button - save card image to `.bin` file
- **Load Dump** button - load card image from `.bin` file
- **Hex viewer** - tabbed or scrollable view showing all 16 sectors with 4 blocks each, 16 bytes per block as hex

### Data Storage

- `card_data`: `dict[int, bytes]` mapping block number (0-63) to 16-byte data
- Stored in memory, optionally saved/loaded as 1024-byte binary files

### Serial Handler Changes

- Parse `DATA:` lines into card_data dict
- Parse `OK:WROTE:` and `ERR:WRITE_FAIL:` for write progress
- New `send_load_block(block, data)` method to format LOAD: lines
- Handle write mode state (WRITE_READY → sending → WRITE_DONE)

### Progress Feedback

- During read: progress bar or sector counter "Reading sector 5/16..."
- During write: "Writing block 23/64..."
- Color-coded sector status: green=ok, red=failed auth

## MIFARE Classic 1K Structure Reference

- 16 sectors (0-15)
- 4 blocks per sector (0-3)
- 16 bytes per block
- Block 0: manufacturer block (UID, BCC, SAK, ATQA) - read-only on genuine cards
- Block 3 of each sector: sector trailer (Key A [6] + Access Bits [4] + Key B [6])
- Total: 64 blocks, 1024 bytes

## Tech Stack

- Firmware: bare-metal AVR C (ATmega328P)
- GUI: Python 3 + CustomTkinter + pyserial
