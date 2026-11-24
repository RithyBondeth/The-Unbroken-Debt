"""Episode 1's family house re-planned (November 21, 2026): the same colonial-era teak
house on its stilts (weatherboards, louvred shutters, plain plank doors, Marseille tiles,
plinth posts: tools/areas/colonial_house.py), but laid out new and deeper so it plays
as a maze, after the user's "redesign the whole house ... complex layout and scary"
and "redo the front too".

Main floor (2.5 m), north up:
- Front block (x -6..6, y 10..22) over the funeral: the veranda (the front stairs at
  its east end); the hall with the ancestor altar on its north wall and a trapdoor in
  its south-west corner down to the funeral; behind the altar the washing room, where
  the body was washed, reached by a narrow door either side of the altar and opening
  north to the back corridor; west, Yay Mey's room and her loom room (the attic ladder,
  a door out to the west gallery and the walkway); east, the parlour and Vuthy's room.
  Side galleries both sides make loops for chases.
- Back block (x -8..8, y 22..34), twice as deep as before: a cross corridor, then a
  long narrow corridor north to a back door nailed shut; west, Sok's study, Sok's
  bedroom and the padlocked room (his medical logs); east, Kanha's room kept as it was,
  the store room, the landing with the rear stairs down, and the washroom.
- Above: the attic under the front roof (plank paths over the ceiling joists, dead
  ends), through a hatch over the loom room.
- West: a raised walkway from the west gallery towards the kitchen house.

The wall builder, windows, veranda and roof are colonial_house's own, pointed at this
plan by `configure()` (they read the plan from that module). The doors are this module's
own and plain (the user, November 23: the old panelled doors with fanlights, strap hinges
and leaves left at odd angles were "so complicated" and full of bugs): a plank frame, a
ledged plank leaf; the doors play needs shut are shut and solid, every other leaf stands
folded right back flat against its wall (fold_clear() picks the side with nothing there).
Blender axes: X east, Y north, Z up; metres. Run inside Blender.
"""
import math
import re

import bpy
import numpy as np
from mathutils import Matrix, Vector

import colonial_house as CH
from colonial_parts import _pivot_at_origin, _uv_box, hang, plinth_post
from khmer import join
from kit import box, collider, library_material, mesh_object, tube

FLOOR, ZW, T = CH.FLOOR, CH.ZW, CH.T
DOOR = CH.DOOR
H = CH.H                       # the front block keeps its footprint (the funeral is under it)
FRONT = CH.FRONT
B = {"x0": -8.0, "x1": 8.0, "y0": 22.0, "y1": 34.0}
CORR = 23.4                    # the cross corridor's north wall
LC = 0.7                       # the long corridor's half width
ALTAR_Y = 17.5                 # the hall's north wall, the altar against it
SPLIT = 16.0                   # Yay Mey's room / loom room, parlour / Vuthy's room
ROW1, ROW2 = 27.4, 30.6        # the back rooms' cross walls
LAND_X = 4.5                   # landing / washroom
TRAP = (-2.75, -1.95, 11.85, 12.65)
STAIR_HOLE = (2.3, 3.2, 30.75, 33.8)
# The attic hatch, 1.65 m in from the north eave (at 20.95 the roof stood 0.67 m over the
# attic boards: no room to climb out); its ladder leans from the north, so Sora climbs
# facing south and steps off onto the plank path.
HATCH = (-5.65, -4.95, 19.3, 20.0)
WALKWAY = (-20.0, -8.0, 18.55, 19.75)   # into the kitchen house's east door (farmstead.py)
PORCH_N = {"x0": -2.0, "x1": 2.0, "y0": 34.0, "y1": 35.4}

WALLS = [
    # name, along_x, slab low, slab high, a0, a1, door gaps, window gaps, outside sign (0 = partition)
    ("wall_front", True, FRONT - T, FRONT, H["x0"], H["x1"], [(-0.5, 0.5)], [(-4.9, -4.1), (4.1, 4.9)], -1),
    ("wall_west", False, H["x0"], H["x0"] + T, FRONT, H["y1"], [(18.7, 19.6)], [(12.6, 13.4), (14.9, 15.7), (20.4, 21.2)], -1),
    ("wall_east", False, H["x1"] - T, H["x1"], FRONT, H["y1"], [(14.6, 15.5), (20.2, 21.1)], [(12.6, 13.4), (16.6, 17.4)], 1),
    # The old back wall, its weatherboards now inside the cross corridor; its shutters stay shut.
    ("wall_back", True, H["y1"] - T, H["y1"], H["x0"], H["x1"], [(0.4, 1.3)], [(-4.9, -4.1), (4.1, 4.9)], 1),
    ("wall_yaymey_hall", False, -3.0, -3.0 + T, FRONT, H["y1"], [(14.6, 15.5)], [], 0),
    ("wall_parlour_hall", False, 3.0 - T, 3.0, FRONT, H["y1"], [(14.6, 15.5)], [], 0),
    ("wall_yaymey_loom", True, SPLIT - T / 2, SPLIT + T / 2, H["x0"], -3.0, [(-5.3, -4.4)], [], 0),
    ("wall_parlour_vuthy", True, SPLIT - T / 2, SPLIT + T / 2, 3.0, H["x1"], [(4.4, 5.3)], [], 0),
    ("wall_altar", True, ALTAR_Y - T / 2, ALTAR_Y + T / 2, -3.0, 3.0, [(-2.8, -2.1), (2.1, 2.8)], [], 0),
    # The back block.
    ("wall_corr", True, CORR - T / 2, CORR + T / 2, B["x0"] + T, B["x1"] - T, [(-LC, LC)], [], 0),
    ("wall_lc_w", False, -LC - T / 2, -LC + T / 2, CORR + T / 2, B["y1"] - T, [(24.6, 25.5), (28.6, 29.5), (31.8, 32.7)], [], 0),
    ("wall_lc_e", False, LC - T / 2, LC + T / 2, CORR + T / 2, B["y1"] - T, [(24.6, 25.5), (28.6, 29.5), (31.8, 32.7)], [], 0),
    ("wall_study_bed", True, ROW1 - T / 2, ROW1 + T / 2, B["x0"] + T, -LC, [(-5.0, -4.1)], [], 0),
    ("wall_bed_locked", True, ROW2 - T / 2, ROW2 + T / 2, B["x0"] + T, -LC, [], [], 0),
    ("wall_kanha_store", True, ROW1 - T / 2, ROW1 + T / 2, LC, B["x1"] - T, [], [], 0),
    ("wall_store_landing", True, ROW2 - T / 2, ROW2 + T / 2, LC, B["x1"] - T, [], [], 0),
    ("wall_landing_wash", False, LAND_X - T / 2, LAND_X + T / 2, ROW2 + T / 2, B["y1"] - T, [(32.4, 33.3)], [], 0),
    ("wall_back_n", True, B["y1"] - T, B["y1"], B["x0"], B["x1"], [(-0.45, 0.45)], [(-6.6, -5.8), (-3.4, -2.6), (2.4, 3.2), (6.0, 6.8)], 1),
    ("wall_back_w", False, B["x0"], B["x0"] + T, B["y0"], B["y1"], [], [(24.9, 25.7), (28.6, 29.4), (31.9, 32.7)], -1),
    ("wall_back_e", False, B["x1"] - T, B["x1"], B["y0"], B["y1"], [], [(24.9, 25.7), (28.6, 29.4), (31.9, 32.7)], 1),
]
BOARD_ENDS = {"wall_west": (FRONT - T - 0.03, H["y1"] + 0.03), "wall_east": (FRONT - T - 0.03, H["y1"] + 0.03),
              "wall_back_w": (B["y0"], B["y1"] + 0.03), "wall_back_e": (B["y0"], B["y1"] + 0.03),
              "wall_back_n": (B["x0"] - 0.04, B["x1"] + 0.04)}
