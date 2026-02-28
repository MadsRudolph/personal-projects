# Nested Attack Firmware Fixes - Status Document

**Date:** 2026-03-01
**Card:** MIFARE Classic 1K, UID: E413B3DA (SALTO key fob)
**Branch:** main (all work committed directly)

## Current State

The nested attack backend (orchestrator, key_recovery, crypto1, nested.exe) is fully implemented and tested (72 Python tests pass). The GUI has both Darkside and Nested attack buttons. The firmware has been fixed to correctly perform software crypto1 authentication for the nested attack.

**The firmware is ready for testing.** Flash and run a nested attack to see if nonce pairs are collected successfully.

## What Was Done

### 1. Nested Attack Backend (completed in previous session)
- `gui/crypto1.py` — Python Crypto1 LFSR implementation
- `gui/key_recovery.py` — `darkside_recover`, `nested_recover`, `calibrate_nested_distance`, `mfkey32_recover`
- `gui/attack.py` — `AttackOrchestrator` with two-phase nested: calibrate PRNG distance, then attack target sector
- `gui/crapto1/nested.c` + `nested.exe` — C CLI tool for brute-force nested key recovery
- `gui/crapto1/mfkey32.c` + `mfkey32.exe` — C CLI tool for mfkey32 recovery
- Byte-ordering: `_bswap32` bridges wire-order (firmware big-endian hex) to internal-order (Python crypto1 little-endian)

### 2. GUI Additions (commit `77240cf`)
- Added `self._last_tag_uid` to track scanned tag UID
- Added target sector dropdown (sectors 5-15) and "Start Nested Attack" button (teal)
- Added `_start_nested()` callback
- Updated event handlers for `nested_calibrated`, `nested_nonce`, `nested_fail`, `nested_complete`

### 3. Firmware Bug Fixes (3 commits on main)

#### Fix 1: Key A/B auto-detection (`4307609`)
**File:** `src/main.c` — `manual_auth()` and `do_nested_collect()`

**Problem:** `manual_auth` hardcoded `PICC_AUTHKA` (Key A = 0x60). The card's sectors 0-4 use Key B = FFFFFFFFFFFF, not Key A. The dump command (`R`) worked because `try_auth()` tries both Key A and Key B.

**Fix:** Added `auth_type` parameter to `manual_auth()`. `do_nested_collect()` tries Key A (250 retries), then Key B (250 retries) if Key A fails.

#### Fix 2: Crypto1 software authentication (`87e9ab2`)
**File:** `src/main.c` — `manual_auth()` Steps 3-6

Three critical bugs in `manual_auth` prevented software crypto1 auth from ever succeeding:

1. **Wrong `is_encrypted` flag** — `crypto1_word(&cs, nr, 1)` told the LFSR that plaintext `nr` was ciphertext. This feeds wrong bits into the LFSR, producing wrong keystream after the first bit.
   - Fix: Encrypt byte-by-byte with `crypto1_byte(&cs, plain[i], 0)` (plaintext mode)

2. **Missing parity LFSR clocking** — Each byte on the MIFARE wire is 9 bits (8 data + 1 parity). `crypto1_word` only clocked 32 bits for 4 bytes instead of 36. Over 8 bytes, the LFSR was 8 clocks behind.
   - Fix: After each encrypted byte, clock the parity bit: `crypto1_bit(&cs, wire_par, 1)`

3. **Wrong parity pre-check** — `parity_check_ok()` ran the LFSR with zero input, producing a different keystream from the actual encryption. It rejected valid nonces.
   - Fix: Check parity inline during actual encryption, not in a separate dry-run

Also fixed `at` decryption (Step 5) to use byte-by-byte with `crypto1_byte(&cs, at_buf[i], 1)` and clock parity bits for correct post-auth LFSR state.

**Also exported:** `odd_parity8()` from `crypto1.c`/`crypto1.h` (was static, now accessible from main.c).

#### Fix 3: Nested re-auth parity handling (`3963e20`)
**File:** `src/main.c` — `do_nested_collect()` Step 2

