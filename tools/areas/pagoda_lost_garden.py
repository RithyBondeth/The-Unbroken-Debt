"""The lost garden: five overgrown zones round Episode 2's compound, joined in a loop through
breaches in its walls. Metres, X east, Y north, in the same space as ep2_area_pagoda.py.

    Court of the Forgotten  lanes of neglected stupas with dead ends, west of the compound
    Sunken Tank             a stepped tank with drowned images, north of the Court
    Spirit Grove            old trees and abandoned shrines, north of the compound
    Root Gallery            collapsed roofed walks, north of the sala's clearing
    Bone Terrace            a dead end with an altar, south of the sala's clearing

Rectangles come from `zones` in src/episodes/ep2/data/garden-layout.json, which the game also
reads to switch distant zones off. Every zone's art hangs off an empty named `zone_<id>`;
colliders and flame positions stay outside it, so they keep working while it is switched off.

No story points move, and the ghosts' navigation stays in the garden. Everything here is
built from the project's scans and kit. The drowned images, the skulls on the terrace and all
the ritual dressing are advisor-review items.
"""
import math

import numpy as np

from forest import tropical_tree
from forest_detail import grass_geometry, understory
from khmer import place
from kit import box, collider, empty, lathe, library_material, mesh_object, plain, tube
from pagoda_architecture import temple_roof
from pagoda_forest import giant
from pagoda_kit import piece
from pagoda_props import leaf_litter
from pagoda_rituals import (bier, bound_trunk, boundary_stakes, candle_cluster, drop_protos, funeral_tatter, hanging_doll,
                            long_bone, marigold_garland, place_copy, pyre_remains, red_string_web, rib, skull, skull_stake,
                            skull_variants, sorcery_altar, wrapped_dead)
from pagoda_ruin import fig_roots, guardian, lean, rubble, seated_image, spirit_house, temple_wall
from pagoda_stupa import memorial

WALL_HEIGHT = 5
# Where the breaches open, shared with the compound walls in ep2_area_pagoda.py.
WEST_BREACH_Y = (-23.3, -20.1)  # compound west wall, bay 5: into the Court
NORTH_BREACH_X = (21.8, 24.9)  # compound north wall, bay 16: into the Spirit Grove
SALA_NORTH_X = (37.0, 41.0)  # sala clearing's north side: into the Root Gallery
SALA_SOUTH_X = (37.0, 41.0)  # sala clearing's south side: into the Bone Terrace
COURT_TANK_BAY = 8  # of the wall along Y 21, from X -81
TANK_GROVE_BAY = 3  # of the wall along X -30, from Y 43
GROVE_GALLERY_Y = (58.0, 62.0)


def _rect(zones, name):
    z = next(z for z in zones if z['id'] == name)
    return z['minX'], z['maxX'], z['minY'], z['maxY']


class Zone:
    """Collects what a zone's builders make and hangs its art off one switchable empty."""

    def __init__(self, coll, name):
        self.coll, self.name = coll, name
        self.before = set(coll.objects)

    def close(self):
        import bpy
        root = empty('zone_' + self.name, self.coll, (0, 0, 0))
        bpy.context.view_layer.update()
        for o in self.coll.objects:
            if o in self.before or o is root or o.parent is not None:
                continue
            if o.name.startswith(('col_', 'light_flame_', 'interact_', 'spawn_', 'marker_', 'patrol_')):
                continue
            world = o.matrix_world.copy()
            o.parent = root
            o.matrix_world = world
        return root


def _ground(coll, m, name, x0, x1, y0, y1, surface='dirt', mat='earth'):
    collider(name, coll, x0, x1, y0, y1, -.18, -.01, surface)
    box(name, coll, x0, x1, y0, y1, -.18, -.01, m[mat])


def _block(coll, x0, x1, y0, y1, height=WALL_HEIGHT):
    collider('boundary', coll, x0, x1, y0, y1, -.2, height, 'stone')


def _slab(coll, m, name, x0, x1, y0, y1, z0, z1, mat='stone', solid=False):
    box(name, coll, x0, x1, y0, y1, z0, z1, m[mat], edge=.012)
    if solid:
        collider(name, coll, x0, x1, y0, y1, z0, z1, 'stone')


def _edge_forest(coll, m, rect, rng, base, gaps=()):
    """Old trees along a zone's outer edge, so its boundary reads as jungle and not as a wall.
    `gaps` are (x, y, radius) kept clear for the way through."""
    x0, x1, y0, y1 = rect
    k = 0
    length = 2 * ((x1 - x0) + (y1 - y0))
    for t in np.arange(0, length, 6.5):
        if t < x1 - x0:
            px, py = x0 + t, y0
        elif t < (x1 - x0) + (y1 - y0):
            px, py = x1, y0 + t - (x1 - x0)
        elif t < 2 * (x1 - x0) + (y1 - y0):
            px, py = x1 - (t - (x1 - x0) - (y1 - y0)), y1
        else:
            px, py = x0, y1 - (t - 2 * (x1 - x0) - (y1 - y0))
        px += rng.normal(0, 1)
        py += rng.normal(0, 1)
        k += 1
        if any((px - a) ** 2 + (py - b) ** 2 < r * r for a, b, r in gaps):
            continue
        tropical_tree(coll, m, px, py, rng.uniform(10, 16), base + k, rng, collision=False)


