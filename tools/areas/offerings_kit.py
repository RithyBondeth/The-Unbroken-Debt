"""Candles, incense and offerings for Episode 1's shrines (2026-11 redesign).

Hand-rolled beeswax tapers, burnt down unevenly, with runs of wax down their
sides that reach the dish and spread into a pool; charred, curled wicks. Joss
sticks with red-dyed bamboo stems standing in a bowl of sand grey with ash,
some burnt to stubs, some with a curl of ash still on the tip; ash fallen round
the bowl. Closed lotus buds, a young coconut trimmed to a point, small bananas
(Poly Haven, CC0) and folded banana-leaf cones (sla thor).

Every builder adds to a `Batch` (shrine_craft) at a placement matrix, so a
shrine's offerings stay a few draw calls. Coordinates in metres, z up.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

import shrine_surfaces as surf
from shrine_craft import place

_mats = {}


def materials():
    """The kit's materials, made once per Blender session."""
    if _mats:
        return _mats
    m = _mats
    m["wax"] = surf.beeswax()
    m["wax_old"] = surf.plain("M_offering_wax_dirty", (.30, .20, .08), rough=.5)
    m["char"] = surf.plain("M_offering_char", (.018, .014, .012), rough=.95)
    m["clay"] = surf.earthenware()
    m["sand"] = surf.sand_ash()
    m["ash"] = surf.plain("M_offering_ash", (.30, .29, .27), rough=1.0)
    m["incense"] = surf.strip("offering_joss_stick", [(0, (.30, .03, .02)), (.32, (.36, .05, .03)), (.33, (.17, .09, .05)),
                                                       (.93, (.20, .11, .06)), (.95, (.32, .31, .29)), (1, (.40, .39, .36))],
                              rough=.9, seed=11)
    m["lotus"] = surf.strip("offering_lotus_bud", [(0, (.48, .55, .32)), (.25, (.72, .70, .55)), (.6, (.80, .62, .60)),
                                                   (.85, (.72, .30, .38)), (1, (.55, .15, .25))],
                            rough=.55, seed=12, size=(32, 256), backface=False)
    m["lotus_old"] = surf.strip("offering_lotus_wilted", [(0, (.30, .30, .17)), (.3, (.42, .35, .26)), (.7, (.40, .24, .22)),
                                                          (1, (.20, .08, .08))],
                                rough=.7, seed=13, size=(32, 256), backface=False)
    m["stem"] = surf.plain("M_offering_lotus_stem", (.12, .20, .06), rough=.6)
    m["coconut"] = surf.coconut_skin()
    leaf = bpy.data.materials.get("M_shrine_folded_banana_leaf")
    if leaf is None:
        from shrine import make_leaf_textures, shrine_materials
        make_leaf_textures()
        leaf = shrine_materials({})["leaf"]
    m["leaf"] = leaf
    from kit import image_material, texture
    dry = image_material("M_offering_dry_banana_leaf", texture("T_ep1_offering_leaf_BC"), rough=.9, tint=(.55, .42, .26))
    dry.use_backface_culling = False
    m["leaf_dry"] = dry
    m["marigold"] = surf.plain("M_offering_marigold", (.62, .22, .015), rough=.85)
    m["marigold_dead"] = surf.plain("M_offering_marigold_dead", (.20, .09, .03), rough=.95)
    m["jasmine"] = surf.plain("M_offering_jasmine", (.62, .60, .52), rough=.8)
    m["bamboo"] = surf.plain("M_offering_bamboo_pin", (.42, .36, .2), rough=.8)
    m["brass"] = surf.plain("M_offering_tarnished_brass", (.36, .25, .11), rough=.45, metal=1.0)
    m["glass"] = surf.plain("M_offering_old_glass", (.42, .45, .40), rough=.12, alpha=.35)
    m["water"] = surf.plain("M_offering_stale_water", (.06, .055, .04), rough=.08)
    m["rice"] = surf.plain("M_offering_rice", (.62, .57, .45), rough=.85)
    m["betel"] = surf.plain("M_offering_betel_leaf", (.07, .14, .03), rough=.45)
    m["banana"] = surf.banana_skin()
    m["banana_crown"] = surf.plain("M_offering_banana_crown", (.12, .1, .04), rough=.8)
    return m


# ----------------------------------------------------------------- candles


def _noise1(rng, n=6):
    phases = rng.uniform(0, math.tau, n)
    amps = rng.uniform(.3, 1, n) / (1 + np.arange(n))
    freqs = 1 + np.arange(n)

    def f(t):
        return float(np.sum(amps * np.sin(freqs * t + phases)))
    return f


