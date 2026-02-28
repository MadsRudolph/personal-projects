from datetime import datetime
from tag_info import Tag

def test_chip_type_classic_1k():
    tag = Tag(atqa="0400", uid="A3B24F01", sak=0x08, uid_len=4, timestamp=datetime.now())
    assert tag.chip_type == "MIFARE Classic 1K"
    assert tag.cloneable == "YES"

def test_chip_type_desfire():
    tag = Tag(atqa="0344", uid="04A3B24F01C780", sak=0x20, uid_len=7, timestamp=datetime.now())
    assert tag.chip_type == "MIFARE DESFire or MIFARE Plus"
    assert tag.cloneable == "NO"

def test_chip_type_unknown():
    tag = Tag(atqa="0000", uid="AABBCCDD", sak=0xFF, uid_len=4, timestamp=datetime.now())
    assert "Unknown" in tag.chip_type
    assert tag.cloneable == "UNKNOWN"

def test_uid_formatted_4byte():
    tag = Tag(atqa="0400", uid="A3B24F01", sak=0x08, uid_len=4, timestamp=datetime.now())
    assert tag.uid_formatted == "A3:B2:4F:01"

def test_uid_formatted_7byte():
    tag = Tag(atqa="0344", uid="04A3B24F01C780", sak=0x20, uid_len=7, timestamp=datetime.now())
    assert tag.uid_formatted == "04:A3:B2:4F:01:C7:80"

def test_chip_type_ultralight():
    tag = Tag(atqa="4400", uid="01020304", sak=0x00, uid_len=4, timestamp=datetime.now())
    assert tag.chip_type == "MIFARE Ultralight or NTAG"
    assert tag.cloneable == "PARTIAL"
