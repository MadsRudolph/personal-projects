/** @file rtc_ds1307.c
 *  @brief DS1307 I2C real-time clock driver with BCD conversion.
 */

#include "config.h"
#include "i2c.h"
#include "rtc_ds1307.h"
#include <stdio.h>
#include <avr/pgmspace.h>

#define DS1307_ADDR_W 0xD0
#define DS1307_ADDR_R 0xD1

static inline uint8_t bcd_to_dec(uint8_t bcd)
{
    return (bcd >> 4) * 10 + (bcd & 0x0F);
}

static inline uint8_t dec_to_bcd(uint8_t dec)
{
    return ((dec / 10) << 4) | (dec % 10);
}

static const char fmt_time[] PROGMEM = "%02u:%02u:%02u";
static const char fmt_date[] PROGMEM = "%02u/%02u/%02u";

void rtc_init(void)
{
    uint8_t sec;

    /* Read register 0 (seconds) */
    i2c_start(DS1307_ADDR_W);
    i2c_write(0x00);
    i2c_start(DS1307_ADDR_R);
    sec = i2c_read_nack();
    i2c_stop();

    /* Clear CH bit (bit 7) to start oscillator */
    if (sec & 0x80) {
        i2c_start(DS1307_ADDR_W);
        i2c_write(0x00);
        i2c_write(sec & 0x7F);
        i2c_stop();
    }
}

void rtc_read(rtc_time_t *t)
{
    /* Set register pointer to 0 */
    i2c_start(DS1307_ADDR_W);
    i2c_write(0x00);

    /* Sequential read of 7 registers: 6 ACK + 1 NACK */
    i2c_start(DS1307_ADDR_R);
    t->sec   = bcd_to_dec(i2c_read_ack() & 0x7F);  /* mask CH bit */
    t->min   = bcd_to_dec(i2c_read_ack());
    t->hour  = bcd_to_dec(i2c_read_ack() & 0x3F);  /* mask 24h mode */
    t->day   = bcd_to_dec(i2c_read_ack());
    t->date  = bcd_to_dec(i2c_read_ack());
    t->month = bcd_to_dec(i2c_read_ack());
    t->year  = bcd_to_dec(i2c_read_nack());
    i2c_stop();
}

void rtc_write(const rtc_time_t *t)
{
    i2c_start(DS1307_ADDR_W);
    i2c_write(0x00);                    /* register pointer */
    i2c_write(dec_to_bcd(t->sec));      /* CH=0 (bit 7 clear) */
    i2c_write(dec_to_bcd(t->min));
    i2c_write(dec_to_bcd(t->hour));
    i2c_write(dec_to_bcd(t->day));
    i2c_write(dec_to_bcd(t->date));
    i2c_write(dec_to_bcd(t->month));
    i2c_write(dec_to_bcd(t->year));
    i2c_stop();
}

void rtc_format_time(const rtc_time_t *t, char *buf)
{
    sprintf_P(buf, fmt_time, t->hour, t->min, t->sec);
}

void rtc_format_date(const rtc_time_t *t, char *buf)
{
    sprintf_P(buf, fmt_date, t->date, t->month, t->year);
}
