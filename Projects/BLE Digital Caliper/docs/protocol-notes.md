# Protocol worksheet

Fill this in during bring-up, then update `firmware/include/config.h` to match.
Do not skip it -- see `prior-art.md` for why published bit maps are unreliable.

## 1. Caliper identification

- Make / model: _______________ (still to record)
- Data port: **4 exposed pads**
- Battery: **LR44** (alkaline). An SR44 silver oxide is the better fit -- same
  size, holds ~1.55 V flat instead of sagging across the whole range.

## 2. Pad identification

Probe each pad against the caliper's own battery negative.

    cd tools && python caliper_padscan.py --label "pads 1 and 2"

Two pads per run (the AD3 has two analog scope channels); move the probes and
repeat for the other two. Wiring and the one thing not to do are in the script's
header. Note that GND and an unconnected probe look identical, so make sure the
tip is really on the pad.

Recorded by the colour of the wire soldered to each pad, which is what we
actually know; the physical left-to-right order of black is not noted.

| Wire | Signal | Notes |
|---|---|---|
| black | `GND` | reference for everything below |
| green | `DATA` | pulses once per 0 bit, flat across a 1 bit |
| orange | `CLK` | 24 pulses per frame, invariant with the reading |
| gray | `VDD` | static; 2 edges in 3 s, both readings identical |

So the expected `GND, DATA, CLK, VDD` set is all present -- but **CLK and DATA
are not in the order you would guess**, and telling them apart took two
captures at different displacements (see below).

- Measured VDD: **1.085 V at the pad, 1.078 V at the cell.** Same number within
  tolerance, so the caliper runs its logic **straight off the battery with no
  regulator** -- the logic level is whatever the cell is doing that day. This
  cell is nearly flat (an alkaline LR44 starts near 1.5 V). Everything below
  was captured on it and was clean, but see `../hardware/level-shifter.md`:
  the shifter has to cover ~1.0 to 1.6 V, not a fixed 1.5 V.
- Clock frequency: **2.13 kHz** within a group (470 us period)
- Frame repetition rate: **6.0 - 6.3 Hz**
- Frame length: **13.2 ms**
- Gap between frames: **~145 ms** -> `CALIPER_FRAME_GAP_US 3000` is correct: it
  sits well above the 930 us group gap and well below the 145 ms frame gap.

### Frame shape

The 24 clock pulses come in **6 groups of 4**, with the clock stretching its
low to ~930 us between groups. Six nibbles suggests a BCD-ish layout, but the
decode below shows a plain LSB-first binary field, so the grouping appears to
be presentation only.

### Telling CLK from DATA

A single capture cannot do it on this caliper. At 0.00 mm the DATA line pulses
once per zero bit, so with an almost-all-zero frame it toggles every bit period
and looks exactly like a clock. What separates them is **capturing two
different readings**: the clock's edge count per frame never changes, DATA's
does.

| line | edges/frame at 0.00 mm | at 19.00 mm |
|---|---|---|
| orange | 47 | 47 (invariant -> CLK) |
| green | 47 | 33 (varies -> DATA) |

The green counts are exactly `2 x (number of zero bits) + 1`, which is what
gives it away as a return-to-zero data line rather than a clock.

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

Data is sampled on the **falling edge of CLK**. (The firmware triggers on
RISING with `SHIFTER_INVERTS 1`, which is the same edge once the inverting
shifter has flipped it.)

| Displayed | Raw frame (24 bits, index 0 first) | count | capture |
|---|---|---|---|
| 0.00 mm | `100000000000000000000000` | 0 | `mm_0.npz` |
| 0.99 mm | `111000110000000000000000` | 99 | `mm_1.npz` |
| 10.01 mm | `110010111110000000000000` | 1001 | `mm_10.npz` |
| 19.00 mm | `100110110111000000000000` | 1900 | `mm_19.npz` |
| 103.76 mm | `100010001000101000000000` | 10376 | `mm_100.npz` |
| 163.82 mm (full scale) | `101111111111111000000000` | 16382 | `mm_max.npz` |
| -1.11 mm | `111110110000000000000100` | 111, sign set | `mm_neg1.npz` |
| 1.0010 in | `101001011111000000000000` | 2002 | `in_1.npz` |

Every one of those decodes back to the displayed value with **zero error**
using the field below. Re-check any time with:

    cd tools && python caliper_decode.py ../captures/mm_*.npz

### The answer

- Magnitude first bit: **1** -> `CALIPER_VALUE_FIRST_BIT`
- Magnitude last bit: **14** -> `CALIPER_VALUE_LAST_BIT`
- Sign bit: **21**, 1 = negative -> `CALIPER_SIGN_BIT`
- Unit bit: **none** -> leave `CALIPER_HAS_UNIT_BIT` at 0
- Bit 0 is always 1. Bits 15-20, 22 and 23 were 0 in every capture.
- Scales: **0.01 mm** and **0.0005 in** per count, both verified.

The 14-bit field is not an assumption. Full scale is 163.82 mm = 16382 counts
and 2^14 - 1 = 16383, so the caliper's whole range is exactly what the field
can hold. Nothing narrower fits 16382, and nothing wider is reachable.

### No unit bit -- and why that matters

Switching the display to inches changes only the **count scale**: 1.0010 in
arrived as 2002 counts of 0.0005 in, and every bit outside the magnitude and
sign fields stayed 0 in both modes. Nothing in the frame says which unit it is.

So the firmware cannot work it out. Switch the caliper to inches without
telling it and the typed number is wrong by a factor of 50.8. Pick the unit
with `CALIPER_DEFAULT_INCHES`, or hold both buttons at boot.

## 4. Verification

Done on the AD3, before any hardware exists:

- [x] Reads 0.00 when closed
- [x] Matches the display across the full range (0 to 163.82 mm, zero error)
- [x] Negative values correct (-1.11 mm, sign bit 21)
- [x] Inch mode correct (1.0010 in = 2002 counts)

Still to do on the ESP32, with `CALIPER_SNIFFER_MODE = 0`:

- [ ] Frames match what the AD3 saw, inverted by the shifter
- [ ] Gauge blocks or a known pin agree to +/-0.01 mm
- [ ] Decimal separator accepted by the CAD field
