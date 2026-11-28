"""Prepares the Sketchfab models used by Episode 1's taxi ride (CC BY 4.0, credited in
docs/production/asset-tracker.csv) as compact library models in art-source/library/scans/.

Each download (a .gltf with its files) is stood upright on its base centre at the origin,
scaled to the real object's size, reduced once to a face cap with its textures downscaled,
and written as scans/<key>.glb with the credit in asset.copyright and in each object's
extras. tools/travel/build-taxi.py then places it. Photo scans are not decimated again
there: their fragmented texture layout tears apart when they are.

The car is kept in its parts (one object per material) so build-taxi.py can line the cabin
with photo textures; only what is never seen from the seats (chassis, boot, spare wheel,
number plates) is left out.

Downloads need a Sketchfab account, so the sources are not fetched by a script; the
prepared GLBs are kept in LFS instead.

    blender -b --factory-startup -P tools/travel/taxi_scans.py -- KEY PATH [KEY PATH ...]
"""

import math
import os
import sys

import bpy
import mathutils

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "art-source", "library", "scans")

# key: Sketchfab title, author, model URL, real height in metres (or the longest side
# when `fit` is "length"), face cap, texture size, extra rotation (degrees about X, Y, Z),
# and which imported objects to keep (`keep`) or drop (`drop`), by name prefix.
SPEC = {
    "taxi_rosalie": dict(title="Citroën Rosalie 1933", author="RolloT",
                         url="https://sketchfab.com/3d-models/e1faaf38287b45f79a5af94a790ad343",
                         size=None, faces=None, tex=1024, car=True,
                         drop=("SM_Wheel", "SM_lower_part", "SM_box", "SM_Immatriculation"),
                         # Parts seen close from the seats keep sharper maps; wings and the
                         # body skin are seen only past the bonnet and through the glass.
                         tex_by_material={"M_internal": 2048, "M_door": 2048},
                         ratio_by_object={"Sm_gardeboue": 0.18, "SM_door": 0.55, "SM_external": 0.7}),
    "taxi_stilt_house": dict(title="Stilt house in DenHung (CanTho - VietNam)", author="Wang Sh D",
                             url="https://sketchfab.com/3d-models/73b917a1b8564feaad1583dfe263c40b",
                             size=6.6, faces=8000, tex=2048),
    "taxi_fan_palm": dict(title="Realistic HD Mexican fan palm (8/10)", author="PlantCatalog",
                          url="https://sketchfab.com/3d-models/00bd2ea54eb1405bb056eac3f1e14673",
                          size=14.0, faces=None, tex=1024, join=False,
                          ratio_by_object={"Washingtonia_robusta_HD_V2_Wash trunk": 0.12,
                                           "Washingtonia_robusta_HD_V2_Wash leaf stalk": 0.3,
                                           "Washingtonia_robusta_HD_V2_Wash cut stalk": 0.15,
                                           "Washingtonia_robusta_HD_V2_Wahs crownshaft": 0.3,
                                           "Washingtonia_robusta_HD_V2_Wash leaf": 0.45}),
    "taxi_wood_pole": dict(title="Weathered Wooden Utility Pole Scan", author="CLLFTVTV",
                           url="https://sketchfab.com/3d-models/18d96c13bbcd456f8651090e1b65d8c1",
                           size=2.1, faces=7000, tex=1024),
    "taxi_mud_puddle": dict(title="Forest mud puddle", author="matousekfoto",
                            url="https://sketchfab.com/3d-models/6a92c9c3db254defa8bc31d240ebe1f2",
                            size=3.4, fit="length", faces=12000, tex=1024),
    # Rigged Renderpeople photoscans: the driver's body (his head is the Khmer driver's own)
    # and Sora's seated legs. Kept on their own skeletons; build-taxi.py poses them.
    "taxi_driver_scan": dict(title="Eric Rigged 001 - Rigged 3D Business Man", author="Renderpeople",
                             url="https://sketchfab.com/3d-models/a46bc9f67aaa415bb4f3241eef900e7f",
                             # Seen at arm's length from Sora's seat: the shirt's weave and
                             # folds and the hands' skin keep 4K colour and relief.
                             rigged=True, tex=4096, drop=("Icosphere",)),
    "taxi_sora_scan": dict(title="Carla Rigged 001 - Rigged 3D Business Women", author="Renderpeople",
                           url="https://sketchfab.com/3d-models/acf520f450d14dd799f98a6fede3edf5",
                           rigged=True, tex=4096, drop=("Icosphere",)),
    # The roadside Neak Ta's body: a real full-body photoscan (tools/characters/
    # build-neakta-roadside.py rigs it, dresses it and darkens it to soot-black).
    "neakta_body_scan": dict(title="Johnny 'D' w/ belt", author="LaPresse3D",
                             url="https://sketchfab.com/3d-models/0c374432696c4fd6a1036a5456a57b99",
                             # Not reduced: collapsing this scan tears its texture layout.
                             size=1.74, faces=None, tex=4096),
    "taxi_banana": dict(title="Banana tree", author="Alnazir",
                        url="https://sketchfab.com/3d-models/3b658ecad29f4d9a9606dbf8fea7c9bb",
                        size=4.2, faces=16000, tex=1024),
    "taxi_termite_mound": dict(title="Termite Mound", author="Chaitanya Krishnan",
                               url="https://sketchfab.com/3d-models/1479964b7e2a4190b107a0d2e0bc2cf8",
                               size=1.7, faces=7000, tex=1024, keep=("TexturedMesh_0",), only_first=True),
}


