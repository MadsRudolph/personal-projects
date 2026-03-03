/** @file mux.c
 *  @brief 74HC4067 mux and CD4053 switch control with settle delays.
 */

#include "config.h"
#include "mux.h"
#include <util/delay.h>

/* ===================================================================
 *  Multiplexer & Switch Control Driver
 *
 *  74HC4067 16-ch analog mux   — PA0-PA4
 *  CD4053  triple 2:1 switch   — PA5-PA7, PC7
 *  NE555 current source enable — PC4
 *  Capacitance charge/discharge — PC5, PC6
 *
 *  All functions use read-modify-write bit masking so that only the
 *  relevant pins are touched; other bits on the same port are
 *  preserved.
 * =================================================================== */

/* Bit masks for convenience */
#define MUX_SEL_MASK  ((1 << MUX_S0) | (1 << MUX_S1) | \
                       (1 << MUX_S2) | (1 << MUX_S3))

#define CUR_ABC_MASK  ((1 << CUR_A) | (1 << CUR_B) | (1 << CUR_C))

#define MUX_SETTLE_US  50
#define CUR_SETTLE_US  50

/* ─── mux_init ───────────────────────────────────────────────────── */
void mux_init(void)
{
    /* 74HC4067: S0-S3 and EN as outputs */
    MUX_DDR |= MUX_SEL_MASK | (1 << MUX_EN);

    /* Disable mux: EN = HIGH (active low) */
    MUX_PORT |= (1 << MUX_EN);

    /* Clear channel select bits */
    MUX_PORT &= ~MUX_SEL_MASK;

    /* CD4053: A, B, C as outputs */
    CUR_ABC_DDR |= CUR_ABC_MASK;

    /* Clear A/B/C */
    CUR_ABC_PORT &= ~CUR_ABC_MASK;

    /* CD4053 INH as output, set HIGH (inhibit) */
    CUR_INH_DDR  |= (1 << CUR_INH_BIT);
    CUR_INH_PORT |= (1 << CUR_INH_BIT);

    /* NE555 enable pin as output, LOW (off) */
    ISRC_DDR  |= (1 << ISRC_BIT);
    ISRC_PORT &= ~(1 << ISRC_BIT);

    /* Capacitance pins: input (Hi-Z), no pull-ups */
    CAP_CHG_DDR  &= ~(1 << CAP_CHG_BIT);
    CAP_CHG_PORT &= ~(1 << CAP_CHG_BIT);
    CAP_DIS_DDR  &= ~(1 << CAP_DIS_BIT);
    CAP_DIS_PORT &= ~(1 << CAP_DIS_BIT);
}

/* ═══════════════════════════════════════════════════════════════════
 *  74HC4067 — 16-channel analog mux
 * ═══════════════════════════════════════════════════════════════════ */

/* ─── mux_select ─────────────────────────────────────────────────── */
void mux_select(uint8_t channel)
{
    uint8_t tmp;

    /* Clamp to valid range */
    channel &= 0x0F;

    /* Read current port state */
    tmp = MUX_PORT;

    /* Clear S0-S3 bits */
    tmp &= ~MUX_SEL_MASK;

    /* Set new channel (S0-S3 are at PA0-PA3, so channel maps 1:1) */
    tmp |= channel;

    /* Enable mux: clear EN bit (active low) */
    tmp &= ~(1 << MUX_EN);

    MUX_PORT = tmp;

    _delay_us(MUX_SETTLE_US);
}

/* ─── mux_disable ────────────────────────────────────────────────── */
void mux_disable(void)
{
    /* Set EN high to disable mux */
    MUX_PORT |= (1 << MUX_EN);
}

/* ═══════════════════════════════════════════════════════════════════
 *  CD4053 — triple 2:1 analog switch (current shunt selection)
 *
 *  range 0-5 maps to a 3-bit binary value on pins A(PA5), B(PA6),
 *  C(PA7).  The three switch sections route different shunt resistors
 *  into the measurement path.
 * ═══════════════════════════════════════════════════════════════════ */

/* ─── cur_select ─────────────────────────────────────────────────── */
void cur_select(uint8_t range)
{
    uint8_t tmp;

    /* Clamp to 0-5 (6 valid current ranges) */
    if (range > 5)
        range = 5;

    tmp = CUR_ABC_PORT;

    /* Clear A/B/C bits (PA5-PA7) */
    tmp &= ~CUR_ABC_MASK;

    /* Map range to A/B/C: shift the 3-bit value up to PA5 position */
    tmp |= ((uint8_t)range << CUR_A);

    CUR_ABC_PORT = tmp;

    /* Uninhibit: drive INH low */
    CUR_INH_PORT &= ~(1 << CUR_INH_BIT);

    _delay_us(CUR_SETTLE_US);
}

/* ─── cur_disable ────────────────────────────────────────────────── */
void cur_disable(void)
{
    /* Inhibit: drive INH high — all switches open */
    CUR_INH_PORT |= (1 << CUR_INH_BIT);
}

/* ═══════════════════════════════════════════════════════════════════
 *  NE555 Constant Current Source
 * ═══════════════════════════════════════════════════════════════════ */

/* ─── isrc_enable ────────────────────────────────────────────────── */
void isrc_enable(void)
{
    ISRC_PORT |= (1 << ISRC_BIT);
}

/* ─── isrc_disable ───────────────────────────────────────────────── */
void isrc_disable(void)
{
    ISRC_PORT &= ~(1 << ISRC_BIT);
}

/* ═══════════════════════════════════════════════════════════════════
 *  Capacitance Charge / Discharge Control
 *
 *  charge:    CHG pin HIGH (output), DIS pin Hi-Z (input)
 *  discharge: DIS pin LOW  (output), CHG pin LOW  (output)
 *  float:     both pins Hi-Z (input), no pull-ups
 * ═══════════════════════════════════════════════════════════════════ */

/* ─── cap_charge ─────────────────────────────────────────────────── */
void cap_charge(void)
{
    /* Discharge pin to Hi-Z: clear DDR bit (input), no pull-up */
    CAP_DIS_DDR  &= ~(1 << CAP_DIS_BIT);
    CAP_DIS_PORT &= ~(1 << CAP_DIS_BIT);

    /* Charge pin as output, drive HIGH */
    CAP_CHG_DDR  |= (1 << CAP_CHG_BIT);
    CAP_CHG_PORT |= (1 << CAP_CHG_BIT);
}

/* ─── cap_discharge ──────────────────────────────────────────────── */
void cap_discharge(void)
{
    /* Charge pin LOW (output) */
    CAP_CHG_DDR  |= (1 << CAP_CHG_BIT);
    CAP_CHG_PORT &= ~(1 << CAP_CHG_BIT);

    /* Discharge pin as output, drive LOW */
    CAP_DIS_DDR  |= (1 << CAP_DIS_BIT);
    CAP_DIS_PORT &= ~(1 << CAP_DIS_BIT);
}

/* ─── cap_float ──────────────────────────────────────────────────── */
void cap_float(void)
{
    /* Both pins to Hi-Z: input mode, no pull-ups */
    CAP_CHG_DDR  &= ~(1 << CAP_CHG_BIT);
    CAP_CHG_PORT &= ~(1 << CAP_CHG_BIT);
    CAP_DIS_DDR  &= ~(1 << CAP_DIS_BIT);
    CAP_DIS_PORT &= ~(1 << CAP_DIS_BIT);
}
