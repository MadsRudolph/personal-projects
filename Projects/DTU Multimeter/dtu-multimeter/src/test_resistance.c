/** @file test_resistance.c
 *  @brief Breadboard test #3: Resistance measurement (74HC4067 mux + ref resistors).
 *
 *  Build env: test_resistance
 *
 *  Wiring (keep OLED + MCP3208 from previous tests):
 *
 *    74HC4067 DIP-24 pinout:
 *      Pin  1 = COM (Z)   → MCP3208 CH0 (pin 1)
 *      Pin  2 = Y7        → Rref7 (10M) → 5V
 *      Pin  3 = Y6        → Rref6 (10M) → 5V
 *      Pin  4 = Y5        → Rref5 (4.7M) → 5V
 *      Pin  5 = Y4        → Rref4 (499k) → 5V
 *      Pin  6 = Y3        → Rref3 (48.7k) → 5V
 *      Pin  7 = Y2        → Rref2 (4.99k) → 5V
 *      Pin  8 = Y1        → Rref1 (499) → 5V
 *      Pin  9 = Y0        → Rref0 (50) → 5V
 *      Pin 10 = S0        → Arduino D22 (PA0)
 *      Pin 11 = S1        → Arduino D23 (PA1)
 *      Pin 12 = GND       → GND
 *      Pin 13 = S2        → Arduino D24 (PA2)
 *      Pin 14 = S3        → Arduino D25 (PA3)
 *      Pin 15 = EN (low)  → Arduino D26 (PA4)
 *      Pin 16 = Y15       → (unused)
 *      Pin 17 = Y14       → (unused)
 *      Pin 18 = Y13       → (unused)
 *      Pin 19 = Y12       → (unused)
 *      Pin 20 = Y11       → (unused)
 *      Pin 21 = Y10       → (unused)
 *      Pin 22 = Y9        → (unused)
 *      Pin 23 = Y8        → (unused)
 *      Pin 24 = VCC       → 5V
 *
 *    Circuit for each reference resistor:
 *      5V ──┤Rref├── mux channel pin
 *
 *    Measurement:
 *      Mux COM ──┬── MCP3208 CH0 (pin 1)
 *                │
 *            R_unknown (test resistor)
 *                │
 *               GND
 *
 *    Formula: R_unknown = R_ref * V_adc / (V_REF - V_adc)
 *
 *  Serial commands:
 *    0-7  = Select mux channel / range manually
 *    a    = Auto-range mode (default)
 *    s    = Scan all channels (diagnostic)
 *
 *  Start with just 1-2 reference resistors to verify the mux works,
 *  then add more as needed.
 */

#include "config.h"
#include "spi.h"
#include "i2c.h"
#include "uart.h"
#include "timer.h"
#include "adc_mcp3208.h"
#include "mux.h"
#include "display.h"

#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <avr/wdt.h>
#include <string.h>

/* ─── Reference resistor values (from config.h) ───────────────────── */
static const float rref[] PROGMEM = {
    RREF_0, RREF_1, RREF_2, RREF_3,
    RREF_4, RREF_5, RREF_6, RREF_7
};

/* ─── Range labels ─────────────────────────────────────────────────── */
static const char * const range_labels[] PROGMEM = {
    "50R",  "500R", "5k",   "50k",
    "500k", "5M",   "50M",  "50M"
};

/* ─── PROGMEM float read ───────────────────────────────────────────── */
static float read_pgm_float(const float *addr)
{
    float val;
    memcpy_P(&val, addr, sizeof(float));
    return val;
}

/* ─── Print helpers ────────────────────────────────────────────────── */
static void uart_print_u16(uint16_t val)
{
    char buf[6];
    uint8_t pos = 5;
    buf[pos] = '\0';
    if (val == 0) { buf[--pos] = '0'; }
    else { while (val > 0) { buf[--pos] = '0' + (val % 10); val /= 10; } }
    uart_puts(&buf[pos]);
}

