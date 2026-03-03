#ifndef DISPLAY_H
#define DISPLAY_H

/** @file display.h
 *  @brief SSD1306 128x64 I2C OLED framebuffer display driver.
 *
 *  Bare-metal driver for the ATmega2560. Maintains a 1024-byte
 *  framebuffer and flushes it to the OLED via I2C (TWI).
 */

#include <stdint.h>

/** @defgroup grp_display SSD1306 OLED Display Driver
 *  @brief 128x64 I2C OLED with 1024-byte framebuffer, text, and drawing primitives.
 *  @{ */

/** @brief Initialise the SSD1306 OLED (full init sequence, clear screen). */
void     display_init(void);

/** @brief Clear the entire framebuffer (memset to 0). */
void     display_clear(void);

/** @brief Flush the 1024-byte framebuffer to the OLED via I2C. */
void     display_flush(void);

/** @name Pixel & Text
 *  @{
 */

/** @brief Set or clear a single pixel.
 *  @param x  Horizontal coordinate (0-127).
 *  @param y  Vertical coordinate (0-63).
 *  @param on 1 to set the pixel, 0 to clear it.
 */
void     display_pixel(uint8_t x, uint8_t y, uint8_t on);

/** @brief Draw a single character at pixel position using the 5x7 font.
 *  @param x Column pixel position.
 *  @param y Row pixel position.
 *  @param c ASCII character to draw.
 */
void     display_char(uint8_t x, uint8_t y, char c);

/** @brief Draw a null-terminated string from RAM at pixel position.
 *  @param x Column pixel position.
 *  @param y Row pixel position.
 *  @param s Pointer to null-terminated string in RAM.
 */
void     display_str(uint8_t x, uint8_t y, const char *s);

/** @brief Draw a null-terminated string from PROGMEM at pixel position.
 *  @param x Column pixel position.
 *  @param y Row pixel position.
 *  @param s Pointer to null-terminated string in PROGMEM.
 */
void     display_str_P(uint8_t x, uint8_t y, const char *s);

/** @brief Draw a string at 2x scale (large digits for primary readout).
 *  @param x Column pixel position.
 *  @param y Row pixel position.
 *  @param s Pointer to null-terminated string.
 */
void     display_str_large(uint8_t x, uint8_t y, const char *s);
/** @} */

/** @name Drawing Primitives
 *  @{
 */

/** @brief Draw a horizontal line.
 *  @param x Starting column.
 *  @param y Row.
 *  @param w Width in pixels.
 */
void     display_hline(uint8_t x, uint8_t y, uint8_t w);

/** @brief Draw a vertical line.
 *  @param x Column.
 *  @param y Starting row.
 *  @param h Height in pixels.
 */
void     display_vline(uint8_t x, uint8_t y, uint8_t h);

/** @brief Draw an unfilled rectangle.
 *  @param x Top-left column.
 *  @param y Top-left row.
 *  @param w Width in pixels.
 *  @param h Height in pixels.
 */
void     display_rect(uint8_t x, uint8_t y, uint8_t w, uint8_t h);

/** @brief Draw a filled rectangle.
 *  @param x Top-left column.
 *  @param y Top-left row.
 *  @param w Width in pixels.
 *  @param h Height in pixels.
 */
void     display_fill_rect(uint8_t x, uint8_t y, uint8_t w, uint8_t h);

/** @brief Draw a horizontal bar graph.
 *  @param x       Top-left column.
 *  @param y       Top-left row.
 *  @param w       Total width in pixels.
 *  @param h       Height in pixels.
 *  @param percent Fill percentage (0-100).
 */
void     display_bar(uint8_t x, uint8_t y, uint8_t w, uint8_t h,
                     uint8_t percent);
/** @} */

/** @brief Get a pointer to the raw framebuffer for direct access.
 *  @return Pointer to the 1024-byte framebuffer (e.g. for scope rendering).
 */
uint8_t *display_buffer(void);

/** @} */ /* end grp_display */

#endif /* DISPLAY_H */
