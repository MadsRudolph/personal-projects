/*  mfkey32.c
 *
 *  MIFARE Classic key recovery from two 32-bit authentication exchanges.
 *  Uses the crapto1 library's lfsr_recovery32 to find candidate LFSR states,
 *  then validates against a second exchange to identify the unique key.
 *
 *  Usage: mfkey32 <uid> <nt0> <nr0> <ar0> <nt1> <nr1> <ar1>
 *  All values in hex. Outputs: "Found key: <12-hex-chars>" or "No key found"
 *
 *  Based on mfkey32v2 by bla <blapost@gmail.com> (GPL v2+)
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include "crapto1.h"

int main(int argc, char *argv[]) {
    if (argc < 8) {
        fprintf(stderr, "Usage: %s <uid> <nt0> <nr0> <ar0> <nt1> <nr1> <ar1>\n",
                argv[0]);
        fprintf(stderr, "All values in hexadecimal.\n");
        return 1;
    }

    uint32_t uid, nt0, nr0_enc, ar0_enc, nt1, nr1_enc, ar1_enc;
    sscanf(argv[1], "%x", &uid);
    sscanf(argv[2], "%x", &nt0);
    sscanf(argv[3], "%x", &nr0_enc);
    sscanf(argv[4], "%x", &ar0_enc);
    sscanf(argv[5], "%x", &nt1);
    sscanf(argv[6], "%x", &nr1_enc);
    sscanf(argv[7], "%x", &ar1_enc);

    /* Generate LFSR successors of the tag challenges */
    uint32_t p64  = prng_successor(nt0, 64);
    uint32_t p64b = prng_successor(nt1, 64);

    /* Extract keystream: ks2 = ar0_enc XOR prng_successor(nt0, 64) */
    struct Crypto1State *s, *t;
    uint64_t key;
    int found = 0;

    s = lfsr_recovery32(ar0_enc ^ p64, 0);
    if (!s) {
        fprintf(stderr, "Memory allocation failed\n");
        return 2;
    }

    for (t = s; t->odd | t->even; ++t) {
        lfsr_rollback_word(t, 0, 0);
        lfsr_rollback_word(t, nr0_enc, 1);
        lfsr_rollback_word(t, uid ^ nt0, 0);
        crypto1_get_lfsr(t, &key);

        /* Validate against second exchange */
        crypto1_word(t, uid ^ nt1, 0);
        crypto1_word(t, nr1_enc, 1);
        if (ar1_enc == (crypto1_word(t, 0, 0) ^ p64b)) {
            printf("Found key: %012" PRIx64 "\n", key);
            found = 1;
            break;
        }
    }

    free(s);

    if (!found) {
        printf("No key found\n");
        return 1;
    }

    return 0;
}
