# Personal DIY Projects

A collection of hardware projects focusing on audio, electronics, and 3D printing. Built and documented using Obsidian.

## 🎯 Active Projects

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

## 📂 Repository Structure

```
Projects/
├── Projects/
│   ├── Illuminate 7Mk2/              # Speaker build project
│   │   ├── Illuminate 7Mk2 - Speaker Build.md
│   │   ├── Parts List - Illuminate 7Mk2.md
│   │   ├── Build Log - Illuminate 7Mk2.md
│   │   └── Amplifier - Fosi Audio V3.md
│   └── Pi Zero PWM Filter/           # PWM audio filter project
│       ├── Pi Zero 2W PWM Audio Filter.md
│       └── Build Guide - 3rd Order PWM Filter.md
├── Resources/
│   ├── Illuminate 7Mk2/              # Speaker resources
│   │   └── *.pdf
│   └── Pi Zero PWM Filter/           # PWM filter resources
├── Notes/                            # Quick reference notes
└── Home.md                           # Vault index
```

---

## 🛠️ Tech Stack

- **Documentation:** Obsidian (markdown-based)
- **3D Modeling/Printing:** PLA filament, support-free design
- **Electronics:** Crossover networks (passive components)
- **Audio:** Dayton Audio drivers, Fosi Audio amplification
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

`audio` `speakers` `diy` `3d-printing` `electroacoustics` `electronics` `amplifiers` `class-d` `power-electronics` `raspberry-pi` `spotify` `obsidian`

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

**Last Updated:** 2026-02-23
