"""The funeral hall's offerings and the vigil's leavings (Episode 1, November 20, 2026
redesign: "add more offerings thing and make the whole funeral more detail, realistic
and scary").

What a Khmer household sets out for its dead in the 1930s (Cultural Guide 3; every item
an advisor-review item): beeswax candles and joss sticks in bowls of sand, a hand of
bananas and a young coconut, folded banana-leaf cups (kantong) of flowers and of betel,
jasmine strung over the portrait, marigolds, rice, water; the banana-trunk baysei on
footed stands; at the coffin's foot a bowl of uncooked rice with a candle in it; and the
monks' raised seat, where the evening's chanting ended: their triangular cushions, palm-
leaf fans (talapat) leaning on the wall, black alms bowls, the saffron robes offered to
them folded on a tray, and the white thread (sai sin) running from the coffin to it.

The vigil has gone on for nights: candles burnt to stubs in pools of wax, one knocked
over, petals and ash trodden into the mat. Coordinates are Blender metres (X east,
Y north, Z up), the hall floor at FLOOR (the reed mat's top).
"""
import math

import bpy
from mathutils import Matrix, Vector

import offerings_kit as ok
from kit import library_material
from shrine_craft import Batch, place

FLOOR = 2.512
TABLE = 3.212            # the portrait altar's top (altar_table_crafted)
DAIS_LOW, DAIS_HIGH = 2.805, 3.055
# The vigil's four incense corners (Vigil.ts, interact_incense_N) and the two baysei
# that stood on the front pair (baysei_N_bowl, their bowls' foot at 2.81).
CORNERS = [(-1.8, 14.55), (1.3, 14.55), (1.3, 16.6), (-1.8, 16.6)]
BAYSEI_FOOT = 2.81
MONKS = (1.62, 2.86, 15.0, 17.45)     # the monks' raised seat, along the east wall
MONKS_H = 0.3


def _mats():
    m = dict(ok.materials())

    def lib(key, tex, tile, tint=None):
        name = f"M_fo_{key}"
        mat = bpy.data.materials.get(name)
        if mat is None:
            mat = library_material(tex, name, tint=tint, tile=tile)
        return mat

    m["teak"] = lib("teak", "teak_veneer", 1.0, tint=(.62, .5, .42))
    m["seat_wood"] = lib("seat_wood", "dark_wooden_planks", 2.0, tint=(.75, .68, .6))
    m["cushion"] = lib("cushion", "quatrefoil_jacquard_fabric", .28, tint=(.55, .2, .14))
    m["robe"] = lib("robe", "rough_linen", .27, tint=(.82, .44, .12))
    m["mat"] = bpy.data.materials.get("M_reed_mat") or lib("mat", "fabric_pattern_07", .4)
    m["thread"] = bpy.data.materials.get("M_white_thread") or m["jasmine"]
    m["iron"] = ok.surf.plain("M_fo_alms_bowl_lacquer", (.025, .022, .02), rough=.32)
    # A talapat's face: dried palm leaf split and stitched flat (the reed scan, its
    # strands running across the fan).
    m["fan_leaf"] = lib("fan_leaf", "reed_roof_04", .35, tint=(.68, .58, .4))
    m["fan_leaf"].use_backface_culling = False
    return m


def _stand(b, m, x, y, top, rng, radius=.15):
    """A turned teak offering stand, footed, its dish tarnished brass."""
    h = top - FLOOR
    prof = [(0, 0), (radius * .95, 0), (radius, .012), (radius * .7, .03), (radius * .32, .06),
            (radius * .24, h * .45), (radius * .3, h * .55), (radius * .24, h * .65), (radius * .3, h - .045),
            (radius * .55, h - .03), (0, h - .03)]
    b.lathe(m["teak"], prof, xf=place(x, y, FLOOR - .002), segments=28, tile=.3)
    dish = [(0, h - .032), (radius * 1.15, h - .03), (radius * 1.2, h - .004), (radius * 1.12, h), (0, h - .02)]
    b.lathe(m["brass"], dish, xf=place(x, y, FLOOR - .002), segments=32, tile=.2)


