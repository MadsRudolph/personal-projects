/**
 * BLE Digital Caliper -- types measurements into any CAD package as a
 * Bluetooth keyboard, so there is no host-side software to install.
 *
 * Bring-up order:
 *   1. CALIPER_SNIFFER_MODE = 1, watch raw frames over USB serial, confirm the
 *      bit layout in config.h against your own caliper.
 *   2. CALIPER_SNIFFER_MODE = 0, pair over BLE, measure something known.
 *
 * See ../docs/protocol-notes.md for the worksheet.
 */
#include <Arduino.h>
#include "config.h"
#include "caliper.h"

#if !CALIPER_SNIFFER_MODE
#include <BleKeyboard.h>
static BleKeyboard bleKeyboard(BLE_DEVICE_NAME, BLE_MANUFACTURER, 100);
#endif

static uint8_t  g_bits[CALIPER_FRAME_BITS];
static CaliperReading g_last = {0.0, false, false};
static uint32_t g_lastActivityMs = 0;

// --- tiny debounced button -------------------------------------------------
struct Button {
    int      pin = -1;          // negative means this button is not fitted
    bool     stable   = true;   // pulled up, so idle is high
    bool     lastRead = true;
    uint32_t changedMs = 0;

    void begin(int p) {
        pin = p;
        if (pin >= 0) {
            pinMode(pin, INPUT_PULLUP);
        }
    }

    // True exactly once per press.
    bool pressed() {
        if (pin < 0) {
            return false;
        }
        bool now = digitalRead(pin);
        if (now != lastRead) {
            lastRead  = now;
            changedMs = millis();
        }
        if (millis() - changedMs > 25 && now != stable) {
            stable = now;
            if (!stable) return true;   // high -> low is the press
        }
        return false;
    }
};

static Button btnSend, btnSendAlt;

// ---------------------------------------------------------------------------

/** Format with the host's decimal separator, since HID sends scancodes. */
static String formatReading(const CaliperReading &r) {
    char buf[16];
    dtostrf(r.value, 0, r.inches ? 4 : 2, buf);

    String s(buf);
    if (DECIMAL_SEPARATOR != '.') {
        s.replace('.', DECIMAL_SEPARATOR);
    }
    return s;
}

static void dumpFrame(const uint8_t *bits, const CaliperReading &r) {
    Serial.print("raw ");
    for (int i = 0; i < CALIPER_FRAME_BITS; i++) {
        if (i && i % 4 == 0) Serial.print(' ');
        Serial.print(bits[i] ? '1' : '0');
    }
    Serial.print("  ->  ");
    Serial.print(formatReading(r));
    Serial.println(r.inches ? " in" : " mm");
}

#if SLEEP_TIMEOUT_MIN > 0
static void enterDeepSleep() {
    Serial.println("idle -- sleeping");
    Serial.flush();
#if defined(CONFIG_IDF_TARGET_ESP32)
    // The classic ESP32 has no GPIO deep-sleep wake source -- that only exists
    // on the C3 and later. EXT0 is the equivalent here, and it requires an
    // RTC-capable pin, which is why PIN_BTN_SEND is GPIO32 on this board.
    esp_sleep_enable_ext0_wakeup((gpio_num_t)PIN_BTN_SEND, 0);
#else
    esp_deep_sleep_enable_gpio_wakeup(1ULL << PIN_BTN_SEND, ESP_GPIO_WAKEUP_GPIO_LOW);
#endif
    esp_deep_sleep_start();
}
#endif

