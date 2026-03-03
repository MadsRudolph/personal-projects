#ifndef MUX_H
#define MUX_H

/** @file mux.h
 *  @brief Multiplexer and analog switch control driver.
 *
 *  - 74HC4067 16-channel analog mux (S0-S3 = PA0-PA3, EN = PA4).
 *  - CD4053 triple 2:1 analog switch (A=PA5, B=PA6, C=PA7, INH=PC7).
 *  - NE555 constant-current source enable (PC4).
 *  - Capacitance charge/discharge control (PC5, PC6).
 */

#include <stdint.h>

/** @defgroup grp_mux Multiplexer & Analog Switches
 *  @brief 74HC4067 mux, CD4053 switches, NE555 current source, cap charge/discharge.
 *  @{ */

/** @defgroup mux_init Mux Initialisation
 *  @{ */

/** @brief Configure all mux/switch pins as outputs.
 *
 *  Mux disabled (EN=HIGH), CD4053 inhibited (INH=HIGH),
 *  current source off, capacitance pins Hi-Z. */
void mux_init(void);

/** @} */

/** @defgroup mux_4067 74HC4067 16-Channel Analog Mux
 *  @{ */

/** @brief Select a mux channel and enable the 74HC4067.
 *  @param channel Channel number (0--15). 50 us settle time applied. */
void mux_select(uint8_t channel);

/** @brief Disable the 74HC4067 (EN=HIGH), disconnecting the signal path. */
void mux_disable(void);

/** @} */

/** @defgroup mux_cd4053 CD4053 Current Shunt Selection
 *  @{ */

/** @brief Select a current measurement range via CD4053 A/B/C bits.
 *  @param range Range index (0--5). Uninhibits the switch with 50 us settle. */
void cur_select(uint8_t range);

/** @brief Inhibit the CD4053 (INH=HIGH), opening all switches. */
void cur_disable(void);

/** @} */

/** @defgroup isrc NE555 Constant Current Source
 *  @{ */

/** @brief Enable the NE555 constant-current source (ISRC pin HIGH). */
void isrc_enable(void);

/** @brief Disable the NE555 constant-current source (ISRC pin LOW). */
void isrc_disable(void);

/** @} */

/** @defgroup cap Capacitance Charge/Discharge
 *  @{ */

/** @brief Begin charging: charge pin HIGH, discharge pin Hi-Z. */
void cap_charge(void);

/** @brief Begin discharging: discharge pin LOW (output), charge pin LOW. */
void cap_discharge(void);

/** @brief Float both pins (input mode, Hi-Z). */
void cap_float(void);

/** @} */

/** @} */ /* end grp_mux */

#endif /* MUX_H */
