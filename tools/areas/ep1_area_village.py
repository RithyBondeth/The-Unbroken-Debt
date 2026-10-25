"""Builds the village for Episode 1, Acts I–III: the 60 m path through the banana
grove from the flooded road, the courtyard with the funeral pavilion, the teak
stilt house (upper floor and the space beneath it), the storage shed, the cooking
shelter for the mourners and the neighbours' huts beyond the fence.

Episode 1 Beat Sheet, sections 4.2–4.4: courtyard 24 x 18 m; the pavilion in
front of the house so its light spills under the stilts; upper floor 12 x 8 m
raised 2.5 m (veranda, hall with the ancestral altar, kitchen, Yay Mey's room,
Sok's room); under the house 15 pillars on a 3 x 4 m grid with the clay jars
J1-J6. Looks follow Léon Busy's 1921 photographs of Cambodia and the funeral
customs in khmer.py (to confirm with the cultural advisor).

Run (repository root), after `npm run fetch-library` and `npm run drawings -- ep1`:
    blender -b --factory-startup -P tools/areas/ep1_area_village.py
then `npm run export -- ep1 && npm run assets -- ep1`.

Blender axes: X east, Y north (towards the house), Z up; metres.
"""

import math
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from kit import *  # noqa: E402,F403  (shared materials and geometry)
from khmer import *  # noqa: E402,F403  (Khmer village builders)
from hall_altar import build_hall_altar
from house_detail import board_panel, gathered_hammock
from forest import *  # noqa: E402,F403  (the forest, the road and what the dead left)

BLEND = os.path.join(ROOT, "art-source", "blender", "ep1", "ep1_area_village.blend")
rng = np.random.default_rng(1910)

FLOOR = 2.5  # upper floor height (stilts)
WALL_H = 2.6
ZW = FLOOR + WALL_H  # top of the walls
HOUSE = {"x0": -6.0, "x1": 6.0, "y0": 10.0, "y1": 18.0}
TENT = {"x0": -4.0, "x1": 4.0, "y0": 1.0, "y1": 7.0, "eave": 2.6, "ridge": 4.6}
YARD = {"x0": -13.0, "x1": 13.0, "y0": -3.0, "y1": 22.0}
# The 60 m path from the road (A1-01): a gentle S through the grove, south to north.
PATH = [(1.5, -60.0), (2.5, -50.0), (0.5, -40.0), (-2.5, -30.0), (-2.0, -20.0), (0.5, -10.0), (0.0, -3.0)]
# The compound stands alone in the forest: no neighbours in sight, only old wells
# (the open one just outside the west fence, one half covered in the grove).
WELLS = [(-17.0, 7.5, False), (9.5, -33.0, True)]
POND = (-20.0, 19.0, 4.0, 3.0)
# Dead trees hung with rags and offerings, deeper in the forest (two seen from the path).
RAG_TREES = [(-6.0, -24.5), (6.5, -45.0), (-16.0, 1.0), (14.0, -8.0), (-15.0, -40.0), (20.0, 5.0)]
HERO_TREES = [(-32.0, 18.0), (30.0, -18.0), (-30.0, -50.0), (33.0, 30.0), (-23.0, 9.0), (22.0, -2.0), (-19.0, -29.0),
              (19.0, -40.0), (-30.0, -3.0), (31.0, 12.0), (-26.0, 30.0), (26.0, -25.0)]
ROAD_Y = -63.5  # centre of the road along the paddies (A1-01)
BANYAN = (-7.0, -35.5)
BAMBOO = [(-9, -7), (8.5, -9), (-16, 18), (16, 6), (-7, -52), (8, -42), (-12, -24), (11, -30), (14.5, 24.5), (-15, 27)]
TREES = [(-12, -14), (10, -20), (-8, -44), (12, -48), (-18, -5), (18, -16), (-20, 14), (20, 20), (-6, 30), (8, 31),
         (-16, -40), (15, -31), (-10, -58), (11, -58)]
DEAD = [(-5, -15), (6, -24), (-8, -57), (5.5, -37), (-14, -48), (13, -12), (-22, 22), (24, 10)]
# Things placed in the grove: nothing else grows within this distance of them.
CLEAR = [(BANYAN, 5.5)] + [(p, 2.2) for p in BAMBOO] + [(p, 2.0) for p in TREES] + [(p, 1.2) for p in DEAD]


def path_distance(x, y):
    """Distance from (x, y) to the path's centre line."""
    best = 1e9
    for (ax, ay), (bx, by) in zip(PATH, PATH[1:]):
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(x - ax - dx * t, y - ay - dy * t))
    return best


def in_yard(x, y, margin=0.0):
    return YARD["x0"] - margin < x < YARD["x1"] + margin and YARD["y0"] - margin < y < YARD["y1"] + margin


def adopt(parent, objs):
    """Puts objects under an interact_ empty without moving them, so the game can
    outline and use them as one thing."""
    bpy.context.view_layer.update()
    for obj in objs:
        world = obj.matrix_world.copy()
        obj.parent = parent
        obj.matrix_world = world
    return parent


def new_since(before):
    """The top-level objects made since `before` (colliders stay where they are)."""
    new = {o for o in bpy.data.objects if o not in before and not o.name.startswith("col_")}
    return [o for o in new if o.parent not in new]


def usable(name, location, build, **props):
    """An interact_ empty with the meshes `build()` makes beneath it, joined into one
    object (library copies stay separate: their meshes are shared)."""
    before = set(bpy.data.objects)
    build()
    made = new_since(before)
    own = [o for o in made if o.type == "MESH" and o.data.users == 1 and not o.children]
    if len(own) > 1:
        joined = join(own, f"{name[len('interact_'):]}_mesh")
        made = [o for o in made if o not in own] + [joined]
    return adopt(empty(name, AREA, location, **props), made)


def ramp(name, coll, x0, x1, y0, y1, z0, z1, mat=None, thickness=0.2, surface="teak", axis="y"):
    """A sloping slab rising from z0 at y0 (or x0) to z1 at y1 (or x1): stairs as a walkable incline."""
    rise = z1 - z0
    cz = (z0 + z1) / 2
    if axis == "y":
        run = y1 - y0
        length, angle, cy = math.hypot(run, rise), math.atan2(rise, run), (y0 + y1) / 2
        obj = box(name, coll, x0, x1, cy - length / 2, cy + length / 2, cz - thickness, cz, mat, tilt=(angle, 0, 0))
    else:
        run = x1 - x0
        length, angle, cx = math.hypot(run, rise), math.atan2(rise, run), (x0 + x1) / 2
        obj = box(name, coll, cx - length / 2, cx + length / 2, y0, y1, cz - thickness, cz, mat, tilt=(0, -angle, 0))
    if name.startswith("col_"):
        obj["surface"] = surface
    return obj


def stairs(name, coll, x0, x1, y0, y1, z0, z1, m, steps, axis="y"):
    """Teak stairs: treads between two stringers, a handrail each side on turned
    posts, and one sloping collider so the controller climbs smoothly. The flight
    rises from z0 at y0 to z1 at y1 (axis "y"), or from x0 to x1 (axis "x")."""
    for k in range(steps):
        t0, t1 = k / steps, (k + 1) / steps
        z = z0 + (z1 - z0) * t1
        if axis == "y":
            a, b = y0 + (y1 - y0) * t0, y0 + (y1 - y0) * t1
            box(f"{name}_tread_{k}", coll, x0 + 0.06, x1 - 0.06, min(a, b) - 0.03, max(a, b), z - 0.045, z, m["teak"], edge=0.006)
        else:
            a, b = x0 + (x1 - x0) * t0, x0 + (x1 - x0) * t1
            box(f"{name}_tread_{k}", coll, min(a, b) - 0.03, max(a, b), y0 + 0.06, y1 - 0.06, z - 0.045, z, m["teak"], edge=0.006)
    sides = ((x0, x0 + 0.06), (x1 - 0.06, x1)) if axis == "y" else ((y0, y0 + 0.06), (y1 - 0.06, y1))
    for k, (s0, s1) in enumerate(sides):
        if axis == "y":
            ramp(f"{name}_stringer_{k}", coll, s0, s1, y0, y1, z0, z1, m["post"], thickness=0.28)
            ends = [((s0 + s1) / 2, y0, z0), ((s0 + s1) / 2, y1, z1)]
        else:
            ramp(f"{name}_stringer_{k}", coll, x0, x1, s0, s1, z0, z1, m["post"], thickness=0.28, axis="x")
            ends = [(x0, (s0 + s1) / 2, z0), (x1, (s0 + s1) / 2, z1)]
        for j, (px, py, pz) in enumerate(ends):
            pole(f"{name}_newel_{k}_{j}", coll, (px, py, pz), (px, py, pz + 0.95), 0.045, m["post"], sides=8, metres=2.0)
        pole(f"{name}_rail_{k}", coll, (ends[0][0], ends[0][1], ends[0][2] + 0.9), (ends[1][0], ends[1][1], ends[1][2] + 0.9),
             0.03, m["post"], sides=8, metres=2.0)
    ramp(f"col_{name}", coll, x0, x1, y0, y1, z0 + 0.02, z1 + 0.02, axis=axis)


def wall(name, coll, x0, x1, y0, y1, z0, z1, mat, gaps=(), surface="teak"):
    """A board wall along X or Y with openings [(a, b, top)] for doors or
    [(a, b, top, sill)] for windows, plus its collider pieces."""
    along_x = (x1 - x0) > (y1 - y0)
    a0, a1 = (x0, x1) if along_x else (y0, y1)
    pieces, at = [], a0
    for gap in sorted(gaps):
        g0, g1, top = gap[:3]
        sill = gap[3] if len(gap) > 3 else z0
        pieces.append((at, g0, z0, z1))
        pieces.append((g0, g1, top, z1))
        pieces.append((g0, g1, z0, sill))
        at = g1
    pieces.append((at, a1, z0, z1))
    for k, (p0, p1, zz0, zz1) in enumerate(pieces):
        if p1 - p0 < 1e-3 or zz1 - zz0 < 1e-3:
            continue
        bx = (p0, p1, y0, y1) if along_x else (x0, x1, p0, p1)
        board_panel(f"{name}_{k}", coll, *bx, zz0, zz1, mat)
        collider(f"{name}_{k}", coll, *bx, zz0, zz1, surface)


def battens(name, coll, fixed, a0, a1, z0, z1, mat, along_x, out, gaps=(), step=0.32):
    """Cover strips over the board joints on a wall's outer face (the house's relief)."""
    k = 0
    a = a0 + step / 2
    while a < a1:
        if not any(g[0] - 0.03 < a < g[1] + 0.03 for g in gaps):
            if along_x:
                box(f"{name}_{k}", coll, a - 0.02, a + 0.02, fixed, fixed + out * 0.025, z0, z1, mat)
            else:
                box(f"{name}_{k}", coll, fixed, fixed + out * 0.025, a - 0.02, a + 0.02, z0, z1, mat)
        else:
            for g in gaps:
                if g[0] - 0.03 < a < g[1] + 0.03:
                    sill = g[3] if len(g) > 3 else z0
                    for (zz0, zz1) in ((z0, sill), (g[2], z1)):
                        if zz1 - zz0 > 0.05:
                            if along_x:
                                box(f"{name}_{k}_{zz0:.1f}", coll, a - 0.02, a + 0.02, fixed, fixed + out * 0.025, zz0, zz1, mat)
                            else:
                                box(f"{name}_{k}_{zz0:.1f}", coll, fixed, fixed + out * 0.025, a - 0.02, a + 0.02, zz0, zz1, mat)
        k += 1
        a += step


def leaf(name, coll, hinge, angle, width, z0, z1, thick, mat):
    """A shutter or door leaf hinged at `hinge`, swung `angle` radians from the wall
    line (angle 0 points along +x; pass the closed direction plus the swing)."""
    hx, hy = hinge
    c, s = math.cos(angle), math.sin(angle)
    nx, ny = -s * thick, c * thick
    pts = [(hx, hy), (hx + c * width, hy + s * width), (hx + c * width + nx, hy + s * width + ny), (hx + nx, hy + ny)]
    verts = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return rotate_uvs(mesh_object(name, coll, verts, faces, mat))


def window(name, coll, along_x, fixed, a, b, sill, top, m, swing, inside):
    """A window frame with two board shutters (no glass in a village house),
    swung open by `swing` radians (0: closed)."""
    w = b - a
    if along_x:
        box(f"{name}_sill", coll, a - 0.05, b + 0.05, fixed - 0.06, fixed + 0.1, sill - 0.05, sill, m["post"])
        box(f"{name}_head", coll, a - 0.05, b + 0.05, fixed - 0.04, fixed + 0.08, top, top + 0.06, m["post"])
    else:
        box(f"{name}_sill", coll, fixed - 0.06, fixed + 0.1, a - 0.05, b + 0.05, sill - 0.05, sill, m["post"])
        box(f"{name}_head", coll, fixed - 0.04, fixed + 0.08, a - 0.05, b + 0.05, top, top + 0.06, m["post"])
    base = 0.0 if along_x else math.pi / 2
    out = -inside
    for k, (hinge_a, sign) in enumerate(((a, 1), (b, -1))):
        hinge = (hinge_a, fixed + out * 0.04) if along_x else (fixed + out * 0.04, hinge_a)
        angle = base + (0 if sign > 0 else math.pi) - sign * out * swing * (1 if along_x else -1)
        leaf(f"{name}_shutter_{k}", coll, hinge, angle, w / 2 - 0.01, sill + 0.02, top - 0.02, 0.03, m["boards"])


def roof_slab(name, coll, x0, x1, ya, za, yb, zb, thick, mat, tile):
    """A sloping slab from the line (ya, za) to (yb, zb) across x0..x1, with UVs laid
    along the slope so tiles keep their true size."""
    length = math.hypot(yb - ya, zb - za)
    ny, nz = -(zb - za) / length, (yb - ya) / length
    if nz < 0:
        ny, nz = -ny, -nz
    top = [(x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb)]
    bottom = [(x, y - ny * thick, z - nz * thick) for (x, y, z) in top]
    verts = top + bottom
    faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    up = (yb - ya) > 0
    if not up:
        faces = [tuple(reversed(f)) for f in faces]
    uv_of = {0: (x0 / tile, 0), 1: (x1 / tile, 0), 2: (x1 / tile, length / tile), 3: (x0 / tile, length / tile)}
    uvs = []
    for f in faces:
        for i in f:
            u, v = uv_of[i % 4]
            uvs.append((u, v))
    return mesh_object(name, coll, verts, faces, mat, uvs=uvs)


