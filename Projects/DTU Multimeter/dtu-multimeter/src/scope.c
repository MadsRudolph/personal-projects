/** @file scope.c
 *  @brief 1000-sample oscilloscope using ATmega internal ADC at 77 ksps.
 */

/* ═══════════════════════════════════════════════════════════════════
 *  Oscilloscope Module — ATmega2560 DTU Digital Multimeter
 *  Bare-metal 10-bit ADC capture with triggering, auto-measurement,
 *  OLED rendering, ASCII waveform output, and binary dump.
 *  All strings stored in PROGMEM.
 * ═══════════════════════════════════════════════════════════════════ */

#include "config.h"
#include "scope.h"
#include "adc_mcp3208.h"
#include "uart.h"
#include "timer.h"
#include "display.h"

#include <math.h>
#include <string.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <util/delay.h>

/* ─── PROGMEM string literals ────────────────────────────────────── */

static const char str_scope_init[]   PROGMEM = "[SCOPE] init\r\n";
static const char str_trig_auto[]    PROGMEM = "AUTO";
static const char str_trig_rise[]    PROGMEM = "RISE";
static const char str_trig_fall[]    PROGMEM = "FALL";
static const char str_trig_none[]    PROGMEM = "FREE";
static const char str_trig_single[]  PROGMEM = "SNGL";
static const char str_tb_label[]     PROGMEM = "TB:";
static const char str_tl_label[]     PROGMEM = "TL:";
static const char str_vpp_label[]    PROGMEM = "Vpp=";
static const char str_freq_label[]   PROGMEM = "f=";
static const char str_hz_unit[]      PROGMEM = "Hz";
static const char str_khz_unit[]     PROGMEM = "kHz";
static const char str_v_unit[]       PROGMEM = "V";
static const char str_ascii_top[]    PROGMEM = "+";
static const char str_ascii_bar[]    PROGMEM = "|";
static const char str_ascii_dash[]   PROGMEM = "-";
static const char str_newline[]      PROGMEM = "\r\n";

/* Trigger mode name table (PROGMEM pointers) */
static const char * const trig_names[] PROGMEM = {
    str_trig_auto, str_trig_rise, str_trig_fall,
    str_trig_none, str_trig_single
};

/* ─── Timebase configuration ─────────────────────────────────────── */

/* Each entry: { ADCSRA prescaler bits, inter-sample delay in us }
 *  Index 0 = fastest (~77 ksps, prescaler /16, ~13 us/sample)
 *  Higher indices add inter-sample delays for slower timebases       */
typedef struct {
    uint8_t  adps;          /* ADPS[2:0] prescaler bits              */
    uint16_t delay_us;      /* Additional delay between samples (us) */
} timebase_cfg_t;

static const timebase_cfg_t tb_table[] PROGMEM = {
    { 0x04,     0 },        /* /16   ~77 ksps   13 us/sample        */
    { 0x05,     0 },        /* /32   ~38 ksps   26 us/sample        */
    { 0x06,     0 },        /* /64   ~19 ksps   52 us/sample        */
    { 0x07,     0 },        /* /128  ~9.6 ksps  104 us/sample       */
    { 0x04,    50 },        /* /16 + 50 us  ~15.9 ksps              */
    { 0x04,   200 },        /* /16 + 200 us ~4.7 ksps               */
    { 0x04,  1000 },        /* /16 + 1 ms   ~987 sps                */
    { 0x04,  5000 },        /* /16 + 5 ms   ~199 sps                */
};

#define TB_COUNT  (sizeof(tb_table) / sizeof(tb_table[0]))

/* ─── Sample period lookup (microseconds, PROGMEM) ───────────────── */

static const float tb_period_us[] PROGMEM = {
    13.0f, 26.0f, 52.0f, 104.0f,
    63.0f, 213.0f, 1013.0f, 5013.0f
};

/* ─── Global scope state ─────────────────────────────────────────── */