def _growth(coll, m, name, rect, rng, count, clear, grass_size=(.35, .85)):
    """Understory and grass over a zone, kept off `clear(x, y)` ground."""
    x0, x1, y0, y1 = rect
    spots = []
    for _ in range(count):
        x, y = rng.uniform(x0 + .5, x1 - .5), rng.uniform(y0 + .5, y1 - .5)
        if not clear(x, y):
            spots.append((x, y))
    understory(coll, spots, rng, prefix=name)
    grass_geometry(name + '_grasses', coll, [(x, y, .015) for x, y in spots], rng, size=grass_size)


# ------------------------------------------------------------------ Court of the Forgotten


def court(coll, m, rect, lamp):
    """Lanes of stupas nobody visits. The lanes are real, some are blocked by standing walls,
    and two avenues always get you through: east to west from the breach, and north to the tank."""
    x0, x1, y0, y1 = rect
    rng = np.random.default_rng(5101)
    zone = Zone(coll, 'court')
    _ground(coll, m, 'earth_court', x0, x1, y0, y1)
    avenue_y = sum(WEST_BREACH_Y) / 2
    avenue_x = -53.9
    placed = []
    k = 0
    for lane_x in np.arange(-36.5, x0 + 3, -5.5):
        if abs(lane_x - avenue_x) < 3:
            continue
        for row_y in np.arange(y0 + 5.5, y1 - 2, 4.2):
            if abs(row_y - avenue_y) < 3.2 or rng.random() > .56:
                continue
            px, py = lane_x + rng.normal(0, .35), row_y + rng.normal(0, .35)
            k += 1
            objs = memorial(coll, m, px, py, 400 + k, rng.uniform(2.3, 3.4), 'court_' + str(k), rng)
            lean(objs, px, py, rng.normal(0, .05), rng.normal(0, .05))
            collider('court_stupa_' + str(k), coll, px - .7, px + .7, py - .7, py + .7, 0, 3.2, 'stone')
            placed.append((px, py))
            if k % 4 == 0:
                # A fig tree stands only on a snapped stupa; a whole one keeps just the roots.
                crown = rng.uniform(1.4, 2.2)
                fig_roots(coll, m, 'court_fig_' + str(k), px, py, 2.4, lambda z: .6 if z < 1.9 else .45, rng, n=7, spread=.9,
                          crown=crown if 'broken' in objs[0].data.name else 0)
    # Standing walls that end lanes: walk one, and you have to come back.
    for j, (a, b) in enumerate([((-41, -10), (-41, 2)), ((-46.5, 6), (-46.5, 17)), ((-60, -12), (-60, 1)),
                                ((-65.5, 5), (-65.5, 16)), ((-71, -14), (-71, -2))]):
        temple_wall(coll, m, 'court_wall_' + str(j), a, b, rng, 'mould_grey', breaches=(1,))
    for j in range(9):
        px, py = rng.uniform(x0 + 5, x1 - 5), rng.uniform(y0 + 5, y1 - 5)
        if abs(py - avenue_y) < 4 or abs(px - avenue_x) < 4 or any((px - a) ** 2 + (py - b) ** 2 < 6 for a, b in placed):
            continue
        giant(coll, m, px, py, rng.uniform(11, 16), 500 + j, rng, reach=1.8, collision=True)
    red_string_web(coll, m, 'court_web', [(x, y, 2.1) for x, y in placed[:12]], rng, density=1.0)
    lamp('court_lane', -47, avenue_y + 1.6, .02, 1.6)
    _edge_forest(coll, m, rect, rng, 540, gaps=[(x1, avenue_y, 6), (avenue_x, y1, 6)])

    def clear(x, y):
        return (abs(y - avenue_y) < 1.6 or abs(x - avenue_x) < 1.6
                or any((x - a) ** 2 + (y - b) ** 2 < 1.2 for a, b in placed))
    _growth(coll, m, 'court', rect, rng, 500, clear)
    return zone.close()


# ------------------------------------------------------------------ Sunken Tank


