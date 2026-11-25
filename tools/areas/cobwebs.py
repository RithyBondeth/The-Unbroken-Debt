"""Old cobwebs for Episode 1: not the drawn orb web of a garden spider but the grey,
dust-laden sheets that house spiders leave in a ceiling corner, sagging under their own
dust, with loose strands and broken threads hanging below.

Every web is anchored: each sheet's edges lie on the ceiling and the walls of its corner
(or on the post and the beam of an angle), and each thread starts and ends on a surface.

The user's review of November 25, 2026 ("fix all the spider webs in the whole village
scene"): the threads were tubes of 0.7 mm, far under a pixel across the room, so the game
drew them as dotted lines (and the house's corner sheets had gone with the old house,
leaving the bare threads hanging in the new rooms). Now:
- a thread is a pair of crossed ribbons a few millimetres wide carrying a soft thread
  drawn in a texture (T_ep1_cobweb_strand_BC), blended: near to, a fine dusty thread; far
  off, its mipmaps fade it to a faint continuous line, never dashes;
- the sheets are veils of anti-aliased threads and settled dust (T_ep1_cobweb_veil_BC),
  blended, in layers: the corner veil, a hammock sagging lower down, a funnel;
- hanging tails end in clots of lint; one or two long streamers of old silk hang lower.
Each group of webs (the house, under it, a shrine, a cart) is two meshes, one per material.
`refit()` rebuilds every web in the village at the end of rebuild-farmstead.py.

Run inside Blender (imported by the house and shrine builders).
"""
import math
import os
import re
import zlib

import bpy
import numpy as np
from mathutils import Vector

from kit import ROOT, image_material, mesh_object

OUT = os.path.join(ROOT, "art-source", "textures", "ep1")
NAME = "T_ep1_cobweb_dusty_BC"


