# Level shifter: ~1.1-1.6 V to 3.3 V

The caliper's CLK and DATA lines swing from 0 to whatever the battery happens
to be sitting at. The ESP32-C3's logic-high threshold is roughly 0.75 x VDD,
about 2.5 V, so **an unshifted caliper line will never read as a logic 1.**
This is not a marginal-timing problem; it simply does not work.

## The rail is the battery, and it moves

Measured on this caliper: **1.078 V at the LR44, 1.085 V at the VDD pad.** Those
are the same number within measurement tolerance, which tells you the caliper
runs its logic **directly off the cell with no regulator**. There is nothing
holding the logic level steady.

That makes the supply a *range*, not a value. An alkaline LR44 leaves the
factory near 1.5 V and sags continuously; 1.078 V is close to the bottom of its
curve. So the shifter has to work over roughly:

| Condition | Rail |
|---|---|
| Fresh silver-oxide SR44 | ~1.55 V |
| Fresh alkaline LR44 | ~1.50 V |
| **Tired cell (measured here)** | **~1.08 V** |
| Design floor | 1.0 V |

**Fit an SR44 (silver oxide) rather than an LR44 (alkaline).** They are the same
size and the SR44 holds ~1.55 V almost flat until it dies, instead of drifting
down through the whole range. A steady rail is worth a lot here: every number
below gets easier, and the shifter stops being the part you have to think about.

The protocol capture in `../docs/protocol-notes.md` was taken on the tired cell
and was completely clean (22 of 22 frames identical), so those findings stand.
Worth re-checking the clock rate on a fresh cell though -- these ASICs often
clock from an RC oscillator that tracks the supply, so 2.13 kHz may shift. It
will not matter: `CALIPER_FRAME_GAP_US` has three orders of magnitude of margin.

## Parts

Per line, so two of everything:

| Part | Qty | Note |
|---|---|---|
| NPN small-signal transistor | 2 | BC547, 2N3904, 2N2222, BC337 -- any of them |
| 10 kohm resistor | 4 | two base, two collector |
| Tactile pushbutton | 2 | BLE mode only; not needed for sniffer bring-up |

All of it was already in the component inventory when this was written:
6x BC547 and 2x BC547A, 30x 10k kit resistors plus 9x 10K0 E96, and 11x 6 mm
tactile buttons. Nothing to order.

### Watch the pinout -- BC547 is not a 2N3904

Flat face toward you, legs pointing down:

```
   BC547            2N3904 / 2N2222
  ___________      ___________
 |   flat    |    |   flat    |
 |___________|    |___________|
   |   |   |        |   |   |
   C   B   E        E   B   C      mirror images
```

The middle leg is Base on both, so a stage wired to the wrong pinout has its
collector and emitter swapped. If one will not switch, swap the outer two legs
before suspecting anything else.

## Do not use a BSS138 shifter

The ubiquitous BSS138 bidirectional level-shifter board is the obvious reach
and it is the wrong answer here. Its gate threshold voltage is specified up to
1.5 V, which is *more* than the entire signal swing on a tired cell -- there is
no margin to turn it on at all. The prior art burned a whole PCB revision
discovering that an IC shifter did not work. See `../docs/prior-art.md`.

## Use a transistor pair

One common-emitter NPN stage per line.

```
          3.3V
            |
           [R2] 10k
            |
            +------> to ESP32 GPIO (inverted)
            |
        collector
            |
 caliper --[R1]-- base        2N3904
 signal   10k   |
        emitter
            |
           GND  (tied to caliper GND)
```

Build one of these per line -- one for CLK, one for DATA.

**This inverts.** A logic high at the caliper reads low at the ESP32. The
firmware accounts for it via `SHIFTER_INVERTS` in `config.h`; leave that at 1.

### Why 10k / 10k survives a flat battery

Size the base resistor at the **worst case**, not the nominal rail, or the
thing works on the bench and fails three months later as the cell ages.

At the 1.0 V design floor, with V_be about 0.7 V, only 0.3 V is left across R1:

- `Ib = 0.3 V / 10k = 30 uA`
- collector load `Ic = 3.3 V / 10k = 330 uA`
- forced beta = 330 / 30 = **11**, which is solid saturation for a 2N3904

On a fresh SR44 that becomes `Ib = 0.85 V / 10k = 85 uA`, forced beta 3.9 --
hard on. So the same 10k / 10k pair covers the whole range with margin at both
ends. R1 must stay under about 18k to keep saturation at 1.0 V; there is no
reason to go near that limit.

The one thing to watch is that 30-85 uA is being drawn out of a weak ASIC
output pin. If the high level at the base looks sagged compared to the raw pad,
raise both resistors together (22k / 22k keeps forced beta at 11 while halving
the load). Timing is a non-issue either way: at a 470 us clock period, even
100k gives a rise time three orders of magnitude faster than needed.

## Notes

- Tie caliper GND to ESP32 GND. This is the only shared connection.
- Leave the caliper on its own cell. Do not try to power the ESP32 from it --
  about 150 mAh against an 80-120 mA radio load is not a real option -- and do
  not back-feed 3.3 V into a ~1.5 V rail.
- 2N3904 is fine; any small-signal NPN works.
- If you see glitching, the firmware already majority-votes three samples per
  bit. Check grounding before adding hardware filtering.

## Bring-up checks

- [ ] Caliper GND to ESP32 GND continuity
- [ ] Caliper VDD measured, and the same value seen at the cell -- record it;
      anything under ~1.1 V means replace the cell before judging the shifter
- [ ] Scope CLK at the ESP32 pin: clean 0-3.3 V swing
- [ ] Scope DATA at the ESP32 pin: same
- [ ] Confirm inversion (caliper high = ESP32 low)
- [ ] Re-check with a fresh cell, since the rail sets the base drive
