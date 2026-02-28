# Component Inventory

Lightweight CLI tool for cataloging THT electronic components. Python 3 + SQLite, no dependencies.

## Quick Start

```bash
python inventory.py          # Start adding components
python inventory.py search 10k
python inventory.py list resistors
python inventory.py stock
python inventory.py update 1 quantity 42
python inventory.py export
```

## Add Mode

Run `python inventory.py` to enter interactive add mode. The tool will prompt for each field, with smart defaults that carry forward between entries:

- **Category** pre-fills with the last-used category
- **Location** pre-fills with the last-used compartment
- **Quantity** defaults to 1
- **Fields adapt** to the component category (resistors prompt for value, connectors prompt for description, etc.)

Type `q` at the name prompt to exit.

## Data

The database is stored as `inventory.db` in the same directory as the script. Use `export` to create CSV backups.
