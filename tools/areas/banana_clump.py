"""Episode 1's banana clump, grown here at true size (the user, Nov 19, 2026: the banana
plants were not detailed at all; their reference render ~/Downloads/tree/banana_plant.png
shows the look: tall yellow stems, long veined leaves torn along their veins, sun-scorched
orange-brown margins, pale papery dead leaves hanging down the stems). Both Tripo models
supplied for it (banana_plant.glb, "banana plants 3d model.fbx") are bare geometry with
no texture or UVs, so the clump is built and textured here instead:

- Six plants from one corm: two mothers (stems 2.1 and 2.7 m, the tallest with a bunch
  of green bananas and its purple bell), a middling one and three suckers.
- Each leaf a curved blade on its petiole, folded along its midrib, rippled at the
  margins, drooping with age; the youngest still a rolled "cigar" at the top; the oldest
  broken at the petiole and hanging down the stem, dead.
- Textures synthesised from the leaf's own coordinates (2K): the lateral veins leaving
  the midrib at 65 degrees, the pale midrib, mottling, tears along the veins from the
  margin in, scorched margins and tips, the tan dead leaf shredded into strips; a stem
  sheet of yellow-green streaks, dark blotches and sheath margins, the green fruit and
  the purple bracts of the bell.

    blender -b --factory-startup --python-exit-code 1 -P tools/areas/banana_clump.py \\
        [-- [--preview OUT.jpg] [--out DIR]]

Writes art-source/library/scans/banana_clump.glb (banana_clump, banana_clump_lod1,
banana_clump_lod2; the clump's foot at the origin, +Z up, 4.5 m tall) and the textures
art-source/textures/ep1/T_ep1_banana_clump_leaf_BC.png, T_ep1_banana_clump_leaf_N.png and
T_ep1_banana_clump_stem_BC.png. village_nature.flora() picks the file up on the next rebuild.
"""
import json
import math
import os
import random
import struct
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "art-source", "library", "scans", "banana_clump.glb")
TEX = os.path.join(ROOT, "art-source", "textures", "ep1")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[ARGS.index("--preview") + 1] if "--preview" in ARGS else None
# A preview can write its model and textures elsewhere, leaving the project untouched.
if "--out" in ARGS:
    OUT = os.path.join(ARGS[ARGS.index("--out") + 1], "banana_clump.glb")
    TEX = ARGS[ARGS.index("--out") + 1]

# Leaf atlas tiles (u ranges): living, scorched, old (yellowing, torn), dead.
TILES = {"green": 0, "scorch": 1, "old": 2, "dead": 3}
TILE_W = 0.25
# Stem sheet regions (u0, u1, v0, v1).
STEM = (0.0, 0.5, 0.0, 1.0)
PETIOLE = (0.0, 0.5, 0.86, 1.0)
FRUIT = (0.5, 1.0, 0.5, 1.0)
BELL = (0.5, 1.0, 0.0, 0.5)


# ----------------------------------------------------------------------- textures

def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def value_noise(h, w, cy, cx, rng):
    """Smooth value noise, h x w, with cy x cx cells."""
    g = rng.random((cy + 2, cx + 2))
    ys = np.linspace(0, cy, h, endpoint=False)
    xs = np.linspace(0, cx, w, endpoint=False)
    y0, x0 = ys.astype(int), xs.astype(int)
    fy, fx = ys - y0, xs - x0
    fy, fx = (fy * fy * (3 - 2 * fy))[:, None], (fx * fx * (3 - 2 * fx))[None, :]
    a, b = g[y0][:, x0], g[y0][:, x0 + 1]
    c, d = g[y0 + 1][:, x0], g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(h, w, cy, cx, rng, octaves=4):
    out, amp, tot = np.zeros((h, w)), 1.0, 0.0
    for k in range(octaves):
        out += amp * value_noise(h, w, cy * 2 ** k, cx * 2 ** k, rng)
        tot += amp
        amp *= 0.5
    return out / tot


def lerp(a, b, t):
    return a + (b - a) * t[..., None]


def rgb(*c):
    return np.array(c, dtype=np.float64)


