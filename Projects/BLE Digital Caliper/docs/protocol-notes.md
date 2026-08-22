# Protocol worksheet

Fill this in during bring-up, then update `firmware/include/config.h` to match.
Do not skip it -- see `prior-art.md` for why published bit maps are unreliable.

## 1. Caliper identification

- Make / model: _______________
- Data port: 4 exposed pads / micro-USB shaped / none
- Battery: LR44 (1.5 V) / CR2032 (3 V)

## 2. Pad identification

Probe each pad against the caliper's own battery negative.

| Pad (L to R) | Signal | Notes |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |

Expected: `GND`, `DATA`, `CLK`, `VDD (~1.5 V)`, but the order is not
standardised.

- Measured VDD: _______ V
- Clock frequency: _______ kHz
- Frame repetition rate: _______ Hz
- Gap between frames: _______ ms  -> set `CALIPER_FRAME_GAP_US`

## 3. Bit mapping

Set `CALIPER_SNIFFER_MODE = 1` and capture frames at known displacements.
Zero the caliper first.

| Displayed | Raw frame (24 bits, index 0 first) |
|---|---|
| 0.00 mm | |
| 1.00 mm | |
| 10.00 mm | |
| 100.00 mm | |
| -1.00 mm | |
| 1.0000 in (if switchable) | |

Then work out:

- Magnitude first bit: _____ -> `CALIPER_VALUE_FIRST_BIT`
- Magnitude last bit: _____ -> `CALIPER_VALUE_LAST_BIT`
- Sign bit: _____ -> `CALIPER_SIGN_BIT`
- Unit bit present? yes / no -> `CALIPER_HAS_UNIT_BIT`, `CALIPER_UNIT_BIT`

Sanity checks:

- 100.00 mm needs a count of 10000, so at least 14 magnitude bits.
- Toggling mm/inch on the caliper should flip exactly one bit if a unit bit
  exists. If nothing changes, it does not.
- Compare 1.00 mm against 10.00 mm -- the count should be exactly 10x.

## 4. Verification

With `CALIPER_SNIFFER_MODE = 0`:

- [ ] Reads 0.00 when closed
- [ ] Matches the display across the full range
- [ ] Negative values correct
- [ ] Gauge blocks or a known pin agree to +/-0.01 mm
- [ ] Decimal separator accepted by the CAD field
