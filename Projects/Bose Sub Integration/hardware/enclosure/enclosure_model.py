"""
subxo enclosure - parametric generator
======================================

Builds base + lid + PCB mock-up for the sub-crossover board.

Re-run this whole file in Blender to rebuild from scratch. Everything lives in
the "SubXO Enclosure" collection, which is wiped and rebuilt on each run;
nothing outside that collection is touched.

Units: 1 Blender unit = 1 mm.

Origin / axes
-------------
KiCad gives positions as (X right, Y down) from the top-left of the board
outline. Here:  blender_x = kicad_x,  blender_y = -kicad_y,  z = 0 at the
inside face of the base floor.

So the board occupies X 0..101, Y 0..-104.
  Y = 0     -> REAR edge   (J1-J4, the I/O terminals)
  Y = -104  -> FRONT edge  (J5/J6, the user controls)

CONFIRMED AGAINST THE BOARD
---------------------------
Outline 101.0 x 104.0 mm and all 13 connector positions were read from
hardware/kicad/subxo.kicad_pcb and match the handoff exactly.

The bottom-face GND pour fills to 0.53 mm from every edge, so there is no
copper-free rim. Nearest *signal* copper to each edge:
    left 4.22 mm (/N1)   right 4.52 mm (/POT_W)
    rear 2.52 mm (/POT_W)  front 2.52 mm (/PWR_A)
Retention therefore only ever touches GND pour, and never goes deeper than
~4 mm at a corner.
"""

import bpy
import bmesh
import math
import os
from mathutils import Vector, Matrix

# ---------------------------------------------------------------------------
# Use the real board exported from KiCad, instead of block stand-ins.
#
# Regenerate the GLB in two steps, from hardware/kicad/:
#
#   "C:/Program Files/KiCad/10.0/bin/python.exe" ../enclosure/pcb3d/make_model_shim.py
#
#   kicad-cli pcb export glb --force --subst-models --no-dnp \
#       -D "KICAD9_3DMODEL_DIR=<abs path to>/hardware/enclosure/pcb3d/models" \
#       --user-origin "82.975x35.975mm" \
#       -o ../enclosure/pcb3d/subxo_board.glb subxo.kicad_pcb
#
# --user-origin is the board outline's top-left in KiCad page coordinates, so
# the export lands with its origin already matching this model's origin. It
# comes in at 1 unit = 1 mm and with Y already negated. No fixing up needed.
#
# The -D redirects model lookup at the shim, so the board file is never edited.
# See pcb3d/make_model_shim.py for why the shim has to be a complete overlay.
# ---------------------------------------------------------------------------
GLB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "pcb3d", "subxo_board.glb")

# ===========================================================================
# PARAMETERS
# ===========================================================================

