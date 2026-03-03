#ifndef FONT5X7_H
#define FONT5X7_H

/** @file font5x7.h
 *  @brief 5x7 pixel monospace font stored in AVR PROGMEM.
 *
 *  Covers ASCII 32 (space) through 126 (~): 95 characters, 5 bytes each
 *  (475 bytes total). Each byte encodes 5 columns of 7 vertical pixels,
 *  LSB = top pixel.
 *
 *  Usage:
 *  @code
 *    uint8_t col_data = pgm_read_byte(&font5x7[(c - 32) * 5 + col]);
 *  @endcode
 *  where @c c is the ASCII character and @c col is 0..4.
 */

#include <stdint.h>
#include <avr/pgmspace.h>

/** @brief 5x7 font bitmap array in PROGMEM (95 chars x 5 bytes = 475 bytes). */
extern const uint8_t font5x7[] PROGMEM;

#endif /* FONT5X7_H */
