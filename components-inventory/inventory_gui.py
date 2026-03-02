import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import os
import sys
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Import data layer from inventory.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inventory

# --- Premium Theme Configuration ---
THEME = {
    "bg_dark": "#1a1a1a",
    "bg_mid": "#242424",
    "bg_light": "#2d2d2d",
    "accent": "#1f538d",
    "accent_glow": "#3b8ed0",
    "text_main": "#eeeeee",
    "text_dim": "#aaaaaa",
    "success": "#2ecc71",
    "warning": "#f1c40f",
    "danger": "#e74c3c",
}

# Appearance settings
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Adaptive field config: category -> (value_label, show_package)
FIELD_CONFIG = {
    "resistor":   ("Value (e.g. 10k, 4.7k)", True),
    "capacitor":  ("Value (e.g. 100nF, 10uF)", True),
    "inductor":   ("Value (e.g. 10uH, 100mH)", True),
    "crystal":    ("Frequency (e.g. 16MHz)", True),
    "diode":      ("Part # (e.g. 1N4148)", True),
    "transistor": ("Part # (e.g. 2N2222)", True),
    "LED":        ("Color/type (e.g. red 5mm)", True),
    "IC":         ("Part # (e.g. ATmega328P)", True),
    "connector":  ("Description (e.g. 2-pin JST)", False),
    "switch":     ("Description (e.g. tactile 6mm)", False),
    "other":      ("Description", False),
}

class Toast(ctk.CTkToplevel):
    """Sleek Growl-style notification overlay."""
    def __init__(self, parent, message, color=THEME["success"]):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)
        
        self.frame = ctk.CTkFrame(self, fg_color=color, corner_radius=10)
        self.frame.pack(fill="both", expand=True)
        
        self.label = ctk.CTkLabel(self.frame, text=message, text_color="white", 
                                 font=ctk.CTkFont(size=13, weight="bold"), padx=25, pady=12)
        self.label.pack()
        
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            tx = px + pw - 320
            ty = py + ph - 100
            self.geometry(f"+{int(tx)}+{int(ty)}")
        except:
            self.geometry("+100+100")
        
        self._fade_in()
        self.after(2500, self._fade_out)

    def _fade_in(self):
        try:
            alpha = self.attributes("-alpha")
            if alpha < 0.95:
                self.attributes("-alpha", alpha + 0.1)
                self.after(20, self._fade_in)
        except: pass

    def _fade_out(self):
        try:
            alpha = self.attributes("-alpha")
            if alpha > 0.05:
                self.attributes("-alpha", alpha - 0.1)
                self.after(20, self._fade_out)
            else:
                self.destroy()
        except: pass

class EditDialog(ctk.CTkToplevel):
    def __init__(self, parent, component_data, on_update):
        super().__init__(parent)
        self.title(f"Edit Component: {component_data['name']}")
        self.geometry("600x550")
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=THEME["bg_dark"])
        
        self.component_data = component_data
        self.on_update = on_update
        self.conn = parent.conn
        
        container = ctk.CTkFrame(self, fg_color=THEME["bg_mid"], corner_radius=15)
        container.pack(fill="both", expand=True, padx=20, pady=20)
        container.grid_columnconfigure(1, weight=1)
        
        row = 0
        ctk.CTkLabel(container, text="Name:").grid(row=row, column=0, padx=20, pady=10, sticky="e")
        self.name_entry = ctk.CTkEntry(container, width=300)
        self.name_entry.grid(row=row, column=1, padx=20, pady=10, sticky="w")
        self.name_entry.insert(0, component_data['name'])
        
        row += 1
        ctk.CTkLabel(container, text="Category:").grid(row=row, column=0, padx=20, pady=10, sticky="e")
        self.cat_menu = ctk.CTkOptionMenu(container, values=inventory.CATEGORIES)
        self.cat_menu.grid(row=row, column=1, padx=20, pady=10, sticky="w")
        self.cat_menu.set(component_data['category'])
        
        row += 1
        self.value_entry = ctk.CTkEntry(container, width=300)
        self.value_entry.grid(row=row, column=1, padx=20, pady=10, sticky="w")
        self.value_entry.insert(0, component_data['value'] or "")
        
        row += 1
        self.pkg_entry = ctk.CTkEntry(container, width=300)
        self.pkg_entry.grid(row=row, column=1, padx=20, pady=10, sticky="w")
        self.pkg_entry.insert(0, component_data['package'] or "")
        
        row += 1
        ctk.CTkLabel(container, text="Quantity:").grid(row=row, column=0, padx=20, pady=10, sticky="e")
        self.qty_entry = ctk.CTkEntry(container, width=100)
        self.qty_entry.grid(row=row, column=1, padx=20, pady=10, sticky="w")
        self.qty_entry.insert(0, str(component_data['quantity']))
        
        row += 1
        ctk.CTkLabel(container, text="Notes:").grid(row=row, column=0, padx=20, pady=10, sticky="e")
        self.notes_entry = ctk.CTkEntry(container, width=300)
        self.notes_entry.grid(row=row, column=1, padx=20, pady=10, sticky="w")
        self.notes_entry.insert(0, component_data['notes'] or "")
        
        # Resistor Color Visuals
        if component_data['category'].lower() == "resistor":
            row += 1
            ctk.CTkLabel(container, text="Color Code:").grid(row=row, column=0, padx=20, pady=10, sticky="e")
            self.color_canvas = tk.Canvas(container, width=200, height=30, bg=THEME["bg_mid"], highlightthickness=0)
            self.color_canvas.grid(row=row, column=1, padx=20, pady=10, sticky="w")
            self._draw_resistor_colors()

    def _draw_resistor_colors(self):
        val = inventory.parse_shop_value(self.component_data['value'])
        colors = inventory.get_resistor_colors(val)
        if colors:
            self.color_canvas.delete("all")
            # Adjust canvas width for 5 bands if needed
            if len(colors) == 5:
                self.color_canvas.configure(width=250)
            
            x = 10
            for color in colors:
                hex_color = inventory.RESISTOR_COLORS[color]["color"]
                self.color_canvas.create_rectangle(x, 5, x+30, 25, fill=hex_color, outline="white")
                x += 40
        else:
            self.color_canvas.create_text(100, 15, text="No code for this value", fill=THEME["text_dim"])
        
        row += 1
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.grid(row=row, column=1, padx=20, pady=20, sticky="w")
        
        self.save_btn = ctk.CTkButton(btn_frame, text="Update", font=ctk.CTkFont(weight="bold"), 
                                     fg_color=THEME["accent"], hover_color=THEME["accent_glow"], command=self._do_update)
        self.save_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.delete_btn = ctk.CTkButton(btn_frame, text="Delete", fg_color=THEME["danger"], command=self._do_delete)
        self.delete_btn.grid(row=0, column=1, padx=10)

    def _do_update(self):
        try:
            qty = int(self.qty_entry.get())
        except ValueError:
            qty = 1
        data = {
            "name": self.name_entry.get().strip(),
            "category": self.cat_menu.get(),
            "value": self.value_entry.get().strip(),
            "package": self.pkg_entry.get().strip(),
            "quantity": qty,
            "notes": self.notes_entry.get().strip(),
        }
        inventory.update_component(self.conn, self.component_data['id'], data)
        Toast(self.master, "Component Updated")
        self.on_update()
        self.destroy()

    def _do_delete(self):
        if messagebox.askyesno("Confirm", f"Delete {self.component_data['name']}?"):
            inventory.delete_component(self.conn, self.component_data['id'])
            Toast(self.master, "Component Deleted", color=THEME["danger"])
            self.on_update()
            self.destroy()

