"""Weathered surfaces for Episode 1's colonial-era family house (1932): painted
teak weatherboards whose paint has chalked and peeled back to grey wood, the
pale distemper of the rooms, faded shutter paint, and terracotta Marseille
tiles crusted with lichen and moss. Each map is generated so the board seams in
the texture fall exactly where the board edges are modelled.

Arrays are rows bottom-to-top as Blender stores pixels, so v runs up the wall.
Run inside Blender (imported by the house builders).
"""
import os

import numpy as np

import weathering
from kit import ROOT
from weathering import cracks, fbm, mould_runs, photo_grain, save, textured, tile_noise

OUT = os.path.join(ROOT, "art-source", "textures", "ep1")


def _out():
    weathering.OUT = OUT


def aniso_noise(size, cu, cv, rng):
    """Smooth wrapping noise with `cu` cells across and `cv` up: long along u."""
    grid = rng.random((cv, cu))
    t_u = np.arange(size) * cu / size
    t_v = np.arange(size) * cv / size
    iu0 = t_u.astype(int) % cu
    iu1 = (iu0 + 1) % cu
    iv0 = t_v.astype(int) % cv
    iv1 = (iv0 + 1) % cv
    fu = t_u - np.floor(t_u)
    fv = t_v - np.floor(t_v)
    fu = fu * fu * (3 - 2 * fu)
    fv = fv * fv * (3 - 2 * fv)
    a = grid[iv0][:, iu0] * (1 - fu)[None, :] + grid[iv0][:, iu1] * fu[None, :]
    b = grid[iv1][:, iu0] * (1 - fu)[None, :] + grid[iv1][:, iu1] * fu[None, :]
    return a * (1 - fv)[:, None] + b * fv[:, None]