def materials():
    lib, img = library_material, image_material
    m = {
        "mud": lib("muddy_tracks", "M_wet_mud", tint=(0.62, 0.55, 0.48)),
        "mud_red": lib("red_dirt_mud_01", "M_wet_mud_red", tint=(0.55, 0.45, 0.4)),
        "water": plain("M_puddle", (0.018, 0.02, 0.022), rough=0.03),
        "flood": plain("M_flood_water", (0.02, 0.022, 0.022), rough=0.05),
        "forest_floor": lib("brown_mud_leaves_01", "M_wet_forest_floor", tint=(0.5, 0.45, 0.38)),
        "termite": lib("red_dirt_mud_01", "M_wet_termite_earth", tint=(0.7, 0.5, 0.42), tile=1.0),
        "bark": lib("bark_brown_02", "M_wet_bark", tint=(0.5, 0.45, 0.4), tile=1.2),
        "bark_dead": lib("bark_brown_02", "M_wet_bark_dead", tint=(0.5, 0.5, 0.5), tile=1.2),
        "post_tar": lib("dark_wood", "M_wet_tarred_post", tint=(0.35, 0.3, 0.28)),
        "leaf_cluster": img("M_tree_leaves", texture("T_ep1_leaf_cluster_BC"), rough=0.5, cutout=True),
        "bamboo_leaves": img("M_bamboo_leaves", texture("T_ep1_bamboo_leaves_BC"), rough=0.5, cutout=True),
        "grass": img("M_grass", texture("T_ep1_grass_BC"), rough=0.6, cutout=True),
        "flag_old": img("M_crocodile_flag_old", texture("T_ep1_flag_old_BC"), rough=0.9, cutout=True),
        "cobweb": img("M_cobweb", texture("T_ep1_cobweb_BC"), rough=1.0, cutout=True),
        "footprints": img("M_muddy_footprints", texture("T_ep1_footprints_BC"), rough=0.4, cutout=True),
        "yantra": img("M_yantra_cloth", texture("T_ep1_yantra_BC"), rough=0.9),
        "bamboo_dead": img("M_bamboo_dead", texture("T_ep1_bamboo_BC"), rough=0.7, tint=(0.6, 0.58, 0.55)),
        "cloth_red": lib("rough_linen", "M_wet_cloth_red", tint=(0.34, 0.05, 0.035)),
        "cloth_yellow": plain("M_cloth_yellow", (0.55, 0.38, 0.08), rough=0.8),
        "cotton_dirty": plain("M_cotton_dirty", (0.5, 0.48, 0.42), rough=0.9),
        "gold_dull": plain("M_gilt_dull", (0.45, 0.33, 0.15), rough=0.5, metal=0.8),
        "soot": plain("M_soot", (0.015, 0.012, 0.01), rough=1.0),
        "betel_leaf_dry": plain("M_dry_leaf", (0.22, 0.17, 0.08), rough=0.8),
        "incense_burnt": plain("M_incense_burnt", (0.12, 0.09, 0.07), rough=0.9),
        "insulator": plain("M_glass_insulator", (0.12, 0.25, 0.22), rough=0.1),
        "umbrella": plain("M_oiled_paper", (0.3, 0.13, 0.06), rough=0.55),
        "krama": plain("M_krama", (0.36, 0.08, 0.06), rough=0.85),
        "brick": lib("clay_plaster", "M_wet_old_brick", tint=(0.55, 0.38, 0.3), tile=1.5),
        "stone_wet": lib("mud_forest", "M_wet_shrine_stone", tint=(0.42, 0.4, 0.36), tile=0.6),
        "sandstone": plain("M_sandstone", (0.32, 0.27, 0.2), rough=0.9),
        "cloth_saffron": lib("rough_linen", "M_wet_cloth_saffron", tint=(0.55, 0.24, 0.05)),
        "rot_meat": plain("M_rotten_meat", (0.12, 0.07, 0.04), rough=0.86),
        "dead_marigold": plain("M_dead_marigold", (0.36, 0.17, 0.05), rough=0.85),
        "wax_red": plain("M_wax_red", (0.4, 0.05, 0.03), rough=0.4),
        "stains": img("M_betel_stains", texture("T_ep1_stains_BC"), rough=0.3, cutout=True),
        "wax_dirty": plain("M_wax_dirty", (0.55, 0.42, 0.22), rough=0.4),
        "rot": plain("M_rotten_food", (0.08, 0.07, 0.05), rough=0.6),
        "dead_flowers": plain("M_dead_flowers", (0.3, 0.22, 0.12), rough=0.9),
        "lotus_leaf": plain("M_lotus_leaf", (0.06, 0.13, 0.05), rough=0.35),
        "rag": lib("rough_linen", "M_wet_rag", tint=(0.42, 0.38, 0.32)),
        "straw": plain("M_straw", (0.42, 0.34, 0.18), rough=0.9),
        "tea_stain": plain("M_tea_stain", (0.09, 0.06, 0.035), rough=0.12),
        "milestone": img("M_milestone", texture("T_ep1_milestone_BC"), rough=0.8),
        "teak": lib("dark_wooden_planks", "M_house_teak"),
        "floor": lib("dark_wood", "M_floor_boards", tint=(0.8, 0.7, 0.62)),
        "boards": lib("weathered_brown_planks", "M_house_boards", tint=(0.5, 0.38, 0.3)),
        "post": lib("dark_wood", "M_house_posts"),
        "post_rough": lib("weathered_planks", "M_wet_rough_posts", tint=(0.55, 0.5, 0.45)),
        "worn": lib("wood_table_worn", "M_worn_wood"),
        "old_planks": lib("old_planks_02", "M_wet_old_planks", tint=(0.7, 0.62, 0.55)),
        "tiles": lib("clay_roof_tiles_02", "M_wet_roof_tiles", tint=(0.7, 0.55, 0.48)),
        "underside": lib("old_planks_02", "M_roof_battens", tint=(0.45, 0.36, 0.3)),
        "thatch": lib("thatch_roof_angled", "M_wet_thatch", tint=(0.62, 0.55, 0.48)),
        "bamboo_wall": lib("bamboo_wall", "M_bamboo_wall", tint=(0.75, 0.68, 0.58)),
        "bamboo_wall_2s": lib("bamboo_wall", "M_wet_bamboo_hood", tint=(0.7, 0.62, 0.52)),
        "bamboo_slats": lib("bamboo_wall", "M_bamboo_slats", tint=(0.8, 0.72, 0.6), tile=1.2),
        "cotton": lib("rough_linen", "M_tent_cotton", colour=(0.8, 0.78, 0.72)),
        "bamboo": img("M_bamboo", texture("T_ep1_bamboo_BC"), rough=0.5),
        "palm_trunk": img("M_palm_trunk", texture("T_ep1_palm_trunk_BC"), rough=0.9),
        "banana_leaf": img("M_banana_leaf", texture("T_ep1_leaf_banana_BC"), rough=0.5, cutout=True),
        "banana_stem": img("M_banana_stem", texture("T_ep1_banana_stem_BC"), rough=0.6),
        "palm_fan": img("M_palm_fan", texture("T_ep1_leaf_palm_BC"), rough=0.55, cutout=True),
        "palm_fan_dead": img("M_palm_fan_dead", texture("T_ep1_leaf_palm_BC"), rough=0.8, cutout=True, tint=(0.95, 0.62, 0.36)),
        "coconut_leaf": img("M_coconut_leaf", texture("T_ep1_leaf_coconut_BC"), rough=0.55, cutout=True),
        "flag": img("M_crocodile_flag", texture("T_ep1_flag_crocodile_BC"), rough=0.85, cutout=True),
        "valance": img("M_valance", texture("T_ep1_valance_BC"), rough=0.85, cutout=True),
        "mat": img("M_reed_mat", texture("T_ep1_mat_BC"), rough=0.8, tile=1.0),
        "coffin_panel": img("M_coffin_gilt", texture("T_ep1_coffin_panel_BC"), rough=0.4),
        "photo": img("M_photo_sok", texture("T_ep1_photo_sok_BC"), rough=0.55),
        "family_prints": img("M_family_prints", texture("T_ep1_family_prints_BC"), rough=0.6),
        "house_papers": img("M_house_papers", texture("T_ep1_house_papers_BC"), rough=0.75),
        "sok_notes": img("M_sok_notes", texture("T_ep1_sok_notes_BC"), rough=0.9, cutout=True),
        "kanha_drawing": img("M_kanha_drawing", texture("T_ep1_kanha_drawing_BC"), rough=0.95),
        "cushion": lib("fabric_pattern_07", "M_cushion"),
        "gold": plain("M_gilt", (0.72, 0.52, 0.22), rough=0.32, metal=1.0),
        "lacquer": plain("M_red_lacquer", (0.26, 0.045, 0.03), rough=0.35),
        "frame": plain("M_frame_wood", (0.07, 0.04, 0.025), rough=0.4),
        "brass": plain("M_brass", (0.62, 0.45, 0.2), rough=0.35, metal=1.0),
        "glaze": plain("M_jar_glaze", (0.08, 0.05, 0.03), rough=0.22),
        "clay": plain("M_clay", (0.36, 0.2, 0.12), rough=0.85),
        "stone": plain("M_stone", (0.22, 0.21, 0.19), rough=0.9),
        "rope": plain("M_rope", (0.35, 0.28, 0.18), rough=0.9),
        "rattan": plain("M_rattan", (0.42, 0.32, 0.18), rough=0.7),
        "thread": plain("M_white_thread", (0.9, 0.9, 0.86), rough=0.8),
        "wax": plain("M_candle_wax", (0.82, 0.62, 0.28), rough=0.45),
        "flame": glow_material("M_flame", texture("T_ep1_flame_BC"), strength=3.0),
        "incense": plain("M_incense", (0.2, 0.1, 0.06), rough=0.85),
        "ember": plain("M_ember", (1.0, 0.3, 0.1), emission=(1.0, 0.25, 0.05), strength=4.0),
        "sand": plain("M_incense_sand", (0.5, 0.45, 0.38), rough=1.0),
        "ash": plain("M_ash", (0.32, 0.3, 0.28), rough=1.0),
        "embers": plain("M_hearth_embers", (0.3, 0.06, 0.02), emission=(1.0, 0.25, 0.05), strength=3.0),
        "betel_leaf": plain("M_betel_leaf", (0.1, 0.22, 0.06), rough=0.4),
        "stem_green": plain("M_stem_green", (0.15, 0.25, 0.08), rough=0.6),
        "jasmine": plain("M_jasmine", (0.88, 0.88, 0.8), rough=0.6),
        "lotus": plain("M_lotus_bud", (0.75, 0.42, 0.45), rough=0.6),
        "rice": plain("M_rice", (0.86, 0.84, 0.78), rough=0.9),
        "coconut": plain("M_coconut", (0.22, 0.27, 0.1), rough=0.55),
        "areca": plain("M_areca_nut", (0.4, 0.24, 0.1), rough=0.6),
        "lime": plain("M_lime_paste", (0.85, 0.78, 0.7), rough=0.9),
        "drum_wood": plain("M_drum_wood", (0.22, 0.08, 0.04), rough=0.4),
        "hide": plain("M_drum_hide", (0.6, 0.5, 0.36), rough=0.7),
        "sandal": plain("M_sandal", (0.12, 0.08, 0.05), rough=0.7),
        "bottle": plain("M_bottle_glass", (0.06, 0.1, 0.06), rough=0.12),
        "kerosene_tin": plain("M_kerosene_tin", (0.35, 0.33, 0.28), rough=0.5, metal=0.7),
        "iron": plain("M_iron", (0.08, 0.07, 0.065), rough=0.6, metal=0.8),
        "paper": plain("M_old_paper", (0.75, 0.68, 0.52), rough=0.95),
        # The inside of a well: lightless.
        "void": plain("M_void", (0.003, 0.003, 0.003), rough=1.0),
        "window_glow": plain("M_lamp_window", (0.2, 0.1, 0.04), emission=(1.0, 0.55, 0.22), strength=1.2),
        "net": plain("M_mosquito_net", (0.78, 0.78, 0.74), rough=0.9),
    }
    for key in ("cotton", "bamboo_wall_2s", "net", "krama", "cotton_dirty", "hide", "cloth_red", "cloth_yellow", "cloth_saffron"):
        m[key].use_backface_culling = False
    return m


# --------------------------------------------------------------- the land


def terrain(m):
    """Uneven ground: wet tracked mud in the courtyard and along the path, leaf litter
    in the forest. South of the grove the road runs on a low bank between drowned
    rice fields; west of the path the bank has sunk under the flood."""
    x0, x1, y0, y1, step = -40, 40, -92, 40, 1.0
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    phase = rng.uniform(0, 10, 6)

    def height(x, y):
        h = (0.06 * math.sin(x * 0.37 + phase[0]) * math.cos(y * 0.29 + phase[1])
             + 0.04 * math.sin(x * 1.1 + y * 0.7 + phase[2]) + 0.02 * math.sin(x * 2.3 - y * 1.9 + phase[3]))
        d = path_distance(x, y)
        near = in_yard(x, y, 1.0) or d < 2.0
        h *= 0.35 if near else 1.8
        if d < 1.2 and not in_yard(x, y):
            h -= 0.03 * (1 - d / 1.2)  # the path is worn down
        road = abs(y - ROAD_Y)
        if y < -60.5:
            if road < 2.6:
                # The bank: crowned, with two cart ruts, sinking into the flood to the west.
                h = 0.14 - 0.02 * road - 0.07 * math.exp(-((road - 0.8) / 0.25) ** 2)
                h -= 0.42 * max(0.0, min(1.0, (-3.5 - x) / 3.0)) * max(0.0, min(1.0, (x + 17.0) / 3.0))
            elif y > ROAD_Y:
                h = min(h, 0.14 - 0.06 * (road - 2.6))
            else:
                # Rice fields under water, cut by the low earth dikes between them,
                # up to the far bank where the forest begins again.
                h = -0.32 + 0.03 * math.sin(x * 0.7 + y * 0.4)
                if y < -86.5:
                    return 0.1 + 0.05 * math.sin(x * 0.9)
                if any(abs(y - yd) < 0.45 for yd in (-74.0, -84.0)) or any(abs(x - xd) < 0.45 for xd in (-34, -20, -6, 8, 22, 36)):
                    h = 0.03
        return h

    verts = [(x0 + i * step, y0 + j * step, height(x0 + i * step, y0 + j * step)) for j in range(ny + 1) for i in range(nx + 1)]
    faces, mats = [], []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
            cx, cy = x0 + (i + 0.5) * step, y0 + (j + 0.5) * step
            mud = in_yard(cx, cy, 0.5) or path_distance(cx, cy) < 1.7 or cy < -60.5
            mats.append(0 if mud else 1)
    ground = mesh_object("ground", AREA, verts, faces, m["mud"], smooth=True)
    ground.data.materials.append(m["forest_floor"])
    for poly, k in zip(ground.data.polygons, mats):
        poly.material_index = k
    collider("ground", AREA, -40, 40, -92, 40, -1, 0, surface="mud")
    # Puddles where the ground sags: in the courtyard, on the path.
    spots = [(-6.5, -1.2, 1.4), (5.8, 0.2, 1.0), (-8.5, 8.5, 1.2), (7.5, 8.2, 0.9), (0.8, 8.4, 1.1), (-2.0, -12.0, 0.8),
             (0.6, -25.0, 1.0), (-1.8, -33.0, 0.7), (2.0, -46.0, 0.9), (9.5, 3.5, 0.8), (-10.5, 13.0, 1.0), (1.2, -56.0, 1.2)]
    for k, (px, py, r) in enumerate(spots):
        n = 18
        pts = [(px + math.cos(2 * math.pi * i / n) * r * (0.7 + 0.35 * rng.random()),
                py + math.sin(2 * math.pi * i / n) * r * (0.55 + 0.3 * rng.random()), 0.012) for i in range(n)]
        mesh_object(f"puddle_{k}", AREA, [(px, py, 0.012)] + pts, [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)], m["water"])
    mesh_object("flood_water", AREA, [(-40, -92, -0.06), (40, -92, -0.06), (40, -60.8, -0.06), (-40, -60.8, -0.06)],
                [(0, 1, 2, 3)], m["flood"])


