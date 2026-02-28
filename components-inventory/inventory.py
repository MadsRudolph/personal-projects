# inventory.py — initial scaffold
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
