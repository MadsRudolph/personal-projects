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
        self._thread = None
        self._running = False

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
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.ser = None

    def send_command(self, cmd):
        if self.ser and self.ser.is_open:
            self.ser.write(cmd.encode())

    @property
    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    def _read_loop(self):
        while self._running and self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode("ascii", errors="ignore").strip()
                if not line:
                    continue
                msg = self.parse_line(line)
                if msg:
                    self.queue.put(msg)
            except Exception:
                continue

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
        elif line.startswith(("OK:", "ERR:", "INFO:")):
            prefix_end = line.index(":")
            return {
                "type": line[:prefix_end],
                "message": line[prefix_end + 1 :],
            }
        return None
