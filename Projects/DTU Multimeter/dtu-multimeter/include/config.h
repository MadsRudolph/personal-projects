#ifndef CONFIG_H
#define CONFIG_H

/** @file config.h
 *  @brief DTU Digital Multimeter master configuration.
 *
 *  Pin assignments, calibration constants, and compile-time parameters
 *  for the ATmega2560-based multimeter (Arduino Mega 2560, 16 MHz).
 */

#include <avr/io.h>
#include <stdbool.h>

/** @defgroup grp_config Configuration
 *  @brief Pin assignments, calibration values, and compile-time parameters.
 *  @{ */

/* ═══════════════════════════════════════════════════════════════════
 *  DTU Digital Multimeter — Master Configuration
 *  Target: ATmega2560 (Arduino Mega 2560), 16 MHz
 * ═══════════════════════════════════════════════════════════════════ */

#ifndef F_CPU
#define F_CPU 16000000UL
#endif

/** @defgroup adc_spi MCP3208 SPI ADC
 *  @brief 12-bit SPI ADC pin definitions and channel assignments.
 *
 *  Mega HW SPI: PB1=SCK(D52), PB2=MOSI(D51), PB3=MISO(D50).
 *  @{
 */
#define ADC_CS_DDR   DDRB
#define ADC_CS_PORT  PORTB
#define ADC_CS_BIT   PB0      /* D53 — chip select                  */

/** @name MCP3208 channel assignments */
/** @{ */
#define ADC_CH_RESIST    0    /**< Resistance measurement channel */
#define ADC_CH_VOLT_HI   1    /**< High-range voltage channel */
#define ADC_CH_VOLT_LO   2    /**< Low-range voltage channel */
#define ADC_CH_CURRENT   3    /**< Current measurement channel */
#define ADC_CH_AC_RECT   4    /**< AC rectified signal channel */
#define ADC_CH_TEMP      5    /**< Temperature sensor channel */
#define ADC_CH_SCOPE     6    /**< Oscilloscope input channel */
#define ADC_CH_AUX       7    /**< Auxiliary / spare channel */
/** @} */
/** @} */ /* end adc_spi */

/** @defgroup mux 74HC4067 16-Channel Analog Mux
 *  @brief Multiplexer select lines and enable pin.
 *
 *  S0-S3 = PA0-PA3 (D22-D25), EN = PA4 (D26, active LOW).
 *  @{
 */
#define MUX_DDR   DDRA
#define MUX_PORT  PORTA
#define MUX_S0    PA0         /**< Mux select bit 0 */
#define MUX_S1    PA1         /**< Mux select bit 1 */
#define MUX_S2    PA2         /**< Mux select bit 2 */
#define MUX_S3    PA3         /**< Mux select bit 3 */
#define MUX_EN    PA4         /**< Mux enable (active LOW) */
/** @} */

/** @defgroup cur_range CD4053 Current Range Switches
 *  @brief Triple 2:1 analog switch for current shunt selection.
 *
 *  A=PA5(D27), B=PA6(D28), C=PA7(D29), INH=PC7(D30).
 *  @{
 */
#define CUR_ABC_DDR   DDRA
#define CUR_ABC_PORT  PORTA
#define CUR_A         PA5     /**< CD4053 channel A select */
#define CUR_B         PA6     /**< CD4053 channel B select */
#define CUR_C         PA7     /**< CD4053 channel C select */
#define CUR_INH_DDR   DDRC
#define CUR_INH_PORT  PORTC
#define CUR_INH_BIT   PC7     /**< CD4053 inhibit (active HIGH) */
/** @} */

/** @defgroup cap Capacitance Charge/Discharge
 *  @brief GPIO pins for capacitance measurement charge/discharge cycle.
 *
 *  Charge = PC6(D31), Discharge = PC5(D32).
 *  @{
 */
#define CAP_CHG_DDR   DDRC
#define CAP_CHG_PORT  PORTC
#define CAP_CHG_PIN   PINC
#define CAP_CHG_BIT   PC6     /**< Capacitor charge control pin */
#define CAP_DIS_DDR   DDRC
#define CAP_DIS_PORT  PORTC
#define CAP_DIS_BIT   PC5     /**< Capacitor discharge control pin */
/** @} */

/** @defgroup isrc NE555 Constant Current Source
 *  @brief Enable pin for NE555-based constant current source.
 *
 *  Enable = PC4(D33).
 *  @{
 */
#define ISRC_DDR   DDRC
#define ISRC_PORT  PORTC
#define ISRC_BIT   PC4        /**< Current source enable pin */
/** @} */

