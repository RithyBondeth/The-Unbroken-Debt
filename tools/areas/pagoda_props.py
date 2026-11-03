"""Episode 2 hall furnishings and gameplay props after the user's Khmer vihara
references (2 November 2026): a white-faced Buddha in a saffron robe on a lotus throne,
a stepped altar with gilded bodhi trees and a crimson curtain swag, carved pediment
devas, low offering tables, a sculpted naga balustrade and the family emblem.
Metres, X east, Y north. Everything is aged: dust, wax, faded cloth, tarnish.
"""
import math

import numpy as np

from kit import collider, lathe, mesh_object, plain, tube, library_material
from pagoda_architecture import Craft
from pagoda_ruin import erode, place_object, sculpt, sphere


def prop_materials():
    m = {
        # The image is painted plaster: ivory skin, saffron robe, both dulled by soot.
        'buddha_skin': library_material('clay_plaster', 'M_ep2_stone_buddha_skin', colour=(.56, .52, .43), tile=.8),
        'robe': library_material('clay_plaster', 'M_ep2_buddha_robe', colour=(.6, .23, .035), tile=.8),
        'curtain': library_material('rough_linen', 'M_ep2_curtain', colour=(.42, .025, .045), tile=.5),
        'lotus_petal': library_material('clay_plaster', 'M_ep2_lotus_petal', colour=(.5, .17, .17), tile=.6),
        'gold_leaf': plain('M_ep2_gold_leaf', (.5, .36, .11), rough=.38, metal=.75),
        'silver_old': plain('M_ep2_silver_old', (.26, .26, .24), rough=.58, metal=.65),
        'slate': library_material('clay_plaster', 'M_ep2_stone_slate', colour=(.085, .085, .08), tile=.6),
        'rice_cooked': plain('M_ep2_rice_cooked', (.62, .6, .5), rough=.85),
        'banana_leaf': plain('M_ep2_banana_leaf', (.07, .12, .045), rough=.7),
        'lacquer': library_material('dark_wooden_planks', 'M_ep2_teak_lacquer', tint=(.32, .14, .08)),
        'paint_green': library_material('clay_plaster', 'M_ep2_paint_green', colour=(.05, .15, .09), tile=1.2),
        'paint_yellow': library_material('clay_plaster', 'M_ep2_paint_yellow', colour=(.45, .33, .07), tile=1.2),
        'iron': plain('M_ep2_iron_rust', (.09, .055, .035), rough=.8, metal=.55),
        'net': plain('M_ep2_mosquito_net', (.5, .5, .46), rough=1, alpha=.45),
        'pillow': library_material('rough_linen', 'M_ep2_pillow', tint=(.48, .44, .36)),
    }
    m['net'].blend_method = 'BLEND'
    # Hand-inked yantra on aged cotton (tools/drawings/ep2.mjs; Khmer text under review).
    import os
    from kit import ROOT, image_material
    for kind in ('circle', 'square'):
        path = os.path.join(ROOT, 'art-source/textures/ep2', f'T_ep2_yantra_{kind}_BC.png')
        if not os.path.exists(path):
            raise SystemExit(f'Missing {path}: run `npm run drawings -- ep2` first.')
        m['yantra_' + kind] = image_material('M_ep2_yantra_' + kind, path, rough=.95)
        m['yantra_' + kind].use_backface_culling = False
    for key in ('robe', 'curtain'):
        m[key].use_backface_culling = False
    return m


def extrude(coll, name, outline, t, mat, origin=(0, 0, 0)):
    """A solid slab from an outline in the XZ plane (left, over the top, to the right),
    `t` thick in Y, wound outward on every face."""
    ox, oy, oz = origin
    n = len(outline)
    verts = [(ox + px, oy + t, oz + pz) for px, pz in outline] + [(ox + px, oy - t, oz + pz) for px, pz in outline]
    faces = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
    for j in range(n):
        k = (j + 1) % n
        faces.append((n + j, n + k, k, j))
    return mesh_object(name, coll, verts, faces, mat)


# ------------------------------------------------------------------ the hall image


def hall_buddha(coll, m, x, y, z, s, yaw):
    """The red lotus throne of the hall's seated Buddha."""
    # The image itself is a real seated body cast as plaster (tools/ep2/build-cinematics.py).
    # The lotus throne: drum, double ring of faded crimson petals, cushion.
    throne = [lathe('hall_buddha_throne', coll, [(.62 * s, -.32 * s), (.6 * s, -.26 * s), (.48 * s, -.2 * s), (.46 * s, -.1 * s), (.55 * s, -.04 * s), (.55 * s, 0), (0, 0)],
                    0, 0, 0, m['gilt'], segments=40)]
    for row, (r, z0, h, n) in enumerate([(.6 * s, -.22 * s, .2 * s, 22), (.55 * s, -.12 * s, .16 * s, 22)]):
        ring = lathe(f'hall_buddha_lotus_{row}', coll, [(r - .04 * s, 0), (r + .05 * s, h * .3), (r + .03 * s, h * .75), (r - .03 * s, h)],
                     0, 0, z0, m['lotus_petal'], segments=n * 8)
        for v in ring.data.vertices:
            a = math.atan2(v.co.y, v.co.x) + (math.pi / n if row else 0)
            petal = abs(math.cos(a * n / 2))
            rad = math.hypot(v.co.x, v.co.y)
            k = (rad + .03 * s * petal) / max(rad, 1e-6)
            v.co.x *= k
            v.co.y *= k
            if (v.co.z - z0) / h > .9:
                v.co.z -= h * .45 * (1 - petal ** 2)
        throne.append(ring)
    for o in throne:
        place_object(o, x, y, z + .32 * s, yaw)
    return throne


