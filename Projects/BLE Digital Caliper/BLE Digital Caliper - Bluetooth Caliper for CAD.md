# BLE Digital Caliper

Bolt an ESP32-C3 onto an ordinary digital caliper so it pairs as a Bluetooth
keyboard and types measurements straight into CAD.

**Status:** 🟡 Planning -- firmware skeleton written, AD3 bench tooling ready,
protocol not yet measured

## Why a keyboard

CAD packages do not speak BLE. They all speak keyboard. Advertising the ESP32
as a **BLE HID keyboard** means Fusion, SolidWorks, Onshape, FreeCAD, Excel and
everything else just work, with no host-side software, no add-in to maintain,
and no per-application integration. Press a button on the caliper, the number
lands in whatever field has focus.

## How it works

```
caliper 1.5V logic --> transistor level shifter --> ESP32-C3 --> BLE HID --> PC
   (CLK + DATA)          (inverts both lines)       (decode)     (keyboard)
```

The caliper pushes a 24-bit frame out of its data port a few times a second.
There is no request line -- we just listen, decode, and buffer the latest
reading. A physical button decides when to actually type it, which matters:
without one you would spray hundreds of numbers into your sketch.

## Hardware

| Part | Notes | ~Cost |
|---|---|---|
| ESP32-C3 SuperMini | Better BLE power profile than classic ESP32 | $3 |
| LiPo 250–400 mAh + TP4056 | Do **not** run this off the caliper's LR44 | $5 |
| 2× 2N3904 + resistors | Level shifter, see `hardware/level-shifter.md` | $0.50 |
| 2× tactile switch | Send-with-Enter, send-with-Space | $0.50 |
| 3D-printed clip | The part you will actually be unhappy with | -- |

## Bring-up order

The protocol work comes **before** any soldering. An Analog Discovery 3 reads
the caliper's 1.5 V lines directly on its analog scope channels, so the whole
bit map can be settled while the hardware is still a pile of parts -- and if
the bit map turns out to be strange, that is much cheaper to find out now.

1. **Find the data port.** Small cover on the top edge of the slider. Four pads:
   `GND`, `DATA`, `CLK`, `VDD (~1.5 V)`. Pad order is not standardised, so
   measure it:

   ```
   cd tools && python caliper_padscan.py
   ```

   Two pads at a time; move the probes and repeat. Record the answer in
   `docs/protocol-notes.md` section 2.

2. **Decode the protocol, still with no hardware built.** Capture at several
   known displacements, then let the decoder solve the bit map:

   ```
   cd tools
   python caliper_capture.py --expect 0.00   --out ../captures/mm_0.npz
   python caliper_capture.py --expect 1.00   --out ../captures/mm_1.npz
   python caliper_capture.py --expect 10.00  --out ../captures/mm_10.npz
   python caliper_capture.py --expect 100.00 --out ../captures/mm_100.npz
   python caliper_capture.py --expect -1.00  --out ../captures/mm_neg1.npz
   python caliper_decode.py ../captures/*.npz
   ```

   It searches every possible magnitude field for the one that reproduces all
   your readings at once and prints a `config.h` block. Fill in
   `docs/protocol-notes.md` section 3 from that.

3. **Build the level shifter.** See `hardware/level-shifter.md`.
4. **Confirm on the ESP32.** `CALIPER_SNIFFER_MODE = 1` in
   `firmware/include/config.h`. The frames should match what the AD3 saw, but
   inverted -- the shifter flips both lines.
5. **Flip to BLE.** `CALIPER_SNIFFER_MODE = 0`, pair, measure something known.
6. **Fix the decimal separator** if the value is rejected -- see below.

## Gotchas

- **The AD3's logic analyzer cannot see this signal either.** Its 16 DIO
  inputs are fixed 3.3 V LVCMOS -- logic high from about 2.0 V -- and the AD3
  exposes no adjustable logic level (unlike the Digital Discovery). A 1.5 V
  high reads as a steady LOW and the lines look dead. Use the two **analog**
  scope channels instead, which is what `tools/` does.
- **1.5 V will not drive an ESP32 input.** Its logic-high threshold is ~2.5 V.
  You must shift up. The BSS138 shifter everyone reaches for is marginal here
  because its gate threshold can be as high as 1.5 V; the prior art in
  `docs/prior-art.md` confirms an IC shifter failed outright. Use transistors.
- **HID sends scancodes, not characters.** On a Danish layout the decimal
  separator is a different physical key than on US, and Windows may want `,`
  rather than `.`. Set `DECIMAL_SEPARATOR` in `config.h`.
- **Your caliper may send no unit bit.** Newer units often dropped it. Set
  `CALIPER_HAS_UNIT_BIT 0` and pick the unit at boot (hold both buttons).
- **Battery life** depends entirely on sleeping. The reference build gets 20
  days standby / 2 hours active from 150 mAh.

## Layout

- `tools/` -- AD3 bench scripts: pad scan, capture, protocol decoder
- `firmware/` -- PlatformIO project, ESP32-C3
- `docs/protocol-notes.md` -- worksheet to fill in during bring-up
- `docs/prior-art.md` -- findings from an existing build, and licensing
- `hardware/level-shifter.md` -- the 1.5 V → 3.3 V circuit
- `reference/esp32-caliper/` -- submodule, fork of the prior art

## Prior art

[Mew463/esp32-caliper](https://github.com/Mew463/esp32-caliper) is a complete
working build of this exact idea, forked to
[MadsRudolph/esp32-caliper](https://github.com/MadsRudolph/esp32-caliper) and
vendored here as a submodule. Read `docs/prior-art.md` before writing any code
-- it confirms the protocol, the level shifter, and several dead ends.

Their closing advice is worth repeating: if you just want a Bluetooth caliper,
buy one. This is worth doing because it is a good embedded project, not because
it is cheaper.
