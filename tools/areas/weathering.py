"""Tileable weathering maps for Episode 2's neglected temple masonry.
Reference notes (docs/production/episode-2-visual-references.md): lime plaster on
old Khmer and Thai chedi blackens in long vertical runs of mould below every ledge,
greens with algae where it stays damp, spalls back to brick, and cracks.
Arrays are rows bottom-to-top as Blender stores pixels, so v runs up the wall.
"""
import math
import os

import bpy
import numpy as np

from kit import LIB, ROOT, image_material

OUT = os.path.join(ROOT, 'art-source/textures/ep2')


def tile_noise(size, cells, rng):
    """Smooth value noise that wraps at the image edge."""
    grid = rng.random((cells, cells))
    t = np.arange(size) * cells / size
    i0 = t.astype(int) % cells
    i1 = (i0 + 1) % cells
    f = t - np.floor(t)
    f = f * f * (3 - 2 * f)
    rows = grid[i0][:, i0] * (1 - f)[None, :] + grid[i0][:, i1] * f[None, :]
    rows1 = grid[i1][:, i0] * (1 - f)[None, :] + grid[i1][:, i1] * f[None, :]
    return rows * (1 - f)[:, None] + rows1 * f[:, None]


def fbm(size, rng, octaves=((4, .5), (9, .28), (23, .14), (61, .08))):
    out = sum(tile_noise(size, c, rng) * a for c, a in octaves)
    return (out - out.min()) / (np.ptp(out) or 1)


def mould_runs(size, rng, count=140, strength=1.0):
    """Darkness from water-borne mould: soft runs that start dense under a ledge and
    thin out downwards, gathered in clusters with broad stained sheets between them,
    rather than an even comb of stripes (which reads as wood grain)."""
    dark = np.zeros((size, size))
    cluster = tile_noise(size, 6, rng)
    for _ in range(count):
        u0 = rng.integers(0, size)
        start = rng.integers(0, size)
        weight = cluster[start, u0]
        if rng.random() > weight * 1.4:
            continue
        sheet = rng.random() < .3
        length = int(rng.uniform(.15, .8) * size)
        width = rng.uniform(18, 60) if sheet else rng.uniform(3, 12)
        amount = rng.uniform(.3, .75 if sheet else 1.0) * strength
        drift = rng.normal(0, .03)
        for step in range(0, length, 3):
            row = (start - step) % size
            t = step / length
            centre = u0 + drift * step
            w = width * (1 - .4 * t)
            lo, hi = int(centre - w * 1.8), int(centre + w * 1.8) + 1
            cols = np.arange(lo, hi)
            fall = np.exp(-((cols - centre) / max(w, .7)) ** 2) * amount * (1 - t) ** 1.2
            idx = cols % size
            for r in (row, (row - 1) % size, (row - 2) % size):
                dark[r, idx] = np.maximum(dark[r, idx], fall)
    # Break each run up so it fades in and out like real staining.
    dark *= .55 + .45 * tile_noise(size, 31, rng)
    return np.clip(dark, 0, 1)


def cracks(size, rng, count=26):
    """Hairline fissures: random walks that branch, a pixel or two wide."""
    mask = np.zeros((size, size), bool)
    for _ in range(count):
        x, y = rng.uniform(0, size, 2)
        a = rng.uniform(0, math.tau)
        for step in range(int(rng.uniform(60, 420))):
            a += rng.normal(0, .35)
            x, y = x + math.cos(a) * 1.5, y + math.sin(a) * 1.5
            xi, yi = int(x) % size, int(y) % size
            mask[yi, xi] = True
            mask[yi, (xi + 1) % size] = True
            if rng.random() < .006:
                a += rng.choice([-1, 1]) * rng.uniform(.6, 1.2)
    return mask


def photo_grain(source, size):
    photo = bpy.data.images.load(os.path.join(LIB, 'materials', source, source + '_BC.jpg'), check_existing=False)
    photo.scale(size, size)
    pixels = np.empty(size * size * 4, dtype=np.float32)
    photo.pixels.foreach_get(pixels)
    bpy.data.images.remove(photo)
    lum = pixels.reshape(size, size, 4)[:, :, :3].mean(axis=2)
    return np.clip(lum / (lum.mean() + .001), .4, 1.6)


