#ifndef MEASURE_H
#define MEASURE_H

/** @file measure.h
 *  @brief Measurement engine for all 22 multimeter modes.
 *
 *  Each measurement function populates a meas_result_t with the primary
 *  display value, secondary data, range, overload flag, and unit string.
 */

#include <stdint.h>
#include "config.h"
#include "trms.h"

/** @defgroup grp_measure Measurement Engine
 *  @brief 22-mode measurement dispatcher with auto-ranging, REL, HOLD, and Min/Max.
 *  @{ */

/** @brief Container for one measurement result. */
typedef struct {
    float    primary;        /**< Main display value */
    float    secondary;      /**< Secondary value (e.g. AC component) */
    uint8_t  range;          /**< Current range index */
    uint8_t  overload;       /**< 1 if input exceeds the selected range */
    char     unit[8];        /**< Unit string: "V", "mV", "kOhm", etc. */
    char     prefix;         /**< SI prefix: ' ', 'm', 'k', 'M' */
} meas_result_t;

/** @name Global measurement state
 *  @brief State variables shared between the measurement engine and UI.
 *  @{
 */
extern volatile mode_t      current_mode;       /**< Active measurement mode */
extern volatile func_mode_t current_func;       /**< Active secondary function */
extern uint8_t              range_locked;        /**< 1 if manual range lock is active */
extern uint8_t              lpf_enabled;         /**< 1 if low-pass filter is active */
extern uint8_t              logging_enabled;     /**< 1 if data logging is active */
extern float                rel_reference;       /**< REL-mode reference value */
extern float                min_val, max_val;    /**< Min/Max recorded values */
extern double               avg_sum;             /**< Running sum for average computation */
extern uint32_t             avg_count;           /**< Sample count for average computation */
extern uint8_t              dbm_impedance_idx;   /**< dBm impedance: 0=50, 1=75, 2=600 Ohm */
/** @} */

/** @brief Initialise measurement hardware (SPI, mux, current switches). */
void measure_init(void);

/** @brief Dispatch to the measurement function for the current mode.
 *  @param result Pointer to result struct to populate.
 */
void measure_dispatch(meas_result_t *result);

/** @name Individual measurement functions
 *  @brief One function per mode; each fills a meas_result_t.
 *  @{
 */

/** @brief Measure DC voltage.
 *  @param r Pointer to result struct. */
void meas_dcv(meas_result_t *r);

/** @brief Measure AC voltage (True-RMS).
 *  @param r Pointer to result struct. */
void meas_acv(meas_result_t *r);

/** @brief Measure DC+AC combined voltage.
 *  @param r Pointer to result struct. */
void meas_dcacv(meas_result_t *r);

/** @brief Measure millivolt DC.
 *  @param r Pointer to result struct. */
void meas_mv_dc(meas_result_t *r);

/** @brief Measure millivolt AC.
 *  @param r Pointer to result struct. */
void meas_mv_ac(meas_result_t *r);

/** @brief Measure resistance (auto-ranging across 8 decades).
 *  @param r Pointer to result struct. */
void meas_resistance(meas_result_t *r);

/** @brief Measure low-ohm resistance using constant current source.
 *  @param r Pointer to result struct. */
void meas_low_ohm(meas_result_t *r);

/** @brief Measure conductance in nanosiemens.
 *  @param r Pointer to result struct. */
void meas_conductance(meas_result_t *r);

/** @brief Continuity test with buzzer.
 *  @param r Pointer to result struct. */
void meas_continuity(meas_result_t *r);

/** @brief Diode forward-voltage test.
 *  @param r Pointer to result struct. */
void meas_diode(meas_result_t *r);

/** @brief Measure capacitance (charge-time method).
 *  @param r Pointer to result struct. */
void meas_capacitance(meas_result_t *r);

/** @brief Measure inductance (RL step-response timing method).
 *  @param r Pointer to result struct. */
void meas_inductance(meas_result_t *r);

/** @brief Measure DC current.
 *  @param r Pointer to result struct. */
void meas_dc_current(meas_result_t *r);

/** @brief Measure AC current (True-RMS).
 *  @param r Pointer to result struct. */
void meas_ac_current(meas_result_t *r);

/** @brief Measure DC+AC combined current.
 *  @param r Pointer to result struct. */
void meas_dcac_current(meas_result_t *r);

/** @brief Measure frequency via hardware counter.
 *  @param r Pointer to result struct. */
void meas_frequency(meas_result_t *r);

/** @brief Measure duty cycle.
 *  @param r Pointer to result struct. */
void meas_duty_cycle(meas_result_t *r);

/** @brief Measure pulse width.
 *  @param r Pointer to result struct. */
void meas_pulse_width(meas_result_t *r);

/** @brief Measure temperature using LM35 sensor.
 *  @param r Pointer to result struct. */
void meas_temperature(meas_result_t *r);

/** @brief Compute dBV from AC voltage measurement.
 *  @param r Pointer to result struct. */
void meas_dbv(meas_result_t *r);

/** @brief Compute dBm from AC voltage and selected impedance.
 *  @param r Pointer to result struct. */
void meas_dbm(meas_result_t *r);
/** @} */

/** @brief Apply secondary function (REL, HOLD, MIN/MAX) to a result.
 *  @param r Pointer to result struct to modify in place.
 */
void measure_apply_secondary(meas_result_t *r);

/** @brief Reset the Min/Max recorded values to their initial state. */
void measure_reset_minmax(void);

/** @} */ /* end grp_measure */

#endif /* MEASURE_H */
