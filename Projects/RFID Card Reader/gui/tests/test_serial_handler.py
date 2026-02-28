from serial_handler import SerialHandler
from tag_info import Tag


def test_parse_tag_line():
    result = SerialHandler.parse_line("TAG:0344:04A3B24F01C780:20:7")
    assert isinstance(result, Tag)
    assert result.atqa == "0344"
    assert result.uid == "04A3B24F01C780"
    assert result.sak == 0x20
    assert result.uid_len == 7


def test_parse_tag_4byte():
    result = SerialHandler.parse_line("TAG:0400:A3B24F01:08:4")
    assert isinstance(result, Tag)
    assert result.sak == 0x08
    assert result.uid_len == 4


def test_parse_ok():
    result = SerialHandler.parse_line("OK:Scanning")
    assert result == {"type": "OK", "message": "Scanning"}


def test_parse_err():
    result = SerialHandler.parse_line("ERR:SELECT CL1 failed")
    assert result == {"type": "ERR", "message": "SELECT CL1 failed"}


def test_parse_info():
    result = SerialHandler.parse_line("INFO:Ready")
    assert result == {"type": "INFO", "message": "Ready"}


def test_parse_empty():
    assert SerialHandler.parse_line("") is None


def test_parse_garbage():
    assert SerialHandler.parse_line("random text") is None


def test_parse_human_readable_ignored():
    assert SerialHandler.parse_line("ATQA: 03 44  UID: 04:A3") is None
    assert SerialHandler.parse_line("Chip Type: MIFARE DESFire") is None
    assert SerialHandler.parse_line("=== Tag Detected ===") is None