def clear_of(x, y):
    return all(math.hypot(x - p[0], y - p[1]) > r for p, r in CLEAR) and \
        all(math.hypot(x - wx, y - wy) > 2.5 for wx, wy, _ in WELLS) and \
        all(math.hypot(x - hx, y - hy) > 2.0 for hx, hy in HERO_TREES) and \
        all(math.hypot(x - rx, y - ry) > 1.5 for rx, ry in RAG_TREES) and \
        ((x - POND[0]) / (POND[2] + 1.5)) ** 2 + ((y - POND[1]) / (POND[3] + 1.5)) ** 2 > 1


def land(x, y, margin=0.0):
    """Ground the forest may grow on: not the yard, the path, the road or the flooded fields."""
    if not (-39.5 < x < 39.5 and -91.5 < y < 39.5):
        return False
    if -86.5 < y < -60.5 or in_yard(x, y, 1.0 + margin) or path_distance(x, y) < 2.0 + margin:
        return False
    return clear_of(x, y)


def scatter(n, test, spacing=0.0, tries=40000):
    """Up to n random spots where test(x, y) holds, at least `spacing` apart."""
    spots = []
    for _ in range(tries):
        if len(spots) >= n:
            break
        x, y = rng.uniform(-39.5, 39.5), rng.uniform(-91.5, 39.5)
        if test(x, y) and all((x - a) ** 2 + (y - b) ** 2 >= spacing ** 2 for a, b in spots):
            spots.append((x, y))
    return spots


def vegetation(m):
    """The forest round the compound: banana plants everywhere under big broadleaf
    trees, sugar and coconut palms standing over them, bamboo thickets, a banyan by
    the path, dead trees, fallen trunks, termite mounds, ferns and grass."""
    k = 0
    tries = 0
    while k < 430 and tries < 20000:
        tries += 1
        x, y = rng.uniform(-39, 39), rng.uniform(-60, 39)
        if not land(x, y, 0.3):
            continue
        banana(AREA, m, x, y, rng.uniform(1.8, 2.8), k, rng)
        k += 1
    # A few clumps inside the fence, in the courtyard's back corners.
    for x, y in ((-11.6, 20.6), (-12.2, 18.8), (11.8, 20.8), (-11.8, -1.6), (12.0, 0.2)):
        banana(AREA, m, x, y, rng.uniform(1.8, 2.5), k, rng)
        k += 1
    for j, (x, y, h) in enumerate([(-15, 4, 13), (15.5, 10, 14), (-9, -18, 12), (6, -34, 15), (-17, 22, 13),
                                   (13, 25, 12), (-6, -48, 14), (9, -55, 13), (-25, -12, 15)]):
        sugar_palm(AREA, m, x, y, h, j, rng)
    for j, (x, y, h) in enumerate([(-11, -9, 9), (8, -14, 10), (-16, 15, 9), (16.5, 18, 10), (-5, -38, 9), (4.5, -26, 8)]):
        coconut_palm(AREA, m, x, y, h, j, rng)
    for j, (x, y) in enumerate(TREES):
        tropical_tree(AREA, m, x, y, rng.uniform(11, 16), j, rng)
    for j, (x, y) in enumerate(DEAD):
        dead_tree(AREA, m, x, y, rng.uniform(6, 10), j, rng)
    for j, (x, y) in enumerate(BAMBOO):
        bamboo_clump(AREA, m, x, y, j, rng)
    banyan(AREA, m, *BANYAN, rng)
    neak_ta_shrine(AREA, m, -3.9, -34.9, math.pi / 2, rng)
    for j, (x, y, h) in enumerate([(-6, -20, 1.8), (5, -29, 1.3), (-4.5, -45, 2.2), (7, -55, 1.6), (-11, -6, 1.2), (15.5, -6, 1.9),
                                   (-17, -20, 2.4), (18, -44, 1.5)]):
        termite_mound(AREA, m, x, y, h, j, rng)
    # Fallen trunks, stumps, roots and dead wood on the forest floor.
    for model, (x, y, rot) in [("dead_tree_trunk", (-5.5, -11, 20)), ("dead_tree_trunk", (6.5, -33, 70)), ("dead_tree_trunk", (-3.8, -55, -30)),
                               ("dead_tree_trunk_02", (7.5, -16, 110)), ("dead_tree_trunk_02", (-10, -40, 45)), ("dead_tree_trunk_02", (16, 14, 15)),
                               ("tree_stump_01", (3.8, -21, 0)), ("tree_stump_01", (-4.2, -41, 90)), ("tree_stump_01", (9.5, -4.5, 200)),
                               ("root_cluster_01", (6.5, -46, 40)), ("root_cluster_01", (-12, -16, 160))]:
        place(AREA, model, (x, y, 0.0), rot_deg=rot, scale=rng.uniform(1.0, 1.3), collide=model != "dry_branches_medium_01", surface="leaves")
    placed = 0
    while placed < 30:
        x, y = rng.uniform(-10, 10), rng.uniform(-58, -5)
        if 1.4 < path_distance(x, y) < 4.0 and clear_of(x, y):
            place(AREA, "dry_branches_medium_01", (x, y, 0.0), rot_deg=rng.uniform(0, 360), scale=rng.uniform(1.0, 1.6))
            placed += 1
    placed = 0
    while placed < 50:
        x, y = rng.uniform(-14, 14), rng.uniform(-60, -4)
        if 2.0 < path_distance(x, y) < 4.5 and clear_of(x, y):
            place(AREA, "fern_02", (x, y, 0.0), rot_deg=rng.uniform(0, 360), scale=rng.uniform(0.7, 1.1))
            placed += 1
    placed = 0
    while placed < 40:
        x, y = rng.uniform(-24, 24), rng.uniform(-60, 32)
        # Far enough that its crown doesn't hang over the path.
        if not in_yard(x, y, 1.5) and 3.5 < path_distance(x, y) < 12 and clear_of(x, y):
            place(AREA, "pachira_aquatica_01", (x, y, 0.0), rot_deg=rng.uniform(0, 360), scale=rng.uniform(1.6, 2.4))
            placed += 1
    spots = []
    while len(spots) < 260:
        x, y = rng.uniform(-16, 16), rng.uniform(-60, 30)
        d = path_distance(x, y)
        if (1.3 < d < 5.0 and not in_yard(x, y, 0.3) and clear_of(x, y)) or (in_yard(x, y, 1.2) and not in_yard(x, y, -0.2)):
            spots.append((x, y, 0.0))
    grass_patch("grove_grass", AREA, m, spots, rng)
    # What the dead left along the way: the rotted flags of earlier funerals, thread
    # strung across the path, offerings at the crossing.
    for j, (x, y) in enumerate([(3.4, -17.5), (-4.6, -29.0), (4.2, -49.0), (-3.2, -58.5)]):
        old_flag(AREA, m, x, y, j, rng)
    path_threads(AREA, m, (-4.6, -22.0), (0.4, -22.0), 2.2, 0, rng)
    path_threads(AREA, m, (-1.2, -44.0), (3.8, -44.0), 2.25, 1, rng)
    # Keep the whole offering cluster beyond the 1.7 m mud-path edge.
    ground_offering(AREA, m, -4.8, -25.5, 0, rng)
    ground_offering(AREA, m, -4.7, -36.0, 1, rng)
    forest_fill(m)


def forest_fill(m):
    """The forest beyond the path, to the edge of the world: more big trees and
    palms, bamboo, shrubs and ferns under them, grass over every open patch, moss
    and rocks, the straw stacks and pond of the neighbours."""
    taken = TREES + DEAD + BAMBOO + [BANYAN]
    far = lambda x, y: land(x, y, 1.0) and all(math.hypot(x - a, y - b) > 6 for a, b in taken)  # noqa: E731
    for j, (x, y) in enumerate(scatter(26, far, spacing=7)):
        tropical_tree(AREA, m, x, y, rng.uniform(11, 17), 300 + j, rng, crown=rng.uniform(0.9, 1.3))
        taken.append((x, y))
    for j, (x, y) in enumerate(HERO_TREES):
        place(AREA, "island_tree_02", (x, y, 0.0), rot_deg=rng.uniform(0, 360), scale=rng.uniform(1.6, 2.0), collide=False)
        collider(f"hero_tree_{j}", AREA, x - 0.5, x + 0.5, y - 0.5, y + 0.5, 0, 3)
    for j, (x, y) in enumerate(scatter(12, far, spacing=5)):
        sugar_palm(AREA, m, x, y, rng.uniform(11, 16), 300 + j, rng)
        taken.append((x, y))
    for j, (x, y) in enumerate(scatter(12, far, spacing=5)):
        coconut_palm(AREA, m, x, y, rng.uniform(8, 11), 300 + j, rng)
        taken.append((x, y))
    for j, (x, y) in enumerate(scatter(10, far, spacing=8)):
        bamboo_clump(AREA, m, x, y, 300 + j, rng)
        taken.append((x, y))
    for j, (x, y) in enumerate(scatter(7, far, spacing=10)):
        dead_tree(AREA, m, x, y, rng.uniform(6, 10), 300 + j, rng)
    # One variant each (khmer.place), so the multi-variant models come in larger numbers.
    for model, count, size in (("shrub_02", 90, (0.8, 1.2)), ("shrub_03", 100, (1.0, 1.6)), ("shrub_04", 40, (1.2, 2.0)),
                               ("pachira_aquatica_01", 70, (1.6, 2.4)), ("fern_02", 170, (0.8, 1.3)), ("tree_stump_02", 10, (0.8, 1.1)),
                               ("moss_01", 12, (1.0, 1.5))):
        margin = 1.5 if model.startswith(("pachira", "shrub_04")) else 0.2
        for x, y in scatter(count, lambda x, y: land(x, y, margin), spacing=2.0):
            place(AREA, model, (x, y, 0.0), rot_deg=rng.uniform(0, 360), scale=rng.uniform(*size))
    for x, y in scatter(30, lambda x, y: land(x, y) and 2.3 < path_distance(x, y) < 5.0, spacing=2.5):
        place(AREA, "grass_medium_02", (x, y, 0.0), rot_deg=rng.uniform(0, 360), scale=rng.uniform(0.8, 1.1))
    for x, y in scatter(4, lambda x, y: land(x, y, 2.0), spacing=15):
        place(AREA, "rock_moss_set_01", (x, y, -0.15), rot_deg=rng.uniform(0, 360), scale=rng.uniform(0.6, 0.9), collide=True, surface="stone")
    # Grass over all the open ground, thinner in the yard along the fences and under the house.
    spots = [(x, y, 0.0) for x, y in scatter(6500, lambda x, y: land(x, y, -0.6), tries=60000)]
    for i in range(0, len(spots), 900):
        grass_patch(f"forest_grass_{i // 900}", AREA, m, spots[i:i + 900], rng, size=(0.45, 1.0))
    forest_enrichment(m)
    yard_edge = [(x, y, 0.0) for x, y in scatter(400, lambda x, y: in_yard(x, y) and not in_yard(x, y, -1.2), tries=20000)]
    grass_patch("yard_edge_grass", AREA, m, yard_edge, rng, size=(0.3, 0.6))
    for j, (x, y) in enumerate(RAG_TREES):
        rag_tree(AREA, m, x, y, j, rng)
    for j, (x, y, cover) in enumerate(WELLS):
        old_well(AREA, m, x, y, rng, j, cover=cover)
    lotus_pond(AREA, m, *POND, rng)


def forest_enrichment(m):
    """Layered fern beds and secondary trees at the path and compound edge."""
    # Cluster growth instead of distributing every species uniformly. Keep the
    # entire worn path, sacred-tree clearing, pond and gameplay props accessible.
    detail_rng = np.random.default_rng(6241910)
    occupied = TREES + DEAD + BAMBOO + [BANYAN] + HERO_TREES
    occupied += [(o.location.x, o.location.y) for o in AREA.objects if o.name.startswith('col_tree_')]
    for j, (x, y) in enumerate(scatter(16, lambda x, y: land(x, y, 1.5)
                                     and all(math.hypot(x-a, y-b) > 4.5 for a, b in occupied), spacing=5)):
        tropical_tree(AREA, m, x, y, detail_rng.uniform(10, 16), 600 + j, detail_rng, crown=1.05)
        occupied.append((x, y))
    seeds = scatter(180, lambda x, y: land(x, y, .35) and path_distance(x, y) < 13, spacing=1.25)
    plants, grass = [], []
    for x, y in seeds:
        for _ in range(4):
            bx, by = x + detail_rng.normal(0, .8), y + detail_rng.normal(0, .8)
            if land(bx, by, .1):
                plants.append((bx, by))
        for _ in range(12):
            bx, by = x + detail_rng.normal(0, 1.1), y + detail_rng.normal(0, 1.1)
            if land(bx, by, -.1):
                grass.append((bx, by, 0.))
    understory(AREA, plants, detail_rng)
    grass_patch('forest_edge_sedge', AREA, m, grass, detail_rng, size=(.5, 1.12))
    house_forest(m)


def house_forest(m):
    """A three-sided forest belt outside the compound, visible from the house."""
    detail_rng = np.random.default_rng(6242011)
    before = set(AREA.objects)
    occupied = [(o.location.x, o.location.y) for o in AREA.objects
                if o.name.startswith(('col_tree_', 'col_palm_', 'col_coco_',
                                      'col_dead_', 'col_bamboo_', 'col_hero_tree_'))]
    # Three trees on each flank and four across the rear: the house sits in
    # forest rather than facing a grove with an empty backdrop. Keep roots
    # outside the fence and crowns above all ground-level access routes.
    specs = [(-26, -15.5, 0, 30)] * 3 + [(15.5, 26, 0, 30)] * 3 + [(-22, 22, 25.5, 36)] * 4
    for j, (x0, x1, y0, y1) in enumerate(specs):
        for _ in range(5000):
            x, y = detail_rng.uniform(x0, x1), detail_rng.uniform(y0, y1)
            if land(x, y, 1.2) and all(math.hypot(x-a, y-b) > 4.5 for a, b in occupied):
                break
        else:
            raise RuntimeError(f'No clear house-side tree position for {j}')
        height = detail_rng.uniform(12, 17)
        obj = tropical_tree(AREA, m, x, y, height, 700+j, detail_rng, crown=1.1)
        obj['forest_height'] = height
        occupied.append((x, y))
    def belt(x, y):
        return ((15 < abs(x) < 27 and 0 < y < 31) or
                (-24 < x < 24 and 24 < y < 36)) and land(x, y, .1)
    seeds = []
    for _ in range(10000):
        x, y = detail_rng.uniform(-27, 27), detail_rng.uniform(0, 36)
        if belt(x, y) and all(math.hypot(x-a, y-b) > 1.3 for a, b in seeds):
            seeds.append((x, y))
            if len(seeds) == 80:
                break
    plants, grass = [], []
    for x, y in seeds:
        for _ in range(3):
            bx, by = x + detail_rng.normal(0, .65), y + detail_rng.normal(0, .65)
            if belt(bx, by):
                plants.append((bx, by))
        for _ in range(20):
            bx, by = x + detail_rng.normal(0, 1.0), y + detail_rng.normal(0, 1.0)
            if belt(bx, by):
                grass.append((bx, by, 0.))
    # Low growth along the inside of the back fence, clear of the shed,
    # rear house access and the cart in the northeast corner.
    for x in (-11.5, -9, -6.5, -3.5, 3.5, 6.5):
        plants.append((x, 21.15))
        for _ in range(18):
            grass.append((x + detail_rng.uniform(-.6, .6), detail_rng.uniform(20.6, 21.7), 0.))
    understory(AREA, plants, detail_rng)
    grass_patch('house_sedge', AREA, m, grass, detail_rng, size=(.3, .8))
    for obj in set(AREA.objects) - before:
        if not obj.name.startswith(('tree_', 'col_tree_')):
            obj.name = 'house_forest_' + obj.name


