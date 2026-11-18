"""The back garden north of the house (Episode 1 village expansion, November 2026).

Through a gap in the back fence by the rear stairs and past the giants that
stand behind the house, the lane comes out where the family kept their garden:

- The ancestors' chedei (ចេតិយ): Episode 2's sculpted family stupas from the
  shared kit (a bell stupa holding the family's ashes, an older bud stupa and
  one snapped through its drum), inside a low brick wall half fallen, ferns at
  their feet. Before the main one: joss stick stubs in a bowl of grey sand,
  candle stubs, dead marigolds.
- The well: a brick ring rendered in lime, laterite slabs round it, a post
  frame with a pulley and a rope going down into the dark; the bucket on the rim.
- Termite mounds of red earth, the biggest with old joss sticks pushed into it
  (spirits live in them).
- The kitchen garden gone wild: raised beds edged with logs under weeds, a bean
  trellis of bamboo fallen in, a broken fence.

Blender axes, metres. Plan in village_layout.NORTH_GARDEN.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

import village_layout as L
from kit import collider
from rural_kit import _lib, log, materials, place_model, timber, tile_of
from shrine_craft import Batch
from west_yard import bamboo_fence


def garden_materials():
    m = dict(materials())
    get = bpy.data.materials.get
    m["lime"] = get("M_neakta_limewash") or m["planks"]
    m["brick"] = get("M_neakta_brick") or m["hewn"]
    m["laterite"] = get("M_neakta_laterite") or m["hewn"]
    m["sandstone"] = get("M_neakta_sandstone") or m["laterite"]
    m["termite"] = _lib("termite", "red_laterite_soil_stones", tint=(.55, .43, .36), tile=.9)
    from rural_kit import _plain
    m["moss"] = _plain("moss", (.035, .055, .022), rough=.9)
    m["mould"] = _plain("mould", (.03, .03, .025), rough=.95)
    return m


# ======================================================================= chedei

# Episode 2's sculpted, baked family stupas (art-source/kits/stupa_kit.blend, built by
# tools/ep2/build-stupas.py), placed here as they are in the wat: (kit piece, dx, dy, scale, turn).
STUPAS = (("stupa_bell", 0.0, 0.0, 1.0, 0), ("stupa_bud", -2.7, -.6, .78, 1), ("stupa_spire_broken", 2.6, -.8, .9, 3))
FOOT = .7  # half the kit stupas' 1.4 m footprint
KIT = L.__file__.replace("tools/areas/village_layout.py", "art-source/kits/stupa_kit.blend")


def _kit_mesh(name):
    """A kit stupa's mesh: the one already in the village (a re-run), else appended from the kit."""
    me = bpy.data.meshes.get(name)
    if me is not None:
        return me
    with bpy.data.libraries.load(KIT, link=False) as (src, dst):
        dst.meshes = [name]
    return dst.meshes[0]


def piece(coll, mesh, name, x, y, z, yaw, scale, tilt=(0.0, 0.0)):
    o = bpy.data.objects.new(name, _kit_mesh(mesh))
    coll.objects.link(o)
    o.location = (x, y, z)
    o.rotation_euler = (tilt[0], tilt[1], yaw)
    o.scale = (scale, scale, scale)
    return o


