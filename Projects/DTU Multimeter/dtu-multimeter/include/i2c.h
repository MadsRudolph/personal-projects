#ifndef I2C_H
#define I2C_H

/** @file i2c.h
 *  @brief TWI/I2C master driver for ATmega2560.
 */

#include <stdint.h>

/** @defgroup grp_i2c I2C (TWI) Master Driver
 *  @brief 400 kHz I2C bus.  Used by the SSD1306 OLED and DS1307 RTC.
 *  @{ */

/** @brief Initialize TWI hardware at standard clock rate. */
void    i2c_init(void);

/** @brief Send START condition and slave address.
 *  @param addr 7-bit slave address with R/W bit in LSB */
void    i2c_start(uint8_t addr);

/** @brief Send STOP condition to release the bus. */
void    i2c_stop(void);

/** @brief Write one byte to the bus after START.
 *  @param data Byte to transmit */
void    i2c_write(uint8_t data);

/** @brief Read one byte from slave and send ACK (more bytes follow).
 *  @return Byte received from slave */
uint8_t i2c_read_ack(void);

/** @brief Read one byte from slave and send NACK (last byte).
 *  @return Byte received from slave */
uint8_t i2c_read_nack(void);

/** @} */

#endif /* I2C_H */
