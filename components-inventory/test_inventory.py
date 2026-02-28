# test_inventory.py
import os
import sqlite3
import tempfile
import unittest

# We'll import from inventory.py
import inventory


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp, "test.db")
        self.conn = inventory.init_db(self.db_path)

    def tearDown(self):
        self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_init_db_creates_table(self):
        cur = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='components'"
        )
        self.assertIsNotNone(cur.fetchone())

    def test_insert_component(self):
        cid = inventory.insert_component(self.conn, {
            "name": "10k resistor",
            "category": "resistor",
            "value": "10k",
            "package": "axial",
            "quantity": 5,
            "location": "A1",
            "notes": "",
        })
        self.assertIsInstance(cid, int)
        row = self.conn.execute("SELECT * FROM components WHERE id=?", (cid,)).fetchone()
        self.assertEqual(row[1], "10k resistor")  # name
        self.assertEqual(row[5], 5)                # quantity

    def test_insert_component_minimal(self):
        cid = inventory.insert_component(self.conn, {
            "name": "JST 2-pin",
            "category": "connector",
            "value": "",
            "package": "",
            "quantity": 1,
            "location": "B2",
            "notes": "",
        })
        row = self.conn.execute("SELECT * FROM components WHERE id=?", (cid,)).fetchone()
        self.assertEqual(row[1], "JST 2-pin")


if __name__ == "__main__":
    unittest.main()
