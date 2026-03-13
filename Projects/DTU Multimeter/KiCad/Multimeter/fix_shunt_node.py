"""Fix U3 Pin 4 'input not driven' by adding PWR_FLAG on SHUNT_NODE net.

Pin 4 is wired to SHUNT_NODE but KiCad complains no output drives it.
Adding PWR_FLAG tells ERC the net is intentionally driven.
Place at (322.58, 87.63) -- the junction between the horizontal and
vertical wires leading to pin 4.
"""
import uuid, shutil, re
from pathlib import Path

SCH = Path(r"C:\Users\Mads2\Documents\Projects\Projects\DTU Multimeter\KiCad\Multimeter\Multimeter.kicad_sch")
PROJ_UUID = "ac1a6b26-ab53-454a-b718-b2b6f7a3a514"

def uid():
    return str(uuid.uuid4())

# ---------- Load ----------
shutil.copy2(SCH, SCH.with_suffix(".kicad_sch.bak"))
content = SCH.read_text(encoding="utf-8")

# Find next available FLG number
flg_nums = [int(m) for m in re.findall(r'#FLG(\d+)', content)]
next_flg = max(flg_nums) + 1 if flg_nums else 1
ref = f"#FLG{next_flg:02d}"

# PWR_FLAG at (322.58, 87.63) -- on the SHUNT_NODE wire junction
pwrflag = f'''
	(symbol
		(lib_id "power:PWR_FLAG")
		(at 322.58 87.63 0)
		(unit 1)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(fields_autoplaced yes)
		(uuid "{uid()}")
		(property "Reference" "{ref}"
			(at 322.58 85.09 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Value" "PWR_FLAG"
			(at 322.58 85.09 0)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Footprint" ""
			(at 322.58 87.63 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Datasheet" ""
			(at 322.58 87.63 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Description" ""
			(at 322.58 87.63 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(pin "1"
			(uuid "{uid()}")
		)
		(instances
			(project ""
				(path "/{PROJ_UUID}"
					(reference "{ref}")
					(unit 1)
				)
			)
		)
	)'''

# Inject before the final closing paren
last_paren = content.rfind(')')
content = content[:last_paren] + pwrflag + '\n' + content[last_paren:]

SCH.write_text(content, encoding="utf-8")
print(f"Added {ref} PWR_FLAG at (322.58, 87.63) on SHUNT_NODE net")
print("Done! Saved. Backup at .kicad_sch.bak")
