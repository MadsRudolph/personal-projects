# Schematic Completion Design — DTU Multimeter

**Date:** 2026-03-12
**Goal:** Fix all 7 ERC errors, reduce 85 warnings to near-zero, and complete the remaining unwired connections in the KiCad schematic.

---

## Current State

All 8 wiring scripts have been applied. The schematic has:
- **7 ERC errors** (dangling labels, unconnected pins, undriven inputs)
- **85 ERC warnings** (~75 off-grid endpoints, ~7 PWR_FLAG mismatches, ~3 other)

## Approach: Hybrid (Script + Manual)

Scripts handle bulk/mechanical fixes. Manual wiring in KiCad for circuit-level changes.

---

## Script Fixes

### Fix 1: TERM_10A / TERM_mA dangling labels
- **Problem:** Labels at (29.21, 44.45) and (29.21, 64.77) sit on wire stubs that don't reach F1/F2 pin 1 endpoints.
- **Fix:** Read exact F1/F2 pin 1 coordinates from schematic, move labels and stubs to align, or remove stubs and place labels directly on pins.

### Fix 2: CAP_DIS dangling label
- **Problem:** `CAP_DIS` label exists on A1 pin 32 but has no matching destination.
- **Fix:** Place a matching `CAP_DIS` label on the discharge node in the NE555/timing area.

### Fix 3: U3 Pin 4 (SHUNT_NODE) input not driven
- **Problem:** CD4053 pin 4 (C-common) has input-type pin, KiCad says not driven.
- **Fix:** Place `SHUNT_NODE` label on pin 4 (322.58, 92.71). If still flagged, add PWR_FLAG on SHUNT_NODE net.

### Fix 4: Off-grid endpoint snapping
- **Problem:** ~75 wire endpoints at fractional mm coordinates (not on 1.27mm grid).
- **Fix:** Script snaps all wire endpoints and power symbol positions to nearest 1.27mm grid point.

### Fix 5: PWR_FLAG library mismatch
- **Problem:** 3 PWR_FLAG symbols don't match current library version.
- **Fix:** Re-place or update PWR_FLAG symbols to match library.

---

## Manual Fixes (in KiCad GUI)

### Fix 6: U4 Unit B — AC Rectifier (pins 5, 6, 7)
- **Problem:** LM358 Unit B completely unwired. Pin 5 (IN+_B) not connected, pin 6 (IN-_B) not connected.
- **Design decision:** Direct feedback (unity-gain buffer). Firmware handles RMS in software.
- **Wiring:**
  - Pin 5 (IN+_B at 454.66, 109.22) → connect to probe input net (label `ADC_CH2` or wire to V/Ohm input)
  - Pin 6 (IN-_B) → wire directly to pin 7 (OUT_B) for unity-gain feedback
  - Pin 7 already has `ADC_CH4` label → connects to U1 CH4

### Fix 7: C7 Pin 2 — Signal source connection
- **Problem:** AC coupling cap C7 has pin 1 wired to U5 (comparator), but pin 2 (65.00, 233.81) is floating.
- **Fix:** Connect C7 pin 2 to probe input net (label `ADC_CH2` or wire to V/Ohm input).

---

## Expected Result

- **0 ERC errors**
- **<10 ERC warnings** (down from 85)

## Build Order

1. Close KiCad
2. Run script fixes (Fix 1-5)
3. Open KiCad, verify script changes visually
4. Manual wiring (Fix 6-7) with exact coordinates provided
5. Run ERC to verify
6. Iterate if any issues remain

---

## Components Not Wired (by design — future expansion)

These are intentionally left for later phases:
- NE555 output routing to probe circuit (capacitance measurement details)
- Full AC rectifier with diode (currently unity-gain buffer)
- Scope input (U1 CH6 — currently no-connect)
- Auxiliary (U1 CH7 — currently no-connect)
