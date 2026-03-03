#ifndef SCOPE_H
#define SCOPE_H

/** @file scope.h
 *  @brief Oscilloscope module for the ATmega2560 DTU multimeter.
 *
 *  Provides 10-bit ADC waveform capture with triggering, automatic
 *  measurements (Vpp, Vrms, frequency, duty), OLED rendering,
 *  ASCII waveform output, and binary dump for the Python GUI.
 */

#include <stdint.h>
#include "config.h"   /* for SCOPE_BUF_SIZE, SCOPE_PRETRIG, trig_mode_t, SCOPE_ADC_CH */

/** @defgroup grp_scope Oscilloscope
 *  @brief 1000-sample waveform capture with triggering, auto-measurements, and rendering.
 *  @{ */

/** @brief Oscilloscope automatic measurement results. */
typedef struct {
    float vpp;      /**< Peak-to-peak voltage */
    float vavg;     /**< Average (DC) voltage */
    float vrms;     /**< True-RMS voltage of captured waveform */
    float freq;     /**< Estimated frequency in Hz */
    float duty;     /**< Duty cycle (0.0 - 1.0) */
} scope_meas_t;

/** @brief Initialise oscilloscope ADC, timer, and default settings. */
void scope_init(void);

/** @brief Capture one triggered waveform into the sample buffer. */
void scope_capture(void);

/** @brief Perform a single-shot capture then stop. */
void scope_single_shot(void);

/** @brief Set the trigger mode.
 *  @param mode Trigger mode (auto, rising, falling, none, single).
 */
void scope_set_trigger(trig_mode_t mode);

/** @brief Set the trigger level directly.
 *  @param level Trigger threshold (0-1023 for 10-bit ADC).
 */
void scope_set_trigger_level(uint16_t level);

/** @brief Adjust the trigger level by a signed step.
 *  @param delta Signed step to add to the current trigger level.
 */
void scope_adjust_trigger(int8_t delta);

/** @brief Set the timebase prescaler index.
 *  @param tb Prescaler index (0-7, lower = faster sample rate).
 */
void scope_set_timebase(uint8_t tb);

/** @brief Adjust the timebase by a signed step.
 *  @param delta Signed step to add to the current timebase index.
 */
void scope_adjust_timebase(int8_t delta);

/** @brief Compute automatic measurements from the captured buffer.
 *  @param m Pointer to result struct to populate with Vpp, Vavg, Vrms, freq, duty.
 */
void scope_auto_measure(scope_meas_t *m);

/** @brief Render the captured waveform into an OLED framebuffer.
 *  @param fb Pointer to the 1024-byte OLED framebuffer.
 */
void scope_render_oled(uint8_t *fb);

/** @brief Print an ASCII-art waveform representation to UART. */
void scope_print_ascii(void);

/** @brief Send the raw capture buffer as binary bytes for the Python GUI. */
void scope_dump_binary(void);

/** @name Scope global state
 *  @{
 */
extern uint16_t scope_buf[SCOPE_BUF_SIZE];  /**< Waveform capture buffer */
extern volatile uint8_t scope_running;       /**< 1 if capture is in progress */
extern trig_mode_t scope_trig_mode;          /**< Current trigger mode */
extern uint16_t scope_trig_level;            /**< Trigger threshold (10-bit) */
extern uint8_t scope_timebase;               /**< Timebase prescaler index */
extern uint8_t scope_ac_coupling;            /**< 1 = AC coupling, 0 = DC */
extern uint8_t scope_use_internal_adc;       /**< 1 = ATmega ADC, 0 = MCP3208 */
/** @} */

/** @} */ /* end grp_scope */

#endif /* SCOPE_H */
