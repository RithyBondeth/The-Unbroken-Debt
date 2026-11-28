"""Rebuild the Neak Ta shrine under the banyan (tools/areas/neakta_shrine.py)
inside the existing village, without regenerating anything else.

    blender -b --factory-startup --python-exit-code 1 art-source/blender/ep1/ep1_area_village.blend \\
        -P tools/areas/rebuild-shrine.py
    npm run export -- ep1/ep1_area_village && npm run assets -- ep1/ep1_area_village.glb

Re-runnable: what it builds lives in the `neakta_shrine` collection and is
replaced each run. The gameplay nodes keep their names and places:
`neakta_stone_watch` (the watcher, Apparitions.ts), `marker_neakta`,
`marker_flies`, `light_flame_shrine` (now at the burning candle's wick) and the
collider `col_neakta_shrine`. The banyan's cloth bands, the verge offerings and
the small spirit house beside the shrine are left as they are.
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
from kit import collider, empty  # noqa: E402
from house_rooms import _complete_gltf_group  # noqa: E402
import neakta_shrine  # noqa: E402

X, Y, FACING = -3.9, -34.9, math.pi / 2
COLL = "neakta_shrine"
OLD = ("neakta_shrine", "neakta_stone_watch", "col_neakta_shrine", "light_flame_shrine", "marker_neakta",
       "marker_flies")

village = bpy.data.collections["ep1_area_village"]
# The markers stay where gameplay expects them.
kept = {}
for name in ("marker_neakta", "marker_flies"):
    o = bpy.data.objects.get(name)
    if o:
        kept[name] = (o.matrix_world.translation.copy(), dict(o.items()))
coll = bpy.data.collections.get(COLL)
if coll is None:
    coll = bpy.data.collections.new(COLL)
    village.children.link(coll)
for o in list(coll.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for name in OLD:
    o = bpy.data.objects.get(name)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)
for mesh in list(bpy.data.meshes):
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
for curve in list(bpy.data.curves):
    if curve.users == 0:
        bpy.data.curves.remove(curve)
unchanged = {o.name: o.matrix_world.copy() for o in bpy.data.objects}
_complete_gltf_group()
print("Building the Neak Ta shrine", flush=True)
objs, watcher, lit, F = neakta_shrine.build(coll, X, Y, FACING, np.random.default_rng(3409))
for o in list(coll.objects):
    for c in list(o.users_collection):
        if c != coll:
            c.objects.unlink(o)
collider("neakta_shrine", coll, X - .84, X + .84, Y - 1.14, Y + 1.14, 0, 2.42, surface="stone")
empty("light_flame_shrine", coll, (lit[0], lit[1], lit[2] + .012), radius=3.0, intensity=.45)
for name, (at, props) in kept.items():
    empty(name, coll, tuple(at), **{k: v for k, v in props.items() if not k.startswith("_")})
for name in ("marker_neakta", "marker_flies"):
    if name not in kept:
        raise SystemExit(f"Missing gameplay marker {name}")
bpy.context.view_layer.update()


def _verts_in(name, lo, hi, delta):
    """Moves the vertices of one object that lie inside a world box (one loose part)."""
    o = bpy.data.objects.get(name)
    if o is None:
        return
    if o.data.users > 1:
        o.data = o.data.copy()
    local = o.matrix_world.inverted().to_3x3() @ Vector(delta)
    lo, hi = Vector(lo), Vector(hi)
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        if all(lo[i] - 0.004 <= w[i] <= hi[i] + 0.004 for i in range(3)):
            v.co += local


def settle():
    """Nothing floats round the shrine: small loose parts (old rice, a cloth scrap,
    any piece of the new shrine) are set down on what lies beneath them; strays
    with nothing beneath are removed."""
    import re
    import bmesh
    import ground_audit
    ground_audit.REGION = (X - 1.7, Y - 2.3, X + 1.7, Y + 2.3)
    small = re.compile(r"^(ground_offering_\d|spirit_house|neakta_.*)$")
    for _pass in range(2):
        failures, ctx = ground_audit.audit()
        bvh, tri_part, parts = ctx["bvh"], ctx["tri_part"], ctx["parts"]
        for f in failures:
            name, _mat, pts, _tri, _vsel = parts[f["part"]]
            if not small.match(name) or len(pts) > 400:
                continue
            low = pts[pts[:, 2] < pts[:, 2].min() + 0.02]
            gap = math.inf
            for v in low[:12]:
                hit = bvh.ray_cast(Vector((v[0], v[1], v[2] - 0.0005)), Vector((0, 0, -1)), 0.5)
                if hit[0] is not None and tri_part[hit[2]] != f["part"]:
                    gap = min(gap, hit[3])
            lo, hi = pts.min(0), pts.max(0)
            _verts_in(name, lo, hi, (0, 0, -50.0) if gap == math.inf else (0, 0, -(gap + 0.002)))
    for o in bpy.data.objects:
        if o.type == "MESH" and small.match(o.name):
            bm = bmesh.new()
            bm.from_mesh(o.data)
            gone = [v for v in bm.verts if (o.matrix_world @ v.co).z < -20]
            if gone:
                bmesh.ops.delete(bm, geom=gone, context="VERTS")
                bm.to_mesh(o.data)
            bm.free()
    after, _ = ground_audit.audit()
    print(f"[shrine] floating parts left round the shrine: {len(after)}", flush=True)
    return after


AUDIT_AS_MODULE = True
left = settle()
for name, matrix in unchanged.items():
    o = bpy.data.objects.get(name)
    assert o is not None and o.matrix_world == matrix, f"Unrelated art moved or vanished: {name}"
for name in OLD[1:]:
    assert bpy.data.objects.get(name), f"Missing gameplay node: {name}"
assert abs(watcher["front"]) < .001
foot = watcher.matrix_world.translation
print(f"Watcher at {tuple(round(v, 3) for v in foot)}, wick {tuple(round(v, 3) for v in lit)}", flush=True)
faces = sum(len(o.data.polygons) for o in coll.objects if o.type == "MESH")
print(f"{COLL}: {len(coll.objects)} objects, {faces} faces", flush=True)
# New maps are saved under art-source/textures/ep1; keep every path relative to the file.
bpy.ops.file.make_paths_relative()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("Neak Ta shrine rebuilt; unrelated art and gameplay nodes verified.", flush=True)
if left:
    print("[shrine] still floating:", [(f["object"], f["gap"]) for f in left], flush=True)