P = {
    # --- board: measured from subxo.kicad_pcb. Do not change. -------------
    "pcb_w":            101.0,
    "pcb_l":            104.0,
    "pcb_th":           1.6,

    # --- FDM print settings ------------------------------------------------
    "wall":             2.4,    # 6 perimeters at 0.4 mm
    "floor_th":         2.4,
    "lid_th":           2.4,
    "fit_clear":        0.3,    # lid lip sliding fit
    "hole_clear":       0.4,    # added to every panel hole diameter

    # --- internal clearances ----------------------------------------------
    "standoff":         4.0,    # board underside above the floor (bare copper)
    "tallest_part":    19.0,    # U2 LM7812. MEASURED 18.86 off the KiCad 3D
                                # model; kept at 19.0 as a deliberate round-up
    "top_headroom":     2.0,
    "side_gap":         6.0,    # board edge to wall, left/right
    "rear_gap":        10.0,    # board rear edge to rear panel inner face

    # The loom over JP1/JP2 is taller than U2 and must be in the height sum,
    # even though it is not drawn: 15 mm fitted header + Dupont socket, plus
    # 8 mm bend allowance for the wires turning toward the front panel.
    # This is the number that sets internal_h.
    "loom_above_board": 23.0,

    # --- board retention: corner clips -------------------------------------
    "retain_clear":     0.4,    # gap between board top and the retention faces
    "pad":              5.0,    # corner support pad, square, over the board
    "ledge_over":       3.0,    # fixed rear ledge reach over the board top
    "hook_over":        2.0,    # front snap hook reach over the board top
    "clip_th":          2.5,    # snap finger thickness
    "clip_wide":        9.0,    # snap finger width
    "mid_pad":          5.0,    # extra mid-span support pads, left/right

    # --- lid ----------------------------------------------------------------
    "lip_w":            2.0,
    "lip_h":            3.0,
    "led_hole":         4.0,    # through the lid
    "led_cbore":        7.0,    # counterbore from the inside
    "led_web":          1.2,    # material left at the outer face
    "boss_r":           3.2,    # corner screw boss. 6.4 dia is ample for an M3
                                # self-tapper and keeps it clear of the board
    "boss_inset":       1.5,    # pulled off the cavity corner, so the screw
                                # hole keeps ~2.2 mm of lid material to the edge
    "boss_pilot":       2.5,    # M3 self-tapping pilot
    "screw_clear":      3.4,
    # No lid counterbore. The lid is only 2.4 mm thick - recessing an M3 head
    # would leave a 1.2 mm web under it, and a 6.2 mm bore breaks out of the
    # corner entirely. Use M3 pan-head screws and let the heads sit proud.

    # --- panel parts -------------------------------------------------------
    # Rotary: AliExpress "20MM Metal Rotary Switch Selector, M9x0.75, 18 teeth
    # knurl shaft, solder terminals". Order the 2P6T and set its end stop to 3
    # positions - the 1P12T cannot drive both C1 and C2 select.
    #   body diameter  20.0  - from the listing
    #   bushing        M9x0.75, so a 9.5 mm clearance hole
    #   shaft          6 mm knurled, 20 mm long
    #   body depth     MEASURED 18.0, from the face that bears on the inside
    #                  of the front panel to the back of the switch. Sets the
    #                  front gap, and so the box length.
    "rotary_body_dia":  20.0,
    "rotary_body_depth": 18.0,
    # Nominal bushing diameter, like pot_hole and toggle_hole - hole_clear is
    # added on top. M9x0.75 measures 9.0, so the cut hole is 9.4.
    "rotary_hole":       9.0,
    "rotary_x":         20.0,   # kept hard left: JP2 is at x=22.0, JP1 at 32.2

    "pot_body_dia":     16.0,
    "pot_body_depth":   10.0,
    "pot_hole":          7.0,
    "pot_x":            82.90,  # aligned to J6

    "toggle_body_dia":  13.0,
    "toggle_body_depth": 20.0,
    "toggle_hole":       6.0,
    "toggle_x":         44.78,  # aligned to J5

    # RCA inputs are a salvaged 4-pair panel, clipped down to one pair and
    # LAID ON ITS SIDE so the two sockets sit side by side. Measured:
    #   25.3 wide (contains the 22.6 mm outer-to-outer socket span)
    #   22.0 tall, 2.2 thick
    # It is a rectangular aperture, not two round holes.
    "rca_panel_w":      25.3,
    "rca_panel_h":      22.0,
    "rca_panel_th":      2.2,
    "rca_panel_x":      33.0,   # midway between J1 (26.5) and J2 (39.5)
    "rca_panel_clear":   0.4,
    "rca_rim_w":         2.5,   # locating rim around the plate, inside
    "rca_rim_extra":     0.3,   # rim depth beyond the plate thickness
    "rca_panel_depth":  12.0,   # ASSUMPTION: inward protrusion, stand-in only

    # Barrels press out through two round holes; the plate stays inside.
    "rca_span":         22.6,   # MEASURED, outer ring to outer ring
    # MEASURED. Pitch is derived, because the 22.6 span is outer-to-outer of
    # these same barrels:  pitch = span - barrel_dia = 14.3 mm.
    "rca_barrel_dia":    8.3,
    "rca_barrel_clear":  0.4,

    "jack_hole":         6.0,
    "jack_body_dia":    10.0,
    "jack_body_depth":  14.0,
    "jack_x":           58.33,  # aligned to J3

    "dc_hole":           8.0,
    "dc_body_dia":      11.0,
    "dc_body_depth":    14.0,
    "dc_x":             87.42,  # aligned to J4

    # --- LEDs: board-mounted, shining at the lid ---------------------------
    "d1_x": 16.09, "d1_y": 81.53,
    "d2_x":  6.49, "d2_y": 81.53,
}

