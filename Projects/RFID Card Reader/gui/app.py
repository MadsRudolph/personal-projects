import customtkinter as ctk

from serial_handler import SerialHandler
from tag_info import Tag


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("RFID Tag Analyzer")
        self.geometry("800x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.serial = SerialHandler()
        self._build_connection_bar()
        self._build_tag_card()
        self._build_scan_buttons()
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
        self.uid_label.pack(pady=(20, 5))

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
        self.clone_label.pack(pady=(0, 20))

    def _build_scan_buttons(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(pady=5)

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

    def _build_log_table(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        ctk.CTkLabel(
            frame, text="Scan Log", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(5, 0))

        self.log_text = ctk.CTkTextbox(
            frame, font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        header = f"{'Time':<10} | {'UID':<22} | {'Chip Type':<30} | SAK\n"
        self.log_text.insert("end", header)
        self.log_text.insert("end", "-" * 78 + "\n")
        self.log_text.configure(state="disabled")

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

    def _send(self, cmd):
        self.serial.send_command(cmd)

    def _poll_serial(self):
        while not self.serial.queue.empty():
            msg = self.serial.queue.get_nowait()
            if isinstance(msg, Tag):
                self._update_tag_display(msg)
                self._add_log_entry(msg)
        self.after(100, self._poll_serial)

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
