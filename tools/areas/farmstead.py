"""Episode 1's farmstead round the re-planned house (November 22, 2026), from the map the
user approved on November 21 ("a big tangled farmstead": one family's compound alone in
the forest, its buildings scattered, narrow mud paths, groves, dry fields, dead ends,
and obstacles as in Home Sweet Home).

    the house (stilt_house.py) in the middle, the funeral under it
    west:   the kitchen house on stilts (the walkway from the house's gallery runs into
            it at its floor), the well below it, and behind a fence with a gap to squeeze
            through, the servants' hut
    east:   the rice barn (big enough to be hunted through in Act III) behind a fence
            and a locked gate; a small granary; the buffalo byre and the ox cart; the
            tool shed in the north-east corner
    north:  the family stupas and the ruins of the first house
    round the house: its yard's low board fence, the gate facing the cart track
    round:  banana groves and old trees between everything, dry stubble fields at the
            east and south-west edges, the forest wall beyond the outer fence

The ruin, granary and byre are the old west yard's (west_yard.py), the stupas and the
well the old north garden's (north_garden.py), built where this plan puts them; their
posts and walls follow the ground there.

Blender metres, X east, Y north, Z up. `build(coll, ground, rng, flora)` makes it all.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

import compound as C
import rural_kit as RK
import stilt_house as SH
import village_layout as L
import village_nature as VN
from kit import box, collider, library_material, mesh_object, tube
from shrine_craft import Batch, place

FARM = (-46.0, 44.0, -40.0, 58.0)               # the outer fence (its gate stays at y -40)
KITCHEN = (-28.0, -20.0, 15.65, 22.65)          # on stilts, floor at the house's: the walkway runs in
WELL = (-25.5, 9.0)
SERVANTS = (-41.0, -36.0, 35.5, 39.5)
FIRST_HOUSE = (-9.0, 51.5, 0.12)                # the ruin (west_yard.first_house), x, y, turn
STUPAS = (-25.0, 48.5)
BARN = (21.0, 29.0, 19.5, 25.5)                 # the rice barn, floor 1.2 m
GRANARY = (32.5, 29.5, 0.35)
BYRE = (29.0, 5.0, 0.08)
CART = (35.5, -1.5, 0.6)
TOOL_SHED = (31.5, 35.5, 37.5, 40.5)
BARN_FENCE = (16.5, 9.0, 36.0)                  # x, y0, y1; the locked gate in it:
BARN_GATE = (21.6, 23.4)
KITCHEN_FENCE = (-33.5, 6.0, 33.0)              # x, y0, y1; the gap to squeeze through:
SQUEEZE = (21.4, 22.06)                         # post to post: about 0.55 m clear, Sora is 0.5 m across
# Dry fields, in from the forest wall (its crowns overhang the fence by 5-8 m).
FIELDS = [(22.0, 34.0, -28.0, -12.0), (-38.0, -22.0, -28.0, -10.0)]


def _smooth(points, step=1.0):
    """A Catmull-Rom line through `points`, sampled about every `step` metres."""
    pts = [Vector((*p, 0)) for p in points]
    pts = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        n = max(1, int(math.ceil((p2 - p1).length / step)))
        for k in range(n):
            t = k / n
            q = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
            out.append((round(q.x, 3), round(q.y, 3)))
    out.append(tuple(points[-1]))
    return out


# The cart track from the outer gate to the house's yard gate, no longer ruled straight
# (the user, Nov 22, 2026: "make it more natural"): it drifts east past the Neak Ta's
# shrine, threads between the two southern groves, swings back west between the fields
# and comes into the yard gate square. No plants on it.
TRACK_BENDS = [(0.0, -46.0), (0.0, -40.0), (0.8, -36.0), (2.6, -31.0), (2.8, -26.5), (1.0, -21.5), (-2.0, -16.5),
               (-3.2, -11.5), (-2.2, -6.5), (-0.6, -2.5), (0.0, 1.5), (0.0, 3.8)]
TRACK = (_smooth(TRACK_BENDS), 1.6)
# The house's yard (the user, Nov 22: "around the main house must have a border as well"):
# a board fence like the farm's, lower, 3-4 m out from the house all round; the yard gate
# faces the track, and the paths go out through gaps where boards and rails are gone.
YARD = (-12.5, 12.5, 3.0, 39.5)
YARD_GAPS = {"s": [(-1.9, 1.9)], "w": [(6.2, 8.4), (35.4, 37.6)], "n": [(0.1, 2.5)], "e": [(11.1, 13.3), (37.2, 39.5)]}
# Narrow mud paths: (points, half width).
PATHS = [
    ([(0.0, 8.5), (-6.0, 6.5), (-14.0, 7.5), (-21.0, 9.5), (-24.0, 12.5), (-28.6, 14.8)], 0.55),   # yard -> well -> kitchen ladder
    ([(-28.6, 23.5), (-31.0, 26.0), (-32.8, 21.75), (-35.5, 22.5), (-38.0, 30.0), (-38.5, 34.8)], 0.45),  # kitchen -> squeeze -> servants
    ([(6.5, 8.0), (11.0, 10.5), (15.0, 15.0), (16.5, 22.5), (20.6, 22.5)], 0.55),                 # yard -> locked gate -> barn
    ([(1.8, 1.4), (9.0, 1.6), (17.0, 0.5), (24.0, 2.0), (28.0, 2.6)], 0.6),                      # yard gate -> byre
    ([(26.0, 8.0), (25.0, 14.0), (27.5, 18.8)], 0.45),                                           # byre -> barn's back
    ([(2.0, 36.0), (1.0, 40.0), (0.5, 46.0), (-4.0, 50.0), (-9.0, 48.0), (-18.0, 47.0), (-25.0, 46.0)], 0.5),  # back -> fallen tree -> ruin -> stupas
    ([(8.5, 37.0), (16.0, 40.0), (25.0, 41.5), (31.0, 39.0)], 0.45),                            # back -> tool shed
    ([(-9.0, 36.2), (-12.5, 36.5), (-20.0, 38.0), (-22.0, 44.0)], 0.4),                         # round the west, out of the yard
    ([(-0.4, -19.0), (-10.0, -18.0), (-21.5, -19.0)], 0.4),                                     # track -> west field
    ([(-2.8, -9.0), (11.0, -10.5), (21.5, -14.0)], 0.4),                                        # track -> east field
]
GROVES = [  # centre, radius, count, what grows (banana | palm | tree | mixed)
    ((-14.5, 42.5), 4.0, 8, "banana"), ((12.0, 46.0), 5.0, 10, "banana"), ((-33.0, 2.0), 5.0, 9, "banana"),
    ((17.0, -5.0), 4.5, 8, "mixed"), ((35.0, 15.0), 3.5, 6, "banana"), ((-38.5, 15.0), 3.5, 6, "mixed"),
    ((-31.0, 44.0), 3.0, 1, "tree"), ((24.0, 49.0), 3.0, 1, "tree"), ((-8.0, -26.0), 5.0, 7, "banana"),
    ((10.0, -25.0), 4.0, 5, "mixed"), ((-30.0, -6.0), 4.0, 4, "palm"), ((27.0, -9.0), 3.5, 3, "palm"),
    ((-20.0, 27.5), 3.0, 4, "banana"), ((34.0, 22.0), 3.0, 4, "banana"),
]
# Plants on the yard floor (Poly Haven), by what they do there.
COVER = {
    "tall": ["grass_medium_01", "grass_medium_02"],
    "short": ["grass_bermuda_01"],
    "weed": ["weed_plant_02", "nettle_plant"],
    "shrub": ["shrub_02", "shrub_03", "shrub_04"],
    "shade": ["fern_02", "calathea_orbifolia_01", "periwinkle_plant"],
    "litter": ["dry_branches_medium_01", "bark_debris_01"],
}
TREE_CROWN = 12.5           # forest_tree_gn's crown radius at scale 1, roughly


def materials():
    m = dict(RK.materials())
    # The fences' weathered boards: the moss texture is olive-lime on its own, and the kit's
    # M_rk_moss_wood (reused by name) never took a tint; in the game's warm lamp it read
    # bright lime where the previews show dark, wet brown boards.
    m["moss_wood"] = bpy.data.materials.get("M_fs_fence_wood") or library_material(
        "moss_wood", "M_fs_fence_wood", tint=(0.6, 0.32, 1.0), tile=1.0)
    m["stone"] = bpy.data.materials.get("M_neakta_laterite") or m["hewn"]
    m["char"] = m["void"]
    m["path"] = library_material("muddy_tracks", "M_fs_path", tint=(0.66, 0.58, 0.52), tile=2.0)
    m["field"] = library_material("brown_mud_03", "M_fs_field", tint=(0.72, 0.64, 0.55), tile=2.4)
    m["stubble"] = m["straw"]
    m["soot"] = RK._plain("soot", (0.025, 0.02, 0.017), rough=0.95)
    m["clay"] = library_material("clay_plaster", "M_fs_clay", tint=(0.55, 0.36, 0.24), tile=0.6)
    return m


# ------------------------------------------------------------------ helpers


def _hide_colliders(coll):
    for o in coll.objects:
        if o.name.startswith("col_"):
            o.hide_render = True
            o.display_type = "WIRE"


def ladder_volume(coll, name, foot, top):
    """A `ladder_` volume (src/core/levelBuilder.ts) round a ladder from `foot` to `top`
    (x, y, z): the climber comes from the foot's side, which `facing` names."""
    dx, dy = foot[0] - top[0], foot[1] - top[1]
    facing = ("+x" if dx > 0 else "-x") if abs(dx) >= abs(dy) else ("+y" if dy > 0 else "-y")
    along_x = abs(dx) >= abs(dy)
    xs, ys = sorted((foot[0], top[0])), sorted((foot[1], top[1]))
    pad_a, pad_s = 0.25, 0.4
    if along_x:
        x0, x1, y0, y1 = xs[0] - pad_a, xs[1] + pad_a, ys[0] - pad_s, ys[1] + pad_s
    else:
        x0, x1, y0, y1 = xs[0] - pad_s, xs[1] + pad_s, ys[0] - pad_a, ys[1] + pad_a
    # Its top stops 6 cm under the floor it leads to: walking over the top (or over the shut
    # trapdoor), facing the climber's way, set Sora climbing out of the floor.
    obj = box(f"ladder_{name}", coll, x0, x1, y0, y1, min(foot[2], top[2]), max(foot[2], top[2]) - 0.06)
    obj["facing"] = facing
    obj.display_type = "WIRE"
    obj.hide_render = True
    return obj


