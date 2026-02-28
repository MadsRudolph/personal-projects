#include <avr/io.h>
#include <util/delay.h>
#include "uart.h"
#include "spi.h"
#include "mfrc522.h"

// Print chip type and cloneability based on SAK byte
static void print_chip_info(uint8_t sak) {
    uart_puts("Chip Type: ");

    if (sak & 0x04) {
        // Cascade bit set -- should not reach here after full resolution
        uart_puts("(incomplete UID, cascade error)\r\n");
        return;
    }

    switch (sak) {
    case 0x08:
        uart_puts("MIFARE Classic 1K\r\n");
        uart_puts("Cloneable with RC522: YES\r\n");
        break;
    case 0x18:
        uart_puts("MIFARE Classic 4K\r\n");
        uart_puts("Cloneable with RC522: YES\r\n");
        break;
    case 0x09:
        uart_puts("MIFARE Mini\r\n");
        uart_puts("Cloneable with RC522: YES\r\n");
        break;
    case 0x20:
        uart_puts("MIFARE DESFire or MIFARE Plus\r\n");
        uart_puts("ISO 14443-4: YES\r\n");
        uart_puts("Cloneable with RC522: NO\r\n");
        uart_puts("Note: AES-128 encryption. Need PN532 or Proxmark3.\r\n");
        break;
    case 0x00:
        uart_puts("MIFARE Ultralight or NTAG\r\n");
        uart_puts("Cloneable with RC522: PARTIAL (no crypto)\r\n");
        break;
    case 0x01:
        uart_puts("TNP3xxx (NFC Forum Type 2)\r\n");
        uart_puts("Cloneable with RC522: NO\r\n");
        break;
    case 0x10:
        uart_puts("MIFARE Plus (SL2)\r\n");
        uart_puts("Cloneable with RC522: NO\r\n");
        break;
    case 0x11:
        uart_puts("MIFARE Plus (SL3)\r\n");
        uart_puts("Cloneable with RC522: NO\r\n");
        break;
    default:
        uart_puts("Unknown (SAK=0x");
        uart_put_hex(sak);
        uart_puts(")\r\n");
        uart_puts("Cloneable with RC522: UNKNOWN\r\n");
        break;
    }
}

int main(void) {
    uint8_t status;
    uint8_t atqa[2];
    uint8_t uid_cl1[5];  // 4 UID bytes + BCC from CL1
    uint8_t uid_cl2[5];  // 4 UID bytes + BCC from CL2
    uint8_t full_uid[10];
    uint8_t uid_len;
    uint8_t sak;

    spi_init();
    uart_init(9600);
    mfrc522_init();

    // LED pins: PC0 = detection indicator
    DDRC |= (1 << PC0);

    uart_puts("\r\n--- RFID Tag Analyzer ---\r\n");
    uart_puts("Present a tag to scan...\r\n\r\n");

    while (1) {
        // Step 1: REQA -- detect card, get ATQA
        status = mfrc522_request(PICC_REQIDL, atqa);
        if (status != MI_OK) {
            _delay_ms(200);
            continue;
        }

        // Step 2: Anti-collision CL1 -- get first 4 UID bytes + BCC
        status = mfrc522_anticoll(PICC_ANTICOLL1, uid_cl1);
        if (status != MI_OK) {
            _delay_ms(200);
            continue;
        }

        // Step 3: SELECT CL1 -- activate card, get SAK
        status = mfrc522_select(PICC_ANTICOLL1, uid_cl1, &sak);
        if (status != MI_OK) {
            uart_puts("SELECT CL1 failed\r\n");
            _delay_ms(500);
            continue;
        }

        // Step 4: Check if cascade needed (SAK bit 2)
        uid_len = 4;
        if (sak & 0x04) {
            // CL1 UID starts with cascade tag (0x88) -- real UID bytes are [1..3]
            full_uid[0] = uid_cl1[1];
            full_uid[1] = uid_cl1[2];
            full_uid[2] = uid_cl1[3];

            // Anti-collision CL2
            status = mfrc522_anticoll(PICC_ANTICOLL2, uid_cl2);
            if (status != MI_OK) {
                uart_puts("ANTICOLL CL2 failed\r\n");
                _delay_ms(500);
                continue;
            }

            // SELECT CL2
            status = mfrc522_select(PICC_ANTICOLL2, uid_cl2, &sak);
            if (status != MI_OK) {
                uart_puts("SELECT CL2 failed\r\n");
                _delay_ms(500);
                continue;
            }

            full_uid[3] = uid_cl2[0];
            full_uid[4] = uid_cl2[1];
            full_uid[5] = uid_cl2[2];
            full_uid[6] = uid_cl2[3];
            uid_len = 7;

            // Check for triple cascade (10-byte UID, very rare)
            if (sak & 0x04) {
                uart_puts("Triple-size UID (10 bytes) -- not supported yet\r\n");
                mfrc522_halt();
                _delay_ms(1000);
                continue;
            }
        } else {
            // Simple 4-byte UID
            for (uint8_t i = 0; i < 4; i++) {
                full_uid[i] = uid_cl1[i];
            }
        }

        // LED blink: tag detected
        PORTC |= (1 << PC0);

        // Print diagnostic report
        uart_puts("=== Tag Detected ===\r\n");

        uart_puts("ATQA: ");
        uart_put_hex(atqa[0]);
        uart_putc(' ');
        uart_put_hex(atqa[1]);
        uart_puts("\r\n");

        uart_puts("UID:  ");
        for (uint8_t i = 0; i < uid_len; i++) {
            uart_put_hex(full_uid[i]);
            if (i < uid_len - 1) uart_putc(':');
        }
        uart_puts(" (");
        uart_putc('0' + uid_len);  // works for 4, 7
        uart_puts(" bytes)\r\n");

        uart_puts("SAK:  0x");
        uart_put_hex(sak);
        uart_puts("\r\n");

        print_chip_info(sak);

        uart_puts("====================\r\n\r\n");

        PORTC &= ~(1 << PC0);

        // Halt card, wait before next scan
        mfrc522_halt();
        _delay_ms(2000);
    }

    return 0;
}
