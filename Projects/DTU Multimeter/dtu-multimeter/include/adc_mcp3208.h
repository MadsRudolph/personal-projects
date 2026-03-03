#ifndef ADC_MCP3208_H
#define ADC_MCP3208_H

/** @file adc_mcp3208.h
 *  @brief MCP3208 12-bit 8-channel SPI ADC driver.
 *
 *  Single-ended reads via SPI Mode 0,0. Supports raw 12-bit conversions,
 *  64x oversampled 15-bit reads, and voltage conversion helpers.
 */

#include <stdint.h>

/** @defgroup grp_adc MCP3208 12-bit ADC
 *  @brief 8-channel SPI ADC with 64x oversampling for 15-bit effective resolution.
 *  @{ */

/** @brief Initialize the ADC chip-select pin (output, HIGH = deselected). */
void     adc_init(void);

/** @brief Read a single 12-bit sample from one channel.
 *  @param channel ADC channel number (0--7)
 *  @return Raw 12-bit result (0--4095) */
uint16_t adc_read_raw(uint8_t channel);

/** @brief Read 64 samples and average, yielding a 15-bit result.
 *  @param channel ADC channel number (0--7)
 *  @return Oversampled 15-bit result (0--32767) */
uint16_t adc_read_oversample(uint8_t channel);

/** @brief Convert a 12-bit raw value to voltage.
 *  @param raw12 Raw ADC value (0--4095)
 *  @return Voltage as V_REF * raw12 / 4095 */
float    adc_to_voltage(uint16_t raw12);

/** @brief Convert a 15-bit oversampled value to voltage.
 *  @param raw15 Oversampled ADC value (0--32767)
 *  @return Voltage as V_REF * raw15 / 32767 */
float    adc_to_voltage_os(uint16_t raw15);

/** @} */

#endif /* ADC_MCP3208_H */
