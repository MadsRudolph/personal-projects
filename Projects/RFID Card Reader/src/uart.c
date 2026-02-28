#include "uart.h"
#include <avr/io.h>

void uart_init(uint32_t baud) {
    uint16_t ubrr = (F_CPU / (16UL * baud)) - 1; 
    UBRR0H = (uint8_t)(ubrr >> 8);
    UBRR0L = (uint8_t)(ubrr);
    UCSR0B = (1 << TXEN0) | (1 << RXEN0);  // enable transmitter and receiver
    UCSR0C = (1 << UCSZ01) | (1 << UCSZ00); // 8-bit data, 1 stop, no parity
}

void uart_putc(char c) {
    while (!(UCSR0A & (1 << UDRE0)))
        ;
    UDR0 = c;
}

void uart_puts(const char *s) {
    while (*s) {
        uart_putc(*s++);
    }
}

void uart_put_hex(uint8_t byte) {
    static const char hex[] = "0123456789ABCDEF";
    uart_putc(hex[byte >> 4]);
    uart_putc(hex[byte & 0x0F]);
}

void uart_put_hex16(uint16_t val) {
    uart_put_hex((uint8_t)(val >> 8));
    uart_put_hex((uint8_t)(val));
}

uint8_t uart_available(void) {
    return (UCSR0A & (1 << RXC0)) ? 1 : 0;
}

char uart_getc(void) {
    while (!(UCSR0A & (1 << RXC0)))
        ;
    return UDR0;
}
