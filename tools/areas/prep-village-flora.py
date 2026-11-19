"""Prepares the user-supplied plant models for the Episode 1 village (November 19, 2026)
and writes them to art-source/library/scans/ with their credit in asset.extras:

  forest_tree_gn.glb   "Tree GN" by TechArtBGN, CC BY 4.0: the broadleaf giant.
  forest_banyan.glb    "Chinese Banyan (Ficus Microcarpa)" by Valery.Li, CC BY 4.0: the
                       Neak Ta shrine's banyan and the strangler figs of the forest.
  sugar_palm.glb       "Washingtonia Robusta Palm_01" by andre.arq.89, CC BY 4.0: stands
                       in for the sugar palms (thnot) by the paddies.
  bamboo_clump.glb     "Bamboo" by local.yany, CC BY 4.0: the thorny bamboo clumps.
  banana_clump.glb     the user's own Tripo banana clump (no texture or UVs as supplied):
                       unwrapped and painted here from its own shape (see paint_banana).

    blender -b --factory-startup --python-exit-code 1 -P tools/areas/prep-village-flora.py -- \\
        ~/Downloads [key ...]

Each file holds the plant twice: `<key>` (LOD0) and `<key>_lod1` (about a third of the
triangles, for the forest past the walls). Every plant stands with its trunk's foot at the
origin, +Z up in Blender; roots that run below the ground stay below it, so a copy set on
the ground at its origin never floats. Leaf and bark materials are rebuilt as plain
metal/rough with alpha clipping (MASK): blended foliage sorts badly and costs overdraw.
"""
import json
import math
import os
import random
import struct
import sys
import zlib

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DOWNLOADS = os.path.expanduser(ARGS[0] if ARGS else "~/Downloads")
ONLY = set(ARGS[1:])
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "art-source", "library", "scans")

MODELS = {
    "forest_tree_gn": {
        "src": "tree/tree_gn.glb",
        "trunk": ["BarkB"],
        "drop": ["PruneB"],
        "leaves": ["ClusterB", "ClusterB2", "VinesB"],
        # Cold, deep jungle greens (forest-style decision, Oct 31): the scan's leaves are
        # a sunny yellow-green.
        "tint": {"ClusterB": (0.62, 0.74, 0.6), "ClusterB2": (0.6, 0.72, 0.58), "VinesB": (0.7, 0.76, 0.64)},
        # The scan's bark is rust-red in places: greyed toward wet, mossy wood.
        "grey": {"BarkB": 0.5, "CortexB": 0.5},
        "lod2": 0.11,
        "lod1": 0.34,
    },
    "forest_banyan": {
        "src": "tree/banyan_ficus_microcarpa_plant.glb",
        "trunk": ["BanyanTreeBark"],
        "leaves": ["BanyanTreeLeaves_1", "BanyanTreeLeaves_2", "Branches_03", "Branches_04", "Vines_01"],
        "tint": {"BanyanTreeLeaves_1": (0.82, 0.9, 0.82), "BanyanTreeLeaves_2": (0.82, 0.9, 0.82)},
        "scale": 1.2,
        # Its aerial roots reach the ground all round: find the trunk above them.
        "band": (3.0, 5.0),
        "lod1": 0.3,
        "lod2": 0.09,
    },
    "sugar_palm": {
        "src": "palm_plant.glb",
        "trunk": ["Material_49"],
        "height": 14.5,
        "target": 46000,
        "lod1": 0.3,
        "lod2": 0.1,
    },
    "bamboo_clump": {
        "src": "bamboo.glb",
        "trunk": ["Trunks1", "Trunks2", "Trunks3"],
        "leaves": ["Leaves1", "Leaves2"],
        # Twigs and leaves are modelled one by one (1.5 M triangles): thin them out.
        "thin": {"Branches1": (0.05, 0.14), "Leaves1": (0.6, 0.85), "Leaves2": (0.6, 0.85)},
        "tint": {"Leaves1": (0.66, 0.74, 0.56), "Leaves2": (0.66, 0.74, 0.56)},
        "decimate": {"Trunks1": 0.5, "Trunks2": 0.5, "Trunks3": 0.5, "Branches1": 0.12, "Leaves1": 0.3, "Leaves2": 0.3},
        "lod1": 0.26,
        # Decimating bamboo strips its leaves: its far LOD keeps whole culms and sprays
        # instead, about half of them.
        "lod2_thin": 0.45,
    },
    "scarecrow": {
        "src": "smartinius_scarecrow_complete_mesh.glb",
        "height": 2.15,
        "lod1": 1.0,
        "ground": "min",
    },
    "banana_clump": {
        "src": "tree/banana_plant.glb",
        "height": 4.6,
        "target": 30000,
        "lod1": 0.3,
        "lod2": 0.1,
        "paint": True,
    },
}


