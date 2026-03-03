#ifndef DISPLAY_RENDER_H
#define DISPLAY_RENDER_H

/** @file display_render.h
 *  @brief Fluke-style OLED display renderer.
 *
 *  Layouts measurement data, oscilloscope waveforms, and the boot
 *  splash screen onto the 128x64 SSD1306 OLED.
 */

#include "measure.h"

/** @defgroup grp_render Display Renderer
 *  @brief Fluke 289-style OLED layout: status bar, primary reading, bar graph, footer.
 *  @{ */

/** @brief Render the full measurement screen (called each main-loop iteration).
 *  @param r Pointer to the current measurement result.
 */
void render_measurement(const meas_result_t *r);

/** @brief Render the oscilloscope waveform and status overlay. */
void render_scope(void);

/** @brief Render the splash/boot screen shown at power-on. */
void render_splash(void);

/** @} */ /* end grp_render */

#endif /* DISPLAY_RENDER_H */