def stupas(coll, m, ground, rng):
    import offerings_kit as ok
    om = ok.materials()
    x, y, _ = L.NORTH_GARDEN["stupa"]
    b = Batch("ng_chedei")
    z = ground(x, y)
    objs = []
    for k, (mesh, dx, dy, sc, turn) in enumerate(STUPAS):
        px, py = x + dx, y + dy
        foot = min(ground(px + u, py + v) for u in (-FOOT * sc, FOOT * sc) for v in (-FOOT * sc, FOOT * sc))
        o = piece(coll, mesh, f"ng_chedei_{k}", px, py, foot - .04, turn * math.pi / 2 + rng.normal(0, .03), sc,
                  tilt=(rng.normal(0, .015), rng.normal(0, .015)) if k else (0.0, 0.0))
        objs.append(o)
        collider(f"ng_chedei_{k}", coll, px - FOOT * sc, px + FOOT * sc, py - FOOT * sc, py + FOOT * sc, foot,
                 foot + 3.5 * sc, surface="stone")
    ledge = Vector((x, y - FOOT - .16, ground(x, y - FOOT - .16)))
    # The low wall round them, fallen in places, a laterite coping on what stands.
    x0, x1, y0, y1 = x - 4.4, x + 4.4, y - 3.4, y + 2.6
    runs = [((x0, y0), (x + -.8, y0)), ((x + .8, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)),
            ((x0, y1), (x0, y0))]
    for (ax, ay), (cx, cy) in runs:
        d = Vector((cx - ax, cy - ay, 0))
        n = int(d.length / .6)
        for k in range(n):
            if rng.random() < .22:
                # A stretch fallen: its bricks lie in the grass.
                for j in range(4):
                    p = Vector((ax, ay, 0)) + d * ((k + rng.random()) / n) + Vector((rng.normal(0, .3), rng.normal(0, .3), 0))
                    b.box(m["brick"], (.22, .11, .06), (p.x, p.y, ground(p.x, p.y) + .02), chamfer=.01, tile=.5,
                          xf=Matrix.Rotation(0, 4, "Z"), jitter=.004, rng=rng)
                continue
            p = Vector((ax, ay, 0)) + d * ((k + .5) / n)
            h = rng.uniform(.38, .6)
            ang = math.atan2(d.y, d.x)
            xf = Matrix.Translation((p.x, p.y, ground(p.x, p.y) - .06)) @ Matrix.Rotation(ang, 4, "Z")
            b.box(m["lime"] if rng.random() < .6 else m["brick"], (d.length / n + .01, .24, h), (0, 0, h / 2), xf=xf,
                  chamfer=.01, tile=.7, grain=False, rough=(.01, 5), rng=rng, max_cuts=4)
            b.box(m["laterite"], (d.length / n + .02, .3, .07), (0, 0, h + .03), xf=xf, chamfer=.01, tile=.5,
                  grain=False)
    objs += list(b.build(coll).values())
    # Offerings at the main stupa's foot, old: stubs of joss sticks in sand, candle stubs, dead flowers.
    o = Batch("ng_offerings")
    if ledge is not None:
        ok.incense_bowl(o, om, Matrix.Translation(ledge + Vector((-.06, .02, 0))), rng, radius=.07, sticks=9, lit=0)
        for k in range(3):
            ok.candle(o, om, Matrix.Translation(ledge + Vector((.09 + .04 * k, .01, 0))), rng, height=.03, lit=False,
                      melt=.9)
        for k in range(5):
            ok.marigold(o, om, ledge + Vector((rng.uniform(-.2, .2), rng.uniform(-.04, .02), .012)), rng, dead=True)
    objs += list(o.build(coll).values())
    # A fern growing from the plinth's crack, others at its foot.
    for k, (dx, dy, zz, sc) in enumerate(((.95, -1.0, 0, .45), (-1.4, .4, 0, .6), (1.3, .9, 0, .7))):
        place_model(coll, "fern_02", x + dx, y + dy, ground, rot=rng.uniform(0, 6.3), scale=sc,
                    z=(ground(x, y) + zz) if zz else None, name=f"ng_fern_{k}")
    return objs


# ======================================================================= well


