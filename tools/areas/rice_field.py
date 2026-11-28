"""Rice for the Episode 1 paddies (November 19, 2026), modelled on the user's
references (art direction: transplanted rice at grain filling, late monsoon; and a
ripe golden field ready to cut).

A hill (one transplanted clump) is 12-20 tillers fanning out from one root: each a
culm with four or five long, narrow blades that arch out and droop at the tip, the
flag leaf shorter and stiffer, and a panicle that bows over on its neck, its
branches hung with grains. Green fields carry pale green-gold grain heads; the ripe
field is straw-gold, heavier, bowed lower.

In the game a field is too many hills to model (a hill is ~3000 triangles and a
paddy holds tens of thousands), so `render_strip` renders rows of these hills to
alpha textures (flat albedo with their own occlusion baked in, front-on) and
`field_cards` stands them up as cards along the rows. Run inside Blender.
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

# Linear albedo.
LEAF = (0.1, 0.22, 0.045)
LEAF_OLD = (0.26, 0.25, 0.08)
LEAF_DEAD = (0.42, 0.32, 0.12)
CULM = (0.14, 0.2, 0.06)
GRAIN_GREEN = (0.58, 0.52, 0.2)
GRAIN_RIPE = (0.62, 0.45, 0.15)
STRAW = (0.5, 0.38, 0.16)


def _bend(p0, d0, length, droop, n):
    """Points along a blade that leaves p0 in direction d0 and droops under gravity."""
    pts = []
    d = Vector(d0).normalized()
    p = Vector(p0)
    seg = length / n
    for i in range(n + 1):
        pts.append(p.copy())
        t = i / n
        d = (d + Vector((0, 0, -droop * (0.4 + 1.6 * t) / n))).normalized()
        p = p + d * seg
    return pts


def _ribbon(bm, layer, pts, width, colour, twist=0.0, taper=0.92):
    """A blade as a strip along pts, its width across the bend."""
    verts = []
    n = len(pts) - 1
    for i, p in enumerate(pts):
        t = i / n
        fwd = (pts[min(i + 1, n)] - pts[max(i - 1, 0)]).normalized()
        side = fwd.cross(Vector((0, 0, 1)))
        if side.length < 1e-4:
            side = Vector((1, 0, 0))
        side.normalize()
        side = Matrix.Rotation(twist * t, 3, fwd) @ side
        w = width * (1 - taper * t ** 1.4) * (0.6 + 0.4 * min(1, t * 6))
        verts.append((bm.verts.new(p - side * w / 2), bm.verts.new(p + side * w / 2)))
    for i in range(n):
        a, b = verts[i]
        c, d = verts[i + 1]
        f = bm.faces.new((a, b, d, c))
        for loop in f.loops:
            loop[layer] = (*colour, 1.0)


def _culm(bm, layer, base, top, r, colour):
    """A thin four-sided stalk."""
    axis = (top - base).normalized()
    side = axis.cross(Vector((0, 0, 1)))
    if side.length < 1e-4:
        side = Vector((1, 0, 0))
    side.normalize()
    up = axis.cross(side)
    rings = []
    for p, rr in ((base, r), (top, r * 0.6)):
        rings.append([bm.verts.new(p + (side * math.cos(a) + up * math.sin(a)) * rr)
                      for a in (0, math.pi / 2, math.pi, 1.5 * math.pi)])
    for k in range(4):
        f = bm.faces.new((rings[0][k], rings[0][(k + 1) % 4], rings[1][(k + 1) % 4], rings[1][k]))
        for loop in f.loops:
            loop[layer] = (*colour, 1.0)


def _grain(bm, layer, at, along, colour, size=0.0095):
    """One grain: two crossed slim diamonds."""
    along = along.normalized()
    side = along.cross(Vector((0, 0, 1)))
    if side.length < 1e-4:
        side = Vector((1, 0, 0))
    side.normalize()
    up = along.cross(side)
    for w in (side, up):
        v = [bm.verts.new(at - along * size * 0.5), bm.verts.new(at + w * size * 0.17),
             bm.verts.new(at + along * size * 0.5), bm.verts.new(at - w * size * 0.17)]
        f = bm.faces.new(v)
        for loop in f.loops:
            loop[layer] = (*colour, 1.0)


def rice_hill(rng, ripe=False, tillers=None):
    """One hill's bmesh, its root at the origin, about a metre tall."""
    bm = bmesh.new()
    layer = bm.loops.layers.color.new("paint")
    tillers = tillers or int(rng.integers(12, 21))
    grain = np.array(GRAIN_RIPE if ripe else GRAIN_GREEN)
    for t in range(tillers):
        yaw = rng.uniform(0, 2 * math.pi)
        lean = rng.uniform(0.05, 0.33)
        base = Vector((math.cos(yaw) * rng.uniform(0, 0.035), math.sin(yaw) * rng.uniform(0, 0.035), -0.04))
        d = Vector((math.cos(yaw) * math.sin(lean), math.sin(yaw) * math.sin(lean), math.cos(lean)))
        height = rng.uniform(0.72, 0.95) * (1.04 if ripe else 1.0)
        top = base + d * height
        culm_col = np.array(STRAW if ripe else CULM) * rng.uniform(0.85, 1.15)
        _culm(bm, layer, base, top, 0.0028, culm_col)
        # Leaves: alternate up the culm, lower ones longer, arching and drooping more.
        leaves = int(rng.integers(4, 6))
        for k in range(leaves):
            h = 0.08 + 0.72 * k / leaves + rng.uniform(-0.03, 0.03)
            p = base + d * (height * h)
            a = yaw + (k % 2) * math.pi + rng.uniform(-0.6, 0.6)
            flag = k == leaves - 1
            out = rng.uniform(0.3, 0.55) if flag else rng.uniform(0.5, 1.1)
            dirn = Vector((math.cos(a) * out, math.sin(a) * out, 1.0))
            length = rng.uniform(0.25, 0.34) if flag else rng.uniform(0.38, 0.62)
            droop = rng.uniform(0.3, 0.7) if flag else rng.uniform(1.2, 2.4)
            age = (0.55 + 0.45 * (1 - k / leaves)) if ripe else (1 - k / leaves) * 0.5
            col = np.array(LEAF) * rng.uniform(0.8, 1.2)
            if ripe:
                col = col * (1 - age) + np.array(LEAF_DEAD) * age
            elif rng.random() < age * 0.6:
                col = col * 0.5 + np.array(LEAF_OLD) * 0.5
            _ribbon(bm, layer, _bend(p, dirn, length, droop, 6), rng.uniform(0.009, 0.014), col,
                    twist=rng.uniform(-1.2, 1.2))
        # Panicle: the neck bows over, branches hang from the rachis, grains along them.
        bow = rng.uniform(3.2, 4.6) * (1.3 if ripe else 1.0)
        neck = _bend(top, d + Vector((math.cos(yaw), math.sin(yaw), 0)) * 0.25,
                     rng.uniform(0.2, 0.28), bow, 7)
        _ribbon(bm, layer, neck, 0.003, culm_col, taper=0.3)
        branches = int(rng.integers(8, 13))
        for b in range(branches):
            i = 1 + int((len(neck) - 2) * b / branches)
            root = neck[i]
            ang = rng.uniform(0, 2 * math.pi)
            bdir = (neck[i + 1] - neck[i]).normalized() + Vector((math.cos(ang), math.sin(ang), 0)) * 0.6
            br = _bend(root, bdir, rng.uniform(0.06, 0.13), 2.2, 4)
            _ribbon(bm, layer, br, 0.0016, culm_col, taper=0.2)
            for j in range(1, len(br)):
                for g in range(int(rng.integers(3, 6))):
                    gp = br[j - 1].lerp(br[j], rng.uniform(0, 1)) + Vector(rng.normal(0, 0.003, 3))
                    gc = grain * rng.uniform(0.82, 1.15)
                    if not ripe and rng.random() < 0.3:
                        gc = gc * 0.7 + np.array(LEAF) * 0.3 * 2
                    _grain(bm, layer, gp, br[j] - br[j - 1] + Vector(rng.normal(0, 0.3, 3)), gc)
    return bm


