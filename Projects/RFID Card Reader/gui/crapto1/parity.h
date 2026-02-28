/* parity.h — compatibility shim for Proxmark3's evenparity32 */
#ifndef PARITY_H
#define PARITY_H
#include <stdint.h>

static inline int evenparity32(uint32_t x) {
    x ^= x >> 16;
    x ^= x >> 8;
    x ^= x >> 4;
    return (0x6996 >> (x & 0xf)) & 1;
}

#endif
