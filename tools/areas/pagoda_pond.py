"""The lotus pond, rebuilt as a sunken, silted, neglected temple tank: an irregular
shore shelving into black water, broken stone steps, reeds and dead lotus, scum,
floating offerings, a sunken boat and a drowned stupa. Metres, X east, Y north.
The player never enters the water: the existing barriers and bridge are unchanged.
"""
import math

import numpy as np

from kit import collider, lathe, mesh_object, plain, tube, box
from pagoda_architecture import Craft
from pagoda_ruin import erode, rubble, lean, place_object

CENTRE = (0.0, 28.2)
# Well below the bank, so from eye height the water reads as a sunken sheet, not a line.
WATER = -.38
# The barriers (X +/-18, Y 17.6..38.6) and the bridge foot at Y 18.2 bound the shore.
SHORE_LIMIT = (18.0, 17.8, 38.4)


def _bump(a, at, width):
    """A smooth bump on the shoreline centred on bearing `at`."""
    d = (a - at + math.pi) % math.tau - math.pi
    return math.exp(-(d / width) ** 2)


def shore_radius(a):
    """Distance from the centre to the shore at bearing `a`: an old tank's oval worn into an
    irregular, natural edge (many octaves, never a clean curve), with a reed-choked cove in
    the north-west, a muddy point pushing out in the east and a slumped corner in the
    south-west. Kept inside the barriers; the south shore passes the bridge foot."""
    rx, ry = 16.6, 9.9
    wobble = (1 + .06 * math.sin(a * 3 + .7) + .045 * math.sin(a * 5 + 2.1) + .03 * math.sin(a * 9)
              + .022 * math.sin(a * 13 + 1.3) + .014 * math.sin(a * 21 + .4) + .009 * math.sin(a * 34 + 2.2))
    wobble += .08 * _bump(a, 2.35, .22) - .07 * _bump(a, -.15, .16) + .05 * _bump(a, 3.95, .14)
    r = rx * ry / math.hypot(ry * math.cos(a), rx * math.sin(a)) * wobble
    xmax, ymin, ymax = SHORE_LIMIT
    c, s = math.cos(a), math.sin(a)
    limit = xmax / abs(c) if abs(c) > 1e-6 else 1e9
    if s > 1e-6:
        limit = min(limit, (ymax - CENTRE[1]) / s)
    elif s < -1e-6:
        limit = min(limit, (CENTRE[1] - ymin) / -s)
    return min(r, limit)


def inside(x, y, margin=0.0):
    a = math.atan2(y - CENTRE[1], x - CENTRE[0])
    return math.hypot(x - CENTRE[0], y - CENTRE[1]) < shore_radius(a) - margin


def pond_materials():
    return {
        'pond_water': plain('M_ep2_pond_water', (.008, .014, .012), rough=.06, metal=.25),
        'scum': plain('M_ep2_pond_scum', (.06, .09, .03), rough=.9),
        'lotus_dead': plain('M_ep2_lotus_dead', (.16, .1, .05), rough=.9),
        # Silt at the waterline: darker and slick where the water laps it.
        'mud_wet': plain('M_ep2_mud_wet', (.035, .03, .022), rough=.35),
    }


