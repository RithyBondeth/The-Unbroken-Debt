"""Household things for Episode 1's re-planned house (November 22, 2026), made as
soft and as worn as the real ones after the user's "the pillows are just like cube
boxes; make every single thing very detailed and realistic":

- pillows: stuffed cotton cases that puff in the middle, pinch to a piped seam, poke
  out at the corners and keep the dent of a head; printed, checked and embroidered
  cases (their cloth generated here);
- the Khmer triangular pillow (the backrest of a seated guest): a row of stuffed
  triangular compartments sewn together, silk with dark red ends;
- mosquito nets hung from the ceiling by their corners, let down or knotted up;
- clothes hung on pegs and lines, folded stacks, books, enamel cups, bottles, tins;
- printed and written paper: ledger pages in a clerk's hand and newspaper pages,
  never blank sheets.

Blender metres, X east, Y north, Z up. Batch builders take a shrine_craft.Batch, the
materials dict from `materials()`, a placement matrix and a numpy Generator.
"""
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

from kit import ROOT, cloth, image_material, library_material, mesh_object, plain, tube
from shrine_craft import Batch, place

TEX = os.path.join(ROOT, "art-source", "textures", "ep1")


# ------------------------------------------------------------------ cloth and paper


def _save(name, px):
    path = os.path.join(TEX, name + ".png")
    if os.path.exists(path):
        return path
    h, w = px.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=px.shape[2] == 4)
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :px.shape[2]] = np.clip(px, 0, 1)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    return path


def _weave(n, rng, amount=0.06):
    """A cotton plain weave's grain and a little uneven dye, as a multiplier."""
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    w = 1 - amount * (0.5 + 0.5 * np.sin(x * math.pi) * np.sin(y * math.pi))
    blot = np.ones((n, n), np.float32)
    for _ in range(14):
        cx, cy, r = rng.uniform(0, n, 2).tolist() + [rng.uniform(n * 0.05, n * 0.2)]
        blot -= 0.05 * np.exp(-(((x - cx) ** 2 + (y - cy) ** 2) / (r * r)))
    return (w * blot)[..., None]


