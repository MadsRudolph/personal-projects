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

| Displayed | Raw frame (24 bits, index 0 first) | capture |
|---|---|---|
| 0.00 mm | `100000000000000000000000` | `captures/mm_0.npz` |
| 19.00 mm | `100110110111000000000000` | `captures/mm_19.npz` |
| 1.00 mm | | |
| 100.00 mm | | |
| 150.00 mm (near full scale) | | |
| -1.00 mm | | |
| 1.0000 in (if switchable) | | |

Bits 1..11 read 1900 at 19.00 mm, which is exactly 19.00 / 0.01 -- the metric
count scale from `prior-art.md` is confirmed, as is the always-1 marker at
bit 0.

Then work out:

- Magnitude first bit: **1** (confirmed) -> `CALIPER_VALUE_FIRST_BIT`
- Magnitude last bit: **>= 11, assumed 14** -> `CALIPER_VALUE_LAST_BIT`.
  Two captures cannot separate 1..11 from 1..14, because 1900 fits in 11 bits
  and bits 12-14 stayed 0. **Capture near full scale to settle this.**
- Sign bit: **unknown** -> `CALIPER_SIGN_BIT`. Needs a negative capture.
- Unit bit present? **unknown** -> `CALIPER_HAS_UNIT_BIT`, `CALIPER_UNIT_BIT`

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
