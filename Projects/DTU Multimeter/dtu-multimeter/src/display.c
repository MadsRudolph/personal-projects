/** @file display.c
 *  @brief SSD1306 128x64 OLED framebuffer driver over I2C.
 */

/* ═══════════════════════════════════════════════════════════════════════════
 *  display.c — SSD1306 128x64 I2C OLED Framebuffer Driver
 *  Target: ATmega2560 bare-metal AVR C (no Arduino)
 *
 *  Uses TWI (I2C) to drive a 0.96" SSD1306 OLED via a 1024-byte local
 *  framebuffer.  All drawing goes into the buffer; call display_flush()
 *  to push the whole frame to the controller in horizontal addressing mode.
 * ═══════════════════════════════════════════════════════════════════════════ */

#include "config.h"
#include "i2c.h"
#include "font5x7.h"
#include "display.h"

#include <string.h>
#include <avr/pgmspace.h>

/* ─── Constants ──────────────────────────────────────────────────────────── */
#define SSD1306_WRITE_ADDR  (OLED_ADDR << 1)   /* 0x3C << 1 = 0x78       */
#define CTRL_CMD            0x00                /* Co=0, D/C#=0: command  */
#define CTRL_DATA           0x40                /* Co=0, D/C#=1: data     */
#define CHUNK_SIZE          16                  /* I2C data bytes per txn */

/* ─── Framebuffer (128 x 64 / 8 = 1024 bytes) ───────────────────────────── */
static uint8_t fb[OLED_WIDTH * OLED_PAGES];     /* 1024 bytes             */

/* ─── SSD1306 Init Sequence (PROGMEM) ────────────────────────────────────── */
static const uint8_t init_cmds[] PROGMEM = {
    0xAE,             /* Display OFF                                        */
    0xD5, 0x80,       /* Set display clock div: default fosc / 1            */
    0xA8, 0x3F,       /* Set multiplex ratio: 64-1                          */
    0xD3, 0x00,       /* Set display offset: none                           */
    0x40,             /* Set start line: 0                                  */
    0x8D, 0x14,       /* Charge pump: enable (internal VCC)                 */
    0x20, 0x00,       /* Memory addressing mode: horizontal                 */
    0xA1,             /* Segment re-map: col 127 = SEG0                     */
    0xC8,             /* COM scan direction: remapped (bottom-to-top)       */
    0xDA, 0x12,       /* COM pins config: alternative, no L/R remap         */
    0x81, 0xCF,       /* Contrast: 207                                      */
    0xD9, 0xF1,       /* Pre-charge period: phase1=1, phase2=15             */
    0xDB, 0x40,       /* VCOMH deselect level: ~0.89 x VCC                  */
    0xA4,             /* Entire display ON — follow RAM                     */
    0xA6,             /* Normal display (not inverted)                      */
    0xAF              /* Display ON                                         */
};

/* ═══════════════════════════════════════════════════════════════════════════
 *  Low-level helpers
 * ═══════════════════════════════════════════════════════════════════════════ */

