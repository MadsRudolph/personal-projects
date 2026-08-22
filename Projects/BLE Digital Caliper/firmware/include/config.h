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
// The 24-bit format below is what most budget calipers emit, and matches the
// Neiko unit documented in docs/prior-art.md. Bit layouts DO vary between
// makes and even between production runs of the same model, so confirm yours
// with CALIPER_SNIFFER_MODE before trusting any reading.
#define CALIPER_FRAME_BITS       24

#define CALIPER_VALUE_FIRST_BIT   1   // first magnitude bit (LSB first)
#define CALIPER_VALUE_LAST_BIT   14   // last magnitude bit, inclusive
#define CALIPER_SIGN_BIT         21   // 1 = negative

// Some calipers signal mm/inch in the frame; many newer ones do not. When the
// unit bit is absent, set CALIPER_HAS_UNIT_BIT to 0 and pick the unit with
// CALIPER_DEFAULT_INCHES (or hold both buttons at boot to toggle).
#define CALIPER_HAS_UNIT_BIT      0
#define CALIPER_UNIT_BIT         23   // only consulted when HAS_UNIT_BIT is 1
#define CALIPER_DEFAULT_INCHES    0

// Magnitude is a raw count. Metric counts are 0.01 mm, imperial 0.0005 in.
#define CALIPER_MM_PER_COUNT      0.01
#define CALIPER_INCH_PER_COUNT    0.0005

// A gap longer than this means the next edge starts a fresh frame.
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
