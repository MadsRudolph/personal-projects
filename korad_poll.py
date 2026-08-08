#!/usr/bin/env python3
"""Poll a Korad-protocol PSU (KD3005P / maybe KD3005D) over a USB-TTL dongle.

Korad serial protocol: 8N1, ASCII commands, NO line terminator, no checksum,
request->response only (the PSU never speaks first). Default tries 115200 then
9600 because the KD3005**D** UART (per profi-max KORAD_WiFi_USB_module) runs at
115200 while the official KD3005P manual says 9600.

Quirk: some firmware answers *IDN? only ONCE until power-cycled. If *IDN? is
silent, power-cycle the PSU before retrying.

Wiring: dongle GND -> J9 GND, dongle RX -> Korad TX, dongle TX -> Korad RX.
Do NOT connect the dongle VCC. Dongle logic level must match the header
(3.3 V unless you measured 5 V on the TX/RX pins).

  python korad_poll.py --list                 # enumerate COM ports
  python korad_poll.py --port COM7            # *IDN? at 115200 then 9600
  python korad_poll.py --port COM7 --probe    # full query sequence
  python korad_poll.py --port COM7 --baud 9600 --cmd "VOUT1?"
"""

import argparse
import sys
import time

import serial
import serial.tools.list_ports as list_ports


def enumerate_ports():
    ports = list(list_ports.comports())
    if not ports:
        print("no COM ports found")
        return
    for p in ports:
        print(f"  {p.device:8s} {p.description}")


def poll(port, baud, cmd, read_s=1.0):
    """Send one ASCII command, return raw response bytes."""
    with serial.Serial(port, baud, bytesize=8, parity="N", stopbits=1,
                        timeout=0.2) as s:
        time.sleep(0.1)
        s.reset_input_buffer()
        s.reset_output_buffer()
        s.write(cmd.encode("ascii"))
        s.flush()
        time.sleep(0.25)
        buf = bytearray()
        t0 = time.time()
        while time.time() - t0 < read_s:
            n = s.in_waiting
            if n:
                buf += s.read(n)
                t0 = time.time()      # keep reading while bytes flow
            else:
                time.sleep(0.02)
        return bytes(buf)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="list COM ports and exit")
    ap.add_argument("--port", help="COM port of the USB-TTL dongle")
    ap.add_argument("--baud", type=int, help="baud (default: try 115200 then 9600)")
    ap.add_argument("--cmd", default="*IDN?", help="single command to send")
    ap.add_argument("--probe", action="store_true",
                    help="send a sequence of query commands")
    args = ap.parse_args()

    if args.list or not args.port:
        enumerate_ports()
        if not args.port:
            return 0

    bauds = [args.baud] if args.baud else [115200, 9600]
    if args.probe:
        cmds = ["*IDN?", "VOUT1?", "IOUT1?", "VSET1?", "ISET1?", "STATUS?"]
    else:
        cmds = [args.cmd]

    any_reply = False
    for b in bauds:
        print(f"\n=== {args.port} @ {b} 8N1 ===")
        for c in cmds:
            try:
                r = poll(args.port, b, c)
            except Exception as e:
                print(f"  {c!r}: ERROR {e}")
                return 2
            txt = r.decode("ascii", "replace")
            flag = "  <-- reply" if r else ""
            if r:
                any_reply = True
            print(f"  {c!r:10} -> {len(r):2d} bytes | ascii={txt!r} "
                  f"| hex={r.hex(' ')}{flag}")
            time.sleep(0.15)
        if any_reply:
            print("  (got data at this baud)")

    if not any_reply:
        print("\nNo reply at any baud. Try: swap dongle TX/RX, power-cycle the PSU "
              "(for the *IDN?-once quirk), confirm dongle logic level matches the header.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