def tank(coll, m, rect, lamp):
    """A stepped tank with images standing drowned in it. One flight of steps goes down to a
    landing at the water; the water itself can't be entered."""
    x0, x1, y0, y1 = rect
    rng = np.random.default_rng(5202)
    zone = Zone(coll, 'tank')
    bx0, bx1, by0, by1 = -69.0, -41.0, 32.0, 60.0  # the basin's rim
    for name, g in {'earth_tank_s': (x0, x1, y0, by0), 'earth_tank_n': (x0, x1, by1, y1),
                    'earth_tank_w': (x0, bx0, by0, by1), 'earth_tank_e': (bx1, x1, by0, by1)}.items():
        _ground(coll, m, name, *g)
    collider('tank_floor', coll, bx0, bx1, by0, by1, -2.2, -2.0, 'stone')
    # Courses of stone stepping down to the water, each a little worn.
    water, depth = -1.05, .22
    for i in range(7):
        top = -depth * (i + 1)
        inset = i * .85
        a0, a1, b0, b1 = bx0 + inset, bx1 - inset, by0 + inset, by1 - inset
        w = .9
        mat = 'mould_grey' if i % 2 else 'stone'
        for name, r in {'s': (a0, a1, b0, b0 + w), 'n': (a0, a1, b1 - w, b1), 'w': (a0, a0 + w, b0, b1), 'e': (a1 - w, a1, b0, b1)}.items():
            _slab(coll, m, f'tank_course_{i}_{name}', *r, top - .4, top, mat)
    box('tank_water', coll, bx0 + 4, bx1 - 4, by0 + 4, by1 - 4, -2.0, water, m['water'])
    # The steps down: a real ramp in the collision, under the visible courses.
    sx = -53.9
    half = 1.2
    landing_y = by0 + 5.6
    z_low = water + .12
    verts = [(sx - half, by0 - .05, -.25), (sx + half, by0 - .05, -.25), (sx - half, landing_y, z_low - .3), (sx + half, landing_y, z_low - .3),
             (sx - half, by0 - .05, -.01), (sx + half, by0 - .05, -.01), (sx - half, landing_y, z_low), (sx + half, landing_y, z_low)]
    mesh_object('col_tank_steps', coll, verts, [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)], surface='stone')
    collider('tank_landing', coll, sx - 2.4, sx + 2.4, landing_y - .05, landing_y + 1.6, z_low - .3, z_low, 'stone')
    _slab(coll, m, 'tank_landing', sx - 2.4, sx + 2.4, landing_y - .05, landing_y + 1.6, z_low - .3, z_low, 'mould_grey')
    # The rim stops you falling in everywhere but the steps, and the landing ends at the water.
    rim = .7
    _block(coll, bx0, sx - half, by0 - .1, by0 + .1, rim)
    _block(coll, sx + half, bx1, by0 - .1, by0 + .1, rim)
    _block(coll, bx0, bx1, by1 - .1, by1 + .1, rim)
    _block(coll, bx0 - .1, bx0 + .1, by0, by1, rim)
    _block(coll, bx1 - .1, bx1 + .1, by0, by1, rim)
    _block(coll, sx - half - .1, sx - half + .1, by0, landing_y, 1.6)
    _block(coll, sx + half - .1, sx + half + .1, by0, landing_y, 1.6)
    _block(coll, sx - 2.5, sx + 2.5, landing_y + 1.6, landing_y + 1.8, 1.6)
    # And it can't be stepped off sideways: that way lies walking about under the water.
    _block(coll, sx - 2.5, sx - 2.4, landing_y - .15, landing_y + 1.8, 1.6)
    _block(coll, sx + 2.4, sx + 2.5, landing_y - .15, landing_y + 1.8, 1.6)
    _block(coll, sx - 2.5, sx - half, landing_y - .15, landing_y - .05, 1.6)
    _block(coll, sx + half, sx + 2.5, landing_y - .15, landing_y - .05, 1.6)
    # Drowned images, up to the chest and the neck, all still facing the steps.
    drowned = [(-61, 44, 1.2, False), (-55.5, 46.5, 1.7, False), (-49, 43.5, 1.2, True), (-63, 51, 1.0, True), (-56, 53.5, 1.4, False),
               (-47.5, 51, 1.0, False), (-59, 40.5, .9, True), (-51, 39.5, .9, False)]
    for j, (px, py, scale, headless) in enumerate(drowned):
        for o in seated_image(coll, m, 'tank_image_' + str(j), px, py, math.pi, scale, headless=headless, damage=j % 3 == 0, seed=30 + j):
            o.location.z = water - .45 * scale + rng.normal(0, .04)
            o.rotation_euler.x += rng.normal(0, .03)
            o.rotation_euler.y += rng.normal(0, .03)
    # Headless guardians at the head of the steps, and the walk round the rim.
    guardian(coll, m, 'tank_guardian_w', sx - 4.2, by0 - 1.4, 0, rng, headless=True, seed=31)
    guardian(coll, m, 'tank_guardian_e', sx + 4.2, by0 - 1.4, 0, rng, seed=32)
    for px in (sx - 4.2, sx + 4.2):
        collider('tank_guardian', coll, px - .5, px + .5, by0 - 1.9, by0 - .9, 0, 2.5, 'stone')
    # A row of walls and trees on the far side, the way on to the grove in between.
    for j, (px, py) in enumerate([(-74, 40), (-76, 54), (-72, 66), (-36, 30), (-37, 64), (-45, 66), (-60, 67), (-77, 27), (-35, 44)]):
        giant(coll, m, px, py, rng.uniform(12, 17), 600 + j, rng, reach=1.8, collision=True)
    lamp('tank_steps', sx - 2.1, by0 - .8, .02, 1.6)
    _edge_forest(coll, m, rect, rng, 620, gaps=[(-53.9, y0, 5), (x1, 54.3, 6)])

    def clear(x, y):
        return bx0 - .6 < x < bx1 + .6 and by0 - 1 < y < by1 + .6 or abs(x - sx) < 1.8 and y < by0
    _growth(coll, m, 'tank', rect, rng, 420, clear, grass_size=(.5, 1.1))
    return zone.close()


