/** @file autorange.c
 *  @brief Auto-ranging state machine with hysteresis and settling guard.
 */

/* ═══════════════════════════════════════════════════════════════════
 *  Auto-Ranging State Machine — ATmega2560
 *  Hysteresis-based range switching with settling guard
 * ═══════════════════════════════════════════════════════════════════ */

#include "config.h"
#include "autorange.h"

/* ─── Thresholds (12-bit ADC scale) ──────────────────────────────── */

#define ADC_MAX        4095
#define THRESH_UP      ((uint16_t)(RANGE_UP_THRESH   * ADC_MAX))  /* ~3767 */
#define THRESH_DOWN    ((uint16_t)(RANGE_DOWN_THRESH  * ADC_MAX))  /* ~327  */

/* ─── Settling guard ─────────────────────────────────────────────── */

#define SETTLE_CYCLES  5     /* suppress range changes for N readings */

static uint8_t settle_count;

/* ─── Public functions ───────────────────────────────────────────── */

int8_t autorange_check(uint16_t raw12)
{
    if (raw12 > THRESH_UP)
        return +1;           /* signal too high — range up */
    if (raw12 < THRESH_DOWN)
        return -1;           /* signal too low  — range down */
    return 0;                /* within good band */
}

uint8_t autorange_clamp(uint8_t range, int8_t delta, uint8_t max_range)
{
    if (delta > 0 && range < max_range - 1)
        return range + 1;
    if (delta < 0 && range > 0)
        return range - 1;
    return range;
}

void autorange_settle_start(void)
{
    settle_count = SETTLE_CYCLES;
}

uint8_t autorange_settling(void)
{
    if (settle_count > 0) {
        settle_count--;
        return 1;
    }
    return 0;
}
