"""The old family yard west of the compound (Episode 1 village expansion, November
2026): where the family lived before the teak house was built in 1932.

- The first house: a small Khmer house of about 1900 on hewn posts, walls of
  split bamboo in light frames, a steep roof of grass thatch. Abandoned for a
  generation: its east end has fallen in, the ridge snapped and the thatch
  slumped through the floor; the rest still stands, rotten and full of holes.
- The rice granary (ជង្រុក): a plank store on six posts, an upturned clay pot on
  each post against rats, a little door high in the gable and a notched log to
  climb to it. Its door hangs open; husks have run out on the ground.
- The buffalo byre (ក្រោលក្របី): a pen of forest poles lashed with rattan, half
  under a lean-to of thatch, the mud inside gone hard, a hollowed log trough, a
  yoke on the rail, the plough against a post and the cold heap of the smudge
  fire that kept the mosquitoes off the animals at night.
- The foot-driven rice pounder and the cooking things under the old house, jars,
  firewood, a fallen bamboo fence and the old ox cart. (`straw_stack` is kept
  but not placed: in the renders it read as a boulder.)

Blender axes, metres. Each building is built in its own frame (x along its
length) and set on the ground where village_layout.WEST_YARD puts it.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

import village_layout as L
from kit import collider, empty
from rural_kit import lashing, log, materials, place_model, ridge_roll, slat_panel, thatch, tile_of, timber
from shrine_craft import Batch


def _frame(x, y, rot, ground, footprint):
    """Placement matrix: the building's floor datum is the lowest ground under its footprint."""
    W = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(rot, 4, "Z")
    pts = [(W @ Vector((u, v, 0))) for u, v in footprint]
    base = min(ground(p.x, p.y) for p in pts)
    W = Matrix.Translation((x, y, base)) @ Matrix.Rotation(rot, 4, "Z")
    return W, base


def _local_ground(W, base, ground):
    def f(u, v):
        p = W @ Vector((u, v, 0))
        return ground(p.x, p.y) - base
    return f


def _finish(batch, coll, W, prefix):
    objs = batch.build(coll, prefix=prefix)
    for o in objs.values():
        o.matrix_world = W
    return list(objs.values())