# ------------------------------------------------------------------ Spirit Grove


def grove(coll, m, rect, lamp):
    """Great old trees, cloth-bound, and the spirit houses people stopped coming to."""
    x0, x1, y0, y1 = rect
    rng = np.random.default_rng(5303)
    zone = Zone(coll, 'grove')
    _ground(coll, m, 'earth_grove', x0, x1, y0, y1)
    # A crooked path joins the three ways in: from the compound, the tank and the gallery.
    path = [(sum(NORTH_BREACH_X) / 2, y0), (20, 52), (6, 58), (-10, 56), (x0, 54.3)]
    branch = [(6, 58), (18, 62), (x1, sum(GROVE_GALLERY_Y) / 2)]

    def on_path(x, y, width=2.4):
        for route in (path, branch):
            for (ax, ay), (bx, by) in zip(route, route[1:]):
                dx, dy = bx - ax, by - ay
                t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
                if (x - ax - dx * t) ** 2 + (y - ay - dy * t) ** 2 < width * width:
                    return True
        return False

    trees = []
    for j in range(46):
        px, py = rng.uniform(x0 + 3, x1 - 3), rng.uniform(y0 + 3, y1 - 3)
        if on_path(px, py, 4.2) or any((px - a) ** 2 + (py - b) ** 2 < 49 for a, b in trees):
            continue
        trees.append((px, py))
        giant(coll, m, px, py, rng.uniform(14, 20), 700 + j, rng, reach=2.1, collision=True, crown=1.1)
    # The oldest are bound with cloth and cord, and something hangs from their branches.
    for j, (px, py) in enumerate(trees[:9]):
        bound_trunk(coll, m, 'grove_trunk_' + str(j), px, py, .6, rng, turns=9)
        for d in range(2):
            a = rng.uniform(0, math.tau)
            hanging_doll(coll, m, f'grove_doll_{j}_{d}', (px + math.cos(a) * 1.6, py + math.sin(a) * 1.6, rng.uniform(2.6, 3.4)), rng, drop=rng.uniform(.4, .9))
    # Abandoned shrines, in clusters at the foot of the old trees. Some have fallen.
    k = 0
    for j, (px, py) in enumerate(trees[:18]):
        for _ in range(int(rng.integers(1, 3))):
            a = rng.uniform(0, math.tau)
            sx, sy = px + math.cos(a) * rng.uniform(2, 3.4), py + math.sin(a) * rng.uniform(2, 3.4)
            if on_path(sx, sy, 2.8) or not (x0 + 1 < sx < x1 - 1 and y0 + 1 < sy < y1 - 1):
                continue
            k += 1
            spirit_house(coll, m, 'grove_shrine_' + str(k), sx, sy, rng.uniform(0, math.tau), rng, fallen=rng.random() < .28)
            collider('grove_shrine_' + str(k), coll, sx - .4, sx + .4, sy - .4, sy + .4, 0, 1.6, 'wood')
    for j in range(5):
        px, py = trees[j]
        pts = [(px + math.cos(t) * .9, py + math.sin(t) * .9, 2.3 + .1 * math.sin(t * 3)) for t in np.linspace(0, math.tau, 14)]
        marigold_garland(coll, m, 'grove_garland_' + str(j), pts, rng, dead=.8)
    lamp('grove_shrine', 12, 64, .02, 1.6)
    lamp('grove_path', -13, 58.5, .02, 1.4)
    _edge_forest(coll, m, rect, rng, 760, gaps=[(sum(NORTH_BREACH_X) / 2, y0, 6), (x0, 54.3, 6), (x1, sum(GROVE_GALLERY_Y) / 2, 6)])

    def clear(x, y):
        return on_path(x, y, 1.5) or any((x - a) ** 2 + (y - b) ** 2 < 1.5 for a, b in trees)
    _growth(coll, m, 'grove', rect, rng, 900, clear)
    return zone.close()


# ------------------------------------------------------------------ Root Gallery