# (name, wall, a, b, swing radians: 0 shut)
WINDOWS = [
    # Yay Mey's two corner windows are the Krasue's (src/episodes/ep1/data/krasue.ts): their
    # shutters stand wide open, or Sora could never see it come.
    ("win_yaymey_s", "wall_front", -4.9, -4.1, 1.45), ("win_parlour_s", "wall_front", 4.1, 4.9, 0.35),
    ("win_yaymey_w", "wall_west", 12.6, 13.4, 1.45), ("win_yaymey_w2", "wall_west", 14.9, 15.7, 0.2),
    ("win_loom_w", "wall_west", 20.4, 21.2, 0.0),
    ("win_parlour_e", "wall_east", 12.6, 13.4, 0.0), ("win_vuthy_e", "wall_east", 16.6, 17.4, 1.1),
    ("win_loom_n", "wall_back", -4.9, -4.1, 0.0), ("win_vuthy_n", "wall_back", 4.1, 4.9, 0.0),
    ("win_locked_n", "wall_back_n", -6.6, -5.8, 0.0), ("win_bed_n", "wall_back_n", -3.4, -2.6, 0.0),
    ("win_landing_n", "wall_back_n", 2.4, 3.2, 0.5), ("win_wash_n", "wall_back_n", 6.0, 6.8, 0.0),
    ("win_study_w", "wall_back_w", 24.9, 25.7, 0.0), ("win_bed_w", "wall_back_w", 28.6, 29.4, 0.3),
    ("win_locked_w", "wall_back_w", 31.9, 32.7, 0.0),
    ("win_kanha_e", "wall_back_e", 24.9, 25.7, 0.15), ("win_store_e", "wall_back_e", 28.6, 29.4, 0.0),
    ("win_wash_e", "wall_back_e", 31.9, 32.7, 0.0),
]
# (name, wall, a, b, leaf): leaf None for an open doorway, "pair" for the front doors, or the
# side the leaf opens to (+1 towards +y in a wall along x, towards -x in a wall along y).
# Doors open into rooms, not corridors.
DOORS = [
    ("front", "wall_front", -0.5, 0.5, "pair"), ("wash_n", "wall_back", 0.4, 1.3, -1),
    ("yaymey", "wall_yaymey_hall", 14.6, 15.5, 1), ("parlour", "wall_parlour_hall", 14.6, 15.5, -1),
    ("loom", "wall_yaymey_loom", -5.3, -4.4, 1), ("vuthy", "wall_parlour_vuthy", 4.4, 5.3, 1),
    ("altar_w", "wall_altar", -2.8, -2.1, 1), ("altar_e", "wall_altar", 2.1, 2.8, 1),
    ("loom_gallery", "wall_west", 18.7, 19.6, -1), ("parlour_gallery", "wall_east", 14.6, 15.5, 1),
    ("vuthy_gallery", "wall_east", 20.2, 21.1, 1), ("lc", "wall_corr", -LC, LC, None),
    ("sok", "wall_lc_w", 24.6, 25.5, -1), ("bedroom", "wall_lc_w", 28.6, 29.5, 1),
    ("locked", "wall_lc_w", 31.8, 32.7, -1), ("kanha", "wall_lc_e", 24.6, 25.5, -1),
    ("store", "wall_lc_e", 28.6, 29.5, -1), ("landing", "wall_lc_e", 31.8, 32.7, None),
    ("study_bed", "wall_study_bed", -5.0, -4.1, 1), ("wash", "wall_landing_wash", 32.4, 33.3, -1),
    ("back", "wall_back_n", -0.45, 0.45, -1),
]
# The doors play keeps shut (and solid): Yay Mey resting behind hers, Sok's study until it is
# unlocked, the padlocked logs room (its key in Kanha's room), the back door nailed shut.
SHUT = {"yaymey", "sok", "locked", "back"}
LEAF_T, LEDGE_T = 0.032, 0.024
# Each open leaf's two places folded back against its wall: [(hinge, turn) beside a, beside b].
FOLDS = {}
FRONT_POSTS = [(x, y) for x in (-6.0, -3.0, 0.0, 3.0, 6.0) for y in (10.0, 14.0, 18.0, 22.0)]
BACK_POSTS = [(x, y) for x in (-8.0, -4.35, -LC, LC, 4.35, 8.0) for y in (26.0, 30.0, 34.0)] + [(-8.0, 22.0), (8.0, 22.0)]
GALLERY_POSTS = [(x, y) for x in (-8.0, 8.0) for y in (14.0, 18.0)]


