#ifndef UART_H
#define UART_H

/** @file uart.h
 *  @brief UART0 driver for ATmega2560 with interrupt-driven ring buffers.
 *
 *  115200 baud, 8N1. TX and RX use ISR-backed ring buffers.
 */

#include <stdint.h>
#include <stdio.h>

/** @defgroup grp_uart UART0 Serial Driver
 *  @brief 115200 baud 8N1 with interrupt-driven TX/RX ring buffers.
 *  @{ */

/** @brief Initialize UART0 at 115200 baud 8N1 and enable TX/RX interrupts. */
void    uart_init(void);

/** @brief Transmit one character (blocks if TX buffer is full).
 *  @param c Character to send */
void    uart_putc(char c);

/** @brief Transmit a null-terminated string from RAM.
 *  @param s Pointer to string in RAM */
void    uart_puts(const char *s);

/** @brief Transmit a null-terminated string from PROGMEM.
 *  @param s Pointer to string in flash (PROGMEM) */
void    uart_puts_P(const char *s);

/** @brief Return the number of bytes waiting in the RX ring buffer.
 *  @return Number of unread bytes available */
uint8_t uart_available(void);

/** @brief Read one character from RX buffer (blocks until data arrives).
 *  @return Received character */
char    uart_getc(void);

/** @brief Non-blocking read from RX buffer.
 *  @return Received character cast to int, or -1 if buffer is empty */
int     uart_getc_nb(void);

/** @brief Print a floating-point value with specified decimal places.
 *  @param val   Value to print
 *  @param decimals Number of digits after the decimal point */
void    uart_print_float(float val, uint8_t decimals);

/** @brief stdout stream for use with printf_P() after uart_init(). */
extern FILE uart_stdout;

/** @} */

#endif /* UART_H */
