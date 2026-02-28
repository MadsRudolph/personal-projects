# Darkside Key Recovery via mfkey32 + crapto1

**Goal:** Implement end-to-end darkside key recovery using the crapto1 C library, turning 2+ NACK events into a recovered 48-bit MIFARE Classic key.

## Algorithm (mfkey32)

Each NACK event provides: `uid`, `nt` (plaintext nonce), `nr_enc` (bytes 0-3 of fake response), `ar_enc` (bytes 4-7 of fake response).

Given two NACK events (subscript 0, 1):

1. `ks2 = ar0_enc ^ prng_successor(nt0, 64)` — extract 32 bits of keystream
2. `lfsr_recovery32(ks2, 0)` — returns ~65536 candidate LFSR states
3. For each candidate: roll back through `nr0_enc` (encrypted) and `uid ^ nt0` (plain) to extract the 48-bit key
4. Validate: forward the LFSR through `uid ^ nt1`, `nr1_enc`, check if `ar1_enc == crypto1_word(t, 0, 0) ^ prng_successor(nt1, 64)`
5. Exactly 1 match = recovered key

## Components

### 1. crapto1 C library + mfkey32 CLI tool

Add crapto1 source files to `gui/crapto1/`:
- `crapto1.c` / `crapto1.h` — LFSR recovery functions
- `crypto1.c` / `crypto1.h` — Crypto1 cipher implementation
- `parity.h` — parity utilities
- `mfkey32.c` — CLI wrapper: `mfkey32 <uid> <nt0> <nr0> <ar0> <nt1> <nr1> <ar1>` -> prints key

Build: `gcc -O2 -o mfkey32 mfkey32.c crapto1.c crypto1.c`

### 2. Python key_recovery.py changes

`darkside_recover(uid, nack_data)`:
- Takes list of `{"nt": int, "nr_ar": bytes}` dicts
- Splits each nr_ar into nr (bytes 0-3) and ar (bytes 4-7)
- Tries all pairs of NACK events
- Calls `mfkey32` CLI via subprocess
- Parses output for recovered key
- Returns list of candidate keys

### 3. Python attack.py changes

- After collecting 2+ NACKs, trigger key recovery immediately
- On success, report recovered key to GUI
- On failure with 2 NACKs, continue collecting more
- Remove/increase 30s timeout for darkside attacks

### 4. Firmware changes

Minimal — current protocol already provides needed data:
- `DARK:NT:<nt_hex>` — plaintext nonce
- `DARK:NACK:<nr_ar_hex>` — the 8-byte fake response we sent

Only change: ensure robust NT-NACK pairing in the serial stream (already works via sequential line output).

## Data Flow

```
Card → MFRC522 → AVR firmware → Serial → Python parser
                                            ↓
                                     AttackOrchestrator
                                     collects NACK events
                                            ↓
                                     darkside_recover()
                                     pairs NACKs, calls mfkey32
                                            ↓
                                     mfkey32 CLI (crapto1)
                                     lfsr_recovery32 + rollback
                                            ↓
                                     Recovered 48-bit key
                                            ↓
                                     GUI displays result
```

## Validation

Test with the existing log data (card UID `E413B3DA`, 5 NACKs collected):
1. NACK 0: NT=unknown (need to pair from log), NR_AR=`29012B032D052F07`
2. NACK 1: NT=unknown, NR_AR=`D801DA03DC05DE07`
3. etc.

Expected: mfkey32 recovers the key for sector 5+ of this card.
