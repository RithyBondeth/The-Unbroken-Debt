"""Builds a photorealistic, heavily weathered 1932 Phnom Penh shophouse rear bathroom
(y = 14.0 .. 16.75, x = 0.0 .. 3.35) for Episode 1's studio prologue.

Every major surface uses weathered PBR (BaseColor + Normal + ORM) textures so nothing
reads flat, plastic or cartoonish:
- Aged octagonal mosaic floor tiles with worn patina, dark damp mildew grout, puddles
  and a recessed rusted cast-iron slotted floor drain.
- Hand-pressed 1930s celadon-ivory ceramic wall tiles with uneven glaze waviness, crazing,
  chipped edges, dark dampness creeping from the floor, rust drip streaks and exposed
  brick/render patches peeling through the damp limewash plaster above.
- Traditional Khmer tiled masonry water cistern (អាងទឹក) with interior waterline algae &
  limescale, dark reflective water (`haunt_bath_tank_water`), chipped blue enamel scoop
  (`haunt_bath_dipper`), brass bibcock tap with 3D pipe elbows/couplings & red shut-off
  wheel valve, weathered teak duckboard & worn wooden bath clogs.
- 1930s colonial wall-mounted porcelain sink with crazed/stained porcelain PBR, molded
  bullnose apron, twin brass cross-head faucets with porcelain caps, hanging brass drain
  chain & rubber plug, under-sink S-trap & shut-off valves, foxed & corner-cracked antique
  mirror (`bath_mirror_glass`), porcelain shelf with worn soap, chipped enamel mug,
  toothbrushes, straight razor, comb & vintage amber/green apothecary bottles.
- 1930s high-cistern pull-chain porcelain toilet with smooth curved ceramic S-horn,
  base bolts, weathered galvanized wall tank with raised molded panel, galvanized flush
  pipe, beaded brass pull-chain with ceramic handle & vintage wall-mounted paper roll.
- Weathered louvred teak bathroom door (`haunt_bath_door`), frosted louvred north window
  with rusted iron security bars & caged enamel pendant bulb (`marker_bath_bulb`).
"""

import math
import os

import bpy
import mathutils
import numpy as np

from kit import *  # noqa: F403

BATH_W = 3.35              # interior width (west party wall x=0 to east bath wall x=3.35)
BATH_P3 = (14.0, 14.15)    # masonry wall between back bedroom and bathroom
BATH_Y0 = BATH_P3[1]       # 14.15
BATH_Y1 = 16.75            # north outer wall inside face
BATH_H = 3.08              # slightly lower, more enclosed wet-room ceiling
BATH_FLOOR_Z = -0.02       # 2 cm wet-zone drop behind the doorway curb
BATH_DOOR = (1.98, 2.86)   # doorway in P3 (beside the family altar x 0.5..1.75 and bed x 3.42..4.28)
TILE_TOP = 1.56            # ceramic wall tile dado height