def leaf_tile(kind, rng, H=2048, W=512):
    """One leaf of the atlas: u across the blade (0.5 the midrib), v base to tip.
    Returns sRGB colour + alpha (H, W, 4) and a height field for the normal map."""
    v = ((np.arange(H) + 0.5) / H)[:, None] * np.ones((1, W))
    u = ((np.arange(W) + 0.5) / W)[None, :] * np.ones((H, 1))
    s = (u - 0.5) * 2
    a = np.abs(s)
    X, Y = a * 0.25, v * 2.0                      # metres across from the midrib, along it
    jitter = 0.003 * (fbm(H, W, 64, 8, rng, 2) - 0.5)
    w = Y - X * 0.47 + jitter                     # constant along a lateral vein
    fine = (0.5 + 0.5 * np.cos(2 * math.pi * w / 0.0034)) ** 6
    major = (0.5 + 0.5 * np.cos(2 * math.pi * w / 0.0165)) ** 14
    mott = fbm(H, W, 24, 6, rng)
    spots = fbm(H, W, 90, 22, rng, 3)
    midrib = np.exp(-(a / 0.024) ** 2)
    rim = smoothstep(0.92, 1.0, a)

    if kind == "dead":
        col = lerp(rgb(0.88, 0.80, 0.66), rgb(0.74, 0.63, 0.48), mott)
        col = lerp(col, rgb(0.55, 0.43, 0.31), fine * 0.55 + major * 0.35)
        blot = smoothstep(0.6, 0.78, fbm(H, W, 30, 8, rng))
        col = lerp(col, rgb(0.47, 0.39, 0.31), blot * 0.7)
        col = lerp(col, rgb(0.86, 0.80, 0.66), midrib * 0.8)
        col = lerp(col, rgb(0.42, 0.31, 0.21), rim * 0.8)
    else:
        col = lerp(rgb(0.30, 0.47, 0.15), rgb(0.48, 0.65, 0.25), mott)
        col = lerp(col, rgb(0.56, 0.66, 0.28), smoothstep(0.8, 1.0, v) * 0.5)   # paler tip
        col = lerp(col, rgb(0.58, 0.66, 0.27), (1 - smoothstep(0.0, 0.1, v)) * 0.6)
        col = col * (1 - 0.13 * fine)[..., None] + 0.06 * major[..., None]
        col = lerp(col, rgb(0.70, 0.74, 0.40), midrib)
        col = lerp(col, rgb(0.44, 0.52, 0.18), rim * 0.6)
        col = lerp(col, rgb(0.33, 0.24, 0.10), smoothstep(0.985, 1.0, a))
        col = lerp(col, rgb(0.30, 0.36, 0.12), smoothstep(0.72, 0.9, spots) * 0.5)
        if kind in ("scorch", "old"):
            edge = fbm(H, W, 40, 6, rng)
            # Sun-scorch comes in patches along the margin and at the tip, not as a rim.
            patch = smoothstep(0.42, 0.62, fbm(H, W, 7, 2, rng, 3))
            reach = 0.6 if kind == "scorch" else 0.78
            burn = np.maximum(smoothstep(reach - 0.2 + 0.35 * edge, reach + 0.12 + 0.35 * edge, a) * patch,
                              smoothstep(0.78 + 0.12 * edge, 0.95, v))
            yellow = smoothstep(0.0, 0.4, burn) * (1 - smoothstep(0.4, 0.75, burn))
            col = lerp(col, rgb(0.70, 0.63, 0.30), yellow * 0.8)
            col = lerp(col, lerp(rgb(0.52, 0.35, 0.17), rgb(0.38, 0.25, 0.12), mott), smoothstep(0.4, 0.85, burn))
            col = lerp(col, rgb(0.30, 0.20, 0.10), smoothstep(0.85, 1.0, burn) * fine * 0.7)
        if kind == "old":
            patch = smoothstep(0.58, 0.75, fbm(H, W, 18, 5, rng))
            col = lerp(col, rgb(0.62, 0.62, 0.24), patch * 0.65)

    alpha = np.ones((H, W))
    tears = {"green": 9, "scorch": 14, "old": 22, "dead": 64}[kind]
    for _ in range(tears):
        w0 = rng.uniform(0.15, 1.92)
        side = 1 if rng.random() < 0.5 else -1
        depth = rng.uniform(0.5, 0.98) if kind == "dead" else rng.uniform(0.25, 0.85)
        # A dead leaf shreds into strips with dark gaps between them.
        width = rng.uniform(0.004, 0.016) if kind == "dead" else rng.uniform(0.0018, 0.0045)
        inside = (np.sign(s) == side) & (a > 1 - depth)
        open_ = width * (0.35 + 0.65 * (a - (1 - depth)) / depth)
        wob = 0.004 * np.sin(a * 23 + w0 * 40)
        alpha[inside & (np.abs(w - w0 - wob) < open_)] = 0
    bites = fbm(H, W, 120, 30, rng, 2)
    ragged = 0.035 if kind in ("old", "dead") else 0.012
    alpha[a > 1 - ragged * smoothstep(0.55, 0.8, bites) * 2] = 0
    alpha[v > 0.993 - 0.01 * bites] = 0

    height = 0.55 * major + 0.2 * fine + 1.6 * midrib + 0.12 * mott
    rgba = np.concatenate([np.clip(col, 0, 1), alpha[..., None]], axis=2)
    return rgba, height