def configure():
    """Points colonial_house's builders at this plan."""
    CH.WALLS = WALLS
    CH.DOOR_TOP = DOOR   # plain doors: no fanlight, the wall closed over the door head
    CH.BOARD_ENDS = BOARD_ENDS
    CH.B = B
    CH.CORRIDOR = CORR
    CH.RIDGE_B = CH.VALLEY + (B["y1"] - B["y0"]) / 2 * math.tan(CH.PITCH)


def existing_materials():
    """The house's surfaces as the village file already has them (reading them back keeps
    a preview from regenerating and rewriting the texture files)."""
    def of(obj, k=0):
        return bpy.data.objects[obj].material_slots[k].material
    m = {
        "cl_weatherboard": of("wall_west_boards"), "cl_room_boards": of("wall_west_lining"), "cl_ceiling": of("house_ceiling"),
        "cl_shutter": of("win_kitchen_w_shutter_0"), "cl_trim": of("tie_beam_-6"), "cl_terracotta": of("roof_s_tiles"),
        "cl_plinth": of("pillar_-6_10_plinth"), "iron": of("win_kitchen_w_bars"), "floor": bpy.data.materials["M_floor_boards"],
    }
    for key, name in (("brass", "M_brass"), ("termite", "M_house_detail_termite_mud"), ("rag", "M_wet_rag")):
        m[key] = bpy.data.materials.get(name)
    return m


# ------------------------------------------------------------------ helpers


def _wall(name):
    return next(w for w in WALLS if w[0] == name)


def _on_wall(x, y, reach=0.15):
    """Whether a post at (x, y) stands in a wall (not in one of its openings)."""
    for name, along_x, lo, hi, a0, a1, doors, windows, out in WALLS:
        f, a = (y, x) if along_x else (x, y)
        if lo - reach <= f <= hi + reach and a0 - reach <= a <= a1 + reach:
            if not any(g0 - 0.2 < a < g1 + 0.2 for g0, g1 in doors + windows):
                return True
    return False


def _cut(spans, a0, a1):
    """Removes [a0, a1] from a list of (lo, hi) spans."""
    out = []
    for lo, hi in spans:
        if a1 <= lo or a0 >= hi:
            out.append((lo, hi))
            continue
        if a0 > lo:
            out.append((lo, a0))
        if a1 < hi:
            out.append((a1, hi))
    return [s for s in out if s[1] - s[0] > 0.02]


def _deck(name, coll, m, x0, x1, y0, y1, holes=(), along_x=True, joist_step=0.8, girders=(), z=FLOOR, missing=()):
    """Floor boards with real gaps on joists, cut round `holes` (x0, x1, y0, y1); a
    girder under each post row; one collider per clear rectangle is left to the game
    build (the preview needs none). `missing`: indices of boards left out (broken)."""
    boards, joists = [], []
    k = 0
    if along_x:
        y = y0
        while y < y1 - 0.02:
            yb = (y + 0.0005, min(y1, y + 0.2095))
            spans = [(x0 - 0.04, x1 + 0.04)]
            for hx0, hx1, hy0, hy1 in holes:
                if yb[1] > hy0 and yb[0] < hy1:
                    spans = _cut(spans, hx0, hx1)
            for s0, s1 in spans:
                if k not in missing:
                    boards.append(box(f"{name}_board", coll, s0, s1, yb[0], yb[1], z - 0.05, z, m["floor"]))
                k += 1
            y += 0.21
        for x in np.arange(x0 + 0.1, x1, joist_step):
            spans = [(y0, y1)]
            for hx0, hx1, hy0, hy1 in holes:
                if hx0 - 0.05 < x < hx1 + 0.05:
                    spans = _cut(spans, hy0, hy1)
            for s0, s1 in spans:
                joists.append(box(f"{name}_joist", coll, x - 0.04, x + 0.04, s0, s1, z - 0.18, z - 0.05, m["cl_trim"]))
    else:
        x = x0
        while x < x1 - 0.02:
            xb = (x + 0.0005, min(x1, x + 0.2095))
            if k not in missing:
                boards.append(box(f"{name}_board", coll, xb[0], xb[1], y0 - 0.04, y1 + 0.04, z - 0.05, z, m["floor"]))
            k += 1
            x += 0.21
        for y in np.arange(y0 + 0.1, y1, joist_step):
            joists.append(box(f"{name}_joist", coll, x0, x1, y - 0.04, y + 0.04, z - 0.18, z - 0.05, m["cl_trim"]))
    # Trimmers framing each hole.
    for k2, (hx0, hx1, hy0, hy1) in enumerate(holes):
        for yy in (hy0 - 0.08, hy1):
            joists.append(box(f"{name}_trimmer", coll, hx0 - 0.08, hx1 + 0.08, yy, yy + 0.08, z - 0.18, z - 0.05, m["cl_trim"]))
    if boards:
        join(boards, f"{name}_boards")
    if joists:
        join(joists, f"{name}_joists")
    for k3, (gx0, gy0, gx1, gy1) in enumerate(girders):
        box(f"{name}_girder_{k3}", coll, gx0, gx1, gy0, gy1, z - 0.42, z - 0.18, m["cl_trim"], edge=0.006)


def plank_door(name, coll, width, height, wood, ledge):
    """A ledged door: vertical boards with a hair's gap between them and two ledges across
    one face, built at the origin with its hinge edge on the Z axis, closed along +X
    (thickness across Y, the ledges on +Y). Nothing else: no panels, no strap hinges."""
    n = max(3, round(width / 0.15))
    bw = width / n
    parts = [box(f"{name}_board", coll, k * bw + 0.0015, (k + 1) * bw - 0.0015, -LEAF_T / 2, LEAF_T / 2, 0, height, wood,
                 edge=0.003) for k in range(n)]
    for z in (0.3, height - 0.34):
        parts.append(box(f"{name}_ledge", coll, 0.05, width - 0.05, LEAF_T / 2, LEAF_T / 2 + LEDGE_T, z - 0.06, z + 0.06,
                         ledge, edge=0.004))
    return _pivot_at_origin(join(parts, name))