uint16_t          scope_buf[SCOPE_BUF_SIZE];
volatile uint8_t  scope_running      = 0;
trig_mode_t       scope_trig_mode    = TRIG_AUTO;
uint16_t          scope_trig_level   = 512;     /* Mid-scale default */
uint8_t           scope_timebase     = 0;       /* Fastest           */
uint8_t           scope_ac_coupling  = 0;       /* DC coupling       */
uint8_t           scope_use_internal_adc = 1;   /* ATmega ADC        */

/* ─── Internal state ─────────────────────────────────────────────── */

static uint16_t dc_offset = 0;                  /* For AC coupling   */

/* ─── PROGMEM float read helper ──────────────────────────────────── */

static float pgm_read_float_near(const float *addr)
{
    float val;
    memcpy_P(&val, addr, sizeof(float));
    return val;
}

/* ─── PROGMEM timebase config read helper ────────────────────────── */

static void tb_read(uint8_t idx, timebase_cfg_t *cfg)
{
    memcpy_P(cfg, &tb_table[idx], sizeof(timebase_cfg_t));
}

/* ═══════════════════════════════════════════════════════════════════
 *  Internal ADC Helpers (ATmega2560 ADC, channel 8 = A8)
 * ═══════════════════════════════════════════════════════════════════ */

static void internal_adc_init(void)
{
    /* AVCC reference, right-adjusted result */
    ADMUX = (1 << REFS0);

    /* Channel 8 → MUX[4:0] = 01000
     *  MUX[3:0] = 0000 in ADMUX (low nibble)
     *  MUX5 = 1 in ADCSRB for channels 8-15                         */
    ADMUX  = (ADMUX & 0xE0) | (SCOPE_ADC_CH & 0x07);
    ADCSRB = (SCOPE_ADC_CH >= 8) ? (1 << MUX5) : 0;

    /* Enable ADC, prescaler /16 for fast conversion (~77 ksps)
     *  ADEN | ADPS2 = 0x84 + ADPS bits from timebase                */
    ADCSRA = (1 << ADEN) | 0x04;  /* /16 default, updated per timebase */
}

static inline void internal_adc_set_prescaler(uint8_t adps)
{
    ADCSRA = (1 << ADEN) | (adps & 0x07);
}

static inline uint16_t internal_adc_read(void)
{
    ADCSRA |= (1 << ADSC);                 /* Start conversion       */
    while (ADCSRA & (1 << ADSC))            /* Wait for completion    */
        ;
    return ADC;                             /* 10-bit result          */
}

/* ─── Sample one value (internal or MCP3208) ─────────────────────── */

static inline uint16_t scope_read_sample(void)
{
    if (scope_use_internal_adc)
        return internal_adc_read();
    else
        return adc_read_raw(ADC_CH_SCOPE) >> 2;  /* 12-bit → 10-bit  */
}

/* ═══════════════════════════════════════════════════════════════════
 *  Initialisation
 * ═══════════════════════════════════════════════════════════════════ */

void scope_init(void)
{
    memset(scope_buf, 0, sizeof(scope_buf));
    scope_running        = 0;
    scope_trig_mode      = TRIG_AUTO;
    scope_trig_level     = 512;
    scope_timebase       = 0;
    scope_ac_coupling    = 0;
    scope_use_internal_adc = 1;
    dc_offset            = 0;

    if (scope_use_internal_adc)
        internal_adc_init();

    uart_puts_P(str_scope_init);
}

/* ═══════════════════════════════════════════════════════════════════
 *  Trigger Configuration
 * ═══════════════════════════════════════════════════════════════════ */

void scope_set_trigger(trig_mode_t mode)
{
    if (mode < TRIG_COUNT)
        scope_trig_mode = mode;
}

void scope_set_trigger_level(uint16_t level)
{
    if (level <= 1023)
        scope_trig_level = level;
}