def _walk(coll, m, name, x, y0, y1, rng, images=False):
    """A roofed cloister walk running north, half fallen: piers, roof sections, some of them
    down, with the strangler figs holding up what is left."""
    width = 4.2
    step = 3.2
    ys = np.arange(y0, y1 + .01, step)
    for j, py in enumerate(ys):
        for side in (-1, 1):
            px = x + side * width / 2
            broken = rng.random() < .24
            height = 1.45 if broken else 3.1
            piece(coll, 'gallery_pier_broken' if broken else 'gallery_pier', f'{name}_pier_{j}_{side}', px, py, 0, rng.integers(0, 4) * math.pi / 2)
            collider(f'{name}_pier', coll, px - .24, px + .24, py - .24, py + .24, 0, height, 'stone')
            if rng.random() < .22:
                fig_roots(coll, m, f'{name}_fig_{j}', px, py, height, lambda z: .34, rng, n=5, spread=.7, crown=rng.uniform(1.2, 2))
        if images and j % 2 == 0:
            side = -1 if j % 4 == 0 else 1
            px = x + side * (width / 2 - .5)
            seated_image(coll, m, f'{name}_image_{j}', px, py + 1.6, -side * math.pi / 2, .7, headless=rng.random() < .5, damage=rng.random() < .4, seed=50 + j)
            collider(f'{name}_image_{j}', coll, px - .4, px + .4, py + 1.2, py + 2, 0, 1.1, 'stone')
    section = 3
    for j in range(0, len(ys) - section, section):
        cy = (ys[j] + ys[j + section]) / 2
        fate = rng.random()
        if fate < .22:
            # Gone: only a heap of what it was made of.
            rubble(coll, m, f'{name}_rubble_{j}', x + rng.uniform(-1.1, 1.1), cy, 1.6, 50, rng)
            continue
        made = set(coll.objects)
        temple_roof(coll, m, f'{name}_roof_{j}', x, cy, width + .5, step * section, 2.9, 1.2)
        roof = [o for o in coll.objects if o not in made and not o.name.startswith('col_')]
        if fate < .6:
            # Sagged on broken piers, one side low.
            lean(roof, x, cy, rng.uniform(-.2, .2), rng.uniform(-.08, .08))


def gallery(coll, m, rect, lamp):
    x0, x1, y0, y1 = rect
    rng = np.random.default_rng(5404)
    zone = Zone(coll, 'gallery')
    _ground(coll, m, 'earth_gallery', x0, x1, y0, y1)
    _walk(coll, m, 'gallery_west', 39, y0 + 4, y1 - 8, rng, images=True)
    _walk(coll, m, 'gallery_east', 54, y0 + 10, y1 - 4, rng)
    # Strangler trunks through the collapsed sections, and two cross walks between the galleries.
    for j, (px, py) in enumerate([(46.5, 18), (46.5, 42), (47, 62), (34, 30), (60, 24), (60, 50), (35, 62), (46, 7)]):
        giant(coll, m, px, py, rng.uniform(12, 18), 800 + j, rng, reach=1.7, collision=True)
    for j, py in enumerate((30, 53)):
        for px in np.arange(42.6, 52, 2.6):
            _slab(coll, m, f'gallery_cross_{j}', px - .6, px + .6, py - 1.3, py + 1.3, -.01, .02, 'stone')
    lamp('gallery_west', 40.3, 22, .02, 1.5)
    lamp('gallery_east', 52.9, 44, .02, 1.5)
    _edge_forest(coll, m, rect, rng, 840, gaps=[(sum(SALA_NORTH_X) / 2, y0, 7), (x0, sum(GROVE_GALLERY_Y) / 2, 7)])

    def clear(x, y):
        return abs(x - 39) < 2.6 or abs(x - 54) < 2.6 or abs(y - 30) < 1.6 or abs(y - 53) < 1.6
    _growth(coll, m, 'gallery', rect, rng, 500, clear)
    return zone.close()


# ------------------------------------------------------------------ Bone Terrace


def _tier_collider(coll, name, x0, x1, y0, y1, z0, z1, run=.55):
    """A raised tier's collider with its edges sloped inwards over `run` metres. Sora's capsule
    rides over only about 10 cm, so a square-edged 14 cm tier is a wall to her; on the slope
    her feet sink into the bricks for a step, which the first-person view never shows."""
    verts = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0 + run, y0 + run, z1), (x1 - run, y0 + run, z1), (x1 - run, y1 - run, z1), (x0 + run, y1 - run, z1)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    mesh_object('col_' + name, coll, verts, faces, surface='stone')


def _raise(objs, dz):
    for o in objs:
        o.location.z += dz
    return objs


def _bone_heap(coll, m, name, x, y, z, rng, skulls, bones, r=.55):
    """Skulls and long bones heaped against each other, as bones are when someone has
    gathered them out of the ground and piled them where they will be seen."""
    k = 0
    for layer, (count, radius, h) in enumerate([(9, r * .78, 0), (6, r * .45, .12), (3, r * .2, .23), (1, 0, .33)]):
        for j in range(count):
            a = math.tau * j / max(count, 1) + rng.normal(0, .2) + layer
            px, py = x + math.cos(a) * radius, y + math.sin(a) * radius
            yaw = a + math.pi / 2 + rng.normal(0, .9)
            place_copy(coll, skulls[k % len(skulls)], px, py, z + h, yaw, (rng.normal(0, .35), rng.normal(0, .35)))
            k += 1
    for j in range(12):
        a = rng.uniform(0, math.tau)
        d = r * rng.uniform(.6, 1.15)
        lean = rng.uniform(.15, .7)
        place_copy(coll, bones[j % len(bones)], x + math.cos(a) * d, y + math.sin(a) * d, z + rng.uniform(.0, .08),
                   a + math.pi / 2 + rng.normal(0, .4), (lean * math.cos(a + math.pi / 2), lean * math.sin(a + math.pi / 2)))
    collider(name, coll, x - r * .8, x + r * .8, y - r * .8, y + r * .8, z, z + .45, 'stone')