def candle(b, m, xf, rng, height=.12, radius=.0105, melt=.5, lit=True, lean=0.0):
    """A hand-rolled beeswax taper standing at xf's origin. Returns the wick
    tip in world space. `melt` 0..1: how far wax has run down its sides."""
    wobble = _noise1(rng)
    low = rng.uniform(0, math.tau)  # where the rim has melted lowest and the wax ran
    top = height

    def radial(a, hz):
        r = 1 + .035 * wobble(a * 2 + hz * 40) + .02 * math.sin(hz * 260 + a)
        return r

    profile = [(radius * 1.06, 0), (radius * 1.04, .004)]
    for k in range(1, 12):
        hz = top * k / 12
        profile.append((radius * (1 - .16 * hz / top), hz))
    rt = radius * .84
    # The burnt top: a ragged lip round a shallow cup of liquid wax.
    profile += [(rt * 1.02, top + .001), (rt * .9, top + .0025), (rt * .55, top - .003), (rt * .2, top - .004), (0, top - .0035)]

    def rim(a, hz):
        r = radial(a, hz)
        return r

    xf_lean = xf @ Matrix.Rotation(lean, 4, "X")
    b.lathe(m["wax"], profile, xf=xf_lean, segments=22, tile=.08, radial=rim)
    # Runs of wax: from the low side of the rim down the taper, some to the dish.
    for k in range(int(4 + melt * 7)):
        a = low + rng.normal(0, .55)
        length = top * rng.uniform(.15, .45 + .55 * melt)
        pts, rad = [], []
        steps = 10
        drift = rng.normal(0, .25)
        for i in range(steps + 1):
            t = i / steps
            hz = top - .002 - length * t
            ang = a + drift * t
            r = radius * (1 - .16 * max(hz, 0) / top) * radial(ang, max(hz, 0)) + .0012
            pts.append((r * math.cos(ang), r * math.sin(ang), max(hz, .001)))
            rad.append(.0018 + .0012 * math.sin(math.pi * t) + (.0016 if t > .9 else 0))
        b.tube(m["wax"], [tuple(xf_lean @ Vector(p)) for p in pts], rad, sides=6, cap_end=True)
    # The wick: a charred, curled thread standing out of the cup.
    curl = rng.uniform(-.5, .5)
    wick = [(0, 0, top - .004), (0, 0, top + .004), (.0012 * math.cos(curl), .0012 * math.sin(curl), top + .009),
            (.003 * math.cos(curl), .003 * math.sin(curl), top + .012)]
    b.tube(m["char"], [tuple(xf_lean @ Vector(p)) for p in wick], [.0009, .0009, .0008, .0006], sides=5, cap_end=True)
    return xf_lean @ Vector((0, 0, top + .012))


def candle_dish(b, m, xf, rng, radius=.055, pool=True, melt=.6):
    """A small fired-clay saucer, its well filled with wax that ran and set."""
    prof = [(0, 0), (radius * .55, 0), (radius * .62, .003), (radius * .64, .004), (radius * .98, .015),
            (radius, .018), (radius * .94, .019), (radius * .66, .007), (0, .006)]
    wob = _noise1(rng)
    b.lathe(m["clay"], prof, xf=xf, segments=28, tile=.25, radial=lambda a, h: 1 + .02 * wob(a * 3), cap=False)
    if pool:
        pr = radius * rng.uniform(.38, .55) * (.6 + .4 * melt)
        edge = _noise1(rng)
        b.lathe(m["wax_old"], [(pr, .0055), (pr * .9, .0085), (pr * .5, .0095), (0, .0098)], xf=xf, segments=28, tile=.08,
                radial=lambda a, h: 1 + .18 * edge(a * 2), cap=True)
        # Drops that spat over the rim and set on it.
        for k in range(int(2 + 4 * melt)):
            a = rng.uniform(0, math.tau)
            r0 = rng.uniform(pr * .8, radius * .9)
            p0 = (r0 * math.cos(a), r0 * math.sin(a), .008 + (r0 / radius) * .008)
            p1 = (p0[0] * 1.08, p0[1] * 1.08, p0[2] + .002)
            b.tube(m["wax"], [tuple(xf @ Vector(p)) for p in (p0, p1)], [.003, .0022], sides=6, cap_end=True)


