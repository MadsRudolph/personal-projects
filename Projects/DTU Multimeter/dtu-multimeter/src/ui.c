/** @file ui.c
 *  @brief Button handling (INT5 + polled) and serial command parser.
 */

/* ═══════════════════════════════════════════════════════════════════
 *  User Interface — ATmega2560 DTU Digital Multimeter
 *  MODE on INT5 (PE5/D3), FUNC/RANGE/SELECT polled with debounce
 *  Serial command parser on UART0
 * ═══════════════════════════════════════════════════════════════════ */

#include "config.h"
#include "ui.h"
#include "measure.h"
#include "uart.h"
#include "timer.h"

#include <avr/interrupt.h>
#include <avr/pgmspace.h>

/* ─── Button press flags ─────────────────────────────────────────── */

volatile uint8_t btn_mode_pressed  = 0;
volatile uint8_t btn_func_pressed  = 0;
volatile uint8_t btn_range_pressed = 0;
volatile uint8_t btn_sel_pressed   = 0;

/* ─── Debounce state ─────────────────────────────────────────────── */

#define DEBOUNCE_MS  50

static uint32_t last_func_ms;
static uint32_t last_range_ms;
static uint32_t last_sel_ms;
static uint32_t last_mode_ms;

/* ─── INT5 ISR — MODE button ────────────────────────────────────── */

ISR(INT5_vect)
{
    uint32_t now = millis();
    if (now - last_mode_ms >= DEBOUNCE_MS) {
        last_mode_ms = now;
        btn_mode_pressed = 1;
    }
}

/* ─── Initialization ─────────────────────────────────────────────── */

void ui_init(void)
{
    /* MODE button: PE5 (D3) as input with pull-up */
    BTN_MODE_DDR  &= ~(1 << BTN_MODE_BIT);
    BTN_MODE_PORT |=  (1 << BTN_MODE_BIT);

    /* FUNC button: PG5 (D4) as input with pull-up */
    BTN_FUNC_DDR  &= ~(1 << BTN_FUNC_BIT);
    BTN_FUNC_PORT |=  (1 << BTN_FUNC_BIT);

    /* RANGE button: PE3 (D5) as input with pull-up */
    BTN_RANGE_DDR  &= ~(1 << BTN_RANGE_BIT);
    BTN_RANGE_PORT |=  (1 << BTN_RANGE_BIT);

    /* SELECT button: PH3 (D6) as input with pull-up */
    BTN_SEL_DDR  &= ~(1 << BTN_SEL_BIT);
    BTN_SEL_PORT |=  (1 << BTN_SEL_BIT);

    /* Configure INT5 (PE5) for falling edge (active-low button) */
    EICRB |=  (1 << ISC51);   /* ISC51=1, ISC50=0 → falling edge */
    EICRB &= ~(1 << ISC50);
    EIMSK |=  (1 << INT5);    /* Enable INT5 */

    last_func_ms  = 0;
    last_range_ms = 0;
    last_sel_ms   = 0;
    last_mode_ms  = 0;
}

/* ─── Poll buttons (call from main loop) ─────────────────────────── */

void ui_poll_buttons(void)
{
    uint32_t now = millis();

    /* FUNC — PG5, active LOW */
    if (!(BTN_FUNC_PINR & (1 << BTN_FUNC_BIT))) {
        if (now - last_func_ms >= DEBOUNCE_MS) {
            last_func_ms = now;
            btn_func_pressed = 1;
        }
    }

    /* RANGE — PE3, active LOW */
    if (!(BTN_RANGE_PINR & (1 << BTN_RANGE_BIT))) {
        if (now - last_range_ms >= DEBOUNCE_MS) {
            last_range_ms = now;
            btn_range_pressed = 1;
        }
    }

    /* SELECT — PH3, active LOW */
    if (!(BTN_SEL_PINR & (1 << BTN_SEL_BIT))) {
        if (now - last_sel_ms >= DEBOUNCE_MS) {
            last_sel_ms = now;
            btn_sel_pressed = 1;
        }
    }
}

/* ─── PROGMEM help text ──────────────────────────────────────────── */