/** @defgroup freq Frequency Input
 *  @brief External interrupt pin for frequency/duty/pulse measurement.
 *
 *  Arduino Mega D2 = PE4 (INT4).
 *  @{
 */
#define FREQ_DDR    DDRE
#define FREQ_PORT   PORTE
#define FREQ_PINR   PINE
#define FREQ_BIT    PE4       /**< Frequency counter input (INT4) */
/** @} */

/** @defgroup buttons Button Inputs
 *  @brief User button pin definitions.
 *
 *  MODE = PE5 (D3, INT5, interrupt driven),
 *  FUNC = PG5 (D4, polled),
 *  RANGE = PE3 (D5, polled),
 *  SEL = PH3 (D6, polled).
 *  @{
 */
#define BTN_MODE_DDR    DDRE
#define BTN_MODE_PORT   PORTE
#define BTN_MODE_PINR   PINE
#define BTN_MODE_BIT    PE5   /**< MODE button (INT5, interrupt) */

#define BTN_FUNC_DDR    DDRG
#define BTN_FUNC_PORT   PORTG
#define BTN_FUNC_PINR   PING
#define BTN_FUNC_BIT    PG5   /**< FUNC button (polled) */

#define BTN_RANGE_DDR   DDRE
#define BTN_RANGE_PORT  PORTE
#define BTN_RANGE_PINR  PINE
#define BTN_RANGE_BIT   PE3   /**< RANGE button (polled) */

#define BTN_SEL_DDR     DDRH
#define BTN_SEL_PORT    PORTH
#define BTN_SEL_PINR    PINH
#define BTN_SEL_BIT     PH3   /**< SELECT button (polled) */
/** @} */

/** @defgroup indicators Indicators (Buzzer & LEDs)
 *  @brief Buzzer and LED output pins.
 *
 *  Buzzer = PH4(D7), Red LED = PH5(D8),
 *  Green LED = PH6(D9), Yellow LED = PB4(D10).
 *  @{
 */
#define BUZZ_DDR   DDRH
#define BUZZ_PORT  PORTH
#define BUZZ_BIT   PH4       /**< Piezo buzzer output */

#define LEDR_DDR   DDRH
#define LEDR_PORT  PORTH
#define LEDR_BIT   PH5       /**< Red LED (overload / error) */

#define LEDG_DDR   DDRH
#define LEDG_PORT  PORTH
#define LEDG_BIT   PH6       /**< Green LED (normal / ready) */

#define LEDY_DDR   DDRB
#define LEDY_PORT  PORTB
#define LEDY_BIT   PB4       /**< Yellow LED (logging active) */
/** @} */

/** @defgroup scope_adc Scope Internal ADC
 *  @brief ATmega2560 internal ADC channels for oscilloscope mode.
 *
 *  A8 = ADC8 (needs MUX5), A9 = ADC9.
 *  @{
 */
#define SCOPE_ADC_CH    8     /**< Primary scope ADC channel */
#define SCOPE_ADC_CH2   9     /**< Secondary scope ADC channel */
/** @} */

/* ═══════════════════════════════════════════════════════════════════
 *  Calibration Constants — MEASURE ACTUAL VALUES AND UPDATE!
 * ═══════════════════════════════════════════════════════════════════ */

/** @defgroup calibration Calibration Constants
 *  @brief Hardware-specific calibration values. Measure and update for each board.
 *  @{
 */
#define V_REF         5.000f    /**< ADC reference voltage (measure Mega 5 V pin) */

/** @name Reference resistors (74HC4067 mux channels 0-7)
 *  @brief Precision resistors used for resistance divider measurement.
 *  @{ */
#define RREF_0        49.9f         /**< Ch0: 50 Ohm range */
#define RREF_1        499.0f        /**< Ch1: 500 Ohm range */
#define RREF_2        4990.0f       /**< Ch2: 5 k range */
#define RREF_3        48700.0f      /**< Ch3: 50 k range (DTU E96 closest) */
#define RREF_4        499000.0f     /**< Ch4: 500 k range */
#define RREF_5        4700000.0f    /**< Ch5: 5 M range */
#define RREF_6        10000000.0f   /**< Ch6: 50 M range */
#define RREF_7        10000000.0f   /**< Ch7: conductance */
/** @} */

#define VDIV_RATIO    11.0f   /**< Voltage divider ratio: (1M + 100k) / 100k = 11:1 */

/** @name Current shunt resistors (Ohms) — CD4053 ranges 0-5
 *  @{ */
