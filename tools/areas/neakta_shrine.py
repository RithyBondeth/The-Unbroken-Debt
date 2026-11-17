"""The Neak Ta shrine under the banyan (Episode 1, 2026-11 redesign).

An old village shrine of soft brick and lime on a laterite-footed platform, a
Marseille-tile roof on teak rafters, open to the east. The banyan has grown
over it: its aerial roots come down over the back wall and grip the bricks.
Inside, on a smoke-black altar of two steps, the Neak Ta sits as a painted
wooden guardian on his throne, black-faced, bearded, a sword in his hand: the
Maritime Asia Heritage Survey's scan "Seated Shrine Figure with Sword,
Thailand" (CC BY-NC-ND 4.0, art-source/library/scans/seated_shrine.glb),
decimated only. Beside him, bare split field stones with old wax on them. On
the platform's lip, beeswax candles burnt down into their own wax, joss sticks
in a pot of stubs, leaf cups of rice and betel, bananas going black, a coconut.

The figure is the watcher of Apparitions.ts (`neakta_stone_watch`): one object,
pivot at its feet, `front` extra = facing - pi/2, as before. Cultural details
are advisor-review items (Cultural Guide).

Local frame: x across the front (north when facing pi/2), y back toward the
banyan, z up; the front is -y. Run inside Blender.
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, noise

import offerings_kit as kit
import shrine_surfaces as surf
from kit import LIB
from shrine_craft import Batch, place

PLATFORM = .34
W, D = 1.1, .8          # half width and half depth of the platform
WALL_TOP = 1.62
EAVE_X, EAVE_Z, RIDGE_Z = 1.2, 1.72, 2.3
ROOF_Y = .98

FIGURE = os.path.join(LIB, "scans", "seated_shrine.glb")

_mats = {}


def materials():
    if _mats:
        return _mats
    _mats.update(kit.materials())
    m = _mats
    m["lime"] = surf.limewash_brick()
    m["brick"] = surf.old_brick()
    m["laterite"] = surf.laterite("neakta_laterite", seed=2630, tile=.6, moss=1.0)
    m["stone"] = surf.sandstone()
    m["timber"] = bpy.data.materials.get("M_phra_phum_grey_teak") or surf.grey_teak()
    m["red"] = surf.cotton("neakta_red_cloth", (.36, .045, .035), 2631)
    m["white"] = surf.cotton("neakta_white_cloth", (.56, .53, .45), 2632, dirt=.9)
    m["bark"] = bpy.data.materials.get("M_wet_bark") or surf.plain("M_wet_bark", (.12, .1, .08), rough=.9)
    tc = bpy.data.materials.get("M_ep1_colonial_terracotta")
    if tc is None:
        from colonial_materials import terracotta
        tc = terracotta("T_ep1_colonial_terracotta", 1937)
    m["tile"] = tc
    m["bottle"] = surf.plain("M_neakta_bottle_glass", (.05, .09, .05), rough=.15)
    m["hair"] = surf.plain("M_neakta_hair", (.012, .011, .01), rough=.6)
    m["iron"] = surf.plain("M_neakta_rusted_iron", (.11, .06, .03), rough=.85, metal=.3)
    m["rope"] = surf.plain("M_neakta_coir_string", (.22, .16, .09), rough=1.0)
    return m


# ------------------------------------------------------------------ the figure


def _apply(obj, mod):
    with bpy.context.temp_override(object=obj, active_object=obj):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def boulder(b, mat, centre, size, rng, tile=.4):
    """A field stone: a lumpy, flattened ball."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1)
    seed = Vector(rng.uniform(0, 40, 3))
    verts, uvs = [], []
    for v in bm.verts:
        n = v.co.normalized()
        k = 1 + .28 * noise.noise(n * 1.1 + seed) + .1 * noise.noise(n * 3.2 + seed) + .03 * noise.noise(n * 9 + seed)
        # Flat broken faces: the stone was split.
        for plane in ((.8, .3, .2), (-.4, .7, .1)):
            dist = n.dot(Vector(plane).normalized())
            if dist > .55:
                k = min(k, .55 / max(dist, .01) * 1.05)
        p = Vector((n.x * size[0], n.y * size[1], n.z * size[2])) * k
        p.z = max(p.z, -size[2] * .55)
        verts.append(tuple(Vector(centre) + p))
        uvs.append(((p.x + p.y) / tile, p.z / tile))
    faces = [tuple(v.index for v in f.verts) for f in bm.faces]
    bm.free()
    b.add(mat, verts, faces, uvs, smooth=True)
    from mathutils.bvhtree import BVHTree
    return BVHTree.FromPolygons([Vector(v) for v in verts], faces)