def well(coll, m, ground, rng):
    x, y = L.NORTH_GARDEN["well"]
    z = ground(x, y)
    b = Batch("ng_well")
    # One continuous wall, so every face points out where it is seen (the game culls back faces):
    # up the outside, over the rim, down the inside; the shaft below in bare brick.
    ring = [(.95, -.05), (.92, .05), (.9, .78), (.86, .82), (.7, .82), (.66, .78), (.66, .5)]
    b.lathe(m["lime"], ring, xf=Matrix.Translation((x, y, z)), segments=32, tile=.7, cap=False,
            radial=lambda a, h: 1 + .01 * math.sin(a * 9))
    b.lathe(m["moss"], [(.958, -.02), (.945, .14), (.928, .2)], xf=Matrix.Translation((x, y, z)), segments=32, tile=1,
            cap=False)
    b.lathe(m["brick"], [(.66, .5), (.66, -.6)], xf=Matrix.Translation((x, y, z)), segments=32, tile=.7, cap=False)
    b.lathe(m["void"], [(.64, .02), (0, .02)], xf=Matrix.Translation((x, y, z)), segments=24, tile=1)
    # Laterite slabs laid round it, sunk and tilted.
    for k in range(9):
        a = k / 9 * math.tau + rng.normal(0, .1)
        p = Vector((x + math.cos(a) * 1.35, y + math.sin(a) * 1.35, 0))
        xf = Matrix.Translation((p.x, p.y, ground(p.x, p.y) - .02)) @ Matrix.Rotation(a, 4, "Z") \
            @ Matrix.Rotation(rng.normal(0, .04), 4, "X")
        b.box(m["laterite"], (.42, .55, .08), (0, 0, 0), xf=xf, chamfer=.02, tile=.5, grain=False, rough=(.01, 6), rng=rng)
    # The frame: two posts, a beam, a pulley, the rope into the dark.
    a = .3
    c, s = math.cos(a), math.sin(a)
    tops = []
    for side in (-1, 1):
        px, py = x + c * 1.08 * side, y + s * 1.08 * side
        timber(b, m["hewn"], (px, py, ground(px, py) - .4), (px, py, z + 2.15), .13, .13, rng)
        tops.append(Vector((px, py, z + 2.1)))
    timber(b, m["hewn"], tops[0] - Vector((c, s, 0)) * .1, tops[1] + Vector((c, s, 0)) * .1, .11, .11, rng)
    pul = Matrix.Translation((x, y, z + 1.92)) @ Matrix.Rotation(a, 4, "Z") @ Matrix.Rotation(math.pi / 2, 4, "Y")
    b.lathe(m["hewn"], [(0, -.035), (.13, -.035), (.1, 0), (.13, .035), (0, .035)], xf=pul, segments=16, tile=.4)
    b.tube(m["rope"], [Vector((x - s * .12, y + c * .12, z + 1.9)), Vector((x - s * .12, y + c * .12, z - .35))], .011,
           sides=5, tile=.3)
    b.tube(m["rope"], [Vector((x + s * .12, y - c * .12, z + 1.9)), Vector((x + s * .35, y - c * .2, z + .86)),
                       Vector((x + s * .5, y - c * .1, z + .83))], .011, sides=5, tile=.3)
    objs = list(b.build(coll).values())
    place_model(coll, "wooden_bucket_01", x + s * .62, y - c * .1, ground, rot=.4, z=z + .82, name="ng_well_bucket")
    place_model(coll, "water_jar", x + 1.6, y + .9, ground, rot=1.0, scan=True, name="ng_well_jar")
    collider("ng_well", coll, x - 1.0, x + 1.0, y - 1.0, y + 1.0, z, z + 1.0, surface="stone")
    return objs


# ======================================================================= termites


def termite_mound(b, m, x, y, z, h, rng, spires=3):
    """Red earth mound: a lumpy, buttressed base fluted by rain, and a few tall
    spires leaning together, every surface pocked with lumps of worked earth."""
    from mathutils import noise
    seed = Vector(rng.uniform(0, 50, 3))

    def lumps(a, hh, scale):
        p = Vector((math.cos(a) * 1.7, math.sin(a) * 1.7, hh * 2.2 / scale)) + seed
        return 1 + .1 * noise.noise(p * 2.0) + .05 * noise.noise(p * 5.0) + .025 * noise.noise(p * 11.0)

    def radial(a, hh):
        flutes = .1 * math.sin(a * 5 + hh * 1.5 + seed.x) * (1 - hh / h) + .05 * math.sin(a * 9 - hh * 3)
        return (1 + flutes) * lumps(a, hh, h)

    rows = 14
    base = [(0, -.1)] + [(h * (.52 - .38 * (t ** 1.3)) * (1 + .06 * math.sin(t * 9)), h * .6 * t) for t in
                          (i / rows for i in range(rows + 1))] + [(0, h * .62)]
    b.lathe(m["termite"], base, xf=Matrix.Translation((x, y, z - .05)), segments=48, tile=.7, radial=radial)
    for k in range(spires):
        a = k / spires * math.tau + rng.uniform(-.4, .4)
        off = Vector((math.cos(a), math.sin(a), 0)) * h * .1
        tall = h * rng.uniform(.75, 1.0) if k == 0 else h * rng.uniform(.45, .75)
        prof = [(h * (.17 - .15 * t ** 1.2), tall * t) for t in (i / 10 for i in range(11))] + [(0, tall * 1.02)]
        lean = Matrix.Rotation(rng.normal(0, .08), 4, "X") @ Matrix.Rotation(rng.normal(0, .08), 4, "Y")
        b.lathe(m["termite"], prof, xf=Matrix.Translation(Vector((x, y, z + h * .35)) + off) @ lean, segments=24,
                tile=.7, radial=lambda aa, hh, t=tall: lumps(aa, hh + 3, t) * (1 + .08 * math.sin(aa * 4 + hh * 6)))


