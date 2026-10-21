"""Shared building blocks for the area scripts in tools/areas/ (run inside Blender):
materials from the CC0 library (art-source/library/), boxes and cylinders with
real-world UVs, colliders and named empties (Technical Design Document, 7.1),
imported library models and the rendered drawings (tools/drawings/).
"""

import math
import os

import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LIB = os.path.join(ROOT, "art-source", "library")
TEXTURES = os.path.join(ROOT, "art-source", "textures", "ep1")

# Real-world size of each library material's texture, in metres (Poly Haven).
TILE = {
    "floor_tiles_06": 3.0,
    "yellow_plaster": 2.0,
    "dark_wooden_planks": 2.0,
    "dark_wood": 2.0,
    "teak_veneer": 1.0,
    "wood_table_worn": 0.55,
    "rough_linen": 0.27,
    "fabric_pattern_07": 0.4,
    "quatrefoil_jacquard_fabric": 0.28,
    "thatch_roof_angled": 1.2,
    "reed_roof_04": 2.5,
    "bamboo_wall": 2.0,
    "clay_roof_tiles_02": 2.5,
    "red_dirt_mud_01": 1.5,
    "muddy_tracks": 2.25,
    "weathered_planks": 2.0,
    "weathered_brown_planks": 1.8,
    "old_planks_02": 2.0,
    "waffle_pique_cotton": 0.28,
    "forest_leaves_02": 3.0,
    "bark_brown_02": 1.0,
    "forest_ground_04": 3.0,
    "brown_mud_leaves_01": 2.0,
    "mud_forest": 2.0,
    "moss_wood": 1.0,
    "clay_plaster": 2.0,
}

# --------------------------------------------------------------- materials


def gltf_output_group():
    group = bpy.data.node_groups.get("glTF Material Output")
    if group is None:
        group = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        group.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    return group


def image(path, non_color):
    img = bpy.data.images.load(path, check_existing=True)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    return img


