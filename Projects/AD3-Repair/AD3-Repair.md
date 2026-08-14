---
title: AD3 Repair - Digilent Analog Discovery 3 Component-Level Repair
type: project
tags:
  - electronics
  - test-equipment
  - repair
  - active-project
status: In Progress
started: 2026-04-12
updated: 2026-04-12
aliases:
  - AD3 Repair
  - Analog Discovery 3 Repair
links:
  - "[TPS25944A Datasheet (Texas Instruments)](https://www.ti.com/lit/ds/symlink/tps25944a.pdf)"
  - "[Digilent Analog Discovery 3 Reference](https://digilent.com/reference/test-and-measurement/analog-discovery-3/start)"
---

# AD3 Repair - Digilent Analog Discovery 3 Component-Level Repair

> [!summary] **Project Goal**
> Component-level repair of a Digilent Analog Discovery 3 that was damaged by 12V applied to the 5V-rated barrel jack. The analog supply section is drawing massive overcurrent (3A vs 0.6A idle). Goal is to find and replace the dead FET, shorted capacitor, or blown boost controller IC in the analog supply chain.

---

![[ad3-board-overview.png]]

### Board Zone Photos

| | |
|---|---|
| ![[ad3-top-left.png]] | ![[ad3-top-right.png]] |
| **Top Left** — 150µH inductors, boost converter FETs/diodes, IC19 area | **Top Right** — Analog front-end relays (IC3, IC2), shielded modules, IC12 |
| ![[ad3-bottom-left.png]] | ![[ad3-bottom-right.png]] |
| **Bottom Left** — IC22 (FTDI FT232HQ), USB-C (J3), IC34/IC35 eFuse area ⚠️ | **Bottom Right** — Spartan-7 FPGA (IC26), barrel jack (J2), IC12 |

---

## 🔗 Quick Links

