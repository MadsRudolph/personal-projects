#include "mfrc522.h"
#include "spi.h"
#include <avr/io.h>
#include <util/delay.h>

void mfrc522_write_reg(uint8_t reg, uint8_t val) {
    spi_select();
    spi_transfer((reg << 1) & 0x7E);  // address byte: 0AAAAAA0 (write)
    spi_transfer(val);
    spi_deselect();
}

uint8_t mfrc522_read_reg(uint8_t reg) {
    uint8_t val;
    spi_select();
    spi_transfer(((reg << 1) & 0x7E) | 0x80);  // address byte: 1AAAAAA0 (read)
    val = spi_transfer(0x00);  // dummy byte to clock in response
    spi_deselect();
    return val;
}

void mfrc522_set_bit(uint8_t reg, uint8_t mask) {
    mfrc522_write_reg(reg, mfrc522_read_reg(reg) | mask);
}

void mfrc522_clear_bit(uint8_t reg, uint8_t mask) {
    mfrc522_write_reg(reg, mfrc522_read_reg(reg) & ~mask);
}

// --- NEW: CRC Calculation Function ---
void mfrc522_calculate_crc(uint8_t *data, uint8_t len, uint8_t *result) {
    mfrc522_clear_bit(DivIrqReg, 0x04);    // Clear CRCIRq
    mfrc522_set_bit(FIFOLevelReg, 0x80);   // Flush FIFO
    mfrc522_write_reg(CommandReg, PCD_Idle);

    for (uint8_t i = 0; i < len; i++) {
        mfrc522_write_reg(FIFODataReg, data[i]);
    }
    
    mfrc522_write_reg(CommandReg, PCD_CalcCRC);

    // Wait for CRC calculation to complete
    uint8_t i = 0xFF;
    while (i--) {
        uint8_t n = mfrc522_read_reg(DivIrqReg);
        if (n & 0x04) break; 
    }

    result[0] = mfrc522_read_reg(CRCResultRegL);
    result[1] = mfrc522_read_reg(CRCResultRegH);
}

// --- NEW: Halt Function ---
void mfrc522_halt(void) {
    uint8_t buffer[4];
    buffer[0] = PICC_HALT;
    buffer[1] = 0;
    
    mfrc522_calculate_crc(buffer, 2, &buffer[2]);
    
    uint8_t back_data[16];
    uint8_t back_len;
    mfrc522_to_card(PCD_Transceive, buffer, 4, back_data, &back_len);
}

void mfrc522_antenna_on(void) {
    uint8_t val = mfrc522_read_reg(TxControlReg);
    if (!(val & 0x03)) {
        mfrc522_set_bit(TxControlReg, 0x03);  // enable TX1 and TX2
    }
}

void mfrc522_reset(void) {
    MFRC522_RST_DDR |= (1 << MFRC522_RST_PIN);
    MFRC522_RST_PORT &= ~(1 << MFRC522_RST_PIN);
    _delay_ms(10);
    MFRC522_RST_PORT |= (1 << MFRC522_RST_PIN);
    _delay_ms(50);

    mfrc522_write_reg(CommandReg, PCD_SoftReset);
    _delay_ms(50);
}

void mfrc522_init(void) {
    mfrc522_reset();
    mfrc522_write_reg(TModeReg, 0x80);
    mfrc522_write_reg(TPrescalerReg, 0xA9);
    mfrc522_write_reg(TReloadRegH, 0x03);
    mfrc522_write_reg(TReloadRegL, 0xE8);
    mfrc522_write_reg(TxASKReg, 0x40);
    mfrc522_write_reg(ModeReg, 0x3D);
    mfrc522_antenna_on();
}

uint8_t mfrc522_to_card(uint8_t command, uint8_t *send_data, uint8_t send_len,
                        uint8_t *back_data, uint8_t *back_len) {
    uint8_t status = MI_ERR;
    uint8_t irq_en = 0x00;
    uint8_t wait_irq = 0x00;
    uint8_t last_bits;
    uint8_t n;
    uint8_t i;

    if (command == PCD_Transceive) {
        irq_en = 0x77;
        wait_irq = 0x30;
    }

    mfrc522_write_reg(ComIEnReg, irq_en | 0x80);
    mfrc522_clear_bit(ComIrqReg, 0x80);
    mfrc522_set_bit(FIFOLevelReg, 0x80);
    mfrc522_write_reg(CommandReg, PCD_Idle);

    for (i = 0; i < send_len; i++) {
        mfrc522_write_reg(FIFODataReg, send_data[i]);
    }

    mfrc522_write_reg(CommandReg, command);

    if (command == PCD_Transceive) {
        mfrc522_set_bit(BitFramingReg, 0x80);
    }

    i = 255;
    do {
        n = mfrc522_read_reg(ComIrqReg);
        i--;
    } while (i && !(n & 0x01) && !(n & wait_irq));

    mfrc522_clear_bit(BitFramingReg, 0x80);

    if (i == 0) return MI_ERR;

    if (!(mfrc522_read_reg(ErrorReg) & 0x1B)) {
        status = MI_OK;
        if (n & 0x01) status = MI_NOTAGERR;

        if (command == PCD_Transceive) {
            n = mfrc522_read_reg(FIFOLevelReg);
            last_bits = mfrc522_read_reg(ControlReg) & 0x07;
            if (last_bits) *back_len = (n - 1) * 8 + last_bits;
            else *back_len = n * 8;

            if (n == 0) n = 1;
            if (n > 16) n = 16;

            for (i = 0; i < n; i++) {
                back_data[i] = mfrc522_read_reg(FIFODataReg);
            }
        }
    }
    return status;
}

