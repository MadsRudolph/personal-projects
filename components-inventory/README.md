# Component Inventory

Lightweight tool for cataloging THT electronic components. Python 3 + SQLite, no dependencies.

## Quick Start (GUI)

```bash
python inventory_gui.py
```

Opens a desktop app with three tabs:

- **Add** — form optimized for rapid entry. Enter saves and loops. Category and location stick between entries.
- **Inventory** — searchable table with category filter. Double-click to edit quantity.
- **Stock** — summary by category with export button.

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Enter | Save & next (in add form) |
| Escape | Clear form |
| Ctrl+1/2/3 | Switch tabs |
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

The database is stored as `inventory.db` in the same directory as the script. Use export to create CSV backups.
