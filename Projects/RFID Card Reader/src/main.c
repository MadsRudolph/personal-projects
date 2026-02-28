#include <avr/io.h>
#include <util/delay.h>
#include "uart.h"
#include "spi.h"
#include "mfrc522.h"

int main(void) {
    uint8_t status;
    uint8_t tag_type[2];
    uint8_t uid[5];  // 4 bytes UID + 1 byte BCC
    uint8_t i;

    // Init peripherals
    spi_init();
    uart_init(9600);
    mfrc522_init();

    // Startup message
    uart_puts("\r\n");
    uart_puts("RFID Card Reader - Bare Metal AVR\r\n");

    // Read chip version as sanity check
    uint8_t version = mfrc522_read_reg(VersionReg);
    uart_puts("MFRC522 version: 0x");
    uart_put_hex(version);
    uart_puts("\r\n");  // expect 0x91 (v1.0) or 0x92 (v2.0)

    uart_puts("Waiting for card...\r\n");

    while (1) {
        // Look for new cards
        status = mfrc522_request(PICC_REQIDL, tag_type);

        if (status == MI_OK) {
            // Card detected, run anti-collision
            status = mfrc522_anticoll(uid);

            if (status == MI_OK) {
                uart_puts("UID: ");
                for (i = 0; i < 4; i++) {
                    uart_put_hex(uid[i]);
                    if (i < 3) {
                        uart_putc(':');
                    }
                }
                uart_puts("\r\n");
            }
        }

        _delay_ms(200);
    }

    return 0;
}