def seated_figure(coll, path, height):
    """A scanned shrine figure (a painted wooden guardian on his throne):
    joined, decimated keeping its UVs and photographed paint, feet at the origin,
    facing -y."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    bpy.context.view_layer.update()
    for o in meshes:
        o.data.transform(o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
        o.parent = None
    names = [o.name for o in new if o.type != "MESH"]
    from khmer import join
    obj = join(meshes, "neakta_stone_watch")
    for name in names:
        if name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    mod = obj.modifiers.new("decimate", "DECIMATE")
    mod.ratio = 40000 / max(1, len(obj.data.polygons))
    _apply(obj, mod)
    co = np.array([v.co[:] for v in obj.data.vertices])
    lo, hi = co.min(axis=0), co.max(axis=0)
    obj.data.transform(Matrix.Scale(height / (hi[2] - lo[2]), 4)
                       @ Matrix.Translation((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2])))
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def watcher(coll, m, foot, facing, rng, height=.68, figure=None):
    """The Neak Ta figure as one object, pivot at its feet (Apparitions.ts)."""
    obj = seated_figure(coll, figure or FIGURE, height)
    # Bake the placement: the mesh faces its shrine's front, the object sits at the foot.
    obj.data.transform(Matrix.Rotation(facing, 4, "Z"))
    obj.matrix_world = Matrix.Translation(foot)
    obj["front"] = facing - math.pi / 2
    return obj


# ------------------------------------------------------------------- shelter


def _platform(b, m, rng):
    # Brick core, laterite footing and a laterite step.
    b.box(m["brick"], (2 * W, 2 * D, PLATFORM - .1), (0, 0, .1 + (PLATFORM - .1) / 2 - .012), tile=1.0, grain=False)
    y = -D - .03
    x = -W - .03
    for side in range(4):
        length = 2 * (W if side % 2 == 0 else D) + .06
        k = 0.0
        while k < length - .05:
            l = min(rng.uniform(.28, .44), length - k)
            if side == 0:
                c, sz = (-W - .03 + k + l / 2, -D - .015, .04), (l - .008, .09, .16)
            elif side == 1:
                c, sz = (W + .015, -D - .03 + k + l / 2, .04), (.09, l - .008, .16)
            elif side == 2:
                c, sz = (W + .03 - k - l / 2, D + .015, .04), (l - .008, .09, .16)
            else:
                c, sz = (-W - .015, D + .03 - k - l / 2, .04), (.09, l - .008, .16)
            b.box(m["laterite"], sz, c, chamfer=.012, tile=.6, rough=(.006, 14), rng=rng, max_cuts=4)
            k += l
    b.box(m["laterite"], (.9, .2, .21), (0, -D - .12, .065), chamfer=.015, tile=.6, rough=(.008, 12), rng=rng, max_cuts=4)
    # Brick pavers on top, worn hollow at the front; a few lifted by roots or gone.
    n_x, n_y = 8, 6
    for i in range(n_x):
        for j in range(n_y):
            if rng.random() < .04:
                continue
            px = -W + (i + .5) * 2 * W / n_x
            py = -D + (j + .5) * 2 * D / n_y
            lift = rng.uniform(0, .004) + (.02 if (j == n_y - 1 and rng.random() < .3) else 0)
            tilt = (rng.normal(0, .01), rng.normal(0, .01))
            xf = place(px, py, PLATFORM - .012 + lift, rx=tilt[0], ry=tilt[1])
            b.box(m["brick"], (2 * W / n_x - .012, 2 * D / n_y - .012, .028), (0, 0, 0), xf=xf, chamfer=.006,
                  tile=.5, jitter=.0012, rng=rng)


def _walls(b, m, rng):
    z0 = PLATFORM
    h = WALL_TOP - z0
    # Back and side walls, limewashed, with a brick coping.
    b.box(m["lime"], (2 * W - .2, .18, h), (0, .69, z0 + h / 2), chamfer=.01, tile=.7, rough=(.006, 6), rng=rng, grain=False, max_cuts=4)
    for sx in (-1, 1):
        b.box(m["lime"], (.18, 1.36, h), (sx * .91, .1, z0 + h / 2), chamfer=.01, tile=.7, rough=(.006, 6), rng=rng, grain=False, max_cuts=4)
        # Front pillars with a plinth and a capital of corbelled brick.
        b.box(m["lime"], (.2, .2, h), (sx * .91, -.64, z0 + h / 2), chamfer=.012, tile=.7, rough=(.005, 8), rng=rng, grain=False, max_cuts=4)
        b.box(m["lime"], (.26, .26, .12), (sx * .91, -.64, z0 + .06), chamfer=.012, tile=.7, rough=(.005, 10), rng=rng, grain=False, max_cuts=4)
        for k, s in enumerate((.24, .28)):
            b.box(m["brick"], (s, s, .05), (sx * .91, -.64, WALL_TOP - .1 + k * .05), chamfer=.008, tile=.5,
                  rough=(.003, 20), rng=rng, max_cuts=4)
    for (sx, sy, cx, cy) in ((2 * W - .16, .22, 0, .69), (.22, 1.4, -.91, .1), (.22, 1.4, .91, .1)):
        b.box(m["brick"], (sx, sy, .05), (cx, cy, WALL_TOP + .025), chamfer=.008, tile=.5, rough=(.004, 15), rng=rng, grain=False, max_cuts=4)
    # The altar: two steps of brick under limewash gone black with smoke.
    b.box(m["lime"], (1.6, .6, .2), (0, .3, z0 + .1), chamfer=.01, tile=.7, rough=(.004, 10), rng=rng, grain=False, max_cuts=4)
    b.box(m["lime"], (.8, .4, .18), (0, .4, z0 + .29), chamfer=.01, tile=.7, rough=(.004, 10), rng=rng, grain=False, max_cuts=4)


def _roof(b, m, rng, coll):
    """Teak plates, rafters and battens; Marseille tiles go on separately."""
    t = m["timber"]
    b.box(t, (2 * EAVE_X + .04, .12, .1), (0, -.64, WALL_TOP + .1), chamfer=.01, tile=.6, jitter=.002, rng=rng)
    for sx in (-1, 1):
        b.box(t, (.12, 1.55, .08), (sx * .91, .03, WALL_TOP + .09), chamfer=.01, tile=.6)
    b.box(t, (.08, 2 * ROOF_Y, .1), (0, 0, RIDGE_Z - .07), chamfer=.01, tile=.6)
    run = EAVE_X
    rise = RIDGE_Z - EAVE_Z
    L = math.hypot(run, rise)
    for k in range(7):
        y = -ROOF_Y + .06 + k * (2 * ROOF_Y - .12) / 6
        for sx in (-1, 1):
            a = Vector((sx * (EAVE_X + .02), y, EAVE_Z - .03))
            c = Vector((0, y, RIDGE_Z - .05))
            mid = (a + c) / 2
            ang = math.atan2(rise, run)
            xf = place(mid.x, mid.y, mid.z, ry=sx * ang)
            b.box(t, (L + .04, .05, .07), (0, 0, 0), xf=xf, chamfer=.006, tile=.6)
    # Battens across the rafters, seen from under the eaves.
    for j in range(5):
        f = (j + .3) / 5
        for sx in (-1, 1):
            x = sx * EAVE_X * (1 - f)
            z = EAVE_Z + rise * f + .02
            b.box(t, (.05, 2 * ROOF_Y, .02), (x, 0, z), tile=.6)
    # Gable ends: weathered boards behind plain bargeboards with a horn at the apex.
    for gy, facing in ((-ROOF_Y + .27, -1), (ROOF_Y - .27, 1)):
        n = 11
        for k in range(n):
            x0 = -EAVE_X * .86 + k * 2 * EAVE_X * .86 / n
            x1 = x0 + 2 * EAVE_X * .86 / n - .006
            xm = (x0 + x1) / 2
            top = RIDGE_Z - .08 - rise * abs(xm) / EAVE_X
            if top - (WALL_TOP + .15) > .02:
                zz0 = WALL_TOP + .15
                b.box(t, (x1 - x0, .025, top - zz0), (xm, gy, (zz0 + top) / 2), tile=.6, jitter=.0015, rng=rng)
    for gy in (-ROOF_Y, ROOF_Y):
        for sx in (-1, 1):
            d = Vector((sx * run, 0, -rise)).normalized()
            p = Vector((sx * rise, 0, run)).normalized()
            apex = Vector((0, gy, RIDGE_Z + .04))
            pts = [apex + d * (L + .06) * f + p * .02 for f in (0, .5, 1)]
            b.sweep(t, [tuple(q) for q in pts], (0, 1, 0), .12, .035, tile=.6)
        pts = []
        widths = []
        for k in range(9):
            f = k / 8
            ang = math.radians(10 + 140 * f ** 1.5)
            pts.append((0, gy - (.04 if gy < 0 else -.04) * (1 - math.cos(ang)),
                        RIDGE_Z + .06 + .2 * math.sin(min(ang, math.pi / 2)) + (.03 * math.sin(ang - math.pi / 2) if ang > math.pi / 2 else 0)))
            widths.append(.06 * (1 - .75 * f) + .008)
        b.sweep(t, pts, (1, 0, 0), widths, .035, tile=.6, taper_thick=.012)


def _tiles(coll, m, rng):
    from colonial_parts import tiled_slope
    objs = []
    # tiled_slope lays tiles across X and up a slope in Y-Z: build in a frame
    # where X runs along the ridge, then turn it into the shrine's frame.
    for side in (-1, 1):
        o = tiled_slope(f"neakta_roof_tiles_{side}", coll, -ROOF_Y, ROOF_Y, (side * EAVE_X, EAVE_Z + .015),
                        (side * .03, RIDGE_Z - .03), m["tile"], rng, missing=.03)
        o.data.transform(Matrix.Rotation(math.pi / 2, 4, "Z"))
        objs.append(o)
    # Half-round ridge tiles bedded in lime mortar.
    b = Batch("neakta_ridge")
    for k in range(9):
        y = -ROOF_Y + .02 + k * .22
        b.lathe(m["tile"], [(.075, 0), (.08, .02), (.075, .25), (0, .25)], segments=10, tile=.3,
                xf=place(0, y - .02, RIDGE_Z + .02, rx=-math.pi / 2 - .03), cap=False)
    objs += list(b.build(coll).values())
    return objs


def _roots(b, m, rng):
    """The banyan's aerial roots: down over the back of the roof and the back wall,
    gripping the brick, branching and rooting at the platform's corner."""
    bark = m["bark"]
    # Two that came down on the shrine itself: over the eave and down a side wall.
    for sx in (-1, 1):
        x = sx * (1.0 + .02)
        y0 = rng.uniform(-.2, .35)
        pts = [Vector((sx * .4, 1.7, 5.0)), Vector((sx * .7, 1.1, 3.0)), Vector((sx * 1.05, .6, EAVE_Z + .25)),
               Vector((sx * 1.25, y0, EAVE_Z + .02)), Vector((x + sx * .04, y0 - .05, 1.3)),
               Vector((x + sx * .035, y0 - .1, .7)), Vector((x + sx * .06, y0 - .12, .25)), Vector((x + sx * .2, y0 - .15, -.06))]
        dense = []
        for i in range(len(pts) - 1):
            for t in np.linspace(0, 1, 6, endpoint=False):
                q = pts[i].lerp(pts[i + 1], t)
                dense.append(q + Vector((noise.noise(q * 4) * .015, noise.noise(q * 4 + Vector((7, 0, 0))) * .015, 0)))
        dense.append(pts[-1])
        r0 = .045 if sx < 0 else .032
        b.tube(bark, [tuple(q) for q in dense], [r0 * (1 - .4 * i / len(dense)) for i in range(len(dense))], sides=8,
               tile=.6, cap_end=True)
    for k in range(9):
        x = rng.uniform(-1.0, 1.0)
        start = Vector((x + rng.normal(0, .3), 1.6 + rng.uniform(0, .5), 4.2 + rng.uniform(0, 1.2)))
        over = Vector((x, ROOF_Y + .1, RIDGE_Z - .25 * abs(x) / EAVE_X + .1))
        if rng.random() < .55:
            # Down the back face of the wall, tight to the lime.
            pts = [start, start.lerp(over, .6) + Vector((0, 0, .2)), Vector((x, .84, WALL_TOP + .08)),
                   Vector((x + rng.normal(0, .05), .8, 1.1)), Vector((x + rng.normal(0, .08), .81, .55)),
                   Vector((x + rng.normal(0, .1), .9, .05)), Vector((x + rng.normal(0, .15), 1.15, -.08))]
        else:
            # Hanging free behind the shrine and rooted in the earth.
            pts = [start, Vector((x, 1.25, 3.0)), Vector((x + rng.normal(0, .08), 1.2, 1.6)),
                   Vector((x + rng.normal(0, .1), 1.22, .5)), Vector((x + rng.normal(0, .1), 1.3, -.08))]
        r0 = rng.uniform(.025, .06)
        dense = []
        for i in range(len(pts) - 1):
            for t in np.linspace(0, 1, 5, endpoint=False):
                q = pts[i].lerp(pts[i + 1], t)
                q += Vector((noise.noise(q * 3) * .02, noise.noise(q * 3 + Vector((5, 0, 0))) * .02, 0))
                dense.append(q)
        dense.append(pts[-1])
        radii = [r0 * (1 - .45 * i / len(dense)) for i in range(len(dense))]
        b.tube(bark, [tuple(q) for q in dense], radii, sides=7, tile=.6, cap_end=True)
        # Fine rootlets fanning out where the root meets the wall or ground.
        foot = dense[-1]
        for j in range(4):
            a = rng.uniform(0, math.tau)
            q = foot + Vector((math.cos(a) * .25, math.sin(a) * .25, -.02))
            b.tube(bark, [tuple(foot + Vector((0, 0, .05))), tuple(foot.lerp(q, .5) + Vector((0, 0, .02))), tuple(q)],
                   [r0 * .35, r0 * .25, r0 * .12], sides=5, tile=.6)


