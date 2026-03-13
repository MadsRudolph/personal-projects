# KiCad Schematic Completion — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all 8 ERC errors, reduce 42 warnings, and complete the DTU Multimeter KiCad schematic.

**Architecture:** Python scripts (raw S-expression injection, same pattern as existing wire_*.py scripts) for bulk wiring fixes. Manual KiCad GUI work for the U4 Unit B rectifier circuit and C7 signal connection.

**Tech Stack:** Python 3.11, raw string manipulation on `.kicad_sch` file, KiCad 9

---

## Current ERC State (2026-03-12)

8 errors, 42 warnings. Errors:
1. `TERM_10A` dangling at (29.21, 36.83)
2. `TERM_mA` dangling at (29.21, 59.69)
3. C7 Pin 2 not connected at (65.00, 231.27)
4. U3 Pin 4 input not driven at (322.58, 90.17)
5. R18 Pin 1 not connected at (292.10, 203.20)
6. U4 Pin 5 not connected at (454.66, 106.68)
7. U4 Pin 5 input not driven at (454.66, 106.68)
8. `CAP_DIS` dangling at (487.68, 252.73)

---

### Task 1: Fix NE555 Timing Resistor Wiring (R17, R18, R19)

**Context:** The timing resistors were moved in KiCad GUI after wire_u6.py ran. The old wires at x=285/290/295 no longer reach the resistor pins. R18 pin 1 is flagged; R17/R19 may also be disconnected.

**Current resistor positions (from schematic):**
- R17 at (293.37, 195.58) → pin1=(293.37, 191.77), pin2=(293.37, 199.39)
- R18 at (292.10, 207.01) → pin1=(292.10, 203.20), pin2=(292.10, 210.82)
- R19 at (292.10, 219.71) → pin1=(292.10, 215.90), pin2=(292.10, 223.52)

**Old wire positions (from wire_u6.py, now stale):**
- DIS bus: vertical at x=285 from y=194.19 to y=218.19
- Branches to R pin1 at: (285→290, y=194.19), (285→290, y=206.19), (285→290, y=218.19)
- Charge bus: vertical at x=295 from y=201.81 to y=225.81
- Branches from R pin2 at: (290→295, y=201.81), (290→295, y=213.81), (290→295, y=225.81)
- Junctions at: (285, 205.74), (285, 206.19), (295, 213.81)

**Files:**
- Modify: `KiCad/Multimeter/Multimeter.kicad_sch`
- Create: `KiCad/Multimeter/fix_ne555_wires.py`

**Step 1: Write the fix script**

The script must:
1. Remove the 6 old horizontal branch wires (from DIS bus to R pin1, from R pin2 to charge bus)
2. Remove the 2 old bus wires (DIS bus vertical, charge bus vertical)
3. Remove the 3 old junctions at (285, 205.74), (285, 206.19), (295, 213.81)
4. Add new DIS bus: vertical wire at x=287 from y=191.77 to y=215.90 (spanning R17 pin1 to R19 pin1)
5. Add new horizontal branches from DIS bus to each R pin1:
   - (287, 191.77) → (293.37, 191.77) for R17
   - (287, 203.20) → (292.10, 203.20) for R18
   - (287, 215.90) → (292.10, 215.90) for R19
6. Add new charge bus: vertical wire at x=298 from y=199.39 to y=223.52 (spanning R17 pin2 to R19 pin2)
7. Add new horizontal branches from each R pin2 to charge bus:
   - (293.37, 199.39) → (298, 199.39) for R17
   - (292.10, 210.82) → (298, 210.82) for R18
   - (292.10, 223.52) → (298, 223.52) for R19
8. Add junctions where bus meets DIS horizontal from U6 pin7 (at 287, 205.74 if pin7 wire still reaches) and at mid-branches
9. Reconnect pin7 DIS wire: check if old wire (266.7, 205.74)→(285, 205.74) exists. Extend or replace with (266.7, 205.74)→(287, 205.74). Add junction at (287, 205.74).
10. Add junctions at (287, 203.20) and (287, 215.90) on DIS bus, and at (298, 210.82) on charge bus.

**Step 2: Close KiCad, run the script**

```bash
cd "C:/Users/Mads2/Documents/Projects/Projects/DTU Multimeter/KiCad/Multimeter"
python fix_ne555_wires.py
```

Expected: "Done! Saved." + list of operations performed.

**Step 3: Open KiCad, visually verify NE555 area**

Check that R17/R18/R19 are all connected to the DIS bus on the left and charge bus on the right. Run ERC — R18 pin 1 error should be gone.

**Step 4: Commit**

```bash
git add KiCad/Multimeter/fix_ne555_wires.py KiCad/Multimeter/Multimeter.kicad_sch
git commit -m "Fix NE555 timing resistor wiring after component relocation"
```

---

