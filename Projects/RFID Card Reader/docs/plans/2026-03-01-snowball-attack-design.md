# Snowball Attack: Adaptive Feedback-Driven Key Recovery

**Date:** 2026-03-01
**Status:** PRD - Ready for Implementation
**Card:** MIFARE Classic 1K (SALTO key fob, UID: E413B3DA)
**Platform:** ATmega328P + MFRC522 + Python GUI

## Problem Statement

The current nested attack is slow, manual, and single-target:

1. **Slow** - Each `N` command runs 50 blind rounds. Most fail due to MFRC522 auto-parity (~6.25% success). The firmware wastes 250 retries on Key A before trying Key B. A single sector takes 1-5 minutes.
2. **Manual** - User must manually trigger calibration, wait, then trigger attack, then repeat for each sector. Cracking all unknown sectors requires 10+ manual interventions.
3. **Dumb** - The firmware learns nothing between rounds. It doesn't remember which key type works, doesn't know which sectors are already cracked, and can't use newly discovered keys as stepping stones.

## Solution: Conversational Protocol + Snowball Orchestrator

Replace the batch `N` command with a **conversational micro-command protocol** where the GUI sends individual operations and the firmware executes them one at a time. The GUI runs a **Snowball Orchestrator** that autonomously cascades through all 16 sectors, using each cracked key to attack the next.

### Core Idea

```
Current:  GUI --"N0014FFFFFFFFFFFF"--> FW (runs 50 blind rounds) --> GUI
Proposed: GUI --"NA:00:FFFFFFFFFFFF:B"--> FW --"AUTH_OK"--> GUI
          GUI --"NP:14"--> FW --"NT:aabb:ccdd"--> GUI
          GUI --"NP:14"--> FW --"RETRY"--> GUI
          GUI --"NP:18"--> FW --"NT:eeff:0011"--> GUI  (switch target mid-session!)
          GUI --"NH"--> FW --"HALTED"--> GUI
```

The GUI decides **what to do next** based on what it's learned so far.

## Requirements

### Firmware: Conversational Nested Protocol

Replace the monolithic `N` command with four micro-commands that operate on a **persistent crypto session**:

| Command | Format | Response | Description |
|---------|--------|----------|-------------|
| `NA` | `NA:<block_hex>:<key_hex>:<A\|B>` | `NA:OK` or `NA:FAIL` | Authenticate to a sector using software crypto1. Establishes encrypted session. Key type (A/B) is explicit - no guessing. |
| `NP` | `NP:<target_block_hex>` | `NP:NT:<nt_known_hex>:<nt_target_hex>` or `NP:RETRY` | Probe a target block. Sends encrypted AUTH for target, returns nonce pair if parity matches, `RETRY` if not. Does NOT halt the card - session stays alive for another probe. |
| `NH` | `NH` | `NH:OK` | Halt card, end crypto session. Required before starting a new `NA`. |
| `NX` | `NX` | `NX:OK` | Abort everything, reset to idle. Emergency stop. |

**Key firmware changes:**
- `manual_auth()` stores crypto state persistently (not on stack)
- After `NA`, card stays in encrypted mode until `NH` or `NX`
- `NP` re-uses the existing crypto state for each probe
- No fixed round count - GUI controls how many probes to run
- Key type is sent explicitly by GUI (no 250-retry Key A/B guessing)

**Firmware state machine:**
```
IDLE --NA--> AUTHED --NP--> AUTHED (loop)
                    --NH--> IDLE
                    --NX--> IDLE
IDLE --NX--> IDLE (safe no-op)
```

### GUI: Snowball Orchestrator

A new `SnowballOrchestrator` class replaces `AttackOrchestrator` for the autonomous attack mode. It implements a state machine that:

1. **Bootstraps** - Starts with one known key (default FFFFFFFFFFFF on sector 0)
2. **Calibrates** - Authenticates to a known sector, probes an adjacent known sector to measure PRNG distance
3. **Attacks** - Uses the calibrated distance to attack the nearest unknown sector
4. **Recovers** - Runs `nested.exe` on collected nonce pairs to recover the key
5. **Snowballs** - Adds the recovered key to its known-key map, picks the next target, repeats from step 2
6. **Completes** - Stops when all 16 sectors are cracked or no more attack paths exist