COLL_NAME = "SubXO Enclosure"

# ===========================================================================
# DERIVED DIMENSIONS
# ===========================================================================

# The rotary switch body must clear the board entirely, otherwise it collides
# with the front-edge film caps (C1_1 sits only 1.4 mm from the front edge).
front_gap = P["rotary_body_depth"] + 3.0

# Internal height is whichever of these three is worst. All three have been
# the binding one at some point, so keep all three in the sum.
#
#   NOTE: the loom term is easy to forget, and forgetting it is silent - the
#   loom envelope simply grows through the lid without any error. It is taller
#   than U2, so with a small rotary switch the LOOM is what sets the height.
h_from_board  = P["standoff"] + P["pcb_th"] + P["tallest_part"] + P["top_headroom"]
h_from_loom   = P["standoff"] + P["pcb_th"] + P["loom_above_board"] + P["top_headroom"]
h_from_rotary = P["rotary_body_dia"] + 3.0

_drivers = {
    "U2 / board parts": h_from_board,
    "JP1/JP2 loom bend": h_from_loom,
    "rotary switch body": h_from_rotary,
}
height_driver = max(_drivers, key=_drivers.get)
internal_h = _drivers[height_driver]

shaft_z = internal_h / 2.0          # FRONT controls share this centre line

# The REAR cluster sits on its own, higher line: centred in the space ABOVE
# the board rather than in the box. With the RCA plate mounted inside, that
# is what keeps the whole plate - and anything hanging off the back of it -
# clear of the board's rear edge, instead of leaving a depth budget to police.
# Front and rear are different faces, so nobody sees the two lines together.
rear_z = (P["standoff"] + P["pcb_th"] + internal_h) / 2.0
board_z0 = P["standoff"]
board_z1 = P["standoff"] + P["pcb_th"]

# cavity extents
in_x0 = -P["side_gap"]
in_x1 = P["pcb_w"] + P["side_gap"]
in_y0 = P["rear_gap"]               # rear
in_y1 = -(P["pcb_l"] + front_gap)   # front

# outer shell extents
out_x0 = in_x0 - P["wall"]
out_x1 = in_x1 + P["wall"]
out_y0 = in_y0 + P["wall"]
out_y1 = in_y1 - P["wall"]

ext_w = out_x1 - out_x0
ext_l = out_y0 - out_y1
ext_h = P["floor_th"] + internal_h + P["lid_th"]

lid_z0 = internal_h
lid_z1 = internal_h + P["lid_th"]

# Corner screw bosses, pulled diagonally off the cavity corners. Sitting them
# exactly on the corner puts them only `wall` from the outside, which does not
# leave enough lid material around the screw hole.
_bi = P["boss_inset"]
BOSS = [(in_x0 + _bi, in_y0 - _bi), (in_x1 - _bi, in_y0 - _bi),
        (in_x0 + _bi, in_y1 + _bi), (in_x1 - _bi, in_y1 + _bi)]

# ===========================================================================
# HELPERS
# ===========================================================================