**Problem:** The re-auth step (encrypted auth to target sector) had the same bugs as `manual_auth`: wrong `parity_check_ok` and missing parity clocking. Additionally, `NESTED:FAIL:PARITY` and `NESTED:FAIL:TARGET` messages were sent for each round failure, which caused the GUI orchestrator to terminate the entire attack (`_guard.finish()`).

**Fix:**
- Replaced `parity_check_ok` with inline parity check + proper LFSR clocking
- Changed parity/target failures to **silent retries** (parity matches ~6.25% of the time with MFRC522 auto-parity — this is expected, not an error)
- Increased rounds from 5 to 50 (expect ~3 successful nonce pairs per run)
- Only `NESTED:FAIL:AUTH` is still sent (means card lost or wrong key — truly terminal)

## Architecture: How the Nested Attack Works

```
GUI (app.py)
  → _start_nested(sector=5, key=FFFFFFFFFFFF, known_sector=0)
  → AttackOrchestrator.start_nested_attack()

Phase 1: Calibrate PRNG distance
  → Sends "N0004FFFFFFFFFFFF" (known_block=0, calib_block=4, key)
  → Firmware: manual_auth(block 0, key B) → re-auth(block 4) → NESTED:NT:aabb:ccdd
  → Orchestrator collects nonce pairs, calls calibrate_nested_distance()
  → Finds PRNG tick distance between known nonce and encrypted target nonce

Phase 2: Attack target sector
  → Sends "N0014FFFFFFFFFFFF" (known_block=0, target_block=20, key)
  → Firmware collects more nonce pairs from known→target
  → Orchestrator calls nested_recover(uid, distance, nonce_pairs)
  → nested_recover invokes nested.exe subprocess for brute-force key search
  → GUI shows "KEY FOUND: xxxxxxxxxxxx" or "No key found"
```

## Known Limitations / Next Steps

1. **Speed**: Each nested round takes ~5-15 seconds (mostly in manual_auth retry loop). With ~6.25% parity success rate and 50 rounds, a single N command takes 1-5 minutes. This is a fundamental limitation of MFRC522 auto-parity — the MFRC522 doesn't let you control parity bits directly.

2. **Potential optimization**: Try Key B first (since we know it works for this card) to skip the 250 failed Key A retries per round. Or add firmware memory to remember which key type succeeded.

3. **Testing the full flow**: The firmware fixes haven't been tested end-to-end yet. After flashing, run the nested attack and verify:
   - Nonce pairs are collected (GUI shows "Nested (calibrating): N nonce pairs")
   - Calibration succeeds (GUI shows "Nested: calibrated (dist=XXX), attacking...")
   - Attack phase collects more nonces
   - Key recovery succeeds or fails with useful info

4. **If calibration gets 0 nonce pairs**: Increase rounds further (to 100+), or the parity probability might be lower than expected.

5. **If key recovery fails**: May need more nonce pairs. The GUI could send multiple N commands, or the orchestrator could retry automatically.

## Key Files

| File | Purpose |
|------|---------|
| `src/main.c` | Firmware: `manual_auth()`, `do_nested_collect()`, command handlers |
| `src/crypto1.c/h` | Firmware: Crypto1 LFSR, `odd_parity8`, `parity_check_ok` |
| `gui/app.py` | GUI: nested attack button, event handlers |
| `gui/attack.py` | Orchestrator: two-phase nested (calibrate → attack) |
| `gui/key_recovery.py` | Python: `calibrate_nested_distance`, `nested_recover`, `_bswap32` |
| `gui/crypto1.py` | Python: Crypto1 implementation |
| `gui/crapto1/nested.exe` | C: brute-force nested key recovery CLI |
| `gui/tests/test_attack.py` | Tests: orchestrator two-phase flow |
| `gui/tests/test_key_recovery.py` | Tests: calibration, PRNG distance, recovery |

## Byte-Order Convention

- **Wire order (big-endian)**: What the firmware sends in hex (e.g., UID `E413B3DA`, nonces)
- **Internal order (little-endian)**: What Python crypto1 uses internally
- **`_bswap32(x)`**: Converts between the two
- All `key_recovery.py` functions accept wire-order inputs and byte-swap internally
- The C tools (`nested.exe`, `mfkey32.exe`) also expect wire-order inputs
