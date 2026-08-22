# Prior art -- Mew463/esp32-caliper

An existing, finished build of this same idea. Forked to
[MadsRudolph/esp32-caliper](https://github.com/MadsRudolph/esp32-caliper) and
included here at `reference/esp32-caliper` as a submodule.

Upstream: <https://github.com/Mew463/esp32-caliper> (56 stars, last touched
July 2026). Their caliper was a **Neiko 01407A**.

## Licensing -- read this before copying anything

**The upstream repo has no licence.** The GitHub API reports `license: null`,
and the only `License.txt` files present are vendor files that came with
SnapEDA/Ultra Librarian component imports -- they cover those footprints, not
the project.

No licence means all rights reserved. Practically:

- **Forking on GitHub is fine.** GitHub's Terms of Service (D.5) grant every
  user the right to fork public repos *within GitHub*. That is why this is a
  submodule pointing at a fork, and not files copied into this repo.
- **Copying their source into our tree is not covered.** The firmware in
  `firmware/` is written from scratch. It reuses *facts* about the protocol and
  the circuit -- which are not copyrightable -- but none of their code.
- If you ever want to publish this, ask the author for a licence first.

## What they confirmed

Independently verified findings, all consistent with the general lore about
budget calipers:

- **ESP32-C3** is a good fit; 150 mAh gets 20 days standby / 2 hours active.
- **Logic level is 1.5 V.** A transistor pair works. An **IC level shifter did
  not work at all** across a whole PCB revision (their V2) -- this cost them a
  board spin. Do not repeat it.
- **BLE HID keyboard** is the right integration path; they drive Onshape with it.
- **Two buttons** is the right ergonomics: one appends Enter, one appends Space
  so you can type a tolerance after the value.

## Protocol as they decoded it

24 bits, sampled on the clock edge, LSB first:

| Bit(s) | Meaning |
|---|---|
| 0 | always 1 |
| 1-14 | magnitude, LSB first |
| 21 | sign, 1 = negative |
| 23 | unit -- **present on their old caliper, absent on the new one** |

Scaling: metric counts are 0.01 mm, imperial counts are 0.0005 in.

Two caveats:

1. Their README says bits 1-15 carry the value, but their code loops
   `for (a = 1; a < 15; a++)`, i.e. bits 1-14. `config.h` follows the code.
   Worth resolving on a scope.
2. The unit bit vanished between two production runs of *the same model*. This
   is the strongest argument for running the sniffer rather than trusting any
   published bit map.

## Techniques worth adopting

- **Triple-sample the data line** and majority-vote. Shifter transitions are
  slow enough to glitch, and one bad sample corrupts the reading. Adopted in
  `caliper.cpp`.
- **Frame resync on a timing gap** rather than a preamble -- a silence longer
  than ~3 ms means the next edge starts a new frame. Adopted.

## Things we deliberately did differently

- **Non-blocking capture.** They busy-wait (`while (!getData());`) on the button
  press, which hangs forever if the caliper is off or unplugged. We capture
  continuously in an ISR and buffer the latest reading, then check freshness
  before typing.
- **No `MyButton.h`.** Their sketch includes an absolute path from the author's
  own machine, so it will not build for anyone else. We use a small inline
  debouncer.
- **No type-zero-then-backspace.** They send `"0"`, wait 200 ms, send Backspace,
  wait 200 ms, then send the value -- presumably to nudge the Onshape input
  field into focus. That is 400 ms of latency per measurement. Try without it
  first and only add it back if your CAD package actually needs it.
- **Configurable decimal separator.** They hardcode `.`, which breaks on a
  Danish keyboard layout.
- **Tab, not Enter, after the value.** Tested against real CAD: Tab advances to
  the next field, while Enter tends to commit or close the whole dialog, which
  is rarely what you meant mid-sketch. `SEND_TERMINATOR_KEY` in `config.h`
  takes any BleKeyboard constant, and `SEND_TERMINATOR 0` types the bare value
  and presses nothing.
