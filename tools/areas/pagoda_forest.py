"""Old-growth jungle round the pagoda, matching Episode 1's forest (forest.py:
buttressed giants half again as tall, lianas, cables, epiphytes, cold deep greens).
Metres, X east, Y north. The compound wall is at X = +/-28 and Y = -27/41; the player
is held inside X +/-29.5, Y -39.5..41.5, so everything past that is set dressing.
"""
import math

import numpy as np

from forest import bamboo_clump, banyan, dead_tree, rag_tree, termite_mound, tropical_tree
from forest_detail import understory
from kit import collider, lathe, tube
from pagoda_ruin import creeper, fig_roots


def giant(coll, m, x, y, h, k, rng, reach=None, collision=False, crown=1.0):
    """A broadleaf giant. `reach` pulls buttress fins, root moss and low vines in
    towards the bole wherever the tree stands beside a walk."""
    tree = tropical_tree(coll, m, x, y, h, k, rng, crown=crown, collision=collision)
    if reach:
        for v in tree.data.vertices:
            if v.co.z > 3.4:
                continue
            dx, dy = v.co.x - x, v.co.y - y
            d = math.hypot(dx, dy)
            allowed = reach + max(0.0, v.co.z - 1.6) * .8
            if d > allowed:
                f = (allowed + (d - allowed) * .12) / d
                v.co.x, v.co.y = x + dx * f, y + dy * f
    return tree


def fallen_log(coll, m, name, x, y, yaw, length, r, rng):
    """A rotted trunk lying where it fell, its root plate torn up at one end."""
    ca, sa = math.cos(yaw), math.sin(yaw)
    pts = [(x + ca * length * t + rng.normal(0, .04), y + sa * length * t + rng.normal(0, .04), r * .8 + .06 * math.sin(t * 5)) for t in np.linspace(0, 1, 7)]
    parts = [tube(name, coll, pts, r, m['bark'], sides=10, metres_per_v=1.5, radius_end=r * .55)]
    parts.append(tube(name + '_moss', coll, [(p[0], p[1], p[2] + r * .82) for p in pts[:-1]], r * .35, m['moss'], sides=6, radius_end=r * .15))
    plate = lathe(name + '_root_plate', coll, [(0, -.2), (r * 2.4, -.1), (r * 2.6, .1), (r * 2.2, .2), (0, .15)], 0, 0, 0, m['earth'], segments=12)
    plate.location = (x - ca * .1, y - sa * .1, r * 1.2)
    plate.rotation_euler = (0, math.pi / 2, yaw)
    parts.append(plate)
    for j in range(7):
        a = rng.uniform(0, math.tau)
        parts.append(tube(name + '_torn_root', coll, [(x, y, r), (x - ca * .3 + math.cos(a) * r * 2, y - sa * .3 + math.sin(a) * r * 2, r + math.sin(a) * r * 2.2),
                                                      (x - ca * .5 + math.cos(a) * r * 3, y - sa * .5 + math.sin(a) * r * 3, r + math.sin(a) * r * 3)],
                          .05, m['bark'], sides=5, radius_end=.01))
    return parts


