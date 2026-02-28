/* Generate test vectors for nested.exe verification.
 * Usage: gen_nested_test <uid> <key_hex> <dist> <nt_known>
 * Outputs the encrypted nonce that nested.exe should recover.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include "crapto1.h"

int main(int argc, char *argv[]) {
    if (argc < 5) {
        fprintf(stderr, "Usage: %s <uid> <key_hex> <dist> <ntK0> [<ntK1> ...]\n", argv[0]);
        return 1;
    }

    uint32_t uid;
    uint64_t key;
    int dist;
    sscanf(argv[1], "%x", &uid);
    sscanf(argv[2], "%" PRIx64, &key);
    dist = atoi(argv[3]);

    printf("uid=%08X key=%012" PRIx64 " dist=%d\n", uid, key, dist);

    for (int i = 4; i < argc; i++) {
        uint32_t nt_known;
        sscanf(argv[i], "%x", &nt_known);

        uint32_t nt_pred = prng_successor(nt_known, dist);

        /* Simulate card: init crypto1 with key, feed uid^nt, get keystream */
        struct Crypto1State *s = crypto1_create(key);
        uint32_t ks32 = crypto1_word(s, uid ^ nt_pred, 0);
        uint32_t nt_enc = nt_pred ^ ks32;
        crypto1_destroy(s);

        printf("nt_k=%08X nt_pred=%08X ks32=%08X nt_enc=%08X\n",
               nt_known, nt_pred, ks32, nt_enc);
    }

    return 0;
}