def fabric_textures():
    rng = np.random.default_rng(1930)
    n = 512
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    out = {}
    # Faded floral print: small red and pink flowers, green leaves on cream.
    col = np.zeros((n, n, 3), np.float32)
    col[:] = (0.78, 0.72, 0.6)
    for _ in range(90):
        cx, cy = rng.uniform(0, n, 2)
        r = rng.uniform(6, 13)
        d = np.hypot((x - cx + n / 2) % n - n / 2, (y - cy + n / 2) % n - n / 2)
        ang = np.arctan2(y - cy, x - cx)
        petal = r * (0.65 + 0.35 * np.cos(5 * ang))
        hue = (0.62, 0.16, 0.14) if rng.random() < 0.6 else (0.72, 0.42, 0.42)
        col[d < petal] = hue
        col[d < r * 0.28] = (0.75, 0.6, 0.2)
        lx, ly = cx + rng.normal(0, 1) * r * 1.6, cy + rng.normal(0, 1) * r * 1.6
        dl = np.hypot((x - lx + n / 2) % n - n / 2, ((y - ly) * 1.8 + n / 2) % n - n / 2)
        col[(dl < r * 0.55) & (d >= petal)] = (0.32, 0.42, 0.24)
    out["floral"] = _save("T_ep1_pillow_floral_BC", col * _weave(n, rng))
    # Red-and-white gingham, finer than a krama, washed out.
    a = ((x // 12) % 2).astype(np.float32)
    b = ((y // 12) % 2).astype(np.float32)
    v = (a + b) / 2
    col = np.stack([0.82 - 0.36 * v, 0.78 - 0.62 * v, 0.72 - 0.6 * v], -1)
    out["gingham"] = _save("T_ep1_pillow_gingham_BC", col * _weave(n, rng))
    # White cotton with a red cross-stitch border band near one edge (the case's end).
    col = np.zeros((n, n, 3), np.float32)
    col[:] = (0.84, 0.81, 0.74)
    band = (x > n * 0.78) & (x < n * 0.9)
    stitch = (((x + y) % 10) < 2) | (((x - y) % 10) < 2)
    col[band & stitch] = (0.6, 0.1, 0.1)
    col[(np.abs(x - n * 0.76) < 2) | (np.abs(x - n * 0.92) < 2)] = (0.45, 0.08, 0.08)
    out["embroidered"] = _save("T_ep1_pillow_embroidered_BC", col * _weave(n, rng))
    # Triangular pillow silk: gold and red stripes with a small ikat lozenge.
    col = np.zeros((n, n, 3), np.float32)
    stripe = (y // 32) % 4
    col[stripe == 0] = (0.55, 0.08, 0.06)
    col[stripe == 1] = (0.7, 0.52, 0.14)
    col[stripe == 2] = (0.42, 0.06, 0.05)
    col[stripe == 3] = (0.18, 0.12, 0.05)
    loz = (np.abs(((x + rng.normal(0, 1.5, (n, 1))) % 32) - 16) + np.abs((y % 32) - 16)) < 6
    col[loz & (stripe == 2)] = (0.78, 0.62, 0.2)
    out["triangle"] = _save("T_ep1_pillow_triangle_BC", col * _weave(n, rng, 0.04))
    # A ledger page in a clerk's hand: ruled lines, a red margin, Khmer-like loops of ink.
    out["ledger"] = _save("T_ep1_paper_ledger_BC", _ledger(rng))
    out["news"] = _save("T_ep1_paper_news_BC", _newspaper(rng))
    # Netting: a fine square mesh, the threads opaque, the holes clear.
    px = np.zeros((256, 256, 4), np.float32)
    px[..., :3] = (0.7, 0.7, 0.66)
    m = ((np.mgrid[0:256, 0:256][0] % 12) < 1) | ((np.mgrid[0:256, 0:256][1] % 12) < 1)
    px[..., 3] = np.where(m, 0.8, 0.0)   # sheer: thin threads, wide holes
    out["net"] = _save("T_ep1_mosquito_net_BC", px)
    return out


def _paper_ground(h, w, rng):
    base = np.zeros((h, w, 3), np.float32)
    base[:] = (0.62, 0.52, 0.36)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    edge = np.minimum(np.minimum(xx, w - xx), np.minimum(yy, h - yy)) / (0.12 * min(h, w))
    base *= (0.82 + 0.18 * np.clip(edge, 0, 1))[..., None]
    for _ in range(20):   # foxing
        cx, cy, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(2, 9)
        base *= (1 - 0.18 * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (r * r)))[..., None]
    return base, xx, yy


def _ledger(rng):
    h, w = 768, 512
    page, xx, yy = _paper_ground(h, w, rng)
    for k in range(48, h - 30, 22):
        page[k:k + 1, 30:w - 20] *= (0.72, 0.78, 0.86)
    page[:, 70:72] *= (1.0, 0.55, 0.5)
    ink = np.zeros((h, w), np.float32)
    for k in range(48, h - 40, 22):
        x = 82 + rng.uniform(0, 10)
        while x < w - 40 and rng.random() > 0.015:
            word = rng.uniform(22, 70)
            for t in np.linspace(0, 1, int(word)):
                px = int(x + t * word)
                py = int(k - 6 + 4 * math.sin(t * word * 0.9 + x) + 2 * math.sin(t * 31))
                if 0 <= py < h - 3 and px < w - 3:
                    ink[py:py + 3, px:px + 2] = 1
            x += word + rng.uniform(5, 10)
    page *= (1 - 0.75 * ink)[..., None] * np.array((1.0, 1.0, 1.0)) + 0
    page[ink > 0] = (0.08, 0.06, 0.1)
    # A bloom of damp and a brown ring where a cup stood.
    page *= (1 - 0.25 * np.exp(-(((xx - w * 0.7) ** 2 + (yy - h * 0.3) ** 2) / (w * w * 0.04))))[..., None]
    return page


def _newspaper(rng):
    h, w = 900, 640
    page, xx, yy = _paper_ground(h, w, rng)
    page *= 0.96
    page[40:96, 30:w - 30] *= 0.25          # the masthead
    cols = 4
    cw = (w - 60) / cols
    for c in range(cols):
        x0 = int(30 + c * cw + 6)
        x1 = int(30 + (c + 1) * cw - 6)
        y = 120
        while y < h - 40:
            if rng.random() < 0.08:
                page[y:y + 18, x0:x1] *= 0.35   # a headline
                y += 26
                continue
            if rng.random() < 0.03:
                page[y:y + 90, x0:x1] *= 0.55   # an engraving's grey block
                y += 98
                continue
            n = rng.integers(int((x1 - x0) * 0.6), x1 - x0)
            page[y:y + 4, x0:x0 + n] *= 0.3
            y += 7
    return page


def materials(m=None):
    m = dict(m or {})
    t = fabric_textures()
    for key in ("floral", "gingham", "embroidered", "triangle"):
        mat = image_material(f"M_hp_pillow_{key}", t[key], rough=0.92)
        mat.use_backface_culling = False
        m[f"pillow_{key}"] = mat
    m["triangle_end"] = library_material("rough_linen", "M_hp_triangle_end", tint=(0.42, 0.06, 0.05), tile=0.2)
    m["ledger_page"] = image_material("M_hp_ledger_page", t["ledger"], rough=0.95)
    m["news_page"] = image_material("M_hp_news_page", t["news"], rough=0.95)
    for key in ("ledger_page", "news_page"):
        m[key].use_backface_culling = False
    m["net"] = image_material("M_hp_mosquito_net", t["net"], rough=0.95, cutout=True)
    m["cotton"] = library_material("rough_linen", "M_hp_cotton", tint=(0.72, 0.68, 0.6), tile=0.4)
    m["cotton"].use_backface_culling = False
    m["sarong"] = m.get("silk") or m["pillow_triangle"]
    m["book_red"] = plain("M_hp_book_red", (0.3, 0.06, 0.04), rough=0.6)
    m["book_brown"] = plain("M_hp_book_brown", (0.22, 0.13, 0.07), rough=0.65)
    m["book_green"] = plain("M_hp_book_green", (0.1, 0.16, 0.1), rough=0.6)
    m["book_pages"] = plain("M_hp_book_pages", (0.7, 0.63, 0.48), rough=0.9)
    m["enamel"] = plain("M_hp_enamel", (0.82, 0.82, 0.76), rough=0.25)
    m["enamel_rim"] = plain("M_hp_enamel_rim", (0.08, 0.12, 0.25), rough=0.3)
    m["bottle_glass"] = plain("M_hp_bottle_glass", (0.25, 0.32, 0.2), rough=0.08, alpha=0.55)
    m["tin"] = library_material("rusty_metal", "M_hp_tin", tint=(0.42, 0.36, 0.3), tile=0.3)
    m["peg_wood"] = library_material("weathered_brown_planks", "M_hp_peg_wood", tint=(0.4, 0.32, 0.26), tile=0.5)
    return m


# ------------------------------------------------------------------ pillows


def pillow(b, mat, xf, L=0.56, W=0.36, H=0.14, rng=None, dent=0.35, piping=None, nu=30, nv=20):
    """A stuffed pillow lying on its broad face, built about its centre at z = 0 (its
    underside). Puffed in the middle, pinched to a piped seam all round, corners poking
    out a little, the dent of a head in the top and fine wrinkles running to the corners."""
    rng = rng or np.random.default_rng(0)
    seam = H * 0.42
    dx, dy = rng.normal(0, L * 0.08), rng.normal(0, W * 0.08)
    ph = rng.uniform(0, 6, 4)

    def outline(u, v):
        su, sv = 2 * u - 1, 2 * v - 1
        ear = 1 + 0.06 * (abs(su) * abs(sv)) ** 6     # the corners poke out
        return su * L / 2 * ear, sv * W / 2 * ear, abs(su), abs(sv)

    def puff(au, av):
        return max(0.0, 1 - au ** 2.4) ** 0.55 * max(0.0, 1 - av ** 2.4) ** 0.55

    def top(u, v):
        x, y, au, av = outline(u, v)
        p = puff(au, av)
        z = seam + (H - seam) * p
        z -= dent * (H - seam) * math.exp(-((x - dx) ** 2 / (L * 0.06) + (y - dy) ** 2 / (W * 0.08)))
        edge = (1 - p) * p * 4
        z += 0.004 * edge * math.sin(18 * math.atan2(y, x + 1e-6) + ph[0])          # wrinkles to the seam
        z += 0.002 * math.sin(x * 40 + ph[1]) * math.sin(y * 37 + ph[2]) * p
        return (x, y, z)

    def bottom(u, v):
        x, y, au, av = outline(u, 1 - v)
        p = puff(au, av)
        return (x, y, seam * (1 - min(1.0, p * 3.0) ** 0.5))

    b.grid(mat, lambda u, v: xf @ Vector(top(u, v)), nu, nv, uv=lambda u, v: (u * L / 0.25, v * W / 0.25))
    b.grid(mat, lambda u, v: xf @ Vector(bottom(u, v)), nu, nv, uv=lambda u, v: (u * L / 0.25, (1 - v) * W / 0.25))
    loop = []
    for k in range(4 * 24 + 1):
        t = k / 24
        side, f = int(t) % 4, t - int(t)
        u, v = [(f, 0.0), (1.0, f), (1 - f, 1.0), (0.0, 1 - f)][side]
        x, y, *_ = outline(u, v)
        loop.append(tuple(xf @ Vector((x * 1.002, y * 1.002, seam))))
    b.tube(piping or mat, loop, 0.0045, sides=6)


def triangle_pillow(b, m, xf, L=0.52, D=0.3, Hh=0.32, cells=10, rng=None):
    """The Khmer triangular pillow, lying on its base: a row of stuffed triangular cells
    sewn together, each puffing out between its seams; dark red patterned ends."""
    rng = rng or np.random.default_rng(1)
    tri = [(-D / 2, 0.0), (D / 2, 0.0), (D * 0.2, Hh)]
    cy, cz = sum(p[0] for p in tri) / 3, sum(p[1] for p in tri) / 3

    def rim(s, scale):
        """A point s (0..1) round the rounded triangle, scaled about its centre."""
        k = int(s * 3) % 3
        f = s * 3 - int(s * 3)
        a, c = tri[k], tri[(k + 1) % 3]
        y = a[0] + (c[0] - a[0]) * f
        z = a[1] + (c[1] - a[1]) * f
        bulge = 0.12 * math.sin(math.pi * f)   # soft, full sides
        y += (y - cy) * bulge
        z += (z - cz) * bulge
        return cy + (y - cy) * scale, cz + (z - cz) * scale

    for c in range(cells):
        x0 = -L / 2 + L * c / cells
        x1 = -L / 2 + L * (c + 1) / cells

        def cell(u, v, x0=x0, x1=x1):
            sc = 0.86 + 0.14 * math.sin(math.pi * v) ** 0.6
            y, z = rim(u, sc)
            return xf @ Vector((x0 + (x1 - x0) * v, y, max(0.0, z)))
        b.grid(m["pillow_triangle"], cell, 36, 6, uv=lambda u, v: (u * 3.6, v * 0.25))
    for side in (-1, 1):
        x = side * L / 2
        centre = xf @ Vector((x, cy, cz))
        ring = [xf @ Vector((x, *rim(s, 0.86))) for s in np.linspace(0, 1, 37)]
        verts = [tuple(centre)] + [tuple(p) for p in ring]
        faces = [(0, i + 1, i + 2) if side > 0 else (0, i + 2, i + 1) for i in range(36)]
        b.add(m["triangle_end"], verts, faces, [(0.5, 0.5)] + [(0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a)) for a in np.linspace(0, math.tau, 37)])


def sleeping_mat_bed(coll, b, m, x, y, z, rot, rng, mat_obj=None, pillows=("embroidered",), blanket=True):
    """A reed mat laid for sleeping, a pillow at its head and a folded cotton blanket."""
    c, s = math.cos(rot), math.sin(rot)
    xf = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, "Z")
    if mat_obj is not None:
        pts = [(x + c * dx - s * dy, y + s * dx + c * dy, z + 0.004) for dx, dy in ((-1.0, -0.45), (1.0, -0.45), (1.0, 0.45), (-1.0, 0.45))]
        mesh_object(f"hp_sleep_mat_{x:.1f}_{y:.1f}", coll, pts, [(0, 1, 2, 3)], mat_obj, uvs=[(0, 0), (2, 0), (2, 0.9), (0, 0.9)])
    for k, key in enumerate(pillows):
        pillow(b, m[f"pillow_{key}"], xf @ place(-0.72, -0.12 + 0.26 * k, 0.008, rz=rng.normal(0, 0.08)), rng=rng)
    if blanket:
        b.grid(m["cotton"], lambda u, v: xf @ Vector((0.1 + 0.7 * u, -0.38 + 0.76 * v,
                                                        0.012 + 0.03 * math.sin(math.pi * v) ** 2 + 0.008 * math.sin(u * 13 + v * 7))),
               20, 14, uv=lambda u, v: (u * 2.8, v * 3))


def mosquito_net(coll, m, x0, x1, y0, y1, z_floor, z_top, name, rng, knotted=False):
    """A net hung by its four corners from the ceiling: let down (its skirt slumped on the
    floor) or gathered up and knotted above the bed."""
    import colonial_house as CH
    ceiling = CH.ZW - 0.005   # the cords are tied to hooks in the ceiling boards
    tie = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)] if not knotted else []
    for k, (x, y) in enumerate(tie):
        tube(f"{name}_cord_{k}", coll, [(x, y, z_top), (x + rng.normal(0, 0.01), y, ceiling)], 0.0015, m["cotton"], sides=4)
    if knotted:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        b = Batch(f"{name}_knot")
        # Gathered up to the hook under the ceiling: a short soft bundle above head height,
        # its cord to the hook.
        top_z = min(z_floor + 2.45, ceiling - 0.12)
        tube(f"{name}_knot_cord", coll, [(cx, cy, top_z), (cx, cy, ceiling)], 0.002, m["cotton"], sides=4)
        b.lathe(m["net"], [(0.03, top_z - 0.8), (0.13, top_z - 0.66), (0.17, top_z - 0.4), (0.12, top_z - 0.14), (0.04, top_z), (0, top_z + 0.02)],
                xf=place(cx, cy, 0), segments=28, tile=0.5, radial=lambda a, h: 1 + 0.15 * math.sin(a * 7 + h * 9), cap=False)
        b.build(coll)
        return
    sag = 0.06
    top = mesh_object(f"{name}_top", coll, [(x0, y0, z_top), (x1, y0, z_top), (x1, y1, z_top), (x0, y1, z_top)], [(0, 1, 2, 3)], m["net"],
                      uvs=[(0, 0), ((x1 - x0) * 2, 0), ((x1 - x0) * 2, (y1 - y0) * 2), (0, (y1 - y0) * 2)])
    top.location.z -= sag / 2
    for side, (a0, a1, plane, axis) in enumerate(((x0, x1, y0, "x"), (x0, x1, y1, "x"), (y0, y1, x0, "y"), (y0, y1, x1, "y"))):
        o = cloth(f"{name}_side_{side}", coll, a0, a1, z_floor + 0.005, z_top, plane, m["net"], folds=int((a1 - a0) * 4) + 2, depth=0.035,
                  segments=(48, 18), axis=axis)
        o.data.materials[0].use_backface_culling = False


