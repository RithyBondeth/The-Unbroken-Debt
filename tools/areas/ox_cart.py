"""The Khmer ox cart (រទេះគោ), built as village carts were and left to rot.

Two tall wheels of fourteen spokes in segmented wooden felloes under a thin iron
tyre, turned hubs bound with iron, an axle under a slatted bed whose two side
beams sweep up behind and run forward into one long curved pole, the yoke with
its upturned ends lying at the pole's tip. Lattice sides of lashed bamboo; on a
passenger cart, a barrel hood of woven bamboo over arched ribs and battens.

Then the years and the night: grey weathered wood, mud dried up the wheels, a
spoke gone and another snapped, a plank missing, webs strung between the
spokes, rotten straw, the hood torn and fraying. The cart on the road wears the
driver's yantra cloth and an old lamp nobody lit; the one behind the house holds
something long rolled in a reed mat and roped, and has dripped onto the ground.

References (user, 2026-11-07): a museum Khmer passenger cart with a woven
barrel hood and a village cart with slatted bamboo sides. Advisor-review: the
wrapped bundle and the yantra cloth. Blender metres, local +Y forward, Z up.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

from kit import collider, empty, lathe, mesh_object, tube

R = 0.72          # wheel radius
TRACK = 0.86      # half the distance between the wheels
BED = R + 0.1     # top of the side beams


def _wheel(name, coll, m, side, rng, broken=False, lean=0.0):
    """One wheel at x = side: felloes, tyre, tapered spokes and an iron-bound hub."""
    parts = []
    x = side
    # Segmented felloes: seven arcs of squared timber with a joint between each.
    for s in range(7):
        a0, a1 = s * math.tau / 7 + .02, (s + 1) * math.tau / 7 - .02
        arc = [(x, (R - .03) * math.cos(a), R + (R - .03) * math.sin(a)) for a in np.linspace(a0, a1, 6)]
        # The lower felloes are caked with the road's dried mud.
        caked = math.sin((a0 + a1) / 2) < -.35
        parts.append(tube(f'{name}_felloe_{s}', coll, arc, .045 if not caked else .05, m['mud'] if caked else m['old_planks'], sides=4))
    tyre = [(x, (R + .012) * math.cos(a), R + (R + .012) * math.sin(a)) for a in np.linspace(0, math.tau, 49)]
    parts.append(tube(f'{name}_tyre', coll, tyre, .016, m['iron'], sides=5))
    for k in range(14):
        if broken and k == 3:
            continue  # lost
        a = k * math.tau / 14 + .05
        end = .93 if not (broken and k == 8) else .5  # snapped halfway
        tip = (x + rng.normal(0, .004), (R - .06) * end * math.cos(a), R + (R - .06) * end * math.sin(a))
        parts.append(tube(f'{name}_spoke_{k}', coll, [(x, .09 * math.cos(a), R + .09 * math.sin(a)), tip],
                          .028, m['worn'], sides=6, radius_end=.017))
    hub = lathe(f'{name}_hub', coll, [(0, -.17), (.07, -.17), (.1, -.12), (.115, 0), (.1, .12), (.07, .17), (0, .17)],
                0, 0, 0, m['worn'], segments=16)
    hub.location = (x, 0, R)
    hub.rotation_euler = (0, math.radians(90), 0)
    parts.append(hub)
    for off in (-.13, .13):
        band = lathe(f'{name}_hub_band', coll, [(.104, -.012), (.112, 0), (.104, .012)], 0, 0, 0, m['iron'], segments=16)
        band.location = (x + off, 0, R)
        band.rotation_euler = (0, math.radians(90), 0)
        parts.append(band)
    # The linchpin through the axle end.
    out = 1 if side > 0 else -1
    parts.append(tube(f'{name}_linchpin', coll, [(x + out * .2, 0, R + .06), (x + out * .2, 0, R - .08)], .01, m['iron'], sides=4))
    bpy.context.view_layer.update()
    if lean:
        pivot = Vector((x, 0, 0))
        rot = Matrix.Rotation(lean, 4, 'Y')
        for p in parts:
            p.data.transform(p.matrix_world)
            p.matrix_world = Matrix.Identity(4)
            for v in p.data.vertices:
                v.co = pivot + (rot @ (v.co - pivot))
            p.location = (0, 0, 0)
            p.rotation_euler = (0, 0, 0)
    return parts


def _hood(name, coll, m, y0, y1, rng, torn=True):
    """A barrel vault of woven bamboo with a thickness, arched ribs and battens,
    lashed down; a hole torn in it and fraying strips at the front edge."""
    parts = []
    w, base, h = .66, BED + .5, .58
    n, k = 18, 14
    hole = lambda i, j: torn and 9 <= i <= 12 and 3 <= j <= 5

    def at(i, j, off):
        a = math.pi * i / n
        y = y0 + (y1 - y0) * j / k
        return (-(w + off) * math.cos(a), y, base + (h + off) * math.sin(a))
    verts, faces, uvs = [], [], []
    for layer, off in enumerate((.02, -.015)):
        b = len(verts)
        for j in range(k + 1):
            for i in range(n + 1):
                verts.append(at(i, j, off))
        for j in range(k):
            for i in range(n):
                if hole(i, j):
                    continue
                q = b + j * (n + 1) + i
                f = (q, q + 1, q + n + 2, q + n + 1)
                faces.append(f if layer == 0 else tuple(reversed(f)))
                uvs += [(i / n * 1.6, j / k * 2), ((i + 1) / n * 1.6, j / k * 2), ((i + 1) / n * 1.6, (j + 1) / k * 2), (i / n * 1.6, (j + 1) / k * 2)]
                if layer:
                    uvs[-4:] = list(reversed(uvs[-4:]))
    # Close the two ends' edges so the shell has a visible thickness.
    stride = (n + 1) * (k + 1)
    for j in (0, k):
        for i in range(n):
            q = j * (n + 1) + i
            faces.append((q, q + 1, q + 1 + stride, q + stride))
            uvs += [(0, 0), (1, 0), (1, .05), (0, .05)]
    parts.append(mesh_object(f'{name}_hood_shell', coll, verts, faces, m['bamboo_wall_2s'], uvs=uvs, smooth=True))
    # Arched ribs, and battens running the length, lashed where they cross.
    for j in (0, 3, 7, 11, 14):
        arch = [at(i, j, .04) for i in range(n + 1)]
        parts.append(tube(f'{name}_hood_rib_{j}', coll, arch, .016, m['bamboo'], sides=6))
    for i in (1, 4, 7, 9, 11, 14, 17):
        parts.append(tube(f'{name}_hood_batten_{i}', coll, [at(i, 0, .055), at(i, k, .055)], .009, m['bamboo'], sides=5))
        for j in (0, 3, 7, 11, 14):
            c = Vector(at(i, j, .05))
            parts.append(tube(f'{name}_hood_lash_{i}_{j}', coll, [tuple(c + Vector((0, -.02, 0))), tuple(c + Vector((0, .02, 0)))],
                              .013, m['rattan'], sides=5))
    # The weave fraying loose at the torn hole and the front edge.
    for q in range(40):
        i = rng.uniform(0, n)
        top = Vector(at(i, k, 0))
        length = rng.uniform(.04, .2)
        parts.append(tube(f'{name}_hood_fray_{q}', coll, [tuple(top), tuple(top + Vector((rng.normal(0, .02), .02, -length)))],
                          .004, m['bamboo_wall_2s'], sides=3, radius_end=.0015))
    for q in range(16):
        i, j = rng.uniform(9, 13), rng.uniform(3, 6)
        top = Vector(at(i, j, 0))
        parts.append(tube(f'{name}_hood_torn_{q}', coll, [tuple(top), tuple(top + Vector((rng.normal(0, .05), rng.normal(0, .05), -rng.uniform(.05, .2))))],
                          .005, m['bamboo_wall_2s'], sides=3, radius_end=.002))
    # The posts it is lashed to, at each corner of the bed.
    for sx in (-w, w):
        for y in (y0 + .05, y1 - .05):
            parts.append(tube(f'{name}_hood_post', coll, [(sx * .97, y, BED), (sx, y, base + .02)], .02, m['bamboo'], sides=6))
    return parts


def ox_cart_detailed(coll, m, name, x, y, rot, hood=False):
    rng = np.random.default_rng(sum(map(ord, name)))
    parent = empty(name, coll, (x, y, 0), (0, 0, rot))
    parts = []
    # Wheels: the yard cart's left wheel has lost a spoke, snapped another and leans.
    yard = not hood
    for side in (-TRACK, TRACK):
        parts += _wheel(f'{name}_wheel_{"l" if side < 0 else "r"}', coll, m, side, rng,
                        broken=yard and side < 0, lean=(.06 if yard and side < 0 else rng.normal(0, .012)))
    parts.append(tube(f'{name}_axle', coll, [(-TRACK - .22, 0, R), (TRACK + .22, 0, R)], .05, m['worn'], sides=8))
    # Two side beams on bolsters over the axle, swept up behind, run forward into the pole.
    for sx in (-.55, .55):
        beam = [(sx, -1.75, BED + .32), (sx, -1.55, BED + .1), (sx, -1.2, BED), (sx, 1.2, BED), (sx * .55, 1.9, BED - .05), (sx * .15, 2.5, BED - .1)]
        parts.append(tube(f'{name}_side_beam_{sx:+.1f}', coll, beam, .055, m['worn'], sides=6))
    parts.append(tube(f'{name}_bolster', coll, [(-.62, 0, R + .06), (.62, 0, R + .06)], .05, m['old_planks'], sides=4))
    # The pole: one long timber curving down to the ground and up at its tip, as
    # it lies with the oxen gone; a forked stick props the yard cart's.
    rest = .55 if hood else .42
    pole = [(0, 2.4, BED - .1), (0, 3.2, BED - .3), (0, 4.0, rest + .1), (0, 4.6, rest), (0, 4.95, rest + .18), (0, 5.15, rest + .45)]
    parts.append(tube(f'{name}_pole', coll, pole, .055, m['worn'], sides=7, radius_end=.035))
    parts.append(tube(f'{name}_prop', coll, [(.05, 4.5, 0), (.02, 4.55, rest - .02)], .03, m['post_rough'], sides=5))
    parts.append(tube(f'{name}_prop_fork', coll, [(.02, 4.55, rest - .08), (-.06, 4.52, rest + .05)], .02, m['post_rough'], sides=5))
    # The yoke with its upturned ends, and its pegs.
    yoke = [(-.8, 4.75, rest + .38), (-.6, 4.75, rest + .22), (0, 4.75, rest + .16), (.6, 4.75, rest + .22), (.8, 4.75, rest + .38)]
    if yard:
        # Unhitched and dropped beside the cart.
        yoke = [(1.1 + .2 * t, 3.4 + 1.4 * t, .05 + .05 * abs(t - .5)) for t in (0, .15, .5, .85, 1)]
    parts.append(tube(f'{name}_yoke', coll, yoke, .045, m['worn'], sides=6))
    for t in (.25, .75):
        p = Vector(yoke[0]).lerp(Vector(yoke[-1]), t)
        parts.append(tube(f'{name}_yoke_peg', coll, [tuple(p), tuple(p + Vector((0, 0, -.22 if not yard else .02)) + (Vector((0, .2, 0)) if yard else Vector()))],
                          .015, m['worn'], sides=5))
    # The bed: planks across on bearers, gaps between, one plank gone.
    for k in range(17):
        if yard and k == 11:
            continue
        py = -1.2 + k * .15
        parts.append(mesh_object(f'{name}_plank_{k}', coll,
                                 [(-.6, py, BED + .055), (.6, py + rng.normal(0, .004), BED + .055), (.6, py + .135, BED + .055), (-.6, py + .135, BED + .055)],
                                 [(0, 1, 2, 3)], m['old_planks']))
    for sx in (-.4, 0, .4):
        parts.append(tube(f'{name}_bearer', coll, [(sx, -1.2, BED + .03), (sx, 1.35, BED + .03)], .025, m['old_planks'], sides=4))
    # Lattice sides of bamboo, lashed at the crossings.
    top = BED + (.5 if hood else .55)
    for sx in (-.62, .62):
        for k in range(9):
            sy = -1.15 + k * .31
            parts.append(tube(f'{name}_upright', coll, [(sx, sy, BED + .05), (sx * 1.03, sy, top)], .016, m['bamboo'], sides=5))
        for z in ((BED + .2, top) if hood else (BED + .18, BED + .36, top)):
            parts.append(tube(f'{name}_rail', coll, [(sx, -1.2, z), (sx * 1.02, 1.35, z)], .018, m['bamboo'], sides=5))
    # Weathering: mud dried up the lower wheels, moss on the beams' shaded side.
    stains = bpy.data.materials.get('M_house_detail_weather_stains')
    if stains:
        from house_decay import Decals, MILDEW
        d = Decals()
        for sx in (-.55, .55):
            d.add(MILDEW, (sx + (.06 if sx > 0 else -.06), -.6, BED - .05), (0, 1, 0), (0, 0, 1), .9, .12, (1 if sx > 0 else -1, 0, 0), offset=.002)
        parts.append(d.finish(f'{name}_weathering', coll, stains))
    # Webs strung between the spokes of both wheels.
    from house_detail import corner_web
    for side in (-TRACK, TRACK):
        for a in (.6, 2.9):
            c = (side, .35 * math.cos(a), R + .35 * math.sin(a))
            parts.append(corner_web(f'{name}_spoke_web', coll, c, (0, math.cos(a + 1.6), math.sin(a + 1.6)), (0, -math.sin(a), math.cos(a)), .3))
    # Rotten straw over the bed.
    strands = []
    for q in range(90):
        px, py = rng.uniform(-.55, .55), rng.uniform(-1.1, 1.25)
        a = rng.uniform(0, math.tau)
        L = rng.uniform(.05, .14)
        strands.append(tube(f'{name}_straw', coll, [(px, py, BED + .062), (px + math.cos(a) * L, py + math.sin(a) * L, BED + .064)],
                            .0025, m['betel_leaf_dry'], sides=3))
    parts += strands
    if hood:
        parts += _hood(name, coll, m, -1.05, 1.2, rng)
        # The driver's yantra cloth tied at the hood's mouth, and a lamp nobody lit.
        cloth = []
        for j in range(7):
            v = j / 6
            for i in range(5):
                u = i / 4 - .5
                cloth.append((u * .32 + .02 * math.sin(v * 5), 1.28 + .02 * math.sin(u * 7) * v, BED + 1.05 - v * .38))
        faces = [(j * 5 + i, j * 5 + i + 1, (j + 1) * 5 + i + 1, (j + 1) * 5 + i) for j in range(6) for i in range(4)]
        parts.append(mesh_object(f'{name}_yantra_cloth', coll, cloth, faces, m['yantra'],
                                 uvs=[uv for j in range(6) for i in range(4) for uv in ((i / 4, 1 - j / 6), ((i + 1) / 4, 1 - j / 6), ((i + 1) / 4, 1 - (j + 1) / 6), (i / 4, 1 - (j + 1) / 6))]))
        parts.append(tube(f'{name}_lamp_cord', coll, [(.45, 1.15, BED + 1.0), (.45, 1.15, BED + .78)], .003, m['rope'], sides=4))
        parts.append(lathe(f'{name}_lamp', coll, [(0, 0), (.05, 0), (.055, .04), (.03, .07), (.035, .14), (.02, .18), (0, .18)],
                           .45, 1.15, BED + .6, m['iron'], segments=12))
        # A single sandal left on the bed.
        parts.append(mesh_object(f'{name}_sandal', coll, [(-.2, .3, BED + .06), (-.12, .32, BED + .06), (-.1, .56, BED + .06), (-.2, .55, BED + .06)],
                                 [(0, 1, 2, 3)], m['sandal']))
    else:
        # Something long, rolled in a reed mat and roped, in the back of the cart.
        bundle = lathe(f'{name}_mat_bundle', coll, [(0, -.85), (.14, -.84), (.19, -.75), (.2, 0), (.18, .75), (.12, .85), (0, .86)],
                       0, 0, 0, m['bamboo_wall_2s'], segments=16)
        bundle.rotation_euler = (math.radians(90), 0, math.radians(4))
        bundle.location = (.05, -.05, BED + .27)
        parts.append(bundle)
        for t in (-.6, 0, .55):
            loop = [(.05 + .215 * math.cos(a), -.05 + t, BED + .27 + .215 * math.sin(a)) for a in np.linspace(0, math.tau, 17)]
            parts.append(tube(f'{name}_bundle_rope', coll, loop, .008, m['rope'], sides=5))
        if stains:
            dread = bpy.data.materials.get('M_house_detail_dread_stains')
            if dread:
                from house_decay import Decals
                d = Decals()
                d.add(0, (0, -.2, .03), (1, 0, 0), (0, 1, 0), .8, .6, (0, 0, 1), offset=.01)
                d.add(1, (.6, -.2, BED - .3), (0, 1, 0), (0, 0, 1), .45, .32, (1, 0, 0), offset=.006)
                parts.append(d.finish(f'{name}_drip', coll, dread))
    # Block the body and wheels; the pole, yoke and props stay walkable.
    bpy.context.view_layer.update()
    body = [o for o in parts if o.type == 'MESH' and not any(k in o.name for k in ('pole', 'prop', 'yoke', 'web', 'straw', 'drip'))]
    local = [o.matrix_world @ v.co for o in body for v in o.data.vertices]
    # One mesh per material: the cart costs a handful of draws, not hundreds.
    from khmer import join
    groups = {}
    for o in parts:
        groups.setdefault(o.active_material.name if o.active_material else '', []).append(o)
    parts = [join(objs, f'{name}_{i:02d}') if len(objs) > 1 else objs[0] for i, objs in enumerate(groups.values())]
    for i, p in enumerate(parts):
        p.name = p.data.name = f'{name}_{i:02d}'
        p.parent = parent
    bpy.context.view_layer.update()
    pts = [parent.matrix_world @ p for p in local]
    xs, ys = [p.x for p in pts], [p.y for p in pts]
    collider(name, coll, min(xs), max(xs), min(ys), max(ys), 0, 1.6)
    return parent