**State machine:**
```
IDLE --> CALIBRATING --> COLLECTING --> RECOVERING --> IDLE (sector done)
                                                  --> CALIBRATING (snowball to next)
     --> FAILED (terminal - card lost, no attack paths)
```

**Targeting strategy:**
- Maintain a `known_keys: dict[int, tuple[bytes, str]]` map (sector -> (key, "A"|"B"))
- After cracking sector N, try sector N+1 first (adjacent sectors often share key patterns)
- If a target fails after max retries, skip it and try the next unknown sector
- Use the known sector closest to the target for authentication (minimizes PRNG distance variance)

**Nonce collection strategy:**
- Collect nonces one at a time via `NP` commands
- After each successful nonce pair, check if we have enough for recovery (minimum 2-3 pairs)
- After collecting enough, attempt early recovery - if it works, move on immediately
- If early recovery fails, collect more (up to configurable max, default 10)
- If `NP:RETRY` received (parity mismatch), immediately send another `NP` - no wasted time

**Speed optimizations from feedback loop:**
- GUI sends key type explicitly (no 250 failed Key A retries)
- GUI can re-auth immediately after card is lost (no waiting for 50 rounds to finish)
- GUI can switch targets mid-session (if sector 5 is hard to crack, try sector 6 instead)
- GUI can try early recovery with just 2 nonce pairs, saving time when it works

### GUI: Live Dashboard

Replace the attacks page with a **real-time card map** showing sector-by-sector status:

```
+--[ MIFARE Classic 1K - E4:13:B3:DA ]--+
|                                         |
|  Sec  Key A         Key B       Status  |
|  00   FFFFFFFFFFFF  FFFFFFFFFFFF  [OK]  |
|  01   A0B1C2D3E4F5  ????????????  [A ]  |
|  02   ????????????  ????????????  [..]  |
|  03   ????????????  ????????????  [..]  |
|  04   FFFFFFFFFFFF  FFFFFFFFFFFF  [OK]  |
|  05   >>attacking<< ????????????  [>>]  |  <-- animated
|  06   ????????????  ????????????  [..]  |
|  ...                                    |
|  15   ????????????  ????????????  [..]  |
|                                         |
|  Progress: 3/16 sectors  |  Elapsed: 2m |
|  Phase: Collecting (sector 5, 2 nonces) |
|  PRNG Distance: 187 ticks               |
|  Last key found: 01 - A0B1C2D3E4F5      |
+-----------------------------------------+
```

**Status indicators per sector:**
- `[OK]` - Both keys known (green)
- `[A ]` or `[ B]` - One key known (yellow)
- `[>>]` - Currently attacking (animated/pulsing)
- `[--]` - Attack failed, skipped (red)
- `[..]` - Unknown, queued (gray)

**Live stats panel:**
- Sectors cracked: N/16
- Current phase: Calibrating / Collecting / Recovering / Idle
- Nonce pairs collected for current target
- PRNG distance (from calibration)
- Elapsed time
- Estimated remaining (based on average time per sector)
- Last recovered key

**Controls:**
- One big "Start Snowball Attack" button
- Abort button
- Optional: priority selector to target a specific sector first

### Serial Protocol Changes

**Parser additions** (`serial_handler.py`):
- Parse `NA:OK`, `NA:FAIL` responses
- Parse `NP:NT:<hex>:<hex>` and `NP:RETRY` responses
- Parse `NH:OK`, `NX:OK` responses

**Wire format:** All commands/responses are ASCII over 9600 baud UART, newline-terminated (`\r\n`), matching existing protocol conventions.

## Architecture

```
+------------------+     serial 9600      +------------------+
|   ATmega328P     |<-------------------->|   Python GUI     |
|   (firmware)     |   NA/NP/NH/NX cmds   |   (app.py)       |
|                  |   responses          |                  |
|  crypto1_state   |                      | SnowballOrch.    |
|  (persistent)    |                      |  known_keys{}    |
|                  |                      |  target_queue    |
|  manual_auth()   |                      |  nonce_pairs[]   |
|  probe_target()  |                      |                  |
|  halt_card()     |                      | key_recovery.py  |
+------------------+                      |  nested.exe      |
                                          |  calibrate()     |
                                          +------------------+
```

