"""Rituals left in the forest round the pagoda: red string, talismans, dolls and a
black-magic altar, after the user's references (3 November 2026). Metres, X east,
Y north. Red cotton cord (sai sin) is tied for protection in Khmer and Thai practice;
here it is strung too thickly, too often, by someone afraid. The skull altar is
sorcery, not temple practice. (Advisor review: every item.)
"""
import math

import numpy as np

from kit import lathe, mesh_object, plain, tube, library_material, sag
from pagoda_architecture import Craft
from pagoda_ruin import erode, place_object, sculpt, sphere


def ritual_materials():
    m = {
        'red_thread': plain('M_ep2_red_thread', (.42, .015, .015), rough=.8),
        'talisman': plain('M_ep2_talisman_paper', (.62, .52, .3), rough=.95),
        'talisman_red': plain('M_ep2_talisman_red', (.5, .06, .04), rough=.95),
        'bone': library_material('clay_plaster', 'M_ep2_stone_bone', colour=(.5, .44, .33), tile=.4),
        'marigold': plain('M_ep2_marigold', (.62, .28, .02), rough=.9),
        'marigold_dead': plain('M_ep2_marigold_dead', (.3, .14, .03), rough=.95),
        'wax_red': plain('M_ep2_wax_red', (.4, .05, .04), rough=.5),
        'ribbon_yellow': plain('M_ep2_ribbon_yellow', (.6, .45, .05), rough=.6),
        'doll_cloth': library_material('rough_linen', 'M_ep2_doll_cloth', tint=(.24, .2, .16)),  # handled, rained on, grimy
    }
    for key in ('talisman', 'talisman_red', 'ribbon_yellow'):
        m[key].use_backface_culling = False
    return m


def talisman(coll, m, name, p, rng, mat=None):
    """A paper tag on a thread, curled by damp, a few inked strokes on it."""
    w, h = .06, rng.uniform(.12, .18)
    x, y, z = p
    a = rng.uniform(0, math.tau)
    ca, sa = math.cos(a), math.sin(a)
    c = Craft()
    pts = [(x - ca * w / 2, y - sa * w / 2, z), (x + ca * w / 2, y + sa * w / 2, z),
           (x + ca * w / 2 + rng.normal(0, .01), y + sa * w / 2, z - h), (x - ca * w / 2, y - sa * w / 2 + rng.normal(0, .01), z - h)]
    paper = mat or m['talisman']
    c.face(paper, pts)
    c.face(paper, list(reversed(pts)))
    objs = c.build(name, coll)
    objs.append(tube(name + '_tie', coll, [(x, y, z + .06), (x, y, z)], .0015, m['red_thread'], sides=3))
    return objs


def bell_charm(coll, m, name, p):
    x, y, z = p
    return [lathe(name, coll, [(0, 0), (.012, .002), (.014, .02), (.006, .03), (0, .032)], x, y, z - .032, m['bronze'], segments=8),
            tube(name + '_tie', coll, [(x, y, z + .05), (x, y, z)], .0015, m['red_thread'], sides=3)]


def hanging_doll(coll, m, name, p, rng, drop=.6):
    """A small cloth doll hung by the neck on red cord: sewn shut, stuffed, stained."""
    x, y, z = p
    parts = [
        sphere(name + '_head', coll, (0, 0, -.05), (.035, .035, .04), m['doll_cloth']),
        sphere(name + '_body', coll, (0, 0, -.13), (.04, .03, .065), m['doll_cloth']),
    ]
    for s in (-1, 1):
        parts.append(tube(name + '_arm', coll, [(s * .03, 0, -.1), (s * .06, 0, -.16)], .012, m['doll_cloth'], sides=6))
        parts.append(tube(name + '_leg', coll, [(s * .015, 0, -.18), (s * .02, 0, -.25)], .013, m['doll_cloth'], sides=6))
    body = sculpt(parts, name, voxel=.006, smooth=2, ratio=.5, rough=.002)
    place_object(body, x, y, z - drop, rng.uniform(0, math.tau), (rng.normal(0, .15), rng.normal(0, .15)))
    objs = [body]
    objs.append(tube(name + '_cord', coll, [(x, y, z), (x, y, z - drop + .02)], .0025, m['red_thread'], sides=3))
    # Stitched-shut eyes and a band of red thread round the neck.
    for s in (-1, 1):
        objs.append(tube(name + '_eye', coll, [(x + s * .012 - .006, y - .034, z - drop - .045), (x + s * .012 + .006, y - .034, z - drop - .045)],
                         .0018, m['red_thread'], sides=3))
    return objs


