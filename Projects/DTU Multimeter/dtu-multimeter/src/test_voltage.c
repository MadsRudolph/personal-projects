/** @file test_voltage.c
 *  @brief Breadboard test #2: Voltage measurement (divider + direct).
 *
 *  Build env: test_voltage
 *
 *  Wiring (keep OLED + MCP3208 from test_basic):
 *
 *    Voltage divider (high range, 0–55 V on breadboard):
 *      V_IN ──┤1 MΩ├──┬──┤100 kΩ├── GND
 *                      │
 *                      └── MCP3208 CH1 (pin 2)
 *
 *    Direct input (low range, 0–5 V):
 *      V_IN ── MCP3208 CH2 (pin 3)
 *
 *    For testing, use the Arduino 5V or 3.3V pin as a known
 *    voltage source, or a potentiometer.
 *
 *  What it does:
 *    - Reads CH1 (divider) and CH2 (direct) at 2 Hz
 *    - Computes actual voltage using VDIV_RATIO for CH1
 *    - Displays both on OLED (large) and serial
 *    - Also shows raw ADC counts for calibration
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
#include <string.h>

/* ─── Format helpers ───────────────────────────────────────────────── */

/* Format millivolts as "XX.XXX" (no unit suffix, 5 chars + NUL) */
static void format_volts(char *buf, uint32_t mv)
{
    /* Up to 99.999 V display */
    uint8_t tens  = (uint8_t)(mv / 10000);
    uint8_t ones  = (uint8_t)((mv / 1000) % 10);
    uint8_t d1    = (uint8_t)((mv / 100) % 10);
    uint8_t d2    = (uint8_t)((mv / 10) % 10);
    uint8_t d3    = (uint8_t)(mv % 10);

    if (tens > 0) {
        buf[0] = '0' + tens;
        buf[1] = '0' + ones;
        buf[2] = '.';
        buf[3] = '0' + d1;
        buf[4] = '0' + d2;
        buf[5] = '0' + d3;
        buf[6] = '\0';
    } else {
        buf[0] = ' ';
        buf[1] = '0' + ones;
        buf[2] = '.';
        buf[3] = '0' + d1;
        buf[4] = '0' + d2;
        buf[5] = '0' + d3;
        buf[6] = '\0';
    }
}

/* Print uint16 to serial */
static void uart_print_u16(uint16_t val)
{
    char buf[6];
    uint8_t pos = 5;
    buf[pos] = '\0';
    if (val == 0) {
        buf[--pos] = '0';
    } else {
        while (val > 0) {
            buf[--pos] = '0' + (val % 10);
            val /= 10;
        }
    }
    uart_puts(&buf[pos]);
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Main
 * ═══════════════════════════════════════════════════════════════════════ */
int main(void)
{
    wdt_disable();
    uart_init();
    sei();

    uart_puts_P(PSTR("\r\n=== DTU Multimeter — Voltage Test ===\r\n"));
    uart_puts_P(PSTR("CH1: High range (1M+100k divider, ratio "));
    uart_print_float(VDIV_RATIO, 2);
    uart_puts_P(PSTR(")\r\n"));
    uart_puts_P(PSTR("CH2: Low range (direct, 0-5V)\r\n\r\n"));

    spi_init();
    i2c_init();
    timer_init();
    adc_init();
    display_init();

    /* Splash */
    display_clear();
    display_str_large(4, 8, "VOLT");
    display_str(10, 32, "Voltage Test");
    display_str(10, 44, "CH1=div CH2=dir");
    display_flush();
    delay_ms(2000);

    uint32_t last_update = 0;

    for (;;) {
        uint32_t now = millis();
        if (now - last_update < 500)
            continue;
        last_update = now;

        /* ── Read both channels with oversampling ──────────────────── */
        uint16_t raw1 = adc_read_oversample(ADC_CH_VOLT_HI);
        uint16_t raw2 = adc_read_oversample(ADC_CH_VOLT_LO);

        /* Convert to voltage (oversampled 15-bit) */
        float v_adc1 = adc_to_voltage_os(raw1);
        float v_adc2 = adc_to_voltage_os(raw2);

        /* Apply divider ratio for high range */
        float v_high = v_adc1 * VDIV_RATIO;
        float v_low  = v_adc2;

        /* Convert to millivolts for display formatting */
        uint32_t mv_high = (uint32_t)(v_high * 1000.0f);
        uint32_t mv_low  = (uint32_t)(v_low  * 1000.0f);

        /* ── Update OLED ───────────────────────────────────────────── */
        display_clear();

        display_str(0, 0, "Voltage Test");
        display_hline(0, 9, 128);

        /* High range (divider) */
        display_str(0, 12, "HI (div):");
        {
            char vbuf[8];
            format_volts(vbuf, mv_high);
            display_str_large(16, 22, vbuf);
        }
        display_str(110, 28, "V");

        display_hline(0, 38, 128);

        /* Low range (direct) */
        display_str(0, 40, "LO (dir):");
        {
            char vbuf[8];
            format_volts(vbuf, mv_low);
            display_str(60, 40, vbuf);
            display_str(98, 40, "V");
        }

        /* Raw ADC values (useful for calibration) */
        display_str(0, 52, "RAW:");
        {
            char buf[6];
            uint16_t r = raw1;
            uint8_t pos = 5;
            buf[pos] = '\0';
            if (r == 0) { buf[--pos] = '0'; }
            else { while (r) { buf[--pos] = '0' + (r % 10); r /= 10; } }
            display_str(30, 52, &buf[pos]);
        }
        display_str(68, 52, "/");
        {
            char buf[6];
            uint16_t r = raw2;
            uint8_t pos = 5;
            buf[pos] = '\0';
            if (r == 0) { buf[--pos] = '0'; }
            else { while (r) { buf[--pos] = '0' + (r % 10); r /= 10; } }
            display_str(74, 52, &buf[pos]);
        }

        display_flush();

        /* ── Serial output ─────────────────────────────────────────── */
        uart_puts_P(PSTR("HI:"));
        uart_print_float(v_high, 3);
        uart_puts_P(PSTR("V (raw="));
        uart_print_u16(raw1);
        uart_puts_P(PSTR(")  LO:"));
        uart_print_float(v_low, 3);
        uart_puts_P(PSTR("V (raw="));
        uart_print_u16(raw2);
        uart_puts_P(PSTR(")\r\n"));
    }

    return 0;
}
