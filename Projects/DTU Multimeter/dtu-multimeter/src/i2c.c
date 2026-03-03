/** @file i2c.c
 *  @brief TWI/I2C master driver implementation (400 kHz).
 */

#include "config.h"
#include "i2c.h"

/* ─── Init TWI at 400 kHz ────────────────────────────────────────
 *  SCL = F_CPU / (16 + 2*TWBR*prescaler)
 *      = 16 000 000 / (16 + 2*12*1) = 400 000 Hz               */
void i2c_init(void)
{
    TWSR = 0x00;            /* prescaler = 1                      */
    TWBR = 12;              /* 400 kHz at 16 MHz F_CPU            */
}

/* ─── START + address ────────────────────────────────────────── */
void i2c_start(uint8_t addr)
{
    TWCR = (1 << TWINT) | (1 << TWSTA) | (1 << TWEN);
    while (!(TWCR & (1 << TWINT)))
        ;
    TWDR = addr;
    TWCR = (1 << TWINT) | (1 << TWEN);
    while (!(TWCR & (1 << TWINT)))
        ;
}

/* ─── STOP ───────────────────────────────────────────────────── */
void i2c_stop(void)
{
    TWCR = (1 << TWINT) | (1 << TWSTO) | (1 << TWEN);
}

/* ─── Write one byte ─────────────────────────────────────────── */
void i2c_write(uint8_t data)
{
    TWDR = data;
    TWCR = (1 << TWINT) | (1 << TWEN);
    while (!(TWCR & (1 << TWINT)))
        ;
}

/* ─── Read one byte + ACK (more bytes follow) ────────────────── */
uint8_t i2c_read_ack(void)
{
    TWCR = (1 << TWINT) | (1 << TWEN) | (1 << TWEA);
    while (!(TWCR & (1 << TWINT)))
        ;
    return TWDR;
}

/* ─── Read one byte + NACK (last byte) ───────────────────────── */
uint8_t i2c_read_nack(void)
{
    TWCR = (1 << TWINT) | (1 << TWEN);
    while (!(TWCR & (1 << TWINT)))
        ;
    return TWDR;
}