void scope_adjust_trigger(int8_t delta)
{
    int16_t new_level = (int16_t)scope_trig_level + (int16_t)delta * 10;
    if (new_level < 0)    new_level = 0;
    if (new_level > 1023) new_level = 1023;
    scope_trig_level = (uint16_t)new_level;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Timebase Configuration
 * ═══════════════════════════════════════════════════════════════════ */

void scope_set_timebase(uint8_t tb)
{
    if (tb < TB_COUNT)
        scope_timebase = tb;
}

void scope_adjust_timebase(int8_t delta)
{
    int8_t new_tb = (int8_t)scope_timebase + delta;
    if (new_tb < 0)               new_tb = 0;
    if (new_tb >= (int8_t)TB_COUNT) new_tb = TB_COUNT - 1;
    scope_timebase = (uint8_t)new_tb;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Inter-sample delay (variable, from timebase table)
 * ═══════════════════════════════════════════════════════════════════ */

static void sample_delay(uint16_t us)
{
    /* _delay_us() needs a compile-time constant, so we loop in 10 us
     * chunks for the variable portion.  The granularity is acceptable
     * for the slower timebases where this is used.                   */
    while (us >= 10) {
        _delay_us(10);
        us -= 10;
    }
    /* Residual 0-9 us — close enough, the ADC conversion time
     * already adds ~13 us of jitter at prescaler /16.               */
}

/* ═══════════════════════════════════════════════════════════════════
 *  Capture Engine
 * ═══════════════════════════════════════════════════════════════════ */

void scope_capture(void)
{
    timebase_cfg_t tb_cfg;
    tb_read(scope_timebase, &tb_cfg);

    /* Apply ADC prescaler for this timebase */
    if (scope_use_internal_adc)
        internal_adc_set_prescaler(tb_cfg.adps);

    /* ── Step 1: AC coupling DC offset removal ────────────────────── */

    if (scope_ac_coupling) {
        uint32_t sum = 0;
        for (uint8_t i = 0; i < 64; i++)
            sum += scope_read_sample();
        dc_offset = (uint16_t)(sum >> 6);
    } else {
        dc_offset = 0;
    }

    /* ── Step 2: Fill pre-trigger buffer (circular) ───────────────── */

    uint16_t pre_idx = 0;
    for (uint16_t i = 0; i < SCOPE_PRETRIG; i++) {
        scope_buf[i] = scope_read_sample();
        if (tb_cfg.delay_us)
            sample_delay(tb_cfg.delay_us);
    }
    pre_idx = SCOPE_PRETRIG;  /* Next write position in pre-trig area */

    /* ── Step 3: Wait for trigger ─────────────────────────────────── */

    uint8_t  triggered    = 0;
    uint16_t trig_pos     = 0;     /* Index in scope_buf where trigger found */
    uint16_t prev_sample  = scope_buf[SCOPE_PRETRIG - 1];
    uint32_t trig_timeout = millis() + 500;  /* 500 ms auto-trigger timeout */

    if (scope_trig_mode == TRIG_NONE) {
        /* Free-run: no triggering, start post-trigger immediately    */
        triggered = 1;
        trig_pos  = SCOPE_PRETRIG;
    } else {
        /* Scan for edge crossing trigger level in incoming samples   */
        while (!triggered) {
            uint16_t s = scope_read_sample();
            if (tb_cfg.delay_us)
                sample_delay(tb_cfg.delay_us);

            /* Overwrite oldest pre-trigger sample (circular) */
            if (pre_idx >= SCOPE_PRETRIG)
                pre_idx = 0;
            scope_buf[pre_idx] = s;
            pre_idx++;

            /* Edge detection */
            if (scope_trig_mode == TRIG_RISING || scope_trig_mode == TRIG_AUTO ||
                scope_trig_mode == TRIG_SINGLE) {
                /* Rising edge: previous below level, current at or above */
                if (prev_sample < scope_trig_level && s >= scope_trig_level) {
                    triggered = 1;
                    trig_pos  = SCOPE_PRETRIG;
                }
            }
            if (!triggered &&
                (scope_trig_mode == TRIG_FALLING)) {
                /* Falling edge: previous above level, current at or below */
                if (prev_sample > scope_trig_level && s <= scope_trig_level) {
                    triggered = 1;
                    trig_pos  = SCOPE_PRETRIG;
                }
            }

            prev_sample = s;

            /* Auto mode: capture anyway on timeout */
            if (!triggered && (scope_trig_mode == TRIG_AUTO || scope_trig_mode == TRIG_SINGLE)) {
                if (millis() > trig_timeout) {
                    triggered = 1;
                    trig_pos  = SCOPE_PRETRIG;
                }
            }
        }

        /* Unroll circular pre-trigger buffer so sample 0 is oldest.
         * pre_idx points to the next write slot = oldest sample.      */
        if (pre_idx < SCOPE_PRETRIG && pre_idx != 0) {
            uint16_t tmp[SCOPE_PRETRIG];
            memcpy(tmp, scope_buf, SCOPE_PRETRIG * sizeof(uint16_t));
            uint16_t tail = SCOPE_PRETRIG - pre_idx;
            memcpy(scope_buf, &tmp[pre_idx], tail * sizeof(uint16_t));
            memcpy(&scope_buf[tail], tmp, pre_idx * sizeof(uint16_t));
        }
    }

    /* ── Step 4: Fill post-trigger samples ────────────────────────── */

    uint16_t post_count = SCOPE_BUF_SIZE - SCOPE_PRETRIG;
    for (uint16_t i = 0; i < post_count; i++) {
        scope_buf[SCOPE_PRETRIG + i] = scope_read_sample();
        if (tb_cfg.delay_us)
            sample_delay(tb_cfg.delay_us);
    }

    /* ── Step 5: Apply AC coupling offset removal ─────────────────── */

    if (scope_ac_coupling && dc_offset > 0) {
        for (uint16_t i = 0; i < SCOPE_BUF_SIZE; i++) {
            int16_t val = (int16_t)scope_buf[i] - (int16_t)dc_offset + 512;
            if (val < 0)    val = 0;
            if (val > 1023) val = 1023;
            scope_buf[i] = (uint16_t)val;
        }
    }
}

/* ═══════════════════════════════════════════════════════════════════
 *  Single-Shot Capture
 * ═══════════════════════════════════════════════════════════════════ */

void scope_single_shot(void)
{
    scope_running = 1;
    scope_capture();
    scope_running = 0;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Auto-Measurements (Vpp, Vavg, Vrms, Frequency, Duty Cycle)
 * ═══════════════════════════════════════════════════════════════════ */

void scope_auto_measure(scope_meas_t *m)
{
    uint16_t min_val = 1023;
    uint16_t max_val = 0;
    uint32_t sum     = 0;
    double   sum_sq  = 0.0;

    /* ── Pass 1: min, max, sum, sum-of-squares ────────────────────── */

    for (uint16_t i = 0; i < SCOPE_BUF_SIZE; i++) {
        uint16_t s = scope_buf[i];
        if (s < min_val) min_val = s;
        if (s > max_val) max_val = s;
        sum    += s;
        sum_sq += (double)s * (double)s;
    }

    float scale = V_REF / 1023.0f;

    /* Vpp */
    m->vpp  = (float)(max_val - min_val) * scale;

    /* Vavg */
    float avg_raw = (float)sum / (float)SCOPE_BUF_SIZE;
    m->vavg = avg_raw * scale;

    /* Vrms */
    float mean_sq = (float)(sum_sq / (double)SCOPE_BUF_SIZE);
    m->vrms = sqrtf(mean_sq) * scale;

    /* ── Pass 2: zero-crossing frequency and duty cycle ───────────── */

    uint16_t midpoint       = (min_val + max_val) / 2;
    uint16_t crossings      = 0;
    uint16_t above_count    = 0;

    for (uint16_t i = 1; i < SCOPE_BUF_SIZE; i++) {
        /* Count rising zero crossings around midpoint */
        if (scope_buf[i - 1] < midpoint && scope_buf[i] >= midpoint)
            crossings++;
        if (scope_buf[i] >= midpoint)
            above_count++;
    }
    /* Check first sample too for duty */
    if (scope_buf[0] >= midpoint)
        above_count++;

    /* Sample period from timebase table */
    float t_sample = pgm_read_float_near(&tb_period_us[scope_timebase]);
    float total_time_s = t_sample * (float)SCOPE_BUF_SIZE / 1e6f;

    /* Frequency: rising crossings / total time */
    if (crossings >= 2)
        m->freq = (float)crossings / total_time_s;
    else
        m->freq = 0.0f;

    /* Duty cycle: percentage of samples above midpoint */
    m->duty = (float)above_count / (float)SCOPE_BUF_SIZE * 100.0f;
}

/* ═══════════════════════════════════════════════════════════════════
 *  OLED Rendering (128x64 SSD1306 framebuffer)
 * ═══════════════════════════════════════════════════════════════════ */

/* Waveform area: x=0..127, y=10..49 (40 pixels height)
 * Top 10 rows: status text
 * Bottom 14 rows: measurement readout                                */

#define WAVE_Y_MIN  10
#define WAVE_Y_MAX  49
#define WAVE_HEIGHT (WAVE_Y_MAX - WAVE_Y_MIN)
#define OLED_COLS   128

static inline void fb_set_pixel(uint8_t *fb, uint8_t x, uint8_t y)
{
    if (x >= OLED_WIDTH || y >= OLED_HEIGHT)
        return;
    fb[x + (y / 8) * OLED_WIDTH] |= (1 << (y & 7));
}

static void fb_draw_char(uint8_t *fb, uint8_t x, uint8_t y, char c)
{
    /* Delegate to display module — we just set pixels for waveform   */
    (void)fb; (void)x; (void)y; (void)c;
    /* Text rendering uses display_char() on the shared framebuffer   */
}

void scope_render_oled(uint8_t *fb)
{
    /* ── Find buffer min/max for scaling ──────────────────────────── */

    uint16_t buf_min = 1023, buf_max = 0;
    for (uint16_t i = 0; i < SCOPE_BUF_SIZE; i++) {
        if (scope_buf[i] < buf_min) buf_min = scope_buf[i];
        if (scope_buf[i] > buf_max) buf_max = scope_buf[i];
    }
    uint16_t range = buf_max - buf_min;
    if (range == 0) range = 1;  /* Avoid division by zero */

    /* ── Draw grid dots (every 16 pixels horizontally, 10 vertically) */

    for (uint8_t gx = 0; gx < OLED_COLS; gx += 16) {
        for (uint8_t gy = WAVE_Y_MIN; gy <= WAVE_Y_MAX; gy += 10)
            fb_set_pixel(fb, gx, gy);
    }

    /* ── Draw trigger level dashed line ───────────────────────────── */

    uint8_t trig_y;
    {
        int16_t tl = (int16_t)scope_trig_level - (int16_t)buf_min;
        if (tl < 0) tl = 0;
        if (tl > (int16_t)range) tl = (int16_t)range;
        trig_y = WAVE_Y_MAX - (uint8_t)((uint32_t)tl * WAVE_HEIGHT / range);
    }
    for (uint8_t x = 0; x < OLED_COLS; x += 4)
        fb_set_pixel(fb, x, trig_y);

    /* ── Draw waveform: 128 columns from 1000 samples (decimate) ─── */

    uint8_t prev_y = 0;
    for (uint8_t x = 0; x < OLED_COLS; x++) {
        /* Map column x to buffer index */
        uint16_t buf_idx = (uint16_t)x * SCOPE_BUF_SIZE / OLED_COLS;
        if (buf_idx >= SCOPE_BUF_SIZE) buf_idx = SCOPE_BUF_SIZE - 1;

        /* Scale sample to waveform Y range (inverted: higher value = lower Y) */
        int16_t  s   = (int16_t)scope_buf[buf_idx] - (int16_t)buf_min;
        uint8_t  y   = WAVE_Y_MAX - (uint8_t)((uint32_t)s * WAVE_HEIGHT / range);

        /* Clamp */
        if (y < WAVE_Y_MIN) y = WAVE_Y_MIN;
        if (y > WAVE_Y_MAX) y = WAVE_Y_MAX;

        fb_set_pixel(fb, x, y);

        /* Draw vertical line segment between consecutive points for
         * continuous waveform appearance                              */
        if (x > 0) {
            uint8_t y0 = (prev_y < y) ? prev_y : y;
            uint8_t y1 = (prev_y < y) ? y : prev_y;
            for (uint8_t yy = y0 + 1; yy < y1; yy++)
                fb_set_pixel(fb, x, yy);
        }
        prev_y = y;
    }

    /* ── Top status bar: trigger mode, timebase, trigger level ────── */

    {
        /* Trigger mode name */
        const char *tname;
        memcpy_P(&tname, &trig_names[scope_trig_mode], sizeof(const char *));
        display_str_P(0, 0, tname);

        /* Timebase index */
        display_str_P(30, 0, str_tb_label);
        display_char(48, 0, '0' + scope_timebase);

        /* Trigger level */
        display_str_P(60, 0, str_tl_label);
        /* 4-digit trigger level number */
        uint16_t tl = scope_trig_level;
        display_char(78, 0, '0' + (tl / 1000) % 10);
        display_char(84, 0, '0' + (tl / 100)  % 10);
        display_char(90, 0, '0' + (tl / 10)   % 10);
        display_char(96, 0, '0' + tl % 10);
    }

    /* ── Bottom: Vpp and frequency ────────────────────────────────── */

    {
        scope_meas_t m;
        scope_auto_measure(&m);

        display_str_P(0, 56, str_vpp_label);
        /* Simple Vpp display: X.XX V */
        uint16_t vpp_mv = (uint16_t)(m.vpp * 1000.0f);
        display_char(24, 56, '0' + (vpp_mv / 1000) % 10);
        display_char(30, 56, '.');
        display_char(36, 56, '0' + (vpp_mv / 100) % 10);
        display_char(42, 56, '0' + (vpp_mv / 10)  % 10);
        display_str_P(48, 56, str_v_unit);

        display_str_P(64, 56, str_freq_label);
        if (m.freq >= 1000.0f) {
            uint16_t f_10 = (uint16_t)(m.freq / 100.0f);  /* freq in 0.1 kHz */
            display_char(76, 56, '0' + (f_10 / 100) % 10);
            display_char(82, 56, '0' + (f_10 / 10)  % 10);
            display_char(88, 56, '.');
            display_char(94, 56, '0' + f_10 % 10);
            display_str_P(100, 56, str_khz_unit);
        } else {
            uint16_t f_hz = (uint16_t)m.freq;
            display_char(76, 56, '0' + (f_hz / 10000) % 10);
            display_char(82, 56, '0' + (f_hz / 1000)  % 10);
            display_char(88, 56, '0' + (f_hz / 100)   % 10);
            display_char(94, 56, '0' + (f_hz / 10)    % 10);
            display_char(100, 56, '0' + f_hz % 10);
            display_str_P(106, 56, str_hz_unit);
        }
    }
}

/* ═══════════════════════════════════════════════════════════════════
 *  ASCII Waveform (80x24) via UART
 * ═══════════════════════════════════════════════════════════════════ */

#define ASCII_COLS  80
#define ASCII_ROWS  24

void scope_print_ascii(void)
{
    /* Find buffer min/max */
    uint16_t buf_min = 1023, buf_max = 0;
    for (uint16_t i = 0; i < SCOPE_BUF_SIZE; i++) {
        if (scope_buf[i] < buf_min) buf_min = scope_buf[i];
        if (scope_buf[i] > buf_max) buf_max = scope_buf[i];
    }
    uint16_t range = buf_max - buf_min;
    if (range == 0) range = 1;

    /* Build row-mapped column array (which row each column maps to) */
    uint8_t col_row[ASCII_COLS];
    for (uint8_t c = 0; c < ASCII_COLS; c++) {
        uint16_t idx = (uint16_t)c * SCOPE_BUF_SIZE / ASCII_COLS;
        if (idx >= SCOPE_BUF_SIZE) idx = SCOPE_BUF_SIZE - 1;
        int16_t  s   = (int16_t)scope_buf[idx] - (int16_t)buf_min;
        /* Row 0 = top = max, row (ROWS-1) = bottom = min */
        col_row[c] = (ASCII_ROWS - 1) - (uint8_t)((uint32_t)s * (ASCII_ROWS - 1) / range);
    }

    /* Trigger level row */
    int16_t tl_s = (int16_t)scope_trig_level - (int16_t)buf_min;
    if (tl_s < 0) tl_s = 0;
    if (tl_s > (int16_t)range) tl_s = (int16_t)range;
    uint8_t trig_row = (ASCII_ROWS - 1) - (uint8_t)((uint32_t)tl_s * (ASCII_ROWS - 1) / range);

    /* Print top border */
    uart_puts_P(str_ascii_top);
    for (uint8_t c = 0; c < ASCII_COLS; c++)
        uart_puts_P(str_ascii_dash);
    uart_puts_P(str_ascii_top);
    uart_puts_P(str_newline);

    /* Print each row */
    for (uint8_t r = 0; r < ASCII_ROWS; r++) {
        uart_puts_P(str_ascii_bar);
        for (uint8_t c = 0; c < ASCII_COLS; c++) {
            if (col_row[c] == r)
                uart_putc('*');
            else if (r == trig_row && (c & 3) == 0)
                uart_putc('-');
            else if (c == 0 || c == ASCII_COLS / 2)
                uart_putc(':');
            else if (r == ASCII_ROWS / 2 && (c & 7) == 0)
                uart_putc('.');
            else
                uart_putc(' ');
        }
        uart_puts_P(str_ascii_bar);
        uart_puts_P(str_newline);
    }

    /* Print bottom border */
    uart_puts_P(str_ascii_top);
    for (uint8_t c = 0; c < ASCII_COLS; c++)
        uart_puts_P(str_ascii_dash);
    uart_puts_P(str_ascii_top);
    uart_puts_P(str_newline);

    /* Print measurements below */
    scope_meas_t m;
    scope_auto_measure(&m);

    uart_puts_P(str_vpp_label);
    uart_print_float(m.vpp, 3);
    uart_puts_P(str_v_unit);
    uart_putc(' ');
    uart_puts_P(str_freq_label);
    uart_print_float(m.freq, 1);
    uart_puts_P(str_hz_unit);
    uart_puts_P(str_newline);
}

/* ═══════════════════════════════════════════════════════════════════
 *  Binary Dump (for Python GUI)
 *  Protocol: 'S' | buf[0] low | buf[0] high | ... | buf[999] high | 'E'
 * ═══════════════════════════════════════════════════════════════════ */

void scope_dump_binary(void)
{
    uart_putc('S');

    for (uint16_t i = 0; i < SCOPE_BUF_SIZE; i++) {
        uart_putc((char)(scope_buf[i] & 0xFF));         /* Low byte  */
        uart_putc((char)((scope_buf[i] >> 8) & 0xFF));  /* High byte */
    }

    uart_putc('E');
}
