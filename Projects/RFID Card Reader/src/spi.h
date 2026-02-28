#ifndef SPI_H
#define SPI_H

#include <stdint.h>

// Pin definitions - ATmega328P Port B
#define SPI_DDR   DDRB
#define SPI_PORT  PORTB
#define SPI_SS    PB2   // Arduino D10
#define SPI_MOSI  PB3   // Arduino D11
#define SPI_MISO  PB4   // Arduino D12
#define SPI_SCK   PB5   // Arduino D13

void spi_init(void);
uint8_t spi_transfer(uint8_t data);
void spi_select(void);
void spi_deselect(void);

#endif
