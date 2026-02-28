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

void mfrc522_antenna_on(void) {
    uint8_t val = mfrc522_read_reg(TxControlReg);
    if (!(val & 0x03)) {
        mfrc522_set_bit(TxControlReg, 0x03);  // enable TX1 and TX2
    }
}

void mfrc522_reset(void) {
    // Hardware reset via RST pin
    MFRC522_RST_DDR |= (1 << MFRC522_RST_PIN);   // RST as output
    MFRC522_RST_PORT &= ~(1 << MFRC522_RST_PIN);  // RST low
    _delay_ms(10);
    MFRC522_RST_PORT |= (1 << MFRC522_RST_PIN);   // RST high
    _delay_ms(50);

    // Software reset
    mfrc522_write_reg(CommandReg, PCD_SoftReset);
    _delay_ms(50);
}

void mfrc522_init(void) {
    mfrc522_reset();

    // Timer: auto-start, prescaler 169 => 40kHz
    mfrc522_write_reg(TModeReg, 0x80);       // TAuto=1
    mfrc522_write_reg(TPrescalerReg, 0xA9);  // prescaler = 169
    mfrc522_write_reg(TReloadRegH, 0x03);    // reload = 0x03E8 = 1000
    mfrc522_write_reg(TReloadRegL, 0xE8);    // => 25ms timeout

    mfrc522_write_reg(TxASKReg, 0x40);       // 100% ASK modulation
    mfrc522_write_reg(ModeReg, 0x3D);        // CRC preset 0x6363

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
        irq_en = 0x77;    // TxIEn, RxIEn, IdleIEn, LoAlertIEn, ErrIEn, TimerIEn
        wait_irq = 0x30;  // RxIRq and IdleIRq
    }

    mfrc522_write_reg(ComIEnReg, irq_en | 0x80);  // enable IRQs
    mfrc522_clear_bit(ComIrqReg, 0x80);            // clear IRQ flags
    mfrc522_set_bit(FIFOLevelReg, 0x80);           // flush FIFO

    mfrc522_write_reg(CommandReg, PCD_Idle);        // cancel any active command

    // Write data to FIFO
    for (i = 0; i < send_len; i++) {
        mfrc522_write_reg(FIFODataReg, send_data[i]);
    }

    // Execute command
    mfrc522_write_reg(CommandReg, command);

    if (command == PCD_Transceive) {
        mfrc522_set_bit(BitFramingReg, 0x80);  // StartSend=1
    }

    // Wait for completion (timeout ~25ms from timer config)
    i = 255;
    do {
        n = mfrc522_read_reg(ComIrqReg);
        i--;
    } while (i && !(n & 0x01) && !(n & wait_irq));  // TimerIRq or wait_irq

    mfrc522_clear_bit(BitFramingReg, 0x80);  // stop transmission

    if (i == 0) {
        return MI_ERR;  // timeout
    }

    if (!(mfrc522_read_reg(ErrorReg) & 0x1B)) {  // no protocol errors
        status = MI_OK;

        if (n & 0x01) {  // TimerIRq — no card response
            status = MI_NOTAGERR;
        }

        if (command == PCD_Transceive) {
            n = mfrc522_read_reg(FIFOLevelReg);
            last_bits = mfrc522_read_reg(ControlReg) & 0x07;

            if (last_bits) {
                *back_len = (n - 1) * 8 + last_bits;
            } else {
                *back_len = n * 8;
            }

            if (n == 0) n = 1;
            if (n > 16) n = 16;  // max 16 bytes from FIFO

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

    mfrc522_write_reg(BitFramingReg, 0x07);  // TxLastBits=7 (short frame, 7 bits)

    tag_type[0] = req_mode;
    status = mfrc522_to_card(PCD_Transceive, tag_type, 1, tag_type, &back_bits);

    if (status != MI_OK || back_bits != 0x10) {  // expect 16-bit ATQA
        status = MI_ERR;
    }

    return status;
}

uint8_t mfrc522_anticoll(uint8_t *uid) {
    uint8_t status;
    uint8_t i;
    uint8_t uid_check = 0;
    uint8_t back_bits;
    uint8_t send[2];

    mfrc522_write_reg(BitFramingReg, 0x00);  // all bits valid

    send[0] = PICC_ANTICOLL;  // anti-collision command CL1
    send[1] = 0x20;           // NVB: 2 bytes sent (command + NVB only)

    status = mfrc522_to_card(PCD_Transceive, send, 2, uid, &back_bits);

    if (status == MI_OK) {
        // Verify BCC (byte 5 = XOR of bytes 1-4)
        for (i = 0; i < 4; i++) {
            uid_check ^= uid[i];
        }
        if (uid_check != uid[4]) {
            status = MI_ERR;
        }
    }

    return status;
}