def build_pond(coll, m, rng):
    """Basin, banks, water and dressing. Returns the bounds the flat ground must leave out."""
    made = []
    cx, cy = CENTRE
    # The basin: a heightfield over the pond's bounding box, flat at the edge, then a steep,
    # broken mud bank down to the water, then a silted shelf. The band either side of the
    # waterline is wet mud, darker and slick.
    x0, x1, y0, y1 = -18.6, 18.6, 17.4, 39.2
    nx, ny = 92, 54
    verts, dry, wet = [], [], []
    bank = 1.9
    for j in range(ny + 1):
        for i in range(nx + 1):
            x, y = x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny
            a = math.atan2(y - cy, x - cx)
            d = math.hypot(x - cx, y - cy) - shore_radius(a)
            if d > bank:
                z = -.01
            elif d > 0:
                # Convex: the bank breaks steeply near the water, as banks the water has
                # undercut do, with slumps and ledges along it.
                t = d / bank
                z = -.01 - (1 - t) ** 1.7 * (-WATER - .02)
                z += .035 * math.sin(a * 23 + d * 3.1) * (1 - t) + rng.normal(0, .01)
            else:
                z = WATER - .02 - min(1.1, -d * .45)
            z += rng.normal(0, .008)
            verts.append((x, y, z))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            face = (a, a + 1, a + nx + 2, a + nx + 1)
            mx = sum(verts[k][0] for k in face) / 4
            my = sum(verts[k][1] for k in face) / 4
            d = math.hypot(mx - cx, my - cy) - shore_radius(math.atan2(my - cy, mx - cx))
            (wet if -.5 < d < .55 else dry).append(face)
    made.append(mesh_object('pond_basin', coll, verts, dry, m['mud'], smooth=True))
    made.append(mesh_object('pond_bank_wet', coll, verts, wet, m['mud_wet'], smooth=True))
    # The water: rings following the shore, fine enough to ripple, slightly past the shore so
    # no gap shows, with planar UVs for the drifting ripple normals (src/render/water).
    rings, segments = 14, 120
    wverts, wfaces, wuvs = [(cx, cy, WATER)], [], []
    for k in range(1, rings + 1):
        f = (k / rings) ** .8
        for i in range(segments):
            a = i / segments * math.tau
            r = (shore_radius(a) + .3) * f
            wverts.append((cx + math.cos(a) * r, cy + math.sin(a) * r, WATER))

    def ring(k, i):
        return 1 + (k - 1) * segments + i % segments
    for i in range(segments):
        wfaces.append((0, ring(1, i), ring(1, i + 1)))
    for k in range(1, rings):
        for i in range(segments):
            wfaces.append((ring(k, i), ring(k + 1, i), ring(k + 1, i + 1), ring(k, i + 1)))
    for face in wfaces:
        for v in face:
            wuvs.append((wverts[v][0] / 6, wverts[v][1] / 6))
    water = mesh_object('pond_water', coll, wverts, wfaces, m['pond_water'], uvs=wuvs)
    made.append(water)
    # Scum and algae in drifts along the still edges.
    c = Craft()
    for _ in range(64):
        a = rng.uniform(0, math.tau)
        r = shore_radius(a) - rng.uniform(.1, 3.4) ** 1.3
        px, py = cx + math.cos(a) * r, cy + math.sin(a) * r
        if abs(px) < 1.6 and py < 28.5:
            continue
        size = rng.uniform(.5, 1.6)
        pts = [(px + math.cos(t) * size * rng.uniform(.6, 1.2), py + math.sin(t) * size * rng.uniform(.4, 1), WATER + .006)
               for t in np.linspace(0, math.tau, 9, endpoint=False)]
        c.face(m['scum'], list(reversed(pts)))
    made += c.build('pond_scum', coll)
    # Lotus: pads on the water, dead stalks bent over with black seed heads.
    for k in range(150):
        a, r = rng.uniform(0, math.tau), rng.uniform(.5, 1) ** .5
        px, py = cx + math.cos(a) * shore_radius(a) * r * .95, cy + math.sin(a) * shore_radius(a) * r * .95
        if abs(px) < 1.6 and py < 28.6 or abs(px) < 5.2 and 27.4 < py < 36.6:
            continue
        rr = rng.uniform(.14, .38)
        # Pads float a little cupped, their rims lifting and curling as they age.
        made.append(lathe('lotus_pad', coll, [(0, 0), (rr * .7, .004), (rr, .012 + rr * .05), (rr * .97, .016 + rr * .05), (0, .008)],
                          px, py, WATER + .004, m['lotus_leaf'], segments=14))
        if k % 4 == 0:
            h = rng.uniform(.35, 1.0)
            bend = rng.uniform(.1, .45)
            ha = rng.uniform(0, math.tau)
            top = (px + math.cos(ha) * bend, py + math.sin(ha) * bend, WATER + h - bend * .5)
            made.append(tube('lotus_stalk_dead', coll, [(px, py, WATER), (px + math.cos(ha) * bend * .3, py + math.sin(ha) * bend * .3, WATER + h * .8), top],
                             .007, m['lotus_dead'], sides=4))
            made.append(lathe('lotus_seed_head', coll, [(.012, 0), (.04, .03), (.045, .05), (0, .055)], top[0], top[1], top[2] - .055, m['lotus_dead'], segments=10))
    # Reeds and rushes in the shallows and on the bank.
    reeds = []
    for _ in range(1700):
        a = rng.uniform(0, math.tau)
        # Thickest in the north-west cove, so the far shore never reads as one clean line.
        r = shore_radius(a) + rng.uniform(-1.6, 1.4) * (1 + .6 * _bump(a, 2.35, .4))
        px, py = cx + math.cos(a) * r, cy + math.sin(a) * r
        if abs(px) < 1.8 and py < 19.5 or abs(px) > 18.2 or not 17.6 < py < 38.8:
            continue
        d = r - shore_radius(a)
        reeds.append((px, py, WATER if d < 0 else -.01 - max(0, 1 - d / 1.9) ** 1.7 * (-WATER - .02)))
    # Stones on the bank and fallen bricks in the shallows.
    for k in range(16):
        a = rng.uniform(0, math.tau)
        r = shore_radius(a) + rng.uniform(-.3, .8)
        made += rubble(coll, m, f'pond_bank_stones_{k}', cx + math.cos(a) * r, cy + math.sin(a) * r, .6, 14, rng,
                       mats=[m['mould_grey'], m['brick']], size=(.22, .18, .1))
    # Roots of the bank trees, laid bare where the water ate the bank, reaching into the pond;
    # and branches fallen from the crowns, half sunk at the edge.
    for k in range(26):
        a = rng.uniform(0, math.tau)
        if abs(math.cos(a)) < .2 and math.sin(a) < 0:
            continue  # keep the bridge foot clear
        r0 = shore_radius(a)
        pts = []
        for t in np.linspace(0, 1, 7):
            d = 1.5 - t * 2.1
            rr = r0 + d
            z = -.01 - max(0, 1 - max(d, 0) / 1.9) ** 1.7 * (-WATER - .02) + .03 if d > 0 else WATER - .05 - t * .15
            aa = a + .05 * math.sin(t * 4 + k)
            pts.append((cx + math.cos(aa) * rr, cy + math.sin(aa) * rr, z + .02))
        made.append(tube(f'pond_bank_root_{k}', coll, pts, rng.uniform(.03, .07), m['bark'], sides=7, radius_end=.012))
    for k in range(7):
        a = rng.uniform(0, math.tau)
        if abs(math.cos(a)) < .25 and math.sin(a) < 0:
            continue
        r0 = shore_radius(a)
        length = rng.uniform(2.2, 4.2)
        turn = rng.normal(0, .5)
        pts = [(cx + math.cos(a + turn * t * .2) * (r0 + .8 - t * length), cy + math.sin(a + turn * t * .2) * (r0 + .8 - t * length),
                (-.02 if t < .2 else WATER + .03 - t * .12)) for t in np.linspace(0, 1, 6)]
        made.append(tube(f'pond_fallen_branch_{k}', coll, pts, rng.uniform(.05, .1), m['bark'], sides=8, radius_end=.025))
        for j in range(3):
            b = pts[int(rng.integers(1, 5))]
            ba = a + rng.uniform(-1.5, 1.5)
            made.append(tube(f'pond_fallen_twig_{k}', coll, [b, (b[0] + math.cos(ba) * .6, b[1] + math.sin(ba) * .6, b[2] + rng.uniform(-.05, .25))],
                             .018, m['bark'], sides=5, radius_end=.006))
    # Broken stone steps down to the water beside the bridge foot.
    c = Craft()
    for k in range(7):
        for side in (-1, 1):
            if (k, side) in ((3, 1), (4, -1), (6, 1)):
                continue  # steps fallen in
            sx = side * 3.1
            c.block(m['mould_grey'], sx, 18.0 + k * .36, -.04 - k * .055, 2.2, .4, .09)
    made += c.build('pond_steps', coll)
    erode(made[-2:], .02, 3)
    # A half-sunken sampan, bow up, rotten through.
    boat = []
    hull = []
    for k in range(13):
        t = k / 12
        w = .55 * math.sin(math.pi * t) + .04
        hull.append((w, t * 4.2))
    b = lathe('pond_sunken_boat', coll, [(r, z) for r, z in hull], 0, 0, 0, m['boards'], segments=10)
    place_object(b, -9.5, 33.5, WATER - .25, .7, (1.45, .25))
    boat.append(b)
    made += boat
    # A small drowned stupa leaning out of the north-west water.
    from pagoda_stupa import memorial
    drowned = memorial(coll, m, -11.5, 34.5, 400, 2.6, 'drowned', rng)
    for o in drowned:
        if o.get('kit_piece'):
            # Its mesh is shared with every stupa of its form: move the copy, not the mesh.
            o.location.z -= .9
            continue
        for v in o.data.vertices:
            v.co.z -= .9
    lean(drowned, -11.5, 34.5, .16, -.1)
    made += drowned
    # Banana-leaf float offerings with burnt-down candles, drifting at the edge.
    for k in range(7):
        a = rng.uniform(0, math.tau)
        r = shore_radius(a) - rng.uniform(.6, 2.5)
        px, py = cx + math.cos(a) * r, cy + math.sin(a) * r
        if abs(px) < 1.8 and py < 28.6:
            continue
        made.append(lathe('pond_float_offering', coll, [(0, 0), (.16, 0), (.18, .03), (.14, .06), (0, .05)], px, py, WATER, m['banana_leaf'], segments=12))
        made.append(lathe('pond_float_candle', coll, [(.012, 0), (.012, .03), (0, .033)], px, py, WATER + .05, m['wax'], segments=6))
        for j in range(3):
            made.append(tube('pond_float_incense', coll, [(px + j * .02 - .02, py, WATER + .05), (px + j * .03 - .03, py + .01, WATER + .14)], .002, m['red_cloth'], sides=3))
    return made, reeds, (x0, x1, y0, y1)
