#include <avr/io.h>
#include <util/delay.h>
#include "uart.h"
#include "spi.h"
#include "mfrc522.h"

#define MODE_IDLE       0
#define MODE_CONTINUOUS 1
#define MODE_ONESHOT    2

// Print chip type and cloneability based on SAK byte (human-readable)
static void print_chip_info(uint8_t sak) {
    uart_puts("Chip Type: ");

    if (sak & 0x04) {
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

// Send tag data in protocol format: TAG:<atqa>:<uid>:<sak>:<uid_len>
static void send_tag_protocol(uint8_t *atqa, uint8_t *uid, uint8_t uid_len, uint8_t sak) {
    uart_puts("TAG:");
    uart_put_hex(atqa[0]);
    uart_put_hex(atqa[1]);
    uart_putc(':');
    for (uint8_t i = 0; i < uid_len; i++) {
        uart_put_hex(uid[i]);
    }
    uart_putc(':');
    uart_put_hex(sak);
    uart_putc(':');
    uart_putc('0' + uid_len);
    uart_puts("\r\n");
}

// Perform one scan cycle. Returns 1 if tag found, 0 otherwise.
static uint8_t do_scan(void) {
    uint8_t status;
    uint8_t atqa[2];
    uint8_t uid_cl1[5];
    uint8_t uid_cl2[5];
    uint8_t full_uid[10];
    uint8_t uid_len;
    uint8_t sak;

    status = mfrc522_request(PICC_REQIDL, atqa);
    if (status != MI_OK) return 0;

    status = mfrc522_anticoll(PICC_ANTICOLL1, uid_cl1);
    if (status != MI_OK) return 0;

    status = mfrc522_select(PICC_ANTICOLL1, uid_cl1, &sak);
    if (status != MI_OK) {
        uart_puts("ERR:SELECT CL1 failed\r\n");
        return 0;
    }

    uid_len = 4;
    if (sak & 0x04) {
        full_uid[0] = uid_cl1[1];
        full_uid[1] = uid_cl1[2];
        full_uid[2] = uid_cl1[3];

        status = mfrc522_anticoll(PICC_ANTICOLL2, uid_cl2);
        if (status != MI_OK) {
            uart_puts("ERR:ANTICOLL CL2 failed\r\n");
            return 0;
        }

        status = mfrc522_select(PICC_ANTICOLL2, uid_cl2, &sak);
        if (status != MI_OK) {
            uart_puts("ERR:SELECT CL2 failed\r\n");
            return 0;
        }

        full_uid[3] = uid_cl2[0];
        full_uid[4] = uid_cl2[1];
        full_uid[5] = uid_cl2[2];
        full_uid[6] = uid_cl2[3];
        uid_len = 7;

        if (sak & 0x04) {
            uart_puts("ERR:Triple-size UID not supported\r\n");
            mfrc522_halt();
            return 0;
        }
    } else {
        for (uint8_t i = 0; i < 4; i++) {
            full_uid[i] = uid_cl1[i];
        }
    }

    // LED on
    PORTC |= (1 << PC0);

    // Protocol line (for GUI)
    send_tag_protocol(atqa, full_uid, uid_len, sak);

    // Human-readable output (for terminal, ignored by GUI)
    uart_puts("ATQA: ");
    uart_put_hex(atqa[0]);
    uart_putc(' ');
    uart_put_hex(atqa[1]);
    uart_puts("  UID: ");
    for (uint8_t i = 0; i < uid_len; i++) {
        uart_put_hex(full_uid[i]);
        if (i < uid_len - 1) uart_putc(':');
    }
    uart_puts("  SAK: 0x");
    uart_put_hex(sak);
    uart_puts("\r\n");
    print_chip_info(sak);

    PORTC &= ~(1 << PC0);

    mfrc522_halt();
    return 1;
}

int main(void) {
    uint8_t scan_mode = MODE_IDLE;

    spi_init();
    uart_init(9600);
    mfrc522_init();

    DDRC |= (1 << PC0);

    uart_puts("INFO:RFID Tag Analyzer v1.0\r\n");

    while (1) {
        // Check for commands from GUI/terminal
        if (uart_available()) {
            char cmd = uart_getc();
            switch (cmd) {
            case 'S':
                scan_mode = MODE_CONTINUOUS;
                uart_puts("OK:Scanning\r\n");
                break;
            case 'P':
                scan_mode = MODE_IDLE;
                uart_puts("OK:Paused\r\n");
                break;
            case 'O':
                scan_mode = MODE_ONESHOT;
                uart_puts("OK:Single scan\r\n");
                break;
            case 'V':
                uart_puts("INFO:RFID Tag Analyzer v1.0\r\n");
                break;
            }
        }

        if (scan_mode == MODE_IDLE) {
            _delay_ms(100);
            continue;
        }

        if (do_scan()) {
            if (scan_mode == MODE_ONESHOT) {
                scan_mode = MODE_IDLE;
            }
            _delay_ms(1500);
        } else {
            _delay_ms(200);
        }
    }

    return 0;
}
