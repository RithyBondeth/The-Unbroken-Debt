"""The pond east of the compound (Episode 1 village expansion, November 2026).

- The pond (ត្រពាំង): still black water in a dug basin, its banks trodden to mud,
  lotus pads in drifts, a few closed buds and the dry, drooping seed heads of
  last season; reeds thick on the far side.
- The bathing jetty: forest posts driven into the bed, a narrow walk of loose
  boards out to a platform with steps down into the water. Boards are missing,
  one hangs in the water; a bucket and a single sandal are left on the end.
- The sala: a small open pavilion on the north bank where the family rested in
  the heat of the day, on hewn posts over laterite footings, a raised plank floor
  with a bench and rail round three sides, a Marseille-tile roof gone black with
  lichen. A rolled mat, a water jar and a tea set are still in it.
- A dugout boat half sunk at the south bank; jars at the water's edge.
- The pond's spirit (`pond_spirit`): a drowned woman in a bloodied white dress
  standing at the end of the jetty, hair over her face (user-supplied Sketchfab
  model, CC BY 4.0, see import-blood-spirit.py); PondSpirit.ts haunts with her.

Blender axes, metres. Plan in village_layout.EAST_POND.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

import village_layout as L
import village_expansion as VE
from kit import collider
from rural_kit import lashing, log, materials, place_model, timber, tile_of
from shrine_craft import Batch
from west_yard import _col, _finish, _frame, _local_ground

WATER = VE.POND_WATER


# ======================================================================= surfaces


def lotus_materials():
    """Lotus pads: a waxy dark green with pale radial veins, browning and holed at
    the rim; and the dead ones, curled and gone tobacco-brown."""
    import shrine_surfaces as ss
    out = {}
    size = 512
    yy, xx = np.mgrid[0:size, 0:size] / size - .5
    r = np.hypot(xx, yy) * 2
    a = np.arctan2(yy, xx)
    rng = np.random.default_rng(2611)
    from weathering import fbm
    n = fbm(size, rng)
    veins = np.clip(1 - np.abs(np.sin(a * 11 + .3 * np.sin(a * 3))) * 9, 0, 1) * np.clip(r * 1.4, 0, 1) * (r < 1)
    ring = np.clip((r - .82) / .18, 0, 1)
    for name, base, edge in (("lotus_pad", (.05, .11, .04), (.16, .13, .05)), ("lotus_dead", (.13, .085, .04), (.07, .05, .03))):
        rgb = np.zeros((size, size, 3))
        for c in range(3):
            rgb[:, :, c] = base[c] * (.85 + .3 * n) + (edge[c] - base[c]) * ring * (.6 + .4 * n)
            rgb[:, :, c] += veins * (.035 if name == "lotus_pad" else .02)
        height = veins * .6 + n * .25
        rough = np.full((size, size), .38 if name == "lotus_pad" else .7) + .1 * n
        mat = bpy.data.materials.get(f"M_{name}") or ss.pbr(name, rgb, height, rough, tile=1.0, normal_strength=1.4)
        mat.use_backface_culling = False
        out[name] = mat
    out["lotus_bud"] = bpy.data.materials.get("M_lotus_bud")
    out["stem"] = bpy.data.materials.get("M_stem_green")
    out["seed_head"] = bpy.data.materials.get("M_rk_seed_head") or _plain("M_rk_seed_head", (.09, .065, .035), .8)
    return out


def _plain(name, colour, rough):
    from kit import plain
    return plain(name, colour, rough=rough)


# ======================================================================= jetty


def jetty(coll, m, ground, rng):
    """The bathing jetty, out from the west bank; returns its end platform's centre."""
    x0, y0, rot = L.EAST_POND["jetty"]
    W = Matrix.Translation((x0, y0, 0)) @ Matrix.Rotation(rot, 4, "Z")
    g = lambda u, v: ground(*(W @ Vector((u, v, 0))).xy)  # noqa: E731
    b = Batch("ep_jetty")
    H, P, BA = m["hewn"], m["planks"], m["bark"]
    deck = WATER + .42
    LEN, HW = 6.2, .55
    # Posts: pairs every 1.5 m, driven deep into the bed; the end platform on four more.
    stations = [(u, v) for u in np.arange(.3, LEN + .01, 1.55) for v in (-HW, HW)]
    stations += [(LEN + 1.6, -.9), (LEN + 1.6, .9), (LEN, -.9), (LEN, .9)]
    for u, v in stations:
        bed = min(g(u, v), WATER) - .6
        top = deck - .05 + rng.uniform(-.03, .04)
        log(b, BA, (u, v, bed), (u + rng.normal(0, .03), v + rng.normal(0, .03), top), .07, .06, rng, sides=7, bow=.01)
    # Stringers along the walk, bearers across under the platform.
    for v in (-HW + .02, HW - .02):
        timber(b, H, (-.3, v, deck - .1), (LEN + .1, v, deck - .1 + rng.uniform(-.03, .02)), .08, .1, rng)
    for u in (LEN, LEN + 1.6):
        timber(b, H, (u, -1.0, deck - .1), (u, 1.0, deck - .1), .1, .1, rng)
    for v in (-.85, 0, .85):
        timber(b, H, (LEN - .05, v, deck - .02), (LEN + 1.65, v, deck - .02), .07, .07, rng)
    # Deck boards across the walk: some gone, one snapped and hanging in the water.
    k = 0
    for u in np.arange(-.25, LEN, .2):
        k += 1
        if rng.random() < .1 or k in (14, 15):
            if k == 14:
                timber(b, P, (u, -HW - .05, deck - .02), (u + .25, HW * .3, WATER - .15), .17, .03, rng, chamfer=.004)
            continue
        jitter = rng.normal(0, .015)
        timber(b, P, (u + jitter, -HW - .05, deck), (u + jitter + rng.normal(0, .01), HW + .05, deck + rng.normal(0, .006)),
               .18, .03, rng, chamfer=.004, jitter=.002)
    for v in np.arange(-.95, .96, .2):
        if rng.random() < .07:
            continue
        timber(b, P, (LEN - .05, v, deck + .04), (LEN + 1.7, v + rng.normal(0, .01), deck + .04), .18, .03, rng,
               chamfer=.004, jitter=.002)
    # Steps down into the water off the platform's end.
    for s in range(3):
        z = deck - .22 * (s + 1)
        u = LEN + 1.75 + .26 * s
        timber(b, P, (u, -.6, z), (u, .6, z), .24, .04, rng, chamfer=.004)
        for v in (-.6, .6):
            log(b, BA, (u, v, min(g(u, v), WATER) - .5), (u, v, z - .02), .05, .045, rng, sides=6)
    # A pole rail along the north side, lashed to taller posts; broken off halfway.
    for u in (.3, 1.85, 3.4):
        log(b, BA, (u, HW + .05, deck - .1), (u, HW + .05, deck + .85), .045, .04, rng, sides=6)
        lashing(b, m["rattan"], (u, HW + .05, deck + .78), (0, 0, 1), .05, turns=3)
    log(b, BA, (.25, HW + .05, deck + .8), (3.45, HW + .05, deck + .78), .035, .03, rng, sides=6, bow=.004)
    log(b, BA, (3.45, HW + .08, deck + .78), (4.5, HW + .5, WATER + .02), .035, .03, rng, sides=6)
    objs = _finish(b, coll, W, "ep_jetty")
    # Sora keeps to the boards: walls along the walk and round the end platform.
    _col(coll, "ep_jetty_walk_n", W, -.3, LEN, HW, HW + .1, deck, deck + .9)
    _col(coll, "ep_jetty_walk_s", W, -.3, LEN, -HW - .1, -HW, deck, deck + .9)
    _col(coll, "ep_jetty_end_n", W, LEN, LEN + 1.7, .95, 1.05, deck, deck + .9)
    _col(coll, "ep_jetty_end_s", W, LEN, LEN + 1.7, -1.05, -.95, deck, deck + .9)
    _col(coll, "ep_jetty_end_e", W, LEN + 1.7, LEN + 1.8, -1.05, 1.05, deck, deck + .9)
    _col(coll, "ep_jetty_deck", W, -.3, LEN + 1.7, -1.0, 1.0, deck - .3, deck + .05)
    return objs, W, deck, LEN