def hung_cloth(coll, m, mat, name, p0, p1, drop, folds=6, rng=None):
    """A sarong, krama or sheet thrown over a line or peg: one continuous cloth that goes up
    one side, over the line and down the other, the two halves parting a little lower
    down, soft irregular folds deepening towards an uneven hem."""
    rng = rng or np.random.default_rng(abs(hash(name)) % (2 ** 32))
    (x0, y0, z), (x1, y1, _) = p0, p1
    along = Vector((x1 - x0, y1 - y0, 0))
    width = along.length
    along.normalize()
    nrm = Vector((-along.y, along.x, 0))
    ph = rng.uniform(0, math.tau, 6)
    f1, f2 = rng.uniform(2.5, 4.5) * folds / 6, rng.uniform(6, 10) * folds / 6
    drops = (drop, drop * rng.uniform(0.7, 1.0))

    def pt(u, v):
        s_ = 2 * v - 1
        side = 1 if s_ >= 0 else -1
        a = abs(s_)
        hang = drops[0 if side < 0 else 1]
        hem = hang * (1 - 0.05 * math.sin(u * math.tau + ph[0]) - 0.04 * math.sin(u * 9 + ph[1]))
        top = min(1.0, a / 0.05)
        zz = z - hem * a + 0.013 * (1 - top)
        amp = 0.003 + 0.03 * a ** 0.8
        fold = amp * (0.7 * math.sin(u * math.pi * f1 + ph[2] + side) + 0.3 * math.sin(u * math.pi * f2 + ph[3]))
        out = side * (0.013 * top + 0.025 * a ** 1.6) + fold
        w = 1 - 0.08 * (1 - a)
        p = Vector((x0, y0, 0)) + along * (width * (0.5 + (u - 0.5) * w)) + nrm * out
        return (p.x, p.y, zz)
    b = Batch(name)
    b.grid(mat, pt, 26, 30, uv=lambda u, v: (u * width / 0.35, v * 2 * drop / 0.35), smooth=True)
    for o in b.build(coll).values():
        o.data.materials[0].use_backface_culling = False


