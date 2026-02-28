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
