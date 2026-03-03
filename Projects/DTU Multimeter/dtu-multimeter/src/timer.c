/** @file timer.c
 *  @brief System tick (Timer1 1ms), millis/micros, and INT4 frequency capture.
 */

#include "config.h"
#include "timer.h"
#include <avr/interrupt.h>
#include <util/atomic.h>

/* ═══════════════════════════════════════════════════════════════════
 *  Timer Driver — ATmega2560, 16 MHz bare-metal
 *
 *  Timer1 — 1 ms system tick (CTC mode)
 *    Prescaler = 1, OCR1A = 15999
 *    TCNT1 counts 0..15999 each ms  (16 000 ticks @ 16 MHz = 1 ms)
 *
 *  INT4 — Frequency / duty-cycle capture on PE4 (D2)
 *    Toggles between rising and falling edge detection in the ISR
 *    to measure both period and high-time.
 * ═══════════════════════════════════════════════════════════════════ */

/* ─── System tick counter ────────────────────────────────────────── */
static volatile uint32_t millis_counter;

/* ─── Frequency capture globals ──────────────────────────────────── */
volatile uint32_t freq_period_us;
volatile uint32_t freq_high_us;
volatile uint8_t  freq_ready;

/* ─── Private state for INT4 edge tracking ───────────────────────── */
static volatile uint32_t last_rising_us;
static volatile uint32_t last_falling_us;
static volatile uint8_t  waiting_for_falling;   /* 0 = next edge is rising */

/* ═══════════════════════════════════════════════════════════════════
 *  timer_init — configure Timer1 tick and INT4 capture
 * ═══════════════════════════════════════════════════════════════════ */
void timer_init(void)
{
    /* ── Timer1: CTC, prescaler = 1 ─────────────────────────────── */
    TCCR1A = 0;
    TCCR1B = (1 << WGM12)              /* CTC — top = OCR1A          */
           | (1 << CS10);              /* clk/1 (no prescaler)       */
    OCR1A  = 15999;                    /* 16 000 counts → 1 ms       */
    TIMSK1 = (1 << OCIE1A);           /* Compare-match A interrupt   */

    /* ── INT4 (PE4): input, pull-up, rising edge ────────────────── */
    FREQ_DDR  &= ~(1 << FREQ_BIT);    /* PE4 as input               */
    FREQ_PORT |=  (1 << FREQ_BIT);    /* internal pull-up            */

    EICRB = (EICRB & ~((1 << ISC41) | (1 << ISC40)))
          | (1 << ISC41) | (1 << ISC40);   /* ISC41:40 = 11 → rising */

    waiting_for_falling = 0;
    freq_ready = 0;

    EIMSK |= (1 << INT4);             /* enable INT4                 */
}

/* ═══════════════════════════════════════════════════════════════════
 *  Timer1 Compare Match A — 1 ms tick
 * ═══════════════════════════════════════════════════════════════════ */
ISR(TIMER1_COMPA_vect)
{
    millis_counter++;
}

/* ═══════════════════════════════════════════════════════════════════
 *  millis — atomic read of millisecond counter
 * ═══════════════════════════════════════════════════════════════════ */
uint32_t millis(void)
{
    uint32_t ms;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        ms = millis_counter;
    }
    return ms;
}

/* ═══════════════════════════════════════════════════════════════════
 *  micros — microseconds since boot
 *
 *  Timer1 runs at 16 MHz (prescaler = 1), TCNT1 spans 0..15999
 *  within each 1 ms period.  TCNT1 / 16 gives the fractional us.
 * ═══════════════════════════════════════════════════════════════════ */
uint32_t micros(void)
{
    uint32_t ms;
    uint16_t tcnt;

    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        ms   = millis_counter;
        tcnt = TCNT1;
        /*
         * If the compare-match flag fired but the ISR hasn't run yet,
         * millis_counter is stale — compensate by adding 1 ms.
         */
        if ((TIFR1 & (1 << OCF1A)) && tcnt < 8000) {
            ms++;
        }
    }

    return ms * 1000UL + (tcnt >> 4);   /* tcnt / 16 */
}

/* ═══════════════════════════════════════════════════════════════════
 *  delay_ms — busy-wait for the given number of milliseconds
 * ═══════════════════════════════════════════════════════════════════ */
void delay_ms(uint16_t ms)
{
    uint32_t start = millis();
    while (millis() - start < ms)
        ;
}

/* ═══════════════════════════════════════════════════════════════════
 *  INT4 ISR — frequency & duty-cycle capture
 *
 *  Alternates edge sense between rising and falling:
 *    Rising  → record timestamp, compute period from previous rising
 *    Falling → record timestamp, compute high-time
 * ═══════════════════════════════════════════════════════════════════ */
ISR(INT4_vect)
{
    uint32_t now = micros();

    if (!waiting_for_falling) {
        /* ── Rising edge ─────────────────────────────────────────── */
        if (last_rising_us != 0) {
            freq_period_us = now - last_rising_us;
            freq_ready     = 1;
        }
        last_rising_us = now;

        /* Switch to falling-edge detect: ISC41:40 = 10 */
        EICRB = (EICRB & ~(1 << ISC40)) | (1 << ISC41);
        waiting_for_falling = 1;

    } else {
        /* ── Falling edge ────────────────────────────────────────── */
        freq_high_us = now - last_rising_us;

        /* Switch back to rising-edge detect: ISC41:40 = 11 */
        EICRB |= (1 << ISC41) | (1 << ISC40);
        waiting_for_falling = 0;
    }
}
