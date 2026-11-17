"""The taxi driver's head and neck from a real photoscan: "A-Pose - Male Full Body 3D Scan"
by OverseerThuror (CC BY 4.0, credited in docs/production/asset-tracker.csv).

From the 2.6-million-face scan this keeps the head and the bare neck, takes off the hoodie,
and turns the modern baseball cap into a 1930s cloth cap: its brim is cut back to a short
peak and its cloth, logos and eyelets are replaced by worn dark cotton twill. His skin is
browned to a Khmer driver's sun-dark tone, keeping every pore, crease and stubble hair of
the photo. A 46,000-triangle copy with its own clean UV layout is then baked from the
full-resolution scan in Cycles: colour (4096 px) and normal relief (2048 px).

    blender -b --factory-startup -P tools/travel/taxi_driver_head.py -- PATH/scene.gltf [--debug DIR]

Writes art-source/library/scans/taxi_driver_head.glb. tools/travel/build-taxi.py sets it on
the scanned body's collar and bakes his glances, nod, speech and blink as shapes.
"""

import math
import os
import sys
import tempfile

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "art-source", "library", "scans", "taxi_driver_head.glb")
LINEN = os.path.join(ROOT, "art-source", "library", "materials", "rough_linen")
CREDIT = dict(title="A-Pose - Male Full Body 3D Scan", author="OverseerThuror",
              url="https://sketchfab.com/3d-models/78c2d136f91c46a8a696d5bacfde2daf",
              license="CC-BY-4.0")
FACES = 46000
CUT = 1.80  # metres up the scan: below the jaw, into the hoodie's collar

args = sys.argv[sys.argv.index("--") + 1:]
SOURCE = args[0]
DEBUG = args[args.index("--debug") + 1] if "--debug" in args else None


def load():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=SOURCE)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join()
    head = bpy.context.active_object
    head.name = head.data.name = "scan_hi"
    for o in [o for o in bpy.data.objects if o.type != "MESH"]:
        bpy.data.objects.remove(o)
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < CUT], context="VERTS")
    # The download is cut into slabs (one per glTF primitive); weld them back into one skin.
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0003)
    bm.to_mesh(head.data)
    bm.free()
    return head


def photo(head):
    return next(n.image for n in head.data.materials[0].node_tree.nodes if n.type == "TEX_IMAGE")


def small_pixels(image, size=2048):
    """The scan's colour map, shrunk for sampling (the 8K original stays for the bake)."""
    copy = image.copy()
    copy.scale(size, size)
    px = np.empty(size * size * 4, np.float32)
    copy.pixels.foreach_get(px)
    bpy.data.images.remove(copy)
    return px.reshape(size, size, 4)[..., :3]


def face_colours(head, px):
    me = head.data
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers.active.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    start = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("loop_start", start)
    total = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("loop_total", total)
    centre = np.add.reduceat(uv, start) / total[:, None]
    h, w = px.shape[:2]
    return px[np.clip((centre[:, 1] % 1) * (h - 1), 0, h - 1).astype(int),
              np.clip((centre[:, 0] % 1) * (w - 1), 0, w - 1).astype(int)]


def centres(head):
    me = head.data
    c = np.empty(len(me.polygons) * 3, np.float32)
    me.polygons.foreach_get("center", c)
    return c.reshape(-1, 3)


def skin_like(c):
    r, g, b = c[:, 0], c[:, 1], c[:, 2]
    return (r > 0.16) & (r > g * 1.04) & (g > b * 0.92) & (r - b > 0.05)


