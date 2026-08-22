#include "caliper.h"

static volatile uint8_t  s_partial[CALIPER_FRAME_BITS];
static volatile uint8_t  s_frame[CALIPER_FRAME_BITS];
static volatile uint8_t  s_index       = 0;
static volatile uint32_t s_lastEdgeUs  = 0;
static volatile bool     s_frameReady  = false;

static bool s_inches = CALIPER_DEFAULT_INCHES;

static portMUX_TYPE s_mux = portMUX_INITIALIZER_UNLOCKED;

/*
 * The level shifter inverts, so the caliper's falling clock edge arrives here
 * as a rising edge. Data is sampled three times and majority-voted: the
 * shifter's transitions are slow enough to produce the occasional glitch, and
 * a single bad sample corrupts the whole reading.
 */
static void IRAM_ATTR onClockEdge() {
    const uint32_t now = micros();

    if (now - s_lastEdgeUs > CALIPER_FRAME_GAP_US) {
        s_index = 0;  // long silence -- this edge starts a new frame
    }
    s_lastEdgeUs = now;

    int votes = digitalRead(PIN_CALIPER_DATA)
              + digitalRead(PIN_CALIPER_DATA)
              + digitalRead(PIN_CALIPER_DATA);
    uint8_t bit = (votes >= 2) ? 1 : 0;
#if SHIFTER_INVERTS
    bit = bit ? 0 : 1;
#endif

    if (s_index < CALIPER_FRAME_BITS) {
        s_partial[s_index++] = bit;

        if (s_index == CALIPER_FRAME_BITS) {
            for (uint8_t i = 0; i < CALIPER_FRAME_BITS; i++) {
                s_frame[i] = s_partial[i];
            }
            s_frameReady = true;
            s_index = 0;
        }
    }
}

void caliperBegin() {
    pinMode(PIN_CALIPER_CLK, INPUT);
    pinMode(PIN_CALIPER_DATA, INPUT);

#if SHIFTER_INVERTS
    attachInterrupt(digitalPinToInterrupt(PIN_CALIPER_CLK), onClockEdge, RISING);
#else
    attachInterrupt(digitalPinToInterrupt(PIN_CALIPER_CLK), onClockEdge, FALLING);
#endif
}

bool caliperTakeFrame(uint8_t *bits) {
    bool got = false;

    portENTER_CRITICAL(&s_mux);
    if (s_frameReady) {
        for (uint8_t i = 0; i < CALIPER_FRAME_BITS; i++) {
            bits[i] = s_frame[i];
        }
        s_frameReady = false;
        got = true;
    }
    portEXIT_CRITICAL(&s_mux);

    return got;
}

CaliperReading caliperDecode(const uint8_t *bits) {
    CaliperReading r = {0.0, s_inches, false};

#if CALIPER_CHECK_MARKER
    // Cheapest possible guard against a frame shifted by one bit -- see the
    // note in config.h. Returning invalid keeps main.cpp from typing it.
    if (bits[CALIPER_MARKER_BIT] != CALIPER_MARKER_VALUE) {
        return r;
    }
#endif

    // Magnitude is little-endian: CALIPER_VALUE_FIRST_BIT is the LSB.
    uint32_t raw = 0;
    for (int i = CALIPER_VALUE_LAST_BIT; i >= CALIPER_VALUE_FIRST_BIT; i--) {
        raw = (raw << 1) | (bits[i] & 1);
    }

#if CALIPER_HAS_UNIT_BIT
    r.inches = bits[CALIPER_UNIT_BIT] != 0;
#endif

    r.value = r.inches ? raw * CALIPER_INCH_PER_COUNT
                       : raw * CALIPER_MM_PER_COUNT;

    if (bits[CALIPER_SIGN_BIT]) {
        r.value = -r.value;
    }

    r.valid = true;
    return r;
}

void caliperSetInches(bool inches) { s_inches = inches; }
bool caliperIsInches()             { return s_inches; }
uint32_t caliperLastEdgeUs()       { return s_lastEdgeUs; }