def door_frame(coll, m, name, wall_name, a, b):
    """Two jambs and a head of plain plank, standing a little proud of both faces."""
    _, along_x, lo, hi, *_r, out = CH._wall(wall_name)
    proud = 0.045 if out else 0.025   # outside walls carry weatherboards over the slab
    f0, f1 = lo - proud, hi + proud
    for k, (p0, p1) in enumerate(((a - 0.07, a), (b, b + 0.07))):
        CH._box_on(f"door_frame_{name}_{k}", coll, along_x, f0, f1, p0, p1, FLOOR, DOOR + 0.07, m["cl_trim"], edge=0.004)
    CH._box_on(f"door_head_{name}", coll, along_x, f0, f1, a - 0.07, b + 0.07, DOOR, DOOR + 0.07, m["cl_trim"], edge=0.004)


def _folds(wall_name, a, b, side):
    """Where a leaf opening to `side` lies folded back flat on that room face: hinged at a
    and lying over the wall beyond a, or hinged at b and lying over the wall beyond b."""
    _, along_x, lo, hi, *_r, out = CH._wall(wall_name)
    on_hi = side > 0 if along_x else side < 0
    clear = LEAF_T / 2 + LEDGE_T + 0.012 + (0.02 if out else 0.0)
    c = hi + clear if on_hi else lo - clear
    if along_x:
        return [((a, c), math.pi), ((b, c), 0.0)]
    return [((c, a), -math.pi / 2), ((c, b), math.pi / 2)]


def _place(leaf, spot):
    (x, y), turn = spot
    hang(leaf, (x, y, FLOOR + 0.008), turn)


def doors(coll, m):
    FOLDS.clear()
    wood, ledge = m["cl_shutter"], m["cl_trim"]
    height = DOOR - FLOOR - 0.015
    for name, wall_name, a, b, leaf in DOORS:
        door_frame(coll, m, name, wall_name, a, b)
        if leaf is None:
            continue
        if leaf == "pair":
            # The front doors, both folded back against the front wall inside the hall.
            w = (b - a) / 2 - 0.01
            for nm, spot in zip(("door_front_leaf_l", "door_front_leaf_r"), _folds(wall_name, a, b, 1)):
                lf = plank_door(nm, coll, w, height, wood, ledge)
                _place(lf, spot)
                FOLDS[nm] = [spot]
            continue
        _, along_x, lo, hi, *_r = CH._wall(wall_name)
        mid = (lo + hi) / 2
        lf = plank_door(f"door_{name}_leaf", coll, b - a - 0.01, height, wood, ledge)
        if name in SHUT:
            _place(lf, (((a + 0.005, mid) if along_x else (mid, a + 0.005)), 0.0 if along_x else math.pi / 2))
            if name not in ("sok", "yaymey", "back"):   # those have their own (rebuild-farmstead.py, below)
                if along_x:
                    collider(f"door_{name}", coll, a, b, lo, hi, FLOOR, DOOR)
                else:
                    collider(f"door_{name}", coll, lo, hi, a, b, FLOOR, DOOR)
        else:
            FOLDS[lf.name] = _folds(wall_name, a, b, leaf)
            _place(lf, FOLDS[lf.name][0])
    _locks(coll, m)


# Things a folded-back leaf may lie over: the walls' own skins, frames, floors, colliders and
# the markers the game reads. Anything else in the way (furniture, a print, a shelf) moves it.
FOLD_IGNORE = re.compile(r"^(door_|col_|wall_|house_floor|house_ceiling|back_floor|floor_|pillar_|win_|light_|marker_|"
                         r"ladder_|nav_|hide_|spawn_|patrol_|trigger_|occ_|tpl_|interact_door|cobweb|dress_.*web)")