def red_string_web(coll, m, name, anchors, rng, density=1.0):
    """Red cord strung between anchors, criss-crossed, sagging, hung with tags, bells and
    the odd doll: a whole stretch of forest someone has tried to bind."""
    objs = []
    n = len(anchors)
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() > .55 * density:
                continue
            a, b = anchors[i], anchors[j]
            if math.dist(a[:2], b[:2]) > 9:
                continue
            drop = .1 + math.dist(a, b) * .06
            line = sag(a, b, drop, n=14)
            objs.append(tube(f'{name}_cord_{i}_{j}', coll, line, .0035, m['red_thread'], sides=3))
            for k in range(2, 13, 3):
                if rng.random() < .55:
                    p = line[k]
                    r = rng.random()
                    if r < .6:
                        objs += talisman(coll, m, f'{name}_tag_{i}_{j}_{k}', p, rng, m['talisman_red'] if rng.random() < .3 else None)
                    elif r < .85:
                        objs += bell_charm(coll, m, f'{name}_bell_{i}_{j}_{k}', p)
                    else:
                        objs += hanging_doll(coll, m, f'{name}_doll_{i}_{j}_{k}', p, rng, drop=rng.uniform(.25, .6))
    return objs


def bound_trunk(coll, m, name, x, y, r, rng, turns=7):
    """Red cord wound round a trunk again and again, a yantra tag tucked under it."""
    pts = []
    z0 = rng.uniform(.8, 1.2)
    for k in range(turns * 16 + 1):
        a = k / 16 * math.tau
        pts.append((x + math.cos(a) * (r + .01), y + math.sin(a) * (r + .01), z0 + k / 16 * .045 + .01 * math.sin(a * 3)))
    objs = [tube(name, coll, pts, .004, m['red_thread'], sides=3)]
    a = rng.uniform(0, math.tau)
    objs += talisman(coll, m, name + '_tag', (x + math.cos(a) * (r + .02), y + math.sin(a) * (r + .02), z0 + .15), rng)
    return objs


def boundary_stakes(coll, m, name, points, rng):
    """A ritual boundary of bamboo stakes with red cord between them, a tag on each span."""
    objs = []
    tops = []
    for k, (x, y) in enumerate(points):
        h = rng.uniform(.9, 1.2)
        lean = rng.normal(0, .05, 2)
        top = (x + lean[0], y + lean[1], h)
        tops.append(top)
        objs.append(tube(f'{name}_stake_{k}', coll, [(x, y, -.1), top], .02, m['bamboo_dead'] if 'bamboo_dead' in m else m['bark'], sides=5))
    for k in range(len(tops) - 1):
        a, b = tops[k], tops[k + 1]
        for dz in (0, -.35):
            line = sag((a[0], a[1], a[2] + dz), (b[0], b[1], b[2] + dz), .12, n=10)
            objs.append(tube(f'{name}_cord_{k}_{dz}', coll, line, .003, m['red_thread'], sides=3))
        if rng.random() < .7:
            objs += talisman(coll, m, f'{name}_tag_{k}', sag(a, b, .12, n=10)[5], rng)
    return objs


def skull(coll, m, name, x, y, z, yaw, rng):
    """An old human skull: cranium, brow, cheekbones, jaw and teeth, dark sockets."""
    parts = [
        sphere(name + '_cranium', coll, (0, .01, .1), (.072, .09, .075), m['bone']),
        sphere(name + '_face', coll, (0, -.055, .055), (.058, .04, .055), m['bone']),
        sphere(name + '_brow', coll, (0, -.075, .085), (.06, .02, .018), m['bone']),
        tube(name + '_jaw', coll, [(-.045, -.03, .03), (-.035, -.075, .005), (.035, -.075, .005), (.045, -.03, .03)], .012, m['bone'], sides=6),
    ]
    for s in (-1, 1):
        parts.append(sphere(name + '_cheek', coll, (s * .05, -.06, .055), (.018, .02, .016), m['bone']))
    head = sculpt(parts, name, voxel=.005, smooth=2, ratio=.5, rough=.002)
    objs = [head]
    for s in (-1, 1):
        objs.append(sphere(name + '_socket', coll, (s * .026, -.094, .07), (.019, .012, .017), m['void']))
    objs.append(sphere(name + '_nose', coll, (0, -.097, .045), (.008, .008, .013), m['void']))
    c = Craft()
    for k in range(8):
        tx = (k - 3.5) * .009
        c.block(m['bone'], tx, -.083, .022, .008, .006, .014)
    objs += c.build(name + '_teeth', coll)
    for o in objs:
        place_object(o, x, y, z, yaw)
    return objs


def marigold_garland(coll, m, name, path, rng, dead=.3):
    objs = []
    for (a, b) in zip(path, path[1:]):
        for t in np.linspace(0, 1, 6, endpoint=False):
            p = tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
            mat = m['marigold_dead'] if rng.random() < dead else m['marigold']
            objs.append(sphere(name, coll, p, (.018, .018, .016), mat, segments=8, rings=5))
    return objs