def stem_sheet(rng, N=1024):
    """Stem (yellow-green, streaked, blotched, sheath margins), petiole tops, the green
    fruit and the purple bell's bracts, on one sheet."""
    img = np.zeros((N, N, 4))
    img[..., 3] = 1
    h, w = N, N // 2
    V = ((np.arange(h) + 0.5) / h)[:, None] * np.ones((1, w))
    U = ((np.arange(w) + 0.5) / w)[None, :] * np.ones((h, 1))
    streak = fbm(h, w, 6, 72, rng, 3)
    col = lerp(rgb(0.80, 0.66, 0.17), rgb(0.55, 0.62, 0.22), smoothstep(0.35, 0.95, V) * 0.8 + 0.2 * streak)
    col = col * (0.82 + 0.3 * streak)[..., None]
    sheath = (0.5 + 0.5 * np.cos(2 * math.pi * (V * 5.5 + U * 1.0 + 0.2 * fbm(h, w, 8, 8, rng)))) ** 40
    col = lerp(col, rgb(0.52, 0.38, 0.16), sheath * 0.7)
    blot = smoothstep(0.64, 0.8, fbm(h, w, 16, 12, rng))
    col = lerp(col, rgb(0.26, 0.18, 0.09), blot * 0.85)
    col = lerp(col, rgb(0.40, 0.30, 0.14), (1 - smoothstep(0.0, 0.16, V)) * 0.75)
    img[:, :w, :3] = np.clip(col, 0, 1)
    # The fruit: green skin, ridged along, freckled.
    fh, fw = N // 2, N // 2
    fv = ((np.arange(fh) + 0.5) / fh)[:, None] * np.ones((1, fw))
    fu = ((np.arange(fw) + 0.5) / fw)[None, :] * np.ones((fh, 1))
    ridge = (0.5 + 0.5 * np.cos(2 * math.pi * fu * 5)) ** 3
    fruit = lerp(rgb(0.32, 0.45, 0.14), rgb(0.44, 0.56, 0.20), fbm(fh, fw, 8, 8, rng) * 0.7 + ridge * 0.3)
    freck = smoothstep(0.78, 0.86, fbm(fh, fw, 64, 64, rng, 2))
    fruit = lerp(fruit, rgb(0.20, 0.24, 0.10), freck * 0.6)
    img[fh:, fw:, :3] = np.clip(fruit, 0, 1)
    # The bell: waxy dark purple-red bracts, paler where one laps the next.
    lap = (0.5 + 0.5 * np.cos(2 * math.pi * (fv * 7 + 0.15 * np.sin(fu * math.tau * 3)))) ** 8
    bell = lerp(rgb(0.30, 0.08, 0.12), rgb(0.40, 0.14, 0.20), fbm(fh, fw, 10, 10, rng))
    bell = lerp(bell, rgb(0.55, 0.28, 0.30), lap * 0.6)
    img[:fh, fw:, :3] = np.clip(bell, 0, 1)
    return img


