"""Prepares the user-supplied shrouded corpse (corpse.glb) as an environmental horror prop.

Usage:
    blender -b --factory-startup --python-exit-code 1 -P tools/characters/import-shrouded-corpse.py -- \
        /Users/bondeth/Downloads/models/corpse.glb
    npm run assets -- ep1/shrouded_corpse

Normalizes scale (~1.85 m long lying flat), rests its underside cleanly on Z=0, centers
at origin, dampens shroud material for rain sheen, and exports
art-export/ep1/shrouded_corpse.glb.
"""
import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.expanduser(sys.argv[sys.argv.index("--") + 1])
OUT = os.path.join(ROOT, "art-export", "ep1", "shrouded_corpse.glb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes:
    raise RuntimeError("No meshes found in corpse GLB")

bpy.context.view_layer.update()
for o in meshes:
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

if len(meshes) > 1:
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()

obj = bpy.context.view_layer.objects.active
obj.name = "shrouded_corpse"
obj.data.name = "shrouded_corpse"

pts = [Vector(c) for c in obj.bound_box]
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
size = mx - mn
length = max(size.x, size.y, 0.1)
scale = 1.85 / length
cx = (mn.x + mx.x) * 0.5
cy = (mn.y + mx.y) * 0.5
obj.data.transform(Matrix.Scale(scale, 4) @ Matrix.Translation((-cx, -cy, -mn.z)))

for mat in obj.data.materials:
    if not mat or not mat.use_nodes:
        continue
    mat.name = "M_shrouded_corpse"
    for node in mat.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            if not node.inputs["Roughness"].is_linked:
                node.inputs["Roughness"].default_value = 0.68

for img in bpy.data.images:
    w, h = img.size
    if max(w, h) > 1024:
        s = 1024 / max(w, h)
        img.scale(int(w * s), int(h * s))
    img.pack()

tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
print(f"[shrouded_corpse] {tris:,} tris, exporting {OUT}")

bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format="GLB",
    export_apply=True,
    export_texcoords=True,
    export_normals=True,
    export_materials="EXPORT",
    export_image_format="JPEG",
    export_jpeg_quality=88,
)
