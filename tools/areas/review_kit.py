"""Shared helpers for the user's second review of November 24, 2026 (house_review.py,
village_review.py): library scans placed as linked copies, generated textures (the
scanned lemon peel turned to an orange's, blood that reads as blood), soft decals, cloth
settled by Blender's solver, candle flames and their lights.

Blender metres, X east, Y north, Z up.
"""
import math
import os
import re

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from kit import LIB, ROOT

TEX = os.path.join(ROOT, "art-source", "textures", "ep1")
CANDLE = (1.0, 0.52, 0.2)


# ------------------------------------------------------------------ scene helpers


def vl():
    bpy.context.view_layer.update()


def tree(o):
    return [o] + list(o.children_recursive)


def box_of(objs):
    pts = []
    for o in objs:
        if o is None or o.type != "MESH" or not o.data.vertices:
            continue
        pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    if not pts:
        return None
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def delete(objs):
    """Deletes the objects and everything parented under them; returns how many."""
    gone = set()
    for o in list(objs):
        if o is None or o.name not in bpy.data.objects:
            continue
        for c in tree(o):
            gone.add(c.name)
    for name in gone:
        o = bpy.data.objects.get(name)
        if o is not None:
            bpy.data.objects.remove(o, do_unlink=True)
    return len(gone)


def roots(pattern, colls=None):
    """Top-level objects whose names match `pattern` (a compiled regex)."""
    out = []
    for o in bpy.data.objects:
        if o.parent is not None or not pattern.match(o.name):
            continue
        if any(c.name.startswith("_") or c.name == "nature_templates" for c in o.users_collection):
            continue
        if colls and not any(c.name in colls for c in o.users_collection):
            continue
        out.append(o)
    return out


def ray_down(x, y, z_from, ignore=(), distance=6.0):
    """The first visible surface under (x, y) from z_from (colliders and markers skipped)."""
    sc = bpy.context.scene
    deps = bpy.context.evaluated_depsgraph_get()
    o = Vector((x, y, z_from))
    for _ in range(12):
        hit, loc, nrm, idx, obj, mat = sc.ray_cast(deps, o, Vector((0, 0, -1)), distance=distance)
        if not hit:
            return None
        if obj.name.startswith(("col_", "light_", "marker_", "_")) or obj in ignore or obj.hide_render:
            o = loc - Vector((0, 0, 0.002))
            continue
        return loc.z
    return None


