"""Old cobwebs for Episode 1's house: not the drawn orb web of a garden spider but
the grey, dust-laden sheets that house spiders leave in a ceiling corner, sagging
under their own dust, with loose strands and broken threads hanging below.

Every web is anchored: each sheet's three edges lie on the ceiling and the two
walls of its corner, and each hanging thread starts on a surface.
Run inside Blender (imported by the house builders).
"""
import math
import os

import bpy
import numpy as np

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


def corner_cobweb(name, coll, corner, along_a, along_b, size, sheet_mat, thread_mat, seed=0):
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
