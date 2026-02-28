# Component Inventory GUI Redesign — Design

## Purpose

Replace the terminal CLI interface with a tkinter GUI app, keeping the existing SQLite database layer. Optimized for fast data entry during sorting sessions.

## Architecture

- Reuse existing `inventory.py` database functions (init_db, insert_component, search_components, list_by_category, get_stock, update_quantity, export_csv)
- New `inventory_gui.py` imports from `inventory.py` and provides the tkinter interface
- CLI version remains available for scripting/export

## GUI Framework

Tkinter (ships with Python, zero dependencies).

## Window Layout

- Title: "Component Inventory"
- Top: Tab buttons — Add (default) | Inventory | Stock
- Center: Content area swaps based on active tab
- Bottom: Status bar (session count, last action)

## Add Tab (Default)

Form fields: Name, Category (dropdown), Value/Part # (adaptive label), Package (show/hide), Quantity (default 1), Location, Notes.

**UX flow:**
1. Cursor starts in Name field on launch
2. Category dropdown remembers last selection (sticky)
3. Location remembers last value (sticky)
4. Value label adapts to category (e.g. "Value" for resistor, "Part #" for IC, "Description" for connector)
5. Package field hidden for connector/switch/other
6. Enter or "Save & Next" button saves, clears form, returns cursor to Name
7. Status bar shows confirmation with session count

## Inventory Tab

- Search box with real-time filtering
- Category filter dropdown
- Treeview table (id, name, category, value, package, qty, location, notes)
- Double-click row to edit quantity

## Stock Tab

- Read-only summary table: Category | Items | Total Qty | with totals
- Export button (file dialog for CSV save location)

## Keyboard Shortcuts

- Enter = save & next (add form)
- Tab = move between fields
- Ctrl+1/2/3 = switch tabs
- Ctrl+E = export
- Escape = clear form

## Adaptive Field Mapping

| Category Group                        | Value Label        | Show Package |
|---------------------------------------|--------------------|--------------|
| resistor, capacitor, inductor, crystal| Value              | Yes          |
| diode, transistor, LED                | Part #             | Yes          |
| IC                                    | Part #             | Yes          |
| connector, switch, other              | Description        | No           |
