"""
Crypto1 stream cipher and MIFARE Classic PRNG.

Pure Python implementation matching the AVR firmware version.
Based on the public crypto1 analysis (Garcia et al., 2008).
"""


def odd_parity8(x: int) -> int:
    """Return 1 if x has an odd number of set bits, 0 otherwise."""
    x ^= x >> 4
    x ^= x >> 2
    x ^= x >> 1
    return x & 1


def parity32(x: int) -> int:
    x ^= x >> 16
    x ^= x >> 8
    return odd_parity8(x & 0xFF)


# Filter function lookup tables
_FILTER_LUT0 = 0xF22C0044
_FILTER_LUT1 = 0x6C81

# LFSR feedback polynomial taps (split into odd/even halves)
LF_POLY_ODD = 0x29CE5C
LF_POLY_EVEN = 0x870804


def _filter_bit(odd: int) -> int:
    f = (_FILTER_LUT0 >> (odd & 0x0F)) & 1
    f |= ((_FILTER_LUT0 >> ((odd >> 4) & 0x0F)) & 1) << 1
    f |= ((_FILTER_LUT0 >> ((odd >> 8) & 0x0F)) & 1) << 2
    f |= ((_FILTER_LUT0 >> ((odd >> 12) & 0x0F)) & 1) << 3
    f |= ((_FILTER_LUT0 >> ((odd >> 16) & 0x0F)) & 1) << 4
    return (_FILTER_LUT1 >> f) & 1


class Crypto1:
    def __init__(self, key: bytes):
        """Initialize with 6-byte key."""
        k = int.from_bytes(key, "big")
        self.odd = 0
        self.even = 0
        for i in range(47, 0, -2):
            self.odd = (self.odd << 1) | ((k >> i) & 1)
        for i in range(46, -1, -2):
            self.even = (self.even << 1) | ((k >> i) & 1)

    def copy(self) -> "Crypto1":
        c = Crypto1.__new__(Crypto1)
        c.odd = self.odd
        c.even = self.even
        return c

    def crypto1_bit(self, inp: int, is_encrypted: int) -> int:
        feedin = self.odd & LF_POLY_ODD
        ret = _filter_bit(self.odd)

        feedin ^= self.even & LF_POLY_EVEN
        feedin = parity32(feedin)

        if is_encrypted:
            feedin ^= inp & 1
        else:
            feedin ^= (inp & 1) ^ ret

        self.even = ((self.even << 1) | ((self.odd >> 23) & 1)) & 0xFFFFFF
        self.odd = ((self.odd << 1) | feedin) & 0xFFFFFF

        return ret

    def crypto1_byte(self, inp: int, is_encrypted: int) -> int:
        ret = 0
        for i in range(8):
            ret |= self.crypto1_bit((inp >> i) & 1, is_encrypted) << i
        return ret

    def crypto1_word(self, inp: int, is_encrypted: int) -> int:
        ret = 0
        for i in range(32):
            ret |= self.crypto1_bit((inp >> i) & 1, is_encrypted) << i
        return ret

    def parity_check_ok(self, n: int) -> bool:
        """Check if auto-parity will be correct for next n bytes."""
        s = self.copy()
        for _ in range(n):
            ks_byte = 0
            for b in range(8):
                ks_byte |= s.crypto1_bit(0, 0) << b
            ks_par = s.crypto1_bit(0, 0)
            if odd_parity8(ks_byte) != ks_par:
                return False
        return True


def prng_successor(x: int, n: int) -> int:
    """MIFARE Classic PRNG: 32-bit LFSR successor."""
    for _ in range(n):
        x = ((x >> 1) | (
            (((x >> 16) ^ (x >> 18) ^ (x >> 19) ^ (x >> 21)) & 1) << 31
        )) & 0xFFFFFFFF
    return x