def peg_rail(coll, m, name, x0, x1, y, z, toward, rng, hang=()):
    """A board of wooden pegs on a wall (along x at y, pegs sticking out to `toward`),
    and what hangs on them: (peg index, material key, drop), or (peg index, material key,
    drop, "dress") for a child's dress hung up by its neckline."""
    b = Batch(name)
    b.box(m["peg_wood"], (x1 - x0, 0.02, 0.09), ((x0 + x1) / 2, y + toward * 0.01, z), chamfer=0.004)
    n = max(2, int((x1 - x0) / 0.3))
    pegs = [x0 + (x1 - x0) * (k + 0.5) / n for k in range(n)]
    for px in pegs:
        b.tube(m["peg_wood"], [(px, y + toward * 0.02, z), (px, y + toward * 0.11, z + 0.03)], 0.011, sides=8, cap_end=True)
    b.build(coll)
    for k, (i, key, drop, *kind) in enumerate(hang):
        px = pegs[i % n]
        if kind and kind[0] == "dress":
            hung_dress(coll, m[key], f"{name}_dress_{k}", (px, y + toward * 0.085, z + 0.035), drop, toward, seed=k)
        else:
            hung_cloth(coll, m, m[key], f"{name}_hang_{k}", (px - 0.16, y + toward * 0.1, z + 0.02), (px + 0.16, y + toward * 0.1, z + 0.02),
                       drop, folds=5)