**Data flow for one sector crack:**
```
1. GUI: NA:00:FFFFFFFFFFFF:B     (auth sector 0, key B)
2. FW:  NA:OK
3. GUI: NP:04                    (calibrate: probe block 4, known sector 1)
4. FW:  NP:NT:aabbccdd:eeff0011  (nonce pair)
5. GUI: NH                       (halt, compute distance)
6. GUI: [calibrate_nested_distance() -> distance=187]
7. GUI: NA:00:FFFFFFFFFFFF:B     (re-auth sector 0)
8. FW:  NA:OK
9. GUI: NP:14                    (attack: probe block 20, unknown sector 5)
10. FW: NP:RETRY                 (parity mismatch - expected ~94% of time)
11. GUI: NP:14                   (try again immediately)
12. FW: NP:NT:11223344:55667788  (success!)
13. GUI: NP:14                   (collect more)
    ... (repeat until enough nonces)
14. GUI: NH                      (halt, run recovery)
15. GUI: [nested.exe -> "Found key: A0B1C2D3E4F5"]
16. GUI: [add to known_keys, pick next target, goto step 1]
```

## Detailed Component Specifications

### Firmware: State Variables

```c
// Persistent nested session state (module-level, not stack)
static uint8_t  nested_mode = 0;           // 0=idle, 1=authed
static crypto1_state nested_cs;             // LFSR state after auth
static uint8_t  nested_uid[4];              // UID from last auth
static uint8_t  nested_nt_known[4];         // nonce from last auth
static uint8_t  nested_auth_block;          // block we're authed to
```

### Firmware: Command Handlers

**`cmd_na(block, key, key_type)`** - Authenticate
- If `nested_mode == 1`, halt first (auto-cleanup)
- Call `manual_auth(block, key, uid, nt, &cs, key_type, 250)`
- On success: copy state to persistent vars, set `nested_mode = 1`, reply `NA:OK`
- On fail: reply `NA:FAIL`

**`cmd_np(target_block)`** - Probe
- Requires `nested_mode == 1`
- Build encrypted AUTH command using persistent `nested_cs`
- Check parity inline (same as current `do_nested_collect` step 2)
- If parity fails: reply `NP:RETRY`, do NOT halt (re-auth needed because crypto state is consumed)
- If parity ok and target responds: reply `NP:NT:<nt_known_hex>:<nt_target_hex>`, halt card
- **Important:** After each NP (success or fail), the crypto session is consumed. GUI must send `NA` again before next `NP`.

**`cmd_nh()`** - Halt
- `mfrc522_halt()`, set `nested_mode = 0`
- Reply `NH:OK`

**`cmd_nx()`** - Abort
- Halt card, reset all nested state, return to `MODE_IDLE`
- Reply `NX:OK`

### Firmware: Main Loop Integration

```c
// In the main while(1) loop, after existing command parsing:
if (scan_mode == MODE_NESTED_CONV) {
    // No automatic rounds - just wait for commands
    if (uart_available()) {
        // Read and parse NA/NP/NH/NX commands
        // Execute corresponding handler
        // Reply on UART
    }
    _delay_ms(1);
    continue;
}
```

The key difference from the old `MODE_NESTED`: no automatic `do_nested_collect()` calls. The firmware just waits for commands.

### GUI: SnowballOrchestrator Class

```python
class SnowballOrchestrator:
    """Autonomous cascading key recovery for all card sectors."""

    def __init__(self, serial_handler, uid: int):
        self.serial = serial_handler
        self.uid = uid
        self.state = "idle"  # idle|calibrating|collecting|recovering|done|failed
        self.known_keys: dict[int, tuple[bytes, str]] = {}  # sector -> (key, "A"|"B")
        self.target_queue: list[int] = []      # sectors to attack, ordered
        self.current_target: int | None = None
        self.current_source: int | None = None  # known sector used for auth
        self.nonce_pairs: list[tuple[int, int]] = []
        self.calibrated_distance: int | None = None
        self.result_queue = queue.Queue()       # events for GUI
        self.stats = SnowballStats()

    def start(self, seed_sector: int, seed_key: bytes, seed_key_type: str):
        """Begin snowball from a known key."""

    def feed(self, msg: dict):
        """Process firmware response, advance state machine."""

    def _pick_next_target(self) -> int | None:
        """Choose next sector to attack based on proximity to known sectors."""

    def _pick_best_source(self, target: int) -> int:
        """Choose known sector closest to target for auth."""

    def _begin_calibration(self):
        """Auth to source sector, probe adjacent known sector."""

    def _begin_collection(self):
        """Auth to source sector, probe target sector."""

    def _attempt_recovery(self):
        """Run nested.exe on collected nonces."""

    def _advance(self):
        """Called after each firmware response to drive the state machine."""
```

