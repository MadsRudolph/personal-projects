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


def test_conv_start_triggers_calibration():
    """After CONV_START, orchestrator starts calibrating (when 2+ known sectors)."""
    serial = FakeSerial()
    orch = SnowballOrchestrator(serial, uid=0xE413B3DA)
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
    """After NA:OK in collecting, orchestrator sends NP to probe target."""
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

    # Simulate auth success then retry
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


# ── Integration: Calibration Flow ──

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