def sorcery_altar(coll, m, name, x, y, yaw, rng):
    """A black-magic altar in the forest: a low stand under a red cloth, a skull on a
    pedestal, melted red candles, a sheaf of burnt-out incense, marigold garlands,
    red and yellow ribbons, little figures. Someone still comes. (Advisor review.)"""
    objs = []
    ca, sa = math.cos(yaw), math.sin(yaw)

    def at(lx, ly, z=0.0):
        return (x + lx * ca - ly * sa, y + lx * sa + ly * ca, z)
    c = Craft()
    for lx, ly, w, d, h, z in [(0, 0, 1.1, .6, .06, .5), (0, .18, 1.0, .25, .45, .56)]:
        px, py, _ = at(lx, ly)
        c.block(m['lacquer'], px, py, z, w, d, h)
    objs += c.build(name + '_stand', coll)
    for sx in (-1, 1):
        for sy in (-1, 1):
            px, py, _ = at(sx * .5, sy * .25)
            objs.append(tube(name + '_leg', coll, [(px, py, 0), (px, py, .5)], .025, m['lacquer'], sides=6))
    px, py, _ = at(0, 0)
    objs.append(mesh_object(name + '_cloth', coll, [at(-.56, -.31, .565), at(.56, -.31, .565), at(.56, -.31, .25), at(-.56, -.31, .25)],
                            [(0, 1, 2, 3), (3, 2, 1, 0)], m['red_cloth']))
    sx, sy, _ = at(0, .18)
    objs.append(lathe(name + '_pedestal', coll, [(.08, 0), (.06, .04), (.04, .1), (.07, .14)], sx, sy, 1.01, m['bronze'], segments=12))
    objs += skull(coll, m, name + '_skull', sx, sy, 1.15, yaw, rng)
    for k in range(7):
        lx = -.42 + k * .14
        px, py, _ = at(lx, -.12)
        h = rng.uniform(.05, .2)
        objs.append(lathe(name + f'_candle_{k}', coll, [(.02, 0), (.026, .01), (.016, .02), (.015, h), (0, h + .005)], px, py, .56, m['wax_red'], segments=8))
        objs.append(lathe(name + f'_drip_{k}', coll, [(.03, 0), (.04, .005), (0, .008)], px, py, .56, m['wax_red'], segments=8))
    px, py, _ = at(.32, .05)
    objs.append(lathe(name + '_incense_pot', coll, [(0, 0), (.07, 0), (.09, .06), (.08, .12), (0, .1)], px, py, .56, m['clay'], segments=12))
    for k in range(40):
        a, r = rng.uniform(0, math.tau), rng.uniform(0, .05)
        bx, by = px + math.cos(a) * r, py + math.sin(a) * r
        objs.append(tube(name + '_stick', coll, [(bx, by, .66), (bx + rng.normal(0, .04), by + rng.normal(0, .04), .66 + rng.uniform(.15, .35))],
                         .002, m['red_cloth'], sides=3))
    for side in (-1, 1):
        path = [at(side * .56, -.31, .56), at(side * .45, -.33, .38), at(side * .3, -.32, .46), at(side * .1, -.31, .55)]
        objs += marigold_garland(coll, m, name + '_garland', path, rng)
        rx, ry, _ = at(side * .5, .1)
        for k, mat in enumerate((m['red_cloth'], m['ribbon_yellow'])):
            objs.append(tube(name + '_ribbon', coll, [(rx, ry, 1.0), (rx + side * .05, ry, .8 - k * .1), (rx + side * .02, ry + .03, .6)], .012, mat, sides=3))
    for k in range(4):
        fx, fy, _ = at(-.35 + k * .22, .02)
        objs.append(lathe(name + f'_figure_{k}', coll, [(0, 0), (.02, 0), (.025, .03), (.015, .06), (.02, .075), (0, .1)], fx, fy, .56, m['gold_leaf'], segments=8))
    erode([o for o in objs if o.name.startswith(name + '_stand')], .004, 9)
    return objs


def handprints(coll, m, name, spots, rng):
    """Old rust-red handprints on walls (tools/drawings/ep2.mjs), one print per decal.
    Each spot is (x, y, z, facing): facing -1 for a wall facing south (-Y), 0 for a
    side wall facing out east or west."""
    import os
    from kit import ROOT, image_material
    mat = m.get('handprints')
    if mat is None:
        path = os.path.join(ROOT, 'art-source/textures/ep2', 'T_ep2_handprints_BC.png')
        mat = m['handprints'] = image_material('M_ep2_handprints', path, rough=.9, cutout=True)
    objs = []
    for k, (x, y, z, facing) in enumerate(spots):
        w, h = rng.uniform(.38, .5), rng.uniform(.75, .95)
        cell = int(rng.integers(0, 4))
        u0, u1 = cell / 4, (cell + 1) / 4
        tilt = rng.normal(0, .12)
        if facing:
            corners = [(x - w / 2, y, z - h), (x + w / 2, y, z - h), (x + w / 2 + tilt * h, y, z), (x - w / 2 + tilt * h, y, z)]
        else:
            out = -.012 if x < 22 else .012
            corners = [(x + out, y - w / 2, z - h), (x + out, y + w / 2, z - h), (x + out, y + w / 2 + tilt * h, z), (x + out, y - w / 2 + tilt * h, z)]
        uvs = [(u0, 0), (u1, 0), (u1, 1), (u0, 1)]
        objs.append(mesh_object(f'{name}_{k}', coll, corners, [(0, 1, 2, 3)], mat, uvs=uvs))
    return objs