def get_collection():
    """Wipe and recreate our own collection. Nothing else is touched."""
    coll = bpy.data.collections.get(COLL_NAME)
    if coll:
        for ob in list(coll.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
    else:
        coll = bpy.data.collections.new(COLL_NAME)
        bpy.context.scene.collection.children.link(coll)
    return coll


def _finish(bm, name, coll):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def box(name, x0, x1, y0, y1, z0, z1, coll):
    """Axis-aligned box from two opposite corners."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((x1 - x0, y1 - y0, z1 - z0)), verts=bm.verts)
    bmesh.ops.translate(
        bm, vec=Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)), verts=bm.verts
    )
    return _finish(bm, name, coll)


def box_c(name, cx, cy, sx, sy, z0, z1, coll, rot_z=0.0):
    """Box by centre + size, optionally rotated about Z."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((sx, sy, z1 - z0)), verts=bm.verts)
    if rot_z:
        bmesh.ops.rotate(
            bm, verts=bm.verts, cent=(0, 0, 0),
            matrix=Matrix.Rotation(math.radians(rot_z), 3, "Z"),
        )
    bmesh.ops.translate(bm, vec=Vector((cx, cy, (z0 + z1) / 2)), verts=bm.verts)
    return _finish(bm, name, coll)


def wedge(name, x0, x1, y0, y1, z_lo, zh_x0, zh_x1, coll):
    """
    Prism with a flat bottom and a top face that ramps along X.

    Used for the snap-hook lead-in: the board pressing down on the ramp cams
    the clip outward. A plain box cannot do that - it just butts against the
    board edge and refuses to go in.
    """
    v = [(x0, y0, z_lo), (x1, y0, z_lo), (x1, y1, z_lo), (x0, y1, z_lo),
         (x0, y0, zh_x0), (x1, y0, zh_x1), (x1, y1, zh_x1), (x0, y1, zh_x0)]
    f = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
         (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def cyl(name, cx, cy, cz, dia, length, coll, axis="Z", seg=48):
    """Cylinder centred on (cx, cy, cz), running along `axis`."""
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=seg,
        radius1=dia / 2.0, radius2=dia / 2.0, depth=length,
    )
    if axis == "Y":
        bmesh.ops.rotate(
            bm, verts=bm.verts, cent=(0, 0, 0),
            matrix=Matrix.Rotation(math.radians(90), 3, "X"),
        )
    bmesh.ops.translate(bm, vec=Vector((cx, cy, cz)), verts=bm.verts)
    return _finish(bm, name, coll)


def cut(target, cutters):
    """Boolean-difference a list of cutter objects out of target, then bin them."""
    for c in cutters:
        m = target.modifiers.new(name="cut", type="BOOLEAN")
        m.operation = "DIFFERENCE"
        m.solver = "EXACT"
        m.object = c
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier=m.name)
    for c in cutters:
        bpy.data.objects.remove(c, do_unlink=True)


def fuse(target, others):
    """Boolean-union a list of objects into target, then bin them."""
    for o in others:
        m = target.modifiers.new(name="add", type="BOOLEAN")
        m.operation = "UNION"
        m.solver = "EXACT"
        m.object = o
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier=m.name)
    for o in others:
        bpy.data.objects.remove(o, do_unlink=True)


def clip_to(target, limiter):
    """Boolean-intersect target with limiter, then bin the limiter."""
    m = target.modifiers.new(name="trim", type="BOOLEAN")
    m.operation = "INTERSECT"
    m.solver = "EXACT"
    m.object = limiter
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(limiter, do_unlink=True)


