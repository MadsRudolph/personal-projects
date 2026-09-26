# ESP32 solder test board

This is the smallest board that proves an ESP32-WROOM-32 hand-soldered to copper etched on the
xTool F1 Ultra actually works. Once it's soldered, you flash it over a USB-UART adapter and blink the
LED on IO2. Everything except the module is through-hole and stocked at the DTU component shop.

- Single-sided, 54 x 46 mm, copper on the bottom (B.Cu). The ESP32 sits on the copper side and
  the through-hole parts go on top.
- Rule: 0.3 mm clearance / 0.5 mm track, inside what the test coupon proved (0.15 / 0.15 clean).
- Gates:
  - Schematic: `sch_score` PASS, ERC 0 violations, netlist verified.
  - Board: fully routed (11/11 nets, 0 unconnected, 0 vias, all tracks 0.5 mm), single GND pour
    in one piece, DRC clean on copper. The only leftovers are silkscreen cosmetics and one
    single-spoke thermal on SW2's GND pad, which is harmless.

## Bill of materials (DTU component shop part numbers)

| Ref | Part | Shop entry |
|---|---|---|
| U1 | ESP32-WROOM-32 module | not in the shop (bring your own) |
| U2 | LM317T, TO-220 | IC / Voltage Regulator / `LM317T` |
| R1 | 243 R | Resistor E96 `243R` |
| R2 | 392 R | Resistor E96 `392R` |
| R3, R4 | 10 k | Resistor E96 `10K0` |
| R5 | 332 R | Resistor E96 `332R` |
| R6 | 1 k | Resistor E96 `1K00` |
| C1, C2 | 10 uF electrolytic | Capacitor / Electrolytic `10µF` |
| C4 | 1 uF electrolytic | Capacitor / Electrolytic `1µF` |
| C3 | 100 nF ceramic | Capacitor / Ceramic `100n` |
| D1 | 3 mm LED, green (IO2) | LED `LED 3MM GRØN` |
| D2 | 3 mm LED, red (power) | LED `LED 3MM RØD` |
| SW1, SW2 | 6 mm tactile pushbutton | Hardware / Switch `Pushbutton` (check it has the 6.5 x 4.5 mm pin pattern) |
| J1 | 1x4 straight male header | Connector / Header `Header Male` (break off 4 pins) |

The shop has no fixed 3.3 V regulator, so the LM317 is set to 1.25 V x (1 + 392/243) = **3.27 V**.
R1 also draws the ~5 mA minimum load the LM317 needs. It needs about 1.7 V of headroom from 5 V,
which is plenty for flashing and blinking. WiFi transmit peaks (~400 mA) may sag it, so for real
WiFi use a stiff 5 V supply or swap in a low-dropout 3.3 V regulator.

## Laser files (`production/`)

Both files are **already mirrored to the copper side**, so do **not** mirror them in XCS.
Check: the copper text **"ESP32 TEST"** must read normally in the XCS preview.

1. **`esp32solder_copper_negative_MIRRORED.dxf`**: the copper to remove.
   - Import it, then **Make compound**. Black is removed; the pads, tracks and GND pour must be white.
   - Engrave with the **`Traces`** preset: 100 %, 600 mm/s, 10 passes, 240 lines/cm, one-way,
     30 kHz, cross hatch. See `../esp32-node/xtool/F1Ultra_PCB_presets.json`.
   - The drill holes are engraved as black dots in the pads, for centring.
2. **`esp32solder_drill_outline_MIRRORED.dxf`**: hole circles (layer `HOLES`) and board outline
   (layer `OUTLINE`).
   - Use the **`Cut/Drill`** vector preset (100 %, 100 mm/s, 160 passes). Both files share the
     same origin, so they stay registered if you import them into the same XCS canvas.
   - Hole sizes: 0.8 mm (resistors, caps), 0.9 mm (LEDs), 1.0 mm (header), 1.1 mm (LM317, buttons).

Sand lightly with 400 grit, then Framing, then Auto height adjustment, then Process.

## Soldering order

1. **ESP32 first**, while the board is still flat. It goes on the **copper side**, with the antenna
   overhanging the top edge, flush with the board edge. Tack two opposite corner pads, check
   alignment, then drag-solder the castellations. The big centre GND pad doesn't need solder;
   GND is carried by pins 1, 15 and 38.
2. Then the through-hole parts from the **plain side**, soldered on the copper side. Go lowest
   first: resistors, ceramic cap, LEDs (flat side = cathode), electrolytics (stripe = minus),
   buttons, header, and the LM317 last.
3. Before powering up, measure with a meter:
   - +5V to GND is not shorted.
   - Adjacent ESP32 pads are not bridged: probe neighbours, especially 1/2/3 (GND/3V3/EN) and
     34/35 (RXD0/TXD0).

## First power-up and flashing

- J1, starting at pin 1 (the square pad, nearest the antenna edge): **GND, 5V, TXD0 (ESP out), RXD0 (ESP in)**.
- Use a USB-UART adapter set to **3.3 V logic**. Wire adapter GND to GND, 5 V to 5V,
  adapter **RX to TXD0**, and adapter **TX to RXD0**.
- The red LED should light. Measure 3.2–3.3 V across C2.
- **Bootloader:** hold **BOOT**, tap **RESET**, release BOOT. Then run `esptool.py chip_id`
  (or `esptool.py flash_id`). If it answers, the module and all four UART/boot joints are good.
- Flash a blink sketch on **GPIO2** (Arduino `LED_BUILTIN` on the ESP32 Dev Module target) to see
  the green LED.

## Files

- `esp32solder_sch.py` builds `esp32solder.kicad_sch` (kicad-schematic DSL). It's the source of truth.
- `place_pcb.py` places the board (the footprint positions come from the flipped module's pads).
  The route came from FreeRouting 2.4.1 via `place_route.py`.
- `finish_pcb.py` adds the copper orientation text and refills the pour.
- `relink_pcb.py` links each footprint to its library and schematic symbol, so KiCad's
  schematic parity, cross-probing and "Update PCB from Schematic" work. `bootstrap_pcb.py`
  runs it automatically.
- `export_laser.py` writes the two DXFs above. It's the same negative-DXF approach as the coupon
  that came out perfectly.
- `esp32solder.placed.kicad_pcb` is the unrouted placement, kept for reference.
- `tools/pyshim` is a Python 3.14 workaround for pcbnew. Run the scripts with
  `PYTHONPATH=tools/pyshim python3 <script>`.
