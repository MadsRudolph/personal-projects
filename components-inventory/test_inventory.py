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

    def _seed(self):
        """Insert a few test components."""
        items = [
            {"name": "10k resistor", "category": "resistor", "value": "10k", "package": "axial", "quantity": 50, "location": "A1", "notes": "1/4W"},
            {"name": "100nF capacitor", "category": "capacitor", "value": "100nF", "package": "ceramic disc", "quantity": 20, "location": "A2", "notes": ""},
            {"name": "1N4148 diode", "category": "diode", "value": "1N4148", "package": "DO-35", "quantity": 30, "location": "A3", "notes": ""},
            {"name": "ATmega328P", "category": "IC", "value": "ATmega328P", "package": "DIP-28", "quantity": 3, "location": "B1", "notes": "Arduino compatible"},
        ]
        for item in items:
            inventory.insert_component(self.conn, item)

    def test_search_by_value(self):
        self._seed()
        results = inventory.search_components(self.conn, "10k")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "10k resistor")

    def test_search_by_notes(self):
        self._seed()
        results = inventory.search_components(self.conn, "Arduino")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "ATmega328P")

    def test_search_no_results(self):
        self._seed()
        results = inventory.search_components(self.conn, "nonexistent_xyz")
        self.assertEqual(len(results), 0)

    def test_list_by_category(self):
        self._seed()
        results = inventory.list_by_category(self.conn, "resistor")
        self.assertEqual(len(results), 1)

    def test_list_by_category_case_insensitive(self):
        self._seed()
        results = inventory.list_by_category(self.conn, "Resistor")
        self.assertEqual(len(results), 1)

    def test_get_stock(self):
        self._seed()
        stock = inventory.get_stock(self.conn)
        categories = {row[0] for row in stock}
        self.assertIn("resistor", categories)
        self.assertIn("IC", categories)

    def test_update_quantity(self):
        self._seed()
        ok = inventory.update_quantity(self.conn, 1, 42)
        self.assertTrue(ok)
        row = self.conn.execute("SELECT quantity FROM components WHERE id=1").fetchone()
        self.assertEqual(row[0], 42)

    def test_update_quantity_nonexistent(self):
        ok = inventory.update_quantity(self.conn, 9999, 1)
        self.assertFalse(ok)

    def test_export_csv(self):
        self._seed()
        output = inventory.export_csv(self.conn)
        self.assertIn("10k resistor", output)
        self.assertIn("ATmega328P", output)
        lines = output.strip().split("\n")
        self.assertEqual(len(lines), 5)  # header + 4 rows


if __name__ == "__main__":
    unittest.main()