def save_image(name, arr, path, non_color=False):
    h, w = arr.shape[:2]
    img = bpy.data.images.get(name) or bpy.data.images.new(name, w, h, alpha=True)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(arr.astype(np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    return img


def textures(rng):
    os.makedirs(TEX, exist_ok=True)
    tiles, heights = [], []
    for kind in ("green", "scorch", "old", "dead"):
        rgba, hgt = leaf_tile(kind, rng)
        tiles.append(rgba)
        heights.append(hgt)
    atlas = np.concatenate(tiles, axis=1)
    height = np.concatenate(heights, axis=1)
    gy, gx = np.gradient(height)
    k = 2.2
    n = np.stack([-gx * k, -gy * k, np.ones_like(gx)], axis=2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    nrm = np.concatenate([n * 0.5 + 0.5, np.ones(n.shape[:2] + (1,))], axis=2)
    leaf = save_image("T_ep1_banana_clump_leaf_BC", atlas, os.path.join(TEX, "T_ep1_banana_clump_leaf_BC.png"))
    leaf_n = save_image("T_ep1_banana_clump_leaf_N", nrm[::2, ::2], os.path.join(TEX, "T_ep1_banana_clump_leaf_N.png"), True)
    stem = save_image("T_ep1_banana_clump_stem_BC", stem_sheet(rng), os.path.join(TEX, "T_ep1_banana_clump_stem_BC.png"))
    return leaf, leaf_n, stem


# ----------------------------------------------------------------------- geometry

class Builder:
    """Vertices, faces, UVs and material indices for one LOD (0 leaf, 1 stem)."""

    def __init__(self):
        self.verts, self.faces, self.uvs, self.mats = [], [], [], []

    def grid(self, rows, uvrows, mat):
        """Quads between consecutive rows of points (each row the same length)."""
        base = len(self.verts)
        n = len(rows[0])
        for row, uvrow in zip(rows, uvrows):
            self.verts += [p[:] for p in row]
            self.uvs += uvrow
        for i in range(len(rows) - 1):
            for j in range(n - 1):
                a = base + i * n + j
                self.faces.append((a, a + 1, a + n + 1, a + n))
                self.mats.append(mat)

    def mesh(self, name, materials):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.verts, [], self.faces)
        uv = me.uv_layers.new(name="UVMap")
        loops = np.zeros(len(me.loops), dtype=np.int64)
        me.loops.foreach_get("vertex_index", loops)
        uvs = np.array(self.uvs, dtype=np.float64)[loops]
        uv.data.foreach_set("uv", uvs.ravel())
        me.polygons.foreach_set("material_index", self.mats)
        for m in materials:
            me.materials.append(m)
        me.shade_smooth()
        me.validate()
        obj = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(obj)
        return obj


def direction(elev, azim):
    return Vector((math.cos(elev) * math.cos(azim), math.cos(elev) * math.sin(azim), math.sin(elev)))


def tube(b, path, radius, sides, region, mat, v_scale=1.0, cap=False):
    """A tube along `path` (Vectors), `radius(i)`; UVs round (u) and along (v) a region."""
    u0, u1, v0, v1 = region
    rows, uvrows = [], []
    n = len(path)
    t_prev = None
    normal = None
    along = 0.0
    for i, p in enumerate(path):
        t = (path[min(n - 1, i + 1)] - path[max(0, i - 1)]).normalized()
        if normal is None:
            normal = t.cross(Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))).normalized()
        else:
            normal = (normal - t * normal.dot(t)).normalized()
        if i:
            along += (p - path[i - 1]).length
        bino = t.cross(normal)
        r = radius(i)
        row, uvrow = [], []
        for s in range(sides + 1):
            a = s / sides * math.tau
            row.append(p + (normal * math.cos(a) + bino * math.sin(a)) * r)
            uvrow.append((u0 + (u1 - u0) * s / sides, v0 + (v1 - v0) * min(1.0, along * v_scale)))
        rows.append(row)
        uvrows.append(uvrow)
        t_prev = t
    b.grid(rows, uvrows, mat)


