"""
MIFARE Classic key recovery algorithms.

Darkside: Recovers key from NACK events (no known key needed).
Nested: Recovers key from nonce pairs (one known key needed).
"""

from crypto1 import Crypto1, prng_successor, odd_parity8, LF_POLY_ODD, LF_POLY_EVEN, _filter_bit, parity32


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


def darkside_recover(uid: int, nack_data: list[dict]) -> list[bytes]:
    """
    Recover key from darkside attack NACK data.

    Args:
        uid: 32-bit card UID
        nack_data: list of {"nt": int, "nr_ar": bytes} dicts from NACK events

    Returns:
        List of candidate keys (6-byte bytes objects)
    """
    candidates = []

    if len(nack_data) < 2:
        return candidates

    # The darkside attack uses the parity oracle:
    # For each NACK event, we know that the parity of our plaintext
    # happened to match the encrypted parity from the card.
    # This constrains bits of the keystream.

    # Simplified approach: collect enough NACK events and use
    # statistical analysis to recover key bits.

    # Full implementation would use lfsr_recovery32 from crapto1.
    # For now, this is a placeholder structure.

    return candidates