def road(m):
    """The road on its bank across the flooded rice fields (A1-01): the cart where the
    driver turned back, the telegraph line, dead trees and stubble standing in the water."""
    ox_cart(AREA, m, "carriage", 1.8, ROAD_Y + 0.3, math.radians(10), hood=True)
    telegraph_line(AREA, m, [(-38, -61.0, 0.04), (-16, -61.0, -0.12), (6, -61.0, 0.03), (28, -61.0, 0.24)], rng, broken=(1,))
    for j, (x, y) in enumerate([(-24, -72), (-9, -78), (14, -70), (26, -82), (3, -86), (-30, -86), (-13, -68.5)]):
        dead_tree(AREA, m, x, y, rng.uniform(5, 9), 100 + j, rng)
    spots = []
    for row in range(14):
        yy = -67.5 - row * 1.6
        for i in range(36):
            x = -38 + i * 2.1 + rng.uniform(-0.4, 0.4)
            if rng.random() < 0.55:
                spots.append((x, yy + rng.uniform(-0.3, 0.3), -0.25))
    grass_patch("paddy_stubble", AREA, m, spots, rng, size=(0.45, 0.7))
    roadside = [(x, y, 0.05) for x, y in ((rng.uniform(-38, 38), ROAD_Y + s * rng.uniform(2.0, 2.6)) for s in [1, -1] * 70)]
    grass_patch("road_grass", AREA, m, roadside, rng, size=(0.4, 0.8))
    # A broken cart wheel half sunk where the bank goes under, lying tilted in the water.
    c = (-10.2, ROAD_Y - 0.4, -0.1)
    u, v = (1.0, 0.0, 0.0), (0.0, 0.95, 0.31)

    def on_wheel(a, r):
        return tuple(c[i] + (u[i] * math.cos(a) + v[i] * math.sin(a)) * r for i in range(3))

    parts = [tube("sunk_wheel_rim", AREA, [on_wheel(2 * math.pi * k / 20, 0.6) for k in range(21)], 0.04, m["worn"], sides=6)]
    for k in range(0, 12, 2):
        parts.append(tube(f"sunk_wheel_spoke_{k}", AREA, [c, on_wheel(2 * math.pi * k / 12, 0.57)], 0.018, m["worn"], sides=4))
    join(parts, "sunk_wheel")
    # The village's straw guardians at the mouth of the path, and one out in the flood.
    ting_mong(AREA, m, -1.4, -61.0, -0.15, 0, rng)
    ting_mong(AREA, m, 4.4, -60.8, 0.25, 1, rng, arms_up=True)
    ting_mong(AREA, m, -7.5, -71.5, math.pi, 2, rng, arms_up=True)
    # Two more along the path through the grove, watching whoever comes up it.
    ting_mong(AREA, m, -4.4, -26.0, 0.2, 3, rng)
    ting_mong(AREA, m, 3.8, -8.5, -0.3, 4, rng, arms_up=True)
    milestone(AREA, m, 5.6, ROAD_Y + 2.1, 0.0)
    field_hut(AREA, m, -18.0, -75.5, rng)
    sampan(AREA, m, 9.5, -69.0, 0.5, 0.25, 0.35)
    # The far bank: a forest edge across the fields, where the fog swallows the world.
    for j in range(12):
        x = -38 + j * 7 + rng.uniform(-2, 2)
        yy = -90 + rng.uniform(-1.5, 1.5)
        if j % 3 == 1:
            bamboo_clump(AREA, m, x, yy, 200 + j, rng)
        elif j % 3 == 2:
            dead_tree(AREA, m, x, yy, rng.uniform(7, 11), 200 + j, rng)
        else:
            tropical_tree(AREA, m, x, yy, rng.uniform(10, 15), 200 + j, rng)
    for j in range(16):
        banana(AREA, m, -38 + j * 5 + rng.uniform(-1.5, 1.5), -88 + rng.uniform(-1.5, 1.5), rng.uniform(2.0, 2.8), 400 + j, rng)


# --------------------------------------------------------------- the house


def house(m):
    """The family's teak house (ផ្ទះ), the kind a civil servant's family built in the
    1920s: round posts on stone footings, board walls with cover strips, shuttered
    windows, a veranda with X-braced railings and a steep clay-tiled roof whose gables
    are boarded in a sunburst under carved bargeboards."""
    h = HOUSE
    for x in (-6.0, -3.0, 0.0, 3.0, 6.0):
        for y in (10.0, 14.0, 18.0):
            # Posts rise through the walls; the one under the middle of the hall stops at the floor.
            top = FLOOR if (x, y) == (0.0, 14.0) else ZW
            box(f"footing_{x:.0f}_{y:.0f}", AREA, x - 0.24, x + 0.24, y - 0.24, y + 0.24, -0.05, 0.1, m["stone"], edge=0.02)
            pole(f"pillar_{x:.0f}_{y:.0f}", AREA, (x, y, 0.1), (x, y, top), 0.155, m["post"], sides=12, metres=2.0, radius_end=0.135)
            collider(f"pillar_{x:.0f}_{y:.0f}", AREA, x - 0.16, x + 0.16, y - 0.16, y + 0.16, 0, top)
    # Floor: girders on the posts, joists across them, boards with real gaps between.
    for y in (10.0, 14.0, 18.0):
        box(f"girder_{y:.0f}", AREA, h["x0"] - 0.2, h["x1"] + 0.2, y - 0.11, y + 0.11, FLOOR - 0.42, FLOOR - 0.18, m["post"])
    for k, x in enumerate(np.arange(h["x0"] + 0.1, h["x1"], 0.8)):
        box(f"joist_{k}", AREA, x - 0.04, x + 0.04, h["y0"], h["y1"], FLOOR - 0.18, FLOOR - 0.05, m["post"])
    for k, y in enumerate(np.arange(h["y0"], h["y1"] - 0.1, 0.21)):
        box(f"floor_board_{k}", AREA, h["x0"] - 0.05, h["x1"] + 0.05, y + 0.005, y + 0.205, FLOOR - 0.05, FLOOR, m["floor"])
    collider("upper_floor", AREA, h["x0"], h["x1"], h["y0"], h["y1"], FLOOR - 0.12, FLOOR)
    zw0, zw1 = FLOOR, ZW
    door = FLOOR + 2.05
    sill, head = FLOOR + 0.8, FLOOR + 1.75
    T = 0.06
    front_gaps = [(-0.5, 0.5, door), (-4.6, -3.8, head, sill), (3.9, 4.7, head, sill)]
    back_gaps = [(1.9, 2.8, door), (-4.8, -4.0, head, sill), (-1.0, -0.2, head, sill)]
    west_gaps = [(12.6, 13.4, head, sill), (16.0, 16.8, head, sill)]
    east_gaps = [(14.0, 14.8, head, sill), (16.7, 17.5, head, sill)]
    wall("wall_front", AREA, h["x0"], h["x1"], 11.5 - T, 11.5, zw0, zw1, m["boards"], gaps=front_gaps)
    wall("wall_back", AREA, h["x0"], h["x1"], h["y1"] - T, h["y1"], zw0, zw1, m["boards"], gaps=back_gaps)
    wall("wall_west", AREA, h["x0"], h["x0"] + T, 11.5, h["y1"], zw0, zw1, m["boards"], gaps=west_gaps)
    wall("wall_east", AREA, h["x1"] - T, h["x1"], 11.5, h["y1"], zw0, zw1, m["boards"], gaps=east_gaps)
    battens("batten_front", AREA, 11.5 - T, h["x0"], h["x1"], zw0, zw1, m["post"], True, -1, front_gaps)
    battens("batten_back", AREA, h["y1"], h["x0"], h["x1"], zw0, zw1, m["post"], True, 1, back_gaps)
    battens("batten_west", AREA, h["x0"], 11.5, h["y1"], zw0, zw1, m["post"], False, -1, west_gaps)
    battens("batten_east", AREA, h["x1"], 11.5, h["y1"], zw0, zw1, m["post"], False, 1, east_gaps)
    # Shutters: open on the kitchen and the hall, shut on Sok's locked room.
    window("win_kitchen_s", AREA, True, 11.5 - T, -4.6, -3.8, sill, head, m, 1.2, 1)
    window("win_sok_s", AREA, True, 11.5 - T, 3.9, 4.7, sill, head, m, 0.0, 1)
    window("win_yaymey_n", AREA, True, h["y1"], -4.8, -4.0, sill, head, m, 0.3, -1)
    window("win_hall_n", AREA, True, h["y1"], -1.0, -0.2, sill, head, m, 1.0, -1)
    window("win_kitchen_w", AREA, False, h["x0"], 12.6, 13.4, sill, head, m, 1.3, 1)
    window("win_yaymey_w", AREA, False, h["x0"], 16.0, 16.8, sill, head, m, 0.0, 1)
    window("win_sok_e", AREA, False, h["x1"], 14.0, 14.8, sill, head, m, 0.0, -1)
    window("win_sok_e2", AREA, False, h["x1"], 16.7, 17.5, sill, head, m, 0.15, -1)
    # Partitions: kitchen (south-west), Yay Mey's room (north-west), Sok's room (east).
    wall("wall_kitchen_hall", AREA, -3.0, -3.0 + T, 11.5, 14.5, zw0, zw1, m["boards"], gaps=[(12.5, 13.4, door)])
    wall("wall_yaymey_hall", AREA, -3.0, -3.0 + T, 14.5, h["y1"], zw0, zw1, m["boards"], gaps=[(15.6, 16.5, door)])
    wall("wall_kitchen_yaymey", AREA, h["x0"], -3.0, 14.5 - T / 2, 14.5 + T / 2, zw0, zw1, m["boards"])
    wall("wall_sok_hall", AREA, 3.0 - T, 3.0, 11.5, h["y1"], zw0, zw1, m["boards"], gaps=[(13.0, 13.9, door)])
    # Door frames, the open front and back doors, and the two shut inner doors.
    for name, along_x, fixed, a, b in (("front", True, 11.5 - T / 2, -0.5, 0.5), ("back", True, h["y1"] - T / 2, 1.9, 2.8),
                                       ("kitchen", False, -3.0 + T / 2, 12.5, 13.4), ("yaymey", False, -3.0 + T / 2, 15.6, 16.5),
                                       ("sok", False, 3.0 - T / 2, 13.0, 13.9)):
        for k, p in enumerate((a, b)):
            q = (p - 0.06, p) if k == 0 else (p, p + 0.06)
            if along_x:
                box(f"door_frame_{name}_{k}", AREA, *q, fixed - 0.05, fixed + 0.05, FLOOR, door + 0.08, m["post"])
            else:
                box(f"door_frame_{name}_{k}", AREA, fixed - 0.05, fixed + 0.05, *q, FLOOR, door + 0.08, m["post"])
        if along_x:
            box(f"door_head_{name}", AREA, a - 0.1, b + 0.1, fixed - 0.06, fixed + 0.06, door, door + 0.12, m["post"])
        else:
            box(f"door_head_{name}", AREA, fixed - 0.06, fixed + 0.06, a - 0.1, b + 0.1, door, door + 0.12, m["post"])
    leaf("door_front_leaf_l", AREA, (-0.5, 11.48), math.radians(100), 0.49, FLOOR + 0.01, door - 0.01, 0.035, m["boards"])
    leaf("door_front_leaf_r", AREA, (0.5, 11.48), math.radians(80), 0.49, FLOOR + 0.01, door - 0.01, 0.035, m["boards"])
    # A hurricane lantern hung by the front door, and a lamp kept at the ancestral altar.
    place(AREA, "Lantern_01", (-0.9, 10.7, FLOOR + 1.7))
    flame("veranda_lantern_flame", AREA, -0.9, 10.7, FLOOR + 1.79, 0.045, m["flame"])
    tube("veranda_lantern_cord", AREA, [(-0.9, 10.7, FLOOR + 1.99), (-0.9, 10.7, ZW + 0.3)], 0.004, m["rope"], sides=4)
    empty("light_flame_veranda", AREA, (-0.9, 10.7, FLOOR + 1.82), radius=6.0, intensity=1.8)
    leaf("door_back_leaf", AREA, (2.8, 17.96), math.radians(-120), 0.88, FLOOR + 0.01, door - 0.01, 0.035, m["boards"])
    # Doors: Yay Mey's stays shut (A1-06); Sok's is locked until Act II (A1-07).
    rotate_uvs(box("interact_door_yaymey", AREA, -3.04, -2.98, 15.6, 16.5, FLOOR, door, m["boards"], action="knock"))
    collider("door_yaymey", AREA, -3.04, -2.98, 15.6, 16.5, FLOOR, door)
    rotate_uvs(box("interact_door_sok", AREA, 2.96, 3.02, 13.0, 13.9, FLOOR, door, m["boards"], action="open", requires="ep1.sok.unlocked"))
    collider("door_sok", AREA, 2.96, 3.02, 13.0, 13.9, FLOOR, door)
    box("door_sok_padlock", AREA, 2.93, 2.96, 13.06, 13.12, FLOOR + 1.0, FLOOR + 1.09, m["iron"])

    # Veranda railing, X-braced in 1.5 m bays like the 1921 houses; open at the stairs (east).
    rz0, rz1 = FLOOR + 0.12, FLOOR + 0.9
    for k in range(8):
        a, b = h["x0"] + 1.5 * k, h["x0"] + 1.5 * (k + 1)
        box(f"rail_post_{k}", AREA, a - 0.04, a + 0.04, 9.96, 10.04, FLOOR, rz1 + 0.05, m["post"])
        for j, (p, q) in enumerate((((a, rz0), (b, rz1)), ((a, rz1), (b, rz0)))):
            tube(f"rail_brace_{k}_{j}", AREA, [(p[0], 10.0, p[1]), (q[0], 10.0, q[1])], 0.025, m["post"], sides=4, metres_per_v=2.0)
    box("rail_top", AREA, h["x0"], h["x1"], 9.94, 10.06, rz1, rz1 + 0.05, m["post"], edge=0.01)
    box("rail_bottom", AREA, h["x0"], h["x1"], 9.96, 10.04, rz0 - 0.05, rz0, m["post"])
    collider("veranda_rail", AREA, h["x0"], h["x1"], 9.95, 10.1, FLOOR, FLOOR + 0.95)
    box("rail_west_top", AREA, h["x0"] - 0.06, h["x0"] + 0.06, 10.0, 11.5, rz1, rz1 + 0.05, m["post"])
    for j, (p, q) in enumerate((((10.0, rz0), (11.5, rz1)), ((10.0, rz1), (11.5, rz0)))):
        tube(f"rail_west_brace_{j}", AREA, [(h["x0"], p[0], p[1]), (h["x0"], q[0], q[1])], 0.025, m["post"], sides=4)
    collider("veranda_rail_w", AREA, h["x0"] - 0.08, h["x0"] + 0.08, 10.0, 11.5, FLOOR, FLOOR + 0.95)

    # Roof: plates on the posts, rafters, purlins, tiles, a ridge capping.
    pitch = math.radians(42)
    zp = ZW + 0.05
    for y in (10.0, 18.0):
        box(f"roof_plate_{y:.0f}", AREA, h["x0"] - 0.3, h["x1"] + 0.3, y - 0.1, y + 0.1, ZW - 0.1, zp, m["post"])
    over, gx = 0.9, 0.9
    ym = (h["y0"] + h["y1"]) / 2
    rise = (ym - h["y0"]) * math.tan(pitch)
    ridge = zp + 0.12 + rise
    ye_s, ye_n = h["y0"] - over, h["y1"] + over
    ze = zp + 0.12 - over * math.tan(pitch)
    for side, ye in ((-1, ye_s), (1, ye_n)):
        roof_slab(f"roof_{'s' if side < 0 else 'n'}", AREA, h["x0"] - gx, h["x1"] + gx, ye, ze, ym, ridge, 0.09, m["tiles"], 2.5)
        roof_slab(f"roof_under_{'s' if side < 0 else 'n'}", AREA, h["x0"] - gx, h["x1"] + gx, ye, ze - 0.09, ym, ridge - 0.09,
                  0.02, m["underside"], 2.0)
        for k, x in enumerate(np.arange(h["x0"] - gx + 0.2, h["x1"] + gx, 0.6)):
            roof_slab(f"rafter_{side}_{k}", AREA, x - 0.03, x + 0.03, ye + side * -0.05, ze - 0.11, ym, ridge - 0.11, 0.12, m["post"], 2.0)
        for k, f in enumerate((0.25, 0.55, 0.8)):
            y = ye + (ym - ye) * f
            z = ze + (ridge - ze) * f - 0.24
            box(f"purlin_{side}_{k}", AREA, h["x0"] - gx, h["x1"] + gx, y - 0.06, y + 0.06, z - 0.08, z + 0.08, m["post"])
    box("ridge_beam", AREA, h["x0"] - gx, h["x1"] + gx, ym - 0.08, ym + 0.08, ridge - 0.42, ridge - 0.12, m["post"])
    tube("ridge_cap", AREA, [(h["x0"] - gx - 0.05, ym, ridge + 0.02), (h["x1"] + gx + 0.05, ym, ridge + 0.02)], 0.11, m["clay"], sides=8)
    # King posts carry the ridge beam on the tie beams over the side walls.
    for x in (h["x0"], h["x1"]):
        box(f"tie_beam_{x:.0f}", AREA, x - 0.08, x + 0.08, h["y0"], h["y1"], ZW - 0.05, ZW + 0.15, m["post"])
        box(f"king_post_{x:.0f}", AREA, x - 0.07, x + 0.07, ym - 0.07, ym + 0.07, ZW + 0.15, ridge - 0.3, m["post"])
    # Gables boarded in, with a sunburst of strips; carved bargeboards with upturned ends.
    for x, out in ((h["x0"], -1), (h["x1"], 1)):
        zb = ZW + 0.15
        g = mesh_object(f"gable_{x:.0f}", AREA, [(x, h["y0"], zb), (x, h["y1"], zb), (x, ym, ridge - 0.15)],
                        [(0, 1, 2) if out > 0 else (0, 2, 1)], m["boards"])
        rotate_uvs(g)
        mesh_object(f"gable_{x:.0f}_in", AREA, [(x - out * 0.03, h["y0"], zb), (x - out * 0.03, h["y1"], zb), (x - out * 0.03, ym, ridge - 0.15)],
                    [(0, 2, 1) if out > 0 else (0, 1, 2)], m["boards"])
        hub = (x + out * 0.03, ym, zb + 0.35)
        for k in range(9):
            a = math.radians(12 + 156 * k / 8)
            reach = (ridge - zb - 0.5) / max(0.35, math.sin(a) + abs(math.cos(a)) * math.tan(pitch))
            end = (hub[0], ym + math.cos(a) * reach, hub[2] + math.sin(a) * reach)
            tube(f"gable_ray_{x:.0f}_{k}", AREA, [hub, end], 0.022, m["post"], sides=4, metres_per_v=2.0)
        box(f"gable_band_{x:.0f}", AREA, x + out * 0.0, x + out * 0.04, h["y0"], h["y1"], zb - 0.05, zb + 0.05, m["post"])
        bx = x + out * gx
        for side, ye in ((-1, ye_s), (1, ye_n)):
            roof_slab(f"bargeboard_{x:.0f}_{side}", AREA, bx - 0.04, bx + 0.04, ye, ze + 0.12, ym, ridge + 0.12, 0.32, m["post"], 2.0)
            tube(f"barge_hook_{x:.0f}_{side}", AREA, [(bx, ye, ze - 0.12), (bx, ye + side * 0.18, ze + 0.0), (bx, ye + side * 0.12, ze + 0.25),
                                                       (bx, ye - side * 0.02, ze + 0.32)], 0.04, m["post"], sides=6, radius_end=0.015)
        tube(f"gable_finial_{x:.0f}", AREA, [(bx, ym, ridge + 0.05), (bx, ym, ridge + 0.4), (bx + out * 0.08, ym, ridge + 0.75)],
             0.05, m["post"], sides=6, radius_end=0.008)
    # Stairs: up the east end onto the veranda (the pavilion stands 2 m in front), and at the back.
    stairs("stairs_front", AREA, 9.0, 6.0, 10.15, 11.35, 0, FLOOR, m, 12, axis="x")
    stairs("stairs_rear", AREA, 1.95, 2.75, 21.0, 18.0, 0, FLOOR, m, 11)


