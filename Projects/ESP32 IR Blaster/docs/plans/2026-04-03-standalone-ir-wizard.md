# Standalone IR Wizard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a self-contained IR learning wizard that runs entirely on the ESP32 D1 Mini — no Home Assistant, no PC needed. Users connect to the ESP's web UI, learn IR codes from physical remotes, save them to flash, and replay them.

**Architecture:** ESPHome external component (`ir_wizard`) adds a web server with REST API on top of existing ESPHome IR TX/RX. A single HTML file served from PROGMEM provides the UI. Learned codes stored as JSON on LittleFS.

**Tech Stack:** ESPHome external component (C++/Python), ArduinoJson, LittleFS, AsyncWebServer (via ESPHome web_server_base), vanilla HTML/CSS/JS.

---

### Task 1: Create external component skeleton

**Files:**
- Create: `components/ir_wizard/__init__.py`
- Create: `components/ir_wizard/ir_wizard.h`
- Create: `components/ir_wizard/ir_wizard.cpp`

**Step 1: Create `__init__.py` — ESPHome component registration**

```python
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID
from esphome.components import web_server_base

DEPENDENCIES = ["web_server_base"]
AUTO_LOAD = ["web_server_base"]

CODEOWNERS = ["@custom"]

ns = cg.esphome_ns.namespace("ir_wizard")
IRWizard = ns.class_("IRWizard", cg.Component)

CONFIG_SCHEMA = cv.Schema({
    cv.GenerateID(): cv.declare_id(IRWizard),
}).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    # Get web_server_base instance
    srv = await cg.get_variable(web_server_base.CONF_WEB_SERVER_BASE_ID)
    cg.add(var.set_web_server(srv))
```

**Step 2: Create minimal `ir_wizard.h`**

```cpp
#pragma once
#include "esphome/core/component.h"
#include "esphome/components/web_server_base/web_server_base.h"

namespace esphome {
namespace ir_wizard {

class IRWizard : public Component {
 public:
  void set_web_server(web_server_base::WebServerBase *base) { this->base_ = base; }
  void setup() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::AFTER_WIFI; }

 protected:
  web_server_base::WebServerBase *base_{nullptr};
};

}  // namespace ir_wizard
}  // namespace esphome
```

**Step 3: Create minimal `ir_wizard.cpp`**

```cpp
#include "ir_wizard.h"
#include "esphome/core/log.h"

namespace esphome {
namespace ir_wizard {

static const char *TAG = "ir_wizard";

void IRWizard::setup() {
  ESP_LOGI(TAG, "IR Wizard component initialized");
}

void IRWizard::dump_config() {
  ESP_LOGCONFIG(TAG, "IR Wizard:");
}

}  // namespace ir_wizard
}  // namespace esphome
```

**Step 4: Verify it compiles**

Update `ir-blaster-d1mini.yaml` to load the external component:

```yaml
external_components:
  - source:
      type: local
      path: components

ir_wizard:
```

Run: `python -m esphome compile ir-blaster-d1mini.yaml`
Expected: SUCCESS

**Step 5: Commit**

```
feat: add ir_wizard external component skeleton
```

---

### Task 2: Add LittleFS storage for device profiles

**Files:**
- Modify: `components/ir_wizard/ir_wizard.h`
- Modify: `components/ir_wizard/ir_wizard.cpp`

**Step 1: Add LittleFS mount and JSON read/write to ir_wizard.cpp**

Add to `ir_wizard.h`:
```cpp
#include <ArduinoJson.h>
#include <LittleFS.h>

// In class:
  void load_devices_();
  void save_devices_();
  std::string devices_json_;  // cached JSON string
```

Add to `ir_wizard.cpp`:
```cpp
void IRWizard::setup() {
  if (!LittleFS.begin(true)) {
    ESP_LOGE(TAG, "LittleFS mount failed");
    return;
  }
  load_devices_();
  ESP_LOGI(TAG, "IR Wizard initialized, devices loaded");
}

void IRWizard::load_devices_() {
  File f = LittleFS.open("/ir_devices.json", "r");
  if (!f) {
    devices_json_ = "[]";
    return;
  }
  devices_json_ = f.readString().c_str();
  f.close();
}

void IRWizard::save_devices_() {
  File f = LittleFS.open("/ir_devices.json", "w");
  if (!f) {
    ESP_LOGE(TAG, "Failed to open file for writing");
    return;
  }
  f.print(devices_json_.c_str());
  f.close();
}
```

**Step 2: Verify it compiles**