def wax_spill(b, m, xf, rng, radius=.04):
    """Old wax set in an irregular puddle on a board (z = 0 at the surface)."""
    edge = _noise1(rng)
    b.lathe(m["wax_old"], [(radius, -.001), (radius * .92, .0018), (radius * .5, .0025), (0, .0026)], xf=xf,
            segments=24, tile=.1, radial=lambda a, h: 1 + .3 * edge(a * 2), cap=True)


def wax_run_over(b, m, top, down, out, rng, length=.08):
    """A run of wax that went over an edge and down a face. `top` is the edge
    point, `down` the face's downward direction, `out` its outward normal."""
    top, down, out = Vector(top), Vector(down).normalized(), Vector(out).normalized()
    pts, rad = [], []
    side = down.cross(out)
    drift = rng.normal(0, .15)
    for i in range(9):
        t = i / 8
        p = top + down * length * t + out * (.0015 + .001 * math.sin(math.pi * t)) + side * drift * length * t * t
        if i == 0:
            p = top - down * .004 + out * .0005
        pts.append(tuple(p))
        rad.append(.0028 + .0015 * (t > .85))
    b.tube(m["wax_old"], pts, rad, sides=6, cap_end=True)


# ------------------------------------------------------------------ incense


def joss_stick(b, m, base, direction, length, rng, burnt=0.0, ash_curl=True):
    """One stick: red bamboo stem, brown incense coat, burnt down by `burnt`
    (0 fresh .. 1 stub). Its lit end carries a grey curl of ash."""
    base, d = Vector(base), Vector(direction).normalized()
    stem = .32
    burn_v = 1 - burnt * (1 - stem - .02)
    l = length * burn_v
    # Stem below the coat: thin bamboo.
    s_end = base + d * length * stem
    b.tube(m["incense"], [tuple(base), tuple(s_end)], .0011, sides=4, v0=0, v1=stem)
    if burn_v > stem + .01:
        c_end = base + d * l
        b.tube(m["incense"], [tuple(s_end), tuple(c_end)], .0019, sides=5, v0=stem, v1=min(burn_v, .93))
        if ash_curl and burnt < .9:
            # The ash holds its shape and droops before it falls.
            side = d.cross(Vector((0, 0, 1)))
            if side.length < .1:
                side = Vector((1, 0, 0))
            side.normalize()
            pts = [c_end]
            p = c_end
            length = rng.uniform(.012, .035)
            for i in range(5):
                p = p + d * length / 5 + side * rng.normal(0, .0006) - Vector((0, 0, .0007 * i * i * length / .03))
                pts.append(p)
            b.tube(m["ash"], [tuple(q) for q in pts], [.0021, .0021, .002, .0019, .0018, .0015], sides=5, cap_end=True)
            b.tube(m["char"], [tuple(c_end - d * .0015), tuple(c_end + d * .0008)], .00205, sides=5)
        else:
            b.tube(m["char"], [tuple(c_end), tuple(c_end + d * .002)], [.0019, .0012], sides=5, cap_end=True)
    else:
        b.tube(m["char"], [tuple(s_end), tuple(s_end + d * .003)], [.0011, .0007], sides=4, cap_end=True)


def incense_bowl(b, m, xf, rng, radius=.085, height=.06, sticks=11, lit=3, glaze=False):
    """A clay bowl of sand grey with ash, joss sticks old and new standing in
    it, stubs crowding the middle and ash fallen over the rim."""
    prof = [(0, 0), (radius * .55, 0), (radius * .6, .004), (radius * .92, height * .45), (radius, height * .9),
            (radius * 1.02, height), (radius * .96, height * 1.02), (radius * .9, height * .9), (0, .008)]
    wob = _noise1(rng)
    b.lathe(m["clay"], prof, xf=xf, segments=32, tile=.25, radial=lambda a, h: 1 + .015 * wob(a * 3), cap=False)
    sand_z = height * .86
    mound = _noise1(rng)
    b.lathe(m["sand"], [(radius * .9, sand_z - .004), (radius * .7, sand_z + .002), (radius * .35, sand_z + .006),
                        (0, sand_z + .007)], xf=xf, segments=32, tile=.12,
            radial=lambda a, h: 1 + .05 * mound(a * 2), cap=True)
    for k in range(sticks):
        a = rng.uniform(0, math.tau)
        r = math.sqrt(rng.random()) * radius * .65
        bx, by = r * math.cos(a), r * math.sin(a)
        tilt = rng.uniform(.03, .22)
        d = Vector((math.cos(a) * tilt, math.sin(a) * tilt, 1)).normalized()
        burnt = rng.uniform(.15, .5) if k < lit else rng.uniform(.8, 1.0)
        base = xf @ Vector((bx, by, sand_z - .02))
        direction = (xf.to_3x3() @ d).normalized()
        joss_stick(b, m, base, direction, rng.uniform(.2, .26), rng, burnt=burnt, ash_curl=k < lit)
    # Fallen ash: grey crumbs and broken curls in the sand and around the foot.
    for k in range(26):
        a = rng.uniform(0, math.tau)
        inside = k < 14
        r = rng.uniform(0, radius * .85) if inside else rng.uniform(radius * 1.05, radius * 1.9)
        z = sand_z + .006 if inside else .0015
        p = Vector((r * math.cos(a), r * math.sin(a), z))
        q = p + Vector((rng.normal(0, .007), rng.normal(0, .007), 0))
        b.tube(m["ash"], [tuple(xf @ p), tuple(xf @ q)], .0016, sides=4, cap_end=True)


