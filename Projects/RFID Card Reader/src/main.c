#include <avr/io.h>
#include <util/delay.h>
#include <stdbool.h>
#include "uart.h"
#include "spi.h"
#include "mfrc522.h"

int main(void) {
    uint8_t status;
    uint8_t tag_type[2];
    uint8_t uid[5];            // Current card UID + BCC
    uint8_t saved_uid[4];      // Buffer for the UID we want to clone
    bool has_saved_uid = false;
    uint8_t i;

    // Init peripherals
    spi_init();
    uart_init(9600);
    mfrc522_init();

    // Setup LEDs for feedback (Optional: PC0 = Success, PC1 = Error)
    DDRC |= (1 << PC0) | (1 << PC1);

    uart_puts("\r\n--- RFID Cloner: Bare Metal AVR ---\r\n");
    uart_puts("Ready. Scan a source card to copy its UID.\r\n");

    while (1) {
        // Look for cards in the field
        status = mfrc522_request(PICC_REQIDL, tag_type);

        if (status == MI_OK) {
            // Card detected, retrieve its UID
            status = mfrc522_anticoll(uid);

            if (status == MI_OK) {
                if (!has_saved_uid) {
                    // MODE 1: SAVE - Capture the source UID
                    for (i = 0; i < 4; i++) {
                        saved_uid[i] = uid[i];
                    }
                    has_saved_uid = true;

                    uart_puts("UID Saved: ");
                    for (i = 0; i < 4; i++) {
                        uart_put_hex(saved_uid[i]);
                        if (i < 3) uart_putc(':');
                    }
                    uart_puts("\r\nNow present a 'Magic' tag to write.\r\n");
                    
                    // Visual feedback: Short blink
                    PORTC |= (1 << PC0);
                    _delay_ms(200);
                    PORTC &= ~(1 << PC0);
                } 
                else {
                    // MODE 2: WRITE - Attempt to clone to the new tag
                    uart_puts("Writing to Block 0...\r\n");

                    // Prepare Block 0 data: [UID (4 bytes), BCC (1 byte), SAK, etc.]
                    uint8_t block0_data[16] = {0};
                    for (i = 0; i < 4; i++) {
                        block0_data[i] = saved_uid[i];
                    }
                    // Calculate BCC (XOR checksum of the 4 UID bytes)
                    block0_data[4] = saved_uid[0] ^ saved_uid[1] ^ saved_uid[2] ^ saved_uid[3];

                    // Attempt write to Block 0 (Targeting "Magic" Gen1 tags)
                    status = mfrc522_write_block(0, block0_data);

                    if (status == MI_OK) {
                        uart_puts("SUCCESS: Card Cloned!\r\n");
                        has_saved_uid = false; // Reset for next pair
                        
                        // Long blink for success
                        PORTC |= (1 << PC0);
                        _delay_ms(1000);
                        PORTC &= ~(1 << PC0);
                    } else {
                        uart_puts("ERROR: Write failed. Use a UID-changeable tag.\r\n");
                        
                        // Error blink
                        PORTC |= (1 << PC1);
                        _delay_ms(500);
                        PORTC &= ~(1 << PC1);
                    }
                }
                
                // Halt the card to prevent constant re-reading while held at the reader
                mfrc522_halt();
            }
        }

        _delay_ms(300); // Poll delay
    }

    return 0;
}