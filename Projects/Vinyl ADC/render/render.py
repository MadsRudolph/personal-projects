"""Build and render the Vinyl ADC product scene in Blender.

PowerShell reproduction:
  & blender.exe -b -P render\render.py
"""

from __future__ import annotations

import importlib.util
import math
import os
import shutil
import sys

import bpy
from mathutils import Vector


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENCLOSURE_SCRIPT = os.path.join(ROOT, "enclosure", "enclosure.py")
spec = importlib.util.spec_from_file_location("vinyl_enclosure", ENCLOSURE_SCRIPT)
enc = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = enc
spec.loader.exec_module(enc)


def material(name, color, metallic=0.0, roughness=0.45):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


MAT_PLA = None
MAT_DARK = None
MAT_PCB = None
MAT_GOLD = None
MAT_SILK = None
MAT_BLUE = None
MAT_CERAMIC = None


def assign(obj, mat):
    obj.data.materials.append(mat)
    return obj


def bevel(obj, width=0.5, segments=3):
    modifier = obj.modifiers.new(name="Product edge radius", type="BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    modifier.angle_limit = math.radians(18)


def cube(name, size, loc, mat, radius=0.35):
    obj = enc.cube(name, size, loc)
    assign(obj, mat)
    if radius:
        bevel(obj, radius, 3)
    return obj


def cyl(name, radius, depth, loc, mat, vertices=48):
    obj = enc.cylinder(name, radius, depth, loc, vertices)
    assign(obj, mat)
    bevel(obj, min(0.25, radius / 5), 2)
    return obj


def pcb_xy(x, y):
    return x - 70.0, 70.0 - y


def add_text(body, loc, size, mat, extrude=0.08, align="CENTER", rotation=(0, 0, 0)):
    bpy.ops.object.text_add(location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = "Label_" + body.replace(" ", "_")
    obj.data.body = body
    obj.data.align_x = align
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = extrude
    obj.data.bevel_depth = 0.025
    assign(obj, mat)
    return obj


def add_dip(ref, x, y, pins, rot=0, oscillator=False):
    px, py = pcb_xy(x, y)
    along = (pins // 2 - 1) * 2.54 + 4.0
    sx, sy = 10.2, along
    if abs(rot) == 90:
        sx, sy = sy, sx
    top = enc.BOARD_BOTTOM_Z + enc.BOARD_Z
    body = cube(ref, (sx, sy, 4.1 if not oscillator else 4.8), (px, py, top + 2.4), MAT_DARK, 0.45)
    if oscillator:
        assign(body, material("Oscillator metal", (0.37, 0.40, 0.42), metallic=0.72, roughness=0.24))
    # Gold gullies suggest the through-hole pins without overloading geometry.
    count = pins // 2
    for side in (-1, 1):
        for i in range(count):
            along_pos = (i - (count - 1) / 2) * 2.54
            if abs(rot) == 90:
                pin_loc = (px + along_pos, py + side * 5.0, top + 0.35)
            else:
                pin_loc = (px + side * 5.0, py - along_pos, top + 0.35)
            cyl(f"{ref}_pin", 0.52, 0.55, pin_loc, MAT_GOLD, 20)


def add_disc_cap(ref, x, y, rot=0):
    px, py = pcb_xy(x, y)
    top = enc.BOARD_BOTTOM_Z + enc.BOARD_Z
    body = cube(ref, (5.0 if rot == 0 else 2.3, 2.3 if rot == 0 else 5.0, 4.8), (px, py, top + 2.6), MAT_CERAMIC, 0.6)
    return body


def add_header(ref, x, y, rows, cols, rot=0, panel_access=False):
    px, py = pcb_xy(x, y)
    long_dim = cols * 2.54 + 1.8
    short_dim = rows * 2.54 + 1.8
    sx, sy = short_dim, long_dim
    if abs(rot) == 90:
        sx, sy = long_dim, short_dim
    top = enc.BOARD_BOTTOM_Z + enc.BOARD_Z
    cube(ref, (sx, sy, 2.8), (px, py, top + 1.4), MAT_DARK, 0.25)
    for row in range(rows):
        for col in range(cols):
            a = (col - (cols - 1) / 2) * 2.54
            b = (row - (rows - 1) / 2) * 2.54
            dx, dy = (a, b) if abs(rot) == 90 else (b, -a)
            pin_h = 13.5 if panel_access else 7.0
            cyl(f"{ref}_pin", 0.34, pin_h, (px + dx, py + dy, top + pin_h / 2), MAT_GOLD, 16)


def build_board():
    board = cube("Vinyl_ADC_Digital_PCB", (enc.BOARD_X, enc.BOARD_Y, enc.BOARD_Z), (0, 0, enc.BOARD_BOTTOM_Z + enc.BOARD_Z / 2), MAT_PCB, 0.5)
    for ref, (x, y) in enc.MOUNT_HOLES.items():
        cutter = enc.cylinder(f"PCB_hole_{ref}", 1.6, enc.BOARD_Z + 0.6, (x, y, enc.BOARD_BOTTOM_Z + enc.BOARD_Z / 2), 48)
        enc.boolean(board, cutter)

    # Exact footprint centres from the 2026-09-03 PCB backup.
    add_dip("U3", 41.08, 52.50, 14)
    add_dip("U4", 86.38, 38.80, 16, -90)
    add_dip("U6", 38.08, 85.52, 16)
    add_dip("U8", 99.58, 70.10, 16)
    add_dip("X1", 27.99, 59.29, 8, oscillator=True)
    for ref, x, y, rot in (
        ("C9", 42.0, 75.1, 0), ("C10", 31.1, 75.2, 0),
        ("C11", 65.3, 74.4, 0), ("C13", 40.7, 109.6, 0),
        ("C15", 93.6, 70.5, 90),
    ):
        add_disc_cap(ref, x, y, rot)
    add_header("J1_CLK_SEL", 32.3525, 49.9075, 1, 3, 180)
    add_header("J2_GPIO", 60.22, 115.60, 1, 8, 90, panel_access=True)
    add_header("J4_BUS", 78.89, 30.00, 2, 8, -90, panel_access=True)

    # Minimal, legible silkscreen treatment.
    z = enc.BOARD_BOTTOM_Z + enc.BOARD_Z + 0.12
    add_text("VINYL ADC", (-5, 8, z), 5.5, MAT_SILK, 0.025, rotation=(0, 0, 0))
    add_text("DIGITAL / 48 kHz", (-5, 1.5, z), 2.2, MAT_SILK, 0.02, rotation=(0, 0, 0))
    return board


def create_product():
    global MAT_PLA, MAT_DARK, MAT_PCB, MAT_GOLD, MAT_SILK, MAT_BLUE, MAT_CERAMIC
    MAT_PLA = material("Warm graphite matte PLA", (0.16, 0.19, 0.23), metallic=0.0, roughness=0.34)
    MAT_DARK = material("IC epoxy", (0.018, 0.021, 0.026), metallic=0.0, roughness=0.30)
    MAT_PCB = material("Deep green soldermask", (0.025, 0.19, 0.105), metallic=0.05, roughness=0.28)
    MAT_GOLD = material("ENIG and pins", (0.82, 0.46, 0.08), metallic=0.82, roughness=0.18)
    MAT_SILK = material("Silkscreen", (0.86, 0.91, 0.84), metallic=0.0, roughness=0.5)
    MAT_BLUE = material("Accent", (0.04, 0.37, 0.72), metallic=0.35, roughness=0.28)
    MAT_CERAMIC = material("Capacitor ceramic", (0.76, 0.27, 0.055), metallic=0.0, roughness=0.4)

    base = enc.build_base(add_bevel=True)
    assign(base, MAT_PLA)
    lid = enc.build_lid(add_bevel=True)
    assign(lid, MAT_PLA)
    build_board()

    # Lid graphics are separate geometry so their exploded motion is explicit.
    lid_items = [lid]
    lid_items.append(add_text("VINYL / ADC", (0, -1, enc.BASE_H + enc.LID_T + 0.08), 9.5, MAT_SILK, 0.11))
    lid_items.append(add_text("DISCRETE  •  STEREO  •  48 kHz", (0, -12, enc.BASE_H + enc.LID_T + 0.08), 2.25, MAT_BLUE, 0.07))
    lid_items.append(add_text("GPIO OUT", (-9.78, -40.8, enc.BASE_H + enc.LID_T + 0.08), 2.0, MAT_SILK, 0.05))
    lid_items.append(add_text("BOARD BUS", (8.89, 35.2, enc.BASE_H + enc.LID_T + 0.08), 2.0, MAT_SILK, 0.05))
    return base, lid_items


def look_at(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_area(name, loc, energy, size, color):
    data = bpy.data.lights.new(name=name, type="AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    look_at(obj, (0, 0, 5))
    return obj


def add_sun(name, rotation, energy, color):
    data = bpy.data.lights.new(name=name, type="SUN")
    data.energy = energy
    data.angle = math.radians(18)
    data.color = color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.rotation_euler = rotation
    return obj


def setup_studio():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.render.resolution_percentage = 100
    scene.world.color = (0.008, 0.010, 0.015)
    world = scene.world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.008, 0.011, 0.018, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.42

    floor_mat = material("Studio floor", (0.018, 0.022, 0.030), 0.0, 0.24)
    floor = cube("Studio_floor", (520, 520, 3), (0, 0, -2.2), floor_mat, 1.0)
    add_area("Key", (-110, -95, 175), 900, 105, (0.70, 0.82, 1.0))
    add_area("Fill", (145, -30, 105), 650, 85, (1.0, 0.62, 0.38))
    add_area("Rim", (20, 135, 155), 1050, 75, (0.42, 0.62, 1.0))
    # Sun lights are scale-independent; scene geometry is authored as 1 BU/mm.
    add_sun("Soft key sun", (math.radians(24), math.radians(-28), math.radians(-35)), 3.2, (0.72, 0.84, 1.0))
    add_sun("Warm fill sun", (math.radians(58), math.radians(12), math.radians(132)), 1.8, (1.0, 0.70, 0.48))
    add_sun("Top rim sun", (math.radians(8), math.radians(35), math.radians(40)), 2.0, (0.55, 0.70, 1.0))

    camera_data = bpy.data.cameras.new("Product camera")
    camera = bpy.data.objects.new("Product camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 55
    return camera


def render_view(camera, filename, loc, target, lens=55):
    camera.location = loc
    camera.data.lens = lens
    look_at(camera, target)
    path = os.path.join(ROOT, "render", filename)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered {path}")


def main():
    enc.configure_units()
    enc.clear_scene()
    enc.export_enclosure(ROOT)
    enc.clear_scene()
    _base, lid_items = create_product()
    camera = setup_studio()

    render_view(camera, "hero.png", (142, -158, 112), (0, 0, 9), 56)
    render_view(camera, "front.png", (0, -180, 72), (0, -5, 12), 62)

    for obj in lid_items:
        obj.location.z += 35.0
    render_view(camera, "exploded.png", (148, -166, 142), (0, 0, 22), 58)

    blend_path = os.path.join(ROOT, "render", "vinyl-adc.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    assets = os.path.join(ROOT, "site", "assets")
    os.makedirs(assets, exist_ok=True)
    for name in ("hero.png", "front.png", "exploded.png"):
        shutil.copy2(os.path.join(ROOT, "render", name), os.path.join(assets, name))
    print(f"Saved {blend_path}")


if __name__ == "__main__":
    main()