# ======================================================================= sala


def sala(coll, m, ground, rng):
    """The pond-side sala; returns its objects, frame and floor height."""
    from colonial_parts import tiled_slope
    x, y, rot = L.EAST_POND["sala"]
    LX, WY = 2.3, 1.55
    W, base = _frame(x, y, rot, ground, [(-LX, -WY), (LX, -WY), (LX, WY), (-LX, WY)])
    g = _local_ground(W, base, ground)
    b = Batch("ep_sala")
    H, P, ST = m["hewn"], m["planks"], m["stone"]
    F = .58
    Z = F + 2.25
    RIDGE = Z + 1.15
    OUT = .65
    for px in (-LX, 0, LX):
        for py in (-WY, WY):
            b.box(ST, (.34, .34, .36), (px, py, g(px, py) + .08), chamfer=.03, tile=.5, rough=(.015, 7), rng=rng)
            timber(b, H, (px, py, g(px, py) + .25), (px + rng.normal(0, .01), py + rng.normal(0, .01), Z), .17, .17, rng,
                   jitter=.005)
    # Floor: bearers, joists, boards.
    for py in (-WY, 0, WY):
        timber(b, H, (-LX - .15, py, F - .17), (LX + .15, py, F - .17), .12, .14, rng)
    for px in np.arange(-LX, LX + .01, .55):
        timber(b, H, (px, -WY - .1, F - .07), (px, WY + .1, F - .07), .07, .08, rng)
    for py in np.arange(-WY - .05, WY + .06, .2):
        timber(b, P, (-LX - .12, py, F), (LX + .12, py, F + rng.normal(0, .004)), .19, .03, rng, chamfer=.004, jitter=.002)
    # The bench along the back and the ends, and a rail over it; open to the pond.
    seat = F + .42
    for (a, c) in (((-LX + .1, WY - .25), (LX - .1, WY - .25)), ((-LX + .25, -WY + .3), (-LX + .25, WY - .4)),
                   ((LX - .25, -WY + .3), (LX - .25, WY - .4))):
        timber(b, P, (*a, seat), (*c, seat), .32, .035, rng, chamfer=.005)
        for t in np.linspace(.08, .92, 4):
            p = Vector((*a, 0)) + (Vector((*c, 0)) - Vector((*a, 0))) * t
            timber(b, H, (p.x, p.y, F + .01), (p.x, p.y, seat - .02), .06, .06, rng)
    for (a, c) in (((-LX, WY), (LX, WY)), ((-LX, -WY), (-LX, WY)), ((LX, -WY), (LX, WY))):
        timber(b, H, (*a, F + .9), (*c, F + .9), .07, .05, rng)
        n = int(Vector((c[0] - a[0], c[1] - a[1])).length / .16)
        for k in range(1, n):
            t = k / n
            p = Vector((a[0] + (c[0] - a[0]) * t, a[1] + (c[1] - a[1]) * t))
            if rng.random() < .1:
                continue
            timber(b, H, (p.x, p.y, F + .02), (p.x, p.y, F + .88), .035, .035, rng, chamfer=.006)
    # Wall plates, tie beams, king posts, ridge, rafters.
    for py in (-WY, WY):
        timber(b, H, (-LX - .3, py, Z), (LX + .3, py, Z), .12, .14, rng)
    for px in (-LX, 0, LX):
        timber(b, H, (px, -WY - .25, Z + .1), (px, WY + .25, Z + .1), .11, .13, rng)
        timber(b, H, (px, 0, Z + .15), (px, 0, RIDGE - .05), .1, .1, rng)
    timber(b, H, (-LX - .7, 0, RIDGE), (LX + .7, 0, RIDGE), .12, .14, rng)
    eave_z = Z - OUT * (RIDGE - Z) / WY
    for px in np.arange(-LX - .65, LX + .66, .45):
        for side in (-1, 1):
            timber(b, H, (px, 0, RIDGE + .02), (px, side * (WY + OUT), eave_z), .05, .07, rng, chamfer=.005)
    for side in (-1, 1):
        for t in np.linspace(.08, .95, 6):
            yy = side * (WY + OUT) * t
            zz = RIDGE + (eave_z - RIDGE) * t + .055
            timber(b, H, (-LX - .7, yy, zz), (LX + .7, yy, zz), .045, .025, rng, chamfer=.003)
    # Bargeboards on the gables.
    for px in (-LX - .72, LX + .72):
        for side in (-1, 1):
            timber(b, P, (px, 0, RIDGE + .1), (px, side * (WY + OUT + .05), eave_z + .04), .22, .03, rng,
                   chamfer=.004, up=(1, 0, 0))
    objs = _finish(b, coll, W, "ep_sala")
    # The tiles: Marseille tiles from the house's roof material, two slopes and a ridge.
    tiles = m["tiles"]
    trng = np.random.default_rng(1936)
    for side in (-1, 1):
        obj = tiled_slope(f"ep_sala_tiles_{'n' if side > 0 else 's'}", coll, -LX - .75, LX + .75,
                          (side * (WY + OUT + .02), eave_z + .1), (0, RIDGE + .12), tiles, trng, missing=.04)
        obj.matrix_world = W
        objs.append(obj)
    r = Batch("ep_sala_ridge")
    for k, px in enumerate(np.arange(-LX - .72, LX + .73, .38)):
        r.lathe(tiles, [(.11, -.2), (.13, 0), (.13, .2), (.11, .22)], xf=Matrix.Translation((px, 0, RIDGE + .19))
                @ Matrix.Rotation(math.pi / 2, 4, "Y"), segments=10, tile=.5, cap=False,
                radial=lambda a, h: 1.0 if math.sin(a) > -.2 else .3)
    objs += _finish(r, coll, W, "ep_sala_ridge")
    _col(coll, "ep_sala_floor", W, -LX - .15, LX + .15, -WY - .1, WY + .1, 0, F)
    _col(coll, "ep_sala_rail_n", W, -LX, LX, WY - .05, WY + .05, F, F + .95)
    _col(coll, "ep_sala_rail_w", W, -LX - .05, -LX + .05, -WY, WY, F, F + .95)
    _col(coll, "ep_sala_rail_e", W, LX - .05, LX + .05, -WY, WY, F, F + .95)
    return objs, W, base, F