def _candle_row(b, m, x0, x1, y, z, rng, n):
    """Candles burnt down where the mourners set them, some still lit."""
    tips = []
    for k in range(n):
        x = x0 + (x1 - x0) * (k + rng.uniform(-.25, .25)) / max(1, n - 1)
        ok.candle_dish(b, m, place(x, y + rng.normal(0, .015), z), rng, radius=.04, melt=rng.uniform(.4, 1))
        lit = rng.random() < .55
        tip = ok.candle(b, m, place(x, y, z + .006, rz=rng.uniform(0, 6)), rng, height=rng.uniform(.03, .11),
                        radius=.0095, melt=rng.uniform(.5, 1), lit=lit)
        if lit:
            tips.append(tip)
        if rng.random() < .4:
            ok.wax_spill(b, m, place(x + rng.normal(0, .02), y + rng.normal(0, .02), z), rng, radius=rng.uniform(.02, .04))
    return tips


def _cushion(b, m, x, y, z, rz):
    """A Khmer triangular back cushion (kneay), its cover faded red brocade."""
    w, d, h = .5, .3, .34
    verts = [(-w / 2, -d / 2, 0), (w / 2, -d / 2, 0), (w / 2, d / 2, 0), (-w / 2, d / 2, 0),
             (-w / 2, d / 2 - .04, h), (w / 2, d / 2 - .04, h)]
    faces = [(0, 1, 2, 3)[::-1], (0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4)]
    uvs_face = []
    xf = place(x, y, z, rz=rz)
    for f in faces:
        pts = [Vector(verts[i]) for i in f]
        b.add(m["cushion"], [tuple(xf @ p) for p in pts], [tuple(range(len(f)))],
              [(p.x / .28 + p.z / .28, p.y / .28 + p.z / .28) for p in pts], smooth=False)
        uvs_face.append(f)


def _talapat(b, m, foot, lean_to, rng):
    """A monk's palm-leaf fan on its long handle, leant against the wall."""
    foot = Vector(foot)
    top = Vector(lean_to)
    axis = (top - foot).normalized()
    length = (top - foot).length
    b.tube(m["teak"], [tuple(foot), tuple(foot + axis * length * .62)], [.012, .011], sides=8)
    # The fan: an oval of stiff leaf, ribbed, its edge bound.
    centre = foot + axis * length * .8
    side = Vector((0, 1, 0))  # the fan faces into the room
    up = axis
    nrm = side.cross(up).normalized()
    ring = 28
    verts = [tuple(centre)]
    uvs = [(.5, .5)]
    for k in range(ring):
        a = math.tau * k / ring
        r = 1 + .03 * math.sin(a * 7)
        p = centre + side * math.cos(a) * .2 * r + up * math.sin(a) * .26 * r + nrm * .006 * math.sin(a * 14)
        verts.append(tuple(p))
        uvs.append((.5 + .5 * math.cos(a), .5 + .5 * math.sin(a)))
    faces = [(0, 1 + k, 1 + (k + 1) % ring) for k in range(ring)]
    uvs = [(u * .45, v * .55) for u, v in uvs]
    b.add(m["fan_leaf"], verts, faces, uvs, smooth=True)
    b.tube(m["rattan"] if "rattan" in m else m["bamboo"], [verts[1 + k] for k in range(ring)] + [verts[1]],
           [.006] * (ring + 1), sides=5)


def _alms_bowl(b, m, x, y, z, rng):
    prof = [(0, 0), (.06, 0), (.11, .03), (.135, .08), (.13, .12), (.115, .14), (.1, .145), (0, .15)]
    b.lathe(m["iron"], prof, xf=place(x, y, z), segments=32, tile=.2)
    lid = [(0, .145), (.112, .145), (.11, .16), (.06, .185), (.02, .19), (.02, .21), (0, .215)]
    b.lathe(m["iron"], lid, xf=place(x, y, z), segments=32, tile=.2)