def gltf_import(path):
    # The glTF importer reuses an existing "glTF Material Output" group and expects all of
    # its sockets; make the full one before anything else can make a partial one.
    from io_scene_gltf2.blender.com.material_helpers import create_settings_group, get_gltf_node_name
    if get_gltf_node_name() not in bpy.data.node_groups:
        create_settings_group(get_gltf_node_name())
    bpy.ops.import_scene.gltf(filepath=path)


def decimate(obj, ratio):
    if ratio >= 1:
        return
    mod = obj.modifiers.new("cap", "DECIMATE")
    mod.ratio = max(ratio, 0.01)
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


def bake_transforms(meshes):
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def bounds(objs):
    co = [v.co for o in objs for v in o.data.vertices]
    lo = mathutils.Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co)))
    hi = mathutils.Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
    return lo, hi


def prepare_rigged(key, spec):
    """A rigged scan: centimetres to metres, skeleton kept, textures downscaled, credited."""
    for o in [o for o in bpy.data.objects if any(o.name.startswith(p) for p in spec.get("drop", ()))]:
        bpy.data.objects.remove(o)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    top = max((o.matrix_world @ v.co).z for o in meshes for v in o.data.vertices)
    if top > 10:  # centimetres
        for o in [o for o in bpy.data.objects if o.parent is None]:
            o.scale = [v * .01 for v in o.scale]
            o.location = [v * .01 for v in o.location]
        bpy.context.view_layer.update()
        bpy.ops.object.select_all(action="SELECT")
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for img in bpy.data.images:
        if max(img.size) > spec["tex"]:
            k = spec["tex"] / max(img.size)
            img.scale(max(1, round(img.size[0] * k)), max(1, round(img.size[1] * k)))
            img.pack()
    credit = f"{spec['title']} by {spec['author']} ({spec['url']}), CC BY 4.0; scaled, maps reduced"
    for o in meshes:
        o["credit"] = credit
        o["licence"] = "CC BY 4.0"
    out = os.path.join(OUT, f"{key}.glb")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_extras=True, export_yup=True,
                              export_apply=False, export_skins=True, export_animations=False,
                              export_copyright=credit, export_cameras=False, export_lights=False)
    top = max((o.matrix_world @ v.co).z for o in meshes for v in o.data.vertices)
    print(f"SCAN {key}: rigged, {sum(len(o.data.polygons) for o in meshes)} faces, {top:.2f} m tall, "
          f"{os.path.getsize(out) / 1e6:.1f} MB")


def prepare(key, path):
    spec = SPEC[key]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    gltf_import(path)
    if spec.get("rigged"):
        return prepare_rigged(key, spec)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    drop = [o for o in meshes if any(o.name.startswith(p) for p in spec.get("drop", ()))]
    if spec.get("keep"):
        kept = [o for o in meshes if any(o.name.startswith(p) for p in spec["keep"])]
        if spec.get("only_first"):
            kept = kept[:1]
        drop += [o for o in meshes if o not in kept]
    for o in drop:
        bpy.data.objects.remove(o)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    bake_transforms(meshes)
    for o in [o for o in bpy.data.objects if o.type != "MESH"]:
        bpy.data.objects.remove(o)
    faces_before = sum(len(o.data.polygons) for o in meshes)
    rx, ry, rz = spec.get("rot", (0, 0, 0))
    turn = mathutils.Euler((math.radians(rx), math.radians(ry), math.radians(rz))).to_matrix().to_4x4()
    for o in meshes:
        o.data.transform(turn)
    if not spec.get("car"):
        # Stand it on its base centre at the origin, at life size.
        lo, hi = bounds(meshes)
        dims = hi - lo
        s = spec["size"] / (max(dims) if spec.get("fit") == "length" else dims.z)
        for o in meshes:
            o.data.transform(mathutils.Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
            o.data.transform(mathutils.Matrix.Scale(s, 4))
    if spec.get("join", not spec.get("car")) and len(meshes) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for o in meshes:
            o.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()
        meshes = [bpy.context.view_layer.objects.active]
        meshes[0].name = meshes[0].data.name = key
    # Reduce once, to a face cap or by part.
    for o in meshes:
        ratio = next((r for p, r in spec.get("ratio_by_object", {}).items() if o.name.startswith(p)), 1.0)
        decimate(o, ratio)
    if spec.get("faces"):
        total = sum(len(o.data.polygons) for o in meshes)
        if total > spec["faces"]:
            for o in meshes:
                decimate(o, spec["faces"] / total)
    # Downscale textures (a texture keeps the size its sharpest user needs).
    need = {}
    for o in meshes:
        for slot in o.material_slots:
            m = slot.material
            if not m or not m.node_tree:
                continue
            cap = spec.get("tex_by_material", {}).get(m.name, spec["tex"])
            for nd in m.node_tree.nodes:
                if nd.type == "TEX_IMAGE" and nd.image:
                    need[nd.image] = max(need.get(nd.image, 0), cap)
    for img, cap in need.items():
        if max(img.size) > cap:
            k = cap / max(img.size)
            img.scale(max(1, round(img.size[0] * k)), max(1, round(img.size[1] * k)))
            img.pack()
    credit = f"{spec['title']} by {spec['author']} ({spec['url']}), CC BY 4.0; scaled and reduced"
    for o in meshes:
        o["credit"] = credit
        o["licence"] = "CC BY 4.0"
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, f"{key}.glb")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_extras=True, export_yup=True,
                              export_apply=True, export_copyright=credit, export_cameras=False,
                              export_lights=False, export_image_format="AUTO")
    lo, hi = bounds(meshes)
    d = hi - lo
    faces = sum(len(o.data.polygons) for o in meshes)
    print(f"SCAN {key}: {faces_before} -> {faces} faces in {len(meshes)} objects, "
          f"{d.x:.2f} x {d.y:.2f} x {d.z:.2f} m, {os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for key, path in zip(args[::2], args[1::2]):
        prepare(key, path)
