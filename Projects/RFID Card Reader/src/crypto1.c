#include "crypto1.h"

// Parity lookup for 4 bits
static const uint8_t ODD_PARITY[16] = {
    0,1,1,0, 1,0,0,1, 1,0,0,1, 0,1,1,0
};

static uint8_t odd_parity8(uint8_t x) {
    return ODD_PARITY[x >> 4] ^ ODD_PARITY[x & 0x0F];
}

static uint8_t parity32(uint32_t x) {
    x ^= x >> 16;
    x ^= x >> 8;
    return odd_parity8(x & 0xFF);
}

// The nonlinear filter function
// Takes 5 bits from specific LFSR tap positions
// Uses a 20-input boolean function (factored into 4x5-bit lookups)
static const uint32_t FILTER_LUT0 = 0xF22C0044UL;
static const uint32_t FILTER_LUT1 = 0x6C81UL;

static uint8_t filter_bit(uint32_t odd) {
    uint32_t f;
    f  = FILTER_LUT0 >> (odd       & 0x0F) & 1;
    f |= (FILTER_LUT0 >> (odd >> 4  & 0x0F) & 1) << 1;
    f |= (FILTER_LUT0 >> (odd >> 8  & 0x0F) & 1) << 2;
    f |= (FILTER_LUT0 >> (odd >> 12 & 0x0F) & 1) << 3;
    f |= (FILTER_LUT0 >> (odd >> 16 & 0x0F) & 1) << 4;
    return (FILTER_LUT1 >> f) & 1;
}

// LFSR feedback polynomial taps (split into odd/even halves)
// Polynomial: x^48 + ... (see MIFARE Classic crypto analysis papers)
#define LF_POLY_ODD  0x29CE5C
#define LF_POLY_EVEN 0x870804

void crypto1_init(crypto1_state *s, uint8_t *key) {
    // Pack 6-byte key into odd/even split LFSR
    uint64_t k = 0;
    for (uint8_t i = 0; i < 6; i++) {
        k = (k << 8) | key[i];
    }

    s->odd = s->even = 0;
    for (int8_t i = 47; i > 0; i -= 2)
        s->odd = (s->odd << 1) | ((k >> i) & 1);
    for (int8_t i = 46; i >= 0; i -= 2)
        s->even = (s->even << 1) | ((k >> i) & 1);
}

uint8_t crypto1_bit(crypto1_state *s, uint8_t in, uint8_t is_encrypted) {
    uint32_t feedin = s->odd & LF_POLY_ODD;
    uint8_t ret = filter_bit(s->odd);

    feedin ^= s->even & LF_POLY_EVEN;
    feedin = parity32(feedin);

    if (is_encrypted)
        feedin ^= (in & 1);
    else
        feedin ^= (in & 1) ^ ret;

    s->even = (s->even << 1) | ((s->odd >> 23) & 1);
    s->odd = (s->odd << 1) | feedin;

    return ret;
}

uint8_t crypto1_byte(crypto1_state *s, uint8_t in, uint8_t is_encrypted) {
    uint8_t ret = 0;
    for (uint8_t i = 0; i < 8; i++) {
        ret |= crypto1_bit(s, (in >> i) & 1, is_encrypted) << i;
    }
    return ret;
}

uint32_t crypto1_word(crypto1_state *s, uint32_t in, uint8_t is_encrypted) {
    uint32_t ret = 0;
    for (uint8_t i = 0; i < 32; i++) {
        ret |= (uint32_t)crypto1_bit(s, (in >> i) & 1, is_encrypted) << i;
    }
    return ret;
}

uint32_t prng_successor(uint32_t x, uint32_t n) {
    // MIFARE Classic PRNG: 32-bit LFSR
    // Feedback: bit31 = bit0 ^ bit2 ^ bit3 ^ bit5
    // (taps at positions 16, 18, 19, 21 from MSB)
    while (n--) {
        x = (x >> 1) | (((x >> 16) ^ (x >> 18) ^ (x >> 19) ^ (x >> 21)) << 31);
    }
    return x;
}

uint8_t parity_check_ok(crypto1_state *s_copy, uint8_t n) {
    // Check if auto-parity will match for the next n encrypted bytes
    // For each byte: auto-parity is correct when odd_parity(ks_data) == ks_parity
    for (uint8_t i = 0; i < n; i++) {
        uint8_t ks_byte = 0;
        for (uint8_t b = 0; b < 8; b++) {
            ks_byte |= crypto1_bit(s_copy, 0, 0) << b;
        }
        uint8_t ks_par = crypto1_bit(s_copy, 0, 0);  // 9th bit = parity keystream
        if (odd_parity8(ks_byte) != ks_par)
            return 0;
    }
    return 1;
}
