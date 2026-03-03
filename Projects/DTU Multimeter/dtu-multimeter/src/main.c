/** @file main.c
 *  @brief Entry point, hardware init, and super loop dispatcher.
 */

/* ═══════════════════════════════════════════════════════════════════
 *  DTU Digital Multimeter — Main Entry Point
 *  ATmega2560, 16 MHz, bare-metal AVR C (no Arduino)
 *
 *  Super loop: init → measure → display → UI → logging → repeat
 * ═══════════════════════════════════════════════════════════════════ */

#include "config.h"
#include "spi.h"
#include "i2c.h"
#include "uart.h"
#include "timer.h"
#include "adc_mcp3208.h"
#include "mux.h"
#include "display.h"
#include "display_render.h"
#include "rtc_ds1307.h"
#include "measure.h"
#include "autorange.h"
#include "scope.h"
#include "ui.h"
#include "logging.h"

#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <avr/wdt.h>
#include <string.h>

/* ─── LED and Buzzer helpers ─────────────────────────────────────── */

static void led_init(void)
{
    /* Red, Green, Yellow LEDs + Buzzer as outputs */
    LEDR_DDR |= (1 << LEDR_BIT);
    LEDG_DDR |= (1 << LEDG_BIT);
    LEDY_DDR |= (1 << LEDY_BIT);
    BUZZ_DDR |= (1 << BUZZ_BIT);

    /* All off initially */
    LEDR_PORT &= ~(1 << LEDR_BIT);
    LEDG_PORT &= ~(1 << LEDG_BIT);
    LEDY_PORT &= ~(1 << LEDY_BIT);
    BUZZ_PORT &= ~(1 << BUZZ_BIT);
}

static inline void led_red(uint8_t on)
{
    if (on) LEDR_PORT |= (1 << LEDR_BIT);
    else    LEDR_PORT &= ~(1 << LEDR_BIT);
}

static inline void led_green(uint8_t on)
{
    if (on) LEDG_PORT |= (1 << LEDG_BIT);
    else    LEDG_PORT &= ~(1 << LEDG_BIT);
}

static inline void led_yellow(uint8_t on)
{
    if (on) LEDY_PORT |= (1 << LEDY_BIT);
    else    LEDY_PORT &= ~(1 << LEDY_BIT);
}

static inline void buzzer(uint8_t on)
{
    if (on) BUZZ_PORT |= (1 << BUZZ_BIT);
    else    BUZZ_PORT &= ~(1 << BUZZ_BIT);
}

/* ─── Mode button handler ────────────────────────────────────────── */

static void handle_mode_button(void)
{
    if (!btn_mode_pressed)
        return;
    btn_mode_pressed = 0;

    mode_t m = current_mode;
    m++;
    if (m >= M_COUNT)
        m = M_DCV;
    current_mode = m;

    /* Disable peripherals when leaving modes that use them */
    mux_disable();
    cur_disable();
    isrc_disable();
    cap_float();
}

/* ─── FUNC button handler ────────────────────────────────────────── */

static void handle_func_button(void)
{
    if (!btn_func_pressed)
        return;
    btn_func_pressed = 0;

    /* Cycle: NONE → REL → HOLD → MINMAX → NONE */
    switch (current_func) {
    case FUNC_NONE:
        current_func = FUNC_REL;
        rel_reference = 0.0f;  /* Will be set on next measurement */
        break;
    case FUNC_REL:
        current_func = FUNC_HOLD;
        break;
    case FUNC_HOLD:
        current_func = FUNC_MINMAX;
        measure_reset_minmax();
        break;
    case FUNC_MINMAX:
        current_func = FUNC_NONE;
        break;
    }
}

/* ─── RANGE button handler ───────────────────────────────────────── */

static void handle_range_button(void)
{
    if (!btn_range_pressed)
        return;
    btn_range_pressed = 0;

    /* Toggle range lock, or step up if already locked */
    if (!range_locked) {
        range_locked = 1;
    }
    /* In locked mode, serial '+' already sets this flag */
}

