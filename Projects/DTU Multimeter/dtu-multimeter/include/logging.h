#ifndef LOGGING_H
#define LOGGING_H

/** @file logging.h
 *  @brief EEPROM circular buffer and UART CSV data logging.
 *
 *  Stores measurement readings in a circular EEPROM buffer and
 *  outputs CSV-formatted data over UART for host capture.
 */

#include <stdint.h>

/** @defgroup grp_logging Data Logging
 *  @brief EEPROM circular buffer (100 entries) with UART CSV output and RTC timestamps.
 *  @{ */

/** @brief Initialise logging by reading the write index and count from EEPROM. */
void logging_init(void);

/** @brief Store one measurement reading to EEPROM and output via UART CSV.
 *  @param value Measured value to log.
 *  @param unit  Null-terminated unit string (e.g. "V", "mA").
 */
void logging_store(float value, const char *unit);

/** @brief Dump all stored EEPROM log entries via UART. */
void logging_dump_eeprom(void);

/** @brief Print the CSV column header line to UART. */
void logging_csv_header(void);

/** @} */ /* end grp_logging */

#endif /* LOGGING_H */