# ======================================================================= the pond


def lotus(coll, m, lm, ground, rng):
    """Pads in drifts, a few closed buds, last season's seed heads gone over."""
    cx, cy, rx, ry, turn = L.EAST_POND["water"]
    b = Batch("ep_lotus")
    drifts = [(rng.uniform(-.7, .7), rng.uniform(-.6, .6), rng.uniform(1.0, 2.6)) for _ in range(7)]

    def pond_xy(u, v):
        c, s = math.cos(turn), math.sin(turn)
        return cx + u * rx * c - v * ry * s, cy + u * rx * s + v * ry * c

    pads = []
    for du, dv, spread in drifts:
        for _ in range(int(spread * 16)):
            u, v = du + rng.normal(0, spread / rx), dv + rng.normal(0, spread / ry)
            if u * u + v * v > .82:
                continue
            x, y = pond_xy(u, v)
            if any(math.hypot(x - a, y - c) < (rr + .12) for a, c, rr in pads):
                continue
            rr = rng.uniform(.18, .38)
            pads.append((x, y, rr))
    for k, (x, y, rr) in enumerate(pads):
        dead = rng.random() < .22
        mat = lm["lotus_dead"] if dead else lm["lotus_pad"]
        notch = rng.uniform(0, math.tau)
        verts, faces, uvs = [(x, y, WATER + .012)], [], [(.5, .5)]
        n = 20
        curl = rng.uniform(.03, .1) if dead else rng.uniform(0, .02)
        for ring, f in ((1, .55), (2, 1.0)):
            for i in range(n + 1):
                a = notch + .12 + (math.tau - .24) * i / n
                rad = rr * f * (1 + .03 * math.sin(a * 7 + k))
                z = WATER + .012 + (curl * (f ** 2) + .008 * math.sin(a * 5 + k)) * (1 if ring == 2 else .3)
                verts.append((x + math.cos(a) * rad, y + math.sin(a) * rad, z))
                uvs.append((.5 + math.cos(a) * f * .5, .5 + math.sin(a) * f * .5))
        for i in range(n):
            faces.append((0, 1 + i, 2 + i))
            a0, b0 = 1 + i, 1 + (n + 1) + i
            faces.append((a0, b0, b0 + 1, a0 + 1))
        b.add(mat, verts, faces, uvs, smooth=True)
    # Stalks: closed buds standing, dry seed heads bowed over.
    for k in range(26):
        x, y, rr = pads[int(rng.integers(len(pads)))]
        x += rng.normal(0, .25)
        y += rng.normal(0, .25)
        seed = k % 3 != 0
        h = rng.uniform(.5, 1.0)
        bend = rng.uniform(.15, .45) if seed else rng.uniform(0, .08)
        a = rng.uniform(0, math.tau)
        pts = [Vector((x + math.cos(a) * bend * t ** 2.2, y + math.sin(a) * bend * t ** 2.2,
                       WATER - .1 + h * (t - bend * .6 * t ** 3))) for t in np.linspace(0, 1, 8)]
        b.tube(lm["stem"] or m["bark"], pts, [.007, .007, .006, .006, .0055, .005, .005, .005], sides=5, tile=.5)
        tip = pts[-1]
        d = (pts[-1] - pts[-2]).normalized()
        q = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        if seed:
            # The seed head: a flat-topped cone, face down, holes gone black.
            b.lathe(lm["seed_head"], [(.012, 0), (.04, .025), (.055, .05), (.055, .056), (0, .058)],
                    xf=Matrix.Translation(tip) @ q, segments=12, tile=.2)
        else:
            b.lathe(lm["lotus_bud"] or m["bark"], [(.006, 0), (.03, .025), (.034, .055), (.02, .09), (0, .11)],
                    xf=Matrix.Translation(tip) @ q, segments=10, tile=.2)
    return list(b.build(coll).values())


