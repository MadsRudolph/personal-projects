#!/usr/bin/env python3
"""Generate the air-core crossover coil footprints.

A bought air-core coil has no standard footprint: you lay it flat on the
board, glue or cable-tie it down, and take its two leads to a pair of holes.
So each footprint here is just two generous through-holes plus a silkscreen
and courtyard circle the size of the coil, so the placer keeps the space clear.

Diameters are TYPICAL for 0.8 mm (20 AWG) air-core coils of that inductance
(Dayton AC20-xx / Jantzen Audio class).  They are provisional -- measure the
coils you actually buy and re-run this script with the real numbers.

Run:  python3 make_coil_footprints.py
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "lib" / "crossover.pretty"
OUT.mkdir(parents=True, exist_ok=True)

PITCH = 10.16      # lead hole spacing, c-c
DRILL = 1.4        # 0.8 mm wire + slack
PADSZ = 3.2        # generous annular ring for a hand-soldered coil lead

# name suffix, outside diameter (mm), what it is for
COILS = [
    ("D40mm", 40.0, "0.20 mH, target DCR 0.29 ohm (L101, tweeter tank)"),
    ("D42mm", 42.0, "0.25 mH, target DCR 0.35 ohm (L102, tweeter shunt)"),
    ("D55mm", 55.0, "0.70 mH, target DCR 0.60 ohm (L201, woofer tank)"),
    ("D70mm", 70.0, "2.0 mH, target DCR 1.06 ohm (L202, woofer series)"),
]


def circle(radius, layer, width):
    return (
        "\t(fp_circle\n"
        "\t\t(center 0 0)\n"
        f"\t\t(end {radius} 0)\n"
        f"\t\t(stroke\n\t\t\t(width {width})\n\t\t\t(type solid)\n\t\t)\n"
        "\t\t(fill no)\n"
        f'\t\t(layer "{layer}")\n'
        "\t)"
    )


for suffix, od, purpose in COILS:
    name = f"L_AirCore_{suffix}_0.8mm"
    r = od / 2.0
    ref_y = -(r + 2.0)
    val_y = r + 2.0
    body = [
        f'(footprint "{name}"',
        "\t(version 20260206)",
        '\t(generator "crossover-tools")',
        '\t(generator_version "10.0")',
        '\t(layer "F.Cu")',
        f'\t(descr "Air-core crossover coil, 0.8 mm (20 AWG) wire, ~{od:.0f} mm '
        f'outside diameter. {purpose}. PROVISIONAL - measure the real coil and '
        'regenerate with tools/make_coil_footprints.py.")',
        '\t(tags "inductor air core crossover speaker THT")',
        '\t(property "Reference" "L**"',
        f"\t\t(at 0 {ref_y} 0)",
        '\t\t(layer "F.SilkS")',
        "\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1 1)\n\t\t\t\t(thickness 0.15)"
        "\n\t\t\t)\n\t\t)",
        "\t)",
        f'\t(property "Value" "{name}"',
        f"\t\t(at 0 {val_y} 0)",
        '\t\t(layer "F.Fab")',
        "\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1 1)\n\t\t\t\t(thickness 0.15)"
        "\n\t\t\t)\n\t\t)",
        "\t)",
        "\t(attr through_hole)",
        "\t(duplicate_pad_numbers_are_jumpers no)",
        circle(r, "F.SilkS", 0.12),                  # coil outside diameter
        circle(r * 0.45, "F.SilkS", 0.12),           # rough winding bore
        circle(r, "F.Fab", 0.1),
        circle(r + 1.0, "F.CrtYd", 0.05),            # keep-out for the placer
        '\t(pad "1" thru_hole circle',
        f"\t\t(at {-PITCH / 2} 0)",
        f"\t\t(size {PADSZ} {PADSZ})",
        f"\t\t(drill {DRILL})",
        '\t\t(layers "*.Cu" "*.Mask")',
        "\t\t(remove_unused_layers no)",
        "\t)",
        '\t(pad "2" thru_hole circle',
        f"\t\t(at {PITCH / 2} 0)",
        f"\t\t(size {PADSZ} {PADSZ})",
        f"\t\t(drill {DRILL})",
        '\t\t(layers "*.Cu" "*.Mask")',
        "\t\t(remove_unused_layers no)",
        "\t)",
        ")",
    ]
    (OUT / f"{name}.kicad_mod").write_text("\n".join(body) + "\n", encoding="utf-8")
    print("wrote", OUT / f"{name}.kicad_mod",
          f"  pad gap {PITCH - PADSZ:.2f} mm (mill floor 0.8 mm)")