def _smooth_noise(xx, yy, N, cell, seed):
    r = np.random.default_rng(seed)
    gs = max(2, N // cell)
    g = r.random((gs, gs)).astype(np.float32)
    gx, gy = (xx / cell) % gs, (yy / cell) % gs
    ix, iy = gx.astype(int), gy.astype(int)
    fx, fy = gx - ix, gy - iy
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    ix1, iy1 = (ix + 1) % gs, (iy + 1) % gs
    a0 = g[iy, ix] * (1 - fx) + g[iy, ix1] * fx
    a1 = g[iy1, ix] * (1 - fx) + g[iy1, ix1] * fx
    return a0 * (1 - fy) + a1 * fy


def _fbm(xx, yy, N, seed):
    return (
        0.50 * _smooth_noise(xx, yy, N, max(8, N // 4), seed)
        + 0.30 * _smooth_noise(xx, yy, N, max(4, N // 12), seed + 1)
        + 0.20 * _smooth_noise(xx, yy, N, max(2, N // 32), seed + 2)
    )


def _normals_from_height(height, strength=0.8):
    gy_, gx_ = np.gradient(height)
    nrm = np.stack([-gx_ * strength, gy_ * strength, np.ones_like(gx_)], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    return nrm * 0.5 + 0.5


def _save_pbr_set(prefix, col, nrm, orm):
    paths = {}
    N = col.shape[0]
    for suffix, arr, non_color in (("BC", col, False), ("N", nrm, True), ("ORM", orm, True)):
        img = bpy.data.images.new(f"{prefix}_{suffix}", N, N, alpha=False)
        rgba = np.ones((N, N, 4), np.float32)
        rgba[..., :3] = np.clip(arr[::-1], 0, 1)
        if non_color:
            img.colorspace_settings.name = "Non-Color"
        img.pixels.foreach_set(rgba.ravel())
        path = os.path.join(TEXTURES, f"{prefix}_{suffix}.png")
        img.filepath_raw = path
        img.file_format = "PNG"
        img.save()
        paths[suffix] = path
    return paths


# =============================================================== weathered PBR materials


def bath_floor_tile_textures():
    """Heavily lived-in 1930s Phnom Penh wet-room mosaic: 10 cm cream-ochre octagonal
    porcelain tiles with weathered charcoal-slate corner dots, deeply stained mossy grout,
    surface scuffing, chipped tile edges, and realistic glossy wet puddles."""
    N, T = 1024, 8
    px = N // T
    yy, xx = np.mgrid[:N, :N].astype(np.float32)
    u = (xx % px) / px
    v = (yy % px) / px
    tx, ty = np.minimum((xx // px).astype(int), T - 1), np.minimum((yy // px).astype(int), T - 1)
    rng = np.random.default_rng(193201)

    ivory = np.array((0.58, 0.54, 0.44), np.float32)
    slate = np.array((0.12, 0.16, 0.14), np.float32)
    grout_c = np.array((0.11, 0.11, 0.09), np.float32)
    col = np.empty((N, N, 3), np.float32)
    col[:] = ivory

    d00 = np.abs(u) + np.abs(v)
    d10 = np.abs(1 - u) + np.abs(v)
    d01 = np.abs(u) + np.abs(1 - v)
    d11 = np.abs(1 - u) + np.abs(1 - v)
    dc = np.minimum(np.minimum(d00, d10), np.minimum(d01, d11))
    col[dc < 0.21] = slate

    # Per-tile kiln & age variation
    shade = rng.uniform(0.88, 1.07, (T, T)).astype(np.float32)
    warmth = rng.uniform(-0.025, 0.025, (T, T)).astype(np.float32)
    col *= shade[ty, tx][..., None]
    col[..., 0] += warmth[ty, tx]
    col[..., 2] -= warmth[ty, tx]

    # Uneven old grout lines (slightly wider/chipped organically)
    jitter = (_smooth_noise(xx, yy, N, 16, 15) - 0.5) * 0.012
    edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v)) + jitter
    grout = (edge < 0.032) | ((dc + jitter > 0.194) & (dc + jitter < 0.230))
    col[grout] = grout_c

    # Layered grime, damp mildew & wet puddles
    grime = _fbm(xx, yy, N, 11)
    puddle_field = _fbm(xx * 0.7, yy * 0.7, N, 17)
    puddle = np.clip((puddle_field - 0.54) * 4.5, 0, 1)
    # Dirt pools in low wear spots and damp mildew greens the grout
    col *= (0.76 + 0.30 * grime[..., None]) * (1.0 - 0.26 * puddle[..., None])
    mould = (grime < 0.44) & (edge < 0.09)
    col[mould] = col[mould] * 0.65 + np.array((0.08, 0.11, 0.06), np.float32) * 0.35

    # Micro pitting, mineral lime specks and hairline cracks
    speck = rng.random((N, N)).astype(np.float32)
    col *= 1.0 + (speck[..., None] - 0.5) * 0.08
    # A couple hairline floor-tile cracks
    for _ in range(4):
        cx, cy = rng.uniform(0, N), rng.uniform(0, N)
        ang = rng.uniform(0, math.pi)
        dx = (xx - cx) * math.cos(ang) + (yy - cy) * math.sin(ang)
        dy = -(xx - cx) * math.sin(ang) + (yy - cy) * math.cos(ang)
        wob = 3.5 * np.sin(dx * 0.07 + cx)
        crack = (np.abs(dy - wob) < 1.1) & (np.abs(dx) < 55) & (~grout)
        col[crack] *= 0.42

    # Uneven hand-laid tile tilt + recessed grout + slight surface pitting
    tilt_x = rng.uniform(-0.8, 0.8, (T, T)).astype(np.float32)
    tilt_y = rng.uniform(-0.8, 0.8, (T, T)).astype(np.float32)
    height = (
        np.where(grout, -1.2, 0.0)
        + tilt_x[ty, tx] * (u - 0.5) * 0.5
        + tilt_y[ty, tx] * (v - 0.5) * 0.5
        + (grime - 0.5) * 0.35
        + (speck - 0.5) * 0.14
    )
    nrm = _normals_from_height(height, 1.05)

    rough = np.where(grout, 0.90 - 0.45 * puddle, 0.42 - 0.32 * puddle + 0.18 * (1 - grime))
    rough = np.clip(rough, 0.05, 0.96)
    ao = np.where(grout, 0.52, np.clip(0.84 + 0.16 * grime, 0.65, 1.0))
    orm = np.stack([ao, rough, np.zeros_like(rough)], -1)
    return _save_pbr_set("T_studio_bath_floor", col, nrm, orm)


def bath_wall_tile_textures():
    """Weathered 1930s hand-pressed glazed celadon-ivory wall tiles (15 cm square):
    organic glaze waviness (hand-made ripples that catch lamplight!), crazing, browned
    damp grout, vertical mineral & rust-water streaks, subtle chipped corners."""
    N, T = 1024, 8
    px = N // T
    yy, xx = np.mgrid[:N, :N].astype(np.float32)
    u = (xx % px) / px
    v = (yy % px) / px
    tx, ty = np.minimum((xx // px).astype(int), T - 1), np.minimum((yy // px).astype(int), T - 1)
    rng = np.random.default_rng(193202)

    glaze = np.array((0.57, 0.59, 0.51), np.float32)
    grout_c = np.array((0.15, 0.14, 0.11), np.float32)
    col = np.empty((N, N, 3), np.float32)
    col[:] = glaze

    shade = rng.uniform(0.90, 1.07, (T, T)).astype(np.float32)
    col *= shade[ty, tx][..., None]

    # Hand-pressed organic glaze ripple & pillowed tile edge
    jitter = (_smooth_noise(xx, yy, N, 16, 25) - 0.5) * 0.008
    edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v)) + jitter
    bevel_h = np.clip(edge / 0.08, 0, 1)
    grout = edge < 0.022
    col[grout] = grout_c

    # Vertical mineral water streaks, brown damp stains, and mould creeping into grout
    streak = _smooth_noise(xx * 3.0, yy * 0.25, N, 64, 21)
    damp = _fbm(xx, yy, N, 22)
    col *= 0.80 + 0.24 * damp[..., None]
    drip = np.clip((streak - 0.56) * 2.4, 0, 1)[..., None]
    col = col * (1 - 0.34 * drip) + np.array((0.32, 0.25, 0.16), np.float32) * 0.34 * drip
    # Subtle dark patina along grout edges
    grout_halo = np.clip((0.065 - edge) / 0.045, 0, 1) * (1 - grout.astype(np.float32))
    col *= 1.0 - 0.22 * grout_halo[..., None] * (1.2 - damp[..., None])

    # Chipped tile glaze specks showing raw terracotta-cream biscuit beneath
    for _ in range(18):
        cx, cy = rng.uniform(0, N), rng.uniform(0, N)
        rad = rng.uniform(2.5, 6.5)
        d = np.hypot(xx - cx, yy - cy)
        chip = d < rad
        col[chip] = np.array((0.46, 0.39, 0.30), np.float32) * rng.uniform(0.85, 1.05)

    # Fine hand-made glaze undulation (makes reflections look genuinely real, never flat!)
    wave = _smooth_noise(xx, yy, N, 32, 27) * 0.45 + _smooth_noise(xx, yy, N, 64, 28) * 0.35
    speck = rng.random((N, N)).astype(np.float32)
    col *= 1.0 + (speck[..., None] - 0.5) * 0.05

    height = np.where(grout, -1.25, (bevel_h - 1.0) * 0.55 + (wave - 0.4) * 0.28)
    nrm = _normals_from_height(height, 0.92)

    rough = np.where(grout, 0.92, 0.16 + 0.22 * (1 - damp) + 0.24 * drip[..., 0])
    rough = np.clip(rough, 0.09, 0.96)
    ao = np.where(grout, 0.54, np.clip(0.88 + 0.12 * damp, 0.72, 1.0))
    orm = np.stack([ao, rough, np.zeros_like(rough)], -1)
    return _save_pbr_set("T_studio_bath_wall_tiles", col, nrm, orm)


def bath_cistern_tile_textures():
    """Deep weathered colonial teal-cobalt tiles for the Khmer water tank (អាងទឹក):
    heavy white calcium limescale crusts, damp algae-green grout, glaze waviness."""
    N, T = 512, 4
    px = N // T
    yy, xx = np.mgrid[:N, :N].astype(np.float32)
    u = (xx % px) / px
    v = (yy % px) / px
    tx, ty = np.minimum((xx // px).astype(int), T - 1), np.minimum((yy // px).astype(int), T - 1)
    rng = np.random.default_rng(193203)

    teal = np.array((0.13, 0.26, 0.27), np.float32)
    col = np.empty((N, N, 3), np.float32)
    col[:] = teal
    shade = rng.uniform(0.84, 1.12, (T, T)).astype(np.float32)
    col *= shade[ty, tx][..., None]

    edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
    grout = edge < 0.032
    col[grout] = np.array((0.28, 0.30, 0.25), np.float32)

    # Mineral limescale & dark damp algae streaks
    scale = _fbm(xx, yy, N, 31)
    streak = _smooth_noise(xx * 2.5, yy * 0.3, N, 32, 33)
    lime = np.clip((scale - 0.56) * 2.6, 0, 1)[..., None] * 0.42
    col = col * (1 - lime) + np.array((0.64, 0.63, 0.56), np.float32) * lime
    algae = np.clip((0.42 - streak) * 2.5, 0, 1)[..., None] * 0.38
    col = col * (1 - algae) + np.array((0.06, 0.11, 0.06), np.float32) * algae

    wave = _smooth_noise(xx, yy, N, 24, 34)
    height = np.where(grout, -1.2, (np.clip(edge / 0.08, 0, 1) - 1.0) * 0.45 + (wave - 0.5) * 0.25)
    nrm = _normals_from_height(height, 0.9)
    rough = np.clip(np.where(grout, 0.92, 0.14 + 0.42 * lime[..., 0] + 0.15 * (1 - scale)), 0.10, 0.95)
    orm = np.stack([np.where(grout, 0.55, 1.0), rough, np.zeros_like(rough)], -1)
    return _save_pbr_set("T_studio_bath_cistern", col, nrm, orm)


def aged_porcelain_textures():
    """Weathered 1930s sanitary porcelain (sink, toilet bowl, coping rim, soap dish):
    warm ivory-bone glaze with fine mineral staining, subtle crazing, rust-tea tint in
    crevices and glossy-to-chalky worn roughness."""
    N = 512
    yy, xx = np.mgrid[:N, :N].astype(np.float32)
    rng = np.random.default_rng(193205)
    mottle = _fbm(xx, yy, N, 51)
    streak = _smooth_noise(xx * 2.2, yy * 0.35, N, 32, 52)
    col = np.full((N, N, 3), (0.74, 0.72, 0.65), np.float32)
    col *= 0.90 + 0.14 * mottle[..., None]
    stain = np.clip((streak - 0.62) * 2.8, 0, 1)[..., None] * 0.28
    col = col * (1 - stain) + np.array((0.48, 0.38, 0.26), np.float32) * stain
    speck = rng.random((N, N)).astype(np.float32)
    col *= 1.0 + (speck[..., None] - 0.5) * 0.04
    height = (mottle - 0.5) * 0.18 + (speck - 0.5) * 0.06
    nrm = _normals_from_height(height, 0.4)
    rough = np.clip(0.14 + 0.18 * (1 - mottle) + 0.28 * stain[..., 0], 0.10, 0.68)
    orm = np.stack([np.clip(0.9 + 0.1 * mottle, 0.8, 1.0), rough, np.zeros_like(rough)], -1)
    return _save_pbr_set("T_studio_bath_porcelain", col, nrm, orm)


def weathered_galv_textures():
    """Weathered 1930s galvanized iron & painted zinc (high toilet cistern tank, flush pipe,
    wash bucket): dull zinc mottling, rust blooms, mineral water runs and varied metalness."""
    N = 512
    yy, xx = np.mgrid[:N, :N].astype(np.float32)
    rng = np.random.default_rng(193206)
    spangle = _fbm(xx, yy, N, 61)
    rust_n = _fbm(xx * 1.3, yy * 0.7, N, 62)
    rust = np.clip((rust_n - 0.58) * 3.5, 0, 1)
    base = np.array((0.40, 0.42, 0.40), np.float32) * (0.78 + 0.38 * spangle[..., None])
    rust_c = np.array((0.28, 0.14, 0.07), np.float32) * (0.8 + 0.3 * rng.random((N, N, 1)).astype(np.float32))
    col = base * (1 - rust[..., None]) + rust_c * rust[..., None]
    height = (spangle - 0.5) * 0.25 + rust * 0.45
    nrm = _normals_from_height(height, 0.7)
    rough = np.clip(0.38 + 0.22 * (1 - spangle) + 0.35 * rust, 0.28, 0.94)
    metal = np.clip(0.76 - 0.62 * rust, 0.08, 0.82)
    orm = np.stack([np.clip(0.82 + 0.18 * spangle, 0.65, 1.0), rough, metal], -1)
    return _save_pbr_set("T_studio_bath_galv", col, nrm, orm)


def aged_copper_textures():
    """Oxidized 1930s copper/brass water pipes with dark tarnish and green verdigris patina."""
    N = 512
    yy, xx = np.mgrid[:N, :N].astype(np.float32)
    n1 = _fbm(xx, yy, N, 71)
    n2 = _fbm(xx * 1.5, yy * 0.8, N, 72)
    verd = np.clip((n2 - 0.60) * 3.4, 0, 1)
    copper = np.array((0.34, 0.22, 0.14), np.float32) * (0.72 + 0.45 * n1[..., None])
    verd_c = np.array((0.22, 0.38, 0.30), np.float32)
    col = copper * (1 - verd[..., None]) + verd_c * verd[..., None]
    nrm = _normals_from_height((n1 - 0.5) * 0.25 + verd * 0.4, 0.65)
    rough = np.clip(0.34 + 0.24 * (1 - n1) + 0.40 * verd, 0.24, 0.94)
    metal = np.clip(0.86 - 0.72 * verd, 0.08, 0.90)
    orm = np.stack([np.clip(0.84 + 0.16 * n1, 0.7, 1.0), rough, metal], -1)
    return _save_pbr_set("T_studio_bath_copper", col, nrm, orm)


def chipped_enamel_textures():
    """Chipped colonial blue-grey enamelled iron for the water scoop (ផ្ដិល): glossy enamel
    with dark iron chips, rust halos and water-scale rings."""
    N = 512
    yy, xx = np.mgrid[:N, :N].astype(np.float32)
    rng = np.random.default_rng(193207)
    mottle = _fbm(xx, yy, N, 81)
    col = np.array((0.18, 0.28, 0.34), np.float32) * (0.86 + 0.24 * mottle[..., None])
    chip_mask = np.zeros((N, N), np.float32)
    for _ in range(28):
        cx, cy = rng.uniform(0, N), rng.uniform(0, N)
        rad = rng.uniform(3, 12)
        d = np.hypot(xx - cx, yy - cy)
        chip_mask = np.maximum(chip_mask, np.clip(1.0 - d / rad, 0, 1))
    iron_hit = chip_mask > 0.45
    rust_ring = (chip_mask > 0.15) & (~iron_hit)
    col[rust_ring] = col[rust_ring] * 0.45 + np.array((0.30, 0.15, 0.07), np.float32) * 0.55
    col[iron_hit] = np.array((0.06, 0.055, 0.05), np.float32)
    nrm = _normals_from_height(-chip_mask * 0.5 + (mottle - 0.5) * 0.12, 0.7)
    rough = np.clip(np.where(iron_hit, 0.72, 0.20 + 0.16 * (1 - mottle) + 0.35 * rust_ring), 0.14, 0.88)
    metal = np.where(iron_hit, 0.65, 0.05).astype(np.float32)
    orm = np.stack([np.ones_like(rough), rough, metal], -1)
    return _save_pbr_set("T_studio_bath_enamel", col, nrm, orm)


def bath_mirror_material():
    """Antique 1930s silvered bathroom mirror: dark mercury-glass reflection, heavy
    copper-black desilvering creeping from edges, pinhead foxing, subtle condensation haze,
    and a realistic hairline corner crack."""
    N = 512
    yy, xx = np.mgrid[:N, :N].astype(np.float32) / N
    rng = np.random.default_rng(193204)
    col = np.full((N, N, 3), (0.28, 0.32, 0.30), np.float32)

    edge = np.minimum(np.minimum(xx, 1 - xx), np.minimum(yy, 1 - yy))
    fox_noise = _fbm(xx * N, yy * N, N, 41)
    desilver = np.clip((0.14 - edge) * 8.5 + (fox_noise - 0.50) * 1.5, 0, 1)
    col = col * (1 - 0.76 * desilver[..., None]) + np.array((0.09, 0.07, 0.05), np.float32) * 0.76 * desilver[..., None]

    for _ in range(130):
        cx, cy = rng.uniform(0.02, 0.98), rng.uniform(0.02, 0.98)
        rad = rng.uniform(0.004, 0.020) * (1.8 if min(cx, 1 - cx, cy, 1 - cy) < 0.22 else 0.75)
        d = np.hypot(xx - cx, yy - cy)
        spot = np.clip(1 - d / rad, 0, 1) ** 1.5
        col = col * (1 - 0.68 * spot[..., None]) + np.array((0.07, 0.06, 0.045), np.float32) * 0.68 * spot[..., None]

    # Realistic hairline crack across the upper-right corner of the mirror glass
    crack_d = np.abs((xx - 0.74) * 0.82 - (yy - 0.76) * 0.57 + 0.012 * np.sin(xx * 42))
    crack = (crack_d < 0.003) & (xx > 0.70) & (yy > 0.72)
    col[crack] = np.array((0.05, 0.06, 0.055), np.float32)

    mist = _fbm(xx * N * 0.8, yy * N * 0.8, N, 45)
    rough = np.clip(0.05 + 0.48 * desilver + 0.18 * np.clip(mist - 0.45, 0, 1) + 0.4 * crack, 0.04, 0.78)
    metal = np.clip(0.94 - 0.78 * desilver - 0.5 * crack, 0.12, 0.95)
    nrm = _normals_from_height(-crack.astype(np.float32) * 0.8 + desilver * 0.12, 0.9)
    orm = np.stack([np.ones_like(rough), rough, metal], -1)
    return _save_pbr_set("T_studio_bath_mirror", col, nrm, orm)


def vintage_wall_switch(area, m, turned, prefix, pos, rot, toggle_angle_deg=26, parent_empty=None):
    """Museum-grade 1930s French-Indochina Bakelite & brass tumbler wall switch:
    bevelled circular rosewood pattress block, stepped glossy ebonite dome cover,
    slotted brass mounting screws, machined brass ferrule collar, sculpted teardrop
    brass dolly lever, and top porcelain cord-entry grommet (zero cartoon cubes!)."""
    root = parent_empty or empty(f"{prefix}_root", area, pos, rot)
    bpy.context.view_layer.update()
    parts = []
    # 1. Bevelled circular dark rosewood pattress mounting block
    pattress = [
        (0.0, 0.0), (0.044, 0.0), (0.044, 0.005), (0.041, 0.011), (0.037, 0.014), (0.0, 0.014)
    ]
    parts.append(turned(f"{prefix}_pattress", pattress, 0, 0, 0, m["rosewood"], segments=28))
    # 2. Stepped circular glossy ebonite/Bakelite dome switch housing with grooved rim
    dome = [
        (0.0, 0.014), (0.032, 0.014), (0.032, 0.019), (0.030, 0.021), (0.030, 0.024),
        (0.025, 0.029), (0.018, 0.032), (0.012, 0.033), (0.0, 0.033)
    ]
    parts.append(turned(f"{prefix}_dome", dome, 0, 0, 0, m["ebonite"], segments=28))
    # 3. Machined brass threaded ferrule collar & lock ring
    collar = [
        (0.0, 0.032), (0.0115, 0.032), (0.0115, 0.036), (0.009, 0.039), (0.007, 0.042), (0.0, 0.042)
    ]
    parts.append(turned(f"{prefix}_collar", collar, 0, 0, 0, m["brass"], segments=18))
    # 4. Two slotted brass mounting screws flanking the switch dome
    for s_idx, sx_ in enumerate((-0.022, 0.022)):
        sc = turned(f"{prefix}_screw_{s_idx}", [(0.0, 0.0), (0.0036, 0.0), (0.0034, 0.0018), (0.0, 0.0026)], sx_, 0.0, 0.025, m["brass"], segments=10)
        parts.append(sc)
        slot = box(f"{prefix}_screw_slot_{s_idx}", area, sx_ - 0.003, sx_ + 0.003, -0.0005, 0.0005, 0.0268, 0.0278, m["dark"])
        parts.append(slot)
    # 5. Sculpted teardrop brass tumbler dolly lever (angled crisply at toggle_angle_deg)
    lever_pivot = empty(f"{prefix}_lever", area, (0, 0, 0.040), (math.radians(toggle_angle_deg), 0, 0))
    lever_pivot.parent = root
    dolly = [
        (0.0, 0.0), (0.0028, 0.0), (0.0024, 0.008), (0.0046, 0.016),
        (0.0064, 0.021), (0.0056, 0.025), (0.0025, 0.027), (0.0, 0.0275)
    ]
    lev_mesh = turned(f"{prefix}_dolly", dolly, 0, 0, 0, m["brass"], segments=16)
    lev_mesh.parent = lever_pivot
    # 6. Top porcelain cord-entry grommet on the pattress rim
    grom = turned(f"{prefix}_grommet", [(0.0, 0.0), (0.006, 0.0), (0.0055, 0.007), (0.0035, 0.009), (0.0, 0.009)], 0, 0, 0, m["porcelain"], segments=12)
    grom.location = (0.0, 0.042, 0.007)
    grom.rotation_euler = (-math.pi / 2, 0, 0)
    parts.append(grom)
    for p in parts:
        p.parent = root
    return root


def _sculpt_porcelain_sink(area, name, sx, sy, sz, y1, mat):
    """Builds a single seamless, watertight 1930s colonial cast-porcelain wall-mounted
    lavabo basin (rounded outer rectangular apron smoothly carved into a deep curved
    oval washbasin — zero separate deck boxes and zero black corner gaps!)."""
    import bmesh

    hx = 0.30
    hy_neg = 0.21
    hy_pos = y1 - 0.012 - sy
    rc = 0.036
    rx, ry = 0.208, 0.122
    by_off = -0.028

    def rect_ray(dx, dy):
        tx = (hx / abs(dx)) if abs(dx) > 1e-6 else 1e9
        ty = (hy_pos / dy) if dy > 1e-6 else ((-hy_neg / dy) if dy < -1e-6 else 1e9)
        t = min(tx, ty)
        px, py = dx * t, dy * t
        # Only round the front two corners tightly; rear corners sit crisp against wall
        # Use r_use consistently in ix/iy clamping so left/right edges stay 100% straight!
        r_use = rc if py < 0 else 0.012
        ix = max(-(hx - r_use), min(hx - r_use, px))
        iy = max(-(hy_neg - r_use), min(hy_pos - r_use, py))
        vx, vy = px - ix, py - iy
        d = math.hypot(vx, vy)
        if d > r_use:
            px, py = ix + vx * (r_use / d), iy + vy * (r_use / d)
        return px, py

    n_ang = 56
    # Profile steps from inner drain -> curved bowl -> rounded lip -> deck -> bullnose -> outer apron -> underside -> drain bottom
    rings = []
    # 0: drain hole perimeter (z = -0.142)
    # 1..6: curved concave bowl wall
    bowl_steps = [
        (0.022 / rx, -0.142),
        (0.28, -0.138),
        (0.54, -0.122),
        (0.76, -0.092),
        (0.91, -0.048),
        (0.985, -0.005),
        (1.00, 0.020),
    ]
    # 7..10: rounded lip & top deck rim out to outer edge
    deck_steps = [
        (0.06, 0.026),
        (0.45, 0.026),
        (0.88, 0.025),
        (0.98, 0.021),
        (1.00, 0.012),
    ]
    # 11..15: outer vertical apron + curved bottom porcelain belly back to bottom center
    outer_steps = [
        (1.00, -0.042),
        (0.97, -0.052),
        (0.82, -0.062),
        (0.55, -0.125),
        (0.28, -0.155),
        (0.08, -0.160),
    ]

    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    ring_verts = []
    for k_i in range(len(bowl_steps) + len(deck_steps) + len(outer_steps)):
        row = []
        for a_i in range(n_ang):
            ang = a_i * math.tau / n_ang
            ca, sa = math.cos(ang), math.sin(ang)
            ox, oy = rect_ray(ca, sa)
            bx, by = rx * ca, by_off + ry * sa
            if k_i < len(bowl_steps):
                frac, dz = bowl_steps[k_i]
                px = bx * frac
                py = by_off + (by - by_off) * frac
            elif k_i < len(bowl_steps) + len(deck_steps):
                u, dz = deck_steps[k_i - len(bowl_steps)]
                px = bx + (ox - bx) * u
                py = by + (oy - by) * u
            else:
                s_scale, dz = outer_steps[k_i - len(bowl_steps) - len(deck_steps)]
                if s_scale >= 0.8:
                    px = ox * s_scale
                    py = oy * s_scale if oy < 0 else min(hy_pos, oy * s_scale)
                else:
                    # Blend smoothly toward underside of oval bowl
                    u_b = s_scale / 0.8
                    px = bx * (0.25 + 0.75 * u_b)
                    py = by_off + (by - by_off) * (0.25 + 0.75 * u_b)
            row.append(bm.verts.new((sx + px, sy + py, sz + dz)))
        ring_verts.append(row)

    # Cap inner drain center & outer bottom center
    v_in = bm.verts.new((sx, sy + by_off, sz - 0.143))
    v_out = bm.verts.new((sx, sy + by_off, sz - 0.161))

    for a_i in range(n_ang):
        b_i = (a_i + 1) % n_ang
        bm.faces.new((v_in, ring_verts[0][a_i], ring_verts[0][b_i]))
        bm.faces.new((v_out, ring_verts[-1][b_i], ring_verts[-1][a_i]))

    for r_i in range(len(ring_verts) - 1):
        r0, r1 = ring_verts[r_i], ring_verts[r_i + 1]
        for a_i in range(n_ang):
            b_i = (a_i + 1) % n_ang
            bm.faces.new((r0[a_i], r1[a_i], r1[b_i], r0[b_i]))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
        for loop in f.loops:
            co = loop.vert.co
            loop[uv_layer].uv = ((co.x - sx) * 1.45 + 0.5, (co.y - sy + (co.z - sz) * 0.7) * 1.45 + 0.5)

    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    area.objects.link(o)
    return o


def build_bathroom(area, m, helpers):
    """Builds the P3 dividing wall, weathered louvred bathroom door, damp tiled wet room,
    Khmer water cistern, colonial sink & cracked antique mirror, high-cistern pull-chain
    toilet, 3D fitted copper/iron plumbing, north frosted window, lighting & 1932 clutter."""
    wall = helpers["wall"]
    turned = helpers["turned"]
    draped = helpers["draped"]
    attach = helpers["attach"]
    textured_material = helpers["textured_material"]
    crack_decal = helpers["crack_decal"]
    cobweb = helpers["cobweb"]
    smooth_path = helpers["smooth_path"]

    # Weathered PBR materials (zero flat plastic/cartoon surfaces!)
    m["bath_floor"] = textured_material("M_studio_bath_floor", bath_floor_tile_textures(), 0.8)
    m["bath_wall_tiles"] = textured_material("M_studio_bath_wall_tiles", bath_wall_tile_textures(), 1.2)
    m["bath_cistern_tiles"] = textured_material("M_studio_bath_cistern", bath_cistern_tile_textures(), 0.65)
    m["bath_porcelain"] = textured_material("M_studio_bath_porcelain", aged_porcelain_textures(), 0.55)
    m["bath_galv"] = textured_material("M_studio_bath_galvanised", weathered_galv_textures(), 0.6)
    m["bath_copper"] = textured_material("M_studio_bath_copper", aged_copper_textures(), 0.4)
    m["bath_enamel_blue"] = textured_material("M_studio_bath_enamel_blue", chipped_enamel_textures(), 0.4)
    m["bath_mirror"] = textured_material("M_studio_bath_mirror", bath_mirror_material(), 0.0)

    m["bath_tile_trim"] = plain("M_studio_bath_tile_trim", (0.11, 0.18, 0.16), rough=0.28)
    m["bath_verdigris"] = plain("M_studio_bath_verdigris", (0.24, 0.36, 0.28), rough=0.68, metal=0.45)
    m["bath_valve_red"] = plain("M_studio_bath_valve_red", (0.36, 0.09, 0.07), rough=0.58, metal=0.35)
    m["bath_frosted"] = plain("M_studio_bath_frosted_glass", (0.32, 0.39, 0.44), rough=0.46, alpha=0.68)
    m["bath_frosted"].surface_render_method = "BLENDED"
    m["bath_water"] = plain("M_studio_bath_water", (0.014, 0.022, 0.025), rough=0.03, alpha=0.92)
    m["bath_water"].surface_render_method = "BLENDED"
    m["bath_soap"] = plain("M_studio_bath_soap", (0.72, 0.66, 0.52), rough=0.62)
    m["bath_amber_glass"] = plain("M_studio_bath_amber_glass", (0.32, 0.13, 0.03), rough=0.12, alpha=0.74)
    m["bath_amber_glass"].surface_render_method = "BLENDED"
    m["bath_green_glass"] = plain("M_studio_bath_green_glass", (0.06, 0.22, 0.11), rough=0.14, alpha=0.74)
    m["bath_green_glass"].surface_render_method = "BLENDED"
    m["bath_bulb"] = plain("M_studio_bath_bulb", (1.0, 0.88, 0.62), rough=0.25, emission=(1.0, 0.84, 0.56), strength=4.8)
    m["bath_plaster"] = library_material("painted_plaster_wall", "M_studio_bath_damp_plaster", tint=(0.82, 0.74, 0.56), tile=1.8)
    m["bath_towel_cotton"] = library_material("rough_linen", "M_studio_bath_towel_cotton", colour=(0.66, 0.62, 0.54), tile=0.28)

    y0, y1 = BATH_Y0, BATH_Y1
    d0, d1 = BATH_DOOR
    fz = BATH_FLOOR_Z

    def oval_turned(name, prof, ox, oy, oz, sx_k, sy_k, mat, segments=32):
        obj = turned(name, prof, 0.0, 0.0, 0.0, mat, segments=segments)
        for v in obj.data.vertices:
            v.co.x = ox + v.co.x * sx_k
            v.co.y = oy + v.co.y * sy_k
            v.co.z = oz + v.co.z
        obj.data.update()
        return obj

    def pipe_elbow(name, at, r=0.0155):
        """3D brass pipe elbow/coupling collar so plumbing corners look truly machined."""
        box(name, area, at[0] - r, at[0] + r, at[1] - r, at[1] + r, at[2] - r, at[2] + r, m["bath_verdigris"], edge=0.004)

    def hung_towel(name, width, drop_front, drop_back, mat, seed=0):
        """Realistic damp bathroom towel draped tightly over the brass rail with soft pleats and level hem."""
        nx, nz = 22, 18
        r_bar = 0.012
        verts, faces, uvs = [], [], []
        # Single continuous cloth strip: back hem -> up over bar -> down to front hem
        steps_back = 12
        steps_arc = 7
        steps_front = nz
        profile = []
        for j in range(steps_back, 0, -1):
            t = j / steps_back
            profile.append((-r_bar - 0.004 * t, -drop_back * t, 0.5 - 0.5 * t))
        for j in range(steps_arc + 1):
            a = math.pi - math.pi * (j / steps_arc)
            profile.append((r_bar * math.cos(a), r_bar * math.sin(a), 0.5))
        for j in range(1, steps_front + 1):
            t = j / steps_front
            profile.append((r_bar + 0.005 * t, -drop_front * t, 0.5 + 0.5 * t))
        rows = []
        v_coord = 0.0
        prev_pt = None
        for py, pz, v_frac in profile:
            if prev_pt is not None:
                v_coord += math.hypot(py - prev_pt[0], pz - prev_pt[1])
            prev_pt = (py, pz)
            hang = max(0.0, -pz) / max(drop_front, 0.01)
            row = []
            for i in range(nx + 1):
                u = i / nx
                x = (u - 0.5) * width
                pleat = (0.009 * math.sin(u * math.tau * 2.5 + seed * 1.7)
                         + 0.004 * math.sin(u * math.tau * 5.2 + seed)) * hang
                hem_sag = (0.005 * math.sin(u * math.pi * 3 + seed) - 0.004 * (2 * u - 1) ** 2) * (hang ** 2)
                row.append(len(verts))
                verts.append((x, py + pleat, pz + hem_sag))
                uvs.append((u * width, v_coord))
            rows.append(row)
        for j in range(len(rows) - 1):
            for i in range(nx):
                a, b = rows[j][i], rows[j][i + 1]
                c, d = rows[j + 1][i + 1], rows[j + 1][i]
                faces.append((a, b, c, d))
        obj = mesh_object(name, area, verts, faces, mat, uvs=uvs)
        for p in obj.data.polygons:
            p.use_smooth = True
        mod = obj.modifiers.new("Thick", "SOLIDIFY")
        mod.thickness = 0.0025
        mod.offset = 0.0
        return obj

    # ========================================================== 1. SHELL & P3 WALL
    wall("wall_p3_west", 0.0, d0, BATH_P3[0], BATH_P3[1], 0.0, 3.4, m["limewash"])
    wall("wall_p3_east", d1, 4.6, BATH_P3[0], BATH_P3[1], 0.0, 3.4, m["limewash"])
    wall("wall_p3_head", d0, d1, BATH_P3[0], BATH_P3[1], 2.22, 3.4, m["limewash"], solid=False)
    box("bath_door_frame_w", area, d0 - 0.05, d0 + 0.01, BATH_P3[0] - 0.018, BATH_P3[1] + 0.018, fz, 2.24, m["wood"], edge=0.005)
    box("bath_door_frame_e", area, d1 - 0.01, d1 + 0.05, BATH_P3[0] - 0.018, BATH_P3[1] + 0.018, fz, 2.24, m["wood"], edge=0.005)
    box("bath_door_frame_head", area, d0 - 0.05, d1 + 0.05, BATH_P3[0] - 0.018, BATH_P3[1] + 0.018, 2.18, 2.25, m["wood"], edge=0.005)
    # Raised worn wet-cement doorway curb
    box("bath_threshold_curb", area, d0, d1, BATH_P3[0] - 0.01, BATH_P3[1] + 0.02, fz, 0.022, m["wet_cement"], edge=0.005)

    # Outer & east masonry enclosure
    wall("bath_wall_east", BATH_W, BATH_W + 0.25, BATH_P3[0], y1 + 0.3, -0.3, 3.45, m["bath_plaster"])
    box("bath_rear_mass_east", area, BATH_W + 0.25, 4.9, BATH_P3[1], BATH_P3[1] + 0.3, -0.3, 3.45, m["outside"])
    wx0, wx1, wz0, wz1 = 1.24, 2.20, 2.02, 2.75
    wall("bath_wall_north_w", -0.3, wx0, y1, y1 + 0.28, -0.3, BATH_H + 0.35, m["bath_plaster"])
    wall("bath_wall_north_e", wx1, BATH_W + 0.25, y1, y1 + 0.28, -0.3, BATH_H + 0.35, m["bath_plaster"])
    wall("bath_wall_north_sill", wx0, wx1, y1, y1 + 0.28, -0.3, wz0, m["bath_plaster"])
    wall("bath_wall_north_head", wx0, wx1, y1, y1 + 0.28, wz1, BATH_H + 0.35, m["bath_plaster"], solid=False)
    box("bath_outside_facade", area, -2.0, 6.0, y1 + 3.2, y1 + 3.4, -2.0, 5.0, m["outside"])

    # Recessed wet mosaic floor & dark plank ceiling with exposed joists
    box("bath_floor_tiles", area, 0.0, BATH_W, y0, y1, -0.07, fz, m["bath_floor"])
    collider("bath_floor", area, -0.1, BATH_W + 0.1, y0 - 0.1, y1 + 0.1, -0.3, fz, surface="stone")
    box("bath_ceiling", area, 0.0, BATH_W, y0, y1, BATH_H, BATH_H + 0.05, m["ceiling"])
    for i in range(1, 5):
        jy = y0 + (y1 - y0) * i / 5
        box(f"bath_ceiling_joist_{i}", area, 0.0, BATH_W, jy - 0.04, jy + 0.04, BATH_H - 0.14, BATH_H, m["joist"], edge=0.005)

    # Ceramic wall tile lining (z = fz .. TILE_TOP) + dark ceramic cove baseboard + bullnose cap + damp limewash
    t = 0.014
    tile_spans = [
        ("w", (0.0, t), (y0, y1)),
        ("e", (BATH_W - t, BATH_W), (y0, y1)),
        ("n", (0.0, BATH_W), (y1 - t, y1)),
        ("s_w", (0.0, d0 - 0.04), (y0, y0 + t)),
        ("s_e", (d1 + 0.04, BATH_W), (y0, y0 + t)),
    ]
    for tag, (xa, xb), (ya, yb) in tile_spans:
        box(f"bath_tiles_{tag}", area, xa, xb, ya, yb, fz + 0.08, TILE_TOP, m["bath_wall_tiles"])
        inset_x = 0.006 if tag in ("w", "e") else 0.0
        inset_y = 0.006 if tag in ("n", "s_w", "s_e") else 0.0
        tx0 = xa - inset_x if tag == "e" else xa
        tx1 = xb + inset_x if tag == "w" else xb
        ty0 = ya - inset_y if tag == "n" else ya
        ty1 = yb + inset_y if tag in ("s_w", "s_e") else yb
        # Dark damp-resistant cove baseboard along the floor
        box(f"bath_cove_{tag}", area, tx0, tx1, ty0, ty1, fz, fz + 0.08, m["bath_tile_trim"], edge=0.004)
        # Bullnose glazed tile cap rail
        box(f"bath_tile_trim_{tag}", area, tx0, tx1, ty0, ty1, TILE_TOP, TILE_TOP + 0.032, m["bath_tile_trim"], edge=0.005)
        if tag != "n":
            box(f"bath_plaster_up_{tag}", area, xa, xb, ya, yb, TILE_TOP + 0.032, BATH_H, m["bath_plaster"])
    box("bath_plaster_up_nw", area, 0.0, wx0, y1 - t, y1, TILE_TOP + 0.032, BATH_H, m["bath_plaster"])
    box("bath_plaster_up_ne", area, wx1, BATH_W, y1 - t, y1, TILE_TOP + 0.032, BATH_H, m["bath_plaster"])
    box("bath_plaster_up_nsill", area, wx0, wx1, y1 - t, y1, TILE_TOP + 0.032, wz0, m["bath_plaster"])
    box("bath_plaster_up_nhead", area, wx0, wx1, y1 - t, y1, wz1, BATH_H, m["bath_plaster"])
    box("bath_plaster_up_sdoor", area, d0 - 0.04, d1 + 0.04, y0, y0 + t, 2.24, BATH_H, m["bath_plaster"])

    # ========================================================== 2. LOUVRED + FROSTED-GLASS BATHROOM DOOR (DYNAMIC HAUNT PROP)
    leaf = (d1 - d0) - 0.025
    door = empty("haunt_bath_door", area, (d0 + 0.015, y0 + 0.005, 0.024), (0, 0, math.radians(132)), action="use")
    bpy.context.view_layer.update()
    dparts = [
        box("bath_door_stile_l", area, 0.0, 0.08, 0.0, 0.04, 0.0, 2.14, m["worn"], edge=0.004),
        box("bath_door_stile_r", area, leaf - 0.08, leaf, 0.0, 0.04, 0.0, 2.14, m["worn"], edge=0.004),
        box("bath_door_rail_bot", area, 0.0, leaf, 0.0, 0.04, 0.0, 0.17, m["wood"], edge=0.004),
        box("bath_door_kickplate", area, 0.01, leaf - 0.01, 0.039, 0.043, 0.01, 0.14, m["bath_galv"], edge=0.002),
        box("bath_door_rail_mid", area, 0.0, leaf, 0.0, 0.04, 0.88, 1.01, m["worn"], edge=0.004),
        box("bath_door_rail_top", area, 0.0, leaf, 0.0, 0.04, 2.02, 2.14, m["worn"], edge=0.004),
        # Upper 4-pane frosted privacy glass window so the flickering bulb peeks through when closed!
        box("bath_door_muntin_v", area, leaf / 2 - 0.012, leaf / 2 + 0.012, 0.010, 0.030, 1.01, 2.02, m["worn"], edge=0.002),
        box("bath_door_muntin_h", area, 0.08, leaf - 0.08, 0.010, 0.030, 1.50, 1.525, m["worn"], edge=0.002),
        box("bath_door_frosted_pane", area, 0.08, leaf - 0.08, 0.017, 0.023, 1.01, 2.02, m["bath_frosted"]),
    ]
    for j in range(13):
        lz = 0.20 + j * 0.051
        dparts.append(box(f"bath_door_louvre_{j}", area, 0.08, leaf - 0.08, 0.004, 0.036, lz, lz + 0.034, m["shutter"], tilt=(0.52, 0, 0)))
    for side, yy, rot in (("out", -0.002, math.pi / 2), ("in", 0.042, -math.pi / 2)):
        # Brass escutcheon backplate + keyhole + turned brass knob with ceramic rosette
        dparts.append(box(f"bath_door_plate_{side}", area, leaf - 0.095, leaf - 0.045, yy - 0.003, yy + 0.003, 0.87, 1.04, m["brass"], edge=0.002))
        kb = turned(f"bath_door_knob_{side}", [(0.0, 0.0), (0.016, 0.0), (0.010, 0.026), (0.023, 0.046), (0.0, 0.058)], 0, 0, 0, m["brass"], segments=16)
        kb.location = (leaf - 0.070, yy, 0.96)
        kb.rotation_euler = (rot, 0, 0)
        dparts.append(kb)
    dparts.append(box("bath_door_bolt_plate", area, leaf - 0.13, leaf - 0.02, 0.040, 0.048, 1.12, 1.16, m["brass"], edge=0.002))
    dparts.append(cylinder("bath_door_bolt_rod", area, 0, 0, 0, 0.09, 0.005, m["brass"], verts=8))
    dparts[-1].location = (leaf - 0.075, 0.054, 1.14)
    dparts[-1].rotation_euler = (0, math.pi / 2, 0)
    for k, hz in enumerate((0.26, 1.08, 1.88)):
        dparts.append(box(f"bath_door_hinge_{k}", area, -0.006, 0.048, 0.036, 0.046, hz - 0.036, hz + 0.036, m["rust"], edge=0.002))
        dparts.append(cylinder(f"bath_door_hinge_pin_{k}", area, -0.004, 0.044, hz - 0.042, hz + 0.042, 0.0055, m["rust"], verts=8))
    for p in dparts:
        p.parent = door

    # ========================================================== 3. HIGH LOUVRED FROSTED WINDOW (NORTH WALL)
    box("bath_win_frame_b", area, wx0 - 0.04, wx1 + 0.04, y1 - 0.02, y1 + 0.22, wz0 - 0.04, wz0 + 0.02, m["wood"], edge=0.005)
    box("bath_win_frame_t", area, wx0 - 0.04, wx1 + 0.04, y1 - 0.02, y1 + 0.22, wz1 - 0.02, wz1 + 0.04, m["wood"], edge=0.005)
    box("bath_win_frame_l", area, wx0 - 0.04, wx0 + 0.02, y1 - 0.02, y1 + 0.22, wz0, wz1, m["wood"], edge=0.005)
    box("bath_win_frame_r", area, wx1 - 0.02, wx1 + 0.04, y1 - 0.02, y1 + 0.22, wz0, wz1, m["wood"], edge=0.005)
    for j in range(7):
        lz = wz0 + 0.05 + j * (wz1 - wz0 - 0.1) / 6.5
        box(f"bath_win_louvre_{j}", area, wx0 + 0.025, wx1 - 0.025, y1 + 0.07, y1 + 0.16, lz, lz + 0.008, m["bath_frosted"], tilt=(-0.48, 0, 0))
    for k in range(6):
        bx = wx0 + 0.11 + k * (wx1 - wx0 - 0.22) / 5
        cylinder(f"bath_win_bar_{k}", area, bx, y1 + 0.04, wz0 + 0.01, wz1 - 0.01, 0.007, m["rust"], verts=8)
    box("bath_win_bar_cross", area, wx0 + 0.02, wx1 - 0.02, y1 + 0.032, y1 + 0.048, (wz0 + wz1) / 2 - 0.008, (wz0 + wz1) / 2 + 0.008, m["rust"])
    empty("marker_bath_window", area, ((wx0 + wx1) / 2, y1 + 0.6, (wz0 + wz1) / 2))

    # ========================================================== 4. KHMER WATER CISTERN (អាងទឹក) — NW CORNER
    cx0, cx1, cy0, cy1, cz1 = 0.015, 0.98, 15.72, y1 - 0.015, 0.84
    wt = 0.105
    w_in = wt * 0.6
    box("bath_tank_wall_e", area, cx1 - wt, cx1, cy0, cy1, fz, cz1, m["bath_cistern_tiles"], edge=0.006)
    box("bath_tank_wall_s", area, cx0, cx1 - wt, cy0, cy0 + wt, fz, cz1, m["bath_cistern_tiles"], edge=0.006)
    box("bath_tank_wall_w", area, cx0, cx0 + w_in, cy0 + wt, cy1, fz, cz1, m["bath_cistern_tiles"])
    box("bath_tank_wall_n", area, cx0 + w_in, cx1 - wt, cy1 - w_in, cy1, fz, cz1, m["bath_cistern_tiles"])
    box("bath_tank_bottom", area, cx0 + w_in, cx1 - wt, cy0 + wt, cy1 - w_in, fz, fz + 0.10, m["bath_cistern_tiles"])
    box("bath_tank_rim_e", area, cx1 - wt - 0.006, cx1 + 0.008, cy0 - 0.008, cy1, cz1, cz1 + 0.026, m["bath_porcelain"], edge=0.008)
    box("bath_tank_rim_s", area, cx0, cx1 - wt - 0.006, cy0 - 0.008, cy0 + wt + 0.006, cz1, cz1 + 0.026, m["bath_porcelain"], edge=0.008)
    # Brass lower drain bung on east face of cistern
    bung = cylinder("bath_tank_drain_bung", area, 0, 0, 0, 0.028, 0.016, m["bath_verdigris"], verts=12)
    bung.location = (cx1 + 0.002, cy0 + 0.22, fz + 0.09)
    bung.rotation_euler = (0, math.pi / 2, 0)
    collider("bath_water_tank", area, cx0, cx1 + 0.02, cy0 - 0.02, cy1, fz, cz1 + 0.04)
    # Dark still reflective water inside cistern (kept separate for runtime ripple haunt!)
    box("haunt_bath_tank_water", area, cx0 + w_in + 0.002, cx1 - wt - 0.002, cy0 + wt + 0.002, cy1 - w_in - 0.002, 0.70, 0.72, m["bath_water"])
    empty("marker_bath_tank", area, ((cx0 + cx1) / 2, (cy0 + cy1) / 2, 0.72))

    # Brass bibcock tap over the water cistern
    tap_y, tap_z = 16.22, 1.06
    tube("bath_tank_tap_neck", area, [(0.015, tap_y, tap_z), (0.14, tap_y, tap_z), (0.175, tap_y, tap_z - 0.015), (0.185, tap_y, tap_z - 0.055)], 0.011, m["brass"], sides=12)
    fl = turned("bath_tank_tap_flange", [(0.0, 0.0), (0.028, 0.0), (0.025, 0.01), (0.014, 0.014), (0.0, 0.014)], 0, 0, 0, m["bath_verdigris"], segments=16)
    fl.location = (0.015, tap_y, tap_z)
    fl.rotation_euler = (0, math.pi / 2, 0)
    cylinder("bath_tank_tap_stem", area, 0.115, tap_y, tap_z + 0.008, tap_z + 0.048, 0.0065, m["brass"], verts=10)
    box("bath_tank_tap_tbar", area, 0.088, 0.142, tap_y - 0.006, tap_y + 0.006, tap_z + 0.044, tap_z + 0.056, m["brass"], edge=0.003)

    # Chipped blue enamel bathing scoop (ផ្ដិល) resting on the cistern's front rim (dynamic haunt prop!)
    dip = empty("haunt_bath_dipper", area, (0.58, cy0 + 0.05, cz1 + 0.026))
    bpy.context.view_layer.update()
    scoop_prof = [(0.0, 0.0), (0.068, 0.0), (0.082, 0.045), (0.092, 0.105), (0.096, 0.112), (0.090, 0.114),
                  (0.084, 0.102), (0.075, 0.045), (0.062, 0.006), (0.0, 0.006)]
    sc = turned("bath_dipper_bowl", scoop_prof, 0.58, cy0 + 0.05, cz1 + 0.026, m["bath_enamel_blue"], segments=24)
    sc_h = tube("bath_dipper_handle", area, [(0.67, cy0 + 0.05, cz1 + 0.125), (0.76, cy0 + 0.04, cz1 + 0.145), (0.83, cy0 + 0.035, cz1 + 0.135)], 0.008, m["bath_enamel_blue"], sides=8)
    attach(sc, dip)
    attach(sc_h, dip)

    # Weathered teak slatted duckboard bath mat + Khmer wooden bath clogs + rusted floor drain
    mx0, mx1, my0, my1 = 0.14, 0.88, 14.96, 15.60
    for k in range(3):
        by = my0 + 0.08 + k * 0.24
        box(f"bath_mat_bearer_{k}", area, mx0 + 0.04, mx1 - 0.04, by - 0.015, by + 0.015, fz, fz + 0.014, m["wood"])
    for k in range(9):
        sx_ = mx0 + k * (mx1 - mx0) / 9
        box(f"bath_mat_slat_{k}", area, sx_ + 0.004, sx_ + (mx1 - mx0) / 9 - 0.006, my0, my1, fz + 0.014, fz + 0.028, m["planks"], edge=0.002)
    for k, (clx, cly, ang) in enumerate(((1.02, 15.22, 0.25), (1.14, 15.32, -0.18))):
        box(f"bath_clog_sole_{k}", area, clx - 0.042, clx + 0.042, cly - 0.115, cly + 0.115, fz + 0.014, fz + 0.03, m["worn"], tilt=(0, 0, ang), edge=0.006)
        box(f"bath_clog_heel_{k}", area, clx - 0.036, clx + 0.036, cly - 0.10, cly - 0.055, fz, fz + 0.016, m["worn"], tilt=(0, 0, ang), edge=0.003)
        box(f"bath_clog_toe_{k}", area, clx - 0.036, clx + 0.036, cly + 0.04, cly + 0.085, fz, fz + 0.016, m["worn"], tilt=(0, 0, ang), edge=0.003)
        box(f"bath_clog_strap_{k}", area, clx - 0.042, clx + 0.042, cly - 0.01, cly + 0.042, fz + 0.03, fz + 0.052, m["satchel_leather"], tilt=(0, 0, ang), edge=0.004)

    drx, dry = 1.18, 15.96
    turned("bath_drain_rim", [(0.055, 0.0), (0.072, 0.0), (0.072, 0.005), (0.055, 0.005)], drx, dry, fz + 0.0005, m["rust"], segments=24)
    cylinder("bath_drain_well", area, drx, dry, fz - 0.015, fz + 0.001, 0.056, m["dark"], verts=20)
    for k in range(5):
        off = (k - 2) * 0.019
        half = math.sqrt(max(0.0, 0.055 ** 2 - off ** 2))
        box(f"bath_drain_bar_{k}", area, drx - half, drx + half, dry + off - 0.004, dry + off + 0.004, fz + 0.001, fz + 0.0045, m["rust"])

    # Weathered galvanized wash bucket + wooden scrub brush
    bkx, bky = 0.28, 14.54
    buck_prof = [(0.0, 0.0), (0.115, 0.0), (0.155, 0.28), (0.162, 0.29), (0.153, 0.292), (0.11, 0.01), (0.0, 0.01)]
    turned("bath_wash_bucket", buck_prof, bkx, bky, fz, m["bath_galv"], segments=24)
    cylinder("bath_bucket_water", area, bkx, bky, fz + 0.135, fz + 0.145, 0.126, m["bath_water"], verts=20)
    handle_arc = [(bkx + 0.158 * math.cos(a), bky + 0.158 * math.sin(a), fz + 0.28 + 0.14 * math.sin(a)) for a in np.linspace(0, math.pi, 17)]
    tube("bath_bucket_handle", area, handle_arc, 0.003, m["rust"], sides=6)
    collider("bath_wash_bucket", area, bkx - 0.17, bkx + 0.17, bky - 0.17, bky + 0.17, fz, fz + 0.30)
    box("bath_scrub_wood", area, 0.50, 0.65, 14.44, 14.51, fz + 0.022, fz + 0.042, m["worn"], tilt=(0, 0, 0.4), edge=0.004)
    box("bath_scrub_bristles", area, 0.505, 0.645, 14.445, 14.505, fz, fz + 0.022, m["bamboo"], tilt=(0, 0, 0.4))

    # ========================================================== 5. SCULPTED COLONIAL PORCELAIN LAVABO & HAUNTED MIRROR
    sx, sy, sz = 1.72, y1 - 0.235, 0.80
    for side in (-0.22, 0.22):
        tube(f"bath_sink_bracket_{side:.2f}", area, [(sx + side, y1 - 0.014, sz - 0.25), (sx + side, y1 - 0.014, sz - 0.04), (sx + side, sy - 0.15, sz - 0.04)], 0.011, m["rust"], sides=8)
        tube(f"bath_sink_brace_{side:.2f}", area, [(sx + side, y1 - 0.014, sz - 0.22), (sx + side, sy - 0.09, sz - 0.042)], 0.008, m["rust"], sides=6)
    # Seamless one-piece cast-porcelain washbasin + integral bevelled backsplash (zero gaps, zero wire line!)
    _sculpt_porcelain_sink(area, "bath_sink_lavabo", sx, sy, sz, y1, m["bath_porcelain"])
    box("bath_sink_backsplash", area, sx - 0.296, sx + 0.296, y1 - 0.042, y1 - 0.012, sz + 0.022, sz + 0.158, m["bath_porcelain"], edge=0.009)
    # Flush brass waste strainer rosette & rear overflow escutcheon ring (no floating plug chain!)
    drain_y = sy - 0.028
    turned("bath_sink_drain_rim", [(0.014, 0.0), (0.026, 0.0), (0.026, 0.0035), (0.014, 0.0035)], sx, drain_y, sz - 0.141, m["brass"], segments=20)
    cylinder("bath_sink_hole", area, sx, drain_y, sz - 0.145, sz - 0.139, 0.015, m["dark"], verts=16)
    for ang_ in (0.0, math.pi / 2):
        box(f"bath_sink_grate_{ang_:.1f}", area, sx - 0.015, sx + 0.015, drain_y - 0.0018, drain_y + 0.0018, sz - 0.140, sz - 0.138, m["bath_verdigris"], tilt=(0, 0, ang_))
    ov = turned("bath_sink_overflow", [(0.006, 0.0), (0.011, 0.0), (0.011, 0.003), (0.006, 0.003)], 0, 0, 0, m["brass"], segments=14)
    ov.location = (sx, drain_y + 0.112, sz - 0.032)
    ov.rotation_euler = (math.pi / 2, 0, 0)
    # Exposed galvanized S-trap & wall escutcheon flange
    strap = [(sx, drain_y, sz - 0.155), (sx, drain_y, sz - 0.275), (sx, drain_y + 0.04, sz - 0.325),
             (sx, drain_y + 0.09, sz - 0.275), (sx, drain_y + 0.14, sz - 0.245), (sx, y1 - 0.012, sz - 0.245)]
    tube("bath_sink_strap", area, smooth_path(strap, 6), 0.020, m["bath_galv"], sides=12)
    sf = turned("bath_sink_trap_flange", [(0.020, 0.0), (0.038, 0.0), (0.036, 0.008), (0.020, 0.010)], 0, 0, 0, m["bath_verdigris"], segments=16)
    sf.location = (sx, y1 - 0.014, sz - 0.245)
    sf.rotation_euler = (math.pi / 2, 0, 0)
    # Twin colonial 1930s brass cross-head pillar taps with stepped collars, curved spouts & porcelain caps
    for k, ox in enumerate((-0.115, 0.115)):
        fx = sx + ox
        fy = y1 - 0.095
        tap_body = [
            (0.0, 0.0), (0.023, 0.0), (0.021, 0.008), (0.015, 0.014),
            (0.013, 0.072), (0.016, 0.080), (0.011, 0.088), (0.011, 0.098), (0.0, 0.098)
        ]
        turned(f"bath_faucet_body_{k}", tap_body, fx, fy, sz + 0.024, m["brass"], segments=18)
        turned(f"bath_faucet_collar_{k}", [(0.021, 0.0), (0.025, 0.0), (0.024, 0.005), (0.021, 0.005)], fx, fy, sz + 0.024, m["bath_verdigris"], segments=16)
        spout = [(fx, fy, sz + 0.078), (fx, fy - 0.042, sz + 0.088), (fx, fy - 0.078, sz + 0.072), (fx, fy - 0.088, sz + 0.046)]
        tube(f"bath_faucet_spout_{k}", area, smooth_path(spout, 5), 0.0085, m["brass"], sides=12)
        turned(f"bath_faucet_nozzle_{k}", [(0.007, 0.0), (0.010, 0.0), (0.010, 0.008), (0.008, 0.010), (0.007, 0.010)], fx, fy - 0.088, sz + 0.039, m["bath_verdigris"], segments=12)
        for ax, ay, bx_, by_ in ((fx - 0.032, fy - 0.004, fx + 0.032, fy + 0.004), (fx - 0.004, fy - 0.032, fx + 0.004, fy + 0.032)):
            box(f"bath_faucet_cross_{k}_{ax:.2f}", area, ax, bx_, ay, by_, sz + 0.114, sz + 0.123, m["brass"], edge=0.003)
        turned(f"bath_faucet_cap_{k}", [(0.0, 0.0), (0.0095, 0.0), (0.009, 0.005), (0.006, 0.0075), (0.0, 0.008)], fx, fy, sz + 0.123, m["bath_porcelain"], segments=14)
    empty("interact_bath_faucet", area, (sx, y1 - 0.16, sz + 0.07), action="use")
    empty("marker_bath_faucet_drip", area, (sx - 0.115, y1 - 0.183, sz + 0.039))
    collider("bath_sink", area, sx - 0.32, sx + 0.32, sy - 0.22, y1, fz, sz + 0.16)

    # Porcelain wall shelf & realistic 1932 toiletries
    sh_z = 1.05
    box("bath_shelf", area, sx - 0.28, sx + 0.28, y1 - 0.135, y1 - 0.014, sh_z, sh_z + 0.018, m["bath_porcelain"], edge=0.005)
    for ox in (-0.22, 0.22):
        box(f"bath_shelf_br_{ox:.2f}", area, sx + ox - 0.012, sx + ox + 0.012, y1 - 0.11, y1 - 0.014, sh_z - 0.06, sh_z, m["bath_verdigris"])
    box("bath_soap_dish", area, sx - 0.24, sx - 0.12, y1 - 0.115, y1 - 0.035, sh_z + 0.018, sh_z + 0.028, m["bath_porcelain"], edge=0.004)
    box("bath_soap_bar", area, sx - 0.225, sx - 0.135, y1 - 0.10, y1 - 0.05, sh_z + 0.028, sh_z + 0.054, m["bath_soap"], tilt=(0, 0, 0.08), edge=0.009)
    tum = [(0.0, 0.0), (0.028, 0.0), (0.034, 0.09), (0.031, 0.092), (0.026, 0.008), (0.0, 0.008)]
    turned("bath_tumbler", tum, sx - 0.04, y1 - 0.078, sh_z + 0.018, m["bath_porcelain"], segments=20)
    tx_c, ty_c, tb_z = sx - 0.04, y1 - 0.078, sh_z + 0.026
    for k, (dx, dy, rx, ry, rz, handle_mat) in enumerate((
        (-0.005, 0.005, 0.07, -0.22, 0.22, m["paper"]),
        (0.006, -0.005, 0.05, 0.20, -0.28, m["worn"]),
    )):
        tb_root = empty(f"bath_toothbrush_root_{k}", area, (tx_c + dx, ty_c + dy, tb_z), (rx, ry, rz))
        bpy.context.view_layer.update()
        tb_handle = box(f"bath_toothbrush_{k}", area, -0.0042, 0.0042, -0.0026, 0.0026, 0.0, 0.142, handle_mat, edge=0.0018)
        tb_bristles = box(f"bath_toothbrush_head_{k}", area, -0.0038, 0.0038, -0.0105, -0.0022, 0.116, 0.140, m["linen"], edge=0.001)
        tb_handle.parent = tb_root
        tb_bristles.parent = tb_root
    bot_a = [(0.0, 0.0), (0.022, 0.0), (0.022, 0.085), (0.010, 0.105), (0.010, 0.125), (0.013, 0.128), (0.0, 0.128)]
    turned("bath_amber_bottle", bot_a, sx + 0.10, y1 - 0.075, sh_z + 0.018, m["bath_amber_glass"], segments=18)
    cylinder("bath_amber_cork", area, sx + 0.10, y1 - 0.075, sh_z + 0.142, sh_z + 0.158, 0.008, m["worn"], verts=10)
    bot_g = [(0.0, 0.0), (0.026, 0.0), (0.026, 0.068), (0.011, 0.085), (0.011, 0.102), (0.0, 0.102)]
    turned("bath_green_bottle", bot_g, sx + 0.175, y1 - 0.082, sh_z + 0.018, m["bath_green_glass"], segments=18)
    cylinder("bath_green_cork", area, sx + 0.175, y1 - 0.082, sh_z + 0.118, sh_z + 0.132, 0.009, m["ebonite"], verts=10)
    box("bath_comb", area, sx + 0.01, sx + 0.075, y1 - 0.115, y1 - 0.088, sh_z + 0.018, sh_z + 0.023, m["ebonite"], tilt=(0, 0, -0.22))
    box("bath_razor", area, sx + 0.21, sx + 0.265, y1 - 0.115, y1 - 0.095, sh_z + 0.018, sh_z + 0.028, m["rosewood"], tilt=(0, 0, 0.35), edge=0.003)

    # Foxed & corner-cracked antique mirror facing -Y into bathroom
    mz0, mz1 = 1.22, 1.92
    mw = 0.27
    m_verts = [(sx - mw, y1 - 0.032, mz0), (sx + mw, y1 - 0.032, mz0), (sx + mw, y1 - 0.032, mz1), (sx - mw, y1 - 0.032, mz1)]
    mesh_object("bath_mirror_glass", area, m_verts, [(0, 1, 2, 3)], m["bath_mirror"], uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    fm = 0.038
    box("bath_mirror_frame_t", area, sx - mw - fm, sx + mw + fm, y1 - 0.044, y1 - 0.014, mz1, mz1 + fm, m["rosewood"], edge=0.006)
    box("bath_mirror_frame_b", area, sx - mw - fm, sx + mw + fm, y1 - 0.044, y1 - 0.014, mz0 - fm, mz0, m["rosewood"], edge=0.006)
    box("bath_mirror_frame_l", area, sx - mw - fm, sx - mw, y1 - 0.044, y1 - 0.014, mz0, mz1, m["rosewood"], edge=0.006)
    box("bath_mirror_frame_r", area, sx + mw, sx + mw + fm, y1 - 0.044, y1 - 0.014, mz0, mz1, m["rosewood"], edge=0.006)
    box("bath_mirror_back", area, sx - mw - 0.01, sx + mw + 0.01, y1 - 0.030, y1 - 0.016, mz0 - 0.01, mz1 + 0.01, m["wood"])
    empty("marker_bath_mirror", area, (sx, y1 - 0.038, (mz0 + mz1) / 2))

    # ========================================================== 6. 1930s HIGH-CISTERN PULL-CHAIN TOILET (EAST WALL)
    tx, ty = BATH_W - 0.40, 16.05
    wc_prof = [(0.0, 0.0), (0.148, 0.0), (0.144, 0.028), (0.105, 0.075), (0.092, 0.16), (0.125, 0.25),
               (0.175, 0.35), (0.188, 0.40), (0.176, 0.418), (0.148, 0.415), (0.135, 0.355),
               (0.088, 0.21), (0.055, 0.14), (0.0, 0.14)]
    oval_turned("bath_toilet_bowl", wc_prof, tx, ty, fz, 1.18, 0.94, m["bath_porcelain"], segments=32)
    # Smooth curved ceramic S-horn outlet into east wall (replaces blocky box!)
    horn_path = [(tx + 0.08, ty, fz + 0.13), (tx + 0.22, ty, fz + 0.14), (BATH_W - 0.014, ty, fz + 0.15)]
    tube("bath_toilet_outlet", area, smooth_path(horn_path, 4), 0.056, m["bath_porcelain"], sides=16)
    # Brass floor mounting bolt caps
    for oy in (-0.11, 0.11):
        turned(f"bath_toilet_bolt_{oy:.2f}", [(0.0, 0.0), (0.012, 0.0), (0.011, 0.012), (0.0, 0.016)], tx - 0.02, ty + oy, fz + 0.024, m["bath_porcelain"], segments=10)
    cylinder("bath_toilet_water", area, tx, ty, fz + 0.13, fz + 0.155, 0.075, m["bath_water"], verts=18)
    seat_pts = [(tx + 0.205 * math.cos(a), ty + 0.165 * math.sin(a), fz + 0.422) for a in np.linspace(0, math.tau, 33)]
    tube("bath_toilet_seat", area, seat_pts, 0.019, m["rosewood"], sides=10)
    lid = cylinder("bath_toilet_lid", area, 0, 0, -0.012, 0.012, 0.185, m["rosewood"], verts=28)
    lid.scale = (1.06, 0.86, 1.0)
    lid.location = (tx + 0.185, ty, fz + 0.61)
    lid.rotation_euler = (0, math.radians(82), 0)
    for oy in (-0.065, 0.065):
        box(f"bath_toilet_hinge_{oy:.2f}", area, tx + 0.17, tx + 0.22, ty + oy - 0.012, ty + oy + 0.012, fz + 0.415, fz + 0.44, m["brass"], edge=0.002)

    # High wall-mounted weathered galvanized cistern tank with molded decorative front panel
    ct_z0, ct_z1 = 2.08, 2.40
    box("bath_cistern_tank", area, BATH_W - 0.26, BATH_W - 0.02, ty - 0.24, ty + 0.24, ct_z0, ct_z1, m["bath_galv"], edge=0.012)
    box("bath_cistern_panel", area, BATH_W - 0.268, BATH_W - 0.258, ty - 0.18, ty + 0.18, ct_z0 + 0.055, ct_z1 - 0.055, m["bath_galv"], edge=0.005)
    box("bath_cistern_lid", area, BATH_W - 0.275, BATH_W - 0.014, ty - 0.255, ty + 0.255, ct_z1, ct_z1 + 0.025, m["bath_galv"], edge=0.006)
    for oy in (-0.18, 0.18):
        tube(f"bath_cistern_bracket_{oy:.2f}", area, [(BATH_W - 0.018, ty + oy, ct_z0 - 0.22), (BATH_W - 0.018, ty + oy, ct_z0), (BATH_W - 0.24, ty + oy, ct_z0)], 0.010, m["rust"], sides=6)
    flush_path = [(BATH_W - 0.11, ty, ct_z0), (BATH_W - 0.11, ty, fz + 0.45), (BATH_W - 0.11, ty, fz + 0.37), (tx + 0.18, ty, fz + 0.36)]
    tube("bath_toilet_flush_pipe", area, smooth_path(flush_path, 5), 0.019, m["bath_galv"], sides=12)
    for cz in (0.95, 1.55):
        box(f"bath_flush_clip_{cz}", area, BATH_W - 0.13, BATH_W - 0.014, ty - 0.025, ty + 0.025, cz - 0.012, cz + 0.012, m["bath_verdigris"])
    tube("bath_flush_lever", area, [(BATH_W - 0.14, ty - 0.24, ct_z1 - 0.04), (BATH_W - 0.14, ty - 0.38, ct_z1 - 0.06)], 0.006, m["rust"], sides=6)
    tube("bath_pull_chain", area, [(BATH_W - 0.14, ty - 0.37, ct_z1 - 0.06), (BATH_W - 0.14, ty - 0.37, 1.32)], 0.0028, m["brass"], sides=6)
    turned("bath_pull_handle", [(0.0, 0.0), (0.011, 0.008), (0.013, 0.032), (0.008, 0.062), (0.005, 0.088), (0.0, 0.092)], BATH_W - 0.14, ty - 0.37, 1.23, m["bath_porcelain"], segments=14)
    # Vintage wall-mounted paper roll holder beside the toilet
    tp_y, tp_z = ty - 0.42, 0.68
    box("bath_tp_plate", area, BATH_W - 0.026, BATH_W - 0.014, tp_y - 0.04, tp_y + 0.04, tp_z - 0.04, tp_z + 0.04, m["wood"], edge=0.003)
    tp_roll = cylinder("bath_tp_roll", area, 0, 0, -0.055, 0.055, 0.052, m["paper"], verts=20)
    tp_roll.location = (BATH_W - 0.095, tp_y, tp_z)
    tp_roll.rotation_euler = (math.pi / 2, 0, 0)
    tube("bath_tp_wire", area, [(BATH_W - 0.026, tp_y - 0.065, tp_z), (BATH_W - 0.095, tp_y - 0.065, tp_z), (BATH_W - 0.095, tp_y + 0.065, tp_z), (BATH_W - 0.026, tp_y + 0.065, tp_z)], 0.0035, m["brass"], sides=6)
    collider("bath_toilet", area, tx - 0.24, BATH_W, ty - 0.24, ty + 0.24, fz, fz + 0.72)

    # ========================================================== 7. FITTED COPPER PLUMBING, TOWEL RAIL & LEDGE
    pipe_z = 0.58
    tube("bath_pipe_main_w", area, [(0.032, y0 + 0.06, fz + 0.10), (0.032, y0 + 0.06, pipe_z), (0.032, 15.66, pipe_z), (0.032, 15.66, tap_z + 0.36), (0.032, y1 - 0.032, tap_z + 0.36)], 0.010, m["bath_copper"], sides=10)
    tube("bath_pipe_over_tank", area, [(0.032, y1 - 0.032, tap_z + 0.36), (1.03, y1 - 0.032, tap_z + 0.36)], 0.010, m["bath_copper"], sides=10)
    tube("bath_pipe_main_n", area, [(1.03, y1 - 0.032, tap_z + 0.36), (1.03, y1 - 0.032, pipe_z), (BATH_W - 0.032, y1 - 0.032, pipe_z)], 0.010, m["bath_copper"], sides=10)
    tube("bath_pipe_main_e", area, [(BATH_W - 0.032, y1 - 0.032, pipe_z), (BATH_W - 0.032, ty + 0.14, pipe_z), (BATH_W - 0.032, ty + 0.14, ct_z1 - 0.06), (BATH_W - 0.10, ty + 0.14, ct_z1 - 0.06)], 0.009, m["bath_copper"], sides=10)
    tube("bath_pipe_drop_tank", area, [(0.032, tap_y, tap_z + 0.36), (0.032, tap_y, tap_z)], 0.009, m["bath_copper"], sides=10)
    # 3D machined brass elbow & T-fittings at every pipe corner (makes plumbing look physically real!)
    for idx, pt in enumerate((
        (0.032, 15.66, pipe_z), (0.032, 15.66, tap_z + 0.36), (0.032, tap_y, tap_z + 0.36),
        (0.032, y1 - 0.032, tap_z + 0.36), (1.03, y1 - 0.032, tap_z + 0.36), (1.03, y1 - 0.032, pipe_z),
        (sx - 0.11, y1 - 0.032, pipe_z), (sx + 0.11, y1 - 0.032, pipe_z),
        (BATH_W - 0.032, y1 - 0.032, pipe_z), (BATH_W - 0.032, ty + 0.14, pipe_z),
    )):
        pipe_elbow(f"bath_pipe_fitting_{idx}", pt)

    valve_z = tap_z + 0.20
    vs = cylinder("bath_valve_stem", area, 0, 0, 0, 0.045, 0.007, m["brass"], verts=8)
    vs.location = (0.032, tap_y, valve_z)
    vs.rotation_euler = (0, math.pi / 2, 0)
    wheel_pts = [(0.075, tap_y + 0.034 * math.cos(a), valve_z + 0.034 * math.sin(a)) for a in np.linspace(0, math.tau, 17)]
    tube("bath_valve_wheel", area, wheel_pts, 0.005, m["bath_valve_red"], sides=6)
    for ox in (-0.11, 0.11):
        tube(f"bath_pipe_riser_sink_{ox:.2f}", area, [(sx + ox, y1 - 0.032, pipe_z), (sx + ox, y1 - 0.032, sz - 0.06), (sx + ox, y1 - 0.095, sz - 0.03)], 0.008, m["bath_copper"], sides=8)
    for px_, py_, pz_ in ((0.025, 14.8, pipe_z), (0.025, 16.0, tap_z + 0.36),
                          (1.25, y1 - 0.025, pipe_z), (2.45, y1 - 0.025, pipe_z), (BATH_W - 0.025, ty + 0.14, 1.35)):
        box(f"bath_pipe_clip_{px_:.1f}_{py_:.1f}", area, px_ - 0.014, px_ + 0.014, py_ - 0.014, py_ + 0.014, pz_ - 0.015, pz_ + 0.015, m["bath_verdigris"])

    # East wall towel bar with damp woven cotton towel & Khmer krama
    tr_x, tr_z = BATH_W - 0.095, 1.18
    for k, yy in enumerate((14.62, 15.32)):
        box(f"bath_towel_br_{k}", area, tr_x - 0.012, BATH_W - 0.014, yy - 0.014, yy + 0.014, tr_z - 0.014, tr_z + 0.014, m["brass"], edge=0.003)
    tube("bath_towel_bar", area, [(tr_x, 14.58, tr_z), (tr_x, 15.36, tr_z)], 0.009, m["brass"], sides=10)
    tw1 = hung_towel("bath_towel_linen", 0.30, 0.44, 0.36, m["bath_towel_cotton"], seed=1)
    tw1.location = (tr_x, 14.82, tr_z)
    tw1.rotation_euler = (0, 0, math.pi / 2)
    tw2 = hung_towel("bath_towel_krama", 0.27, 0.48, 0.38, m["krama"], seed=3)
    tw2.location = (tr_x, 15.16, tr_z)
    tw2.rotation_euler = (0, 0, math.pi / 2)

    box("bath_east_ledge", area, BATH_W - 0.14, BATH_W - 0.014, 15.42, 15.72, 0.92, 0.94, m["rosewood"], edge=0.004)
    box("bath_spare_soap", area, BATH_W - 0.11, BATH_W - 0.04, 15.48, 15.57, 0.94, 0.968, m["bath_soap"], edge=0.005)
    turned("bath_tin_powder", [(0.0, 0.0), (0.026, 0.0), (0.026, 0.11), (0.016, 0.12), (0.016, 0.132), (0.0, 0.132)], BATH_W - 0.08, 15.65, 0.94, m["bath_galv"], segments=16)

    # ========================================================== 8. CAGED PENDANT BULB, CLEATS & DECAY
    lx, ly, lz = 1.68, 15.45, BATH_H - 0.48
    tube("bath_lamp_cord", area, [(lx, ly, BATH_H), (lx, ly, lz + 0.06)], 0.0035, m["cord"], sides=6)
    turned("bath_lamp_shade", [(0.014, 0.0), (0.024, -0.02), (0.115, -0.085), (0.13, -0.095), (0.122, -0.098), (0.105, -0.085), (0.018, -0.025)], lx, ly, lz + 0.06, m["enamel_green"], segments=24)
    cylinder("bath_lamp_holder", area, lx, ly, lz - 0.005, lz + 0.055, 0.018, m["ebonite"], verts=14)
    cylinder("bath_lamp_bulb", area, lx, ly, lz - 0.068, lz - 0.005, 0.026, m["bath_bulb"], verts=14)
    for k in range(4):
        a = k * math.pi / 4
        cage = [(lx + 0.042 * math.sin(t) * math.cos(a), ly + 0.042 * math.sin(t) * math.sin(a), lz - 0.01 - 0.075 * (1 - math.cos(t)) / 2) for t in np.linspace(-math.pi / 2, math.pi / 2, 13)]
        tube(f"bath_lamp_cage_{k}", area, cage, 0.0018, m["rust"], sides=5)
    empty("marker_bath_bulb", area, (lx, ly, lz - 0.08))
    bwire = [(lx, ly, BATH_H - 0.02), (1.84, ly, BATH_H - 0.02), (1.84, y0 + 0.023, BATH_H - 0.02), (1.84, y0 + 0.023, 1.448)]
    tube("bath_wiring", area, bwire, 0.004, m["cord"], sides=6)
    for k, pz_ in enumerate((1.95, 2.65)):
        cl = turned(f"bath_cleat_{k}", [(0.0, 0.0), (0.012, 0.0), (0.012, 0.02), (0.008, 0.024), (0.0, 0.024)], 0, 0, 0, m["bath_porcelain"], segments=10)
        cl.location = (1.84, y0 + 0.014, pz_)
        cl.rotation_euler = (-math.pi / 2, 0, 0)
    vintage_wall_switch(area, m, turned, "bath_switch", (1.84, y0 + 0.014, 1.40), (math.pi / 2, 0, math.pi), toggle_angle_deg=26)

    crack_decal("bath_crack_w", (0.016, 15.85, 2.38), (1, 0, 0), (0, 0.18, 1), (0.44, 0.84), 2)
    crack_decal("bath_crack_n", (2.68, y1 - 0.016, 2.45), (0, -1, 0), (-0.25, 0, 1), (0.44, 0.84), 5)
    crack_decal("bath_crack_e", (BATH_W - 0.016, 15.20, 2.55), (-1, 0, 0), (0, -0.22, 1), (0.38, 0.72), 1)
    cobweb("bath_cobweb_0", (0.016, y1 - 0.016, BATH_H), (1, 0, 0), (0, -1, -0.55), 0.52)
    cobweb("bath_cobweb_1", (BATH_W - 0.016, y0 + 0.016, BATH_H), (-1, 0, 0), (0, 1, -0.5), 0.46)
    cobweb("bath_cobweb_2", (BATH_W - 0.016, y1 - 0.016, BATH_H), (-1, 0, 0), (0, -1, -0.5), 0.48)