def interiors(m):
    """The hall with the ancestral altar, the kitchen, Yay Mey's and Sok's rooms."""
    F = FLOOR
    box("hall_mat", AREA, -1.8, 1.8, 12.4, 15.2, F, F + 0.006, m["mat"])
    # Authored cabinet and close-view altar components share the original anchors.
    build_hall_altar(AREA, m, F)
    collider("altar_ancestral", AREA, -0.8, 0.8, 17.4, 17.92, F, F + 1.1)
    empty("light_flame_hall", AREA, (0.3, 17.5, F + 1.2), radius=4.0, intensity=0.9)
    # Kanha's drawing of the betel tray, pinned beside the altar (A1-08).
    usable("interact_kanha_drawing", (1.1, 17.9, F + 1.5), lambda: mesh_object(
        "kanha_drawing", AREA, [(0.9, 17.89, F + 1.3), (1.3, 17.89, F + 1.3), (1.3, 17.89, F + 1.7), (0.9, 17.89, F + 1.7)],
        [(0, 1, 2, 3)], m["kanha_drawing"], uvs=[(0, 0), (1, 0), (1, 1), (0, 1)]), action="examine")
    # The detailed stand is built with the altar; retain its collision and tray marker.
    collider("offering_stand", AREA, -0.3, 0.3, 16.75, 17.2, F, F + 0.34)
    empty("marker_betel_tray", AREA, (0.0, 16.975, F + 0.34))
    usable("interact_incense_bundle", (-0.45, 17.55, F + 1.12), lambda: [
        pole(f"incense_bundle_{k}", AREA, (-0.6, 17.52 + k * 0.006, F + 1.105), (-0.3, 17.55 + k * 0.004, F + 1.11), 0.003, m["incense"], sides=4)
        for k in range(8)], action="pickup", item="incense")
    usable("interact_altar_candle", (0.45, 17.55, F + 1.12), lambda: lathe("spare_candle", AREA, [(0.014, 0.0), (0.014, 0.17), (0.0, 0.175)],
                                                                         0.45, 17.5, F + 1.1, m["wax"], segments=8), action="pickup", item="candle")
    box("hall_shelf", AREA, 2.75, 2.95, 15.0, 16.6, F + 1.2, F + 1.24, m["post"])
    usable("interact_lime_pot", (2.85, 15.6, F + 1.3), lambda: (
        lathe("lime_pot", AREA, [(0.0, 0.0), (0.04, 0.0), (0.055, 0.04), (0.045, 0.08), (0.03, 0.09), (0.0, 0.09)], 2.85, 15.6, F + 1.24, m["brass"], segments=12),
        lathe("lime_paste", AREA, [(0.0, 0.088), (0.03, 0.088)], 2.85, 15.6, F + 1.24, m["lime"], segments=10)),
        action="pickup", item="lime")
    usable("interact_oil_hall", (2.85, 16.2, F + 1.3), lambda: oil_bottle("oil_hall", 2.85, 16.2, F + 1.24, m), action="pickup", item="oil")
    usable("interact_sewing_box", (-2.5, 17.5, F + 0.3), lambda: (
        box("sewing_box", AREA, -2.7, -2.3, 17.3, 17.7, F, F + 0.22, m["worn"], edge=0.01),
        box("sewing_box_lid", AREA, -2.71, -2.29, 17.29, 17.71, F + 0.22, F + 0.25, m["lacquer"], edge=0.008)),
        action="open", item="shed_key")
    for k, (x, y) in enumerate([(-2.6, 12.0), (2.6, 17.4)]):
        box(f"hide_wardrobe_H{k + 1}", AREA, x - 0.35, x + 0.35, y - 0.3, y + 0.3, F, F + 1.9, m["teak"], edge=0.01)
        collider(f"wardrobe_H{k + 1}", AREA, x - 0.35, x + 0.35, y - 0.3, y + 0.3, F, F + 1.9)
    # Kitchen: a clay hearth box filled with ash, three stones and a pot; shelves of jars.
    box("kitchen_hearth", AREA, -5.8, -4.6, 11.7, 12.6, F, F + 0.45, m["clay"], edge=0.02)
    box("kitchen_hearth_ash", AREA, -5.72, -4.68, 11.78, 12.52, F + 0.45, F + 0.47, m["ash"])
    collider("kitchen_hearth", AREA, -5.8, -4.6, 11.7, 12.6, F, F + 0.6)
    # Keep the three stones under the pot's foot ring, with its base at their tops.
    for k, (sx, sy) in enumerate(((-5.295, 12.025), (-5.105, 12.025), (-5.2, 12.19))):
        lathe(f"hearth_stone_{k}", AREA, [(0.0, 0.0), (0.07, 0.0), (0.08, 0.06), (0.05, 0.14), (0.0, 0.15)], sx, sy, F + 0.46, m["stone"], segments=7)
    place(AREA, "ceramic_pot", (-5.2, 12.08, F + 0.61), scale=0.55)
    box("kitchen_table", AREA, -5.0, -3.6, 13.2, 14.2, F + 0.7, F + 0.75, m["worn"], edge=0.01)
    for lx in (-4.95, -3.65):
        for ly in (13.25, 14.15):
            box(f"kitchen_table_leg_{lx:.1f}_{ly:.1f}", AREA, lx - 0.03, lx + 0.03, ly - 0.03, ly + 0.03, F, F + 0.7, m["worn"])
    collider("kitchen_table", AREA, -5.0, -3.6, 13.2, 14.2, F, F + 0.75)
    usable("interact_betel_leaves", (-4.6, 13.5, F + 0.8), lambda: [
        box(f"betel_leaf_{k}", AREA, -4.72 + k * 0.01, -4.5 + k * 0.01, 13.42, 13.58, F + 0.75 + k * 0.004, F + 0.753 + k * 0.004, m["betel_leaf"],
            tilt=(0, 0, 0.2 * k)) for k in range(6)], action="pickup", item="betel")
    usable("interact_areca_nut", (-4.1, 13.9, F + 0.8), lambda: (
        place(AREA, "wooden_bowl_01", (-4.1, 13.9, F + 0.75), scale=0.45),
        [lathe(f"areca_{k}", AREA, [(0.0, 0.0), (0.02, 0.008), (0.022, 0.025), (0.0, 0.04)], -4.1 + 0.025 * math.cos(k * 2.1),
               13.9 + 0.025 * math.sin(k * 2.1), F + 0.77, m["areca"], segments=8) for k in range(4)]), action="pickup", item="areca")
    # Centre the bottle and its pickup anchor over the narrow wall shelf.
    usable("interact_oil_kitchen", (-5.82, 13.9, F + 1.0), lambda: oil_bottle("oil_kitchen", -5.82, 13.9, F + 0.95, m), action="pickup", item="oil")
    box("kitchen_shelf", AREA, -5.94, -5.7, 13.4, 14.4, F + 0.9, F + 0.95, m["post"])
    usable("interact_kitchen_drawer", (-3.8, 13.2, F + 0.65), lambda: box("kitchen_drawer", AREA, -4.0, -3.7, 13.18, 13.2, F + 0.6, F + 0.69, m["worn"]),
           action="open", item="matches")
    place(AREA, "wicker_basket_02", (-5.6, 14.1, F), scale=1.3)
    place(AREA, "wooden_bucket_01", (-3.4, 12.0, F), scale=0.9)
    water_jar("kitchen_jar", AREA, -5.6, 13.0, m, scale=0.7)
    # Yay Mey's room: her sleeping mat under a mosquito net, a small chest.
    box("yaymey_mat", AREA, -5.6, -3.8, 15.2, 16.4, F, F + 0.03, m["mat"])
    box("yaymey_pillow", AREA, -5.5, -5.1, 15.4, 16.2, F + 0.03, F + 0.12, m["cotton"], edge=0.03)
    for k, (a, b, axis) in enumerate(((-5.7, -3.7, "x"), (-5.7, -3.7, "x"), (15.1, 16.5, "y"), (15.1, 16.5, "y"))):
        fixed = (15.1, 16.5, -5.7, -3.7)[k]
        cloth(f"mosquito_net_{k}", AREA, a, b, F + 0.05, F + 1.6, fixed, m["net"], folds=6, depth=0.03, axis=axis)
    empty("marker_yay_mey_room", AREA, (-4.5, 16.5, F))
    box("yaymey_chest", AREA, -3.6, -3.15, 17.3, 17.75, F, F + 0.4, m["lacquer"], edge=0.01)
    # Sok's room: desk, chair, manuscripts, the gramophone, the chest under loose planks.
    box("sok_desk", AREA, 4.6, 5.8, 16.6, 17.6, F + 0.72, F + 0.76, m["teak"], edge=0.01)
    for lx in (4.65, 5.75):
        for ly in (16.65, 17.55):
            box(f"sok_desk_leg_{lx:.1f}_{ly:.1f}", AREA, lx - 0.03, lx + 0.03, ly - 0.03, ly + 0.03, F, F + 0.72, m["teak"])
    collider("sok_desk", AREA, 4.6, 5.8, 16.6, 17.6, F, F + 0.76)
    usable("interact_sok_desk", (5.2, 16.6, F + 0.6), lambda: box("sok_desk_drawer", AREA, 4.95, 5.45, 16.58, 16.6, F + 0.6, F + 0.7, m["teak"]),
           action="open", requires="drawer_key")
    place(AREA, "chinese_armchair", (5.2, 16.15, F), rot_deg=180)
    for k in range(4):
        box(f"palm_leaf_manuscript_{k}", AREA, 4.75, 5.3, 17.25 + k * 0.07, 17.3 + k * 0.07, F + 0.76, F + 0.8 + 0.02 * (k % 2), m["paper"], edge=0.004)
    place(AREA, "vintage_oil_lamp", (5.6, 17.35, F + 0.76))
    place(AREA, "book_encyclopedia_set_01", (3.4, 17.7, F), rot_deg=0)
    place(AREA, "vintage_suitcase", (3.6, 12.2, F), rot_deg=90)
    usable("interact_gramophone", (5.4, 15.6, F + 0.9), lambda: gramophone(5.4, 15.6, F, m), action="use")
    usable("interact_loose_planks", (4.5, 12.5, F + 0.02), lambda: [
        box(f"loose_plank_{k}", AREA, 4.1, 4.95, 12.2 + k * 0.21, 12.4 + k * 0.21, F, F + 0.012, m["floor"], tilt=(0, 0.01 * k, 0)) for k in range(3)],
        action="open", requires="brass_key")
    usable("interact_oil_sok", (5.6, 12.0, F + 0.1), lambda: oil_bottle("oil_sok", 5.6, 12.0, F, m), action="pickup", item="oil")


