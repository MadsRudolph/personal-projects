#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include "secrets.h"

// Green LED D1 on GPIO2, active high (GPIO2 -> 332R -> LED -> GND).
const int LED_PIN = 2;
const float HZ_MIN = 0.1f;
const float HZ_MAX = 20.0f;

WebServer server(80);
Preferences prefs;

float blinkHz = 1.0f;
bool ledOn = false;
unsigned long lastToggle = 0;

// The LM317 supply sags on full-power WiFi bursts (see BRINGUP.md), and a
// phone hotspot is close by, so transmit at low power.
const wifi_power_t TX_POWER = WIFI_POWER_8_5dBm;

const char PAGE[] PROGMEM = R"HTML(<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESP32 Blink</title>
<style>
:root{--bg:#f4f4f1;--card:#fff;--fg:#1d1d1b;--mute:#6b6b66;--acc:#1f9d55;--line:#e2e2dc}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1f1f1d;--fg:#eeeeea;--mute:#9a9a94;--acc:#3ccf7a;--line:#33332f}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.4 system-ui,sans-serif;display:flex;justify-content:center;padding:24px 16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:24px;width:100%;max-width:420px}
h1{font-size:18px;margin:0 0 4px}
.sub{color:var(--mute);font-size:13px;margin-bottom:24px}
.led{width:56px;height:56px;border-radius:50%;margin:0 auto 20px;background:var(--line);transition:background .05s,box-shadow .05s}
.led.on{background:var(--acc);box-shadow:0 0 24px var(--acc)}
.hz{font-size:44px;font-weight:600;text-align:center;font-variant-numeric:tabular-nums}
.hz small{font-size:18px;color:var(--mute);font-weight:400}
input[type=range]{width:100%;margin:20px 0 12px;accent-color:var(--acc)}
.presets{display:flex;gap:8px;flex-wrap:wrap}
button{flex:1;padding:10px 0;border-radius:8px;border:1px solid var(--line);background:transparent;color:var(--fg);font:inherit;cursor:pointer}
button:hover{border-color:var(--acc)}
.stats{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:24px;font-size:13px;color:var(--mute)}
.stats b{display:block;color:var(--fg);font-size:15px;font-variant-numeric:tabular-nums}
</style></head><body>
<div class="card">
<h1>ESP32 solder test</h1>
<div class="sub">Green LED D1 on GPIO2</div>
<div class="led" id="led"></div>
<div class="hz"><span id="hz">-</span> <small>Hz</small></div>
<input type="range" id="slider" min="0" max="1000" step="1">
<div class="presets">
<button data-hz="0.5">0.5</button><button data-hz="1">1</button>
<button data-hz="2">2</button><button data-hz="5">5</button><button data-hz="10">10</button>
</div>
<div class="stats">
<div>Signal<b id="rssi">-</b></div><div>Uptime<b id="up">-</b></div><div>Heap<b id="heap">-</b></div>
</div>
</div>
<script>
const MIN=0.1,MAX=20,s=document.getElementById('slider');
// Log-scale slider so 0.1-1 Hz gets as much travel as 2-20 Hz.
const toHz=v=>+(MIN*Math.pow(MAX/MIN,v/1000)).toFixed(2);
const toPos=hz=>Math.round(1000*Math.log(hz/MIN)/Math.log(MAX/MIN));
let hz=1,timer,sendT;
function show(h){hz=h;document.getElementById('hz').textContent=h<1?h.toFixed(2):h.toFixed(1);
 clearInterval(timer);const led=document.getElementById('led');
 timer=setInterval(()=>led.classList.toggle('on'),500/h);}
function send(h){clearTimeout(sendT);sendT=setTimeout(()=>fetch('/api?hz='+h).then(r=>r.json()).then(apply),80);}
function apply(d){if(document.activeElement!==s)s.value=toPos(d.hz);if(d.hz!==hz)show(d.hz);
 document.getElementById('rssi').textContent=d.rssi+' dBm';
 const t=d.uptime;document.getElementById('up').textContent=t<3600?Math.floor(t/60)+'m '+t%60+'s':Math.floor(t/3600)+'h '+Math.floor(t%3600/60)+'m';
 document.getElementById('heap').textContent=Math.round(d.heap/1024)+' kB';}
s.oninput=()=>{const h=toHz(s.value);show(h);send(h);};
document.querySelectorAll('button').forEach(b=>b.onclick=()=>{const h=+b.dataset.hz;s.value=toPos(h);show(h);send(h);});
const poll=()=>fetch('/api').then(r=>r.json()).then(apply).catch(()=>{});
poll();setInterval(poll,3000);
</script></body></html>)HTML";

void sendState() {
  char json[96];
  snprintf(json, sizeof(json), "{\"hz\":%.2f,\"rssi\":%d,\"uptime\":%lu,\"heap\":%u}",
           blinkHz, WiFi.RSSI(), millis() / 1000, ESP.getFreeHeap());
  server.send(200, "application/json", json);
}

void handleApi() {
  if (server.hasArg("hz")) {
    float hz = constrain(server.arg("hz").toFloat(), HZ_MIN, HZ_MAX);
    if (hz != blinkHz) {
      blinkHz = hz;
      prefs.putFloat("hz", blinkHz);
      Serial.printf("blink frequency set to %.2f Hz\n", blinkHz);
    }
  }
  sendState();
}

void setup() {
  pinMode(LED_PIN, OUTPUT);
  Serial.begin(115200);
  Serial.println();
  Serial.println("ESP32 solder test: WiFi dashboard");

  prefs.begin("blink", false);
  blinkHz = constrain(prefs.getFloat("hz", 1.0f), HZ_MIN, HZ_MAX);

  WiFi.mode(WIFI_STA);
  WiFi.setTxPower(TX_POWER);
  WiFi.setHostname("esp32solder");
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.printf("connecting to %s", WIFI_SSID);

  // Fast flicker while connecting.
  while (WiFi.status() != WL_CONNECTED) {
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    delay(100);
    if (millis() % 1000 < 100) Serial.print('.');
  }
  Serial.printf("\nconnected, IP %s, RSSI %d dBm\n",
                WiFi.localIP().toString().c_str(), WiFi.RSSI());

  if (MDNS.begin("esp32solder")) {
    MDNS.addService("http", "tcp", 80);
    Serial.println("dashboard: http://esp32solder.local/");
  }
  server.on("/", [] { server.send_P(200, "text/html", PAGE); });
  server.on("/api", handleApi);
  server.begin();
  Serial.printf("dashboard: http://%s/\n", WiFi.localIP().toString().c_str());
}

void loop() {
  server.handleClient();
  unsigned long now = millis();
  if (now - lastToggle >= (unsigned long)(500.0f / blinkHz)) {
    lastToggle = now;
    ledOn = !ledOn;
    digitalWrite(LED_PIN, ledOn);
  }
}