class ResistorHelper(ctk.CTkToplevel):
    def __init__(self, parent, on_select):
        super().__init__(parent)
        self.title("Resistor Color Code Helper")
        self.geometry("650x500")
        self.transient(parent)
        self.grab_set()
        self.on_select = on_select
        self.configure(fg_color=THEME["bg_dark"])
        
        container = ctk.CTkFrame(self, fg_color=THEME["bg_mid"], corner_radius=15)
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(container, text="Resistor Color Code Identifier", 
                    font=ctk.CTkFont(size=20, weight="bold"), text_color=THEME["accent_glow"]).pack(pady=15)
        
        self.band_count = ctk.IntVar(value=4)
        toggle_frame = ctk.CTkFrame(container, fg_color="transparent")
        toggle_frame.pack(pady=5)
        ctk.CTkRadioButton(toggle_frame, text="4 Bands", variable=self.band_count, value=4, command=self._setup_bands).pack(side="left", padx=10)
        ctk.CTkRadioButton(toggle_frame, text="5 Bands", variable=self.band_count, value=5, command=self._setup_bands).pack(side="left", padx=10)
        
        self.shorthand_var = ctk.StringVar()
        self.shorthand_var.trace_add("write", self._on_shorthand_change)
        sh_frame = ctk.CTkFrame(container, fg_color="transparent")
        sh_frame.pack(pady=5)
        ctk.CTkLabel(sh_frame, text="Shorthand:", text_color=THEME["text_dim"]).pack(side="left", padx=10)
        self.shorthand_entry = ctk.CTkEntry(sh_frame, placeholder_text="e.g. bn,bk,bk,r", width=250, textvariable=self.shorthand_var)
        self.shorthand_entry.pack(side="left")
        
        self.bands_frame = ctk.CTkFrame(container, fg_color="transparent")
        self.bands_frame.pack(pady=10)
        
        self.calc_label = ctk.CTkLabel(container, text="Value: ---", font=ctk.CTkFont(size=18, weight="bold"))
        self.calc_label.pack(pady=10)
        
        self.matches_list = tk.Listbox(container, height=6, bg="#2b2b2b", fg="white", 
                                      borderwidth=0, highlightthickness=0, 
                                      selectbackground=THEME["accent"], font=("Arial", 10))
        self.matches_list.pack(fill="x", padx=20, pady=(0, 10))
        self.matches_list.bind("<Double-1>", lambda e: self._on_apply())
        
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Apply Selected", fg_color=THEME["accent"], command=self._on_apply).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="transparent", border_width=1, command=self.destroy).pack(side="left", padx=10)
        
        self.match_data = []
        self._setup_bands()

    def _setup_bands(self):
        for w in self.bands_frame.winfo_children(): w.destroy()
        num = self.band_count.get()
        self.selected_colors = []
        all_colors = sorted(list(inventory.RESISTOR_COLORS.keys()))
        for i in range(num):
            var = ctk.StringVar(value="black" if i < (num-1) else "gold")
            self.selected_colors.append(var)
            f = ctk.CTkFrame(self.bands_frame, fg_color="transparent")
            f.pack(side="left", padx=5)
            menu = ctk.CTkOptionMenu(f, values=all_colors, variable=var, width=80, command=lambda _: self._recalculate())
            menu.pack()
            preview = ctk.CTkFrame(f, width=80, height=10, corner_radius=2)
            preview.pack(pady=2)
            def update_preview(v=var, p=preview): p.configure(fg_color=inventory.RESISTOR_COLORS[v.get()]["color"])
            var.trace_add("write", lambda *_, up=update_preview: up())
            update_preview()
        self._recalculate()

    def _on_shorthand_change(self, *args):
        text = self.shorthand_var.get().lower().strip()
        if not text: return
        parts = text.replace(",", " ").split()
        if not parts: return
        
        full_colors = []
        for p in parts:
            if p in inventory.COLOR_SHORTHAND: full_colors.append(inventory.COLOR_SHORTHAND[p])
            elif p in inventory.RESISTOR_COLORS: full_colors.append(p)
                
        if not full_colors: return
        
        if len(full_colors) >= 5 and self.band_count.get() == 4:
            self.band_count.set(5)
            self._setup_bands()
        
        for i, color in enumerate(full_colors):
            if i < len(self.selected_colors):
                self.selected_colors[i].set(color)
        self._recalculate()

    def _recalculate(self):
        bands = [v.get() for v in self.selected_colors]
        val, tol = inventory.calculate_resistance(bands)
        if val is not None:
            txt = f"Value: {inventory.format_resistance(val)} Ω"
            if tol: txt += f" ±{tol}%"
            self.calc_label.configure(text=txt, text_color=THEME["accent_glow"])
            self._find_shop_matches(val)
        else:
            self.calc_label.configure(text="Value: Incomplete", text_color=THEME["danger"])

    def _find_shop_matches(self, target_val):
        self.matches_list.delete(0, "end")
        resistors = self.master.shop_data.search("", cat_filter="resistor", limit=None)
        self.match_data = [item for item in resistors if abs((inventory.parse_shop_value(item["value"]) or 0) - target_val) < (target_val * 0.001)]
        for item in self.match_data:
            self.matches_list.insert("end", f"[{item['part_number']}] {item['value']} - {item['subcategory']}")

    def _on_apply(self):
        sel = self.matches_list.curselection()
        if sel:
            self.on_select(self.match_data[sel[0]])
            self.destroy()

SHOP_TO_APP_CATEGORY = {
    "resistor": "resistor", "capacitor": "capacitor", "inductor": "inductor",
    "diode": "diode", "transistor": "transistor", "ic": "IC", "connector": "connector",
    "led": "LED", "crystal": "crystal", "switch": "switch",
    "encoder": "other", "hardware": "other", "ir": "other",
    "optocoupler": "other", "photodiode": "other", "sensor": "other",
}