def hill_object(name, coll, rng, ripe=False, tillers=None):
    bm = rice_hill(rng, ripe, tillers)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def paint_material(name="M_rice_paint"):
    """Flat albedo from the paint attribute, darkened by ambient occlusion: what the
    card textures hold (the game lights them)."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    col = nt.nodes.new("ShaderNodeVertexColor")
    col.layer_name = "paint"
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.25
    ao.samples = 16
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 0.6
    nt.links.new(col.outputs["Color"], ao.inputs["Color"])
    nt.links.new(col.outputs["Color"], mix.inputs["A"])
    nt.links.new(ao.outputs["AO"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    mat.use_backface_culling = False
    return mat


def lit_material(name="M_rice_lit"):
    """For Cycles previews of modelled hills: the paint as a leafy surface."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    col = nt.nodes.new("ShaderNodeVertexColor")
    col.layer_name = "paint"
    nt.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.6
    bsdf.inputs["Subsurface Weight"].default_value = 0.0
    mat.use_backface_culling = False
    return mat


def render_strip(path, ripe, seed, width=2.0, height=1.25, px=(2048, 1280), rows=3):
    """Renders a strip of rice rows, `width` m wide, front-on and orthographic, to a
    PNG with alpha: hills every 0.25 m along the rows, `rows` rows behind each other
    0.22 m apart (so the strip has depth and no gaps), hills spilling over the edges
    so the card tiles side by side."""
    rng = np.random.default_rng(seed)
    scene = bpy.data.scenes.new(f"rice_strip_{seed}")
    coll = scene.collection
    mat = paint_material()
    objs = []
    for r in range(rows):
        x = -width / 2 - 0.25
        while x < width / 2 + 0.3:
            o = hill_object("rice_hill_tmp", coll, rng, ripe)
            o.data.materials.append(mat)
            o.location = (x + rng.uniform(-0.04, 0.04), r * 0.22 + rng.uniform(-0.03, 0.03), 0)
            o.rotation_euler = (0, 0, rng.uniform(0, 2 * math.pi))
            objs.append(o)
            x += 0.25
    cam = bpy.data.objects.new("rice_cam", bpy.data.cameras.new("rice_cam"))
    coll.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = width
    cam.location = (0, -5, height / 2 - 0.04)
    cam.rotation_euler = (math.pi / 2, 0, 0)
    scene.camera = cam
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = False
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = px
    cam.data.sensor_fit = "HORIZONTAL"
    scene.render.pixel_aspect_x = 1
    # Height of the frame follows the aspect: width * py / px must equal `height`.
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = path
    world = bpy.data.worlds.new("rice_world")
    world.color = (0, 0, 0)
    scene.world = world
    with bpy.context.temp_override(scene=scene):
        bpy.ops.render.render(write_still=True)
    for o in objs:
        bpy.data.meshes.remove(o.data)
    bpy.data.objects.remove(cam)
    bpy.data.scenes.remove(scene)
    return path