def reeds(coll, ground, rng):
    """Reeds and sedge round the banks: thick on the east and south, thin by the jetty and sala."""
    from forest_detail import grass_geometry
    cx, cy, rx, ry, turn = L.EAST_POND["water"]
    spots = []
    jx, jy, _ = L.EAST_POND["jetty"]
    sx, sy, _ = L.EAST_POND["sala"]
    for _ in range(2600):
        a = rng.uniform(0, math.tau)
        k = rng.uniform(.9, 1.28)
        u, v = math.cos(a) * rx * k, math.sin(a) * ry * k
        x = cx + u * math.cos(turn) - v * math.sin(turn)
        y = cy + u * math.sin(turn) + v * math.cos(turn)
        thick = .35 + .65 * max(0, math.cos(a - .3))  # east side thickest
        if math.hypot(x - jx, y - jy) < 2.0 or math.hypot(x - sx, y - sy) < 3.4 or L.lane_distance(x, y) < 1.0:
            continue
        if rng.random() > thick:
            continue
        spots.append((x, y, max(ground(x, y), WATER - .05)))
    return grass_geometry("ep_reeds", coll, spots, rng, size=(.7, 1.5))


def dugout(coll, m, ground, rng):
    """A dugout boat (ទូក) swamped at the south bank, its stern under water."""
    b = Batch("ep_dugout")
    cx, cy, rx, ry, turn = L.EAST_POND["water"]
    x, y = cx - 1.5, cy - ry * .92
    M = Matrix.Translation((x, y, WATER - .12)) @ Matrix.Rotation(turn + .35, 4, "Z") @ Matrix.Rotation(.1, 4, "Y") \
        @ Matrix.Rotation(-.12, 4, "X")
    L_, B, D = 4.6, .62, .38

    def hull(u, v):
        t = u * 2 - 1
        half = B / 2 * (1 - abs(t) ** 2.6)
        ang = math.pi * (v - .5) * 1.7
        y0 = math.sin(ang) * half
        z0 = (1 - math.cos(ang)) * D * .55 - D * .1 + .12 * abs(t) ** 3
        rim = abs(ang) > 1.3
        return M @ Vector((t * L_ / 2, y0, z0 + (.02 if rim else 0)))

    b.grid(m["hewn"], hull, 40, 10, uv=lambda u, v: (u * L_ / 1.4, v * 1.2 / 1.4))
    b.grid(m["hewn"], lambda u, v: hull(u, v) + (M.to_3x3() @ Vector((0, 0, .045))), 40, 10,
           uv=lambda u, v: (u * L_ / 1.4, v * 1.2 / 1.4))
    return list(b.build(coll).values())