static const char help_text[] PROGMEM =
    "DTU Multimeter Serial Commands:\r\n"
    "  R  Toggle REL mode\r\n"
    "  H  Toggle HOLD\r\n"
    "  A  Toggle Auto-Hold\r\n"
    "  M  Toggle Min/Max/Avg\r\n"
    "  L  Toggle Low-Pass Filter\r\n"
    "  G  Toggle Data Logging\r\n"
    "  K  Toggle Range Lock\r\n"
    "  +  Range up (manual)\r\n"
    "  -  Range down (manual)\r\n"
    "  Z  Cycle dBm impedance\r\n"
    "  P  Print Min/Max stats\r\n"
    "  E  Dump EEPROM log\r\n"
    "  ?  This help\r\n";

/* ─── Serial command processing ──────────────────────────────────── */

void ui_process_serial(void)
{
    int c = uart_getc_nb();
    if (c < 0)
        return;

    switch ((char)c) {
    case 'R':
    case 'r':
        if (current_func == FUNC_REL) {
            current_func = FUNC_NONE;
            uart_puts_P(PSTR("REL off\r\n"));
        } else {
            current_func = FUNC_REL;
            /* Store current reading as reference at next measurement */
            uart_puts_P(PSTR("REL on\r\n"));
        }
        break;

    case 'H':
    case 'h':
        if (current_func == FUNC_HOLD) {
            current_func = FUNC_NONE;
            uart_puts_P(PSTR("HOLD off\r\n"));
        } else {
            current_func = FUNC_HOLD;
            uart_puts_P(PSTR("HOLD on\r\n"));
        }
        break;

    case 'M':
    case 'm':
        if (current_func == FUNC_MINMAX) {
            current_func = FUNC_NONE;
            uart_puts_P(PSTR("MinMax off\r\n"));
        } else {
            current_func = FUNC_MINMAX;
            measure_reset_minmax();
            uart_puts_P(PSTR("MinMax on\r\n"));
        }
        break;

    case 'L':
    case 'l':
        lpf_enabled = !lpf_enabled;
        uart_puts_P(lpf_enabled ? PSTR("LPF on\r\n") : PSTR("LPF off\r\n"));
        break;

    case 'G':
    case 'g':
        logging_enabled = !logging_enabled;
        uart_puts_P(logging_enabled ? PSTR("LOG on\r\n") : PSTR("LOG off\r\n"));
        break;

    case 'K':
    case 'k':
        range_locked = !range_locked;
        uart_puts_P(range_locked ? PSTR("Range LOCKED\r\n") : PSTR("Range AUTO\r\n"));
        break;

    case '+':
        /* Range up handled by main loop */
        btn_range_pressed = 1;
        break;

    case '-':
        /* Range down — flag for main loop */
        /* We reuse btn_sel_pressed as range-down trigger from serial */
        btn_sel_pressed = 1;
        break;

    case 'Z':
    case 'z':
        dbm_impedance_idx = (dbm_impedance_idx + 1) % 3;
        uart_puts_P(PSTR("dBm Z: "));
        if (dbm_impedance_idx == 0) uart_puts_P(PSTR("50\r\n"));
        else if (dbm_impedance_idx == 1) uart_puts_P(PSTR("75\r\n"));
        else uart_puts_P(PSTR("600\r\n"));
        break;

    case 'P':
    case 'p':
        uart_puts_P(PSTR("Min: "));
        uart_print_float(min_val, 4);
        uart_puts_P(PSTR("  Max: "));
        uart_print_float(max_val, 4);
        uart_puts_P(PSTR("  Avg: "));
        if (avg_count > 0)
            uart_print_float((float)(avg_sum / (double)avg_count), 4);
        else
            uart_puts_P(PSTR("N/A"));
        uart_puts_P(PSTR("\r\n"));
        break;

    case 'E':
    case 'e':
        /* EEPROM dump handled by logging module — flag for main loop */
        uart_puts_P(PSTR("EEPROM dump:\r\n"));
        /* logging_dump_eeprom() called from main */
        break;

    case '?':
        uart_puts_P(help_text);
        break;

    default:
        break;
    }
}