def mat(name, rgba, rough=0.55, metallic=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    if b:
        b.inputs["Base Color"].default_value = rgba
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metallic
    return m


def paint(ob, m):
    ob.data.materials.clear()
    ob.data.materials.append(m)


# ===========================================================================
# BUILD
# ===========================================================================

if bpy.context.object and bpy.context.object.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")

coll = get_collection()

M_CASE  = mat("subxo_case",  (0.80, 0.80, 0.82, 1.0), rough=0.62)
M_LID   = mat("subxo_lid",   (0.72, 0.73, 0.76, 1.0), rough=0.62)
M_PANEL = mat("subxo_panel", (0.72, 0.68, 0.30, 1.0), rough=0.35, metallic=0.85)

# ---------------------------------------------------------------------------
# 1. BASE
# ---------------------------------------------------------------------------

base = box("Base", out_x0, out_x1, out_y1, out_y0, -P["floor_th"], internal_h, coll)

# hollow it out
cavity = box("_cavity", in_x0, in_x1, in_y1, in_y0, 0.0, internal_h + 10.0, coll)
cut(base, [cavity])

# corner screw bosses, fused into the wall corners
bosses = [
    cyl("_boss%d" % i, bx, by, internal_h / 2.0, P["boss_r"] * 2, internal_h, coll)
    for i, (bx, by) in enumerate(BOSS)
]
fuse(base, bosses)

# A boss centred on a cavity corner is wider than the wall it sits in, so it
# would bulge out of the shell. Trim everything back to the outer envelope,
# which leaves the correct quarter-round boss flush with the walls.
clip_to(base, box("_shell", out_x0, out_x1, out_y1, out_y0, -P["floor_th"], internal_h, coll))

# --- RCA plate pocket ------------------------------------------------------
# The salvaged plate stays INSIDE. Its two barrels press out through a pair of
# round holes; this rim only locates the plate in X and Z so it cannot wander
# or rotate. The rim runs through the full wall thickness so it merges with
# the wall as solid overlap rather than meeting it face-to-face.
rc = P["rca_panel_clear"]
ap_x0 = P["rca_panel_x"] - (P["rca_panel_w"] + rc) / 2
ap_x1 = P["rca_panel_x"] + (P["rca_panel_w"] + rc) / 2
ap_z0 = rear_z - (P["rca_panel_h"] + rc) / 2
ap_z1 = rear_z + (P["rca_panel_h"] + rc) / 2

rw = P["rca_rim_w"]
rim_y0 = in_y0 - (P["rca_panel_th"] + P["rca_rim_extra"])
# The plate very nearly fills the wall height, so the top rail would otherwise
# stand proud of the wall and hold the lid off. Clamp it to the wall top.
rim_top = min(ap_z1 + rw, internal_h)
rim_bot = max(ap_z0 - rw, 0.0)
fuse(base, [
    box("_rimL", ap_x0 - rw, ap_x0, rim_y0, out_y0, rim_bot, rim_top, coll),
    box("_rimR", ap_x1, ap_x1 + rw, rim_y0, out_y0, rim_bot, rim_top, coll),
    box("_rimB", ap_x0 - rw, ap_x1 + rw, rim_y0, out_y0, rim_bot, ap_z0, coll),
    box("_rimT", ap_x0 - rw, ap_x1 + rw, rim_y0, out_y0, ap_z1, rim_top, coll),
])

cutters = []

# --- panel holes -----------------------------------------------------------
hc = P["hole_clear"]
rear_y = in_y0 + P["wall"] / 2.0
front_y = in_y1 - P["wall"] / 2.0
deep = P["wall"] * 4

for nm, x, d in (
    ("jack", P["jack_x"], P["jack_hole"]),
    ("dc",   P["dc_x"],   P["dc_hole"]),
):
    cutters.append(cyl("_h_" + nm, x, rear_y, rear_z, d + hc, deep, coll, axis="Y"))

# --- two barrel holes. Pitch is derived from the measured 22.6 span --------
rca_pitch = P["rca_span"] - P["rca_barrel_dia"]
for nm, sgn in (("rcaL", -1), ("rcaR", +1)):
    cutters.append(cyl("_h_" + nm, P["rca_panel_x"] + sgn * rca_pitch / 2,
                       rear_y, rear_z,
                       P["rca_barrel_dia"] + P["rca_barrel_clear"], deep,
                       coll, axis="Y"))

for nm, x, d in (
    ("rotary", P["rotary_x"],  P["rotary_hole"]),
    ("toggle", P["toggle_x"],  P["toggle_hole"]),
    ("pot",    P["pot_x"],     P["pot_hole"]),
):
    cutters.append(cyl("_h_" + nm, x, front_y, shaft_z, d + hc, deep, coll, axis="Y"))

# --- boss pilot holes ------------------------------------------------------
for i, (bx, by) in enumerate(BOSS):
    cutters.append(
        cyl("_pilot%d" % i, bx, by, internal_h - 6.0, P["boss_pilot"], 14.0, coll)
    )

cut(base, cutters)

# --- board retention -------------------------------------------------------
# Rear two corners are FIXED ledges; front two are FLEXING snap clips.
# Slide the board's rear edge under the ledges, then press the front down until
# it snaps. Nothing ever needs a screw through the board.

W, L = P["pcb_w"], P["pcb_l"]
pad, over = P["pad"], P["ledge_over"]
retain = []

# support pads, all four corners: board underside rests on these
for cx, cy in ((0, 0), (W, 0), (0, -L), (W, -L)):
    sx0, sx1 = (cx, cx + pad) if cx == 0 else (cx - pad, cx)
    sy0, sy1 = (cy - pad, cy) if cy == 0 else (cy, cy + pad)
    retain.append(box("_pad", sx0, sx1, sy0, sy1, 0.0, board_z0, coll))

# mid-span support pads on the long edges, to stop the board bowing when the
# front clips are pressed home
mp = P["mid_pad"]
for cx in (0, W):
    sx0, sx1 = (cx, cx + mp) if cx == 0 else (cx - mp, cx)
    retain.append(box("_midpad", sx0, sx1, -L / 2 - mp / 2, -L / 2 + mp / 2, 0.0, board_z0, coll))

# Retention faces sit `retain_clear` ABOVE the board, not flush on it. Two
# reasons: FR4 thickness varies, and both the ledges and hooks are cantilevered
# horizontal overhangs that will droop a few tenths on FDM. At zero clearance
# that droop pinches the board and it will not go in.
rz = board_z1 + P["retain_clear"]

# rear: fixed L-ledges, rigid. The board slides under these first, so they
# need no lead-in - just clearance.
for cx in (0, W):
    ox0, ox1 = (cx - P["clip_th"], cx + over) if cx == 0 else (cx - over, cx + P["clip_th"])
    ux0, ux1 = (cx - P["clip_th"], cx) if cx == 0 else (cx, cx + P["clip_th"])
    retain.append(box("_rearpost", ux0, ux1, -pad, 0.0, 0.0, rz + 2.5, coll))
    retain.append(box("_rearledge", ox0, ox1, -pad, 0.0, rz, rz + 2.5, coll))

# front: flexing snap fingers WITH a lead-in ramp on top of each hook, so
# pressing the board down cams the finger outward instead of jamming on it.
cw = P["clip_wide"]
tip = 0.4                      # flat left at the hook tip; a knife edge will
hook_h = 1.4                   # not print and would shear off anyway
for cx in (0, W):
    fx0, fx1 = (cx - P["clip_th"], cx) if cx == 0 else (cx, cx + P["clip_th"])
    retain.append(box("_clip", fx0, fx1, -L, -L + cw, 0.0, rz + hook_h, coll))
    if cx == 0:
        # tip points inward (+x), so the ramp falls from the finger to the tip
        retain.append(wedge("_hook", cx - P["clip_th"], cx + P["hook_over"],
                            -L, -L + cw, rz, rz + hook_h, rz + tip, coll))
    else:
        retain.append(wedge("_hook", cx - P["hook_over"], cx + P["clip_th"],
                            -L, -L + cw, rz, rz + tip, rz + hook_h, coll))

fuse(base, retain)
paint(base, M_CASE)

# ---------------------------------------------------------------------------
# 2. LID
# ---------------------------------------------------------------------------

lid = box("Lid", out_x0, out_x1, out_y1, out_y0, lid_z0, lid_z1, coll)

# locating lip: LEFT AND RIGHT RAILS ONLY. A full perimeter lip would collide
# with the rotary switch body across the front.
lw, lh = P["lip_w"], P["lip_h"]
fc = P["fit_clear"]
OVER = 0.5   # cutters always overshoot the face they break through. A cutter
             # ending exactly ON a face produces coincident geometry, and the
             # EXACT solver leaves non-manifold edges behind - which slices badly.

# Rails are stopped short of the screw bosses rather than being cut around
# them afterwards. Same result, one less boolean, no coincident faces.
rail_y0 = (in_y1 + _bi) + P["boss_r"] + 1.0
rail_y1 = (in_y0 - _bi) - P["boss_r"] - 1.0
rails = [
    box("_railL", in_x0 + fc, in_x0 + fc + lw, rail_y0, rail_y1, lid_z0 - lh, lid_z0, coll),
    box("_railR", in_x1 - fc - lw, in_x1 - fc, rail_y0, rail_y1, lid_z0 - lh, lid_z0, coll),
]
fuse(lid, rails)

lidcuts = []

# LED windows above D1 and D2. Counterbored from the inside: the LEDs sit
# ~19 mm below the lid, so a plain 4 mm hole would read very dim off-axis.
# The counterbore's top face is deliberately exact - it forms the web - but
# its bottom overshoots through the lid underside.
cb_top = lid_z1 - P["led_web"]
cb_bot = lid_z0 - OVER
for nm, lx, ly in (("D1", P["d1_x"], P["d1_y"]), ("D2", P["d2_x"], P["d2_y"])):
    lidcuts.append(
        cyl("_ledc_" + nm, lx, -ly, (cb_top + cb_bot) / 2,
            P["led_cbore"], cb_top - cb_bot, coll)
    )
    lidcuts.append(
        cyl("_led_" + nm, lx, -ly, lid_z0 + P["lid_th"] / 2,
            P["led_hole"], P["lid_th"] + 2 * OVER, coll)
    )

# screw clearance holes, straight through - no counterbore, see the P dict
for i, (bx, by) in enumerate(BOSS):
    lidcuts.append(cyl("_sc%d" % i, bx, by, lid_z0 + P["lid_th"] / 2,
                       P["screw_clear"], P["lid_th"] + lh + 4 * OVER, coll))

cut(lid, lidcuts)
paint(lid, M_LID)

# ---------------------------------------------------------------------------
# 3. THE REAL BOARD, IMPORTED FROM KICAD
# ---------------------------------------------------------------------------
# No stand-in geometry. Everything here is the actual exported board.
#
# J1-J7 are SUBSTITUTES: genuine Phoenix MKDS-1,5 5.08 mm blocks standing in
# for the bornier parts the footprints name, because no bornier 3D model exists
# in any KiCad library. Same pitch and similar height, different body.
#
# Still absent, no model anywhere:
#   D1, D2  custom energy_system laser-pad footprints. ~6 mm tall.
#   LK1     wire link. Flat.
# Neither is close to binding against U2 at 18.86 mm and the loom at 23 mm.

if not os.path.exists(GLB_PATH):
    raise RuntimeError(
        "Board export missing: %s\nRegenerate it with the kicad-cli command "
        "in the header of this file." % GLB_PATH)

# import into our collection, not whatever happens to be active
_view = bpy.context.view_layer
_prev_active = _view.active_layer_collection
_view.active_layer_collection = next(
    c for c in _view.layer_collection.children if c.collection == coll)

_before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=GLB_PATH)
_imported = [o for o in bpy.data.objects if o not in _before]
_view.active_layer_collection = _prev_active