def hung_dress(coll, mat, name, peg, drop, toward, seed=0):
    """A girl's cotton dress hung on a peg by its neckline: the shoulders slope away from
    the peg, puffed short sleeves, a gathered waist, the skirt falling in soft folds to a
    hem that hangs a little unevenly. `toward` is the side of the wall it hangs out to."""
    px, py, pz = peg
    ph = 1.7 * seed + 0.4
    b = Batch(name)

    def half_width(v):        # across the wall
        return float(np.interp(v, (0.0, 0.07, 0.14, 0.32, 0.42, 1.0), (0.035, 0.115, 0.125, 0.11, 0.1, 0.19)))

    def half_depth(v):        # out from the wall
        return float(np.interp(v, (0.0, 0.1, 0.32, 0.42, 1.0), (0.012, 0.03, 0.035, 0.03, 0.055)))

    def pt(u, v):
        a = math.tau * u
        cx, cy = math.cos(a), math.sin(a)
        skirt = max(0.0, (v - 0.42) / 0.58)
        # Gathered at the waist, the skirt's folds deepening towards the hem.
        ripple = 1 + (0.05 + 0.13 * skirt) * skirt ** 0.5 * math.sin(a * 7 + ph) + 0.04 * skirt * math.sin(a * 13 + 2 * ph)
        x = half_width(v) * cx * ripple
        dy = half_depth(v) * cy * ripple
        # Hung from the peg at the neckline, the shoulders falling away to either side.
        top = 0.07 * min(1.0, abs(x) / 0.12) ** 1.4
        hem_sag = 0.018 * math.sin(a * 3 + ph) * skirt
        z = pz - top - (drop - 0.04) * v - hem_sag
        return (px + x, py + toward * (half_depth(0.42) + 0.006) + toward * dy, z)

    b.grid(mat, pt, 36, 18, uv=lambda u, v: (u * 1.6, v * drop / 0.3), smooth=True)
    # Short puffed sleeves at the shoulders, hanging down.
    for side in (-1, 1):
        s0 = (px + side * 0.105, py + toward * 0.04, pz - 0.075)
        s1 = (px + side * 0.15, py + toward * 0.04, pz - 0.15)
        b.tube(mat, [s0, ((s0[0] + s1[0]) / 2, s0[1], (s0[2] + s1[2]) / 2 - 0.005), s1], [0.034, 0.038, 0.028], sides=10, cap_end=False)
    # The neckline's binding, round the peg.
    b.tube(mat, [(px + 0.035 * math.cos(t), py + toward * (0.04 + 0.014 * math.sin(t)), pz - 0.004) for t in np.linspace(0, math.tau, 17)],
           0.005, sides=5)
    b.build(coll)