def tris(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def import_clean(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    bpy.context.view_layer.update()
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    for o in meshes:
        o.data = o.data.copy()  # instanced primitives: each object gets its own data
        o.data.transform(o.matrix_world)
        o.parent = None
        o.matrix_world.identity()
    for o in [o for o in bpy.context.scene.objects if o.type != "MESH"]:
        bpy.data.objects.remove(o)
    for o in meshes:
        # Vertex colours only tint the scan (and the game's batcher drops them).
        while o.data.color_attributes:
            o.data.color_attributes.remove(o.data.color_attributes[0])
    return meshes


def split_by_material(meshes):
    """One object per material, so each can be thinned or decimated on its own."""
    out = {}
    for o in meshes:
        names = [s.material.name if s.material else "none" for s in o.material_slots] or ["none"]
        for i, name in enumerate(names):
            bm = bmesh.new()
            bm.from_mesh(o.data)
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != i], context="FACES")
            if not bm.faces:
                bm.free()
                continue
            me = bpy.data.meshes.new(f"{name}_part")
            bm.to_mesh(me)
            bm.free()
            me.materials.clear()
            me.materials.append(bpy.data.materials.get(name))
            for p in me.polygons:
                p.material_index = 0
            part = bpy.data.objects.new(f"{name}_part", me)
            bpy.context.scene.collection.objects.link(part)
            out.setdefault(name, []).append(part)
    for o in meshes:
        bpy.data.objects.remove(o)
    return {k: join(v, f"{k}_part") for k, v in out.items()}


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    obj.data.name = name
    return obj


