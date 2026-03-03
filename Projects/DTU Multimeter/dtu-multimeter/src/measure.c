/** @file measure.c
 *  @brief Measurement engine for 22 modes with auto-ranging and secondary functions.
 */

/* ═══════════════════════════════════════════════════════════════════
 *  Measurement Engine — ATmega2560 DTU Digital Multimeter
 *  22 measurement modes with auto-ranging and secondary functions
 * ═══════════════════════════════════════════════════════════════════ */

#include "config.h"
#include "measure.h"
#include "adc_mcp3208.h"
#include "mux.h"
#include "autorange.h"
#include "trms.h"
#include "timer.h"

#include <math.h>
#include <string.h>
#include <avr/pgmspace.h>

/* ─── Reference resistor lookup table ────────────────────────────── */

static const float rref[N_RES_RANGES] PROGMEM = {
    RREF_0, RREF_1, RREF_2, RREF_3,
    RREF_4, RREF_5, RREF_6, RREF_7
};

/* ─── Current shunt lookup table ─────────────────────────────────── */

static const float ishunt[N_CUR_RANGES] PROGMEM = {
    ISHUNT_0, ISHUNT_1, ISHUNT_2, ISHUNT_3, ISHUNT_4, ISHUNT_5
};

/* ─── Capacitance charge resistor lookup ─────────────────────────── */

static const float cap_r[N_CAP_RANGES] PROGMEM = {
    CAP_R0, CAP_R1, CAP_R2
};

/* ─── Inductance series resistor lookup ──────────────────────────── */

static const float ind_r[N_IND_RANGES] PROGMEM = {
    IND_R0, IND_R1, IND_R2
};

static const uint8_t ind_mux[N_IND_RANGES] PROGMEM = {
    IND_MUX_CH0, IND_MUX_CH1, IND_MUX_CH2
};

/* ─── dBm impedance options ──────────────────────────────────────── */

static const float dbm_z[] PROGMEM = { 50.0f, 75.0f, 600.0f };

/* ─── Global measurement state ───────────────────────────────────── */

volatile mode_t      current_mode     = M_DCV;
volatile func_mode_t current_func     = FUNC_NONE;
uint8_t              range_locked     = 0;
uint8_t              lpf_enabled      = 0;
uint8_t              logging_enabled  = 0;
float                rel_reference    = 0.0f;
float                min_val, max_val;
double               avg_sum          = 0.0;
uint32_t             avg_count        = 0;
uint8_t              dbm_impedance_idx = 0;

/* ─── Per-mode range indices ─────────────────────────────────────── */

static uint8_t res_range = 2;   /* start at 5k range     */
static uint8_t cur_range = 2;   /* start at 50mA range   */
static uint8_t cap_range = 0;   /* start at 1M (large C) */
static uint8_t ind_range = 1;   /* start at 499 Ohm (medium L) */

/* ─── Low-pass filter state ──────────────────────────────────────── */

static float lpf_prev = 0.0f;

static float apply_lpf(float val)
{
    if (!lpf_enabled)
        return val;
    lpf_prev = LPF_ALPHA * val + (1.0f - LPF_ALPHA) * lpf_prev;
    return lpf_prev;
}

/* ─── PROGMEM float read helper ──────────────────────────────────── */

static float read_pgm_float(const float *addr)
{
    float val;
    memcpy_P(&val, addr, sizeof(float));
    return val;
}

/* ─── Helper: format unit string ─────────────────────────────────── */