def classify(head, px):
    """Per face: 0 skin, 1 hair, 2 cap, 3 hoodie (dropped)."""
    col = face_colours(head, px)
    ctr = centres(head)
    lum = col @ np.array([0.3, 0.59, 0.11])
    skin = skin_like(col)
    # The neck's axis from the bare skin just under the jaw.
    band = skin & (ctr[:, 2] > 1.84) & (ctr[:, 2] < 1.88)
    axis = ctr[band, :2].mean(0)
    radius = np.linalg.norm(ctr[:, :2] - axis, axis=1)
    purple = (col[:, 2] > col[:, 0] * 1.12) & (col[:, 2] > col[:, 1] * 1.12)
    # Hair on the scalp and sideburns only: dark stubble and the shadow under his jaw are skin.
    hair = (lum < 0.13) & ~purple & (ctr[:, 2] > 1.945)
    kind = np.zeros(len(col), np.int8)
    kind[hair] = 1
    # The cap: everything above the brow that is not his skin or hair; the brim, logos,
    # eyelets, button and snapback strap included.
    # Its lower edge runs above his brow and ears and dips to the strap at the back.
    back = np.clip((ctr[:, 1] - axis[1]) / np.maximum(radius, 1e-6), 0, 1)
    edge = BROW - 0.078 * back ** 1.5
    cap = (ctr[:, 2] > edge) & ~(skin & (ctr[:, 2] < BROW + 0.005) & (back < 0.35))
    cap |= (ctr[:, 2] > BROW - 0.01) & (ctr[:, 1] < BRIM_ROOT - 0.004)  # the brim
    cap |= (ctr[:, 2] > CROWN)
    # The khaki brim lining and snapback strap: yellower than any of his skin.
    khaki = (col[:, 1] > col[:, 0] * 0.86) & (col[:, 0] > 0.42) & (col[:, 2] < col[:, 1])
    cap |= khaki & (ctr[:, 2] > 1.94)
    kind[cap] = 2
    # The hoodie stands off the neck (over 10.4 cm from its axis); his nape and the shadow
    # under his jaw are skin even where the photo is dark.
    hood = (ctr[:, 2] < 1.875) & (~skin) & (radius > 0.104 + 0.01 * back) & (back > 0.3)
    hood |= (ctr[:, 2] < 1.855) & (~skin)
    hood |= (ctr[:, 2] < 1.9) & purple & (radius > 0.08)  # the hood's lining, never a mole
    kind[hood] = 3
    print("TAXI_HEAD axis", axis.round(3), "faces skin/hair/cap/hood",
          [int((kind == k).sum()) for k in range(4)])
    return kind, axis


def keep(head, kind):
    me = head.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    layer = bm.faces.layers.int.new("kind")
    for f in bm.faces:
        f[layer] = int(kind[f.index])
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[layer] == 3], context="FACES")
    # Crumbs of the hoodie and floating scan noise go; the head and its neck stay.
    bm.faces.ensure_lookup_table()
    seen = set()
    pieces = []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack = [f]
        piece = []
        seen.add(f.index)
        while stack:
            g = stack.pop()
            piece.append(g)
            for e in g.edges:
                for n in e.link_faces:
                    if n.index not in seen:
                        seen.add(n.index)
                        stack.append(n)
        pieces.append(piece)
    pieces.sort(key=len)
    bmesh.ops.delete(bm, geom=[f for p in pieces[:-1] if len(p) < 4000 for f in p], context="FACES")
    print("TAXI_HEAD pieces kept", [len(p) for p in pieces if len(p) >= 4000])
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # Pinholes left by dark specks (a mole, a shadowed crease) are closed again.
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary and min(v.co.z for v in e.verts) > 1.88], sides=400)
    bm.to_mesh(me)
    bm.free()


def vertex_masks(head):
    """Cap and hair masks as colour attributes, softened across their borders."""
    me = head.data
    kind = np.empty(len(me.polygons), np.int32)
    me.attributes["kind"].data.foreach_get("value", kind)
    cap = np.zeros(len(me.vertices))
    hair = np.zeros(len(me.vertices))
    count = np.zeros(len(me.vertices))
    for p in me.polygons:
        for v in p.vertices:
            cap[v] += kind[p.index] == 2
            hair[v] += kind[p.index] == 1
            count[v] += 1
    cap /= np.maximum(count, 1)
    hair /= np.maximum(count, 1)
    edges = np.empty(len(me.edges) * 2, np.int32)
    me.edges.foreach_get("vertices", edges)
    edges = edges.reshape(-1, 2)
    for _ in range(4):
        for m in (cap, hair):
            s = np.zeros_like(m)
            n = np.zeros_like(m)
            np.add.at(s, edges[:, 0], m[edges[:, 1]])
            np.add.at(s, edges[:, 1], m[edges[:, 0]])
            np.add.at(n, edges[:, 0], 1)
            np.add.at(n, edges[:, 1], 1)
            m[:] = (m + s) / (1 + n)
    attr = me.color_attributes.new("masks", "FLOAT_COLOR", "POINT")
    data = np.zeros((len(me.vertices), 4), np.float32)
    data[:, 0] = cap
    data[:, 1] = hair
    data[:, 3] = 1
    attr.data.foreach_set("color", data.ravel())
    return cap