def library_material(tex_id, name=None, tint=None, colour=None, tile=None):
    """Principled material from a library texture set (BC, N, ORM), as glTF expects.
    `colour` replaces the colour map (keeping the weave or grain in N and ORM);
    `tile` overrides the texture's real-world size in metres."""
    mat = bpy.data.materials.new(name or f"M_{tex_id}")
    mat.use_backface_culling = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    base = os.path.join(LIB, "materials", tex_id, tex_id)
    bc = nodes.new("ShaderNodeTexImage")
    bc.image = image(f"{base}_BC.jpg", False)
    if colour:
        nodes.remove(bc)
        bsdf.inputs["Base Color"].default_value = (*colour, 1)
    elif tint:
        mix = nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs[7].default_value = (*tint, 1)
        links.new(bc.outputs["Color"], mix.inputs[6])
        links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    else:
        links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
    nrm = nodes.new("ShaderNodeTexImage")
    nrm.image = image(f"{base}_N.jpg", True)
    nmap = nodes.new("ShaderNodeNormalMap")
    links.new(nrm.outputs["Color"], nmap.inputs["Color"])
    links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    orm = nodes.new("ShaderNodeTexImage")
    orm.image = image(f"{base}_ORM.jpg", True)
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(orm.outputs["Color"], split.inputs["Color"])
    links.new(split.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(split.outputs["Blue"], bsdf.inputs["Metallic"])
    out = nodes.new("ShaderNodeGroup")
    out.node_tree = gltf_output_group()
    links.new(split.outputs["Red"], out.inputs["Occlusion"])
    mat["tile"] = tile or TILE[tex_id]
    return mat


def plain(name, colour, rough=0.6, metal=0.0, alpha=1.0, emission=None, strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_backface_culling = alpha >= 1.0
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*colour, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Alpha"].default_value = alpha
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    mat["tile"] = 1.0
    return mat


def image_material(name, path, rough=0.9, cutout=False, tint=None, tile=0.0, metal=0.0):
    """Material from one colour image. `cutout` uses its alpha as a mask (leaves,
    the flag, the valance: glTF alphaMode MASK) and shows both sides; `tint`
    multiplies the colour (dead leaves from the green ones)."""
    mat = bpy.data.materials.new(name)
    mat.use_backface_culling = not cutout
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image(path, False)
    if tint:
        mix = nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs[7].default_value = (*tint, 1)
        links.new(tex.outputs["Color"], mix.inputs[6])
        links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    else:
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if cutout:
        # The glTF exporter reads Alpha through a Round node as alphaMode MASK, cutoff 0.5.
        rnd = nodes.new("ShaderNodeMath")
        rnd.operation = "ROUND"
        links.new(tex.outputs["Alpha"], rnd.inputs[0])
        links.new(rnd.outputs[0], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    mat["tile"] = tile  # 0: stretch the image over each face once
    return mat


def glow_material(name, path, strength=3.0):
    """A self-lit card from one image with alpha (flames): the image is both colour
    and emission, its alpha blends it into the air (glTF alphaMode BLEND); both sides."""
    mat = bpy.data.materials.new(name)
    mat.use_backface_culling = False
    mat.blend_method = "BLEND"
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image(path, False)
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Emission Strength"].default_value = strength
    bsdf.inputs["Roughness"].default_value = 1.0
    mat["tile"] = 0.0
    return mat


def texture(file):
    """Path of a painted texture (tools/drawings/village.mjs), checked."""
    path = os.path.join(TEXTURES, f"{file}.png")
    if not os.path.exists(path):
        raise SystemExit(f"Missing {path}: run `npm run drawings -- ep1` first.")
    return path


# ---------------------------------------------------------------- geometry


def world_uvs(obj):
    """Box-projected UVs at the material's real-world tile size (or 0-1 per face)."""
    mesh = obj.data
    tile = mesh.materials[0].get("tile", 1.0) if mesh.materials else 1.0
    uv = mesh.uv_layers.new(name="UVMap")
    mw = obj.matrix_world
    for poly in mesh.polygons:
        n = poly.normal
        axis = max(range(3), key=lambda i: abs(n[i]))
        ua, va = [(1, 2), (0, 2), (0, 1)][axis]
        coords = [mw @ mesh.vertices[mesh.loops[i].vertex_index].co for i in poly.loop_indices]
        if tile == 0.0:
            us = [c[ua] for c in coords]
            vs = [c[va] for c in coords]
            for li, c in zip(poly.loop_indices, coords):
                uv.data[li].uv = ((c[ua] - min(us)) / (max(us) - min(us) or 1), (c[va] - min(vs)) / (max(vs) - min(vs) or 1))
        else:
            for li, c in zip(poly.loop_indices, coords):
                uv.data[li].uv = (c[ua] / tile, c[va] / tile)


def bevel(obj, width=0.008):
    mod = obj.modifiers.new("bevel", "BEVEL")
    mod.width = width
    mod.segments = 2
    mod.limit_method = "ANGLE"


def box(name, coll, x0, x1, y0, y1, z0, z1, mat=None, tilt=(0, 0, 0), edge=0.0, **props):
    """Box from min/max corners, origin at its centre; `tilt` rotates it in place."""
    mesh = bpy.data.meshes.new(name)
    cx, cy, cz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
    verts = [(x - cx, y - cy, z - cz) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = (cx, cy, cz)
    obj.rotation_euler = tilt
    coll.objects.link(obj)
    if mat:
        mesh.materials.append(mat)
        bpy.context.view_layer.update()
        world_uvs(obj)
    if edge:
        bevel(obj, edge)
    for k, v in props.items():
        obj[k] = v
    return obj


def collider(name, coll, x0, x1, y0, y1, z0, z1, surface="teak"):
    return box(f"col_{name}", coll, x0, x1, y0, y1, z0, z1, surface=surface)


def cylinder(name, coll, x, y, z0, z1, radius, mat, verts=24, radius_top=None, **props):
    bpy.ops.mesh.primitive_cone_add(
        vertices=verts, radius1=radius, radius2=radius if radius_top is None else radius_top, depth=z1 - z0,
        location=(x, y, (z0 + z1) / 2),
    )
    obj = bpy.context.active_object
    obj.name = name
    for c in obj.users_collection:
        c.objects.unlink(obj)
    coll.objects.link(obj)
    obj.data.materials.append(mat)
    bpy.context.view_layer.update()
    world_uvs(obj)
    for k, v in props.items():
        obj[k] = v
    return obj


def empty(name, coll, location, rotation=(0, 0, 0), **props):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.rotation_euler = rotation
    obj.empty_display_type = "PLAIN_AXES"
    coll.objects.link(obj)
    for k, v in props.items():
        obj[k] = v
    return obj


def cloth(name, coll, x0, x1, z0, z1, y, mat, folds=7, depth=0.04, segments=(40, 12), axis="x"):
    """A hanging cloth panel with soft vertical folds (curtains)."""
    nx, nz = segments
    mesh = bpy.data.meshes.new(name)
    verts, faces = [], []
    for j in range(nz + 1):
        for i in range(nx + 1):
            u = i / nx
            t = x0 + (x1 - x0) * u
            off = math.sin(u * folds * 2 * math.pi) * depth * (0.6 + 0.4 * j / nz)
            z = z1 - (z1 - z0) * j / nz
            verts.append((t, y + off, z) if axis == "x" else (y + off, t, z))
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    mesh.materials.append(mat)
    bpy.context.view_layer.update()
    world_uvs(obj)
    mat.use_backface_culling = False
    return obj


def import_model(coll, model_id, location, rot_deg=0.0, name=None, collide=True, scale=1.0, surface="teak", swap=None, **props):
    """Imports a library glTF under an empty named `name` (e.g. interact_lamp) at
    `location` (the model's origin, usually its base centre). `swap` replaces
    materials by name (e.g. a frame's picture)."""
    path = os.path.join(LIB, "models", model_id, f"{model_id}.gltf")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for obj in new:
        for slot in obj.material_slots:
            if swap and slot.material and slot.material.name in swap:
                slot.material = swap[slot.material.name]
    parent = empty(name or f"prop_{model_id}", coll, location, (0, 0, math.radians(rot_deg)), **props)
    parent.scale = (scale, scale, scale)
    for obj in new:
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        coll.objects.link(obj)
        if obj.parent is None:
            obj.parent = parent
    bpy.context.view_layer.update()
    if collide:
        pts = [o.matrix_world @ v.co for o in new if o.type == "MESH" for v in o.data.vertices]
        if pts:
            xs, ys, zs = [p.x for p in pts], [p.y for p in pts], [p.z for p in pts]
            collider(f"{(name or model_id)}", coll, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), surface)
    return parent


def top_of(parent):
    """Highest point of an imported model, in world space."""
    bpy.context.view_layer.update()
    zs = [(o.matrix_world @ v.co).z for o in parent.children_recursive if o.type == "MESH" for v in o.data.vertices]
    return max(zs) if zs else parent.location.z


def mesh_object(name, coll, verts, faces, mat=None, uvs=None, smooth=False, **props):
    """A mesh from vertices and faces; `uvs` gives one (u, v) per face corner, in
    face order, or box-projected world UVs are made from the material's tile."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    if mat:
        mesh.materials.append(mat)
    if uvs is not None:
        layer = mesh.uv_layers.new(name="UVMap")
        for i, uv in enumerate(uvs):
            layer.data[i].uv = uv
    elif mat:
        bpy.context.view_layer.update()
        world_uvs(obj)
    if smooth:
        for poly in mesh.polygons:
            poly.use_smooth = True
    for k, v in props.items():
        obj[k] = v
    return obj


def lathe(name, coll, profile, x, y, z, mat, segments=24, v_scale=1.0, **props):
    """A turned shape (jar, urn, drum) from (radius, height) points, bottom to top,
    standing at (x, y, z). U runs round it and V up its profile."""
    verts, faces, uvs = [], [], []
    n = len(profile)
    lengths = [0.0]
    for (r0, h0), (r1, h1) in zip(profile, profile[1:]):
        lengths.append(lengths[-1] + math.hypot(r1 - r0, h1 - h0))
    for i, (r, h) in enumerate(profile):
        for k in range(segments + 1):
            a = 2 * math.pi * k / segments
            verts.append((x + r * math.cos(a), y + r * math.sin(a), z + h))
    for i in range(n - 1):
        for k in range(segments):
            a = i * (segments + 1) + k
            faces.append((a, a + 1, a + segments + 2, a + segments + 1))
            for (ii, kk) in ((i, k), (i, k + 1), (i + 1, k + 1), (i + 1, k)):
                uvs.append((kk / segments, lengths[ii] * v_scale))
    return mesh_object(name, coll, verts, faces, mat, uvs=uvs, smooth=True, **props)


def tube(name, coll, points, radius, mat, sides=6, metres_per_v=1.0, radius_end=None, **props):
    """A rope, thread or pole along `points` (a list of (x, y, z)). U round, V along."""
    verts, faces, uvs = [], [], []
    total = 0.0
    dist = [0.0]
    for a, b in zip(points, points[1:]):
        total += math.dist(a, b)
        dist.append(total)
    for i, p in enumerate(points):
        a = points[max(0, i - 1)]
        b = points[min(len(points) - 1, i + 1)]
        t = [b[j] - a[j] for j in range(3)]
        tl = math.sqrt(sum(c * c for c in t)) or 1
        t = [c / tl for c in t]
        up = (0, 0, 1) if abs(t[2]) < 0.9 else (1, 0, 0)
        n1 = [t[1] * up[2] - t[2] * up[1], t[2] * up[0] - t[0] * up[2], t[0] * up[1] - t[1] * up[0]]
        l1 = math.sqrt(sum(c * c for c in n1)) or 1
        n1 = [c / l1 for c in n1]
        n2 = [t[1] * n1[2] - t[2] * n1[1], t[2] * n1[0] - t[0] * n1[2], t[0] * n1[1] - t[1] * n1[0]]
        r = radius if radius_end is None else radius + (radius_end - radius) * dist[i] / (total or 1)
        for k in range(sides + 1):
            ang = 2 * math.pi * k / sides
            c, s_ = math.cos(ang) * r, math.sin(ang) * r
            verts.append(tuple(p[j] + n1[j] * c + n2[j] * s_ for j in range(3)))
    for i in range(len(points) - 1):
        for k in range(sides):
            a = i * (sides + 1) + k
            faces.append((a, a + 1, a + sides + 2, a + sides + 1))
            for (ii, kk) in ((i, k), (i, k + 1), (i + 1, k + 1), (i + 1, k)):
                uvs.append((kk / sides, dist[ii] / metres_per_v))
    return mesh_object(name, coll, verts, faces, mat, uvs=uvs, smooth=True, **props)


def sag(a, b, drop, n=8):
    """Points of a cord hanging between a and b, dropping `drop` metres at the middle."""
    return [tuple(a[j] + (b[j] - a[j]) * t - (drop * 4 * t * (1 - t) if j == 2 else 0) for j in range(3))
            for t in (i / n for i in range(n + 1))]


# ------------------------------------------------------------ drawings


def drawing(name, file):
    """Paper with one of the rendered drawings (tools/drawings/ep1.mjs)."""
    path = os.path.join(TEXTURES, f"{file}.png")
    if not os.path.exists(path):
        raise SystemExit(f"Missing {path}: run `npm run drawings -- ep1` first.")
    return image_material(name, path)


def picture_uvs(obj, right, up):
    """Lays the image upright for someone facing the picture: `right` and `up` are
    world directions across it (box UVs alone mirror pictures seen from some walls)."""
    bpy.context.view_layer.update()
    mesh = obj.data
    mw = obj.matrix_world
    uv = mesh.uv_layers.active
    for poly in mesh.polygons:
        coords = [mw @ mesh.vertices[mesh.loops[i].vertex_index].co for i in poly.loop_indices]
        us = [sum(c[k] * right[k] for k in range(3)) for c in coords]
        vs = [sum(c[k] * up[k] for k in range(3)) for c in coords]
        for li, u, v in zip(poly.loop_indices, us, vs):
            uv.data[li].uv = ((u - min(us)) / (max(us) - min(us) or 1), (v - min(vs)) / (max(vs) - min(vs) or 1))
