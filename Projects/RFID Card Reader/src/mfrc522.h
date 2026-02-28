#ifndef MFRC522_H
#define MFRC522_H

#include <stdint.h>

// RST pin - PB1 (Arduino D9)
#define MFRC522_RST_DDR   DDRB
#define MFRC522_RST_PORT  PORTB
#define MFRC522_RST_PIN   PB1

// Status codes
#define MI_OK       0
#define MI_NOTAGERR 1
#define MI_ERR      2

// MFRC522 register addresses (datasheet Table 20)
// Page 0: Command and Status
#define CommandReg      0x01
#define ComIEnReg       0x02
#define DivIEnReg       0x03
#define ComIrqReg       0x04
#define DivIrqReg       0x05
#define ErrorReg        0x06
#define Status1Reg      0x07
#define Status2Reg      0x08
#define FIFODataReg     0x09
#define FIFOLevelReg    0x0A
#define WaterLevelReg   0x0B
#define ControlReg      0x0C
#define BitFramingReg   0x0D
#define CollReg         0x0E

// Page 1: Communication
#define ModeReg         0x11
#define TxModeReg       0x12
#define RxModeReg       0x13
#define TxControlReg    0x14
#define TxASKReg        0x15

// Page 2: Configuration
#define CRCResultRegH   0x21
#define CRCResultRegL   0x22
#define ModWidthReg     0x24
#define RFCfgReg        0x26
#define GsNReg          0x27
#define CWGsPReg        0x28
#define ModGsPReg       0x29
#define TModeReg        0x2A
#define TPrescalerReg   0x2B
#define TReloadRegH     0x2C
#define TReloadRegL     0x2D

// Page 3: Test
#define VersionReg      0x37

// PCD commands (written to CommandReg)
#define PCD_Idle        0x00
#define PCD_CalcCRC     0x03
#define PCD_Transmit    0x04
#define PCD_Receive     0x08
#define PCD_Transceive  0x0C
#define PCD_MFAuthent   0x0E
#define PCD_SoftReset   0x0F

// PICC commands
#define PICC_REQIDL     0x26  // REQA - request idle cards
#define PICC_REQALL     0x52  // WUPA - request all cards
#define PICC_ANTICOLL   0x93  // Anti-collision/Select CL1
#define PICC_HALT       0x50

// Max UID length
#define MFRC522_UID_LEN 4

// Function prototypes
void    mfrc522_init(void);
void    mfrc522_write_reg(uint8_t reg, uint8_t val);
uint8_t mfrc522_read_reg(uint8_t reg);
void    mfrc522_set_bit(uint8_t reg, uint8_t mask);
void    mfrc522_clear_bit(uint8_t reg, uint8_t mask);
void    mfrc522_antenna_on(void);
void    mfrc522_reset(void);
uint8_t mfrc522_request(uint8_t req_mode, uint8_t *tag_type);
uint8_t mfrc522_anticoll(uint8_t *uid);
uint8_t mfrc522_to_card(uint8_t command, uint8_t *send_data, uint8_t send_len,
                        uint8_t *back_data, uint8_t *back_len);

#endif
