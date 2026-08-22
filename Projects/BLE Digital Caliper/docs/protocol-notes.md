# Protocol worksheet

Fill this in during bring-up, then update `firmware/include/config.h` to match.
Do not skip it -- see `prior-art.md` for why published bit maps are unreliable.

## 1. Caliper identification

- Make / model: _______________
- Data port: 4 exposed pads / micro-USB shaped / none
- Battery: LR44 (1.5 V) / CR2032 (3 V)

## 2. Pad identification

Probe each pad against the caliper's own battery negative.

    cd tools && python caliper_padscan.py --label "pads 1 and 2"

Two pads per run (the AD3 has two analog scope channels); move the probes and
repeat for the other two. Wiring and the one thing not to do are in the script's
header. Note that GND and an unconnected probe look identical, so make sure the
tip is really on the pad.

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

Zero the caliper first, then capture at each displacement below with the AD3 --
no firmware and no level shifter needed yet:

    cd tools
    python caliper_capture.py --expect 10.00 --out ../captures/mm_10.npz
    ...
    python caliper_decode.py ../captures/*.npz

`caliper_decode.py` searches every possible magnitude field for the one that
reproduces all the readings at once, finds the sign bit by comparing negative
captures against positive ones, and prints a `config.h` block. Copy its answers
into the table and the list below.

If it reports that both clock polarities fit, they differ by a uniform one-bit
shift and the bit numbers are only valid together with the edge the firmware
triggers on -- do not mix a bit map from one with the edge from the other.

(`CALIPER_SNIFFER_MODE = 1` on the ESP32 does the same job later, as a check
that the shifter and the ISR agree with what the AD3 saw.)

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
  exists. If nothing changes, it does not. Capture the same displacement in
  both units and compare the two frames printed by `caliper_decode.py`.
- The decoder lists several magnitude fields when the wider ones only fit
  because their top bits never got exercised. Capture something near full
  scale (e.g. 150 mm on a 150 mm caliper) to rule them out.
- Compare 1.00 mm against 10.00 mm -- the count should be exactly 10x.

## 4. Verification

With `CALIPER_SNIFFER_MODE = 0`:

- [ ] Reads 0.00 when closed
- [ ] Matches the display across the full range
- [ ] Negative values correct
- [ ] Gauge blocks or a known pin agree to +/-0.01 mm
- [ ] Decimal separator accepted by the CAD field