def fold_clear():
    """After the rooms are furnished: each folded leaf keeps the first of its places with
    nothing standing or hanging against the wall there, else tries its other, else goes
    (an open doorway is better than a door through a wardrobe)."""
    from mathutils.bvhtree import BVHTree
    vl = bpy.context.view_layer
    vl.update()
    deps = bpy.context.evaluated_depsgraph_get()
    cands = [o for o in bpy.data.objects if o.type == "MESH" and not FOLD_IGNORE.match(o.name) and o.visible_get()
             and len(o.data.vertices) and not o.hide_render]
    boxes = {}
    for o in cands:
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        boxes[o] = (Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)]))
    trees = {}

    def tree_of(o):
        if o not in trees:
            ev = o.evaluated_get(deps)
            me = ev.to_mesh()
            me.transform(o.matrix_world)
            trees[o] = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
            ev.to_mesh_clear()
        return trees[o]

    def blocked(leaf):
        vl.update()
        pts = [leaf.matrix_world @ Vector(c) for c in leaf.bound_box]
        lo = Vector([min(p[i] for p in pts) - 0.03 for i in range(3)])
        hi = Vector([max(p[i] for p in pts) + 0.03 for i in range(3)])
        lo.z = FLOOR + 0.04   # a rug under a door is no matter
        slab = BVHTree.FromPolygons([Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)],
                                    [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
        for o, (blo, bhi) in boxes.items():
            if o is leaf or any(blo[i] > hi[i] or bhi[i] < lo[i] for i in range(3)):
                continue
            inside = all(lo[i] <= blo[i] and bhi[i] <= hi[i] for i in range(3))
            if inside or tree_of(o).overlap(slab):
                return o.name
        return None

    report = {}
    for name, spots in FOLDS.items():
        leaf = bpy.data.objects.get(name)
        if leaf is None:
            continue
        why = None
        for spot in spots:
            _place(leaf, spot)
            why = blocked(leaf)
            if why is None:
                break
        if why is not None:
            report[name] = f"removed ({why})"
            bpy.data.objects.remove(leaf, do_unlink=True)
        else:
            report[name] = "beside a" if spot is spots[0] else "beside b"
    print("[doors] folded", report, flush=True)
    return report


# ------------------------------------------------------------------ structure


def posts(coll, m):
    made = []
    for x, y in FRONT_POSTS + BACK_POSTS:
        top = ZW if (y == 10.0 or _on_wall(x, y)) else FLOOR
        tag = f"{x:.2f}_{y:.0f}".replace(".", "p").replace("-", "m")
        plinth_post(f"pillar_{tag}", coll, x, y, top, m["cl_trim"], m["cl_plinth"], size=0.24, plinth=0.46, plinth_h=0.42)
        collider(f"pillar_{tag}", coll, x - 0.2, x + 0.2, y - 0.2, y + 0.2, 0, top)
        made.append((x, y, top))
    for x, y in GALLERY_POSTS:
        tag = f"{x:.0f}_{y:.0f}".replace("-", "m")
        plinth_post(f"pillar_gallery_{tag}", coll, x, y, CH.GALLERY_EAVE, m["cl_trim"], m["cl_plinth"], size=0.24, plinth=0.46, plinth_h=0.42)
    for x, y in ((PORCH_N["x0"], PORCH_N["y1"]), (PORCH_N["x1"], PORCH_N["y1"])):
        plinth_post(f"pillar_porch_{x:.0f}", coll, x, y, FLOOR + 1.0, m["cl_trim"], m["cl_plinth"], size=0.2, plinth=0.4, plinth_h=0.42)
    # Plates and tie beams the roofs sit on.
    for x in (H["x0"], H["x1"]):
        box(f"tie_beam_{x:.0f}", coll, x - 0.1, x + 0.1, H["y0"] - 0.12, H["y1"] + 0.12, ZW, ZW + 0.2, m["cl_trim"], edge=0.008)
    for x in (B["x0"], B["x1"]):
        box(f"tie_beam_back_{x:.0f}", coll, x - 0.1, x + 0.1, B["y0"] - 0.12, B["y1"] + 0.12, ZW, ZW + 0.2, m["cl_trim"], edge=0.008)
    for y in (H["y0"], H["y1"]):
        box(f"roof_plate_{y:.0f}", coll, H["x0"] - 0.3, H["x1"] + 0.3, y - 0.12, y + 0.12, ZW, ZW + 0.2, m["cl_trim"], edge=0.008)
    box("roof_plate_34", coll, B["x0"] - 0.3, B["x1"] + 0.3, B["y1"] - 0.12, B["y1"] + 0.12, ZW, ZW + 0.2, m["cl_trim"], edge=0.008)
    for x0, x1 in ((B["x0"] - 0.3, H["x0"]), (H["x1"], B["x1"] + 0.3)):
        box(f"roof_plate_22_{x0:.0f}", coll, x0, x1, B["y0"] - 0.12, B["y0"] + 0.12, ZW, ZW + 0.2, m["cl_trim"], edge=0.008)
    return made


def floors(coll, m):
    front_rows = [(H["x0"] - 0.2, y - 0.11, H["x1"] + 0.2, y + 0.11) for y in (10.0, 14.0, 18.0, 22.0)]
    _deck("house_floor", coll, m, H["x0"], H["x1"], H["y0"], H["y1"], holes=[TRAP], girders=front_rows)
    back_rows = [(B["x0"] - 0.2, y - 0.11, B["x1"] + 0.2, y + 0.11) for y in (22.0, 26.0, 30.0, 34.0)]
    _deck("back_floor", coll, m, B["x0"], B["x1"], B["y0"], B["y1"], holes=[STAIR_HOLE], girders=back_rows)
    for label, (x0, x1) in (("gallery_w", (B["x0"], H["x0"])), ("gallery_e", (H["x1"], B["x1"]))):
        _deck(label, coll, m, x0, x1, CH.GALLERY_W[0], CH.GALLERY_W[1], joist_step=0.7,
              girders=[(x0 - 0.1, y - 0.11, x1 + 0.1, y + 0.11) for y in (14.0, 18.0)])
    # The back porch beyond the nailed door: boards gone, its stairs fallen.
    _deck("porch_n", coll, m, PORCH_N["x0"], PORCH_N["x1"], PORCH_N["y0"], PORCH_N["y1"], joist_step=0.7, missing=(2, 3, 5),
          girders=[(PORCH_N["x0"] - 0.1, PORCH_N["y1"] - 0.11, PORCH_N["x1"] + 0.1, PORCH_N["y1"] + 0.11)])
    # The game's floors: one collider per clear rectangle round the trapdoor and the stair
    # well; the trapdoor's lid has its own (the game lifts it); the galleries, the walkway.
    def around(label, rect, hole):
        x0, x1, y0, y1 = rect
        hx0, hx1, hy0, hy1 = hole
        for k, (a, b, c, d) in enumerate(((x0, x1, y0, hy0), (x0, x1, hy1, y1), (x0, hx0, hy0, hy1), (hx1, x1, hy0, hy1))):
            collider(f"{label}_floor_{k}", coll, a, b, c, d, FLOOR - 0.12, FLOOR)
    around("house_floor", (H["x0"], H["x1"], H["y0"], H["y1"]), TRAP)
    collider("trapdoor_lid", coll, TRAP[0], TRAP[1], TRAP[2], TRAP[3], FLOOR - 0.12, FLOOR)
    around("back_floor", (B["x0"], B["x1"], B["y0"], B["y1"]), STAIR_HOLE)
    for label, (x0, x1) in (("gallery_w", (B["x0"], H["x0"])), ("gallery_e", (H["x1"], B["x1"]))):
        collider(f"{label}_floor", coll, x0, x1, CH.GALLERY_W[0], CH.GALLERY_W[1], FLOOR - 0.12, FLOOR)
    collider("walkway_floor", coll, WALKWAY[0], WALKWAY[1], WALKWAY[2], WALKWAY[3], FLOOR - 0.12, FLOOR)


def ceilings(coll, m):
    """Tongue-and-groove ceilings; the loom room's has the attic hatch in it."""
    x0, x1, y0, y1 = H["x0"] + T, H["x1"] - T, FRONT, H["y1"] - T
    hx0, hx1, hy0, hy1 = HATCH
    pieces = [(x0, x1, y0, hy0), (x0, x1, hy1, y1), (x0, hx0, hy0, hy1), (hx1, x1, hy0, hy1)]
    for k, (a0, a1, b0, b1) in enumerate(pieces):
        c = box(f"house_ceiling_{k}", coll, a0, a1, b0, b1, ZW - 0.02, ZW, m["cl_ceiling"])
        c.data.uv_layers.remove(c.data.uv_layers[0])
        _uv_box(c, m["cl_ceiling"], 2.0, 0, 1)
    cb = box("house_ceiling_back", coll, B["x0"] + T, B["x1"] - T, B["y0"], B["y1"] - T, ZW - 0.02, ZW, m["cl_ceiling"])
    cb.data.uv_layers.remove(cb.data.uv_layers[0])
    _uv_box(cb, m["cl_ceiling"], 2.0, 0, 1, u_offset=0.7)
    # The hatch's frame, and its lid lying open on the attic boards.
    for (a0, a1, b0, b1) in ((hx0 - 0.05, hx1 + 0.05, hy0 - 0.05, hy0), (hx0 - 0.05, hx1 + 0.05, hy1, hy1 + 0.05),
                             (hx0 - 0.05, hx0, hy0, hy1), (hx1, hx1 + 0.05, hy0, hy1)):
        box("attic_hatch_frame", coll, a0, a1, b0, b1, ZW - 0.06, ZW + 0.14, m["cl_trim"])
    lid = box("attic_hatch_lid", coll, hx1 + 0.06, hx1 + 0.76, hy0, hy1, ZW + 0.165, ZW + 0.2, m["cl_shutter"])


def attic(coll, m, rng):
    """The roof space over the front block: ceiling joists, plank paths laid over them
    from the hatch (crawl height there) to the standing room under the ridge, and on
    to dead ends; the rest is bare joists over the ceiling."""
    jz = ZW + 0.14
    joists = [box("attic_joist", coll, x - 0.035, x + 0.035, H["y0"] + 0.15, H["y1"] - 0.15, ZW, jz, m["cl_trim"])
              for x in np.arange(H["x0"] + 0.3, H["x1"], 0.6)]
    join(joists, "attic_joists")
    planks = library_material("weathered_planks", "M_sh_attic_planks", tint=(0.62, 0.56, 0.5), tile=1.6)
    hx0, hx1, hy0, hy1 = HATCH
    # The path from the hatch starts at its south edge (it ran on over half the opening).
    paths = [((-5.3, hy0 - 0.1), (-5.3, 16.0)), ((-5.3, 16.0), (5.1, 16.0)), ((0.0, 16.0), (0.0, 12.6)), ((2.6, 16.0), (2.6, 19.6))]
    boards = []
    walk = []
    for (ax, ay), (bx, by) in paths:
        if ax == bx:   # along y: three boards side by side
            for k in range(3):
                x = ax - 0.3 + k * 0.205 + rng.normal(0, 0.006)
                boards.append(box("attic_plank", coll, x, x + 0.2, min(ay, by) - 0.1, max(ay, by) + 0.1, jz, jz + 0.025, planks))
            walk.append((ax - 0.31, ax + 0.31, min(ay, by) - 0.1, max(ay, by) + 0.1))
        else:
            for k in range(3):
                y = ay - 0.3 + k * 0.205 + rng.normal(0, 0.006)
                boards.append(box("attic_plank", coll, min(ax, bx) - 0.1, max(ax, bx) + 0.1, y, y + 0.2, jz, jz + 0.025, planks))
            walk.append((min(ax, bx) - 0.1, max(ax, bx) + 0.1, ay - 0.31, ay + 0.31))
    join(boards, "attic_planks")
    # Something to walk on under every board (only the east-west path had one: off it,
    # Sora fell through the ceiling into the rooms below).
    for k, (x0_, x1_, y0_, y1_) in enumerate(walk):
        collider("attic_paths" if k == 1 else f"attic_paths_{k}", coll, x0_, x1_, y0_, y1_, ZW, jz + 0.03)


def ladder(name, coll, mat, foot, top, width=0.42, rung=0.28):
    """Two rails and round rungs from `foot` to `top` (x, y, z)."""
    foot, top = Vector(foot), Vector(top)
    run = top - foot
    side = run.cross(Vector((0, 0, 1)))
    side = side.normalized() * width / 2 if side.length > 1e-6 else Vector((width / 2, 0, 0))
    parts = []
    for s in (-1, 1):
        parts.append(tube(f"{name}_rail", coll, [tuple(foot + side * s), tuple(top + side * s)], 0.028, mat, sides=6))
    n = int(run.length / rung)
    for k in range(1, n + 1):
        p = foot + run * (k / (n + 0.6))
        parts.append(tube(f"{name}_rung", coll, [tuple(p - side * 1.05), tuple(p + side * 1.05)], 0.018, mat, sides=6))
    return join(parts, name)


def stairs(name, coll, m, top, bottom, width=0.9):
    """A plain teak stair: two stringers, treads, and a handrail on its open side."""
    top, bottom = Vector(top), Vector(bottom)
    run = Vector((bottom.x - top.x, bottom.y - top.y, 0))
    length = run.length
    d = run.normalized()
    side = Vector((-d.y, d.x, 0))
    rise = top.z - bottom.z
    n = max(2, round(rise / 0.19))
    parts = []
    for s in (-1, 1):
        a = top + side * s * (width / 2) + Vector((0, 0, -0.12))
        b = bottom + side * s * (width / 2) + Vector((0, 0, 0.1))
        parts.append(tube(f"{name}_stringer", coll, [tuple(a), tuple(b)], 0.06, m["cl_trim"], sides=4))
    for k in range(1, n):
        f = k / n
        c = top + run * f + Vector((0, 0, -rise * f))
        lo, hi = c - d * 0.02, c + d * (length / n + 0.02)
        xs = [p.x for p in (lo + side * width / 2, lo - side * width / 2, hi + side * width / 2, hi - side * width / 2)]
        ys = [p.y for p in (lo + side * width / 2, lo - side * width / 2, hi + side * width / 2, hi - side * width / 2)]
        parts.append(box(f"{name}_tread", coll, min(xs), max(xs), min(ys), max(ys), c.z - 0.035, c.z, m["floor"]))
    rail = [top + side * (width / 2 + 0.03) + Vector((0, 0, 0.9)), bottom + side * (width / 2 + 0.03) + Vector((0, 0, 0.9))]
    parts.append(tube(f"{name}_handrail", coll, [tuple(p) for p in rail], 0.025, m["cl_trim"], sides=6))
    for k in range(4):
        f = (k + 0.5) / 4
        p = top + run * f + Vector((0, 0, -rise * f)) + side * (width / 2 + 0.03)
        parts.append(tube(f"{name}_baluster", coll, [tuple(p), tuple(p + Vector((0, 0, 0.9)))], 0.02, m["cl_trim"], sides=6))
    return join(parts, name)


def _locks(coll, m):
    """The padlock, the nailed back door's planks and the hall trapdoor's lid."""
    # The padlocked room: hasp, staple and an old padlock on the corridor side.
    x = -LC + T / 2
    box("door_locked_hasp", coll, x, x + 0.004, 32.48, 32.7, FLOOR + 1.02, FLOOR + 1.06, m["iron"])
    box("door_locked_staple", coll, x, x + 0.03, 32.7, 32.73, FLOOR + 1.01, FLOOR + 1.07, m["iron"])
    box("door_locked_padlock", coll, x + 0.015, x + 0.03, 32.69, 32.75, FLOOR + 0.95, FLOOR + 1.03, m["iron"], edge=0.004)
    # The back door nailed shut from inside: rough planks across it, nail heads.
    planks = library_material("weathered_planks", "M_sh_nailed_planks", tint=(0.55, 0.5, 0.45), tile=1.2)
    y = B["y1"] - T - 0.03
    for k, (z, tilt) in enumerate(((FLOOR + 0.45, 0.0), (FLOOR + 1.05, 0.12), (FLOOR + 1.6, -0.06), (FLOOR + 1.9, 0.0))):
        p = box(f"door_back_nail_plank_{k}", coll, -0.68, 0.68, y - 0.026, y, z - 0.085, z + 0.085, planks)
        p.rotation_euler.y = tilt
        for xn in (-0.6, 0.6):
            box(f"door_back_nail_{k}", coll, xn - 0.008, xn + 0.008, y - 0.03, y - 0.026, z - 0.008, z + 0.008, m["iron"])
    plank = box("door_back_nail_plank_diag", coll, -0.75, 0.75, y - 0.05, y - 0.026, FLOOR + 1.2 - 0.09, FLOOR + 1.2 + 0.09, planks)
    plank.rotation_euler.y = math.radians(52)
    collider("door_back_nailed", coll, -0.5, 0.5, y - 0.06, B["y1"], FLOOR, DOOR)
    # The trapdoor in the hall: a lid of boards flush in the floor, an iron ring to lift it.
    hx0, hx1, hy0, hy1 = TRAP
    lid_wood = library_material("weathered_brown_planks", "M_sh_trapdoor_planks", tint=(0.3, 0.24, 0.2), tile=0.9)
    lid = [box("trapdoor_board", coll, hx0 + 0.01 + k * (hx1 - hx0 - 0.02) / 4 + 0.002, hx0 + 0.01 + (k + 1) * (hx1 - hx0 - 0.02) / 4 - 0.002,
               hy0 + 0.01, hy1 - 0.01, FLOOR - 0.045, FLOOR - 0.002, lid_wood) for k in range(4)]
    join(lid, "trapdoor_lid")
    for k in range(3):
        yb = hy0 + 0.03 + k * (hy1 - hy0 - 0.06) / 3
        box("trapdoor_batten", coll, hx0 + 0.03, hx1 - 0.03, yb, yb + 0.06, FLOOR - 0.09, FLOOR - 0.045, m["cl_trim"])
    ring = [(hx1 - 0.12 + 0.035 * math.cos(a), (hy0 + hy1) / 2 + 0.035 * math.sin(a), FLOOR + 0.002) for a in np.linspace(0, math.tau, 17)]
    tube("trapdoor_ring", coll, ring, 0.005, m["iron"], sides=5)
    box("trapdoor_staple", coll, hx1 - 0.135, hx1 - 0.105, (hy0 + hy1) / 2 - 0.05, (hy0 + hy1) / 2 - 0.03, FLOOR - 0.002, FLOOR + 0.01, m["iron"])


def galleries(coll, m):
    g0, g1 = CH.GALLERY_W
    for label, x0, x1, xo in (("gallery_w", B["x0"], H["x0"], B["x0"]), ("gallery_e", H["x1"], B["x1"], B["x1"])):
        posts = [(xo, g0), (xo, 18.0), (xo, g1)]
        if label == "gallery_w":   # a gap in the rail where the walkway leaves
            CH.balustrade(f"{label}_rail_a", coll, m, (xo, g0), (xo, WALKWAY[2]), posts=posts)
            CH.balustrade(f"{label}_rail_b", coll, m, (xo, WALKWAY[3]), (xo, g1), posts=posts)
        else:
            CH.balustrade(f"{label}_rail", coll, m, (xo, g0), (xo, g1), posts=posts)
        CH.balustrade(f"{label}_rail_end", coll, m, (x0, g0), (x1, g0), posts=[(xo, g0), (H["x0"] if x0 < 0 else H["x1"], g0)])
    # The back porch's rail, broken where its stairs fell away.
    CH.balustrade("porch_n_rail_w", coll, m, (PORCH_N["x0"], PORCH_N["y0"]), (PORCH_N["x0"], PORCH_N["y1"]), posts=[(PORCH_N["x0"], PORCH_N["y1"])])
    CH.balustrade("porch_n_rail_n", coll, m, (PORCH_N["x0"], PORCH_N["y1"]), (0.4, PORCH_N["y1"]), posts=[(PORCH_N["x0"], PORCH_N["y1"])])


def walkway(coll, m, rng, ground):
    """A raised plank walkway on posts from the west gallery to the kitchen house's door
    (farmstead.py), with a pole rail each side."""
    x0, x1, y0, y1 = WALKWAY
    _deck("walkway", coll, m, x0, x1, y0, y1, along_x=False, joist_step=0.6,
          girders=[(x0, y - 0.07, x1, y + 0.07) for y in (y0 + 0.08, y1 - 0.08)])
    poles = library_material("weathered_planks", "M_sh_walkway_poles", tint=(0.5, 0.46, 0.42), tile=1.0)
    rails = []
    for x in np.arange(x1 - 0.2, x0, -2.2):
        for y in (y0 + 0.05, y1 - 0.05):
            rails.append(box("walkway_post", coll, x - 0.07, x + 0.07, y - 0.07, y + 0.07, ground(x, y) - 0.1, FLOOR - 0.18, m["cl_trim"]))
            rails.append(tube("walkway_rail_post", coll, [(x, y, FLOOR), (x + rng.normal(0, 0.01), y, FLOOR + 0.95)], 0.035, poles, sides=6))
    for y in (y0 + 0.05, y1 - 0.05):
        rails.append(tube("walkway_rail", coll, [(x1, y, FLOOR + 0.95), (x0 + 0.2, y, FLOOR + 0.93)], 0.03, poles, sides=6))
        collider(f"walkway_rail_{y:.1f}", coll, x0, x1, y - 0.05, y + 0.05, FLOOR, FLOOR + 0.98)
    join(rails, "walkway_frame")


def build(coll, m, ground=lambda x, y: 0.0, seed=1932):
    """The whole shell; everything lands in `coll`. `ground(x, y)` is the terrain height."""
    configure()
    rng = np.random.default_rng(seed)
    posts(coll, m)
    floors(coll, m)
    CH.walls(coll, m)
    ceilings(coll, m)
    for name, wall_name, a, b, swing in WINDOWS:
        CH.window_unit(coll, m, name, wall_name, a, b, swing)
    doors(coll, m)
    CH.veranda(coll, m)
    galleries(coll, m)
    CH.roof(coll, m, rng)
    attic(coll, m, rng)
    walkway(coll, m, rng, ground)
    # The trapdoor's ladder down to the funeral, the loom room's up to the hatch, the rear stairs.
    hx0, hx1, hy0, hy1 = TRAP
    tx = (hx0 + hx1) / 2
    # Down in the opening against its north edge (leaning out under the floor, the climber's
    # head met the boards before the opening): the climber steps off north onto the hall floor.
    ladder("trapdoor_ladder", coll, m["cl_trim"], (tx, hy0 + 0.25, ground(tx, hy0 + 0.25)), (tx, hy1 - 0.05, FLOOR))
    ax0, ax1, ay0, ay1 = HATCH
    ladder("attic_ladder", coll, m["cl_trim"], ((ax0 + ax1) / 2, ay1 + 0.55, FLOOR), ((ax0 + ax1) / 2, (ay0 + ay1) / 2, ZW + 0.15),
           width=0.38, rung=0.26)
    sx0, sx1, sy0, sy1 = STAIR_HOLE
    sx = (sx0 + sx1) / 2
    stairs("rear_stairs", coll, m, (sx, sy1, FLOOR), (sx, sy0 - 0.35, ground(sx, sy0 - 0.35)), width=sx1 - sx0 - 0.08)
    # A rail round the stair well on the landing.
    CH.balustrade("rear_stairs_rail_w", coll, m, (sx0 - 0.05, sy0), (sx0 - 0.05, sy1 - 0.9))
    # Open at the top on both sides, like the west rail: the strip east of the well (and the
    # bathing corner's door off it) is reached across the top of the stairs; railed to the
    # wall, it could not be reached at all.
    CH.balustrade("rear_stairs_rail_e", coll, m, (sx1 + 0.05, sy0), (sx1 + 0.05, sy1 - 0.9))


def rear_barricade(coll, m, rng):
    """O5, Act III: the rear stairs boarded off at their head. Rough planks nailed across
    both ways onto the stairs (west and east of the well's top, where its rails end), bent
    nails, and Vuthy's old trunk dragged against the west boards. The game shows it, and
    its colliders, only in Act III (named `o5_barricade*`)."""
    from shrine_craft import Batch
    sx0, sx1, sy0, sy1 = STAIR_HOLE
    y0, y1 = sy1 - 0.95, sy1 + 0.02
    # The trapdoor's weathered brown planks (built with the house, above).
    planks = bpy.data.materials.get("M_sh_trapdoor_planks") or library_material(
        "weathered_brown_planks", "M_sh_trapdoor_planks", tint=(0.3, 0.24, 0.2), tile=0.9)
    b = Batch("o5_barricade")
    for side, x in (("w", sx0 - 0.06), ("e", sx1 + 0.06)):
        for k, z in enumerate((0.22, 0.5, 0.78, 1.02)):
            tilt = rng.normal(0, 0.06)
            zc = FLOOR + z + rng.normal(0, 0.02)
            b.box(planks, (0.03, y1 - y0 + 0.12, rng.uniform(0.13, 0.17)), (0, 0, 0),
                  xf=Matrix.Translation((x + rng.normal(0, 0.006), (y0 + y1) / 2 + rng.normal(0, 0.03), zc)) @ Matrix.Rotation(tilt, 4, "X"),
                  chamfer=0.004)
            for yn in (y0 + 0.02, y1 - 0.04):   # nail heads, some bent over
                b.box(m["iron"], (0.012, 0.008, 0.008), (x + 0.02 * (1 if side == "e" else -1), yn, zc + 0.03), chamfer=0.001)
        b.box(planks, (0.05, 0.05, 1.2), (x, y0 - 0.02, FLOOR + 0.6))   # an upright nailed to the rail's end
    b.build(coll)
    for side, xa, xb in (("w", sx0 - 0.1, sx0 - 0.02), ("e", sx1 + 0.02, sx1 + 0.1)):
        col = collider(f"o5_barricade_{side}", coll, xa, xb, y0 - 0.05, y1, FLOOR, FLOOR + 1.2)
        col.display_type = "WIRE"
        col.hide_render = True