# The export already lands at 1 unit = 1 mm with the origin on the board's
# top-left and Y negated, so the only correction is lifting it onto the
# standoffs. Move the roots; children follow.
for ob in _imported:
    if ob.parent is None:
        ob.location.z += board_z0
        ob.name = "BOARD_" + ob.name
bpy.context.view_layer.update()

# The loom over JP1/JP2 is deliberately NOT drawn - nothing in this scene is
# invented geometry. It is still in the height sum though: `loom_above_board`
# is what sets internal_h, so the box is sized for a loom you cannot see here.

# ---------------------------------------------------------------------------
# 4. PANEL PART STAND-INS
# ---------------------------------------------------------------------------

panels = []
# rear, protruding inward (+Y) from the rear panel inner face
for nm, x, d, dep in (
    ("JACK",  P["jack_x"],  P["jack_body_dia"], P["jack_body_depth"]),
    ("DC",    P["dc_x"],    P["dc_body_dia"],  P["dc_body_depth"]),
):
    panels.append(cyl("PANEL_" + nm, x, in_y0 - dep / 2, rear_z, d, dep, coll, axis="Y", seg=24))

# RCA plate: sits INSIDE, against the wall, inside the locating rim. Its two
# barrels pass out through the wall. The rearward envelope is an assumption.
pw2, ph2 = P["rca_panel_w"] / 2, P["rca_panel_h"] / 2
panels.append(box("PANEL_RCA_PLATE",
                  P["rca_panel_x"] - pw2, P["rca_panel_x"] + pw2,
                  in_y0 - P["rca_panel_th"], in_y0,
                  rear_z - ph2, rear_z + ph2, coll))
