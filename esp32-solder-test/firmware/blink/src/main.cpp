#include <Arduino.h>

// Green LED D1 on GPIO2, active high (GPIO2 -> 332R -> LED -> GND).
const int LED_PIN = 2;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  Serial.begin(115200);
  Serial.println();
  Serial.println("ESP32 solder test: blink on GPIO2");
}

void loop() {
  static unsigned long n = 0;
  digitalWrite(LED_PIN, HIGH);
  Serial.printf("blink %lu on\n", n);
  delay(500);
  digitalWrite(LED_PIN, LOW);
  Serial.printf("blink %lu off\n", n);
  delay(500);
  n++;
}
