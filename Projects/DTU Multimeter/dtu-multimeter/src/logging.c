/** @file logging.c
 *  @brief EEPROM circular buffer and UART CSV data logging with RTC timestamps.
 */

#include "config.h"
#include "logging.h"
#include "rtc_ds1307.h"
#include "uart.h"

#include <avr/eeprom.h>
#include <avr/pgmspace.h>
#include <stdio.h>

/* ═══════════════════════════════════════════════════════════════════
 *  Data Logging — Circular EEPROM Buffer + UART CSV
 *
 *  EEPROM layout:
 *    Addr 0       : write_index  (uint8_t, 0 .. LOG_EEPROM_MAX-1)
 *    Addr 1       : entry_count  (uint8_t, 0 .. LOG_EEPROM_MAX)
 *    Addr 2+      : entries[]    (10 bytes each)
 *
 *  Entry format (10 bytes):
 *    [0..3]  float value
 *    [4]     hour   (0-23)
 *    [5]     minute (0-59)
 *    [6]     second (0-59)
 *    [7]     date   (1-31)
 *    [8]     month  (1-12)
 *    [9]     year   (0-99)
 * ═══════════════════════════════════════════════════════════════════ */

/* ─── EEPROM addresses ───────────────────────────────────────────── */
#define EE_ADDR_INDEX   ((uint8_t *)0)
#define EE_ADDR_COUNT   ((uint8_t *)1)
#define EE_ENTRY_BASE   2
#define EE_ENTRY_SIZE   10

/* ─── PROGMEM strings ────────────────────────────────────────────── */
static const char csv_hdr[]    PROGMEM = "Time,Date,Value,Unit\r\n";
static const char csv_fmt[]    PROGMEM = "%02u:%02u:%02u,%02u/%02u/%02u,";
static const char csv_sep[]    PROGMEM = ",";
static const char csv_crlf[]   PROGMEM = "\r\n";
static const char msg_empty[]  PROGMEM = "EEPROM log empty.\r\n";
static const char unit_none[]  PROGMEM = "?";

/* ─── Module state ───────────────────────────────────────────────── */
static uint8_t log_index;          /* Next write position (0..99)    */
static uint8_t log_count;          /* Total stored entries (0..100)  */

/* ─── Helpers ────────────────────────────────────────────────────── */

/* Compute the EEPROM byte address for entry n */
static uint8_t *ee_entry_addr(uint8_t n)
{
    return (uint8_t *)(uint16_t)(EE_ENTRY_BASE + (uint16_t)n * EE_ENTRY_SIZE);
}

/* Write a float to an arbitrary EEPROM byte address */
static void ee_write_float(uint8_t *addr, float val)
{
    eeprom_update_float((float *)addr, val);
}

/* Read a float from an arbitrary EEPROM byte address */
static float ee_read_float(const uint8_t *addr)
{
    return eeprom_read_float((const float *)addr);
}

/* ─── Print a single CSV data line for one entry ─────────────────── */
static void print_entry(float value, uint8_t hour, uint8_t min,
                         uint8_t sec, uint8_t date, uint8_t month,
                         uint8_t year, const char *unit_pgm)
{
    char buf[24];

    /* "HH:MM:SS,DD/MM/YY," */
    snprintf_P(buf, sizeof(buf), csv_fmt,
               hour, min, sec, date, month, year);
    uart_puts(buf);

    /* value */
    uart_print_float(value, 4);

    /* ",unit\r\n" */
    uart_puts_P(csv_sep);
    uart_puts_P(unit_pgm);
    uart_puts_P(csv_crlf);
}

/* ═══════════════════════════════════════════════════════════════════
 *  Public API
 * ═══════════════════════════════════════════════════════════════════ */

/* ─── logging_init ───────────────────────────────────────────────── */
void logging_init(void)
{
    log_index = eeprom_read_byte(EE_ADDR_INDEX);
    log_count = eeprom_read_byte(EE_ADDR_COUNT);

    /* Sanity check — virgin / corrupted EEPROM reads 0xFF */
    if (log_index >= LOG_EEPROM_MAX) {
        log_index = 0;
        log_count = 0;
        eeprom_update_byte(EE_ADDR_INDEX, 0);
        eeprom_update_byte(EE_ADDR_COUNT, 0);
    }
    if (log_count > LOG_EEPROM_MAX) {
        log_count = 0;
        eeprom_update_byte(EE_ADDR_COUNT, 0);
    }
}

/* ─── logging_store ──────────────────────────────────────────────── */
void logging_store(float value, const char *unit)
{
    rtc_time_t t;
    uint8_t   *base;

    /* 1. Read current time from DS1307 */
    rtc_read(&t);

    /* 2. Write entry to EEPROM at current index */
    base = ee_entry_addr(log_index);

    ee_write_float(base, value);                 /* bytes 0-3: value  */
    eeprom_update_byte(base + 4, t.hour);        /* byte  4: hour     */
    eeprom_update_byte(base + 5, t.min);         /* byte  5: minute   */
    eeprom_update_byte(base + 6, t.sec);         /* byte  6: second   */
    eeprom_update_byte(base + 7, t.date);        /* byte  7: date     */
    eeprom_update_byte(base + 8, t.month);       /* byte  8: month    */
    eeprom_update_byte(base + 9, t.year);        /* byte  9: year     */

    /* 3. Advance index (wrap), cap count */
    log_index++;
    if (log_index >= LOG_EEPROM_MAX)
        log_index = 0;

    if (log_count < LOG_EEPROM_MAX)
        log_count++;

    /* 4. Persist index and count */
    eeprom_update_byte(EE_ADDR_INDEX, log_index);
    eeprom_update_byte(EE_ADDR_COUNT, log_count);

    /* 5. Print CSV line to UART */
    /* unit is expected to be a PROGMEM pointer from the caller */
    print_entry(value, t.hour, t.min, t.sec,
                t.date, t.month, t.year, unit);
}

/* ─── logging_dump_eeprom ────────────────────────────────────────── */
void logging_dump_eeprom(void)
{
    uint8_t i, pos;
    uint8_t *base;
    float   val;
    uint8_t hour, min, sec, date, month, year;

    if (log_count == 0) {
        uart_puts_P(msg_empty);
        return;
    }

    /* Print CSV header first */
    logging_csv_header();

    /* Determine start position: oldest entry first */
    if (log_count >= LOG_EEPROM_MAX)
        pos = log_index;           /* buffer full — oldest is at write_index */
    else
        pos = 0;                   /* buffer not full — oldest is at 0       */

    for (i = 0; i < log_count; i++) {
        base = ee_entry_addr(pos);

        val   = ee_read_float(base);
        hour  = eeprom_read_byte(base + 4);
        min   = eeprom_read_byte(base + 5);
        sec   = eeprom_read_byte(base + 6);
        date  = eeprom_read_byte(base + 7);
        month = eeprom_read_byte(base + 8);
        year  = eeprom_read_byte(base + 9);

        /* Unit is not stored in EEPROM — print placeholder */
        print_entry(val, hour, min, sec, date, month, year, unit_none);

        pos++;
        if (pos >= LOG_EEPROM_MAX)
            pos = 0;
    }
}

/* ─── logging_csv_header ─────────────────────────────────────────── */
void logging_csv_header(void)
{
    uart_puts_P(csv_hdr);
}
