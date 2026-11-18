"""Shared preparation of the user's statue models for the shrines (November 2026).

The statues are the user's own Tripo models (paid plan, so studio-owned): one
dense mesh (about 2M triangles) on a patchwork texture atlas. `prepare()`
keeps the faces a script's `cut` does not drop, closes the small holes the
generator left, decimates to a game budget on fresh UVs and bakes the colour
and normals of the dense original onto them, ageing the colour on the way to
suit the village's shrines: paint faded and flaking to its bare ground, soot
rising from the joss sticks and caught in every crease, grime run down the
upright faces, dust on what faces up. The result is written as a library scan
(feet at the origin, centred, facing -Y) with its credit in asset.extras.

Used by tools/areas/import-neakta-statue.py and import-phra-phum-statue.py;
run inside `blender -b --factory-startup`.
"""
import json
import os
import struct

import bmesh
import bpy
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCANS = os.path.join(ROOT, "art-source", "library", "scans")

# How heavily a statue is aged; every value is a default `prepare(look=...)` can override.
LOOK = dict(
    saturation=.58, value=.6,                       # faded and darkened paint
    bare=((.15, .14, .123), (.27, .255, .225)),     # what shows where the paint flakes off (cement)
    flake=(.6, .67),                                # fine-noise band that flakes
    rise=(.3, .98, .22, .78),                       # soot from z0 to z1 (source units), amount s0 to s1
    crease=.95,                                     # soot caught in creases
    streak=.35,                                     # grime run down upright faces
    dust=.4,
    soot=(.017, .015, .013),
    dust_colour=(.115, .1, .08),
    roughness=.9,
)


def run(op, obj, **kw):
    with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj],
                                   selected_editable_objects=[obj]):
        return op(**kw)


def face_colours(me, img):
    """Texture colour under each face's first corner (linear RGB)."""
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    n = len(me.polygons)
    ls = np.empty(n, np.int64)
    me.polygons.foreach_get("loop_start", ls)
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)[ls]
    xi = np.clip((uv[:, 0] % 1) * w, 0, w - 1).astype(int)
    yi = np.clip((uv[:, 1] % 1) * h, 0, h - 1).astype(int)
    return px[yi, xi, :3]


def largest_island(bm):
    bm.faces.ensure_lookup_table()
    seen, best = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, comp = [f], []
        seen.add(f.index)
        while stack:
            g = stack.pop()
            comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        if len(comp) > len(best):
            best = comp
    keep = set(best)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in keep], context="FACES")


def node(nt, kind, loc, **inputs):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def maprange(nt, src, a, b, c=0., d=1., loc=(0, 0)):
    m = node(nt, "ShaderNodeMapRange", loc)
    m.interpolation_type = "SMOOTHSTEP"
    m.inputs[1].default_value, m.inputs[2].default_value = a, b
    m.inputs[3].default_value, m.inputs[4].default_value = c, d
    nt.links.new(src, m.inputs[0])
    return m.outputs[0]


def mix(nt, a, b, fac, loc=(0, 0)):
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    m.location = loc
    for sock, v in ((m.inputs[6], a), (m.inputs[7], b), (m.inputs[0], fac)):
        if isinstance(v, (tuple, list)):
            sock.default_value = (*v, 1) if len(v) == 3 else v
        elif isinstance(v, float):
            sock.default_value = v
        else:
            nt.links.new(v, sock)
    return m.outputs[2]


def math_(nt, op, a, b, loc=(0, 0)):
    m = nt.nodes.new("ShaderNodeMath")
    m.operation = op
    m.use_clamp = op in ("MULTIPLY", "ADD")
    m.location = loc
    for sock, v in ((m.inputs[0], a), (m.inputs[1], b)):
        if isinstance(v, float):
            sock.default_value = v
        else:
            nt.links.new(v, sock)
    return m.outputs[0]