def oil_bottle(name, x, y, z, m):
    """A bottle of kerosene for the lamp, corked."""
    return (lathe(name, AREA, [(0.0, 0.0), (0.04, 0.0), (0.042, 0.01), (0.042, 0.13), (0.02, 0.17), (0.013, 0.2), (0.0, 0.2)],
                  x, y, z, m["bottle"], segments=12),
            lathe(f"{name}_cork", AREA, [(0.011, 0.19), (0.011, 0.225), (0.0, 0.225)], x, y, z, m["worn"], segments=6))


def gramophone(x, y, z, m):
    """Sok's gramophone on its stand: cabinet, turntable and a brass horn."""
    box("gramophone_stand", AREA, x - 0.3, x + 0.3, y - 0.3, y + 0.3, z, z + 0.62, m["teak"], edge=0.01)
    box("gramophone_cabinet", AREA, x - 0.2, x + 0.2, y - 0.2, y + 0.2, z + 0.62, z + 0.8, m["lacquer"], edge=0.01)
    lathe("gramophone_platter", AREA, [(0.0, 0.0), (0.16, 0.0), (0.16, 0.012), (0.0, 0.012)], x, y, z + 0.8, m["iron"], segments=20)
    horn = [(x + 0.12, y + 0.1, z + 0.85), (x + 0.16, y + 0.12, z + 1.0), (x + 0.12, y + 0.05, z + 1.18), (x + 0.0, y - 0.1, z + 1.3)]
    tube("gramophone_neck", AREA, horn[:3], 0.02, m["brass"], sides=8)
    bell = lathe("gramophone_horn", AREA, [(0.02, 0.0), (0.05, 0.12), (0.11, 0.22), (0.22, 0.28), (0.23, 0.29)], 0, 0, 0, m["brass"], segments=20)
    bell.location = horn[2]
    bell.rotation_euler = (math.radians(70), 0, math.radians(-20))
    collider("gramophone", AREA, x - 0.3, x + 0.3, y - 0.3, y + 0.3, z, z + 0.85)


def under_house(m):
    """Beneath the floor: the six jars, firewood, boards, baskets, a hammock."""
    for k, (x, y, kind) in enumerate([(-4.5, 11.0, "oil"), (-1.5, 16.5, "key"), (1.5, 11.5, "lore"),
                                      (4.5, 16.8, "key"), (-4.8, 16.8, "oil"), (4.6, 11.2, "key")]):
        usable(f"interact_jar_J{k + 1}", (x, y, 0.9), lambda x=x, y=y, k=k: water_jar(f"jar_J{k + 1}", AREA, x, y, m),
               action="search", holds=kind)
        collider(f"jar_J{k + 1}", AREA, x - 0.36, x + 0.36, y - 0.36, y + 0.36, 0, 0.85)
    # Firewood stacked in a rack between two stakes.
    for k in range(18):
        row, col = divmod(k, 6)
        y = 13.1 + col * 0.09
        tube(f"firewood_{k}", AREA, [(-5.8, y, 0.06 + row * 0.11), (-4.2, y + 0.02, 0.06 + row * 0.11)], 0.05, m["post_rough"], sides=6)
    collider("firewood", AREA, -5.8, -4.2, 13.0, 13.6, 0, 0.9)
    for k in range(5):
        box(f"stacked_board_{k}", AREA, 1.0, 2.6, 14.6 + (k % 2) * 0.05, 15.4 - (k % 2) * 0.05, k * 0.05, k * 0.05 + 0.04, m["old_planks"])
    collider("stacked_boards", AREA, 1.0, 2.6, 14.6, 15.4, 0, 0.6)
    for k, (x, y, s) in enumerate(((-2.2, 17.4, 1.6), (-2.6, 17.0, 1.2), (0.8, 12.4, 1.5))):
        place(AREA, "wicker_basket_02", (x, y, 0), rot_deg=40 * k, scale=s)
    place(AREA, "wooden_ladder_02", (5.6, 13.6, 0), rot_deg=90).rotation_euler.x = math.radians(-14)
    # A cloth hammock between two posts on the west side, out of the patrol's path.
    gathered_hammock(AREA, m)
    # Fish traps, a buffalo yoke, a spade and the family's chopping knife.
    for k, (x, y) in enumerate(((2.3, 16.9), (2.65, 17.2), (2.2, 17.45))):
        trap = lathe(f"fish_trap_{k}", AREA, [(0.0, 0.0), (0.16, 0.05), (0.2, 0.3), (0.12, 0.65), (0.06, 0.75), (0.0, 0.75)], 0, 0, 0,
                     m["bamboo_wall_2s"], segments=10)
        trap.location = (x, y, 0.2)
        trap.rotation_euler = (math.radians(90), 0, math.radians(40 * k))
    tube("buffalo_yoke", AREA, [(-3.2, 17.85, 1.6), (-3.0, 17.75, 1.75), (-2.6, 17.75, 1.78), (-2.2, 17.75, 1.75), (-2.0, 17.85, 1.6)],
         0.05, m["worn"], sides=6)
    place(AREA, "rusted_spade_01", (-2.8, 10.25, 0.5), rot_deg=10).rotation_euler.x = math.radians(-12)
    place(AREA, "machete", (-5.0, 13.3, 0.35), rot_deg=70).rotation_euler.y = math.radians(90)
    for k, (x, y) in enumerate(((-5.6, 15.2), (-5.2, 15.7))):
        lathe(f"straw_bundle_{k}", AREA, [(0.0, 0.0), (0.22, 0.0), (0.25, 0.4), (0.18, 0.8), (0.05, 0.9), (0.0, 0.9)], x, y, 0.0, m["thatch"], segments=10)
    collider("straw", AREA, -5.85, -4.95, 14.95, 15.95, 0, 0.9)
    # A chicken coop of woven bamboo, empty; a child's wooden cart left by the middle post.
    lathe("chicken_coop", AREA, [(0.0, 0.0), (0.5, 0.0), (0.5, 0.15), (0.4, 0.45), (0.2, 0.6), (0.0, 0.62)], -5.3, 12.2, 0.0, m["bamboo_wall_2s"], segments=12)
    box("toy_cart", AREA, -0.85, -0.6, 14.9, 15.05, 0.05, 0.12, m["worn"], edge=0.006)
    for k, (dx, dy) in enumerate(((-0.82, 14.88), (-0.63, 14.88), (-0.82, 15.07), (-0.63, 15.07))):
        w = lathe(f"toy_wheel_{k}", AREA, [(0.0, -0.008), (0.04, -0.008), (0.04, 0.008), (0.0, 0.008)], 0, 0, 0, m["worn"], segments=10)
        w.location = (dx, dy, 0.04)
        w.rotation_euler = (math.radians(90), 0, 0)
    for k, (x, y) in enumerate([(-6, 10), (6, 10), (6, 18), (-6, 18), (0, 14)]):
        empty(f"patrol_roamer_{k:02d}", AREA, (x * 0.7, y + (0.6 if y < 14 else -0.6 if y > 14 else 0), 0))
    empty("spawn_under_house", AREA, (0, 9.0, 0), (0, 0, 0), checkpoint="CP5")
    # Between the pillars, clear of the jars and the roamer's round.
    ritual_traces(AREA, m, -1.5, 12.0, rng)


# ---------------------------------------------------------------- the funeral


def funeral(m):
    from funeral import funeral_materials
    m = funeral_materials(m)
    t = TENT
    pavilion(AREA, m, t, rng)
    # The thread and its handle: all four sides are used as one thing (A3-01 snaps it).
    usable("interact_thread", (t["x0"] + 0.3, t["y0"], 2.3), lambda: protective_thread(AREA, m, t), action="examine")
    # The dais at the back: two steps under white cloth, the coffin on top.
    box("dais_low", AREA, -1.6, 1.6, 4.8, 6.85, 0.0, 0.3, m["teak"], edge=0.01)
    box("dais_high", AREA, -1.3, 1.3, 5.1, 6.7, 0.3, 0.55, m["teak"], edge=0.01)
    box("dais_cloth_low", AREA, -1.61, 1.61, 4.79, 6.86, 0.3, 0.31, m["cotton"])
    box("dais_cloth_high", AREA, -1.31, 1.31, 5.09, 6.71, 0.55, 0.56, m["cotton"])
    cloth("dais_skirt_s", AREA, -1.62, 1.62, 0.02, 0.31, 4.78, m["cotton"], folds=16, depth=0.02)
    for x, name in ((-1.62, "w"), (1.62, "e")):
        cloth(f"dais_skirt_{name}", AREA, 4.8, 6.85, 0.02, 0.31, x, m["cotton"], folds=10, depth=0.02, axis="y")
    collider("dais", AREA, -1.6, 1.6, 4.8, 6.85, 0, 0.56)
    ridge = coffin(AREA, m, -1.0, 1.0, 5.55, 6.25, 0.56)
    # The lamp kept burning at the head of the coffin all night.
    lathe("coffin_lamp", AREA, [(0.0, 0.0), (0.05, 0.0), (0.07, 0.02), (0.06, 0.035), (0.0, 0.03)], -1.15, 5.9, 0.56, m["clay"], segments=10)
    flame("coffin_lamp_flame", AREA, -1.15, 5.9, 0.6, 0.04, m["flame"])
    empty("light_flame_coffin", AREA, (-1.15, 5.9, 0.66), radius=2.5, intensity=0.8)
    # The monks' seat on the west side, and the white cord from the coffin to it.
    monks_seat(AREA, m, -3.75, -2.55, 2.4, 6.2, 0.4)
    tube("bangskol_cord", AREA, sag((-0.95, 5.55, ridge - 0.05), (-2.55, 4.3, 0.44), 0.18, n=14), 0.004, m["thread"], sides=4)
    # The altar before the coffin, facing the mourners.
    flames = altar(AREA, m, 0.0, 4.25, 0.05, rng)
    for k, f in enumerate(flames):
        empty(f"light_flame_altar_{k}", AREA, f, radius=2.5, intensity=0.45)
    # The four tall incense urns at the dais corners (the vigil's incense loop).
    for k, (x, y) in enumerate([(-1.9, 4.55), (1.9, 4.55), (1.9, 6.6), (-1.9, 6.6)]):
        usable(f"interact_incense_{k}", (x, y, 0.95), lambda x=x, y=y, k=k: tall_burner(f"incense_burner_{k}", AREA, x, y, 0.05, m, rng),
               action="tend", corner=k)
    # The main burner in front of the altar, where the token is burned (A3-07).
    lathe("main_burner", AREA, [(0.2, 0.0), (0.2, 0.05), (0.1, 0.1), (0.08, 0.25), (0.16, 0.32), (0.22, 0.45), (0.23, 0.5),
                                (0.2, 0.52), (0.0, 0.52)], 0.0, 3.55, 0.05, m["brass"], segments=20)
    lathe("main_burner_sand", AREA, [(0.0, 0.0), (0.2, 0.0)], 0.0, 3.55, 0.565, m["sand"], segments=16)
    incense_sticks("main_burner_incense", AREA, 0.0, 3.55, 0.565, m, 9, rng, length=0.28, spread=0.1)
    collider("main_burner", AREA, -0.23, 0.23, 3.32, 3.78, 0, 0.57)
    empty("marker_main_burner", AREA, (0, 3.55, 0.62))
    # East side: a bamboo platform for the mourners (an oil bottle left on it), the drums.
    bamboo_bed("tent_bed", AREA, m, 2.75, 3.75, 1.6, 5.4, 0.45)
    usable("interact_oil_tent", (3.2, 2.4, 0.5), lambda: oil_bottle("oil_tent", 3.2, 2.4, 0.45, m), action="pickup", item="oil")
    place(AREA, "wicker_basket_02", (3.3, 4.6, 0.45), scale=1.1)
    skor_drums(AREA, m, 3.0, 6.3)
    # Lanterns hung from the frame, and the jars of water at its edge.
    for k, (x, y) in enumerate([(-3.0, 2.0), (3.0, 2.0), (-3.0, 6.0), (3.0, 6.0)]):
        place(AREA, "Lantern_01", (x, y, 1.9))
        flame(f"lantern_flame_{k}", AREA, x, y, 1.99, 0.045, m["flame"])
        tube(f"lantern_cord_{k}", AREA, [(x, y, 2.19), (x, y, 2.6 + abs(y - 4.0) * 0.67 - 0.05)], 0.004, m["rope"], sides=4)
        empty(f"light_flame_tent_{k}", AREA, (x, y, 2.02), radius=6.0, intensity=3.0)
    for k, (x, y) in enumerate([(-4.6, 1.4), (4.6, 1.6), (-4.7, 6.5)]):
        water_jar(f"water_jar_{k}", AREA, x, y, m, scale=0.85)
        collider(f"water_jar_{k}", AREA, x - 0.32, x + 0.32, y - 0.32, y + 0.32, 0, 0.75)
    sandals(AREA, m, [(-1.6, 0.75, 0.2), (-1.0, 0.7, -0.1), (1.3, 0.8, 0.4), (2.1, 0.7, -0.3)])
    empty("marker_yay_mey", AREA, (-1.6, 3.0, 0.05))
    empty("marker_vuthy", AREA, (1.9, 4.6, 0.05))
    empty("marker_lightning", AREA, (-20, -10, 30))
    crocodile_flag(AREA, m, -2.6, -2.2, rng)


def eave(k, a, b):
    """A roof edge rain drips from (the game runs the drips between the two markers)."""
    empty(f"marker_eave_{k}_a", AREA, a)
    empty(f"marker_eave_{k}_b", AREA, b)