def wall_colliders(coll, name, start, end, z0, height, openings, thick=0.12, surface="teak"):
    """Thin collider boxes along a wall from `start` to `end`, leaving its doorways
    (openings from the floor, z0 < 0.1) open."""
    s, e = Vector((*start, 0)), Vector((*end, 0))
    length = (e - s).length
    doors = sorted((a0, a1) for a0, a1, oz0, _oz1 in openings if oz0 < 0.1)
    spans, at = [], 0.0
    for a0, a1 in doors:
        if a0 > at:
            spans.append((at, a0))
        at = max(at, a1)
    if at < length:
        spans.append((at, length))
    d = (e - s).normalized()
    for k, (a0, a1) in enumerate(spans):
        p0, p1 = s + d * a0, s + d * a1
        collider(f"{name}_{k}", coll, min(p0.x, p1.x) - thick / 2, max(p0.x, p1.x) + thick / 2,
                 min(p0.y, p1.y) - thick / 2, max(p0.y, p1.y) + thick / 2, z0, z0 + height, surface=surface)


def ramp_collider(coll, name, low, high, half):
    """A sloped collider (a triangle mesh in the game) from the middle of its low edge to
    the middle of its high edge (x, y, z), `half` wide each side."""
    lo, hi = Vector(low), Vector(high)
    run = Vector((hi.x - lo.x, hi.y - lo.y, 0)).normalized()
    side = Vector((-run.y, run.x, 0)) * half
    verts = [tuple(lo - side), tuple(lo + side), tuple(hi + side), tuple(hi - side)]
    obj = mesh_object(f"col_{name}", coll, verts, [(3, 2, 1, 0)], None)   # facing up
    obj["surface"] = "teak"
    obj.display_type = "WIRE"
    obj.hide_render = True
    return obj


def _ribbon(coll, ground, pts, half, mat, name, step=0.35, lift=0.025, wob=0.12, rng=None):
    """A strip of trodden mud following `pts`, hugging the ground, its edges wandering."""
    rng = rng or np.random.default_rng(len(pts))
    dense = []
    for a, c in zip(pts, pts[1:]):
        a, c = Vector((*a, 0)), Vector((*c, 0))
        n = max(1, int((c - a).length / step))
        for k in range(n):
            dense.append(a.lerp(c, k / n))
    dense.append(Vector((*pts[-1], 0)))
    verts, faces, uvs = [], [], []
    dist = 0.0
    phase = (sum(map(ord, name)) % 628) / 100.0   # from the name: the farm's shared rng stays untouched
    for i, p in enumerate(dense):
        q0 = dense[max(0, i - 1)]
        q1 = dense[min(len(dense) - 1, i + 1)]
        t = (q1 - q0).normalized()
        nrm = Vector((-t.y, t.x, 0))
        if i:
            dist += (p - dense[i - 1]).length
        w = half * (1 + wob * math.sin(dist * 1.7 + 1.3) + 0.5 * wob * math.sin(dist * 4.1))
        for k, s in enumerate((-1.0, -0.5, 0.0, 0.5, 1.0)):
            r = p + nrm * s * w
            z = ground(r.x, r.y) + (lift - 0.02 * (abs(s) < 0.6) if abs(s) < 0.9 else -0.02)
            verts.append((r.x, r.y, z))
            # A slow meander through the texture, so its 2 m tile doesn't stripe the path.
            uvs.append((s * w / 2.0 + 0.31 * math.sin(dist * 0.23 + phase) + 0.12 * math.sin(dist * 0.61),
                        dist / 2.0 + 0.18 * math.sin(dist * 0.17 + 2 * phase) + 0.08 * s * math.sin(dist * 0.9)))
    for i in range(len(dense) - 1):
        for k in range(4):
            a = i * 5 + k
            faces.append((a, a + 1, a + 6, a + 5))
    return mesh_object(name, coll, verts, faces, mat, uvs=uvs, smooth=True)


def _wall_with_openings(b, m, mat, start, end, F, height, openings, rng, gaps=None):
    """Slat panels from `start` to `end` (x, y) between floor F and F + height, broken by
    openings (a0, a1, z0, z1) measured along the wall from `start`."""
    s, e = Vector((*start, 0)), Vector((*end, 0))
    along = (e - s).normalized()
    length = (e - s).length
    up = Vector((0, 0, 1))
    spans, at = [], 0.0
    for a0, a1, z0, z1 in sorted(openings):
        if a0 > at:
            spans.append((at, a0, 0.0, height))
        if z0 > 0.01:
            spans.append((a0, a1, 0.0, z0))
        if z1 < height - 0.01:
            spans.append((a0, a1, z1, height))
        at = a1
    if at < length:
        spans.append((at, length, 0.0, height))
    for a0, a1, z0, z1 in spans:
        if a1 - a0 < 0.05 or z1 - z0 < 0.05:
            continue
        o = s + along * a0 + Vector((0, 0, F + z0))
        RK.slat_panel(b, mat, m["hewn"], o, along, up, a1 - a0, z1 - z0, rng, gaps=gaps, frame=(z1 - z0) > 0.6)


