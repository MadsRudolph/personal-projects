import csv
import io
import os
import sqlite3
import sys
from datetime import datetime

DB_NAME = "inventory.db"

CATEGORIES = [
    "resistor", "capacitor", "inductor", "diode", "transistor",
    "IC", "connector", "LED", "crystal", "switch", "other",
]

def get_db_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_NAME)

def init_db(db_path=None):
    if db_path is None:
        db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            value TEXT,
            package TEXT,
            quantity INTEGER NOT NULL DEFAULT 1,
            location TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    return conn

def insert_component(conn, data):
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        """INSERT INTO components (name, category, value, package, quantity, location, notes, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["name"],
            data["category"],
            data.get("value", "") or None,
            data.get("package", "") or None,
            data.get("quantity", 1),
            data.get("location", ""),
            data.get("notes", "") or None,
            now,
            now,
        ),
    )
    conn.commit()
    return cur.lastrowid


def _row_to_dict(row, cursor):
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


def search_components(conn, query):
    sql = """
        SELECT * FROM components
        WHERE name LIKE ? OR category LIKE ? OR value LIKE ?
           OR package LIKE ? OR location LIKE ? OR notes LIKE ?
        ORDER BY category, name
    """
    pattern = f"%{query}%"
    cur = conn.execute(sql, (pattern,) * 6)
    return [_row_to_dict(r, cur) for r in cur.fetchall()]


def list_by_category(conn, category):
    sql = "SELECT * FROM components WHERE LOWER(category) = LOWER(?) ORDER BY name"
    cur = conn.execute(sql, (category,))
    return [_row_to_dict(r, cur) for r in cur.fetchall()]


def get_stock(conn):
    sql = """
        SELECT category, COUNT(*) as items, SUM(quantity) as total_qty
        FROM components
        GROUP BY category
        ORDER BY category
    """
    return conn.execute(sql).fetchall()


def update_quantity(conn, component_id, new_qty):
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        "UPDATE components SET quantity=?, updated_at=? WHERE id=?",
        (new_qty, now, component_id),
    )
    conn.commit()
    return cur.rowcount > 0


def export_csv(conn):
    cur = conn.execute("SELECT * FROM components ORDER BY category, name")
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(cols)
    writer.writerows(rows)
    return output.getvalue()


DISPLAY_COLS = ["id", "name", "category", "value", "package", "qty", "location", "notes"]

def format_table(rows):
    if not rows:
        return "  No components found."
    display_rows = []
    for r in rows:
        display_rows.append({
            "id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "value": r.get("value") or "",
            "package": r.get("package") or "",
            "qty": r["quantity"],
            "location": r.get("location") or "",
            "notes": r.get("notes") or "",
        })
    widths = {}
    for col in DISPLAY_COLS:
        widths[col] = max(len(col), max(len(str(r[col])) for r in display_rows))
    lines = []
    header = "  ".join(str(col).ljust(widths[col]) for col in DISPLAY_COLS)
    lines.append(header)
    lines.append("-" * len(header))
    for r in display_rows:
        line = "  ".join(str(r[col]).ljust(widths[col]) for col in DISPLAY_COLS)
        lines.append(line)
    return "\n".join(lines)


def format_stock(stock_rows):
    if not stock_rows:
        return "  Inventory is empty."
    lines = []
    lines.append(f"  {'Category':<15} {'Items':>6} {'Total Qty':>10}")
    lines.append("  " + "-" * 33)
    total_items = 0
    total_qty = 0
    for cat, items, qty in stock_rows:
        lines.append(f"  {cat:<15} {items:>6} {qty:>10}")
        total_items += items
        total_qty += qty
    lines.append("  " + "-" * 33)
    lines.append(f"  {'TOTAL':<15} {total_items:>6} {total_qty:>10}")
    return "\n".join(lines)


CATEGORY_FIELDS = {
    "resistor":   [("value", "Value (e.g. 10k, 4.7k)"), ("package", "Package (e.g. axial, 0805)")],
    "capacitor":  [("value", "Value (e.g. 100nF, 10uF)"), ("package", "Package (e.g. ceramic disc, electrolytic)")],
    "inductor":   [("value", "Value (e.g. 10uH, 100mH)"), ("package", "Package (e.g. axial, toroid)")],
    "crystal":    [("value", "Frequency (e.g. 16MHz, 32.768kHz)"), ("package", "Package (e.g. HC-49)")],
    "diode":      [("value", "Part # (e.g. 1N4148, 1N4007)"), ("package", "Package (e.g. DO-35, DO-41)")],
    "transistor": [("value", "Part # (e.g. 2N2222, BC547)"), ("package", "Package (e.g. TO-92, TO-220)")],
    "LED":        [("value", "Color/type (e.g. red 5mm, green 3mm)"), ("package", "Package (e.g. 5mm, 3mm)")],
    "IC":         [("value", "Part # (e.g. ATmega328P, NE555)"), ("package", "Package (e.g. DIP-8, DIP-28)")],
    "connector":  [("value", "Description (e.g. 2-pin JST, DB9 male)")],
    "switch":     [("value", "Description (e.g. tactile 6mm, SPDT toggle)")],
    "other":      [("value", "Description")],
}


CHEATSHEET = """
=== Component Inventory ===

  Commands:
    python inventory.py              Add components (interactive)
    python inventory.py search <q>   Search all fields
    python inventory.py list <cat>   List by category
    python inventory.py stock        Inventory summary
    python inventory.py update <id> quantity <n>
    python inventory.py export       Dump to CSV

  Categories: {}

  During add mode:
    - Press Enter to accept [default] values
    - Type 'q' or 'quit' at the name prompt to exit
