/**
 * caliper.h -- Decoder for the caliper's synchronous serial output.
 *
 * The caliper pushes frames out on its own schedule a few times a second;
 * there is no request line. We capture edges in an ISR and decode in the main
 * loop, so nothing here blocks.
 */
#pragma once

#include <Arduino.h>
#include "config.h"

struct CaliperReading {
    double value;     // signed, already scaled to mm or inches
    bool   inches;    // true if `value` is in inches
    bool   valid;
};

/** Configure pins and attach the clock interrupt. */
void caliperBegin();

/**
 * Copy the most recent complete frame into `bits` (CALIPER_FRAME_BITS entries,
 * index 0 = first bit received). Returns false if no new frame has arrived
 * since the last call.
 */
bool caliperTakeFrame(uint8_t *bits);

/** Decode a captured frame into a reading. */
CaliperReading caliperDecode(const uint8_t *bits);

/** Unit selection, used when the caliper sends no unit bit. */
void caliperSetInches(bool inches);
bool caliperIsInches();

/** micros() timestamp of the last clock edge seen, for liveness checks. */
uint32_t caliperLastEdgeUs();