def shore_walls(coll, segments=72, r=1.24):
    """The game's ground is flat under the water: walls along the shore keep Sora
    out of the pond except along the jetty (its own side walls take over there)."""
    cx, cy, rx, ry, turn = L.EAST_POND["water"]
    jx, jy, _ = L.EAST_POND["jetty"]
    c, s = math.cos(turn), math.sin(turn)
    pts = []
    for i in range(segments + 1):
        a = math.tau * i / segments
        u, v = math.cos(a) * rx * r, math.sin(a) * ry * r
        pts.append((cx + u * c - v * s, cy + u * s + v * c))
    walls = []
    for k, (a, b) in enumerate(zip(pts, pts[1:])):
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if abs(my - jy) < .75 and mx < jx + 2.5:
            continue  # the jetty's root
        pad = .12
        walls.append(collider(f"ep_shore_{k}", coll, min(a[0], b[0]) - pad, max(a[0], b[0]) + pad,
                              min(a[1], b[1]) - pad, max(a[1], b[1]) + pad, -.3, 1.2, surface="mud"))
    return walls


def build(coll, ground, rng=None):
    rng = rng or np.random.default_rng(1931)
    m = dict(materials())
    m["stone"] = bpy.data.materials.get("M_neakta_laterite") or m["hewn"]
    roof = bpy.data.objects.get("roof_s_tiles")
    m["tiles"] = roof.data.materials[0] if roof else m["boards"]
    lm = lotus_materials()
    water = bpy.data.materials.get("M_flood_water")
    objs = [VE.pond_water(coll, water)]
    shore_walls(coll)
    j, JW, deck, LEN = jetty(coll, m, ground, rng)
    objs += j
    s, SW, sbase, F = sala(coll, m, ground, rng)
    objs += s
    objs += lotus(coll, m, lm, ground, rng)
    objs += reeds(coll, ground, rng)
    objs += dugout(coll, m, ground, rng)
    # The pond's spirit (PondSpirit.ts shows and hides it): at the end of the jetty,
    # her back to the shore, looking out over the water.
    p = JW @ Vector((LEN + 1.15, -.1, 0))
    spirit = place_model(coll, "blood_stained_spirit", p.x, p.y, ground, rot=L.EAST_POND["jetty"][2] + .08, scan=True,
                         z=deck + .045, name="pond_spirit")
    spirit["haunt"] = "pond"
    # On the jetty's end: a bucket and one sandal. On the bank: jars.
    p = JW @ Vector((LEN + .9, .45, 0))
    place_model(coll, "wooden_bucket_01", p.x, p.y, ground, rot=.7, z=deck + .055, name="ep_bucket")
    sandal = bpy.data.objects.get("sandal_0")
    if sandal is not None:
        d = sandal.copy()
        coll.objects.link(d)
        d.name = "ep_sandal"
        q = JW @ Vector((LEN + 1.35, -.35, 0))
        low = min((sandal.matrix_world @ v.co).z for v in sandal.data.vertices)
        c = sandal.matrix_world.translation
        d.matrix_world = Matrix.Translation((q.x - c.x, q.y - c.y, deck + .056 - low)) @ sandal.matrix_world
    for k, (u, v, model) in enumerate([(-.9, -1.0, "water_jar"), (-1.3, -.2, "jar_plain"), (-1.0, 1.0, "jar_handles")]):
        p = JW @ Vector((u, v, 0))
        place_model(coll, model, p.x, p.y, ground, rot=rng.uniform(0, math.tau), scan=True, name=f"ep_{model}_{k}")
    # In the sala: a rolled mat on the bench, a water jar, a tea set on the boards.
    for u, v, model, scan, rot, tilt, zoff in [(1.2, 1.25, "straw_mat", True, 0.0, (0, 0), .42),
                                              (-1.7, 1.0, "water_jar", True, .4, (0, 0), 0),
                                              (.1, .4, "tea_set_01", False, .9, (0, 0), 0)]:
        p = SW @ Vector((u, v, 0))
        place_model(coll, model, p.x, p.y, ground, rot=rot, scan=scan, tilt=tilt, z=sbase + F + .02 + zoff,
                    name=f"ep_sala_{model}")
    return objs
