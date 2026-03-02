# Component Browser Panel Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a reactive chip-grid browser panel to the bottom of the Add tab that shows clickable components from the DTU shop CSV or existing inventory, filtered by category and value input.

**Architecture:** New `ComponentBrowser` widget class embedded in `inventory_gui.py`. Data fetching via new helper methods on the existing `ShopData` class and a new `get_inventory_by_category()` function in `inventory.py`. The browser reacts to category changes and value field typing, rendering chips in a scrollable wrapping grid.

**Tech Stack:** Python 3.11, customtkinter, tkinter Canvas (for scrollable chip grid), SQLite3, existing `inventory.py` data layer.

---

### Task 1: Data layer — category-filtered browse helpers

**Files:**
- Modify: `components-inventory/inventory.py:380-398` (ShopData.search)
- Modify: `components-inventory/inventory.py:266-269` (list_by_category)
- Create: `components-inventory/test_browser_data.py`

The existing `ShopData.search()` requires a text query — we need a mode that returns all items in a category (for initial browse). The existing `list_by_category()` works but returns dicts with DB column names; we need consistent shape.

**Step 1: Write test for browse_by_category on ShopData**

```python
# test_browser_data.py
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inventory

def test_shop_browse_by_category_returns_items():
    shop = inventory.ShopData()
    results = shop.browse("resistor")
    assert len(results) > 0
    assert all(r["category"] == "resistor" for r in results)

def test_shop_browse_with_value_filter():
    shop = inventory.ShopData()
    results = shop.browse("resistor", value_filter="4.7")
    assert len(results) > 0
    # All results should contain "4.7" somewhere in value/part_number/subcategory
    for r in results:
        combined = f"{r['value']} {r['part_number']} {r['subcategory']}".lower()
        assert "4.7" in combined or "4k7" in combined

def test_shop_browse_empty_category_returns_empty():
    shop = inventory.ShopData()
    results = shop.browse("nonexistent_category")
    assert results == []

def test_shop_browse_ic_maps_correctly():
    """Shop CSV uses 'ic' lowercase, app uses 'IC' — browse should handle both."""
    shop = inventory.ShopData()
    results_lower = shop.browse("ic")
    results_upper = shop.browse("IC")
    assert len(results_lower) > 0
    assert len(results_lower) == len(results_upper)

def test_shop_browse_led_maps_correctly():
    shop = inventory.ShopData()
    results = shop.browse("LED")
    assert len(results) > 0

def test_inventory_browse_by_category():
    """Test fetching inventory items by category."""
    conn = inventory.init_db(":memory:")
    inventory.insert_component(conn, {"name": "TL072", "category": "IC", "value": "", "quantity": 1})
    inventory.insert_component(conn, {"name": "100nF", "category": "capacitor", "value": "100nF", "quantity": 5})

    results = inventory.browse_inventory(conn, "IC")
    assert len(results) == 1
    assert results[0]["name"] == "TL072"

    results = inventory.browse_inventory(conn, "capacitor")
    assert len(results) == 1
    conn.close()

def test_inventory_browse_with_value_filter():
    conn = inventory.init_db(":memory:")
    inventory.insert_component(conn, {"name": "10k Resistor", "category": "resistor", "value": "10k", "quantity": 1})
    inventory.insert_component(conn, {"name": "4.7k Resistor", "category": "resistor", "value": "4.7k", "quantity": 1})
    inventory.insert_component(conn, {"name": "100k Resistor", "category": "resistor", "value": "100k", "quantity": 1})

    results = inventory.browse_inventory(conn, "resistor", value_filter="4.7")
    assert len(results) == 1
    assert results[0]["value"] == "4.7k"
    conn.close()

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
```

**Step 2: Run tests to verify they fail**

Run: `cd components-inventory && python -m pytest test_browser_data.py -v`
Expected: FAIL — `ShopData` has no `browse` method, `browse_inventory` doesn't exist.

**Step 3: Implement `ShopData.browse()` method**

Add after `ShopData.search()` (line ~398 in `inventory.py`):

```python
def browse(self, category, value_filter=None, limit=None):
    """Return all items in a category, optionally filtered by value substring."""
    cat = category.lower()
    results = []
    for item in self.items:
        if item["category"] != cat:
            continue
        if value_filter:
            combined = f"{item['value']} {item['part_number']} {item['subcategory']}".lower()
            if value_filter.lower() not in combined:
                continue
        results.append(item)
        if limit is not None and len(results) >= limit:
            break
    return results
```