def terrace(coll, m, rect, lamp):
    """The way ends here. A brick terrace with a sorcerer's altar, ringed with skulls on low
    tiers, bones underfoot and red cord overhead. Skulls on stakes warn at the way in; bones
    are heaped at the back corners; a body rolled in a mat lies on a bier by a burnt-out
    pyre, and a fresh grave waits for it beyond the bricks. Funeral cloth hangs in rags in
    the trees. Nothing here is a temple's practice. (Advisor review: every item.)"""
    x0, x1, y0, y1 = rect
    rng = np.random.default_rng(5505)
    zone = Zone(coll, 'terrace')
    # Old bone is stained the colour of the earth it lay in: grimy, with grain, never clean white.
    m = dict(m, bone=library_material('clay_plaster', 'M_ep2_bone_old', colour=(.27, .22, .15), tile=.35))
    _ground(coll, m, 'earth_terrace', x0, x1, y0, y1)
    cx, cy = 47.0, -33.0
    gate_x = sum(SALA_SOUTH_X) / 2
    tiers = [(11, 6.2, -.01, .14), (8.2, 4.6, .13, .28)]
    for i, (half_x, half_y, base, top) in enumerate(tiers):
        _slab(coll, m, f'terrace_tier_{i}', cx - half_x, cx + half_x, cy - half_y, cy + half_y, -.01, top, 'brick' if i else 'mould_grey')
        _tier_collider(coll, f'terrace_tier_{i}', cx - half_x, cx + half_x, cy - half_y, cy + half_y, base, top)
    t0, t1 = tiers[0][3], tiers[1][3]
    sorcery_altar(coll, m, 'terrace_altar', cx, cy - 1.6, 0, rng)
    collider('terrace_altar', coll, cx - 1, cx + 1, cy - 2.4, cy - .8, 0, 1.2, 'stone')
    # A machete laid across the altar.
    knife = place(coll, 'machete', (cx + .05, cy - 1.84, .585), 0)
    knife.rotation_euler = (math.pi / 2, 0, math.pi / 2 + .25)

    skulls = skull_variants(coll, m, rng, n=6, prefix='terrace_skullv')
    bones = [long_bone(coll, m, f'terrace_bonev_{k}', rng, length=L) for k, L in enumerate((.46, .4, .3))]

    # Skulls in rows along the back tiers, all facing the way in.
    k = 0
    for row, (span, py, pz) in enumerate([(7.4, cy - 4.2, t1), (10, cy - 5.6, t0)]):
        for px in np.arange(cx - span, cx + span + .01, .5):
            if rng.random() < .22:
                continue
            k += 1
            place_copy(coll, skulls[k % len(skulls)], px + rng.normal(0, .07), py + rng.normal(0, .07), pz,
                       math.pi + rng.normal(0, .45), (rng.normal(0, .1), rng.normal(0, .1)))
    # Heaped bones in the two back corners.
    for j, px in enumerate((cx - 7.3, cx + 7.3)):
        _bone_heap(coll, m, f'terrace_heap_{j}', px, cy - 5.4, t0, rng, skulls, bones, r=.5)
    # Loose bones underfoot: knuckles and splinters, long bones, ribs.
    for j in range(46):
        bx, by = rng.uniform(cx - 8, cx + 8), rng.uniform(cy - 4, cy + 4.4)
        a = rng.uniform(0, math.tau)
        length = rng.uniform(.04, .16)
        tube('terrace_bone', coll, [(bx, by, t1 + .012), (bx + math.cos(a) * length, by + math.sin(a) * length, t1 + .016)], rng.uniform(.006, .012), m['bone'], sides=5)
    for j in range(16):
        bx, by = rng.uniform(cx - 7.6, cx + 7.6), rng.uniform(cy - 4.2, cy + 4.2)
        if abs(bx - cx) < 1.6 and by > cy - 2.6:
            continue  # the walk up to the altar stays clear
        place_copy(coll, bones[j % len(bones)], bx, by, t1 - .008, rng.uniform(0, math.tau), (0, rng.normal(0, .05)))
    for j in range(14):
        rib(coll, m, 'terrace_rib', rng.uniform(cx - 7.6, cx + 7.6), rng.uniform(cy - 4.2, cy + 4.2), t1, rng.uniform(0, math.tau), rng)

    # The dead one, rolled in a mat on a bamboo bier, east of the altar. A little oil lamp
    # burns at the head; whoever lit it has not gone far.
    bx, by = cx + 5.6, cy + 1.8
    bier(coll, m, 'terrace_bier', bx, by, t1, math.pi / 2 + .08)
    wrapped_dead(coll, m, 'terrace_dead', bx, by, t1 + .088, math.pi / 2 + .08, rng)
    collider('terrace_bier', coll, bx - 1.2, bx + 1.2, by - .4, by + .4, t1, t1 + .45, 'wood')
    lamp('terrace_dead', bx - 1.55, by + .45, t1, 1.25)
    candle_cluster(coll, m, 'terrace_dead_candles', bx - 1.5, by - .35, t1, rng, n=5, r=.16)
    # Where another was burnt, west of the altar: ash, charred logs, a skull in the ash.
    pyre_remains(coll, m, 'terrace_pyre', cx - 5.4, cy + 1.6, t1, rng, skulls[2])
    jug = place(coll, 'jug_01', (cx - 4.1, cy + 2.6, t1 + .08), 40)
    jug.rotation_euler = (math.pi / 2, 0, .7)
    # A pot of bones tipped over at the west end of the low tier.
    pot = place(coll, 'ceramic_pot', (cx - 10, cy + 3.4, t0 + .25), 0, .8)
    pot.rotation_euler = (math.radians(78), 0, 2.2)
    for j in range(3):
        place_copy(coll, bones[j], cx - 9.4 + j * .18, cy + 2.7 - j * .1, t0 - .008, rng.uniform(1.6, 2.4))
    place_copy(coll, skulls[4], cx - 9.1, cy + 2.4, t0, 2.6, (.3, 0))
    place(coll, 'wooden_bowl_01', (cx - .9, cy - .55, t1), 0)
    # Candles burnt down in their puddles in front of the altar and at the ends of the rows.
    for j, (px, py) in enumerate([(cx - 1.9, cy - .5), (cx + 2.4, cy - .2), (cx - 7.1, cy - 3.7), (cx + 7.1, cy - 3.7)]):
        candle_cluster(coll, m, f'terrace_candles_{j}', px, py, t1, rng)

    # A grave dug in the earth past the east end of the tiers, the spade left in the spoil.
    gx, gy = cx + 13.2, cy + .4
    spoil = lathe('terrace_grave_spoil', coll, [(1.05, 0), (.9, .14), (.6, .3), (.25, .38), (0, .4)], 0, 0, 0, m['mud'], segments=16)
    spoil.location, spoil.scale = (gx + 1.1, gy, -.02), (1, 1.5, 1)
    _slab(coll, m, 'terrace_grave_pit', gx - .45, gx + .45, gy - 1, gy + 1, -.012, -.004, 'void')
    collider('terrace_grave', coll, gx - .5, gx + 2.1, gy - 1.6, gy + 1.6, 0, .4, 'dirt')
    spade = place(coll, 'rusted_spade_01', (gx + .9, gy - .5, .5), 0)
    spade.rotation_euler = (math.radians(22), math.radians(-12), .5)

    # The tiers are breaking up: brick heaps where corners have gone, roots over the bricks.
    for j, (px, py, r, pz) in enumerate([(cx - 11, cy - 6.2, .9, 0), (cx + 11, cy + 6.2, .8, 0), (cx + 11, cy - 6.2, 1.1, 0),
                                         (cx + 8.2, cy + 4.6, .6, t0), (cx - 8.2, cy - 4.6, .5, t0)]):
        _raise(rubble(coll, m, f'terrace_rubble_{j}', px, py, r, 40, rng), pz)
    place(coll, 'root_cluster_01', (cx + 12.4, cy - 6.8, -.05), 210, .75)
    place(coll, 'dead_tree_trunk', (cx - 4, cy - 6.75, .06), 4)
    for j, (px, py, rx, ry, pz) in enumerate([(cx - 9.6, cy + 4.6, 1.4, 1, t0), (cx + 6.6, cy - 3.6, 1.2, .7, t1), (cx + 9.8, cy + 5, 1.6, .9, t0)]):
        _raise(leaf_litter(coll, m, f'terrace_litter_{j}', px, py, rx, ry, rng), pz)

    # The way in: skulls on stakes either side of the path, past the old cord boundary.
    for j, (side, py) in enumerate([(-1, y1 - 2.4), (1, y1 - 2.9), (-1, y1 - 4.2), (1, y1 - 4.4)]):
        px = gate_x + side * rng.uniform(2.2, 2.6)
        skull_stake(coll, m, f'terrace_skull_stake_{j}', skulls[j % len(skulls)], px, py, rng)
        collider(f'terrace_skull_stake_{j}', coll, px - .07, px + .07, py - .07, py + .07, 0, 1.4, 'wood')
    for j, px in enumerate((cx - 2.9, cx + 2.9)):
        skull_stake(coll, m, f'terrace_altar_stake_{j}', skulls[(j + 3) % len(skulls)], px, cy - 3.2, rng, height=1.8)
        collider(f'terrace_altar_stake_{j}', coll, px - .07, px + .07, cy - 3.27, cy - 3.13, 0, 1.8, 'wood')

    anchors = [(cx - 9, cy - 5, 3.2), (cx + 9, cy - 5, 3.4), (cx - 7, cy + 5, 3.1), (cx + 8, cy + 5, 3.3), (cx, cy - 3, 3.0), (cx - 3, cy + 2, 3.2)]
    for j, (px, py, _) in enumerate(anchors[:4]):
        giant(coll, m, px + (2.5 if px > cx else -2.5), py + (1.6 if py > cy else -1.6), rng.uniform(11, 15), 900 + j, rng, reach=1.5, collision=True)
    red_string_web(coll, m, 'terrace_web', anchors, rng, density=1.6)
    boundary_stakes(coll, m, 'terrace_stakes', [(gate_x + side * 2.2, y1 - 1.4 - t * 1.9) for side in (-1, 1) for t in range(2)], rng)
    for j, (px, py, top, drop) in enumerate([(cx - 3, cy - .2, 3.0, .9), (cx + 3, cy - .2, 3.0, .9), (bx + .4, by + .2, 3.1, 1.5), (cx - 5.6, cy + 1.2, 3.0, 1.2)]):
        hanging_doll(coll, m, 'terrace_doll_' + str(j), (px, py, top), rng, drop=drop)
    # White funeral cloth torn into rags, caught high in the trees and on the cord.
    for j, (px, py, top) in enumerate(anchors + [(cx - 12.6, cy + 2, 4.4), (cx + 12.2, cy + 1, 4.1), (cx + 1.5, cy + 6.4, 3.8), (gate_x - 1.2, y1 - 3.4, 3.6)]):
        funeral_tatter(coll, m, f'terrace_tatter_{j}', px + rng.normal(0, .3), py + rng.normal(0, .3), top - .05, rng)
    lamp('terrace_altar', cx + 1.5, cy - .6, t1, 2.0)
    _edge_forest(coll, m, rect, rng, 920, gaps=[(gate_x, y1, 6)])
    drop_protos(coll, skulls + bones)

    def clear(x, y):
        return (abs(x - cx) < 11.6 and abs(y - cy) < 6.8 or abs(x - gate_x) < 1.8
                or abs(x - gx - .8) < 2 and abs(y - gy) < 2)
    _growth(coll, m, 'terrace', rect, rng, 260, clear)
    return zone.close()


