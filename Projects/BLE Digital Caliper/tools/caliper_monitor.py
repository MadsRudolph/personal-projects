#!/usr/bin/env python3
"""Watch the ESP32's sniffer output live, and check it against the caliper.

Run it, then move the jaws and watch the number follow the display. This is
the acceptance test for CALIPER_SNIFFER_MODE: if this tracks correctly across
the range, the shifter, the ISR edge, the inversion and the bit map are all
right, and the only thing left is BLE.

    python caliper_monitor.py                 # auto-detect the port
    python caliper_monitor.py --port COM7
    python caliper_monitor.py --seconds 60

Ctrl-C stops it and prints a summary.

WHAT TO LOOK FOR

  * the value matches the caliper display, everywhere in the range
  * "bad marker" stays at 0. That counts frames whose bit 0 was not the
    always-1 marker, which is how a frame shifted by one bit shows up. DATA
    holds for only ~60 us after the clock edge, so a late ISR does exactly
    that -- see CALIPER_CHECK_MARKER in firmware/include/config.h.
  * the frame rate. This caliper sends about 6 frames/s while the reading is
    changing and about 3/s when it is sitting still, and stops altogether
    once it powers itself down. A sudden zero is usually the caliper asleep,
    not a wiring fault -- nudge the jaws before suspecting the hardware.
"""

import argparse
import re
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("needs pyserial:  pip install pyserial")
    sys.exit(2)

FRAME = re.compile(r"raw ([01 ]+)\s+->\s+(-?[\d.]+) (mm|in)")


def find_port():
    """The USB-serial bridge on an ESP32 DevKit: CP210x, CH340 or FTDI."""
    candidates = []
    for p in list_ports.comports():
        blob = f"{p.description} {p.hwid}".lower()
        if any(k in blob for k in ("cp210", "ch340", "ch910", "ftdi",
                                   "silicon labs", "usb serial")):
            candidates.append(p.device)
    return candidates[0] if candidates else None


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default=None, help="e.g. COM7 (default: detect)")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--seconds", type=float, default=0.0,
                    help="stop after this long (default: until Ctrl-C)")
    args = ap.parse_args()

    port = args.port or find_port()
    if not port:
        print("no USB-serial port found -- pass --port COM7")
        return 2

    try:
        ser = serial.Serial(port, args.baud, timeout=0.3)
    except Exception as exc:
        print(f"could not open {port}: {exc}")
        print("PlatformIO's monitor or another terminal may still hold it.")
        return 2

    print(f"listening on {port} @ {args.baud} -- move the jaws. Ctrl-C to stop.\n")
    frames = bad = 0
    values = []
    last_report = time.time()
    recent = 0
    t0 = time.time()

    try:
        while True:
            if args.seconds and time.time() - t0 > args.seconds:
                break
            line = ser.readline()
            if not line:
                continue
            text = line.decode("utf-8", "replace").rstrip()
            m = FRAME.match(text)
            if not m:
                if text.startswith("hb:") and not frames:
                    print("  " + text)      # only useful while nothing decodes
                continue

            bits, value, unit = m.group(1).replace(" ", ""), \
                float(m.group(2)), m.group(3)
            frames += 1
            recent += 1
            values.append(value)
            if bits[0] != "1":
                bad += 1

            now = time.time()
            if now - last_report >= 0.5:
                rate = recent / (now - last_report)
                recent = 0
                last_report = now
                flag = f"   BAD MARKERS: {bad}" if bad else ""
                print(f"\r  {value:10.2f} {unit}   {rate:4.1f} frames/s   "
                      f"{frames} total{flag}   ", end="", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()

    print("\n")
    if not frames:
        print("No frames at all.")
        print("  - is the caliper awake? nudge the jaws")
        print("  - check the heartbeat line: edges=0 means nothing is reaching")
        print("    the pin, so it is the shifter or the wiring, not the decode")
        print("  - tools/caliper_shifter_check.py tests the shifter on its own")
        return 1

    print(f"{frames} frames, {bad} with a bad marker bit "
          f"({100.0*bad/frames:.1f}%)")
    print(f"range {min(values):.2f} .. {max(values):.2f}, "
          f"{len(set(values))} distinct values")
    if len(set(values)) == 1:
        print("Only one value seen -- the jaws did not move, so this does not")
        print("yet prove it tracks. Run it again and sweep the full range.")
    elif bad == 0:
        print("Tracked across a range with no shifted frames. That is the "
              "sniffer stage passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