def thin(obj, keep, small_keep, rng):
    """Keeps a random share of the mesh's loose pieces (leaves, twigs): `keep` of the
    small ones and `small_keep` of the large ones (by size)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    seen = set()
    islands = []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, island = [f], []
        seen.add(f.index)
        while stack:
            g = stack.pop()
            island.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        islands.append(island)
    sizes = []
    for island in islands:
        co = [v.co for f in island for v in f.verts]
        lo = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co)))
        hi = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
        sizes.append((hi - lo).length)
    cut = float(np.percentile(sizes, 80)) if sizes else 0
    doomed = []
    for island, size in zip(islands, sizes):
        share = small_keep if size >= cut else keep
        if rng.random() > share:
            doomed.extend(island)
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bm.to_mesh(obj.data)
    bm.free()
    print(f"  thinned {obj.name}: {len(islands)} pieces -> {tris(obj)} triangles", flush=True)


def decimate(obj, ratio):
    if ratio >= 0.999:
        return
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("decimate", "DECIMATE")
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)


def trunk_centre(parts, trunk, band):
    """The trunk's centre where it stands clear of roots: the densest column of trunk
    vertices in a band of heights."""
    co = np.array([v.co[:] for o in parts if o.data.materials[0] and o.data.materials[0].name in trunk
                   for v in o.data.vertices])
    z0 = float(np.percentile(co[:, 2], 1))
    pts = co[(co[:, 2] > z0 + band[0]) & (co[:, 2] < z0 + band[1])][:, :2]
    cell = 0.5
    keys = np.floor(pts / cell).astype(int)
    uniq, counts = np.unique(keys, axis=0, return_counts=True)
    best = (uniq[np.argmax(counts)] + 0.5) * cell
    near = pts[np.hypot(pts[:, 0] - best[0], pts[:, 1] - best[1]) < 1.4]
    return float(np.median(near[:, 0])), float(np.median(near[:, 1]))


def grey_image(image, amount):
    """Pulls an image toward its own luminance and a little darker, in place."""
    px = np.array(image.pixels[:], dtype=np.float32).reshape(-1, 4)
    lum = px[:, :3] @ np.array([0.3, 0.59, 0.11], dtype=np.float32)
    px[:, :3] = (px[:, :3] * (1 - amount) + lum[:, None] * amount) * 0.86
    image.pixels.foreach_set(px.ravel())
    image.pack()


def foot(parts, trunk):
    """The trunk's foot: centre of the trunk material's vertices just above its lowest
    ring (roots that spread or sink are ignored), and the ground height there."""
    co = np.array([v.co[:] for o in parts if o.data.materials[0] and o.data.materials[0].name in trunk
                   for v in o.data.vertices]) if trunk else None
    if co is None or not len(co):
        co = np.array([v.co[:] for o in parts for v in o.data.vertices])
    z0 = float(np.percentile(co[:, 2], 1))
    ring = co[(co[:, 2] > z0 + 0.6) & (co[:, 2] < z0 + 1.6)]
    if len(ring) < 8:
        ring = co[co[:, 2] < z0 + 2.5]
    cx, cy = float(np.median(ring[:, 0])), float(np.median(ring[:, 1]))
    # The ground: the lowest point within a trunk's width of that centre, not a root tip.
    near = co[np.hypot(co[:, 0] - cx, co[:, 1] - cy) < 0.9]
    gz = float(np.percentile(near[:, 2], 5)) if len(near) > 20 else z0
    return cx, cy, max(gz, z0)


def rebuild_material(mat, tint=None, leaf=False):
    """Base colour (× tint), alpha clipped at 0.5, normal map, flat roughness."""
    nt = mat.node_tree
    images = {}
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")

    def source(socket):
        if not socket.is_linked:
            return None
        node = socket.links[0].from_node
        while node.type != "TEX_IMAGE":
            linked = [i for i in node.inputs if i.is_linked]
            if not linked:
                return None
            # Mix nodes: the image is on input A (the colour), not the vertex colour.
            linked = [i for i in linked if i.links[0].from_node.type in ("TEX_IMAGE", "MIX", "MATH", "SEPARATE_COLOR")] or linked
            node = linked[0].links[0].from_node
        return node.image

    images["color"] = source(bsdf.inputs["Base Color"])
    images["alpha"] = source(bsdf.inputs["Alpha"])
    nrm = bsdf.inputs["Normal"]
    images["normal"] = None
    if nrm.is_linked and nrm.links[0].from_node.type == "NORMAL_MAP":
        images["normal"] = source(nrm.links[0].from_node.inputs["Color"])
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = 0.78 if leaf else 0.9
    bsdf.inputs["Specular IOR Level"].default_value = 0.35 if leaf else 0.25
    if images["color"]:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = images["color"]
        if tint:
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs["Factor"].default_value = 1.0
            nt.links.new(tex.outputs["Color"], mix.inputs["A"])
            mix.inputs["B"].default_value = (*tint, 1.0)
            nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
        else:
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        alpha_tex = tex
        if images["alpha"] and images["alpha"] != images["color"]:
            alpha_tex = nt.nodes.new("ShaderNodeTexImage")
            alpha_tex.image = images["alpha"]
            alpha_tex.image.colorspace_settings.name = "Non-Color"
        if images["alpha"] or leaf:
            # The pattern Blender's glTF exporter reads as alphaMode MASK, cutoff 0.5.
            less = nt.nodes.new("ShaderNodeMath")
            less.operation = "LESS_THAN"
            less.inputs[1].default_value = 0.5
            sub = nt.nodes.new("ShaderNodeMath")
            sub.operation = "SUBTRACT"
            sub.inputs[0].default_value = 1.0
            nt.links.new(alpha_tex.outputs["Alpha"], less.inputs[0])
            nt.links.new(less.outputs["Value"], sub.inputs[1])
            nt.links.new(sub.outputs["Value"], bsdf.inputs["Alpha"])
    if images["normal"]:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = images["normal"]
        tex.image.colorspace_settings.name = "Non-Color"
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(tex.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    mat.surface_render_method = "DITHERED"
    mat.use_backface_culling = False
    for image in images.values():
        if image and max(image.size) > 2048:
            k = 2048 / max(image.size)
            image.scale(int(image.size[0] * k), int(image.size[1] * k))


def paint_banana(obj, rng):
    """The Tripo clump came as bare geometry. Paints it from its own shape: each leaf
    (piece) gets a living green, a sun-scorched one with brown margins or the papery
    tan of a dead leaf hanging down the stem; stems are the yellow-green of a banana's
    pseudostem, darker and streaked at the foot. The colours go into a face-corner
    attribute over a fresh unwrap, and Cycles bakes them, with fine lateral veins and
    mottling, into a 2K texture."""
    me = obj.data
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(50), island_margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")

    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    zs = np.array([v.co.z for v in bm.verts])
    z0, height = float(zs.min()), float(np.ptp(zs))
    # Tripo fuses leaves to their stems, so pieces are found by a flood that stops
    # at sharp folds (leaf to stem), not by connectivity.
    seen = np.full(len(bm.faces), -1, dtype=np.int32)
    pieces = []
    for f in bm.faces:
        if seen[f.index] >= 0:
            continue
        k = len(pieces)
        stack, piece = [f], []
        seen[f.index] = k
        while stack:
            g = stack.pop()
            piece.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if seen[h.index] < 0 and g.normal.angle(h.normal, 0) < math.radians(40):
                        seen[h.index] = k
                        stack.append(h)
        pieces.append(piece)
    colours = np.zeros((len(bm.faces), 3), dtype=np.float32)
    counts = {}
    for piece in pieces:
        area = sum(f.calc_area() for f in piece) or 1e-9
        centre = sum((f.calc_center_median() * f.calc_area() for f in piece), Vector()) / area
        zc = (centre.z - z0) / height
        nz = sum(abs(f.normal.z) * f.calc_area() for f in piece) / area
        co = np.array([v.co[:] for f in piece for v in f.verts])
        ext = np.ptp(co, axis=0)
        u = rng.random()
        if ext[2] > 2.5 * max(ext[0], ext[1], 1e-6) and nz < 0.3:
            kind = "stem"
        elif zc < 0.5 and nz < 0.5 and u < 0.75:
            kind = "dead"          # old leaves hanging down the pseudostem
        elif u < 0.2:
            kind = "scorched"
        else:
            kind = "green"
        counts[kind] = counts.get(kind, 0) + 1
        base = np.array({
            "stem": (0.30, 0.34, 0.075),
            "dead": (0.34, 0.25, 0.14),
            "scorched": (0.13, 0.19, 0.045),
            "green": (0.055, 0.13, 0.03),
        }[kind]) * (0.78 + 0.44 * rng.random())
        for f in piece:
            c = base.copy()
            fz = (f.calc_center_median().z - z0) / height
            if kind == "stem" and fz < 0.15:
                c *= np.array((0.55, 0.45, 0.4))
            elif kind == "scorched" and (f.calc_center_median() - centre).length > 0.55 * float(np.max(ext)) * 0.5:
                c = np.array((0.29, 0.19, 0.075)) * (0.8 + 0.4 * rng.random())   # dry margin
            elif kind == "green" and rng.random() < 0.05:
                c = np.array((0.2, 0.15, 0.06))       # torn, dried strips
            elif kind == "dead" and rng.random() < 0.2:
                c = np.array((0.12, 0.085, 0.05))     # dark streaks of rot
            colours[f.index] = c * (0.88 + 0.24 * rng.random())
    bm.free()
    attr = me.color_attributes.new("paint", "FLOAT_COLOR", "CORNER")
    loop_faces = np.zeros(len(me.loops), dtype=np.int32)
    for p in me.polygons:
        loop_faces[p.loop_start:p.loop_start + p.loop_total] = p.index
    rgba = np.concatenate([colours[loop_faces], np.ones((len(me.loops), 1), np.float32)], axis=1)
    attr.data.foreach_set("color", rgba.ravel())

    image = bpy.data.images.new("T_banana_clump_BC", 2048, 2048, alpha=False)
    mat = bpy.data.materials.new("M_banana_clump")
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    paint = nt.nodes.new("ShaderNodeVertexColor")
    paint.layer_name = "paint"
    uvn = nt.nodes.new("ShaderNodeUVMap")
    wave = nt.nodes.new("ShaderNodeTexWave")          # lateral veins
    wave.wave_type = "BANDS"
    wave.inputs["Scale"].default_value = 260
    wave.inputs["Distortion"].default_value = 3
    wave.inputs["Detail"].default_value = 2
    noise = nt.nodes.new("ShaderNodeTexNoise")        # mottling
    noise.inputs["Scale"].default_value = 90
    noise.inputs["Detail"].default_value = 6
    ramp = nt.nodes.new("ShaderNodeMath")
    ramp.operation = "MULTIPLY_ADD"
    ramp.inputs[1].default_value = 0.14
    ramp.inputs[2].default_value = 0.88
    ramp2 = nt.nodes.new("ShaderNodeMath")
    ramp2.operation = "MULTIPLY_ADD"
    ramp2.inputs[1].default_value = 0.3
    ramp2.inputs[2].default_value = 0.82
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    mul2 = nt.nodes.new("ShaderNodeMix")
    mul2.data_type = "RGBA"
    mul2.blend_type = "MULTIPLY"
    mul2.inputs["Factor"].default_value = 1.0
    nt.links.new(uvn.outputs["UV"], wave.inputs["Vector"])
    nt.links.new(uvn.outputs["UV"], noise.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs[0])
    nt.links.new(noise.outputs["Fac"], ramp2.inputs[0])
    nt.links.new(paint.outputs["Color"], mul.inputs["A"])
    nt.links.new(ramp.outputs["Value"], mul.inputs["B"])
    nt.links.new(mul.outputs["Result"], mul2.inputs["A"])
    nt.links.new(ramp2.outputs["Value"], mul2.inputs["B"])
    nt.links.new(mul2.outputs["Result"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    nt.nodes.active = tex
    me.materials.clear()
    me.materials.append(mat)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 4
    scene.render.bake.margin = 6
    bpy.ops.object.bake(type="EMIT")
    image.pack()
    # The game material: the baked colour, no attribute.
    for n in list(nt.nodes):
        if n not in (out, tex):
            nt.nodes.remove(n)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = 0.6
    bsdf.inputs["Specular IOR Level"].default_value = 0.4
    mat.use_backface_culling = False
    me.color_attributes.remove(attr)
    print(f"  painted banana: {len(pieces)} pieces {counts}", flush=True)


def write(key, lods, extras):
    lod0, lod1 = lods[0], lods[1]
    bpy.ops.object.select_all(action="DESELECT")
    for o in lods:
        o.select_set(True)
    path = os.path.join(OUT, f"{key}.glb")
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=True, export_cameras=False, export_lights=False,
                              export_image_format="AUTO")
    with open(path, "rb") as f:
        glb = bytearray(f.read())
    n = struct.unpack("<I", glb[12:16])[0]
    doc = json.loads(glb[20:20 + n])
    doc["asset"]["extras"] = extras
    text = json.dumps(doc, separators=(",", ":")).encode()
    text += b" " * ((4 - len(text) % 4) % 4)
    out = bytearray(glb[:12]) + struct.pack("<I", len(text)) + b"JSON" + text + glb[20 + n:]
    out[8:12] = struct.pack("<I", len(out))
    with open(path, "wb") as f:
        f.write(out)
    print(f"Wrote {path}: " + ", ".join(f"LOD{i} {tris(o)}" for i, o in enumerate(lods)) + " triangles", flush=True)


def source_extras(path):
    with open(path, "rb") as f:
        data = f.read(1 << 20)
    n = struct.unpack("<I", data[12:16])[0]
    if 20 + n > len(data):
        with open(path, "rb") as f:
            data = f.read(20 + n)
    return json.loads(data[20:20 + n])["asset"].get("extras", {})


def prepare(key, spec):
    src = os.path.join(DOWNLOADS, spec["src"])
    print(f"== {key} from {src}", flush=True)
    rng = random.Random(zlib.crc32(key.encode()))
    meshes = import_clean(src)
    parts = split_by_material(meshes)
    for name in spec.get("drop", []):
        if name in parts:
            bpy.data.objects.remove(parts.pop(name))
    for name, (keep, big) in spec.get("thin", {}).items():
        if name in parts:
            thin(parts[name], keep, big, rng)
    for name, ratio in spec.get("decimate", {}).items():
        if name in parts:
            decimate(parts[name], ratio)
    for name, obj in parts.items():
        mat = obj.data.materials[0]
        if mat and mat.node_tree:
            rebuild_material(mat, spec.get("tint", {}).get(name), name in spec.get("leaves", []))
    objs = list(parts.values())
    for name, amount in spec.get("grey", {}).items():
        mat = parts[name].data.materials[0] if name in parts else None
        tex = next((n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE"), None) if mat else None
        if tex and tex.image and not tex.image.get("greyed"):
            grey_image(tex.image, amount)
            tex.image["greyed"] = True
    cx, cy, gz = foot(objs, spec.get("trunk"))
    if spec.get("band"):
        cx, cy = trunk_centre(objs, spec["trunk"], spec["band"])
    if not spec.get("trunk") or spec.get("ground") == "min":
        # A clump with no single trunk (the bananas): its pseudostems stand on its base.
        gz = min(v.co.z for o in objs for v in o.data.vertices)
        co = np.array([v.co[:] for o in objs for v in o.data.vertices])
        # Stood on its own base: the centre of its lowest fifth (a stake, the stems).
        low = co[co[:, 2] < gz + 0.2 * float(np.ptp(co[:, 2]))]
        cx, cy = float(np.median(low[:, 0])), float(np.median(low[:, 1]))
    zmax = max((v.co.z for o in objs for v in o.data.vertices))
    k = spec.get("scale", 1.0)
    if spec.get("height"):
        k = spec["height"] / (zmax - gz)
    for o in objs:
        for v in o.data.vertices:
            v.co.x = (v.co.x - cx) * k
            v.co.y = (v.co.y - cy) * k
            v.co.z = (v.co.z - gz) * k
        o.data.update()
    lod0 = join(objs, key)
    if spec.get("target"):
        decimate(lod0, spec["target"] / max(1, tris(lod0)))
    if spec.get("paint"):
        paint_banana(lod0, rng)
    lod1 = lod0.copy()
    lod1.data = lod0.data.copy()
    lod1.name = lod1.data.name = f"{key}_lod1"
    bpy.context.scene.collection.objects.link(lod1)
    decimate(lod1, spec["lod1"])
    lods = [lod0, lod1]
    if spec.get("lod2_thin"):
        lod2 = lod1.copy()
        lod2.data = lod1.data.copy()
        lod2.name = lod2.data.name = f"{key}_lod2"
        bpy.context.scene.collection.objects.link(lod2)
        thin(lod2, spec["lod2_thin"], spec["lod2_thin"], rng)
        lods.append(lod2)
    elif spec.get("lod2"):
        # The forest past the walls: a few thousand triangles, seen only through mist.
        lod2 = lod0.copy()
        lod2.data = lod0.data.copy()
        lod2.name = lod2.data.name = f"{key}_lod2"
        bpy.context.scene.collection.objects.link(lod2)
        decimate(lod2, spec["lod2"])
        lods.append(lod2)
    extras = source_extras(src) if not spec.get("paint") else {
        "author": "the user (Tripo)", "license": "project-owned", "title": "Banana clump"}
    co = np.array([v.co[:] for v in lod0.data.vertices])
    extras["adapted"] = (f"materials rebuilt (alpha clip), trunk foot at the origin, "
                         f"{float(co[:, 2].max()):.1f} m tall, {tris(lod0)} triangles (LOD1 {tris(lod1)})")
    write(key, lods, extras)


for key, spec in MODELS.items():
    if ONLY and key not in ONLY:
        continue
    prepare(key, spec)
