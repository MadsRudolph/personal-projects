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


def test_parse_dark_uid():
    result = SerialHandler.parse_line("DARK:UID:E413B3DA")
    assert result == {"type": "DARK", "subtype": "UID", "uid": "E413B3DA"}


def test_parse_dark_nt():
    result = SerialHandler.parse_line("DARK:NT:A1B2C3D4")
    assert result == {"type": "DARK", "subtype": "NT", "nt": "A1B2C3D4"}


def test_parse_dark_nack():
    result = SerialHandler.parse_line("DARK:NACK:0102030405060708")
    assert result == {"type": "DARK", "subtype": "NACK", "nr_ar": "0102030405060708"}


def test_parse_dark_timeout():
    result = SerialHandler.parse_line("DARK:TIMEOUT")
    assert result == {"type": "DARK", "subtype": "TIMEOUT"}


def test_parse_dark_done():
    result = SerialHandler.parse_line("DARK:DONE")
    assert result == {"type": "DARK", "subtype": "DONE"}


def test_parse_nested_nt():
    result = SerialHandler.parse_line("NESTED:NT:A1B2C3D4:E5F6A7B8")
    assert result == {
        "type": "NESTED",
        "subtype": "NT",
        "nt_known": "A1B2C3D4",
        "nt_target": "E5F6A7B8",
    }


def test_parse_nested_fail():
    result = SerialHandler.parse_line("NESTED:FAIL:AUTH")
    assert result == {"type": "NESTED", "subtype": "FAIL", "reason": "AUTH"}


def test_parse_nested_done():
    result = SerialHandler.parse_line("NESTED:DONE")
    assert result == {"type": "NESTED", "subtype": "DONE"}


# ── Conversational Nested Protocol ──

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
