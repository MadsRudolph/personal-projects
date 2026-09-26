#!/usr/bin/env python3
"""Link a script-built board's footprints back to their schematic symbols.

pcbnew.FootprintLoad() gives a footprint with no library nickname and no
symbol path, so KiCad sees every part as unrelated to the schematic:
schematic-parity DRC reports footprint_symbol_mismatch on all of them,
cross-probing does nothing, and "Update PCB from Schematic" treats each part
as new. This sets, from the exported netlist, each footprint's
  - LIB_ID   (e.g. Resistor_THT:R_Axial_...)
  - path     (/<sheet uuids>/<symbol uuid>)
  - Sheetname / Sheetfile fields
without moving anything or touching copper.

    PYTHONPATH=tools/pyshim python3 relink_pcb.py board.kicad_pcb board.net
"""
import sys
import sexpdata
from sexpdata import Symbol
import pcbnew


def components(netfile):
    t = sexpdata.loads(open(netfile, encoding="utf-8").read())
    v = lambda x: x.value() if isinstance(x, Symbol) else x
    head = lambda n: v(n[0]) if isinstance(n, list) and n else None
    out = {}
    for it in t:
        if head(it) != "components":
            continue
        for c in it[1:]:
            f = {head(x): x for x in c[1:] if isinstance(x, list)}
            sheet = next(str(y[1]) for y in f["sheetpath"][1:] if head(y) == "tstamps")
            props = {}
            for x in c[1:]:
                if head(x) == "property":
                    kv = {head(y): str(y[1]) for y in x[1:]}
                    props[kv.get("name")] = kv.get("value")
            out[str(f["ref"][1])] = {"fp": str(f["footprint"][1]),
                                     "path": sheet.rstrip("/") + "/" + str(f["tstamps"][1]),
                                     "sheetname": props.get("Sheetname", ""),
                                     "sheetfile": props.get("Sheetfile", "")}
    return out


def relink(board, comps):
    n = 0
    for fp in board.GetFootprints():
        c = comps.get(fp.GetReference())
        if not c:
            continue
        lib, name = c["fp"].split(":", 1)
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetPath(pcbnew.KIID_PATH(c["path"]))
        if c["sheetname"]:
            fp.SetSheetname(c["sheetname"])
        if c["sheetfile"]:
            fp.SetSheetfile(c["sheetfile"])
        n += 1
    return n


if __name__ == "__main__":
    pcb, net = sys.argv[1], sys.argv[2]
    b = pcbnew.LoadBoard(pcb)
    n = relink(b, components(net))
    pcbnew.SaveBoard(pcb, b)
    print(f"relinked {n}/{len(b.GetFootprints())} footprints in {pcb}")
