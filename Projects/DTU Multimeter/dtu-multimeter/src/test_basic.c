/** @file test_basic.c
 *  @brief Breadboard test #1: OLED display + MCP3208 ADC.
 *
 *  Build with:  pio run -e test_basic
 *  Upload with: pio run -e test_basic -t upload
 *  Monitor:     pio device monitor -b 115200
 *
 *  Wiring:
 *    Arduino Mega   →   SSD1306 OLED (I2C)
 *      D20 (SDA)    →   SDA
 *      D21 (SCL)    →   SCL
 *      5V           →   VCC
 *      GND          →   GND
 *
 *    Arduino Mega   →   MCP3208 DIP-16 (SPI)
 *      D50 (MISO)   →   DOUT  (pin 12)
 *      D51 (MOSI)   →   DIN   (pin 11)
 *      D52 (SCK)    →   CLK   (pin 13)
 *      D53 (CS)     →   CS    (pin 10)
 *      5V           →   VDD   (pin 16)
 *      5V           →   VREF  (pin 15)
 *      GND          →   DGND  (pin 9)
 *      GND          →   AGND  (pin 14)
 *
 *    Test inputs:
 *      - Connect a potentiometer (10k) between 5V and GND,
 *        wiper to MCP3208 CH0 (pin 1) for a variable test voltage.
 *      - Leave other channels floating or tie to GND/5V.
 */

#include "config.h"
#include "spi.h"
#include "i2c.h"
#include "uart.h"
#include "timer.h"
#include "adc_mcp3208.h"
#include "display.h"

#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <avr/wdt.h>
#include <stdio.h>
#include <string.h>

/* ─── Simple integer-to-string (avoids pulling in sprintf for floats) ── */
static void format_voltage(char *buf, uint16_t raw12)
{
    /* voltage = raw * 5000 / 4095  (in millivolts) */
    uint32_t mv = (uint32_t)raw12 * 5000UL / 4095UL;
    uint8_t  v  = (uint8_t)(mv / 1000);
    uint16_t frac = (uint16_t)(mv % 1000);

    buf[0] = '0' + v;
    buf[1] = '.';
    buf[2] = '0' + (frac / 100);
    buf[3] = '0' + ((frac / 10) % 10);
    buf[4] = '0' + (frac % 10);
    buf[5] = 'V';
    buf[6] = '\0';
}

/* ─── Format channel label: "C0:" ───────────────────────────────────── */
static void format_ch_label(char *buf, uint8_t ch)
{
    buf[0] = 'C';
    buf[1] = '0' + ch;
    buf[2] = ':';
    buf[3] = '\0';
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Main
 * ═══════════════════════════════════════════════════════════════════════ */
int main(void)
{
    wdt_disable();

    /* ─── Init peripherals ─────────────────────────────────────────── */
    uart_init();
    sei();

    uart_puts_P(PSTR("\r\n=== DTU Multimeter — Breadboard Test ===\r\n"));
    uart_puts_P(PSTR("Block 1: OLED Display (I2C)\r\n"));
    uart_puts_P(PSTR("Block 2: MCP3208 ADC (SPI)\r\n\r\n"));

    spi_init();
    i2c_init();
    timer_init();
    adc_init();

    uart_puts_P(PSTR("SPI + I2C initialized.\r\n"));

    /* ─── Init display ─────────────────────────────────────────────── */
    uart_puts_P(PSTR("Initializing OLED...\r\n"));
    display_init();

    /* Splash screen */
    display_clear();
    display_str_large(4, 8, "DTU");
    display_str(10, 32, "Multimeter v1.0");
    display_str(10, 44, "Breadboard Test");
    display_flush();

    uart_puts_P(PSTR("OLED OK — splash displayed.\r\n"));
    delay_ms(2000);

    /* ─── Test MCP3208: read all 8 channels once ───────────────────── */
    uart_puts_P(PSTR("\r\nMCP3208 initial read:\r\n"));
    for (uint8_t ch = 0; ch < 8; ch++) {
        uint16_t raw = adc_read_raw(ch);
        char label[4], vbuf[8];
        format_ch_label(label, ch);
        format_voltage(vbuf, raw);

        uart_puts(label);
        uart_putc(' ');
        uart_puts_P(PSTR("raw="));

        /* Print raw as decimal */
        char numbuf[6];
        uint16_t r = raw;
        uint8_t pos = 5;
        numbuf[pos] = '\0';
        do {
            numbuf[--pos] = '0' + (r % 10);
            r /= 10;
        } while (r > 0);
        uart_puts(&numbuf[pos]);

        uart_puts_P(PSTR("  "));
        uart_puts(vbuf);
        uart_puts_P(PSTR("\r\n"));
    }

    uart_puts_P(PSTR("\r\nEntering live display loop (2 Hz)...\r\n"));
    uart_puts_P(PSTR("Watch OLED + serial for updates.\r\n\r\n"));

    /* ═══════════════════════════════════════════════════════════════════
     *  Live loop: read all 8 ADC channels, display on OLED + serial
     * ═══════════════════════════════════════════════════════════════════ */
    uint32_t last_update = 0;
    uint32_t loop_count = 0;

    for (;;) {
        uint32_t now = millis();

        if (now - last_update < 500)
            continue;
        last_update = now;
        loop_count++;

        /* Read all channels */
        uint16_t raw[8];
        for (uint8_t ch = 0; ch < 8; ch++)
            raw[ch] = adc_read_raw(ch);

        /* ── Update OLED ───────────────────────────────────────────── */
        display_clear();

        /* Title bar */
        display_str(0, 0, "ADC Test");

        /* Show CH0 large (primary test channel) */
        {
            char vbuf[8];
            format_voltage(vbuf, raw[0]);
            display_str_large(16, 12, vbuf);
        }

        /* Show CH1-CH7 small in two rows at bottom */
        for (uint8_t ch = 1; ch < 5; ch++) {
            char label[4], vbuf[8];
            format_ch_label(label, ch);
            format_voltage(vbuf, raw[ch]);

            uint8_t x = (ch - 1) * 32;
            display_str(x, 36, label);
            /* Show just voltage digits (trim 'V') */
            vbuf[5] = '\0';
            display_str(x, 44, vbuf);
        }
        for (uint8_t ch = 5; ch < 8; ch++) {
            char label[4], vbuf[8];
            format_ch_label(label, ch);
            format_voltage(vbuf, raw[ch]);

            uint8_t x = (ch - 5) * 32;
            display_str(x, 52, label);
            vbuf[5] = '\0';
            display_str(x, 56, vbuf);
        }

        /* Heartbeat indicator */
        if (loop_count & 1)
            display_pixel(124, 0, 1);

        display_flush();

        /* ── Serial output ─────────────────────────────────────────── */
        for (uint8_t ch = 0; ch < 8; ch++) {
            char label[4], vbuf[8];
            format_ch_label(label, ch);
            format_voltage(vbuf, raw[ch]);

            uart_puts(label);
            uart_puts(vbuf);
            if (ch < 7)
                uart_puts_P(PSTR("  "));
        }
        uart_puts_P(PSTR("\r\n"));
    }

    return 0;
}