def shorten_brim(head, cap):
    """A 1930s peaked cap: the long baseball brim cut back to a short, slightly lowered peak."""
    co = np.empty(len(head.data.vertices) * 3, np.float32)
    head.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    front = BRIM_ROOT
    brim = (cap > 0.5) & (co[:, 1] < front) & (co[:, 2] > BROW - 0.01)
    t = co[brim, 1] - front  # negative: how far out in front of the crown
    co[brim, 1] = front + t * 0.38
    co[brim, 2] -= (-t) * 0.2
    head.data.vertices.foreach_set("co", co.ravel())
    head.data.update()
    # The embroidered letters stand out of the crown: ironed flat, the seams kept soft.
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bm.verts.ensure_lookup_table()
    crown = [bm.verts[i] for i in np.nonzero((cap > 0.95) & (co[:, 1] > front - 0.002))[0]]
    for _ in range(12):
        bmesh.ops.smooth_vert(bm, verts=crown, factor=0.6, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.to_mesh(head.data)
    bm.free()
    print("TAXI_HEAD brim verts", int(brim.sum()), "crown verts", len(crown))


def extend_neck(head, axis):
    """A neck tube fitted just inside the scan's own neck and carried 8 cm down into the
    shirt collar. Where the hoodie hid his nape the tube is the skin under his hairline."""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(head.data)
    tree = BVHTree.FromBMesh(bm)
    ax = Vector((axis[0], axis[1], 0))
    sides = 64
    levels = [1.81, 1.83, 1.85, 1.87, 1.89]
    reach = np.full((len(levels), sides), np.nan)
    for i, z in enumerate(levels):
        for k in range(sides):
            a = 2 * math.pi * k / sides
            hit = tree.ray_cast(ax + Vector((0, 0, z)), Vector((math.sin(a), -math.cos(a), 0)), 0.16)
            if hit[0] is not None:
                reach[i, k] = (hit[0].xy - ax.xy).length
    # Where a height has no skin (the nape the hoodie hid), the nearest height above it does.
    for i in range(len(levels) - 2, -1, -1):
        gap = np.isnan(reach[i])
        reach[i, gap] = reach[i + 1, gap]
    for i in range(len(levels)):
        row = reach[i]
        if np.isnan(row).any():
            idx = np.arange(sides)
            ok = ~np.isnan(row)
            row[~ok] = np.interp(idx[~ok], idx[ok], row[ok], period=sides)
        reach[i] = np.convolve(np.r_[row[-2:], row, row[:2]], np.ones(5) / 5, "valid")
    masks = bm.verts.layers.float_color.get("masks")
    heights = [1.73, 1.77] + levels
    radii = [reach[0] * 0.95, reach[0] * 0.95] + [reach[i] * 0.94 - 0.002 for i in range(len(levels))]
    rings = []
    for z, rad in zip(heights, radii):
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            v = bm.verts.new(ax + Vector((math.sin(a) * rad[k], -math.cos(a) * rad[k], z)))
            v[masks] = (0, 0, 1, 1)
            ring.append(v)
        rings.append(ring)
    for lo, hi in zip(rings, rings[1:]):
        for k in range(sides):
            bm.faces.new((lo[k], lo[(k + 1) % sides], hi[(k + 1) % sides], hi[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(head.data)
    bm.free()
    print("TAXI_HEAD neck reach", np.round(reach[:, ::8], 3).tolist())


def roughness(head):
    """How glossy each part is, as a colour attribute baked into the roughness map: wet
    eyes, lips with a little shine, sweat on the nose and brow, matte hair and cotton cap."""
    me = head.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    masks = np.empty(len(me.vertices) * 4, np.float32)
    me.color_attributes["masks"].data.foreach_get("color", masks)
    masks = masks.reshape(-1, 4)
    r = np.full(len(co), 0.5, np.float32)
    front = co[:, 1] < -0.07
    oily = front & (co[:, 2] > 1.92) & (co[:, 2] < 2.01) & (np.abs(co[:, 0]) < 0.03)
    r[oily] = 0.42
    for ex in EYES_X:
        d = ((co[:, 0] - ex) / 0.0165) ** 2 + ((co[:, 2] - EYE_Z) / 0.0058) ** 2
        r[front & (d < 1)] = 0.1
    lips = front & (np.abs(co[:, 2] - MOUTH_Z) < 0.0065) & (co[:, 0] > -0.026) & (co[:, 0] < 0.031)
    r[lips] = 0.36
    r = r * (1 - masks[:, 1]) + 0.66 * masks[:, 1]
    r = r * (1 - masks[:, 0]) + 0.9 * masks[:, 0]
    attr = me.color_attributes.new("rough", "FLOAT_COLOR", "POINT")
    data = np.zeros((len(co), 4), np.float32)
    data[:, 0] = r
    data[:, 3] = 1
    attr.data.foreach_set("color", data.ravel())


def bake_material(head, image):
    """The scan's photo, browned where it is skin, with cotton twill where the cap was."""
    m = bpy.data.materials.new("bake_source")
    m.use_nodes = True
    nt = m.node_tree
    n, l = nt.nodes, nt.links
    bsdf = n["Principled BSDF"]
    tex = n.new("ShaderNodeTexImage")
    tex.image = image
    masks = n.new("ShaderNodeVertexColor")
    masks.layer_name = "masks"
    sep = n.new("ShaderNodeSeparateColor")
    l.new(masks.outputs["Color"], sep.inputs[0])
    # Sun-browned skin: deeper, warmer and less pink than the scan's indoor complexion.
    curve = n.new("ShaderNodeRGBCurve")
    for i, pts in enumerate([[(0, 0), (0.5, 0.36), (1, 0.8)],   # R
                             [(0, 0), (0.5, 0.25), (1, 0.66)],  # G
                             [(0, 0), (0.5, 0.17), (1, 0.52)]]):  # B
        c = curve.mapping.curves[i]
        for j, (x, y) in enumerate(pts):
            if j < len(c.points):
                c.points[j].location = (x, y)
            else:
                c.points.new(x, y)
    curve.mapping.update()
    l.new(tex.outputs["Color"], curve.inputs["Color"])
    # The neck carried down into the collar is plain neck skin, not stretched photo.
    neck = n.new("ShaderNodeMix")
    neck.data_type = "RGBA"
    l.new(sep.outputs[2], neck.inputs["Factor"])
    l.new(curve.outputs["Color"], neck.inputs[6])
    mottle = n.new("ShaderNodeTexNoise")
    mottle.inputs["Scale"].default_value = 90
    mottle.inputs["Detail"].default_value = 8
    tint = n.new("ShaderNodeMix")
    tint.data_type = "RGBA"
    tint.inputs[6].default_value = (0.15, 0.055, 0.025, 1)
    tint.inputs[7].default_value = (0.24, 0.095, 0.045, 1)
    l.new(mottle.outputs["Fac"], tint.inputs["Factor"])
    l.new(tint.outputs[2], neck.inputs[7])
    # Hair stays the photo's own black.
    hair = n.new("ShaderNodeMix")
    hair.data_type = "RGBA"
    l.new(sep.outputs[1], hair.inputs["Factor"])
    l.new(neck.outputs[2], hair.inputs[6])
    l.new(tex.outputs["Color"], hair.inputs[7])
    # Worn dark twill for the cap, laid on by box projection in the head's own space.
    coord = n.new("ShaderNodeTexCoord")
    mapping = n.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (9, 9, 9)
    l.new(coord.outputs["Object"], mapping.inputs["Vector"])
    linen = n.new("ShaderNodeTexImage")
    linen.image = bpy.data.images.load(os.path.join(LINEN, "rough_linen_BC.jpg"))
    linen.projection = "BOX"
    linen.projection_blend = 0.3
    l.new(mapping.outputs["Vector"], linen.inputs["Vector"])
    dye = n.new("ShaderNodeMix")
    dye.data_type = "RGBA"
    dye.blend_type = "MULTIPLY"
    dye.inputs["Factor"].default_value = 1
    dye.inputs[7].default_value = (0.17, 0.14, 0.11, 1)
    l.new(linen.outputs["Color"], dye.inputs[6])
    # Sweat and grime darken the band where it sits on his brow.
    sweat = n.new("ShaderNodeMix")
    sweat.data_type = "RGBA"
    sweat.blend_type = "MULTIPLY"
    sep_xyz = n.new("ShaderNodeSeparateXYZ")
    l.new(coord.outputs["Object"], sep_xyz.inputs[0])
    band = n.new("ShaderNodeMapRange")
    band.inputs["From Min"].default_value = BROW + 0.035
    band.inputs["From Max"].default_value = BROW
    l.new(sep_xyz.outputs["Z"], band.inputs["Value"])
    grime = n.new("ShaderNodeMath")
    grime.operation = "MULTIPLY"
    grime.inputs[1].default_value = 0.45
    l.new(band.outputs[0], grime.inputs[0])
    l.new(grime.outputs[0], sweat.inputs["Factor"])
    l.new(dye.outputs[2], sweat.inputs[6])
    sweat.inputs[7].default_value = (0.45, 0.4, 0.33, 1)
    cap = n.new("ShaderNodeMix")
    cap.data_type = "RGBA"
    l.new(sep.outputs[0], cap.inputs["Factor"])
    l.new(hair.outputs[2], cap.inputs[6])
    l.new(sweat.outputs[2], cap.inputs[7])
    l.new(cap.outputs[2], bsdf.inputs["Base Color"])
    rough = n.new("ShaderNodeVertexColor")
    rough.layer_name = "rough"
    rsep = n.new("ShaderNodeSeparateColor")
    l.new(rough.outputs["Color"], rsep.inputs[0])
    l.new(rsep.outputs[0], bsdf.inputs["Roughness"])
    head.data.materials.clear()
    head.data.materials.append(m)


def weigh_islands(lo):
    """Texture where it is looked at: the face's islands get about five times the area,
    the ears three, the cap and the neck in the collar far less."""
    from bpy_extras.bmesh_utils import bmesh_linked_uv_islands
    bm = bmesh.new()
    bm.from_mesh(lo.data)
    uv = bm.loops.layers.uv.active
    for island in bmesh_linked_uv_islands(bm, uv):
        c = sum((f.calc_center_median() for f in island), Vector()) / len(island)
        if c.y < -0.06 and 1.86 < c.z < 2.02:
            k = 2.3
        elif abs(c.x) > 0.06 and -0.03 < c.y < 0.045 and 1.89 < c.z < 2.0:
            k = 1.8
        elif c.z < 1.845:
            k = 0.35
        elif c.z > BROW + 0.01 or c.y < BRIM_ROOT:
            k = 0.55
        else:
            k = 1.0
        pts = [l[uv].uv for f in island for l in f.loops]
        mid = sum(pts, Vector((0, 0))) / len(pts)
        for f in island:
            for l in f.loops:
                l[uv].uv = mid + (l[uv].uv - mid) * k
    bm.to_mesh(lo.data)
    bm.free()


def low_copy(head):
    lo = head.copy()
    lo.data = head.data.copy()
    lo.name = lo.data.name = "taxi_driver_head_scan"
    bpy.context.collection.objects.link(lo)
    for name in ("masks", "rough"):
        lo.data.color_attributes.remove(lo.data.color_attributes[name])
    # Ears, eyes, nose and lips keep their scanned shape: a coarse ear bakes torn, its
    # rays reaching the cap behind it.
    co = np.empty(len(lo.data.vertices) * 3, np.float32)
    lo.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    ears = (np.abs(co[:, 0]) > 0.06) & (co[:, 1] > -0.03) & (co[:, 1] < 0.045) & (co[:, 2] > 1.89) & (co[:, 2] < 2.0)
    face = (co[:, 1] < -0.07) & (co[:, 2] > 1.875) & (co[:, 2] < 1.985) & (np.abs(co[:, 0]) < 0.06)
    group = lo.vertex_groups.new(name="detail")
    for i in np.nonzero(ears)[0]:
        group.add([int(i)], 1.0, "REPLACE")
    for i in np.nonzero(face & ~ears)[0]:
        group.add([int(i)], 0.6, "REPLACE")
    mod = lo.modifiers.new("cap", "DECIMATE")
    mod.ratio = FACES / len(lo.data.polygons)
    mod.use_collapse_triangulate = True
    mod.vertex_group = "detail"
    mod.invert_vertex_group = True
    mod.vertex_group_factor = 12
    bpy.context.view_layer.objects.active = lo
    bpy.ops.object.modifier_apply(modifier=mod.name)
    # Collapsing leaves a few slivers, flipped triangles and pinholes (one showed as a dark
    # wedge on his jaw): dissolved, turned outward and closed again.
    bm = bmesh.new()
    bm.from_mesh(lo.data)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=0.0002)
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary and min(v.co.z for v in e.verts) > 1.8], sides=40)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bm.to_mesh(lo.data)
    bm.free()
    while lo.data.uv_layers:
        lo.data.uv_layers.remove(lo.data.uv_layers[0])
    lo.data.uv_layers.new(name="UVMap")
    bpy.ops.object.select_all(action="DESELECT")
    lo.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.6)
    bpy.ops.object.mode_set(mode="OBJECT")
    weigh_islands(lo)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, scale=True, margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    for p in lo.data.polygons:
        p.use_smooth = True
    print("TAXI_HEAD low faces", len(lo.data.polygons))
    return lo


