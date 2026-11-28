"""Prepares the Sketchfab scans used in the Ep1 studio's hall (CC BY 4.0, credited in
docs/production/asset-tracker.csv) as compact library models in art-source/library/scans/.

Each download (a .glb, or a .gltf with its files) is stood upright on its base centre at
the origin, scaled to the real object's size, reduced to a face cap with its textures
downscaled, and written as scans/<key>.glb with the credit in asset.copyright and in the
root node's extras. tools/areas/ep1_area_studio.py then places it with `scan(key, ...)`.

Downloads need a Sketchfab account, so the sources are not fetched by a script; the
prepared GLBs are kept in LFS instead.

    blender -b --factory-startup -P tools/areas/studio_scans.py -- KEY PATH [KEY PATH ...]
"""

import math
import os
import sys

import bpy
import mathutils

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "art-source", "library", "scans")

# key: Sketchfab title, author, model URL, real height in metres (or length along the
# longest side when `fit` is "length"), face cap, texture size, extra rotation (degrees
# about X, Y, Z) applied after import to stand it the right way up.
SPEC = {
    "water_jar": dict(title="Jar with stamps, Ganedalam", author="Maritime Asia Heritage Survey",
                      url="https://sketchfab.com/3d-models/1cc807bd680c4d8e8ae72fb7c6f39f83", size=0.78, faces=30000, tex=2048),
    "clay_stove": dict(title="Tunisian Kanoun - Traditional Clay Stove", author="meddboubakerr",
                       url="https://sketchfab.com/3d-models/b81f528045394110afb39ca26bcd815a", size=0.3, faces=12000, tex=1024),
    "rice_sack": dict(title="Old burlap bag photo scan", author="teilorandersen",
                      url="https://sketchfab.com/3d-models/d52b9c947f994d528e872f71a1cabba1", size=0.52, faces=8000, tex=1024),
    "straw_mat": dict(title="Straw_Mat", author="KHS_Asset",
                      url="https://sketchfab.com/3d-models/a345f9daa7664fbabc6331ed8ec3c2e0", size=0.95, fit="length", faces=4000, tex=1024),
    "winnowing_tray": dict(title="Traditional bamboo basket", author="leeyeji1027",
                           url="https://sketchfab.com/3d-models/721187e24dc94f53957de1016855577e", size=0.62, fit="length", faces=8000, tex=1024),
    "basket_round": dict(title="Bamboo_Basket", author="KHS_Asset",
                         url="https://sketchfab.com/3d-models/6c7e1244d46c457fb6f3d6194663073b", size=0.38, fit="length", faces=3000, tex=512),
    "basket_deep": dict(title="Basket", author="KHS_Asset",
                        url="https://sketchfab.com/3d-models/f097383b0dc949759f7a544b49a4729b", size=0.34, fit="length", faces=3000, tex=512),
    "broom": dict(title="Broom", author="KHS_Asset",
                  url="https://sketchfab.com/3d-models/1043e0664c404dc8b57e6ccc62491567", size=0.7, fit="length", faces=3000, tex=512),
    "kettle": dict(title="Old Kettle with Lid", author="Odin.Branigan",
                   url="https://sketchfab.com/3d-models/5c109d4cc69946b4add01824b9e8aed8", size=0.24, faces=4000, tex=1024),
    "jar_handles": dict(title="Jar", author="KHS_Asset",
                        url="https://sketchfab.com/3d-models/d00a1cb787314ffb9c5bd9c830e67b94", size=0.42, faces=3000, tex=512),
    "jar_plain": dict(title="Jar", author="KHS_Asset",
                      url="https://sketchfab.com/3d-models/9908305b49f74af2a32bad7240fe1021", size=0.34, faces=3000, tex=1024),
    "cooking_pot": dict(title="clay cooking pot", author="josemtavares",
                        url="https://sketchfab.com/3d-models/38c0785f24104cc0a1ffb91509ed4d12", size=0.42, faces=6000, tex=1024),
}


def prepare(key, path):
    spec = SPEC[key]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    # Bake every transform into the meshes and join them under one object.
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    for o in [o for o in bpy.data.objects if o != obj]:
        bpy.data.objects.remove(o)
    rx, ry, rz = spec.get("rot", (0, 0, 0))
    obj.data.transform(mathutils.Euler((math.radians(rx), math.radians(ry), math.radians(rz))).to_matrix().to_4x4())
    # Stand it on its base centre at the origin, at life size.
    co = [v.co for v in obj.data.vertices]
    lo = mathutils.Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co)))
    hi = mathutils.Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
    dims = hi - lo
    s = spec["size"] / (max(dims) if spec.get("fit") == "length" else dims.z)
    obj.data.transform(mathutils.Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    obj.data.transform(mathutils.Matrix.Scale(s, 4))
    obj.name = obj.data.name = key
    # Reduce to the face cap.
    faces = len(obj.data.polygons)
    if faces > spec["faces"]:
        mod = obj.modifiers.new("cap", "DECIMATE")
        mod.ratio = spec["faces"] / faces
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    # Downscale textures.
    for img in bpy.data.images:
        if img.size[0] > spec["tex"] or img.size[1] > spec["tex"]:
            k = spec["tex"] / max(img.size)
            img.scale(max(1, round(img.size[0] * k)), max(1, round(img.size[1] * k)))
            img.pack()
    credit = f"{spec['title']} by {spec['author']} ({spec['url']}), CC BY 4.0; scaled and reduced"
    obj["credit"] = credit
    obj["licence"] = "CC BY 4.0"
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, f"{key}.glb")
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_extras=True, export_yup=True, export_apply=True,
                              export_copyright=credit, export_cameras=False, export_lights=False)
    d = obj.dimensions
    print(f"SCAN {key}: {faces} -> {len(obj.data.polygons)} faces, {d.x:.2f} x {d.y:.2f} x {d.z:.2f} m, {os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for key, path in zip(args[::2], args[1::2]):
        prepare(key, path)
