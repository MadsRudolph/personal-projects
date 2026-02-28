import customtkinter as ctk
from tkinter import filedialog

from serial_handler import SerialHandler
from tag_info import Tag
from card_data import CardData


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("RFID Tag Analyzer")
        self.geometry("900x750")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.serial = SerialHandler()
        self.card_data = CardData()
        self._write_pending = []
        self._writing = False

        self._build_connection_bar()
        self._build_tag_card()
        self._build_scan_buttons()
        self._build_rw_buttons()
        self._build_hex_viewer()
        self._build_log_table()
        self._poll_serial()

    def _build_connection_bar(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(frame, text="Port:").pack(side="left", padx=(10, 5))

        self.port_var = ctk.StringVar()
        self.port_menu = ctk.CTkOptionMenu(
            frame, variable=self.port_var, values=[""], width=120
        )
        self.port_menu.pack(side="left", padx=5)

        ctk.CTkButton(
            frame, text="Refresh", width=70, command=self._refresh_ports
        ).pack(side="left", padx=5)

        self.connect_btn = ctk.CTkButton(
            frame, text="Connect", width=90, command=self._toggle_connect
        )
        self.connect_btn.pack(side="left", padx=5)

<<<<<<< HEAD
=======
        ctk.CTkButton(
            frame,
            text="Reset",
            fg_color="#da3633",
            hover_color="#b62324",
            width=70,
            command=self._reset_device,
        ).pack(side="left", padx=5)

>>>>>>> claude/pedantic-robinson
        self.status_label = ctk.CTkLabel(
            frame, text="Disconnected", text_color="red"
        )
        self.status_label.pack(side="right", padx=10)

        self._refresh_ports()

    def _build_tag_card(self):
        self.card = ctk.CTkFrame(self)
        self.card.pack(fill="x", padx=10, pady=5)

        self.uid_label = ctk.CTkLabel(
            self.card,
            text="No tag scanned",
            font=ctk.CTkFont(family="Consolas", size=28, weight="bold"),
        )
        self.uid_label.pack(pady=(15, 5))

        info = ctk.CTkFrame(self.card, fg_color="transparent")
        info.pack(pady=5)

        self.atqa_label = ctk.CTkLabel(info, text="ATQA: --", font=ctk.CTkFont(size=13))
        self.atqa_label.pack(side="left", padx=20)

        self.sak_label = ctk.CTkLabel(info, text="SAK: --", font=ctk.CTkFont(size=13))
        self.sak_label.pack(side="left", padx=20)

        self.chip_label = ctk.CTkLabel(
            self.card, text="", font=ctk.CTkFont(size=15)
        )
        self.chip_label.pack(pady=5)

        self.clone_label = ctk.CTkLabel(
            self.card, text="", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.clone_label.pack(pady=(0, 15))

    def _build_scan_buttons(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(pady=3)

        self.scan_btn = ctk.CTkButton(
            frame,
            text="Start Scan",
            fg_color="#2ea043",
            hover_color="#238636",
            width=120,
            command=lambda: self._send("S"),
        )
        self.scan_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(
            frame,
            text="Stop",
            fg_color="#da3633",
            hover_color="#b62324",
            width=90,
            command=lambda: self._send("P"),
        )
        self.stop_btn.pack(side="left", padx=5)

        self.single_btn = ctk.CTkButton(
            frame, text="Single Scan", width=110, command=lambda: self._send("O")
        )
        self.single_btn.pack(side="left", padx=5)

    def _build_rw_buttons(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(pady=3)

        self.read_btn = ctk.CTkButton(
            frame,
            text="Read Card",
            fg_color="#1f6feb",
            hover_color="#1958c7",
            width=120,
            command=self._read_card,
        )
        self.read_btn.pack(side="left", padx=5)

        self.write_btn = ctk.CTkButton(
            frame,
            text="Write Card",
            fg_color="#d29922",
            hover_color="#b07d1a",
            width=120,
            command=self._write_card,
        )
        self.write_btn.pack(side="left", padx=5)

        self.blk0_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            frame, text="Write Block 0", variable=self.blk0_var
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            frame, text="Save Dump", width=90, command=self._save_dump
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame, text="Load Dump", width=90, command=self._load_dump
        ).pack(side="left", padx=5)

        self.progress_label = ctk.CTkLabel(frame, text="")
        self.progress_label.pack(side="left", padx=10)

    def _build_hex_viewer(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=(3, 5))

        ctk.CTkLabel(
            frame, text="Card Data", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(5, 0))

        self.hex_text = ctk.CTkTextbox(
            frame, font=ctk.CTkFont(family="Consolas", size=11), height=180
        )
        self.hex_text.pack(fill="both", expand=True, padx=5, pady=5)
        self._refresh_hex_viewer()

    def _build_log_table(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

<<<<<<< HEAD
        ctk.CTkLabel(
            frame, text="Scan Log", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(5, 0))
=======
        log_header = ctk.CTkFrame(frame, fg_color="transparent")
        log_header.pack(fill="x", padx=10, pady=(5, 0))

        ctk.CTkLabel(
            log_header, text="Scan Log", font=ctk.CTkFont(weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            log_header, text="Clear", width=60, command=self._clear_log
        ).pack(side="right")
>>>>>>> claude/pedantic-robinson

        self.log_text = ctk.CTkTextbox(
            frame, font=ctk.CTkFont(family="Consolas", size=12), height=120
        )
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        header = f"{'Time':<10} | {'UID':<22} | {'Chip Type':<30} | SAK\n"
        self.log_text.insert("end", header)
        self.log_text.insert("end", "-" * 78 + "\n")
        self.log_text.configure(state="disabled")

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
            except Exception as e:
                self.status_label.configure(
                    text=f"Error: {e}", text_color="red"
                )

<<<<<<< HEAD
=======
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
        self.progress_label.configure(text="Reset!")
        # Drain the queue
        while not self.serial.queue.empty():
            self.serial.queue.get_nowait()

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        header = f"{'Time':<10} | {'UID':<22} | {'Chip Type':<30} | SAK\n"
        self.log_text.insert("end", header)
        self.log_text.insert("end", "-" * 78 + "\n")
        self.log_text.configure(state="disabled")

>>>>>>> claude/pedantic-robinson
    def _send(self, cmd):
        self.serial.send_command(cmd)

    def _read_card(self):
        if not self.serial.is_connected:
            return
        self.card_data.clear()
        self.progress_label.configure(text="Reading...")
        self._send("R")

    def _write_card(self):
        if not self.serial.is_connected or not self.card_data.has_data:
            return
        self._write_pending = self.card_data.blocks_for_write(
            allow_block0=self.blk0_var.get()
        )
        self._writing = True
        self.progress_label.configure(text="Waiting for card...")
        cmd = "B" if self.blk0_var.get() else "W"
        self._send(cmd)

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

    def _load_dump(self):
        path = filedialog.askopenfilename(
            filetypes=[("Binary dump", "*.bin"), ("All files", "*.*")],
        )
        if path:
            self.card_data.load_bin(path)
            self._refresh_hex_viewer()
            self.progress_label.configure(text=f"Loaded {self.card_data.block_count} blocks")

    def _poll_serial(self):
        while not self.serial.queue.empty():
            msg = self.serial.queue.get_nowait()
            if isinstance(msg, Tag):
                self._update_tag_display(msg)
                self._add_log_entry(msg)
            elif isinstance(msg, dict):
                if msg["type"] == "DATA":
                    self.card_data.set_block(msg["block"], msg["data"])
                    sector = self.card_data.sector_for_block(msg["block"])
                    self.progress_label.configure(
                        text=f"Reading sector {sector}/15..."
                    )
                elif msg["type"] == "OK":
                    if msg["message"] == "DUMP_COMPLETE":
                        self.progress_label.configure(
                            text=f"Read complete: {self.card_data.block_count} blocks"
                        )
                        self._refresh_hex_viewer()
                    elif msg["message"] == "WRITE_READY":
                        self._send_next_write()
                    elif msg["message"].startswith("WROTE:"):
                        self._send_next_write()
                    elif msg["message"] == "WRITE_DONE":
                        self._writing = False
                        self.progress_label.configure(text="Write complete!")
                elif msg["type"] == "ERR":
                    self.progress_label.configure(
                        text=f"Error: {msg['message']}"
                    )
        self.after(100, self._poll_serial)

    def _send_next_write(self):
        if self._write_pending:
            block, hex_data = self._write_pending.pop(0)
            total = self.card_data.block_count
            remaining = len(self._write_pending)
            written = total - remaining - 1
            self.progress_label.configure(
                text=f"Writing block {block} ({written}/{total})..."
            )
            self.serial.send_load_block(block, hex_data)
        else:
<<<<<<< HEAD
<<<<<<< HEAD
            self._send("D")
=======
            self.serial.send_command("D\n")  # Needs newline - firmware is in line mode
>>>>>>> claude/pedantic-robinson
=======
            self.serial.send_command("D\n")  # Needs newline - firmware is in line mode
>>>>>>> claude/pedantic-robinson

    def _update_tag_display(self, tag):
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
