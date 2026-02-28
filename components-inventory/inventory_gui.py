import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys

# Import data layer from inventory.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inventory


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


class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Component Inventory")
        self.geometry("780x520")
        self.minsize(600, 400)

        self.conn = inventory.init_db()
        self.session_count = 0
        self.last_category = inventory.CATEGORIES[0]
        self.last_location = ""

        self._build_ui()
        self._bind_shortcuts()
        self.show_tab("add")

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self):
        # Tab buttons
        tab_bar = ttk.Frame(self)
        tab_bar.pack(fill="x", padx=8, pady=(8, 0))

        self.tab_buttons = {}
        for label in ("Add", "Inventory", "Stock"):
            btn = ttk.Button(tab_bar, text=label,
                             command=lambda l=label: self.show_tab(l.lower()))
            btn.pack(side="left", padx=(0, 4))
            self.tab_buttons[label.lower()] = btn

        # Content container
        self.content = ttk.Frame(self)
        self.content.pack(fill="both", expand=True, padx=8, pady=4)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief="sunken",
                               anchor="w", padding=(6, 2))
        status_bar.pack(fill="x", side="bottom", padx=8, pady=(0, 8))

        # Build each tab (hidden initially)
        self.tabs = {}
        self._build_add_tab()
        self._build_inventory_tab()
        self._build_stock_tab()

    def _build_add_tab(self):
        frame = ttk.Frame(self.content)
        self.tabs["add"] = frame

        # Form grid
        form = ttk.LabelFrame(frame, text="Add Component", padding=12)
        form.pack(fill="both", expand=True, pady=4)

        row = 0
        # Name
        ttk.Label(form, text="Name:").grid(row=row, column=0, sticky="e", padx=(0, 8), pady=4)
        self.add_name = ttk.Entry(form, width=40)
        self.add_name.grid(row=row, column=1, sticky="ew", pady=4)

        # Category
        row += 1
        ttk.Label(form, text="Category:").grid(row=row, column=0, sticky="e", padx=(0, 8), pady=4)
        self.add_category = ttk.Combobox(form, values=inventory.CATEGORIES, state="readonly", width=37)
        self.add_category.grid(row=row, column=1, sticky="ew", pady=4)
        self.add_category.set(self.last_category)
        self.add_category.bind("<<ComboboxSelected>>", self._on_category_change)

        # Value (adaptive label)
        row += 1
        self.value_label_var = tk.StringVar(value="Value:")
        self.value_label = ttk.Label(form, textvariable=self.value_label_var)
        self.value_label.grid(row=row, column=0, sticky="e", padx=(0, 8), pady=4)
        self.add_value = ttk.Entry(form, width=40)
        self.add_value.grid(row=row, column=1, sticky="ew", pady=4)

        # Package (hideable)
        row += 1
        self.pkg_label = ttk.Label(form, text="Package:")
        self.pkg_label.grid(row=row, column=0, sticky="e", padx=(0, 8), pady=4)
        self.add_package = ttk.Entry(form, width=40)
        self.add_package.grid(row=row, column=1, sticky="ew", pady=4)
        self.pkg_row = row

        # Quantity
        row += 1
        ttk.Label(form, text="Quantity:").grid(row=row, column=0, sticky="e", padx=(0, 8), pady=4)
        self.add_qty = ttk.Entry(form, width=10)
        self.add_qty.grid(row=row, column=1, sticky="w", pady=4)
        self.add_qty.insert(0, "1")

        # Location
        row += 1
        ttk.Label(form, text="Location:").grid(row=row, column=0, sticky="e", padx=(0, 8), pady=4)
        self.add_location = ttk.Entry(form, width=20)
        self.add_location.grid(row=row, column=1, sticky="w", pady=4)

        # Notes
        row += 1
        ttk.Label(form, text="Notes:").grid(row=row, column=0, sticky="e", padx=(0, 8), pady=4)
        self.add_notes = ttk.Entry(form, width=40)
        self.add_notes.grid(row=row, column=1, sticky="ew", pady=4)

        # Save button
        row += 1
        self.save_btn = ttk.Button(form, text="Save & Next  (Enter)", command=self._save_component)
        self.save_btn.grid(row=row, column=0, columnspan=2, pady=(12, 4))

        form.columnconfigure(1, weight=1)

        # Apply initial adaptive fields
        self._update_adaptive_fields()

    def _build_inventory_tab(self):
        frame = ttk.Frame(self.content)
        self.tabs["inventory"] = frame

        # Search bar
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill="x", pady=(4, 4))

        ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_inventory())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side="left", padx=(0, 8))

        ttk.Label(search_frame, text="Category:").pack(side="left", padx=(0, 4))
        self.filter_category = ttk.Combobox(search_frame,
                                            values=["All"] + inventory.CATEGORIES,
                                            state="readonly", width=14)
        self.filter_category.set("All")
        self.filter_category.bind("<<ComboboxSelected>>", lambda *_: self._refresh_inventory())
        self.filter_category.pack(side="left")

        # Treeview
        cols = ("id", "name", "category", "value", "package", "qty", "location", "notes")
        self.inv_tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")

        col_widths = {"id": 40, "name": 140, "category": 80, "value": 100,
                      "package": 80, "qty": 45, "location": 60, "notes": 120}
        for col in cols:
            self.inv_tree.heading(col, text=col.capitalize() if col != "qty" else "Qty")
            self.inv_tree.column(col, width=col_widths.get(col, 80), minwidth=30)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.inv_tree.yview)
        self.inv_tree.configure(yscrollcommand=scrollbar.set)

        self.inv_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.inv_tree.bind("<Double-1>", self._on_tree_double_click)

    def _build_stock_tab(self):
        frame = ttk.Frame(self.content)
        self.tabs["stock"] = frame

        # Stock treeview
        cols = ("category", "items", "total_qty")
        self.stock_tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="none")
        self.stock_tree.heading("category", text="Category")
        self.stock_tree.heading("items", text="Items")
        self.stock_tree.heading("total_qty", text="Total Qty")
        self.stock_tree.column("category", width=160)
        self.stock_tree.column("items", width=80, anchor="e")
        self.stock_tree.column("total_qty", width=100, anchor="e")
        self.stock_tree.pack(fill="both", expand=True, pady=(4, 4))

        # Export button
        ttk.Button(frame, text="Export to CSV  (Ctrl+E)", command=self._export_csv).pack(pady=(4, 4))

    # ── Tab switching ────────────────────────────────────────────────

    def show_tab(self, name):
        for tab_frame in self.tabs.values():
            tab_frame.pack_forget()
        self.tabs[name].pack(fill="both", expand=True)

        if name == "add":
            self.add_name.focus_set()
        elif name == "inventory":
            self._refresh_inventory()
        elif name == "stock":
            self._refresh_stock()

    # ── Add tab logic ────────────────────────────────────────────────

    def _on_category_change(self, event=None):
        self._update_adaptive_fields()

    def _update_adaptive_fields(self):
        cat = self.add_category.get()
        label_text, show_pkg = FIELD_CONFIG.get(cat, ("Description", False))
        self.value_label_var.set(label_text + ":")

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
            self.status_var.set("Name is required")
            return

        category = self.add_category.get()
        location = self.add_location.get().strip()
        if not location:
            self.add_location.focus_set()
            self.status_var.set("Location is required")
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

        val_str = f" {data['value']}" if data["value"] else ""
        pkg_str = f" [{data['package']}]" if data["package"] else ""
        self.status_var.set(
            f"Saved #{cid}: {name}{val_str}{pkg_str} x{qty} @ {location}  "
            f"({self.session_count} added this session)"
        )

        # Clear form, keep sticky defaults
        self.add_name.delete(0, "end")
        self.add_value.delete(0, "end")
        self.add_package.delete(0, "end")
        self.add_qty.delete(0, "end")
        self.add_qty.insert(0, "1")
        self.add_notes.delete(0, "end")
        # Keep category and location as sticky defaults
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
        self.status_var.set("Form cleared")

    # ── Inventory tab logic ──────────────────────────────────────────

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

        # Apply category filter to search results too
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
        comp_id = int(values[0])
        comp_name = values[1]
        current_qty = values[5]

        dialog = tk.Toplevel(self)
        dialog.title(f"Update Quantity — {comp_name}")
        dialog.geometry("300x120")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text=f"Component: {comp_name}").pack(pady=(12, 4))
        qty_frame = ttk.Frame(dialog)
        qty_frame.pack(pady=4)
        ttk.Label(qty_frame, text="New quantity:").pack(side="left", padx=(0, 4))
        qty_entry = ttk.Entry(qty_frame, width=10)
        qty_entry.pack(side="left")
        qty_entry.insert(0, str(current_qty))
        qty_entry.select_range(0, "end")
        qty_entry.focus_set()

        def do_update(e=None):
            try:
                new_qty = int(qty_entry.get())
            except ValueError:
                return
            inventory.update_quantity(self.conn, comp_id, new_qty)
            self.status_var.set(f"Updated #{comp_id} ({comp_name}) quantity to {new_qty}")
            dialog.destroy()
            self._refresh_inventory()

        qty_entry.bind("<Return>", do_update)
        ttk.Button(dialog, text="Update", command=do_update).pack(pady=8)

    # ── Stock tab logic ──────────────────────────────────────────────

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
        self.stock_tree.insert("", "end", values=("TOTAL", total_items, total_qty))

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
        self.status_var.set(f"Exported to {filepath}")

    # ── Keyboard shortcuts ───────────────────────────────────────────

    def _bind_shortcuts(self):
        self.bind("<Return>", self._on_enter)
        self.bind("<Escape>", self._clear_form)
        self.bind("<Control-Key-1>", lambda e: self.show_tab("add"))
        self.bind("<Control-Key-2>", lambda e: self.show_tab("inventory"))
        self.bind("<Control-Key-3>", lambda e: self.show_tab("stock"))
        self.bind("<Control-e>", self._export_csv)
        self.bind("<Control-E>", self._export_csv)

    def _on_enter(self, event):
        # Only trigger save if we're on the add tab and focus is in a form widget
        focused = self.focus_get()
        add_widgets = (self.add_name, self.add_value, self.add_package,
                       self.add_qty, self.add_location, self.add_notes,
                       self.add_category, self.save_btn)
        if focused in add_widgets:
            self._save_component()
            return "break"

    # ── Cleanup ──────────────────────────────────────────────────────

    def destroy(self):
        self.conn.close()
        super().destroy()


if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop()
