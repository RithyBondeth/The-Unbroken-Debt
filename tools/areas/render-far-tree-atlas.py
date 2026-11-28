"""Renders Episode 1's far-forest atlas from the village's own scanned plants
(November 19, 2026): the cards ForestBorder.ts stands up past the modelled forest,
so the distant tree line is the same trees as the near one, not painted shapes.

    blender -b --factory-startup --python-exit-code 1 -P tools/areas/render-far-tree-atlas.py

Writes art-source/textures/ep1/T_ep1_far_trees_BC.png: 4 x 2 cells of 512 px, each a
plant standing on the cell's bottom edge, seen side-on (orthographic), its albedo with
its own ambient occlusion baked in and alpha around it; the game lights and fogs it.
Cells (the ForestBorder Card.variant numbers): 0-2 the broadleaf giant from three
sides, 3 the strangler fig, 4 sugar palm, 5 banana clump (no bamboo, Nov 19), 6 the fig from another side,
7 a second sugar palm (no leafless trees: the user, Nov 19).
"""
import math
import os

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCANS = os.path.join(ROOT, "art-source", "library", "scans")
OUT = os.path.join(ROOT, "art-source", "textures", "ep1", "T_ep1_far_trees_BC.png")
CELL = 512
CELLS = [
    ("forest_tree_gn", 0, False), ("forest_tree_gn", 120, False), ("forest_tree_gn", 240, False),
    ("forest_banyan", 30, False), ("sugar_palm", 0, False), ("banana_clump", 0, False),
    ("forest_banyan", 150, False), ("sugar_palm", 90, False),
]


def flat(mat):
    """Albedo x AO as emission, alpha kept: what the card holds."""
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
    if not bsdf or not out:
        return
    colour = bsdf.inputs["Base Color"]
    alpha = bsdf.inputs["Alpha"]
    emit = nt.nodes.new("ShaderNodeEmission")
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 1.5
    if colour.is_linked:
        nt.links.new(colour.links[0].from_socket, ao.inputs["Color"])
    else:
        ao.inputs["Color"].default_value = colour.default_value
    nt.links.new(ao.outputs["Color"], emit.inputs["Color"])
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    if alpha.is_linked:
        nt.links.new(alpha.links[0].from_socket, mix.inputs["Fac"])
    else:
        mix.inputs["Fac"].default_value = alpha.default_value
    nt.links.new(clear.outputs[0], mix.inputs[1])
    nt.links.new(emit.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.cycles.transparent_max_bounces = 64
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = scene.render.resolution_y = CELL
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    world = bpy.data.worlds.new("w")
    world.color = (0, 0, 0)
    scene.world = world
    loaded = {}
    for key in {c[0] for c in CELLS}:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(SCANS, f"{key}.glb"))
        for o in set(bpy.data.objects) - before:
            if o.name.endswith("_lod1"):
                bpy.data.objects.remove(o)
            elif o.type == "MESH":
                loaded[key] = o
                o.hide_render = True
    for mat in bpy.data.materials:
        if mat.node_tree:
            flat(mat)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = "ORTHO"
    tiles = []
    for i, (key, yaw, dead) in enumerate(CELLS):
        src = loaded[key]
        obj = src.copy()
        obj.data = src.data.copy() if dead else src.data
        scene.collection.objects.link(obj)
        obj.hide_render = False
        if dead:
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            leafy = [k for k, m in enumerate(obj.data.materials) if m and ("Cluster" in m.name or "Vines" in m.name)]
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in leafy], context="FACES")
            bm.to_mesh(obj.data)
            bm.free()
        obj.rotation_euler = (0, 0, math.radians(yaw))
        bpy.context.view_layer.update()
        pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
        top = max(p.z for p in pts)
        half = max(max(abs(p.x) for p in pts), max(abs(p.y) for p in pts))
        size = max(top, 2 * half) * 1.02
        cam.data.ortho_scale = size
        cam.location = (0, -60, size / 2)
        cam.rotation_euler = (math.pi / 2, 0, 0)
        path = os.path.join(os.path.dirname(OUT), f"_far_cell_{i}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        tiles.append(path)
        bpy.data.objects.remove(obj)
    # Assemble the atlas (4 x 2) from the cells.
    atlas = bpy.data.images.new("T_ep1_far_trees_BC", CELL * 4, CELL * 2, alpha=True)
    import numpy as np
    px = np.zeros((CELL * 2, CELL * 4, 4), dtype=np.float32)
    for i, path in enumerate(tiles):
        img = bpy.data.images.load(path)
        a = np.array(img.pixels[:], dtype=np.float32).reshape(CELL, CELL, 4)
        col, row = i % 4, i // 4
        # Image rows run bottom-up: atlas row 0 is the top row.
        y0 = (1 - row) * CELL
        px[y0:y0 + CELL, col * CELL:(col + 1) * CELL] = a
        bpy.data.images.remove(img)
        os.remove(path)
    atlas.pixels.foreach_set(px.ravel())
    atlas.filepath_raw = OUT
    atlas.file_format = "PNG"
    atlas.save()
    print("Wrote", OUT, flush=True)


main()
