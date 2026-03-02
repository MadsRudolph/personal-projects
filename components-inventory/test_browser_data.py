# test_browser_data.py
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inventory

def test_shop_browse_by_category_returns_items():
    shop = inventory.ShopData()
    results = shop.browse("resistor")
    assert len(results) > 0
    assert all(r["category"] == "resistor" for r in results)

def test_shop_browse_with_value_filter():
    shop = inventory.ShopData()
    results = shop.browse("resistor", value_filter="4.7")
    assert len(results) > 0
    for r in results:
        combined = f"{r['value']} {r['part_number']} {r['subcategory']}".lower()
        assert "4.7" in combined or "4k7" in combined

def test_shop_browse_empty_category_returns_empty():
    shop = inventory.ShopData()
    results = shop.browse("nonexistent_category")
    assert results == []

def test_shop_browse_ic_maps_correctly():
    shop = inventory.ShopData()
    results_lower = shop.browse("ic")
    results_upper = shop.browse("IC")
    assert len(results_lower) > 0
    assert len(results_lower) == len(results_upper)

def test_shop_browse_led_maps_correctly():
    shop = inventory.ShopData()
    results = shop.browse("LED")
    assert len(results) > 0

def test_inventory_browse_by_category():
    conn = inventory.init_db(":memory:")
    inventory.insert_component(conn, {"name": "TL072", "category": "IC", "value": "", "quantity": 1})
    inventory.insert_component(conn, {"name": "100nF", "category": "capacitor", "value": "100nF", "quantity": 5})
    results = inventory.browse_inventory(conn, "IC")
    assert len(results) == 1
    assert results[0]["name"] == "TL072"
    results = inventory.browse_inventory(conn, "capacitor")
    assert len(results) == 1
    conn.close()

def test_inventory_browse_with_value_filter():
    conn = inventory.init_db(":memory:")
    inventory.insert_component(conn, {"name": "10k Resistor", "category": "resistor", "value": "10k", "quantity": 1})
    inventory.insert_component(conn, {"name": "4.7k Resistor", "category": "resistor", "value": "4.7k", "quantity": 1})
    inventory.insert_component(conn, {"name": "100k Resistor", "category": "resistor", "value": "100k", "quantity": 1})
    results = inventory.browse_inventory(conn, "resistor", value_filter="4.7")
    assert len(results) == 1
    assert results[0]["value"] == "4.7k"
    conn.close()

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
