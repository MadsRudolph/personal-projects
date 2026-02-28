import queue
import threading

import serial
import serial.tools.list_ports

from datetime import datetime
from tag_info import Tag


class SerialHandler:
    def __init__(self):
        self.ser = None
        self.queue = queue.Queue()
        self.raw_queue = queue.Queue()
        self._thread = None
        self._running = False
        self._lock = threading.Lock()

    @staticmethod
    def list_ports():
        return [p.device for p in serial.tools.list_ports.comports()]

    def connect(self, port, baud=9600):
        self.ser = serial.Serial(port, baud, timeout=1)
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def disconnect(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        with self._lock:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.ser = None

    def send_command(self, cmd):
        with self._lock:
            if self.ser and self.ser.is_open:
                self.ser.write(cmd.encode())

    @property
    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    def _read_loop(self):
        while self._running:
            try:
                with self._lock:
                    s = self.ser
                if not s or not s.is_open:
                    break
                line = s.readline().decode("ascii", errors="ignore").strip()
                if not line:
                    continue
                self.raw_queue.put(line)
                msg = self.parse_line(line)
                if msg:
                    self.queue.put(msg)
            except (OSError, serial.SerialException):
                break
            except Exception:
                continue

    def send_load_block(self, block, hex_data):
        """Send a LOAD:<block_hex>:<data_hex> line for writing."""
        cmd = f"LOAD:{block:02X}:{hex_data}\n"
        with self._lock:
            if self.ser and self.ser.is_open:
                self.ser.write(cmd.encode())

    @staticmethod
    def parse_line(line):
        if not line:
            return None
        if line.startswith("TAG:"):
            parts = line[4:].split(":")
            if len(parts) == 4:
                return Tag(
                    atqa=parts[0],
                    uid=parts[1],
                    sak=int(parts[2], 16),
                    uid_len=int(parts[3]),
                    timestamp=datetime.now(),
                )
        elif line.startswith("DATA:"):
            parts = line[5:].split(":")
            if len(parts) == 2 and len(parts[1]) == 32:
                return {
                    "type": "DATA",
                    "block": int(parts[0], 16),
                    "data": parts[1],
                }
        elif line.startswith("DARK:"):
            parts = line[5:].split(":", 1)
            subtype = parts[0]
            if subtype == "UID" and len(parts) > 1:
                return {"type": "DARK", "subtype": "UID", "uid": parts[1]}
            elif subtype == "NT" and len(parts) > 1:
                return {"type": "DARK", "subtype": "NT", "nt": parts[1]}
            elif subtype == "NACK" and len(parts) > 1:
                return {"type": "DARK", "subtype": "NACK", "nr_ar": parts[1]}
            elif subtype == "TIMEOUT":
                return {"type": "DARK", "subtype": "TIMEOUT"}
            elif subtype == "DONE":
                return {"type": "DARK", "subtype": "DONE"}
            elif subtype == "ERR" and len(parts) > 1:
                return {"type": "DARK", "subtype": "ERR", "message": parts[1]}
        elif line.startswith("NESTED:"):
            parts = line[7:].split(":", 2)
            subtype = parts[0]
            if subtype == "NT" and len(parts) >= 2:
                nt_parts = parts[1].split(":")
                if len(nt_parts) == 2:
                    return {
                        "type": "NESTED",
                        "subtype": "NT",
                        "nt_known": nt_parts[0],
                        "nt_target": nt_parts[1],
                    }
                # Handle case: NESTED:NT:aabb:ccdd (3 parts after initial split)
                elif len(parts) == 3:
                    return {
                        "type": "NESTED",
                        "subtype": "NT",
                        "nt_known": parts[1],
                        "nt_target": parts[2],
                    }
            elif subtype == "FAIL" and len(parts) > 1:
                return {"type": "NESTED", "subtype": "FAIL", "reason": parts[1]}
            elif subtype == "DONE":
                return {"type": "NESTED", "subtype": "DONE"}
        elif line.startswith(("OK:", "ERR:", "INFO:")):
            prefix_end = line.index(":")
            return {
                "type": line[:prefix_end],
                "message": line[prefix_end + 1:],
            }
        return None