def _cloth(b, m, rng):
    """Strips of faded red and white cloth knotted round one root and one pillar."""
    for sx, z in ((1, 1.0),):
        ring = []
        for t in np.linspace(0, math.tau, 33):
            cx, cy = math.cos(t), math.sin(t)
            k = max(abs(cx), abs(cy))
            ring.append((sx * .91 + .108 * cx / k ** .9, -.64 + .108 * cy / k ** .9, z + .008 * math.sin(t * 2)))
        b.tube(m["white"], ring, .009, sides=6, flatten=.35)
        b.tube(m["red"], [(x, y, zz + .035) for x, y, zz in ring], .008, sides=6, flatten=.35)


def _inside(b, m, rng):
    """Stones bound in cloth and a broken carved lintel beside the figure."""
    z1 = PLATFORM + .2
    for k, (x, y, size) in enumerate(((.55, .35, (.08, .07, .15)), (.62, .14, (.09, .08, .07)), (-.56, .3, (.06, .055, .05)))):
        c = (x, y, z1 + size[2] * .5)
        boulder(b, m["stone"], c, size, rng)
        # Wax from candles once stood on it, run down its sides.
        top = Vector(c) + Vector((0, 0, size[2] * .85))
        if k == 0:
            kit.wax_spill(b, m, place(top.x, top.y, top.z), rng, radius=.025)
            for j in range(4):
                a = rng.uniform(0, math.tau)
                d = Vector((math.cos(a), math.sin(a), -1.4)).normalized()
                pts = [top + Vector((math.cos(a), math.sin(a), 0)) * .02 + d * size[2] * t for t in (0, .4, .8)]
                b.tube(m["wax_old"], [tuple(q) for q in pts], [.004, .0035, .005], sides=5, cap_end=True)


    # Old offerings on the upper step: a brass bowl, a stub of candle, ash.
    b.lathe(m["brass"], [(0, 0), (.04, 0), (.07, .03), (.075, .045), (.068, .046), (.04, .01), (0, .008)],
            xf=place(-.18, .1, z1), segments=24, tile=.15, cap=False)
    kit.candle(b, m, place(.16, .1, z1), rng, height=.03, radius=.011, melt=1)
    kit.wax_spill(b, m, place(.16, .1, z1), rng, radius=.03)
    kit.incense_bowl(b, m, place(0, .08, z1), rng, radius=.05, height=.045, sticks=12, lit=2)