uint8_t mfrc522_request(uint8_t req_mode, uint8_t *tag_type) {
    uint8_t status;
    uint8_t back_bits;
    mfrc522_write_reg(BitFramingReg, 0x07);
    tag_type[0] = req_mode;
    status = mfrc522_to_card(PCD_Transceive, tag_type, 1, tag_type, &back_bits);
    if (status != MI_OK || back_bits != 0x10) status = MI_ERR;
    return status;
}

uint8_t mfrc522_anticoll(uint8_t cascade_level, uint8_t *uid) {
    uint8_t status;
    uint8_t i;
    uint8_t uid_check = 0;
    uint8_t back_bits;
    uint8_t send[2];

    mfrc522_write_reg(BitFramingReg, 0x00);
    send[0] = cascade_level;
    send[1] = 0x20;

    status = mfrc522_to_card(PCD_Transceive, send, 2, uid, &back_bits);

    if (status == MI_OK) {
        for (i = 0; i < 4; i++) uid_check ^= uid[i];
        if (uid_check != uid[4]) status = MI_ERR;
    }
    return status;
}

uint8_t mfrc522_select(uint8_t cascade_level, uint8_t *uid, uint8_t *sak) {
    uint8_t status;
    uint8_t buffer[9];
    uint8_t back_data[3];
    uint8_t back_len;

    // Build SELECT command: [CL, NVB=0x70, UID0, UID1, UID2, UID3, BCC, CRC_L, CRC_H]
    buffer[0] = cascade_level;
    buffer[1] = 0x70;  // NVB: all 40 UID bits complete
    for (uint8_t i = 0; i < 5; i++) {
        buffer[2 + i] = uid[i];  // 4 UID bytes + BCC from anticoll
    }
    mfrc522_calculate_crc(buffer, 7, &buffer[7]);

    mfrc522_write_reg(BitFramingReg, 0x00);  // Full byte framing

    status = mfrc522_to_card(PCD_Transceive, buffer, 9, back_data, &back_len);
    if (status == MI_OK) {
        *sak = back_data[0];
    }
    return status;
}

uint8_t mfrc522_auth(uint8_t auth_mode, uint8_t block, uint8_t *key, uint8_t *uid) {
    uint8_t buffer[12];
    uint8_t n;
    uint8_t i;

    // Build auth command: [auth_mode, block, key(6), uid(4)]
    buffer[0] = auth_mode;
    buffer[1] = block;
    for (i = 0; i < 6; i++) {
        buffer[2 + i] = key[i];
    }
    for (i = 0; i < 4; i++) {
        buffer[8 + i] = uid[i];
    }

    // PCD_MFAuthent does not use transceive - it's a special command
    mfrc522_write_reg(ComIEnReg, 0x12);  // IdleIRq and ErrIRq
    mfrc522_clear_bit(ComIrqReg, 0x80);
    mfrc522_set_bit(FIFOLevelReg, 0x80); // Flush FIFO
    mfrc522_write_reg(CommandReg, PCD_Idle);

    // Write data to FIFO
    for (i = 0; i < 12; i++) {
        mfrc522_write_reg(FIFODataReg, buffer[i]);
    }

    mfrc522_write_reg(CommandReg, PCD_MFAuthent);

    // Wait for completion
    i = 255;
    do {
        n = mfrc522_read_reg(ComIrqReg);
        i--;
    } while (i && !(n & 0x01) && !(n & 0x10));

    // Check Status2Reg - Crypto1On bit indicates successful auth
    if (mfrc522_read_reg(Status2Reg) & 0x08) {
        return MI_OK;
    }
    return MI_ERR;
}

uint8_t mfrc522_read_block(uint8_t block, uint8_t *buffer) {
    uint8_t status;
    uint8_t cmd[4];
    uint8_t back_len;

    cmd[0] = PICC_READ;
    cmd[1] = block;
    mfrc522_calculate_crc(cmd, 2, &cmd[2]);

    status = mfrc522_to_card(PCD_Transceive, cmd, 4, buffer, &back_len);
    if (status != MI_OK || back_len != 0x90) {
        // 0x90 = 144 bits = 18 bytes (16 data + 2 CRC)
        return MI_ERR;
    }
    return MI_OK;
}

uint8_t mfrc522_write_block(uint8_t block, uint8_t *data) {
    uint8_t status;
    uint8_t cmd[4];
    uint8_t back_data[16];
    uint8_t back_len;

    // Phase 1: Send WRITE command + block number
    cmd[0] = PICC_WRITE;
    cmd[1] = block;
    mfrc522_calculate_crc(cmd, 2, &cmd[2]);

    status = mfrc522_to_card(PCD_Transceive, cmd, 4, back_data, &back_len);
    // Expect 4-bit ACK (0x0A)
    if (status != MI_OK || back_len != 4 || (back_data[0] & 0x0F) != 0x0A) {
        return MI_ERR;
    }

    // Phase 2: Send 16 bytes of data + CRC
    uint8_t write_buf[18];
    for (uint8_t i = 0; i < 16; i++) {
        write_buf[i] = data[i];
    }
    mfrc522_calculate_crc(write_buf, 16, &write_buf[16]);

    status = mfrc522_to_card(PCD_Transceive, write_buf, 18, back_data, &back_len);
    if (status != MI_OK || back_len != 4 || (back_data[0] & 0x0F) != 0x0A) {
        return MI_ERR;
    }

    return MI_OK;
}

void mfrc522_stop_crypto(void) {
    mfrc522_clear_bit(Status2Reg, 0x08);  // Clear MFCrypto1On bit
}