# ------------------------------------------------------------------ flowers


def lotus_bud(b, m, base, axis, rng, size=.075, old=False, stem=.0):
    """A closed lotus bud of overlapping pointed petals; a stem of `stem` metres below."""
    mat = m["lotus_old" if old else "lotus"]
    axis = Vector(axis).normalized()
    ref = Vector((1, 0, 0)) if abs(axis.x) < .9 else Vector((0, 1, 0))
    u = axis.cross(ref).normalized()
    w = axis.cross(u).normalized()
    base = Vector(base)
    rot0 = rng.uniform(0, math.tau)
    for layer, (count, scale, open_) in enumerate(((5, 1.0, .12 if not old else .3), (5, .9, .04))):
        for k in range(count):
            a0 = rot0 + (k + .5 * layer) * math.tau / count
            span = math.tau / count * 1.25

            def petal(uu, vv, a0=a0, span=span, scale=scale, open_=open_):
                a = a0 + (uu - .5) * span * (1 - .7 * vv)
                r = size * .32 * scale * math.sin(math.pi * min(1, vv * .92 + .05)) ** .75
                r += open_ * size * vv * vv * (1 - abs(uu - .5) * 2) * .5
                r *= 1 - .08 * (abs(uu - .5) * 2) ** 2
                z = size * scale * vv
                return base + axis * z + (u * math.cos(a) + w * math.sin(a)) * r

            b.grid(mat, petal, 4, 7, uv=lambda uu, vv: (uu, vv), smooth=True)
    if stem > 0:
        b.tube(m["stem"], [tuple(base - axis * stem), tuple(base + axis * .004)], .0028, sides=6)


def marigold(b, m, centre, rng, radius=.016, dead=False):
    """A marigold head: a dense ruffled pompom of petals over a ring of open ones."""
    mat = m["marigold_dead" if dead else "marigold"]
    centre = Vector(centre)
    r = radius
    ph = rng.uniform(0, math.tau)
    shrink = .8 if dead else 1.0
    b.lathe(mat, [(r * .55, 0), (r * .95, r * .2), (r * .92 * shrink, r * .55), (r * .62 * shrink, r * .85),
                  (r * .25, r * .98 * shrink), (0, r * shrink)], xf=Matrix.Translation(centre), segments=18, tile=.05,
            radial=lambda a, h: 1 + .13 * math.sin(a * 13 + ph + h * 300) * math.sin(h * 900 + a * 3))
    for k in range(9):
        a = ph + k * math.tau / 9
        d = Vector((math.cos(a), math.sin(a), .25 - (.3 if dead else 0)))
        p0 = centre + Vector((math.cos(a), math.sin(a), 0)) * r * .6 + Vector((0, 0, r * .15))
        b.tube(mat, [tuple(p0), tuple(p0 + d * r * .55)], [r * .32, r * .2], sides=4, flatten=.3, cap_end=True)


def jasmine_string(b, m, points, rng):
    """Jasmine buds threaded on a string, browned by days in the heat."""
    for i in range(len(points) - 1):
        a, c = Vector(points[i]), Vector(points[i + 1])
        for t in np.linspace(0, 1, 4, endpoint=False):
            p = a.lerp(c, t)
            d = Vector(rng.normal(0, 1, 3)).normalized()
            b.tube(m["jasmine" if rng.random() < .4 else "marigold_dead"], [tuple(p - d * .006), tuple(p + d * .006)],
                   [.003, .0012], sides=5, cap_end=True)