**Step 4: Implement `browse_inventory()` function**

Add after `list_by_category()` (line ~269 in `inventory.py`):

```python
def browse_inventory(conn, category, value_filter=None):
    """Return inventory items by category with optional value filter."""
    if value_filter:
        sql = """SELECT * FROM components
                 WHERE LOWER(category) = LOWER(?)
                 AND (value LIKE ? OR name LIKE ?)
                 ORDER BY name"""
        pattern = f"%{value_filter}%"
        cur = conn.execute(sql, (category, pattern, pattern))
    else:
        sql = "SELECT * FROM components WHERE LOWER(category) = LOWER(?) ORDER BY name"
        cur = conn.execute(sql, (category,))
    return [_row_to_dict(r, cur) for r in cur.fetchall()]
```

**Step 5: Run tests to verify they pass**

Run: `cd components-inventory && python -m pytest test_browser_data.py -v`
Expected: All 8 tests PASS.

**Step 6: Commit**

```bash
git add components-inventory/inventory.py components-inventory/test_browser_data.py
git commit -m "feat: add browse helpers for component browser panel"
```

---

### Task 2: ComponentBrowser widget — scrollable chip grid

**Files:**
- Modify: `components-inventory/inventory_gui.py` (add ComponentBrowser class before InventoryApp)

This is the self-contained widget. It manages its own scrollable canvas, chip rendering, toggle state, and count badge. It accepts a callback for chip clicks.

**Step 1: Add the ComponentBrowser class**

Insert before the `class InventoryApp` definition (line 322) in `inventory_gui.py`:

```python
# --- Category mapping: shop CSV lowercase → app CATEGORIES ---
SHOP_TO_APP_CATEGORY = {
    "resistor": "resistor", "capacitor": "capacitor", "inductor": "inductor",
    "diode": "diode", "transistor": "transistor", "ic": "IC", "connector": "connector",
    "led": "LED", "crystal": "crystal", "switch": "switch",
    "encoder": "other", "hardware": "other", "ir": "other",
    "optocoupler": "other", "photodiode": "other", "sensor": "other",
}

# First-band color for resistor chip left-border hint
RESISTOR_BAND_HINT = {}  # populated lazily


class ComponentBrowser(ctk.CTkFrame):
    """Scrollable chip-grid browser for the Add tab bottom panel."""

    CHIPS_PER_PAGE = 100

    def __init__(self, parent, shop_data, conn, on_chip_click, **kwargs):
        super().__init__(parent, fg_color=THEME["bg_mid"], corner_radius=15, **kwargs)
        self.shop_data = shop_data
        self.conn = conn
        self.on_chip_click = on_chip_click
        self.source = "shop"  # "shop" or "inventory"
        self.current_items = []
        self.displayed_count = 0

        # --- Header row ---
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(10, 5))

        ctk.CTkLabel(header, text="Component Browser",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=THEME["accent_glow"]).pack(side="left")

        self.count_label = ctk.CTkLabel(header, text="", text_color=THEME["text_dim"],
                                        font=ctk.CTkFont(size=11))
        self.count_label.pack(side="right", padx=(10, 0))

        toggle_frame = ctk.CTkFrame(header, fg_color="transparent")
        toggle_frame.pack(side="right")
        self.shop_btn = ctk.CTkButton(toggle_frame, text="Shop", width=80, height=28,
                                      font=ctk.CTkFont(size=12),
                                      fg_color=THEME["accent"], command=lambda: self._set_source("shop"))
        self.shop_btn.pack(side="left", padx=(0, 2))
        self.inv_btn = ctk.CTkButton(toggle_frame, text="My Inventory", width=100, height=28,
                                     font=ctk.CTkFont(size=12),
                                     fg_color="gray25", command=lambda: self._set_source("inventory"))
        self.inv_btn.pack(side="left")

        # --- Scrollable chip area ---
        self.canvas = tk.Canvas(self, bg=THEME["bg_mid"], highlightthickness=0, borderwidth=0)
        self.scrollbar = ctk.CTkScrollbar(self, orientation="vertical", command=self.canvas.yview)
        self.chip_frame = ctk.CTkFrame(self.canvas, fg_color=THEME["bg_mid"])

        self.canvas_window = self.canvas.create_window((0, 0), window=self.chip_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10))
        self.scrollbar.pack(side="right", fill="y", padx=(0, 5), pady=(0, 10))

        self.chip_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        # Mousewheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        # Re-layout chips when canvas width changes
        self._layout_chips()

    def _on_mousewheel(self, event):
        # Only scroll if mouse is over this widget
        try:
            widget = event.widget
            while widget:
                if widget == self.canvas or widget == self.chip_frame:
                    self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                    return
                widget = widget.master
        except (AttributeError, tk.TclError):
            pass

    def _set_source(self, source):
        self.source = source
        self.shop_btn.configure(fg_color=THEME["accent"] if source == "shop" else "gray25")
        self.inv_btn.configure(fg_color=THEME["accent"] if source == "inventory" else "gray25")
        # Trigger refresh with whatever category/filter is active
        self.event_generate("<<SourceChanged>>")

    def update_chips(self, category, value_filter=""):
        """Fetch data and render chips for the given category and optional filter."""
        if self.source == "shop":
            self.current_items = self.shop_data.browse(category, value_filter=value_filter or None)
        else:
            self.current_items = inventory.browse_inventory(
                self.conn, category, value_filter=value_filter or None
            )
        self.displayed_count = 0
        self._render_chips()

    def _render_chips(self):
        """Clear and re-render chips up to CHIPS_PER_PAGE."""
        for w in self.chip_frame.winfo_children():
            w.destroy()

        items_to_show = self.current_items[:self.CHIPS_PER_PAGE]
        self.displayed_count = len(items_to_show)
        total = len(self.current_items)

        if total == 0:
            ctk.CTkLabel(self.chip_frame, text="No components found",
                         text_color=THEME["text_dim"]).pack(pady=20)
            self.count_label.configure(text="0 items")
            return

        count_text = f"{self.displayed_count} of {total}" if self.displayed_count < total else f"{total} items"
        self.count_label.configure(text=count_text)

        # Store chip buttons for layout
        self.chip_buttons = []
        for item in items_to_show:
            chip = self._create_chip(item)
            self.chip_buttons.append(chip)

        self._layout_chips()

        # "Load more" button if truncated
        if self.displayed_count < total:
            more_btn = ctk.CTkButton(self.chip_frame, text=f"Load more ({total - self.displayed_count} remaining)",
                                     fg_color="transparent", border_width=1, height=28,
                                     command=self._load_more)
            more_btn.pack(pady=10)

    def _layout_chips(self):
        """Flow-layout chips into rows based on current canvas width."""
        try:
            canvas_w = self.canvas.winfo_width()
        except tk.TclError:
            return
        if canvas_w < 50:
            canvas_w = 800  # fallback before first render

        chip_w = 95
        chip_h = 32
        pad_x = 4
        pad_y = 4
        cols = max(1, (canvas_w - 20) // (chip_w + pad_x))

        for i, chip in enumerate(getattr(self, 'chip_buttons', [])):
            row = i // cols
            col = i % cols
            x = 10 + col * (chip_w + pad_x)
            y = 5 + row * (chip_h + pad_y)
            chip.place(x=x, y=y, width=chip_w, height=chip_h)

        # Update frame height
        if hasattr(self, 'chip_buttons') and self.chip_buttons:
            total_rows = (len(self.chip_buttons) - 1) // cols + 1
            frame_h = 10 + total_rows * (chip_h + pad_y) + 50  # extra for load-more
            self.chip_frame.configure(height=frame_h)

    def _create_chip(self, item):
        """Create a single chip button for a component."""
        if self.source == "shop":
            label = item.get("value") or item.get("part_number", "?")
            # Truncate long labels
            if len(label) > 12:
                label = label[:11] + "\u2026"
        else:
            label = item.get("value") or item.get("name", "?")
            if len(label) > 12:
                label = label[:11] + "\u2026"

        chip = ctk.CTkButton(
            self.chip_frame,
            text=label,
            font=ctk.CTkFont(size=11),
            fg_color=THEME["bg_light"],
            hover_color=THEME["accent_glow"],
            text_color=THEME["text_main"],
            corner_radius=6,
            height=28,
            command=lambda i=item: self.on_chip_click(i, self.source),
        )
        return chip

    def _load_more(self):
        """Extend displayed chips by another page."""
        next_batch = self.current_items[self.displayed_count:self.displayed_count + self.CHIPS_PER_PAGE]
        self.displayed_count += len(next_batch)

        # Remove "load more" button
        children = self.chip_frame.winfo_children()
        for child in children:
            if isinstance(child, ctk.CTkButton) and "Load more" in (child.cget("text") or ""):
                child.destroy()
                break

        for item in next_batch:
            chip = self._create_chip(item)
            self.chip_buttons.append(chip)

        total = len(self.current_items)
        count_text = f"{self.displayed_count} of {total}" if self.displayed_count < total else f"{total} items"
        self.count_label.configure(text=count_text)

        self._layout_chips()

        if self.displayed_count < total:
            more_btn = ctk.CTkButton(self.chip_frame, text=f"Load more ({total - self.displayed_count} remaining)",
                                     fg_color="transparent", border_width=1, height=28,
                                     command=self._load_more)
            more_btn.pack(pady=10)
```

