import time

import customtkinter as ctk
from datetime import datetime
from tkinter import filedialog, messagebox

from serial_handler import SerialHandler
from tag_info import Tag
from card_data import CardData
from attack import AttackOrchestrator


class OperationGuard:
    def __init__(self):
        self._operation = None
        self._op_start_time = None

    @property
    def is_busy(self):
        return self._operation is not None

    @property
    def operation(self):
        return self._operation

    def start(self, op_name):
        if self._operation is not None:
            return False
        self._operation = op_name
        self._op_start_time = time.monotonic()
        return True

    def finish(self):
        self._operation = None
        self._op_start_time = None

    def check_timeout(self, elapsed_seconds=None, timeout=30):
        if not self._operation:
            return False
        if elapsed_seconds is None:
            elapsed_seconds = time.monotonic() - self._op_start_time
        if elapsed_seconds >= timeout:
            self._operation = None
            self._op_start_time = None
            return True
        return False


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("RFID Tag Analyzer Pro")
        self.geometry("1100x800")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Data & Handlers
        self.serial = SerialHandler()
        self.card_data = CardData()
        self._write_pending = []
        self._writing = False
        self._guard = OperationGuard()
        self.attack = AttackOrchestrator(self.serial)
        self._last_tag_uid = None

        # UI State
        self.current_page = None
        self.nav_buttons = {}

        self._setup_grid()
        self._build_sidebar()
        self._build_main_frames()
        self._show_page("dashboard")
        
        self._poll_serial()

    def _setup_grid(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=4)  # Page content area
        self.grid_rowconfigure(1, weight=1)  # Persistent log area

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1)

        logo = ctk.CTkLabel(
            self.sidebar, text="RFID ANALYZER", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        logo.grid(row=0, column=0, padx=20, pady=(20, 10))

        pages = [
            ("dashboard", "Dashboard", "house"),
            ("rw", "Read / Write", "pen-to-square"),
            ("attacks", "Attacks", "bolt"),
        ]

        for i, (id, label, icon) in enumerate(pages):
            btn = ctk.CTkButton(
                self.sidebar, text=label, corner_radius=0, height=40,
                border_spacing=10, fg_color="transparent", text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"), anchor="w",
                command=lambda p=id: self._show_page(p)
            )
            btn.grid(row=i+1, column=0, sticky="ew")
            self.nav_buttons[id] = btn

        # Connection Bar (now simple in sidebar)
        conn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        conn_frame.grid(row=6, column=0, padx=10, pady=10, sticky="ew")

        self.port_var = ctk.StringVar()
        self.port_menu = ctk.CTkOptionMenu(
            conn_frame, variable=self.port_var, values=[""], height=30
        )
        self.port_menu.pack(fill="x", pady=5)

        btn_row = ctk.CTkFrame(conn_frame, fg_color="transparent")
        btn_row.pack(fill="x")

        ctk.CTkButton(
            btn_row, text="Refresh", width=80, height=28, command=self._refresh_ports
        ).pack(side="left", padx=(0, 5))

        self.connect_btn = ctk.CTkButton(
            btn_row, text="Connect", width=80, height=28, command=self._toggle_connect
        )
        self.connect_btn.pack(side="left")

        ctk.CTkButton(
            conn_frame, text="HW Reset", fg_color="#da3633", hover_color="#b62324",
            height=28, command=self._reset_device
        ).pack(fill="x", pady=(5, 0))

        self.status_label = ctk.CTkLabel(conn_frame, text="Disconnected", text_color="#da3633", font=ctk.CTkFont(size=11))
        self.status_label.pack(pady=(5, 0))

        # Global STOP button - very prominent
        self.sidebar_stop_btn = ctk.CTkButton(
            self.sidebar, text="GLOBAL STOP", fg_color="#da3633", hover_color="#b62324",
            height=50, font=ctk.CTkFont(size=14, weight="bold"),
            command=self._global_stop
        )
        self.sidebar_stop_btn.grid(row=7, column=0, padx=10, pady=(20, 20), sticky="ew")

        self._refresh_ports()

    def _build_main_frames(self):
        self.pages = {}
        for p in ["dashboard", "rw", "attacks"]:
            frame = ctk.CTkFrame(self, fg_color="transparent")
            self.pages[p] = frame

        self._build_dashboard_page()
        self._build_rw_page()
        self._build_attacks_page()
        self._build_persistent_log()

    def _show_page(self, name):
        if self.current_page:
            self.pages[self.current_page].grid_forget()
            self.nav_buttons[self.current_page].configure(fg_color="transparent")

        self.pages[name].grid(row=0, column=1, sticky="nsew", padx=20, pady=(20, 10))
        self.nav_buttons[name].configure(fg_color=("gray75", "gray25"))
        self.current_page = name

    def _build_persistent_log(self):
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid(row=1, column=1, sticky="nsew", padx=20, pady=(0, 20))
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.log_frame, fg_color="transparent", height=30)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 0))

        ctk.CTkLabel(header, text="System & Debug Logs", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="Clear Logs", width=80, height=22, command=self._clear_system_log).pack(side="right")

        self.sys_log = ctk.CTkTextbox(self.log_frame, font=ctk.CTkFont(family="Consolas", size=11), height=150)
        self.sys_log.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.sys_log.configure(state="disabled")

    def _build_dashboard_page(self):
        p = self.pages["dashboard"]
        p.grid_columnconfigure(0, weight=1)

        # Tag Card
        self.card = ctk.CTkFrame(p, border_width=2, border_color="#1f6feb", corner_radius=15)
        self.card.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        self.uid_label = ctk.CTkLabel(
            self.card, text="No tag scanned",
            font=ctk.CTkFont(family="Consolas", size=32, weight="bold"),
        )
        self.uid_label.pack(pady=(25, 10))

        info_row = ctk.CTkFrame(self.card, fg_color="transparent")
        info_row.pack(pady=10)

        self.atqa_label = ctk.CTkLabel(info_row, text="ATQA: --", font=ctk.CTkFont(size=14))
        self.atqa_label.pack(side="left", padx=30)

        self.sak_label = ctk.CTkLabel(info_row, text="SAK: --", font=ctk.CTkFont(size=14))
        self.sak_label.pack(side="left", padx=30)

        self.chip_label = ctk.CTkLabel(self.card, text="", font=ctk.CTkFont(size=18))
        self.chip_label.pack(pady=5)

        self.clone_label = ctk.CTkLabel(self.card, text="", font=ctk.CTkFont(size=16, weight="bold"))
        self.clone_label.pack(pady=(0, 25))

        # Scan Controls
        ctrls = ctk.CTkFrame(p)
        ctrls.grid(row=1, column=0, sticky="ew", pady=10, padx=2)
        
        ctk.CTkLabel(ctrls, text="Scan Controls", font=ctk.CTkFont(weight="bold")).pack(pady=10)

        btns = ctk.CTkFrame(ctrls, fg_color="transparent")
        btns.pack(pady=(0, 15))

        self.scan_btn = ctk.CTkButton(
            btns, text="Start Continuous Scan", fg_color="#2ea043", hover_color="#238636",
            width=180, height=40, command=lambda: self._send("S")
        )
        self.scan_btn.pack(side="left", padx=10)

        self.single_btn = ctk.CTkButton(
            btns, text="Single Scan", width=120, height=40, command=lambda: self._send("O")
        )
        self.single_btn.pack(side="left", padx=10)

        self.stop_btn = ctk.CTkButton(
            btns, text="Stop", fg_color="#da3633", hover_color="#b62324",
            width=100, height=40, command=self._global_stop
        )
        self.stop_btn.pack(side="left", padx=10)

        # Recent Scan Log (Mini version)
        ctk.CTkLabel(p, text="Recent Activity", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="w", pady=(10, 5))
        
        self.log_text = ctk.CTkTextbox(p, font=ctk.CTkFont(family="Consolas", size=12), height=200)
        self.log_text.grid(row=3, column=0, sticky="nsew")
        header = f"{'Time':<10} | {'UID':<22} | {'Chip Type':<25} | SAK\n"
        self.log_text.insert("end", header)
        self.log_text.insert("end", "-" * 70 + "\n")
        self.log_text.configure(state="disabled")

    def _build_rw_page(self):
        p = self.pages["rw"]
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(2, weight=1)

        # Operational Controls
        ctrls = ctk.CTkFrame(p)
        ctrls.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        top_row = ctk.CTkFrame(ctrls, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=10)

        self.read_btn = ctk.CTkButton(
            top_row, text="Read Full Dump", fg_color="#1f6feb", hover_color="#1958c7",
            width=150, height=35, command=self._read_card
        )
        self.read_btn.pack(side="left", padx=5)

        self.write_btn = ctk.CTkButton(
            top_row, text="Write to Card", fg_color="#d29922", hover_color="#b07d1a",
            width=150, height=35, command=self._write_card
        )
        self.write_btn.pack(side="left", padx=5)

        self.blk0_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(top_row, text="Lock Block 0", variable=self.blk0_var).pack(side="left", padx=10)

        ctk.CTkButton(
            top_row, text="Format (Erase)", fg_color="#da3633", hover_color="#b62324",
            width=130, height=35, command=self._format_card
        ).pack(side="right", padx=5)

        mid_row = ctk.CTkFrame(ctrls, fg_color="transparent")
        mid_row.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(mid_row, text="Open .bin", width=100, command=self._load_dump).pack(side="left", padx=5)
        ctk.CTkButton(mid_row, text="Save .bin", width=100, command=self._save_dump).pack(side="left", padx=5)

        self.progress_bar = ctk.CTkProgressBar(mid_row, width=300)
        self.progress_bar.pack(side="right", padx=10)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(mid_row, text="Idle", font=ctk.CTkFont(size=12, slant="italic"))
        self.progress_label.pack(side="right", padx=5)

        # Hex Viewer
        self.hex_text = ctk.CTkTextbox(p, font=ctk.CTkFont(family="Consolas", size=11))
        self.hex_text.grid(row=2, column=0, sticky="nsew", pady=10)
        self._refresh_hex_viewer()

    def _build_attacks_page(self):
        p = self.pages["attacks"]
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(4, weight=1)

        # ── Snowball Attack Section ──
        snow_frame = ctk.CTkFrame(p, fg_color="#1a1a2e", border_width=2,
                                   border_color="#0d9488", corner_radius=10)
        snow_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10), padx=2)
        snow_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            snow_frame, text="Snowball Attack",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, pady=(10, 5), padx=10, sticky="w")

        ctk.CTkLabel(
            snow_frame,
            text="Autonomously crack all sectors using cascading key recovery",
            text_color="gray60",
        ).grid(row=1, column=0, padx=10, sticky="w")

        # Sector Map Grid (4 cols x 4 rows = 16 sectors)
        self._sector_frames = {}
        self._sector_labels = {}
        self._sector_key_labels = {}
        map_frame = ctk.CTkFrame(snow_frame, fg_color="transparent")
        map_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        for col in range(4):
            map_frame.grid_columnconfigure(col, weight=1)

        for sector in range(16):
            row_idx = sector // 4
            col_idx = sector % 4
            sf = ctk.CTkFrame(map_frame, width=100, height=60,
                              fg_color="#2b2b2b", corner_radius=8,
                              border_width=1, border_color="#444444")
            sf.grid(row=row_idx, column=col_idx, padx=4, pady=4, sticky="nsew")
            sf.grid_propagate(False)

            lbl = ctk.CTkLabel(sf, text=f"S{sector:02d}",
                               font=ctk.CTkFont(size=13, weight="bold"))
            lbl.place(relx=0.5, rely=0.3, anchor="center")

            key_lbl = ctk.CTkLabel(sf, text="??????",
                                   font=ctk.CTkFont(family="Consolas", size=9),
                                   text_color="gray50")
            key_lbl.place(relx=0.5, rely=0.7, anchor="center")

            self._sector_frames[sector] = sf
            self._sector_labels[sector] = lbl
            self._sector_key_labels[sector] = key_lbl

        # Stats row
        stats_frame = ctk.CTkFrame(snow_frame, fg_color="transparent")
        stats_frame.grid(row=3, column=0, padx=10, pady=(0, 5), sticky="ew")

        self._snow_status_label = ctk.CTkLabel(
            stats_frame, text="Ready", font=ctk.CTkFont(size=12))
        self._snow_status_label.pack(side="left", padx=10)

        self._snow_progress_label = ctk.CTkLabel(
            stats_frame, text="0/16 sectors",
            font=ctk.CTkFont(size=12, weight="bold"))
        self._snow_progress_label.pack(side="right", padx=10)

        self._snow_time_label = ctk.CTkLabel(
            stats_frame, text="", font=ctk.CTkFont(size=11),
            text_color="gray60")
        self._snow_time_label.pack(side="right", padx=10)

        # Buttons row
        btn_frame = ctk.CTkFrame(snow_frame, fg_color="transparent")
        btn_frame.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.snowball_btn = ctk.CTkButton(
            btn_frame, text="Start Snowball Attack",
            fg_color="#0d9488", hover_color="#0f766e",
            width=220, height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_snowball,
        )
        self.snowball_btn.pack(side="left", padx=5)

        self.snow_stop_btn = ctk.CTkButton(
            btn_frame, text="Abort", fg_color="#da3633",
            hover_color="#b62324", width=100, height=45,
            command=self._stop_snowball,
        )
        self.snow_stop_btn.pack(side="left", padx=5)

        # ── Manual Attacks Section ──
        manual_frame = ctk.CTkFrame(p, fg_color="#2b2b2b")
        manual_frame.grid(row=1, column=0, sticky="ew", pady=10, padx=2)

        ctk.CTkLabel(
            manual_frame, text="Manual Attacks",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(10, 5))

        man_btns = ctk.CTkFrame(manual_frame, fg_color="transparent")
        man_btns.pack(pady=(0, 10))

        self.crack_btn = ctk.CTkButton(
            man_btns, text="Darkside Attack", fg_color="#8b5cf6",
            hover_color="#7c3aed", width=160, height=35,
            command=self._start_crack,
        )
        self.crack_btn.pack(side="left", padx=5)

        nested_row = ctk.CTkFrame(man_btns, fg_color="transparent")
        nested_row.pack(side="left", padx=10)
        ctk.CTkLabel(nested_row, text="Sector:").pack(side="left", padx=(0, 4))
        self._nested_sector_var = ctk.StringVar(value="5")
        self._nested_sector_menu = ctk.CTkOptionMenu(
            nested_row, variable=self._nested_sector_var,
            values=[str(s) for s in range(5, 16)],
            width=60, height=30,
        )
        self._nested_sector_menu.pack(side="left", padx=(0, 4))
        self.nested_btn = ctk.CTkButton(
            nested_row, text="Nested Attack", fg_color="#0d9488",
            hover_color="#0f766e", width=140, height=35,
            command=self._start_nested,
        )
        self.nested_btn.pack(side="left")

        self.attack_label = ctk.CTkLabel(p, text="", font=ctk.CTkFont(size=14))
        self.attack_label.grid(row=2, column=0, pady=5)

        # ── Attack Event Log ──
        ctk.CTkLabel(p, text="Attack Log",
                     font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=3, column=0, sticky="w", pady=(5, 2))
        self.attack_log = ctk.CTkTextbox(
            p, font=ctk.CTkFont(family="Consolas", size=11), height=150)
        self.attack_log.grid(row=4, column=0, sticky="nsew")
        self.attack_log.configure(state="disabled")

    def _start_crack(self):
        if not self.serial.is_connected:
            self._log("Crack failed: not connected", "ERROR")
            return
        if not self._guard.start("cracking"):
            self._log("Operation in progress, please wait", "WARN")
            return
        self.attack_label.configure(text="Darkside attack...")
        self._log("Starting darkside attack on sector 0")
        self.attack.start_darkside(0)

    def _start_nested(self):
        if not self.serial.is_connected:
            self._log("Nested attack failed: not connected", "ERROR")
            return
        if not self._last_tag_uid:
            self._log("Nested attack failed: scan a tag first", "ERROR")
            return
        if not self._guard.start("nested_attack"):
            self._log("Operation in progress, please wait", "WARN")
            return
        target = int(self._nested_sector_var.get())
        uid_int = int(self._last_tag_uid, 16)
        self.attack._uid = uid_int
        self.attack_label.configure(text="Nested: calibrating...")
        self._log(f"Starting nested attack on sector {target} (UID={self._last_tag_uid})")
        self.attack.start_nested_attack(
            known_sector=0, target_sector=target,
            known_key=bytes.fromhex("FFFFFFFFFFFF"),
        )

    def _start_snowball(self):
        if not self.serial.is_connected:
            self._log("Snowball failed: not connected", "ERROR")
            return
        if not self._last_tag_uid:
            self._log("Snowball failed: scan a tag first", "ERROR")
            return
        if not self._guard.start("snowball"):
            self._log("Operation in progress, please wait", "WARN")
            return

        from snowball import SnowballOrchestrator
        uid_int = int(self._last_tag_uid, 16)
        self.snowball = SnowballOrchestrator(self.serial, uid=uid_int)
        self.snowball.start(
            seed_sector=0,
            seed_key=bytes.fromhex("FFFFFFFFFFFF"),
            seed_key_type="B",
        )
        self._log(f"Snowball attack started (UID={self._last_tag_uid})")
        self._snow_status_label.configure(text="Starting...")
        # Reset sector map
        for s in range(16):
            self._sector_frames[s].configure(border_color="#444444",
                                              fg_color="#2b2b2b")
            self._sector_key_labels[s].configure(text="??????",
                                                  text_color="gray50")
        # Mark sector 0 as known
        self._sector_frames[0].configure(fg_color="#0d3320",
                                          border_color="#2ea043")
        self._sector_key_labels[0].configure(text="FFFFFFFFFFFF",
                                              text_color="#2ea043")

    def _stop_snowball(self):
        if hasattr(self, 'snowball') and self.snowball.state not in ("idle", "done"):
            self.snowball.stop()
            self._guard.finish()
            self._snow_status_label.configure(text="Stopped")
            self._log("Snowball attack stopped by user", "WARN")

    def _process_snowball_events(self):
        """Process events from the snowball orchestrator and update GUI."""
        while not self.snowball.result_queue.empty():
            result = self.snowball.result_queue.get_nowait()
            event = result.get("event", "")

            if event == "snowball_started":
                n = result["total_unknown"]
                self._snow_progress_label.configure(text=f"1/{n + 1} sectors")
                self._attack_log(f"Snowball started: {n} sectors to crack")

            elif event == "sector_calibrating":
                src, tgt = result["source"], result["target"]
                self._snow_status_label.configure(
                    text=f"Calibrating (S{src:02d} -> S{tgt:02d})")
                self._sector_frames[tgt].configure(
                    border_color="#d29922", fg_color="#2b2200")
                self._attack_log(f"Calibrating: S{src:02d} -> S{tgt:02d}")

            elif event == "sector_calibrated":
                d = result["distance"]
                self._attack_log(
                    f"PRNG distance: {d} ({result['samples']} samples)")

            elif event == "sector_collecting":
                tgt = result["target"]
                n = result["nonce_count"]
                self._snow_status_label.configure(
                    text=f"Collecting S{tgt:02d}: {n} nonces")
                self._sector_frames[tgt].configure(
                    border_color="#d29922", fg_color="#2b2200")

            elif event == "sector_recovering":
                tgt = result["target"]
                self._snow_status_label.configure(
                    text=f"Recovering S{tgt:02d}...")
                self._attack_log(
                    f"Recovering S{tgt:02d} ({result['nonce_count']} nonces)")

            elif event == "sector_cracked":
                s = result["sector"]
                key = result["key"]
                t = result["time_taken"]
                cracked = self.snowball.stats.sectors_cracked
                self._sector_frames[s].configure(
                    fg_color="#0d3320", border_color="#2ea043")
                self._sector_key_labels[s].configure(
                    text=key, text_color="#2ea043")
                self._snow_progress_label.configure(
                    text=f"{cracked + 1}/16 sectors")
                self._snow_status_label.configure(text=f"Cracked S{s:02d}!")
                self._attack_log(f"CRACKED S{s:02d}: {key} ({t:.1f}s)")

            elif event == "sector_failed":
                s = result["sector"]
                reason = result["reason"]
                self._sector_frames[s].configure(
                    fg_color="#3b1111", border_color="#da3633")
                self._sector_key_labels[s].configure(
                    text="FAILED", text_color="#da3633")
                self._attack_log(f"FAILED S{s:02d}: {reason}")

            elif event == "snowball_complete":
                self._guard.finish()
                n = result["total_cracked"]
                t = result["total_time"]
                self._snow_status_label.configure(text="Complete!")
                self._snow_progress_label.configure(
                    text=f"{n + 1}/16 sectors")
                elapsed = f"{t:.0f}s" if t < 60 else f"{t/60:.1f}m"
                self._snow_time_label.configure(text=f"Total: {elapsed}")
                self._attack_log(f"COMPLETE: {n} sectors cracked in {elapsed}")
                self._log(f"Snowball complete: {n} sectors, {elapsed}")

            elif event == "snowball_stopped":
                self._guard.finish()
                self._attack_log("Snowball stopped by user")

    def _attack_log(self, text):
        """Write to the attack event log."""
        ts = datetime.now().strftime("%H:%M:%S")
        self.attack_log.configure(state="normal")
        self.attack_log.insert("end", f"[{ts}] {text}\n")
        self.attack_log.see("end")
        self.attack_log.configure(state="disabled")

    def _global_stop(self):
        """Global halt for all active processes."""
        # Stop scanning
        self._send("P")
        # Stop snowball if active
        if hasattr(self, 'snowball') and self.snowball.state not in ("idle", "done"):
            self.snowball.stop()
            self._snow_status_label.configure(text="Stopped")
        # Stop attacks
        if self.attack.state != "idle":
            self.attack.stop()
            self.attack_label.configure(text="Stopped")
        if self._guard.is_busy:
            self._guard.finish()
            self._log("Global STOP triggered: halting all processes", "WARN")
        else:
            self._log("Stop signal sent", "INFO")

        self.progress_label.configure(text="Stopped")
        self.progress_bar.set(0)

    def _stop_crack(self):
        if self.attack.state != "idle":
            self.attack.stop()
            self._guard.finish()
            self.attack_label.configure(text="Attack stopped")
            self._log("Attack stopped by user", "WARN")


    def _log(self, text, level="INFO"):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        tag = {"INFO": "INFO ", "WARN": "WARN ", "ERROR": "ERROR", "TX": " TX  ", "RX": " RX  "}
        prefix = tag.get(level, level.ljust(5))
        line = f"[{ts}] {prefix}  {text}\n"
        self.sys_log.configure(state="normal")
        self.sys_log.insert("end", line)
        self.sys_log.see("end")
        self.sys_log.configure(state="disabled")

    def _clear_system_log(self):
        self.sys_log.configure(state="normal")
        self.sys_log.delete("1.0", "end")
        self.sys_log.configure(state="disabled")

    def _refresh_hex_viewer(self):
        self.hex_text.configure(state="normal")
        self.hex_text.delete("1.0", "end")

        if not self.card_data.has_data:
            self.hex_text.insert("end", "No card data. Use 'Read Card' or 'Load Dump'.\n")
        else:
            for sector in range(16):
                self.hex_text.insert("end", f"--- Sector {sector:2d} ---\n")
                for b in range(4):
                    block = sector * 4 + b
                    data = self.card_data.get_block(block)
                    if data:
                        spaced = " ".join(data[i:i+2] for i in range(0, 32, 2))
                        label = "T" if self.card_data.is_sector_trailer(block) else " "
                        self.hex_text.insert(
                            "end", f"  Blk {block:2d} [{label}]: {spaced}\n"
                        )
                    else:
                        self.hex_text.insert(
                            "end", f"  Blk {block:2d}:      -- no data --\n"
                        )

        self.hex_text.configure(state="disabled")

    def _refresh_ports(self):
        ports = SerialHandler.list_ports()
        values = ports if ports else ["No ports found"]
        self.port_menu.configure(values=values)
        if ports:
            self.port_var.set(ports[0])

    def _toggle_connect(self):
        if self.serial.is_connected:
            self.serial.disconnect()
            self.connect_btn.configure(text="Connect")
            self.status_label.configure(text="Disconnected", text_color="red")
            self._log("Disconnected")
        else:
            port = self.port_var.get()
            if not port or port == "No ports found":
                return
            try:
                self.serial.connect(port)
                self.connect_btn.configure(text="Disconnect")
                self.status_label.configure(
                    text=f"Connected: {port}", text_color="#2ea043"
                )
                self._log(f"Connected to {port}")
            except Exception as e:
                self.status_label.configure(
                    text=f"Error: {e}", text_color="red"
                )
                self._log(f"Connection failed: {e}", "ERROR")

    def _reset_device(self):
        """Toggle DTR to hardware-reset the ATmega328P."""
        if not self.serial.is_connected:
            return
        import time
        self.serial.ser.dtr = False
        time.sleep(0.1)
        self.serial.ser.dtr = True
        self._write_pending = []
        self._writing = False
        self._guard.finish()
        self.attack.stop()
        if hasattr(self, 'snowball') and self.snowball.state not in ("idle", "done"):
            self.snowball.state = "idle"
        self.attack_label.configure(text="")
        self.progress_label.configure(text="Reset!")
        # Drain both queues
        while not self.serial.queue.empty():
            self.serial.queue.get_nowait()
        while not self.serial.raw_queue.empty():
            self.serial.raw_queue.get_nowait()
        self._log("Device reset (DTR toggle)", "WARN")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        header = f"{'Time':<10} | {'UID':<22} | {'Chip Type':<30} | SAK\n"
        self.log_text.insert("end", header)
        self.log_text.insert("end", "-" * 78 + "\n")
        self.log_text.configure(state="disabled")

    def _send(self, cmd):
        self.serial.send_command(cmd)
        self._log(f"Sent: {cmd!r}", "TX")

    def _read_card(self):
        if not self.serial.is_connected:
            self._log("Read card failed: not connected", "ERROR")
            return
        if not self._guard.start("reading"):
            self._log("Operation in progress, please wait", "WARN")
            return
        self.card_data.clear()
        self.progress_label.configure(text="Reading...")
        self._log("Starting card read (full dump)")
        self._send("R")

    def _write_card(self):
        if not self.serial.is_connected:
            self._log("Write card failed: not connected", "ERROR")
            return
        if not self.card_data.has_data:
            self._log("Write card failed: no card data loaded", "ERROR")
            return
        if not self._guard.start("writing"):
            self._log("Operation in progress, please wait", "WARN")
            return
        self._write_pending = self.card_data.blocks_for_write(
            allow_block0=self.blk0_var.get()
        )
        self._writing = True
        blk0 = " (including block 0)" if self.blk0_var.get() else ""
        self._log(f"Starting card write: {len(self._write_pending)} blocks{blk0}")
        self.progress_label.configure(text="Waiting for card...")
        cmd = "B" if self.blk0_var.get() else "W"
        self._send(cmd)

    def _format_card(self):
        if not self.serial.is_connected:
            self._log("Format failed: not connected", "ERROR")
            return
        confirm = messagebox.askyesno(
            "Format Card",
            "This will erase ALL data and reset all keys to factory defaults.\n\n"
            "This cannot be undone. Proceed?",
            icon="warning",
        )
        if not confirm:
            self._log("Format cancelled by user")
            return
        if not self._guard.start("formatting"):
            self._log("Operation in progress, please wait", "WARN")
            return
        self.progress_label.configure(text="Formatting...")
        self._log("Starting card format (erase to factory defaults)")
        self._send("F")

    def _save_dump(self):
        if not self.card_data.has_data:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".bin",
            filetypes=[("Binary dump", "*.bin"), ("All files", "*.*")],
        )
        if path:
            self.card_data.save_bin(path)
            self.progress_label.configure(text="Saved!")
            self._log(f"Dump saved to {path}")

    def _load_dump(self):
        path = filedialog.askopenfilename(
            filetypes=[("Binary dump", "*.bin"), ("All files", "*.*")],
        )
        if path:
            self.card_data.load_bin(path)
            self._refresh_hex_viewer()
            self.progress_label.configure(text=f"Loaded {self.card_data.block_count} blocks")
            self._log(f"Dump loaded from {path} ({self.card_data.block_count} blocks)")

    def _poll_serial(self):
        # Log raw serial lines
        while not self.serial.raw_queue.empty():
            raw = self.serial.raw_queue.get_nowait()
            self._log(raw, "RX")

        while not self.serial.queue.empty():
            msg = self.serial.queue.get_nowait()
            if isinstance(msg, Tag):
                self._update_tag_display(msg)
                self._add_log_entry(msg)
            elif isinstance(msg, dict):
                # Route to snowball orchestrator if active
                if (hasattr(self, 'snowball') and
                        self.snowball.state not in ("idle", "done") and
                        msg.get("type") in ("NA", "NP", "NH", "NX", "OK")):
                    self.snowball.feed(msg)
                    self._process_snowball_events()
                    if msg.get("type") in ("NA", "NP", "NH", "NX"):
                        continue  # consumed by snowball
                    # OK messages may also need default handling below

                if msg.get("type") in ("DARK", "NESTED"):
                    self.attack.feed(msg)
                    while not self.attack.result_queue.empty():
                        result = self.attack.result_queue.get_nowait()
                        event = result.get("event", "")
                        if event == "dark_uid":
                            self._log(f"Darkside: card UID={result['uid']}")
                        elif event == "dark_nack":
                            self.attack_label.configure(
                                text=f"Darkside: {result['count']} NACKs"
                            )
                        elif event == "dark_timeout":
                            self._log("Darkside: timeout (retrying)")
                        elif event == "dark_complete":
                            self._guard.finish()
                            n = result["nack_count"]
                            keys = result["candidates"]
                            if keys:
                                self.attack_label.configure(
                                    text=f"Found {len(keys)} key candidate(s)"
                                )
                                self._log(f"Darkside complete: {n} NACKs -> {len(keys)} candidates: {', '.join(keys)}")
                            else:
                                self.attack_label.configure(
                                    text=f"No keys found ({n} NACKs)"
                                )
                                self._log(f"Darkside complete: {n} NACKs, no candidates", "WARN")
                        elif event == "nested_nonce":
                            phase = result.get("phase", "")
                            label = "calibrating" if phase == "calibrating" else "attacking"
                            self.attack_label.configure(
                                text=f"Nested ({label}): {result['count']} nonce pairs"
                            )
                        elif event == "nested_calibrated":
                            d = result["distance"]
                            self.attack_label.configure(text=f"Nested: calibrated (dist={d}), attacking...")
                            self._log(f"Nested: PRNG distance calibrated to {d} ({result['samples']} samples)")
                        elif event == "nested_fail":
                            self._guard.finish()
                            self.attack_label.configure(text=f"Nested failed: {result['reason']}")
                            self._log(f"Nested failed: {result['reason']}", "WARN")
                        elif event == "nested_complete":
                            self._guard.finish()
                            keys = result.get("candidates", [])
                            n = result["nonce_pairs"]
                            if keys:
                                self.attack_label.configure(
                                    text=f"KEY FOUND: {keys[0]}"
                                )
                                self._log(f"Nested complete: {n} pairs -> KEY FOUND: {', '.join(keys)}")
                            else:
                                self.attack_label.configure(
                                    text=f"No key found ({n} pairs)"
                                )
                                self._log(f"Nested complete: {n} pairs, no key found", "WARN")
                elif msg["type"] == "DATA":
                    self.card_data.set_block(msg["block"], msg["data"])
                    sector = self.card_data.sector_for_block(msg["block"])
                    self.progress_label.configure(text=f"Reading sector {sector}/15...")
                    self.progress_bar.set(sector / 15)
                elif msg["type"] == "OK":
                    if msg["message"] == "DUMP_COMPLETE":
                        self._guard.finish()
                        self.progress_label.configure(text="Dump complete")
                        self.progress_bar.set(1.0)
                        self._refresh_hex_viewer()
                        self._log(f"Dump complete: {self.card_data.block_count} blocks read")
                    elif msg["message"] == "WRITE_READY":
                        self._log("Card ready for writing")
                        self._send_next_write()
                    elif msg["message"].startswith("WROTE:"):
                        self._send_next_write()
                    elif msg["message"] == "WRITE_DONE":
                        self._guard.finish()
                        self._writing = False
                        self.progress_label.configure(text="Write complete!")
                        self.progress_bar.set(1.0)
                        self._log("Write complete!")
                    elif msg["message"].startswith("FORMAT:"):
                        sector_hex = msg["message"][7:]
                        try:
                            sector = int(sector_hex, 16)
                            self.progress_label.configure(text=f"Formatting sector {sector}/15...")
                            self.progress_bar.set(sector / 15)
                        except ValueError:
                            pass
                    elif msg["message"] == "FORMAT_COMPLETE":
                        self._guard.finish()
                        self.progress_label.configure(text="Format complete!")
                        self.progress_bar.set(1.0)
                        self._log("Card formatted to factory defaults")
                        self.card_data.clear()
                        self._refresh_hex_viewer()
                elif msg["type"] == "ERR":
                    err_msg = msg["message"]
                    if err_msg.startswith("FORMAT_AUTH:"):
                        self._log(f"Format: auth failed on sector 0x{err_msg[12:]}", "WARN")
                    elif err_msg.startswith("FORMAT_WRITE:"):
                        self._log(f"Format: write failed on block 0x{err_msg[13:]}", "WARN")
                    else:
                        self.progress_label.configure(text=f"Error: {err_msg}")
                        self._log(f"Firmware error: {err_msg}", "ERROR")
                elif msg["type"] == "INFO":
                    self._log(f"Firmware: {msg['message']}")
        
        attack_ops = ("cracking", "nested_attack", "snowball")
        op_timeout = 300 if self._guard.operation in attack_ops else 30
        if self._guard.check_timeout(timeout=op_timeout):
            self.progress_label.configure(text="Timeout")
            self.progress_bar.set(0)
            self._log(f"Operation timed out after {op_timeout}s", "WARN")
            if self.attack.state != "idle":
                self.attack.stop()
        self.after(100, self._poll_serial)

    def _send_next_write(self):
        if self._write_pending:
            block, hex_data = self._write_pending.pop(0)
            total = self.card_data.block_count or 64
            remaining = len(self._write_pending)
            written = total - remaining - 1
            self.progress_label.configure(text=f"Writing blk {block}...")
            self.progress_bar.set(written / total)
            self._log(f"Sent: LOAD:{block:02X}:{hex_data[:8]}...", "TX")
            self.serial.send_load_block(block, hex_data)
        else:
            self._log("Sent: D (write done)", "TX")
            self.serial.send_command("D\n")

    def _update_tag_display(self, tag):
        self._last_tag_uid = tag.uid
        self.uid_label.configure(text=tag.uid_formatted)
        atqa = tag.atqa
        self.atqa_label.configure(
            text=f"ATQA: {atqa[:2]} {atqa[2:]}" if len(atqa) == 4 else f"ATQA: {atqa}"
        )
        self.sak_label.configure(text=f"SAK: 0x{tag.sak:02X}")
        self.chip_label.configure(text=tag.chip_type)

        colors = {"YES": "#2ea043", "NO": "#da3633", "PARTIAL": "#d29922", "UNKNOWN": "gray"}
        color = colors.get(tag.cloneable, "gray")
        self.clone_label.configure(
            text=f"Cloneable: {tag.cloneable}", text_color=color
        )

    def _add_log_entry(self, tag):
        time_str = tag.timestamp.strftime("%H:%M:%S")
        line = f"{time_str}  | {tag.uid_formatted:<22} | {tag.chip_type:<30} | 0x{tag.sak:02X}\n"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def destroy(self):
        self.serial.disconnect()
        super().destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