for nm, sgn in (("L", -1), ("R", +1)):
    bx = P["rca_panel_x"] + sgn * rca_pitch / 2
    panels.append(cyl("PANEL_RCA_BARREL_" + nm, bx, out_y0 - 6.0, rear_z,
                      P["rca_barrel_dia"], 16.0, coll, axis="Y", seg=24))
panels.append(box("PANEL_RCA_ENVELOPE",
                  P["rca_panel_x"] - pw2, P["rca_panel_x"] + pw2,
                  in_y0 - P["rca_panel_depth"], in_y0 - P["rca_panel_th"],
                  rear_z - ph2, rear_z + ph2, coll))

# front, protruding inward (-Y is outward here, so bodies go +Y from in_y1)
for nm, x, d, dep in (
    ("ROTARY", P["rotary_x"], P["rotary_body_dia"], P["rotary_body_depth"]),
    ("TOGGLE", P["toggle_x"], P["toggle_body_dia"], P["toggle_body_depth"]),
    ("POT",    P["pot_x"],    P["pot_body_dia"],   P["pot_body_depth"]),
):
    panels.append(cyl("PANEL_" + nm, x, in_y1 + dep / 2, shaft_z, d, dep, coll, axis="Y", seg=24))

# knobs, outside the front panel
for nm, x, d in (("ROTARY", P["rotary_x"], 25.0), ("POT", P["pot_x"], 20.0)):
    panels.append(cyl("KNOB_" + nm, x, out_y1 - 8.0, shaft_z, d, 16.0, coll, axis="Y", seg=32))

