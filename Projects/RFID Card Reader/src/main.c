#include <avr/io.h>
#include <util/delay.h>
#include "uart.h"

int main(void) {
    uart_init(9600);
    uart_puts("UART OK\r\n");

    while (1) {
        uart_puts("tick\r\n");
        _delay_ms(1000);
    }
    return 0;
}
