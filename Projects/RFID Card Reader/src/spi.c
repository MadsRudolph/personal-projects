#include "spi.h"
#include <avr/io.h>

void spi_init(void) {
    // Set SS, MOSI, SCK as outputs; MISO as input
    SPI_DDR |= (1 << SPI_SS) | (1 << SPI_MOSI) | (1 << SPI_SCK);
    SPI_DDR &= ~(1 << SPI_MISO);

    // SS high (deselected)
    SPI_PORT |= (1 << SPI_SS);

    // Enable SPI, master mode, clock = F_CPU/16 (~1MHz)
    SPCR = (1 << SPE) | (1 << MSTR) | (1 << SPR0);
}

uint8_t spi_transfer(uint8_t data) {
    SPDR = data;
    while (!(SPSR & (1 << SPIF)))
        ;
    return SPDR;
}

void spi_select(void) {
    SPI_PORT &= ~(1 << SPI_SS);
}

void spi_deselect(void) {
    SPI_PORT |= (1 << SPI_SS);
}