**Step 2: Manually verify class loads without syntax errors**

Run: `cd components-inventory && python -c "import inventory_gui; print('OK')"`
Expected: `OK` (or customtkinter display init, but no crash).

**Step 3: Commit**

```bash
git add components-inventory/inventory_gui.py
git commit -m "feat(gui): add ComponentBrowser chip-grid widget"
```

---

### Task 3: Integrate browser into Add tab layout

**Files:**
- Modify: `components-inventory/inventory_gui.py` — `InventoryApp.__init__`, `_setup_add_tab`, `_on_quick_cat_select`, `_on_category_change`

**Step 1: Update Add tab layout to include browser panel**

In `_setup_add_tab()`, after the sidebar block (line ~425), add the browser panel at grid row 2:

```python
        # --- Component Browser Panel (bottom) ---
        self.browser = ComponentBrowser(self.add_frame, self.shop_data, self.conn,
                                        on_chip_click=self._on_browser_chip_click)
        self.browser.grid(row=2, column=0, columnspan=2, padx=20, pady=(5, 15), sticky="nsew")
        self.browser.bind("<<SourceChanged>>", lambda e: self._refresh_browser())

        # Give row 2 some weight so the browser gets space
        self.add_frame.grid_rowconfigure(2, weight=2)
        self.add_frame.grid_rowconfigure(1, weight=3)
```

**Step 2: Add the value field trace for live filtering**

Add a StringVar to the value entry so we can trace it. In `_setup_add_tab`, replace the value entry creation (lines 399-401):

```python
        self.value_var = ctk.StringVar()
        self.value_var.trace_add("write", self._on_value_typing)
        ctk.CTkLabel(self.form, text="Value:", text_color=THEME["text_dim"]).grid(row=2, column=0, padx=(20, 0), sticky="e")
        self.add_value = ctk.CTkEntry(self.form, placeholder_text="e.g. 10k, 100nF", width=400, textvariable=self.value_var)
        self.add_value.grid(row=2, column=1, padx=20, pady=15, sticky="w")
```

**Step 3: Add handler methods**

Replace the empty `_on_category_change` (line 731) and add new methods:

```python
    def _on_category_change(self, choice):
        self._refresh_browser()

    def _on_value_typing(self, *args):
        self._refresh_browser()

    def _refresh_browser(self):
        """Refresh the component browser chips based on current category and value."""
        if hasattr(self, 'browser'):
            category = self.add_category.get()
            value_filter = self.value_var.get().strip() if hasattr(self, 'value_var') else ""
            self.browser.update_chips(category, value_filter)

    def _on_browser_chip_click(self, item, source):
        """Auto-fill form from a browser chip click."""
        if source == "shop":
            name = f"{item.get('part_number', '')} {item.get('subcategory', '')}".strip()
            self.name_var.set(name)
            # Map shop category to app category
            shop_cat = item.get("category", "").lower()
            app_cat = SHOP_TO_APP_CATEGORY.get(shop_cat, "other")
            self.add_category.set(app_cat)
            self.add_value.delete(0, "end")
            self.add_value.insert(0, item.get("value", ""))
            self.add_notes.delete(0, "end")
            self.add_notes.insert(0, item.get("description", ""))
        else:
            # Inventory source
            self.name_var.set(item.get("name", ""))
            self.add_category.set(item.get("category", "other"))
            self.add_value.delete(0, "end")
            self.add_value.insert(0, item.get("value", "") or "")
            self.add_package.delete(0, "end")
            self.add_package.insert(0, item.get("package", "") or "")
            self.add_notes.delete(0, "end")
            self.add_notes.insert(0, item.get("notes", "") or "")
        # Focus quantity for quick save
        self.add_qty.focus_set()
        self.add_qty.select_range(0, "end")
```

