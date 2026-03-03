#ifndef RTC_DS1307_H
#define RTC_DS1307_H

/** @file rtc_ds1307.h
 *  @brief DS1307 real-time clock I2C driver.
 *
 *  Provides read/write access to the DS1307 RTC and helper functions
 *  for formatting time and date strings.
 */

#include <stdint.h>

/** @defgroup grp_rtc DS1307 Real-Time Clock
 *  @brief I2C RTC for timestamping data log entries.
 *  @{ */

/** @brief DS1307 date/time structure (BCD-decoded). */
typedef struct {
    uint8_t sec;    /**< Seconds (0-59) */
    uint8_t min;    /**< Minutes (0-59) */
    uint8_t hour;   /**< Hours (0-23, 24-hour format) */
    uint8_t day;    /**< Day of week (1-7) */
    uint8_t date;   /**< Day of month (1-31) */
    uint8_t month;  /**< Month (1-12) */
    uint8_t year;   /**< Year (0-99, offset from 2000) */
} rtc_time_t;

/** @brief Initialise the DS1307 RTC (start oscillator if halted). */
void rtc_init(void);

/** @brief Read the current time from the DS1307.
 *  @param t Pointer to time struct to populate.
 */
void rtc_read(rtc_time_t *t);

/** @brief Write a time/date to the DS1307.
 *  @param t Pointer to time struct with values to set.
 */
void rtc_write(const rtc_time_t *t);

/** @brief Format time as "HH:MM:SS" into a buffer.
 *  @param t   Pointer to time struct.
 *  @param buf Output buffer (must hold at least 9 bytes).
 */
void rtc_format_time(const rtc_time_t *t, char *buf);

/** @brief Format date as "DD/MM/YY" into a buffer.
 *  @param t   Pointer to time struct.
 *  @param buf Output buffer (must hold at least 9 bytes).
 */
void rtc_format_date(const rtc_time_t *t, char *buf);

/** @} */ /* end grp_rtc */

#endif
