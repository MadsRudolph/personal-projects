"""
MIFARE Classic key recovery algorithms.

mfkey32: Recovers key from two sniffed authentication exchanges (uses crapto1 C library).
Nested: Recovers key from nonce pairs (one known key needed).
"""

import os
import subprocess

from crypto1 import Crypto1, prng_successor, odd_parity8, LF_POLY_ODD, LF_POLY_EVEN, _filter_bit, parity32

# Path to the mfkey32 CLI tool (compiled crapto1)
_MFKEY32_PATH = os.path.join(os.path.dirname(__file__), "crapto1", "mfkey32.exe")


def find_prng_distance(nt_start: int, nt_end: int, max_dist: int = 65536) -> int | None:
    """Find how many PRNG ticks separate two nonce values."""
    state = nt_start
    for i in range(max_dist + 1):
        if state == nt_end:
            return i
        state = prng_successor(state, 1)
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


def nested_recover(uid: int, nt_known: int, nt_target: int,
                   known_key: bytes, target_block: int) -> list[bytes]:
    """
    Recover target sector key from nested authentication nonce pair.

    Args:
        uid: 32-bit card UID
        nt_known: plaintext nonce from known-key auth
        nt_target: nonce from target sector (may be encrypted or plain depending on protocol)
        known_key: 6-byte known key
        target_block: target sector's first block number

    Returns:
        List of candidate keys (6-byte bytes objects)
    """
    candidates = []

    # Find PRNG distance between nonces
    # The PRNG advances during the auth protocol, typically 160-1200 ticks
    dist = find_prng_distance(nt_known, nt_target, max_dist=65536)

    if dist is not None:
        # nt_target matches a PRNG prediction -- it was sent in plaintext
        # This means the card dropped crypto before sending it
        # The key recovery uses the fact that we can predict the nonce
        # For each possible key, check if the PRNG timing is consistent
        pass  # Placeholder for full LFSR rollback attack

    # Brute-force approach for nested (works when PRNG is predictable):
    # Try all 65536 possible PRNG states and check consistency
    # This is the simplified version -- the full crapto1 nested attack
    # uses LFSR rollback for O(2^16) instead of O(2^48)

    # For now, return empty -- full implementation requires the LFSR
    # rollback tables which are generated from the crypto1 structure
    return candidates


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