""".format(", ".join(CATEGORIES))


def prompt(label, default="", required=False):
    """Prompt for input with optional default. Returns stripped string."""
    if default:
        display = f"  {label} [{default}]: "
    else:
        display = f"  {label}: "
    while True:
        val = input(display).strip()
        if not val and default:
            return default
        if not val and not required:
            return ""
        if not val and required:
            print("    (required)")
            continue
        return val


def prompt_category(default=""):
    """Show numbered category list, return selected category."""
    print("  Category:")
    for i, cat in enumerate(CATEGORIES, 1):
        marker = " *" if cat == default else ""
        print(f"    {i:2}. {cat}{marker}")
    while True:
        if default:
            raw = input(f"  Choose [{CATEGORIES.index(default) + 1}]: ").strip()
        else:
            raw = input("  Choose: ").strip()
        if not raw and default:
            return default
        # Accept number or name
        try:
            idx = int(raw)
            if 1 <= idx <= len(CATEGORIES):
                return CATEGORIES[idx - 1]
        except ValueError:
            low = raw.lower()
            for cat in CATEGORIES:
                if cat.lower() == low:
                    return cat
        print("    (invalid — enter number or category name)")


def add_mode(conn):
    """Interactive add loop optimized for rapid entry."""
    print(CHEATSHEET)
    print("  Entering add mode. Type 'q' at name prompt to stop.\n")

    count = 0
    last_category = ""
    last_location = ""

    while True:
        print(f"  --- Component #{count + 1} ---")
        name = input("  Name: ").strip()
        if name.lower() in ("q", "quit", "exit"):
            break
        if not name:
            print("    (name is required)\n")
            continue

        category = prompt_category(default=last_category)
        last_category = category

        data = {"name": name, "category": category}

        # Adaptive fields based on category
        fields = CATEGORY_FIELDS.get(category, CATEGORY_FIELDS["other"])
        for field_key, field_label in fields:
            data[field_key] = prompt(field_label)

        # Ensure keys exist
        data.setdefault("value", "")
        data.setdefault("package", "")

        qty_str = prompt("Quantity", default="1")
        try:
            data["quantity"] = int(qty_str)
        except ValueError:
            data["quantity"] = 1

        data["location"] = prompt("Location (e.g. A1)", default=last_location, required=True)
        last_location = data["location"]

        data["notes"] = prompt("Notes (optional)")

        cid = insert_component(conn, data)
        count += 1

        # Summary line
        val_str = f" {data.get('value', '')}" if data.get("value") else ""
        pkg_str = f" [{data.get('package', '')}]" if data.get("package") else ""
        print(f"  -> #{cid}: {name}{val_str}{pkg_str} x{data['quantity']} @ {data['location']}  ({count} added)\n")

    print(f"\n  Session complete: {count} components added.")


def cmd_search(conn, query):
    results = search_components(conn, query)
    print(f"\n  Search results for '{query}':\n")
    print(format_table(results))


def cmd_list(conn, category):
    # Fuzzy match category name
    match = None
    for cat in CATEGORIES:
        if cat.lower().startswith(category.lower()):
            match = cat
            break
    if not match:
        print(f"  Unknown category: {category}")
        print(f"  Valid: {', '.join(CATEGORIES)}")
        return
    results = list_by_category(conn, match)
    print(f"\n  {match} ({len(results)} items):\n")
    print(format_table(results))


def cmd_stock(conn):
    stock = get_stock(conn)
    print("\n  Inventory Stock:\n")
    print(format_stock(stock))


def cmd_update(conn, args):
    # Expected: update <id> quantity <n>
    if len(args) < 4 or args[2] != "quantity":
        print("  Usage: update <id> quantity <new_qty>")
        return
    try:
        cid = int(args[1])
        qty = int(args[3])
    except ValueError:
        print("  Error: id and quantity must be numbers")
        return
    if update_quantity(conn, cid, qty):
        print(f"  Updated component #{cid} quantity to {qty}")
    else:
        print(f"  Component #{cid} not found")


def cmd_export(conn):
    output = export_csv(conn)
    filename = f"inventory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    with open(filepath, "w", newline="") as f:
        f.write(output)
    print(f"  Exported to {filepath}")


def main():
    conn = init_db()
    args = sys.argv[1:]

    try:
        if not args or args[0] == "add":
            add_mode(conn)
        elif args[0] == "search":
            if len(args) < 2:
                print("  Usage: search <query>")
            else:
                cmd_search(conn, " ".join(args[1:]))
        elif args[0] == "list":
            if len(args) < 2:
                print("  Usage: list <category>")
            else:
                cmd_list(conn, args[1])
        elif args[0] == "stock":
            cmd_stock(conn)
        elif args[0] == "update":
            cmd_update(conn, args)
        elif args[0] == "export":
            cmd_export(conn)
        else:
            print(CHEATSHEET)
    except KeyboardInterrupt:
        print("\n  Bye!")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