# --------------------------------------------------------------- the rest


def coconut(b, m, xf, rng, height=.21, radius=.085):
    """A whole young green coconut lying on its side: three soft ridges, the
    germination end a blunt point, the brown star of its calyx at the stalk."""
    prof = [(0, 0)]
    for k in range(1, 16):
        t = k / 15
        r = radius * math.sin(math.pi * t) ** .62 * (1 + .08 * (t - .5))
        prof.append((r, height * t))
    prof.append((0, height))
    turn = rng.uniform(0, math.tau)
    lie = place(0, 0, radius * .93) @ Matrix.Rotation(math.pi / 2 - .12, 4, "Y") @ Matrix.Translation((0, 0, -height / 2))
    b.lathe(m["coconut"], prof, xf=xf @ lie, segments=36, tile=height,
            radial=lambda a, h: 1 - .055 * (1 - math.cos(3 * (a + turn))) * math.sin(math.pi * h / height) ** 2, cap=False)
    # The calyx: four stiff brown sepals in a star round the stalk.
    top = xf @ lie
    for k in range(4):
        a = turn + k * math.tau / 4 + rng.normal(0, .1)
        d = Vector((math.cos(a), math.sin(a), -.35))
        base = Vector((0, 0, height - .004))
        b.sweep(m["banana_crown"], [tuple(top @ (base + d * t * .045)) for t in (0, .5, 1)], tuple(top.to_3x3() @
                Vector((-math.sin(a), math.cos(a), 0)).cross(d).normalized()), [.024, .018, .004], .003, tile=.1)
    b.tube(m["banana_crown"], [tuple(top @ Vector((0, 0, height - .006))), tuple(top @ Vector((.003, 0, height + .012)))],
           [.006, .004], sides=6, cap_end=True)


def leaf_cup(b, m, xf, rng, size=.075, height=.04, fill="flowers", old=False):
    """A kantong: a strip of banana leaf folded into a square cup, its corners
    pleated and pinned with slivers of bamboo, filled with flowers, rice or
    betel. `old`: the leaf gone brown and slack."""
    leaf = m["leaf_dry" if old else "leaf"]
    h = size / 2
    corners = [(-h, -h), (h, -h), (h, h), (-h, h)]
    sag = .006 if not old else .012
    # Walls: one strip round the four sides, bulging and wavy along the top.
    n_side = 8
    ring = []
    for c in range(4):
        (x0, y0), (x1, y1) = corners[c], corners[(c + 1) % 4]
        for k in range(n_side):
            t = k / n_side
            ring.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, math.sin(math.pi * t)))
    ring.append(ring[0])
    verts, faces, uvs = [], [], []
    wob = rng.uniform(0, math.tau)
    for i, (x, y, bulge) in enumerate(ring):
        out = Vector((x, y, 0)).normalized()
        u = i / (len(ring) - 1)
        for j, f in enumerate((0, .5, 1)):
            top = height * (1 - (.15 if old else .05) * math.sin(u * 23 + wob)) * (.98 - .2 * (1 - bulge) * 0)
            z = f * top - (sag * bulge if f == 1 and old else 0)
            p = Vector((x, y, z)) + out * (bulge * .004 * (1 - abs(f - .5) * 2) + f * .004)
            verts.append(tuple(xf @ p))
            uvs.append((u * 4, f))
    cols = 3
    for i in range(len(ring) - 1):
        for j in range(cols - 1):
            a = i * cols + j
            faces.append((a, a + cols, a + cols + 1, a + 1))
    b.add(leaf, verts, faces, uvs, smooth=True)
    # The floor.
    b.add(leaf, [tuple(xf @ Vector((x, y, .001))) for x, y in corners], [(0, 1, 2, 3)],
          [(0, 0), (1, 0), (1, 1), (0, 1)], smooth=False)
    # Pleated corners pinned with bamboo slivers.
    for x, y in corners:
        out = Vector((x, y, 0)).normalized()
        p = Vector((x, y, height * .6)) + out * .006
        tangent = Vector((-out.y, out.x, 0))
        b.add(leaf, [tuple(xf @ q) for q in (p - Vector((0, 0, height * .5)), p + out * .01, p + Vector((0, 0, height * .4)))],
              [(0, 1, 2)], [(0, 0), (1, .5), (0, 1)], smooth=False)
        b.tube(m["bamboo"], [tuple(xf @ (p - tangent * .012)), tuple(xf @ (p + tangent * .012))], .0009, sides=4)
    # What is in it.
    if fill == "flowers":
        for k in range(5):
            q = Vector((rng.uniform(-h * .55, h * .55), rng.uniform(-h * .55, h * .55), height * .55))
            marigold(b, m, xf @ q, rng, radius=.012, dead=old)
        for k in range(14):
            q = xf @ Vector((rng.uniform(-h * .7, h * .7), rng.uniform(-h * .7, h * .7), height * .6))
            d = Vector(rng.normal(0, 1, 3)).normalized()
            b.tube(m["jasmine" if not old else "marigold_dead"], [tuple(q - d * .005), tuple(q + d * .005)],
                   [.0028, .0011], sides=5, cap_end=True)
    elif fill == "rice":
        b.lathe(m["rice"], [(h * .9, height * .45), (h * .5, height * .62), (0, height * .66)], xf=xf, segments=16,
                tile=.1, radial=lambda a, z: 1 / max(abs(math.cos(a)), abs(math.sin(a))) ** .8)
        rice_grains(b, m, xf @ Vector((0, 0, height * .66)), rng, count=30, spread=h * .4)
    elif fill == "betel":
        for k in range(3):
            a = k * 2.1 + rng.uniform(0, .5)
            base = Vector((math.cos(a) * h * .3, math.sin(a) * h * .3, height * .3))
            axis = Vector((math.cos(a) * .7, math.sin(a) * .7, 1)).normalized()
            tip = base + axis * .045

            def cone(u, v, base=base, axis=axis):
                ang = u * math.tau
                ref = axis.cross(Vector((0, 0, 1))).normalized()
                w = axis.cross(ref)
                r = .011 * (1 - v)
                return xf @ (base + axis * .045 * v + (ref * math.cos(ang) + w * math.sin(ang)) * r)

            b.grid(m["betel"], cone, 10, 3, uv=lambda u, v: (u, v), smooth=True)