def books(b, m, x0, x1, y, z, depth, rng, toward=1, lean_last=True):
    """A row of books standing on a shelf from x0 to x1, spines toward `toward` (+y/-y)."""
    x = x0
    keys = ("book_red", "book_brown", "book_green", "ledger" if "ledger" in m else "book_brown")
    while x < x1 - 0.03:
        th, h = rng.uniform(0.025, 0.06), rng.uniform(0.17, 0.27)
        key = keys[rng.integers(0, len(keys))]
        cx = x + th / 2
        b.box(m[key], (th, depth, h), (cx, y, z + h / 2), chamfer=0.003)
        b.box(m["book_pages"], (th - 0.006, depth - 0.012, h - 0.012), (cx, y - toward * 0.004, z + h / 2), chamfer=0.001)
        x += th + 0.002
    if lean_last:
        th, h = 0.04, 0.24
        xf = Matrix.Translation((x + 0.09, y, z)) @ Matrix.Rotation(0.5, 4, "Y") @ Matrix.Translation((0, 0, h / 2))
        b.box(m["book_red"], (th, depth, h), (0, 0, 0), xf=xf, chamfer=0.003)


def enamel_cup(b, m, x, y, z, rng):
    b.lathe(m["enamel"], [(0, 0), (0.035, 0), (0.038, 0.07), (0.04, 0.075), (0.036, 0.075), (0.033, 0.008), (0, 0.008)],
            xf=place(x, y, z, rz=rng.uniform(0, 6)), segments=20, tile=0.1)
    b.lathe(m["enamel_rim"], [(0.0385, 0.071), (0.041, 0.074), (0.04, 0.077), (0.0375, 0.075)], xf=place(x, y, z), segments=20, tile=0.1)
    a = rng.uniform(0, 6)
    hx, hy = math.cos(a), math.sin(a)
    b.tube(m["enamel"], [(x + hx * 0.038, y + hy * 0.038, z + 0.058), (x + hx * 0.062, y + hy * 0.062, z + 0.045),
                         (x + hx * 0.04, y + hy * 0.04, z + 0.02)], 0.005, sides=6)


