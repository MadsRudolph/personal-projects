from crypto1 import Crypto1, prng_successor


def test_prng_successor_single():
    # PRNG successor is deterministic
    x = 0x01020304
    y = prng_successor(x, 1)
    assert isinstance(y, int)
    assert y != x


def test_prng_successor_zero_steps():
    assert prng_successor(0xDEADBEEF, 0) == 0xDEADBEEF


def test_prng_successor_deterministic():
    a = prng_successor(0x11223344, 100)
    b = prng_successor(0x11223344, 100)
    assert a == b


def test_crypto1_init():
    c = Crypto1(bytes.fromhex("FFFFFFFFFFFF"))
    assert c is not None


def test_crypto1_bit_returns_0_or_1():
    c = Crypto1(bytes.fromhex("FFFFFFFFFFFF"))
    bit = c.crypto1_bit(0, 0)
    assert bit in (0, 1)


def test_crypto1_byte():
    c = Crypto1(bytes.fromhex("FFFFFFFFFFFF"))
    ks = c.crypto1_byte(0, 0)
    assert 0 <= ks <= 255


def test_crypto1_word():
    c = Crypto1(bytes.fromhex("FFFFFFFFFFFF"))
    ks = c.crypto1_word(0, 0)
    assert 0 <= ks <= 0xFFFFFFFF


def test_crypto1_deterministic():
    c1 = Crypto1(bytes.fromhex("A0A1A2A3A4A5"))
    c2 = Crypto1(bytes.fromhex("A0A1A2A3A4A5"))
    for _ in range(100):
        assert c1.crypto1_bit(0, 0) == c2.crypto1_bit(0, 0)


def test_crypto1_different_keys_differ():
    c1 = Crypto1(bytes.fromhex("FFFFFFFFFFFF"))
    c2 = Crypto1(bytes.fromhex("A0A1A2A3A4A5"))
    ks1 = c1.crypto1_word(0, 0)
    ks2 = c2.crypto1_word(0, 0)
    assert ks1 != ks2


def test_odd_parity():
    from crypto1 import odd_parity8
    assert odd_parity8(0x00) == 0  # 0 ones = even -> parity bit 0
    assert odd_parity8(0x01) == 1  # 1 one = odd -> parity bit 1
    assert odd_parity8(0xFF) == 0  # 8 ones = even -> parity bit 0
    assert odd_parity8(0x03) == 0  # 2 ones = even -> parity bit 0