class AutocompleteDropdown:
    """Styled autocomplete dropdown using a Toplevel overlay window."""

    MAX_VISIBLE = 8
    ROW_HEIGHT = 40

    def __init__(self, parent_app, on_select):
        self._parent = parent_app
        self.on_select = on_select
        self._rows = []
        self._items = []
        self._selected_idx = -1
        self._entry = None

        # Borderless overlay window
        self._win = tk.Toplevel(parent_app)
        self._win.overrideredirect(True)
        self._win.withdraw()
        self._win.transient(parent_app)
        self._win.configure(bg=THEME["bg_light"])

        # Styled container
        self._frame = ctk.CTkFrame(self._win,
                                    fg_color=THEME["bg_light"],
                                    corner_radius=12,
                                    border_width=2,
                                    border_color=THEME["accent"])
        self._frame.pack(fill="both", expand=True)

        # Header with match count
        header = ctk.CTkFrame(self._frame, fg_color="transparent", height=24)
        header.pack(fill="x", padx=12, pady=(8, 2))
        header.pack_propagate(False)

        self.count_label = ctk.CTkLabel(header, text="",
                                         font=ctk.CTkFont(size=10),
                                         text_color=THEME["text_dim"])
        self.count_label.pack(side="left")

        self.source_label = ctk.CTkLabel(header, text="DTU Shop",
                                          font=ctk.CTkFont(size=10, weight="bold"),
                                          text_color=THEME["accent_glow"])
        self.source_label.pack(side="right")

        # Separator line
        sep = ctk.CTkFrame(self._frame, fg_color=THEME["bg_mid"], height=1)
        sep.pack(fill="x", padx=10, pady=(0, 4))

        # Rows container
        self.rows_container = ctk.CTkFrame(self._frame, fg_color="transparent")
        self.rows_container.pack(fill="both", expand=True, padx=6, pady=(0, 8))

    def show(self, items, entry_widget):
        """Position below entry_widget and display matching items."""
        if not items:
            self.hide()
            return

        self._items = items
        self._entry = entry_widget
        self._selected_idx = -1

        # Clear old rows
        for row_frame in self._rows:
            row_frame.destroy()
        self._rows = []

        # Create rows (limit visible)
        visible = items[:self.MAX_VISIBLE]
        for idx, item in enumerate(visible):
            row = self._create_row(item, idx)
            row.pack(fill="x", padx=2, pady=1)
            self._rows.append(row)

        # Update count
        total = len(items)
        showing = len(visible)
        if total > showing:
            self.count_label.configure(text=f"{showing} of {total} matches")
        else:
            self.count_label.configure(text=f"{total} match{'es' if total != 1 else ''}")

        # Position below entry using screen coordinates
        x = entry_widget.winfo_rootx()
        y = entry_widget.winfo_rooty() + entry_widget.winfo_height() + 4
        width = max(entry_widget.winfo_width() + 60, 460)
        height = len(visible) * self.ROW_HEIGHT + 42

        self._win.geometry(f"{width}x{height}+{x}+{y}")
        self._win.deiconify()
        self._win.lift()

        # Bind keyboard navigation on entry
        entry_widget.bind("<Down>", self._on_key_down)
        entry_widget.bind("<Up>", self._on_key_up)
        entry_widget.bind("<Return>", self._on_key_enter)
        entry_widget.bind("<Escape>", self._on_key_escape)

    def hide(self):
        """Hide the dropdown and unbind keyboard events."""
        if self._entry:
            try:
                self._entry.unbind("<Down>")
                self._entry.unbind("<Up>")
                self._entry.unbind("<Return>")
                self._entry.unbind("<Escape>")
            except Exception:
                pass
        self._win.withdraw()
        self._selected_idx = -1

    def _create_row(self, item, idx):
        """Create a single styled suggestion row."""
        row = ctk.CTkFrame(self.rows_container, fg_color="transparent",
                           corner_radius=8, height=self.ROW_HEIGHT - 4)
        row.pack_propagate(False)

        # Determine display info based on item source
        cat = item.get("category", "").lower()
        value = item.get("value", "") or ""
        part_num = item.get("part_number", "") or item.get("name", "") or ""
        package = item.get("package", "") or ""
        desc = item.get("description", "") or item.get("subcategory", "") or ""

        # Passives: show value prominently; actives: show part number
        if cat in ("resistor", "capacitor", "inductor", "crystal"):
            primary = value or part_num
            tertiary = desc[:35] if desc else part_num
        else:
            primary = part_num or value
            tertiary = desc[:35] if desc else value

        # -- Left side: primary text (bold, white) --
        p_lbl = ctk.CTkLabel(row, text=primary,
                              font=ctk.CTkFont(size=13, weight="bold"),
                              text_color=THEME["text_main"])
        p_lbl.pack(side="left", padx=(14, 0))

        # -- Resistor color bands (visual) --
        if cat == "resistor" and value:
            parsed = inventory.parse_shop_value(value)
            colors = inventory.get_resistor_colors(parsed) if parsed else None
            if colors:
                band_w = 8
                gap = 3
                canvas_w = len(colors) * (band_w + gap) + gap + 6
                band_canvas = tk.Canvas(row, width=canvas_w, height=22,
                                        bg=THEME["bg_mid"], highlightthickness=0, bd=0)
                band_canvas.pack(side="left", padx=(10, 0))
                # Draw resistor body background
                band_canvas.create_rectangle(2, 2, canvas_w - 2, 20,
                                              fill="#c4a46c", outline="#a08050", width=1)
                x = gap + 3
                for color_name in colors:
                    hex_c = inventory.RESISTOR_COLORS[color_name]["color"]
                    outline_c = "#555555" if color_name == "black" else hex_c
                    band_canvas.create_rectangle(x, 4, x + band_w, 18,
                                                  fill=hex_c, outline=outline_c, width=1)
                    x += band_w + gap

        # -- Package badge (accent colored) --
        if package:
            pkg_badge = ctk.CTkLabel(row, text=package,
                                      font=ctk.CTkFont(size=10),
                                      text_color=THEME["accent_glow"],
                                      fg_color=THEME["bg_dark"],
                                      corner_radius=4, width=50)
            pkg_badge.pack(side="left", padx=(10, 0))

        # -- Right side: description or secondary info (dim) --
        if tertiary and tertiary != primary:
            t_lbl = ctk.CTkLabel(row, text=tertiary,
                                  font=ctk.CTkFont(size=10),
                                  text_color=THEME["text_dim"])
            t_lbl.pack(side="right", padx=(0, 14))

        # Hover and click handlers
        def on_enter(e, r=row, i=idx):
            self._selected_idx = i
            self._highlight_rows()

        def on_leave(e, r=row):
            r.configure(fg_color="transparent")

        def on_click(e, it=item):
            self.on_select(it)
            self.hide()

        for widget in [row] + list(row.winfo_children()):
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            widget.bind("<Button-1>", on_click)

        return row

    def _highlight_rows(self):
        """Highlight the selected row, clear others."""
        for i, row in enumerate(self._rows):
            if i == self._selected_idx:
                row.configure(fg_color=THEME["accent"])
            else:
                row.configure(fg_color="transparent")

    def _on_key_down(self, event):
        if self._rows:
            self._selected_idx = min(self._selected_idx + 1, len(self._rows) - 1)
            self._highlight_rows()
        return "break"

    def _on_key_up(self, event):
        if self._rows:
            self._selected_idx = max(self._selected_idx - 1, 0)
            self._highlight_rows()
        return "break"

    def _on_key_enter(self, event):
        visible = self._items[:self.MAX_VISIBLE]
        if 0 <= self._selected_idx < len(visible):
            self.on_select(visible[self._selected_idx])
            self.hide()
            return "break"

    def _on_key_escape(self, event):
        self.hide()
        return "break"


class InventoryApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Component Inventory Pro")
        self.geometry("1100x700")
        self.configure(fg_color=THEME["bg_dark"])
        self.conn = inventory.init_db()
        self.shop_data = inventory.ShopData()
        self.session_count = 0
        self.last_category = "resistor"
        self._dropdown_filling = False

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self._build_sidebar()
        self._build_main_content()
        self._bind_shortcuts()
        self.select_frame_by_name("add")

    def _build_sidebar(self):
        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=THEME["bg_mid"])
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.navigation_frame, text="Inventory Pro", font=ctk.CTkFont(size=20, weight="bold"), text_color=THEME["accent_glow"]).pack(pady=30)
        self.add_btn_nav = ctk.CTkButton(self.navigation_frame, text="Add Item", fg_color="transparent", command=lambda: self.select_frame_by_name("add")).pack(fill="x")
        self.inv_btn_nav = ctk.CTkButton(self.navigation_frame, text="Inventory", fg_color="transparent", command=lambda: self.select_frame_by_name("inventory")).pack(fill="x")
        self.stock_btn_nav = ctk.CTkButton(self.navigation_frame, text="Stock", fg_color="transparent", command=lambda: self.select_frame_by_name("stock")).pack(fill="x")
        self.dash_btn_nav = ctk.CTkButton(self.navigation_frame, text="Dashboard", fg_color="transparent", command=lambda: self.select_frame_by_name("dashboard")).pack(fill="x")
        self.shop_btn_nav = ctk.CTkButton(self.navigation_frame, text="DTU Shop", fg_color="transparent", command=lambda: self.select_frame_by_name("shop")).pack(fill="x")

    def _build_main_content(self):
        self.add_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.inventory_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stock_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dashboard_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.shop_frame = ctk.CTkFrame(self, fg_color="transparent")

        self._setup_add_tab()
        self._setup_inventory_tab()
        self._setup_stock_tab()
        self._setup_dashboard_tab()
        self._setup_shop_tab()

    def _setup_add_tab(self):
        self.add_frame.grid_columnconfigure(0, weight=3)
        self.add_frame.grid_columnconfigure(1, weight=1)
        
        header = ctk.CTkFrame(self.add_frame, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="ew")
        ctk.CTkLabel(header, text="Add New Component", font=ctk.CTkFont(size=26, weight="bold"), text_color=THEME["accent_glow"]).pack(side="left")
        
        cat_bar = ctk.CTkFrame(header, fg_color="transparent")
        cat_bar.pack(side="right")
        self.cat_buttons = {}
        for cat in ["resistor", "capacitor", "IC", "transistor", "diode", "LED"]:
            btn = ctk.CTkButton(cat_bar, text=cat.capitalize(), width=90, fg_color="gray25", command=lambda c=cat: self._on_quick_cat_select(c))
            btn.pack(side="left", padx=2)
            self.cat_buttons[cat] = btn

        self.form = ctk.CTkFrame(self.add_frame, fg_color=THEME["bg_mid"], corner_radius=15)
        self.form.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        self.name_var = ctk.StringVar()
        self.name_var.trace_add("write", self._on_name_typing)
        ctk.CTkLabel(self.form, text="Name:", text_color=THEME["text_dim"]).grid(row=0, column=0, padx=(20, 0), sticky="e")
        self.add_name = ctk.CTkEntry(self.form, placeholder_text="Enter component name...", width=400, textvariable=self.name_var)
        self.add_name.grid(row=0, column=1, padx=20, pady=15, sticky="w")
        
        ctk.CTkLabel(self.form, text="Category:", text_color=THEME["text_dim"]).grid(row=1, column=0, padx=(20, 0), sticky="e")
        self.add_category = ctk.CTkOptionMenu(self.form, values=inventory.CATEGORIES, command=self._on_category_change)
        self.add_category.grid(row=1, column=1, padx=20, pady=15, sticky="w")
        self.add_category.set(self.last_category)
        
        self.value_var = ctk.StringVar()
        self.value_var.trace_add("write", self._on_value_typing)
        ctk.CTkLabel(self.form, text="Value:", text_color=THEME["text_dim"]).grid(row=2, column=0, padx=(20, 0), sticky="e")
        self.add_value = ctk.CTkEntry(self.form, placeholder_text="e.g. 10k, 100nF", width=400, textvariable=self.value_var)
        self.add_value.grid(row=2, column=1, padx=20, pady=15, sticky="w")
        
        ctk.CTkLabel(self.form, text="Package:", text_color=THEME["text_dim"]).grid(row=3, column=0, padx=(20, 0), sticky="e")
        self.add_package = ctk.CTkEntry(self.form, placeholder_text="e.g. 0805, TO-92", width=400)
        self.add_package.grid(row=3, column=1, padx=20, pady=15, sticky="w")
        
        ctk.CTkLabel(self.form, text="Quantity:", text_color=THEME["text_dim"]).grid(row=4, column=0, padx=(20, 0), sticky="e")
        self.add_qty = ctk.CTkEntry(self.form, width=80)
        self.add_qty.grid(row=4, column=1, padx=20, pady=15, sticky="w")
        self.add_qty.insert(0, "1")
        
        ctk.CTkLabel(self.form, text="Notes:", text_color=THEME["text_dim"]).grid(row=5, column=0, padx=(20, 0), sticky="e")
        self.add_notes = ctk.CTkEntry(self.form, placeholder_text="Additional details...", width=400)
        self.add_notes.grid(row=5, column=1, padx=20, pady=15, sticky="w")
        
        btn_f = ctk.CTkFrame(self.form, fg_color="transparent")
        btn_f.grid(row=6, column=1, padx=20, pady=20, sticky="w")
        ctk.CTkButton(btn_f, text="Save", fg_color=THEME["accent"], command=self._save_component).pack(side="left", padx=5)
        ctk.CTkButton(btn_f, text="Identify Resistor", fg_color="transparent", border_width=1, command=self._open_resistor_helper).pack(side="left", padx=5)
        
        sidebar = ctk.CTkFrame(self.add_frame, fg_color=THEME["bg_mid"], corner_radius=15)
        sidebar.grid(row=1, column=1, padx=(0, 20), pady=10, sticky="nsew")
        ctk.CTkLabel(sidebar, text="Recent", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        self.recent_list = tk.Listbox(sidebar, bg="#2b2b2b", fg="white", borderwidth=0)
        self.recent_list.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Autocomplete dropdowns (Toplevel overlay windows) ---
        self.value_dropdown = AutocompleteDropdown(self, on_select=self._on_value_dropdown_select)
        self.name_dropdown = AutocompleteDropdown(self, on_select=self._on_name_dropdown_select)
        self.name_dropdown.source_label.configure(text="Part Search")

        # Hide dropdowns when entry loses focus (200ms delay so clicks register)
        self.add_value.bind("<FocusOut>", lambda e: self.after(200, self.value_dropdown.hide))
        self.add_name.bind("<FocusOut>", lambda e: self.after(200, self.name_dropdown.hide))

        self.add_frame.grid_rowconfigure(1, weight=1)

    def _setup_inventory_tab(self):
        # Header Tools
        header = ctk.CTkFrame(self.inventory_frame, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(header, text="Inventory List", font=ctk.CTkFont(size=24, weight="bold"), text_color=THEME["accent_glow"]).pack(side="left")
        
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_inventory())
        ctk.CTkEntry(header, placeholder_text="Search components...", width=300, textvariable=self.search_var).pack(side="left", padx=10)
        
        self.delete_sel_btn = ctk.CTkButton(header, text="Delete Selected", fg_color=THEME["danger"], 
                                          command=self._delete_selected_inventory, width=120)
        self.delete_sel_btn.pack(side="right")
        
        # Treeview Container
        tree_container = ctk.CTkFrame(self.inventory_frame, fg_color=THEME["bg_mid"], corner_radius=10)
        tree_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # ttk Style for Dark Treeview
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                        background=THEME["bg_light"],
                        foreground=THEME["text_main"],
                        rowheight=35,
                        fieldbackground=THEME["bg_light"],
                        bordercolor=THEME["bg_dark"],
                        borderwidth=0,
                        indent=0)
        style.map("Treeview", background=[('selected', THEME["accent"])])
        style.configure("Treeview.Heading", background=THEME["bg_mid"], foreground=THEME["text_dim"], 
                        relief="flat", font=('Arial', 10, 'bold'))
        style.map("Treeview.Heading", background=[('active', THEME["bg_light"])])

        cols = ("id", "name", "category", "value", "package", "qty", "notes")
        self.inv_tree = ttk.Treeview(tree_container, columns=cols, show="tree headings", style="Treeview")

        # Tree column (#0) for color band images
        self.inv_tree.heading("#0", text="Color Code")
        self.inv_tree.column("#0", width=130, stretch=False, anchor="center")

        # Column Config
        col_widths = {"id": 50, "name": 200, "category": 100, "value": 110, "package": 100, "qty": 60, "notes": 250}
        for col in cols:
            self.inv_tree.heading(col, text=col.capitalize())
            self.inv_tree.column(col, width=col_widths.get(col, 100), anchor="center" if col in ("id", "qty") else "w")

        self._color_band_images = []  # Keep references to prevent GC

        scrollbar = ctk.CTkScrollbar(tree_container, orientation="vertical", command=self.inv_tree.yview)
        self.inv_tree.configure(yscrollcommand=scrollbar.set)
        self.inv_tree.pack(side="left", fill="both", expand=True, padx=(2,0), pady=2)
        scrollbar.pack(side="right", fill="y", padx=(0,2), pady=2)
        
        self.inv_tree.bind("<Double-1>", self._on_tree_double_click)
        self.inv_tree.bind("<Delete>", lambda e: self._delete_selected_inventory())

    def _setup_stock_tab(self):
        header = ctk.CTkFrame(self.stock_frame, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(header, text="Stock Summary", font=ctk.CTkFont(size=24, weight="bold"), text_color=THEME["accent_glow"]).pack(side="left")
        
        self.export_btn = ctk.CTkButton(header, text="Export CSV", command=self._export_csv,
                                       fg_color="gray25", hover_color=THEME["accent"], height=35)
        self.export_btn.pack(side="right")

        self.export_ai_btn = ctk.CTkButton(header, text="Export for AI", command=self._export_ai_markdown,
                                            fg_color=THEME["accent"], hover_color=THEME["accent_glow"], height=35)
        self.export_ai_btn.pack(side="right", padx=(0, 10))
        
        # Treeview Container
        tree_container = ctk.CTkFrame(self.stock_frame, fg_color=THEME["bg_mid"], corner_radius=10)
        tree_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        cols = ("category", "items", "total_qty")
        self.stock_tree = ttk.Treeview(tree_container, columns=cols, show="headings", style="Treeview")
        for col in cols:
            self.stock_tree.heading(col, text=col.replace("_", " ").capitalize())
            self.stock_tree.column(col, anchor="center", width=200)

        scrollbar = ctk.CTkScrollbar(tree_container, orientation="vertical", command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=scrollbar.set)
        self.stock_tree.pack(side="left", fill="both", expand=True, padx=(2,0), pady=2)
        scrollbar.pack(side="right", fill="y", padx=(0,2), pady=2)

    def _setup_dashboard_tab(self):
        header = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(header, text="Stock Overview", font=ctk.CTkFont(size=24, weight="bold"), text_color=THEME["accent_glow"]).pack(side="left")
        
        self.stats_frame = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=20, pady=10)
        
        self.total_unique_lbl = ctk.CTkLabel(self.stats_frame, text="Total Unique Items: 0", font=ctk.CTkFont(size=16))
        self.total_unique_lbl.pack(side="left", padx=(0, 20))
        self.total_qty_lbl = ctk.CTkLabel(self.stats_frame, text="Grand Total Quantity: 0", font=ctk.CTkFont(size=16))
        self.total_qty_lbl.pack(side="left")

        self.chart_container = ctk.CTkFrame(self.dashboard_frame, fg_color=THEME["bg_mid"], corner_radius=10)
        self.chart_container.pack(fill="both", expand=True, padx=20, pady=10)
        self.chart_canvas = None

    def _refresh_dashboard(self):
        stats = inventory.get_category_stats(self.conn)
        
        total_unique = sum(row[1] for row in stats)
        total_qty = sum(row[2] for row in stats)
        
        self.total_unique_lbl.configure(text=f"Total Unique Items: {total_unique}")
        self.total_qty_lbl.configure(text=f"Grand Total Quantity: {total_qty}")
        
        if self.chart_canvas:
            self.chart_canvas.get_tk_widget().destroy()
            
        if not stats:
            return

        categories = [row[0].capitalize() for row in stats]
        quantities = [row[2] for row in stats]

        # Premium Dark Theme Donut Chart
        fig, ax = plt.subplots(figsize=(8, 5), facecolor=THEME["bg_mid"])
        ax.set_facecolor(THEME["bg_mid"])

        # Modern color palette
        n = len(categories)
        colors = plt.cm.GnBu([0.45 + (0.5 * i / max(1, n - 1)) for i in range(n)])

        wedges, texts, autotexts = ax.pie(
            quantities, labels=categories, autopct=lambda p: f'{int(round(p * sum(quantities) / 100))}',
            colors=colors, startangle=140, pctdistance=0.78,
            wedgeprops=dict(width=0.45, edgecolor=THEME["bg_mid"], linewidth=2),
            textprops=dict(color=THEME["text_main"], fontsize=11)
        )

        for at in autotexts:
            at.set_fontsize(10)
            at.set_fontweight("bold")
            at.set_color(THEME["text_main"])

        # Center label
        ax.text(0, 0, f"{sum(quantities)}\ntotal", ha='center', va='center',
                fontsize=18, fontweight='bold', color=THEME["accent_glow"])

        ax.set_title("Inventory by Category", color=THEME["text_main"],
                      pad=20, fontsize=16, fontweight='bold')

        fig.tight_layout()

        self.chart_canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        self.chart_canvas.draw()
        self.chart_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    # ------------------------------------------------------------------ #
    #                       DTU SHOP BROWSER TAB                          #
    # ------------------------------------------------------------------ #

    def _setup_shop_tab(self):
        """Build the DTU Shop browser with category sidebar and filtered list."""
        self.shop_frame.grid_columnconfigure(1, weight=1)
        self.shop_frame.grid_rowconfigure(2, weight=1)

        # --- Left category sidebar ---
        cat_panel = ctk.CTkFrame(self.shop_frame, fg_color=THEME["bg_mid"],
                                 corner_radius=10, width=210)
        cat_panel.grid(row=0, column=0, rowspan=3, padx=(20, 10), pady=20, sticky="nsew")
        cat_panel.grid_propagate(False)

        ctk.CTkLabel(cat_panel, text="Categories",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=THEME["accent_glow"]).pack(pady=(15, 10))

        # Gather unique categories with counts from shop data
        shop_cats = {}
        for item in self.shop_data.items:
            c = item["category"]
            shop_cats[c] = shop_cats.get(c, 0) + 1

        self._shop_cat_var = "all"
        self._shop_subcat_var = None
        self._shop_cat_buttons = {}

        # "All" button
        btn = ctk.CTkButton(cat_panel,
                            text=f"All  ({len(self.shop_data.items)})",
                            fg_color=THEME["accent"], hover_color=THEME["accent_glow"],
                            anchor="w", height=32,
                            command=lambda: self._shop_select_category("all"))
        btn.pack(fill="x", padx=10, pady=2)
        self._shop_cat_buttons["all"] = btn

        for cat, count in sorted(shop_cats.items(), key=lambda x: -x[1]):
            display = cat.upper() if cat in ("ic", "led", "ir") else cat.capitalize()
            btn = ctk.CTkButton(cat_panel,
                                text=f"{display}  ({count})",
                                fg_color="transparent", hover_color=THEME["bg_light"],
                                anchor="w", height=32,
                                command=lambda c=cat: self._shop_select_category(c))
            btn.pack(fill="x", padx=10, pady=2)
            self._shop_cat_buttons[cat] = btn

        # Subcategory chips container (populated dynamically)
        self._shop_subcat_frame = ctk.CTkScrollableFrame(cat_panel,
                                                          fg_color="transparent",
                                                          label_text="")
        self._shop_subcat_frame.pack(fill="both", expand=True, padx=10, pady=(10, 15))

        # --- Top header bar ---
        header = ctk.CTkFrame(self.shop_frame, fg_color="transparent")
        header.grid(row=0, column=1, padx=(0, 20), pady=(20, 0), sticky="ew")

        ctk.CTkLabel(header, text="DTU Component Shop",
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=THEME["accent_glow"]).pack(side="left")

        self._shop_count_label = ctk.CTkLabel(header, text="",
                                               font=ctk.CTkFont(size=13),
                                               text_color=THEME["text_dim"])
        self._shop_count_label.pack(side="right", padx=(0, 10))

        self._shop_search_var = ctk.StringVar()
        self._shop_search_var.trace_add("write", lambda *_: self._on_shop_search())
        search_entry = ctk.CTkEntry(header, placeholder_text="Search parts...",
                                    width=280, textvariable=self._shop_search_var)
        search_entry.pack(side="right", padx=10)

        # --- Filter bar ---
        filter_bar = ctk.CTkFrame(self.shop_frame, fg_color="transparent", height=36)
        filter_bar.grid(row=1, column=1, padx=(0, 20), pady=(8, 0), sticky="ew")

        ctk.CTkLabel(filter_bar, text="Show:",
                     font=ctk.CTkFont(size=12),
                     text_color=THEME["text_dim"]).pack(side="left", padx=(0, 8))

        self._shop_ownership_filter = "all"
        self._shop_filter_buttons = {}
        for fkey, flabel in [("all", "All"), ("owned", "Owned"), ("not_owned", "Not Owned")]:
            btn = ctk.CTkButton(filter_bar, text=flabel, width=90, height=28,
                                font=ctk.CTkFont(size=12),
                                fg_color=THEME["accent"] if fkey == "all" else "gray25",
                                hover_color=THEME["accent_glow"],
                                corner_radius=14,
                                command=lambda k=fkey: self._shop_set_ownership_filter(k))
            btn.pack(side="left", padx=3)
            self._shop_filter_buttons[fkey] = btn

        # --- Scrollable item list ---
        self._shop_list = ctk.CTkScrollableFrame(self.shop_frame,
                                                  fg_color=THEME["bg_mid"],
                                                  corner_radius=10)
        self._shop_list.grid(row=2, column=1, padx=(0, 20), pady=(10, 20), sticky="nsew")
        self._shop_list.grid_columnconfigure(0, weight=1)
        self._shop_row_images = []   # prevent GC of PhotoImage objects
        self._shop_search_pending = None

    def _shop_select_category(self, cat):
        """Handle category button click — update highlight, subcategories, refresh."""
        self._shop_cat_var = cat
        self._shop_subcat_var = None

        # Update button highlights
        for c, btn in self._shop_cat_buttons.items():
            btn.configure(fg_color=THEME["accent"] if c == cat else "transparent")

        # Rebuild subcategory chips
        for w in self._shop_subcat_frame.winfo_children():
            w.destroy()

        if cat != "all":
            subcats = {}
            for item in self.shop_data.items:
                if item["category"] == cat and item["subcategory"]:
                    subcats[item["subcategory"]] = subcats.get(item["subcategory"], 0) + 1

            if subcats:
                ctk.CTkLabel(self._shop_subcat_frame, text="Subcategories",
                             font=ctk.CTkFont(size=11, weight="bold"),
                             text_color=THEME["text_dim"]).pack(anchor="w", pady=(0, 4))
                for sc, cnt in sorted(subcats.items(), key=lambda x: -x[1]):
                    btn = ctk.CTkButton(self._shop_subcat_frame,
                                        text=f"{sc} ({cnt})",
                                        fg_color="gray25", hover_color=THEME["accent"],
                                        height=26, font=ctk.CTkFont(size=11),
                                        anchor="w",
                                        command=lambda s=sc: self._shop_select_subcategory(s))
                    btn.pack(fill="x", pady=1)

        self._refresh_shop()

    def _shop_select_subcategory(self, subcat):
        """Toggle a subcategory chip on/off."""
        if self._shop_subcat_var == subcat:
            self._shop_subcat_var = None
        else:
            self._shop_subcat_var = subcat

        # Update chip highlights
        for w in self._shop_subcat_frame.winfo_children():
            if isinstance(w, ctk.CTkButton):
                is_active = w.cget("text").startswith(subcat)
                w.configure(fg_color=THEME["accent"] if is_active else "gray25")

        self._refresh_shop()

    def _shop_set_ownership_filter(self, fkey):
        """Set the ownership filter (all / owned / not_owned) and refresh."""
        self._shop_ownership_filter = fkey
        for k, btn in self._shop_filter_buttons.items():
            btn.configure(fg_color=THEME["accent"] if k == fkey else "gray25")
        self._refresh_shop()

    def _on_shop_search(self):
        """Debounced search — wait 250ms after last keystroke before refreshing."""
        if self._shop_search_pending:
            self.after_cancel(self._shop_search_pending)
        self._shop_search_pending = self.after(250, self._refresh_shop)

    def _build_owned_lookup(self):
        """Build a fast lookup dict from inventory for owned-badge matching."""
        owned = {}
        cur = self.conn.execute(
            "SELECT category, value, name, quantity FROM components"
        )
        for cat, val, name, qty in cur.fetchall():
            cat_low = cat.lower()
            if val:
                owned[(cat_low, val.lower())] = owned.get((cat_low, val.lower()), 0) + qty
            if name:
                owned[(cat_low, name.lower())] = owned.get((cat_low, name.lower()), 0) + qty
        return owned

    def _check_owned(self, shop_item, owned):
        """Return owned quantity if a shop item matches an inventory entry, else 0."""
        cat = shop_item["category"].lower()
        app_cat = SHOP_TO_APP_CATEGORY.get(cat, "other").lower()

        # Match by value string
        val = (shop_item.get("value") or "").lower()
        if val:
            qty = owned.get((app_cat, val), 0)
            if qty > 0:
                return qty

        # Match by part number against inventory names
        pn = (shop_item.get("part_number") or "").lower()
        if pn:
            qty = owned.get((app_cat, pn), 0)
            if qty > 0:
                return qty

        # For resistors: numeric comparison
        if cat == "resistor" and val:
            shop_val = inventory.parse_shop_value(val)
            if shop_val:
                for key, q in owned.items():
                    if key[0] == "resistor" and key[1]:
                        inv_val = inventory.parse_shop_value(key[1])
                        if inv_val and abs(inv_val - shop_val) < max(0.01, shop_val * 0.001):
                            return q
        return 0

    def _refresh_shop(self):
        """Populate the shop list with filtered items + owned badges."""
        # Clear previous rows
        for w in self._shop_list.winfo_children():
            w.destroy()
        self._shop_row_images = []
        self._shop_search_pending = None

        # Current filters
        cat = self._shop_cat_var
        subcat = self._shop_subcat_var
        search = self._shop_search_var.get().strip().lower() if hasattr(self, "_shop_search_var") else ""
        ownership = self._shop_ownership_filter if hasattr(self, "_shop_ownership_filter") else "all"

        # Build owned lookup early (needed for ownership filter + badges)
        owned = self._build_owned_lookup()

        # Filter items
        items = []
        for item in self.shop_data.items:
            if cat != "all" and item["category"] != cat:
                continue
            if subcat and item["subcategory"] != subcat:
                continue
            if search:
                blob = f"{item['part_number']} {item['value']} {item['subcategory']} {item['description']}".lower()
                if search not in blob:
                    continue
            # Ownership filter
            if ownership != "all":
                is_owned = self._check_owned(item, owned) > 0
                if ownership == "owned" and not is_owned:
                    continue
                if ownership == "not_owned" and is_owned:
                    continue
            items.append(item)

        self._shop_count_label.configure(
            text=f"Showing {min(len(items), 200)} of {len(items)} items"
            if len(items) > 200 else f"{len(items)} items"
        )

        if not items:
            ctk.CTkLabel(self._shop_list, text="No items match the current filters.",
                         font=ctk.CTkFont(size=14), text_color=THEME["text_dim"]).pack(pady=40)
            return

        MAX_DISPLAY = 200
        for idx, item in enumerate(items[:MAX_DISPLAY]):
            bg = THEME["bg_light"] if idx % 2 == 0 else THEME["bg_mid"]
            row = ctk.CTkFrame(self._shop_list, fg_color=bg, corner_radius=6, height=48)
            row.pack(fill="x", padx=4, pady=1)
            row.pack_propagate(False)

            # Part number (bold mono)
            ctk.CTkLabel(row, text=item["part_number"],
                         font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
                         text_color=THEME["text_main"]).pack(side="left", padx=(12, 8))

            # Value
            if item["value"]:
                ctk.CTkLabel(row, text=item["value"],
                             font=ctk.CTkFont(size=13),
                             text_color=THEME["accent_glow"]).pack(side="left", padx=(0, 8))

            # Resistor color bands
            if item["category"] == "resistor" and item["value"]:
                res_val = inventory.parse_shop_value(item["value"])
                if res_val:
                    colors = inventory.get_resistor_colors(res_val)
                    if colors:
                        img = self._create_color_band_image(colors)
                        self._shop_row_images.append(img)
                        ctk.CTkLabel(row, text="", image=img).pack(side="left", padx=(0, 8))

            # Subcategory badge
            if item["subcategory"]:
                ctk.CTkLabel(row, text=item["subcategory"],
                             font=ctk.CTkFont(size=10),
                             fg_color="gray30", corner_radius=4,
                             text_color=THEME["text_dim"]).pack(side="left", padx=(0, 8))

            # Description (fills remaining space)
            if item["description"]:
                ctk.CTkLabel(row, text=item["description"],
                             font=ctk.CTkFont(size=11),
                             text_color=THEME["text_dim"],
                             anchor="w").pack(side="left", fill="x", expand=True, padx=(0, 8))

            # Owned badge
            owned_qty = self._check_owned(item, owned)
            if owned_qty > 0:
                ctk.CTkLabel(row, text=f"×{owned_qty} owned",
                             font=ctk.CTkFont(size=11, weight="bold"),
                             text_color=THEME["success"]).pack(side="right", padx=(0, 12))

        if len(items) > MAX_DISPLAY:
            ctk.CTkLabel(self._shop_list,
                         text=f"… and {len(items) - MAX_DISPLAY} more. Use search to narrow results.",
                         font=ctk.CTkFont(size=12),
                         text_color=THEME["text_dim"]).pack(pady=10)

    def select_frame_by_name(self, name):
        for f in [self.add_frame, self.inventory_frame, self.stock_frame, self.dashboard_frame, self.shop_frame]: f.grid_forget()
        if name == "add":
            self.add_frame.grid(row=0, column=1, sticky="nsew")
        elif name == "inventory":
            self.inventory_frame.grid(row=0, column=1, sticky="nsew")
            self._refresh_inventory()
        elif name == "stock":
            self.stock_frame.grid(row=0, column=1, sticky="nsew")
            self._refresh_stock()
        elif name == "dashboard":
            self.dashboard_frame.grid(row=0, column=1, sticky="nsew")
            self._refresh_dashboard()
        elif name == "shop":
            self.shop_frame.grid(row=0, column=1, sticky="nsew")
            self._refresh_shop()

    def _on_quick_cat_select(self, cat):
        self.add_category.set(cat)
        for c, b in self.cat_buttons.items(): b.configure(fg_color=THEME["accent"] if c == cat else "gray25")
        self.value_dropdown.hide()
        self.name_dropdown.hide()
        self.add_name.focus_set()

    def _on_name_typing(self, *args):
        if self._dropdown_filling:
            return
        query = self.name_var.get().strip()
        if len(query) < 2:
            self.name_dropdown.hide()
            return

        # Search in current category first, then globally
        current_cat = self.add_category.get()
        results = self.shop_data.search(query, cat_filter=current_cat, limit=20)
        if not results:
            results = self.shop_data.search(query, limit=20)

        self.name_dropdown.source_label.configure(text="Part Search")
        self.name_dropdown.show(results, self.add_name)

    def _on_name_dropdown_select(self, item):
        """Auto-fill form when a name suggestion is clicked."""
        self._dropdown_filling = True
        try:
            self.name_var.set(f"{item['part_number']} {item['subcategory']}")
            cat = item['category'].lower()
            self.add_category.set(cat if cat in inventory.CATEGORIES else "other")
            self.add_value.delete(0, "end")
            self.add_value.insert(0, item['value'])
            self.add_notes.delete(0, "end")
            self.add_notes.insert(0, item['description'])
            self.add_qty.focus_set()
            self.add_qty.select_range(0, "end")
        finally:
            self._dropdown_filling = False

    def _save_component(self):
        name = self.add_name.get().strip()
        if not name: return
        data = {
            "name": name, "category": self.add_category.get(), "value": self.add_value.get(),
            "package": self.add_package.get(), "quantity": int(self.add_qty.get() or 1),
            "location": "Main Box", "notes": self.add_notes.get()
        }
        cid, merged = inventory.insert_component(self.conn, data)
        self.recent_list.insert(0, f"#{cid}: {name} x{data['quantity']}")
        self._clear_form()
        if merged:
            Toast(self, f"Merged into existing {name}")
        else:
            Toast(self, f"Saved {name}")

    def _clear_form(self):
        for e in [self.add_name, self.add_value, self.add_package, self.add_notes]: e.delete(0, "end")
        self.add_qty.delete(0, "end"); self.add_qty.insert(0, "1")
        self.value_dropdown.hide()
        self.name_dropdown.hide()

    def _open_resistor_helper(self):
        ResistorHelper(self, self._on_resistor_selected)

    def _on_resistor_selected(self, item):
        # Set name from part number and subcategory
        name = f"{item['part_number']} {item['subcategory']}".strip()
        self.name_var.set(name)
        
        # Switch to resistor category
        self.add_category.set("resistor")
        self._on_category_change("resistor")
        
        # Set value
        self.add_value.delete(0, "end")
        self.add_value.insert(0, item['value'])
        
        # Focus value or name
        self.add_value.focus_set()
        Toast(self, f"Applied: {item['value']}")

    def _create_color_band_image(self, colors):
        """Create a small PIL image showing resistor color bands."""
        w, h = 120, 26
        img = Image.new("RGB", (w, h), color=THEME["bg_light"])
        draw = ImageDraw.Draw(img)
        # Resistor body
        draw.rectangle([4, 3, w - 4, h - 3], fill="#c4a46c", outline="#a08050")
        # Draw bands
        n = len(colors)
        band_w = 6
        spacing = (w - 12) / (n + 1)
        for i, color_name in enumerate(colors):
            hex_c = inventory.RESISTOR_COLORS.get(color_name, {}).get("color", "#808080")
            bx = int(6 + spacing * (i + 0.5))
            draw.rectangle([bx, 5, bx + band_w, h - 5], fill=hex_c, outline="#333333")
        return ImageTk.PhotoImage(img)

    def _refresh_inventory(self):
        for i in self.inv_tree.get_children(): self.inv_tree.delete(i)
        self._color_band_images = []  # Clear old image references
        rows = inventory.search_components(self.conn, self.search_var.get())
        for r in rows:
            img = None
            if r["category"].lower() == "resistor":
                val = inventory.parse_shop_value(r["value"])
                colors = inventory.get_resistor_colors(val)
                if colors:
                    img = self._create_color_band_image(colors)
                    self._color_band_images.append(img)

            self.inv_tree.insert("", "end", image=img or "", values=(
                r["id"], r["name"], r["category"], r["value"],
                r["package"], r["quantity"], r["notes"]
            ))

    def _on_tree_double_click(self, event):
        sel = self.inv_tree.selection()
        if sel:
            v = self.inv_tree.item(sel[0], "values")
            EditDialog(self, {"id": int(v[0]), "name": v[1], "category": v[2], "value": v[3], "package": v[4], "quantity": int(v[5]), "notes": v[6]}, self._refresh_inventory)

    def _delete_selected_inventory(self):
        sel = self.inv_tree.selection()
        if not sel: return
        
        count = len(sel)
        msg = f"Delete {count} selected item(s)?" if count > 1 else "Delete selected item?"
        if messagebox.askyesno("Confirm", msg):
            for i in sel:
                cid = self.inv_tree.item(i)['values'][0]
                inventory.delete_component(self.conn, cid)
            Toast(self, f"Deleted {count} item(s)", color=THEME["danger"])
            self._refresh_inventory()

    def _refresh_stock(self):
        for i in self.stock_tree.get_children(): self.stock_tree.delete(i)
        for r in inventory.get_stock(self.conn): self.stock_tree.insert("", "end", values=r)

    def _export_csv(self):
        default_name = f"inventory_export_{datetime.now().strftime('%Y-%m-%d')}.csv"
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", 
            filetypes=[("CSV Files", "*.csv")],
            initialfile=default_name
        )
        if path:
            try:
                # The StringIO already contains the BOM and UTF-8 content
                content = inventory.export_csv(self.conn)
                with open(path, "w", encoding="utf-8-sig", newline="") as f:
                    f.write(content)
                Toast(self, "Export Successful")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export CSV: {e}")

    def _export_ai_markdown(self):
        default_name = "my_components.md"
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt")],
            initialfile=default_name
        )
        if path:
            try:
                content = inventory.export_ai_markdown(self.conn)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                Toast(self, f"AI export saved")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {e}")

    def _bind_shortcuts(self):
        self.bind("<Control-Key-1>", lambda e: self.select_frame_by_name("add"))
        self.bind("<Control-Key-2>", lambda e: self.select_frame_by_name("inventory"))
        self.bind("<Control-Key-3>", lambda e: self.select_frame_by_name("stock"))
        self.bind("<Control-Key-5>", lambda e: self.select_frame_by_name("shop"))

    def _on_category_change(self, choice):
        self.value_dropdown.hide()
        self.name_dropdown.hide()

    def _on_value_typing(self, *args):
        if self._dropdown_filling:
            return
        query = self.value_var.get().strip()
        if len(query) < 1:
            self.value_dropdown.hide()
            return

        category = self.add_category.get()
        results = self.shop_data.browse(category, query)
        self.value_dropdown.source_label.configure(text="DTU Shop")
        self.value_dropdown.show(results, self.add_value)

    def _on_value_dropdown_select(self, item):
        """Auto-fill form when a value suggestion is clicked."""
        self._dropdown_filling = True
        try:
            name = f"{item.get('part_number', '')} {item.get('subcategory', '')}".strip()
            self.name_var.set(name)
            shop_cat = item.get("category", "").lower()
            app_cat = SHOP_TO_APP_CATEGORY.get(shop_cat, "other")
            self.add_category.set(app_cat)
            self.add_value.delete(0, "end")
            self.add_value.insert(0, item.get("value", ""))
            self.add_notes.delete(0, "end")
            self.add_notes.insert(0, item.get("description", ""))
            self.add_qty.focus_set()
            self.add_qty.select_range(0, "end")
        finally:
            self._dropdown_filling = False

if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop()
