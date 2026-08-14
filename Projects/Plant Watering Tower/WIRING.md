# Wiring — Plant Watering Tower

Standalone bench reference. For the firmware, calibration, and safety rationale see
[README.md](README.md).

## ⚠️ Before you touch anything

- Do **all** mains-side work with the plug **physically unplugged**.
- This pump is **230V AC** — a bare joint can kill you or start a fire. Enclose every
  live conductor, bond exposed metal to earth, and have it checked if you're not
  competent with mains.
- The relay module is **non-opto-isolated**: treat the whole low-voltage side as if it
  could become live under a fault. Keep mains and low-voltage wiring physically separated.

## Two isolated sides

| Side | What's on it | Voltage |
|---|---|---|
| **Mains** | wall plug → relay contacts (COM/NO) → thermal cutoff → pump | 230V AC |
| **Low-voltage** | 5V supply, D1 Mini ESP32, relay coil, float switch | 5V / 3.3V |

They meet at **exactly one wire**: `ESP32 GPIO16 → relay IN`. Nothing else crosses.

## Full system

```
                 ┌──────────────────── MAINS SIDE (230V) ────────────────────┐
                 │                                                            │
 wall   LIVE ────┼──→ relay COM                                              │
 plug   (brown)  │      relay NO ──→ Lead A ─[thermal cutoff]─ pump pin 1    │
                 │      relay NC ──→ (unused)                                 │
        NEUTRAL ─┼──────────────────────────── Lead B ──────── pump pin 2    │
        (blue)   │                            (yellow wire)                   │
        EARTH ───┼──→ metal enclosure / exposed metal  (NOT the pump body)    │
        (grn/yel)│                                                            │
                 └────────────────────────────────────────────────────────────┘
                                            ▲
                          relay IN ─────────┘  (only crossing)
                                            │
                 ┌──────────────────── LOW-VOLTAGE SIDE (5V) ────────────────┐
                 │                                                            │
   5V supply ──┬─┼──→ D1 Mini 5V                                             │
               └─┼──→ relay VCC                                              │
               ┌─┼──→ D1 Mini G                                              │
   0V / GND ───┼─┼──→ relay GND                                             │
               └─┼──→ float switch (leg 1)                                  │
                 │                                                            │
   D1 Mini 16 ───┼──→ relay IN                                              │
   D1 Mini 17 ───┼──→ float switch (leg 2)                                  │
                 └────────────────────────────────────────────────────────────┘
```

## The pump's two leads

The coil is AC, so it isn't polarity-sensitive — what matters is that the thermal cutoff
stays **in series** with the coil.

- **Lead A** = free terminal of the **thermal cutoff** (white part).
  Internally `thermal cutoff ← white wire ← pump pin 1`. → **switched-live** side.
- **Lead B** = free end of the **yellow** wire, off pump pin 2. → **neutral** side.
  - *This unit:* pump pin 2 also has a small **red** wire — it reads **0 Ω to yellow**, i.e. a
    redundant tap on the same terminal. Use either yellow or red for neutral; **cap the other
    one off insulated** (it's a mains conductor). It is *not* a thermal device.

## Mains side (relay switches LIVE only)

| From | To |
|---|---|
| Mains **LIVE** (brown) | relay **COM** |
| relay **NO** | **Lead A** (thermal cutoff free terminal) → pump |
| Mains **NEUTRAL** (blue) | **Lead B** (yellow wire) → pump |
| Mains **EARTH** (grn/yel) | the pump's **metal bracket** + any exposed metal / enclosure (**not** the plastic pump body) |
| relay **NC** | unused — leave empty |

- A salvaged appliance **cable + plug** supplies Live/Neutral/Earth.
- **Verify conductor colours with a meter** — don't trust them.
- DK wall plugs are unfused → add an inline **fuse holder (1 A)** on the live. (53 W pump
  draws ~0.23 A, so 1 A is ample headroom.)
- **Earth the pump's metal bracket.** Crimp the green/yellow PE to clean bare metal (scrape
  off any coating) under a screw with a star washer. Verify **plug earth pin → bracket = ~0 Ω**.
  If a live fault ever reaches the bracket, this trips the RCD instead of making it live.

## Low-voltage side — Wemos/Lolin D1 Mini ESP32

Pins are silkscreened as bare numbers. GPIO16/17 are free and boot-safe on this board
(WROOM-32, no PSRAM; neither is a strapping pin), which is why the firmware uses them.

| ESP32 pin (silkscreen) | Connects to | Notes |
|---|---|---|
| **5V** | 5V supply **+** relay `VCC` | The 5V pin carries USB 5V while flashing |
| **G** / GND | supply 0V **+** relay `GND` **+** float leg | All grounds **must** be common |
| **16** (`relay_pin`) | relay `IN` | Only signal crossing to mains; 3.3V logic |
| **17** (`float_pin`) | float switch (other leg → **G**) | Internal pull-up in firmware; no resistor |

- Do **not** power the relay coil from **3V3** — it needs 5V to pull in reliably.
- If the board has a single ground pin, join relay GND + supply return + float leg there.

### Relay drive — IMPORTANT (this module is active-LOW)

This Tongling module is **active-low** *and* its `IN` has an internal pull-up to 5V. A 3.3V
push-pull "high" from the ESP only **half-turns-off** the input transistor → it stalls at
**~0.9 A and just twitches, never latching**. The fix (already in `pump.yaml`) is to drive
GPIO16 **open-drain + inverted**:

```yaml
pin:
  number: ${relay_pin}
  inverted: true
  mode:
    output: true
    open_drain: true
```

- **OFF** → pin floats → module's own pull-up takes `IN` to a true **5V** → clean off.
- **ON** → pin pulls `IN` to **0V** → relay clicks in.

No external pull-up resistor was needed (the module has its own). If you ever swap to a
module *without* an internal pull-up, add a 4.7 k–10 k resistor from `IN` to 5V.

## Things to verify by test

1. **Relay drive:** confirmed **active-low + open-drain** (see above). Relay off at idle,
   clicks on during a dose/manual run, normal current (~0.07 A added).
2. **Float sense:** lift/lower the float, watch *Reservoir has water* in HA. Flip
   `inverted:` on the `reservoir_has_water` sensor until **ON = water present**.