### Task 2: Fix TERM_10A and TERM_mA Dangling Labels

**Context:** Labels at (29.21, 36.83) and (29.21, 59.69) with wires going down to F1 pin1 (29.21, 41.91) and F2 pin1 (29.21, 62.23). The ERC reports these as dangling. The label connection point at angle=180 may not land on the wire endpoint. We need to verify the actual fuse positions (F1 moved to 29.21, 45.72 and F2 to 29.21, 66.04 — pin1 at y-3.81 = 41.91 and 62.23 respectively).

The wires exist: (29.21, 36.83)→(29.21, 41.91) and (29.21, 59.69)→(29.21, 62.23). The labels sit at the top of these wires. If KiCad still flags them as dangling, the label's connection point may not coincide with a wire endpoint.

**Files:**
- Modify: `KiCad/Multimeter/Multimeter.kicad_sch`
- Create: `KiCad/Multimeter/fix_term_labels_v2.py`

**Step 1: Write the fix script**

Try changing the label angle from 180 to 0 (keeping same position). At angle=0 the connection point is at the label position itself. If the label is at (29.21, 36.83) and the wire starts at (29.21, 36.83), angle=0 should connect.

If that doesn't work, alternative: remove the labels and wires, then re-add with the label placed directly at the fuse pin1 coordinate (29.21, 41.91) and (29.21, 62.23).

**Step 2: Run script with KiCad closed**

```bash
python fix_term_labels_v2.py
```

**Step 3: Verify in KiCad, run ERC**

TERM_10A and TERM_mA errors should be gone.

**Step 4: Commit**

```bash
git add KiCad/Multimeter/fix_term_labels_v2.py KiCad/Multimeter/Multimeter.kicad_sch
git commit -m "Fix TERM_10A and TERM_mA dangling label connections"
```

---

### Task 3: Fix U3 Pin 4 (SHUNT_NODE) Not Driven

**Context:** U3 pin 4 (CD4053 OUT/IN_CX_OR_CY) at (322.58, 90.17) is typed as "Input" in the KiCad symbol, but it's bidirectional in reality. Pins 4, 14, 15 should all be on the SHUNT_NODE net.

**Files:**
- Modify: `KiCad/Multimeter/Multimeter.kicad_sch`
- Create: `KiCad/Multimeter/fix_shunt_node.py`

**Step 1: Write the fix script**

Check if SHUNT_NODE label is already at pin 4. If not, add one at (322.58, 90.17) with angle=180 (label extends left from pin). Also check pins 14 and 15 have SHUNT_NODE labels.

The "input not driven" error may persist even with the label because all connected pins are input-type. Fix: add a no_connect flag if it's not actually used in the core modes, OR change the pin type in the library symbol to passive. Simplest: just mark it with a net label and accept the warning, or add a PWR_FLAG on the SHUNT_NODE net to satisfy the driver requirement.

**Step 2: Run script**

```bash
python fix_shunt_node.py
```

**Step 3: Verify in KiCad, run ERC**

U3 pin 4 error should be gone (or downgraded to warning).

**Step 4: Commit**

```bash
git add KiCad/Multimeter/fix_shunt_node.py KiCad/Multimeter/Multimeter.kicad_sch
git commit -m "Fix U3 SHUNT_NODE connection on pin 4"
```

---

### Task 4: Fix CAP_DIS Dangling Label

**Context:** `CAP_DIS` at (487.68, 252.73) on the Arduino side has no matching label. The capacitance timing circuit needs a discharge path. Per the design, `CAP_DIS` controls an FET or pin that discharges the timing capacitor. Since the NE555 area already has the timing circuit, we need a `CAP_DIS` label placed on the discharge node — likely near the TMR_CAP net or a dedicated discharge point.

For the core-only prototype (no capacitance measurement), the simplest fix is to add a no-connect flag on the A1 CAP_DIS pin wire, or place a matching label on a stub wire in the timing area for future connection.

**Files:**
- Modify: `KiCad/Multimeter/Multimeter.kicad_sch`
- Create: `KiCad/Multimeter/fix_cap_dis.py`

**Step 1: Write the fix script**

Option A (placeholder): Add a matching `CAP_DIS` label near the NE555 timing area with a short stub wire, to be connected properly when capacitance measurement is implemented.

Option B (simpler): Replace the `CAP_DIS` label on A1 pin 32 with a no_connect flag, since capacitance mode is not in the core prototype scope.

**Decision: Use Option A** — preserve the label pair for future expansion.

Place `CAP_DIS` label at a reasonable position near the timing circuit, e.g., near the charge bus, with a short dangling wire that can be connected later.

**Step 2: Run script**

**Step 3: Verify, run ERC**

**Step 4: Commit**

```bash
git add KiCad/Multimeter/fix_cap_dis.py KiCad/Multimeter/Multimeter.kicad_sch
git commit -m "Add CAP_DIS label destination in timing circuit"
```