def _col(coll, name, W, x0, x1, y0, y1, z0, z1, surface="teak"):
    """A collider box from local corners (axis-aligned in world after placement)."""
    pts = [W @ Vector((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    xs, ys, zs = [p.x for p in pts], [p.y for p in pts], [p.z for p in pts]
    return collider(name, coll, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), surface=surface)


# ======================================================================= house


def first_house(coll, m, ground, rng):
    x, y, rot = L.WEST_YARD["house"]
    LX, WY = 3.6, 2.3
    F, Z, RIDGE = 1.95, 3.8, 6.25
    OUT = .8
    W, base = _frame(x, y, rot, ground, [(-LX, -WY), (LX, -WY), (LX, WY), (-LX, WY)])
    g = _local_ground(W, base, ground)
    b = Batch("wy_house")
    T, H, P, B, BA = m["thatch"], m["hewn"], m["planks"], m["bamboo"], m["bark"]
    eave_z = Z - OUT * (RIDGE - Z) / WY

    def post(px, py, top, w=.17, lean=(0, 0), broken=None):
        foot = Vector((px, py, g(px, py) - .35))
        head = Vector((px + lean[0], py + lean[1], top))
        if broken:
            # Snapped: the stump stands, the rest lies where it fell.
            cut = foot + (head - foot) * broken[0]
            timber(b, H, foot, cut, w, w, rng, jitter=.006)
            fall = Vector(broken[1])
            timber(b, H, Vector((fall.x, fall.y, g(fall.x, fall.y) + w * .45)),
                   Vector((fall.x + broken[2][0], fall.y + broken[2][1], g(fall.x + broken[2][0], fall.y + broken[2][1]) + w * .5)),
                   w, w, rng, twist=.3)
            return cut
        timber(b, H, foot, head, w, w, rng, jitter=.006)
        return head

    # --- posts: two wall rows, king posts at the gables, floor posts down the middle.
    xs = (-LX, -1.2, 1.2, LX)
    for px in xs:
        for py in (-WY, WY):
            if px == LX and py == WY:
                post(px, py, Z, broken=(.42, (px + .5, py + .9), (1.4, 1.6)))
            elif px == LX and py == -WY:
                post(px, py, Z - .15, lean=(.35, -.2))
            else:
                post(px, py, Z)
    post(-LX, 0, RIDGE, w=.19)
    post(LX, 0, Z + .55, w=.19, lean=(-.5, .1))
    for px in (-1.2, 1.2):
        post(px, 0, F - .2, w=.16)

    # --- floor: girders on the posts, joists across, boards along; the east end gone.
    for py in (-WY, 0, WY):
        x1 = 1.9 if py == WY else LX + .2
        drop = -.55 if py == WY else 0
        timber(b, H, (-LX - .2, py, F - .22), (x1, py, F - .22 + drop), .14, .16, rng)
    for jx in np.arange(-LX + .15, LX, .62):
        if jx > 2.2 and rng.random() < .6:
            continue
        sag = -.35 * max(0, (jx - 1.6) / 2.0)
        timber(b, H, (jx, -WY - .1, F - .1), (jx, WY + .1, F - .1 + sag), .08, .1, rng)
    boards = np.arange(-WY + .1, WY, .21)
    for k, by in enumerate(boards):
        x0, x1 = -LX - .05, LX + .05
        if rng.random() < .12:
            continue  # rotted through
        if by > .6:
            x1 = 1.5 + rng.uniform(-.3, .5)  # the north-east corner fell in
        sag = 0
        timber(b, P, (x0, by, F - .02), (x1, by, F - .02 + sag), .19, .025, rng, chamfer=.004, jitter=.003)
    # Boards that fell with the corner: hanging from the edge to the ground.
    for k in range(5):
        by = .9 + k * .28
        top = Vector((1.5 + rng.uniform(-.2, .3), by, F - .05))
        foot = Vector((2.4 + rng.uniform(0, .8), by + rng.uniform(-.2, .2), 0))
        foot.z = g(foot.x, foot.y) + .02
        timber(b, P, top, foot, .19, .025, rng, chamfer=.004, twist=rng.uniform(-.3, .3))

    # --- wall plates, ridge and the frame of the roof.
    timber(b, H, (-LX - .3, -WY, Z), (1.25, -WY, Z - .03), .13, .13, rng)
    timber(b, H, (1.25, -WY, Z - .03), (3.85, -WY - .2, Z - .75), .13, .13, rng, twist=.15)
    timber(b, H, (-LX - .3, WY, Z), (1.4, WY, Z - .08), .13, .13, rng)
    timber(b, H, (1.4, WY, Z - .08), (3.1, WY + .6, g(3.1, WY + .6) + .1), .13, .13, rng, twist=.4)  # fallen end
    timber(b, H, (-LX - .55, 0, RIDGE + .05), (1.1, 0, RIDGE - .05), .14, .14, rng)
    # The ridge snapped by the king post; its east half rests on the floor's broken edge.
    timber(b, H, (1.1, .05, RIDGE - .15), (3.3, .4, F - .2), .14, .14, rng, twist=.2)

    def rafter(rx, side, top_z=RIDGE, end=None):
        a = Vector((rx, 0, top_z + .02))
        c = Vector((rx, side * (WY + OUT), eave_z)) if end is None else Vector(end)
        log(b, BA, a, c, .045, .035, rng, sides=6, bow=.01, knots=.05)

    for rx in np.arange(-LX - .3, LX + .25, .6):
        for side in (-1, 1):
            if rx < 1.0:
                rafter(rx, side)
            elif side == 1 and rx < 2.4:
                # Northern rafters hang from the broken ridge, ends on the floor.
                rafter(rx, side, top_z=RIDGE - .5 - (rx - 1.0), end=(rx + .2, WY + .2, F + rng.uniform(-.3, .2)))
            elif side == -1 and rx < 2.0:
                rafter(rx, side, top_z=RIDGE - .2 - (rx - 1.0) * .7)
            elif rng.random() < .5:
                # Fallen rafters lying across the floor and the ground.
                a = Vector((rx + rng.uniform(-.3, .3), rng.uniform(-1.5, 1.5), F + .03))
                c = a + Vector((rng.uniform(-.6, .6), side * rng.uniform(1.4, 2.4), 0))
                c.z = max(F + .03, g(c.x, c.y) + .03) if abs(c.y) < WY else g(c.x, c.y) + .03
                log(b, BA, a, c, .04, .032, rng, sides=6)
    # Purlins (battens) under the thatch on the standing slopes.
    for side in (-1, 1):
        for t in (.22, .5, .78):
            yy = side * (WY + OUT) * t
            zz = RIDGE + (eave_z - RIDGE) * t - .05
            x_end = .9 if side == -1 else 1.3
            log(b, BA, (-LX - .35, yy, zz), (x_end, yy, zz - .02), .03, .028, rng, sides=5, bow=.005)
            lashing(b, m["rattan"], (-1.2, yy, zz), (1, 0, 0), .032, turns=3)

    # --- thatch: the west of both slopes still on, rotted through in places; the east fallen.
    noise = rng.uniform(0, 100, 3)
    span = (LX + .55) * 2

    def torn(limit):
        """The broken edge where the slope stops, raggedly (a smooth tear, not cells)."""
        return lambda v: (0.0, limit + .05 * math.sin(v * 11 + noise[0]) + .03 * math.sin(v * 29 + noise[1])
                          + .015 * math.sin(v * 71 + noise[2]))

    for side, east, rot in ((-1, 1.0, .35), (1, 1.5, .45)):
        r0, r1 = (-LX - .55, 0, RIDGE + .12), (LX + .55, 0, RIDGE + .12)
        e0, e1 = (-LX - .55, side * (WY + OUT), eave_z + .08), (LX + .55, side * (WY + OUT), eave_z + .08)
        thatch(b, T, r0, r1, e0, e1, rng, thick=.18, sag=.07, extent=torn((east + LX + .55) / span), ragged=.2,
               under=m["thatch_dark"], rot=rot, cell=(.16, .12))
    # The north-east quarter slid off inwards: its ridge edge came down on the floor,
    # its eave edge on the ground outside the north wall; it lies there like a ramp.
    thatch(b, m["thatch_dark"], (1.35, .35, F + .12), (3.7, .55, F - .1),
           (1.3, WY + 1.55, g(1.3, WY + 1.55) + .12), (3.9, WY + 1.4, g(3.9, WY + 1.4) + .1),
           rng, thick=.16, sag=.12, ragged=.25, rot=.55, cell=(.22, .17),
           droop=lambda u, v: (0, 0, -.25 * math.sin(math.pi * v) * math.sin(math.pi * u)))
    # The south-east quarter still hangs from the broken ridge, twisted and sagging
    # to the east, most of its straw gone.
    thatch(b, m["thatch_dark"], (1.0, .02, RIDGE - .1), (3.4, .35, F + .55),
           (1.05, -WY - OUT + .1, eave_z + .05), (3.9, -WY - .5, 1.25),
           rng, thick=.15, sag=.2, ragged=.3, rot=.75, cell=(.22, .17),
           droop=lambda u, v: (0, 0, -.6 * math.sin(math.pi * u) * math.sin(math.pi * v)))
    # Fallen straw in drifts round the east end.
    for k in range(9):
        cx, cy = LX + rng.uniform(-1.2, 1.4), rng.uniform(-WY - 1.0, WY + 1.4)
        a = rng.uniform(0, math.tau)
        d = Vector((math.cos(a), math.sin(a), 0))
        nrm = Vector((-d.y, d.x, 0))
        size = rng.uniform(.5, 1.0)
        z0 = g(cx, cy) + .02 if abs(cy) > WY or cx > LX - .2 else F + .01
        thatch(b, m["thatch_dark"], Vector((cx, cy, z0 + .08)) - d * size, Vector((cx, cy, z0 + .08)) + d * size,
               Vector((cx, cy, z0)) - d * size + nrm * size * .8, Vector((cx, cy, z0)) + d * size + nrm * size * .8,
               rng, thick=.07, sag=-.05, ragged=.15, course=1.0, rot=.3, cell=(.25, .2), strands=.5)
    ridge_roll(b, m["thatch_dark"], (-LX - .55, 0, RIDGE + .21), (.85, 0, RIDGE + .15), .14, rng)

    # --- walls: split bamboo panels in frames; the south front, north back, west gable.
    def wall(x0, x1, py, gaps=None, missing=()):
        segs = list(zip(xs[:-1], xs[1:]))
        for (a, c) in segs:
            if a < x0 - .01 or c > x1 + .01 or (a, c) in missing:
                continue
            face_out = -1 if py < 0 else 1
            origin = (a + .09, py + face_out * .02, F + .02) if py < 0 else (c - .09, py + face_out * .02, F + .02)
            along = (1, 0, 0) if py < 0 else (-1, 0, 0)
            slat_panel(b, B, H, origin, along, (0, 0, 1), (c - a) - .18, Z - F - .14, rng, gaps=gaps)

    rot_mask = lambda seed: (lambda t: math.sin(t * 31 + seed) > .72 or (t > .7 and math.sin(t * 9 + seed) > .2))
    wall(-LX, 1.2, -WY, gaps=rot_mask(noise[0]), missing=((-1.2, 1.2),))  # the doorway bay stays open
    wall(-LX, 1.2, WY, gaps=rot_mask(noise[1]))
    # The doorway bay: a narrow board wall each side of the door frame.
    for (a, c) in ((-1.11, -.55), (.45, 1.11)):
        slat_panel(b, B, H, (a, -WY - .02, F + .02), (1, 0, 0), (0, 0, 1), c - a, Z - F - .14, rng,
                   gaps=lambda t: math.sin(t * 13 + noise[2]) > .85)
    for dx in (-.5, .4):
        timber(b, H, (dx, -WY - .04, F), (dx, -WY - .04, Z - .1), .08, .07, rng)
    timber(b, H, (-.55, -WY - .04, Z - .55), (.45, -WY - .04, Z - .55), .07, .07, rng)
    # The door: one board leaf hanging from its top peg, swung out and dropped at the foot.
    door = Matrix.Translation((-.5, -WY - .06, F + .05)) @ Matrix.Rotation(-1.15, 4, "Z") @ Matrix.Rotation(.08, 4, "Y")
    for k in range(4):
        b.box(P, (.215, .03, 1.45), (.11 + k * .22, 0, .72), xf=door, chamfer=.004, tile=tile_of(P), jitter=.003, rng=rng)
    b.box(H, (.9, .035, .07), (.45, -.03, 1.2), xf=door, chamfer=.006, tile=tile_of(H))
    b.box(H, (.9, .035, .07), (.45, -.03, .25), xf=door, chamfer=.006, tile=tile_of(H))
    # West gable: bamboo below, a thatch triangle above the wall plate.
    slat_panel(b, B, H, (-LX - .02, WY - .09, F + .02), (0, -1, 0), (0, 0, 1), 2 * WY - .18, Z - F - .14, rng,
               gaps=rot_mask(noise[2] + 1))
    for t in np.linspace(-WY + .2, WY - .2, 10):
        hgt = (RIDGE - Z) * (1 - abs(t) / WY) - .05
        b.add(T, [(-LX - .03, t - .2, Z), (-LX - .03, t + .2, Z), (-LX - .03, t + .2, Z + hgt), (-LX - .03, t - .2, Z + hgt)],
              [(0, 1, 2, 3)], [(t / 1.3, 0), ((t + .4) / 1.3, 0), ((t + .4) / 1.3, hgt / 1.3), (t / 1.3, hgt / 1.3)])
    # East wall: gone; two panels lie in the weeds below it.
    for k in range(2):
        cx = LX + .9 + k * .8
        cy = rng.uniform(-1.4, .6)
        lie = Matrix.Translation((cx, cy, g(cx, cy) + .03 + k * .03)) @ Matrix.Rotation(rng.uniform(-.5, .5), 4, "Z") \
            @ Matrix.Rotation(math.pi / 2 - .04, 4, "X")
        p0 = lie @ Vector((-.8, 0, 0))
        slat_panel(b, B, H, p0, (lie.to_3x3() @ Vector((1, 0, 0))), (lie.to_3x3() @ Vector((0, 1, 0))), 1.6, 1.4, rng,
                   gaps=lambda t: math.sin(t * 21 + k) > .6)

    # --- the front ladder-stair: two stringers, treads, two of them gone.
    foot_y = -WY - 1.55
    sz = g(-.05, foot_y)
    for sx in (-.45, .35):
        timber(b, H, (sx, foot_y, sz - .05), (sx, -WY - .05, F), .06, .14, rng)
    for k in range(1, 7):
        if k in (3, 5):
            continue
        t = k / 7
        ty = foot_y + (-WY - .05 - foot_y) * t
        tz = sz + (F - sz) * t
        timber(b, P, (-.52, ty, tz), (.42, ty, tz), .2, .035, rng, chamfer=.004)

    objs = _finish(b, coll, W, "wy_house")
    # Colliders: posts are thin; block the stair and the house's underside as a whole.
    _col(coll, "wy_house_body", W, -LX, 1.4, -WY, WY, F - .25, Z, surface="teak")
    _col(coll, "wy_house_debris", W, 1.4, LX + 1.6, -WY, WY + 1.2, 0, .6, surface="teak")
    for px in xs:
        for py in (-WY, WY):
            _col(coll, f"wy_house_post_{px:+.0f}_{py:+.0f}", W, px - .1, px + .1, py - .1, py + .1, -.3, F)
    return objs, W, base


# ======================================================================= granary


def granary(coll, m, ground, rng):
    x, y, rot = L.WEST_YARD["granary"]
    LX, WY = 1.6, 1.2
    F, Z, RIDGE, OUT = 1.3, 2.95, 4.35, .7
    W, base = _frame(x, y, rot, ground, [(-LX, -WY), (LX, -WY), (LX, WY), (-LX, WY)])
    g = _local_ground(W, base, ground)
    b = Batch("wy_granary")
    T, H, P, BO = m["thatch"], m["hewn"], m["planks"], m["boards"]
    for px in (-LX, 0, LX):
        for py in (-WY, WY):
            timber(b, H, (px, py, g(px, py) - .3), (px, py, F - .18), .17, .17, rng, jitter=.006)
    # The floor frame and boards.
    for py in (-WY, WY):
        timber(b, H, (-LX - .2, py, F - .12), (LX + .2, py, F - .12), .14, .14, rng)
    for px in np.linspace(-LX, LX, 6):
        timber(b, H, (px, -WY - .15, F - .02), (px, WY + .15, F - .02), .08, .08, rng)
    # Walls: tight vertical boards, warped, a few split; a sill and top plate.
    for side in (-1, 1):
        for k, bx in enumerate(np.arange(-LX + .02, LX, .19)):
            hgt = Z - F - .05 - (.25 if rng.random() < .08 else 0)
            lean = rng.normal(0, .008)
            timber(b, P, (bx + .09, side * (WY + .02), F + .04), (bx + .09 + lean, side * (WY + .02), F + .04 + hgt),
                   .185, .03, rng, chamfer=.004, jitter=.003, up=(0, 1, 0))
        timber(b, H, (-LX - .1, side * (WY + .06), Z - .05), (LX + .1, side * (WY + .06), Z - .05), .1, .1, rng)
    door_y = (-.32, .32)
    for side in (-1, 1):
        gx = side * (LX + .02)
        for k, by in enumerate(np.arange(-WY + .02, WY, .19)):
            mid = by + .09
            top = Z - .05 + (RIDGE - Z - .1) * (1 - abs(mid) / (WY + .1))
            bottom = F + .04
            if side == 1 and door_y[0] < mid < door_y[1]:
                timber(b, P, (gx, mid, top - .5), (gx, mid, top), .185, .03, rng, chamfer=.004, up=(1, 0, 0))
                continue
            timber(b, P, (gx, mid, bottom), (gx, mid, top), .185, .03, rng, chamfer=.004, jitter=.003, up=(1, 0, 0))
    # The door, open on its pegs; its sill and the dark inside.
    sill_z = F + .3
    timber(b, H, (LX + .05, door_y[0] - .08, sill_z), (LX + .05, door_y[1] + .08, sill_z), .08, .06, rng)
    dm = Matrix.Translation((LX + .04, door_y[1], sill_z)) @ Matrix.Rotation(1.25, 4, "Z")
    for k in range(3):
        b.box(P, (.2, .03, 1.05), (-.11 - k * .205, 0, .55), xf=dm, chamfer=.004, tile=tile_of(P), jitter=.003, rng=rng)
    b.box(m["void"], (.04, .64, 1.1), (LX - .03, 0, sill_z + .55), tile=1)
    # Roof: grass thatch, whole but for two rotten patches; a ridge roll.
    eave_z = Z - OUT * (RIDGE - Z) / WY
    for side in (-1, 1):
        r0, r1 = (-LX - .55, 0, RIDGE + .1), (LX + .55, 0, RIDGE + .1)
        e0, e1 = (-LX - .55, side * (WY + OUT), eave_z + .06), (LX + .55, side * (WY + OUT), eave_z + .06)
        if side == 1:
            r0, r1, e0, e1 = r1, r0, e1, e0
        thatch(b, T, r0, r1, e0, e1, rng, thick=.17, sag=.05, ragged=.16, under=m["thatch_dark"], rot=.18)
        for rx in np.arange(-LX - .4, LX + .45, .55):
            log(b, m["bark"], (rx, 0, RIDGE), (rx, side * (WY + OUT - .05), eave_z), .035, .03, rng, sides=5)
    ridge_roll(b, m["thatch_dark"], (-LX - .6, 0, RIDGE + .18), (LX + .6, 0, RIDGE + .18), .12, rng)
    timber(b, H, (-LX - .5, 0, RIDGE - .05), (LX + .5, 0, RIDGE - .05), .1, .12, rng)
    # A notched log to climb to the door, leaning on the sill.
    lx0 = LX + 1.05
    log(b, m["bark"], (lx0, .05, g(lx0, .05) - .05), (LX + .12, .02, sill_z + .05), .1, .08, rng, sides=8)
    for k in range(1, 4):
        t = k / 4.4
        p = Vector((lx0 + (LX + .12 - lx0) * t, .05, g(lx0, .05) + (sill_z - g(lx0, .05)) * t))
        b.box(m["hewn"], (.06, .16, .03), tuple(p + Vector((.07, 0, .07))), chamfer=.01, tile=1)
    objs = _finish(b, coll, W, "wy_granary")
    # Rat guards: an old pot upturned on each post, a hole knocked through its base.
    for k, (px, py) in enumerate((px, py) for px in (-LX, 0, LX) for py in (-WY, WY)):
        p = W @ Vector((px, py, 0))
        place_model(coll, "jar_plain", p.x, p.y, ground, rot=rng.uniform(0, math.tau), scan=True, height=.36,
                    tilt=(math.pi, 0.0), z=base + g(px, py) + .72, name=f"wy_granary_ratguard_{k}")
    _col(coll, "wy_granary_body", W, -LX - .1, LX + .1, -WY - .1, WY + .1, F - .2, Z)
    for px in (-LX, 0, LX):
        for py in (-WY, WY):
            _col(coll, f"wy_granary_post_{px:+.0f}_{py:+.0f}", W, px - .25, px + .25, py - .25, py + .25, -.3, F)
    return objs, W, base


# ======================================================================= byre


def byre(coll, m, ground, rng):
    x, y, rot = L.WEST_YARD["byre"]
    LX, WY = 3.0, 2.2
    W, base = _frame(x, y, rot, ground, [(-LX, -WY), (LX, -WY), (LX, WY), (-LX, WY)])
    g = _local_ground(W, base, ground)
    b = Batch("wy_byre")
    BA, T, R = m["bark"], m["thatch"], m["rattan"]
    posts = []
    for px in (-3.0, -1.5, 0.0, 1.5, 3.0):
        for py in (-WY, WY):
            posts.append((px, py))
    for py in (-.75, .75):
        posts += [(-LX, py), (LX, py)]
    roof_hi, roof_lo = 2.45, 1.65
    tops = {}
    for px, py in posts:
        under_roof = px <= .6
        top = (roof_lo + (roof_hi - roof_lo) * (px + 3.4) / 4.0 - .05) if under_roof else 1.35 + rng.uniform(-.05, .1)
        lean = (rng.normal(0, .04), rng.normal(0, .04))
        log(b, BA, (px, py, g(px, py) - .4), (px + lean[0], py + lean[1], top), .1, .085, rng, sides=8)
        tops[(px, py)] = (px + lean[0], py + lean[1], top)
    # Extra roof posts along the high side.
    for py in (-WY, 0, WY):
        log(b, BA, (.6, py, g(.6, py) - .4), (.6, py, roof_hi - .05), .1, .09, rng, sides=8)
    # Rails, lashed at each post; the gate gap on the east end, its poles down.
    for z in (.55, 1.05):
        for side in (-WY, WY):
            log(b, BA, (-LX - .2, side, g(-LX, side) + z), (LX + .2, side, g(LX, side) + z), .055, .045, rng, sides=6, bow=.008)
            for px in (-3.0, -1.5, 0.0, 1.5, 3.0):
                lashing(b, R, (px, side, g(px, side) + z), (1, 0, 0), .095, turns=3)
        log(b, BA, (-LX, -WY - .2, g(-LX, -WY) + z), (-LX, WY + .2, g(-LX, WY) + z), .055, .045, rng, sides=6, bow=.008)
        for py in (-WY - .15, WY + .15):
            log(b, BA, (LX, py, g(LX, py) + z), (LX, py * .35, g(LX, py) + z), .05, .045, rng, sides=6)
    # One gate pole still rests on the stub of the south rail, its other end down in the mud.
    log(b, BA, (LX, -.86, g(LX, -WY) + 1.05 + .095), (LX + .45, .95, g(LX + .45, .95) + .03), .045, .04, rng, sides=6, bow=0)
    log(b, BA, (LX + .6, -1.1, g(LX + .6, -1.1) + .05), (LX + .9, 1.2, g(LX + .9, 1.2) + .05), .045, .04, rng, sides=6)
    # The lean-to roof over the west half.
    r0, r1 = (.85, WY + .5, roof_hi + .12), (.85, -WY - .5, roof_hi + .12)
    e0, e1 = (-LX - .75, WY + .5, roof_lo), (-LX - .75, -WY - .5, roof_lo)
    for py in np.arange(-WY - .4, WY + .5, .6):
        log(b, BA, (.85, py, roof_hi + .02), (-LX - .7, py, roof_lo - .06), .04, .035, rng, sides=5)
    log(b, BA, (.75, -WY - .5, roof_hi - .03), (.75, WY + .5, roof_hi - .03), .07, .065, rng, sides=7)
    log(b, BA, (-LX + .02, -WY - .5, roof_lo + .1), (-LX + .02, WY + .5, roof_lo + .1), .07, .065, rng, sides=7)
    thatch(b, T, r1, r0, e1, e0, rng, thick=.16, sag=.08, ragged=.22, under=m["thatch_dark"], rot=.4)
    # The hollowed log trough on two stones along the west rail.
    tr = Matrix.Translation((-LX + .6, 0, g(-LX + .6, 0) + .32)) @ Matrix.Rotation(math.pi / 2, 4, "X")
    prof = [(.0, -1.1), (.24, -1.1), (.26, -.9), (.27, .9), (.25, 1.1), (.0, 1.1)]
    b.lathe(BA, [(r, h) for r, h in prof], xf=tr, segments=12, tile=1.0,
            radial=lambda a, h: (.55 if math.sin(a) < -.2 else 1.0))
    b.box(m["void"], (.3, 2.0, .02), (-LX + .6, 0, g(-LX + .6, 0) + .38), tile=1)
    for py in (-.7, .7):
        b.box(m["stone"], (.32, .28, .2), (-LX + .6, py, g(-LX + .6, py) + .08), chamfer=.04, tile=.6,
              rough=(.02, 8), rng=rng)
    # The yoke over the north rail; the plough against the corner post.
    yk = Matrix.Translation((-.8, WY + .02, g(-.8, WY) + 1.12)) @ Matrix.Rotation(math.pi / 2, 4, "Z")
    yoke = [Vector((0, t, .12 * (abs(t) / .75) ** 3)) for t in np.linspace(-.8, .8, 12)]
    b.tube(m["hewn"], [yk @ p for p in yoke], .045, sides=6, tile=1.0)
    for t in (-.42, .42):
        for d in (-.12, .12):
            # The neck pegs pass through the yoke, a pair either side of each ox's neck.
            b.tube(m["hewn"], [yk @ Vector((0, t + d, .05)), yk @ Vector((0, t + d, -.3))], .014, sides=5, tile=1.0)
    pl = Matrix.Translation((LX - .1, -WY + .25, g(LX, -WY) + .02)) @ Matrix.Rotation(.6, 4, "Z") @ Matrix.Rotation(-.95, 4, "Y")
    b.tube(m["hewn"], [pl @ Vector((0, 0, 0)), pl @ Vector((1.0, 0, .12)), pl @ Vector((2.1, 0, .55))], .04, sides=6, tile=1)
    b.tube(m["hewn"], [pl @ Vector((.1, 0, 0)), pl @ Vector((-.25, 0, .55)), pl @ Vector((-.35, 0, .9))], .035, sides=6, tile=1)
    b.box(m["iron"], (.22, .08, .03), tuple(pl @ Vector((.12, 0, -.03))), tile=1)
    objs = _finish(b, coll, W, "wy_byre")
    # The pen's floor: hard mud and old straw, dung; a cold smudge-fire heap by the gate.
    floor = Batch("wy_byre_floor")
    nu, nv = 24, 18
    floor.grid(m["mud"], lambda u, v: (-LX + 2 * LX * u, -WY + 2 * WY * v, g(-LX + 2 * LX * u, -WY + 2 * WY * v) + .02),
               nu, nv, uv=lambda u, v: (u * 2 * LX / 2, v * 2 * WY / 2))
    for k in range(70):
        u, v = rng.uniform(-LX + .2, LX - .2), rng.uniform(-WY + .2, WY - .2)
        a = rng.uniform(0, math.tau)
        L0 = rng.uniform(.12, .3)
        p = Vector((u, v, g(u, v) + .02))
        d = Vector((math.cos(a), math.sin(a), 0)) * L0
        n = Vector((-d.y, d.x, 0)).normalized() * .006
        floor.add(m["straw"], [p - d - n, p + d - n, p + d + n, p - d + n], [(0, 1, 2, 3)],
                  [(0, 0), (1, 0), (1, .05), (0, .05)], smooth=False)
    for k in range(9):
        u, v = rng.uniform(-LX + .3, .8), rng.uniform(-WY + .3, WY - .3)
        r = rng.uniform(.08, .14)
        floor.lathe(m["dung"], [(0, .0), (r, 0), (r * .8, .025), (r * .3, .035), (0, .037)],
                    xf=Matrix.Translation((u, v, g(u, v) + .005)), segments=10, tile=.3,
                    radial=lambda a, h, s=rng.uniform(0, 6): 1 + .15 * math.sin(a * 3 + s))
    ax, ay = LX + 1.6, 1.4
    floor.lathe(m["ash"], [(0, 0), (.55, 0), (.45, .05), (.25, .1), (0, .12)], xf=Matrix.Translation((ax, ay, g(ax, ay))),
                segments=16, tile=.5, radial=lambda a, h: 1 + .12 * math.sin(a * 4))
    for k in range(6):
        a = rng.uniform(0, math.tau)
        p = Vector((ax + math.cos(a) * .15, ay + math.sin(a) * .15, g(ax, ay) + .08))
        q = p + Vector((math.cos(a) * .5, math.sin(a) * .5, -.06))
        floor.tube(m["char"], [p, q], .02, sides=5, tile=.3)
    objs += _finish(floor, coll, W, "wy_byre_floor")
    for px, py in posts:
        _col(coll, f"wy_byre_post_{px:+.1f}_{py:+.1f}", W, px - .1, px + .1, py - .1, py + .1, -.2, 1.3)
    _col(coll, "wy_byre_rail_n", W, -LX, LX, WY - .06, WY + .06, 0, 1.15)
    _col(coll, "wy_byre_rail_s", W, -LX, LX, -WY - .06, -WY + .06, 0, 1.15)
    _col(coll, "wy_byre_rail_w", W, -LX - .06, -LX + .06, -WY, WY, 0, 1.15)
    _col(coll, "wy_byre_trough", W, -LX + .3, -LX + .9, -1.1, 1.1, 0, .6)
    return objs, W, base


# ======================================================================= yard


def straw_stack(coll, m, ground, rng, x, y, name="wy_straw_stack"):
    """A rice-straw stack built up round a pole in rings of sheaves, each ring's
    butt ends standing out over the one below, the crown roped; old, slumped to
    one side and gone grey on its weather face."""
    from rural_kit import _straws
    b = Batch(name)
    z0 = ground(x, y)
    rings = 6
    prof = [(1.4, 0.0), (1.55, .4), (1.6, 1.0), (1.5, 1.6), (1.25, 2.15), (.9, 2.6), (.55, 2.95), (.25, 3.15), (.04, 3.25)]

    def radius_at(h):
        for (r0, h0), (r1, h1) in zip(prof, prof[1:]):
            if h <= h1:
                return r0 + (r1 - r0) * (h - h0) / (h1 - h0)
        return prof[-1][0]

    seed = rng.uniform(0, 9, 4)
    lean = Vector((.18, -.1, 0))

    def pt(u, v):
        a = u * math.tau
        h = v * 3.25
        ring = (v * rings) % 1.0
        r = radius_at(h) * (1 + .06 * math.sin(a * 5 + h * 3 + seed[0]) + .03 * math.sin(a * 17 - h * 9 + seed[1])
                            + .015 * math.sin(a * 41 + h * 23 + seed[3]))
        r += .012 * ring * (1 - v)
        r *= 1 + .06 * math.sin(a + seed[2]) * v  # slumped to one side
        return Vector((x + math.cos(a) * r, y + math.sin(a) * r, z0 - .04 + h)) + lean * v * v

    nu, nv = 96, rings * 7
    b.grid(m["straw"], pt, nu, nv, uv=lambda u, v: (u * math.tau * 1.5 / 1.6 + .3 * math.sin(v * 9), v * 3.25 / 1.6 * .9))
    # Loose straws under each ring's butt.
    for k in range(1, rings):
        v = k / rings - .01
        for i in range(110):
            u = rng.random()
            p0, p1 = pt(u, v), pt(u + .004, v)
            out = (p0 - Vector((x, y, p0.z))).normalized()
            _straws(b, m["straw"], p0, p1, p0 - Vector((0, 0, .05)), p1 - Vector((0, 0, .05)), out, Vector((0, 0, 1)),
                    rng, 1.6, hang=True, count=2)
    log(b, m["bark"], (x + lean.x, y + lean.y, z0 + 2.9), (x + lean.x + .06, y + lean.y - .03, z0 + 4.1), .05, .035, rng, sides=6)
    # Pulled straw lying round its foot.
    for k in range(90):
        a = rng.uniform(0, math.tau)
        rr = rng.uniform(1.95, 3.0)
        px, py = x + math.cos(a) * rr, y + math.sin(a) * rr
        d = Vector((math.cos(a + rng.normal(0, .8)), math.sin(a + rng.normal(0, .8)), 0)) * rng.uniform(.12, .3)
        p = Vector((px, py, ground(px, py) + .015))
        nn = Vector((-d.y, d.x, 0)).normalized() * .006
        b.add(m["straw"], [p - d - nn, p + d - nn, p + d + nn, p - d + nn], [(0, 1, 2, 3)], [(0, 0), (.4, 0), (.4, .01), (0, .01)])
    objs = b.build(coll)
    collider(name, coll, x - 1.4, x + 1.4, y - 1.4, y + 1.4, z0, z0 + 2.8, surface="leaves")
    return list(objs.values())


def rice_pounder(coll, m, ground, rng, W, base):
    """The foot-driven rice pounder (ត្បាល់ជាន់) under the old house: a long beam on
    a pivot, the pestle at its head over a hollowed log mortar."""
    b = Batch("wy_pounder")
    g = _local_ground(W, base, ground)
    px, py = -2.4, -.6
    z = g(px, py)
    b.lathe(m["hewn"], [(0, 0), (.24, 0), (.25, .38), (.2, .42), (.12, .4), (.12, .2), (0, .2)],
            xf=Matrix.Translation((px, py, z - .05)), segments=16, tile=.6,
            radial=lambda a, h: 1 + .02 * math.sin(a * 5))
    b.box(m["void"], (.2, .2, .01), (px, py, z + .2), tile=1)
    pivot = Vector((px + 1.7, py, z + .45))
    for d in (-.2, .2):
        timber(b, m["hewn"], (pivot.x, py + d, z - .2), (pivot.x, py + d, pivot.z + .1), .08, .08, rng)
    head = Vector((px, py, z + .75))
    tail = Vector((px + 2.9, py, z + .18))
    timber(b, m["hewn"], head, tail, .12, .12, rng, jitter=.004)
    b.tube(m["hewn"], [head + Vector((0, 0, .05)), head + Vector((0, 0, -.45))], .05, sides=8, tile=1)
    log(b, m["bark"], pivot + Vector((0, -.3, 0)), pivot + Vector((0, .3, 0)), .03, .03, rng, sides=6)
    objs = _finish(b, coll, W, "wy_pounder")
    return objs


def bamboo_fence(coll, m, ground, rng, pts, name):
    """A fallen fence of split bamboo on posts along `pts`: most of it down."""
    b = Batch(name)
    for (ax, ay), (cx, cy) in zip(pts, pts[1:]):
        d = Vector((cx - ax, cy - ay, 0))
        n = int(d.length / 1.4) + 1
        for k in range(n):
            t = k / n
            px, py = ax + d.x * t, ay + d.y * t
            standing = rng.random() < .55
            if standing:
                h = rng.uniform(.6, 1.2)
                lean = Vector((rng.normal(0, .12), rng.normal(0, .12), 0))
                log(b, m["bark"], (px, py, ground(px, py) - .3), Vector((px, py, ground(px, py) + h)) + lean, .045, .04, rng, sides=6)
            if rng.random() < .5:
                # A run of slats, propped or flat in the grass.
                q = Vector((px, py, 0)) + d.normalized() * rng.uniform(.2, .6)
                ang = math.atan2(d.y, d.x) + rng.normal(0, .3)
                along = Vector((math.cos(ang), math.sin(ang), 0))
                up = Vector((0, 0, 1)) if standing and rng.random() < .4 else Vector((-along.y, along.x, 0)) * -1
                tilt = .25 if up.z else 0
                origin = Vector((q.x, q.y, ground(q.x, q.y) + .03))
                upv = (Vector((0, 0, 1)) * (1 - tilt) + Vector((-along.y, along.x, 0)) * tilt).normalized() if up.z else Vector((-along.y, along.x, .02)).normalized()
                slat_panel(b, m["bamboo"], m["bark"], origin, along, upv, rng.uniform(.8, 1.4), rng.uniform(.7, 1.0), rng,
                           gaps=lambda t: math.sin(t * 17 + k) > .5, frame=False)
    return list(b.build(coll).values())


def firewood(coll, m, ground, rng, x, y, rot, name):
    b = Batch(name)
    z = ground(x, y)
    M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, "Z")
    for row in range(4):
        for k in range(7 - row):
            cy = (k - (6 - row) / 2) * .13
            cz = .055 + row * .105
            a = M @ Vector((-.5 + rng.normal(0, .05), cy, cz))
            c = M @ Vector((.5 + rng.normal(0, .05), cy + rng.normal(0, .02), cz + rng.normal(0, .01)))
            log(b, m["bark"], a, c, .06, .055, rng, sides=7, bow=.01, rows=3)
    return list(b.build(coll).values())


def _copy_tree(coll, root_name, dx, dy, rot, ground, about, name):
    """Linked copies of an existing village object tree (the yard cart, a banana
    clump), moved to (dx, dy), turned by `rot` about `about`, set on the ground."""
    src = bpy.data.objects.get(root_name)
    if src is None:
        return []
    out = []

    def copy(o, parent):
        d = o.copy()
        d.name = f"{name}_{o.name}"
        coll.objects.link(d)
        d.parent = parent
        out.append(d)
        for c in o.children:
            copy(c, d)
        return d

    top = copy(src, None)
    ax, ay = about
    old = Vector(src.matrix_world.translation)
    M = Matrix.Translation((dx, dy, 0)) @ Matrix.Rotation(rot, 4, "Z") @ Matrix.Translation((-ax, -ay, 0))
    top.matrix_world = M @ src.matrix_world
    top.location.z += ground(dx, dy) - ground_old(ax, ay)
    return out


def ground_old(x, y):
    """Height of the pre-expansion ground (the cart's old spot is inside it)."""
    import village_expansion as VE
    return VE.Ground()(x, y)


def yard_dressing(coll, m, ground, rng, HW):
    """The life the family left: the ox cart, cooking under the house, baskets and
    mats, a felled log and stumps."""
    objs = []
    cx, cy, crot = L.WEST_YARD["cart"]
    objs += _copy_tree(coll, "yard_cart", cx, cy, crot - math.radians(-70), ground, (10.6, 19.6), "wy_cart")
    # Cooking under the house's west end: the clay stove, its ash, a pot and a kettle.
    for u, v, model, rot, tilt in [(-1.6, 1.0, "clay_stove", .3, (0, 0)), (-1.1, 1.3, "cooking_pot", 1.2, (0, 0)),
                                   (-2.0, .55, "kettle", 2.0, (0, 0)), (-.2, -.9, "winnowing_tray", .4, (1.35, 0)),
                                   (.6, 1.8, "broom", 0.0, (1.5, .1)), (1.0, .2, "straw_mat", .2, (0, 0)),
                                   (-3.4, .3, "basket_deep", .5, (0, 0))]:
        p = HW @ Vector((u, v, 0))
        place_model(coll, model, p.x, p.y, ground, rot=rot + rng.normal(0, .2), scan=True, tilt=tilt, name=f"wy_{model}_under")
    # Logs and stumps: an old felled trunk by the fence, two stumps, mossy stones.
    for model, x, y, rot, s in [("dead_tree_trunk", -51.5, 12.0, .9, 1.0), ("tree_stump_01", -39.0, 25.5, 0, 1.0),
                                ("tree_stump_02", -48.5, 15.2, 1.4, .9)]:
        place_model(coll, model, x, y, ground, rot=rot, scale=s, sink=.04, name=f"wy_{model}")
    return objs


def build(coll, ground, rng=None):
    """The whole west yard into `coll`. Returns (objects, lamp points for previews)."""
    rng = rng or np.random.default_rng(1900)
    m = dict(materials())
    m["stone"] = bpy.data.materials.get("M_neakta_laterite") or m["hewn"]
    m["char"] = m["void"]
    objs = []
    h, HW, hbase = first_house(coll, m, ground, rng)
    objs += h
    objs += granary(coll, m, ground, rng)[0]
    objs += byre(coll, m, ground, rng)[0]
    objs += rice_pounder(coll, m, ground, rng, HW, hbase)
    # (The rice-straw stack read as a boulder in the renders; left out for now.)
    gx, gy, _ = L.WEST_YARD["granary"]
    objs += firewood(coll, m, ground, rng, gx - 2.6, gy - 2.4, .4, "wy_firewood")
    objs += bamboo_fence(coll, m, ground, rng, [(-55.5, 9.0), (-56.0, 17.0), (-53.5, 26.5), (-46.0, 29.5)], "wy_fence")
    # Water jars and baskets under the old house; a jar by the granary.
    hx, hy, hr = L.WEST_YARD["house"]
    for k, (u, v, model, s) in enumerate([(-3.0, 1.6, "jar_handles", 1.15), (-2.2, 1.9, "jar_plain", 1.0),
                                          (-1.5, 1.5, "jar_handles", .95), (.3, 1.4, "basket_deep", 1.0),
                                          (-3.2, -1.2, "basket_round", 1.0), (-.6, .9, "rice_sack", 1.0)]):
        p = HW @ Vector((u, v, 0))
        place_model(coll, model, p.x, p.y, ground, rot=rng.uniform(0, math.tau), scale=s, scan=True,
                    tilt=((.0, .0) if k != 4 else (1.2, .2)), name=f"wy_{model}_{k}")
    p = Vector((gx + 2.2, gy + 1.3, 0))
    place_model(coll, "jar_plain", p.x, p.y, ground, rot=1.1, scan=True, scale=1.2, name="wy_jar_granary")
    objs += yard_dressing(coll, m, ground, rng, HW)
    # The old tree's skirt of litter is the forest's; keep its foot clear for colliders.
    return objs