# ------------------------------------------------------------------ the whole


def boundaries(coll, zones):
    """The outer limits of the loop and the walls between its zones, with the ways through."""
    court_r, tank_r = _rect(zones, 'court'), _rect(zones, 'tank')
    grove_r, gallery_r = _rect(zones, 'grove'), _rect(zones, 'gallery')
    terrace_r = _rect(zones, 'terrace')
    # Court and tank, west, south and north.
    _block(coll, court_r[0] - 1, court_r[0], court_r[2] - 1, tank_r[3] + 1)
    _block(coll, court_r[0], court_r[1] + .5, court_r[2] - 1, court_r[2])
    _block(coll, tank_r[0], tank_r[1], tank_r[3], tank_r[3] + 1)
    # The grove, west, north and east, each with its way through.
    tank_grove = (43 + TANK_GROVE_BAY * 3.222, 43 + (TANK_GROVE_BAY + 1) * 3.222)
    _block(coll, grove_r[1], grove_r[1] + .4, grove_r[2], GROVE_GALLERY_Y[0])
    _block(coll, grove_r[1], grove_r[1] + .4, GROVE_GALLERY_Y[1], grove_r[3] + 1)
    _block(coll, grove_r[0], grove_r[1] + .4, grove_r[3], grove_r[3] + 1)
    _block(coll, grove_r[0] - .5, grove_r[0] + .5, tank_r[3], grove_r[3] + 1)
    # The gallery, north, east and south past the clearing.
    _block(coll, gallery_r[0], gallery_r[1] + 1, gallery_r[3], gallery_r[3] + 1)
    _block(coll, gallery_r[1], gallery_r[1] + 1, terrace_r[2] - 1, gallery_r[3])
    _block(coll, 45.5, gallery_r[1], gallery_r[2] - 1, gallery_r[2])
    # The terrace, north past the clearing and south.
    _block(coll, 45.5, terrace_r[1], terrace_r[3], terrace_r[3] + 1)
    _block(coll, terrace_r[0] - .5, terrace_r[1], terrace_r[2] - 1, terrace_r[2])
    return tank_grove


def build_lost_garden(coll, m, zones, lamp):
    """Everything outside the compound. Call after the compound's walls exist."""
    rng = np.random.default_rng(5606)
    tank_grove = boundaries(coll, zones)
    court_tank = temple_wall(coll, m, 'court_tank_wall', (-81, 21), (-30, 21), rng, 'mould_grey', breaches=(COURT_TANK_BAY, 3), open_bays=(COURT_TANK_BAY,))
    tank_grove_wall = temple_wall(coll, m, 'tank_grove_wall', (-30, 43), (-30, 72), rng, 'mould_white', breaches=(TANK_GROVE_BAY,), open_bays=(TANK_GROVE_BAY,))
    del court_tank, tank_grove_wall, tank_grove
    roots = [court(coll, m, _rect(zones, 'court'), lamp), tank(coll, m, _rect(zones, 'tank'), lamp), grove(coll, m, _rect(zones, 'grove'), lamp),
             gallery(coll, m, _rect(zones, 'gallery'), lamp), terrace(coll, m, _rect(zones, 'terrace'), lamp)]
    return roots
