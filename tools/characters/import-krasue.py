"""Prepares the user's Krasue for Episode 1 (November 2026).

The source is the user's own Tripo model (~/Downloads/krasue.glb, November 23): a woman's
head, its long black hair blown out round it, trailing her heart, lungs, liver and the
coils of her gut on a red thread of throat, all one dense surface (about 1.9M triangles)
on a 4K texture atlas (colour, roughness/metal, normals).

    blender -b --factory-startup --python-exit-code 1 -P tools/characters/import-krasue.py -- \\
        ~/Downloads/krasue.glb

Welds the vertices the file splits along its texture seams (left split, decimation frays
every seam: see import-blood-spirit.py), decimates the closed surface to about 120k
triangles with the seams kept, so the original atlas still fits, and halves the textures
to 2K. Writes art-source/library/scans/krasue.glb in the source's own units (about 0.98
tall, the face toward -Y), with the credit in asset.extras. tools/characters/build-krasue.py
rigs it for the game.
"""
import os
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "areas"))
from statue_prep import _credit  # noqa: E402

SRC = os.path.expanduser(sys.argv[sys.argv.index("--") + 1])
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "art-source", "library", "scans", "krasue.glb")
TRIS = 120000
TEXTURE = 2048

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
if len(meshes) > 1:
    bpy.ops.object.join()
body = bpy.context.view_layer.objects.active
body.name = body.data.name = "krasue"

bm = bmesh.new()
bm.from_mesh(body.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bm.to_mesh(body.data)
bm.free()
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.seams_from_islands()
bpy.ops.object.mode_set(mode="OBJECT")
tris = len(body.data.polygons)
mod = body.modifiers.new("decimate", "DECIMATE")
mod.ratio = min(1.0, TRIS / tris)
mod.use_collapse_triangulate = True
bpy.ops.object.modifier_apply(modifier=mod.name)
for p in body.data.polygons:
    p.use_smooth = True
print(f"Decimated {tris} -> {len(body.data.polygons)} triangles", flush=True)

# The atlas at 2K, under the names the asset build knows (colour; normals and the
# roughness/metal map as detail maps).
mat = body.data.materials[0]
mat.name = "M_ep1_krasue"
for n in mat.node_tree.nodes:
    if n.type != "TEX_IMAGE" or not n.image:
        continue
    img = n.image
    kind = "N" if "normal" in img.name else "ORM" if "_rm" in img.name else "BC"
    img.scale(TEXTURE, TEXTURE)
    img.name = f"T_ep1_krasue_{kind}"
    img.file_format = "PNG" if kind == "N" else "JPEG"

os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_yup=True, export_apply=True,
                          use_selection=True, export_cameras=False, export_lights=False,
                          export_image_format="AUTO", export_image_quality=92)
_credit(SRC, OUT, {
    "title": "Krasue (a woman's head trailing her heart, lungs and gut)",
    "author": "The Unbroken Debt (made by the studio with Tripo AI, paid plan)",
    "source": "user-supplied krasue.glb",
    "license": "Studio-owned (Tripo paid plan: commercial use, no attribution required)",
    "adapted": f"seams welded, decimated to {len(body.data.polygons)} triangles, textures {TEXTURE} px",
})
