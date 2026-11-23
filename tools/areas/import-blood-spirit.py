"""Prepares the user-supplied Sketchfab ghost for the village (November 2026):
"Horror Ghost Character - Blood Stained Spirit" by adhamasalah, CC BY 4.0
(https://sketchfab.com/3d-models/horror-ghost-character-blood-stained-spirit-ed1a90be19404450935720f7abaae471).

    blender -b --factory-startup --python-exit-code 1 -P tools/areas/import-blood-spirit.py -- \\
        ~/Downloads/horror_ghost_character_-_blood_stained_spirit.glb

Joins its two meshes, welds the vertices the file splits along its texture seams (left
split, the decimation frays every seam into loose shards: her hair and dress broke up
into splinters up close), decimates the closed surface (198k -> about 60k triangles,
the seams kept so the texture stays put), stands it 1.58 m tall with its feet at the
origin facing +X, and writes
art-source/library/scans/blood_stained_spirit.glb with the credit in asset.extras.
"""
import json
import os
import struct
import sys

import bmesh
import bpy

SRC = os.path.expanduser(sys.argv[sys.argv.index("--") + 1])
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "art-source", "library", "scans", "blood_stained_spirit.glb")
HEIGHT = 1.58
TRIS = 60000

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.context.view_layer.update()
for o in meshes:
    o.data.transform(o.matrix_world)
    o.parent = None
    o.matrix_world.identity()
for o in [o for o in bpy.context.scene.objects if o.type != "MESH"]:
    bpy.data.objects.remove(o)
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.join()
body = bpy.context.view_layer.objects.active
body.name = "blood_stained_spirit"
body.data.name = "blood_stained_spirit"
bm = bmesh.new()
bm.from_mesh(body.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bm.to_mesh(body.data)
bm.free()
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.seams_from_islands()
bpy.ops.object.mode_set(mode="OBJECT")
tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
mod = body.modifiers.new("decimate", "DECIMATE")
mod.ratio = min(1.0, TRIS / tris)
mod.use_collapse_triangulate = True
bpy.ops.object.modifier_apply(modifier=mod.name)
for p in body.data.polygons:
    p.use_smooth = True
co = [v.co for v in body.data.vertices]
z0, z1 = min(c.z for c in co), max(c.z for c in co)
cx = sum(c.x for c in co) / len(co)
cy = sum(c.y for c in co) / len(co)
k = HEIGHT / (z1 - z0)
for v in body.data.vertices:
    v.co.x = (v.co.x - cx) * k
    v.co.y = (v.co.y - cy) * k
    v.co.z = (v.co.z - z0) * k
body.data.update()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_yup=True, export_apply=True,
                          export_cameras=False, export_lights=False)

# The credit travels with the file, as the other scans' do.
with open(SRC, "rb") as f:
    data = f.read()
n = struct.unpack("<I", data[12:16])[0]
extras = json.loads(data[20:20 + n])["asset"].get("extras", {})
extras["adapted"] = f"joined, seams welded, decimated to {sum(len(p.vertices) - 2 for p in body.data.polygons)} triangles, scaled to {HEIGHT} m"
with open(OUT, "rb") as f:
    glb = bytearray(f.read())
n = struct.unpack("<I", glb[12:16])[0]
doc = json.loads(glb[20:20 + n])
doc["asset"]["extras"] = extras
text = json.dumps(doc, separators=(",", ":")).encode()
text += b" " * ((4 - len(text) % 4) % 4)
rest = glb[20 + n:]
out = bytearray(glb[:12]) + struct.pack("<I", len(text)) + b"JSON" + text + rest
out[8:12] = struct.pack("<I", len(out))
with open(OUT, "wb") as f:
    f.write(out)
print("Wrote", OUT, extras, flush=True)