def _offerings(b, m, rng):
    lip = -D + .14
    z = PLATFORM + .004
    lit = None
    # A row of candles burnt down where they stood, one still alight.
    for k, x in enumerate((-.42, -.24, -.08, .05, .2, .36)):
        h = .12 if x == .05 else rng.uniform(.01, .05)
        kit.wax_spill(b, m, place(x, lip + rng.normal(0, .02), z), rng, radius=rng.uniform(.025, .045))
        tip = kit.candle(b, m, place(x, lip, z + .002, rz=rng.uniform(0, 6)), rng, height=h, radius=.0105,
                         melt=.9, lean=rng.normal(0, .04))
        if x == .05:
            lit = tip
    for k in range(12):
        x = rng.uniform(-.55, .5)
        kit.wax_run_over(b, m, (x, -D - .002, PLATFORM + .004), (0, 0, -1), (0, -1, 0), rng,
                         length=rng.uniform(.05, .25))
    kit.incense_bowl(b, m, place(.5, -.5, z), rng, radius=.075, height=.1, sticks=34, lit=4)
    kit.leaf_cup(b, m, place(-.6, -.52, z, rz=.3), rng, size=.09, height=.04, fill="rice", old=True)
    kit.leaf_cup(b, m, place(-.32, -.42, z, rz=-.2), rng, size=.075, height=.035, fill="betel")
    kit.leaf_cup(b, m, place(.27, -.4, z, rz=.5), rng, size=.07, height=.035, fill="flowers", old=True)
    b.lathe(m["clay"], [(0, 0), (.07, 0), (.12, .014), (.125, .018), (.115, .018), (.07, .007), (0, .006)],
            xf=place(.72, -.3, z), segments=28, tile=.25, cap=False)
    kit.bananas(b, m, place(.66, -.3, z + .006, rz=.3), rng, count=7, length=.1)
    kit.coconut(b, m, place(-.78, -.35, z, rz=1.1), rng, height=.17, radius=.07)
    kit.rice_grains(b, m, (-.6, -.6, z), rng, count=60, spread=.05)
    for k in range(6):
        kit.marigold(b, m, (rng.uniform(-.9, .9), rng.uniform(-.7, -.2), z), rng, .01, dead=True)
    # A bottle of rice spirit and two tiny cups, one knocked over.
    b.lathe(m["bottle"], [(0, 0), (.033, 0), (.036, .01), (.036, .15), (.02, .19), (.012, .21), (.012, .25), (.014, .26),
                          (0, .26)], xf=place(-.9, -.5, z), segments=16, tile=.3, cap=False)
    kit.small_cup(b, m, place(-.86, -.62, z), rng, radius=.02, height=.028, liquid="water")
    kit.small_cup(b, m, place(-.78, -.66, z + .02) @ Matrix.Rotation(1.5, 4, "X"), rng, radius=.02, height=.028)
    return lit


