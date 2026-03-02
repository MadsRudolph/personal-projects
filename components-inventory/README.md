# Component Inventory Pro

Desktop app for cataloging THT electronic components with a built-in DTU shop browser. Python 3 + customtkinter + SQLite.

## Features

- **Dashboard** — visual overview with donut chart breakdown by category and quick stats (total components, categories, locations)
- **Add** — form optimized for rapid entry. Enter saves and loops. Category and location stick between entries
- **Inventory** — searchable table with category filter, inline quantity editing, and visual resistor color bands (4-band and 5-band)
- **Stock** — summary by category with CSV export
- **DTU Shop Browser** — browse 1,400+ components from the DTU component shop, filter by category/subcategory, search by part number or value, and see which items you already own
- **AI Export** — generate a markdown summary of your entire inventory, ready to paste into an LLM for project planning

## Quick Start

### Run from source

```bash
pip install customtkinter pillow
python inventory_gui.py
```

### Windows executable

A pre-built `InventoryPro.exe` is available in the `dist/` folder — no Python installation required.

To build it yourself:

```bash
pip install pyinstaller
python -m PyInstaller InventoryPro.spec
```

## DTU Shop Browser

The shop tab loads component data from the DTU component shop CSV and lets you:

- Browse by category (resistors, capacitors, ICs, LEDs, etc.)
- Filter by subcategory chips
- Search by part number, value, or description
- Filter by ownership status (All / Owned / Not Owned)
- See visual resistor color bands inline
- Cross-references your inventory automatically — owned items get a green badge

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Enter | Save & next (in add form) |
| Escape | Clear form |
| Ctrl+1/2/3/4/5 | Switch tabs |
| Ctrl+E | Export to CSV |

## CLI (Alternative)

```bash
python inventory.py          # Interactive add mode
python inventory.py search 10k
python inventory.py list resistors
python inventory.py stock
python inventory.py update 1 quantity 42
python inventory.py export
```

## Data

- **Database:** `inventory.db` (SQLite, same directory as the script)
- **Shop data:** `dtu_component_shop(1).csv` (bundled in the exe)
- **Export:** CSV backup via the Stock tab or CLI

## Tech Stack

- **GUI:** customtkinter (dark theme)
- **Charts:** PIL/Pillow for donut chart rendering
- **Database:** SQLite via Python's built-in `sqlite3`
- **Packaging:** PyInstaller
