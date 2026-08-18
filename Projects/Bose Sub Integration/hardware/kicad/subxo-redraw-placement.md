# Sub crossover — redraw placement reference

Target layout for the readable redraw. Coordinates are millimetres on
KiCad's 1.27 mm grid, as shown in Eeschema's status bar. Set the editor
grid to 50 mil before moving anything.

See `subxo-redraw-reference.pdf` for what the finished sheet looks like,
and `subxo-redraw-reference.kicad_sch` if you want to open the drawing
itself for comparison.

## Bands

| band | y range (mm) | contents |
|---|---|---|
| 1 | 20–60 | power in, status LEDs, virtual ground, U1 supply |
| 2 | 70–180 | L/R inputs, summing, Sallen-Key low-pass, polarity inverter |
| 3 | 195–260 | output stage, spare section |

Signal flows left to right in each band.

## Part placement

| ref | x | y | rot | mirror | value |
|---|---|---|---|---|---|
| R10 | 132.08 | 38.1 | 0 | - | 4k7 |
| R11 | 147.32 | 38.1 | 0 | - | 4k7 |
| R8 | 187.96 | 38.1 | 0 | - | 10k |
| J4 | 17.78 | 40.64 | 0 | y | PWR IN 15V |
| U2 | 55.88 | 40.64 | 0 | - | LM7812 |
| U1 | 261.62 | 43.18 | 0 | - | TL074 |
| C10 | 38.1 | 44.45 | 0 | - | 100uF/50V |
| C11 | 66.04 | 44.45 | 0 | - | 100uF/50V |
| C12 | 78.74 | 44.45 | 0 | - | 100nF |
| C13 | 91.44 | 44.45 | 0 | - | 100nF |
| C14 | 104.14 | 44.45 | 0 | - | 100nF |
| U1 | 223.52 | 45.72 | 0 | - | TL074 |
| D1 | 132.08 | 48.26 | 90 | - | PWR green |
| D2 | 147.32 | 48.26 | 90 | - | INV amber |
| R9 | 187.96 | 48.26 | 0 | - | 10k |
| C15 | 200.66 | 48.26 | 0 | - | 100uF/50V |
| LK1 | 119.38 | 52.07 | 0 | - | 0R wire link |
| J7 | 160.02 | 57.15 | 0 | - | INV LED |
| JP1 | 83.82 | 88.9 | 0 | y | C1 select |
| C1_3 | 106.68 | 100.33 | 180 | - | 150nF film |
| C1_2 | 124.46 | 100.33 | 180 | - | 220nF film |
| C1_1 | 142.24 | 100.33 | 180 | - | 470nF film |
| J1 | 17.78 | 120.65 | 0 | y | IN L |
| C_in1 | 35.56 | 120.65 | 90 | - | 220n or 2u2 |
| R1_1 | 66.04 | 120.65 | 90 | - | 16k5 |
| R_b1 | 50.8 | 128.27 | 0 | - | 100k |
| R2 | 104.14 | 132.08 | 90 | - | 8k25 |
| U1 | 144.78 | 134.62 | 0 | - | TL074 |
| R3 | 195.58 | 134.62 | 90 | - | 10k |
| J2 | 17.78 | 140.97 | 0 | y | IN R |
| C_in2 | 35.56 | 140.97 | 90 | - | 220n or 2u2 |
| R1_2 | 66.04 | 140.97 | 90 | - | 16k5 |
| U1 | 236.22 | 142.24 | 0 | - | TL074 |
| R_b2 | 50.8 | 148.59 | 0 | - | 100k |
| C2_1 | 106.68 | 151.13 | 0 | - | 150nF film |
| C2_2 | 124.46 | 151.13 | 0 | - | 120nF film |
| C2_3 | 142.24 | 151.13 | 0 | - | 68nF film |
| R4 | 218.44 | 157.48 | 90 | - | 10k |
| JP2 | 83.82 | 172.72 | 0 | y | C2 select |
| R5 | 127.0 | 205.74 | 90 | - | 100R |
| J5 | 43.18 | 213.36 | 0 | y | POLARITY SW |
| J6 | 93.98 | 213.36 | 0 | y | LEVEL POT 10k |
| J3 | 162.56 | 213.36 | 0 | - | OUT 3.5mm |
| C_out1 | 66.04 | 215.9 | 90 | - | 10uF/50V |
| R6 | 127.0 | 220.98 | 90 | - | 100R |
| U1 | 218.44 | 223.52 | 0 | - | TL074 |
| R7 | 119.38 | 238.76 | 90 | - | 10R |
| JP3 | 91.44 | 248.92 | 0 | y | GND lift |
