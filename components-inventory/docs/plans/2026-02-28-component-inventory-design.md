# Component Inventory CLI — Design

## Purpose

Lightweight terminal tool for cataloging THT electronic components during sorting sessions, and searching the inventory when planning builds.

## Architecture

Single Python file (`inventory.py`) using only stdlib + sqlite3. SQLite database (`inventory.db`) auto-created on first run in the same directory as the script.

## Database Schema

Single `components` table:

| Column     | Type    | Constraints                    |
|------------|---------|--------------------------------|
| id         | INTEGER | PRIMARY KEY AUTOINCREMENT      |
| name       | TEXT    | NOT NULL                       |
| category   | TEXT    | NOT NULL (from fixed list)     |
| value      | TEXT    | nullable                       |
| package    | TEXT    | nullable                       |
| quantity   | INTEGER | NOT NULL DEFAULT 1             |
| location   | TEXT    | box compartment label          |
| notes      | TEXT    | optional                       |
| created_at | TEXT    | ISO 8601 timestamp             |
| updated_at | TEXT    | ISO 8601 timestamp             |

## Categories

Fixed list: resistor, capacitor, inductor, diode, transistor, IC, connector, LED, crystal, switch, other

## CLI Commands

| Command                          | Description                          |
|----------------------------------|--------------------------------------|
| `python inventory.py`            | Enter add mode (default)             |
| `python inventory.py add`        | Same as above                        |
| `python inventory.py search <q>` | Full-text search across all fields   |
| `python inventory.py list <cat>` | Filter by category                   |
| `python inventory.py stock`      | Summary grouped by category          |
| `python inventory.py update <id> quantity <n>` | Adjust quantity       |
| `python inventory.py export`     | Dump to CSV                          |

## Add Mode UX

### Flow

1. Print cheatsheet + session counter
2. Prompt name (required) — `q`/`quit` exits
3. Prompt category — numbered list, pre-fill with last-used
4. Prompt category-specific fields (see mapping below)
5. Quantity — default 1
6. Location — required, pre-fill last-used
7. Notes — optional (Enter to skip)
8. One-line summary, save, increment session counter, loop

### Adaptive Field Mapping

| Category Group                        | Fields Prompted          |
|---------------------------------------|--------------------------|
| resistor, capacitor, inductor, crystal| value, package           |
| diode, transistor, LED                | value (part #), package  |
| IC                                    | value (part #), package  |
| connector, switch                     | description (as value)   |
| other                                 | description (as value)   |

### Smart Defaults

- Category pre-fills with last-used category
- Location pre-fills with last-used location
- Quantity defaults to 1
- Defaults carry across entries within the same session

## Search & Display

- Results as formatted text table with auto-sized columns
- `stock` groups by category with subtotals and grand total
- Search queries match against all text fields (name, category, value, package, location, notes)

## Error Handling

- Graceful Ctrl+C (no partial saves)
- Invalid input re-prompts
- Nonexistent IDs show clear error message
- DB created automatically if missing
