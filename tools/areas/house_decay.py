"""The house after three days of rain and a death: weathering and neglect.

Water streaks under the eaves and windows, mildew low on the boards, mud splashed
up the stilts and termite tubes climbing two of them, kitchen soot over the
windows, moss and lichen on the tiles, slipped and broken tiles, white mourning
rags on the stairs, a paper wasp nest under an eave, fish traps and baskets stored
under the house, and more webs. Additive only: nothing here collides, moves or replaces gameplay geometry.

Shared by the full village builder and rebuild-house-decay.py. Blender metres, Z up.
Original procedural stain atlas (T_ep1_house_decay_BC); no photographs are used.
"""
import math
import os

import bpy
import numpy as np
from mathutils import Vector

from kit import TEXTURES, image_material, mesh_object, tube
from khmer import join
from house_detail import corner_web, detail_material

FLOOR, ZW = 2.5, 5.1
X0, X1, Y0, Y1 = -6.0, 6.0, 10.0, 22.0
FRONT = 11.5 - 0.06
# The roof (house() in ep1_area_village.py): 42° slopes from the eaves to the ridge.
PITCH = math.radians(42)
RIDGE_Y = (Y0 + Y1) / 2
EAVE_Z = ZW + 0.05 + 0.12 - 0.9 * math.tan(PITCH)
RIDGE_Z = ZW + 0.05 + 0.12 + (RIDGE_Y - Y0) * math.tan(PITCH)
EAVE_S, EAVE_N = Y0 - 0.9, Y1 + 0.9
ROOF_X = (X0 - 0.9, X1 + 0.9)

# Atlas cells (2 × 2): drip streaks, mildew, splashed mud, soot.
STREAK, MILDEW, MUD, SOOT = range(4)


