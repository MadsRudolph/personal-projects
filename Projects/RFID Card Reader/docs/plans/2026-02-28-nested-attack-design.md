# Nested Attack Key Recovery Design

**Goal:** Recover unknown MIFARE Classic sector keys (sectors 5-15) from a SALTO key fob using the nested authentication attack, leveraging the known default key `FFFFFFFFFFFF` from sectors 0-4.

## Background

The MIFARE Classic nested authentication attack exploits the weak PRNG (32-bit LFSR) and the Crypto1 cipher. During nested authentication, the card encrypts the target nonce with the unknown key's initial keystream. Since the PRNG is deterministic, the plaintext nonce is predictable, allowing extraction of 32 bits of keystream from the unknown key. `lfsr_recovery32` then recovers candidate LFSR states, which are rolled back to extract the 48-bit key.

## Architecture

### Phase 1: Calibration

Nested auth between two known sectors (sector 0 -> sector 1, both key `FFFFFFFFFFFF`).

Since both keys are known, we brute-force the PRNG distance `d`:
- For each `d` in 0..65536:
  - `nt_predicted = prng_successor(nt_known, d)`
  - Init crypto1 with known key, feed `uid ^ nt_predicted`
  - Compare first 32 bits of keystream against `nt_target ^ nt_predicted`
- Matching `d` = the PRNG tick distance between nested nonces

This runs in pure Python (~65K crypto1 inits, sub-second).

### Phase 2: Collection

Nested auth from sector 0 (known) to target sector (unknown).

Firmware command: `N<known_block><target_block><key_hex>`

Firmware collects 5 `(nt_known, nt_target_enc)` pairs, where `nt_target_enc` is encrypted with key_B's initial keystream.

### Phase 3: Recovery

Using the calibrated distance `d`:

1. `nt_predicted = prng_successor(nt_known, d)`
2. `ks32 = nt_target_enc ^ nt_predicted` (32 bits of key_B keystream)
3. `lfsr_recovery32(ks32, uid ^ nt_predicted)` -> ~65K candidate LFSR states
4. Roll back each candidate through `uid ^ nt_predicted` to extract 48-bit key
5. Validate each candidate against the remaining 4 nonce pairs
6. Surviving candidate = key_B

### Phase 4: Repeat

Iterate over sectors 5-15. Once any sector key is recovered, it can also be used as a known key for further nested attacks.

## Components

### `crapto1/nested.exe` (New C CLI tool)

Uses existing Proxmark3 crapto1 library (`lfsr_recovery32`, `crypto1_word`, etc.).

**Usage:** `nested.exe <uid> <dist> <nt0_k> <nt0_t> [<nt1_k> <nt1_t> ...]`

- `uid`: 32-bit card UID (hex)
- `dist`: calibrated PRNG distance (decimal)
- `ntN_k`: known-sector nonce (hex)
- `ntN_t`: target-sector encrypted nonce (hex)

**Output:** `Found key: XXXXXXXXXXXX` or `No key found`

**Algorithm:**
1. First pair: compute `nt_pred = prng_successor(nt0_k, dist)`, `ks32 = nt0_t ^ nt_pred`
2. `lfsr_recovery32(ks32, uid ^ nt_pred)` -> candidate list
3. For each candidate: extract 48-bit key by rolling back LFSR
4. For each remaining pair: verify the key produces matching keystream
5. Output first key that passes all validations

### `key_recovery.py` (Modified)

**New functions:**
- `calibrate_nested_distance(uid, nt_known, nt_target, known_key)` -> `int`
  - Brute-forces PRNG distance using known key
  - Returns the distance `d` where keystream matches

- `nested_recover(uid, distance, nonce_pairs)` -> `list[bytes]`
  - Calls `nested.exe` via subprocess
  - Returns list of candidate keys

### `attack.py` (Modified)

**Orchestrator changes:**
- New state: `"nested_calibrating"` for calibration phase
- `start_nested_attack(known_sector, target_sector, known_key)`:
  1. First sends calibration command (sector 0 -> sector 1)
  2. On calibration DONE: compute distance, send attack command
  3. On attack DONE: call `nested_recover()`, report result
- Store `_calibrated_distance` for reuse across sectors
- On `nested_complete`: attempt key recovery and report

## Data Flow

```
GUI: start_nested_attack(known=0, target=5, key=FFFFFFFFFFFF)
  |
  v
Orchestrator: state="nested_calibrating"
  -> firmware: N0004FFFFFFFFFFFF  (sector 0 -> sector 1, calibration)
  <- firmware: NESTED:NT:<nt_k>:<nt_t>  (x5)
  <- firmware: NESTED:DONE
  |
  v
Python: calibrate_nested_distance(uid, pairs, FFFFFFFFFFFF) -> d=160
  |
  v
Orchestrator: state="nested"
  -> firmware: N0014FFFFFFFFFFFF  (sector 0 -> sector 5, block 0x14)
  <- firmware: NESTED:NT:<nt_k>:<nt_t>  (x5)
  <- firmware: NESTED:DONE
  |
  v
Python: nested_recover(uid, d=160, pairs) -> subprocess nested.exe
  -> nested.exe: lfsr_recovery32 + validate
  <- Found key: A1B2C3D4E5F6
  |
  v
GUI: "Key recovered for sector 5: A1B2C3D4E5F6"
```

## Error Handling

- Calibration fails (no distance found): firmware may not support nested auth properly, or card doesn't respond. Report to user.
- No candidates survive validation: distance may vary between calibration and attack. Try distance +/- 1..5 window.
- Firmware NESTED:FAIL: report reason (AUTH, PARITY, TARGET) to user.
- nested.exe timeout: 300s limit (lfsr_recovery32 is fast, but validation of 65K candidates across 4 pairs may take time).

## Testing

- Unit test calibration with known test vectors (key FFFFFFFFFFFF, synthetic nonces)
- Unit test nested.exe with synthetic nonce pairs generated from a known key
- Integration test: full flow from orchestrator through recovery