def bottle(b, m, x, y, z, rng, h=0.26):
    b.lathe(m["bottle_glass"], [(0, 0), (0.035, 0), (0.037, h * 0.62), (0.016, h * 0.8), (0.014, h), (0, h)],
            xf=place(x, y, z), segments=18, tile=0.1)


def kerosene_tin(b, m, x, y, z, rot=0.0):
    xf = place(x, y, z, rz=rot)
    b.box(m["tin"], (0.24, 0.24, 0.35), (0, 0, 0.175), xf=xf, chamfer=0.006)
    b.lathe(m["tin"], [(0, 0.35), (0.025, 0.35), (0.025, 0.38), (0, 0.38)], xf=xf @ Matrix.Translation((0.07, 0.07, 0)), segments=10, tile=0.1)
    b.tube(m["tin"], [tuple(xf @ Vector((-0.08, 0, 0.35))), tuple(xf @ Vector((0, 0, 0.42))), tuple(xf @ Vector((0.08, 0, 0.35)))], 0.004, sides=5)


def papers(coll, m, x0, x1, y0, y1, z, n, rng, name="hp_papers", news=0.3):
    """Pages drifted over a floor or a table: ledger pages and newspaper, curling."""
    b = Batch(name)
    for k in range(n):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        a = rng.uniform(0, math.tau)
        c, s = math.cos(a), math.sin(a)
        key = "news_page" if rng.random() < news else "ledger_page"
        w, h = (0.3, 0.42) if key == "news_page" else (0.2, 0.3)
        curl = rng.uniform(0.0, 0.03)

        def pt(u, v):
            dx, dy = (u - 0.5) * w, (v - 0.5) * h
            lift = curl * (abs(2 * u - 1) ** 3 + abs(2 * v - 1) ** 3)
            return (x + c * dx - s * dy, y + s * dx + c * dy, z + 0.001 + 0.0005 * k + lift)
        b.grid(m[key], pt, 4, 5, uv=lambda u, v: (u, v), smooth=True)
    b.build(coll)
