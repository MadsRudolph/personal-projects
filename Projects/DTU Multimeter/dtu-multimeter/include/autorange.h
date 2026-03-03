#ifndef AUTORANGE_H
#define AUTORANGE_H

/** @file autorange.h
 *  @brief Auto-ranging state machine.
 *
 *  Manages automatic range selection for resistance, current, and
 *  capacitance measurements based on ADC reading thresholds.
 */

#include <stdint.h>

/** @defgroup grp_autorange Auto-Ranging State Machine
 *  @brief Hysteresis-based auto-ranging with settling guard for stable transitions.
 *  @{ */

/** @brief Check if a range change is needed based on the current ADC reading.
 *  @param raw12 Current 12-bit ADC reading (0-4095).
 *  @return +1 to range up, -1 to range down, 0 to stay.
 */
int8_t autorange_check(uint16_t raw12);

/** @brief Clamp a range index within valid bounds after applying a delta.
 *  @param range     Current range index.
 *  @param delta     Change from autorange_check (+1, -1, or 0).
 *  @param max_range Number of ranges (e.g. N_RES_RANGES).
 *  @return New range index clamped to [0, max_range-1].
 */
uint8_t autorange_clamp(uint8_t range, int8_t delta, uint8_t max_range);

/** @brief Start the settling counter after a range change.
 *
 *  Suppresses further range changes for several cycles to let the
 *  signal stabilize on the new range. Call after every range switch.
 */
void     autorange_settle_start(void);

/** @brief Check whether the auto-range is still settling.
 *  @return 1 if still settling (suppress range changes), 0 if stable.
 */
uint8_t  autorange_settling(void);

/** @} */ /* end grp_autorange */

#endif /* AUTORANGE_H */