### GUI: SnowballStats

```python
class SnowballStats:
    """Track timing and progress for the live dashboard."""
    start_time: float
    sectors_cracked: int
    sectors_failed: int
    total_nonces_collected: int
    total_retries: int
    current_phase: str
    current_nonce_count: int
    last_key_found: str | None
    per_sector_times: list[float]
```

### GUI: Dashboard Widget

A `SectorMapWidget` (CustomTkinter frame) that renders the 16-sector card state:
- Uses a grid of colored labels/frames, one per sector
- Updates in real-time as `SnowballOrchestrator` emits events
- Shows the active sector with a highlighted/pulsing border
- Stats panel below the grid with live counters

### GUI: Event Flow

The `SnowballOrchestrator` emits events to the GUI via `result_queue`:

| Event | Data | GUI Action |
|-------|------|------------|
| `snowball_started` | seed sector, total unknown | Show "Snowball attack started" |
| `sector_calibrating` | source, target, distance | Update status to "Calibrating" |
| `sector_collecting` | target, nonce_count | Update nonce counter |
| `sector_recovering` | target, nonce_count | Update status to "Recovering..." |
| `sector_cracked` | sector, key, key_type, time_taken | Mark sector green, update stats |
| `sector_failed` | sector, reason | Mark sector red, move to next |
| `snowball_complete` | total_cracked, total_time, keys | Show final results |
| `snowball_failed` | reason | Show error |

## Backward Compatibility

- The old `N` command and `AttackOrchestrator` remain functional (not removed)
- New commands (`NA`, `NP`, `NH`, `NX`) are additive
- The existing Attacks page keeps the single-sector Darkside and Nested buttons
- The Snowball Attack is a new button/page alongside existing attacks
- Existing tests remain unchanged; new tests cover the snowball flow

## Acceptance Criteria

1. **One-button operation**: User presses "Start Snowball Attack", system autonomously cracks all accessible sectors
2. **Progressive key cascade**: Each recovered key is used to attack additional sectors
3. **Live dashboard**: Real-time sector map with status colors, nonce counts, timing stats
4. **Speed improvement**: At least 2x faster than manual sector-by-sector attack (no Key A/B guessing, no wasted batch rounds, early recovery attempts)
5. **Resilience**: Handles card removal/re-placement, parity failures, recovery failures gracefully
6. **Abort**: User can stop at any time, keeping all keys recovered so far

## Implementation Scope

### Firmware Changes (src/main.c, src/crypto1.c)
- Add `MODE_NESTED_CONV` mode
- Add persistent crypto session state variables
- Add `cmd_na()`, `cmd_np()`, `cmd_nh()`, `cmd_nx()` handlers
- Add command parser for `NA:`, `NP:`, `NH:`, `NX:` in the main loop
- Keep existing `MODE_NESTED` and `do_nested_collect()` for backward compat

### GUI Changes
- `gui/snowball.py` - New `SnowballOrchestrator` and `SnowballStats` classes
- `gui/serial_handler.py` - Parse new `NA:`, `NP:`, `NH:`, `NX:` responses
- `gui/app.py` - Add snowball dashboard widget, wire up button and event handlers
- `gui/key_recovery.py` - No changes (reuses `calibrate_nested_distance`, `nested_recover`)

### Tests
- `gui/tests/test_snowball.py` - Orchestrator state machine, targeting, cascading
- Firmware testing on hardware (flash and run against SALTO card)

## Open Questions

1. **Card removal handling**: If the card is removed mid-session, should the orchestrator auto-retry when it's placed back, or require user intervention? (Recommend: auto-retry with backoff)
2. **Key B vs Key A**: Should we always try both key types when validating a recovered key? (Recommend: yes, store whichever works)
3. **Multiple PRNG distances**: Should we re-calibrate for each target sector or cache the distance? (Recommend: re-calibrate each time since distance can vary slightly between sessions)
