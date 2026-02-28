import queue
from attack import AttackOrchestrator


class FakeSerial:
    def __init__(self):
        self.is_connected = True
        self.commands = []
        self.queue = queue.Queue()
        self.raw_queue = queue.Queue()

    def send_command(self, cmd):
        self.commands.append(cmd)


def test_orchestrator_init():
    serial = FakeSerial()
    orch = AttackOrchestrator(serial)
    assert orch.state == "idle"


def test_orchestrator_start_darkside():
    serial = FakeSerial()
    orch = AttackOrchestrator(serial)
    orch.start_darkside(sector=0)
    assert orch.state == "darkside"
    assert "K00" in serial.commands


def test_orchestrator_start_nested():
    serial = FakeSerial()
    orch = AttackOrchestrator(serial)
    orch.start_nested(
        known_block=0, target_block=0x14,
        known_key=bytes.fromhex("FFFFFFFFFFFF")
    )
    assert orch.state == "nested"
    assert any("N" in cmd for cmd in serial.commands)


def test_orchestrator_stop():
    serial = FakeSerial()
    orch = AttackOrchestrator(serial)
    orch.start_darkside(sector=0)
    orch.stop()
    assert orch.state == "idle"
    assert "X" in serial.commands


def test_darkside_nt_nack_pairing():
    """NT messages are correctly paired with subsequent NACK messages."""
    serial = FakeSerial()
    orch = AttackOrchestrator(serial)
    orch.start_darkside(sector=0)

    # Simulate: UID → NT → NACK sequence
    orch.feed({"type": "DARK", "subtype": "UID", "uid": "E413B3DA"})
    orch.feed({"type": "DARK", "subtype": "NT", "nt": "A9770B9F"})
    orch.feed({"type": "DARK", "subtype": "NACK", "nr_ar": "29012B032D052F07"})

    assert len(orch._nack_data) == 1
    assert orch._nack_data[0]["nt"] == 0xA9770B9F
    assert orch._nack_data[0]["nr_ar"] == bytes.fromhex("29012B032D052F07")
    assert orch._last_nt is None  # consumed after NACK


def test_darkside_nt_timeout_clears():
    """TIMEOUT between NT and NACK clears the pending NT."""
    serial = FakeSerial()
    orch = AttackOrchestrator(serial)
    orch.start_darkside(sector=0)

    orch.feed({"type": "DARK", "subtype": "NT", "nt": "AABBCCDD"})
    orch.feed({"type": "DARK", "subtype": "TIMEOUT"})

    assert orch._last_nt is None
    assert len(orch._nack_data) == 0


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


def test_nested_calibration_then_attack():
    """Orchestrator runs calibration phase then transitions to attack phase."""
    serial = FakeSerial()
    orch = AttackOrchestrator(serial)
    orch._uid = 0xE413B3DA

    known_key = bytes.fromhex("FFFFFFFFFFFF")
    orch.start_nested_attack(
        known_sector=0,
        target_sector=5,
        known_key=known_key,
    )

    # Should be in calibration phase
    assert orch.state == "nested_calibrating"
    # Should have sent nested command for calibration (sector 0 block -> sector 1 block 04)
    assert any("N" in cmd and "04" in cmd for cmd in serial.commands)

    # Feed valid calibration nonce pair
    uid_wire = 0xE413B3DA
    nt_known_wire = 0x01020304
    dist = 160
    nt_enc_wire = _make_calibration_nonce(uid_wire, nt_known_wire, known_key, dist)

    orch.feed({"type": "NESTED", "subtype": "NT",
               "nt_known": f"{nt_known_wire:08X}",
               "nt_target": f"{nt_enc_wire:08X}"})
    orch.feed({"type": "NESTED", "subtype": "DONE"})

    # Should transition to attack phase
    assert orch.state == "nested"
    assert orch._calibrated_distance == dist
    # Should have sent second nested command for target sector (block 0x14 = 20)
    assert len(serial.commands) >= 2


def test_nested_calibration_fails_with_bad_data():
    """Orchestrator goes idle when calibration produces no valid distance."""
    serial = FakeSerial()
    orch = AttackOrchestrator(serial)
    orch._uid = 0xE413B3DA

    orch.start_nested_attack(
        known_sector=0,
        target_sector=5,
        known_key=bytes.fromhex("FFFFFFFFFFFF"),
    )

    # Feed garbage nonce pair that won't calibrate
    orch.feed({"type": "NESTED", "subtype": "NT",
               "nt_known": "01020304", "nt_target": "AABBCCDD"})
    orch.feed({"type": "NESTED", "subtype": "DONE"})

    # Should fail gracefully
    assert orch.state == "idle"
    result = orch.result_queue.get(timeout=1)
    # Skip the nonce event
    if result.get("event") == "nested_nonce":
        result = orch.result_queue.get(timeout=1)
    assert result["event"] == "nested_fail"
    assert result["reason"] == "calibration_failed"


def test_nested_attack_stores_distance():
    """Orchestrator stores calibrated distance and uses it for recovery."""
    serial = FakeSerial()
    orch = AttackOrchestrator(serial)
    orch._uid = 0xE413B3DA

    known_key = bytes.fromhex("FFFFFFFFFFFF")
    orch.start_nested_attack(
        known_sector=0,
        target_sector=5,
        known_key=known_key,
    )

    # Feed valid calibration data
    uid_wire = 0xE413B3DA
    nt_known_wire = 0x01020304
    dist = 160
    nt_enc_wire = _make_calibration_nonce(uid_wire, nt_known_wire, known_key, dist)

    orch.feed({"type": "NESTED", "subtype": "NT",
               "nt_known": f"{nt_known_wire:08X}",
               "nt_target": f"{nt_enc_wire:08X}"})
    orch.feed({"type": "NESTED", "subtype": "DONE"})

    assert orch._calibrated_distance == dist
    assert orch.state == "nested"
