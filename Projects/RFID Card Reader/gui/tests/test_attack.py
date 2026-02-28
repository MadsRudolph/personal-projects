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
