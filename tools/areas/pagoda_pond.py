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
WATER = -.2


def shore_radius(a):
    """Distance from the centre to the shore at bearing `a`, an uneven oval inside the
    barriers (X +/-18, Y 17.6..38.6). The south shore passes the bridge foot at Y 18.2."""
    rx, ry = 16.6, 9.9
    wobble = 1 + .06 * math.sin(a * 3 + .7) + .045 * math.sin(a * 5 + 2.1) + .03 * math.sin(a * 9)
    return rx * ry / math.hypot(ry * math.cos(a), rx * math.sin(a)) * wobble


def inside(x, y, margin=0.0):
    a = math.atan2(y - CENTRE[1], x - CENTRE[0])
    return math.hypot(x - CENTRE[0], y - CENTRE[1]) < shore_radius(a) - margin


def pond_materials():
    return {
        'pond_water': plain('M_ep2_pond_water', (.008, .014, .012), rough=.06, metal=.25),
        'scum': plain('M_ep2_pond_scum', (.06, .09, .03), rough=.9),
        'lotus_dead': plain('M_ep2_lotus_dead', (.16, .1, .05), rough=.9),
    }


def build_pond(coll, m, rng):
    """Basin, banks, water and dressing. Returns the bounds the flat ground must leave out."""
    made = []
    cx, cy = CENTRE
    # The basin: a heightfield over the pond's bounding box, flat at the edge, shelving
    # past the shore to a silted floor. Mud near the water, earth further out.
    x0, x1, y0, y1 = -18.6, 18.6, 17.4, 39.2
    nx, ny = 76, 44
    verts, faces = [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x, y = x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny
            a = math.atan2(y - cy, x - cx)
            d = math.hypot(x - cx, y - cy) - shore_radius(a)
            # d < 0 is under water. A short bank above the waterline, then a soft shelf.
            if d > 1.4:
                z = -.01
            elif d > 0:
                z = -.01 - (1.4 - d) / 1.4 * .16
            else:
                z = WATER - .02 - min(.9, -d * .35)
            z += rng.normal(0, .012)
            verts.append((x, y, z))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    made.append(mesh_object('pond_basin', coll, verts, faces, m['mud'], smooth=True))
    # Black water: one sheet following the shore, slightly past it so no gap shows.
    outline = [(cx + math.cos(a) * (shore_radius(a) + .25), cy + math.sin(a) * (shore_radius(a) + .25), WATER)
               for a in np.linspace(0, math.tau, 96, endpoint=False)]
    water = mesh_object('pond_water', coll, [(cx, cy, WATER)] + outline,
                        [(0, k + 1, (k + 1) % len(outline) + 1) for k in range(len(outline))], m['pond_water'])
    made.append(water)
    # Scum and algae in drifts along the still edges.
    c = Craft()
    for _ in range(26):
        a = rng.uniform(0, math.tau)
        r = shore_radius(a) - rng.uniform(.2, 2.8)
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
        made.append(lathe('lotus_pad', coll, [(0, 0), (rr, 0), (rr, .008), (0, .008)], px, py, WATER + .004, m['lotus_leaf'], segments=12))
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
    for _ in range(900):
        a = rng.uniform(0, math.tau)
        r = shore_radius(a) + rng.uniform(-1.2, 1.0)
        px, py = cx + math.cos(a) * r, cy + math.sin(a) * r
        if abs(px) < 1.8 and py < 19.5 or abs(px) > 18.2 or not 17.6 < py < 38.8:
            continue
        reeds.append((px, py, WATER if r < shore_radius(a) else -.06))
    # Stones on the bank and fallen bricks in the shallows.
    for k in range(16):
        a = rng.uniform(0, math.tau)
        r = shore_radius(a) + rng.uniform(-.3, .8)
        made += rubble(coll, m, f'pond_bank_stones_{k}', cx + math.cos(a) * r, cy + math.sin(a) * r, .6, 14, rng,
                       mats=[m['mould_grey'], m['brick']], size=(.22, .18, .1))
    # Broken stone steps down to the water beside the bridge foot.
    c = Craft()
    for k in range(5):
        for side in (-1, 1):
            if (k, side) in ((3, 1), (4, -1)):
                continue  # steps fallen in
            sx = side * 3.1
            c.block(m['mould_grey'], sx, 18.0 + k * .38, -.04 - k * .045, 2.2, .4, .09)
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