def stilt_hut(coll, m, ground, rng, name, x0, x1, y0, y1, F, wall_h, wall_mat, openings, pitch=40.0, over=0.8,
              rot_thatch=0.06, post_step=4.0, open_gables=True, thatch_holes=None):
    """A Khmer hut on round posts: a plank floor at F over girders, split-bamboo (or board)
    walls with doors and windows (`openings`: {side: [(a0, a1, z0, z1)]}, a along the wall
    from its west/south end, z from the floor), and a thick grey thatch roof whose ridge
    runs east-west; gables left open for the smoke. Returns the floor height."""
    b = Batch(name)
    xs = list(np.linspace(x0, x1, max(2, round((x1 - x0) / post_step) + 1)))
    ys = list(np.linspace(y0, y1, max(2, round((y1 - y0) / post_step) + 1)))
    top = F + wall_h
    for x in xs:
        for y in ys:
            edge = x in (xs[0], xs[-1]) or y in (ys[0], ys[-1])
            g = ground(x, y)
            RK.log(b, m["bark"], Vector((x, y, g - 0.4)), Vector((x, y, (top + 0.05) if edge else F - 0.1)), 0.13, 0.11, rng)
            b.box(m["stone"], (0.42, 0.42, 0.22), (x, y, g + 0.05), chamfer=0.03, jitter=0.01, rng=rng)
    for y in ys:
        RK.timber(b, m["hewn"], Vector((x0 - 0.25, y, F - 0.16)), Vector((x1 + 0.25, y, F - 0.16)), 0.16, 0.14, rng)
        RK.timber(b, m["hewn"], Vector((x0 - 0.2, y, top)), Vector((x1 + 0.2, y, top)), 0.14, 0.12, rng)
    for x in xs:
        RK.timber(b, m["hewn"], Vector((x, y0 - 0.2, top + 0.13)), Vector((x, y1 + 0.2, top + 0.13)), 0.12, 0.12, rng)
    # Floor boards across the joists, a gap between each.
    x = x0
    k = 0
    while x < x1 - 0.05:
        w = rng.uniform(0.17, 0.24)
        b.box(m["boards"], (min(w, x1 - x) - 0.008, y1 - y0 + 0.1, 0.035), (x + min(w, x1 - x) / 2, (y0 + y1) / 2, F - 0.0175),
              jitter=0.003, rng=rng)
        x += w
        k += 1
    for x in np.arange(x0 + 0.3, x1, 0.7):
        RK.timber(b, m["hewn"], Vector((x, y0 - 0.1, F - 0.06)), Vector((x, y1 + 0.1, F - 0.06)), 0.07, 0.07, rng)
    # Walls.
    sides = {"s": ((x0, y0), (x1, y0)), "n": ((x0, y1), (x1, y1)), "w": ((x0, y0), (x0, y1)), "e": ((x1, y0), (x1, y1))}
    for side, (a, c) in sides.items():
        _wall_with_openings(b, m, wall_mat, a, c, F, wall_h, openings.get(side, []), rng)
    # The roof: thatch slopes north and south from an east-west ridge.
    yc = (y0 + y1) / 2
    half = (y1 - y0) / 2
    rz = top + 0.2 + half * math.tan(math.radians(pitch))
    ez = top + 0.2 - over * math.tan(math.radians(pitch))
    for sgn in (-1, 1):
        RK.thatch(b, m["thatch"], (x0 - 0.7, yc, rz), (x1 + 0.7, yc, rz), (x0 - 0.7, yc + sgn * (half + over), ez),
                  (x1 + 0.7, yc + sgn * (half + over), ez), rng, under=m["thatch_dark"], rot=rot_thatch, hole=thatch_holes)
    RK.ridge_roll(b, m["thatch_dark"], (x0 - 0.75, yc, rz + 0.08), (x1 + 0.75, yc, rz + 0.08), 0.16, rng)
    for x in (x0, x1):
        RK.timber(b, m["hewn"], Vector((x, yc, top + 0.2)), Vector((x, yc, rz)), 0.12, 0.12, rng)
    # Gables: closed low down with slats, the apex left open (smoke and swifts).
    for x in (x0, x1):
        h = (rz - top) * (0.45 if open_gables else 0.95)
        for sgn in (-1, 1):
            o = Vector((x, yc, top + 0.2))
            RK.slat_panel(b, wall_mat, m["hewn"], o + Vector((0, sgn * 0.05, 0)), (0, sgn, 0), (0, 0, 1),
                          half * (1 - h / (rz - top)), h, rng, frame=False)
    b.build(coll)
    collider(f"{name}_floor", coll, x0, x1, y0, y1, F - 0.12, F)
    for side, (a, c) in sides.items():
        wall_colliders(coll, f"{name}_wall_{side}", a, c, F, wall_h, openings.get(side, []))
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            collider(f"{name}_post_{i}_{j}", coll, x - 0.13, x + 0.13, y - 0.13, y + 0.13, ground(x, y) - 0.2, F - 0.12)
    return F


# ------------------------------------------------------------------ buildings


def kitchen_house(coll, m, ground, rng):
    """The kitchen on stilts at the house's floor height: the walkway runs into its east
    door; a ladder down from the west door to the well path. Inside: the hearth on its
    sand box, the clay stove, pots, water jars, a shelf of jars, baskets from the rafters,
    soot over everything. Under it: firewood, jars, the rice pounder's place."""
    x0, x1, y0, y1 = KITCHEN
    F = SH.FLOOR
    wy0, wy1 = SH.WALKWAY[2], SH.WALKWAY[3]
    stilt_hut(coll, m, ground, rng, "fs_kitchen", x0, x1, y0, y1, F, 2.1, m["bamboo"],
              {"e": [(wy0 - y0, wy1 - y0, 0.0, 1.95)], "w": [(3.0, 3.9, 0.0, 1.95)],
               "s": [(1.6, 2.5, 0.8, 1.5), (5.4, 6.3, 0.8, 1.5)], "n": [(3.6, 4.6, 0.8, 1.5)]},
              rot_thatch=0.09, post_step=2.4)
    SH.ladder("fs_kitchen_ladder", coll, m["hewn"], (x0 - 1.0, y0 + 3.45, ground(x0 - 1.0, y0 + 3.45)), (x0 - 0.05, y0 + 3.45, F))
    ladder_volume(coll, "fs_kitchen", (x0 - 1.0, y0 + 3.45, ground(x0 - 1.0, y0 + 3.45)), (x0 - 0.05, y0 + 3.45, F))
    b = Batch("fs_kitchen_inside")
    # The hearth: a timber frame of sand and ash, three firestones, the clay stove.
    hx, hy = x0 + 1.6, y1 - 1.4
    for (a, c) in (((hx - 0.7, hy - 0.45), (hx + 0.7, hy - 0.45)), ((hx - 0.7, hy + 0.45), (hx + 0.7, hy + 0.45))):
        RK.timber(b, m["hewn"], Vector((*a, F + 0.08)), Vector((*c, F + 0.08)), 0.1, 0.16, rng)
    b.box(m["ash"], (1.36, 0.82, 0.12), (hx, hy, F + 0.08), jitter=0.01, rng=rng)
    for k in range(3):
        a = k * math.tau / 3
        b.box(m["stone"], (0.16, 0.14, 0.18), (hx + 0.32 * math.cos(a) - 0.25, hy + 0.22 * math.sin(a), F + 0.23), chamfer=0.03, jitter=0.01, rng=rng)
    b.box(m["soot"], (x1 - x0 - 0.2, y1 - y0 - 0.2, 0.01), ((x0 + x1) / 2, (y0 + y1) / 2, F + 2.07))
    # A shelf of planks along the north wall.
    for z in (F + 0.9, F + 1.45):
        b.box(m["boards"], (2.6, 0.32, 0.03), (x0 + 4.9, y1 - 0.22, z), jitter=0.003, rng=rng)
        for dx in (-1.1, 1.1):   # the cleats nailed to the wall that carry it
            b.box(m["hewn"], (0.05, 0.3, 0.05), (x0 + 4.9 + dx, y1 - 0.21, z - 0.04))
    b.build(coll)
    for k, (model, u, v, z, s) in enumerate((("clay_stove", hx + 0.25, hy, F + 0.14, 1.0), ("cooking_pot", hx + 0.25, hy + 0.02, None, 1.0),
                                            ("kettle", hx - 0.3, hy - 0.05, F + 0.14, 1.0), ("water_jar", x1 - 0.55, y0 + 0.6, F, 1.1),
                                            ("water_jar", x1 - 1.25, y0 + 0.5, F, 1.0), ("jar_plain", x0 + 4.2, y1 - 0.22, F + 0.915, 0.8),
                                            ("jar_handles", x0 + 4.9, y1 - 0.22, F + 0.915, 0.75), ("jar_plain", x0 + 5.6, y1 - 0.22, F + 1.465, 0.7),
                                            ("cooking_pot", x0 + 4.5, y1 - 0.22, F + 1.465, 0.9), ("basket_deep", x0 + 6.6, y0 + 1.0, F, 1.0),
                                            ("rice_sack", x0 + 7.1, y0 + 1.8, F, 1.0), ("straw_mat", x0 + 3.5, y0 + 1.6, F, 1.0),
                                            ("winnowing_tray", x0 + 2.4, y0 + 0.08, F + 1.2, 1.0), ("broom", x1 - 0.25, y1 - 0.4, F, 1.0))):
        zz = z if z is not None else None
        if model == "cooking_pot" and z is None:
            zz = stove_top - 0.03      # down in the stove's mouth
        tilt = (1.45, 0.0) if model in ("winnowing_tray", "broom") else (0.0, 0.0)
        rot = rng.uniform(0, math.tau)
        if model == "winnowing_tray":
            # Stood on its rim on the floor, leant back on the south wall (it stood in the
            # air at F + 1.2 with nothing under it).
            zz, rot = F, math.pi
        placed = RK.place_model(coll, model, u, v, ground, rot=rot, scale=s, scan=True, z=zz, tilt=tilt,
                                name=f"fs_kitchen_{model}_{k}")
        if model == "clay_stove":
            bpy.context.view_layer.update()   # place_model moved it up after reading its points
            stove_top = max((o.matrix_world @ Vector(c)).z for o in placed.children_recursive if o.type == "MESH" for c in o.bound_box)
    # Under the kitchen: firewood stacked between the posts, jars, a basket.
    import west_yard as WY
    WY.firewood(coll, m, ground, rng, x0 + 1.5, y0 + 1.0, 0.1, "fs_kitchen_firewood")
    WY.firewood(coll, m, ground, rng, x0 + 5.5, y1 - 1.2, -0.2, "fs_kitchen_firewood_b")
    for k, (model, u, v) in enumerate((("jar_handles", x0 + 3.2, y1 - 0.6), ("jar_plain", x0 + 3.9, y1 - 0.8), ("basket_round", x1 - 1.5, y0 + 2.4))):
        RK.place_model(coll, model, u, v, ground, rot=rng.uniform(0, 6), scan=True, name=f"fs_kitchen_under_{model}_{k}")
    return [(hx - 0.25, hy, F + 0.45)]   # the fire's embers: a glow under the pot