static void u16_to_str(char *buf, uint16_t val)
{
    uint8_t pos = 5;
    buf[pos] = '\0';
    if (val == 0) { buf[--pos] = '0'; }
    else { while (val > 0) { buf[--pos] = '0' + (val % 10); val /= 10; } }
    /* Left-justify */
    if (pos > 0) {
        uint8_t len = 5 - pos;
        for (uint8_t i = 0; i <= len; i++)
            buf[i] = buf[pos + i];
    }
}

/* Format resistance with auto-scaling */
static void format_resistance(char *buf, float ohms)
{
    uint32_t val;
    char suffix;

    if (ohms >= 1e6f) {
        val = (uint32_t)(ohms / 1000.0f);  /* in kOhm, then format as X.XXX M */
        suffix = 'M';
        /* val is in kOhm */
        uint16_t integer = (uint16_t)(val / 1000);
        uint16_t frac = (uint16_t)(val % 1000);
        buf[0] = (integer >= 10) ? ('0' + integer / 10) : ' ';
        buf[1] = '0' + (integer % 10);
        buf[2] = '.';
        buf[3] = '0' + (frac / 100);
        buf[4] = '0' + ((frac / 10) % 10);
        buf[5] = suffix;
        buf[6] = '\0';
    } else if (ohms >= 1e3f) {
        val = (uint32_t)(ohms);  /* in Ohm */
        suffix = 'k';
        uint16_t integer = (uint16_t)(val / 1000);
        uint16_t frac = (uint16_t)(val % 1000);
        buf[0] = (integer >= 10) ? ('0' + integer / 10) : ' ';
        buf[1] = '0' + (integer % 10);
        buf[2] = '.';
        buf[3] = '0' + (frac / 100);
        buf[4] = '0' + ((frac / 10) % 10);
        buf[5] = suffix;
        buf[6] = '\0';
    } else {
        val = (uint32_t)(ohms * 10.0f);  /* tenths of ohms */
        buf[0] = (val >= 10000) ? ('0' + (val / 10000) % 10) : ' ';
        buf[1] = (val >= 1000) ? ('0' + (val / 1000) % 10) : ' ';
        buf[2] = '0' + (val / 100) % 10;
        buf[3] = '0' + (val / 10) % 10;
        buf[4] = '.';
        buf[5] = '0' + (val % 10);
        buf[6] = '\0';
    }
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Main
 * ═══════════════════════════════════════════════════════════════════════ */
int main(void)
{
    wdt_disable();
    uart_init();
    sei();

    uart_puts_P(PSTR("\r\n=== DTU Multimeter — Resistance Test ===\r\n"));
    uart_puts_P(PSTR("Commands: 0-7=range, a=auto, s=scan\r\n\r\n"));

    spi_init();
    i2c_init();
    timer_init();
    adc_init();
    mux_init();
    display_init();

    /* Splash */
    display_clear();
    display_str_large(4, 8, "OHM");
    display_str(10, 32, "Resistance Test");
    display_str(10, 44, "0-7:rng a:auto");
    display_flush();
    delay_ms(2000);

    uint8_t current_range = 2;  /* Start at 5k range */
    uint8_t auto_mode = 1;
    uint32_t last_update = 0;

    for (;;) {
        /* ── Handle serial commands ────────────────────────────────── */
        int c = uart_getc_nb();
        if (c >= '0' && c <= '7') {
            current_range = (uint8_t)(c - '0');
            auto_mode = 0;
            uart_puts_P(PSTR("Range: "));
            uart_putc((char)c);
            uart_puts_P(PSTR("\r\n"));
        } else if (c == 'a' || c == 'A') {
            auto_mode = 1;
            uart_puts_P(PSTR("Auto-range ON\r\n"));
        } else if (c == 's' || c == 'S') {
            /* Scan all 8 channels */
            uart_puts_P(PSTR("\r\n--- Mux Channel Scan ---\r\n"));
            for (uint8_t ch = 0; ch < 8; ch++) {
                mux_select(ch);
                delay_ms(10);
                uint16_t raw = adc_read_oversample(ADC_CH_RESIST);
                float v = (float)raw * V_REF / 32767.0f;

                uart_puts_P(PSTR("CH"));
                uart_putc('0' + ch);
                uart_puts_P(PSTR(": raw="));
                uart_print_u16(raw);
                uart_puts_P(PSTR("  V="));
                uart_print_float(v, 3);
                uart_puts_P(PSTR("V\r\n"));
            }
            mux_disable();
            uart_puts_P(PSTR("------------------------\r\n\r\n"));
            continue;
        }

        uint32_t now = millis();
        if (now - last_update < 500)
            continue;
        last_update = now;

        /* ── Select range and read ─────────────────────────────────── */
        mux_select(current_range);

        uint16_t raw = adc_read_oversample(ADC_CH_RESIST);
        float v = (float)raw * V_REF / 32767.0f;
        float ref = read_pgm_float(&rref[current_range]);

        /* Calculate resistance */
        float r_val = 0.0f;
        uint8_t overload = 0;
        float denom = V_REF - v;
        if (denom < 0.001f) {
            r_val = 99999999.0f;
            overload = 1;
        } else {
            r_val = ref * v / denom;
        }

        /* ── Auto-range ────────────────────────────────────────────── */
        if (auto_mode) {
            float ratio = v / V_REF;
            if (ratio > 0.92f && current_range < 7) {
                current_range++;
            } else if (ratio < 0.08f && current_range > 0) {
                current_range--;
            }
        }

        /* ── Update OLED ───────────────────────────────────────────── */
        display_clear();

        display_str(0, 0, "Resistance Test");
        display_hline(0, 9, 128);

        /* Main reading */
        if (overload) {
            display_str_large(10, 14, "OL");
        } else {
            char rbuf[8];
            format_resistance(rbuf, r_val);
            display_str_large(4, 14, rbuf);
        }

        display_hline(0, 32, 128);

        /* Range info */
        display_str(0, 35, "Range:");
        {
            char ch = '0' + current_range;
            display_char(42, 35, ch);
        }
        display_str(54, 35, auto_mode ? "(auto)" : "(man)");

        /* Rref value */
        display_str(0, 44, "Rref:");
        uart_print_float(ref, 0);  /* serial only for precision */

        /* Raw ADC + voltage */
        display_str(0, 52, "ADC:");
        {
            char nbuf[6];
            u16_to_str(nbuf, raw);
            display_str(30, 52, nbuf);
        }
        display_str(68, 52, "V:");
        {
            /* Show voltage as X.XXX */
            uint32_t mv = (uint32_t)(v * 1000.0f);
            char vbuf[7];
            vbuf[0] = '0' + (mv / 1000);
            vbuf[1] = '.';
            vbuf[2] = '0' + ((mv / 100) % 10);
            vbuf[3] = '0' + ((mv / 10) % 10);
            vbuf[4] = '0' + (mv % 10);
            vbuf[5] = '\0';
            display_str(80, 52, vbuf);
        }

        display_flush();

        /* ── Serial output ─────────────────────────────────────────── */
        uart_puts_P(PSTR("R"));
        uart_putc('0' + current_range);
        uart_puts_P(PSTR(": "));
        if (overload) {
            uart_puts_P(PSTR("OL  "));
        } else {
            uart_print_float(r_val, 1);
            uart_puts_P(PSTR(" Ohm  "));
        }
        uart_puts_P(PSTR("Vadc="));
        uart_print_float(v, 3);
        uart_puts_P(PSTR("V  raw="));
        uart_print_u16(raw);
        uart_puts_P(PSTR("  Rref="));
        uart_print_float(ref, 0);
        uart_puts_P(PSTR("\r\n"));
    }

    return 0;
}
