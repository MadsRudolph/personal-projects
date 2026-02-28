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


def test_parse_data_line():
    result = SerialHandler.parse_line("DATA:00:A1B2C3D4050607080910111213141516")
    assert result == {
        "type": "DATA",
        "block": 0,
        "data": "A1B2C3D4050607080910111213141516",
    }


def test_parse_data_line_high_block():
    result = SerialHandler.parse_line("DATA:3F:00112233445566778899AABBCCDDEEFF")
    assert result == {
        "type": "DATA",
        "block": 0x3F,
        "data": "00112233445566778899AABBCCDDEEFF",
    }


def test_parse_ok_dump_complete():
    result = SerialHandler.parse_line("OK:DUMP_COMPLETE")
    assert result == {"type": "OK", "message": "DUMP_COMPLETE"}


def test_parse_ok_write_ready():
    result = SerialHandler.parse_line("OK:WRITE_READY")
    assert result == {"type": "OK", "message": "WRITE_READY"}


def test_parse_ok_wrote():
    result = SerialHandler.parse_line("OK:WROTE:0A")
    assert result == {"type": "OK", "message": "WROTE:0A"}


def test_parse_err_auth_fail():
    result = SerialHandler.parse_line("ERR:AUTH_FAIL:03")
    assert result == {"type": "ERR", "message": "AUTH_FAIL:03"}


def test_parse_ok_format_progress():
    result = SerialHandler.parse_line("OK:FORMAT:05")
    assert result == {"type": "OK", "message": "FORMAT:05"}


def test_parse_ok_format_complete():
    result = SerialHandler.parse_line("OK:FORMAT_COMPLETE")
    assert result == {"type": "OK", "message": "FORMAT_COMPLETE"}


def test_parse_err_format_auth():
    result = SerialHandler.parse_line("ERR:FORMAT_AUTH:03")
    assert result == {"type": "ERR", "message": "FORMAT_AUTH:03"}


def test_parse_err_format_write():
    result = SerialHandler.parse_line("ERR:FORMAT_WRITE:0A")
    assert result == {"type": "ERR", "message": "FORMAT_WRITE:0A"}
