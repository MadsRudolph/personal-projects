#include <avr/io.h>
#include <util/delay.h>
#include "uart.h"
#include "spi.h"
#include "mfrc522.h"

#define MODE_IDLE       0
#define MODE_CONTINUOUS 1
#define MODE_ONESHOT    2
#define MODE_WRITE      3
#define MODE_WRITE_BLK0 4

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

static const uint8_t default_key[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

static void send_block_data(uint8_t block, uint8_t *data) {
    uart_puts("DATA:");
    uart_put_hex(block);
    uart_putc(':');
    for (uint8_t i = 0; i < 16; i++) {
        uart_put_hex(data[i]);
    }
    uart_puts("\r\n");
}

static void do_dump(void) {
    uint8_t status;
    uint8_t atqa[2];
    uint8_t uid[5];
    uint8_t sak;
    uint8_t block_data[18]; // 16 data + 2 CRC from read

    // Detect card
    status = mfrc522_request(PICC_REQIDL, atqa);
    if (status != MI_OK) {
        uart_puts("ERR:NO_TAG\r\n");
        return;
    }

    status = mfrc522_anticoll(PICC_ANTICOLL1, uid);
    if (status != MI_OK) {
        uart_puts("ERR:ANTICOLL\r\n");
        return;
    }

    status = mfrc522_select(PICC_ANTICOLL1, uid, &sak);
    if (status != MI_OK) {
        uart_puts("ERR:SELECT\r\n");
        return;
    }

    // Read all 16 sectors
    for (uint8_t sector = 0; sector < 16; sector++) {
        uint8_t first_block = sector * 4;

        // Authenticate sector with Key A
        status = mfrc522_auth(PICC_AUTHKA, first_block, (uint8_t *)default_key, uid);
        if (status != MI_OK) {
            uart_puts("ERR:AUTH_FAIL:");
            uart_put_hex(sector);
            uart_puts("\r\n");
            continue;
        }

        // Read all 4 blocks in sector
        for (uint8_t b = 0; b < 4; b++) {
            uint8_t block = first_block + b;
            status = mfrc522_read_block(block, block_data);
            if (status == MI_OK) {
                send_block_data(block, block_data);
            } else {
                uart_puts("ERR:READ_FAIL:");
                uart_put_hex(block);
                uart_puts("\r\n");
            }
        }
    }

    mfrc522_stop_crypto();
    mfrc522_halt();
    uart_puts("OK:DUMP_COMPLETE\r\n");
}

static uint8_t hex_char_to_val(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return 0xFF;
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

static uint8_t write_uid[5];
static uint8_t write_authenticated_sector;

static uint8_t parse_hex_byte(const char *s) {
    uint8_t hi = hex_char_to_val(s[0]);
    uint8_t lo = hex_char_to_val(s[1]);
    if (hi == 0xFF || lo == 0xFF) return 0;
    return (hi << 4) | lo;
}

static void do_write_init(void) {
    uint8_t status;
    uint8_t atqa[2];
    uint8_t sak;

    status = mfrc522_request(PICC_REQIDL, atqa);
    if (status != MI_OK) {
        uart_puts("ERR:NO_TAG\r\n");
        return;
    }

    status = mfrc522_anticoll(PICC_ANTICOLL1, write_uid);
    if (status != MI_OK) {
        uart_puts("ERR:ANTICOLL\r\n");
        return;
    }

    status = mfrc522_select(PICC_ANTICOLL1, write_uid, &sak);
    if (status != MI_OK) {
        uart_puts("ERR:SELECT\r\n");
        return;
    }

    write_authenticated_sector = 0xFF;
    uart_puts("OK:WRITE_READY\r\n");
}

static void handle_load_line(char *line, uint8_t len, uint8_t allow_block0) {
    // Expect: LOAD:<2 hex chars block>:<32 hex chars data>
    // Minimum length: 5 (LOAD:) + 2 + 1 + 32 = 40
    if (len < 40) {
        uart_puts("ERR:BAD_FORMAT\r\n");
        return;
    }

    // Parse block number
    uint8_t block = parse_hex_byte(&line[5]);

    // Skip block 0 unless allowed
    if (block == 0 && !allow_block0) {
        uart_puts("OK:SKIP_BLK0\r\n");
        return;
    }

    // Parse 16 data bytes
    uint8_t data[16];
    for (uint8_t i = 0; i < 16; i++) {
        data[i] = parse_hex_byte(&line[8 + i * 2]);
    }

    // Authenticate if needed (new sector)
    uint8_t sector = block / 4;
    if (sector != write_authenticated_sector) {
        uint8_t status = mfrc522_auth(PICC_AUTHKA, block, (uint8_t *)default_key, write_uid);
        if (status != MI_OK) {
            uart_puts("ERR:WRITE_AUTH:");
            uart_put_hex(block);
            uart_puts("\r\n");
            return;
        }
        write_authenticated_sector = sector;
    }

    // Write block
    uint8_t status = mfrc522_write_block(block, data);
    if (status == MI_OK) {
        uart_puts("OK:WROTE:");
        uart_put_hex(block);
        uart_puts("\r\n");
    } else {
        uart_puts("ERR:WRITE_FAIL:");
        uart_put_hex(block);
        uart_puts("\r\n");
    }
}

int main(void) {
    uint8_t scan_mode = MODE_IDLE;
    char line_buf[48];
    uint8_t line_pos = 0;

    spi_init();
    uart_init(9600);
    mfrc522_init();

    DDRC |= (1 << PC0);

    uart_puts("INFO:RFID Tag Analyzer v2.0\r\n");

    while (1) {
        if (uart_available()) {
            char c = uart_getc();

            if (scan_mode == MODE_WRITE || scan_mode == MODE_WRITE_BLK0) {
                // In write mode: buffer lines until \r or \n
                if (c == '\r' || c == '\n') {
                    if (line_pos > 0) {
                        line_buf[line_pos] = '\0';
                        if (line_buf[0] == 'D') {
                            mfrc522_stop_crypto();
                            mfrc522_halt();
                            uart_puts("OK:WRITE_DONE\r\n");
                            scan_mode = MODE_IDLE;
                        } else if (line_pos >= 5 && line_buf[0] == 'L') {
                            handle_load_line(line_buf, line_pos,
                                scan_mode == MODE_WRITE_BLK0 ? 1 : 0);
                        } else {
                            uart_puts("ERR:BAD_CMD\r\n");
                        }
                        line_pos = 0;
                    }
                } else if (line_pos < sizeof(line_buf) - 1) {
                    line_buf[line_pos++] = c;
                }
            } else {
                // Normal command mode (single char commands)
                switch (c) {
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
                    uart_puts("INFO:RFID Tag Analyzer v2.0\r\n");
                    break;
                case 'R':
                    do_dump();
                    break;
                case 'W':
                    scan_mode = MODE_WRITE;
                    do_write_init();
                    break;
                case 'B':
                    scan_mode = MODE_WRITE_BLK0;
                    do_write_init();
                    break;
                }
            }
        }

        if (scan_mode == MODE_WRITE || scan_mode == MODE_WRITE_BLK0) {
            continue;  // No delay - must read UART fast to avoid RX overflow
        }

        if (scan_mode == MODE_IDLE) {
            _delay_ms(10);
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