Run: `python -m esphome compile ir-blaster-d1mini.yaml`
Expected: SUCCESS

**Step 3: Commit**

```
feat: add LittleFS storage for IR device profiles
```

---

### Task 3: Add REST API endpoints

**Files:**
- Modify: `components/ir_wizard/ir_wizard.h`
- Modify: `components/ir_wizard/ir_wizard.cpp`

**Step 1: Register HTTP handlers in setup()**

Endpoints:
- `GET /api/devices` — return devices JSON
- `POST /api/devices` — create device `{"name":"Samsung TV"}`
- `DELETE /api/devices?id=samsung-tv` — delete device
- `POST /api/devices/buttons` — add button `{"device_id":"...","name":"Power","protocol":"NEC","address":"0x1234","command":"0x5678"}`
- `DELETE /api/devices/buttons?device_id=...&index=0` — delete button
- `POST /api/send` — send IR code `{"protocol":"NEC","address":"0x1234","command":"0x5678"}`

```cpp
void IRWizard::setup() {
  if (!LittleFS.begin(true)) {
    ESP_LOGE(TAG, "LittleFS mount failed");
    return;
  }
  load_devices_();

  auto *server = this->base_->get_server();

  server->on("/api/devices", HTTP_GET, [this](AsyncWebServerRequest *request) {
    request->send(200, "application/json", this->devices_json_.c_str());
  });

  // POST /api/devices — create device
  server->on("/api/devices", HTTP_POST,
    [](AsyncWebServerRequest *request) {},
    nullptr,
    [this](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total) {
      this->handle_create_device_(request, data, len);
    });

  // DELETE /api/devices?id=xxx
  server->on("/api/devices", HTTP_DELETE, [this](AsyncWebServerRequest *request) {
    this->handle_delete_device_(request);
  });

  // POST /api/devices/buttons — add button
  server->on("/api/devices/buttons", HTTP_POST,
    [](AsyncWebServerRequest *request) {},
    nullptr,
    [this](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total) {
      this->handle_add_button_(request, data, len);
    });

  // DELETE /api/devices/buttons?device_id=xxx&index=0
  server->on("/api/devices/buttons", HTTP_DELETE, [this](AsyncWebServerRequest *request) {
    this->handle_delete_button_(request);
  });

  // POST /api/send — transmit IR code
  server->on("/api/send", HTTP_POST,
    [](AsyncWebServerRequest *request) {},
    nullptr,
    [this](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total) {
      this->handle_send_(request, data, len);
    });

  ESP_LOGI(TAG, "IR Wizard API registered");
}
```

**Step 2: Implement handler methods**

Each handler parses JSON with ArduinoJson, modifies `devices_json_`, calls `save_devices_()`, returns response.

**Step 3: Verify it compiles**

Run: `python -m esphome compile ir-blaster-d1mini.yaml`

**Step 4: Commit**

```
feat: add REST API endpoints for device/button CRUD and IR send
```

---

### Task 4: Add IR learn mode via remote_receiver

**Files:**
- Modify: `components/ir_wizard/__init__.py` (add remote_receiver dependency)
- Modify: `components/ir_wizard/ir_wizard.h`
- Modify: `components/ir_wizard/ir_wizard.cpp`

**Step 1: Register as RemoteReceiverListener**

```cpp
#include "esphome/components/remote_base/remote_base.h"
#include "esphome/components/remote_receiver/remote_receiver.h"

class IRWizard : public Component, public remote_base::RemoteReceiverListener {
  // ...
  void set_receiver(remote_receiver::RemoteReceiverComponent *receiver) { this->receiver_ = receiver; }
  bool on_receive(remote_base::RemoteReceiveData data) override;

  // Learn mode state
  bool learn_active_{false};
  std::string learned_code_json_;  // last captured code as JSON

  remote_receiver::RemoteReceiverComponent *receiver_{nullptr};
};
```

**Step 2: Implement on_receive() — try all protocols**

```cpp
bool IRWizard::on_receive(remote_base::RemoteReceiveData data) {
  if (!this->learn_active_) return false;

  // Try NEC
  auto nec = remote_base::NECProtocol().decode(data);
  if (nec.has_value()) {
    char buf[128];
    snprintf(buf, sizeof(buf),
      "{\"protocol\":\"NEC\",\"address\":\"0x%04X\",\"command\":\"0x%04X\"}",
      nec->address, nec->command);
    this->learned_code_json_ = buf;
    this->learn_active_ = false;
    return true;
  }

  // Try Samsung, Sony, RC5, RC6, LG, Panasonic... (similar pattern)
  // ...

  return false;
}
```