def relief_deva(coll, m, name, x, y, z, h, end):
    """A praying deva carved in the pediment, flattened into relief, in a flame frame."""
    s = h
    parts = [
        sphere(name + '_body', coll, (0, 0, .42 * s), (.13 * s, .09 * s, .2 * s), m['carved']),
        sphere(name + '_legs', coll, (0, -.02 * s, .15 * s), (.22 * s, .1 * s, .1 * s), m['carved']),
        sphere(name + '_head', coll, (0, 0, .69 * s), (.07 * s, .065 * s, .085 * s), m['carved']),
        tube(name + '_crown', coll, [(0, 0, .74 * s), (0, 0, .98 * s)], .055 * s, m['carved'], sides=10, radius_end=.004),
        sphere(name + '_hands', coll, (0, -.09 * s, .5 * s), (.03 * s, .03 * s, .07 * s), m['carved']),
    ]
    for side in (-1, 1):
        parts.append(tube(name + '_arm', coll, [(side * .12 * s, 0, .56 * s), (side * .1 * s, -.06 * s, .44 * s), (side * .02 * s, -.09 * s, .48 * s)], .03 * s, m['carved'], sides=8))
    body = sculpt(parts, name, voxel=.012 * max(s, .6), smooth=3, ratio=.4, rough=.002)
    for v in body.data.vertices:
        v.co.y *= .4
    place_object(body, x, y, z, 0 if end < 0 else math.pi)
    frame = [(x + math.sin(t) * .38 * s * (1.05 - .3 * math.cos(t * 2)), y + end * .02, z + .05 * s + (1 - math.cos(t)) * .55 * s) for t in np.linspace(-1.55, 1.55, 30)]
    tube(name + '_frame', coll, frame, .025 * s, m['carved'], sides=6)
    for j, t in enumerate(np.linspace(-1.4, 1.4, 9)):
        px, pz = frame[int((t + 1.55) / 3.1 * 29)][0], frame[int((t + 1.55) / 3.1 * 29)][2]
        out = (px - x) / (abs(px - x) + .001)
        tube(name + '_flame', coll, [(px, y + end * .02, pz), (px + out * .08 * s, y + end * .02, pz + .1 * s), (px + out * .03 * s, y + end * .02, pz + .16 * s)],
             .014 * s, m['carved'], sides=5, radius_end=.002)
    return body


# ------------------------------------------------------------------ altar


def money_tree(coll, m, name, x, y, z, h, rng):
    """A gilded bodhi tree of the kind set on altars: a trunk, branching twigs and
    heart-shaped gold leaves, the gilding worn and dulled."""
    parts = [tube(name, coll, [(x, y, z), (x, y, z + h * .45)], .015, m['gold_leaf'], sides=6, radius_end=.01)]
    leaves = Craft()
    for j in range(7):
        a = j * math.tau / 7 + rng.uniform(-.3, .3)
        base = (x, y, z + h * (.3 + .1 * (j % 3)))
        tip = (x + math.cos(a) * h * .28, y + math.sin(a) * h * .28, base[2] + h * rng.uniform(.25, .55))
        parts.append(tube(name + '_twig', coll, [base, tip], .007, m['gold_leaf'], sides=4))
        for k in range(5):
            t = .35 + k * .15
            p = tuple(base[i] + (tip[i] - base[i]) * t for i in range(3))
            la = a + rng.uniform(-1.2, 1.2)
            ca, sa = math.cos(la), math.sin(la)
            w, l = .028, .07
            pts = [p, (p[0] + ca * l * .3 - sa * w, p[1] + sa * l * .3 + ca * w, p[2] - .01), (p[0] + ca * l, p[1] + sa * l, p[2] - .04),
                   (p[0] + ca * l * .3 + sa * w, p[1] + sa * l * .3 - ca * w, p[2] - .01)]
            leaves.face(m['gold_leaf'], pts)
            leaves.face(m['gold_leaf'], list(reversed(pts)))
    parts += leaves.build(name + '_leaves', coll)
    parts.append(lathe(name + '_pot', coll, [(.06, 0), (.08, .05), (.06, .1), (.07, .12), (0, .12)], x, y, z - .01, m['gilt'], segments=12))
    return parts


def curtain_swag(coll, m, name, x0, x1, y, top, drop, rng):
    """A crimson curtain hung in a deep swag from the beam, faded, its lower edge
    rotted and torn."""
    nx, ny = 44, 10
    verts, faces = [], []
    for j in range(ny + 1):
        t = j / ny
        for i in range(nx + 1):
            u = i / nx
            sag = drop * math.sin(u * math.pi) * t
            fold = .06 * math.sin(u * 46) * (.3 + t)
            px = x0 + (x1 - x0) * u
            pz = top - .15 - sag - .25 * t
            if j == ny:
                pz -= rng.uniform(0, .12)
            verts.append((px, y - .35 * math.sin(u * math.pi) * t + fold, pz))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    swag = mesh_object(name, coll, verts, faces, m['curtain'], smooth=True)
    # Side drapes falling to the floor, gathered and tied back at shoulder height.
    drapes = []
    for edge, inward in ((x0, 1), (x1, -1)):
        verts, faces = [], []
        nx2, ny2 = 8, 14
        for j in range(ny2 + 1):
            t = j / ny2
            h = top - .15 - (top - .4) * t
            pinch = 1 - .75 * math.exp(-((t - .45) / .12) ** 2)
            for i in range(nx2 + 1):
                u = i / nx2
                px = edge + inward * (.55 * u * pinch + .06)
                verts.append((px, y - .1 + .05 * math.sin(u * 19 + t * 3), h))
        for j in range(ny2):
            for i in range(nx2):
                a = j * (nx2 + 1) + i
                faces.append((a, a + 1, a + nx2 + 2, a + nx2 + 1))
        drapes.append(mesh_object(name + '_drape', coll, verts, faces, m['curtain'], smooth=True))
    return [swag] + drapes


def stepped_altar(coll, m, x, y, base):
    c = Craft()
    tiers = [(2.8, 2.0, .34, m['red']), (2.2, 1.55, .3, m['paint_green']), (1.7, 1.2, .26, m['red'])]
    z = base
    for w, d, h, mat in tiers:
        c.block(mat, x, y, z, w, d, h)
        c.block(m['gilt'], x, y, z + h, w + .06, d + .06, .04)
        z += h + .04
    c.build('hall_altar_tiers', coll)
    collider('hall_altar', coll, x - 1.4, x + 1.4, y - 1.0, y + 1.0, 0, z, 'stone')
    return z


# ------------------------------------------------------------------ offerings


def offering_table(coll, m, name, x, y, z0=0.0):
    """A low lacquered offering table with turned legs and an apron."""
    c = Craft()
    c.block(m['lacquer'], x, y, z0 + .38, .96, .7, .06)
    for side in (-1, 1):
        c.block(m['lacquer'], x, y + side * .3, z0 + .3, .88, .03, .08)
        c.block(m['lacquer'], x + side * .43, y, z0 + .3, .03, .62, .08)
    objs = c.build(name, coll)
    for sx in (-1, 1):
        for sy in (-1, 1):
            objs.append(lathe(name + '_leg', coll, [(.035, 0), (.05, .03), (.03, .1), (.045, .2), (.03, .3), (.04, .38)], x + sx * .4, y + sy * .27, z0, m['lacquer'], segments=10))
    erode(objs, .004, 9)
    return objs


