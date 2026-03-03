/** @file display_render.c
 *  @brief Fluke 289-style OLED measurement layout renderer.
 */

/* ═══════════════════════════════════════════════════════════════════
 *  Display Renderer — ATmega2560 DTU Digital Multimeter
 *  Fluke 289-style layout on 128x64 SSD1306 OLED
 *
 *  Layout:
 *    y=0-8:   Status bar (mode, range, REL/HLD/LOG/LCK flags)
 *    y=9:     Separator line
 *    y=10-38: Primary reading (large 2x font)
 *    y=39:    Separator line
 *    y=40-47: Secondary info (Min/Max or AC component)
 *    y=48-54: Analog bar graph
 *    y=55-63: Time + status footer
 * ═══════════════════════════════════════════════════════════════════ */

#include "config.h"
#include "display_render.h"
#include "display.h"
#include "measure.h"
#include "rtc_ds1307.h"
#include "timer.h"

#include <stdio.h>
#include <string.h>
#include <avr/pgmspace.h>

/* ─── PROGMEM mode name table ────────────────────────────────────── */

static const char mn_dcv[]   PROGMEM = "DC V";
static const char mn_acv[]   PROGMEM = "AC V";
static const char mn_dcacv[] PROGMEM = "DC+AC";
static const char mn_mvdc[]  PROGMEM = "mV DC";
static const char mn_mvac[]  PROGMEM = "mV AC";
static const char mn_res[]   PROGMEM = "OHM";
static const char mn_lohm[]  PROGMEM = "LO-R";
static const char mn_cond[]  PROGMEM = "nS";
static const char mn_cont[]  PROGMEM = "CONT";
static const char mn_diod[]  PROGMEM = "DIODE";
static const char mn_cap[]   PROGMEM = "CAP";
static const char mn_ind[]   PROGMEM = "IND";
static const char mn_dci[]   PROGMEM = "DC A";
static const char mn_aci[]   PROGMEM = "AC A";
static const char mn_dcaci[] PROGMEM = "DC+ACA";
static const char mn_freq[]  PROGMEM = "FREQ";
static const char mn_duty[]  PROGMEM = "DUTY";
static const char mn_puls[]  PROGMEM = "PULSE";
static const char mn_temp[]  PROGMEM = "TEMP";
static const char mn_dbv[]   PROGMEM = "dBV";
static const char mn_dbm[]   PROGMEM = "dBm";
static const char mn_scope[] PROGMEM = "SCOPE";

static const char * const mode_names[] PROGMEM = {
    mn_dcv, mn_acv, mn_dcacv, mn_mvdc, mn_mvac,
    mn_res, mn_lohm, mn_cond, mn_cont, mn_diod,
    mn_cap, mn_ind, mn_dci, mn_aci, mn_dcaci,
    mn_freq, mn_duty, mn_puls, mn_temp,
    mn_dbv, mn_dbm, mn_scope
};

/* ─── Helper: read mode name from PROGMEM table ──────────────────── */

static void get_mode_name(mode_t mode, char *buf, uint8_t len)
{
    const char *ptr;
    memcpy_P(&ptr, &mode_names[mode], sizeof(const char *));
    strncpy_P(buf, ptr, len - 1);
    buf[len - 1] = '\0';
}

/* ─── Format float to string ─────────────────────────────────────── */

static void float_to_str(float val, uint8_t decimals, char *buf, uint8_t len)
{
    /* Simple manual formatting to avoid heavy sprintf float */
    int neg = 0;
    if (val < 0.0f) {
        neg = 1;
        val = -val;
    }

    uint32_t integer = (uint32_t)val;
    float frac = val - (float)integer;

    /* Build fraction digits */
    uint32_t frac_int = 0;
    float mult = 1.0f;
    for (uint8_t i = 0; i < decimals; i++)
        mult *= 10.0f;
    frac_int = (uint32_t)(frac * mult + 0.5f);

    /* Handle rounding overflow */
    if (decimals > 0) {
        uint32_t frac_max = (uint32_t)mult;
        if (frac_int >= frac_max) {
            frac_int = 0;
            integer++;
        }
    }

    if (decimals > 0) {
        snprintf_P(buf, len, neg ? PSTR("-%lu.%0*lu") : PSTR("%lu.%0*lu"),
                   (unsigned long)integer, decimals, (unsigned long)frac_int);
    } else {
        snprintf_P(buf, len, neg ? PSTR("-%lu") : PSTR("%lu"),
                   (unsigned long)integer);
    }
}

/* ═══════════════════════════════════════════════════════════════════
 *  Render Measurement Screen
 * ═══════════════════════════════════════════════════════════════════ */

