"""Verify exported enclosure meshes are closed, manifold solids."""

import os

import bmesh
import bpy


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def verify(path):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.wm.stl_import(filepath=path)
    obj = bpy.context.object
    mesh = obj.data
    mesh.validate(verbose=True)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    boundary = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
    non_manifold = sum(1 for edge in bm.edges if not edge.is_manifold)
    volume = abs(bm.calc_volume(signed=True))
    dims = tuple(round(v, 3) for v in obj.dimensions)
    print(f"VERIFY {os.path.basename(path)} dims_mm={dims} boundary_edges={boundary} non_manifold_edges={non_manifold} volume_mm3={volume:.3f}")
    bm.free()
    if boundary or non_manifold or volume <= 0:
        raise RuntimeError(f"Mesh verification failed: {path}")


for filename in ("vinyl-adc-base.stl", "vinyl-adc-lid.stl"):
    verify(os.path.join(ROOT, "enclosure", filename))