for ob in panels:
    paint(ob, M_PANEL)

# ===========================================================================
# REPORT
# ===========================================================================

# Booleans can leave objects hidden, and a hidden object cannot be selected,
# which silently exports an empty STL. Force everything visible.
for ob in coll.objects:
    ob.hide_render = False
    try:
        ob.hide_set(False)
    except RuntimeError:
        pass

result = {
    "external_mm": [round(ext_w, 2), round(ext_l, 2), round(ext_h, 2)],
    "internal_h": round(internal_h, 2),
    "height_driver": height_driver,
    "h_from_board": round(h_from_board, 2),
    "h_from_loom": round(h_from_loom, 2),
    "h_from_rotary": round(h_from_rotary, 2),
    "front_gap": round(front_gap, 2),
    "shaft_z": round(shaft_z, 2),
    "board_z": [round(board_z0, 2), round(board_z1, 2)],
    "u2_top": round(board_z1 + P["tallest_part"], 2),
    "u2_headroom": round(internal_h - (board_z1 + P["tallest_part"]), 2),
    "loom_top": round(board_z1 + P["loom_above_board"], 2),
    "loom_headroom": round(internal_h - (board_z1 + P["loom_above_board"]), 2),
    "rotary_body_z": [round(shaft_z - P["rotary_body_dia"] / 2, 2),
                      round(shaft_z + P["rotary_body_dia"] / 2, 2)],
    "led_to_lid": round(internal_h - (board_z1 + 6.0), 2),
    "objects": len(coll.objects),
}
print(result)
