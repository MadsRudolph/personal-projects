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
