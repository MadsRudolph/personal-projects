import csv
import io
import os
import sqlite3
import sys
from datetime import datetime

# --- Constants & Paths ---
PROJECT_DIR = r"C:\Users\Mads2\Documents\Projects\components-inventory"

def get_db_path():
    """Always prioritize the database in the original project folder."""
    path = os.path.join(PROJECT_DIR, "inventory.db")
    if os.path.exists(path):
        return path
    return os.path.join(os.getcwd(), "inventory.db")

DB_NAME = get_db_path()

def get_shop_csv_path():
    """Smart lookup for the shop CSV, prioritizing the project folder."""
    paths = [
        os.path.join(PROJECT_DIR, "dtu_component_shop(1).csv"),
        r"C:\Users\Mads2\OneDrive\Skrivebord\dtu_component_shop(1).csv",
        os.path.join(os.environ["USERPROFILE"], "Desktop", "dtu_component_shop(1).csv"),
        os.path.join(os.getcwd(), "dtu_component_shop(1).csv")
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[0] 

SHOP_CSV_PATH = get_shop_csv_path()

CATEGORIES = [
    "resistor", "capacitor", "inductor", "diode", "transistor",
    "IC", "connector", "LED", "crystal", "switch", "other",
]

# --- Resistor Color Code Data ---
RESISTOR_COLORS = {
    "black":  {"digit": 0, "multiplier": 1,          "tolerance": None, "color": "#000000"},
    "brown":  {"digit": 1, "multiplier": 10,         "tolerance": 1,    "color": "#8b4513"},
    "red":    {"digit": 2, "multiplier": 100,        "tolerance": 2,    "color": "#ff0000"},
    "orange": {"digit": 3, "multiplier": 1000,       "tolerance": 0.05, "color": "#ffa500"},
    "yellow": {"digit": 4, "multiplier": 10000,      "tolerance": 0.02, "color": "#ffff00"},
    "green":  {"digit": 5, "multiplier": 100000,     "tolerance": 0.5,  "color": "#008000"},
    "blue":   {"digit": 6, "multiplier": 1000000,    "tolerance": 0.25, "color": "#0000ff"},
    "violet": {"digit": 7, "multiplier": 10000000,   "tolerance": 0.1,  "color": "#ee82ee"},
    "gray":   {"digit": 8, "multiplier": 100000000,  "tolerance": 0.01, "color": "#808080"},
    "white":  {"digit": 9, "multiplier": 1000000000, "tolerance": None, "color": "#ffffff"},
    "gold":   {"digit": None, "multiplier": 0.1,      "tolerance": 5,    "color": "#ffd700"},
    "silver": {"digit": None, "multiplier": 0.01,     "tolerance": 10,   "color": "#c0c0c0"},
}

COLOR_SHORTHAND = {
    "bk": "black", "bn": "brown", "br": "brown", "r": "red", "o": "orange",
    "y": "yellow", "g": "green", "bu": "blue", "v": "violet", "gy": "gray",
    "w": "white", "gd": "gold", "si": "silver"
}

def calculate_resistance(bands):
    if len(bands) < 4 or len(bands) > 5:
        return None, None
    try:
        bands = [b.lower() for b in bands]
        if len(bands) == 4:
            d1 = RESISTOR_COLORS[bands[0]]["digit"]
            d2 = RESISTOR_COLORS[bands[1]]["digit"]
            mult = RESISTOR_COLORS[bands[2]]["multiplier"]
            tol = RESISTOR_COLORS[bands[3]]["tolerance"]
            if d1 is None or d2 is None: return None, None
            value = (d1 * 10 + d2) * mult
        else:
            d1 = RESISTOR_COLORS[bands[0]]["digit"]
            d2 = RESISTOR_COLORS[bands[1]]["digit"]
            d3 = RESISTOR_COLORS[bands[2]]["digit"]
            mult = RESISTOR_COLORS[bands[3]]["multiplier"]
            tol = RESISTOR_COLORS[bands[4]]["tolerance"]
            if d1 is None or d2 is None or d3 is None: return None, None
            value = (d1 * 100 + d2 * 10 + d3) * mult
        return value, tol
    except (KeyError, TypeError):
        return None, None

def format_resistance(value):
    if value is None: return ""
    if value >= 1000000:
        return f"{value/1000000:g}M"
    if value >= 1000:
        return f"{value/1000:g}k"
    return f"{value:g}"

def get_resistor_colors(value):
    """Returns a list of 4 or 5 color names for a given resistance value. Prefers 5-band for precision."""
    if value is None or value <= 0: return None
    
    import math
    try:
        # 5-band logic (3 digits + multiplier + tolerance)
        exp5 = math.floor(math.log10(value)) - 2
        mult5_val = 10**exp5
        val5 = round(value / mult5_val)
        
        if val5 >= 1000:
            val5 //= 10
            exp5 += 1
            mult5_val *= 10
            
        d1 = int(val5 // 100)
        d2 = int((val5 // 10) % 10)
        d3 = int(val5 % 10)
        
        digit_to_color = {d["digit"]: name for name, d in RESISTOR_COLORS.items() if d["digit"] is not None}
        mult_to_color = {round(d["multiplier"], 4): name for name, d in RESISTOR_COLORS.items() if d["multiplier"] is not None}
        
        res5 = None
        if (d1 in digit_to_color and d2 in digit_to_color and d3 in digit_to_color and 
            round(mult5_val, 4) in mult_to_color):
            res5 = [digit_to_color[d1], digit_to_color[d2], digit_to_color[d3], mult_to_color[round(mult5_val, 4)], "brown"]

        # 4-band logic (2 digits + multiplier + tolerance)
        exp4 = math.floor(math.log10(value)) - 1
        mult4_val = 10**exp4
        val4 = round(value / mult4_val)
        if val4 >= 100:
            val4 /= 10
            exp4 += 1
            mult4_val *= 10
        
        d1_4 = int(val4 // 10)
        d2_4 = int(val4 % 10)
        
        res4 = None
        if d1_4 in digit_to_color and d2_4 in digit_to_color and round(mult4_val, 4) in mult_to_color:
            res4 = [digit_to_color[d1_4], digit_to_color[d2_4], mult_to_color[round(mult4_val, 4)], "gold"]
            
        # Decision: If the value is a standard E24 (10, 22, 47 etc), prefer 4-band
        # Otherwise if it fits 5-band perfectly, use that.
        if res4 and (value % mult4_val == 0):
            return res4
        return res5 or res4
    except:
        pass
    return None

def parse_shop_value(val_str):
    if not val_str: return None
    val_str = val_str.lower().strip().replace(" ", "").replace("ohm", "").replace("ω", "")
    try:
        val_str = val_str.replace(",", ".")
        multiplier = 1
        if val_str.endswith("k"):
            multiplier = 1000
            val_str = val_str[:-1]
        elif val_str.endswith("m"):
            multiplier = 1000000
            val_str = val_str[:-1]
        elif val_str.endswith("r"): 
            val_str = val_str[:-1]
        if "k" in val_str: 
            parts = val_str.split("k")
            left = float(parts[0])
            right = float(parts[1] or 0)
            return (left + right / (10**len(parts[1]))) * 1000
        if "r" in val_str: 
            parts = val_str.split("r")
            left = float(parts[0])
            right = float(parts[1] or 0)
            return (left + right / (10**len(parts[1])))
        return float(val_str) * multiplier
    except:
        return None

def init_db(db_path=None):
    if db_path is None:
        db_path = DB_NAME
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
    # Check for existing component to merge
    name = data["name"]
    cat = data["category"]
    val = data.get("value", "") or None
    pkg = data.get("package", "") or None
    
    match_sql = """
        SELECT id, quantity FROM components 
        WHERE LOWER(name) = LOWER(?) AND LOWER(category) = LOWER(?)
    """
    params = [name, cat]
    if val:
        match_sql += " AND value = ?"
        params.append(val)
    else:
        match_sql += " AND value IS NULL"
    
    if pkg:
        match_sql += " AND package = ?"
        params.append(pkg)
    else:
        match_sql += " AND package IS NULL"
        
    existing = conn.execute(match_sql, params).fetchone()
    
    now = datetime.now().isoformat(timespec="seconds")
    if existing:
        # Merge quantity
        new_qty = existing[1] + int(data.get("quantity", 1))
        conn.execute(
            "UPDATE components SET quantity=?, updated_at=? WHERE id=?",
            (new_qty, now, existing[0])
        )
        conn.commit()
        return existing[0], True # Return ID and merge status
    
    # Insert new
    cur = conn.execute(
        """INSERT INTO components (name, category, value, package, quantity, location, notes, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            name, cat, val, pkg,
            data.get("quantity", 1),
            data.get("location", "Main Box"),
            data.get("notes", "") or None,
            now, now
        ),
    )
    conn.commit()
    return cur.lastrowid, False


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


def delete_component(conn, component_id):
    cur = conn.execute("DELETE FROM components WHERE id=?", (component_id,))
    conn.commit()
    return cur.rowcount > 0


def update_component(conn, component_id, data):
    now = datetime.now().isoformat(timespec="seconds")
    fields = []
    values = []
    
    # Map possible data keys to column names
    for key in ["name", "category", "value", "package", "quantity", "location", "notes"]:
        if key in data:
            fields.append(f"{key}=?")
            values.append(data[key])
    
    if not fields:
        return False
        
    fields.append("updated_at=?")
    values.append(now)
    values.append(component_id)
    
    sql = f"UPDATE components SET {', '.join(fields)} WHERE id=?"
    cur = conn.execute(sql, tuple(values))
    conn.commit()
    return cur.rowcount > 0


def get_category_stats(conn):
    """Returns (category, count, total_quantity) for all components."""
    query = """
        SELECT category, COUNT(*), SUM(quantity) 
        FROM components 
        GROUP BY category 
        ORDER BY SUM(quantity) DESC
    """
    cur = conn.execute(query)
    return cur.fetchall()

def export_csv(conn):
    """Generates a CSV string of the inventory, optimized for Excel."""
    query = "SELECT id, name, category, value, package, quantity, notes FROM components ORDER BY category, name"
    cur = conn.execute(query)
    rows = cur.fetchall()
    
    output = io.StringIO()
    # Write BOM for Excel UTF-8 compatibility
    output.write('\ufeff')
    
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["ID", "Name", "Category", "Value", "Package", "Quantity", "Notes"])
    
    for row in rows:
        writer.writerow(row)
        
    return output.getvalue()

class ShopData:
    """Helper to load and search the master shop CSV."""
    def __init__(self, csv_path=SHOP_CSV_PATH):
        self.csv_path = csv_path
        self.items = []
        self._load()

    def _load(self):
        if not os.path.exists(self.csv_path):
            return
        
        try:
            # Use utf-8-sig to handle potential BOM and errors='replace' for robustness
            with open(self.csv_path, "r", encoding="utf-8-sig", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Map shop CSV headers: Category,Subcategory,Part_Number,Value,Description
                    self.items.append({
                        "id": row.get("Part_Number", ""),
                        "category": row.get("Category", "").lower().strip(),
                        "subcategory": row.get("Subcategory", ""),
                        "part_number": row.get("Part_Number", ""),
                        "value": row.get("Value", ""),
                        "description": row.get("Description", "")
                    })
            print(f"Shop data loaded: {len(self.items)} items from {self.csv_path}")
        except Exception as e:
            print(f"Error loading shop CSV: {e}")

    def search(self, query, cat_filter=None, limit=10):
        query = query.lower() if query else ""
        cat_filter = cat_filter.lower() if cat_filter else None
        
        results = []
        for item in self.items:
            if cat_filter and item["category"] != cat_filter:
                continue
                
            if query:
                match_str = f"{item['category']} {item['part_number']} {item['value']} {item['subcategory']} {item['description']}".lower()
                if query in match_str:
                    results.append(item)
            elif cat_filter:
                results.append(item)
            
            if limit is not None and len(results) >= limit:
                break
        return results


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
