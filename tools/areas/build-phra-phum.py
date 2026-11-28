"""Build the Episode 1 Preah Phum (spirit house, save point) as a game asset.

    blender -b --factory-startup --python-exit-code 1 -P tools/areas/build-phra-phum.py
    npm run assets -- ep1/phra_phum.glb

Writes the editable source art-source/props/phra-phum/phra-phum.blend and the
raw export art-export/ep1/phra_phum.glb; `npm run assets` compresses it to
public/assets/ep1/phra_phum.glb (KTX2 textures, meshopt). The game
(src/episodes/ep1/act1/PhraPhum.ts) lights the three wicks, marked by the
empties phra_phum_wick_left / _right / _inner. Small plain-coloured offerings
share one palette material, so the whole spirit house stays a few dozen draw calls.
"""
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from kit import ROOT  # noqa: E402

SRC = os.path.join(ROOT, "art-source", "props", "phra-phum")
EXPORT = os.path.join(ROOT, "art-export", "ep1", "phra_phum.glb")


def _is_plain(mat):
    nodes = mat.node_tree.nodes
    return (not any(n.type == "TEX_IMAGE" for n in nodes)
            and getattr(mat, "surface_render_method", "DITHERED") != "BLENDED" and mat.blend_method != "BLEND")


def palette(objs):
    """Fold plain (untextured, opaque) materials into one swatch atlas: each
    swatch carries its colour, roughness and metalness; faces map to its centre."""
    plain = [o for o in objs if _is_plain(o.data.materials[0])]
    if len(plain) < 2:
        return objs
    n, size = 8, 64
    cell = size // n
    bc = np.ones((size, size, 4), np.float32)
    orm = np.ones((size, size, 4), np.float32)
    for k, o in enumerate(plain):
        bsdf = o.data.materials[0].node_tree.nodes["Principled BSDF"]
        col = bsdf.inputs["Base Color"].default_value
        i, j = k % n, k // n
        bc[j * cell:(j + 1) * cell, i * cell:(i + 1) * cell, :3] = col[:3]
        orm[j * cell:(j + 1) * cell, i * cell:(i + 1) * cell, 1] = bsdf.inputs["Roughness"].default_value
        orm[j * cell:(j + 1) * cell, i * cell:(i + 1) * cell, 2] = bsdf.inputs["Metallic"].default_value
        u, v = (i + .5) / n, (j + .5) / n
        for d in o.data.uv_layers.active.data:
            d.uv = (u, v)
    images = []
    for name, px, non_color in (("T_ep1_phra_phum_palette_BC", bc, False), ("T_ep1_phra_phum_palette_ORM", orm, True)):
        img = bpy.data.images.new(name, size, size, alpha=False)
        if non_color:
            img.colorspace_settings.name = "Non-Color"
        img.pixels.foreach_set(px.ravel())
        img.filepath_raw = os.path.join(ROOT, "art-source", "textures", "ep1", name + ".png")
        img.file_format = "PNG"
        img.save()
        images.append(img)
    mat = bpy.data.materials.new("M_phra_phum_offering_palette")
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = images[0]
    t.interpolation = "Closest"
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    t2 = nt.nodes.new("ShaderNodeTexImage")
    t2.image = images[1]
    t2.interpolation = "Closest"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(t2.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    for o in plain:
        o.data.materials[0] = mat
    from khmer import join
    merged = join(plain, "phra_phum_offering_palette")
    return [o for o in objs if o not in plain] + [merged]


def webs_to_mesh(coll, webs):
    """Cobweb sheets, threads (curves) and dust clumps as one mesh per material."""
    deps = bpy.context.evaluated_depsgraph_get()
    meshes = []
    for o in webs:
        if "_dust_" in o.name:
            o.scale *= .45
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    for o in webs:
        mesh = bpy.data.meshes.new_from_object(o.evaluated_get(deps))
        mesh.transform(o.matrix_world)
        new = bpy.data.objects.new(o.name + "_m", mesh)
        coll.objects.link(new)
        if not mesh.materials and o.data.materials:
            mesh.materials.append(o.data.materials[0])
        meshes.append(new)
        bpy.data.objects.remove(o, do_unlink=True)
    from khmer import join
    by_mat = {}
    for o in meshes:
        by_mat.setdefault(o.data.materials[0].name, []).append(o)
    return [join(group, f"phra_phum_cobweb_{'sheet' if ('dusty' in name or 'veil' in name) else 'thread'}") for name, group in by_mat.items()]


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = bpy.data.collections.new("phra_phum")
    bpy.context.scene.collection.children.link(coll)
    import phra_phum
    res = phra_phum.build(coll, np.random.default_rng(1932))
    objs = palette(res["objects"])
    objs += webs_to_mesh(coll, res["webs"])
    for name, w in (("left", res["wicks"][0]), ("right", res["wicks"][1]), ("inner", res["inner_wick"])):
        e = bpy.data.objects.new(f"phra_phum_wick_{name}", None)
        coll.objects.link(e)
        e.location = w
    for o in list(bpy.context.scene.objects):
        if o.name not in coll.objects:
            bpy.data.objects.remove(o, do_unlink=True)
    tris = 0
    meshes = [o for o in coll.objects if o.type == "MESH"]
    for o in meshes:
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
    print(f"PREAH PHUM: {len(meshes)} meshes, {tris} triangles, "
          f"{len({o.data.materials[0].name for o in meshes})} materials", flush=True)
    os.makedirs(SRC, exist_ok=True)
    os.makedirs(os.path.dirname(EXPORT), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SRC, "phra-phum.blend"))
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile()
    bpy.ops.object.select_all(action="DESELECT")
    for o in coll.objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=EXPORT, export_format="GLB", use_selection=True, export_yup=True,
                              export_extras=True, export_cameras=False, export_lights=False, export_apply=True)
    print("Exported", EXPORT, flush=True)


main()