def funeral_details(m):
    """The mourners' things, and the signs that something has been in the pavilion:
    an upset cup, petals and rice scattered before the altar, candle stubs burnt out,
    muddy bare footprints coming round from behind the drape towards the coffin."""
    from funeral import funeral_materials
    m = funeral_materials(m)
    t = TENT
    # Oiled-paper umbrellas leaned on the corner post: it has rained for three days.
    for k, (dx, a) in enumerate(((0.12, 0.22), (0.2, -0.15), (0.05, 0.05))):
        x, y = t["x0"] + dx, t["y0"] - 0.18 - k * 0.07
        top = (x + 0.05 + 0.25 * math.sin(a), y - 0.1, 0.92)
        tube(f"umbrella_{k}", AREA, [(x, y, 0.02), (x + 0.02, y - 0.03, 0.25), top], 0.06, m["umbrella"], sides=8, radius_end=0.012)
        tube(f"umbrella_{k}_handle", AREA, [top, (top[0], top[1], top[2] + 0.12)], 0.01, m["bamboo"], sides=4)
    # A betel tray and the tea things on the mats where the mourners sat.
    lathe("betel_tray", AREA, [(0.0, 0.0), (0.22, 0.0), (0.24, 0.04), (0.23, 0.045), (0.0, 0.03)], -2.2, 2.4, 0.056, m["teak"], segments=16)
    box("betel_box", AREA, -2.28, -2.14, 2.34, 2.44, 0.086, 0.14, m["brass"], edge=0.006)
    for k, (dx, dy) in enumerate(((0.1, 0.08), (-0.1, 0.1), (0.05, -0.1))):
        lathe(f"betel_pot_{k}", AREA, [(0.0, 0.0), (0.025, 0.0), (0.035, 0.03), (0.02, 0.05), (0.0, 0.05)], -2.2 + dx, 2.4 + dy, 0.086, m["brass"], segments=10)
    lathe("teapot", AREA, [(0.0, 0.0), (0.06, 0.0), (0.085, 0.05), (0.075, 0.1), (0.04, 0.12), (0.015, 0.14), (0.0, 0.14)], -2.6, 3.0, 0.056, m["glaze"], segments=14)
    tube("teapot_spout", AREA, [(-2.53, 3.0, 0.1), (-2.48, 3.0, 0.14)], 0.012, m["glaze"], sides=6, radius_end=0.007)
    for k, (dx, dy) in enumerate(((0.15, 0.05), (0.12, -0.12))):
        lathe(f"tea_cup_{k}", AREA, [(0.0, 0.0), (0.025, 0.0), (0.035, 0.045), (0.0, 0.04)], -2.6 + dx, 3.0 + dy, 0.056, m["glaze"], segments=10)
    # The third cup knocked over, its tea spilled across the mat.
    cup = lathe("tea_cup_spilled", AREA, [(0.0, 0.0), (0.025, 0.0), (0.035, 0.045), (0.0, 0.04)], 0, 0, 0, m["glaze"], segments=10)
    cup.location = (-2.3, 3.25, 0.09)
    cup.rotation_euler = (math.radians(95), 0, math.radians(30))
    n = 14
    pts = [(-2.15 + math.cos(2 * math.pi * i / n) * 0.18 * (0.6 + 0.5 * rng.random()), 3.35 + math.sin(2 * math.pi * i / n) * 0.11, 0.058) for i in range(n)]
    mesh_object("tea_spill", AREA, [(-2.15, 3.35, 0.058)] + pts, [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)], m["tea_stain"])
    # Folded white mourning clothes left on the bamboo platform.
    for k in range(3):
        box(f"folded_cloth_{k}", AREA, 2.9, 3.3, 3.6 + k * 0.02, 3.9 + k * 0.02, 0.45 + k * 0.05, 0.5 + k * 0.05, m["cotton"], edge=0.015)
    # Petals and rice thrown before the altar, scattered further than any hand threw them.
    petals = [(rng.uniform(-0.9, 0.9), rng.uniform(3.0, 3.9), 0.056) for _ in range(70)]
    beads("scattered_petals", AREA, petals, 0.008, m["jasmine"])
    rice = [(rng.uniform(-0.8, 0.8), rng.uniform(3.2, 3.95), 0.054) for _ in range(120)]
    beads("scattered_rice", AREA, rice, 0.0035, m["rice"])
    # Candle stubs burnt down to nothing on the dais step.
    for k, x in enumerate((-1.25, 1.25, -0.6)):
        lathe(f"candle_stub_{k}", AREA, [(0.0, 0.0), (0.03, 0.0), (0.022, 0.015), (0.014, 0.03), (0.0, 0.03)], x, 4.95, 0.31, m["wax"], segments=8)
    # Bare footprints in mud: in from behind the back drape, down the east side, to the coffin.
    decal("footprints_0", AREA, m, "footprints", (2.15, 6.35), 0.32, 0.8, math.pi, 0.058)
    decal("footprints_1", AREA, m, "footprints", (2.0, 5.5), 0.32, 0.8, math.pi + 0.25, 0.058)
    decal("footprints_2", AREA, m, "footprints", (1.75, 4.85), 0.32, 0.8, math.pi + 0.9, 0.058)
    # White paper streamers hanging from the ridge.
    for k in range(10):
        x = -3.6 + k * 0.8
        tube(f"streamer_{k}", AREA, [(x, 4.0, 4.38), (x + 0.02, 4.02, 4.0), (x - 0.01, 4.0, 3.62)], 0.025, m["cotton"], sides=3, radius_end=0.012)
    cobweb("tent_web_0", AREA, m, (t["x0"] + 0.06, t["y1"] - 0.06, t["eave"] - 0.05), (0.7, 0, 0), (0, -0.4, -0.6), 0.7)
    cobweb("tent_web_1", AREA, m, (t["x1"] - 0.06, t["y1"] - 0.06, t["eave"] - 0.05), (-0.7, 0, 0), (0, -0.4, -0.6), 0.7)
    # Rain off the thatch: front and back eaves.
    eave(0, (t["x0"] - 0.65, t["y0"] - 0.55, 2.3), (t["x1"] + 0.65, t["y0"] - 0.55, 2.3))
    eave(1, (t["x0"] - 0.65, t["y1"] + 0.55, 2.3), (t["x1"] + 0.65, t["y1"] + 0.55, 2.3))
    # White cloth banners on tall bamboo poles at the pavilion's front corners and
    # the courtyard gate: the white banners every Khmer funeral raises.
    for k, (bx, by) in enumerate(((t["x0"] - 0.9, t["y0"] - 1.4), (t["x1"] + 0.9, t["y0"] - 1.4), (-2.3, -2.4), (2.3, -2.4))):
        h = 5.2 if k < 2 else 4.4
        pole(f"banner_pole_{k}", AREA, (bx, by, -0.2), (bx + 0.05, by, h), 0.04, m["bamboo"], sides=6)
        pole(f"banner_bar_{k}", AREA, (bx - 0.3, by, h - 0.15), (bx + 0.35, by, h - 0.12), 0.012, m["bamboo"], sides=4)
        cloth(f"banner_{k}", AREA, bx - 0.25, bx + 0.3, h - 3.0 + 0.4 * (k % 2), h - 0.17, by, m["cotton"], folds=3, depth=0.03, segments=(6, 16))
        collider(f"banner_pole_{k}", AREA, bx - 0.06, bx + 0.06, by - 0.06, by + 0.06, 0, 2.5)
    # A pair of baysei (បាយសី): tiered towers of folded banana leaf on bowls, for the dead.
    for k, bx in enumerate((-1.45, 1.45)):
        by = 4.55
        lathe(f"baysei_{k}_bowl", AREA, [(0.0, 0.0), (0.11, 0.0), (0.16, 0.08), (0.17, 0.1), (0.0, 0.09)], bx, by, 0.31, m["brass"], segments=14)
        z = 0.41
        for tier, r in enumerate((0.15, 0.13, 0.11, 0.09, 0.07, 0.05, 0.035)):
            lathe(f"baysei_{k}_tier_{tier}", AREA, [(r, 0.0), (r * 0.82, 0.07), (r * 0.35, 0.1), (0.0, 0.1)], bx, by, z, m["betel_leaf"], segments=12)
            beads(f"baysei_{k}_flowers_{tier}", AREA, [(bx + math.cos(a) * r * 0.9, by + math.sin(a) * r * 0.9, z + 0.02)
                                                       for a in (2 * math.pi * i / 10 for i in range(10))], 0.01, m["jasmine"])
            z += 0.075
        pole(f"baysei_{k}_spire", AREA, (bx, by, z), (bx, by, z + 0.12), 0.006, m["stem_green"], sides=4)
        beads(f"baysei_{k}_top", AREA, [(bx, by, z + 0.13)], 0.018, m["jasmine"])
    # Rows of thin candles and lotus bouquets along the dais step.
    for k in range(12):
        cx = -1.25 + 2.5 * k / 11
        if abs(cx) < 0.5:
            continue
        lathe(f"step_candle_{k}", AREA, [(0.008, 0.0), (0.008, 0.13), (0.0, 0.135)], cx, 4.9, 0.31, m["wax"], segments=6)
        if k % 2:
            flame(f"step_candle_{k}_flame", AREA, cx, 4.9, 0.445, 0.02, m["flame"])
    for k, cx in enumerate((-0.95, 0.95)):
        place(AREA, "brass_vase_03", (cx, 5.0, 0.31), scale=1.2)
        lotus_buds(f"step_lotus_{k}", AREA, cx, 5.0, 0.49, m, n=5)
    # Flies over the food left for the mourners.
    empty("marker_flies_tent", AREA, (-2.2, 2.4, 0.4))
    from funeral import finish_props
    finish_props(AREA, m, rng)


def house_details(m):
    """Around the house: a protective yantra over the doors, the jar to wash feet at
    the stairs, rain jars under the eaves, mourning clothes hung to dry under the
    house, cobwebs in its corners."""
    F = FLOOR
    yantra = box("yantra_front", AREA, -0.2, 0.2, 11.435, 11.44, F + 2.2, F + 2.56, m["yantra"])
    picture_uvs(yantra, (1, 0, 0), (0, 0, 1))
    yantra = box("yantra_sok", AREA, 2.925, 2.93, 13.27, 13.63, F + 2.2, F + 2.56, m["yantra"])
    picture_uvs(yantra, (0, -1, 0), (0, 0, 1))
    water_jar("footwash_jar", AREA, 9.65, 9.6, m, scale=0.75)
    collider("footwash_jar", AREA, 9.35, 9.95, 9.3, 9.9, 0, 0.65)
    lathe("footwash_ladle", AREA, [(0.0, -0.06), (0.06, -0.05), (0.08, 0.0)], 9.62, 9.58, 0.72, m["coconut"], segments=10)
    sandals(AREA, m, [(9.5, 10.5, 1.6), (9.9, 10.9, 1.3), (9.3, 11.2, 1.9)])
    for k, (x, y) in enumerate(((-6.7, 19.3), (6.7, 19.3), (-6.7, 8.7))):
        water_jar(f"rain_jar_{k}", AREA, x, y, m, scale=1.1, lid=False)
        collider(f"rain_jar_{k}", AREA, x - 0.4, x + 0.4, y - 0.4, y + 0.4, 0, 0.95)
    # Mourning clothes on a line between the back posts.
    tube("clothesline", AREA, sag((3.0, 18.12, 2.05), (6.0, 18.12, 2.05), 0.08, n=10), 0.006, m["rope"], sides=4)
    for k, (a, b, drop, mat) in enumerate(((3.25, 3.85, 0.75, "cotton"), (4.05, 4.95, 1.05, "cotton"), (5.15, 5.75, 0.6, "krama"))):
        cloth(f"hung_cloth_{k}", AREA, a, b, 2.02 - drop, 2.0, 18.13, m[mat], folds=3, depth=0.03, segments=(10, 6))
    for k, (corner, right, down) in enumerate((((-5.85, 10.1, F - 0.45), (0.8, 0, 0), (0, 0.3, -0.7)),
                                               ((2.85, 14.0, F - 0.45), (-0.7, 0, 0), (0, -0.4, -0.6)),
                                               ((5.85, 17.9, F - 0.45), (-0.8, 0, 0), (0, -0.3, -0.7)),
                                               ((-2.85, 17.9, F - 0.45), (0.7, 0, 0), (0, -0.3, -0.7)),
                                               ((-5.9, 11.56, ZW - 0.08), (0.6, 0, 0), (0, 0.3, -0.5)),
                                               ((5.9, 17.9, ZW - 0.08), (-0.6, 0, 0), (0, -0.3, -0.5)),
                                               ((-5.9, 14.44, ZW - 0.08), (0.7, 0, 0), (0, -0.3, -0.5)))):
        cobweb(f"house_web_{k}", AREA, m, corner, right, down, 0.75)
    # Rain off the roof's eaves.
    eave(2, (-6.9, 9.1, 4.35), (6.9, 9.1, 4.35))
    eave(3, (-6.9, 18.9, 4.35), (6.9, 18.9, 4.35))
    F = FLOOR
    # The hall's mantel clock on its own shelf (the hands are the model's; stopping them at 8:12 comes with the beats).
    place(AREA, "mantel_clock_01", (-1.6, 17.8, F + 1.24), rot_deg=180)
    box("clock_shelf", AREA, -1.9, -1.3, 17.7, 17.94, F + 1.2, F + 1.24, m["teak"])
    # The family's old photographs (the group, the mother, the eldest daughter), faded.
    # With them, high by the altar as images of monks are hung, a young monk at Angkor.
    for k, (fx, fz, hw, hh, u0, u1) in enumerate(((2.15, F + 1.8, 0.2, 0.14, 0.0, 0.4), (-2.3, F + 1.75, 0.1, 0.14, 0.4, 0.6),
                                                  (-2.0, F + 1.98, 0.1, 0.14, 0.6, 0.8), (1.1, F + 1.95, 0.1, 0.14, 0.8, 1.0))):
        box(f"family_frame_{k}", AREA, fx - hw - 0.03, fx + hw + 0.03, 17.93, 17.95, fz - hh - 0.03, fz + hh + 0.03, m["frame"])
        y = 17.925
        mesh_object(f"family_print_{k}", AREA, [(fx - hw, y, fz - hh), (fx + hw, y, fz - hh), (fx + hw, y, fz + hh), (fx - hw, y, fz + hh)],
                    [(0, 1, 2, 3)], m["family_prints"], uvs=[(u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0)])
    # Papers on the east wall of the hall (T_ep1_house_papers_BC, pixel rectangles as
    # in tools/drawings/village.mjs): the merchant's calendar for 1932 on a nail, Sok's
    # school certificate framed over the shelf; the head-tax receipt on the shelf.
    def papers_uv(px, py, pw, ph):
        u0, u1, v0, v1 = px / 2048, (px + pw) / 2048, 1 - (py + ph) / 1024, 1 - py / 1024
        return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]

    x = 2.935
    for name, (yc, z0, w, h, rect) in (("calendar", (14.45, F + 1.32, 0.3, 0.48, (0, 0, 640, 1024))),
                                       ("certificate", (15.8, F + 1.55, 0.35, 0.5, (1152, 0, 716, 1024)))):
        y0, y1 = yc - w / 2, yc + w / 2
        mesh_object(f"hall_{name}", AREA, [(x, y1, z0), (x, y0, z0), (x, y0, z0 + h), (x, y1, z0 + h)], [(0, 1, 2, 3)],
                    m["house_papers"], uvs=papers_uv(*rect))
    box("hall_certificate_frame", AREA, 2.938, 2.945, 15.6, 16.0, F + 1.525, F + 2.075, m["frame"])
    pole("hall_calendar_nail", AREA, (2.94, 14.45, F + 1.86), (2.91, 14.45, F + 1.87), 0.004, m["iron"], sides=4)
    tube("hall_calendar_string", AREA, [(2.932, 14.33, F + 1.8), (2.915, 14.45, F + 1.86), (2.932, 14.57, F + 1.8)], 0.002, m["thread"], sides=3)
    rx0, rx1, ry0, ry1, rz = 2.79, 2.88, 15.08, 15.207, F + 1.2425
    mesh_object("hall_tax_receipt", AREA, [(rx0, ry1, rz), (rx0, ry0, rz), (rx1, ry0, rz), (rx1, ry1, rz)], [(0, 1, 2, 3)],
                m["house_papers"], uvs=papers_uv(640, 0, 512, 720))
    # Palm-leaf manuscripts (សាស្ត្រាស្លឹករឹត) between boards, tied with cord, one wrapped in cloth.
    for j in range(3):
        # Each volume rests on the binding cord of the one below it.
        z = F + 1.24 + j * 0.04
        y0 = 15.72 + j * 0.01
        box(f"hall_satra_{j}", AREA, 2.8, 2.9, y0, y0 + 0.3, z, z + 0.035, m["worn" if j != 1 else "krama"], edge=0.004)
        for t in (0.25, 0.75):
            tube(f"hall_satra_cord_{j}_{int(t * 4)}", AREA, [(2.795, y0 + 0.3 * t, z - 0.001), (2.795, y0 + 0.3 * t, z + 0.037),
                                                            (2.905, y0 + 0.3 * t, z + 0.037), (2.905, y0 + 0.3 * t, z - 0.001)], 0.003, m["thread"], sides=3)

    # Rolled sleeping mats and pillows along the hall wall, clothes hung on pegs.
    for k in range(3):
        # The ten-sided roll's lowest vertices lie radius * cos(pi / 10) below its centre.
        z = F + 0.11 * math.cos(math.pi / 10)
        tube(f"rolled_mat_{k}", AREA, [(-2.75, 12.4 + k * 0.3, z), (-1.55, 12.4 + k * 0.3, z)], 0.11, m["mat"], sides=10, metres_per_v=1.0)
    for k in range(3):
        box(f"hall_pillow_{k}", AREA, -2.7, -2.3, 13.5 + k * 0.42, 13.85 + k * 0.42, F, F + 0.14, m["cotton"], edge=0.04)
    # Hang clothes on the solid partition, clear of Yay Mey's doorway (15.6–16.5).
    for k, (cy, mat) in enumerate(((14.68, "krama"), (15.02, "cotton_dirty"), (15.36, "cotton"))):
        pole(f"peg_{k}", AREA, (-2.93, cy, F + 1.75), (-2.82, cy, F + 1.75), 0.012, m["post"], sides=4)
        cloth(f"peg_cloth_{k}", AREA, cy - 0.17, cy + 0.17, F + 1.0, F + 1.74, -2.86, m[mat], folds=3, depth=0.03, axis="y", segments=(8, 8))
    # A hanging lamp in the hall, unlit; rice baskets and a betel set by the altar.
    tube("hall_lamp_cord", AREA, [(0.0, 14.5, ZW + 1.5), (0.0, 14.5, F + 2.04)], 0.004, m["rope"], sides=4)
    place(AREA, "Lantern_01", (0.0, 14.5, F + 1.75))
    for k, (bx, by) in enumerate(((1.6, 17.5), (2.0, 17.3))):
        place(AREA, "wicker_basket_02", (bx, by, F), rot_deg=50 * k, scale=1.6)
    usable("interact_betel_tray", (1.1, 16.9, F + 0.05), lambda: lathe(
        "hall_betel_tray", AREA, [(0.0, 0.0), (0.18, 0.0), (0.2, 0.05), (0.0, 0.04)], 1.1, 16.9, F, m["lacquer"], segments=14),
        action="pickup", item="betel_tray")
    lathe("hall_spittoon", AREA, [(0.0, 0.0), (0.07, 0.0), (0.09, 0.08), (0.05, 0.12), (0.1, 0.16), (0.0, 0.15)], 1.45, 16.6, F, m["brass"], segments=12)


