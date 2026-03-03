# Personal DIY Projects

A collection of hardware projects focusing on audio, electronics, and 3D printing. Built and documented using Obsidian.

## 🎯 Active Projects

### 🧰 [Component Inventory Pro](components-inventory/)

Desktop app for cataloging THT electronic components with a built-in DTU shop browser. Track your parts, visualize resistor color bands, browse 1,400+ shop items, and see what you already own.

**Status:** 🟢 Working

**Key Features:**
- **Dashboard** with donut chart and stats
- **Inventory** with search, category filter, and visual resistor color bands
- **DTU Shop Browser** — browse/search/filter shop components, ownership cross-referencing
- **AI Export** — markdown summary for LLM-assisted project planning
- **Windows exe** — standalone build via PyInstaller

**Tech:** Python 3, customtkinter, SQLite, Pillow

---

### 🔊 [Illuminate 7Mk2 - 3D-Printed Speaker Build](Projects/Illuminate%207Mk2/Illuminate%207Mk2%20-%20Speaker%20Build.md)

Building a pair of audiophile-grade 3D-printed bookshelf speakers from scratch.

**Status:** 🟡 Planning

**Key Specs:**
- **Drivers:** Dayton Audio RS180P-8 (7" woofer) + RST28F-4 (28mm tweeter)
- **Enclosure:** 3D-printed PLA (~4750g required)
- **Frequency Response:** 50Hz - 20kHz (-3dB)
- **Impedance:** 8Ω nominal
- **Amplifier:** Fosi Audio V3 (TPA3255-based Class D, 300W x 2 @ 4Ω)

**Budget:** ~1750-2730 DKK (~$250-390 USD)

**Documentation:**
- [📋 Parts List](Projects/Illuminate%207Mk2/Parts%20List%20-%20Illuminate%207Mk2.md) - Complete BOM with suppliers and prices
- [📖 Build Log](Projects/Illuminate%207Mk2/Build%20Log%20-%20Illuminate%207Mk2.md) - Detailed build progress tracker
- [⚡ Amplifier Details](Projects/Illuminate%207Mk2/Amplifier%20-%20Fosi%20Audio%20V3.md) - Fosi Audio V3 specifications and setup

**Resources:**
- [Parts & Purchase Guide PDF](Resources/Illuminate%207Mk2/Illuminate_7_Mk2_Parts_and_Purchase_Guide.pdf)
- [Spec Sheet PDF](Resources/Illuminate%207Mk2/Illuminate_7Mk2_Spec_Sheet.pdf)

---

### ⚡ [Pi Zero 2W PWM Audio Filter](Projects/Pi%20Zero%20PWM%20Filter/Pi%20Zero%202W%20PWM%20Audio%20Filter.md)

Filtered PWM audio output for Raspberry Pi Zero 2W running Raspotify (Spotify Connect).

![Proto board build](Resources/Pi%20Zero%20PWM%20Filter/images/proto-board-build.jpg)

**Status:** 🟢 Working Prototype

**Key Specs:**
- **Platform:** Raspberry Pi Zero 2W
- **Software:** Raspotify (Spotify Connect)
- **Filter:** 3rd order Sallen-Key (RC + active, TL072)
- **Output:** Stereo line-level via screw terminals
- **PWM Attenuation:** -40.6dB @ 31.25kHz
- **Optimal Volume:** ALSA PCM at 75% (-22.6 dB)

**Tested With:**
- Active speakers (direct connection) — clean audio
- Schiit Saga preamp — working, noise floor at high gain

**Documentation:**
- [📋 Main Project](Projects/Pi%20Zero%20PWM%20Filter/Pi%20Zero%202W%20PWM%20Audio%20Filter.md) - Filter designs, BOM, Pi configuration
- [🔧 Build Guide](Projects/Pi%20Zero%20PWM%20Filter/Build%20Guide%20-%203rd%20Order%20PWM%20Filter.md) - Step-by-step build with AD3 testing

---

### 📡 [ESP32 IR Blaster - Smart Home IR Controller](Projects/ESP32%20IR%20Blaster/ESP32%20IR%20Blaster%20-%20Smart%20Home.md)

WiFi-connected IR blaster/receiver using ESP32 and ESPHome, integrating with Home Assistant to control any IR device.

**Status:** 🟢 Proof of Concept Complete

**Key Specs:**
- **Platform:** ESP32 with ESPHome firmware
- **Integration:** Home Assistant (native API)
- **IR Transmitter:** SFH4546 LED via 2N2222 driver
- **IR Receiver:** VS1838 (38 kHz demodulator)
- **Protocols:** NEC (including repeat codes for hold buttons)

**HAOS Add-on:** [IR Remote Wizard](https://github.com/MadsRudolph/ir-remote-wizard) — Auto-discovery add-on using the Flipper-IRDB database to find IR codes for your devices without manual learning.

**Documentation:**
- [📋 Main Project](Projects/ESP32%20IR%20Blaster/ESP32%20IR%20Blaster%20-%20Smart%20Home.md) - Circuit design, BOM, ESPHome config
- [🔧 Learning Remote Codes](Projects/ESP32%20IR%20Blaster/Learning%20Remote%20Codes%20-%20ESP32%20IR%20Blaster.md) - How to capture and add IR codes

---

### 💳 [RFID Card Reader - Bare Metal AVR](Projects/RFID%20Card%20Reader/RFID%20Card%20Reader.md)

Bare-metal RFID card reader using MFRC522 and Arduino Uno. Reads 13.56 MHz MIFARE card UIDs over serial. Pure embedded C with direct ATmega328P register access — no Arduino framework.

**Status:** 🟡 Proof of Concept

**Key Specs:**
- **MCU:** ATmega328P (Arduino Uno), bare-metal C
- **RFID Module:** MFRC522 RC522 (13.56 MHz, ISO 14443A)
- **Interface:** Hardware SPI (~1 MHz)
- **Output:** UART serial at 9600 baud
- **Build System:** PlatformIO (atmelavr, no framework)

**Documentation:**
- [📋 Main Project](Projects/RFID%20Card%20Reader/RFID%20Card%20Reader.md) - Wiring, software architecture, technical notes

---

### 🔬 [DTU Digital Multimeter](Projects/DTU%20Multimeter/DTU%20Multimeter%20-%20Digital%20Multimeter.md)

Fluke 289-class auto-ranging digital multimeter — bare-metal AVR C firmware on ATmega2560.

**Status:** 🟡 In Development

**Key Specs:**
- **MCU:** ATmega2560 @ 16 MHz (Arduino Mega 2560)
- **ADC:** MCP3208 12-bit SPI (100 ksps) + 64x oversampling
- **Display:** SSD1306 128x64 OLED (I2C)
- **Modes:** 22 measurement modes (DC/AC V, R, I, C, L, freq, temp, scope...)
- **Build System:** PlatformIO, pure avr-gcc (no Arduino framework)

**Documentation:**
- [📋 Main Project](Projects/DTU%20Multimeter/DTU%20Multimeter%20-%20Digital%20Multimeter.md) - Full specs, circuit design, component list
- [🔧 Build Guide](Projects/DTU%20Multimeter/Build%20Guide%20-%20DTU%20Multimeter.md) - Assembly, flashing, calibration

---

## 📂 Repository Structure

```
├── components-inventory/              # Component Inventory Pro app
│   ├── inventory_gui.py              # GUI (customtkinter)
│   ├── inventory.py                  # Data layer & CLI
│   ├── dist/InventoryPro.exe         # Windows executable
│   └── test_browser_data.py          # Tests
├── Projects/
│   ├── Illuminate 7Mk2/              # Speaker build project
│   ├── Pi Zero PWM Filter/           # PWM audio filter project
│   ├── ESP32 IR Blaster/             # Smart home IR controller
│   ├── RFID Card Reader/            # Bare-metal RFID reader
│   └── DTU Multimeter/              # Digital multimeter project
├── Resources/
│   ├── Illuminate 7Mk2/              # Speaker resources
│   └── Pi Zero PWM Filter/           # PWM filter resources
├── ir-remote-wizard/                  # HAOS add-on (git submodule)
├── Notes/                            # Quick reference notes
└── Home.md                           # Vault index
```

---

## 🛠️ Tech Stack

- **Documentation:** Obsidian (markdown-based)
- **Desktop Apps:** Python 3, customtkinter, SQLite, Pillow, PyInstaller
- **3D Modeling/Printing:** PLA filament, support-free design
- **Electronics:** Analog filters, crossover networks, IR circuits, bare-metal AVR firmware
- **Audio:** Dayton Audio drivers, Fosi Audio amplification, PWM filtering
- **Smart Home:** Home Assistant, ESPHome, ESP32
- **Embedded:** Raspberry Pi Zero 2W, ESP32, ATmega328P, ATmega2560, avr-gcc, PlatformIO
- **Version Control:** Git + GitHub

---

## 🎓 Background

I'm a Diplomingeniør (B.Eng.) student at DTU studying Electrical Engineering with focus on:
- Analog & mixed-signal electronics
- Electroacoustics & transducers
- Power electronics (Class D amplifiers, SMPS)
- Digital signal processing

These projects combine my academic knowledge with hands-on building experience.

---

## 🏷️ Topics

`audio` `speakers` `diy` `3d-printing` `electroacoustics` `electronics` `amplifiers` `class-d` `power-electronics` `raspberry-pi` `spotify` `esp32` `esphome` `home-assistant` `smart-home` `ir-remote` `rfid` `avr` `bare-metal` `embedded` `atmega2560` `multimeter` `obsidian` `python` `customtkinter` `sqlite` `inventory`

---

## 📊 Project Backlog

Future projects I'm considering:

### Audio
- [ ] Headphone amplifier build
- [ ] DAC project with AK4493 or ES9038Q2M
- [ ] Subwoofer design
- [ ] Room acoustic treatment

### Electronics
- [ ] ESP32-based audio streamer
- [ ] PCB design practice (audio circuits)
- [ ] Custom power supply builds

### 3D Printing
- [ ] 3D printer upgrades
- [ ] Custom equipment enclosures
- [ ] Functional prints for workshop organization

---

## 🔗 Links

- **GitHub:** [@MadsRudolph](https://github.com/MadsRudolph)
- **PrintYourSpeakers:** [printyourspeakers.com](https://www.printyourspeakers.com)
- **Dayton Audio:** [parts-express.com](https://www.parts-express.com)
- **Fosi Audio:** [fosiaudio.com](https://fosiaudio.com)

---

## 📝 Notes

This repository uses Obsidian for project documentation. To view with full functionality:
1. Install [Obsidian](https://obsidian.md)
2. Clone this repository
3. Open the folder as an Obsidian vault

Alternatively, all files are standard markdown and can be viewed directly on GitHub.

---

**Last Updated:** 2026-03-03