def termites(coll, m, ground, rng):
    import offerings_kit as ok
    om = ok.materials()
    b = Batch("ng_termite")
    o = Batch("ng_termite_offerings")
    for k, (x, y, h) in enumerate(L.NORTH_GARDEN["termites"]):
        z = ground(x, y)
        termite_mound(b, m, x, y, z, h, rng, spires=3 if h > 2 else 2)
        collider(f"ng_termite_{k}", coll, x - h * .45, x + h * .45, y - h * .45, y + h * .45, z, z + h, surface="dirt")
        if k == 0:
            # Old joss sticks pushed into the earth on the mound's face, and a clay cup.
            for j in range(9):
                a = -math.pi / 2 + rng.normal(0, .35)
                r = h * .47
                base = Vector((x + math.cos(a) * r, y + math.sin(a) * r, z + .12 + rng.uniform(0, .08)))
                ok.joss_stick(o, om, base, Vector((math.cos(a) * .3, math.sin(a) * .3, 1)), .3, rng, burnt=rng.uniform(.6, .95))
            ok.small_cup(o, om, Matrix.Translation((x + .1, y - h * .56, ground(x + .1, y - h * .56))), rng, radius=.04)
    return list(b.build(coll).values()) + list(o.build(coll).values())


# ======================================================================= beds


def beds(coll, m, ground, rng):
    from forest_detail import grass_geometry
    cx, cy = L.NORTH_GARDEN["beds"]
    b = Batch("ng_beds")
    weeds = []
    for k in range(3):
        bx, by = cx + (k - 1) * 1.9, cy + rng.normal(0, .15)
        z = ground(bx, by)
        xf = Matrix.Translation((bx, by, z)) @ Matrix.Rotation(rng.normal(0, .05), 4, "Z")
        # A mound of dug earth gone hard, edged with split logs.
        b.grid(m["mud"], lambda u, v: xf @ Vector(((u - .5) * 1.2, (v - .5) * 4.0,
                                                   .16 * math.sin(math.pi * u) ** .6 * (1 - abs(v - .5) ** 4 * 8) - .02)),
               10, 24, uv=lambda u, v: (u * 1.2 / 2, v * 4 / 2))
        for side in (-1, 1):
            log(b, m["bark"], xf @ Vector((side * .66, -2.0, .06)), xf @ Vector((side * .66, 2.0, .06)), .07, .065, rng,
                sides=7)
        for _ in range(40):
            p = xf @ Vector((rng.uniform(-.5, .5), rng.uniform(-1.9, 1.9), 0))
            weeds.append((p.x, p.y, ground(p.x, p.y) + .1))
    # The bean trellis: bamboo poles crossed and tied, half fallen.
    tx, ty = cx + 3.4, cy + .4
    for k in range(5):
        y0 = ty - 1.6 + k * .8
        fallen = k >= 3
        for side in (-1, 1):
            foot = Vector((tx + side * .45, y0, ground(tx + side * .45, y0) - .2))
            top = Vector((tx - side * .25, y0 + (.6 if fallen else 0), foot.z + (.6 if fallen else 2.1)))
            log(b, m["bamboo"], foot, top, .02, .018, rng, sides=6, tile=.4)
    # The ridge pole lies in the crotches where the standing pairs cross.
    log(b, m["bamboo"], (tx, ty - 1.75, ground(tx, ty - 1.6) + 1.12), (tx, ty + .2, ground(tx, ty) + 1.12), .018, .016,
        rng, sides=6, bow=0)
    objs = list(b.build(coll).values())
    objs += grass_geometry("ng_weeds", coll, weeds, rng, size=(.3, .75))
    return objs


def build(coll, ground, rng=None):
    rng = rng or np.random.default_rng(1925)
    m = garden_materials()
    objs = []
    objs += stupas(coll, m, ground, rng)
    objs += well(coll, m, ground, rng)
    objs += termites(coll, m, ground, rng)
    objs += beds(coll, m, ground, rng)
    gx, gy = L.NORTH_GARDEN["clearing"][:2]
    objs += bamboo_fence(coll, m, ground, rng, [(-15.5, 41.0), (-12.0, 54.0), (6.0, 55.5), (15.0, 50.0)], "ng_fence")
    return objs
