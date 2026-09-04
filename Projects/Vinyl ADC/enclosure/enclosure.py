"""Parametric, support-free two-part enclosure for the Vinyl ADC digital PCB.

Run with Blender 4.4+:
  & blender.exe -b -P enclosure\enclosure.py

All dimensions are millimetres. Blender scene units are configured so one
Blender unit equals one millimetre.
"""

from __future__ import annotations

import math
import os
import sys

import bpy


BOARD_X = 100.0
BOARD_Y = 100.0
BOARD_Z = 1.6
CLEARANCE = 0.5
WALL = 3.0
FLOOR = 3.0
STANDOFF_H = 5.0
BASE_H = 18.0
LID_T = 3.0
LIP_H = 2.0
LIP_T = 1.4
OUTER_X = BOARD_X + 2 * (CLEARANCE + WALL)  # 107 mm
OUTER_Y = BOARD_Y + 2 * (CLEARANCE + WALL)  # 107 mm
INNER_X = BOARD_X + 2 * CLEARANCE           # 101 mm
INNER_Y = BOARD_Y + 2 * CLEARANCE           # 101 mm
BOARD_BOTTOM_Z = FLOOR + STANDOFF_H

# Converted from KiCad coordinates. Board bounds are X/Y = 20..120 mm.
# Blender Y is inverted so the PCB front (KiCad Y=120) faces -Y.
MOUNT_HOLES = {
    "H1": (-44.0, 44.0),
    "H2": (44.0, 44.0),
    "H3": (-44.0, -44.0),
    "H4": (44.0, -44.0),
}

CONNECTORS = {
    "J2_GPIO": {"center": (-9.78, -45.60), "side": "front", "width": 22.5, "height": 10.0},
    "J4_BUS": {"center": (8.89, 40.00), "side": "rear", "width": 22.5, "height": 10.0},
}


def configure_units() -> None:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 0.001


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def cube(name: str, size: tuple[float, float, float], location: tuple[float, float, float]):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def cylinder(name: str, radius: float, depth: float, location: tuple[float, float, float], vertices: int = 64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    return obj


def boolean(target, cutter, operation="DIFFERENCE") -> None:
    bpy.context.view_layer.objects.active = target
    modifier = target.modifiers.new(name=f"{operation}_{cutter.name}", type="BOOLEAN")
    modifier.operation = operation
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def bevel(obj, width=1.0, segments=3) -> None:
    modifier = obj.modifiers.new(name="Edge softening", type="BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    modifier.angle_limit = math.radians(20)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def build_base(name="Vinyl_ADC_Base", add_bevel=True):
    base = cube(name, (OUTER_X, OUTER_Y, BASE_H), (0, 0, BASE_H / 2))
    cavity = cube("Base_cavity", (INNER_X, INNER_Y, BASE_H - FLOOR + 0.2), (0, 0, FLOOR + (BASE_H - FLOOR + 0.2) / 2))
    boolean(base, cavity)

    # Four 7 mm bosses, bored to the exact 3.2 mm board-hole diameter.
    for ref, (x, y) in MOUNT_HOLES.items():
        boss = cylinder(f"Boss_{ref}", 3.5, STANDOFF_H, (x, y, FLOOR + STANDOFF_H / 2))
        boolean(base, boss, "UNION")
        bore = cylinder(f"Bore_{ref}", 1.6, FLOOR + STANDOFF_H + 0.4, (x, y, (FLOOR + STANDOFF_H) / 2))
        boolean(base, bore)

    if add_bevel:
        bevel(base, 0.8, 3)
    return base


def build_lid(name="Vinyl_ADC_Lid", assembled=True, add_bevel=True):
    z_plate = BASE_H + LID_T / 2 if assembled else LID_T / 2
    lid = cube(name, (OUTER_X, OUTER_Y, LID_T), (0, 0, z_plate))

    # Downward locating lip in the assembled model. For its exported STL the
    # complete lid is rotated so the broad outer face sits on the print bed.
    lip_z = BASE_H - LIP_H / 2 if assembled else LID_T + LIP_H / 2
    outer = cube("Lid_lip_outer", (INNER_X - 0.4, INNER_Y - 0.4, LIP_H), (0, 0, lip_z))
    inner = cube("Lid_lip_inner", (INNER_X - 0.4 - 2 * LIP_T, INNER_Y - 0.4 - 2 * LIP_T, LIP_H + 0.2), (0, 0, lip_z))
    boolean(outer, inner)
    boolean(lid, outer, "UNION")

    # J2 and J4 are vertical/top-entry headers. Their access therefore belongs
    # in the lid, not in a side wall; this preserves the PCB orientation.
    for key, item in CONNECTORS.items():
        cx, cy = item["center"]
        cut_z = BASE_H + LID_T / 2 if assembled else LID_T / 2
        cut = cube(f"{key}_cut", (item["width"], 5.8, LID_T + 0.6), (cx, cy, cut_z))
        boolean(lid, cut)
    if add_bevel:
        bevel(lid, 0.8, 3)
    return lid


def export_selected_stl(obj, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True, apply_modifiers=True)


def export_enclosure(root: str) -> None:
    configure_units()
    clear_scene()
    base = build_base(add_bevel=False)
    export_selected_stl(base, os.path.join(root, "enclosure", "vinyl-adc-base.stl"))

    clear_scene()
    lid = build_lid(assembled=False, add_bevel=False)
    export_selected_stl(lid, os.path.join(root, "enclosure", "vinyl-adc-lid.stl"))


if __name__ == "__main__":
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    export_enclosure(repo_root)
    print(f"Exported enclosure STLs under {os.path.join(repo_root, 'enclosure')}")