/* Send a single command byte to the SSD1306 */
static void display_cmd(uint8_t cmd)
{
    i2c_start(SSD1306_WRITE_ADDR);
    i2c_write(CTRL_CMD);
    i2c_write(cmd);
    i2c_stop();
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  Public API
 * ═══════════════════════════════════════════════════════════════════════════ */

/* ─── display_init ───────────────────────────────────────────────────────── */
void display_init(void)
{
    /* Send the entire PROGMEM init sequence */
    for (uint8_t i = 0; i < sizeof(init_cmds); i++)
        display_cmd(pgm_read_byte(&init_cmds[i]));

    display_clear();
    display_flush();
}

/* ─── display_clear ──────────────────────────────────────────────────────── */
void display_clear(void)
{
    memset(fb, 0x00, sizeof(fb));
}

/* ─── display_flush ──────────────────────────────────────────────────────── */
void display_flush(void)
{
    /* Set column address range 0..127 */
    display_cmd(0x21);
    display_cmd(0);
    display_cmd(OLED_WIDTH - 1);

    /* Set page address range 0..7 */
    display_cmd(0x22);
    display_cmd(0);
    display_cmd(OLED_PAGES - 1);

    /* Send framebuffer in 16-byte chunks (64 transactions x 16 bytes) */
    for (uint16_t offset = 0; offset < sizeof(fb); offset += CHUNK_SIZE) {
        i2c_start(SSD1306_WRITE_ADDR);
        i2c_write(CTRL_DATA);
        for (uint8_t j = 0; j < CHUNK_SIZE; j++)
            i2c_write(fb[offset + j]);
        i2c_stop();
    }
}

/* ─── display_pixel ──────────────────────────────────────────────────────── */
void display_pixel(uint8_t x, uint8_t y, uint8_t on)
{
    if (x >= OLED_WIDTH || y >= OLED_HEIGHT)
        return;

    uint16_t idx = x + (uint16_t)(y >> 3) * OLED_WIDTH;
    uint8_t  bit = (1 << (y & 7));

    if (on)
        fb[idx] |= bit;
    else
        fb[idx] &= ~bit;
}

/* ─── display_char ───────────────────────────────────────────────────────── */
void display_char(uint8_t x, uint8_t y, char c)
{
    if (c < 32 || c > 126)
        c = '?';

    uint16_t base = (uint16_t)(c - 32) * 5;

    for (uint8_t col = 0; col < 5; col++) {
        uint8_t line = pgm_read_byte(&font5x7[base + col]);
        for (uint8_t row = 0; row < 7; row++) {
            if (line & (1 << row))
                display_pixel(x + col, y + row, 1);
        }
    }
}

/* ─── display_str ────────────────────────────────────────────────────────── */
void display_str(uint8_t x, uint8_t y, const char *s)
{
    while (*s) {
        display_char(x, y, *s++);
        x += 6;                        /* 5px char + 1px gap */
    }
}

/* ─── display_str_P (PROGMEM string) ─────────────────────────────────────── */
void display_str_P(uint8_t x, uint8_t y, const char *s)
{
    char c;
    while ((c = pgm_read_byte(s++)) != '\0') {
        display_char(x, y, c);
        x += 6;
    }
}

/* ─── display_str_large (2x scaled: 10x14 per character) ─────────────────── */
void display_str_large(uint8_t x, uint8_t y, const char *s)
{
    while (*s) {
        char c = *s++;
        if (c < 32 || c > 126)
            c = '?';

        uint16_t base = (uint16_t)(c - 32) * 5;

        for (uint8_t col = 0; col < 5; col++) {
            uint8_t line = pgm_read_byte(&font5x7[base + col]);
            for (uint8_t row = 0; row < 7; row++) {
                if (line & (1 << row)) {
                    /* Draw a 2x2 block for each set pixel */
                    uint8_t px = x + col * 2;
                    uint8_t py = y + row * 2;
                    display_pixel(px,     py,     1);
                    display_pixel(px + 1, py,     1);
                    display_pixel(px,     py + 1, 1);
                    display_pixel(px + 1, py + 1, 1);
                }
            }
        }
        x += 12;                       /* 10px char + 2px gap */
    }
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  Drawing Primitives
 * ═══════════════════════════════════════════════════════════════════════════ */

/* ─── display_hline ──────────────────────────────────────────────────────── */
void display_hline(uint8_t x, uint8_t y, uint8_t w)
{
    for (uint8_t i = 0; i < w; i++)
        display_pixel(x + i, y, 1);
}

/* ─── display_vline ──────────────────────────────────────────────────────── */
void display_vline(uint8_t x, uint8_t y, uint8_t h)
{
    for (uint8_t i = 0; i < h; i++)
        display_pixel(x, y + i, 1);
}

/* ─── display_rect ───────────────────────────────────────────────────────── */
void display_rect(uint8_t x, uint8_t y, uint8_t w, uint8_t h)
{
    display_hline(x, y, w);                /* top    */
    display_hline(x, y + h - 1, w);       /* bottom */
    display_vline(x, y, h);               /* left   */
    display_vline(x + w - 1, y, h);       /* right  */
}

/* ─── display_fill_rect ──────────────────────────────────────────────────── */
void display_fill_rect(uint8_t x, uint8_t y, uint8_t w, uint8_t h)
{
    for (uint8_t row = 0; row < h; row++)
        display_hline(x, y + row, w);
}

/* ─── display_bar (progress bar) ─────────────────────────────────────────── */
void display_bar(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint8_t percent)
{
    if (percent > 100)
        percent = 100;

    /* Outer rectangle */
    display_rect(x, y, w, h);

    /* Inner filled region (1px inset on each side) */
    if (w > 2 && h > 2) {
        uint8_t inner_w = (uint8_t)(((uint16_t)(w - 2) * percent) / 100);
        if (inner_w > 0)
            display_fill_rect(x + 1, y + 1, inner_w, h - 2);
    }
}

/* ─── display_buffer ─────────────────────────────────────────────────────── */
uint8_t *display_buffer(void)
{
    return fb;
}
