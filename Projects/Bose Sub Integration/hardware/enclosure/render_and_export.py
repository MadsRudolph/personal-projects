"""
subxo enclosure - renders + STL export

Run AFTER enclosure_model.py (that script wipes and rebuilds the collection,
taking the camera and lights with it, so this one recreates them).

Writes:
    renders/*.png
    stl/subxo_base.stl, stl/subxo_lid.stl   (1 unit = 1 mm, ready to slice)

Nothing outside the "SubXO Enclosure" collection is modified: the scene
camera, world, render settings and the default Cube/Light render flags are
all saved and put back at the end.
"""

import bpy
import os
import math
import struct
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(bpy.data.filepath)) if bpy.data.filepath else \
    r"C:\Users\Mads2\personal-projects\Projects\Bose Sub Integration\hardware\enclosure"
RDIR = os.path.join(HERE, "renders")
SDIR = os.path.join(HERE, "stl")
os.makedirs(RDIR, exist_ok=True)
os.makedirs(SDIR, exist_ok=True)

scene = bpy.context.scene
coll = bpy.data.collections["SubXO Enclosure"]

# --- save everything we are about to touch --------------------------------
orig = {
    "camera": scene.camera,
    "world": scene.world,
    "filepath": scene.render.filepath,
    "res": (scene.render.resolution_x, scene.render.resolution_y,
            scene.render.resolution_percentage),
    "hide": {n: bpy.data.objects[n].hide_render
             for n in ("Cube", "Light") if n in bpy.data.objects},
}
for n in orig["hide"]:
    bpy.data.objects[n].hide_render = True

# --- render world ----------------------------------------------------------
w = bpy.data.worlds.get("subxo_render_world") or bpy.data.worlds.new("subxo_render_world")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.10, 0.11, 0.125, 1.0)
scene.world = w

# --- lighting: three suns, no cast shadows, for a clean technical read -----
for nm, rot, energy in (
    ("SubXO_Key",  (math.radians(52), 0, math.radians(38)), 3.2),
    ("SubXO_Fill", (math.radians(66), 0, math.radians(-115)), 2.0),
    ("SubXO_Rim",  (math.radians(112), 0, math.radians(190)), 1.6),
):
    ld = bpy.data.lights.new(nm, type='SUN')
    ld.energy = energy
    ld.use_shadow = False
    ob = bpy.data.objects.new(nm, ld)
    ob.rotation_euler = rot
    coll.objects.link(ob)

for attr, val in (("use_shadows", False), ("taa_render_samples", 64),
                  ("use_raytracing", False), ("use_gtao", True)):
    try:
        setattr(scene.eevee, attr, val)
    except Exception:
        pass

cd = bpy.data.cameras.new("SubXO_Cam")
cd.clip_start, cd.clip_end = 1.0, 20000.0
cam = bpy.data.objects.new("SubXO_Cam", cd)
coll.objects.link(cam)
scene.camera = cam
scene.render.image_settings.file_format = 'PNG'
scene.render.resolution_percentage = 100

CENTRE = Vector((50.5, -63.0, 16.0))
made = []


def shoot(name, loc, rx, ry, target=CENTRE, ortho=None, lens=60.0, euler=None):
    scene.render.resolution_x, scene.render.resolution_y = rx, ry
    if ortho:
        cd.type, cd.ortho_scale = 'ORTHO', ortho
    else:
        cd.type, cd.lens = 'PERSP', lens
    cam.location = Vector(loc)
    cam.rotation_euler = euler if euler else \
        (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(RDIR, name)
    bpy.ops.render.render(write_still=True)
    made.append(name + ".png")


lid = bpy.data.objects["Lid"]
base = bpy.data.objects["Base"]

lid.location.z = 55.0
shoot("01_exploded_iso", (250, -300, 210), 1600, 1100)
lid.location.z = 0.0

lid.hide_render = True
# straight down: explicit euler, a look-at has no defined up vector here
shoot("02_interior_top", (50.5, -63.0, 400), 1200, 1500, ortho=155.0, euler=(0, 0, 0))
shoot("03_interior_iso", (215, -265, 150), 1600, 1100, lens=70.0)
lid.hide_render = False

shoot("04_assembled_front", (165, -340, 135), 1600, 1100,
      target=Vector((50.5, -80.0, 14.0)), lens=52.0)
shoot("05_assembled_rear", (-170, 230, 130), 1600, 1100, lens=70.0)

# side elevation with the shell hidden: shows what actually sets the height
base.hide_render = True
shoot("06_height_stack", (-450, -63.0, 15.5), 1600, 900, ortho=150.0,
      target=Vector((50.5, -63.0, 15.5)))
base.hide_render = False


# --- STL export ------------------------------------------------------------
def export(objname, fname):
    ob = bpy.data.objects[objname]
    ob.hide_set(False)                      # hidden objects cannot be selected,
    bpy.ops.object.select_all(action='DESELECT')   # and export silently empties
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    p = os.path.join(SDIR, fname)
    bpy.ops.wm.stl_export(filepath=p, export_selected_objects=True,
                          global_scale=1.0, use_scene_unit=False,
                          apply_modifiers=True)
    ob.select_set(False)
    return p


def stl_bbox(p):
    """Read the STL back and measure it, so a bad scale cannot slip through."""
    with open(p, "rb") as f:
        f.read(80)
        n = struct.unpack("<I", f.read(4))[0]
        lo, hi = [1e30] * 3, [-1e30] * 3
        for _ in range(n):
            d = f.read(50)
            for v in range(3):
                for a in range(3):
                    o = 12 + v * 12 + a * 4
                    val = struct.unpack("<f", d[o:o + 4])[0]
                    lo[a] = min(lo[a], val)
                    hi[a] = max(hi[a], val)
    return {"tris": n, "size_mm": [round(hi[i] - lo[i], 2) for i in range(3)]}


stls = {}
for objname, fname in (("Base", "subxo_base.stl"), ("Lid", "subxo_lid.stl")):
    p = export(objname, fname)
    stls[fname] = stl_bbox(p)

# --- restore ---------------------------------------------------------------
scene.camera = orig["camera"]
scene.world = orig["world"]
scene.render.filepath = orig["filepath"]
(scene.render.resolution_x, scene.render.resolution_y,
 scene.render.resolution_percentage) = orig["res"]
for n, v in orig["hide"].items():
    bpy.data.objects[n].hide_render = v

result = {"renders": made, "stl": stls}
print(result)