void setup() {
    Serial.begin(115200);

    btnSend.begin(PIN_BTN_SEND);
    btnSendAlt.begin(PIN_BTN_SEND_ALT);

#if PIN_BTN_SEND_ALT >= 0
    // Holding both buttons at boot flips the unit, for calipers that send no
    // unit bit in the frame. Needs two buttons, and it cannot be done on the
    // BOOT button: holding GPIO0 through a reset enters download mode.
    delay(50);
    if (!digitalRead(PIN_BTN_SEND) && !digitalRead(PIN_BTN_SEND_ALT)) {
        caliperSetInches(!CALIPER_DEFAULT_INCHES);
    }
#endif

    caliperBegin();
    g_lastActivityMs = millis();

#if CALIPER_SNIFFER_MODE
    Serial.println("sniffer mode -- move the caliper, frames follow");
#else
    bleKeyboard.begin();
    // Without this the port is silent in BLE mode, so there is no way to tell
    // a running board from a dead one.
    Serial.print("BLE mode -- advertising as ");
    Serial.println(BLE_DEVICE_NAME);
    Serial.print("Pair from the host, focus a field, then press the button on "
                 "GPIO");
    Serial.println(PIN_BTN_SEND);
#endif
}

#if CALIPER_SNIFFER_MODE
/* Bring-up heartbeat. Prints even when nothing is arriving, which is the
 * case that needs the most help: it separates "no edges reach the pin at
 * all" (wiring or shifter) from "edges arrive but frames never complete"
 * (timing), and shows the idle levels the shifter is presenting. With
 * SHIFTER_INVERTS the caliper's idle-high lines should read LOW here. */
static void heartbeat() {
    static uint32_t lastMs = 0;
    if (millis() - lastMs < 2000) {
        return;
    }
    lastMs = millis();

    const uint32_t edges = caliperEdgeCount();
    Serial.printf("hb: edges=%lu  bit=%u/%u  CLK(gpio%d)=%d DATA(gpio%d)=%d",
                  (unsigned long)edges, caliperPartialIndex(),
                  CALIPER_FRAME_BITS, PIN_CALIPER_CLK,
                  digitalRead(PIN_CALIPER_CLK), PIN_CALIPER_DATA,
                  digitalRead(PIN_CALIPER_DATA));
    if (edges) {
        Serial.printf("  last edge %lu ms ago",
                      (unsigned long)((micros() - caliperLastEdgeUs()) / 1000));
    } else {
        Serial.print("  -- NO EDGES: check the shifter, not the decode");
    }
    Serial.println();
}
#endif

void loop() {
#if CALIPER_SNIFFER_MODE
    heartbeat();
#endif
    if (caliperTakeFrame(g_bits)) {
        g_last = caliperDecode(g_bits);
#if CALIPER_SNIFFER_MODE
        dumpFrame(g_bits, g_last);
#endif
    }

#if !CALIPER_SNIFFER_MODE
    // Report the link only when it changes, so the port stays quiet in use.
    static int wasConnected = -1;
    const bool connected = bleKeyboard.isConnected();
    if ((int)connected != wasConnected) {
        wasConnected = connected;
        Serial.println(connected ? "BLE connected -- press to type"
                                 : "BLE waiting for a host");
    }
    if (!connected) {
        return;
    }

    // Button 1 types the value and moves on; button 2 leaves the caret in the
    // field, with a space after the value, so a tolerance can be typed.
    const bool send    = btnSend.pressed();
    const bool sendAlt = btnSendAlt.pressed();

    if (send || sendAlt) {
        if (g_last.valid && micros() - caliperLastEdgeUs() < 2000000UL) {
            bleKeyboard.print(formatReading(g_last).c_str());
            if (sendAlt) {
                bleKeyboard.print(" ");
            }
#if SEND_TERMINATOR
            else {
                bleKeyboard.write(SEND_TERMINATOR_KEY);
            }
#endif
            g_lastActivityMs = millis();
        } else {
            Serial.println("no fresh reading -- is the caliper on?");
        }
    }

#if SLEEP_TIMEOUT_MIN > 0
    if (millis() - g_lastActivityMs > (uint32_t)SLEEP_TIMEOUT_MIN * 60000UL) {
        enterDeepSleep();
    }
#endif
#endif
}
