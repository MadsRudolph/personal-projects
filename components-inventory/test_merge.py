import inventory
import os
conn = inventory.init_db()
data = {'name':'TestResistor', 'category':'resistor', 'value':'1k', 'package':'0805', 'quantity':10}
# Clean up
conn.execute('DELETE FROM components WHERE name="TestResistor"')
# First insert
id1, m1 = inventory.insert_component(conn, data)
print(f"Insert 1: ID={id1}, Merged={m1}")
# Second insert
data['quantity'] = 20
id2, m2 = inventory.insert_component(conn, data)
print(f"Insert 2: ID={id2}, Merged={m2}")
# Check quantity
final_qty = conn.execute('SELECT quantity FROM components WHERE id=?', (id1,)).fetchone()[0]
print(f"Final Quantity: {final_qty}")
# Check colors
colors = inventory.get_resistor_colors(1000)
print(f"1k Colors: {colors}")
colors_10k = inventory.get_resistor_colors(10000)
print(f"10k Colors: {colors_10k}")
