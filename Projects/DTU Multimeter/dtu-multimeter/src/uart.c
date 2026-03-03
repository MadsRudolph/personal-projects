/** @file uart.c
 *  @brief UART0 interrupt-driven driver with ring buffers and printf redirect.
 */

#include "config.h"
#include "uart.h"

#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <string.h>
#include <stdlib.h>

/* ═══════════════════════════════════════════════════════════════════
 *  UART0 Driver — ATmega2560, 115200 baud (U2X0), interrupt-driven
 * ═══════════════════════════════════════════════════════════════════ */

/* ─── Baud rate calculation (U2X0 enabled) ───────────────────────── */
#define BAUD 115200UL
#define UBRR_VAL ((F_CPU / (8UL * BAUD)) - 1)   /* = 16 @ 16 MHz   */

/* ─── Ring buffer masks (sizes must be powers of two) ────────────── */
#define TX_MASK (UART_TX_BUF - 1)
#define RX_MASK (UART_RX_BUF - 1)

#if (UART_TX_BUF & TX_MASK)
  #error "UART_TX_BUF must be a power of two"
#endif
#if (UART_RX_BUF & RX_MASK)
  #error "UART_RX_BUF must be a power of two"
#endif

/* ─── TX ring buffer ─────────────────────────────────────────────── */
static volatile uint8_t tx_buf[UART_TX_BUF];
static volatile uint8_t tx_head;               /* written by main    */
static volatile uint8_t tx_tail;               /* read by ISR        */

/* ─── RX ring buffer ─────────────────────────────────────────────── */
static volatile uint8_t rx_buf[UART_RX_BUF];
static volatile uint8_t rx_head;               /* written by ISR     */
static volatile uint8_t rx_tail;               /* read by main       */

/* ─── stdout stream for printf_P ─────────────────────────────────── */
static int uart_putc_stream(char c, FILE *stream);
FILE uart_stdout = FDEV_SETUP_STREAM(uart_putc_stream, NULL, _FDEV_SETUP_WRITE);

/* ═══════════════════════════════════════════════════════════════════
 *  uart_init — Configure UART0: 115200-8N1, U2X0, TX/RX + interrupts
 * ═══════════════════════════════════════════════════════════════════ */
void uart_init(void)
{
    /* Set baud rate */
    UBRR0H = (uint8_t)(UBRR_VAL >> 8);
    UBRR0L = (uint8_t)(UBRR_VAL);

    /* Enable double-speed for lower baud error at 115200 */
    UCSR0A = (1 << U2X0);

    /* Enable TX, RX, and RX-complete interrupt */
    UCSR0B = (1 << TXEN0) | (1 << RXEN0) | (1 << RXCIE0);

    /* Frame: 8 data, 1 stop, no parity */
    UCSR0C = (1 << UCSZ01) | (1 << UCSZ00);

    /* Clear buffer indices */
    tx_head = 0;
    tx_tail = 0;
    rx_head = 0;
    rx_tail = 0;

    /* Redirect stdout so printf_P works */
    stdout = &uart_stdout;
}

/* ═══════════════════════════════════════════════════════════════════
 *  TX ISR — USART0 Data Register Empty
 *  Sends next byte from TX ring buffer; disables UDRIE when empty.
 * ═══════════════════════════════════════════════════════════════════ */
ISR(USART0_UDRE_vect)
{
    if (tx_head == tx_tail) {
        /* Buffer empty — disable Data Register Empty interrupt */
        UCSR0B &= ~(1 << UDRIE0);
        return;
    }
    UDR0 = tx_buf[tx_tail];
    tx_tail = (tx_tail + 1) & TX_MASK;
}

/* ═══════════════════════════════════════════════════════════════════
 *  RX ISR — USART0 Receive Complete
 *  Stores incoming byte into RX ring buffer (drops if full).
 * ═══════════════════════════════════════════════════════════════════ */
ISR(USART0_RX_vect)
{
    uint8_t data = UDR0;
    uint8_t next = (rx_head + 1) & RX_MASK;

    if (next != rx_tail) {          /* room in buffer? */
        rx_buf[rx_head] = data;
        rx_head = next;
    }
    /* else: overflow — byte dropped silently */
}

