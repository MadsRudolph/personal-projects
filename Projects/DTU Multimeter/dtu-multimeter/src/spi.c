/** @file spi.c
 *  @brief SPI master driver implementation (Mode 0,0, 2 MHz).
 */

#include "config.h"
#include "spi.h"
#include <avr/pgmspace.h>

/* ═══════════════════════════════════════════════════════════════════
 *  SPI Master Driver — ATmega2560 HW SPI
 *  Mode 0,0 (CPOL=0, CPHA=0), CLK = F_CPU/8 = 2 MHz
 *
 *  Pin mapping (Port B):
 *    PB0 (D53) — SS   (output, managed by peripheral drivers)
 *    PB1 (D52) — SCK  (output)
 *    PB2 (D51) — MOSI (output)
 *    PB3 (D50) — MISO (input)
 * ═══════════════════════════════════════════════════════════════════ */

static const char init_msg[] PROGMEM = "SPI: init 2 MHz mode 0,0\n";

/* ─── spi_init ───────────────────────────────────────────────────── */
void spi_init(void)
{
    /* SS(PB0), MOSI(PB2), SCK(PB1) as output; MISO(PB3) as input */
    DDRB |=  (1 << PB0) | (1 << PB1) | (1 << PB2);
    DDRB &= ~(1 << PB3);

    /* Drive SS high (deselect) */
    PORTB |= (1 << PB0);

    /*
     * SPCR: SPE  = 1  (enable SPI)
     *       MSTR = 1  (master mode)
     *       CPOL = 0  (Mode 0,0)
     *       CPHA = 0
     *       SPR0 = 1  (base prescaler /8 with SPI2X)
     *       SPR1 = 0
     *
     * Prescaler: SPR1:0 = 01 gives /16 base.
     *            SPI2X  = 1 halves to /8 → 16 MHz / 8 = 2 MHz.
     */
    SPCR = (1 << SPE) | (1 << MSTR) | (1 << SPR0);
    SPSR |= (1 << SPI2X);

    (void)init_msg;   /* suppress unused warning if not consumed */
}

/* ─── spi_transfer ───────────────────────────────────────────────── */
uint8_t spi_transfer(uint8_t data)
{
    SPDR = data;
    while (!(SPSR & (1 << SPIF)))
        ;
    return SPDR;
}