def blade(b, start, azim, elev, length, width, droop, kind, nu, nv, rng, fold=0.22, ripple=0.035,
          twist=0.0, sag=0.25):
    """A banana leaf blade from `start`: its midrib leaves at (azim, elev) and bends down
    by `droop` radians towards the tip; the halves rise from the folded midrib, ripple and
    sag at the margins. UVs: across the blade (its tile), along it base to tip."""
    tile = TILES[kind]
    u0 = tile * TILE_W
    rows, uvrows = [], []
    p = Vector(start)
    phase = rng.uniform(0, math.tau)
    freq = rng.uniform(2.5, 4.5)
    for i in range(nv + 1):
        t = i / nv
        e = elev - droop * t ** 1.4
        az = azim + twist * 0.15 * t
        d = direction(e, az)
        side = Vector((-math.sin(az), math.cos(az), 0))
        roll = twist * t
        up = d.cross(side).normalized()
        side = (side * math.cos(roll) + up * math.sin(roll)).normalized()
        up = d.cross(side).normalized()
        if up.z < 0:
            up = -up
        prof = min(1.0, t / 0.1) ** 0.55 * max(0.0, 1 - max(0.0, (t - 0.78) / 0.22) ** 2) ** 0.5
        hw = width / 2 * max(prof, 0.06 if t < 0.999 else 0.0)
        row, uvrow = [], []
        for j in range(nu + 1):
            s = j / nu * 2 - 1
            a = abs(s)
            lift = (fold * a - sag * a * a * (0.4 + t)) * hw
            wave = ripple * math.sin(t * freq * math.tau + phase + s * 1.7) * a * a
            row.append(p + side * (s * hw) + up * (lift + wave))
            uvrow.append((u0 + (s * 0.5 + 0.5) * TILE_W * 0.998 + 0.001, t))
        rows.append(row)
        uvrows.append(uvrow)
        p = p + d * (length / nv)
    b.grid(rows, uvrows, 0)