def footed_tray(coll, m, name, x, y, z, r=.3):
    return lathe(name, coll, [(0, 0), (.12, 0), (.1, .03), (.06, .06), (.07, .09), (r, .1), (r + .04, .13), (r + .03, .15), (r - .02, .12), (0, .12)],
                 x, y, z, m['bronze'], segments=32)


def rice_ball(coll, m, name, x, y, z, rng):
    """Pressed sticky rice: a lumpy, grain-pitted mound, not a sphere."""
    ball = sphere(name, coll, (x, y, z + .045), (.07, .065, .05), m['rice_cooked'], segments=20, rings=14)
    seed = rng.uniform(0, 9)
    for v in ball.data.vertices:
        n = v.co.normalized()
        v.co *= 1 + .08 * math.sin(n.x * 9 + seed) * math.cos(n.y * 7) + .04 * math.sin(n.z * 23 + n.x * 17)
        if v.co.z < -.4:
            v.co.z = -.4
    return ball


def banana_leaf(coll, m, name, x, y, z, w=.34, l=.5, yaw=0.0):
    nx, ny = 6, 4
    verts, faces = [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, t = i / nx - .5, j / ny - .5
            verts.append((u * l, t * w, .012 * (u * 2) ** 2 + .01 * (t * 2) ** 2))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    leaf = mesh_object(name, coll, verts, faces, m['banana_leaf'], smooth=True)
    return place_object(leaf, x, y, z, yaw)


# ------------------------------------------------------------------ guardians of the way


def naga_rail(coll, m, name, x, rng, y0=-31.2, y1=-25.7):
    """A naga balustrade in old grey stone: a stepped base, a scaled body rising to a
    fan of five hooded heads with a flame crest, all fused into one carving."""
    side = 1 if x > 0 else -1
    c = Craft()
    c.block(m['mould_grey'], x, (y0 + y1) / 2 - .15, 0, .62, y1 - y0 + .3, .18)
    c.block(m['mould_white'], x, (y0 + y1) / 2 - .15, .18, .48, y1 - y0 + .2, .22)
    base = c.build(name + '_base', coll)
    erode(base, .01, 5)
    lx = 0.0
    body_pts = [(0, -5.3, 0), (0, -3.6, .02), (0, -1.8, .05), (0, -.7, .15), (0, -.25, .45), (0, -.05, .85), (0, .03, 1.15)]
    parts = [tube(name + '_body', coll, body_pts, .17, m['mould_grey'], sides=14, radius_end=.16)]
    parts.append(sphere(name + '_tail', coll, (0, -5.45, .02), (.1, .2, .08), m['mould_grey']))
    hh = 1.3
    heads = []
    for k in range(5):
        a = (k - 2) * .45
        hx, hz = math.sin(a) * .66, hh + math.cos(a) * .36 - .1
        heads.append((hx, hz))
        parts.append(tube(name + '_neck', coll, [(0, .03, 1.05), (hx * .5, 0, (1.05 + hz) / 2 - .05), (hx, -.04, hz - .12)], .085, m['mould_grey'], sides=10, radius_end=.075))
        # The cobra hood flares wide and flat behind each head.
        parts.append(sphere(name + '_hood', coll, (hx, .0, hz), (.18, .055, .26), m['mould_grey']))
        parts.append(sphere(name + '_head', coll, (hx, -.09, hz + .05), (.085, .1, .07), m['mould_grey']))
        parts.append(sphere(name + '_snout', coll, (hx, -.2, hz + .03), (.055, .09, .045), m['mould_grey']))
        parts.append(tube(name + '_crest', coll, [(hx, .04, hz + .22), (hx * 1.08, .05, hz + .4), (hx * 1.02, .04, hz + .55)], .04, m['mould_grey'], sides=6, radius_end=.004))
    naga = sculpt(parts, name, voxel=.018, smooth=4, ratio=.45, rough=.004, seed=int(x))
    for v in naga.data.vertices:
        if v.co.z < 1.2 and v.co.y < .1:
            # Overlapping scale rows along the body.
            v.co += v.normal * .006 * (abs(math.sin(v.co.y * 38 + math.atan2(v.co.x, v.co.z - .4) * 3)) - .5)
    place_object(naga, x, y1 - .1, .4, 0)
    eyes = []
    for hx, hz in heads:
        for e in (-1, 1):
            eyes.append(sphere(name + '_eye', coll, (x + hx + e * .055, y1 - .1 - .17, .4 + hz + .1), (.018, .012, .015), m['void']))
    collider(name, coll, x - .31, x + .31, y0 - .3, y1 + .1, 0, 1.4, 'stone')
    return [naga] + base + eyes


# ------------------------------------------------------------------ the family marks


def family_emblem(coll, m, name, x, y, z):
    """The silver five-petalled flower in low relief, tarnished almost black at the edges."""
    backing = lathe(name + '_plaque', coll, [(0, 0), (.17, 0), (.18, .02), (0, .02)], 0, 0, 0, m['slate'], segments=24)
    backing.rotation_euler = (math.pi / 2, 0, 0)
    backing.location = (x, y + .02, z)
    parts = [backing, lathe(name + '_boss', coll, [(0, 0), (.04, 0), (.035, .015), (0, .022)], 0, 0, 0, m['silver_old'], segments=16)]
    parts[-1].rotation_euler = (math.pi / 2, 0, 0)
    parts[-1].location = (x, y - .002, z)
    petals = Craft()
    for k in range(5):
        a = math.pi / 2 + k * math.tau / 5
        ca, sa = math.cos(a), math.sin(a)
        for side in (1,):
            pts = [(x + ca * .03, y, z + sa * .03), (x + ca * .07 - sa * .035, y - .012, z + sa * .07 + ca * .035),
                   (x + ca * .12, y - .006, z + sa * .12), (x + ca * .07 + sa * .035, y - .012, z + sa * .07 - ca * .035)]
            petals.face(m['silver_old'], pts)
            petals.face(m['silver_old'], list(reversed(pts)))
    parts += petals.build(name + '_petals', coll)
    ring = [(x + math.cos(t) * .15, y - .004, z + math.sin(t) * .15) for t in np.linspace(0, math.tau, 33)]
    parts.append(tube(name + '_ring', coll, ring, .008, m['silver_old'], sides=5))
    return parts


def inscribed_tablet(coll, m, name, x, y, z, rng):
    """A dark stone tablet set into the pedestal, its incised lines worn past reading.
    (No invented Khmer: the text is given in English by the game.)"""
    c = Craft()
    c.block(m['slate'], x, y, z, .42, .04, .28)
    c.block(m['mould_grey'], x, y - .004, z - .02, .48, .04, .02)
    c.block(m['mould_grey'], x, y - .004, z + .28, .48, .04, .025)
    objs = c.build(name, coll)
    for row in range(5):
        zz = z + .05 + row * .045
        # Incised strokes, worn through in places.
        px, end = x - .17, x + .17 - rng.uniform(0, .1) * (row == 4)
        while px < end:
            length = rng.uniform(.03, .1)
            pts = [(px + t, y - .021, zz + .003 * math.sin((px + t) * 160)) for t in np.linspace(0, min(length, end - px), 4)]
            if rng.random() > .2:
                objs.append(tube(name + '_line', coll, pts, .0025, m['void'], sides=3))
            px += length + rng.uniform(.008, .03)
    return objs


# ------------------------------------------------------------------ the hungry dead


def hungry_ghost(coll, m, name, seed):
    """A preta as temple murals show them: very tall and starved to the bone, hunched,
    a swollen belly, a needle-thin neck and pinhole mouth, arms long enough to drag,
    hair hanging lank. Feet at the origin, facing -Y. One fused sculpt."""
    rng = np.random.default_rng(seed)
    sk = m['skin']
    parts = [
        # Swollen, sagging belly under a caved-in ribcage.
        # The belly sags like a filled sack, heaviest low down.
        sphere('pret_belly', coll, (0, -.14, 1.98), (.3, .3, .28), sk),
        sphere('pret_belly_sag', coll, (0, -.2, 1.74), (.37, .36, .3), sk),
        sphere('pret_belly_fold', coll, (0, -.27, 1.62), (.3, .26, .14), sk),
        sphere('pret_pelvis', coll, (0, .02, 1.6), (.22, .16, .14), sk),
        sphere('pret_ribcage', coll, (0, -.2, 2.42), (.23, .19, .3), sk),
        sphere('pret_shoulders', coll, (0, -.22, 2.66), (.27, .13, .07), sk),
        tube('pret_spine', coll, [(0, .1, 1.62), (0, .08, 2.0), (0, .0, 2.4), (0, -.12, 2.68)], .07, sk, sides=10),
        # A long thin neck thrust forward, the skull hanging low.
        tube('pret_neck', coll, [(0, -.22, 2.7), (0, -.36, 2.95), (0, -.52, 3.06)], .045, sk, sides=10, radius_end=.035),
        sphere('pret_skull', coll, (0, -.62, 3.08), (.145, .175, .18), sk),
        sphere('pret_jaw', coll, (0, -.74, 2.95), (.08, .09, .075), sk),
    ]
    for side in (-1, 1):
        parts += [
            sphere('pret_cheek', coll, (side * .075, -.74, 3.06), (.035, .03, .03), sk),
            sphere('pret_brow', coll, (side * .06, -.75, 3.14), (.05, .03, .025), sk),
            tube('pret_collarbone', coll, [(side * .03, -.32, 2.66), (side * .25, -.26, 2.7)], .025, sk, sides=6),
            # Arms reaching nearly to the knees, knobbed at the elbow, with long clawed fingers.
            tube('pret_upper_arm', coll, [(side * .27, -.22, 2.66), (side * .36, -.3, 2.25), (side * .4, -.36, 1.92)], .045, sk, sides=10, radius_end=.035),
            sphere('pret_elbow', coll, (side * .4, -.36, 1.92), (.05, .05, .055), sk),
            tube('pret_forearm', coll, [(side * .4, -.36, 1.92), (side * .42, -.5, 1.5), (side * .4, -.6, 1.18)], .035, sk, sides=10, radius_end=.026),
            sphere('pret_hand', coll, (side * .4, -.62, 1.14), (.045, .03, .06), sk),
            # Legs: bone and tendon, the knees standing out.
            tube('pret_thigh', coll, [(side * .17, .0, 1.62), (side * .22, -.14, 1.2), (side * .23, -.2, .9)], .065, sk, sides=10, radius_end=.045),
            sphere('pret_knee', coll, (side * .23, -.21, .9), (.065, .06, .07), sk),
            tube('pret_shin', coll, [(side * .23, -.2, .9), (side * .2, -.08, .45), (side * .19, .0, .1)], .04, sk, sides=10, radius_end=.03),
            tube('pret_foot', coll, [(side * .19, .04, .06), (side * .2, -.14, .04), (side * .21, -.3, .025)], .035, sk, sides=8, radius_end=.02),
        ]
        for rib in range(6):
            z = 2.22 + rib * .065
            parts.append(tube('pret_rib', coll, [(side * .02, -.38, z + .02), (side * .16, -.37, z), (side * .25, -.24, z - .02), (side * .22, -.05, z - .03)], .016, sk, sides=6))
        for f in range(4):
            spread = (f - 1.5) * .022
            parts.append(tube('pret_finger', coll, [(side * .4 + spread, -.63, 1.1), (side * .4 + spread * 1.4, -.67, .92), (side * .4 + spread * 1.6, -.62, .76)],
                              .011, sk, sides=6, radius_end=.003))
    for j in range(7):
        parts.append(sphere('pret_vertebra', coll, (0, .13 - j * .02, 1.7 + j * .14), (.03, .03, .03), sk))
    body = sculpt(parts, name, voxel=.02, smooth=3, ratio=.5, rough=.003, seed=seed)
    # Skin hanging in loose folds over the belly and drawn tight over bone elsewhere.
    for v in body.data.vertices:
        sag = max(0.0, 1 - abs(v.co.z - 1.75) / .35) * (v.co.y < -.1)
        v.co += v.normal * (.006 * math.sin(v.co.z * 70 + v.co.x * 20) * sag + .002 * math.sin(v.co.x * 90) * math.sin(v.co.z * 80))
    extras = []
    for side in (-1, 1):
        extras.append(sphere('pret_eye_socket', coll, (side * .05, -.765, 3.09), (.035, .02, .03), m['void']))
        extras.append(sphere('pret_blind_eye', coll, (side * .05, -.775, 3.09), (.009, .004, .008), m['eye']))
    extras.append(sphere('pret_pinhole_mouth', coll, (0, -.795, 2.97), (.008, .005, .01), m['void']))
    # Lank hair hanging from the scalp over the face and down the back.
    for j in range(80):
        a = rng.uniform(-math.pi, math.pi)
        top = (math.sin(a) * .13, -.62 + math.cos(a) * .15, 3.18 + rng.uniform(-.03, .05))
        front = math.cos(a) < -.2
        length = rng.uniform(.6, 1.4) if not front else rng.uniform(.35, .75)
        out = (top[0] * 1.5, top[1] + (-.1 if front else .12))
        phase = rng.uniform(0, math.tau)
        pts = [top] + [(out[0] + .03 * math.sin(t * 9 + phase) + rng.normal(0, .01), out[1] + .02 * math.cos(t * 7 + phase), top[2] - length * t)
                       for t in (.2, .4, .6, .8, 1.0)]
        extras.append(tube('pret_hair', coll, pts, rng.uniform(.003, .006), m['hair'], sides=3, radius_end=.0015))
    return [body] + extras


# ------------------------------------------------------------------ the ground


def leaf_litter(coll, m, name, x, y, rx, ry, rng):
    """A drift of dry leaves with no edge: an irregular, feathered leaf-mould ground
    under hundreds of curled leaves and twigs that spill out past it."""
    from forest_detail import Leaves, forest_materials
    rings, seg = 6, 36
    lobes = [(rng.uniform(.08, .2), int(rng.integers(2, 6)), rng.uniform(0, math.tau)) for _ in range(3)]
    verts, faces = [(x, y, .016)], []
    for i in range(1, rings + 1):
        t = i / rings
        for j in range(seg):
            a = j * math.tau / seg
            r = t * (1 + sum(amp * math.sin(a * k + ph) for amp, k, ph in lobes)) * (1 + rng.uniform(-.06, .06) * t)
            verts.append((x + math.cos(a) * rx * r, y + math.sin(a) * ry * r, .016 - .02 * t ** 3))
    for j in range(seg):
        faces.append((0, 1 + j, 1 + (j + 1) % seg))
    for i in range(rings - 1):
        for j in range(seg):
            a, b = 1 + i * seg + j, 1 + i * seg + (j + 1) % seg
            faces.append((a, a + seg, b + seg, b))
    ground = mesh_object(name, coll, verts, faces, m['leaves'], smooth=True)
    mats = forest_materials()
    litter = Leaves()
    for _ in range(int(rx * ry * 240)):
        a, d = rng.uniform(0, math.tau), math.sqrt(rng.random()) * 1.25
        px, py = x + math.cos(a) * rx * d, y + math.sin(a) * ry * d
        litter.add((px, py, .02 + .02 * (1 - d) * rng.random()), rng.uniform(0, math.tau), rng.uniform(.08, .22),
                   rng.uniform(.04, .09), .015, 3, rng.uniform(-.25, -.05))
    parts = [ground, litter.build(name + '_leaves', coll, mats['litter'])]
    for j in range(int(rng.integers(4, 8))):
        a, d = rng.uniform(0, math.tau), rng.uniform(0, 1.1)
        px, py = x + math.cos(a) * rx * d, y + math.sin(a) * ry * d
        b = rng.uniform(0, math.tau)
        length = rng.uniform(.3, .8)
        parts.append(tube(name + '_twig', coll, [(px, py, .03), (px + math.cos(b) * length * .5, py + math.sin(b) * length * .5, .045),
                                                 (px + math.cos(b + .3) * length, py + math.sin(b + .3) * length, .03)],
                          rng.uniform(.006, .014), m['bark'], sides=4, radius_end=.003))
    return parts


def sutra_table(coll, m, name, x, y, z0, rng):
    """The monk's low reading table: lacquered teak, a palm-leaf manuscript bundle
    tied with cord, a lacquered betel box and a water bowl."""
    objs = offering_table(coll, m, name, x, y, z0)
    c = Craft()
    for k in range(9):
        c.block(m['paper'], x - .18, y + .02, z0 + .44 + k * .007, .46, .055, .006)
    c.block(m['lacquer'], x - .18, y + .02, z0 + .44 + 9 * .007, .5, .065, .012)
    objs += c.build(name + '_manuscript', coll)
    objs.append(tube(name + '_cord', coll, [(x - .18, y - .02, z0 + .43), (x - .18, y - .02, z0 + .52), (x - .18, y + .06, z0 + .52), (x - .18, y + .06, z0 + .43)],
                     .005, m['rope'], sides=4))
    objs.append(lathe(name + '_bowl', coll, [(0, 0), (.04, 0), (.07, .03), (.08, .07), (0, .06)], x + .28, y - .12, z0 + .44, m['bronze'], segments=16))
    objs.append(lathe(name + '_water', coll, [(0, 0), (.072, 0)], x + .28, y - .12, z0 + .5, m['water'], segments=14))
    c = Craft()
    c.block(m['lacquer'], x + .24, y + .14, z0 + .44, .16, .12, .07)
    c.block(m['red'], x + .24, y + .14, z0 + .51, .17, .13, .02)
    objs += c.build(name + '_betel_box', coll)
    return objs


# ------------------------------------------------------------------ the hall entrance


def hall_doors(coll, m, x, y, floor, rng):
    """Two carved teak door leaves standing ajar inside the doorway: raised panels,
    a lozenge-carved centre rail, iron ring pulls, red paint flaking off."""
    objs = []
    for side in (-1, 1):
        c = Craft()
        w, h, t = 1.3, 2.62, .07
        c.block(m['carved'], w / 2, 0, 0, w, t, h)
        for z0, z1 in ((.12, .95), (1.1, 1.75), (1.9, 2.5)):
            c.block(m['red'], w / 2, -t / 2 - .006, z0, w - .22, .012, z1 - z0)
            c.block(m['carved'], w / 2, -t / 2 - .016, z0 + .06, w - .34, .012, z1 - z0 - .12)
        c.block(m['gilt'], w / 2, -t / 2 - .012, 1.0, w - .1, .016, .06)
        leaf = c.build(f'hall_door_{side}', coll)
        ring = [(w - .12 + .05 * math.cos(a), -t / 2 - .03, 1.25 + .05 * math.sin(a)) for a in np.linspace(0, math.tau, 13)]
        leaf.append(tube(f'hall_door_ring_{side}', coll, ring, .008, m['iron'], sides=5))
        for o in leaf:
            o.location = (x + side * 1.33, y, floor)
            # Hinged at the jambs and swung in, leaving the doorway open behind the chains.
            o.rotation_euler = (0, 0, (math.pi if side > 0 else 0) + side * math.radians(rng.uniform(95, 110)) * -1)
        objs += leaf
    return objs


def sealed_doorway(coll, m, name, x, y, z0, width, height, rng):
    """What seals the hall: rusted chains crossed over the opening and padlocked, a
    white cotton cord strung through them, a yantra cloth nailed across the middle."""
    parts = []
    link = .07
    for a, b in [((x - width / 2, y, z0 + height * .92), (x + width / 2, y, z0 + height * .18)),
                 ((x + width / 2, y, z0 + height * .92), (x - width / 2, y, z0 + height * .18)),
                 ((x - width / 2, y, z0 + height * .55), (x + width / 2, y, z0 + height * .5))]:
        length = math.dist(a, b)
        n = int(length / link)
        for k in range(n):
            t = (k + .5) / n
            sag = .12 * 4 * t * (1 - t)
            p = (a[0] + (b[0] - a[0]) * t, a[1] - .02, a[2] + (b[2] - a[2]) * t - sag)
            yaw = math.atan2(b[2] - a[2], b[0] - a[0])
            ring = [(p[0] + math.cos(yaw) * .045 * math.cos(s), p[1] + (.025 * math.sin(s) if k % 2 else 0),
                     p[2] + math.sin(yaw) * .045 * math.cos(s) + (0 if k % 2 else .025 * math.sin(s))) for s in np.linspace(0, math.tau, 9)]
            parts.append(tube(name + '_link', coll, ring, .009, m['iron'], sides=4))
    c = Craft()
    c.block(m['iron'], x, y - .05, z0 + height * .5 - .1, .12, .05, .1)
    parts += c.build(name + '_padlock', coll)
    parts.append(tube(name + '_shackle', coll, [(x - .04, y - .05, z0 + height * .5), (x - .04, y - .05, z0 + height * .5 + .06), (x + .04, y - .05, z0 + height * .5 + .06), (x + .04, y - .05, z0 + height * .5)],
                      .01, m['iron'], sides=5))
    cord = [(x - width / 2 + width * t, y - .06, z0 + height * (.72 - .08 * math.sin(t * math.pi))) for t in np.linspace(0, 1, 16)]
    parts.append(tube(name + '_white_cord', coll, cord, .004, m['thread'], sides=4))
    parts += yantra_cloth(coll, m, name + '_yantra', x, y - .07, z0 + height * .66, .62, .62, rng, kind='circle')
    return parts


def yantra_cloth(coll, m, name, x, y, z, w, h, rng, facing=-1, kind='circle'):
    """An old cotton yantra nailed up: the hand-inked drawing (tools/drawings/ep2.mjs),
    sagging between its nails, the hem frayed and uneven. (Advisor review.)"""
    nx, nz = 10, 10
    verts, faces, uvs = [], [], []
    for j in range(nz + 1):
        for i in range(nx + 1):
            u, t = i / nx, j / nz
            sag = .025 * math.sin(u * math.pi) * t + .008 * math.sin(u * 9 + t * 6)
            fray = rng.uniform(-.035, 0) if j == nz else 0
            verts.append((x - w / 2 + w * u, y + facing * (.006 + sag), z - h * t + fray))
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
            for k in (a, a + 1, a + nx + 2, a + nx + 1):
                i2, j2 = k % (nx + 1), k // (nx + 1)
                # The pagoda's world root mirrors X for Babylon: flip U so the script reads true.
                uvs.append((1 - i2 / nx, 1 - j2 / nz))
    parts = [mesh_object(name, coll, verts, faces, m['yantra_' + kind], uvs=uvs, smooth=True)]
    for sx in (-1, 1):
        parts.append(sphere(name + '_nail', coll, (x + sx * (w / 2 - .03), y + facing * .012, z - .03), (.012, .008, .012), m['iron']))
    return parts


def verse_board(coll, m, name, x, y, z, rng):
    """The bell verse: a yellowed sheet pinned to a black lacquered board on two
    posts, its corners curled, the ink run with damp."""
    parts = []
    c = Craft()
    c.block(m['lacquer'], x, y, z, 1.2, .05, .8)
    c.block(m['carved'], x, y, z + .8, 1.32, .08, .07)
    c.block(m['carved'], x, y, z - .05, 1.28, .07, .05)
    parts += c.build(name + '_board', coll)
    nx, nz = 6, 5
    verts, faces = [], []
    for j in range(nz + 1):
        for i in range(nx + 1):
            u, t = i / nx, j / nz
            curl = .03 * (max(0, abs(u - .5) * 2 - .7) + max(0, abs(t - .5) * 2 - .7)) * 3
            verts.append((x - .42 + .84 * u, y - .03 - curl, z + .7 - .58 * t))
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    parts.append(mesh_object(name + '_sheet', coll, verts, faces, m['paper'], smooth=True))
    for row in range(7):
        zz = z + .62 - row * .07
        px = x - .34
        while px < x + .32:
            length = rng.uniform(.04, .12)
            if rng.random() > .15:
                parts.append(tube(name + '_ink', coll, [(px, y - .034, zz + .003 * math.sin(px * 70)), (px + length, y - .034, zz)], .0028, m['void'], sides=3))
            px += length + .02
    for sx in (-1, 1):
        parts.append(tube(name + '_post', coll, [(x + sx * .64, y + .04, 0), (x + sx * .64, y + .04, z + .9)], .05, m['teak'], sides=8))
    for k in range(4):
        parts.append(sphere(name + '_nail', coll, (x + (-.4 if k % 2 else .4), y - .035, z + (.1 if k < 2 else .68)), (.012, .006, .012), m['iron']))
    return parts


def bell_pavilion(coll, m, name, x0, x1, y, bells, rng):
    """A little timber bell frame on stone footings with a tiled roof; the three bells
    hang on ropes beside a wooden striker. Webs where the posts meet the beam."""
    from pagoda_architecture import temple_roof
    parts = []
    c = Craft()
    for x in (x0, x1):
        c.block(m['mould_grey'], x, y, 0, .42, .42, .22)
    parts += c.build(name + '_footings', coll)
    for x in (x0, x1):
        parts.append(lathe(name + '_post', coll, [(.11, 0), (.1, .1), (.09, 2.5), (.11, 2.6), (.13, 2.7)], x, y, .22, m['teak'], segments=12))
    c = Craft()
    c.block(m['carved'], (x0 + x1) / 2, y, 2.78, x1 - x0 + .5, .16, .18)
    for x in (x0, x1):
        for s in (-1, 1):
            parts.append(tube(name + '_brace', coll, [(x, y, 2.2), (x + s * .45, y, 2.78)], .04, m['teak'], sides=6))
    parts += c.build(name + '_beam', coll)
    before = set(coll.objects)
    temple_roof(coll, m, name, 0, 0, 1.5, x1 - x0 + 1.0, 0, .62)
    roof = [o for o in coll.objects if o not in before]
    cx = (x0 + x1) / 2
    for o in roof:
        if o.type != 'MESH':
            continue
        for v in o.data.vertices:
            px, py = v.co.x, v.co.y
            # A true quarter turn (not a mirror), so faces keep their outward winding.
            v.co.x, v.co.y, v.co.z = cx - py, y + px, v.co.z + 2.96
    parts += roof
    for bx in bells:
        parts.append(tube(name + '_rope', coll, [(bx, y, 2.78), (bx, y, 2.3)], .014, m['rope'], sides=5))
    sx = x0 + .2
    parts.append(tube(name + '_striker_rope', coll, [(sx, y + .2, 2.78), (sx, y + .2, 1.45)], .01, m['rope'], sides=4))
    parts.append(tube(name + '_striker', coll, [(sx, y + .2 - .25, 1.4), (sx, y + .2 + .25, 1.4)], .05, m['teak'], sides=8))
    from house_detail import corner_web
    corner_web(name + '_web_0', coll, (x0 + .1, y, 2.7), (1, 0, 0), (0, 0, -1), .45)
    corner_web(name + '_web_1', coll, (x1 - .1, y, 2.7), (-1, 0, 0), (0, 0, -1), .45)
    return parts


# ------------------------------------------------------------------ Sophal's kuti


def mosquito_net(coll, m, name, x0, x1, y0, y1, z0, z1, rng):
    """A mosquito net hung over the sleeping mat from four strings: sagging, grey with
    age, its hem pooled on the floor. In the dark it is a pale shape that might be anyone."""
    nx, ny, nz = 10, 6, 8
    verts, faces = [], []
    ring = []
    for i in range(nx):
        ring.append((x0 + (x1 - x0) * i / nx, y0))
    for j in range(ny):
        ring.append((x1, y0 + (y1 - y0) * j / ny))
    for i in range(nx):
        ring.append((x1 - (x1 - x0) * i / nx, y1))
    for j in range(ny):
        ring.append((x0, y1 - (y1 - y0) * j / ny))
    n = len(ring)
    for k in range(nz + 1):
        t = k / nz
        for i, (px, py) in enumerate(ring):
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            belly = .06 * math.sin(t * math.pi) + .02 * math.sin(i * 1.7 + t * 4)
            dx, dy = px - cx, py - cy
            d = math.hypot(dx, dy) or 1
            z = z1 - (z1 - z0) * t - (.08 * math.sin(i / n * math.tau * 4) ** 2 if k == 0 else 0)
            verts.append((px + dx / d * belly, py + dy / d * belly, z))
    for k in range(nz):
        for i in range(n):
            a, b = k * n + i, k * n + (i + 1) % n
            faces.append((a, b, b + n, a + n))
    top = len(verts)
    verts.append(((x0 + x1) / 2, (y0 + y1) / 2, z1 + .03))
    for i in range(n):
        faces.append((top, (i + 1) % n, i))
    net = mesh_object(name, coll, verts, faces, m['net'], smooth=True)
    strings = [tube(name + '_string', coll, [(px, py, z1), (px, py, z1 + .9)], .003, m['thread'], sides=3)
               for px, py in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
    return [net] + strings


def kuti_furnishings(coll, m, x, y, floor, rng):
    """The monk's room as he lives in it: altar shelf with a small image, sleeping mat
    under a mosquito net, robes on a pole, alms bowl, water jar, manuscripts, sandals,
    a yantra cloth, webs in the rafters. Kept clear of the walk from door to table."""
    from house_detail import corner_web
    from khmer import place
    from kit import cloth
    objs = []
    f = floor
    # Altar shelf against the back wall, behind and above the seated monk.
    c = Craft()
    c.block(m['lacquer'], x, y + 3.2, f + .85, 1.4, .36, .05)
    for sx in (-.6, .6):
        c.block(m['lacquer'], x + sx, y + 3.2, f, .05, .3, .85)
    c.block(m['red_cloth'], x, y + 3.37, f + .9, 1.3, .02, .9)
    objs += c.build('kuti_altar_shelf', coll)
    for o in seated_image_small(coll, m, 'kuti_altar_image', x, y + 3.25, f + .9):
        objs.append(o)
    for sx in (-.45, .45):
        objs += candles_tall(coll, m, f'kuti_altar_candle_{sx}', x + sx, y + 3.2, f + .9)
    objs.append(lathe('kuti_altar_vase', coll, [(.04, 0), (.06, .06), (.04, .14), (.05, .16)], x - .28, y + 3.25, f + .9, m['clay'], segments=10))
    for k in range(5):
        objs.append(tube('kuti_dried_flower', coll, [(x - .28, y + 3.25, f + 1.05), (x - .28 + rng.normal(0, .05), y + 3.25 + rng.normal(0, .03), f + 1.25 + rng.uniform(0, .08))],
                         .003, m['garland_dead'], sides=3))
    objs += incense_pot_small(coll, m, 'kuti_altar_incense', x + .25, y + 3.22, f + .9, rng)
    # Sleeping mat, pillow and folded blanket under the mosquito net, west side.
    sx, sy = x - 2.55, y + 1.5
    c = Craft()
    c.block(m['bamboo_wall'], sx, sy, f, .8, 1.9, .015)
    c.block(m['pillow'], sx, sy + .78, f + .015, .5, .2, .12)
    c.block(m['white_cloth'], sx, sy - .55, f + .015, .62, .45, .06)
    objs += c.build('kuti_sleeping_mat', coll)
    objs += mosquito_net(coll, m, 'kuti_mosquito_net', sx - .5, sx + .5, sy - 1.05, sy + 1.05, f + .02, f + 1.75, rng)
    # Robes drying on a bamboo pole along the east wall.
    px = x + 3.2
    objs.append(tube('kuti_robe_pole', coll, [(px, y + .3, f + 1.85), (px, y + 2.6, f + 1.85)], .025, m['bamboo'], sides=6))
    objs.append(cloth('kuti_hung_robe', coll, y + .5, y + 1.6, f + .55, f + 1.84, px, m['saffron'], folds=5, depth=.035, segments=(20, 10), axis='y'))
    objs.append(cloth('kuti_hung_bathing_cloth', coll, y + 1.75, y + 2.4, f + 1.0, f + 1.84, px, m['white_cloth'], folds=3, depth=.03, segments=(12, 8), axis='y'))
    # Alms bowl in its cover on a stand, beside the monk.
    bx, by = x - 1.1, y + 1.0
    objs.append(lathe('kuti_alms_stand', coll, [(.12, 0), (.1, .05), (.06, .25), (.12, .28)], bx, by, f, m['lacquer'], segments=14))
    objs.append(lathe('kuti_alms_bowl', coll, [(0, 0), (.08, 0), (.15, .06), (.16, .14), (.13, .2), (.11, .22)], bx, by, f + .28, m['lacquer'], segments=20))
    objs.append(lathe('kuti_alms_lid', coll, [(.12, 0), (.13, .02), (.08, .07), (.02, .09), (0, .1)], bx, by, f + .5, m['bronze'], segments=16))
    # A big water jar with a lid and coconut-shell ladle by the door.
    jx, jy = x + 2.9, y - 2.7
    objs.append(lathe('kuti_water_jar', coll, [(.16, 0), (.3, .15), (.34, .4), (.28, .62), (.18, .7), (.2, .74)], jx, jy, f, m['clay'], segments=24))
    objs.append(lathe('kuti_jar_lid', coll, [(.22, 0), (.22, .02), (.1, .05), (0, .06)], jx, jy, f + .74, m['teak'], segments=16))
    objs.append(lathe('kuti_ladle', coll, [(0, 0), (.06, .01), (.07, .05)], jx + .1, jy, f + .8, m['bark'], segments=10))
    # Manuscripts on a wall shelf, a yantra cloth above, sandals left at the door.
    c = Craft()
    c.block(m['teak'], x + 3.25, y - .9, f + 1.1, .3, 1.4, .04)
    for k in range(6):
        c.block(m['paper'], x + 3.25, y - 1.45 + k * .22, f + 1.14, .25, .18, .07 + .02 * (k % 2))
        c.block(m['lacquer'], x + 3.25, y - 1.45 + k * .22, f + 1.21 + .02 * (k % 2), .27, .19, .012)
    objs += c.build('kuti_manuscript_shelf', coll)
    objs += yantra_cloth(coll, m, 'kuti_yantra', x, y + 3.34, f + 2.3, .6, .6, rng, facing=-1, kind='square')
    c = Craft()
    for k, (ox, yaw) in enumerate(((-.12, .1), (.12, -.15))):
        c.block(m['bark'], x - .9 + ox, y - 3.25, f, .1, .26, .02)
    objs += c.build('kuti_sandals', coll)
    for k, corner in enumerate(((x - 3.3, y + 3.3, f + 2.9), (x + 3.3, y + 3.3, f + 2.9), (x + 3.3, y - 3.3, f + 2.9))):
        corner_web(f'kuti_web_{k}', coll, corner, (1 if corner[0] < x else -1, 0, 0), (0, -1 if corner[1] > y else 1, -.6), .55)
    return objs


def seated_image_small(coll, m, name, x, y, z):
    from pagoda_ruin import seated_image
    objs = seated_image(coll, m, name, x, y, 0, .3, seed=77)
    for o in objs:
        o.location.z = z + .13 * .3
        o.data.materials[0] = m['gold_leaf']
    return objs


def candles_tall(coll, m, name, x, y, z):
    return [lathe(name, coll, [(.03, 0), (.035, .02), (.012, .03), (.012, .22), (.016, .23), (0, .225)], x, y, z, m['wax'], segments=10),
            lathe(name + '_holder', coll, [(.05, 0), (.06, .02), (.02, .03), (.03, .04)], x, y, z, m['bronze'], segments=12)]


def incense_pot_small(coll, m, name, x, y, z, rng):
    from pagoda_ruin import incense_pot
    return incense_pot(coll, m, name, x, y, z, rng)


def supplies_contents(coll, m, x, y, z, rng):
    """Sophal's supplies: a coil of white cotton thread on a reel, two small oil
    bottles and a matchbox, on a lacquered tray."""
    parts = [lathe('supplies_tray', coll, [(0, 0), (.24, 0), (.26, .03), (.24, .04), (0, .03)], x, y, z, m['lacquer'], segments=24)]
    parts.append(lathe('thread_reel', coll, [(.04, 0), (.06, 0), (.06, .01), (.035, .015), (.035, .065), (.06, .07), (.06, .08), (.04, .08)], x - .1, y, z + .03, m['teak'], segments=14))
    coil = [(x - .1 + .048 * math.cos(t), y + .048 * math.sin(t), z + .045 + t * .0012) for t in np.linspace(0, 30 * math.pi, 240)]
    parts.append(tube('white_cotton_thread', coll, coil, .004, m['thread'], sides=3))
    for k, bx in enumerate((.06, .14)):
        parts.append(lathe(f'oil_bottle_{k}', coll, [(0, 0), (.03, 0), (.032, .08), (.012, .1), (.012, .13), (0, .13)], x + bx, y + .05, z + .03, m['glass'], segments=10))
    c = Craft()
    c.block(m['paper'], x + .1, y - .1, z + .03, .08, .05, .02)
    c.block(m['red_cloth'], x + .1, y - .1, z + .05, .081, .051, .002)
    parts += c.build('matchbox', coll)
    return parts


def lore_contents(coll, m, x, y, z, rng):
    """The monk's record: loose yellowed sheets, the top one written over, an ink
    pot and a bamboo pen."""
    parts = []
    c = Craft()
    for k in range(6):
        c.block(m['paper'], x + rng.normal(0, .01), y + rng.normal(0, .01), z + k * .003, .3, .4, .003)
    parts += c.build('lore_monk_sheets', coll)
    for row in range(9):
        px, zz = x - .12, y + .16 - row * .035
        while px < x + .12:
            length = rng.uniform(.03, .08)
            parts.append(tube('lore_monk_ink', coll, [(px, zz, z + .02), (px + length, zz + .002, z + .02)], .0018, m['void'], sides=3))
            px += length + .015
    parts.append(lathe('lore_monk_inkpot', coll, [(0, 0), (.03, 0), (.035, .03), (.015, .045), (.015, .05)], x + .24, y + .1, z, m['glass'], segments=10))
    parts.append(tube('lore_monk_pen', coll, [(x + .19, y - .1, z + .02), (x + .27, y + .08, z + .03)], .004, m['bamboo'], sides=4))
    return parts
