# Class D simulation testbenches

One KiCad sheet per block of the amplifier. Open a `.kicad_pro` in KiCad, then
**Inspect -> Simulator** and press Run: each sheet carries its own analysis
command, both as text on the sheet and in its `.wbk` workbook.

| sheet | what it answers |
|---|---|
| `sim_a_vground` | does the 6 V virtual ground come up and settle? |
| `sim_b_triangle` | is the carrier the right frequency and amplitude? |
| `sim_c_input` | are AUDIO_P and AUDIO_N truly equal and opposite? |
| `sim_d_pwm` | does duty track the audio, and stay complementary? |

## Models

`models/classd_sim.lib` holds behavioural subcircuits for the four parts no one
ships a model for — `OPAMP_TL074`, `CMP_LM311`, `INV_CD4049`, `DRV_HIP4082` —
each parameterised with the datasheet figures recorded in `docs/BUILD-NOTES.md`.
They use only primitives every ngspice understands (B/E/G sources, switches and
lossless T-lines for delay), deliberately avoiding the XSPICE digital models
KiCad's own class-D demo relies on, because those are not compiled into every
ngspice build.

The IRF540N is the exception: `models/IRF-Power-VDMOS.mod` is the real VDMOS
card KiCad ships, body diode included.

## Verifying

`tools/test_models.py` checks each model against its datasheet numbers.
`tools/run_sims.py` exports each sheet through `kicad-cli` and asserts the
numbers the design is supposed to produce. Both need the miniconda interpreter
that has PySpice:

```
C:\Users\Mads2\miniconda3\python.exe tools\test_models.py
C:\Users\Mads2\miniconda3\python.exe tools\run_sims.py
```

These are a harness for catching broken testbenches, not part of the
deliverable — the sheets themselves run in KiCad's own simulator.

## What the simulations found

- **The carrier lands at ~215 kHz, not the 250 kHz the arithmetic predicts.**
  The LM311's 165 ns propagation delay adds to every half period, roughly
  330 ns per cycle. `RV1` covers it easily, which is exactly why the brief
  asked for a trimmer — but do not expect the calculated value to be the one
  you set.
- The virtual ground takes about 2.5 s to settle through R1||R2 into C1. Worth
  knowing before deciding a board is dead at power-on.
- AUDIO_P stays at 5.29 V minimum at design level, clear of the TL074's
  V-+4 V input common-mode floor. That is the design's one flagged electrical
  risk, and it is checked explicitly rather than assumed.
