#ifndef UI_H
#define UI_H

/** @file ui.h
 *  @brief User interface -- buttons and serial command parser.
 *
 *  The MODE button is interrupt-driven (INT5). FUNC, RANGE, and SELECT
 *  buttons are polled with software debounce each main-loop iteration.
 */

#include <stdint.h>

/** @defgroup grp_ui User Interface
 *  @brief MODE button (INT5 interrupt), FUNC/RANGE/SELECT (polled), serial commands.
 *  @{ */

/** @brief Configure button GPIO pins, pull-ups, and INT5 ISR. */
void ui_init(void);

/** @brief Poll FUNC, RANGE, and SELECT buttons (call each main loop).
 *
 *  Reads pin state with debounce and sets the corresponding press flags.
 */
void ui_poll_buttons(void);

/** @brief Check UART receive buffer for serial commands and execute them. */
void ui_process_serial(void);

/** @name Button press flags
 *  @brief Set by ISR or polling, cleared by the consumer after handling.
 *  @{
 */
extern volatile uint8_t btn_mode_pressed;   /**< MODE button pressed flag */
extern volatile uint8_t btn_func_pressed;   /**< FUNC button pressed flag */
extern volatile uint8_t btn_range_pressed;  /**< RANGE button pressed flag */
extern volatile uint8_t btn_sel_pressed;    /**< SELECT button pressed flag */
/** @} */

/** @} */ /* end grp_ui */

#endif /* UI_H */