def cooking_shelter(m):
    """The mourners' kitchen at the west side of the courtyard: a lean-to of thatch on
    bamboo posts over two three-stone hearths, big pots, firewood and baskets."""
    x0, x1, y0, y1 = -11.2, -8.0, 2.0, 6.4
    for x, y, top in ((x0, y0, 2.5), (x0, y1, 2.5), (x1, y0, 2.0), (x1, y1, 2.0)):
        pole(f"cook_post_{x:.0f}_{y:.0f}", AREA, (x, y, -0.1), (x, y, top), 0.06, m["bamboo"])
        collider(f"cook_post_{x:.0f}_{y:.0f}", AREA, x - 0.07, x + 0.07, y - 0.07, y + 0.07, 0, top)
    slope = [(x0 - 0.5, 2.62), (x1 + 0.6, 1.95)]
    verts = [(slope[0][0], y0 - 0.5, slope[0][1]), (slope[1][0], y0 - 0.5, slope[1][1]),
             (slope[1][0], y1 + 0.5, slope[1][1]), (slope[0][0], y1 + 0.5, slope[0][1])]
    top = [(x, y, z + 0.12) for x, y, z in verts]
    mesh_object("cook_roof", AREA, verts + top, [(4, 5, 6, 7), (3, 2, 1, 0), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], m["thatch"])
    for k, (hx, hy) in enumerate(((-10.2, 3.2), (-10.2, 5.2))):
        lathe(f"cook_ash_{k}", AREA, [(0.0, 0.0), (0.45, 0.0), (0.4, 0.04), (0.0, 0.05)], hx, hy, 0.0, m["ash"], segments=12)
        lathe(f"cook_embers_{k}", AREA, [(0.0, 0.05), (0.18, 0.05)], hx, hy, 0.0, m["embers"], segments=10)
        for j in range(3):
            a = 2 * math.pi * j / 3
            lathe(f"cook_stone_{k}_{j}", AREA, [(0.0, 0.0), (0.09, 0.0), (0.1, 0.1), (0.06, 0.2), (0.0, 0.21)],
                  hx + math.cos(a) * 0.22, hy + math.sin(a) * 0.22, 0.02, m["stone"], segments=7)
        place(AREA, "ceramic_pot", (hx, hy, 0.2), rot_deg=40 * k, scale=1.1)
        for j in range(3):
            a = 2 * math.pi * j / 3 + 0.4
            tube(f"cook_wood_{k}_{j}", AREA, [(hx + math.cos(a) * 0.1, hy + math.sin(a) * 0.1, 0.06),
                                              (hx + math.cos(a) * 0.7, hy + math.sin(a) * 0.7, 0.03)], 0.03, m["post_rough"], sides=5)
        collider(f"cook_hearth_{k}", AREA, hx - 0.45, hx + 0.45, hy - 0.45, hy + 0.45, 0, 0.6)
    empty("light_flame_kitchen", AREA, (-10.2, 4.2, 0.4), radius=3.5, intensity=0.6)
    for k in range(10):
        tube(f"cook_firewood_{k}", AREA, [(-11.0, 2.3 + k * 0.08, 0.05 + (k % 3) * 0.09), (-11.0 + 1.2, 2.32 + k * 0.08, 0.05 + (k % 3) * 0.09)],
             0.045, m["post_rough"], sides=6)
    collider("cook_firewood", AREA, -11.05, -9.75, 2.2, 3.15, 0, 0.35)
    for k, (x, y, s) in enumerate(((-8.6, 2.6, 1.6), (-8.5, 3.3, 1.3), (-8.7, 5.9, 1.5))):
        place(AREA, "wicker_basket_02", (x, y, 0), rot_deg=70 * k, scale=s)
    for k in range(4):
        place(AREA, "wooden_bowl_01", (-8.55, 4.5 + k * 0.02, 0.0 + k * 0.05), scale=0.6)
    water_jar("cook_jar", AREA, -8.6, 6.9, m)
    collider("cook_jar", AREA, -8.95, -8.25, 6.55, 7.25, 0, 0.85)
    place(AREA, "wooden_bucket_01", (-9.2, 6.8, 0), scale=1.0)
    bamboo_bed("cook_bed", AREA, m, -9.4, -8.3, 4.9, 6.2, 0.4)


def shed(m):
    """The storage shed east of the house (optional, locked: A1-11): woven bamboo walls,
    a single slope of thatch, a plank door."""
    sx0, sx1, sy0, sy1 = 9.0, 12.0, 13.0, 16.0
    T = 0.05
    wall("shed_wall_w", AREA, sx0, sx0 + T, sy0, sy1, 0, 2.3, m["bamboo_wall"], gaps=[(14.0, 15.0, 2.0)], surface="dirt")
    wall("shed_wall_e", AREA, sx1 - T, sx1, sy0, sy1, 0, 2.3, m["bamboo_wall"], surface="dirt")
    wall("shed_wall_s", AREA, sx0, sx1, sy0, sy0 + T, 0, 2.3, m["bamboo_wall"], surface="dirt")
    wall("shed_wall_n", AREA, sx0, sx1, sy1 - T, sy1, 0, 2.3, m["bamboo_wall"], surface="dirt")
    for x, y in ((sx0, sy0), (sx1, sy0), (sx0, sy1), (sx1, sy1)):
        pole(f"shed_post_{x:.0f}_{y:.0f}", AREA, (x, y, -0.1), (x, y, 2.75 if x == sx1 else 2.35), 0.07, m["post_rough"], metres=2.0)
    verts = [(sx0 - 0.45, sy0 - 0.4, 2.3), (sx1 + 0.4, sy0 - 0.4, 2.8), (sx1 + 0.4, sy1 + 0.4, 2.8), (sx0 - 0.45, sy1 + 0.4, 2.3)]
    top = [(x, y, z + 0.12) for x, y, z in verts]
    mesh_object("shed_roof", AREA, verts + top, [(4, 5, 6, 7), (3, 2, 1, 0), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], m["thatch"])
    mesh_object("shed_gable_s", AREA, [(sx0, sy0 - 0.01, 2.3), (sx1, sy0 - 0.01, 2.3), (sx1, sy0 - 0.01, 2.75)], [(0, 1, 2), (0, 2, 1)], m["bamboo_wall"])
    mesh_object("shed_gable_n", AREA, [(sx0, sy1 + 0.01, 2.3), (sx1, sy1 + 0.01, 2.3), (sx1, sy1 + 0.01, 2.75)], [(0, 1, 2), (0, 2, 1)], m["bamboo_wall"])
    rotate_uvs(box("interact_shed_door", AREA, sx0 - 0.04, sx0 + 0.02, 14.0, 15.0, 0, 2.0, m["old_planks"], action="open", requires="shed_key"))
    collider("shed_door", AREA, sx0 - 0.04, sx0 + 0.02, 14.0, 15.0, 0, 2.0)
    box("shed_padlock", AREA, sx0 - 0.07, sx0 - 0.04, 14.88, 14.94, 1.0, 1.09, m["iron"])
    box("shed_shelf", AREA, 10.4, 11.8, 13.3, 15.8, 0.8, 0.85, m["old_planks"])
    for lx in (10.45, 11.75):
        for ly in (13.35, 15.75):
            box(f"shed_shelf_leg_{lx:.1f}_{ly:.1f}", AREA, lx - 0.03, lx + 0.03, ly - 0.03, ly + 0.03, 0, 0.8, m["old_planks"])
    usable("interact_oil_shed_1", (11.3, 13.6, 0.9), lambda: oil_bottle("oil_shed_1", 11.3, 13.6, 0.85, m), action="pickup", item="oil")
    usable("interact_oil_shed_2", (11.3, 13.9, 0.9), lambda: oil_bottle("oil_shed_2", 11.3, 13.9, 0.85, m), action="pickup", item="oil")
    usable("interact_land_deed", (11.2, 15.2, 0.9), lambda: box("land_deed", AREA, 11.05, 11.35, 15.05, 15.3, 0.85, 0.856, m["paper"], tilt=(0, 0, 0.2)),
           action="pickup", item="lore", lore="L4")
    usable("interact_kanha_photo", (10.6, 15.6, 1.1), lambda: box("kanha_photo", AREA, 10.5, 10.7, 15.55, 15.57, 0.85, 1.12, m["paper"], tilt=(0.25, 0, 0)),
           action="pickup", item="lore", lore="L5")
    place(AREA, "wooden_ladder_02", (11.6, 15.6, 0), rot_deg=0).rotation_euler.x = math.radians(-12)
    for k in range(3):
        box(f"shed_tin_{k}", AREA, 10.5 + k * 0.3, 10.75 + k * 0.3, 13.4, 13.6, 0.0, 0.35, m["kerosene_tin"], edge=0.01)


def build():
    global AREA
    bpy.ops.wm.read_factory_settings(use_empty=True)
    AREA = bpy.data.collections.new("ep1_area_village")
    bpy.context.scene.collection.children.link(AREA)
    m = materials()

    terrain(m)
    vegetation(m)
    road(m)
    # Where Sora starts, by the cart (A1-01).
    empty("spawn_player", AREA, (1.2, -59.5, 0), (0, 0, 0), checkpoint="CP1")
    empty("marker_driver", AREA, (2.6, -61.2, 1.2))
    # The compound's fence with its opening onto the path, and the cart in the yard.
    bamboo_fence(AREA, m, "fence_s", (YARD["x0"], YARD["y0"]), (YARD["x1"], YARD["y0"]), gap=(11.4, 14.6))
    bamboo_fence(AREA, m, "fence_w", (YARD["x0"], YARD["y0"]), (YARD["x0"], YARD["y1"]))
    bamboo_fence(AREA, m, "fence_e", (YARD["x1"], YARD["y0"]), (YARD["x1"], YARD["y1"]))
    bamboo_fence(AREA, m, "fence_n", (YARD["x0"], YARD["y1"]), (YARD["x1"], YARD["y1"]))
    for x in (-1.6, 1.6):
        pole(f"gate_post_{x:+.0f}", AREA, (x, YARD["y0"], -0.2), (x, YARD["y0"], 2.2), 0.07, m["post_rough"], metres=2.0)
    pole("gate_beam", AREA, (-1.9, YARD["y0"], 2.1), (1.9, YARD["y0"], 2.12), 0.05, m["post_rough"], metres=2.0)
    ox_cart(AREA, m, "yard_cart", 10.6, 19.6, math.radians(-70))

    funeral(m)
    funeral_details(m)
    house(m)
    house_details(m)
    interiors(m)
    under_house(m)
    cooking_shelter(m)
    shed(m)

    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    tris = sum(len(o.data.polygons) for o in AREA.all_objects if o.type == "MESH" and not o.name.startswith("col_"))
    print(f"Saved {BLEND}: {len(AREA.all_objects)} objects, ~{tris} faces")


build()