def _pot(b, m, rng, at):
    """A sealed clay pot beside the platform: its mouth bound in cloth and string,
    black hair escaping under the cloth, iron nails driven into the clay. Somebody
    has asked the spirit for something here (advisor review)."""
    px, py = at
    prof = [(0, 0), (.1, 0), (.16, .08), (.17, .16), (.12, .26), (.09, .28), (.1, .31), (0, .3)]
    b.lathe(m["clay"], prof, xf=place(px, py, -.03), segments=24, tile=.25)
    b.lathe(m["white"], [(.13, .19), (.12, .27), (.11, .31), (0, .325)], xf=place(px, py, -.03), segments=24, tile=.3)
    ring = [(px + .113 * math.cos(t), py + .113 * math.sin(t), .245) for t in np.linspace(0, math.tau, 25)]
    b.tube(m["rope"], ring, .005, sides=5)
    for j in range(22):
        a = rng.uniform(0, math.tau)
        r0 = Vector((px + .112 * math.cos(a), py + .112 * math.sin(a), .23))
        mid = r0 + Vector((.045 * math.cos(a), .045 * math.sin(a), -.07))
        end = Vector((r0.x + .075 * math.cos(a) + rng.normal(0, .02), r0.y + .075 * math.sin(a) + rng.normal(0, .02),
                      rng.uniform(-.01, .1)))
        b.tube(m["hair"], [tuple(r0), tuple(mid), tuple(end)], [.0012, .001, .0006], sides=3)
    for j in range(6):
        a = rng.uniform(0, math.tau)
        zz = rng.uniform(.03, .15)
        o = Vector((px + .165 * math.cos(a), py + .165 * math.sin(a), zz))
        b.tube(m["iron"], [tuple(o - Vector((math.cos(a), math.sin(a), 0)) * .02),
                           tuple(o + Vector((math.cos(a), math.sin(a), .1)).normalized() * .045)], .0035, sides=4)