def stain_atlas():
    """Soft decals in one RGBA atlas; alpha carries the stain, colour its tone."""
    path = os.path.join(TEXTURES, 'T_ep1_house_decay_BC.png')
    rng = np.random.default_rng(6242101)
    size, half = 1024, 512
    yy, xx = np.mgrid[0:half, 0:half].astype(float)
    u, v = xx / (half - 1), yy / (half - 1)  # v = 0 at the bottom (Blender pixel rows)
    fine = rng.normal(0, 1, (half, half))
    blur = sum(np.roll(np.roll(fine, i, 0), j, 1) for i in range(-2, 3) for j in range(-2, 3)) / 25
    cells = []
    # Streaks: wet runs from the top edge, uneven lengths and widths, darker at the source.
    a = np.zeros((half, half))
    for _ in range(26):
        c, w = rng.uniform(.06, .94), rng.uniform(.006, .026)
        length = rng.uniform(.25, .98)
        run = np.clip((v - (1 - length)) / length, 0, 1) ** .7
        wobble = .01 * np.sin(v * rng.uniform(9, 20) + rng.uniform(0, 6))
        a = np.maximum(a, np.exp(-((u - c - wobble) / w) ** 2) * run * rng.uniform(.45, .9))
    a = np.maximum(a, np.clip((v - .93) / .07, 0, 1) * .5 * (1 + blur))  # a ragged wet line under the drip
    cells.append((a, (.075, .058, .04)))
    # Mildew: blotchy dark green-black colonies with speckled edges.
    d = np.hypot(u - .5, (v - .5) * 1.3)
    blob = np.clip(1 - d / .48, 0, 1) * (.65 + 2.2 * blur)
    specks = (rng.random((half, half)) < .05) * np.clip(1 - d / .55, 0, 1) * .8
    cells.append((np.clip(blob + specks, 0, 1), (.035, .045, .026)))
    # Mud: heavy at the ground, flicked up in drops.
    band = np.clip(1 - v / .55, 0, 1) ** 1.4
    drops = np.zeros((half, half))
    for _ in range(140):
        cx, cy, r = rng.uniform(0, 1), rng.uniform(0, .8) ** 1.6, rng.uniform(.004, .018)
        drops = np.maximum(drops, np.clip(1 - np.hypot(u - cx, v - cy) / r, 0, 1) * 1.2)
    cells.append((np.clip(band * (.8 + 1.5 * blur) + drops, 0, 1), (.13, .085, .05)))
    # Soot: a plume rising from a window head, broad and soft.
    plume = np.exp(-((u - .5) / (.16 + .3 * v)) ** 2) * np.clip(1 - v, 0, 1) ** .6
    cells.append((np.clip(plume * (.9 + 1.2 * blur), 0, 1), (.018, .015, .013)))
    # Rendered as a cutout (alpha 0.5): noise breaks every edge into wet, flaking runs.
    grain = rng.normal(0, 1, (half, half))
    mottle = .55 * blur + .18 * grain
    pixels = np.zeros((size, size, 4))
    for k, (alpha, colour) in enumerate(cells):
        alpha = np.where(alpha > .04, alpha * 1.05 + mottle * (.45 if k != SOOT else .7) - .05, 0)
        x, y = (k % 2) * half, (1 - k // 2) * half
        tone = np.clip(1 + .25 * blur[..., None], .7, 1.3) * np.array(colour)
        pixels[y:y + half, x:x + half, :3] = tone
        pixels[y:y + half, x:x + half, 3] = np.clip(alpha, 0, 1)
    from forest_detail import save_map
    save_map('T_ep1_house_decay_BC', pixels)
    return path


def decay_materials():
    # A cutout, as the leaves and webs are: the renderer's blended pass loses soft decals.
    stains = (bpy.data.materials.get('M_house_detail_weather_stains')
              or image_material('M_house_detail_weather_stains', stain_atlas(), rough=.42, cutout=True))
    m = {
        'stains': stains,
        'moss': detail_material('M_house_detail_moss', (.04, .065, .022), .95),
        'lichen': detail_material('M_house_detail_lichen', (.19, .2, .15), .95),
        'paper': detail_material('M_house_detail_wasp_paper', (.15, .135, .11), .98),
        'termite': detail_material('M_house_detail_termite_mud', (.2, .13, .08), .97),
        'rag': detail_material('M_house_detail_mourning_rag', (.4, .38, .33), .96),
        'void': detail_material('M_house_detail_roof_void', (.008, .007, .006), 1),
        'cane': detail_material('M_house_detail_old_cane', (.24, .18, .1), .85),
    }
    for key in ('rag', 'cane'):
        m[key].use_backface_culling = False
    return m


class Decals:
    """Quads offset just off a surface, each showing one atlas cell, merged at the end."""

    def __init__(self):
        self.verts, self.faces, self.uvs = [], [], []

    def add(self, cell, bottom, right, up, width, height, normal, offset=.007, flip=False):
        b, r, u, n = Vector(bottom), Vector(right).normalized(), Vector(up).normalized(), Vector(normal)
        base = b + n * offset
        corners = [base - r * width / 2, base + r * width / 2,
                   base + r * width / 2 + u * height, base - r * width / 2 + u * height]
        u0, v0 = (cell % 2) * .5, (1 - cell // 2) * .5
        uv = [(u0, v0), (u0 + .5, v0), (u0 + .5, v0 + .5), (u0, v0 + .5)]
        if flip:
            uv = [uv[1], uv[0], uv[3], uv[2]]
        i = len(self.verts)
        self.verts += [tuple(c) for c in corners]
        face = (i, i + 1, i + 2, i + 3)
        # Wind towards the surface normal so the decal faces outwards.
        if (corners[1] - corners[0]).cross(corners[3] - corners[0]).dot(n) < 0:
            face, uv = tuple(reversed(face)), list(reversed(uv))
        self.faces.append(face)
        self.uvs += uv

    def finish(self, name, coll, mat):
        return mesh_object(name, coll, self.verts, self.faces, mat, uvs=self.uvs)


def roof_point(x, t, side):
    """A point on the tiles' top surface, t from the eave (0) to the ridge (1)."""
    ye = EAVE_S if side < 0 else EAVE_N
    return Vector((x, ye + (RIDGE_Y - ye) * t, EAVE_Z + (RIDGE_Z - EAVE_Z) * t))


def roof_normal(side):
    return Vector((0, side * math.sin(PITCH), math.cos(PITCH)))


def lump(name, coll, mat, centre, radius, normal, rng, flat=.35, seg=6):
    """An irregular low cushion (moss, lichen, a wasp nest's lobe) on a surface."""
    n = Vector(normal).normalized()
    a = n.cross(Vector((0, 0, 1)) if abs(n.z) < .9 else Vector((1, 0, 0))).normalized()
    b = n.cross(a)
    verts, faces = [], []
    rings = 3
    for j in range(rings + 1):
        phi = (j / rings) * math.pi / 2
        for i in range(seg):
            th = i / seg * math.tau
            k = radius * (.75 + .5 * rng.random())
            p = (Vector(centre) + (a * math.cos(th) + b * math.sin(th)) * k * math.cos(phi)
                 + n * radius * flat * math.sin(phi))
            verts.append(tuple(p))
    for j in range(rings):
        for i in range(seg):
            p, q = j * seg + i, j * seg + (i + 1) % seg
            faces.append((p, q, q + seg, p + seg))
    return mesh_object(name, coll, verts, faces, mat, smooth=True)


def house_decay(coll, m):
    """Adds the weathering; returns the created objects."""
    rng = np.random.default_rng(6242102)
    d = decay_materials()
    before = set(coll.objects)
    walls = Decals()
    # Faces: (fixed coordinate, along-x, outward normal, the openings' centres and widths).
    sides = [
        ('front', FRONT, True, (0, -1, 0), [(-4.2, .8), (4.3, .8)], [(0, 1.2)]),
        ('back', Y1, True, (0, 1, 0), [(-4.4, .8), (-.6, .8), (4.4, .8)], [(2.35, 1.0)]),
        ('west', X0, False, (-1, 0, 0), [(13.0, .8), (16.4, .8), (20.4, .8)], []),
        ('east', X1, False, (1, 0, 0), [(14.4, .8), (17.1, .8), (20.0, .8)], []),
    ]
    for label, fixed, along_x, normal, windows, doors in sides:
        lo, hi = (X0, X1) if along_x else (11.5 if label in ('west', 'east') else Y0, Y1)
        right = (1, 0, 0) if along_x else (0, 1, 0)

        def at(a, z):
            return (a, fixed, z) if along_x else (fixed, a, z)
        # Under each sill the rain runs off and stains the boards to the floor line.
        for c, w in windows:
            walls.add(STREAK, at(c, FLOOR + .02), right, (0, 0, 1), w * 1.35, .8 - .02, normal, flip=rng.random() < .5)
        # Under the eaves: runs from the top of the wall, wherever no opening is.
        a = lo + .4
        while a < hi - .4:
            width = rng.uniform(.7, 1.4)
            if all(abs(a - c) > (w + width) / 2 for c, w in windows + doors):
                walls.add(STREAK, at(a, ZW - rng.uniform(.95, 1.5)), right, (0, 0, 1), width,
                          ZW - .02 - (ZW - rng.uniform(.95, 1.5)), normal, flip=rng.random() < .5)
            a += rng.uniform(.9, 1.7)
        # Mildew low on the boards where the splash never dries.
        for _ in range(3):
            a = rng.uniform(lo + .5, hi - .5)
            if all(abs(a - c) > .7 for c, _ in doors):
                walls.add(MILDEW, at(a, FLOOR + rng.uniform(.02, .2)), right, (0, 0, 1), rng.uniform(.5, 1.1),
                          rng.uniform(.35, .7), normal)
    # Kitchen smoke has blackened the boards over both kitchen windows.
    walls.add(SOOT, (-4.2, FRONT, FLOOR + 1.72), (1, 0, 0), (0, 0, 1), 1.2, ZW - FLOOR - 1.72, (0, -1, 0), offset=.009)
    walls.add(SOOT, (X0, 13.0, FLOOR + 1.72), (0, 1, 0), (0, 0, 1), 1.2, ZW - FLOOR - 1.72, (-1, 0, 0), offset=.009)
    walls.finish('house_decay_wall_stains', coll, d['stains'])

    # Mud splashed up every stilt, as a thin sleeve over the post.
    sleeves = []
    for x in (-6.0, -3.0, 0.0, 3.0, 6.0):
        for y in (10.0, 14.0, 18.0, 22.0):
            verts, faces, uvs = [], [], []
            seg = 16
            top = rng.uniform(.55, .85)
            for j, z in enumerate((.1, top)):
                for i in range(seg + 1):
                    th = i / seg * math.tau
                    verts.append((x + .159 * math.cos(th), y + .159 * math.sin(th), z))
            for i in range(seg):
                faces.append((i, i + 1, seg + 2 + i, seg + 1 + i))
                u0, u1 = .5 * i / seg, .5 * (i + 1) / seg  # the mud cell, once round the post
                uvs += [(u0, 0), (u1, 0), (u1, .5), (u0, .5)]
            sleeves.append(mesh_object('house_decay_post_mud', coll, verts, faces, d['stains'], uvs=uvs))
    join(sleeves, 'house_decay_post_mud')

    # Termite tubes climbing two stilts from the ground.
    for k, (x, y) in enumerate(((-6.0, Y1), (3.0, 10.0))):
        for j in range(3):
            th = rng.uniform(0, math.tau)
            pts = []
            for i in range(14):
                z = .05 + i * .16
                th += rng.normal(0, .08)
                pts.append((x + .165 * math.cos(th), y + .165 * math.sin(th), z))
            tube(f'house_decay_termite_{k}_{j}', coll, pts, .012, d['termite'], sides=5, radius_end=.006)

    # Moss on the lower tiles and along the shaded north slope, lichen spots higher up.
    tufts = []
    for side, count in ((-1, 70), (1, 120)):
        n = roof_normal(side)
        for i in range(count):
            t = rng.uniform(0, .35) ** 1.3 if rng.random() < .75 else rng.uniform(.3, .97)
            p = roof_point(rng.uniform(*ROOF_X), t, side) + n * .02
            moss = t < .4 or rng.random() < .3
            tufts.append(lump('house_decay_moss', coll, d['moss'] if moss else d['lichen'], p,
                              rng.uniform(.06, .2) if moss else rng.uniform(.03, .07), n, rng,
                              flat=.4 if moss else .12))
    # Moss on the stone footings, on their shaded faces.
    for x in (-6.0, -3.0, 0.0, 3.0, 6.0):
        for y in (10.0, 14.0, 18.0, 22.0):
            if rng.random() < .6:
                tufts.append(lump('house_decay_moss', coll, d['moss'], (x + rng.uniform(-.2, .2), y + .24, .05),
                                  rng.uniform(.06, .1), (0, 1, .2), rng, flat=.5))
    join(tufts, 'house_decay_moss')

    # Gaps where tiles have slipped: the dark of the attic between the battens.
    holes = []
    for k, (x, t, side) in enumerate(((-3.6, .42, -1), (4.4, .3, 1), (1.2, .62, 1), (-5.1, .2, 1))):
        n = roof_normal(side)
        up = (roof_point(x, t + .05, side) - roof_point(x, t, side)).normalized()
        centre = roof_point(x, t, side) + n * .012
        w, h = rng.uniform(.35, .5), rng.uniform(.3, .45)
        corners = [centre + Vector((-w / 2, 0, 0)) - up * h / 2, centre + Vector((w / 2, 0, 0)) - up * h / 2,
                   centre + Vector((w / 2, 0, 0)) + up * h / 2, centre + Vector((-w / 2, 0, 0)) + up * h / 2]
        face = (0, 1, 2, 3) if (corners[1] - corners[0]).cross(corners[3] - corners[0]).dot(n) > 0 else (3, 2, 1, 0)
        holes.append(mesh_object(f'house_decay_roof_gap_{k}', coll, [tuple(c) for c in corners], [face], d['void']))
        for j in (-.3, .3):
            a = centre + up * h * j + n * .01
            holes.append(tube(f'house_decay_batten_{k}', coll, [a - Vector((w / 2 + .05, 0, 0)), a + Vector((w / 2 + .05, 0, 0))],
                              .018, m['post'], sides=4))
        # The slipped tiles themselves, lodged lower down the slope.
        for j in range(3):
            p = roof_point(x + rng.uniform(-.4, .4), max(.03, t - rng.uniform(.08, .2)), side) + n * .05
            holes.append(tile(f'house_decay_slipped_tile_{k}_{j}', coll, m['tiles'], p, n, up, rng))
    join(holes, 'house_decay_roof_damage')
    # Broken tiles fallen onto the ground below the eaves.
    shards = []
    for k in range(16):
        y = (EAVE_S - rng.uniform(.1, .7)) if k % 2 else (EAVE_N + rng.uniform(.1, .7))
        p = Vector((rng.uniform(-6.5, 6.5), y, .03))
        tilt = Vector((rng.uniform(-.4, .4), rng.uniform(-.4, .4), 1)).normalized()
        shards.append(tile('house_decay_tile_shard', coll, m['tiles'], p, tilt, Vector((1, 0, 0)), rng, broken=True))
    join(shards, 'house_decay_tile_shards')

    # White mourning rags knotted to the stair rail and the veranda posts, soaked.
    rags = []
    for k, (x, y, z) in enumerate(((6.02, 9.98, FLOOR + .9), (3.0, 9.97, FLOOR + .94), (-3.0, 9.97, FLOOR + .94),
                                   (7.6, 10.12, 1.45))):
        rags.append(tube(f'house_decay_rag_knot_{k}', coll, [(x - .03, y - .01, z), (x + .03, y - .03, z - .01)],
                         .018, d['rag'], sides=5))
        drop = rng.uniform(.35, .6)
        verts, faces = [], []
        for j in range(7):
            s = j / 6
            sway = .04 * math.sin(s * 3 + k)
            w = .07 * (1 - .5 * s)
            verts += [(x - w + sway, y - .03 - .02 * s, z - drop * s), (x + w + sway, y - .03 - .01 * s, z - drop * s - .02 * (j % 2))]
            if j:
                faces.append((2 * j - 2, 2 * j - 1, 2 * j + 1, 2 * j))
        rags.append(mesh_object(f'house_decay_rag_{k}', coll, verts, faces, d['rag'], smooth=True))
    join(rags, 'house_decay_mourning_rags')

    # A paper wasp nest under the north-east eave, and an older broken one.
    nest = []
    for k, (c, r) in enumerate((((5.6, Y1 + .55, 4.62), .16), ((-5.4, 9.45, 4.6), .09))):
        for j in range(4):
            p = Vector(c) + Vector((0, 0, -j * r * .55))
            nest.append(lump(f'house_decay_wasp_nest_{k}', coll, d['paper'], p, r * (1 - .12 * j), (0, 0, -1), rng, flat=.9, seg=9))
        nest.append(tube(f'house_decay_wasp_stalk_{k}', coll, [tuple(Vector(c) + Vector((0, 0, .1))), c], .012, d['paper'], sides=4))
    join(nest, 'house_decay_wasp_nests')

    # Stored under the floor, hung from the girders above head height: fish traps and baskets.
    stored = []
    for k, (x, y) in enumerate(((-4.6, 18.0), (-1.4, 18.0), (4.7, 10.0))):
        top = Vector((x, y + (.16 if y > 14 else -.16), FLOOR - .42))
        stored.append(tube(f'house_decay_hook_cord_{k}', coll, [tuple(top), tuple(top - Vector((0, 0, .2)))], .005, m['rope'], sides=4))
        stored += fish_trap(f'house_decay_fish_trap_{k}', coll, d['cane'], top - Vector((0, 0, .2)), rng)
    join(stored, 'house_decay_stored_traps')

    # More webs: the veranda's eave corners and under the stair head.
    for k, (corner, right, down) in enumerate((((-5.95, 10.05, ZW - .05), (.6, 0, 0), (0, .25, -.55)),
                                               ((5.95, 10.05, ZW - .05), (-.6, 0, 0), (0, .25, -.55)),
                                               ((6.9, 9.15, EAVE_Z - .12), (-.7, 0, 0), (0, .3, -.4)),
                                               ((-6.9, Y1 + .85, EAVE_Z - .12), (.7, 0, 0), (0, -.3, -.4)),
                                               ((7.5, 10.2, 1.2), (0, .5, 0), (0, 0, -.6)))):
        corner_web(f'house_decay_web_{k}', coll, corner, right, down, .8)
    return set(coll.objects) - before


def tile(name, coll, mat, at, normal, along, rng, broken=False):
    """A curved clay tile (or a broken piece of one) lying on `normal`."""
    n = Vector(normal).normalized()
    a = (Vector(along) - n * Vector(along).dot(n)).normalized()
    b = n.cross(a)
    length = rng.uniform(.12, .2) if broken else .32
    width = rng.uniform(.08, .14) if broken else .2
    span = rng.uniform(.5, .9) if broken else 1
    verts, faces = [], []
    seg = 6
    for j in range(2):
        for i in range(seg + 1):
            th = math.pi * (i / seg * span + (1 - span) / 2)
            p = Vector(at) + a * (j - .5) * length + b * math.cos(th) * width / 2 + n * math.sin(th) * width * .25
            verts.append(tuple(p))
    for i in range(seg):
        faces.append((i, i + 1, seg + 2 + i, seg + 1 + i))
    obj = mesh_object(name, coll, verts, faces, mat, smooth=True)
    obj.data.materials[0].use_backface_culling = obj.data.materials[0].use_backface_culling
    return obj


def fish_trap(name, coll, mat, top, rng):
    """A lop: a slatted bamboo fish trap, narrow at the mouth, hung by its neck."""
    parts = []
    length, radius = rng.uniform(.6, .8), rng.uniform(.14, .19)
    ribs = 14
    for i in range(ribs):
        th = i / ribs * math.tau
        pts = []
        for j in range(7):
            s = j / 6
            r = radius * math.sin(math.pi * (.15 + .75 * s)) * (1 - .25 * s) + .03
            pts.append(tuple(top + Vector((r * math.cos(th), r * math.sin(th), -length * s))))
        parts.append(tube(name, coll, pts, .0045, mat, sides=3))
    for j in (1, 3, 5):
        s = j / 6
        r = radius * math.sin(math.pi * (.15 + .75 * s)) * (1 - .25 * s) + .033
        parts.append(tube(name, coll, [tuple(top + Vector((r * math.cos(t), r * math.sin(t), -length * s)))
                                       for t in np.linspace(0, math.tau, 17)], .006, mat, sides=3))
    return parts
