/**
 * config.h -- Build-time configuration for the BLE digital caliper.
 *
 * Everything you are likely to change while bringing the hardware up lives
 * here. The defaults target an ESP32-C3 SuperMini on a breadboard.
 */
#pragma once

// ---------------------------------------------------------------------------
// Pin map (ESP32-C3 SuperMini)
// ---------------------------------------------------------------------------
// CLK and DATA arrive from the caliper via the transistor level shifter, which
// INVERTS both lines. See ../../hardware/level-shifter.md.
//
// The caliper side runs at 1.085 V, not the 1.5 V an LR44 implies -- measured,
// see docs/protocol-notes.md. Size the shifter for that.
#define PIN_CALIPER_CLK   3
#define PIN_CALIPER_DATA  1

// Momentary buttons to ground, using the internal pull-ups.
#define PIN_BTN_SEND      4   // type the value, then Enter
#define PIN_BTN_SEND_ALT  5   // type the value, then Space (room for tolerance)

// Optional. Set to -1 if your board has no WS2812.
#define PIN_STATUS_LED    8

// ---------------------------------------------------------------------------
// Level shifter polarity
// ---------------------------------------------------------------------------
// The two-transistor shifter is a pair of common-emitter inverters, so a logic
// high at the caliper reads as a low on the ESP32. Set to 0 only if you use a
// non-inverting shifter.
#define SHIFTER_INVERTS   1

// ---------------------------------------------------------------------------
// Protocol -- VERIFY THESE AGAINST YOUR OWN CALIPER
// ---------------------------------------------------------------------------
// MEASURED and VERIFIED on this caliper with an Analog Discovery 3 -- see
// docs/protocol-notes.md. Eight captures spanning 0 to full scale, plus a
// negative and an inch reading, all decode to their displayed value with zero
// error using exactly the values below.
//
// DATA is valid on the FALLING edge of CLK at the caliper.
//
// The magnitude field really is 14 bits: full scale is 163.82 mm = 16382
// counts, and 2^14 - 1 = 16383. The caliper's range IS the field's capacity,
// which is about as direct a confirmation as you get.
#define CALIPER_FRAME_BITS       24

#define CALIPER_VALUE_FIRST_BIT   1   // first magnitude bit (LSB first)
#define CALIPER_VALUE_LAST_BIT   14   // last magnitude bit, inclusive
#define CALIPER_SIGN_BIT         21   // 1 = negative (verified at -1.11 mm)

// This caliper has NO unit bit -- confirmed. Switching the display to inches
// changes the COUNT SCALE and nothing else: 1.001 in came through as 2002
// counts of 0.0005 in, and every bit outside the magnitude and sign fields
// stayed 0. docs/prior-art.md saw the same on a newer unit.
//
// The consequence matters: the frame does not say what unit it is in, so if
// you switch the caliper to inches and do not tell the firmware, it will type
// a number that is wrong by a factor of 25.4/0.5. Pick the unit with
// CALIPER_DEFAULT_INCHES, or hold both buttons at boot to toggle.
#define CALIPER_HAS_UNIT_BIT      0
#define CALIPER_UNIT_BIT         23   // only consulted when HAS_UNIT_BIT is 1
#define CALIPER_DEFAULT_INCHES    0

// Magnitude is a raw count. Both scales verified against the display:
// 163.82 mm = 16382 counts of 0.01 mm, and 1.0010 in = 2002 counts of
// 0.0005 in.
#define CALIPER_MM_PER_COUNT      0.01
#define CALIPER_INCH_PER_COUNT    0.0005

// A gap longer than this means the next edge starts a fresh frame. Measured on
// this caliper: 145 ms between frames, and 930 us between the six groups of
// four clock pulses within a frame. 3000 sits safely between the two.
#define CALIPER_FRAME_GAP_US   3000

// ---------------------------------------------------------------------------
// Bring-up aids
// ---------------------------------------------------------------------------
// 1 = dump every raw frame as binary over USB serial and do not touch BLE.
// This is the first thing to run against an unknown caliper.
#define CALIPER_SNIFFER_MODE      1

// ---------------------------------------------------------------------------
// Host keyboard behaviour
// ---------------------------------------------------------------------------
// HID sends scancodes, not characters, so the decimal separator depends on the
// host's keyboard layout. On a Danish layout '.' and ',' are different keys and
// Windows may expect a comma. Set to ',' if your CAD field rejects the value.
#define DECIMAL_SEPARATOR       '.'

#define BLE_DEVICE_NAME         "Caliper"
#define BLE_MANUFACTURER        "MadsRudolph"

// Idle minutes before deep sleep. Wake is via the send button.
#define SLEEP_TIMEOUT_MIN         3