def small_cup(b, m, xf, rng, radius=.025, height=.035, liquid=None):
    """A tiny clay cup for water or rice wine."""
    b.lathe(m["clay"], [(0, 0), (radius * .7, 0), (radius * .72, .003), (radius, height), (radius * .9, height),
                        (radius * .66, .006), (0, .005)], xf=xf, segments=20, tile=.25, cap=False)
    if liquid:
        b.lathe(m[liquid], [(radius * .9, height * .7), (0, height * .7)], xf=xf, segments=18, tile=.1, cap=False)


def bananas(b, m, xf, rng, count=6, length=.1):
    """A hand of small Khmer bananas (chek ambong) lying on a plate: a row of
    fingers side by side from one crown, curving up, gone spotted and brown."""
    gap = .025
    b.lathe(m["banana_crown"], [(.006, 0), (.009, .004), (.009, (count - 1) * gap + .004), (.006, (count - 1) * gap + .008)],
            xf=xf @ Matrix.Translation((0, -(count - 1) * gap / 2 - .004, .016)) @ Matrix.Rotation(-math.pi / 2, 4, "X"),
            segments=8, tile=.05)
    for k in range(count):
        off = (k - (count - 1) / 2) * gap
        fan = off * 1.2 + rng.normal(0, .02)
        lift = .004 * abs(k - (count - 1) / 2)
        L = length * rng.uniform(.9, 1.06)
        pts, rad = [], []
        for i in range(13):
            t = i / 12
            x = .006 + L * t
            z = .013 + .03 * t * t + lift
            pts.append(xf @ Vector((x * math.cos(fan), off + x * math.sin(fan), z)))
            r = .0045 + .0085 * math.sin(math.pi * min(1, t * 1.2)) ** .6
            if t > .9:
                r *= max(.35, 1 - (t - .9) * 7)
            rad.append(r)
        b.tube(m["banana"], [tuple(p) for p in pts], rad, sides=5, v0=0, v1=1, cap_end=True, flatten=.85)


def rice_grains(b, m, centre, rng, count=60, spread=.03):
    centre = Vector(centre)
    for k in range(count):
        a = rng.uniform(0, math.tau)
        r = abs(rng.normal(0, spread))
        p = centre + Vector((r * math.cos(a), r * math.sin(a), .0012))
        d = Vector((math.cos(a * 3), math.sin(a * 3), 0)) * .0032
        b.tube(m["rice"], [tuple(p - d), tuple(p + d)], .0011, sides=4, cap_end=True)
