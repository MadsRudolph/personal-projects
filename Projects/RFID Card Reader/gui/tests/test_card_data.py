import os
import tempfile
from card_data import CardData


def test_empty_card():
    card = CardData()
    assert card.block_count == 0
    assert not card.has_data


def test_set_and_get_block():
    card = CardData()
    card.set_block(0, "A1B2C3D4050607080910111213141516")
    assert card.get_block(0) == "A1B2C3D4050607080910111213141516"
    assert card.block_count == 1
    assert card.has_data


def test_get_missing_block():
    card = CardData()
    assert card.get_block(5) is None


def test_sector_for_block():
    card = CardData()
    assert card.sector_for_block(0) == 0
    assert card.sector_for_block(3) == 0
    assert card.sector_for_block(4) == 1
    assert card.sector_for_block(63) == 15


def test_is_sector_trailer():
    card = CardData()
    assert card.is_sector_trailer(3)
    assert card.is_sector_trailer(7)
    assert card.is_sector_trailer(63)
    assert not card.is_sector_trailer(0)
    assert not card.is_sector_trailer(4)


def test_clear():
    card = CardData()
    card.set_block(0, "A1B2C3D4050607080910111213141516")
    card.clear()
    assert card.block_count == 0
    assert not card.has_data


def test_save_and_load_bin():
    card = CardData()
    for i in range(64):
        card.set_block(i, f"{i:02X}" * 16)

    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        path = f.name

    try:
        card.save_bin(path)
        assert os.path.getsize(path) == 1024

        card2 = CardData()
        card2.load_bin(path)
        assert card2.block_count == 64
        for i in range(64):
            assert card2.get_block(i) == f"{i:02X}" * 16
    finally:
        os.unlink(path)


def test_blocks_for_write_skips_block0():
    card = CardData()
    for i in range(8):
        card.set_block(i, "AA" * 16)
    blocks = card.blocks_for_write(allow_block0=False)
    assert 0 not in [b for b, _ in blocks]
    assert len(blocks) == 7


def test_blocks_for_write_includes_block0():
    card = CardData()
    for i in range(8):
        card.set_block(i, "AA" * 16)
    blocks = card.blocks_for_write(allow_block0=True)
    assert 0 in [b for b, _ in blocks]
    assert len(blocks) == 8
