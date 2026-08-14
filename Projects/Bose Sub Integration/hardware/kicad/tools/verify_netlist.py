"""Check the exported netlist against the handoff document, net by net.

This is deliberately an INDEPENDENT transcription of the tables in
``HANDOFF - KiCad Schematic.md``: it is written from the document, not from
build_schematic.py, so a generator bug (wrong op-amp unit, a label that missed
its stub, a pin geometry mistake) shows up as a mismatch rather than being
echoed back. It also re-checks the five danger-list items explicitly and
confirms every footprint is through-hole and present on disk.

Usage:  py -3.13 tools/verify_netlist.py            (expects subxo.json next to
                                                     the schematic)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NETJSON = ROOT / "subxo.json"

# Resolution order must match KiCad's: the project fp-lib-table first (its
# entries shadow same-named global ones), then the stock libraries of the KiCad
# that actually opens this project -- KiCad 10. Checking against KiCad 9 instead
# is how the bornier terminal blocks got through: 9 still ships them, 10 deleted
# them from TerminalBlock.pretty, so the board would not load them.
FP_DIRS = [
    ROOT / "lib",
    Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints"),
]

# net -> {"REF.PIN", ...}, transcribed from the handoff tables.
EXPECTED = {
    # Power (handoff "Power" table)
    "VIN": {"J4.1", "C10.1", "U2.1"},
    "GND": {"J4.2", "C10.2", "U2.2", "C11.2", "C12.2", "C13.2", "C14.2",
            "R9.2", "C15.2", "U1.11", "J1.2", "J2.2", "J6.3", "R7.1", "JP3.1"},
    "V12": {"U2.3", "C11.1", "C12.1", "C13.1", "C14.1", "R8.1", "U1.4"},
    "VG_DIV": {"R8.2", "R9.1", "C15.1", "U1.10"},
    # TL074 sections A3 (virtual ground) and A4 (terminated spare)
    "VGND": {"U1.8", "U1.9", "U1.12", "U1.5", "R_b1.2", "R_b2.2",
             "JP2.2", "JP2.4", "JP2.6"},
    "SPARE_OUT": {"U1.13", "U1.14"},
    # Signal path
    "IN_L": {"J1.1", "C_in1.1"},
    "IN_R": {"J2.1", "C_in2.1"},
    "A_L": {"C_in1.2", "R_b1.1", "R1_1.1"},
    "A_R": {"C_in2.2", "R_b2.1", "R1_2.1"},
    "N1": {"R1_1.2", "R1_2.2", "R2.1", "JP1.2", "JP1.4", "JP1.6"},
    "N2": {"R2.2", "U1.3", "C2_1.1", "C2_2.1", "C2_3.1"},
    "OUT1": {"U1.1", "U1.2", "C1_1.1", "C1_2.1", "C1_3.1", "R3.1", "J5.1"},
    "INV_IN": {"R3.2", "R4.1", "U1.6"},
    "OUT2": {"U1.7", "R4.2", "J5.2"},
    # Switched capacitors
    "C1A_SEL": {"C1_1.2", "JP1.1"},
    "C1B_SEL": {"C1_2.2", "JP1.3"},
    "C1C_SEL": {"C1_3.2", "JP1.5"},
    "C2A_SEL": {"C2_1.2", "JP2.1"},
    "C2B_SEL": {"C2_2.2", "JP2.3"},
    "C2C_SEL": {"C2_3.2", "JP2.5"},
    # Output stage
    "SW_COM": {"J5.3", "C_out1.1"},
    "POT_TOP": {"C_out1.2", "J6.1"},
    "POT_W": {"J6.2", "R5.1", "R6.1"},
    "OUT_TIP": {"R5.2", "J3.1"},
    "OUT_RING": {"R6.2", "J3.2"},
    "OUT_GND": {"R7.2", "JP3.2", "J3.3"},
}

EXPECTED_VALUES = {
    "C10": "100uF", "C11": "100uF", "C12": "100nF", "C13": "100nF",
    "C14": "100nF", "C15": "100uF", "R8": "10k", "R9": "10k",
    "C_in1": "2.2uF", "C_in2": "2.2uF", "R_b1": "100k", "R_b2": "100k",
    "R1_1": "16k5", "R1_2": "16k5", "R2": "8k25", "R3": "10k", "R4": "10k",
    "R5": "100R", "R6": "100R", "R7": "10R",
    "C1_1": "330nF", "C1_2": "220nF", "C1_3": "150nF",
    "C2_1": "150nF", "C2_2": "100nF", "C2_3": "68nF",
    "C_out1": "10uF", "U1": "TL074", "U2": "LM7812",
}

SMD_MARKERS = ("SOIC", "TSOT", "SOT-23", "SolderWire", "QFN", "0805", "0603",
               "1206", "SMD", "Handsolder")

fails: list[str] = []
notes: list[str] = []


def check(cond, msg):
    (notes if cond else fails).append(("ok   " if cond else "FAIL ") + msg)


def main() -> int:
    data = json.loads(NETJSON.read_text(encoding="utf-8"))
    comps = {c["ref"]: c for c in data["components"]}

    # actual net -> {"REF.PIN"}; the exporter prefixes local nets with "/"
    actual: dict[str, set[str]] = {}
    for ref, c in comps.items():
        for pin, net in c["pads"].items():
            actual.setdefault(net.lstrip("/"), set()).add(f"{ref}.{pin}")

    # 1. every handoff net, member for member
    for net, want in EXPECTED.items():
        got = actual.get(net)
        if got is None:
            fails.append(f"FAIL net {net} missing from the netlist")
            continue
        if got != want:
            fails.append(f"FAIL net {net}: extra={sorted(got - want)} "
                         f"missing={sorted(want - got)}")
        else:
            notes.append(f"ok   net {net} ({len(want)} pins)")

    # 2. no nets beyond the handoff, and nothing left floating on one pin
    for net, got in actual.items():
        if net not in EXPECTED:
            fails.append(f"FAIL unexpected net {net}: {sorted(got)}")
        elif len(got) < 2:
            fails.append(f"FAIL net {net} has a single connection: {sorted(got)}")

    # 3. every pin of every component lands on a net (no floating pins)
    for ref, c in comps.items():
        for pin, net in c["pads"].items():
            if not net:
                fails.append(f"FAIL {ref}.{pin} is unconnected")

    # 4. TL074: all four sections used or terminated, both supply pins wired
    tl = comps["U1"]["pads"]
    check(set(tl) == {str(i) for i in range(1, 15)},
          "U1: all 14 DIP pins carry a net (no floating section, no NC pin)")

    # 5. the handoff's five danger-list items, checked one at a time
    check("C1_1.2" in actual["C1A_SEL"] and "JP1.1" in actual["C1A_SEL"]
          and actual["N1"] >= {"JP1.2", "JP1.4", "JP1.6"},
          "danger 1: C1 group returns to N1 through JP1, not to N2")
    check(not any(p.startswith("C1_") for p in actual["N2"]),
          "danger 1: no C1 capacitor sits on N2")
    check(actual["A_L"] >= {"R_b1.1"} and actual["A_R"] >= {"R_b2.1"}
          and "R_b1.2" in actual["VGND"] and "R_b2.2" in actual["VGND"],
          "danger 2: R_b1/R_b2 bias A_L/A_R to VGND, after the coupling caps")
    check(not any(p.startswith("R_b") for p in actual["N1"]),
          "danger 2: no bias resistor lands on N1")
    check("J6.3" in actual["GND"] and "J6.3" not in actual["VGND"],
          "danger 3: pot bottom (J6.3) is on GND, not VGND")
    check("C_out1.1" in actual["SW_COM"] and "C_out1.2" in actual["POT_TOP"],
          "danger 4: C_out pin 1 (+) faces SW_COM, pin 2 faces the pot")
    check("U1.11" in actual["GND"], "danger 5: U1 pin 11 is on GND")
    check("U1.4" in actual["V12"], "danger 5: U1 pin 4 is on V12 (single supply)")

    # 6. values
    for ref, frag in EXPECTED_VALUES.items():
        val = comps[ref]["value"]
        check(frag.lower() in val.lower(), f"value {ref} = {val!r} contains {frag!r}")

    # 7. footprints: assigned, through-hole, and present on disk
    for ref, c in sorted(comps.items()):
        fp = c.get("footprint") or ""
        if not fp:
            fails.append(f"FAIL {ref} has no footprint")
            continue
        if any(m.lower() in fp.lower() for m in SMD_MARKERS):
            fails.append(f"FAIL {ref} footprint looks SMD: {fp}")
        lib, name = fp.split(":", 1)
        found = any((d / f"{lib}.pretty" / f"{name}.kicad_mod").exists()
                    for d in FP_DIRS)
        check(found, f"footprint {ref}: {fp}")

    for line in notes:
        print(line)
    for line in fails:
        print(line)
    print(f"\n{len(notes)} checks passed, {len(fails)} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