def wood_grain(size, rng, boards):
    """Teak along u: growth rings bent by slow noise, fine fibres, the odd knot.
    Each board gets its own figure. Returns brightness around 1."""
    v = np.arange(size)[:, None] / size
    board = np.floor(v * boards).astype(int)
    warp = aniso_noise(size, 3, boards * 6, rng)
    rings = np.sin((v * boards * 3.5 + warp * 4 + board * 1.7) * np.pi * 2)
    fibres = aniso_noise(size, 6, size // 3, rng)
    fine = aniso_noise(size, 24, size // 2, rng)
    out = 1 + .09 * rings + .16 * (fibres - .5) + .08 * (fine - .5)
    # Board-to-board tone and a knot or two.
    tone = rng.uniform(.82, 1.12, boards)[board]
    out *= tone
    yy, xx = np.mgrid[:size, :size]
    for _ in range(max(1, boards // 3)):
        kx, ky = rng.uniform(0, size), (rng.integers(0, boards) + rng.uniform(.3, .7)) * size / boards
        r = np.hypot((xx - kx) / 1.0, (yy - ky) * 2.5)
        out *= 1 - .35 * np.exp(-(r / rng.uniform(6, 14)) ** 2)
    return out


def photo_rgb(source, size):
    """A library photo's colour map as an array (rows bottom-to-top)."""
    import bpy
    from kit import LIB
    photo = bpy.data.images.load(os.path.join(LIB, "materials", source, source + "_BC.jpg"), check_existing=False)
    photo.scale(size, size)
    pixels = np.empty(size * size * 4, dtype=np.float32)
    photo.pixels.foreach_get(pixels)
    bpy.data.images.remove(photo)
    return pixels.reshape(size, size, 4)[:, :, :3].astype(np.float64)


def aniso_fbm(size, rng, octaves):
    out = sum(aniso_noise(size, cu, cv, rng) * amp for cu, cv, amp in octaves)
    return (out - out.min()) / (np.ptp(out) or 1)


def painted_boards(name, paint, seed, *, boards=10, size=2048, tile=2.0, peel=.5, grime=.6,
                   wood=(.33, .31, .28), lap=True, rough=.86, joints=True):
    """Boards running along u, `boards` of them per tile, painted `paint` and
    weathered. The paint has chalked and crazed; where the rain beats it has
    lifted in ragged flakes, longer along the grain, worst at each board's lower
    edge and low on the wall, showing silver-grey teak (the grain is a real teak
    photograph, shifted board to board). Each flake keeps a lifted lip of paint.
    `lap`: weatherboards, each lapping over the one below (shadowed lower edge)."""
    _out()
    rng = np.random.default_rng(seed)
    photo = photo_rgb("teak_veneer", size)
    v_rows = np.arange(size)
    board = (v_rows * boards // size)
    shift = rng.integers(0, size, boards)
    teak = np.empty_like(photo)
    for i in range(boards):
        rows = board == i
        teak[rows] = np.roll(photo[rows], shift[i], axis=1)
    lum = teak.mean(axis=2)
    grain = lum / (lum.mean() + 1e-6)
    v = np.broadcast_to(((v_rows / size * boards) % 1.0)[:, None], (size, size))
    # Bare wood: the teak weathered silver-grey, darker in the late wood.
    grey = np.array(wood)[None, None, :] * grain[:, :, None]
    bare = grey * .75 + teak * .25 * .55
    bare *= rng.uniform(.8, 1.1, boards)[board][:, None, None]
    # Paint: a chalky film with faint brush strokes along the grain.
    film = fbm(size, rng, ((3, .5), (8, .3), (21, .2)))
    strokes = aniso_noise(size, 10, size // 6, rng)
    painted = np.array(paint)[None, None, :] * (.8 + .28 * film + .06 * (strokes - .5))[:, :, None]
    painted *= (.97 + .03 * grain)[:, :, None]
    # Where it has failed: a ragged field, longer along the grain, with a set coverage.
    field = aniso_fbm(size, rng, ((4, 10, .45), (9, 24, .3), (23, 60, .17), (64, 150, .08)))
    field += .1 * fbm(size, rng, ((90, .6), (180, .4)))
    patch = fbm(size, rng, ((2, .6), (5, .4)))
    edge = np.clip(1 - v / .3, 0, 1) if lap else np.clip(1 - np.minimum(v, 1 - v) / .15, 0, 1)
    low = np.linspace(1, 0, size)[:, None] ** 2
    field = field + .55 * patch + .22 * edge + .25 * low
    threshold = np.quantile(field, 1 - min(.6, peel * .4))
    gone = field > threshold
    lip = (field > threshold - .022) & ~gone
    under = gone & (field < threshold + .015)
    rgb = np.where(gone[:, :, None], bare, painted)
    rgb[lip] *= 1.1
    rgb[under] *= .45
    # Crazing in the sound paint.
    craze = cracks(size, rng, count=int(90 * peel + 20)) & ~gone
    rgb[craze] *= .7
    # Rain runs and grime, damp low down, a soot cast.
    runs = mould_runs(size, rng, count=90, strength=grime)
    rgb *= (1 - .5 * runs)[:, :, None]
    damp = np.clip(np.linspace(1, -.2, size)[:, None] * fbm(size, rng, ((3, .6), (9, .4))) * 1.5, 0, 1) * grime
    green = np.array([.06, .08, .04])
    rgb = rgb * (1 - .4 * damp[:, :, None]) + green * .4 * damp[:, :, None]
    soot = fbm(size, rng, ((2, .7), (6, .3)))
    rgb *= (1 - .22 * grime * soot)[:, :, None]
    # Board edges: the lap's shadow line or a tongue-and-groove V joint.
    if not joints:
        shade = np.zeros((size, size))
    elif lap:
        shade = np.clip(1 - v / .05, 0, 1) * .55 + np.clip((v - .92) / .08, 0, 1) * .1
    else:
        shade = np.clip(1 - np.minimum(v, 1 - v) / .02, 0, 1) * .65
    rgb *= (1 - shade)[:, :, None]
    height = np.where(gone, .18 * grain - .22, .06 + .02 * film) + np.where(lip, .08, 0) - .04 * runs
    height[craze] -= .05
    height -= shade * .5
    path, normal = save(name, rgb, height, 2.4)
    return textured("M_" + name.replace("T_", ""), path, normal, rough, tile, .9)


def terracotta(name, seed, size=1024, tile=1.0):
    """Old Marseille tiles: fired-clay orange-browns, black lichen crust, pale
    rosettes of lichen, moss in the damp, soot."""
    _out()
    rng = np.random.default_rng(seed)
    grain = photo_grain("clay_plaster", size)
    blotch = fbm(size, rng)
    base = np.array([.42, .17, .09])[None, None, :] * grain[:, :, None] * (.7 + .5 * blotch)[:, :, None]
    burn = fbm(size, rng, ((3, .6), (8, .4)))
    base *= (1 - .3 * np.clip(burn * 1.8 - .7, 0, 1))[:, :, None]
    crust = np.clip((fbm(size, rng, ((6, .45), (17, .35), (45, .2))) - .48) * 3.0, 0, 1)
    black = np.array([.03, .03, .025])
    rgb = base * (1 - .75 * crust[:, :, None]) + black * .75 * crust[:, :, None]
    lichen = fbm(size, rng, ((30, .6), (70, .4))) > .78
    rgb[lichen] = rgb[lichen] * .45 + np.array([.42, .42, .34]) * .55
    orange = (fbm(size, rng, ((22, .6), (55, .4))) > .83) & ~lichen
    rgb[orange] = rgb[orange] * .5 + np.array([.55, .3, .06]) * .5
    moss = np.clip((fbm(size, rng, ((3, .5), (9, .3), (27, .2))) - .62) * 2.2, 0, 1) * (.6 + .4 * fbm(size, rng, ((40, .6), (90, .4))))
    rgb = rgb * (1 - .6 * moss[:, :, None]) + np.array([.07, .1, .03]) * .6 * moss[:, :, None]
    height = .3 * blotch + .2 * grain + .25 * crust + .3 * moss
    path, normal = save(name, rgb, height, 2.0)
    return textured("M_" + name.replace("T_", ""), path, normal, .82, tile, .8)


def colonial_materials():
    """The house's surfaces, keyed for the builders."""
    return {
        # Weatherboards outside: a faded ochre limewash paint gone grey and green below.
        "cl_weatherboard": painted_boards("T_ep1_colonial_weatherboard", (.6, .53, .37), 1932, boards=10, peel=.55, grime=.75),
        # Rooms: tongue-and-groove boards in a pale green distemper, stained and flaking.
        "cl_room_boards": painted_boards("T_ep1_colonial_room_boards", (.42, .46, .38), 1933, boards=20, peel=.38, grime=.45,
                                         lap=False, wood=(.26, .22, .18)),
        # Ceilings: the same boards, darker with lamp soot.
        "cl_ceiling": painted_boards("T_ep1_colonial_ceiling", (.36, .35, .3), 1934, boards=20, peel=.3, grime=.9,
                                     lap=False, wood=(.2, .17, .14)),
        # Shutters, louvres, fretwork and trim: a once-green paint, chalky.
        "cl_shutter": painted_boards("T_ep1_colonial_shutter", (.2, .3, .25), 1935, boards=2, size=1024, tile=.8,
                                     peel=.5, grime=.5, lap=False, joints=False),
        # Trim and posts: dark oiled teak, its paint long gone.
        "cl_trim": painted_boards("T_ep1_colonial_trim", (.16, .11, .07), 1936, boards=1, size=1024, tile=1.0,
                                  peel=.25, grime=.55, lap=False, wood=(.2, .17, .14), rough=.7, joints=False),
        "cl_terracotta": terracotta("T_ep1_colonial_terracotta", 1937),
    }
