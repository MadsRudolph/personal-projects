#ifndef TIMER_H
#define TIMER_H

/** @file timer.h
 *  @brief System tick and frequency capture driver for ATmega2560.
 *
 *  Timer1 provides a 1 ms system tick (millis/micros/delay_ms).
 *  INT4 captures frequency and duty cycle on PE4 (Arduino D2).
 */

#include <stdint.h>

/** @defgroup grp_timer Timer / Tick Driver
 *  @brief Timer1 CTC for 1 ms system tick (millis, micros, delay_ms).
 *  @{ */

/** @brief Start Timer1 1 ms tick and INT4 frequency capture. */
void     timer_init(void);

/** @brief Milliseconds elapsed since boot (read atomically).
 *  @return Tick count in milliseconds */
uint32_t millis(void);

/** @brief Microseconds elapsed since boot.
 *  @return Tick count in microseconds */
uint32_t micros(void);

/** @brief Blocking delay using the millis() tick.
 *  @param ms Delay duration in milliseconds */
void     delay_ms(uint16_t ms);

/** @} */

/** @defgroup grp_timer_freq Frequency Capture (INT4)
 *  @brief Volatile results written by the INT4 ISR.
 *  @{ */

/** @brief Period between consecutive rising edges in microseconds. */
extern volatile uint32_t freq_period_us;

/** @brief High-time (rising to falling edge) in microseconds. */
extern volatile uint32_t freq_high_us;

/** @brief Set to 1 by the ISR when a new measurement is ready. */
extern volatile uint8_t  freq_ready;

/** @} */

#endif /* TIMER_H */