def rice_barn(coll, m, ground, rng):
    """The rice barn: a board-walled store on posts with a wide double door facing the
    house and a plank ramp up to it; bins of grain, sacks stacked to the rafters, baskets,
    a half loft reached by a ladder: aisles to be hunted through in Act III."""
    x0, x1, y0, y1 = BARN
    F = 1.2
    stilt_hut(coll, m, ground, rng, "fs_barn", x0, x1, y0, y1, F, 2.5, m["boards"],
              {"w": [(2.2, 3.8, 0.0, 2.2)], "s": [(3.0, 3.6, 1.2, 1.6)], "n": [(5.0, 5.6, 1.2, 1.6)]},
              pitch=38.0, rot_thatch=0.04, post_step=2.0)
    b = Batch("fs_barn_inside")
    # The doors stand open, the ramp of split logs up to the sill.
    yc = y0 + 3.0
    for sgn, ang in ((-1, -1.9), (1, 1.75)):   # each leaf swung out to the west
        hinge = Vector((x0, yc + sgn * 0.8, F))
        d = Vector((math.cos(ang), math.sin(ang), 0))
        RK.slat_panel(b, m["boards"], m["hewn"], hinge, d, (0, 0, 1), 0.78, 2.15, rng)
    for k in range(6):
        z = F - 0.04 - k * F / 6
        x = x0 - 0.3 - k * 0.32
        RK.log(b, m["bark"], Vector((x, yc - 0.85, z)), Vector((x, yc + 0.85, z)), 0.08, 0.07, rng)
    # Two log stringers under them from the ground to the sill, so each rung lies on
    # something (they stood in the air, a staircase of logs). The rungs' undersides run
    # 0.625 up per metre from 0.08 m at the lowest; no draws from rng (the farm shares it).
    for dy in (-0.6, 0.6):
        ends = [(xa, 0.08 + 0.625 * (xa - (x0 - 1.9)) - 0.07) for xa in (x0 - 2.05, x0 - 0.1)]
        b.tube(m["bark"], [(xa, yc + dy, za) for xa, za in ends], 0.07, sides=8)
    # Grain bins along the north wall, their lids askew; the loft over the east end.
    for k in range(3):
        bx = x0 + 1.4 + k * 1.9
        for (sx, sy, cx, cy) in ((1.6, 0.05, bx, y1 - 1.25), (1.6, 0.05, bx, y1 - 0.15), (0.05, 1.1, bx - 0.8, y1 - 0.7), (0.05, 1.1, bx + 0.8, y1 - 0.7)):
            b.box(m["boards"], (sx, sy, 1.1), (cx, cy, F + 0.55), jitter=0.003, rng=rng)
        b.box(m["straw"], (1.5, 1.0, 0.04), (bx, y1 - 0.7, F + 0.85 + 0.1 * k), jitter=0.01, rng=rng)
        b.box(m["boards"], (1.62, 1.12, 0.035), (bx + rng.normal(0, 0.04), y1 - 0.7 + rng.normal(0, 0.04), F + 1.12 + 0.02 * k))
    lz = F + 2.35
    x = x1 - 3.2
    while x < x1 - 0.05:
        b.box(m["boards"], (0.2, y1 - y0 - 0.15, 0.03), (x + 0.1, (y0 + y1) / 2, lz), jitter=0.003, rng=rng)
        x += 0.215
    RK.timber(b, m["hewn"], Vector((x1 - 3.25, y0 + 0.1, lz - 0.08)), Vector((x1 - 3.25, y1 - 0.1, lz - 0.08)), 0.14, 0.14, rng)
    b.box(m["straw"], (5.0, 2.0, 0.02), (x0 + 3.0, y0 + 2.4, F + 0.01), jitter=0.02, rng=rng)   # husks spilled
    b.build(coll)
    SH.ladder("fs_barn_ladder", coll, m["hewn"], (x1 - 3.9, y0 + 3.0, F), (x1 - 3.25, y0 + 3.0, lz + 0.05))
    ladder_volume(coll, "fs_barn_loft", (x1 - 3.9, y0 + 3.0, F), (x1 - 3.25, y0 + 3.0, lz + 0.05))
    collider("fs_barn_loft", coll, x1 - 3.2, x1, y0, y1, lz - 0.05, lz + 0.02)
    # The ramp of split logs up to the doors.
    # Along the rungs' tops (from where they meet the ground to just short of the sill).
    ramp_collider(coll, "fs_barn_ramp", (x0 - 2.28, yc, ground(x0 - 2.28, yc)), (x0 - 0.15, yc, F + 0.06), 0.85)
    for k in range(16):
        u = x0 + 0.6 + (k % 8) * 0.62 + rng.normal(0, 0.05)
        v = y0 + 0.45 + (k // 8) * 0.55
        RK.place_model(coll, "rice_sack", u, v, ground, rot=rng.normal(0, 0.3), scan=True, z=F + (0.0 if k < 8 else 0.0), name=f"fs_barn_sack_{k}")
    for k in range(6):
        u = x1 - 2.6 + (k % 3) * 0.7
        v = y0 + 0.5 + (k // 3) * 0.6
        RK.place_model(coll, "rice_sack", u, v, ground, rot=rng.normal(0, 0.3), scan=True, z=lz + 0.015, name=f"fs_barn_loft_sack_{k}")
    for k, (model, u, v) in enumerate((("basket_deep", x0 + 6.6, y1 - 2.0), ("basket_round", x0 + 7.2, y1 - 2.3),
                                       ("winnowing_tray", x0 + 4.0, y0 + 2.9), ("basket_deep", x0 + 2.2, y0 + 3.6))):
        RK.place_model(coll, model, u, v, ground, rot=rng.uniform(0, 6), scan=True, z=F, name=f"fs_barn_{model}_{k}")


def tool_shed(coll, m, ground, rng, door_open=True):
    """A plank shed on the ground under a lean-to of thatch, its door ajar: hoes, the
    spade, the machete, rope, baskets, the plough."""
    x0, x1, y0, y1 = TOOL_SHED
    b = Batch("fs_toolshed")
    g = min(ground(x, y) for x in (x0, x1) for y in (y0, y1))
    hs, hn = 2.4, 1.9
    for x in (x0, (x0 + x1) / 2, x1):
        for y, h in ((y0, hs), (y1, hn)):
            RK.log(b, m["bark"], Vector((x, y, g - 0.4)), Vector((x, y, g + h)), 0.1, 0.09, rng)
    for y, h in ((y0, hs), (y1, hn)):
        RK.timber(b, m["hewn"], Vector((x0 - 0.2, y, g + h)), Vector((x1 + 0.2, y, g + h)), 0.12, 0.12, rng)
    _wall_with_openings(b, m, m["planks"], (x0, y0), (x1, y0), g, hs - 0.05, [(0.8, 1.7, 0.0, 1.85)], rng)
    wall_colliders(coll, "fs_toolshed_wall_s", (x0, y0), (x1, y0), g, hs - 0.05, [(0.8, 1.7, 0.0, 1.85)])
    wall_colliders(coll, "fs_toolshed_wall_n", (x0, y1), (x1, y1), g, hn - 0.05, [])
    wall_colliders(coll, "fs_toolshed_wall_w", (x0, y0), (x0, y1), g, hn - 0.05, [])
    wall_colliders(coll, "fs_toolshed_wall_e", (x1, y0), (x1, y1), g, hn - 0.05, [])
    _wall_with_openings(b, m, m["planks"], (x0, y1), (x1, y1), g, hn - 0.05, [], rng)
    _wall_with_openings(b, m, m["planks"], (x0, y0), (x0, y1), g, hn - 0.05, [], rng)
    _wall_with_openings(b, m, m["planks"], (x1, y0), (x1, y1), g, hn - 0.05, [(1.0, 1.6, 1.0, 1.4)], rng)
    RK.thatch(b, m["thatch"], (x0 - 0.5, y0 - 0.6, g + hs + 0.25), (x1 + 0.5, y0 - 0.6, g + hs + 0.25),
              (x0 - 0.5, y1 + 0.6, g + hn - 0.05), (x1 + 0.5, y1 + 0.6, g + hn - 0.05), rng, under=m["thatch_dark"], rot=0.05)
    # The door, hanging open on one hinge (in the game the old shed's locked door hangs here).
    if door_open:
        RK.slat_panel(b, m["planks"], m["hewn"], Vector((x0 + 0.8, y0, g + 0.03)), (math.cos(-2.1), math.sin(-2.1), 0), (0, 0, 1), 0.88, 1.8, rng)
    b.build(coll)
    for k, (model, u, v, rot, tilt) in enumerate((("rusted_spade_01", x1 - 0.3, y1 - 0.3, 0.3, (0.25, 0.0)),
                                                  ("hatchet", x0 + 0.5, y1 - 0.25, 1.2, (0.0, 0.0)),
                                                  ("machete", x0 + 1.6, y1 - 0.25, 0.4, (1.5, 0.0)))):
        RK.place_model(coll, model, u, v, ground, rot=rot, tilt=tilt, name=f"fs_toolshed_{model}_{k}")
    for k, (model, u, v) in enumerate((("basket_round", x1 - 1.0, y0 + 0.6), ("basket_deep", x1 - 1.6, y1 - 0.5))):
        RK.place_model(coll, model, u, v, ground, rot=rng.uniform(0, 6), scan=True, name=f"fs_toolshed_{model}_{k}")
    SH.ladder("fs_toolshed_ladder", coll, m["hewn"], (x1 + 0.9, y0 - 0.2, ground(x1 + 0.9, y0 - 0.2)), (x1 + 0.15, y0 - 0.25, g + 2.3))


def servants_hut(coll, m, ground, rng):
    x0, x1, y0, y1 = SERVANTS
    F = 1.2
    stilt_hut(coll, m, ground, rng, "fs_servants", x0, x1, y0, y1, F, 1.9, m["bamboo"],
              {"s": [(0.6, 1.45, 0.0, 1.8)], "e": [(0.6, 1.4, 0.7, 1.3)]}, pitch=42.0, rot_thatch=0.14, post_step=2.5)
    SH.ladder("fs_servants_ladder", coll, m["hewn"], (x0 + 1.02, y0 - 0.9, ground(x0 + 1.02, y0 - 0.9)), (x0 + 1.02, y0 - 0.05, F))
    ladder_volume(coll, "fs_servants", (x0 + 1.02, y0 - 0.9, ground(x0 + 1.02, y0 - 0.9)), (x0 + 1.02, y0 - 0.05, F))
    for k, (model, u, v) in enumerate((("straw_mat", x0 + 1.2, y0 + 2.6), ("jar_plain", x1 - 0.5, y1 - 0.5), ("basket_round", x0 + 0.6, y1 - 0.5))):
        RK.place_model(coll, model, u, v, ground, rot=rng.uniform(0, 6), scan=True, z=F, name=f"fs_servants_{model}_{k}")


def old_yard(coll, m, ground, rng):
    """The ruin of the first house, the small granary and the buffalo byre (west_yard.py's
    builders, set where this plan puts them), the ox cart, the stupas and the well."""
    import north_garden as NG
    import ox_cart as OX
    import west_yard as WY
    L.WEST_YARD["house"] = FIRST_HOUSE
    L.WEST_YARD["granary"] = GRANARY
    L.WEST_YARD["byre"] = BYRE
    WY.first_house(coll, m, ground, rng)
    WY.granary(coll, m, ground, rng)
    WY.byre(coll, m, ground, rng)
    L.NORTH_GARDEN["stupa"] = (STUPAS[0], STUPAS[1], 0.0)
    L.NORTH_GARDEN["well"] = WELL
    gm = NG.garden_materials()
    NG.stupas(coll, gm, ground, rng)
    NG.well(coll, gm, ground, rng)
    try:
        # The cart's own material names, from this kit's (and the village's where it has them).
        cm = dict(m)
        cm.update({"old_planks": m["boards"], "worn": m["hewn"], "post_rough": m["bark"], "bamboo_wall_2s": m["bamboo"],
                   "betel_leaf_dry": bpy.data.materials.get("M_betel_leaf_dry") or m["straw"],
                   "sandal": bpy.data.materials.get("M_sandal") or m["hewn"],
                   "yantra": bpy.data.materials.get("M_yantra") or m["boards"]})
        OX.ox_cart_detailed(coll, cm, "fs_ox_cart", CART[0], CART[1], CART[2], hood=True)
    except Exception as e:   # the cart wants its own materials; the preview can go without it
        print("[farmstead] ox cart skipped:", e)


# ------------------------------------------------------------------ fences, obstacles, ground


def fences(coll, m, ground, rng):
    """The outer fence with its gate (south), the barn yard's fence with the locked gate,
    and the kitchen yard's fence with the gap a body can squeeze through."""
    b = Batch("fs_fence")
    x0, x1, y0, y1 = FARM
    tall, bay = 1.9, 2.1
    C._fence_run(b, m, ground, rng, (x0, y0), (-C.GATE_HALF, y0), tall, bay, 0.9)
    C._fence_run(b, m, ground, rng, (C.GATE_HALF, y0), (x1, y0), tall, bay, 0.9)
    C._fence_run(b, m, ground, rng, (x0, y0), (x0, y1), tall, bay, 0.92)
    C._fence_run(b, m, ground, rng, (x1, y0), (x1, y1), tall, bay, 0.92)
    C._fence_run(b, m, ground, rng, (x0, y1), (x1, y1), tall, bay, 0.92)
    for sx in (-1, 1):
        p = Vector((sx * (C.GATE_HALF + 0.1), y0, 0))
        z = ground(p.x, p.y)
        RK.log(b, m["bark"], p + Vector((0, 0, z - 0.5)), p + Vector((0, 0, z + 2.75)), 0.15, 0.13, rng)
    zg = ground(0, y0)
    RK.timber(b, m["hewn"], Vector((-C.GATE_HALF - 0.55, y0, zg + 2.55)), Vector((C.GATE_HALF + 0.55, y0, zg + 2.6)), 0.16, 0.14, rng)
    # The barn yard: tall boards, the gate in it chained and padlocked.
    bx, by0, by1 = BARN_FENCE
    g0, g1 = BARN_GATE
    C._fence_run(b, m, ground, rng, (bx, by0), (bx, g0 - 0.14), 2.0, 2.0, 0.97)
    C._fence_run(b, m, ground, rng, (bx, g1 + 0.14), (bx, by1), 2.0, 2.0, 0.97)
    bx1 = BARN[1] + 6.0
    C._fence_run(b, m, ground, rng, (bx, by1), (bx1, by1), 2.0, 2.0, 0.97)
    C._fence_run(b, m, ground, rng, (bx, by0), (bx1, by0), 2.0, 2.0, 0.97)
    C._fence_run(b, m, ground, rng, (bx1, by0), (bx1, by1), 2.0, 2.0, 0.97)
    for y in (g0, g1):
        z = ground(bx, y)
        RK.log(b, m["bark"], Vector((bx, y, z - 0.5)), Vector((bx, y, z + 2.75)), 0.13, 0.12, rng)
    zg = ground(bx, (g0 + g1) / 2)
    # A lintel across the gate posts, so it reads as the way in even shut.
    RK.timber(b, m["hewn"], Vector((bx, g0 - 0.4, zg + 2.6)), Vector((bx, g1 + 0.4, zg + 2.66)), 0.15, 0.13, rng)
    # The leaf: boards on three ledges and a brace, hung off the north post, chained shut
    # on the outside (the key is in the house: Act III). Its own objects, so the game can
    # swing it open (the same draws from rng as before: nothing else in the farm moves).
    leaf = Batch("fs_barn_gate_leaf")
    for k in range(int((g1 - g0 - 0.24) / 0.155)):
        y = g0 + 0.2 + k * 0.155
        leaf.box(m["boards"], (0.032, 0.148, 1.8 + rng.uniform(-0.05, 0.04)), (bx + 0.03, y, zg + 1.02), jitter=0.004, rng=rng)
    for z in (0.32, 1.0, 1.68):
        RK.timber(leaf, m["hewn"], Vector((bx - 0.03, g0 + 0.16, zg + z)), Vector((bx - 0.03, g1 - 0.12, zg + z)), 0.08, 0.05, rng)
    RK.timber(leaf, m["hewn"], Vector((bx - 0.03, g0 + 0.2, zg + 0.36)), Vector((bx - 0.03, g1 - 0.16, zg + 1.64)), 0.075, 0.045, rng)
    leaf.build(coll)
    # The chain: twice round the south post and the leaf's edge, a padlock hanging off it.
    chain = []
    for t in np.linspace(0, 2 * math.tau, 40):
        chain.append((bx - 0.02 + 0.17 * math.cos(t), g0 + 0.07 + 0.2 * math.sin(t), zg + 1.08 - 0.012 * t))
    chain += [(bx - 0.19, g0 + 0.12, zg + 0.98), (bx - 0.21, g0 + 0.16, zg + 0.88)]
    tube("fs_gate_chain", coll, chain, 0.011, m["iron"], sides=6)
    lock = Batch("fs_barn_gate_padlock")
    lock.box(m["iron"], (0.035, 0.075, 0.09), (bx - 0.22, g0 + 0.17, zg + 0.8), chamfer=0.008)
    lock.build(coll)
    tube("fs_gate_shackle", coll, [(bx - 0.22, g0 + 0.145, zg + 0.84), (bx - 0.22, g0 + 0.145, zg + 0.89),
                                   (bx - 0.22, g0 + 0.17, zg + 0.91), (bx - 0.22, g0 + 0.195, zg + 0.89),
                                   (bx - 0.22, g0 + 0.195, zg + 0.84)], 0.006, m["iron"], sides=6)
    # The kitchen yard: an old board fence, two boards gone at one bay.
    kx, ky0, ky1 = KITCHEN_FENCE
    C._fence_run(b, m, ground, rng, (kx, ky0), (kx, SQUEEZE[0]), 1.8, 2.0, 0.98)
    C._fence_run(b, m, ground, rng, (kx, SQUEEZE[1]), (kx, ky1), 1.8, 2.0, 0.98)
    for k, (dy, lean) in enumerate(((0.05, 0.4), (0.35, -0.25))):   # the fallen boards
        y = SQUEEZE[0] + dy
        z = ground(kx - 0.4, y)
        b.box(m["planks"], (0.025, 0.15, 1.7), (kx - 0.45 - 0.3 * k, y, z + 0.4 + 0.25 * k), jitter=0.004, rng=rng)
    b.build(coll)
    collider("fs_barn_gate", coll, bx - 0.05, bx + 0.12, g0, g1, zg, zg + 2.1)
    runs = [("outer_w", (x0, y0), (x0, y1)), ("outer_e", (x1, y0), (x1, y1)), ("outer_n", (x0, y1), (x1, y1)),
            ("outer_s_w", (x0, y0), (-C.GATE_HALF, y0)), ("outer_s_e", (C.GATE_HALF, y0), (x1, y0)),
            ("barn_w_s", (bx, by0), (bx, g0 - 0.14)), ("barn_w_n", (bx, g1 + 0.14), (bx, by1)),
            ("barn_n", (bx, by1), (bx1, by1)), ("barn_s", (bx, by0), (bx1, by0)), ("barn_e", (bx1, by0), (bx1, by1)),
            ("kitchen_s", (kx, ky0), (kx, SQUEEZE[0])), ("kitchen_n", (kx, SQUEEZE[1]), (kx, ky1))]
    for name, a, c in runs:
        za = min(ground(*a), ground(*c))
        wall_colliders(coll, f"fs_fence_{name}", a, c, za - 0.3, 2.3, [], thick=0.16, surface="teak")


def cart_track(coll, ground):
    """The cart track from the outer gate into the yard, along TRACK's bends: two ruts, a
    grassy hump between them, its width wandering, branches down in the storm on it."""
    rng = np.random.default_rng(21)
    muddy = library_material("muddy_tracks", "M_v2_track", tint=(0.7, 0.62, 0.56), tile=2.25)
    line = [Vector((*p, 0)) for p in TRACK[0]]
    # Resample every 0.3 m along the line, with each sample's way and side.
    seg = [0.0]
    for a, b in zip(line, line[1:]):
        seg.append(seg[-1] + (b - a).length)
    total = seg[-1]

    def at(dist):
        i = max(0, min(len(line) - 2, int(np.searchsorted(seg, dist) - 1)))
        f = (dist - seg[i]) / max(seg[i + 1] - seg[i], 1e-6)
        p = line[i].lerp(line[i + 1], f)
        way = (line[min(i + 1, len(line) - 1)] - line[max(i - 1, 0)]).normalized() if 0 < i < len(line) - 2 else (line[i + 1] - line[i]).normalized()
        return p, Vector((-way.y, way.x, 0))

    verts, faces, uvs = [], [], []
    ss = np.arange(0.0, total, 0.3)
    for j, d in enumerate(ss):
        p, side = at(d)
        half = 1.15 * (1 + 0.1 * math.sin(d * 0.21 + 0.7) + 0.06 * math.sin(d * 0.67))
        for i, u in enumerate(np.linspace(-1.0, 1.0, 9)):
            w = u * half
            q = p + side * w
            rut = -0.04 * math.exp(-((abs(u) - 0.57) ** 2) / 0.016)
            edge = -0.02 if abs(u) > 0.96 else 0.0
            verts.append((q.x, q.y, ground(q.x, q.y) + 0.03 + rut + edge))
            # A slow meander through the texture: its tile no longer stripes the ruts.
            uvs.append((w + 1.15 + 0.35 * math.sin(d * 0.19) + 0.12 * math.sin(d * 0.53), d + 0.25 * math.sin(d * 0.13 + 0.8 * u)))
    for j in range(len(ss) - 1):
        for i in range(8):
            a = j * 9 + i
            faces.append((a, a + 1, a + 10, a + 9))
    mesh_object("farm_track", coll, verts, faces, muddy, uvs=uvs, smooth=True)
    grass = VN.poly_haven("grass_medium_01") + VN.poly_haven("grass_medium_02")
    for d in ss[::2]:
        if rng.random() < 0.7:
            p, side = at(d)
            q = p + side * rng.normal(0, 0.05)
            VN.put(coll, grass[int(rng.integers(len(grass)))], q.x, q.y, ground, rng.uniform(0, 6), rng.uniform(0.5, 0.8))
    for name in ("dry_branches_medium_01", "bark_debris_01"):
        objs = VN.poly_haven(name)
        for _ in range(18):
            p, side = at(rng.uniform(0, total))
            q = p + side * rng.uniform(-1.3, 1.3)
            VN.put(coll, objs[int(rng.integers(len(objs)))], q.x, q.y, ground, rng.uniform(0, 6), rng.uniform(0.7, 1.2))


def track_distance(x, y):
    """Metres from (x, y) to the cart track's centre line."""
    pts = TRACK[0]
    return min(_seg_distance(x, y, *a, *b) for a, b in zip(pts, pts[1:]))


def _yard_runs():
    """The yard fence's runs between its gaps: (name, start, end)."""
    x0, x1, y0, y1 = YARD
    sides = {"s": ((x0, y0), (x1, y0)), "e": ((x1, y0), (x1, y1)), "n": ((x0, y1), (x1, y1)), "w": ((x0, y0), (x0, y1))}
    runs = []
    for side, (a, c) in sides.items():
        along_x = a[1] == c[1]
        lo, hi = (a[0], c[0]) if along_x else (a[1], c[1])
        cuts = [lo]
        for g0, g1 in sorted(YARD_GAPS.get(side, [])):
            cuts += [g0, g1]
        cuts.append(hi)
        for k in range(0, len(cuts), 2):
            s0, s1 = cuts[k], cuts[k + 1]
            if s1 - s0 < 0.3:
                continue
            p0 = (s0, a[1]) if along_x else (a[0], s0)
            p1 = (s1, a[1]) if along_x else (a[0], s1)
            runs.append((f"{side}{k // 2}", p0, p1))
    return runs


def house_border(coll, m, ground):
    """The house's yard fence: weathered boards on posts as the farm's, lower (1.35 m), a
    share of its bays down to bare rails; the yard gate's two log posts and lintel face
    the track (its leaf long gone), and the paths leave through gaps. Built last, from its
    own random sequence, so nothing else in the farm moves for it."""
    rng = np.random.default_rng(3307)
    b = Batch("fs_yard_fence")
    runs = _yard_runs()
    for name, a, c in runs:
        C._fence_run(b, m, ground, rng, a, c, 1.35, 2.0, 0.78, rails=(0.3, 0.74))
    x0, x1, y0, y1 = YARD
    g0, g1 = YARD_GAPS["s"][0]
    for gx in (g0 - 0.08, g1 + 0.08):
        z = ground(gx, y0)
        RK.log(b, m["bark"], Vector((gx, y0, z - 0.5)), Vector((gx, y0, z + 2.3)), 0.12, 0.11, rng)
    zg = ground((g0 + g1) / 2, y0)
    RK.timber(b, m["hewn"], Vector((g0 - 0.45, y0, zg + 2.12)), Vector((g1 + 0.45, y0, zg + 2.17)), 0.13, 0.11, rng)
    b.build(coll)
    for name, a, c in runs:
        za = min(ground(*a), ground(*c))
        wall_colliders(coll, f"fs_yard_{name}", a, c, za - 0.3, 1.75, [], thick=0.16, surface="teak")
    # What grew where the fence now stands goes (the fence's feet get the game's tall grass).
    gone = []
    for o in coll.objects:
        if o.type != "MESH" or not (o.name.endswith("_n") or "_n." in o.name or "flora" in o.keys()):
            continue
        bb = [o.matrix_world @ Vector(v) for v in o.bound_box]
        cx, cy = sum(p.x for p in bb) / 8, sum(p.y for p in bb) / 8
        if max(max(p.x for p in bb) - min(p.x for p in bb), max(p.y for p in bb) - min(p.y for p in bb)) > 4.0:
            continue
        if any(_seg_distance(cx, cy, *a, *c) < 0.5 for _, a, c in runs):
            gone.append(o)
    for o in gone:
        bpy.data.objects.remove(o, do_unlink=True)
    _hide_colliders(coll)
    return runs


def dry_field(coll, m, ground, rng, x0, x1, y0, y1, name):
    """A harvested paddy gone dry: cracked mud between low bunds, rows of cut stubble."""
    step = 0.6
    nx, ny = int((x1 - x0) / step) + 1, int((y1 - y0) / step) + 1
    verts, faces, uvs = [], [], []
    for j in range(ny):
        for i in range(nx):
            x, y = x0 + i * step, y0 + j * step
            verts.append((x, y, ground(x, y) + 0.03))
            uvs.append((x / 2.4, y / 2.4))
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    mesh_object(f"{name}_mud", coll, verts, faces, m["field"], uvs=uvs, smooth=True)
    b = Batch(f"{name}_stubble")
    for y in np.arange(y0 + 0.4, y1 - 0.3, 0.55):
        for x in np.arange(x0 + 0.4, x1 - 0.3, 0.5):
            if rng.random() < 0.18:
                continue
            px, py = x + rng.normal(0, 0.06), y + rng.normal(0, 0.05)
            h = rng.uniform(0.1, 0.22)
            b.lathe(m["stubble"], [(0.045, 0), (0.05, h * 0.3), (0.035, h), (0, h * 1.02)], xf=place(px, py, ground(px, py) + 0.02),
                    segments=6, tile=0.3, radial=lambda a, hh: 1 + 0.35 * math.sin(a * 5 + hh * 40))
    b.build(coll)
    # The bunds round the field: low banks of earth.
    for (a, c) in (((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))):
        _ribbon(coll, ground, [a, c], 0.35, m["path"], f"{name}_bund", lift=0.12, wob=0.05, rng=rng)


def groves(coll, f, ground, rng, keep_out, game=False):
    """Banana clumps, palms and a few old trees between the buildings: the tangle. Off the
    paths, and a tree's crown never over a roof."""
    keys = {"banana": ["banana_clump"], "palm": ["sugar_palm"], "tree": ["forest_tree_gn"],
            "mixed": ["banana_clump", "banana_clump", "banana_clump", "sugar_palm", "forest_tree_gn"]}
    placed = 0
    for (cx, cy), r, n, kind in GROVES:
        for k in range(n * 10):
            a, d = rng.uniform(0, math.tau), r * math.sqrt(rng.random())
            x, y = cx + d * math.cos(a), cy + d * math.sin(a)
            key = keys[kind][rng.integers(0, len(keys[kind]))]
            s = rng.uniform(0.38, 0.52) if key == "forest_tree_gn" else rng.uniform(0.85, 1.25)
            margin = 0.6 * TREE_CROWN * s if key == "forest_tree_gn" else 1.5
            if _box_distance(x, y, keep_out) < margin or path_distance(x, y) < (2.0 if key == "forest_tree_gn" else 0.9):
                continue
            # The game draws the lighter scan away from where Sora walks.
            src = f[key][1] if game and path_distance(x, y) > 6.0 else f[key][0]
            VN.place(coll, src, f"fs_grove_{key}", x, y, VN.ground_under(ground, x, y, 0.5), rng.uniform(0, math.tau), s)
            placed += 1
            n -= 1
            if n <= 0:
                break
    return placed


def _smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def _seg_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def path_distance(x, y):
    """Metres from (x, y) to the nearest path's edge, the cart track's included (< 0 on it)."""
    best = 1e9
    for pts, half in PATHS + [TRACK]:
        for a, b in zip(pts, pts[1:]):
            best = min(best, _seg_distance(x, y, *a, *b) - half)
    return best


def _box_distance(x, y, boxes):
    """Metres from (x, y) to the nearest box (< 0 inside one)."""
    best = 1e9
    for x0, x1, y0, y1 in boxes:
        dx, dy = max(x0 - x, 0.0, x - x1), max(y0 - y, 0.0, y - y1)
        best = min(best, math.hypot(dx, dy) if (dx or dy) else -min(x - x0, x1 - x, y - y0, y1 - y))
    return best


def _fence_lines():
    x0, x1, y0, y1 = FARM
    bx, by0, by1 = BARN_FENCE
    kx, ky0, ky1 = KITCHEN_FENCE
    return [((x0, y0), (x1, y0)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1)), ((x0, y1), (x1, y1)),
            ((bx, by0), (bx, by1)), ((bx, by1), (BARN[1] + 6.0, by1)), ((bx, by0), (BARN[1] + 6.0, by0)),
            ((kx, ky0), (kx, ky1))] + [(a, c) for _, a, c in _yard_runs()]


def ground_cover(coll, ground, rng, keep_out, game=False):
    """Grass, weeds, shrubs and litter over the yard floor: trodden bare by the doors and
    along the paths, thick at the feet of the fences, on the field bunds and in the shade
    of the groves, where nobody walks."""
    src = {role: [o for name in names for o in VN.poly_haven(name)] for role, names in COVER.items()}
    # Tall grass from the bigger clumps only (the tiny ones read as bare mud at eye level).
    src["tall"] = sorted(src["tall"], key=lambda o: -max(o.dimensions))[:max(4, len(src["tall"]) * 3 // 5)]
    import ground_mask as GM
    # The game grows its tall grass at runtime (TallGrass.ts) and batches the rest: it gets
    # no grass clumps from here and a quarter of the other plants.
    smau = None if game else bpy.data.objects.get("tpl_grass_clump")
    keep = 0.28 if game else 1.0
    fence = _fence_lines()
    x0, x1, y0, y1 = FARM
    step = 0.7
    count = {}
    for y in np.arange(y0 + 0.6, y1 - 0.4, step):
        for x in np.arange(x0 + 0.6, x1 - 0.4, step):
            px, py = x + rng.uniform(-0.38, 0.38), y + rng.uniform(-0.38, 0.38)
            dfield = _box_distance(px, py, FIELDS)
            if dfield < -0.7:
                continue                    # the field itself: its own stubble
            dp = path_distance(px, py)
            db = _box_distance(px, py, keep_out)
            if dp < 0.08 or db < 0.2:
                continue
            df = min(_seg_distance(px, py, *a, *c) for a, c in fence)
            shade = any(math.hypot(px - cx, py - cy) < r + 1.2 for (cx, cy), r, _n, _k in GROVES)
            wild = _smooth(0.1, 2.8, dp) * _smooth(0.3, 3.2, db)
            edge = max(1 - _smooth(0.1, 1.0, df), 1 - _smooth(0.0, 0.9, abs(dfield)))   # fence feet, bunds
            wild = max(wild, 0.9 * edge * _smooth(0.0, 0.5, dp))
            if smau is not None and wild > 0.55 and GM.fbm(px / 7.0 + 31.0, py / 7.0 - 17.0) > 0.47 and rng.random() < 0.9:
                for _ in range(int(rng.integers(1, 4))):
                    VN.put(coll, smau, px + rng.normal(0, 0.25), py + rng.normal(0, 0.25), ground, rng.uniform(0, math.tau),
                           rng.uniform(0.75, 1.25) * (0.75 + 0.35 * wild))
                    count["smau"] = count.get("smau", 0) + 1
                if rng.random() < 0.6:
                    continue
            if rng.random() > 0.12 + 0.85 * wild:
                continue
            if game and rng.random() > keep:
                continue
            r = rng.random()
            if shade and r < 0.4:
                role = "shade"
            elif wild > 0.75 and r < 0.13:
                role = "shrub"
            elif r < 0.12 + 0.55 * wild:
                role = "tall"
            elif r < 0.78:
                role = "short"
            elif r < 0.93:
                role = "weed"
            else:
                role = "litter"
            s = {"tall": rng.uniform(0.9, 1.2) + 0.8 * wild, "short": rng.uniform(1.3, 2.0), "weed": rng.uniform(0.9, 1.4),
                 "shrub": rng.uniform(0.75, 1.2), "shade": rng.uniform(0.9, 1.4), "litter": rng.uniform(0.8, 1.2)}[role]
            if game and role == "tall":
                continue
            pool = src[role]
            clumps = {"short": 1 if game else 3, "tall": 1 + int(wild > 0.45) + int(wild > 0.8)}.get(role, 1)
            for _ in range(clumps):
                VN.put(coll, pool[int(rng.integers(len(pool)))], px + rng.normal(0, 0.22), py + rng.normal(0, 0.22),
                       ground, rng.uniform(0, math.tau), s * rng.uniform(0.85, 1.15))
                count[role] = count.get(role, 0) + 1
    return count


def build(coll, ground, rng=None, flora=None, game=False):
    rng = rng or np.random.default_rng(1932)
    m = materials()
    f = flora or VN.flora()
    kitchen_glow = kitchen_house(coll, m, ground, rng)
    rice_barn(coll, m, ground, rng)
    tool_shed(coll, m, ground, rng, door_open=not game)
    servants_hut(coll, m, ground, rng)
    old_yard(coll, m, ground, rng)
    fences(coll, m, ground, rng)
    for k, fld in enumerate(FIELDS):
        dry_field(coll, m, ground, rng, *fld, f"fs_field_{k}")
    for k, (pts, half) in enumerate(PATHS):
        _ribbon(coll, ground, pts, half, m["path"], f"fs_path_{k}", rng=rng)
    buildings = [(-9, 9, 8, 36), KITCHEN, SERVANTS, BARN, TOOL_SHED, (26, 32, 2, 8), (31, 34, 28, 31),
                 (WELL[0] - 1.4, WELL[0] + 1.4, WELL[1] - 1.4, WELL[1] + 1.4)]
    groves(coll, f, ground, rng, buildings + [(-14, -4, 47, 56), (-29, -21, 44, 53)] + list(FIELDS), game=game)
    stupas = []
    for o in coll.objects:
        if o.name.startswith("col_ng_chedei"):
            bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
            stupas.append((min(p.x for p in bb), max(p.x for p in bb), min(p.y for p in bb), max(p.y for p in bb)))
    print("[farmstead] ground cover", ground_cover(coll, ground, rng, buildings + stupas, game=game), flush=True)
    C.OUTER = FARM
    C.tree_wall(coll, ground, rng, f, depth=(2.5, 14.0), spacing=3.4)
    house_border(coll, m, ground)
    _hide_colliders(coll)
    return kitchen_glow
