#ifndef TRMS_H
#define TRMS_H

/** @file trms.h
 *  @brief True-RMS computation engine.
 *
 *  Samples an MCP3208 channel at 20 kHz (50 us intervals) and computes
 *  True-RMS, DC, AC component, and peak values.
 */

#include <stdint.h>

/** @defgroup grp_trms True-RMS Computation
 *  @brief Samples at 20 kHz and computes RMS, DC, AC, and peak values.
 *  @{ */

/** @brief True-RMS measurement results. */
typedef struct {
    float rms;          /**< True-RMS value (voltage or current) */
    float dc;           /**< DC component (mean) */
    float ac;           /**< AC component: sqrt(rms^2 - dc^2) */
    float peak_pos;     /**< Positive peak (max sample in window) */
    float peak_neg;     /**< Negative peak (min sample in window) */
} trms_result_t;

/** @brief Perform a full True-RMS measurement on one ADC channel.
 *
 *  Samples the channel, computes RMS/DC/AC/peaks, and fills the result struct.
 *  @param adc_channel MCP3208 channel number (0-7).
 *  @param result      Pointer to result struct to populate.
 */
void  trms_measure(uint8_t adc_channel, trms_result_t *result);

/** @brief Compute True-RMS from a raw 12-bit sample array.
 *  @param samples Pointer to array of 12-bit ADC values.
 *  @param count   Number of samples in the array.
 *  @return True-RMS value in ADC counts.
 */
float trms_compute_rms(const uint16_t *samples, uint16_t count);

/** @brief Compute DC (mean) from a raw 12-bit sample array.
 *  @param samples Pointer to array of 12-bit ADC values.
 *  @param count   Number of samples in the array.
 *  @return DC (mean) value in ADC counts.
 */
float trms_compute_dc(const uint16_t *samples, uint16_t count);

/** @} */ /* end grp_trms */

#endif /* TRMS_H */