def fill_gaps(image, passes=24):
    w, h = image.size
    px = np.empty(w * h * 4, np.float32)
    image.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    rgb = px[..., :3]
    have = rgb.sum(-1) > 0.012
    for _ in range(passes):
        if have.all():
            break
        acc = np.zeros_like(rgb)
        n = np.zeros((h, w), np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            m = np.roll(have, (dy, dx), (0, 1))
            acc += np.roll(rgb, (dy, dx), (0, 1)) * m[..., None]
            n += m
        grow = (~have) & (n > 0)
        rgb[grow] = acc[grow] / n[grow, None]
        have = have | grow
    px[..., 3] = 1
    image.pixels.foreach_set(px.ravel())


def bake(hi, lo):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 4
    colour = bpy.data.images.new("T_taxi_driver_head_BC", 4096, 4096)
    normal = bpy.data.images.new("T_taxi_driver_head_N", 2048, 2048)
    normal.colorspace_settings.name = "Non-Color"
    rough = bpy.data.images.new("T_taxi_driver_head_R", 1024, 1024)
    rough.colorspace_settings.name = "Non-Color"
    m = bpy.data.materials.new("M_taxi_driver_head_scan")
    m.use_nodes = True
    nt = m.node_tree
    target = nt.nodes.new("ShaderNodeTexImage")
    lo.data.materials.clear()
    lo.data.materials.append(m)
    bpy.ops.object.select_all(action="DESELECT")
    hi.select_set(True)
    lo.select_set(True)
    bpy.context.view_layer.objects.active = lo
    bake = sc.render.bake
    bake.use_selected_to_active = True
    # Short rays: the ear is thinner than a longer cage, and would bake its own back.
    bake.cage_extrusion = 0.003
    bake.max_ray_distance = 0.01
    bake.margin = 16
    bake.margin_type = "EXTEND"
    for image, kind in [(colour, "DIFFUSE"), (normal, "NORMAL"), (rough, "ROUGHNESS")]:
        target.image = image
        nt.nodes.active = target
        if kind == "DIFFUSE":
            bake.use_pass_direct = False
            bake.use_pass_indirect = False
            bake.use_pass_color = True
        bpy.ops.object.bake(type=kind)
        print("TAXI_HEAD baked", kind)
    # Texels a ray missed (a pinhole in the scan) and the black around every UV island
    # are filled from their neighbours, so no hole shows and no seam darkens in the mips.
    for image in (colour, normal, rough):
        fill_gaps(image)
    folder = tempfile.mkdtemp()
    for image, ext in [(colour, "jpg"), (normal, "png"), (rough, "png")]:
        image.filepath_raw = os.path.join(folder, f"{image.name}.{ext}")
        image.file_format = "JPEG" if ext == "jpg" else "PNG"
        if ext == "jpg":
            bpy.context.scene.render.image_settings.quality = 92
        image.save()
        image.source = "FILE"
        image.reload()
    # The glTF material: photo colour, baked relief, matte skin.
    nt.nodes.remove(target)
    bsdf = nt.nodes["Principled BSDF"]
    bc = nt.nodes.new("ShaderNodeTexImage")
    bc.image = colour
    nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
    nm = nt.nodes.new("ShaderNodeTexImage")
    nm.image = normal
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(nm.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    rm = nt.nodes.new("ShaderNodeTexImage")
    rm.image = rough
    # glTF reads roughness from green: the grey map's green channel is the roughness.
    rs = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(rm.outputs["Color"], rs.inputs[0])
    nt.links.new(rs.outputs[1], bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = 0
    return colour


def export(lo):
    for o in list(bpy.data.objects):
        if o is not lo:
            bpy.data.objects.remove(o)
    lo["credit"] = f"{CREDIT['title']} by {CREDIT['author']} ({CREDIT['url']}), {CREDIT['license']}"
    for k, v in CREDIT.items():
        lo[k] = v
    bpy.context.scene["copyright"] = lo["credit"]
    bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_extras=True,
                              export_copyright=lo["credit"], export_image_format="AUTO",
                              export_yup=True, export_apply=True, export_attributes=False)
    print("TAXI_HEAD wrote", OUT, os.path.getsize(OUT))


def debug_render(objs, name, colour="TEXTURE"):
    if not DEBUG:
        return
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = colour
    sc.render.resolution_x, sc.render.resolution_y = 600, 760
    cam = bpy.data.objects.get("dbg_cam") or bpy.data.objects.new("dbg_cam", bpy.data.cameras.new("dbg_cam"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens = 85
    centre = Vector((0, 0, 1.97))
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o not in objs
    for view, d in [("front", (0, -1, 0)), ("side", (1, 0, 0.05)), ("three", (-0.75, -0.65, 0.1)), ("back", (-0.6, 1, 0.15))]:
        cam.location = centre + Vector(d).normalized() * 1.25
        cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(DEBUG, f"{name}_{view}.png")
        bpy.ops.render.render(write_still=True)


# Heights on this scan (metres): the cap's lower edge above his brow, the crown above
# which nothing is his own, and the front of the crown where the brim starts.
BROW = 2.015
CROWN = 2.075
BRIM_ROOT = -0.104
# His eyes (centre heights and across), mouth line, and the jaw's hinge before his ear.
EYES_X = (-0.040, 0.034)
EYE_Z = 1.9695
MOUTH_Z = 1.890

head = load()
px = small_pixels(photo(head))
kind, axis = classify(head, px)
head.data.attributes.new("kind", "INT", "FACE").data.foreach_set("value", kind.astype(np.int32))
keep(head, kind)
cap = vertex_masks(head)
shorten_brim(head, cap)
extend_neck(head, axis)
roughness(head)
image = photo(head)
bake_material(head, image)
if DEBUG:
    debug_render([head], "mask", "VERTEX")
    if "--stop" in args:
        sys.exit(0)
lo = low_copy(head)
bake(head, lo)
debug_render([lo], "lo")
export(lo)