/* ═══════════════════════════════════════════════════════════════════
 *  uart_putc — Queue one char into TX buffer (blocks if full)
 * ═══════════════════════════════════════════════════════════════════ */
void uart_putc(char c)
{
    uint8_t next = (tx_head + 1) & TX_MASK;

    /* Block until space available */
    while (next == tx_tail)
        ;

    tx_buf[tx_head] = (uint8_t)c;
    tx_head = next;

    /* Enable UDRE interrupt to start transmission */
    UCSR0B |= (1 << UDRIE0);
}

/* ─── Stream wrapper for FDEV_SETUP_STREAM ───────────────────────── */
static int uart_putc_stream(char c, FILE *stream)
{
    (void)stream;
    if (c == '\n')
        uart_putc('\r');
    uart_putc(c);
    return 0;
}

/* ═══════════════════════════════════════════════════════════════════
 *  uart_puts — Send a NUL-terminated string from RAM
 * ═══════════════════════════════════════════════════════════════════ */
void uart_puts(const char *s)
{
    while (*s)
        uart_putc(*s++);
}

/* ═══════════════════════════════════════════════════════════════════
 *  uart_puts_P — Send a NUL-terminated string from PROGMEM
 * ═══════════════════════════════════════════════════════════════════ */
void uart_puts_P(const char *s)
{
    char c;
    while ((c = pgm_read_byte(s++)) != '\0')
        uart_putc(c);
}

/* ═══════════════════════════════════════════════════════════════════
 *  uart_available — Number of bytes waiting in RX buffer
 * ═══════════════════════════════════════════════════════════════════ */
uint8_t uart_available(void)
{
    return (rx_head - rx_tail) & RX_MASK;
}

/* ═══════════════════════════════════════════════════════════════════
 *  uart_getc — Read one char from RX buffer (blocks until data)
 * ═══════════════════════════════════════════════════════════════════ */
char uart_getc(void)
{
    while (rx_head == rx_tail)
        ;

    char c = (char)rx_buf[rx_tail];
    rx_tail = (rx_tail + 1) & RX_MASK;
    return c;
}

/* ═══════════════════════════════════════════════════════════════════
 *  uart_getc_nb — Non-blocking read; returns -1 if buffer empty
 * ═══════════════════════════════════════════════════════════════════ */
int uart_getc_nb(void)
{
    if (rx_head == rx_tail)
        return -1;

    char c = (char)rx_buf[rx_tail];
    rx_tail = (rx_tail + 1) & RX_MASK;
    return (int)(unsigned char)c;
}

/* ═══════════════════════════════════════════════════════════════════
 *  uart_print_float — Print a float with N decimal places
 *  Manual integer+fraction formatting (no dtostrf dependency).
 * ═══════════════════════════════════════════════════════════════════ */
void uart_print_float(float val, uint8_t decimals)
{
    char buf[16];

    /* Handle negative values */
    if (val < 0.0f) {
        uart_putc('-');
        val = -val;
    }

    /* Round to requested decimal places */
    float rounding = 0.5f;
    for (uint8_t i = 0; i < decimals; i++)
        rounding /= 10.0f;
    val += rounding;

    /* Integer part */
    uint32_t int_part = (uint32_t)val;
    float remainder   = val - (float)int_part;

    /* Convert integer part to string (reverse fill) */
    uint8_t pos = 0;
    if (int_part == 0) {
        buf[pos++] = '0';
    } else {
        char tmp[11];
        uint8_t ti = 0;
        while (int_part > 0) {
            tmp[ti++] = '0' + (int_part % 10);
            int_part /= 10;
        }
        /* Reverse into buf */
        while (ti > 0)
            buf[pos++] = tmp[--ti];
    }

    /* Decimal point and fractional digits */
    if (decimals > 0) {
        buf[pos++] = '.';
        for (uint8_t i = 0; i < decimals; i++) {
            remainder *= 10.0f;
            uint8_t digit = (uint8_t)remainder;
            buf[pos++] = '0' + digit;
            remainder -= digit;
        }
    }

    buf[pos] = '\0';
    uart_puts(buf);
}