def plant(b, base, stem_h, leaves, dead, lod, rng, fruit=False, lean=(0.0, 0.0)):
    """One pseudostem with its crown of leaves, its dead leaves and maybe a bunch."""
    nu, nv, sides, rings = [(8, 26, 10, 9), (4, 10, 6, 4), (2, 5, 4, 2)][lod]
    k = min(1.0, max(0.32, stem_h / 2.7))
    lean_v = Vector((lean[0], lean[1], 0))
    top = base + Vector((0, 0, stem_h)) + lean_v * stem_h
    r0, r1 = 0.07 + 0.09 * k, 0.045 + 0.05 * k
    path = [base + Vector((0, 0, -0.12))] + [base + (top - base) * (i / rings) for i in range(rings + 1)]
    tube(b, path, lambda i: (r0 * 1.25 if i <= 1 else r0 + (r1 - r0) * (i - 1) / rings), sides, STEM, 1,
         v_scale=1 / max(stem_h, 0.5))
    # The rolled young leaf at the top.
    if lod < 2:
        cig = [top + Vector((0, 0, 0.02)) + direction(1.45, rng.uniform(0, 6)) * (0.9 * k * i / 4) for i in range(5)]
        tube(b, cig, lambda i: max(0.006, r1 * 0.55 * (1 - i / 4.5)), max(4, sides // 2),
             (0.0, TILE_W * 0.18, 0.2, 0.9), 0)
    azim = rng.uniform(0, math.tau)
    for n in range(leaves):
        age = n / max(1, leaves - 1)               # 0 the youngest (upright) to 1 the oldest
        azim += math.radians(137.5) + rng.uniform(-0.25, 0.25)
        elev = math.radians(70 - 45 * age + rng.uniform(-6, 6))
        pet_len = (0.2 + 0.3 * k) * rng.uniform(0.8, 1.15)
        z0 = top.z - 0.05 - 0.25 * age * k
        p0 = Vector((top.x, top.y, z0))
        pet_dir = direction(elev + math.radians(8), azim)
        pts = [p0 + pet_dir * (pet_len * i / 3) for i in range(4)]
        if lod < 2:
            tube(b, pts, lambda i: 0.036 * k + 0.016 - 0.007 * i, max(4, sides // 2), PETIOLE, 1, v_scale=1 / 0.5)
        kind = "green" if age < 0.45 else rng.choice(["green", "scorch", "scorch", "old"])
        length = (1.35 + 1.0 * k) * rng.uniform(0.85, 1.12)
        width = (0.36 + 0.3 * k) * rng.uniform(0.85, 1.1)
        # The blade arches out from its petiole and only its outer half bends down.
        droop = math.radians(25 + 70 * age + rng.uniform(-8, 8))
        blade(b, pts[-1], azim, elev, length, width, droop, kind, nu, nv, rng,
              fold=rng.uniform(0.15, 0.32), ripple=0.012 + 0.012 * age, twist=rng.uniform(-0.5, 0.5),
              sag=0.15 + 0.35 * age)
    for n in range(dead if lod < 2 else min(dead, 1)):
        azim += math.radians(137.5) + rng.uniform(-0.4, 0.4)
        z0 = top.z - rng.uniform(0.0, 0.3) * k
        out = direction(math.radians(25), azim) * (r1 + 0.1 + 0.12 * k)
        start = Vector((top.x, top.y, z0)) + out
        length = (1.0 + 1.0 * k) * rng.uniform(0.85, 1.1)
        width = (0.24 + 0.2 * k) * rng.uniform(0.8, 1.05)
        # Broken at the petiole, the blade hangs down the stem, a little off it.
        blade(b, start, azim, math.radians(-78 - rng.uniform(0, 9)), length, width,
              math.radians(rng.uniform(-6, 4)), "dead", max(2, nu - 2), max(4, nv - 6), rng,
              fold=rng.uniform(0.25, 0.45), ripple=0.03, twist=rng.uniform(-0.45, 0.45), sag=0.2)
    if fruit and lod < 2:
        bunch(b, top, rng, lod)


def bunch(b, top, rng, lod):
    """The fruit stalk arching out and down from the crown, five hands of green bananas
    curving up along it, and the purple bell at its end."""
    azim = rng.uniform(0, math.tau)
    pts, p = [], top + Vector((0, 0, 0.05))
    for i in range(9):
        e = math.radians(40 - 26 * i)
        p = p + direction(e, azim) * 0.13
        pts.append(p)
    tube(b, [top] + pts, lambda i: 0.035 - 0.0015 * i, 6 if lod == 0 else 4, PETIOLE, 1, v_scale=2)
    for h in range(5):
        c = pts[3 + h]
        nf = 11 - h if lod == 0 else 4
        for f in range(nf):
            a = azim + math.pi + (f / max(1, nf - 1) - 0.5) * math.radians(200)
            radial = Vector((math.cos(a), math.sin(a), 0))
            fp = [c + radial * 0.05]
            for s in range(4 if lod == 0 else 2):
                d = (radial * (0.9 - 0.25 * s) + Vector((0, 0, 0.35 + 0.35 * s))).normalized()
                fp.append(fp[-1] + d * (0.045 if lod == 0 else 0.09))
            tube(b, fp, lambda i, n=len(fp): 0.016 * (1 - (i / (n - 1)) ** 3 * 0.75) + 0.004, 6 if lod == 0 else 3,
                 FRUIT, 1, v_scale=5)
    end = pts[-1]
    bell = [end + Vector((0, 0, -0.04 * i)) + direction(-1.3, azim) * 0.015 * i for i in range(7)]
    tube(b, bell, lambda i: 0.075 * math.sin(math.pi * min(0.98, (i + 0.6) / 7)) ** 0.7, 8 if lod == 0 else 5,
         BELL, 1, v_scale=3.5)


CLUMP = [  # x, y, stem height, leaves, dead leaves, fruit, lean
    (0.0, 0.0, 2.7, 10, 6, True, (0.03, -0.02)),
    (1.25, 0.75, 2.1, 9, 5, False, (0.06, 0.04)),
    (-1.15, 0.95, 1.55, 8, 4, False, (-0.07, 0.05)),
    (0.65, -1.2, 0.85, 7, 2, False, (0.03, -0.08)),
    (-0.9, -0.8, 0.38, 6, 1, False, (-0.06, -0.05)),
    (1.95, -0.45, 0.26, 5, 1, False, (0.09, -0.02)),
]


def build_lod(lod, leaf_mat, stem_mat):
    rng = random.Random(6242711)                   # the same plants at every LOD
    b = Builder()
    for x, y, h, leaves, dead, fruit, lean in CLUMP:
        plant(b, Vector((x, y, 0.0)), h, leaves if lod < 2 else max(4, leaves - 3), dead, lod, rng, fruit, lean)
    name = "banana_clump" if lod == 0 else f"banana_clump_lod{lod}"
    return b.mesh(name, [leaf_mat, stem_mat])


# ----------------------------------------------------------------------- materials

def material(name, image, normal=None, clip=False, roughness=0.6):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Specular IOR Level"].default_value = 0.4
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if clip:
        # The pattern Blender's glTF exporter reads as alphaMode MASK, cutoff 0.5.
        less = nt.nodes.new("ShaderNodeMath")
        less.operation = "LESS_THAN"
        less.inputs[1].default_value = 0.5
        sub = nt.nodes.new("ShaderNodeMath")
        sub.operation = "SUBTRACT"
        sub.inputs[0].default_value = 1.0
        nt.links.new(tex.outputs["Alpha"], less.inputs[0])
        nt.links.new(less.outputs["Value"], sub.inputs[1])
        nt.links.new(sub.outputs["Value"], bsdf.inputs["Alpha"])
        # Light through the leaf, as a banana leaf glows when the light is behind it.
        bsdf.inputs["Transmission Weight"].default_value = 0.0
        bsdf.inputs["Subsurface Weight"].default_value = 0.0
    if normal:
        nt_ = nt.nodes.new("ShaderNodeTexImage")
        nt_.image = normal
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = 0.8
        nt.links.new(nt_.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    m.surface_render_method = "DITHERED"
    m.use_backface_culling = False
    return m


def write(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=True, export_cameras=False, export_lights=False,
                              export_image_format="AUTO")
    with open(OUT, "rb") as f:
        glb = bytearray(f.read())
    n = struct.unpack("<I", glb[12:16])[0]
    doc = json.loads(glb[20:20 + n])
    tris = [sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs]
    doc["asset"]["extras"] = {
        "author": "Project (tools/areas/banana_clump.py)",
        "license": "project-owned",
        "title": "Banana clump",
        "adapted": f"grown and textured procedurally after the user's reference render; 4.5 m tall; "
                   f"{tris[0]} triangles (LOD1 {tris[1]}, LOD2 {tris[2]})",
    }
    text = json.dumps(doc, separators=(",", ":")).encode()
    text += b" " * ((4 - len(text) % 4) % 4)
    out = bytearray(glb[:12]) + struct.pack("<I", len(text)) + b"JSON" + text + glb[20 + n:]
    out[8:12] = struct.pack("<I", len(out))
    with open(OUT, "wb") as f:
        f.write(out)
    print(f"Wrote {OUT}: " + ", ".join(f"LOD{i} {t}" for i, t in enumerate(tris)) + " triangles", flush=True)


def preview(lod0, path):
    """A studio render like the reference: dark grey ground and sky, soft key light."""
    sc = bpy.context.scene
    for o in bpy.data.objects:
        if o.type == "MESH" and o is not lod0:
            o.hide_render = True
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.cycles.transparent_max_bounces = 64
    sc.render.resolution_x, sc.render.resolution_y = 1600, 940
    world = bpy.data.worlds.new("studio")
    world.color = (0.05, 0.05, 0.055)
    sc.world = world
    me = bpy.data.meshes.new("floor")
    me.from_pydata([(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)])
    fm = bpy.data.materials.new("floor")
    fm.diffuse_color = (0.04, 0.04, 0.042, 1)
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.035, 0.035, 0.038, 1)
    me.materials.append(fm)
    floor = bpy.data.objects.new("floor", me)
    sc.collection.objects.link(floor)
    for name, energy, rot, size in (("key", 4.5, (50, 0, 35), 2.0), ("fill", 1.2, (65, 0, 200), 8.0)):
        l = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN"))
        l.data.energy = energy
        l.data.angle = math.radians(size)
        l.rotation_euler = tuple(math.radians(a) for a in rot)
        sc.collection.objects.link(l)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens = 35
    cam.location = (1.6, -12.8, 3.2)
    cam.rotation_euler = (Vector((0.2, 0, 2.05)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.render.filepath = path
    sc.render.image_settings.file_format = "JPEG"
    bpy.ops.render.render(write_still=True)
    print("Preview", path, flush=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rng = np.random.default_rng(6242712)
    leaf, leaf_n, stem = textures(rng)
    leaf_mat = material("Leaf", leaf, leaf_n, clip=True, roughness=0.5)
    stem_mat = material("Stem", stem, roughness=0.62)
    lods = [build_lod(i, leaf_mat, stem_mat) for i in range(3)]
    write(lods)
    if PREVIEW:
        preview(lods[0], PREVIEW)


main()