def collection(name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


# ------------------------------------------------------------------ library scans


class Scans:
    """Poly Haven scans imported once each into the hidden `_review_protos` collection
    (collections starting with "_" are not exported) and placed as linked copies: every
    copy shares its piece's mesh, so a plate of oranges is one mesh drawn six times."""

    def __init__(self):
        self.coll = bpy.data.collections.get("_review_protos")
        if self.coll is None:
            self.coll = bpy.data.collections.new("_review_protos")
            bpy.context.scene.collection.children.link(self.coll)
        self.coll.hide_render = True
        self.cache = {}

    def pieces(self, model_id, tris=None, retex=None):
        """{piece name: (mesh, size)} for a library model: each mesh's transform applied, its
        origin moved to the middle of its foot, decimated to about `tris` triangles.
        `retex(material)` may replace a piece's material (the orange from the lemon)."""
        key = (model_id, tris, retex.__name__ if retex else None)
        if key in self.cache:
            return self.cache[key]
        path = os.path.join(LIB, "models", model_id, f"{model_id}.gltf")
        if not os.path.exists(path):
            path = os.path.join(LIB, "scans", f"{model_id}.glb")       # the project's own scans
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=path)
        new = [o for o in bpy.data.objects if o not in before]
        vl()
        out = {}
        deps = bpy.context.evaluated_depsgraph_get()
        for o in new:
            if o.type != "MESH":
                continue
            if tris and len(o.data.polygons) > tris:
                mod = o.modifiers.new("dec", "DECIMATE")
                mod.ratio = max(0.02, tris / max(1, len(o.data.polygons) * 1.0))
                deps = bpy.context.evaluated_depsgraph_get()
                me = bpy.data.meshes.new_from_object(o.evaluated_get(deps))
            else:
                me = o.data.copy()
            me.transform(o.matrix_world)
            vs = [v.co for v in me.vertices]
            lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
            hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
            me.transform(Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
            me.name = f"scan_{model_id}_{o.name}"
            if retex:
                for i, mat in enumerate(me.materials):
                    me.materials[i] = retex(mat)
            out[re.sub(r"\.\d+$", "", o.name)] = (me, hi - lo)
        for o in new:
            bpy.data.objects.remove(o, do_unlink=True)
        self.cache[key] = out
        return out

    def put(self, coll, model_id, piece, name, xf, size=None, along=None, tris=None, retex=None):
        """A copy of `piece` (a name, or None for the model's first) placed by matrix `xf`
        (its foot at xf's origin). `size` scales its largest side (or its `along` axis:
        0 x, 1 y, 2 z) to that many metres."""
        ps = self.pieces(model_id, tris, retex)
        if piece is None:
            piece = sorted(ps)[0]
        me, dims = ps[piece]
        o = bpy.data.objects.new(name, me)
        coll.objects.link(o)
        k = 1.0
        if size:
            k = size / max(1e-4, dims[along] if along is not None else max(dims))
        o.matrix_world = xf @ Matrix.Scale(k, 4)
        return o


def settle(o, ignore=(), drop=0.0):
    """Stands an object on whatever is under its middle (ray down from just above it)."""
    vl()
    bb = box_of([o])
    if bb is None:
        return o
    c = (bb[0] + bb[1]) / 2
    z = ray_down(c.x, c.y, bb[1].z + 0.01, ignore=set(ignore) | {o})
    if z is not None:
        o.location.z += z - bb[0].z - drop
    vl()
    return o


# ------------------------------------------------------------------ images


def save_png(name, rgba):
    """Writes a float RGBA array (rows top to bottom, 0-1, sRGB values) to the textures."""
    h, w = rgba.shape[:2]
    path = os.path.join(TEX, f"{name}.png")
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.colorspace_settings.name = "sRGB"
    img.pixels.foreach_set(np.ascontiguousarray(np.clip(rgba[::-1], 0, 1), dtype=np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return path


def load_rgba(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1].copy()
    bpy.data.images.remove(img)
    return a


def noise(shape, rng, scales=((6, 0.45), (18, 0.3), (60, 0.25))):
    """Smooth value noise, 0-1, as a sum of upsampled random grids."""
    h, w = shape
    out = np.zeros(shape, dtype=np.float32)
    ys = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    xs = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    for n, amp in scales:
        g = rng.random((n + 2, n + 2)).astype(np.float32)
        fy, fx = ys * n, xs * n
        iy, ix = np.floor(fy).astype(int), np.floor(fx).astype(int)
        ty, tx = fy - iy, fx - ix
        ty, tx = ty * ty * (3 - 2 * ty), tx * tx * (3 - 2 * tx)
        a = g[iy, ix] * (1 - tx) + g[iy, ix + 1] * tx
        b = g[iy + 1, ix] * (1 - tx) + g[iy + 1, ix + 1] * tx
        out += amp * (a * (1 - ty) + b * ty)
    return out / sum(a for _, a in scales)


def blur(a, r):
    """Box blur, r pixels (twice: close to a gaussian)."""
    if r < 1:
        return a
    for _ in range(2):
        for axis in (0, 1):
            c = np.cumsum(np.pad(a, [(r + 1, r) if i == axis else (0, 0) for i in range(a.ndim)], mode="edge"), axis=axis)
            hi = np.take(c, np.arange(2 * r + 1, c.shape[axis]), axis=axis)
            lo = np.take(c, np.arange(0, c.shape[axis] - 2 * r - 1), axis=axis)
            a = (hi - lo) / (2 * r + 1)
    return a


def orange_peel():
    """The scanned lemon's peel turned to a ripe orange's (mandarins on Khmer altars):
    hue down from lemon yellow to orange, a little greener at the stalk end, the scan's
    pores and blemishes kept."""
    path = os.path.join(TEX, "T_ep1_orange_scan_BC.png")
    if os.path.exists(path):
        return path
    src = load_rgba(os.path.join(LIB, "models", "lemon", "textures", "lemon_diff_1k.jpg"))
    rgb = src[..., :3]
    L = 0.3 * rgb[..., 0] + 0.59 * rgb[..., 1] + 0.11 * rgb[..., 2]
    rng = np.random.default_rng(1101)
    n = noise(L.shape, rng, ((5, 0.6), (22, 0.4)))
    base = np.array([0.96, 0.6, 0.15])
    deep = np.array([0.86, 0.43, 0.08])
    tone = base[None, None] * (1 - n[..., None] * 0.5) + deep[None, None] * (n[..., None] * 0.5)
    out = np.clip(tone * (L[..., None] / max(1e-3, float(L.mean()))) ** 1.1, 0, 1)
    return save_png("T_ep1_orange_scan_BC", np.dstack([out, np.ones_like(L)]))


def _hand(h, w, cx, cy, s, rng, spread=1.0):
    """A hand's print mask (0-1) at (cx, cy) pixels, palm `s` pixels across, fingers up."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    def capsule(x0, y0, x1, y1, r):
        px, py = xx - x0, yy - y0
        dx, dy = x1 - x0, y1 - y0
        t = np.clip((px * dx + py * dy) / max(1e-3, dx * dx + dy * dy), 0, 1)
        d = np.hypot(px - t * dx, py - t * dy)
        return np.clip((r - d) / (r * 0.35), 0, 1)
    palm = np.clip(1 - ((xx - cx) / (s * 0.5)) ** 2 - ((yy - cy) / (s * 0.58)) ** 2, 0, 1) ** 0.35
    m = palm.copy()
    fingers = [(-0.36, 0.78, 0.13), (-0.12, 0.92, 0.14), (0.12, 0.88, 0.135), (0.34, 0.7, 0.12)]
    for k, (fx, fl, fr) in enumerate(fingers):
        a = (fx * 0.35 + rng.normal(0, 0.04)) * spread
        x0, y0 = cx + fx * s, cy - s * 0.48
        x1, y1 = x0 + math.sin(a) * fl * s, y0 - math.cos(a) * fl * s
        f = capsule(x0, y0, x1, y1, fr * s)
        # The pad at each tip prints hardest; the joints' creases leave gaps.
        for j in (0.33, 0.66):
            jx, jy = x0 + (x1 - x0) * j, y0 + (y1 - y0) * j
            along = (xx - jx) * math.sin(a) - (yy - jy) * math.cos(a)
            f *= 1 - 0.65 * np.exp(-(along / (0.012 * s)) ** 2)
        m = np.maximum(m, f)
    tx0, ty0 = cx - s * 0.5, cy + s * 0.05
    m = np.maximum(m, capsule(tx0, ty0, tx0 - s * 0.32, ty0 - s * 0.42, s * 0.13))
    # The palm's creases print as thin gaps.
    for (a0, b0, a1, b1) in ((-0.45, -0.12, 0.4, -0.25), (-0.5, 0.08, 0.15, -0.05), (-0.1, 0.45, -0.25, -0.2)):
        line = capsule(cx + a0 * s, cy + b0 * s, cx + a1 * s, cy + b1 * s, s * 0.018)
        m *= 1 - 0.7 * line
    return m


def blood_rgba(mask, rng, wet=0.5):
    """Blood over a mask: dark where it lay thick, thinner and redder at the edges,
    drying brown at its rims, its alpha soft (a soaked print, not a cut-out)."""
    h, w = mask.shape
    n1 = noise((h, w), rng, ((8, 0.4), (30, 0.35), (120, 0.25)))
    n2 = noise((h, w), rng, ((50, 0.5), (200, 0.5)))
    density = np.clip(mask * (0.55 + 0.75 * n1) - 0.12 * (n2 > 0.62), 0, 1)
    thick = blur(density, 2)
    rim = np.clip(density - blur(density, 6), 0, 1) * 2.0
    fresh = np.array([0.36, 0.035, 0.025])
    dark = np.array([0.13, 0.012, 0.01])
    dry = np.array([0.24, 0.1, 0.06])
    col = fresh[None, None] * (1 - thick[..., None]) + dark[None, None] * thick[..., None]
    col = col * (1 - rim[..., None] * (1 - wet) * 0.6) + dry[None, None] * rim[..., None] * (1 - wet) * 0.6
    alpha = np.clip(density ** 0.8 * 1.15, 0, 0.97)
    return np.dstack([col, alpha])


def blood_handprint():
    """Two hands dragged down a cloth in blood: the prints, the smear under them, runs."""
    path = os.path.join(TEX, "T_ep1_blood_hands_BC.png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(2402)
    h, w = 1024, 512
    m = _hand(h, w, 256, 330, 230, rng)
    # Dragged: the print smeared down as the hand slid, thinning out.
    drag = np.zeros_like(m)
    for k in range(1, 90):
        f = (1 - k / 90) ** 1.6 * 0.5
        drag = np.maximum(drag, np.roll(m, k * 4, axis=0) * f * (rng.uniform(0.7, 1.0)))
    drag[:300] = 0
    streak = noise((h, w), rng, ((3, 0.2), (90, 0.8)))
    drag *= np.clip((streak - 0.25) * 2.2, 0, 1) ** 0.7
    m = np.maximum(m, drag)
    # Runs from the heaviest places, beaded at their ends.
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    for k in range(7):
        x0 = rng.uniform(150, 370)
        y0 = rng.uniform(380, 640)
        L = rng.uniform(90, 330)
        wd = rng.uniform(2.0, 4.5)
        wob = rng.uniform(0, 6)
        line = np.exp(-((xx - x0 - 3 * np.sin(yy / 40 + wob)) / wd) ** 2) * ((yy > y0) & (yy < y0 + L))
        bead = np.exp(-(((xx - x0) / (wd * 1.8)) ** 2 + ((yy - y0 - L) / (wd * 2.4)) ** 2))
        m = np.maximum(m, line * 0.85 + bead)
    return save_png("T_ep1_blood_hands_BC", blood_rgba(np.clip(m, 0, 1), rng, wet=0.35))


def blood_pool():
    """A pool of dark blood soaked into the earth and the mat: a thick glossy middle, the
    edge broken into lobes and splashes, a brown rim where it dried first."""
    path = os.path.join(TEX, "T_ep1_blood_pool_BC.png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(2403)
    n = 1024
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) / n - 0.5
    r = np.hypot(xx * 1.15, yy)
    lobes = noise((n, n), rng, ((4, 0.6), (11, 0.4)))
    m = np.clip((0.36 + 0.12 * (lobes - 0.5) * 2 - r) * 14, 0, 1)
    for k in range(26):
        a = rng.uniform(0, math.tau)
        d = rng.uniform(0.3, 0.46)
        s = rng.uniform(0.004, 0.016)
        m = np.maximum(m, np.exp(-(((xx - math.cos(a) * d) ** 2 + (yy - math.sin(a) * d) ** 2) / s ** 2)))
    return save_png("T_ep1_blood_pool_BC", blood_rgba(m, rng, wet=0.7))


def blood_runs():
    """Blood soaked from the top edge of a cloth and run down it in uneven threads."""
    path = os.path.join(TEX, "T_ep1_blood_runs_BC.png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(2404)
    h, w = 512, 1024
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    band = noise((h, w), rng, ((6, 0.7), (40, 0.3)))
    m = np.clip(((60 + 70 * band) - yy) / 30, 0, 1)
    for k in range(34):
        x0 = rng.uniform(0, w)
        L = rng.uniform(80, 470)
        wd = rng.uniform(1.6, 5.0)
        wob = rng.uniform(0, 6)
        line = np.exp(-((xx - x0 - 4 * np.sin(yy / 50 + wob)) / wd) ** 2) * (yy < 40 + L)
        bead = np.exp(-(((xx - x0 - 4 * math.sin((40 + L) / 50 + wob)) / (wd * 1.7)) ** 2 + ((yy - 40 - L) / (wd * 2.3)) ** 2))
        m = np.maximum(m, line * rng.uniform(0.6, 0.95) + bead)
    return save_png("T_ep1_blood_runs_BC", blood_rgba(np.clip(m, 0, 1), rng, wet=0.3))


def soft_material(name, path, rough=0.4, colour_scale=None):
    """A decal with soft edges: its colour from the image, its alpha straight into the
    shader (glTF alphaMode BLEND), both faces, no shadow."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_backface_culling = False
    mat.blend_method = "BLEND"
    try:
        mat.surface_render_method = "BLENDED"
    except Exception:
        pass
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path, check_existing=True)
    tex.image.alpha_mode = "STRAIGHT"
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = rough
    mat["tile"] = 0.0
    return mat


def decal(coll, name, mat, corners, uv=((0, 0), (1, 0), (1, 1), (0, 1)), n=1):
    """A quad decal from four corners (counter-clockwise seen from its front), subdivided
    `n` times along each side so it can follow a curve."""
    verts, faces, uvs = [], [], []
    c = [Vector(p) for p in corners]
    for j in range(n + 1):
        for i in range(n + 1):
            u, v = i / n, j / n
            p = (c[0] * (1 - u) + c[1] * u) * (1 - v) + (c[3] * (1 - u) + c[2] * u) * v
            verts.append(tuple(p))
            uvs.append((uv[0][0] + (uv[1][0] - uv[0][0]) * u, uv[0][1] + (uv[3][1] - uv[0][1]) * v))
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i
            faces.append((a, a + 1, a + n + 2, a + n + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    layer = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            layer.data[li].uv = uvs[me.loops[li].vertex_index]
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def press(o, target, direction, lift=0.003):
    """Moves each vertex of decal `o` along `direction` onto `target`'s surface (rays from
    behind it), `lift` short of it: a print that follows a cloth's folds. Faces with a
    vertex whose ray missed (past the surface's edge) are cut away, so nothing of the
    decal is left standing in the air."""
    import bmesh
    inv = target.matrix_world.inverted()
    d_local = (inv.to_3x3() @ direction).normalized()
    missed = set()
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        ok_, loc, nrm, idx = target.ray_cast(inv @ (w - direction * 0.5), d_local, distance=2.0)
        if ok_:
            v.co = o.matrix_world.inverted() @ (target.matrix_world @ loc - direction * lift)
        else:
            missed.add(v.index)
    o.data.update()
    if missed:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.verts[i] for i in missed], context="VERTS")
        bm.to_mesh(o.data)
        bm.free()
        o.data.update()
    if not o.data.polygons:
        bpy.data.objects.remove(o, do_unlink=True)
        return None
    return o


def section(objs, z0, z1, keep=lambda p: True):
    """The (x0, x1, y0, y1) footprint of the objects' vertices between heights z0 and z1
    that `keep` accepts: a post's or a pillar's cross-section there."""
    pts = []
    for o in objs:
        if o is None or o.type != "MESH":
            continue
        mw = o.matrix_world
        pts += [mw @ v.co for v in o.data.vertices]
    sel = [p for p in pts if z0 <= p.z <= z1 and keep(p)]
    if not sel:
        return None
    return (min(p.x for p in sel), max(p.x for p in sel), min(p.y for p in sel), max(p.y for p in sel))


def wrap(b, mat, sec, z, rng, width=0.022, tail=0.0, gap=0.006, side=(1, 0)):
    """A strip of cloth tied round a post's cross-section `sec` at height z (a band hugging
    its four faces), its end hanging `tail` metres down the face on `side` (+x, -y...)."""
    x0, x1, y0, y1 = sec
    x0, x1, y0, y1 = x0 - gap, x1 + gap, y0 - gap, y1 + gap
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    pts = []
    for (ax, ay), (bx, by) in zip(corners, corners[1:]):
        for t in np.linspace(0, 1, 5, endpoint=False):
            pts.append((ax + (bx - ax) * t, ay + (by - ay) * t, z + rng.normal(0, 0.003)))
    pts.append(pts[0])
    b.tube(mat, pts, width / 2, sides=4)
    if tail > 0:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        fx = x1 + 0.003 if side[0] > 0 else (x0 - 0.003 if side[0] < 0 else cx)
        fy = y1 + 0.003 if side[1] > 0 else (y0 - 0.003 if side[1] < 0 else cy)
        if side[0] == 0:
            fx += rng.uniform(-0.3, 0.3) * (x1 - x0)
        else:
            fy += rng.uniform(-0.3, 0.3) * (y1 - y0)
        down = [(fx, fy, z), (fx + 0.004 * side[0], fy + 0.004 * side[1], z - tail * 0.5), (fx + 0.008 * side[0], fy + 0.008 * side[1], z - tail)]
        b.sweep(mat, down, Vector((side[0], side[1], 0)) if any(side) else Vector((1, 0, 0)), [width * 1.3, width * 1.1, width * 0.8], 0.0015)


def ground_decal(coll, name, mat, surface, cx, cy, w, h, angle, lift=0.004, n=6):
    """A decal lying on uneven ground: each vertex dropped onto `surface(x, y)`."""
    o = decal(coll, name, mat, [(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)], n=n)
    c, s = math.cos(angle), math.sin(angle)
    for v in o.data.vertices:
        x, y = cx + c * v.co.x - s * v.co.y, cy + s * v.co.x + c * v.co.y
        v.co = (x, y, surface(x, y) + lift)
    o.data.update()
    return o


# ------------------------------------------------------------------ cloth


def cloth_grid(name, coll, mat, corner, u_axis, v_axis, nu, nv, uv_scale=(1.0, 1.0)):
    """A flat grid of quads from `corner` along u_axis and v_axis (Vectors, full length)."""
    verts, faces, uvs = [], [], []
    for j in range(nv + 1):
        for i in range(nu + 1):
            verts.append(tuple(Vector(corner) + u_axis * (i / nu) + v_axis * (j / nv)))
            uvs.append((i / nu * uv_scale[0], j / nv * uv_scale[1]))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            faces.append((a, a + 1, a + nu + 2, a + nu + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    layer = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            layer.data[li].uv = uvs[me.loops[li].vertex_index]
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def simulate_cloth(o, pinned, colliders=(), frames=60, mass=0.15, bending=0.5, shrink=0.0, wind=None, quality=8):
    """Runs Blender's cloth solver on `o` (vertex indices `pinned` held still) over
    `colliders` (objects given a collision modifier for the run) and keeps frame `frames`
    as plain geometry. `wind` (strength, direction Vector) adds a steady breeze."""
    sc = bpy.context.scene
    grp = o.vertex_groups.new(name="pin")
    if pinned:
        grp.add(list(pinned), 1.0, "REPLACE")
    mod = o.modifiers.new("cloth", "CLOTH")
    s = mod.settings
    s.quality = quality
    s.mass = mass
    s.bending_stiffness = bending
    s.tension_stiffness = 15
    s.compression_stiffness = 15
    s.shrink_min = shrink
    s.vertex_group_mass = "pin"
    mod.collision_settings.use_self_collision = False
    mod.collision_settings.distance_min = 0.004
    mod.point_cache.frame_start = 1
    mod.point_cache.frame_end = frames
    added = []
    for c in colliders:
        if not any(m.type == "COLLISION" for m in c.modifiers):
            m = c.modifiers.new("collision", "COLLISION")
            added.append((c, m))
            c.collision.thickness_outer = 0.006
            c.collision.cloth_friction = 5
    field = None
    if wind:
        strength, direction = wind
        field = bpy.data.objects.new(f"_{o.name}_wind", None)
        bpy.context.scene.collection.objects.link(field)
        bpy.context.view_layer.objects.active = field
        field.field.type = "WIND"
        field.field.strength = strength
        field.field.noise = 0.6
        field.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    f0, f1 = sc.frame_start, sc.frame_end
    sc.frame_start, sc.frame_end = 1, frames
    for f in range(1, frames + 1):
        sc.frame_set(f)
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(deps))
    old = o.data
    o.modifiers.clear()
    o.data = me
    me.name = o.name
    bpy.data.meshes.remove(old)
    o.vertex_groups.clear()
    for c, m in added:
        c.modifiers.remove(m)
    if field:
        bpy.data.objects.remove(field, do_unlink=True)
    sc.frame_start, sc.frame_end = f0, f1
    sc.frame_set(1)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def box_drape(name, coll, mat, rect, top, floor, centre, size, rng, nu=48, nv=36, rumple=0.025):
    """A cloth thrown over a box (rect = x0, x1, y0, y1; its top at `top`): lying on the
    top with soft ripples, falling down every side it overhangs in vertical folds, flaring
    a little, and lying on the floor where it reaches it. Deterministic (no solver)."""
    x0, x1, y0, y1 = rect
    cx, cy = centre
    sx, sy = size
    ph = rng.uniform(0, 6, 6)
    verts, faces, uvs = [], [], []
    for j in range(nv + 1):
        for i in range(nu + 1):
            u, v = i / nu, j / nv
            px, py = cx + (u - 0.5) * sx, cy + (v - 0.5) * sy
            ox = max(0.0, x0 - px, px - x1)
            oy = max(0.0, y0 - py, py - y1)
            nx = -1 if px < x0 else (1 if px > x1 else 0)
            ny = -1 if py < y0 else (1 if py > y1 else 0)
            qx = min(max(px, x0), x1)
            qy = min(max(py, y0), y1)
            d = math.hypot(ox, oy)
            ripple = rumple * (0.5 * math.sin(px * 7 + ph[0]) * math.sin(py * 9 + ph[1]) + 0.35 * math.sin(px * 17 + py * 5 + ph[2]))
            if d == 0:
                p = Vector((px, py, top + 0.004 + max(0.0, ripple)))
            else:
                drop = top - d
                fold = 0.035 * min(1.0, d * 3) * (math.sin((qx * 23 + ph[3]) if ny else (qy * 23 + ph[4])) + 0.4 * math.sin((qx if ny else qy) * 57 + ph[5]))
                out = Vector((nx, ny, 0)).normalized() if (nx or ny) else Vector((0, 0, 0))
                flare = 0.06 * d + fold
                if drop > floor + 0.004:
                    p = Vector((qx, qy, drop)) + out * (0.004 + flare)
                else:
                    extra = floor + 0.004 - drop
                    p = Vector((qx, qy, floor + 0.004 + 0.01 * max(0.0, math.sin(extra * 20 + ph[0])))) + out * (0.004 + flare + extra)
            verts.append(tuple(p))
            uvs.append((u * sx / 0.35, v * sy / 0.35))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            faces.append((a, a + 1, a + nu + 2, a + nu + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    layer = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            layer.data[li].uv = uvs[me.loops[li].vertex_index]
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    sub = o.modifiers.new("smooth", "CORRECTIVE_SMOOTH")
    sub.iterations = 6
    sub.factor = 0.6
    deps = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(o.evaluated_get(deps))
    o.modifiers.clear()
    o.data = me2
    me2.name = name
    bpy.data.meshes.remove(me)
    return o


def solidify(o, thickness=0.002):
    """Gives a cloth a little thickness (applied), so its edge shows."""
    mod = o.modifiers.new("solid", "SOLIDIFY")
    mod.thickness = thickness
    mod.offset = 0
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(deps))
    old = o.data
    o.modifiers.clear()
    o.data = me
    me.name = o.name
    bpy.data.meshes.remove(old)
    return o


# ------------------------------------------------------------------ flames


def flame_template():
    """The candle flame every lit wick carries (the rebuild's `candle_flame` mesh) and the
    world matrix one of its copies has, with the foot of that copy."""
    me = bpy.data.meshes.get("candle_flame")
    src = next((o for o in bpy.data.objects if o.data is me), None) if me else None
    if src is None:
        src = bpy.data.objects.get("hall_altar_lamp_flame")
        me = src.data if src else None
    if src is None:
        return None
    vl()
    sp = [src.matrix_world @ Vector(c) for c in src.bound_box]
    foot = Vector((sum(p.x for p in sp) / 8, sum(p.y for p in sp) / 8, min(p.z for p in sp)))
    return me, src.matrix_world.copy(), foot


def flames_and_lights(coll, tips, prefix, light_prefix, watts=0.6, colour=CANDLE):
    """A flame on each wick tip (named so FuneralRoom.ts wavers them) and a light marker
    above each (VillageLights.ts: the previews' watts)."""
    t = flame_template()
    out = []
    for k, tip in enumerate(tips):
        tip = Vector(tuple(tip))
        if t:
            me, mw, foot = t
            o = bpy.data.objects.new(f"{prefix}_{k:03d}", me)
            coll.objects.link(o)
            m = mw.copy()
            m.translation = mw.translation + (tip + Vector((0, 0, 0.002)) - foot)
            o.matrix_world = m
            out.append(o)
        name = f"light_flame_{light_prefix}_{k:02d}"
        old = bpy.data.objects.get(name)
        if old is not None:
            bpy.data.objects.remove(old, do_unlink=True)
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "PLAIN_AXES"
        e.empty_display_size = 0.05
        e.location = tip + Vector((0, 0, 0.03))
        coll.objects.link(e)
        e["watts"] = float(watts)
        e["color"] = [round(float(c), 3) for c in colour]
        e["radius"] = round(max(1.8, min(12.0, 3.2 * math.sqrt(watts))), 2)
    return out


def flames_out(box_min, box_max, patterns=("house_flame_", "light_flame_house_room_", "fu_flame_", "light_flame_fu_candle_")):
    """Deletes the flames and light markers standing inside a box (when the things that
    carried them are rebuilt)."""
    gone = []
    for o in bpy.data.objects:
        if not o.name.startswith(patterns):
            continue
        p = o.matrix_world.translation if o.type == "EMPTY" else (lambda b: (b[0] + b[1]) / 2)(box_of([o]) or (o.location, o.location))
        if all(box_min[i] <= p[i] <= box_max[i] for i in range(3)):
            gone.append(o)
    return delete(gone)


def marker(coll, name, at, **props):
    old = bpy.data.objects.get(name)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "PLAIN_AXES"
    e.empty_display_size = 0.05
    e.location = tuple(at)
    coll.objects.link(e)
    for k, v in props.items():
        e[k] = v
    return e
