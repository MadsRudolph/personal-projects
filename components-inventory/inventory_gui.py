import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import os
import sys
from PIL import Image

# Import data layer from inventory.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inventory

# Appearance settings
ctk.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

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

class EditDialog(ctk.CTkToplevel):
    def __init__(self, parent, component_data, on_update):
        super().__init__(parent)
        self.title(f"Edit Component: {component_data['name']}")
        self.geometry("600x650")
        self.transient(parent)
        self.grab_set()
        
        self.component_data = component_data
        self.on_update = on_update
        self.conn = parent.conn
        
        self.grid_columnconfigure(0, weight=1)
        
        container = ctk.CTkFrame(self)
        container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        container.grid_columnconfigure(1, weight=1)
        
        # Form fields
        row = 0
        ctk.CTkLabel(container, text="Name:").grid(row=row, column=0, padx=20, pady=10, sticky="e")
        self.name_entry = ctk.CTkEntry(container, width=300)
        self.name_entry.grid(row=row, column=1, padx=20, pady=10, sticky="w")
        self.name_entry.insert(0, component_data['name'])
        
        row += 1
        ctk.CTkLabel(container, text="Category:").grid(row=row, column=0, padx=20, pady=10, sticky="e")
        self.cat_menu = ctk.CTkOptionMenu(container, values=inventory.CATEGORIES, command=self._on_category_change)
        self.cat_menu.grid(row=row, column=1, padx=20, pady=10, sticky="w")
        self.cat_menu.set(component_data['category'])
        
        row += 1
        self.value_label = ctk.CTkLabel(container, text="Value:")
        self.value_label.grid(row=row, column=0, padx=20, pady=10, sticky="e")
        self.value_entry = ctk.CTkEntry(container, width=300)
        self.value_entry.grid(row=row, column=1, padx=20, pady=10, sticky="w")
        self.value_entry.insert(0, component_data['value'] or "")
        
        row += 1
        self.pkg_label = ctk.CTkLabel(container, text="Package:")
        self.pkg_label.grid(row=row, column=0, padx=20, pady=10, sticky="e")
        self.pkg_entry = ctk.CTkEntry(container, width=300)
        self.pkg_entry.grid(row=row, column=1, padx=20, pady=10, sticky="w")
        self.pkg_entry.insert(0, component_data['package'] or "")
        
        row += 1
        ctk.CTkLabel(container, text="Quantity:").grid(row=row, column=0, padx=20, pady=10, sticky="e")
        self.qty_entry = ctk.CTkEntry(container, width=100)
        self.qty_entry.grid(row=row, column=1, padx=20, pady=10, sticky="w")
        self.qty_entry.insert(0, str(component_data['quantity']))
        
        row += 1
        ctk.CTkLabel(container, text="Location:").grid(row=row, column=0, padx=20, pady=10, sticky="e")
        self.loc_entry = ctk.CTkEntry(container, width=200)
        self.loc_entry.grid(row=row, column=1, padx=20, pady=10, sticky="w")
        self.loc_entry.insert(0, component_data['location'] or "")
        
        row += 1
        ctk.CTkLabel(container, text="Notes:").grid(row=row, column=0, padx=20, pady=10, sticky="e")
        self.notes_entry = ctk.CTkEntry(container, width=300)
        self.notes_entry.grid(row=row, column=1, padx=20, pady=10, sticky="w")
        self.notes_entry.insert(0, component_data['notes'] or "")
        
        # Action Buttons
        row += 1
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.grid(row=row, column=1, padx=20, pady=20, sticky="w")
        
        self.save_btn = ctk.CTkButton(btn_frame, text="Update", command=self._do_update)
        self.save_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.delete_btn = ctk.CTkButton(btn_frame, text="Delete", fg_color="#d32f2f", hover_color="#b71c1c", command=self._do_delete)
        self.delete_btn.grid(row=0, column=1)
        
        self._update_adaptive_fields()

    def _on_category_change(self, choice):
        self._update_adaptive_fields()

    def _update_adaptive_fields(self):
        cat = self.cat_menu.get()
        label_text, show_pkg = FIELD_CONFIG.get(cat, ("Description", False))
        self.value_label.configure(text=label_text + ":")
        if show_pkg:
            self.pkg_label.grid()
            self.pkg_entry.grid()
        else:
            self.pkg_label.grid_remove()
            self.pkg_entry.grid_remove()

    def _do_update(self):
        try:
            qty = int(self.qty_entry.get().strip() or 0)
        except ValueError:
            qty = 0
            
        data = {
            "name": self.name_entry.get().strip(),
            "category": self.cat_menu.get(),
            "value": self.value_entry.get().strip(),
            "package": self.pkg_entry.get().strip(),
            "quantity": qty,
            "location": self.loc_entry.get().strip(),
            "notes": self.notes_entry.get().strip(),
        }
        if not data["name"]:
            return
        
        inventory.update_component(self.conn, self.component_data['id'], data)
        self.on_update()
        self.destroy()

    def _do_delete(self):
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{self.component_data['name']}'?")
        if confirm:
            inventory.delete_component(self.conn, self.component_data['id'])
            self.on_update()
            self.destroy()

class InventoryApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Component Inventory Pro")
        self.geometry("1100x650")
        self.minsize(900, 550)

        self.conn = inventory.init_db()
        self.session_count = 0
        self.last_category = inventory.CATEGORIES[0]
        self.last_location = ""

        # set grid layout 1x2
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_content()
        
        self.select_frame_by_name("add")
        self._bind_shortcuts()

    def _build_sidebar(self):
        # Create navigation frame
        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(4, weight=1)

        self.navigation_frame_label = ctk.CTkLabel(self.navigation_frame, text="  Inventory Pro", 
                                                 compound="left", font=ctk.CTkFont(size=20, weight="bold"))
        self.navigation_frame_label.grid(row=0, column=0, padx=20, pady=20)

        self.add_btn_nav = ctk.CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10, text="Add Component",
                                           fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                           anchor="w", command=self.add_button_event)
        self.add_btn_nav.grid(row=1, column=0, sticky="ew")

        self.inv_btn_nav = ctk.CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10, text="Inventory",
                                              fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                              anchor="w", command=self.inv_button_event)
        self.inv_btn_nav.grid(row=2, column=0, sticky="ew")

        self.stock_btn_nav = ctk.CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10, text="Stock Summary",
                                              fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                              anchor="w", command=self.stock_button_event)
        self.stock_btn_nav.grid(row=3, column=0, sticky="ew")

        self.appearance_mode_menu = ctk.CTkOptionMenu(self.navigation_frame, values=["Light", "Dark", "System"],
                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_menu.grid(row=5, column=0, padx=20, pady=20, sticky="s")
        self.appearance_mode_menu.set("Dark")

    def _build_main_content(self):
        # Create Add Frame
        self.add_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.add_frame.grid_columnconfigure(0, weight=1)
        self._build_add_content()

        # Create Inventory Frame
        self.inventory_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.inventory_frame.grid_columnconfigure(0, weight=1)
        self.inventory_frame.grid_rowconfigure(1, weight=1)
        self._build_inventory_content()

        # Create Stock Frame
        self.stock_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stock_frame.grid_columnconfigure(0, weight=1)
        self.stock_frame.grid_rowconfigure(2, weight=1)
        self._build_stock_content()

    def _build_add_content(self):
        # Title
        label = ctk.CTkLabel(self.add_frame, text="Add New Component", font=ctk.CTkFont(size=24, weight="bold"))
        label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Form Container
        self.form_container = ctk.CTkFrame(self.add_frame)
        self.form_container.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.form_container.grid_columnconfigure(1, weight=1)

        # Name
        ctk.CTkLabel(self.form_container, text="Name:").grid(row=0, column=0, padx=20, pady=15, sticky="e")
        self.add_name = ctk.CTkEntry(self.form_container, placeholder_text="e.g. 10k resistor, NE555...", width=400)
        self.add_name.grid(row=0, column=1, padx=20, pady=15, sticky="w")

        # Category
        ctk.CTkLabel(self.form_container, text="Category:").grid(row=1, column=0, padx=20, pady=15, sticky="e")
        self.add_category = ctk.CTkOptionMenu(self.form_container, values=inventory.CATEGORIES, command=self._on_category_change)
        self.add_category.grid(row=1, column=1, padx=20, pady=15, sticky="w")
        self.add_category.set(self.last_category)

        # Value
        self.value_label = ctk.CTkLabel(self.form_container, text="Value:")
        self.value_label.grid(row=2, column=0, padx=20, pady=15, sticky="e")
        self.add_value = ctk.CTkEntry(self.form_container, placeholder_text="Value", width=400)
        self.add_value.grid(row=2, column=1, padx=20, pady=15, sticky="w")

        # Package
        self.pkg_label = ctk.CTkLabel(self.form_container, text="Package:")
        self.pkg_label.grid(row=3, column=0, padx=20, pady=15, sticky="e")
        self.add_package = ctk.CTkEntry(self.form_container, placeholder_text="Package", width=400)
        self.add_package.grid(row=3, column=1, padx=20, pady=15, sticky="w")

        # Qty and Location side by side
        ql_frame = ctk.CTkFrame(self.form_container, fg_color="transparent")
        ql_frame.grid(row=4, column=1, padx=20, pady=15, sticky="w")
        
        ctk.CTkLabel(ql_frame, text="Quantity:").grid(row=0, column=0, padx=(0, 10), pady=0)
        self.add_qty = ctk.CTkEntry(ql_frame, width=80)
        self.add_qty.grid(row=0, column=1, padx=(0, 20), pady=0)
        self.add_qty.insert(0, "1")

        ctk.CTkLabel(ql_frame, text="Location:").grid(row=0, column=2, padx=(0, 10), pady=0)
        self.add_location = ctk.CTkEntry(ql_frame, width=120, placeholder_text="e.g. A1, Bin 4")
        self.add_location.grid(row=0, column=3, pady=0)

        # Notes
        ctk.CTkLabel(self.form_container, text="Notes:").grid(row=5, column=0, padx=20, pady=15, sticky="e")
        self.add_notes = ctk.CTkEntry(self.form_container, placeholder_text="Optional notes", width=400)
        self.add_notes.grid(row=5, column=1, padx=20, pady=15, sticky="w")

        # Buttons
        btn_frame = ctk.CTkFrame(self.form_container, fg_color="transparent")
        btn_frame.grid(row=6, column=1, padx=20, pady=25, sticky="w")

        self.save_btn = ctk.CTkButton(btn_frame, text="Save Component", command=self._save_component, font=ctk.CTkFont(weight="bold"), height=35)
        self.save_btn.grid(row=0, column=0, padx=(0, 10))

        self.clear_btn = ctk.CTkButton(btn_frame, text="Clear Form", fg_color="transparent", border_width=1, command=self._clear_form, height=35)
        self.clear_btn.grid(row=0, column=1)

        # Status Label in Add Tab
        self.add_status_label = ctk.CTkLabel(self.add_frame, text="Ready", text_color="gray")
        self.add_status_label.grid(row=2, column=0, padx=25, pady=10, sticky="w")

        self._update_adaptive_fields()

    def _build_inventory_content(self):
        # Header Tools
        header = ctk.CTkFrame(self.inventory_frame, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text="Inventory List", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w")
        
        search_box = ctk.CTkFrame(header)
        search_box.grid(row=0, column=2, sticky="e")
        
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_inventory())
        self.search_entry = ctk.CTkEntry(search_box, placeholder_text="Search components...", width=300, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=0, padx=10, pady=10)

        self.filter_category = ctk.CTkOptionMenu(search_box, values=["All"] + inventory.CATEGORIES, command=lambda _: self._refresh_inventory())
        self.filter_category.grid(row=0, column=1, padx=10, pady=10)
        self.filter_category.set("All")

        # Treeview Styles
        tree_container = ctk.CTkFrame(self.inventory_frame)
        tree_container.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", 
                        background="#2b2b2b", 
                        foreground="white", 
                        rowheight=30, 
                        fieldbackground="#2b2b2b",
                        borderwidth=0)
        style.map("Treeview", background=[('selected', '#1f538d')])
        style.configure("Treeview.Heading", background="#333333", foreground="white", relief="flat", font=('Arial', 10, 'bold'))
        style.map("Treeview.Heading", background=[('active', '#3f3f3f')])

        cols = ("id", "name", "category", "value", "package", "qty", "location", "notes")
        self.inv_tree = ttk.Treeview(tree_container, columns=cols, show="headings", style="Treeview")
        
        col_widths = {"id": 50, "name": 200, "category": 100, "value": 120,
                      "package": 100, "qty": 60, "location": 80, "notes": 250}
        for col in cols:
            self.inv_tree.heading(col, text=col.capitalize() if col != "qty" else "Qty")
            self.inv_tree.column(col, width=col_widths.get(col, 100), anchor="center" if col in ("id", "qty") else "w")

        scrollbar = ctk.CTkScrollbar(tree_container, orientation="vertical", command=self.inv_tree.yview)
        self.inv_tree.configure(yscrollcommand=scrollbar.set)

        self.inv_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.inv_tree.bind("<Double-1>", self._on_tree_double_click)

    def _build_stock_content(self):
        # Header Tools
        header = ctk.CTkFrame(self.stock_frame, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text="Stock Summary", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w")
        
        self.export_btn = ctk.CTkButton(header, text="Export CSV", command=self._export_csv, fg_color="#333333", border_width=1, height=35)
        self.export_btn.grid(row=0, column=2, sticky="e")

        # Dashboard View (Cards)
        self.stats_frame = ctk.CTkFrame(self.stock_frame, fg_color="transparent")
        self.stats_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        # Layout metrics will be added here dynamically in _refresh_stock

        # Detailed Table
        self.stock_tree_container = ctk.CTkFrame(self.stock_frame)
        self.stock_tree_container.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.stock_tree_container.grid_columnconfigure(0, weight=1)
        self.stock_tree_container.grid_rowconfigure(0, weight=1)
        
        cols = ("category", "items", "total_qty")
        self.stock_tree = ttk.Treeview(self.stock_tree_container, columns=cols, show="headings", style="Treeview")
        self.stock_tree.heading("category", text="Category")
        self.stock_tree.heading("items", text="Unique Items")
        self.stock_tree.heading("total_qty", text="Total Stock")
        for col in cols:
            self.stock_tree.column(col, anchor="center")
        
        self.stock_tree.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ctk.CTkScrollbar(self.stock_tree_container, orientation="vertical", command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

    # ── Sidebar Events ────────────────────────────────────────────────

    def select_frame_by_name(self, name):
        # set button color for selected button
        self.add_btn_nav.configure(fg_color=("gray75", "gray25") if name == "add" else "transparent")
        self.inv_btn_nav.configure(fg_color=("gray75", "gray25") if name == "inventory" else "transparent")
        self.stock_btn_nav.configure(fg_color=("gray75", "gray25") if name == "stock" else "transparent")

        # show selected frame
        if name == "add":
            self.add_frame.grid(row=0, column=1, sticky="nsew")
            self.add_name.focus_set()
        else:
            self.add_frame.grid_forget()
        
        if name == "inventory":
            self.inventory_frame.grid(row=0, column=1, sticky="nsew")
            self._refresh_inventory()
        else:
            self.inventory_frame.grid_forget()
        
        if name == "stock":
            self.stock_frame.grid(row=0, column=1, sticky="nsew")
            self._refresh_stock()
        else:
            self.stock_frame.grid_forget()

    def add_button_event(self):
        self.select_frame_by_name("add")

    def inv_button_event(self):
        self.select_frame_by_name("inventory")

    def stock_button_event(self):
        self.select_frame_by_name("stock")

    def change_appearance_mode_event(self, new_appearance_mode):
        ctk.set_appearance_mode(new_appearance_mode)

    # ── Add Tab Logic ────────────────────────────────────────────────

    def _on_category_change(self, choice):
        self._update_adaptive_fields()

    def _update_adaptive_fields(self):
        cat = self.add_category.get()
        label_text, show_pkg = FIELD_CONFIG.get(cat, ("Description", False))
        self.value_label.configure(text=label_text + ":")

        if show_pkg:
            self.pkg_label.grid()
            self.add_package.grid()
        else:
            self.pkg_label.grid_remove()
            self.add_package.grid_remove()

    def _save_component(self, event=None):
        name = self.add_name.get().strip()
        if not name:
            self.add_name.focus_set()
            self.add_status_label.configure(text="Name is required", text_color="red")
            return

        category = self.add_category.get()
        location = self.add_location.get().strip()
        if not location:
            self.add_location.focus_set()
            self.add_status_label.configure(text="Location is required", text_color="red")
            return

        qty_str = self.add_qty.get().strip() or "1"
        try:
            qty = int(qty_str)
        except ValueError:
            qty = 1

        data = {
            "name": name,
            "category": category,
            "value": self.add_value.get().strip(),
            "package": self.add_package.get().strip(),
            "quantity": qty,
            "location": location,
            "notes": self.add_notes.get().strip(),
        }

        cid = inventory.insert_component(self.conn, data)
        self.session_count += 1
        self.last_category = category
        self.last_location = location

        self.add_status_label.configure(
            text=f"Saved #{cid}: {name} (Total this session: {self.session_count})",
            text_color="green"
        )

        # Clear form, keep sticky defaults
        self.add_name.delete(0, "end")
        self.add_value.delete(0, "end")
        self.add_package.delete(0, "end")
        self.add_qty.delete(0, "end")
        self.add_qty.insert(0, "1")
        self.add_notes.delete(0, "end")
        self.add_name.focus_set()

    def _clear_form(self, event=None):
        self.add_name.delete(0, "end")
        self.add_value.delete(0, "end")
        self.add_package.delete(0, "end")
        self.add_qty.delete(0, "end")
        self.add_qty.insert(0, "1")
        self.add_location.delete(0, "end")
        self.add_notes.delete(0, "end")
        self.add_name.focus_set()
        self.add_status_label.configure(text="Form cleared", text_color="gray")

    # ── Inventory Logic ──────────────────────────────────────────────

    def _refresh_inventory(self):
        for item in self.inv_tree.get_children():
            self.inv_tree.delete(item)

        query = self.search_var.get().strip()
        cat_filter = self.filter_category.get()

        if query:
            rows = inventory.search_components(self.conn, query)
        elif cat_filter != "All":
            rows = inventory.list_by_category(self.conn, cat_filter)
        else:
            cur = self.conn.execute("SELECT * FROM components ORDER BY category, name")
            rows = [inventory._row_to_dict(r, cur) for r in cur.fetchall()]

        if query and cat_filter != "All":
            rows = [r for r in rows if r["category"].lower() == cat_filter.lower()]

        for r in rows:
            self.inv_tree.insert("", "end", values=(
                r["id"], r["name"], r["category"],
                r.get("value") or "", r.get("package") or "",
                r["quantity"], r.get("location") or "",
                r.get("notes") or "",
            ))

    def _on_tree_double_click(self, event):
        sel = self.inv_tree.selection()
        if not sel:
            return
        values = self.inv_tree.item(sel[0], "values")
        
        # Map values back to dict for the dialog
        comp_data = {
            "id": int(values[0]),
            "name": values[1],
            "category": values[2],
            "value": values[3],
            "package": values[4],
            "quantity": int(values[5]),
            "location": values[6],
            "notes": values[7]
        }
        
        EditDialog(self, comp_data, self._refresh_inventory)

    # ── Stock Logic ──────────────────────────────────────────────────

    def _refresh_stock(self):
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)

        stock = inventory.get_stock(self.conn)
        total_items = 0
        total_qty = 0
        for cat, items, qty in stock:
            self.stock_tree.insert("", "end", values=(cat, items, qty))
            total_items += items
            total_qty += qty
        
        # Update Dashboard Stats
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        metrics = [
            ("Total Unique Components", total_items, "#1f538d"),
            ("Total Stock Volume", total_qty, "#2fa572"),
            ("Top Categories", len(stock), "#8d6e63")
        ]

        for i, (label, val, color) in enumerate(metrics):
            card = ctk.CTkFrame(self.stats_frame, width=220, height=80, border_width=1, border_color=color)
            card.grid(row=0, column=i, padx=10, pady=5)
            card.grid_propagate(False)
            ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=11)).pack(pady=(10, 0))
            ctk.CTkLabel(card, text=str(val), font=ctk.CTkFont(size=20, weight="bold"), text_color=color).pack()

    def _export_csv(self, event=None):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="inventory_export.csv",
        )
        if not filepath:
            return
        output = inventory.export_csv(self.conn)
        with open(filepath, "w", newline="") as f:
            f.write(output)

    # ── Shortcuts ───────────────────────────────────────────────────

    def _bind_shortcuts(self):
        self.bind("<Control-Key-1>", lambda e: self.select_frame_by_name("add"))
        self.bind("<Control-Key-2>", lambda e: self.select_frame_by_name("inventory"))
        self.bind("<Control-Key-3>", lambda e: self.select_frame_by_name("stock"))
        self.bind("<Return>", self._on_enter)

    def _on_enter(self, event):
        # Trigger save if we're in the add frame
        focused = self.focus_get()
        if focused in (self.add_name, self.add_value, self.add_package, self.add_qty, self.add_location, self.add_notes):
            self._save_component()
            return "break"

    def destroy(self):
        if hasattr(self, 'conn'):
            self.conn.close()
        super().destroy()

if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop()
