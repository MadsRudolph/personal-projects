#ifndef CRYPTO1_H
#define CRYPTO1_H

#include <stdint.h>

typedef struct {
    uint32_t odd;
    uint32_t even;
} crypto1_state;

// Initialize LFSR with 48-bit key
void crypto1_init(crypto1_state *s, uint8_t *key);

// Process one bit through the cipher
// Returns keystream bit
// is_encrypted: 0 = input is plaintext (XOR with ks before feeding)
//               1 = input is ciphertext (feed directly)
uint8_t crypto1_bit(crypto1_state *s, uint8_t in, uint8_t is_encrypted);

// Process one byte, returns keystream byte
uint8_t crypto1_byte(crypto1_state *s, uint8_t in, uint8_t is_encrypted);

// Process 32 bits, returns keystream word
uint32_t crypto1_word(crypto1_state *s, uint32_t in, uint8_t is_encrypted);

// MIFARE Classic tag PRNG successor
// Steps the 32-bit LFSR forward by n ticks
uint32_t prng_successor(uint32_t x, uint32_t n);

// Odd parity of a byte (1 if odd number of set bits)
uint8_t odd_parity8(uint8_t x);

// Check if auto-parity will be correct for encrypted data
// Returns 1 if odd_parity(ks_data_byte) == ks_parity_bit for all n bytes
// s_copy: copy of cipher state (will be advanced), n: number of bytes to check
uint8_t parity_check_ok(crypto1_state *s_copy, uint8_t n);

#endif
