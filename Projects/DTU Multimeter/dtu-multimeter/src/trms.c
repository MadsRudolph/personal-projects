/** @file trms.c
 *  @brief True-RMS computation engine with 20 kHz sampling.
 */

/* ═══════════════════════════════════════════════════════════════════
 *  trms.c — True-RMS Computation Engine
 *  Target: ATmega2560, bare-metal (no Arduino framework)
 *
 *  Samples an MCP3208 12-bit ADC channel at 20 kHz (50 us intervals)
 *  and computes True-RMS, DC, AC, and peak values.
 *
 *  Uses a double (64-bit) accumulator for the sum-of-squares to
 *  avoid overflow: 400 samples x 4095^2 ~ 6.7e9, which exceeds
 *  the 24-bit mantissa of a float but fits comfortably in a double.
 * ═══════════════════════════════════════════════════════════════════ */

#include "trms.h"
#include "config.h"
#include "adc_mcp3208.h"
#include "timer.h"
#include <math.h>

/* Scale factor: convert 12-bit raw value to voltage */
#define RAW_TO_V  (V_REF / 4095.0f)

/* ─── trms_measure ────────────────────────────────────────────────
 *  1. Acquire TRMS_SAMPLES readings at TRMS_INTERVAL_US spacing
 *  2. Track min/max during acquisition
 *  3. Compute RMS, DC, AC, convert peaks to voltage
 *  4. Fill result struct
 * ──────────────────────────────────────────────────────────────── */
void trms_measure(uint8_t adc_channel, trms_result_t *result)
{
    static uint16_t buf[TRMS_SAMPLES];   /* static — 800 B off the stack */

    uint16_t raw_min = 4095;
    uint16_t raw_max = 0;

    /* ── Acquisition loop ─────────────────────────────────────── */
    uint32_t next_time = micros();

    for (uint16_t i = 0; i < TRMS_SAMPLES; i++) {
        /* Busy-wait until the next sample instant */
        while (micros() < next_time)
            ;

        uint16_t raw = adc_read_raw(adc_channel);
        buf[i] = raw;

        if (raw < raw_min) raw_min = raw;
        if (raw > raw_max) raw_max = raw;

        next_time += TRMS_INTERVAL_US;
    }

    /* ── Compute DC (mean) ────────────────────────────────────── */
    result->dc = trms_compute_dc(buf, TRMS_SAMPLES);

    /* ── Compute True-RMS ─────────────────────────────────────── */
    result->rms = trms_compute_rms(buf, TRMS_SAMPLES);

    /* ── AC component ─────────────────────────────────────────── */
    float rms2 = result->rms * result->rms;
    float dc2  = result->dc  * result->dc;

    if (rms2 > dc2)
        result->ac = sqrtf(rms2 - dc2);
    else
        result->ac = 0.0f;     /* rounding guard */

    /* ── Peaks → voltage ──────────────────────────────────────── */
    result->peak_pos = (float)raw_max * RAW_TO_V;
    result->peak_neg = (float)raw_min * RAW_TO_V;
}

/* ─── trms_compute_rms ────────────────────────────────────────────
 *  RMS = sqrt( (1/N) * sum(raw_i^2) ) * V_REF / 4095
 *
 *  A double accumulator is used because the worst-case sum
 *  (400 * 4095^2 ≈ 6.7 x 10^9) exceeds 32-bit float precision.
 * ──────────────────────────────────────────────────────────────── */
float trms_compute_rms(const uint16_t *samples, uint16_t count)
{
    double sum_sq = 0.0;

    for (uint16_t i = 0; i < count; i++) {
        double s = (double)samples[i];
        sum_sq += s * s;
    }

    float rms_raw = sqrtf((float)(sum_sq / (double)count));
    return rms_raw * RAW_TO_V;
}

/* ─── trms_compute_dc ─────────────────────────────────────────────
 *  DC = (1/N) * sum(raw_i) * V_REF / 4095
 *
 *  A uint32_t accumulator suffices: 400 * 4095 = 1 638 000,
 *  well within 32-bit range.
 * ──────────────────────────────────────────────────────────────── */
float trms_compute_dc(const uint16_t *samples, uint16_t count)
{
    uint32_t sum = 0;

    for (uint16_t i = 0; i < count; i++)
        sum += samples[i];

    float mean_raw = (float)sum / (float)count;
    return mean_raw * RAW_TO_V;
}
