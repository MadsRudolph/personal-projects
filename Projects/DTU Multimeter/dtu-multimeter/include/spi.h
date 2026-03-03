#ifndef SPI_H
#define SPI_H

/** @file spi.h
 *  @brief SPI master driver for ATmega2560.
 *
 *  Hardware SPI in Mode 0,0 (CPOL=0, CPHA=0), CLK = F_CPU/8 = 2 MHz.
 */

#include <stdint.h>

/** @defgroup grp_spi SPI Master Driver
 *  @brief Hardware SPI in Mode 0,0, CLK = 2 MHz.  Used by the MCP3208 ADC.
 *  @{ */

/** @brief Initialize hardware SPI as master in Mode 0,0 at 2 MHz. */
void    spi_init(void);

/** @brief Full-duplex SPI byte transfer.
 *  @param data Byte to transmit on MOSI
 *  @return Byte received on MISO */
uint8_t spi_transfer(uint8_t data);

/** @} */

#endif /* SPI_H */