---

### Task 5: Fix C7 Pin 2 — Connect to Probe Input (Manual)

**Context:** C7 is the AC coupling cap for the LM311 comparator. Pin 1 wired to U5 IN+. Pin 2 at (65.00, 231.27) is floating. It should connect to the V/Ohm probe input net (`ADC_CH2`).

**Do in KiCad GUI:**

1. Open schematic, navigate to C7 (around x=65, y=227)
2. C7 pin 2 is at (65.00, 231.27)
3. Add a net label `ADC_CH2` at C7 pin 2, pointing down or to the side
4. This connects C7 to the same probe input net used by the voltage divider and resistance circuit

**Verify:** Run ERC — C7 pin 2 error should be gone.

**Commit:**
```bash
git add KiCad/Multimeter/Multimeter.kicad_sch
git commit -m "Connect C7 pin 2 to probe input (ADC_CH2)"
```

---

### Task 6: Fix U4 Unit B — Wire AC Rectifier as Unity Buffer (Manual)

**Context:** U4 pin 5 (IN+_B) at (454.66, 106.68) is unconnected. Pin 6 (IN-_B) at (454.66, 106.68) and pin 7 (OUT_B) at (474.98, 109.22) also need wiring. Design decision: direct feedback (unity-gain buffer).

**Do in KiCad GUI:**

1. Navigate to U4 Unit B (around x=455-475, y=107-112)
2. Pin 5 (IN+_B) at (454.66, 106.68) — this is actually the inverting input based on the ERC position. Check the actual pin layout in the schematic.
   - Actually from the ERC: pin 5 is at (454.66, 106.68). The LM358 unit 2 has: pin 5 = IN+, pin 6 = IN-, pin 7 = OUT.
   - Wait — the ERC says U4 Pin 5 at (454.66, 106.68). Let me recheck: U4 unit 2 is at (464.82, 109.22). Pin 5 (IN+) offset is (-10.16, -2.54) = (454.66, 106.68). Pin 6 (IN-) offset is (-10.16, +2.54) = (454.66, 111.76). Pin 7 (OUT) offset is (+10.16, 0) = (474.98, 109.22).
3. **Wire pin 5 (IN+_B) at (454.66, 106.68):**
   - Add a net label `ADC_CH2` at pin 5 — connects to probe input
   - OR draw a short wire left from pin 5 and place the label
4. **Wire pin 6 (IN-_B) at (454.66, 111.76) to pin 7 (OUT_B) at (474.98, 109.22):**
   - Draw wire from pin 6 (454.66, 111.76) down to (454.66, 114.30)
   - Then right to (477.52, 114.30)
   - Then up to (477.52, 109.22)
   - Then left to pin 7 (474.98, 109.22)
   - This creates the feedback loop underneath the op-amp symbol

**Verify:** Run ERC — U4 pin 5 errors should be gone.

**Commit:**
```bash
git add KiCad/Multimeter/Multimeter.kicad_sch
git commit -m "Wire U4 Unit B as unity-gain buffer for AC measurement"
```

---

### Task 7: Address Off-Grid Warnings (Script)

**Context:** 37 endpoint_off_grid warnings from components/wires placed at fractional mm coordinates by previous scripts. These are non-critical but noisy.

**Files:**
- Create: `KiCad/Multimeter/fix_offgrid.py`

**Step 1: Write the fix script**

For each off-grid coordinate reported in the ERC:
- Snap to nearest 1.27mm grid point
- Update both wire endpoints and symbol positions
- Be careful: moving a symbol moves all its pins, so only move power symbols (#PWR*) and small passives, not ICs

**Caution:** This is the riskiest script. If a snap breaks a connection, it creates new errors. Consider running this last and checking ERC after each batch.

**Step 2: Run script, verify, commit**

```bash
python fix_offgrid.py
```

**Step 3: Final ERC check**

Target: 0 errors, <5 warnings (PWR_FLAG mismatches are cosmetic).

**Step 4: Commit**

```bash
git add KiCad/Multimeter/fix_offgrid.py KiCad/Multimeter/Multimeter.kicad_sch
git commit -m "Snap off-grid endpoints to 1.27mm grid"
```

---

## Execution Order

1. **Task 1** — NE555 wires (fixes R18 error, biggest script)
2. **Task 2** — TERM labels (fixes 2 errors)
3. **Task 3** — SHUNT_NODE (fixes 1 error)
4. **Task 4** — CAP_DIS (fixes 1 error)
5. **Task 5** — C7 manual (fixes 1 error)
6. **Task 6** — U4 Unit B manual (fixes 2 errors)
7. **Task 7** — Off-grid cleanup (fixes warnings)

After each task: run ERC to confirm error count decreases. After all tasks: target 0 errors, minimal warnings.
