# Level shifter: 1.5 V to 3.3 V

The caliper's CLK and DATA lines swing 0-1.5 V. The ESP32-C3's logic-high
threshold is roughly 0.75 x VDD, about 2.5 V, so **an unshifted caliper line
will never read as a logic 1.** This is not a marginal-timing problem; it
simply does not work.

## Do not use a BSS138 shifter

The ubiquitous BSS138 bidirectional level-shifter board is the obvious reach
and it is the wrong answer here. Its gate threshold voltage is specified up to
1.5 V, which is the entire signal swing -- there is no margin to turn it on
reliably. The prior art burned a whole PCB revision discovering that an IC
shifter did not work at all. See `../docs/prior-art.md`.

## Use a transistor pair

One common-emitter NPN stage per line. 1.5 V is comfortably above V_be of about
0.7 V, so the transistor switches hard, and the output swings rail to rail at
3.3 V.

```
          3.3V
            |
           [R2] 10k
            |
            +------> to ESP32 GPIO (inverted)
            |
        collector
            |
 1.5V --[R1]-- base        2N3904
 signal  10k   |
        emitter
            |
           GND  (tied to caliper GND)
```

Build one of these per line -- one for CLK, one for DATA.

**This inverts.** A logic high at the caliper reads low at the ESP32. The
firmware accounts for it via `SHIFTER_INVERTS` in `config.h`; leave that at 1.

## Notes

- Tie caliper GND to ESP32 GND. This is the only shared connection.
- Leave the caliper on its own LR44. Do not try to power the ESP32 from it --
  about 150 mAh against an 80-120 mA radio load is not a real option, and do
  not back-feed 3.3 V into a 1.5 V rail.
- 2N3904 is fine; any small-signal NPN works. R1 and R2 at 10k are not
  critical.
- If you see glitching, the firmware already majority-votes three samples per
  bit. Check grounding before adding hardware filtering.

## Bring-up checks

- [ ] Caliper GND to ESP32 GND continuity
- [ ] Caliper VDD measures about 1.5 V
- [ ] Scope CLK at the ESP32 pin: clean 0-3.3 V swing
- [ ] Scope DATA at the ESP32 pin: same
- [ ] Confirm inversion (caliper high = ESP32 low)