#define ISHUNT_0      10000.0f      /**< 10 k   -- 500 uA range */
#define ISHUNT_1      1000.0f       /**< 1 k    -- 5 mA range */
#define ISHUNT_2      100.0f        /**< 100    -- 50 mA range */
#define ISHUNT_3      10.0f         /**< 10     -- 400 mA range */
#define ISHUNT_4      1.0f          /**< 1      -- 5 A range */
#define ISHUNT_5      0.1f          /**< 0.1    -- 10 A range */
/** @} */

/** @name LM358 amplifier gains
 *  @{ */
#define CUR_GAIN_LO   1.0f          /**< Low gain (unity) */
#define CUR_GAIN_HI   10.0f         /**< High gain (9.09 k / 1 k feedback) */
/** @} */

#define I_SOURCE       0.010f       /**< NE555 constant current source (~10 mA) */

/** @name Capacitance charge resistors
 *  @{ */
#define CAP_R0         1000000.0f   /**< 1 M  -- large caps */
#define CAP_R1         10000.0f     /**< 10 k -- medium caps */
#define CAP_R2         100.0f       /**< 100  -- small caps */
/** @} */

/** @name Inductance series resistors (reuse mux reference channels)
 *  @brief Known series R for RL step-response timing (L = tau * R).
 *  @{ */
#define IND_R0         4990.0f      /**< 4.99 k -- large inductors (H)    */
#define IND_R1         499.0f       /**< 499    -- medium inductors (mH)  */
#define IND_R2         49.9f        /**< 49.9   -- small inductors (uH)   */
/** @} */

/** @name Inductance mux channel assignments
 *  @{ */
#define IND_MUX_CH0    2            /**< Mux ch for IND range 0 (4.99 k)  */
#define IND_MUX_CH1    1            /**< Mux ch for IND range 1 (499)     */
#define IND_MUX_CH2    0            /**< Mux ch for IND range 2 (49.9)    */
/** @} */
/** @} */ /* end calibration */

/* ═══════════════════════════════════════════════════════════════════
 *  Oversampling & Auto-Range
 * ═══════════════════════════════════════════════════════════════════ */

/** @defgroup oversampling Oversampling & Auto-Range Thresholds
 *  @brief Parameters for oversampling (extra resolution bits) and auto-range switching.
 *  @{
 */
#define OS_EXTRA_BITS  3            /**< Extra bits of resolution from oversampling */
#define OS_COUNT       64           /**< 4^3 = 64 samples per oversample cycle */

#define RANGE_UP_THRESH   0.92f     /**< ADC > 92% full-scale triggers range up */
#define RANGE_DOWN_THRESH 0.08f     /**< ADC < 8% full-scale triggers range down */
/** @} */

/* ═══════════════════════════════════════════════════════════════════
 *  True-RMS Engine
 * ═══════════════════════════════════════════════════════════════════ */

/** @defgroup trms_cfg True-RMS Engine Configuration
 *  @brief Sample count and timing for True-RMS computation.
 *  @{
 */
#define TRMS_SAMPLES       400      /**< Number of samples per RMS window */
#define TRMS_INTERVAL_US   50       /**< Sample interval in microseconds (20 kHz) */
/** @} */

/* ═══════════════════════════════════════════════════════════════════
 *  Oscilloscope
 * ═══════════════════════════════════════════════════════════════════ */

/** @defgroup scope_cfg Oscilloscope Configuration
 *  @brief Buffer sizes and pre-trigger depth for oscilloscope mode.
 *  @{
 */
#define SCOPE_BUF_SIZE     1000     /**< Capture buffer size in samples */
#define SCOPE_PRETRIG      250      /**< Pre-trigger samples (25% of buffer) */
/** @} */

/* ═══════════════════════════════════════════════════════════════════
 *  Number of ranges per mode
 * ═══════════════════════════════════════════════════════════════════ */

/** @defgroup range_counts Range Counts
 *  @brief Number of selectable ranges for each measurement category.
 *  @{
 */
#define N_RES_RANGES  8             /**< Resistance ranges (8 mux channels) */
#define N_CUR_RANGES  6             /**< Current ranges (6 CD4053 shunts) */
#define N_CAP_RANGES  3             /**< Capacitance ranges (3 charge resistors) */
#define N_IND_RANGES  3             /**< Inductance ranges (3 series resistors) */
/** @} */

/* ═══════════════════════════════════════════════════════════════════
 *  Measurement Mode Enumeration
 * ═══════════════════════════════════════════════════════════════════ */

