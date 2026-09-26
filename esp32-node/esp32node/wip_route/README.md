# NOT A USABLE BOARD -- routing work in progress (2026-09-25)

FreeRouting 2.4.1 (headless) result on the placement from ../place_pcb.py, with the
hand-drawn J1 escape kept (PLACE_ROUTE_KEEP_LOCKED=1).

- 20 missing links, 13 split nets (+3V3 in 8 pieces, IO0, +5V, EN, IO15, IO2, IO23,
  RXD0, TXD0, USB_D+/-, CC1)
- 1 real short: a GND track from J1's right shell pad crosses the locked VBUS stub
  (FreeRouting did not treat the imported locked stubs as obstacles)

Kept only so the next session can see where the router gives up. See ../HANDOFF.md.