def dusty_web_texture(size=2048, seed=1931):
    """A veil of hair-fine threads: each thread is faint, they build up where they
    cross, densest along the top (where the web meets the ceiling) and torn open
    lower down; dust has settled into a grey film between them and beads some threads.
    Alpha is the coverage, so the web is see-through (glTF alphaMode BLEND)."""
    import weathering
    path = os.path.join(OUT, NAME + ".png")
    rng = np.random.default_rng(seed)
    ink = np.zeros((size, size))
    for _ in range(2600):
        if rng.random() < .65:
            a = np.array([rng.uniform(0, size), size * rng.uniform(0, 1) ** .6])
            ang = rng.normal(0, .55)
        else:
            a = np.array([rng.uniform(0, size), rng.uniform(.5, 1) * size])
            ang = -math.pi / 2 + rng.normal(0, .7)
        length = rng.uniform(.05, .55) * size
        bend = rng.normal(0, .2)
        b = a + length * np.array([math.cos(ang), math.sin(ang)])
        mid = (a + b) / 2 + bend * length * np.array([-math.sin(ang), math.cos(ang)])
        t = np.linspace(0, 1, int(length * 2))[:, None]
        pts = (1 - t) ** 2 * a + 2 * (1 - t) * t * mid + t ** 2 * b
        keep = (pts[:, 0] >= 0) & (pts[:, 0] < size) & (pts[:, 1] >= 0) & (pts[:, 1] < size)
        pts = pts[keep]
        if len(pts) == 0:
            continue
        xi, yi = pts[:, 0].astype(int), pts[:, 1].astype(int)
        np.maximum.at(ink, (yi, xi), np.maximum(ink[yi, xi], 0) * 0 + rng.uniform(.28, .6))
        # Crossings build up.
        ink[yi, xi] += .05
    # A settled dust film, heaviest near the top edge and in sagging pockets.
    top = (np.arange(size) / size)[:, None] ** 1.5
    film = weathering.fbm(size, rng, ((3, .5), (8, .3), (21, .2)))
    veil = np.clip((film - .3) * 1.5, 0, 1) * (.22 + .5 * top)
    # Dust beads on some threads.
    for _ in range(500):
        x0, y0 = rng.integers(2, size - 2), rng.integers(2, size - 2)
        if ink[y0, x0] > 0 or rng.random() < .2:
            r = rng.uniform(1.0, 2.5)
            ys, xs = np.mgrid[y0 - 2:y0 + 3, x0 - 2:x0 + 3]
            blob = np.exp(-((xs - x0) ** 2 + (ys - y0) ** 2) / (r * r))
            ink[ys, xs] = np.maximum(ink[ys, xs], blob * .9)
    # Torn: holes through the lower half.
    holes = np.zeros((size, size), bool)
    yy, xx = np.ogrid[:size, :size]
    for _ in range(16):
        cx, cy, r = rng.uniform(0, size), rng.uniform(0, size * .6), rng.uniform(80, 280)
        holes |= ((xx - cx) ** 2 + ((yy - cy) * 1.4) ** 2) < r * r
    ink[holes] *= .3
    veil[holes] *= .2
    alpha = np.clip(1 - (1 - np.clip(ink, 0, 1)) * (1 - veil), 0, 1)
    rgba = np.zeros((size, size, 4), np.float32)
    rgba[:, :, :3] = np.array([.7, .68, .63]) * (.8 + .2 * film)[:, :, None]
    rgba[:, :, 3] = alpha
    img = bpy.data.images.new(NAME, width=size, height=size, alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    return path


def web_materials():
    path = os.path.join(OUT, NAME + ".png")
    if not os.path.exists(path):
        dusty_web_texture()
    sheet = image_material("M_cobweb_dusty", path, rough=1.0)
    # See-through: the texture's alpha straight into the shader (glTF alphaMode BLEND).
    nodes, links = sheet.node_tree.nodes, sheet.node_tree.links
    tex = next(n for n in nodes if n.type == "TEX_IMAGE")
    links.new(tex.outputs["Alpha"], nodes["Principled BSDF"].inputs["Alpha"])
    sheet.use_backface_culling = False
    sheet.surface_render_method = "BLENDED"
    from kit import plain
    thread = plain("M_cobweb_thread", (.5, .48, .44), rough=1.0, alpha=.55)
    thread.surface_render_method = "BLENDED"
    return sheet, thread


def _sheet(name, coll, a, b, c, sag, mat, rng, n=10):
    """A triangle of web with corners a, b (on the ceiling) and c (down the corner
    line). Its edges stay on the three surfaces; the middle sags."""
    a, b, c = (np.array(p, float) for p in (a, b, c))
    verts, faces, uvs, index = [], [], [], {}
    u0, v0 = rng.random() * .5, rng.random() * .5
    for i in range(n + 1):
        for j in range(n + 1 - i):
            k = n - i - j
            wa, wb, wc = i / n, j / n, k / n
            p = wa * a + wb * b + wc * c
            bubble = 27 * wa * wb * wc  # 0 on every edge, 1 in the middle
            p = p + np.array([0, 0, -sag * bubble * (1 + .2 * rng.normal())])
            index[(i, j)] = len(verts)
            verts.append(tuple(p))
            uvs.append((u0 + .5 * (wa + .5 * wc), v0 + .5 * (1 - wc)))
    for i in range(n):
        for j in range(n - i):
            faces.append((index[(i, j)], index[(i + 1, j)], index[(i, j + 1)]))
            if i + j + 1 < n:
                faces.append((index[(i + 1, j)], index[(i + 1, j + 1)], index[(i, j + 1)]))
    loop_uvs = [uvs[v] for f in faces for v in f]
    return mesh_object(name, coll, verts, faces, mat, uvs=loop_uvs)


def _thread(name, coll, points, radius, mat):
    """A thread through `points` (a short tube)."""
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 1
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, q in zip(spline.points, points):
        p.co = (*q, 1)
    obj = bpy.data.objects.new(name, curve)
    coll.objects.link(obj)
    curve.materials.append(mat)
    return obj


def legacy_corner_cobweb(name, coll, corner, along_a, along_b, size, sheet_mat, thread_mat, seed=0):
    """A dusty web in a ceiling corner. `corner` is where the ceiling meets the two
    walls; `along_a`/`along_b` run along each wall into the room; `size` is the
    reach of the biggest sheet in metres."""
    rng = np.random.default_rng(seed)
    p = np.array(corner, float)
    da, db = np.array(along_a, float), np.array(along_b, float)
    down = np.array([0, 0, -1.0])
    made = []
    for k in range(3):
        s = size * (1 - .28 * k) * rng.uniform(.85, 1.1)
        a = p + da * s * rng.uniform(.8, 1.2)
        b = p + db * s * rng.uniform(.8, 1.2)
        c = p + down * s * rng.uniform(.9, 1.4)
        made.append(_sheet(f"{name}_sheet_{k}", coll, a, b, c, s * rng.uniform(.12, .22), sheet_mat, rng))
    # Loose threads: from the ceiling out along each wall, sagging; a few broken ones hang down.
    for k in range(9):
        t0 = rng.uniform(.2, 1.0) * size
        start = p + (da if k % 2 else db) * t0
        end = p + (db if k % 2 else da) * rng.uniform(.1, .5) * size + down * rng.uniform(.1, .6) * size
        pts = []
        for j in range(9):
            f = j / 8
            q = start * (1 - f) + end * f + down * .08 * size * math.sin(math.pi * f)
            pts.append(tuple(q))
        made.append(_thread(f"{name}_thread_{k}", coll, pts, .0007, thread_mat))
    for k in range(4):
        start = p + da * rng.uniform(.05, .6) * size + db * rng.uniform(.05, .6) * size
        start[2] = p[2]
        length = rng.uniform(.1, .35)
        pts = [tuple(start + down * length * j / 6 + np.array([rng.normal(0, .004), rng.normal(0, .004), 0])) for j in range(7)]
        made.append(_thread(f"{name}_drop_{k}", coll, pts, .0008, thread_mat))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=rng.uniform(.004, .009), location=pts[-1])
        clump = bpy.context.active_object
        clump.name = f"{name}_dust_{k}"
        clump.scale = (1, 1, 1.6)
        for c_ in clump.users_collection:
            c_.objects.unlink(clump)
        coll.objects.link(clump)
        clump.data.materials.append(thread_mat)
        made.append(clump)
    return made


# ------------------------------------------------------------------ the textures (Nov 25)

VEIL = "T_ep1_cobweb_veil_BC"
STRAND = "T_ep1_cobweb_strand_BC"
SILK = np.array([.6, .585, .55])        # old silk furred grey with dust (sRGB)
COLUMNS = 4                             # the strand texture's kinds, side by side in U