/** @brief Primary measurement modes (22 total, including oscilloscope). */
typedef enum {
    M_DCV = 0,     /**< DC Voltage */
    M_ACV,         /**< AC Voltage True-RMS */
    M_DCACV,       /**< DC+AC combined voltage */
    M_MV_DC,       /**< Millivolt DC */
    M_MV_AC,       /**< Millivolt AC */
    M_RESIST,      /**< Resistance */
    M_LOW_OHM,     /**< Low-Ohm (constant current source) */
    M_CONDUCT,     /**< Conductance (nS) */
    M_CONTIN,      /**< Continuity (buzzer) */
    M_DIODE,       /**< Diode test */
    M_CAP,         /**< Capacitance */
    M_IND,         /**< Inductance (RL step-response) */
    M_DCI,         /**< DC Current */
    M_ACI,         /**< AC Current True-RMS */
    M_DCACI,       /**< DC+AC Current */
    M_FREQ,        /**< Frequency */
    M_DUTY,        /**< Duty cycle */
    M_PULSE,       /**< Pulse width */
    M_TEMP,        /**< Temperature (LM35 sensor) */
    M_DBV,         /**< dBV (decibels relative to 1 V) */
    M_DBM,         /**< dBm (decibels relative to 1 mW) */
    M_SCOPE,       /**< Oscilloscope */
    M_COUNT        /**< Total number of modes (sentinel) */
} mode_t;

/* ═══════════════════════════════════════════════════════════════════
 *  Secondary Function Flags
 * ═══════════════════════════════════════════════════════════════════ */

/** @brief Secondary function modifiers applied to any measurement. */
typedef enum {
    FUNC_NONE = 0, /**< No secondary function active */
    FUNC_REL,      /**< Relative (delta) mode */
    FUNC_HOLD,     /**< Display hold */
    FUNC_MINMAX    /**< Min/Max recording */
} func_mode_t;

/* ═══════════════════════════════════════════════════════════════════
 *  Scope Trigger Modes
 * ═══════════════════════════════════════════════════════════════════ */

/** @brief Oscilloscope trigger modes. */
typedef enum {
    TRIG_AUTO = 0, /**< Auto-trigger (free-running if no edge found) */
    TRIG_RISING,   /**< Trigger on rising edge */
    TRIG_FALLING,  /**< Trigger on falling edge */
    TRIG_NONE,     /**< No trigger (continuous capture) */
    TRIG_SINGLE,   /**< Single-shot capture */
    TRIG_COUNT     /**< Number of trigger modes (sentinel) */
} trig_mode_t;

/* ═══════════════════════════════════════════════════════════════════
 *  Continuity threshold
 * ═══════════════════════════════════════════════════════════════════ */

#define CONTIN_THRESHOLD  25.0f     /**< Continuity beep threshold in Ohms */

/* ═══════════════════════════════════════════════════════════════════
 *  Data Logging
 * ═══════════════════════════════════════════════════════════════════ */

#define LOG_EEPROM_MAX    100       /**< Maximum circular EEPROM log entries */

/* ═══════════════════════════════════════════════════════════════════
 *  Low-Pass Filter default coefficient
 * ═══════════════════════════════════════════════════════════════════ */

#define LPF_ALPHA         0.1f     /**< IIR low-pass coefficient: y = 0.1*x + 0.9*y_prev */

/* ═══════════════════════════════════════════════════════════════════
 *  OLED dimensions
 * ═══════════════════════════════════════════════════════════════════ */

/** @defgroup oled OLED Display Parameters
 *  @brief SSD1306 128x64 I2C OLED dimensions and address.
 *  @{
 */
#define OLED_WIDTH   128            /**< Display width in pixels */
#define OLED_HEIGHT  64             /**< Display height in pixels */
#define OLED_PAGES   8              /**< Number of 8-pixel pages (64 / 8) */
#define OLED_ADDR    0x3C           /**< I2C slave address of the SSD1306 */
/** @} */

/* ═══════════════════════════════════════════════════════════════════
 *  UART buffer sizes
 * ═══════════════════════════════════════════════════════════════════ */

/** @defgroup grp_config_uart UART Buffer Sizes
 *  @brief Transmit and receive ring buffer sizes for UART0.
 *  @{
 */
#define UART_TX_BUF  64             /**< UART transmit buffer size in bytes */
#define UART_RX_BUF  32             /**< UART receive buffer size in bytes */
/** @} */

/** @} */ /* end grp_config */

#endif /* CONFIG_H */