def aged(nt, base_tex, normal_tex, look, blotch=None):
    """The dense source's shader: an emission of the aged colour (for the colour
    bake) and a Principled with its normal map (for the normal bake).
    `blotch` = (centre, radii, paint colours): a dark, non-red patch inside that
    ellipsoid is painted over like the rest of the figure."""
    L = nt.links
    for n in list(nt.nodes):
        if n not in (base_tex, normal_tex):
            nt.nodes.remove(n)
    out = node(nt, "ShaderNodeOutputMaterial", (1600, 0))
    geo = node(nt, "ShaderNodeNewGeometry", (-900, -300))
    col = base_tex.outputs["Color"]
    lum = node(nt, "ShaderNodeRGBToBW", (-600, 300))
    L.new(col, lum.inputs[0])
    lum = lum.outputs[0]
    n_fine = node(nt, "ShaderNodeTexNoise", (-600, -500), Scale=34., Detail=6., Roughness=.62)
    L.new(geo.outputs["Position"], n_fine.inputs["Vector"])
    n_big = node(nt, "ShaderNodeTexNoise", (-600, -800), Scale=7., Detail=8., Roughness=.6)
    L.new(geo.outputs["Position"], n_big.inputs["Vector"])
    bare = mix(nt, look["bare"][0], look["bare"][1], n_fine.outputs["Fac"], (-100, -400))
    c = col
    paint = None
    if blotch:
        centre, radii, colours = blotch
        rel = node(nt, "ShaderNodeVectorMath", (-700, -100))
        rel.operation = "SUBTRACT"
        L.new(geo.outputs["Position"], rel.inputs[0])
        rel.inputs[1].default_value = centre
        sc = node(nt, "ShaderNodeVectorMath", (-550, -100))
        sc.operation = "DIVIDE"
        L.new(rel.outputs[0], sc.inputs[0])
        sc.inputs[1].default_value = radii
        ln = node(nt, "ShaderNodeVectorMath", (-400, -100))
        ln.operation = "LENGTH"
        L.new(sc.outputs[0], ln.inputs[0])
        inside = maprange(nt, ln.outputs["Value"], 1., .8, loc=(-250, -100))
        dark = maprange(nt, lum, .26, .17, loc=(-250, 100))
        rgb = node(nt, "ShaderNodeSeparateColor", (-600, 500))
        L.new(col, rgb.inputs[0])
        redness = math_(nt, "SUBTRACT", rgb.outputs[0], rgb.outputs[1], (-450, 500))
        not_red = maprange(nt, redness, .1, .04, loc=(-300, 500))
        mask = math_(nt, "MULTIPLY", math_(nt, "MULTIPLY", inside, dark, (-100, 0)), not_red, (0, 100))
        paint = mix(nt, colours[0], colours[1], n_big.outputs["Fac"], (-100, -250))
        c = mix(nt, c, paint, mask, (100, 200))
    # Holes closed by prepare() have no texture of their own.
    patch = node(nt, "ShaderNodeAttribute", (-100, 400))
    patch.attribute_type = "GEOMETRY"
    patch.attribute_name = "fill"
    c = mix(nt, c, paint if paint is not None else bare, patch.outputs["Fac"], (200, 300))
    # Paint flaking off in patches (not on black hair).
    flake = maprange(nt, n_fine.outputs["Fac"], *look["flake"], loc=(-100, -650))
    flake = math_(nt, "MULTIPLY", flake, maprange(nt, lum, .1, .2, loc=(-250, -700)), (50, -650))
    flake = math_(nt, "MULTIPLY", flake, maprange(nt, n_big.outputs["Fac"], .45, .6, loc=(-250, -900)), (200, -650))
    c = mix(nt, c, bare, flake, (300, 200))
    fade = node(nt, "ShaderNodeHueSaturation", (450, 200), Saturation=look["saturation"], Value=look["value"])
    L.new(c, fade.inputs["Color"])
    # Soot: thicker higher up (the smoke rises past the head) and in every crease.
    ao = node(nt, "ShaderNodeAmbientOcclusion", (-250, -1100))
    ao.only_local = True
    ao.samples = 16
    ao.inputs["Distance"].default_value = .05
    crease = maprange(nt, ao.outputs["AO"], 1., .55, loc=(-50, -1100))
    zpos = node(nt, "ShaderNodeSeparateXYZ", (-700, -1300))
    L.new(geo.outputs["Position"], zpos.inputs[0])
    rise = maprange(nt, zpos.outputs["Z"], *look["rise"], loc=(-450, -1300))
    patchy = maprange(nt, n_big.outputs["Fac"], .3, .75, .6, 1.3, loc=(-250, -1300))
    soot = math_(nt, "MULTIPLY", rise, patchy, (0, -1300))
    soot = math_(nt, "ADD", soot, math_(nt, "MULTIPLY", crease, look["crease"], (150, -1150)), (300, -1250))
    # Grime run down in streaks, only on upright faces.
    sv = node(nt, "ShaderNodeVectorMath", (-700, -1450))
    sv.operation = "MULTIPLY"
    L.new(geo.outputs["Position"], sv.inputs[0])
    sv.inputs[1].default_value = (1., 1., .1)
    streak = node(nt, "ShaderNodeTexNoise", (-500, -1450), Scale=45., Detail=3., Roughness=.5)
    L.new(sv.outputs[0], streak.inputs["Vector"])
    streak = maprange(nt, streak.outputs["Fac"], .5, .68, 0., look["streak"], loc=(-250, -1450))
    nz0 = node(nt, "ShaderNodeSeparateXYZ", (-500, -1550))
    L.new(geo.outputs["Normal"], nz0.inputs[0])
    upright = maprange(nt, math_(nt, "ABSOLUTE", nz0.outputs["Z"], 0., (-350, -1550)), .65, .3, loc=(-200, -1550))
    soot = math_(nt, "ADD", soot, math_(nt, "MULTIPLY", streak, upright, (300, -1450)), (450, -1300))
    c = mix(nt, fade.outputs["Color"], look["soot"], soot, (650, 200))
    # Dust and ash on whatever faces up.
    nz = node(nt, "ShaderNodeSeparateXYZ", (-700, -1600))
    L.new(geo.outputs["Normal"], nz.inputs[0])
    up = maprange(nt, nz.outputs["Z"], .45, .9, 0., look["dust"], loc=(-450, -1600))
    up = math_(nt, "MULTIPLY", up, n_big.outputs["Fac"], (0, -1600))
    c = mix(nt, c, look["dust_colour"], up, (850, 200))
    emit = node(nt, "ShaderNodeEmission", (1100, 200))
    L.new(c, emit.inputs["Color"])
    nmap = node(nt, "ShaderNodeNormalMap", (900, -300))
    L.new(normal_tex.outputs["Color"], nmap.inputs["Color"])
    bsdf = node(nt, "ShaderNodeBsdfPrincipled", (1100, -300))
    L.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    return out, emit, bsdf