/* ─── SELECT button handler ──────────────────────────────────────── */

static void handle_select_button(void)
{
    if (!btn_sel_pressed)
        return;
    btn_sel_pressed = 0;

    /* Toggle low-pass filter */
    lpf_enabled = !lpf_enabled;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Main
 * ═══════════════════════════════════════════════════════════════════ */

int main(void)
{
    /* ─── Disable watchdog (in case bootloader left it on) ──────── */
    wdt_disable();

    /* ─── Initialize peripherals ────────────────────────────────── */
    uart_init();
    sei();   /* Enable interrupts early so UART TX ISR can drain the buffer */

    uart_puts_P(PSTR("\r\n=== DTU Digital Multimeter v1.0 ===\r\n"));
    uart_puts_P(PSTR("Initializing...\r\n"));

    spi_init();
    i2c_init();
    timer_init();
    adc_init();
    mux_init();
    led_init();
    ui_init();
    display_init();
    rtc_init();
    scope_init();
    measure_init();
    logging_init();

    /* Splash screen */
    render_splash();
    delay_ms(1500);

    uart_puts_P(PSTR("Ready. Press ? for help.\r\n"));
    led_green(1);

    /* ─── Measurement result buffer ─────────────────────────────── */
    meas_result_t result;
    memset(&result, 0, sizeof(result));

    /* ─── Timing for display/logging rates ──────────────────────── */
    uint32_t last_display_ms = 0;
    uint32_t last_log_ms     = 0;

    static uint8_t hold_frozen = 0;

    /* ═══════════════════════════════════════════════════════════════
     *  Super Loop
     * ═══════════════════════════════════════════════════════════════ */

    for (;;) {
        uint32_t now = millis();

        /* ─── Handle buttons ────────────────────────────────────── */
        ui_poll_buttons();
        handle_mode_button();
        handle_func_button();
        handle_range_button();
        handle_select_button();

        /* ─── Handle serial commands ────────────────────────────── */
        ui_process_serial();

        /* ─── Scope mode (separate path) ────────────────────────── */
        if (current_mode == M_SCOPE) {
            if (scope_running) {
                scope_capture();
                scope_meas_t sm;
                scope_auto_measure(&sm);
            }

            if (now - last_display_ms >= 100) {
                last_display_ms = now;
                scope_render_oled(display_buffer());
                render_scope();
            }
            continue;
        }

        /* ─── Normal measurement modes ──────────────────────────── */

        /* Skip measurement if HOLD is active and we already have a value */
        if (current_func == FUNC_HOLD && hold_frozen) {
            /* Still update display at normal rate */
            if (now - last_display_ms >= 200) {
                last_display_ms = now;
                render_measurement(&result);
            }
            continue;
        }

        /* Perform measurement */
        measure_dispatch(&result);

        /* Capture REL reference on first measurement after enabling */
        if (current_func == FUNC_REL && rel_reference == 0.0f) {
            rel_reference = result.primary + rel_reference;
            /* Re-apply to get delta = 0 on first reading */
        }

        /* HOLD: freeze after first measurement */
        if (current_func == FUNC_HOLD) {
            hold_frozen = 1;
        } else {
            hold_frozen = 0;
        }

        /* ─── Continuity buzzer (fast response) ────────────────── */
        if (current_mode == M_CONTIN) {
            buzzer(result.primary < CONTIN_THRESHOLD);
        } else {
            buzzer(0);
        }

        /* ─── LED indicators ────────────────────────────────────── */
        led_red(result.overload);
        led_green(!result.overload);
        led_yellow(current_func == FUNC_HOLD || logging_enabled);

        /* ─── Update display (~5 Hz) ────────────────────────────── */
        if (now - last_display_ms >= 200) {
            last_display_ms = now;
            render_measurement(&result);
        }

        /* ─── Data logging (1 sample/sec) ───────────────────────── */
        if (logging_enabled && (now - last_log_ms >= 1000)) {
            last_log_ms = now;
            logging_store(result.primary, result.unit);
        }
    }

    return 0;  /* Never reached */
}