**Step 3: Add learn API endpoints**

- `POST /api/learn/start` — sets `learn_active_ = true`, clears `learned_code_json_`
- `GET /api/learn/result` — returns `learned_code_json_` or `{"status":"waiting"}`
- `POST /api/learn/stop` — sets `learn_active_ = false`

**Step 4: Update `__init__.py` to pass receiver reference**

```python
DEPENDENCIES = ["web_server_base", "remote_receiver"]

async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    srv = await cg.get_variable(web_server_base.CONF_WEB_SERVER_BASE_ID)
    cg.add(var.set_web_server(srv))
    # Pass remote_receiver reference
    recv = await cg.get_variable(cv.use_id(remote_receiver.RemoteReceiverComponent)(config))
    cg.add(var.set_receiver(recv))
```

**Step 5: Verify it compiles**

**Step 6: Commit**

```
feat: add IR learn mode via remote_receiver listener
```

---

### Task 5: Add IR transmit functionality

**Files:**
- Modify: `components/ir_wizard/__init__.py` (add remote_transmitter dependency)
- Modify: `components/ir_wizard/ir_wizard.h`
- Modify: `components/ir_wizard/ir_wizard.cpp`

**Step 1: Add transmitter reference and send methods**

```cpp
#include "esphome/components/remote_transmitter/remote_transmitter.h"

// In class:
  void set_transmitter(remote_transmitter::RemoteTransmitterComponent *tx) { this->transmitter_ = tx; }
  void send_ir_code_(const std::string &protocol, const std::string &address,
                     const std::string &command, const std::string &raw_data);

  remote_transmitter::RemoteTransmitterComponent *transmitter_{nullptr};
```

**Step 2: Implement send for each protocol**

Uses ESPHome's protocol encode methods directly:
```cpp
void IRWizard::send_ir_code_(const std::string &protocol, ...) {
  auto call = this->transmitter_->transmit();
  if (protocol == "NEC") {
    auto nec = remote_base::NECData{(uint16_t)addr_int, (uint16_t)cmd_int};
    remote_base::NECProtocol().encode(call.get_data(), nec);
  }
  // ... other protocols
  call.perform();
}
```

**Step 3: Wire up in `__init__.py`**

**Step 4: Verify it compiles and test send via API**

**Step 5: Commit**

```
feat: add IR transmit via remote_transmitter
```

---

### Task 6: Build the web UI

**Files:**
- Create: `components/ir_wizard/index_html.h` (HTML as PROGMEM string)

**Step 1: Build single HTML file with embedded CSS/JS**

Two views:
1. **Home** — device cards with button grids. Tap button → `POST /api/send`. "Add Device" button.
2. **Learn Mode** — name device, then loop: tap "Listen" → `POST /api/learn/start` → poll `GET /api/learn/result` → name button → test → save.

Dark theme, mobile-friendly, minimal.

**Step 2: Embed as PROGMEM in header file**

```cpp
// index_html.h
#pragma once
const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
...
</html>
)rawliteral";
```

**Step 3: Serve from root endpoint**

```cpp
#include "index_html.h"

// In setup():
server->on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
  request->send_P(200, "text/html", INDEX_HTML);
});
```

**Step 4: Flash and test in browser at http://192.168.50.148/**

**Step 5: Commit**

```
feat: add standalone web UI for IR wizard
```

---

### Task 7: Update ESPHome YAML config

**Files:**
- Modify: `ir-blaster-d1mini.yaml`

**Step 1: Strip HA-only config, add external component**

Remove: `api:` section (no HA), all service definitions
Keep: `wifi`, `ota`, `logger`, `captive_portal`, `remote_transmitter`, `remote_receiver`, `status_led`
Add: `external_components` pointing to `components/`, `ir_wizard:` config

**Step 2: Compile and flash**

Run: `python -m esphome run ir-blaster-d1mini.yaml --device COM7`

**Step 3: Test full flow in browser**

1. Browse to http://192.168.50.148/
2. Create a device
3. Learn a button from physical remote
4. Test the button
5. Save and verify persistence after reboot

**Step 4: Commit**

```
feat: standalone IR blaster — no Home Assistant required
```

---

### Task Order & Dependencies

```
Task 1 (skeleton) → Task 2 (storage) → Task 3 (REST API) → Task 4 (learn) → Task 5 (transmit) → Task 6 (web UI) → Task 7 (YAML + integration test)
```

All tasks are sequential — each builds on the previous.