def _splat(ink, xy, value, wrap=True):
    """Adds `value` at sub-pixel points `xy` (N x 2, x right, y down) by bilinear weights:
    threads drawn this way stay smooth at every angle instead of stair-stepped."""
    h, w = ink.shape
    x, y = xy[:, 0], xy[:, 1]
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = x - x0, y - y0
    for dx, dy, wt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        xi, yi = x0 + dx, y0 + dy
        if wrap:
            xi, yi = xi % w, yi % h
            np.add.at(ink, (yi, xi), wt * value)
        else:
            ok = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
            np.add.at(ink, (yi[ok], xi[ok]), (wt * value)[ok] if np.ndim(value) else wt[ok] * value)


def _curve(a, b, bend, step=0.5):
    """Points every `step` pixels along a gently bowed thread from a to b."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    length = float(np.hypot(*d)) or 1.0
    mid = (a + b) / 2 + bend * length * np.array([-d[1], d[0]]) / length
    t = np.linspace(0, 1, max(2, int(length / step)))[:, None]
    return (1 - t) ** 2 * a + 2 * (1 - t) * t * mid + t ** 2 * b


def _blur(img, sigma):
    """A separable Gaussian blur that wraps at the edges."""
    r = max(1, int(3 * sigma))
    k = np.exp(-np.arange(-r, r + 1) ** 2 / (2 * sigma * sigma))
    k /= k.sum()
    out = sum(np.roll(img, i, axis=0) * k[i + r] for i in range(-r, r + 1))
    return sum(np.roll(out, i, axis=1) * k[i + r] for i in range(-r, r + 1))


def _save(name, colour, alpha):
    path = os.path.join(OUT, name + ".png")
    h, w = alpha.shape
    rgba = np.zeros((h, w, 4), np.float32)
    rgba[:, :, :3] = colour
    rgba[:, :, 3] = np.clip(alpha, 0, 1)
    img = bpy.data.images.new(name, width=w, height=h, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(rgba[::-1]).ravel())   # Blender's rows run bottom up
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return path


def veil_texture(size=1024, seed=1925):
    """An old sheet web: thousands of fine threads laid every way and crossing, thicker
    where many run together near the anchored edge (the top of the image), settled dust
    clogging the mesh in soft patches, torn open lower down. Anti-aliased; alpha is the
    coverage (blended in the game)."""
    import weathering
    path = os.path.join(OUT, VEIL + ".png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(seed)
    ink = np.zeros((size, size))
    for k in range(3400):
        if rng.random() < .45:          # the sheet's weave: long threads across it
            a = rng.uniform(0, size, 2)
            ang = rng.uniform(0, math.pi)
            length = rng.uniform(.06, .3) * size
        else:                           # short ties and broken ends
            a = rng.uniform(0, size, 2)
            ang = rng.uniform(0, math.pi)
            length = rng.uniform(.01, .07) * size
        b = a + length * np.array([math.cos(ang), math.sin(ang)])
        pts = _curve(a, b, rng.normal(0, .08))
        # Thicker, dustier threads near the top (where the sheet is anchored).
        top = 1 - (pts[:, 1] % size) / size
        _splat(ink, pts, rng.uniform(.06, .22) * (.7 + .6 * top) * .5)
    threads = 1 - np.exp(-ink * 1.6)
    film = weathering.fbm(size, rng, ((3, .5), (7, .3), (19, .2)))
    # Settled dust: a soft felt between the threads, in drifts.
    felt = weathering.fbm(size, rng, ((48, .5), (110, .5)))
    clog = np.clip((film - .3) * 1.6, 0, 1) * (.3 + .25 * felt)
    # Dust beads caught on the threads.
    beads = np.zeros_like(ink)
    _splat(beads, rng.uniform(0, size, (900, 2)), rng.uniform(.6, 1.4, 900))
    beads = _blur(beads, .9) * threads * 3
    alpha = 1 - (1 - threads) * (1 - clog) * (1 - np.clip(beads, 0, .6))
    # Torn: ragged holes, more of them lower down.
    yy, xx = np.mgrid[:size, :size]
    holes = np.zeros((size, size))
    for _ in range(26):
        cx, cy, r = rng.uniform(0, size), rng.uniform(.25, 1.0) * size, rng.uniform(25, 120)
        d = np.hypot(np.minimum(abs(xx - cx), size - abs(xx - cx)), (yy - cy) * 1.3)
        holes = np.maximum(holes, np.clip((r - d) / 18, 0, 1))
    holes *= .85 + .15 * film
    alpha *= 1 - holes * .9
    shade = (.82 + .18 * film)[:, :, None]
    return _save(VEIL, SILK * shade, np.clip(alpha * .85, 0, .8))


def strand_texture(width=64, height=512, seed=1926):
    """Four kinds of thread, each a column `width` pixels wide, drawn down the middle of
    its column with a soft falloff (the ribbon carrying it is wider than the silk):
    0 a clean thread; 1 a dusty thread, fuzzed and beaded; 2 a hanging tail (U 0.5-0.75)
    ending in a clot of lint at the bottom of the image; 3 a streamer, a few threads
    twisted loosely together. Columns 0, 1 and 3 tile top to bottom."""
    path = os.path.join(OUT, STRAND + ".png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(seed)
    alpha = np.zeros((height, width * COLUMNS))
    xs = np.arange(width)
    for col in range(COLUMNS):
        ink = np.zeros((height, width))
        cx = width / 2
        if col in (0, 1):
            wob = cx + 1.2 * np.sin(np.linspace(0, math.tau * 2, height) + rng.uniform(0, 6))
            core = 1.3 if col == 0 else 1.9
            for y in range(height):
                ink[y] = np.exp(-(xs - wob[y]) ** 2 / (2 * core * core)) * (.9 if col == 0 else .8)
            if col == 1:                                # fuzz: short fibres off the thread
                for _ in range(260):
                    y0 = rng.uniform(0, height)
                    a = (cx + rng.normal(0, 1.2), y0)
                    ang = rng.uniform(-1.2, 1.2) + (0 if rng.random() < .5 else math.pi)
                    L = rng.uniform(2, 9)
                    b = (a[0] + L * math.cos(ang), a[1] + L * math.sin(ang) * .6)
                    _splat(ink, _curve(a, b, rng.normal(0, .2), .3), .22)
            n_beads = 12 if col == 0 else 46
            for _ in range(n_beads):
                y0, r = rng.uniform(0, height), rng.uniform(1.0, 2.6 if col == 1 else 1.6)
                d2 = (xs[None, :] - cx) ** 2 + (np.arange(height)[:, None] - y0) ** 2
                ink = np.maximum(ink, np.exp(-d2 / (r * r)) * .85)
        elif col == 2:                                  # a tail and its clot of lint
            clot_y = height * .88
            for y in range(height):
                ink[y] = np.exp(-(xs - cx - .8 * math.sin(y / 23)) ** 2 / (2 * 1.7 ** 2)) * .8
            for _ in range(520):
                rr = abs(rng.normal(0, 7.5))
                ang = rng.uniform(0, math.tau)
                a = (cx + rr * math.cos(ang) * .8, clot_y + rr * math.sin(ang) * 1.6)
                b = (a[0] + rng.normal(0, 6), a[1] + rng.normal(0, 7))
                _splat(ink, _curve(a, b, rng.normal(0, .3), .3), .3, wrap=False)
            yy, xx = np.mgrid[:height, :width]
            ink += np.exp(-((xx - cx) ** 2 / (2 * 5.0 ** 2) + (yy - clot_y) ** 2 / (2 * 9.0 ** 2))) * .7
            ink[int(clot_y + 24):] *= np.linspace(1, 0, height - int(clot_y + 24))[:, None] ** 2
        else:                                           # a streamer of a few twisted threads
            for k in range(5):
                ph, amp = rng.uniform(0, math.tau), rng.uniform(4, 13)
                pts = np.stack([cx + amp * np.sin(np.linspace(0, math.tau * 3, height * 2) + ph),
                                np.linspace(0, height, height * 2)], axis=1)
                _splat(ink, pts, .9)
            ink = _blur(ink, .8) * 1.3
            for _ in range(40):
                y0, r = rng.uniform(0, height), rng.uniform(1.2, 3.2)
                x0 = cx + rng.normal(0, 7)
                d2 = (xs[None, :] - x0) ** 2 + (np.arange(height)[:, None] - y0) ** 2
                ink = np.maximum(ink, np.exp(-d2 / (r * r)) * .7)
        # The halo of fine fluff round every thread, faint.
        ink = np.maximum(ink, _blur(ink, 4.0) * .35)
        # Nothing reaches the column's edges: neighbours stay apart in the mipmaps.
        edge = np.clip(np.minimum(xs, width - 1 - xs) / 6.0, 0, 1)
        strength = (.6, .6, .5, .42)[col]
        alpha[:, col * width:(col + 1) * width] = np.clip(ink, 0, 1) * edge[None, :] * strength
    return _save(STRAND, SILK, alpha)


def materials():
    """The veil and the strand materials (blended, both sides, no shine)."""
    out = []
    for name, path in (("M_cobweb_veil", veil_texture()), ("M_cobweb_strand", strand_texture())):
        mat = bpy.data.materials.get(name)
        if mat is None:
            mat = image_material(name, path, rough=1.0)
            nodes, links = mat.node_tree.nodes, mat.node_tree.links
            tex = next(n for n in nodes if n.type == "TEX_IMAGE")
            links.new(tex.outputs["Alpha"], nodes["Principled BSDF"].inputs["Alpha"])
            bsdf = nodes["Principled BSDF"]
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = 0.1
            mat.use_backface_culling = False
            mat.blend_method = "BLEND"
            mat.surface_render_method = "BLENDED"
        out.append(mat)
    return tuple(out)


# ------------------------------------------------------------------ the geometry (Nov 25)


class Webs:
    """Collects the veils and strands of many webs; `build` makes one mesh of each."""

    def __init__(self):
        self.parts = {"veil": ([], [], []), "strand": ([], [], [])}

    def _add(self, kind, verts, faces, uvs):
        V, Fc, U = self.parts[kind]
        base = len(V)
        V.extend(tuple(v) for v in verts)
        Fc.extend(tuple(base + i for i in f) for f in faces)
        U.extend(uvs)

    def sheet(self, a, b, c, sag, rng, n=10, free=None, droop=0.0):
        """A web sheet over the triangle a, b, c: anchored along its edges, sagging `sag`
        in the middle. `free` names an edge left hanging in the air ("ab", "bc" or "ca"),
        which droops `droop` and frays."""
        a, b, c = Vector(a), Vector(b), Vector(c)
        verts, faces, uvs, index = [], [], [], {}
        u0, v0, rot = rng.uniform(0, .5), rng.uniform(0, .5), rng.uniform(0, math.tau)
        down = Vector((0, 0, -1))
        for i in range(n + 1):
            for j in range(n + 1 - i):
                k = n - i - j
                wa, wb, wc = i / n, j / n, k / n
                p = a * wa + b * wb + c * wc
                bubble = 27 * wa * wb * wc
                hang = 0.0
                if free:
                    w1, w2 = {"ab": (wa, wb), "bc": (wb, wc), "ca": (wc, wa)}[free]
                    edge = 4 * w1 * w2              # 1 at the free edge's middle, 0 at its ends
                    near = 1 - {"ab": wc, "bc": wa, "ca": wb}[free]
                    hang = droop * edge * near ** 2 * (1 + .35 * rng.normal())
                p = p + down * (sag * bubble * (1 + .15 * rng.normal()) + hang)
                index[(i, j)] = len(verts)
                verts.append(p)
                # UVs: the triangle laid into half the veil texture, turned at random, the
                # anchored corner c towards the top (the dense threads).
                x, y = wa + .5 * wc - .5, .5 - wc
                uvs.append((u0 + .25 + .5 * (x * math.cos(rot) - y * math.sin(rot)) * .9,
                            v0 + .25 + .5 * (x * math.sin(rot) + y * math.cos(rot)) * .9))
        for i in range(n):
            for j in range(n - i):
                faces.append((index[(i, j)], index[(i + 1, j)], index[(i, j + 1)]))
                if i + j + 1 < n:
                    faces.append((index[(i + 1, j)], index[(i + 1, j + 1)], index[(i, j + 1)]))
        loop_uvs = [uvs[v] for f in faces for v in f]
        self._add("veil", verts, faces, loop_uvs)

    def ribbon(self, pts, width, col, facing, cross=True, tile=0.5):
        """A thread along `pts`: two crossed ribbons `width` wide carrying column `col` of
        the strand texture (V runs along it, `tile` metres to a repeat; a tail's column 2 is
        stretched once from top to bottom)."""
        pts = [Vector(p) for p in pts]
        if len(pts) < 2:
            return
        facing = Vector(facing).normalized()
        u0, u1 = col / COLUMNS + .004, (col + 1) / COLUMNS - .004
        lengths = [0.0]
        for p, q in zip(pts, pts[1:]):
            lengths.append(lengths[-1] + (q - p).length)
        total = lengths[-1] or 1.0
        sides = []
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            s1 = t.cross(facing)
            if s1.length < 1e-4:
                s1 = t.cross(Vector((0, 0, 1))) if abs(t.z) < .9 else t.cross(Vector((1, 0, 0)))
            s1.normalize()
            sides.append((s1, t.cross(s1).normalized()))
        for which in ((0, 1) if cross else (0,)):
            verts, faces, uvs = [], [], []
            for i, p in enumerate(pts):
                s = sides[i][which] * width / 2
                verts += [p - s, p + s]
                v = 1 - lengths[i] / total if col == 2 else lengths[i] / tile
                uvs.append(((u0, v), (u1, v)))
            loop_uvs = []
            for i in range(len(pts) - 1):
                a = 2 * i
                faces.append((a, a + 1, a + 3, a + 2))
                loop_uvs += [uvs[i][0], uvs[i][1], uvs[i + 1][1], uvs[i + 1][0]]
            self._add("strand", verts, faces, loop_uvs)

    def thread(self, a, b, sag, facing, rng, col=0, width=0.005, bow=None, n=9):
        """A thread strung from a to b, sagging `sag` and bowed out along `bow`."""
        a, b = Vector(a), Vector(b)
        pts = []
        for j in range(n):
            f = j / (n - 1)
            q = a.lerp(b, f) + Vector((0, 0, -sag * math.sin(math.pi * f)))
            if bow is not None:
                q += Vector(bow) * math.sin(math.pi * f)
            pts.append(q)
        self.ribbon(pts, width, col, facing)

    def tail(self, top, length, facing, rng, width=0.01):
        """A broken thread hanging from `top`, a clot of lint at its end, turning a little."""
        top = Vector(top)
        drift = Vector((rng.normal(0, .02), rng.normal(0, .02), 0))
        pts = [top + Vector((0, 0, -length * j / 6)) + drift * (j / 6) ** 2 for j in range(7)]
        self.ribbon(pts, width, 2, facing)

    def streamer(self, top, length, facing, rng, width=0.014):
        """A long rope of old silk furred with dust, hanging in a slow curve."""
        top = Vector(top)
        swing = Vector((rng.normal(0, .05), rng.normal(0, .05), 0))
        pts = [top + Vector((0, 0, -length * j / 9)) + swing * math.sin(math.pi * j / 18) for j in range(10)]
        self.ribbon(pts, width, 3, facing, tile=0.35)

    def build(self, coll, name, parent=None):
        veil, strand = materials()
        made = []
        for kind, mat in (("veil", veil), ("strand", strand)):
            V, Fc, U = self.parts[kind]
            if not Fc:
                continue
            o = mesh_object(f"{name}_cobweb_{kind}", coll, V, Fc, mat, uvs=U)
            if parent is not None:
                o.parent = parent
                o.matrix_parent_inverse = parent.matrix_world.inverted()
            made.append(o)
        self.parts = {"veil": ([], [], []), "strand": ([], [], [])}
        return made


def corner_web(W, corner, along_a, along_b, size, rng):
    """A house spider's web in a ceiling corner: three veils across the corner from the
    ceiling down the corner line, a hammock sheet strung lower between the two walls
    (its outer edge free, sagging), scaffold threads from wall to wall, tails and a
    streamer hanging under it. `along_a`/`along_b` run along the walls into the room."""
    p = Vector(corner)
    da, db = Vector(along_a).normalized(), Vector(along_b).normalized()
    down = Vector((0, 0, -1))
    room = (da + db).normalized()
    facing = (room + down * .35).normalized()
    U = rng.uniform
    for k in range(3):
        s = size * (1 - .3 * k) * U(.85, 1.1)
        W.sheet(p + da * s * U(.8, 1.15), p + db * s * U(.8, 1.15), p + down * s * U(.8, 1.2), s * U(.1, .18), rng)
    # The hammock.
    h, s = size * U(.5, .7), size * U(.75, .95)
    ha, hb = p + da * s + down * h * U(.85, 1.1), p + db * s + down * h * U(.85, 1.1)
    hc = p + down * h * U(1.05, 1.25)
    W.sheet(ha, hb, hc, s * U(.08, .14), rng, free="ab", droop=s * U(.12, .22))
    # Scaffold threads, wall to wall over and under the hammock.
    for k in range(9):
        za, zb = U(.02, .95) * size, U(.02, .95) * size
        a = p + da * U(.12, 1.0) * size + down * za
        b = p + db * U(.12, 1.0) * size + down * zb
        W.thread(a, b, U(.01, .06) * size, facing, rng, col=0 if k % 3 else 1, width=0.005 if k % 3 else 0.007,
                 bow=room * U(.0, .06) * size)
    # A few from the ceiling down to the hammock's edge.
    for k in range(4):
        t = U(.25, .75)
        edge = ha.lerp(hb, t) + down * (s * .15 * 4 * t * (1 - t))
        top = p + (da * U(.2, .8) + db * U(.2, .8)) * size
        W.thread(top, edge, .0, facing, rng, col=0, width=0.0045, n=4)
    # Tails from the hammock's edge and the veils; one or two streamers.
    for k in range(int(rng.integers(3, 6))):
        t = U(.15, .85)
        at = ha.lerp(hb, t) + down * (s * .17 * 4 * t * (1 - t))
        W.tail(at, U(.05, .22), facing, rng)
    for k in range(int(rng.integers(0, 2)) + (1 if size > .45 else 0)):
        t = U(.3, .7)
        at = ha.lerp(hb, t) + down * (s * .17 * 4 * t * (1 - t))
        W.streamer(at, U(.15, .4) * min(1.0, size / .45), facing, rng)


def angle_web(W, corner, u, v, size, facing, rng, veil=True):
    """A web in the angle of two surfaces (a post and the beam it carries, two spokes): a
    veil across the angle bellied out along `facing`, radial threads from the corner to a
    sagging bridge thread, cross threads between them, broken ends hanging."""
    c, u, v = Vector(corner), Vector(u).normalized(), Vector(v).normalized()
    facing = Vector(facing).normalized()
    U = rng.uniform

    def point(t, r):
        d = u * (1 - t) + v * t
        return c + d * r * size + facing * .025 * size * math.sin(t * math.pi) * r + Vector((0, 0, -.04 * size * math.sin(t * math.pi) * r))

    if veil:
        W.sheet(c, c + u * size * U(.6, .85), c + v * size * U(.6, .85), 0.0, rng, n=8, free="ab", droop=size * U(.06, .12))
    spokes = int(rng.integers(7, 11))
    ts = sorted([0.0, 1.0] + [U(.05, .95) for _ in range(spokes - 2)])
    for t in ts:
        W.ribbon([c, point(t, .5), point(t, 1.0)], 0.0045, 0, facing)
    W.ribbon([point(i / 16, 1.0) for i in range(17)], 0.006, 1, facing)
    for ring in range(1, 8):
        r = ring / 8
        for k in range(len(ts) - 1):
            if rng.random() < .3:
                continue
            a, b = point(ts[k], r), point(ts[k + 1], r * U(.96, 1.04))
            W.thread(a, b, .012 * size * r, facing, rng, col=0, width=0.004, n=4)
    for k in range(int(rng.integers(1, 4))):
        W.tail(point(U(.2, .8), U(.6, 1.0)), U(.05, .22), facing, rng)


def corner_cobweb(name, coll, corner, along_a, along_b, size, sheet_mat=None, thread_mat=None, seed=0):
    """A dusty web in a ceiling corner as its own two meshes (veil, strands). `corner` is
    where the ceiling meets the two walls; `along_a`/`along_b` run along each wall into the
    room; `size` is the reach of the biggest sheet in metres. (The material arguments of
    the old builder are no longer used.)"""
    W = Webs()
    corner_web(W, corner, along_a, along_b, size, np.random.default_rng(seed))
    return W.build(coll, name)


# ------------------------------------------------------------------ the village's webs (Nov 25)


LEGACY = re.compile(r"^(M_cobweb_dusty|M_cobweb_thread|M_house_detail_dusty_silk)")
SKIP = ("col_", "light_", "marker_", "_", "nav_", "trigger_", "hide_", "spawn_", "occ_")


def _ray(origin, direction, distance):
    """The first visible surface along a ray: (distance, object) or None."""
    sc, deps = bpy.context.scene, bpy.context.evaluated_depsgraph_get()
    o, d = Vector(origin), Vector(direction).normalized()
    gone = 0.0
    for _ in range(16):
        hit, loc, nrm, idx, obj, mat = sc.ray_cast(deps, o, d, distance=distance - gone)
        if not hit:
            return None
        hidden = obj.hide_render or any(c.name.startswith("_") or c.hide_render for c in obj.users_collection)
        if obj.name.startswith(SKIP) or hidden or "cobweb" in obj.name:
            gone += (loc - o).length + .002
            o = loc + d * .002
            continue
        return gone + (loc - o).length, obj
    return None


def _legacy_anchor(prefix):
    """The corner, the two directions and the size of an old web, from its biggest veil
    (vertices 0, n and the last of the first row: c, b, a in _sheet's order)."""
    o = bpy.data.objects.get(f"{prefix}_sheet_0")
    if o is None or o.type != "MESH":
        return None
    n = 10
    vs = [o.matrix_world @ v.co for v in o.data.vertices]
    if len(vs) != (n + 1) * (n + 2) // 2:
        return None
    c, b, a = vs[0], vs[n], vs[(n + 1) * (n + 2) // 2 - 1]
    p = Vector((c.x, c.y, max(a.z, b.z)))
    da, db = a - p, b - p
    da.z = db.z = 0
    if da.length < 1e-3 or db.length < 1e-3:
        return None
    return p, da.normalized(), db.normalized(), (da.length + db.length) / 2, o.users_collection[0]


def _house_corners(rng):
    """Ceiling corners of the house's rooms that can hold a web: two walls and the ceiling
    meet there (no door, window or shutter cut into either wall under it), nothing tall
    stands in it, and the web stays clear of whatever is near. One to three per room."""
    import stilt_house as SH
    ceiling = SH.ZW - 0.02
    H, B, LC = SH.H, SH.B, SH.LC
    rooms = {
        # name: (x0, x1, y0, y1, webs)
        "yaymey": (H["x0"], -3.0, SH.FRONT, SH.SPLIT, 1), "loom": (H["x0"], -3.0, SH.SPLIT, H["y1"], 2),
        "hall": (-3.0, 3.0, SH.FRONT, SH.ALTAR_Y, 2), "store": (-3.0, 3.0, SH.ALTAR_Y, H["y1"], 2),
        "parlour": (3.0, H["x1"], SH.FRONT, SH.SPLIT, 1), "vuthy": (3.0, H["x1"], SH.SPLIT, H["y1"], 1),
        "cross": (B["x0"], B["x1"], B["y0"], SH.CORR, 2), "long": (-LC, LC, SH.CORR, B["y1"], 2),
        "study": (B["x0"], -LC, SH.CORR, SH.ROW1, 2), "bedroom": (B["x0"], -LC, SH.ROW1, SH.ROW2, 1),
        "locked": (B["x0"], -LC, SH.ROW2, B["y1"], 3), "kanha": (LC, B["x1"], SH.CORR, SH.ROW1, 1),
        "store_back": (LC, B["x1"], SH.ROW1, SH.ROW2, 2), "landing": (LC, SH.LAND_X, SH.ROW2, B["y1"], 1),
        "washroom": (SH.LAND_X, B["x1"], SH.ROW2, B["y1"], 2),
    }
    # The hall's front corner east of the door (the user's screenshot, Nov 25) always has one.
    must = {("hall", 1, 0)}
    out = []
    for name, (x0, x1, y0, y1, count) in rooms.items():
        cands = []
        for ix, (cx, sx) in enumerate(((x0, 1), (x1, -1))):
            for iy, (cy, sy) in enumerate(((y0, 1), (y1, -1))):
                cands.append(((name, ix, iy), cx, cy, sx, sy))
        order = list(rng.permutation(len(cands)))
        order.sort(key=lambda i: cands[i][0] not in must)
        made = 0
        for i in order:
            key, cx, cy, sx, sy = cands[i]
            if made >= count:
                break
            q = Vector((cx + sx * 0.3, cy + sy * 0.3, ceiling - 0.1))
            hx, hy, hz = _ray(q, (-sx, 0, 0), 0.6), _ray(q, (0, -sy, 0), 0.6), _ray(q, (0, 0, 1), 0.4)
            if not (hx and hy and hz):
                continue
            p = Vector((q.x - sx * (hx[0] - 0.004), q.y - sy * (hy[0] - 0.004), q.z + hz[0] - 0.004))
            size = float(rng.uniform(0.32, 0.5) if name not in ("locked", "store_back", "store") else rng.uniform(0.42, 0.62))
            da, db = Vector((sx, 0, 0)), Vector((0, sy, 0))
            ok = True
            # Both walls whole under the web, the ceiling whole over it.
            for t in (0.1, 0.5, 0.95, 1.2):
                for z in (0.05, 0.5, 1.0, 1.35):
                    for along, normal in ((da, db), (db, da)):
                        at = p + along * t * size + Vector((0, 0, -z * size)) + normal * 0.05
                        h = _ray(at, -normal, 0.1)
                        if h is None:
                            ok = False
                for u in (0.2, 0.7):
                    at = p + (da * t + db * u) * size + Vector((0, 0, -0.05))
                    if _ray(at, (0, 0, 1), 0.1) is None:
                        ok = False
            # Nothing tall in the corner, nothing beside the web's reach.
            for t in (0.15, 0.5, 0.9):
                for u in (0.15, 0.5, 0.9):
                    at = p + (da * t + db * u) * size * 1.25 + Vector((0, 0, -0.03))
                    h = _ray(at, (0, 0, -1), 1.7 * size + 0.3)
                    if h is not None:
                        ok = False
            if not ok:
                continue
            out.append((key, p, da, db, size))
            made += 1
        if made < count:
            print(f"[webs] {name}: {made} of {count} corners free", flush=True)
    return out


def _under_house(rng, count=9):
    """Angles of a stilt and the girder it carries under the house: the girder's underside
    found by a ray up, the post's face by a ray back."""
    import stilt_house as SH
    out = []
    posts = [(x, y) for x, y in SH.FRONT_POSTS] + [(x, y) for x, y in SH.BACK_POSTS]
    order = rng.permutation(len(posts))
    for i in order:
        if len(out) >= count:
            break
        x, y = posts[i]
        sx = float(rng.choice((-1, 1)))
        h = _ray((x + sx * 0.35, y, SH.FLOOR - 1.2), (0, 0, 1), 1.0)
        if h is None:
            continue
        zg = SH.FLOOR - 1.2 + h[0]
        if zg < SH.FLOOR - 0.75:
            continue
        hp = _ray((x + sx * 0.5, y, zg - 0.12), (-sx, 0, 0), 0.6)
        if hp is None:
            continue
        p = Vector((x + sx * (0.5 - hp[0] + 0.004), y, zg - 0.004))
        size = float(rng.uniform(0.35, 0.6))
        # Clear below and beside the web.
        if _ray(p + Vector((sx * size * 0.4, 0, -0.05)), (0, 0, -1), size * 1.1) is not None:
            continue
        if any(_ray(p + Vector((sx * size * 0.35, 0, -size * 0.35)), (0, d, 0), 0.12) for d in (-1, 1)):
            continue
        out.append((p, Vector((sx, 0, 0)), Vector((0, 0, -1)), size))
    return out


def refit():
    """Every web in the village rebuilt (the user's review of November 25): the old
    threads and sheets out; the house's rooms webbed in corners that hold a web, the
    angles of stilts and girders under it, the Neak Ta shrine's corners where its old webs
    were, the ox carts' wheels. (The spirit house's webs are made new by
    village_review.spirit_house through corner_cobweb.)"""
    rng = np.random.default_rng(2511)
    anchors = {pre: _legacy_anchor(pre) for pre in ("neakta_web_l", "neakta_web_r")}
    carts = []
    for o in list(bpy.data.objects):
        mats = [s.material.name for s in o.material_slots if s.material] if o.type in ("MESH", "CURVE") else []
        if mats and all(LEGACY.match(m) for m in mats) and "silk" in mats[0] and o.parent is not None:
            carts.append(o.parent)
    gone = 0
    for o in list(bpy.data.objects):
        if o.type not in ("MESH", "CURVE"):
            continue
        mats = [s.material.name for s in o.material_slots if s.material]
        if mats and all(LEGACY.match(m) for m in mats):
            bpy.data.objects.remove(o, do_unlink=True)
            gone += 1
    print("[webs] old webs out:", gone, flush=True)
    bpy.context.view_layer.update()

    # The house.
    hc = bpy.data.collections.get("stilt_house")
    if hc is not None:
        W = Webs()
        corners = _house_corners(rng)
        for key, p, da, db, size in corners:
            corner_web(W, p, da, db, size, rng)
        W.build(hc, "house_webs")
        print("[webs] house corners:", [(k[0], round(p.x, 2), round(p.y, 2), round(s, 2)) for k, p, _, _, s in corners], flush=True)
        W = Webs()
        under = _under_house(rng)
        for p, u, v, size in under:
            angle_web(W, p, u, v, size, (0, 1, 0), rng)
        fu = bpy.data.collections.get("funeral_under") or hc
        W.build(fu, "under_house_webs")
        print("[webs] under the house:", [(round(p.x, 2), round(p.y, 2), round(p.z, 2), round(s, 2)) for p, _, _, s in under], flush=True)
    # The Neak Ta shrine, where its old webs were.
    for pre, anchor in anchors.items():
        if anchor is None:
            print("[webs] no anchor for", pre, flush=True)
            continue
        p, da, db, size, coll = anchor
        W = Webs()
        corner_web(W, p, da, db, size, np.random.default_rng(zlib.crc32(pre.encode())))
        W.build(coll, pre)
    # The ox carts' wheels: between two spokes on each side, as before.
    import ox_cart as OX
    for root in {c.name: c for c in carts}.values():
        W = Webs()
        M = root.matrix_world
        axis = (M.to_3x3() @ Vector((1, 0, 0))).normalized()
        for side in (-OX.TRACK, OX.TRACK):
            for a in (.6, 2.9):
                c = M @ Vector((side, .35 * math.cos(a), OX.R + .35 * math.sin(a)))
                u = M.to_3x3() @ Vector((0, math.cos(a + 1.6), math.sin(a + 1.6)))
                v = M.to_3x3() @ Vector((0, -math.sin(a), math.cos(a)))
                angle_web(W, c, u, v, .3, axis, rng, veil=rng.random() < .5)
        W.build(root.users_collection[0], f"{root.name}_wheel", parent=root)
        print("[webs] cart", root.name, flush=True)