- [[#Background - What Happened|Background]]
- [[#Diagnostic Findings|Current Findings]]
- [[#Measurement Plan|Measurement Plan]]
- [[#Repair Log|Repair Log]]

---

## 📋 Background - What Happened

The damaged AD3 had **12V applied to the barrel jack** (AUX input), which is rated for **5V only**. This is a 2.4× overvoltage event. The TPS25944A eFuse (IC35) on the barrel jack path has an absolute maximum rating of 6.5V, so 12V would have blown straight through it and into the downstream boost converter circuitry.

A second, fully working AD3 is available as a **golden reference board** for voltage/resistance comparisons.

---

## ⚡ Diagnostic Findings

### What Works
- Board **enumerates correctly** in Device Manager as "Analog Discovery 3" over USB-C
- **3.3V digital rails** appear alive (FPGA/USB controller functioning)
- **USB current draw** is normal at **0.125A**
- **No hard shorts** found on output rail (~970Ω to GND unpowered)

### What's Broken
- **WaveForms error:** "device stopped working due to low or high supply voltage"
- **AUX rail draws 3.087A** when powered via USB + 5V barrel jack (expected ~0.6A idle)
- **IC35 (TPS25944A)** gets very hot on USB power alone
- **Input rail reads 4V** instead of expected 5V (voltage drop across damaged eFuse)

### IC35 Close-Up (Faulty eFuse)

![[ad3-ic35-closeup.png]]

> [!warning] **IC35 (red box) = TPS25944A** — confirmed damaged. Gets hot on USB power alone. 12V overvoltage likely blew internal MOSFET gate oxide, creating a resistive short. IC34 (above) is the identical USB-path eFuse and appears healthy.

### Components Identified So Far

| Ref Des | Part | Role | Status |
|---------|------|------|--------|
| IC35 | TPS25944A | eFuse / power path controller (barrel jack path) | 🔴 Gets very hot |
| IC34 | TPS25944A | eFuse / power path controller (USB path) | 🟢 Normal temp |
| L? (×2) | 150µH inductors | Boost converter output inductors (±15V rails) | ❓ Untested |
| IC? | Unknown | Boost converter controller(s) | ❓ Not yet identified |
| Q? | Unknown | Boost converter FET(s) | ❓ Not yet identified |

### Suspected Fault Path

```
5V input → IC35 (TPS25944A eFuse) → Boost converter → ±15V analog rails
                  ↑ HOT                    ↑ SUSPECT AREA
```

The 3A overcurrent is on the AUX (barrel jack) rail, strongly suggesting a damaged component in the analog boost converter chain downstream of IC35. The 12V overvoltage likely killed a FET or controller IC in the boost stage, which is now presenting as a near-short to the input rail.

---

## 🔧 Equipment Available

| Equipment | Use |
|-----------|-----|
| DMM | Resistance and DC voltage measurements |
| Bench PSU (current-limited) | Safe power-up of damaged board |
| Working AD3 (golden reference) | Baseline measurements + oscilloscope/voltmeter |
| Soldering iron | Through-hole and fine-pitch work |
| Hot air station | SMD rework / IC removal |

---

## 📐 Measurement Plan

### Phase 1 — Working Board Baseline (Golden Reference)

> [!warning] **Power the working board normally via USB-C.** Do NOT apply bench PSU to the working board — it doesn't need it and you risk damaging your reference.

#### 1.1 DC Rail Mapping

Power the working AD3 via USB-C and measure these DC voltages relative to a solid GND point (USB shield or a GND pad near the barrel jack connector):

| Test Point | Expected | Description |
|------------|----------|-------------|
| Barrel jack input pad (center pin) | 0V (nothing connected) | AUX input, unpowered |
| IC35 input pin (VIN) | ~5V (backfed from USB path via IC34) | eFuse input |
| IC35 output pin (VOUT) | ~5V | eFuse output, feeds boost converters |
| IC34 input pin (VIN) | ~5V | USB eFuse input |
| IC34 output pin (VOUT) | ~5V | USB eFuse output |
| Positive boost output cap (+) | **+15V** (or similar, could be +5V to +16.5V) | Positive analog rail |
| Negative boost output cap (−) | **−15V** (or similar) | Negative analog rail |
| 3.3V rail (any decoupling cap near FPGA) | 3.3V | Digital supply |
| 1.0V or 1.2V rail (if visible near FPGA) | 1.0V–1.2V | FPGA core supply |
| Inductor L1, switch-side pad | DC average ~5V, switching waveform | Boost switch node 1 |
| Inductor L2, switch-side pad | DC average ~5V, switching waveform | Boost switch node 2 |

#### 1.2 Inductor Switch Node Waveforms

Use the second working AD3 (or an oscilloscope channel) to capture the **switching waveform** on each inductor's switch-side pad:

- **Expected:** Square wave, typically 200kHz–2MHz, swinging between ~0V and ~5V (or Vout)
- **Record:** Frequency, amplitude, duty cycle
- These waveforms confirm the boost converter is actively switching

#### 1.3 Resistance Baseline (Power Off)

Unplug the working board and measure resistance to GND from:

| Test Point | Expected | Notes |
|------------|----------|-------|
| IC35 VOUT pad | Record value | Downstream impedance of analog supply |
| Positive boost output cap (+) | Record value | Should be high (kΩ range) |
| Negative boost output cap (−) | Record value | Should be high (kΩ range) |
| Each inductor, switch-side pad | Record value | FET drain impedance to GND |

> [!tip] **Polarity matters for resistance**
> If you get different readings when you swap DMM leads, note both values — this indicates a semiconductor junction in the path.

#### 1.4 Component Marking Photography

While the working board is unpowered, photograph these components on the working board with close-up macro shots:

- [ ] IC35 and IC34 — confirm markings match TPS25944A
- [ ] Both 150µH inductors — note manufacturer part number if visible
- [ ] Boost converter controller IC(s) — small ICs near the inductors
- [ ] Boost converter FET(s) — small SOT-23 or PowerPAK packages near inductors
- [ ] Any Schottky diodes near the boost section
- [ ] All capacitors on the boost output rails — note sizes (0402/0603/0805)

---

### Phase 2 — Damaged Board Measurements (Bench PSU)

> [!warning] **Critical: Current-Limit Your Bench PSU**
> Start at **5.0V / 0.3A limit**. This is below the 0.6A healthy idle draw, so if the PSU goes into current limiting immediately, you know the fault is still present. Increase in 0.1A steps only if needed. **Never exceed 1.0A** until the fault is found.

#### 2.1 Cold Resistance Checks (No Power)

Before applying any power, measure resistance to GND from the same points as Phase 1.3:

| Test Point | Working Board | Damaged Board | Verdict |
|------------|---------------|---------------|---------|
| IC35 VOUT | (from 1.3) | Measure | Match? |
| Positive boost cap (+) | (from 1.3) | Measure | Match? |
| Negative boost cap (−) | (from 1.3) | Measure | Match? |
| Inductor L1 switch node | (from 1.3) | Measure | Match? |
| Inductor L2 switch node | (from 1.3) | Measure | Match? |

> [!important] **Key Diagnostic**
> If any resistance reading on the damaged board is **significantly lower** than the working board (e.g., <10Ω vs kΩ), you've found the shorted rail. Trace it back to the component.

#### 2.2 Powered Voltage Checks (5V / 0.3A Limit via Barrel Jack)

Connect bench PSU to the barrel jack (center positive, 5.0V, 0.3A limit):

1. **Does the PSU current-limit immediately?**
   - YES → Fault is downstream of barrel jack. PSU voltage will sag below 5V. Note the voltage and current. Proceed to thermal inspection.
   - NO → Board draws less than 0.3A. Increase limit to 0.5A and check again.

2. Measure the same DC test points as Phase 1.1:

| Test Point | Working Value | Damaged Value | Delta |
|------------|---------------|---------------|-------|
| IC35 VIN | 5V | ? | |
| IC35 VOUT | 5V | ? | |
| Positive boost cap | +15V | ? | |
| Negative boost cap | −15V | ? | |
| 3.3V rail | 3.3V | ? | |

#### 2.3 Thermal Inspection

With power applied (at current limit), use your finger or thermal camera to feel for hot components:

- [ ] IC35 (TPS25944A) — already known hot
- [ ] IC34 (TPS25944A) — should stay cool
- [ ] Boost controller IC(s) near inductors
- [ ] FETs near inductors (small SOT-23 / PowerPAK)
- [ ] Any capacitors that feel warm (shorted cap)
- [ ] Inductors themselves (saturated inductor won't get hot from a short)

> [!tip] **The hottest component is the one closest to the fault.** If IC35 is hot but nothing downstream is, the short is very close to IC35's output. If a FET is hotter than IC35, the FET itself is shorted.

#### 2.4 Switch Node Probing (If Board Draws <1A)

If the board is not in hard current-limiting, probe the inductor switch nodes with the working AD3 as an oscilloscope:

- **Switching waveform present?** → Boost converter is trying to work
- **Flat DC (0V or Vin)?** → Boost controller not switching — dead controller or shorted FET holding the node low/high
- **Compare frequency and duty cycle** to working board

---

### Phase 3 — Fault Isolation Decision Tree

```
START: Cold resistance check on IC35 VOUT
  │
  ├─ LOW (<50Ω) ──→ Short is between IC35 output and boost input
  │                   ├─ Lift IC35 output (or desolder) and re-check
  │                   │   ├─ Still low → Shorted cap on the rail
  │                   │   └─ Now high → IC35 itself is shorted internally
  │                   └─ Check each boost converter input individually
  │
  └─ NORMAL (matches working board)
      │
      ├─ Power up at 5V/0.3A
      │   ├─ Hits current limit immediately
      │   │   ├─ Check positive boost output cap → LOW = positive rail shorted
      │   │   ├─ Check negative boost output cap → LOW = negative rail shorted  
      │   │   ├─ Check inductor switch nodes
      │   │   │   ├─ One node is 0Ω to GND → FET drain-source shorted
      │   │   │   └─ Both normal → Boost controller is commanding full duty cycle
      │   │   │       (controller may be damaged, locking FET ON)
      │   │   └─ Feel for heat → Hottest component = closest to fault
      │   │
      │   └─ Does NOT hit current limit
      │       ├─ Check boost output voltages
      │       │   ├─ Both ±15V present → Board may be OK, re-test in WaveForms
      │       │   ├─ One rail missing → That converter stage is dead
      │       │   └─ Both missing → Shared enable/control signal is broken
      │       └─ Check WaveForms again with USB connected
      │
      └─ Power up via USB only
          ├─ IC35 still gets hot → IC35 itself is damaged
          │   (even with no barrel jack power, USB backfeeds through IC34
          │    and IC35's body diode or internal FET may be conducting)
          └─ IC35 stays cool → Problem is only in the barrel jack power path
```

---

### Phase 4 — Component Identification

#### Reading IC Markings

| What to Look For | Where | How to Read |
|------------------|-------|-------------|
| Boost controller IC | Small IC (SOT-23-5, MSOP-8, or QFN) near each inductor | Note the full marking. Search "[marking] site:ti.com" or use TI's marking search tool |
| FETs | SOT-23 or PowerPAK near inductor switch nodes | Marking is usually 1-3 characters. Cross-reference with board position and known boost controller datasheets (the datasheet usually recommends specific FETs) |
| Schottky diodes | Small packages near boost output caps | Often marked with a band or single character |

> [!tip] **Use the working board for identification**
> The markings on the working board will be legible. The damaged board's ICs may be charred or discolored, making markings unreadable.

#### Common Boost Converter ICs in Digilent Products

Digilent frequently uses **Texas Instruments** boost converters. Common candidates for generating ±15V from 5V:

- **TPS55340** — 5A, 40V boost converter (single inductor)
- **TPS61170** — LED driver / boost converter
- **LM3488** — high-efficiency boost controller
- **TPS61040/41** — 28V boost converter
- Look for **TI markings** and cross-reference on [TI's IC Marking Search](https://www.ti.com/packaging/docs/partlookup.tsp)

#### FET Identification

If the boost controller is an external-FET topology:
- Measure the FET gate-source and drain-source with a diode-mode DMM
- **Healthy N-channel MOSFET:** Gate-Source = open, Drain-Source = ~0.4-0.7V one direction (body diode)
- **Shorted FET:** <1Ω in any direction = dead

---

### Phase 5 — Repair Procedure

#### 5.1 Removing the Faulty Component

> [!warning] **Protect nearby components with Kapton tape or aluminum foil**

1. **Add flux** generously to all pins/pads of the faulty component
2. **Hot air settings:** 350-380°C, medium airflow, 5-8mm nozzle
3. **Heat evenly** — move the nozzle in small circles over the component
4. **Wait for solder to reflow** on all pins simultaneously (15-30 seconds)
5. **Lift the component** with fine tweezers once all solder is molten
6. **Clean the pads** with solder wick and flux, then IPA

#### 5.2 Installing the Replacement

1. **Inspect pads** under magnification — ensure no lifted traces or bridged pads
2. **Apply flux** to cleaned pads
3. **Tin one corner pad** with a small amount of solder
4. **Place the new component** with tweezers, aligning pin 1
5. **Tack the corner** with soldering iron to hold the part in place
6. **Reflow all pins** with hot air (340-360°C, slightly lower than removal)
7. **Inspect under magnification** for bridges or cold joints
8. **Clean flux residue** with IPA

#### 5.3 Post-Repair Verification

1. **Cold resistance check** — compare to working board values (Phase 2.1)
2. **Power up at 5V / 0.3A limit** — should NOT current-limit
3. **Increase to 0.5A, then 1.0A** — check all rail voltages
4. **Connect USB and test in WaveForms** — verify analog channels work
5. **Run WaveForms self-test** (if available) to confirm full functionality

---

## 📝 Repair Log

### 2026-04-12 — Initial Diagnostics

- Identified IC35 (TPS25944A) as the barrel jack eFuse — gets very hot
- AUX rail draws 3.087A at 5V (massively overcurrent)
- USB draws 0.125A (normal)
- WaveForms reports supply voltage error
- Board enumerates correctly over USB-C
- 3.3V digital rails alive
- No hard shorts on output rail (~970Ω unpowered)
- IC35 input reads 4V instead of 5V (excessive voltage drop)
- Suspect: dead FET or blown boost controller downstream of IC35
- **Next step:** Phase 1 baseline measurements on working board

---

## 🔗 References

- [TPS25944A Datasheet (Texas Instruments)](https://www.ti.com/lit/ds/symlink/tps25944a.pdf)
- [Digilent Analog Discovery 3 Reference](https://digilent.com/reference/test-and-measurement/analog-discovery-3/start)
- [TI IC Marking Search Tool](https://www.ti.com/packaging/docs/partlookup.tsp)