def bake(kind, high, low, out, shader, img):
    bpy.context.scene.cycles.bake_type = kind
    high.active_material.node_tree.links.new(shader.outputs[0], out.inputs["Surface"])
    target = low.active_material.node_tree.nodes["bake_target"]
    target.image = img
    low.active_material.node_tree.nodes.active = target
    for o in bpy.context.view_layer.objects:
        o.select_set(o in (high, low))
    bpy.context.view_layer.objects.active = low
    kw = dict(type=kind, use_selected_to_active=True, cage_extrusion=.008, max_ray_distance=.02, margin=8)
    if kind == "NORMAL":
        kw.update(normal_space="TANGENT")
    bpy.ops.object.bake(**kw)


def _load(src, name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    bpy.ops.import_scene.gltf(filepath=src)
    meshes = [o for o in scene.objects if o.type == "MESH"]
    bpy.context.view_layer.update()
    for o in meshes:
        o.data.transform(o.matrix_world)
        o.parent = None
        o.matrix_world.identity()
    for o in [o for o in scene.objects if o.type != "MESH"]:
        bpy.data.objects.remove(o)
    if len(meshes) > 1:
        for o in meshes:
            o.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()
    high = bpy.context.view_layer.objects.active or meshes[0]
    high.name = name + "_source"
    return high


def _credit(src, out, extras):
    with open(src, "rb") as f:
        data = f.read()
    n = struct.unpack("<I", data[12:16])[0]
    src_asset = json.loads(data[20:20 + n])["asset"]
    aigc = json.loads(src_asset.get("extras", {}).get("AIGC", "{}"))
    extras = dict(extras)
    extras.setdefault("ai_generated", f"{src_asset.get('generator', 'unknown')} {src_asset.get('version', '')}".strip())
    extras["source"] = extras["source"] + ", Tripo task " + aigc.get("ProduceID", "unknown")
    with open(out, "rb") as f:
        glb = bytearray(f.read())
    n = struct.unpack("<I", glb[12:16])[0]
    doc = json.loads(glb[20:20 + n])
    doc["asset"]["extras"] = extras
    text = json.dumps(doc, separators=(",", ":")).encode()
    text += b" " * ((4 - len(text) % 4) % 4)
    rest = glb[20 + n:]
    res = bytearray(glb[:12]) + struct.pack("<I", len(text)) + b"JSON" + text + rest
    res[8:12] = struct.pack("<I", len(res))
    with open(out, "wb") as f:
        f.write(res)
    print("Wrote", out, f"{len(res) / 1e6:.1f} MB", extras, flush=True)


def prepare(src, name, height, extras, cut=None, tris=36000, bake_px=2048, look=None, blotch=None):
    """Writes art-source/library/scans/<name>.glb. `cut(centres, colours)` returns
    a mask of the faces to drop (source coordinates); the largest piece left is kept."""
    look = dict(LOOK, **(look or {}))
    scene = bpy.context.scene
    high = _load(src, name)
    scene = bpy.context.scene
    mat = high.active_material
    tex = [n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE"]
    base_tex = next(n for n in tex if n.image.colorspace_settings.name != "Non-Color" and
                    any(lk.to_socket.name == "Base Color" for lk in n.outputs["Color"].links))
    normal_tex = next(n for n in tex if any(lk.to_node.type == "NORMAL_MAP" for lk in n.outputs["Color"].links))

    bm = bmesh.new()
    bm.from_mesh(high.data)
    bm.faces.ensure_lookup_table()
    if cut:
        cols = face_colours(high.data, base_tex.image)
        cen = np.array([f.calc_center_median()[:] for f in bm.faces])
        drop = cut(cen, cols)
        bmesh.ops.delete(bm, geom=[f for f, d in zip(bm.faces, drop) if d], context="FACES")
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    largest_island(bm)
    # Close the small holes (the generator's and the cut's); a big opening such
    # as a cut-off underside stays open.
    fill = bm.faces.layers.float.new("fill")
    edges = [e for e in bm.edges if e.is_boundary]
    filled = bmesh.ops.holes_fill(bm, edges=edges, sides=300)["faces"]
    for f in filled:
        f[fill] = 1.
    bmesh.ops.triangulate(bm, faces=filled)
    bm.to_mesh(high.data)
    bm.free()
    print(f"Figure kept: {len(high.data.polygons)} faces", flush=True)

    # The game mesh: decimated on fresh UVs.
    low = high.copy()
    low.data = high.data.copy()
    low.name = low.data.name = name
    scene.collection.objects.link(low)
    mod = low.modifiers.new("decimate", "DECIMATE")
    mod.ratio = min(1., tris / len(low.data.polygons))
    run(bpy.ops.object.modifier_apply, low, modifier=mod.name)
    while low.data.uv_layers:
        low.data.uv_layers.remove(low.data.uv_layers[0])
    low.data.uv_layers.new(name="UVMap")
    bpy.ops.object.select_all(action="DESELECT")
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=.002, area_weight=.6)
    bpy.ops.object.mode_set(mode="OBJECT")
    for p in low.data.polygons:
        p.use_smooth = True
    print(f"Game mesh: {len(low.data.polygons)} triangles", flush=True)

    col_img = bpy.data.images.new(f"T_{name}_BC", bake_px, bake_px)
    nrm_img = bpy.data.images.new(f"T_{name}_N", bake_px, bake_px)
    nrm_img.colorspace_settings.name = "Non-Color"
    lm = bpy.data.materials.new(f"M_{name}")
    lm.use_nodes = True
    low.data.materials.clear()
    low.data.materials.append(lm)
    t = lm.node_tree.nodes.new("ShaderNodeTexImage")
    t.name = "bake_target"
    out, emit, bsdf = aged(mat.node_tree, base_tex, normal_tex, look, blotch)
    scene.cycles.samples = 48
    bake("EMIT", high, low, out, emit, col_img)
    scene.cycles.samples = 8
    bake("NORMAL", high, low, out, bsdf, nrm_img)

    # The game material: baked colour and normals, matt (old paint and soot).
    nt = lm.node_tree
    nt.nodes.remove(t)
    p = nt.nodes["Principled BSDF"]
    p.inputs["Roughness"].default_value = look["roughness"]
    p.inputs["Metallic"].default_value = 0.
    bc = nt.nodes.new("ShaderNodeTexImage")
    bc.image = col_img
    nt.links.new(bc.outputs["Color"], p.inputs["Base Color"])
    nn = nt.nodes.new("ShaderNodeTexImage")
    nn.image = nrm_img
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(nn.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
    bpy.data.objects.remove(high)

    # Scale and seat: the lowest point at the origin, centred, facing -Y.
    co = np.array([v.co[:] for v in low.data.vertices])
    lo, hi = co.min(0), co.max(0)
    k = height / (hi[2] - lo[2])
    co = (co - [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]]) * k
    low.data.vertices.foreach_set("co", co.ravel())
    low.data.update()
    out_path = os.path.join(SCANS, name + ".glb")
    os.makedirs(SCANS, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    low.select_set(True)
    bpy.ops.export_scene.gltf(filepath=out_path, export_format="GLB", export_yup=True, export_apply=True,
                              use_selection=True, export_cameras=False, export_lights=False,
                              export_image_format="JPEG", export_image_quality=90)
    extras = dict(extras)
    extras["adapted"] = extras["adapted"].format(tris=len(low.data.polygons), px=bake_px, height=height)
    _credit(src, out_path, extras)
    return out_path