def render_top(path, ripe, seed, size=2.0, px=1024):
    """The rice canopy seen from straight above: a `size` m square of hills at 0.25 m,
    spilling over its edges so tiles join, alpha where the water shows between hills."""
    rng = np.random.default_rng(seed)
    scene = bpy.data.scenes.new(f"rice_top_{seed}")
    coll = scene.collection
    mat = paint_material()
    objs = []
    n = int(size / 0.25) + 2
    for i in range(n):
        for j in range(n):
            o = hill_object("rice_hill_tmp", coll, rng, ripe)
            o.data.materials.append(mat)
            o.location = (-size / 2 - 0.125 + i * 0.25 + rng.uniform(-0.03, 0.03),
                          -size / 2 - 0.125 + j * 0.25 + rng.uniform(-0.03, 0.03), 0)
            o.rotation_euler = (0, 0, rng.uniform(0, 2 * math.pi))
            objs.append(o)
    cam = bpy.data.objects.new("rice_cam", bpy.data.cameras.new("rice_cam"))
    coll.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = size
    cam.location = (0, 0, 5)
    scene.camera = cam
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.cycles.transparent_max_bounces = 64
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = px
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = path
    world = bpy.data.worlds.new("rice_world")
    world.color = (0, 0, 0)
    scene.world = world
    with bpy.context.temp_override(scene=scene):
        bpy.ops.render.render(write_still=True)
    for o in objs:
        bpy.data.meshes.remove(o.data)
    bpy.data.objects.remove(cam)
    bpy.data.scenes.remove(scene)
    return path


def render_hills(path, ripe, seed, cells=4, cell_px=(512, 1024), width=0.62, height=1.24):
    """Single hills front-on, one per atlas cell (`cells` across), for the paddies' hill
    cards: each cell `width` x `height` m, the hill's root on the cell's bottom edge."""
    rng = np.random.default_rng(seed)
    scene = bpy.data.scenes.new(f"rice_hills_{seed}")
    coll = scene.collection
    mat = paint_material()
    cam = bpy.data.objects.new("rice_cam", bpy.data.cameras.new("rice_cam"))
    coll.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = height
    cam.data.sensor_fit = "VERTICAL"
    cam.location = (0, -5, height / 2 - 0.04)
    cam.rotation_euler = (math.pi / 2, 0, 0)
    scene.camera = cam
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.cycles.transparent_max_bounces = 64
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = cell_px
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    world = bpy.data.worlds.new("rice_world")
    world.color = (0, 0, 0)
    scene.world = world
    tiles = []
    for i in range(cells):
        o = hill_object("rice_hill_tmp", coll, rng, ripe, tillers=int(rng.integers(14, 22)))
        o.data.materials.append(mat)
        # Keep the hill inside its cell: squeeze its spread across the card a little.
        o.scale = (min(1.0, width / max(0.01, o.dimensions.x + 0.02)),) * 2 + (1.0,)
        scene.render.filepath = f"{path}.cell{i}.png"
        with bpy.context.temp_override(scene=scene):
            bpy.ops.render.render(write_still=True)
        tiles.append(scene.render.filepath)
        bpy.data.meshes.remove(o.data)
    w, h = cell_px
    atlas = np.zeros((h, w * cells, 4), dtype=np.float32)
    for i, tile in enumerate(tiles):
        img = bpy.data.images.load(tile)
        atlas[:, i * w:(i + 1) * w] = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
        bpy.data.images.remove(img)
        import os
        os.remove(tile)
    out = bpy.data.images.new(os.path.basename(path), w * cells, h, alpha=True)
    out.pixels.foreach_set(atlas.ravel())
    out.filepath_raw = path
    out.file_format = "PNG"
    out.save()
    bpy.data.objects.remove(cam)
    bpy.data.scenes.remove(scene)
    return path