**Step 4: Update `_on_quick_cat_select` to also refresh browser**

Modify `_on_quick_cat_select` (line 588-591) — add `self._refresh_browser()`:

```python
    def _on_quick_cat_select(self, cat):
        self.add_category.set(cat)
        for c, b in self.cat_buttons.items(): b.configure(fg_color=THEME["accent"] if c == cat else "gray25")
        self._refresh_browser()
        self.add_name.focus_set()
```

**Step 5: Trigger initial browser population**

In `select_frame_by_name`, after showing the add frame (line 577), refresh the browser:

```python
        if name == "add":
            self.add_frame.grid(row=0, column=1, sticky="nsew")
            self._refresh_browser()
```

**Step 6: Run the app and manually verify**

Run: `cd components-inventory && python inventory_gui.py`

Verify:
- Browser panel visible at bottom of Add tab
- Chips show resistor values by default
- Clicking a quick-select button (e.g. "Capacitor") updates chips
- Typing in Value field filters chips live
- Clicking a chip auto-fills the form
- Shop/Inventory toggle switches data source
- Scrolling works in the chip area

**Step 7: Commit**

```bash
git add components-inventory/inventory_gui.py
git commit -m "feat(gui): integrate component browser panel into Add tab"
```

---

### Task 4: Polish — clear form resets browser, prevent feedback loops

**Files:**
- Modify: `components-inventory/inventory_gui.py` — `_clear_form`, `_on_browser_chip_click`, `_on_value_typing`

**Step 1: Prevent value trace → browser refresh loop on chip click**

When a chip click sets the value field, the value trace fires and would re-filter the browser (removing the chip the user just clicked). Add a guard flag:

In `__init__` of InventoryApp, add:
```python
        self._browser_filling = False
```

Wrap `_on_browser_chip_click` body with the flag:
```python
    def _on_browser_chip_click(self, item, source):
        self._browser_filling = True
        try:
            # ... existing auto-fill code ...
        finally:
            self._browser_filling = False
```

Guard `_on_value_typing`:
```python
    def _on_value_typing(self, *args):
        if not self._browser_filling:
            self._refresh_browser()
```

**Step 2: Reset browser after form clear (Save)**

In `_clear_form`, add at the end:
```python
        self._refresh_browser()
```

**Step 3: Run app, test full workflow**

Run: `cd components-inventory && python inventory_gui.py`

Test workflow:
1. Select "Resistor" → browser shows all resistor chips
2. Type "4.7" in value → chips filter to 4.7-related values
3. Click a chip → form fills, browser does NOT re-filter
4. Hit Save → form clears, browser resets to full category view
5. Toggle to "My Inventory" → shows your own components
6. Switch to "IC" category → browser shows IC chips from shop

**Step 4: Commit**

```bash
git add components-inventory/inventory_gui.py
git commit -m "fix(gui): prevent browser feedback loop on chip auto-fill"
```

---

### Task 5: Run all tests and final verification

**Files:** None (verification only)

**Step 1: Run data layer tests**

Run: `cd components-inventory && python -m pytest test_browser_data.py test_merge.py -v`
Expected: All tests PASS.

**Step 2: Launch app for final smoke test**

Run: `cd components-inventory && python inventory_gui.py`

Checklist:
- [ ] Browser visible at bottom of Add tab
- [ ] Quick-select buttons update browser
- [ ] Category dropdown updates browser
- [ ] Value typing filters browser live
- [ ] Chip click auto-fills form
- [ ] Focus moves to Quantity after chip click
- [ ] Shop/Inventory toggle works
- [ ] "Load more" button appears for large categories (500+ resistors)
- [ ] Scrolling works in chip area
- [ ] Save clears form and resets browser
- [ ] Other tabs (Inventory, Stock, Dashboard) unaffected

**Step 3: Final commit**

```bash
git add -A
git commit -m "test: add component browser data layer tests"
```