def build(coll, rng):
    """Everything above, as a few batched objects. Returns the lit flames' tips (for
    lights) and the joss bowls' tops (for smoke)."""
    m = _mats()
    b = Batch("funeral_offerings")
    flames, smoke = [], []

    # -- The two baysei on tall teak stands either side of the shroud's open front.
    for k, (x, y) in enumerate(CORNERS[:2]):
        _stand(b, m, x + (.1 if k == 0 else -.1), y, BAYSEI_FOOT, rng)

    # -- The portrait altar's top.
    plate = [(0, 0), (.1, 0), (.12, .012), (.125, .018), (0, .006)]
    b.lathe(m["clay"], plate, xf=place(.36, 14.24, TABLE), segments=28, tile=.2)
    ok.bananas(b, m, place(.36, 14.24, TABLE + .006, rz=2.6), rng, count=7, length=.1)
    ok.coconut(b, m, place(-.93, 14.36, TABLE, rz=.4), rng, height=.17, radius=.068)
    ok.leaf_cup(b, m, place(-.5, 14.02, TABLE, rz=.2), rng, size=.07, height=.035, fill="flowers")
    ok.leaf_cup(b, m, place(.04, 14.02, TABLE, rz=-.3), rng, size=.07, height=.035, fill="betel")
    ok.small_cup(b, m, place(-.95, 14.06, TABLE), rng, radius=.022, height=.03, liquid="water")
    ok.rice_grains(b, m, (.23, 14.15, TABLE), rng, count=50, spread=.035)
    for _ in range(9):
        ok.marigold(b, m, (rng.uniform(-.98, .48), rng.uniform(13.98, 14.18), TABLE), rng, .012, dead=rng.random() < .5)
    # Jasmine strung along the front of the portrait's riser.
    ok.jasmine_string(b, m, [(-.42 + .84 * t / 10 - .0, 14.29 - .012 * math.sin(math.pi * t / 10), TABLE + .004)
                             for t in range(11)], rng)

    # -- Candles: on the floor either side of the burner, and along the dais's low step.
    flames += _candle_row(b, m, -1.0, -.62, 13.58, FLOOR, rng, 4)
    flames += _candle_row(b, m, .14, .5, 13.58, FLOOR, rng, 4)
    flames += _candle_row(b, m, -1.5, -1.3, 14.92, DAIS_LOW, rng, 2)
    flames += _candle_row(b, m, .82, 1.02, 14.92, DAIS_LOW, rng, 2)
    # One knocked over on the step, its wax run out across the cloth.
    ok.candle(b, m, place(-.95, 15.0, DAIS_LOW + .011, rz=.4) @ Matrix.Rotation(math.pi / 2, 4, "Y"), rng,
              height=.1, radius=.0105, melt=.3, lit=False)
    ok.wax_spill(b, m, place(-.9, 15.02, DAIS_LOW), rng, radius=.05)

    # -- At the coffin's foot (east end, on the low step): rice with a candle and sticks in it.
    bowl = [(0, 0), (.05, 0), (.08, .03), (.095, .07), (.09, .075), (0, .06)]
    b.lathe(m["clay"], bowl, xf=place(.98, 15.9, DAIS_LOW), segments=28, tile=.2)
    ok.rice_grains(b, m, (.98, 15.9, DAIS_LOW + .062), rng, count=160, spread=.03)
    flames.append(ok.candle(b, m, place(.98, 15.9, DAIS_LOW + .06), rng, height=.08, radius=.009, melt=.6, lit=True))
    for k in range(3):
        a = k * 2.1
        ok.joss_stick(b, m, Vector((.98 + .03 * math.cos(a), 15.9 + .03 * math.sin(a), DAIS_LOW + .06)),
                      Vector((.08 * math.cos(a), .08 * math.sin(a), 1)).normalized(), .2, rng, burnt=.3)
    smoke.append(Vector((.98, 15.9, DAIS_LOW + .3)))
    ok.coconut(b, m, place(.98, 16.35, DAIS_LOW, rz=1.4), rng, height=.16, radius=.065)

    # -- The monks' raised seat along the east wall, the chanting over.
    x0, x1, y0, y1 = MONKS
    b.box(m["seat_wood"], (x1 - x0, y1 - y0, MONKS_H), ((x0 + x1) / 2, (y0 + y1) / 2, FLOOR - .005 + MONKS_H / 2),
          chamfer=.01, tile=2.0)
    top = FLOOR - .005 + MONKS_H
    b.add(m["mat"], [(x0 + .04, y0 + .04, top + .003), (x1 - .04, y0 + .04, top + .003), (x1 - .04, y1 - .04, top + .003),
                     (x0 + .04, y1 - .04, top + .003)], [(0, 1, 2, 3)],
          [(0, 0), ((x1 - x0) / .9, 0), ((x1 - x0) / .9, (y1 - y0) / .9), (0, (y1 - y0) / .9)], smooth=False)
    for k, y in enumerate((15.35, 15.95, 16.55, 17.12)):
        _cushion(b, m, x1 - .2, y, top + .003, rz=-math.pi / 2)
    for y, lean in ((15.62, .06), (16.25, -.05), (16.86, .04)):
        _talapat(b, m, (x1 - .05, y, top + .004), (x1 + .02, y + lean, top + 1.45), rng)
    # Two candles left burning on the seat's edge after the monks went home.
    for y in (15.72, 16.78):
        ok.candle_dish(b, m, place(x0 + .14, y, top + .003), rng, radius=.04, melt=.8)
        flames.append(ok.candle(b, m, place(x0 + .14, y, top + .009, rz=rng.uniform(0, 6)), rng, height=.075,
                                radius=.0095, melt=.7, lit=True))
    _alms_bowl(b, m, x0 + .35, 15.3, top + .003, rng)
    _alms_bowl(b, m, x0 + .35, 17.1, top + .003, rng)
    # Saffron robes offered to the monks, folded on a tray.
    b.box(m["brass"], (.46, .34, .02), (x0 + .4, 16.2, top + .013), chamfer=.004, tile=.2)
    for j in range(3):
        b.box(m["robe"], (.36 - .02 * j, .26 - .015 * j, .045), (x0 + .4 + .005 * j, 16.2, top + .046 + .045 * j),
              chamfer=.012, tile=.27)
    # Sai sin: the white cord from the coffin's handle across to the monks' seat.
    a = Vector((.79, 16.24, 3.38))
    c = Vector((x0 + .1, 16.0, top + .02))
    pts, rad = [], []
    for i in range(17):
        t = i / 16
        p = a.lerp(c, t)
        p.z -= .18 * math.sin(math.pi * t)
        pts.append(tuple(p))
        rad.append(.0018)
    b.tube(m["thread"], pts, rad, sides=4)

    # -- Petals and marigolds trodden into the mat, a trail of them toward the door.
    for _ in range(40):
        ok.marigold(b, m, (rng.uniform(-1.6, 1.1), rng.uniform(12.6, 14.7), FLOOR), rng, .011, dead=rng.random() < .7)
    objs = b.build(coll)
    return objs, flames, smoke