def save(name, rgb, height, normal_strength=2.2):
    """Writes colour and a tangent-space normal derived from `height`."""
    size = rgb.shape[0]
    os.makedirs(OUT, exist_ok=True)
    rgba = np.ones((size, size, 4), dtype=np.float32)
    rgba[:, :, :3] = np.clip(rgb, 0, 1)
    path = os.path.join(OUT, name + '_BC.png')
    img = bpy.data.images.new(name + '_BC', width=size, height=size, alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    gy, gx = np.gradient(height)
    normal = np.ones((size, size, 4), dtype=np.float32)
    normal[:, :, 0] = .5 - np.clip(gx * normal_strength * size / 64, -.45, .45)
    normal[:, :, 1] = .5 - np.clip(gy * normal_strength * size / 64, -.45, .45)
    normal[:, :, 2] = .9
    npath = path.replace('_BC', '_N')
    # Relief this soft survives at half resolution; it halves the download.
    normal = normal.reshape(size // 2, 2, size // 2, 2, 4).mean(axis=(1, 3))
    ni = bpy.data.images.new(name + '_N', width=size // 2, height=size // 2, alpha=True)
    ni.colorspace_settings.name = 'Non-Color'
    ni.pixels.foreach_set(normal.ravel())
    ni.filepath_raw = npath
    ni.file_format = 'PNG'
    ni.save()
    return path, ni


def textured(mat_name, path, normal_image, rough, tile, strength=.8):
    mat = image_material(mat_name, path, rough=rough, tile=tile)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = normal_image
    n = nodes.new('ShaderNodeNormalMap')
    n.inputs['Strength'].default_value = strength
    links.new(tex.outputs['Color'], n.inputs['Color'])
    links.new(n.outputs['Normal'], mat.node_tree.nodes['Principled BSDF'].inputs['Normal'])
    return mat


def mouldy_plaster(name, colour, seed, mould=1.0, algae=.5, spall=.5, size=1024, tile=2.0):
    """Old lime plaster: photographic grain, broad damp tide-marks, black runs of
    mould, green algae blooms, hairline cracks and spalled patches of brick."""
    rng = np.random.default_rng(seed)
    grain = photo_grain('clay_plaster', size)
    damp = fbm(size, rng)
    blotch = fbm(size, rng, ((3, .6), (7, .3), (17, .1)))
    runs = mould_runs(size, rng, count=70, strength=mould * .8)
    base = np.array(colour)[None, None, :] * grain[:, :, None] * (.82 + .3 * damp)[:, :, None]
    # Algae greens and darkens the damp half; old soot and lichen bloom elsewhere.
    green = np.array([.11, .14, .07])
    wet = np.clip((blotch - .5) * 2.4, 0, 1) * algae
    rgb = base * (1 - wet[:, :, None] * .55) + green * wet[:, :, None] * .45
    black = np.array([.035, .038, .03])
    grime = fbm(size, rng, ((2, .5), (5, .3), (11, .2)))
    rgb *= (.7 + .45 * grime)[:, :, None]
    rgb = rgb * (1 - runs[:, :, None] * .5) + black * runs[:, :, None] * .5
    # Black crust: mottled colonies of mould and soot, the dominant look of old lime.
    crust = np.clip((fbm(size, rng, ((5, .45), (13, .3), (31, .17), (80, .08))) - .5) * 2.6, 0, 1) * mould
    rgb = rgb * (1 - crust[:, :, None] * .7) + black * crust[:, :, None] * .7
    # Faint lichen: strong pale flecks read as spots at a distance.
    lichen = (fbm(size, rng, ((40, .6), (90, .4))) > .82) & (damp > .45)
    rgb[lichen] = rgb[lichen] * .8 + np.array([.3, .32, .26]) * .2
    height = .6 * damp + .2 * grain - .25 * runs + .15 * crust
    # Spalls: the plaster has fallen in irregular scabs, showing brick and mortar.
    scab = fbm(size, rng, ((5, .55), (13, .3), (37, .15)))
    hole = scab > 1 - .12 * spall
    rim = (scab > 1 - .12 * spall - .03) & ~hole
    brick = np.array([.24, .1, .06]) * grain[:, :, None]
    yy, xx = np.mgrid[:size, :size]
    mortar = ((yy % 36) < 5) | (((xx + (yy // 36 % 2) * 77) % 154) < 5)
    brick[mortar] = (.09, .085, .075)
    rgb[hole] = brick[hole] * (1 - runs[hole, None] * .5)
    rgb[rim] *= .55
    height[hole] -= .35
    height[hole & mortar] -= .12
    crack = cracks(size, rng)
    rgb[crack] *= .3
    height[crack] -= .2
    path, normal = save(name, rgb, height)
    return textured('M_ep2_' + name.replace('T_ep2_', ''), path, normal, .93, tile)


def old_brick(name, seed, size=1024, tile=1.4, soot=.35):
    """Exposed Khmer brick: long thin bricks in staggered courses, eroded arrises,
    recessed lime mortar, salt bloom and soot from old fires."""
    rng = np.random.default_rng(seed)
    grain = photo_grain('clay_plaster', size)
    yy, xx = np.mgrid[:size, :size]
    course = 30
    row = yy // course
    col = (xx + (row % 2) * 70) // 140
    ids = (row * 131 + col * 71) % 997
    tone = rng.random(997)[ids]
    palette = np.array([[.27, .11, .06], [.32, .15, .08], [.2, .085, .05], [.14, .07, .05]])
    rgb = palette[(tone * 4).astype(int) % 4] * grain[:, :, None] * (.85 + .3 * tone[:, :, None])
    edge_y = np.minimum(yy % course, course - yy % course)
    edge_x = np.minimum((xx + (row % 2) * 70) % 140, 140 - (xx + (row % 2) * 70) % 140)
    mortar = (edge_y < 4) | (edge_x < 4)
    erosion = fbm(size, rng, ((19, .5), (53, .5)))
    mortar |= ((edge_y < 7) | (edge_x < 7)) & (erosion > .62)
    rgb[mortar] = np.array([.1, .095, .085]) * grain[mortar, None]
    salt = fbm(size, rng, ((6, .7), (15, .3))) > .72
    rgb[salt & ~mortar] = rgb[salt & ~mortar] * .6 + np.array([.42, .4, .34]) * .4
    sooty = fbm(size, rng, ((3, .7), (8, .3)))
    rgb *= (1 - soot * np.clip(sooty * 1.6 - .5, 0, 1))[:, :, None]
    runs = mould_runs(size, rng, count=120, strength=.7)
    rgb *= (1 - .7 * runs)[:, :, None]
    height = np.where(mortar, -.4, 0) + .25 * erosion + .1 * grain
    path, normal = save(name, rgb, height, 3.0)
    return textured('M_ep2_' + name.replace('T_ep2_', ''), path, normal, .9, tile, 1.0)


def eroded_stone(name, colour, seed, size=1024, tile=1.2):
    """Sandstone images and boundary stones: lichen rosettes, black crust, pitting."""
    rng = np.random.default_rng(seed)
    grain = photo_grain('clay_plaster', size)
    pits = fbm(size, rng, ((70, .5), (150, .5)))
    blotch = fbm(size, rng)
    rgb = np.array(colour)[None, None, :] * grain[:, :, None] * (.75 + .45 * blotch)[:, :, None]
    crust = fbm(size, rng, ((5, .6), (12, .4))) > .62
    rgb[crust] *= .68
    lichen = fbm(size, rng, ((24, .6), (60, .4))) > .8
    rgb[lichen] = rgb[lichen] * .7 + np.array([.5, .52, .4]) * .3
    runs = mould_runs(size, rng, count=100, strength=.7)
    rgb *= (1 - .55 * runs)[:, :, None]
    height = .5 * blotch - .5 * (pits < .3) + .1 * grain
    path, normal = save(name, rgb, height, 2.6)
    return textured('M_ep2_' + name.replace('T_ep2_', ''), path, normal, .92, tile, .9)