void render_measurement(const meas_result_t *r)
{
    display_clear();

    char buf[20];

    /* ─── Status bar (y=0) ─────────────────────────────────────── */
    get_mode_name(current_mode, buf, sizeof(buf));
    display_str(0, 0, buf);

    /* Range indicator */
    if (range_locked) {
        snprintf_P(buf, sizeof(buf), PSTR("R%u LCK"), r->range);
    } else {
        snprintf_P(buf, sizeof(buf), PSTR("R%u"), r->range);
    }
    display_str(50, 0, buf);

    /* Function flags on the right */
    uint8_t fx = 88;
    if (current_func == FUNC_REL)    { display_str_P(fx, 0, PSTR("REL")); fx += 24; }
    if (current_func == FUNC_HOLD)   { display_str_P(fx, 0, PSTR("HLD")); fx += 24; }
    if (current_func == FUNC_MINMAX) { display_str_P(fx, 0, PSTR("M/M")); fx += 24; }
    if (logging_enabled)             { display_str_P(fx, 0, PSTR("LOG")); fx += 24; }
    if (lpf_enabled)                 { display_str_P(fx, 0, PSTR("LPF")); }

    /* Separator line */
    display_hline(0, 9, 128);

    /* ─── Primary reading (y=12, large font) ───────────────────── */
    uint8_t dec = 3;
    if (current_mode == M_FREQ || current_mode == M_TEMP)
        dec = 2;
    else if (current_mode == M_CONTIN || current_mode == M_DIODE)
        dec = 3;
    else if (current_mode == M_DBV || current_mode == M_DBM)
        dec = 1;

    float display_val = r->primary;

    /* Overload display */
    if (r->overload) {
        display_str_large(4, 14, "OL");
    } else {
        float_to_str(display_val, dec, buf, sizeof(buf));
        display_str_large(4, 14, buf);
    }

    /* Unit string to the right of the reading */
    display_str(110, 20, r->unit);

    /* Separator line */
    display_hline(0, 39, 128);

    /* ─── Secondary info (y=41) ────────────────────────────────── */
    if (current_func == FUNC_MINMAX) {
        /* Show Min/Max */
        display_str_P(0, 41, PSTR("Mn:"));
        float_to_str(min_val, 2, buf, sizeof(buf));
        display_str(18, 41, buf);

        display_str_P(68, 41, PSTR("Mx:"));
        float_to_str(max_val, 2, buf, sizeof(buf));
        display_str(86, 41, buf);
    } else if (r->secondary != 0.0f) {
        /* Show secondary value (e.g. AC component) */
        float_to_str(r->secondary, 3, buf, sizeof(buf));
        display_str(0, 41, buf);
    }

    /* ─── Analog bar graph (y=48-54) ───────────────────────────── */
    /* Map primary to 0-100% based on expected range */
    uint8_t percent = 0;
    if (!r->overload && display_val >= 0.0f) {
        /* Normalize to percentage (assume full scale around 5V / 100%) */
        float fs;
        switch (current_mode) {
        case M_DCV:  case M_ACV:  case M_DCACV:
            fs = 55.0f; break;
        case M_MV_DC: case M_MV_AC:
            fs = 5000.0f; break;
        case M_TEMP:
            fs = 110.0f; break;
        case M_DUTY:
            fs = 100.0f; break;
        default:
            fs = display_val * 2.0f;  /* auto-scale */
            if (fs < 1.0f) fs = 1.0f;
            break;
        }
        float pct = display_val / fs * 100.0f;
        if (pct > 100.0f) pct = 100.0f;
        if (pct < 0.0f) pct = 0.0f;
        percent = (uint8_t)pct;
    }
    display_bar(0, 48, 128, 6, percent);

    /* ─── Footer (y=56) ────────────────────────────────────────── */
    rtc_time_t t;
    rtc_read(&t);
    rtc_format_time(&t, buf);
    display_str(0, 56, buf);

    /* Log entry count if logging */
    if (logging_enabled) {
        display_str_P(80, 56, PSTR("LOG"));
    }

    /* AUTO or LOCK indicator */
    if (range_locked)
        display_str_P(104, 56, PSTR("LOCK"));
    else
        display_str_P(104, 56, PSTR("AUTO"));

    display_flush();
}

/* ═══════════════════════════════════════════════════════════════════
 *  Render Scope Screen (placeholder — full impl in scope.c)
 * ═══════════════════════════════════════════════════════════════════ */

void render_scope(void)
{
    /* Scope rendering is handled by scope_render_oled() which
     * writes directly into the framebuffer. This function just
     * adds the status bar and measurements overlay. */
    display_clear();

    /* Status bar */
    display_str_P(0, 0, PSTR("SCOPE"));

    /* Timebase info */
    display_str_P(42, 0, PSTR("AUTO"));

    /* Waveform area (y=10-49) rendered by scope module */

    /* Auto-measurements footer */
    display_str_P(0, 52, PSTR("Vp:"));
    display_str_P(0, 58, PSTR("f:"));

    display_flush();
}

/* ═══════════════════════════════════════════════════════════════════
 *  Splash Screen
 * ═══════════════════════════════════════════════════════════════════ */

void render_splash(void)
{
    display_clear();
    display_str_P(20, 10, PSTR("DTU Multimeter"));
    display_str_P(28, 24, PSTR("v1.0  2026"));
    display_str_P(16, 40, PSTR("ATmega2560  16MHz"));
    display_str_P(22, 52, PSTR("Initializing..."));
    display_flush();
}