# Where the vigil's four incense corners stand now (Blender x, y): the front pair on
# the mat before the shroud, where mourners kneel; the back pair outside the shroud's
# sides (inside it, Sora could not reach them).
VIGIL_CORNERS = [(-1.35, 13.78, 0.0), (.85, 13.78, 0.0), (1.72, 17.72, .3), (-2.32, 15.95, .3)]


def vigil_burner(coll, marker, x, y, stand, rng):
    """A clay bowl of sand and joss sticks for the vigil to tend (Vigil.ts finds the
    sticks by their material, M_incense, and the sand by M_incense_sand), on a low
    teak stand at the back corners. Built as one mesh under `marker`."""
    m = dict(_mats())
    for key, name in (("incense", "M_incense"), ("sand", "M_incense_sand"), ("ash", "M_funeral_ash")):
        mat = bpy.data.materials.get(name)
        if mat is not None:
            m[key] = mat
    b = Batch(f"{marker.name}_burner")
    z = FLOOR
    if stand:
        _stand(b, m, x, y, FLOOR + stand, rng, radius=.12)
        z = FLOOR + stand
    ok.incense_bowl(b, m, place(x, y, z), rng, radius=.09, height=.075, sticks=18, lit=5)
    ok.rice_grains(b, m, (x, y, FLOOR), rng, count=30, spread=.08)
    objs = list(b.build(coll).values())
    from khmer import join
    burner = join(objs, marker.name.replace("interact_incense", "incense_burner"))
    mw = burner.matrix_world.copy()
    burner.parent = marker
    burner.matrix_world = mw
    return burner