def outer_forest(coll, m, rng, avoid=(), clear=(), solid=()):
    """Three ranks of old growth beyond the walls and along the approach track."""
    trees = []
    k = 0
    # The rank pressed against the wall, then the deep rank, then the far wall of trunks.
    for x0, x1, step, hmin, hmax in [(29.6, 32.5, 4.4, 11, 16), (33, 38, 5.2, 13, 18), (38.5, 44, 9.5, 14, 19)]:
        for side in (-1, 1):
            y = -48 + rng.uniform(0, step)
            while y < 50:
                trees.append((side * rng.uniform(x0, x1), y, rng.uniform(hmin, hmax)))
                y += step * rng.uniform(.8, 1.2)
    for y0, y1 in [(42.2, 47.5)]:
        x = -28 + rng.uniform(0, 4)
        while x < 28:
            trees.append((x, rng.uniform(y0, y1), rng.uniform(12, 18)))
            x += rng.uniform(4.2, 6.2)
    for y0, y1 in [(-45, -41)]:
        x = -28 + rng.uniform(0, 4)
        while x < 28:
            trees.append((x, rng.uniform(y0, y1), rng.uniform(12, 18)))
            x += rng.uniform(4.2, 6.2)
    # The approach: a track hemmed in by trunks on both sides, open only near the middle.
    for x, y in [(-13, -37), (-18, -32.5), (-22.5, -38), (-26.5, -34), (13.5, -38.5), (17.5, -33), (22, -37.5), (26.8, -29.8),
                 (-7.2, -30.2), (6.7, -29.5)]:
        trees.append((x + rng.normal(0, .4), y + rng.normal(0, .4), rng.uniform(11, 15)))
    for x, y, h in trees:
        # Clearings the player walks into (x0, x1, y0, y1) keep only their ring of trunks.
        if any(x0 < x < x1 and y0 < y < y1 for x0, x1, y0, y1 in clear):
            continue
        # `solid` ground can be walked on, so what stands on it has to stop you.
        near_track = abs(y) < 40 and abs(x) < 28 or any(x0 < x < x1 and y0 < y < y1 for x0, x1, y0, y1 in solid)
        giant(coll, m, x, y, h, 700 + k, rng, reach=1.6 if near_track else None, collision=near_track,
              crown=rng.uniform(1.0, 1.2))
        k += 1

    def stop(name, x, y, r):
        # Out of bounds until the lost garden: what stands where you can now walk needs a body.
        if any(x0 < x < x1 and y0 < y < y1 for x0, x1, y0, y1 in solid):
            collider(name, coll, x - r, x + r, y - r, y + r, 0, 2.2, 'stone')

    # Dead giants and rag trees: someone still ties cloth here.
    for j, (x, y) in enumerate([(31.5, -12), (-32, 9), (34, 27), (-33.5, -30), (-6, 46), (18, -44), (-11, -33.2), (11.5, -31.4)]):
        dead_tree(coll, m, x, y, rng.uniform(8, 13), 820 + j, rng)
        stop(f'dead_tree_{j}', x, y, .6)
    rag_tree(coll, m, -5.6, -35.8, 0, rng)
    rag_tree(coll, m, 31.2, 4, 1, rng)
    stop('rag_tree', 31.2, 4, .5)
    for j, (x, y) in enumerate([(-16, -35), (20, -35.5), (-31, -17), (31, 20), (-31, 33), (8.5, -38.6), (-24, -29.8)]):
        termite_mound(coll, m, x, y, rng.uniform(.8, 1.6), 30 + j, rng)
        stop(f'termite_mound_{j}', x, y, .7)
    for j, (x, y, yaw, length) in enumerate([(-15.5, -31, .3, 7), (14, -30.4, 2.9, 6), (30, -24, 1.6, 9), (-30.5, 18, 1.4, 8), (6, 43, .1, 9)]):
        fallen_log(coll, m, f'fallen_log_{j}', x, y, yaw, length, rng.uniform(.3, .45), rng)
        if abs(x) < 28 and y < -28:
            collider(f'fallen_log_{j}', coll, *sorted([x, x + math.cos(yaw) * length]), *sorted([y - .4, y + math.sin(yaw) * length + .4]), 0, .8)
    # Stranglers gripping the wall from outside, their roots pouring over the coping.
    for j, (x, y, wx, wy, a0) in enumerate([(31.6, -14, 28, -14, math.pi), (-31.4, 26, -28, 26, 0), (-12, 44.2, -12, 41.5, -math.pi / 2)]):
        banyan(coll, m, x, y, rng, dressing=False)
        stop(f'wall_banyan_{j}', x, y, 1.4)
        wall = [o for o in coll.all_objects if o.name.startswith('compound_wall') and o.type == 'MESH'
                and _holds(o, wx, wy)]
        for bearing in (a0, a0 + math.pi):
            fig_roots(coll, m, f'wall_fig_{j}', wx, wy, 1.9, lambda z: .46, rng,
                      n=5, spread=1.0, around=(bearing - .45, bearing + .45), crown=0, support=wall, seat=0)
    for j, (x, y) in enumerate([(31, -36), (-31.5, -4), (33, 38), (-34, 40), (26, -44), (-25, -45), (35, 12), (-35, -16)]):
        bamboo_clump(coll, m, x, y, 40 + j, rng)
        stop(f'outer_bamboo_{j}', x, y, .7)
    # Floor of ferns and dead leaves outside the wall and along the track.
    spots = []
    # Fog swallows the floor beyond a few metres of the wall; keep the budget near it.
    for _ in range(2000):
        x, y = rng.uniform(-34, 34), rng.uniform(-43, 46)
        outside = abs(x) > 28.6 or y > 41.6
        approach = y < -27.6 and abs(x) > 4.2 and abs(x) < 28.6
        if (outside or approach) and not any((x - ax) ** 2 + (y - ay) ** 2 < r * r for ax, ay, r in avoid):
            spots.append((x, y))
    understory(coll, spots, rng, prefix='pagoda_jungle')
    # Lianas sagging between the outer crowns over the approach.
    for j, (a, b) in enumerate([((-7, -30, 12), (6.7, -29.5, 13)), ((-13, -37, 14), (-7, -30, 11)), ((6.7, -29.5, 12), (13.5, -38.5, 13))]):
        drop = rng.uniform(3, 5)
        pts = [tuple(a[i] + (b[i] - a[i]) * t - (drop * 4 * t * (1 - t) if i == 2 else 0) for i in range(3)) for t in np.linspace(0, 1, 12)]
        tube(f'approach_liana_{j}', coll, pts, .045, m['bark'], sides=5)
        creeper(coll, m, f'approach_liana_leaves_{j}', pts[3:9], rng, density=3)
    return spots


def _holds(o, x, y, margin=.4):
    """Whether object `o`'s footprint covers (x, y)."""
    from mathutils import Vector
    pts = [o.matrix_basis @ Vector(c) for c in o.bound_box]
    return (min(p.x for p in pts) - margin < x < max(p.x for p in pts) + margin
            and min(p.y for p in pts) - margin < y < max(p.y for p in pts) + margin)
