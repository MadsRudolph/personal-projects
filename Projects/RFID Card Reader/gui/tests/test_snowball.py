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
