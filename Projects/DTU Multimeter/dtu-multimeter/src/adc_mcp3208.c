/** @file adc_mcp3208.c
 *  @brief MCP3208 12-bit SPI ADC driver with oversampling.
 */

/* ═══════════════════════════════════════════════════════════════════
 *  MCP3208 12-bit SPI ADC Driver — ATmega2560
 *  Single-ended mode, 8 channels, bare-metal register access
 * ═══════════════════════════════════════════════════════════════════ */

#include "config.h"
#include "spi.h"
#include "adc_mcp3208.h"

#include <util/delay.h>

/* ─── Helpers ─────────────────────────────────────────────────────── */

#define ADC_CS_LOW()   (ADC_CS_PORT &= ~(1 << ADC_CS_BIT))
#define ADC_CS_HIGH()  (ADC_CS_PORT |=  (1 << ADC_CS_BIT))

/* ─── Init ────────────────────────────────────────────────────────── */

void adc_init(void)
{
    ADC_CS_DDR  |=  (1 << ADC_CS_BIT);   /* CS pin as output       */
    ADC_CS_HIGH();                        /* deselect (idle HIGH)   */
}

/* ─── Single 12-bit read ──────────────────────────────────────────── */

uint16_t adc_read_raw(uint8_t channel)
{
    uint8_t byte1, byte2, byte3;

    ADC_CS_LOW();
    _delay_us(1);                         /* t_SUCS settling time   */

    /*  MCP3208 SPI frame (single-ended):
     *  byte1: 0  0  0  0  0  1  SGL  D2
     *  byte2: D1 D0  x  x  x  x  x   x
     *  byte3: clocks out remaining result bits
     *
     *  SGL=1 for single-ended → leading nibble = 0x06
     *  D2 is the MSB of the 3-bit channel number.
     */
    byte1 = spi_transfer(0x06 | (channel >> 2));
    byte2 = spi_transfer((channel & 0x03) << 6);
    byte3 = spi_transfer(0x00);

    ADC_CS_HIGH();

    /* byte2 lower 4 bits = B11..B8, byte3 = B7..B0 */
    return (uint16_t)((byte2 & 0x0F) << 8) | byte3;
}

/* ─── 64× oversampled read (15-bit) ──────────────────────────────── */

uint16_t adc_read_oversample(uint8_t channel)
{
    uint32_t sum = 0;

    for (uint8_t i = 0; i < OS_COUNT; i++)
        sum += adc_read_raw(channel);

    return (uint16_t)(sum >> OS_EXTRA_BITS);
}

/* ─── Voltage conversions ─────────────────────────────────────────── */

float adc_to_voltage(uint16_t raw12)
{
    return (float)raw12 * V_REF / 4095.0f;
}

float adc_to_voltage_os(uint16_t raw15)
{
    return (float)raw15 * V_REF / 32767.0f;
}
