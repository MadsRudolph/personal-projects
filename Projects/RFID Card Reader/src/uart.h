#ifndef UART_H
#define UART_H

#include <stdint.h>

void uart_init(uint32_t baud);
void uart_putc(char c);
void uart_puts(const char *s);
void uart_put_hex(uint8_t byte);
void uart_put_hex16(uint16_t val);

#endif