static void set_unit(meas_result_t *r, const char *u)
{
    strncpy(r->unit, u, sizeof(r->unit) - 1);
    r->unit[sizeof(r->unit) - 1] = '\0';
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 0: DC Voltage
 * ═══════════════════════════════════════════════════════════════════ */

void meas_dcv(meas_result_t *r)
{
    /* Try low range first (direct, 0-5V, better resolution) */
    uint16_t raw_lo = adc_read_oversample(ADC_CH_VOLT_LO);
    float v_lo = adc_to_voltage_os(raw_lo);

    if (v_lo < 4.5f) {
        r->primary = apply_lpf(v_lo);
        set_unit(r, "V");
        r->overload = 0;
    } else {
        /* High range via voltage divider */
        uint16_t raw_hi = adc_read_oversample(ADC_CH_VOLT_HI);
        float v_hi = adc_to_voltage_os(raw_hi) * VDIV_RATIO;
        r->primary = apply_lpf(v_hi);
        set_unit(r, "V");
        r->overload = (v_hi > 54.0f) ? 1 : 0;
    }
    r->secondary = 0.0f;
    r->range = (r->primary < 4.5f) ? 0 : 1;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 1: AC Voltage True-RMS
 * ═══════════════════════════════════════════════════════════════════ */

void meas_acv(meas_result_t *r)
{
    trms_result_t trms;
    trms_measure(ADC_CH_VOLT_LO, &trms);
    r->primary   = apply_lpf(trms.ac);
    r->secondary = trms.dc;
    set_unit(r, "V");
    r->overload  = (trms.peak_pos > 4.9f) ? 1 : 0;
    r->range     = 0;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 2: DC+AC Voltage Combined
 * ═══════════════════════════════════════════════════════════════════ */

void meas_dcacv(meas_result_t *r)
{
    trms_result_t trms;
    trms_measure(ADC_CH_VOLT_LO, &trms);
    r->primary   = apply_lpf(trms.rms);
    r->secondary = trms.ac;
    set_unit(r, "V");
    r->overload  = (trms.peak_pos > 4.9f) ? 1 : 0;
    r->range     = 0;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 3: mV DC
 * ═══════════════════════════════════════════════════════════════════ */

void meas_mv_dc(meas_result_t *r)
{
    uint16_t raw = adc_read_oversample(ADC_CH_VOLT_LO);
    float v = adc_to_voltage_os(raw);
    r->primary   = apply_lpf(v * 1000.0f);
    r->secondary = 0.0f;
    set_unit(r, "mV");
    r->overload  = (v > 4.9f) ? 1 : 0;
    r->range     = 0;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 4: mV AC
 * ═══════════════════════════════════════════════════════════════════ */

void meas_mv_ac(meas_result_t *r)
{
    trms_result_t trms;
    trms_measure(ADC_CH_VOLT_LO, &trms);
    r->primary   = apply_lpf(trms.ac * 1000.0f);
    r->secondary = trms.dc * 1000.0f;
    set_unit(r, "mV");
    r->overload  = 0;
    r->range     = 0;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 5: Resistance (8 auto-ranges)
 * ═══════════════════════════════════════════════════════════════════ */

void meas_resistance(meas_result_t *r)
{
    /* Select reference resistor via mux */
    mux_select(res_range);

    uint16_t raw = adc_read_oversample(ADC_CH_RESIST);
    float v = adc_to_voltage_os(raw);
    float ref = read_pgm_float(&rref[res_range]);

    /* R_unknown = R_ref * V_adc / (V_REF - V_adc) */
    float denom = V_REF - v;
    if (denom < 0.001f) {
        r->primary  = 99999999.0f;
        r->overload = 1;
    } else {
        r->primary  = apply_lpf(ref * v / denom);
        r->overload = 0;
    }

    /* Auto-range (unless locked) */
    if (!range_locked && !autorange_settling()) {
        uint16_t raw12 = adc_read_raw(ADC_CH_RESIST);
        int8_t delta = autorange_check(raw12);
        uint8_t new_range = autorange_clamp(res_range, delta, N_RES_RANGES);
        if (new_range != res_range) {
            res_range = new_range;
            autorange_settle_start();
        }
    }

    /* Format unit based on magnitude */
    if (r->primary >= 1e6f) {
        r->primary /= 1e6f;
        set_unit(r, "MOhm");
        r->prefix = 'M';
    } else if (r->primary >= 1e3f) {
        r->primary /= 1e3f;
        set_unit(r, "kOhm");
        r->prefix = 'k';
    } else {
        set_unit(r, "Ohm");
        r->prefix = ' ';
    }
    r->secondary = 0.0f;
    r->range = res_range;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 6: Low Ohms (NE555 constant current)
 * ═══════════════════════════════════════════════════════════════════ */

void meas_low_ohm(meas_result_t *r)
{
    isrc_enable();

    /* Small delay for current to stabilize */
    uint32_t start = millis();
    while (millis() - start < 10)
        ;

    uint16_t raw = adc_read_oversample(ADC_CH_RESIST);
    float v = adc_to_voltage_os(raw);

    isrc_disable();

    /* R = V / I_SOURCE */
    r->primary   = apply_lpf(v / I_SOURCE);
    r->secondary = 0.0f;
    set_unit(r, "Ohm");
    r->prefix    = ' ';
    r->overload  = 0;
    r->range     = 0;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 7: Conductance (nS)
 * ═══════════════════════════════════════════════════════════════════ */

void meas_conductance(meas_result_t *r)
{
    /* Use highest resistance range */
    mux_select(N_RES_RANGES - 1);

    uint16_t raw = adc_read_oversample(ADC_CH_RESIST);
    float v = adc_to_voltage_os(raw);
    float ref = read_pgm_float(&rref[N_RES_RANGES - 1]);

    float denom = V_REF - v;
    float resistance;
    if (denom < 0.001f)
        resistance = 99999999.0f;
    else
        resistance = ref * v / denom;

    /* G = 1/R in nanoSiemens */
    r->primary   = apply_lpf(1.0e9f / resistance);
    r->secondary = resistance;
    set_unit(r, "nS");
    r->prefix    = ' ';
    r->overload  = 0;
    r->range     = N_RES_RANGES - 1;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 8: Continuity (FAST — no oversampling)
 * ═══════════════════════════════════════════════════════════════════ */

void meas_continuity(meas_result_t *r)
{
    /* Use lowest R_ref (49.9 Ohm) for best low-R resolution */
    mux_select(0);

    /* Single fast read — no oversampling for speed */
    uint16_t raw = adc_read_raw(ADC_CH_RESIST);
    float v = adc_to_voltage(raw);
    float ref = read_pgm_float(&rref[0]);

    float denom = V_REF - v;
    if (denom < 0.001f) {
        r->primary = 99999.0f;
    } else {
        r->primary = ref * v / denom;
    }

    /* Buzzer control is handled by the main loop checking threshold */
    r->secondary = 0.0f;
    set_unit(r, "Ohm");
    r->prefix    = ' ';
    r->overload  = 0;
    r->range     = 0;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 9: Diode Test
 * ═══════════════════════════════════════════════════════════════════ */

void meas_diode(meas_result_t *r)
{
    /* Use 50k reference → ~100 uA test current */
    mux_select(3);

    uint16_t raw = adc_read_oversample(ADC_CH_RESIST);
    float vf = adc_to_voltage_os(raw);

    r->primary   = vf;
    r->secondary = 0.0f;
    set_unit(r, "V");
    r->prefix    = ' ';
    r->overload  = (vf > 4.5f) ? 1 : 0;
    r->range     = 0;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 10: Capacitance (RC Timing)
 * ═══════════════════════════════════════════════════════════════════ */

void meas_capacitance(meas_result_t *r)
{
    float r_charge = read_pgm_float(&cap_r[cap_range]);

    /* Step 1: Fully discharge */
    cap_discharge();
    delay_ms(50);

    /* Step 2: Start charging */
    cap_charge();

    /* Step 3: Time until ADC reads 63.2% of max
     * 63.2% of 4095 = 2588 (12-bit) */
    uint16_t threshold = 2588;
    uint32_t t_start = micros();
    uint32_t timeout  = t_start + 5000000UL;  /* 5 second timeout */

    while (1) {
        uint16_t raw = adc_read_raw(ADC_CH_RESIST);
        if (raw >= threshold)
            break;
        if (micros() > timeout) {
            /* Timeout — capacitor too large for this range */
            cap_float();
            r->primary  = 0.0f;
            r->overload = 1;
            set_unit(r, "F");
            r->range    = cap_range;
            return;
        }
    }

    uint32_t t_end = micros();
    cap_float();

    /* tau = time in seconds */
    float tau = (float)(t_end - t_start) / 1e6f;

    /* C = tau / R */
    float cap = tau / r_charge;

    /* Auto-range based on timing */
    if (!range_locked) {
        if (tau < 0.001f && cap_range > 0) {
            cap_range--;
            autorange_settle_start();
        } else if (tau > 2.0f && cap_range < N_CAP_RANGES - 1) {
            cap_range++;
            autorange_settle_start();
        }
    }

    /* Format unit */
    if (cap >= 1e-3f) {
        r->primary = cap * 1e3f;
        set_unit(r, "mF");
        r->prefix = 'm';
    } else if (cap >= 1e-6f) {
        r->primary = cap * 1e6f;
        set_unit(r, "uF");
        r->prefix = 'u';
    } else {
        r->primary = cap * 1e9f;
        set_unit(r, "nF");
        r->prefix = 'n';
    }

    r->primary   = apply_lpf(r->primary);
    r->secondary = 0.0f;
    r->overload  = 0;
    r->range     = cap_range;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 11: Inductance (RL Step-Response Timing)
 * ═══════════════════════════════════════════════════════════════════ */

void meas_inductance(meas_result_t *r)
{
    float r_series = read_pgm_float(&ind_r[ind_range]);
    uint8_t mux_ch = pgm_read_byte(&ind_mux[ind_range]);

    /* Select series resistor via mux */
    mux_select(mux_ch);

    /* Discharge any stored energy — short inductor through R_series */
    cap_discharge();
    delay_ms(50);

    /* Read baseline (zero-current) ADC value */
    uint16_t baseline = adc_read_raw(ADC_CH_RESIST);

    /* Apply step voltage, wait for steady state to measure final value */
    cap_charge();
    delay_ms(100);
    uint16_t final_raw = adc_read_raw(ADC_CH_RESIST);
    cap_float();

    /* Check for open circuit / no inductor */
    uint16_t delta = (final_raw > baseline) ? (final_raw - baseline) : 0;
    if (delta < 20) {
        mux_disable();
        r->primary  = 0.0f;
        r->overload = 1;
        set_unit(r, "H");
        r->range    = ind_range;
        return;
    }

    /* Compute 63.2% threshold */
    uint16_t threshold = baseline + (uint16_t)((float)delta * 0.632f);

    /* Now do the timed measurement: discharge, then step and time */
    cap_discharge();
    delay_ms(50);

    cap_charge();
    uint32_t t_start = micros();
    uint32_t timeout = t_start + 5000000UL;  /* 5 second timeout */

    while (1) {
        uint16_t raw = adc_read_raw(ADC_CH_RESIST);
        if (raw >= threshold)
            break;
        if (micros() > timeout) {
            cap_float();
            mux_disable();
            r->primary  = 0.0f;
            r->overload = 1;
            set_unit(r, "H");
            r->range    = ind_range;
            return;
        }
    }

    uint32_t t_end = micros();
    cap_float();
    mux_disable();

    /* tau = L / R  →  L = tau * R */
    float tau = (float)(t_end - t_start) / 1e6f;
    float inductance = tau * r_series;

    /* Auto-range based on tau.
     * Note: for inductance, SMALLER R gives LONGER tau (tau = L/R),
     * so we range towards smaller R when tau is too short. */
    if (!range_locked) {
        if (tau < 0.0001f && ind_range < N_IND_RANGES - 1) {
            ind_range++;            /* smaller R → longer tau */
            autorange_settle_start();
        } else if (tau > 2.0f && ind_range > 0) {
            ind_range--;            /* larger R → shorter tau */
            autorange_settle_start();
        }
    }

    /* Format unit */
    if (inductance >= 1.0f) {
        r->primary = inductance;
        set_unit(r, "H");
        r->prefix = ' ';
    } else if (inductance >= 1e-3f) {
        r->primary = inductance * 1e3f;
        set_unit(r, "mH");
        r->prefix = 'm';
    } else {
        r->primary = inductance * 1e6f;
        set_unit(r, "uH");
        r->prefix = 'u';
    }

    r->primary   = apply_lpf(r->primary);
    r->secondary = 0.0f;
    r->overload  = 0;
    r->range     = ind_range;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 12: DC Current (6 auto-ranges)
 * ═══════════════════════════════════════════════════════════════════ */

void meas_dc_current(meas_result_t *r)
{
    cur_select(cur_range);

    uint16_t raw = adc_read_oversample(ADC_CH_CURRENT);
    float v = adc_to_voltage_os(raw);
    float shunt = read_pgm_float(&ishunt[cur_range]);

    /* Gain is 10x for lowest shunt (0.1 Ohm), 1x otherwise */
    float gain = (cur_range == N_CUR_RANGES - 1) ? CUR_GAIN_HI : CUR_GAIN_LO;

    /* I = V_adc / (R_shunt * Gain) */
    float current = v / (shunt * gain);

    /* Auto-range */
    if (!range_locked && !autorange_settling()) {
        uint16_t raw12 = adc_read_raw(ADC_CH_CURRENT);
        int8_t delta = autorange_check(raw12);
        uint8_t new_range = autorange_clamp(cur_range, delta, N_CUR_RANGES);
        if (new_range != cur_range) {
            cur_range = new_range;
            autorange_settle_start();
        }
    }

    /* Format unit */
    if (current >= 1.0f) {
        r->primary = apply_lpf(current);
        set_unit(r, "A");
        r->prefix = ' ';
    } else if (current >= 0.001f) {
        r->primary = apply_lpf(current * 1000.0f);
        set_unit(r, "mA");
        r->prefix = 'm';
    } else {
        r->primary = apply_lpf(current * 1e6f);
        set_unit(r, "uA");
        r->prefix = 'u';
    }

    r->secondary = 0.0f;
    r->overload  = (v > 4.9f) ? 1 : 0;
    r->range     = cur_range;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 12: AC Current True-RMS
 * ═══════════════════════════════════════════════════════════════════ */

void meas_ac_current(meas_result_t *r)
{
    cur_select(cur_range);

    trms_result_t trms;
    trms_measure(ADC_CH_CURRENT, &trms);

    float shunt = read_pgm_float(&ishunt[cur_range]);
    float gain = (cur_range == N_CUR_RANGES - 1) ? CUR_GAIN_HI : CUR_GAIN_LO;

    float ac_current = trms.ac / (shunt * gain);
    r->primary   = apply_lpf(ac_current * 1000.0f);
    r->secondary = trms.dc / (shunt * gain) * 1000.0f;
    set_unit(r, "mA");
    r->prefix    = 'm';
    r->overload  = 0;
    r->range     = cur_range;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 13: DC+AC Current Combined
 * ═══════════════════════════════════════════════════════════════════ */

void meas_dcac_current(meas_result_t *r)
{
    cur_select(cur_range);

    trms_result_t trms;
    trms_measure(ADC_CH_CURRENT, &trms);

    float shunt = read_pgm_float(&ishunt[cur_range]);
    float gain = (cur_range == N_CUR_RANGES - 1) ? CUR_GAIN_HI : CUR_GAIN_LO;

    float rms_current = trms.rms / (shunt * gain);
    r->primary   = apply_lpf(rms_current * 1000.0f);
    r->secondary = trms.ac / (shunt * gain) * 1000.0f;
    set_unit(r, "mA");
    r->prefix    = 'm';
    r->overload  = 0;
    r->range     = cur_range;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 14: Frequency
 * ═══════════════════════════════════════════════════════════════════ */

extern volatile uint32_t freq_period_us;
extern volatile uint8_t  freq_ready;

void meas_frequency(meas_result_t *r)
{
    if (freq_ready) {
        freq_ready = 0;
        float period_s = (float)freq_period_us / 1e6f;
        float freq = (period_s > 0.0f) ? (1.0f / period_s) : 0.0f;

        if (freq >= 1000.0f) {
            r->primary = apply_lpf(freq / 1000.0f);
            set_unit(r, "kHz");
            r->prefix = 'k';
        } else {
            r->primary = apply_lpf(freq);
            set_unit(r, "Hz");
            r->prefix = ' ';
        }
        r->overload = 0;
    } else {
        r->primary  = 0.0f;
        set_unit(r, "Hz");
        r->prefix   = ' ';
        r->overload = 0;
    }
    r->secondary = 0.0f;
    r->range     = 0;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 15: Duty Cycle
 * ═══════════════════════════════════════════════════════════════════ */

extern volatile uint32_t freq_high_us;

void meas_duty_cycle(meas_result_t *r)
{
    if (freq_ready && freq_period_us > 0) {
        freq_ready = 0;
        float duty = (float)freq_high_us / (float)freq_period_us * 100.0f;
        r->primary = apply_lpf(duty);
        r->overload = 0;
    } else {
        r->primary  = 0.0f;
        r->overload = 0;
    }
    r->secondary = 0.0f;
    set_unit(r, "%");
    r->prefix    = ' ';
    r->range     = 0;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 16: Pulse Width
 * ═══════════════════════════════════════════════════════════════════ */

void meas_pulse_width(meas_result_t *r)
{
    if (freq_ready && freq_high_us > 0) {
        freq_ready = 0;
        float pw_ms = (float)freq_high_us / 1000.0f;
        r->primary = apply_lpf(pw_ms);
        r->overload = 0;
    } else {
        r->primary  = 0.0f;
        r->overload = 0;
    }
    r->secondary = 0.0f;
    set_unit(r, "ms");
    r->prefix    = ' ';
    r->range     = 0;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 17: Temperature (LM35)
 * ═══════════════════════════════════════════════════════════════════ */

void meas_temperature(meas_result_t *r)
{
    uint16_t raw = adc_read_oversample(ADC_CH_TEMP);
    float v = adc_to_voltage_os(raw);

    /* LM35: 10 mV/°C → T = V / 0.010 */
    r->primary   = apply_lpf(v / 0.010f);
    r->secondary = v * 1000.0f;   /* mV for reference */
    set_unit(r, "\xB0""C");       /* degree sign + C */
    r->prefix    = ' ';
    r->overload  = (r->primary > 110.0f) ? 1 : 0;
    r->range     = 0;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 18: dBV
 * ═══════════════════════════════════════════════════════════════════ */

void meas_dbv(meas_result_t *r)
{
    trms_result_t trms;
    trms_measure(ADC_CH_VOLT_LO, &trms);

    float vrms = trms.ac;
    if (vrms < 1e-6f) vrms = 1e-6f;   /* floor to avoid log(0) */

    r->primary   = apply_lpf(20.0f * log10f(vrms / 1.0f));
    r->secondary = vrms;
    set_unit(r, "dBV");
    r->prefix    = ' ';
    r->overload  = 0;
    r->range     = 0;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode 19: dBm
 * ═══════════════════════════════════════════════════════════════════ */

void meas_dbm(meas_result_t *r)
{
    trms_result_t trms;
    trms_measure(ADC_CH_VOLT_LO, &trms);

    float vrms = trms.ac;
    if (vrms < 1e-6f) vrms = 1e-6f;

    float z = read_pgm_float(&dbm_z[dbm_impedance_idx]);
    float power = (vrms * vrms) / z;

    r->primary   = apply_lpf(10.0f * log10f(power / 0.001f));
    r->secondary = vrms;
    set_unit(r, "dBm");
    r->prefix    = ' ';
    r->overload  = 0;
    r->range     = dbm_impedance_idx;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Initialization
 * ═══════════════════════════════════════════════════════════════════ */

void measure_init(void)
{
    current_mode  = M_DCV;
    current_func  = FUNC_NONE;
    range_locked  = 0;
    lpf_enabled   = 0;
    rel_reference = 0.0f;
    min_val       =  1e30f;
    max_val       = -1e30f;
    avg_sum       = 0.0;
    avg_count     = 0;
    res_range     = 2;
    cur_range     = 2;
    cap_range     = 0;
    ind_range     = 1;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Mode Dispatch
 * ═══════════════════════════════════════════════════════════════════ */

typedef void (*meas_fn)(meas_result_t *);

static const meas_fn dispatch_table[] PROGMEM = {
    meas_dcv,           /* M_DCV      */
    meas_acv,           /* M_ACV      */
    meas_dcacv,         /* M_DCACV    */
    meas_mv_dc,         /* M_MV_DC    */
    meas_mv_ac,         /* M_MV_AC    */
    meas_resistance,    /* M_RESIST   */
    meas_low_ohm,       /* M_LOW_OHM  */
    meas_conductance,   /* M_CONDUCT  */
    meas_continuity,    /* M_CONTIN   */
    meas_diode,         /* M_DIODE    */
    meas_capacitance,   /* M_CAP      */
    meas_inductance,    /* M_IND      */
    meas_dc_current,    /* M_DCI      */
    meas_ac_current,    /* M_ACI      */
    meas_dcac_current,  /* M_DCACI    */
    meas_frequency,     /* M_FREQ     */
    meas_duty_cycle,    /* M_DUTY     */
    meas_pulse_width,   /* M_PULSE    */
    meas_temperature,   /* M_TEMP     */
    meas_dbv,           /* M_DBV      */
    meas_dbm,           /* M_DBM      */
};

void measure_dispatch(meas_result_t *result)
{
    mode_t mode = current_mode;
    if (mode >= M_SCOPE)
        return;  /* Scope handled separately */

    meas_fn fn;
    memcpy_P(&fn, &dispatch_table[mode], sizeof(meas_fn));
    fn(result);

    /* Apply secondary functions */
    measure_apply_secondary(result);
}

/* ═══════════════════════════════════════════════════════════════════
 *  Secondary Function Processing (REL, HOLD, MIN/MAX)
 * ═══════════════════════════════════════════════════════════════════ */

void measure_apply_secondary(meas_result_t *r)
{
    /* REL mode: subtract stored reference */
    if (current_func == FUNC_REL) {
        r->primary -= rel_reference;
    }

    /* Min/Max tracking */
    if (current_func == FUNC_MINMAX) {
        if (r->primary < min_val) min_val = r->primary;
        if (r->primary > max_val) max_val = r->primary;
        avg_sum += (double)r->primary;
        avg_count++;
    }

    /* HOLD mode: don't update primary (handled in display layer) */
}

void measure_reset_minmax(void)
{
    min_val   =  1e30f;
    max_val   = -1e30f;
    avg_sum   = 0.0;
    avg_count = 0;
}