def build(coll, x, y, facing, rng=None, figure=None):
    """Build the shrine at (x, y) facing `facing` (front direction = facing).
    Returns (objects, watcher, lit wick world position, collider)."""
    rng = rng or np.random.default_rng(3409)
    m = materials()
    # Local -y is the front (as forest.py's at()): facing pi/2 turns it to face east.
    F = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(facing, 4, "Z")
    b = Batch("neakta_shrine")
    _platform(b, m, rng)
    _walls(b, m, rng)
    _roof(b, m, rng, coll)
    _roots(b, m, rng)
    _cloth(b, m, rng)
    _inside(b, m, rng)
    lit = _offerings(b, m, rng)
    _pot(b, m, rng, (1.35, .35))
    objs = list(b.build(coll).values())
    objs += _tiles(coll, m, rng)
    from cobwebs import corner_cobweb, web_materials
    sheet, thread = bpy.data.materials.get("M_cobweb_dusty"), bpy.data.materials.get("M_cobweb_thread")
    if sheet is None or thread is None:
        sheet, thread = web_materials()
    webs = []
    webs += corner_cobweb("neakta_web_l", coll, (-.81, .59, WALL_TOP + .05), (1, 0, 0), (0, -1, 0), .22, sheet, thread, seed=21)
    webs += corner_cobweb("neakta_web_r", coll, (.81, .59, WALL_TOP + .05), (-1, 0, 0), (0, -1, 0), .16, sheet, thread, seed=22)
    for o in objs + webs:
        o.matrix_world = F @ o.matrix_world
    foot = F @ Vector((0, .4, PLATFORM + .38))
    fig = watcher(coll, m, foot, facing, rng, figure=figure)
    return objs + webs, fig, F @ lit, F
