"""Rebuilds Episode 1's village as the farmstead (November 22, 2026): the re-planned house
on its stilts with the funeral under it, and the tangled farm round it, from the Cycles
previews the user approved on November 21-22. Patches the village file in place:

    blender -b art-source/blender/ep1/ep1_area_village.blend -P tools/areas/rebuild-farmstead.py

then `npm run export -- ep1 && npm run assets -- ep1`.

1. Takes out the water (paddies, the pond, puddles), the tight compound's fences, lane,
   yard and outdoor kitchen, the old shed, the funeral in the hall, the old house's shell,
   and the plants standing where the farm's buildings, fields and paths go.
2. Builds the house's new shell (stilt_house.py) and moves every old room's furniture and
   game markers into its new room; the kitchen's into the kitchen house.
3. Dresses the new rooms (house_new_rooms.py, house_props.py, house_dressing.py).
4. Builds the funeral under the house (funeral_under.py) and moves the vigil's markers,
   the portrait and the thread there.
5. Builds the farmstead (farmstead.py, game mode: the tall grass is the game's own), the
   winding cart track from the gate and the house's yard fence, and moves the shed's things
   into the tool shed and the six jars to the storage under the back block and the barn.

Run it once on the November 20 file: what it takes out is gone afterwards (git has it).
"""
import math
import os
import re
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import compound as C  # noqa: E402
import farmstead as FS  # noqa: E402
import funeral_under as FU  # noqa: E402
import stilt_house as SH  # noqa: E402
import village_expansion as VE  # noqa: E402
import village_nature as VN  # noqa: E402
from kit import box, collider, cylinder, import_model, library_material, mesh_object, tube  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
F = SH.FLOOR
sc = bpy.context.scene
vl = bpy.context.view_layer
ground = VE.Ground()


# ------------------------------------------------------------------ helpers


def collection(name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        sc.collection.children.link(coll)
    for obj in list(coll.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    return coll


def protected(o):
    return any(c.name in ("_protos", "nature_templates") for c in o.users_collection)


def delete(objs):
    gone = set()
    for o in list(objs):
        if o.name in gone or o.name not in bpy.data.objects:
            continue
        for c in [o] + list(o.children_recursive):
            gone.add(c.name)
    for name in gone:
        o = bpy.data.objects.get(name)
        if o is not None:
            bpy.data.objects.remove(o, do_unlink=True)
    return len(gone)


def world_box(objs):
    pts = []
    for o in objs:
        if o.type == "MESH" and len(o.data.vertices):
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
        elif o.type in ("EMPTY", "LIGHT", "CURVE"):
            pts.append(o.matrix_world.translation.copy())
    if not pts:
        return None
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def tree(o):
    return [o] + list(o.children_recursive)


def centre(o):
    bb = world_box(tree(o))
    return (bb[0] + bb[1]) / 2 if bb else o.matrix_world.translation.copy()


def roots():
    return [o for o in bpy.data.objects if o.parent is None and o.users_collection and not protected(o)]


class Excluded:
    """Builds with the rest of the village out of the view layer: every box the kit makes
    updates the view layer, which with the whole village in it costs a second each."""

    def __init__(self, *names):
        self.names = set(names)

    def __enter__(self):
        self.saved = {lc.name: lc.exclude for lc in vl.layer_collection.children}
        for lc in vl.layer_collection.children:
            lc.exclude = lc.name not in self.names

    def __exit__(self, *exc):
        for lc in vl.layer_collection.children:
            if lc.name in self.saved:
                lc.exclude = self.saved[lc.name]
        vl.update()


def put(o, x, y, surface_z, turn=0.0):
    """Moves a marker (and what hangs under it) so its things stand on `surface_z` at (x, y):
    the bottom of its meshes on the surface, or the marker 5 cm over it when it has none."""
    vl.update()
    meshes = [c for c in tree(o) if c.type == "MESH" and len(c.data.vertices)]
    bb = world_box(meshes) if meshes else None
    if bb:
        c = (bb[0] + bb[1]) / 2
        pivot, lift = Vector((c.x, c.y, bb[0].z)), surface_z - bb[0].z
    else:
        pivot, lift = o.matrix_world.translation.copy(), surface_z + 0.05 - o.matrix_world.translation.z
    M = (Matrix.Translation(Vector((x - pivot.x, y - pivot.y, lift))) @ Matrix.Translation(pivot)
         @ Matrix.Rotation(turn, 4, "Z") @ Matrix.Translation(-pivot))
    o.matrix_world = M @ o.matrix_world


def obj(name):
    o = bpy.data.objects.get(name)
    if o is None:
        print(f"[rebuild] missing {name}", flush=True)
    return o


# ------------------------------------------------------------------ 1. out


WATER = re.compile(r"^(paddy_|col_paddy_|flood|pond|puddle|forest_border_water|cp_pp_)")   # with the paddies' wading floor
COMPOUND = re.compile(r"^(compound_fence|compound_yard_fence|treewall_|gate_beam|gate_post|cp_lane|cp_yard|cook_|col_cook_"
                      r"|col_compound_|col_fence_|footprints|path_threads)")
HALL_FUNERAL = re.compile(r"^(altar_|baysei|step_|candle_stub|main_burner|dais_|hall_mat|incense_burner|funeral_prop|"
                          r"bangskol|scattered_|house_dread_hall|lantern_|thread_mesh|coffin_lamp|coffin_|"
                          # The November 20 funeral's shroud round the coffin and the monks' seat with its
                          # offerings (funeral_shroud.py, funeral_offerings.py): not in the approved hall.
                          r"hall_shroud|funeral_offerings)")
# Their colliders (named col_...): left behind, they stood in the hall as invisible walls.
HALL_FUNERAL_COL = re.compile(r"^col_(altar_|coffin|dais|main_burner|baysei|step_|incense_burner|funeral_|hall_shroud)")
OLD_SHELL = re.compile(
    r"^(wall_|col_|door_|win_|pillar_|roof_|gable|ridge|gallery_|porch_|back_board|back_joist|back_girder|back_floor|rail_|veranda_"
    r"|tie_beam|valley|baluster|house_ceiling|house_print|house_card|house_cobweb|house_beam|house_decay_termite|house_detail_tied"
    r"|floor_board|joist|girder|yantra_|stairs_rear|batten_|rafter_|purlin_|king_post_|footing_|bargeboard_|barge_hook_)")
SHELL_COL = re.compile(r"^col_(wall|door|win|pillar|rail|veranda|gallery|stair|floor|porch|back|roof|joist|beam|step|house_floor|post)")
# Kept through the shell's removal: they move to the new house.
KEEP_SHELL = re.compile(r"^(stairs_front_detailed|col_door_sok|door_sok_padlock|col_wardrobe_|col_house_chinese|col_shed_door)")
# The funeral's things that go under the house with it (moved, not rebuilt).
FUNERAL_MARKERS = ("interact_incense_0", "interact_incense_1", "interact_incense_2", "interact_incense_3", "marker_main_burner",
                   "interact_thread", "marker_flies_tent", "marker_vuthy", "marker_yay_mey", "interact_oil_tent")


def take_out():
    n = delete(o for o in bpy.data.objects if not protected(o) and o.type == "MESH" and (
        WATER.match(o.name) or any(s.material and re.search(r"water|flood", s.material.name, re.I) for s in o.material_slots)))
    print("[rebuild] water out", n, flush=True)
    n = delete(o for o in bpy.data.objects if not protected(o) and (COMPOUND.match(o.name) or o.name == "pond_spirit"))
    print("[rebuild] compound out", n, flush=True)
    for name in ("expansion_west", "expansion_east", "expansion_north"):
        c = bpy.data.collections.get(name)
        if c:
            print("[rebuild]", name, [o.name for o in c.objects][:30], flush=True)
            delete(list(c.objects))


# ------------------------------------------------------------------ lights (as the previews lit them)
#
# Every light the approved Cycles previews had goes into the village as a light_flame_
# marker carrying the preview's strength in watts, its colour and a reach; the game makes
# a light of each (VillageLights.ts), and a flame mesh burns on every lit wick, as in the
# previews (preview_v2.py, house_preview.py, farm_preview.py).

FLAME = {}
# The hall funeral's, the old kitchen's and the old veranda lantern's (its lantern went with the
# old shell; the previews have no light there).
LIGHTS_OUT = re.compile(r"^light_flame_(altar_\d+|coffin|offering_\d+|kitchen|veranda)$")


def keep_flame_template():
    """The hall's altar candle flame, the one the previews set on every lit wick, kept as
    a mesh before the hall's funeral goes."""
    src = bpy.data.objects.get("altar_candle_0_flame")
    if src is None:
        raise RuntimeError("altar_candle_0_flame missing: run on the November 20 file")
    vl.update()
    sp = [src.matrix_world @ Vector(c) for c in src.bound_box]
    FLAME["mesh"] = src.data.copy()
    FLAME["mesh"].name = "candle_flame"
    FLAME["matrix"] = src.matrix_world.copy()
    FLAME["foot"] = Vector((sum(p.x for p in sp) / 8, sum(p.y for p in sp) / 8, min(p.z for p in sp)))


def flames_at(coll, tips, prefix):
    """A candle flame standing on each wick tip (linked copies of one mesh)."""
    for k, tip in enumerate(tips):
        o = bpy.data.objects.new(f"{prefix}_{k:03d}", FLAME["mesh"])
        coll.objects.link(o)
        mw = FLAME["matrix"].copy()
        mw.translation = FLAME["matrix"].translation + (Vector(tuple(tip)) + Vector((0, 0, 0.002)) - FLAME["foot"])
        o.matrix_world = mw


def light_marker(coll, name, at, watts, colour):
    """A light_flame_ marker: the preview light's strength (W), colour and reach (m)."""
    old = bpy.data.objects.get(f"light_flame_{name}")
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    e = bpy.data.objects.new(f"light_flame_{name}", None)
    e.empty_display_type = "PLAIN_AXES"
    e.empty_display_size = 0.05
    e.location = tuple(at)
    coll.objects.link(e)
    e["watts"] = float(watts)
    e["color"] = [round(float(c), 3) for c in colour]
    # Where a light that strong stops mattering in the dark (the game windows it to zero).
    e["radius"] = round(max(1.8, min(12.0, 3.2 * math.sqrt(watts))), 2)
    return e


CANDLE = (1.0, 0.52, 0.2)
LAMP = (1.0, 0.55, 0.22)


def funeral_out():
    """The hall's funeral: its dais, burners, lamps and the old coffin go (the new coffin
    is built under the house); its markers are kept to move down with it."""
    keep_flame_template()
    print("[rebuild] stale lights out", delete(o for o in bpy.data.objects if LIGHTS_OUT.match(o.name)), flush=True)
    keep = set(FUNERAL_MARKERS)
    gone = []
    for o in bpy.data.objects:
        if protected(o) or not (HALL_FUNERAL.match(o.name) or HALL_FUNERAL_COL.match(o.name)) or o.name in keep or (
                o.parent and o.parent.name in keep):
            continue
        if not o.name.startswith("coffin_"):
            c = o.matrix_world.translation
            if o.type == "MESH" and len(o.data.vertices):
                bb = [o.matrix_world @ Vector(v) for v in o.bound_box]
                c = sum(bb, Vector()) / 8
            if not (-3.3 < c.x < 3.3 and 11.2 < c.y < 22.3 and c.z > 2.2):
                continue
        gone.append(o)
    print("[rebuild] hall funeral out", delete(gone), flush=True)
    # The old portrait in its frame: the wreath's photograph takes its place.
    old = obj("portrait_sok")
    props = {}
    photo = obj("interact_portrait")
    if photo:
        props = {k: photo[k] for k in photo.keys() if k not in ("_RNA_UI",)}
    photo_name = photo.name if photo else None
    if old:
        delete([old])
    if photo_name and photo_name in bpy.data.objects:
        delete([bpy.data.objects[photo_name]])
    return props


def shell_out():
    house_area = lambda x, y: -9.0 < x < 9.5 and 9.0 < y < 30.0  # noqa: E731
    gone = []
    for o in bpy.data.objects:
        if protected(o) or not OLD_SHELL.match(o.name) or KEEP_SHELL.match(o.name) or o.name == "col_ground":
            continue
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box] if o.type == "MESH" else [o.matrix_world.translation]
        cx, cy = sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts)
        if not (house_area(cx, cy) and max(p.z for p in pts) > 0.3):
            continue
        if o.name.startswith("col_") and not SHELL_COL.match(o.name):
            dx = max(p.x for p in pts) - min(p.x for p in pts)
            dy = max(p.y for p in pts) - min(p.y for p in pts)
            dz = max(p.z for p in pts) - min(p.z for p in pts)
            if not ((max(dx, dy) > 1.5 and min(dx, dy) < 0.35) or (dx > 2.5 and dy > 2.5 and dz < 0.6)):
                continue        # a piece of furniture's: it moves with its piece
        gone.append(o)
    print("[rebuild] old shell out", delete(gone), flush=True)


# ------------------------------------------------------------------ 2. furniture into the new rooms


OLD = {"kitchen": (-6, -3, 11.5, 14.5), "yaymey": (-6, -3, 14.5, 22), "hall": (-3, 3, 11.5, 22), "sok": (3, 6, 11.5, 18),
       "vuthy": (3, 6, 18, 22), "store": (-8, -3, 23.2, 28), "dining": (-3, 2, 23.2, 28), "spare": (2, 8, 23.2, 28),
       "porch": (-3, 2, 28, 29.5), "corr": (-8, 8, 22, 23.2)}
NEW = {"hall": ((-3, 3, 11.5, 17.5), 0), "yaymey": ((-6, -3, 11.5, 16), 0), "sok": ((-8, -0.7, 23.4, 27.4), -90),
       "vuthy": ((3, 6, 16, 22), 0), "store": ((0.7, 8, 27.4, 30.6), 0), "dining": ((-8, -0.7, 27.4, 30.6), 0),
       "spare": ((0.7, 8, 23.4, 27.4), 0), "porch": ((-2, 2, 34, 35.4), 0), "corr": ((-8, 8, 22, 23.4), 0)}
# Pieces set by hand, and what goes with them: (pattern, centre x, y, turn in degrees).
SPECIAL = [
    (r"wardrobe_H1", (-7.57, 29.0, 0)), (r"wardrobe_H2", (7.57, 26.2, 0)),
    # The sofa keeps the old room's turn: its back to the front wall, its seat to the room.
    (r"chinese_sofa", (4.5, 12.06, 0)), (r"chinese_tea_table", (4.5, 13.35, 0)),
    (r"chinese_console_table", (3.2, 13.05, 180)), (r"house_chinese_armchair", (5.45, 13.6, -90)),
]
DOOR_LEAVES = ("interact_door_sok", "interact_door_yaymey")


def turn_about(c, deg):
    return Matrix.Translation(c) @ Matrix.Rotation(math.radians(deg), 4, "Z") @ Matrix.Translation(-c)


def room_transform(room, lo, hi):
    (nx0, nx1, ny0, ny1), deg = NEW[room]
    ox0, ox1, oy0, oy1 = OLD[room]
    oc = Vector(((ox0 + ox1) / 2, (oy0 + oy1) / 2, 0))
    nc = Vector(((nx0 + nx1) / 2, (ny0 + ny1) / 2, 0))
    R = Matrix.Rotation(math.radians(deg), 4, "Z")
    rect = [R @ (Vector((x, y, 0)) - oc) for x in (ox0, ox1) for y in (oy0, oy1)]
    rr = [(min(p[i] for p in rect), max(p[i] for p in rect)) for i in (0, 1)]
    corners = [R @ (Vector((x, y, 0)) - oc) for x in (lo.x, hi.x) for y in (lo.y, hi.y)]
    ab = [(min(p[i] for p in corners), max(p[i] for p in corners)) for i in (0, 1)]
    nn = [(nx0 - nc.x, nx1 - nc.x), (ny0 - nc.y, ny1 - nc.y)]
    shift = []
    for i in (0, 1):
        (r0, r1), (a0, a1), (n0, n1) = rr[i], ab[i], nn[i]
        g0, g1 = a0 - r0, r1 - a1
        if g0 < 0.35 and g0 <= g1:      # against a wall: stays against the new room's
            s = n0 + g0 - a0
        elif g1 < 0.35:
            s = n1 - g1 - a1
        else:                           # in the room: the same share of the way across
            mid = (a0 + a1) / 2
            s = n0 + (mid - r0) / (r1 - r0) * (n1 - n0) - mid
        if a1 - a0 < n1 - n0 - 0.1:
            s = min(max(s, n0 + 0.05 - a0), n1 - 0.05 - a1)
        shift.append(s)
    return Matrix.Translation(nc + Vector((shift[0], shift[1], 0))) @ R @ Matrix.Translation(-oc)


MARKER = re.compile(r"^(interact_|marker_|hide_|spawn_)")
NEW_COLLS = ("stilt_house", "funeral_under", "farmstead")
# A part of a piece of furniture built as its own object: a table's legs, a shelf's
# uprights, a bin's feet and lid, a trunk's clasp, a shelf's brackets.
PART = re.compile(r"^(.+?)_(leg|foot|upright|lid|clasp|bracket)(?:_[\w.]+|\.\d{3})?$")


def furniture_groups(furniture):
    """The furniture that moves as one: each piece with its parts (a table top with its
    legs; a shelf's boards with their uprights), and with what lies on it (a letter and
    coins on a table). Moved one by one, each part was fitted to the new room on its own
    and landed somewhere else: legs standing out in the air beside their table top."""
    names = {f[0].name: f for f in furniture}
    up = {n: n for n in names}

    def find(n):
        while up[n] != n:
            up[n] = up[up[n]]
            n = up[n]
        return n

    def join(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            up[ra] = rb

    for n in names:
        m = PART.match(n)
        if not m:
            continue
        base = m.group(1)
        if base in names:
            join(n, base)
        sib = re.compile(rf"^{re.escape(base)}_\d+(\.\d{{3}})?$")
        for other in names:
            if other != n and sib.match(other):
                join(n, other)

    def boxes():
        out = {}
        for n, (r, lo, hi, c, room) in names.items():
            g = find(n)
            if g in out:
                out[g] = (Vector(map(min, out[g][0], lo)), Vector(map(max, out[g][1], hi)))
            else:
                out[g] = (lo.copy(), hi.copy())
        return out

    gb = boxes()
    # The pieces set by hand keep only their own parts: the new rooms' dressing sets their
    # tops, and what lay on them in the old rooms (the dining room's) goes its own way.
    special = {find(n) for n in names if any(re.search(pat, n) for pat, _v in SPECIAL)}
    for n, (r, lo, hi, c, room) in names.items():
        if lo.z < F + 0.05 or max(hi.x - lo.x, hi.y - lo.y) > 1.0:
            continue
        best = None
        for g, (glo, ghi) in gb.items():
            if g == find(n) or g in special or names[g][4] != room or ghi.z - glo.z < 0.1:
                continue
            if glo.x <= c.x <= ghi.x and glo.y <= c.y <= ghi.y and abs(lo.z - ghi.z) < 0.03:
                vol = (ghi.x - glo.x) * (ghi.y - glo.y) * (ghi.z - glo.z)
                if best is None or vol < best[0]:
                    best = (vol, g)
        if best:
            join(n, best[1])
    groups = {}
    for n in names:
        groups.setdefault(find(n), []).append(names[n])
    return list(groups.values())


def furnish_moves(skip):
    """Every root over the floor in an old room moves into its new room; a marker or a
    collider moves with the piece of furniture it belongs to. Returns the moved roots, the
    kitchen's (for the kitchen house) and the dining room's (they go)."""
    vl.update()
    found = []
    for r in roots():
        if r.name in skip or any(c.name in NEW_COLLS for c in r.users_collection):
            continue
        bb = world_box(tree(r))
        if bb is None:
            continue
        lo, hi = bb
        c = (lo + hi) / 2
        if lo.z < 2.3 or c.z > 6.0:
            continue
        room = next((k for k, (a, b, d, e) in OLD.items() if a <= c.x <= b and d <= c.y <= e), None)
        if room is not None:
            found.append((r, lo, hi, c, room))
    moved, kitchen, dining = [], [], []
    plan = {}
    furniture = [f for f in found if not MARKER.match(f[0].name) and not f[0].name.startswith("col_")]
    for group in furniture_groups(furniture):
        if len(group) > 1:
            print("[rebuild] moved as one:", sorted(f[0].name for f in group)[:12], flush=True)
        main = max(group, key=lambda f: (f[2] - f[1]).x * (f[2] - f[1]).y * max((f[2] - f[1]).z, 0.05))
        special = next(((f, v) for f in group for pat, v in SPECIAL if re.search(pat, f[0].name)), None)
        if special:
            (r, lo, hi, c, room), (tx, ty, deg) = special
            M = Matrix.Translation(Vector((tx - c.x, ty - c.y, 0))) @ turn_about(Vector((c.x, c.y, 0)), deg)
        elif main[4] in ("kitchen", "dining"):
            M = main[4]
        else:
            lo = Vector(map(min, *[f[1] for f in group])) if len(group) > 1 else main[1]
            hi = Vector(map(max, *[f[2] for f in group])) if len(group) > 1 else main[2]
            M = room_transform(main[4], lo, hi)
        for f in group:
            plan[f[0].name] = M
    for r, lo, hi, c, room in found:
        if r.name in plan:
            continue
        partner = None
        if r.name.startswith("col_") and r.name[4:] in plan:
            partner = r.name[4:]
        else:
            # The smallest piece of furniture (not a rug or a rail the length of a room)
            # whose box, grown 25 cm, holds the marker's or collider's middle.
            best = None
            for fr, flo, fhi, fc, froom in furniture:
                if max(fhi.x - flo.x, fhi.y - flo.y) > 2.5:
                    continue
                if flo.x - 0.25 <= c.x <= fhi.x + 0.25 and flo.y - 0.25 <= c.y <= fhi.y + 0.25 and flo.z - 0.3 <= c.z <= fhi.z + 0.4:
                    vol = (fhi.x - flo.x) * (fhi.y - flo.y) * max(fhi.z - flo.z, 0.05)
                    if best is None or vol < best[0]:
                        best = (vol, fr.name)
            partner = best[1] if best else None
        if partner is not None:
            plan[r.name] = plan[partner]
        elif room in ("kitchen", "dining"):
            plan[r.name] = room
        else:
            plan[r.name] = room_transform(room, lo, hi)
    bundles = {}
    for r, lo, hi, c, room in found:
        M = plan[r.name]
        if isinstance(M, str) and M == "kitchen":
            kitchen.append(r)
        elif isinstance(M, str) and M == "dining":
            dining.append(r)
        else:
            r.matrix_world = M @ r.matrix_world
            moved.append(r)
            bundles.setdefault(id(M), []).append(r)
    vl.update()
    return moved, kitchen, dining, list(bundles.values())


def keep_clear(bundles):
    """The trapdoor, the stair well and the attic ladder's foot stay clear; the hall's
    south-west corner round the trapdoor is left bare. A piece steps aside whole, with its
    parts, what lies on it and its markers."""
    zones = [(SH.TRAP[0] - 0.3, SH.TRAP[1] + 0.3, SH.TRAP[2] - 0.3, SH.TRAP[3] + 0.6),
             (SH.STAIR_HOLE[0] - 0.15, SH.STAIR_HOLE[1] + 0.15, SH.STAIR_HOLE[2] - 0.1, SH.STAIR_HOLE[3] + 0.15),
             (SH.HATCH[0] - 0.25, SH.HATCH[1] + 0.25, SH.HATCH[2], SH.HATCH[3] + 0.8)]
    corner = []
    for bundle in bundles:
        things = [r for r in bundle if not r.name.startswith(("interact_", "marker_", "hide_", "col_"))]
        bb = world_box([o for r in things for o in tree(r)])
        if bb is None or bb[0].z > F + 1.2:
            continue
        lo, hi = bb
        if lo.x < -1.0 and hi.x > -3.0 and lo.y < 13.6 and hi.y > 11.5:
            corner += things
            continue
        for zx0, zx1, zy0, zy1 in zones:
            if lo.x < zx1 and hi.x > zx0 and lo.y < zy1 and hi.y > zy0:
                for r in bundle:
                    r.matrix_world = Matrix.Translation((zx1 + 0.05 - lo.x, 0, 0)) @ r.matrix_world
                break
    print("[rebuild] trapdoor corner cleared", delete(corner), flush=True)


DRESS_OUT = re.compile(r"^(hall_pillow|yaymey_pillow|yaymey_mat|yaymey_rolled_mat|vuthy_pillow|vuthy_cushion|vuthy_mat|vuthy_blanket|"
                       r"dining_cushion|dining_mat|mosquito_net|rolled_mat|hall_mat|vuthy_net_|yaymey_hung|yaymey_clothes|hung_cloth|"
                       r"peg_cloth|corridor_shirt|corridor_krama|vuthy_sarong|vuthy_cloth|spare_dust_sheet)")


def doors(hc):
    """Sok's study door and Yay Mey's door are the old leaves (they keep the game's
    properties), hung in the new doorways in place of the new shell's leaves, and given the
    new shell's plain plank leaf for a body (stilt_house.plank_door). Yay Mey's stays shut
    and solid; Sok's keeps its own collider and padlock, the padlock set on the new face."""
    for name, leaf, x, y0, y1, turn in (("interact_door_sok", "door_sok_leaf", -SH.LC, 24.6, 25.5, 180),
                                         ("interact_door_yaymey", "door_yaymey_leaf", -3.0, 14.6, 15.5, 0)):
        o = obj(name)
        new = bpy.data.objects.get(leaf)
        if o is None:
            continue
        vl.update()
        lo, hi = world_box(tree(o))
        c = (lo + hi) / 2
        M = Matrix.Translation(Vector((x - c.x, (y0 + y1) / 2 - c.y, F - lo.z))) @ turn_about(Vector((c.x, c.y, 0)), turn)
        group = [o] + ([bpy.data.objects[n] for n in ("col_door_sok", "door_sok_padlock") if n in bpy.data.objects]
                       if name == "interact_door_sok" else [])
        for g in group:
            if g.parent is None or g.parent not in group:
                g.matrix_world = M @ g.matrix_world
        vl.update()
        if new is not None:
            me = new.data.copy()
            me.transform(o.matrix_world.inverted() @ new.matrix_world)
            o.data = me
            delete([new])
    lock = bpy.data.objects.get("door_sok_padlock")
    if lock is not None:
        vl.update()
        lo, _ = world_box([lock])
        lock.matrix_world = Matrix.Translation((-SH.LC + SH.LEAF_T / 2 + 0.002 - lo.x, 0, 0)) @ lock.matrix_world
    collider("door_yaymey", hc, -3.0, -3.0 + SH.T, 14.6, 15.5, F, SH.DOOR)
    vl.update()


# What never moves with a room: the house's own walls, floors, doors and windows.
FIXED = re.compile(r"^(wall_|door_|win_|house_floor|back_floor|house_ceiling|pillar_|trapdoor|attic_|"
                   r"col_(wall|door|win|house_floor|back_floor|pillar|trapdoor|attic|gallery|walkway))")


def pieces_in(x0, x1, y0, y1, z0=None, z1=None, name=None):
    """Roots (with their colliders) whose middle lies in the box; `name` a regex they match."""
    z0 = F - 0.1 if z0 is None else z0
    z1 = SH.ZW if z1 is None else z1
    vl.update()
    out = []
    for o in bpy.data.objects:
        if o.parent is not None or FIXED.match(o.name) or protected(o) or (name and not re.match(name, o.name)):
            continue
        bb = world_box(tree(o))
        if bb is None:
            continue
        c = (bb[0] + bb[1]) / 2
        if x0 <= c.x <= x1 and y0 <= c.y <= y1 and z0 <= c.z <= z1:
            out.append(o)
    return out


def move(objs, M, label):
    for o in objs:
        o.matrix_world = M @ o.matrix_world
    vl.update()
    print(f"[tidy] {label}:", sorted(o.name for o in objs), flush=True)


def shift(objs, dx=0.0, dy=0.0, dz=0.0, label=""):
    move(objs, Matrix.Translation((dx, dy, dz)), label)


def turn_to(objs, pivot, deg, target, label):
    """Turns pieces `deg` about the vertical through `pivot` and sets `pivot` on `target`."""
    p, t = Vector((pivot[0], pivot[1], 0.0)), Vector((target[0], target[1], 0.0))
    move(objs, Matrix.Translation(t) @ Matrix.Rotation(math.radians(deg), 4, "Z") @ Matrix.Translation(-p), label)


def named(*names):
    return [o for o in (bpy.data.objects.get(n) for n in names) if o is not None]


def tidy_house(hm):
    """The user, November 23 ("so many floating items, items cover the door, and poster
    aren't show in full size ... look at everything carefully"): every doorway and window
    cleared, nothing left floating, every picture shown whole. tools/areas audit:
    scratchpad audit_house.py. The old house's pieces came into the new rooms where its
    walls had stood: pegs and Kanha's drawing ended up in doorways, shelves across them."""
    # The mourning cloths over the family photographs and Kanha's mirror read as blank
    # stained sheets that hide the pictures; the old back wall's pegs and Vuthy's pegs
    # now stand in thin air in doorways and a window.
    gone = [o for o in bpy.data.objects if re.match(r"^(family_frame_\d+_cover|kanha_mirror_cloth|corridor_peg_\d+|vuthy_peg_\d+)$", o.name)]
    print("[tidy] covers and stray pegs out", delete(gone), flush=True)
    # Kanha's drawing hung in the north door of the washing room: on the wall beside it.
    shift(named("interact_kanha_drawing"), dx=0.75, label="Kanha's drawing beside the north door")
    # The hall's shelf ran into the parlour's doorway: it and what stands on it move south.
    shift(pieces_in(2.7, 2.97, 13.1, 14.8, 3.68, 4.0), dy=-0.35, label="hall shelf clear of the parlour door")
    # The family photographs: off the door frames, onto the clear walls.
    shift(named("family_frame_0", "family_print_0"), dy=1.59, label="photograph clear of the parlour door")
    shift(named("family_frame_1", "family_print_1"), dx=3.8, label="photograph clear of the west altar door")
    shift(named("family_frame_2", "family_print_2"), dx=3.85, label="photograph clear of the west altar door")
    shift(named("prop_wicker_basket_02.002"), dx=0.75, label="baskets clear of the west altar door")
    shift(pieces_in(-2.75, -2.25, 14.68, 15.2, F - 0.1, F + 0.5), dy=-0.75, label="sewing box clear of Yay Mey's door")
    # Yay Mey's room: her betel set goes with her mat to the east wall (house_dressing),
    # her chest to the west wall under the window (low, it hides nothing), her shelf from
    # beside the loom room's door to the west wall between the windows.
    shift(pieces_in(-5.7, -4.6, 12.8, 13.4, F - 0.1, F + 0.4, name=r"^yaymey_(betel|mortar|pestle|spittoon)"), dx=1.65, dy=-0.25,
          label="Yay Mey's betel set with her mat")
    shift(pieces_in(-3.65, -3.1, 13.05, 13.6, F - 0.1, F + 0.6, name=r"^(col_)?yaymey_chest"), dx=-2.3,
          label="Yay Mey's chest under the west window")
    turn_to(pieces_in(-5.85, -5.0, 15.6, 15.97, 3.8, 4.7), (-5.425, 15.94), 90, (-5.94, 14.15), "Yay Mey's shelf to the west wall")
    # Vuthy's trunk stood in his door; the stool on the east gallery in its door.
    shift(pieces_in(5.1, 5.9, 16.25, 16.9, F - 0.1, F + 0.6), dy=0.75, label="Vuthy's trunk clear of his door")
    shift(named("house_wooden_stool_02_8"), dy=0.85, label="gallery stool clear of the door")
    # Kanha's suitcases stood against her mirror by the door: along the south wall.
    turn_to(pieces_in(0.85, 1.55, 25.4, 27.2, name=r"^house_vintage_suitcase"), (1.19, 26.3), -90, (3.6, 23.72),
            "Kanha's suitcases to the south wall")
    # The store's shelves ran across its door: to the north wall, with what is on them.
    turn_to(pieces_in(0.72, 1.2, 27.6, 30.45), (0.73, 29.04), -90, (2.3, 30.57), "store shelves to the north wall")
    shift(named("house_rusted_spade_01_23"), dy=-0.7, label="spade clear of the store window")
    # Sok's study: the desk stood in his door's swing; the gramophone and the armchair
    # stood in each other.
    shift(pieces_in(-2.25, -1.15, 23.55, 24.85), dx=-0.25, dy=-0.12, label="Sok's desk clear of his door")
    shift(named("prop_chinese_armchair"), dx=-0.1, dy=0.15, label="armchair drawn back from the desk")
    gram = obj("interact_gramophone")
    if gram is not None:
        c = centre(gram)
        shift([gram], dx=-2.0 - c.x, dy=27.06 - c.y, label="gramophone against the north wall")
    # The bathing corner: the dipper rests on the jar's mouth (it hung beside it), the ash
    # pot clear of the door, and the slats on sleepers if theirs did not come along.
    jar, dip = obj("bath_jar"), obj("bath_dipper")
    if jar is not None and dip is not None:
        jb, db = world_box(tree(jar)), world_box(tree(dip))
        d = Vector(((jb[0].x + jb[1].x) / 2 - (db[0].x + db[1].x) / 2, (jb[0].y + jb[1].y) / 2 - (db[0].y + db[1].y) / 2,
                    jb[1].z - 0.025 - db[0].z))
        shift(named("bath_dipper", "bath_dipper_handle"), d.x, d.y, d.z, "dipper on the jar")
    shift(named("bath_ash_pot"), dx=2.3, dy=-1.95, label="ash pot clear of the washroom door")
    slats = [o for o in bpy.data.objects if o.name.startswith("bath_slat")]
    if slats and not any(o.name.startswith("bath_sleeper") for o in bpy.data.objects):
        bb = world_box(slats)
        for k, x in enumerate((bb[0].x + 0.12, (bb[0].x + bb[1].x) / 2, bb[1].x - 0.12)):
            box(f"bath_sleeper_{k}", bpy.data.collections["stilt_house"], x - 0.05, x + 0.05, bb[0].y + 0.02, bb[1].y - 0.02, F,
                bb[0].z, hm["cl_trim"])
        print("[tidy] slats set on new sleepers", flush=True)
    better_trunk(hm)
    prayer_beads()
    store_rope_and_mats()
    detail_boxes()


def _ball(verts, faces, c, r, us=8, vs=6):
    """A low UV sphere's vertices and quads appended to the lists."""
    base = len(verts)
    verts.append((c[0], c[1], c[2] - r))
    for i in range(1, vs):
        a = math.pi * i / vs
        for j in range(us):
            b = math.tau * j / us
            verts.append((c[0] + r * math.sin(a) * math.cos(b), c[1] + r * math.sin(a) * math.sin(b), c[2] - r * math.cos(a)))
    verts.append((c[0], c[1], c[2] + r))
    top = len(verts) - 1
    for j in range(us):
        faces.append((base, base + 1 + (j + 1) % us, base + 1 + j))
    for i in range(vs - 2):
        r0, r1 = base + 1 + i * us, base + 1 + (i + 1) * us
        for j in range(us):
            faces.append((r0 + j, r0 + (j + 1) % us, r1 + (j + 1) % us, r1 + j))
    last = base + 1 + (vs - 2) * us
    for j in range(us):
        faces.append((last + j, last + (j + 1) % us, top))


def prayer_beads():
    """Yay Mey's prayer beads were a five-sided tube hanging in the air a centimetre in
    front of her shelf: a string of wooden beads lying on the shelf, over its lip and
    hanging in a loop, with the large bead and a cotton tassel at the bottom."""
    shelf, old = obj("yaymey_shelf"), obj("yaymey_prayer_beads")
    if shelf is None or old is None:
        return
    lo, hi = world_box([shelf])
    blo, bhi = world_box([old])
    wood = old.active_material
    tassel = obj("yaymey_prayer_tassel")
    thread = tassel.active_material if tassel else wood
    coll = old.users_collection[0]
    delete([old] + ([tassel] if tassel else []))
    r, pitch = 0.0055, 0.0118
    fx, c, top = hi.x, (blo.y + bhi.y) / 2, hi.z        # the shelf's front lip, the beads' old centre
    zt, w, back, drop = top + r, 0.034, 0.06, 0.16
    path = [(fx - back - w * math.sin(t), c - w * math.cos(t), zt) for t in np.linspace(0, math.pi, 9)][::-1]
    path += [(fx - 0.004, c + w, zt), (fx + r * 0.8, c + w, top - 0.002), (fx + r, c + w * 0.97, top - 0.03)]
    path += [(fx + r, c + w * 0.97 * math.cos(math.pi * t), top - 0.03 - (drop - 0.03) * math.sin(math.pi * t))
             for t in np.linspace(0.06, 0.94, 15)]
    path += [(fx + r, c - w * 0.97, top - 0.03), (fx + r * 0.8, c - w, top - 0.002), (fx - 0.004, c - w, zt), (fx - back, c - w, zt)]
    pts = [Vector(p) for p in path]
    pts.append(pts[0])
    seg = [(a - b).length for a, b in zip(pts[1:], pts[:-1])]
    total = sum(seg)
    n = int(total / pitch)
    verts, faces = [], []
    for k in range(n):
        d, i = k * total / n, 0
        while d > seg[i]:
            d -= seg[i]
            i += 1
        p = pts[i].lerp(pts[i + 1], d / seg[i])
        _ball(verts, faces, p, r * (0.93 + 0.07 * math.sin(k * 2.3)))
    low = min(pts, key=lambda q: q.z)
    _ball(verts, faces, (fx + r, c, low.z - 0.012), 0.0085, 10, 8)    # the large bead where the loop closes
    mesh_object("yaymey_prayer_beads", coll, verts, faces, wood, smooth=True)
    # The tassel: a knot, then a flared skirt of cotton threads.
    tv, tf = [], []
    _ball(tv, tf, (fx + r, c, low.z - 0.026), 0.005, 8, 6)
    z0, z1 = low.z - 0.03, low.z - 0.085
    for k in range(18):
        a = math.tau * k / 18
        for (rr0, rr1) in ((0.0035, 0.011),):
            p0 = Vector((fx + r + rr0 * math.cos(a), c + rr0 * math.sin(a), z0))
            p1 = Vector((fx + r + rr1 * math.cos(a), c + rr1 * math.sin(a), z1 + 0.004 * math.sin(k * 1.7)))
            side = Vector((-math.sin(a), math.cos(a), 0)) * 0.0011
            b = len(tv)
            tv += [tuple(p0 - side), tuple(p0 + side), tuple(p1 + side), tuple(p1 - side)]
            tf.append((b, b + 1, b + 2, b + 3))
    mesh_object("yaymey_prayer_tassel", coll, tv, tf, thread, smooth=True)
    print("[tidy] prayer beads strung over the shelf lip:", n, "beads", flush=True)


def _rope(name, coll, path, rr, mat, pitch=0.034, step=0.007):
    """A three-strand laid rope along `path` (points): three strands twisting round it."""
    pts = [Vector(p) for p in path]
    dense = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        n = max(1, int((b - a).length / step))
        dense += [a.lerp(b, (k + 1) / n) for k in range(n)]
    strands, s = [[], [], []], 0.0
    for i, p in enumerate(dense):
        t = (dense[min(i + 1, len(dense) - 1)] - dense[max(i - 1, 0)]).normalized()
        nrm = t.cross(Vector((0, 0, 1)))
        nrm = nrm.normalized() if nrm.length > 1e-4 else Vector((1, 0, 0))
        bi = nrm.cross(t)
        if i:
            s += (p - dense[i - 1]).length
        for j in range(3):
            a = s / pitch * math.tau + j * math.tau / 3
            strands[j].append(tuple(p + (nrm * math.cos(a) + bi * math.sin(a)) * rr * 0.47))
    from khmer import join as kjoin
    return kjoin([tube(f"{name}_strand", coll, st, rr * 0.56, mat, sides=5, metres_per_v=0.05) for st in strands], name)


def _rolled_mat(name, coll, mat, base, axis, length, r0=0.016, r1=0.068, turns=3.1, th=0.004, phase=0.0):
    """A sleeping mat rolled up: a thin woven sheet wound into a spiral (seen at both
    ends), with its outer edge along the length."""
    a = Vector(axis).normalized()
    u = Vector((1, 0, 0)) if abs(a.x) < 0.9 else Vector((0, 1, 0))
    u = (u - a * u.dot(a)).normalized()
    v = a.cross(u)
    n = int(turns * 30)
    ring = []
    for k in range(n + 1):                    # the outer face, in to out
        t = k / n
        th_ = phase + t * turns * math.tau
        ring.append((math.cos(th_), math.sin(th_), r0 + (r1 - r0) * t))
    outer = [(c, s_, r) for c, s_, r in ring]
    inner = [(c, s_, r - th) for c, s_, r in ring][::-1]
    loop = outer + inner
    verts = []
    for h in (0.0, length):
        for c, s_, r in loop:
            verts.append(tuple(Vector(base) + u * (r * c) + v * (r * s_) + a * h))
    m = len(loop)
    faces = [(i, (i + 1) % m, m + (i + 1) % m, m + i) for i in range(m)]
    for off in (0, m):                         # the spiral band at each end
        for k in range(n):
            faces.append((off + k, off + k + 1, off + m - 2 - k, off + m - 1 - k))
    o = mesh_object(name, coll, verts, faces, mat)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data)
    bm.free()
    parts = [o]
    for f in (0.22, 0.78):                     # tied round with string at two places
        c0 = Vector(base) + a * (length * f)
        circ = [tuple(c0 + (u * math.cos(q) + v * math.sin(q)) * (r1 + 0.0025)) for q in np.linspace(0, math.tau, 25)]
        parts.append(tube(f"{name}_tie", coll, circ, 0.0022, mat, sides=4))
    from khmer import join as kjoin
    return kjoin(parts, name)


def store_rope_and_mats():
    """The store's coils of rope were two smooth white tori and its rolled mats three plain
    cylinders standing loose in the room (one through a shelf board): a laid rope in two
    loose coils with a trailing end, and three mats rolled and tied, leaning in the corner
    on the south wall."""
    old_rope = [o for o in bpy.data.objects if re.match(r"^store_rope_\d+$", o.name)]
    old_mats = [o for o in bpy.data.objects if re.match(r"^store_rolled_mat_\d+$", o.name)]
    if not old_rope or not old_mats:
        return
    coll = old_rope[0].users_collection[0]
    rope_mat = old_rope[0].active_material.copy()
    rope_mat.name = "M_store_coir_rope"
    bsdf = next((nd for nd in rope_mat.node_tree.nodes if nd.type == "BSDF_PRINCIPLED"), None)
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.21, 0.15, 0.085, 1)
        bsdf.inputs["Roughness"].default_value = 0.95
    mat_mat = old_mats[0].active_material
    delete(old_rope + old_mats)
    F = SH.FLOOR
    rng = np.random.default_rng(23)
    for k, (cx, cy, R0, turns, rr) in enumerate(((2.95, 27.97, 0.16, 5.0, 0.011), (3.43, 28.03, 0.12, 3.5, 0.0095))):
        path, ph = [], rng.uniform(0, math.tau)
        for q in np.linspace(0, turns * math.tau, int(turns * 40)):
            R = R0 * (1 + 0.07 * math.sin(q * 0.7 + ph) + 0.03 * math.sin(q * 2.3))
            c = Vector((cx + 0.012 * math.sin(q / 3 + ph), cy + 0.012 * math.cos(q / 2.3), 0))
            path.append(c + Vector((R * math.cos(q + ph), R * math.sin(q + ph), F + rr + q / math.tau * 1.25 * rr)))
        end, out = path[-1], Vector((math.cos(turns * math.tau + ph), math.sin(turns * math.tau + ph), 0))
        side = Vector((-out.y, out.x, 0))
        path += [end + out * 0.04 + side * 0.06 - Vector((0, 0, (end.z - F - rr) * 0.4)),
                 end + out * 0.1 + side * 0.11 - Vector((0, 0, end.z - F - rr)),
                 end + out * 0.22 + side * 0.12 - Vector((0, 0, end.z - F - rr))]
        _rope(f"store_rope_{k}", coll, path, rr, rope_mat)
    face = SH.ROW1 + SH.T / 2
    tilt = math.radians(5)
    for k, x in enumerate((4.25, 4.43, 4.6)):
        r1, L = 0.068 - 0.004 * k, 1.1 - 0.06 * k
        axis = (rng.uniform(-0.015, 0.015), -math.sin(tilt), math.cos(tilt))
        yb = face + 0.014 + r1 * math.cos(tilt) + L * math.sin(tilt)
        _rolled_mat(f"store_rolled_mat_{k}", coll, mat_mat, (x, yb, F + r1 * math.sin(tilt)), axis, L, r1=r1, phase=rng.uniform(0, math.tau))
    print("[tidy] store rope coiled, mats rolled and leant on the south wall", flush=True)


def _joined(parts, name):
    """Joins meshes after applying each one's modifiers (a join keeps only the active
    object's, so the bevels on the rest would be lost)."""
    deps = bpy.context.evaluated_depsgraph_get()
    for o in parts:
        if o.type == "MESH" and o.modifiers:
            me = bpy.data.meshes.new_from_object(o.evaluated_get(deps))
            o.modifiers.clear()
            o.data = me
    from khmer import join as kjoin
    return kjoin(parts, name)


def detail_boxes():
    """Three plain boxes that read as placeholders: Yay Mey's chest (a red cube) made a
    lacquered chest on a plinth with an overhanging lid, gilt bands, brass corners and a
    hasp; the sewing box given brass corners and a clasp, with a spool of red thread, a
    pincushion and scissors on its lid; the bath stool a plank seat on two plank legs."""
    M = bpy.data.materials
    lacquer, brass, gilt, wood = M.get("M_red_lacquer"), M.get("M_brass"), M.get("M_gilt_dull"), M.get("M_worn_wood")
    thread, iron = M.get("M_wet_cloth_red") or lacquer, M.get("M_iron")
    chest = obj("yaymey_chest")
    if chest is not None and len(chest.data.vertices) <= 8:
        lo, hi = world_box([chest])
        coll = chest.users_collection[0]
        delete([chest])
        x0, x1, y0, y1, z0, z1 = lo.x, hi.x, lo.y, hi.y, lo.z, hi.z
        lid = z1 - 0.07
        p = [box("yc_plinth", coll, x0 + 0.02, x1 - 0.02, y0 + 0.02, y1 - 0.02, z0, z0 + 0.045, lacquer, edge=0.006),
             box("yc_body", coll, x0 + 0.012, x1 - 0.012, y0 + 0.012, y1 - 0.012, z0 + 0.045, lid - 0.004, lacquer, edge=0.006),
             box("yc_lid", coll, x0, x1, y0, y1, lid, z1 - 0.012, lacquer, edge=0.01),
             box("yc_lid_top", coll, x0 + 0.03, x1 - 0.03, y0 + 0.03, y1 - 0.03, z1 - 0.012, z1, lacquer, edge=0.008)]
        for z in (z0 + 0.06, lid - 0.022):                 # gilt bands round the body
            p.append(box("yc_band", coll, x0 + 0.01, x1 - 0.01, y0 + 0.01, y1 - 0.01, z, z + 0.009, gilt))
        p.append(box("yc_lid_band", coll, x0 - 0.002, x1 + 0.002, y0 - 0.002, y1 + 0.002, lid + 0.02, lid + 0.028, gilt))
        for cx in (x0, x1):                                # brass corner caps on the lid and at the feet
            for cy in (y0, y1):
                sx, sy = (1 if cx == x0 else -1), (1 if cy == y0 else -1)
                p.append(box("yc_cap", coll, min(cx, cx + sx * 0.055) - 0.002, max(cx, cx + sx * 0.055) + 0.002,
                             min(cy, cy + sy * 0.055) - 0.002, max(cy, cy + sy * 0.055) + 0.002, z1 - 0.045, z1 + 0.002, brass, edge=0.003))
                p.append(box("yc_foot_cap", coll, min(cx, cx + sx * 0.06) + sx * 0.02, max(cx, cx + sx * 0.06) + sx * 0.02,
                             min(cy, cy + sy * 0.06) + sy * 0.02, max(cy, cy + sy * 0.06) + sy * 0.02, z0, z0 + 0.05, brass, edge=0.003))
        ym = (y0 + y1) / 2                                 # the front faces the room (+x)
        p.append(box("yc_hasp_plate", coll, x1 - 0.012, x1 - 0.004, ym - 0.04, ym + 0.04, lid - 0.07, lid - 0.01, brass, edge=0.003))
        p.append(box("yc_hasp", coll, x1 + 0.0, x1 + 0.006, ym - 0.012, ym + 0.012, lid - 0.06, lid + 0.03, brass, edge=0.002))
        p.append(box("yc_lock", coll, x1 + 0.006, x1 + 0.022, ym - 0.018, ym + 0.018, lid - 0.1, lid - 0.055, brass, edge=0.004))
        p.append(tube("yc_shackle", coll, [(x1 + 0.014, ym - 0.012, lid - 0.056), (x1 + 0.014, ym - 0.012, lid - 0.035),
                                            (x1 + 0.014, ym, lid - 0.025), (x1 + 0.014, ym + 0.012, lid - 0.035), (x1 + 0.014, ym + 0.012, lid - 0.056)],
                      0.0025, iron or brass, sides=5))
        _joined(p, "yaymey_chest")
    sew = obj("interact_sewing_box")
    body = next((c for c in sew.children if c.type == "MESH"), None) if sew is not None else None
    if body is not None and not any(c.name.startswith("sewing_box_spool") for c in sew.children):
        lo, hi = world_box([body])
        coll = body.users_collection[0]
        x0, x1, y0, y1, z0, z1 = lo.x, hi.x, lo.y, hi.y, lo.z, hi.z
        p = []
        for cx in (x0, x1):
            for cy in (y0, y1):
                sx, sy = (1 if cx == x0 else -1), (1 if cy == y0 else -1)
                p.append(box("sb_cap", coll, min(cx, cx + sx * 0.04) - 0.002, max(cx, cx + sx * 0.04) + 0.002,
                             min(cy, cy + sy * 0.04) - 0.002, max(cy, cy + sy * 0.04) + 0.002, z1 - 0.035, z1 + 0.002, brass, edge=0.002))
        ym = (y0 + y1) / 2
        p.append(box("sb_clasp", coll, x1, x1 + 0.006, ym - 0.018, ym + 0.018, z1 - 0.07, z1 - 0.01, brass, edge=0.002))
        _joined(p, "sewing_box_fittings")
        # A wooden spool of red thread, a pincushion with pins, scissors, on the lid.
        sx, sy = x0 + 0.11, y0 + 0.12
        q = [cylinder("sewing_box_spool_end", coll, sx, sy, z1, z1 + 0.006, 0.019, wood, verts=16),
             cylinder("sewing_box_spool_thread", coll, sx, sy, z1 + 0.006, z1 + 0.044, 0.016, thread, verts=16),
             cylinder("sewing_box_spool_end", coll, sx, sy, z1 + 0.044, z1 + 0.05, 0.019, wood, verts=16)]
        q.append(tube("sewing_box_spool_tail", coll, [(sx + 0.016, sy, z1 + 0.03), (sx + 0.04, sy + 0.01, z1 + 0.002), (sx + 0.09, sy + 0.03, z1 + 0.001)],
                      0.0009, thread, sides=4))
        verts, faces = [], []
        _ball(verts, faces, (x1 - 0.1, y1 - 0.11, z1 + 0.02), 0.032, 12, 8)
        cush = mesh_object("sewing_box_spool_cushion", coll, [(v[0], v[1], z1 + (v[2] - z1) * 0.7) for v in verts], faces, thread, smooth=True)
        q.append(cush)
        for k in range(5):
            a = k * 1.3
            base = Vector((x1 - 0.1 + 0.022 * math.cos(a), y1 - 0.11 + 0.022 * math.sin(a), z1 + 0.034))
            q.append(tube("sewing_box_spool_pin", coll, [tuple(base), tuple(base + Vector((0.01 * math.cos(a), 0.01 * math.sin(a), 0.022)))],
                          0.0007, iron or brass, sides=3))
        cx, cy = (x0 + x1) / 2 + 0.03, y0 + 0.08                 # scissors, open a little
        for sgn in (-1, 1):
            d = Vector((math.cos(0.12 * sgn), math.sin(0.12 * sgn), 0))
            tip = Vector((cx, cy, z1 + 0.003)) + d * 0.09
            q.append(tube("sewing_box_spool_blade", coll, [(cx, cy, z1 + 0.003), tuple(tip)], 0.0028, iron or brass, sides=4, radius_end=0.0008))
            ring_c = Vector((cx, cy, z1 + 0.003)) - d * 0.035 + Vector((0, 0.014 * sgn, 0))
            q.append(tube("sewing_box_spool_ring", coll, [tuple(ring_c + Vector((0.013 * math.cos(t), 0.011 * math.sin(t), 0))) for t in np.linspace(0, math.tau, 13)],
                          0.0022, iron or brass, sides=4))
        groups = {}
        for o in q:
            groups.setdefault(o.active_material.name, []).append(o)
        bits = [_joined(objs, f"sewing_box_spool_{mn}") for mn, objs in groups.items()]
        for o in bits + [obj("sewing_box_fittings")]:
            mw = o.matrix_world.copy()
            o.parent = sew
            o.matrix_world = mw
    stool = obj("bath_stool")
    if stool is not None and len(stool.data.vertices) <= 8:
        lo, hi = world_box([stool])
        coll = stool.users_collection[0]
        delete([stool])
        x0, x1, y0, y1, z0, z1 = lo.x, hi.x, lo.y, hi.y, lo.z, hi.z
        p = [box("bs_seat", coll, x0, x1, y0 + 0.02, y1 - 0.02, z1 - 0.028, z1, wood, edge=0.008)]
        for x in (x0 + 0.03, x1 - 0.055):
            p.append(box("bs_leg", coll, x, x + 0.025, y0 + 0.035, y1 - 0.035, z0, z1 - 0.028, wood, edge=0.004))
        p.append(box("bs_rail", coll, x0 + 0.05, x1 - 0.05, (y0 + y1) / 2 - 0.015, (y0 + y1) / 2 + 0.015, z0 + 0.05, z0 + 0.075, wood, edge=0.003))
        _joined(p, "bath_stool")
    print("[tidy] chest, sewing box and bath stool detailed", flush=True)


def better_trunk(hm):
    """Vuthy's trunk was a plain box: a camphor-wood trunk with a lid that sits proud of
    the body, iron corner caps and bands, side handles and a hasp."""
    old = obj("vuthy_trunk")
    if old is None:
        return
    lo, hi = world_box([old])
    coll = old.users_collection[0]
    delete([old] + named("vuthy_trunk_clasp"))
    wood, iron = hm["cl_trim"], hm["iron"]
    x0, x1, y0, y1, z0, z1 = lo.x, hi.x, lo.y, hi.y, lo.z, hi.z
    lid = z1 - 0.12
    parts = [box("vuthy_trunk_body", coll, x0 + 0.01, x1 - 0.01, y0 + 0.01, y1 - 0.01, z0 + 0.03, lid - 0.004, wood, edge=0.008),
             box("vuthy_trunk_lid", coll, x0, x1, y0, y1, lid, z1, wood, edge=0.014),
             box("vuthy_trunk_plinth", coll, x0 + 0.02, x1 - 0.02, y0 + 0.02, y1 - 0.02, z0, z0 + 0.03, wood)]
    for x in (x0 + 0.1, x1 - 0.1):           # iron bands over the lid and down the front and back
        parts.append(box("vuthy_trunk_band", coll, x - 0.018, x + 0.018, y0 - 0.004, y1 + 0.004, z1 - 0.002, z1 + 0.003, iron))
        for y in (y0 - 0.004, y1 + 0.001):
            parts.append(box("vuthy_trunk_band", coll, x - 0.018, x + 0.018, y, y + 0.003, z0 + 0.04, z1, iron))
    for x in (x0, x1 - 0.06):                 # corner caps
        for y in (y0, y1 - 0.06):
            parts.append(box("vuthy_trunk_cap", coll, x - 0.003, x + 0.063, y - 0.003, y + 0.063, z1 - 0.06, z1 + 0.004, iron, edge=0.004))
    xm = (x0 + x1) / 2
    parts.append(box("vuthy_trunk_hasp", coll, xm - 0.025, xm + 0.025, y0 - 0.01, y0 - 0.002, lid - 0.09, lid + 0.03, iron, edge=0.003))
    for x in (x0 - 0.012, x1 + 0.004):        # side handles
        parts.append(box("vuthy_trunk_handle", coll, x, x + 0.008, (y0 + y1) / 2 - 0.07, (y0 + y1) / 2 + 0.07, z1 - 0.2, z1 - 0.17, iron))
    t = _joined(parts, "vuthy_trunk")
    print("[tidy] Vuthy's trunk made a trunk", t.name, flush=True)


def house_fixes(hm):
    """Vuthy's trunk was the old village's placeholder box in bright lacquer: dark teak
    now. The old store's hatchet and machete hung on pegs that stayed behind in the old
    room: in the new store they floated across the window, so they go with their pegs."""
    trunk = bpy.data.objects.get("vuthy_trunk")
    if trunk is not None:
        trunk.data.materials.clear()
        trunk.data.materials.append(hm["cl_trim"])
    gone = [x for o in bpy.data.objects if re.match(r"^(house_hatchet|house_machete|store_peg)_\d+$", o.name) for x in tree(o)]
    print("[rebuild] store tools out", delete(gone), flush=True)


def house_lights(hc, room_flames, dress_lights):
    """The house lit by its own few flames (turned down Nov 24, 2026, the user: "the whole
    house ... more scary, darkness"): the rooms' candles (0.6 W, the corridor lamp 1.8 W)
    with a flame on each wick, the dressing's lamps (1.4 W), Vuthy's hurricane lamp
    (1.2 W), Sok's desk lamp (1.8 W) and every other flame in the house (0.8 W)."""
    for k, tip in enumerate(room_flames):
        if k > 0:   # the first is the corridor lamp's light, its flame inside the model's globe
            flames_at(hc, [tip], f"house_flame_{k:02d}")
        light_marker(hc, f"house_room_{k:02d}", Vector(tuple(tip)) + Vector((0, 0, 0.03)), 1.8 if k == 0 else 0.6, CANDLE)
    for k, p in enumerate(dress_lights):
        light_marker(hc, f"house_dress_{k}", p, 1.4, LAMP)
    vl.update()
    lamp = bpy.data.objects.get("vuthy_hurricane_lamp")
    lb = world_box(list(lamp.children_recursive)) if lamp else None
    if lb:
        light_marker(hc, "house_vuthy_lamp", (lb[0] + lb[1]) / 2 + Vector((0.12, 0.0, -0.06)), 1.2, LAMP)
    # Sok's study: his desk lamp left burning, the only light in there.
    desk = bpy.data.objects.get("sok_desk")
    if desk is not None:
        db = world_box(tree(desk))
        dx, dy = db[1].x - 0.22, (db[0].y + db[1].y) / 2 + 0.18
        lamp = import_model(hc, "vintage_oil_lamp", (dx, dy, db[1].z), rot_deg=10, name="study_desk_lamp", collide=False)
        vl.update()
        lb = world_box(list(lamp.children_recursive))
        if lb:
            light_marker(hc, "house_study_lamp", ((lb[0].x + lb[1].x) / 2 + 0.1, (lb[0].y + lb[1].y) / 2, lb[0].z + (lb[1].z - lb[0].z) * 0.55),
                         1.8, LAMP)
    # The lamps and candles that came into the house with its furniture. The hall altar's
    # lamp and the veranda's lantern keep their lights' names (Act III's failing lamps).
    named = {"hall_altar_lamp_flame": "hall", "veranda_lantern_flame": "veranda"}
    n = 0
    found = [o for o in bpy.data.objects if o.type == "MESH" and "flame" in o.name and not protected(o) and o.users_collection]
    for o in found:
        if any(c.name.startswith("_") or c.name in ("stilt_house", "funeral_under", "farmstead") for c in o.users_collection):
            continue
        bb = world_box([o])
        if bb is None:
            continue
        p = (bb[0] + bb[1]) / 2
        if -8.5 < p.x < 8.5 and 9.0 < p.y < 35 and p.z > 2.5:
            key = named.get(o.name) or "house_" + re.sub(r"[^a-z0-9]+", "_", o.name.lower()).strip("_")
            light_marker(hc, key, p + Vector((0, 0, 0.04)), 0.8, LAMP)
            n += 1
    print("[rebuild] house lights", len(room_flames), len(dress_lights), n, flush=True)


# ------------------------------------------------------------------ 3-5. builds


def kitchen_house_things(kitchen):
    """The old kitchen's markers (betel leaves, areca nut, the drawer, oil) and what stands
    under them go to the kitchen house, on a low table by its south wall; its other things
    (the hearth, the shelves) go: the kitchen house has its own."""
    x0, x1, y0, y1 = FS.KITCHEN
    keep = [r for r in kitchen if r.name.startswith("interact_")]
    gone = [r for r in kitchen if r not in keep]
    print("[rebuild] kitchen markers", [r.name for r in keep], "gone", len(gone), flush=True)
    delete(gone)
    coll = bpy.data.collections["farmstead"]
    from shrine_craft import Batch
    m = FS.materials()
    b = Batch("fs_kitchen_table")
    tx, ty, h = x0 + 3.6, y0 + 0.7, 0.42
    b.box(m["boards"], (1.4, 0.56, 0.04), (tx, ty, F + h - 0.02))
    for dx in (-0.62, 0.62):
        for dy in (-0.22, 0.22):
            b.box(m["hewn"], (0.06, 0.06, h - 0.04), (tx + dx, ty + dy, F + (h - 0.04) / 2))
    b.build(coll)
    spots = {"interact_betel_leaves": (tx - 0.45, ty, F + h), "interact_areca_nut": (tx + 0.05, ty, F + h),
             "interact_oil_kitchen": (tx + 0.5, ty, F + h), "interact_kitchen_drawer": (x1 - 0.9, y1 - 1.5, F)}
    for r in keep:
        x, y, z = spots.get(r.name, (tx, ty + 0.12, F + h))
        put(r, x, y, z)


COFFIN_BUDGET = 40000   # triangles per coffin piece: the gilt reliefs were ~216 k on the body alone


def decimate_coffin(coll):
    """The coffin's gilt reliefs, collapsed to a budget: from a metre away the carving
    reads the same, and the game draws the coffin from across the yard."""
    for o in list(coll.objects):
        if o.type != "MESH" or not o.name.startswith("coffin_"):
            continue
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        if tris <= COFFIN_BUDGET * 1.2:
            continue
        mod = o.modifiers.new("decimate", "DECIMATE")
        mod.ratio = COFFIN_BUDGET / tris
        mod.use_collapse_triangulate = True
        vl.update()
        me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        o.modifiers.remove(mod)
        old = o.data
        o.data = me
        me.name = old.name
        if old.users == 0:
            bpy.data.meshes.remove(old)
        print("[rebuild] decimated", o.name, tris, "->", sum(len(p.vertices) - 2 for p in me.polygons), flush=True)


def under_house_funeral(props):
    coll = collection("funeral_under")
    rng = np.random.default_rng(21)
    portrait = os.path.join(ROOT, "art-source/textures/ep1/T_ep1_photo_sok_BC.png")
    with Excluded("funeral_under"):
        # (No smoke threads: they are the Cycles previews'; the game makes its own smoke.)
        m, flames, glows, smokes = FU.build(coll, ground, rng, portrait)
        FU.loudspeaker_pole(coll, m, ground, rng, *FU.SPEAKER_POLE)
        # The dread pass the user approved on Nov 24 (Cycles previews of Nov 23): the
        # funeral after three nights. Its own generator, the previews' seed, so it lays
        # out as they did and nothing else moves.
        FU.dread(coll, m, ground, np.random.default_rng(2311))
        # The torn cloths hang to between 0.8 and 1.4 m: Sora bumps them, not walks
        # through them (a body's width round each, up to the joists).
        for o in [o for o in coll.objects if o.name.startswith("fu_dread_rag_")]:
            xs = [(o.matrix_world @ v.co) for v in o.data.vertices]
            x0, x1 = min(p.x for p in xs) - 0.08, max(p.x for p in xs) + 0.08
            y0, y1 = min(p.y for p in xs) - 0.08, max(p.y for p in xs) + 0.08
            collider(o.name, coll, x0, x1, y0, y1, min(p.z for p in xs) - 0.05, FU.JOISTS, surface="dirt")
        # The guttering candle on the earth behind the monks' table, where the previews'
        # watcher stands (preview_v2.py), drawn from its own generator so nothing else moves.
        import offerings_kit as ok
        from shrine_craft import Batch, place
        wrng = np.random.default_rng(2117)
        wb = Batch("fu_watcher_candle")
        wg = ground(-1.72, 17.3)
        ok.candle_dish(wb, m, place(-1.72, 17.3, wg), wrng, radius=0.04, melt=0.9)
        flames.append(ok.candle(wb, m, place(-1.72, 17.3, wg + 0.006), wrng, height=0.035, radius=0.011, melt=1.0))
        wb.build(coll)
        decimate_coffin(coll)
    for o in coll.objects:
        if o.name.startswith("coffin_body"):
            o["hollow"] = True          # CorpseModels.ts opens the authored coffin, lined inside
    # A flame on every lit wick, and the previews' lights: every candle 0.6 W, the fire pot
    # 9 W. The previews' 10 W bulb light sat inside the bulb's own solid glass, so Cycles
    # blocked it and only the glowing glass lit the funeral: matched by eye in the game
    # (Nov 24, 2026), that is about 0.4 W. At 10 W the game's shadowless light lit the
    # canopy flags, the wreath and the coffin's lacquer twice as bright as the previews.
    flames_at(coll, flames, "fu_flame")
    for k, tip in enumerate(flames):
        light_marker(coll, f"fu_candle_{k:03d}", Vector(tuple(tip)) + Vector((0, 0, 0.03)), 0.6, CANDLE)
    light_marker(coll, "fu_fire", glows[0], 9.0, (1.0, 0.45, 0.12))
    light_marker(coll, "fu_bulb", glows[1], 0.4, (1.0, 0.72, 0.45))
    print("[rebuild] funeral flames", len(flames), flush=True)
    # The game's portrait: the wreath's photograph, under a portrait_sok node with the
    # wreath's frame counted as its authored surround (DeskModels.ts animates the eyes).
    photo = bpy.data.objects["fu_portrait_photo"]
    frame = bpy.data.objects["fu_portrait_frame"]
    vl.update()
    pb = world_box([photo])
    holder = bpy.data.objects.new("portrait_sok", None)
    coll.objects.link(holder)
    holder.location = (pb[0] + pb[1]) / 2
    # The holder's matrix must be current before its children are set by world matrix,
    # or they keep their world position as an offset from it (the photo hung twice as
    # far out, in the back block).
    vl.update()
    for o, name in ((photo, "interact_portrait"), (frame, "portrait_floral_surround_wreath")):
        mw = o.matrix_world.copy()
        o.name = name
        o.parent = holder
        o.matrix_world = mw
    for k, v in props.items():
        photo[k] = v
    # The vigil's markers, in their new places round the coffin.
    cx, cy = FU.COFFIN
    tx, ty = FU.TABLE
    top = world_box([bpy.data.objects["fu_table_top"]])[1].z
    g = ground
    spots = {
        "interact_incense_0": (cx - 1.25, cy - 0.75, g(cx - 1.25, cy - 0.75) + 0.1),
        "interact_incense_1": (cx + 1.25, cy - 0.75, g(cx + 1.25, cy - 0.75) + 0.1),
        "interact_incense_2": (cx + 1.25, cy + 0.75, g(cx + 1.25, cy + 0.75) + 0.1),
        "interact_incense_3": (cx - 1.25, cy + 0.75, g(cx - 1.25, cy + 0.75) + 0.1),
        "marker_main_burner": (tx - 0.25, ty + 0.1, top + 0.07),
        "interact_thread": (FU.AXIS, FU.AREA[3] - 0.3, FU.JOISTS - 0.25),
        "marker_flies_tent": (cx + 0.6, cy, g(cx, cy) + 0.9),
        "marker_vuthy": (cx + 1.9, cy - 1.2, g(cx + 1.9, cy - 1.2)),
        "marker_yay_mey": (FU.MONKS[0] + 1.2, FU.MONKS[1] - 1.5, g(FU.MONKS[0] + 1.2, FU.MONKS[1] - 1.5)),
        "interact_oil_tent": (FU.FIRE[0] - 0.7, FU.FIRE[1] - 0.4, g(FU.FIRE[0] - 0.7, FU.FIRE[1] - 0.4)),
    }
    for name, (x, y, z) in spots.items():
        o = obj(name)
        if o is None:
            continue
        # Their hall burners and lamps go (the funeral under the house has its own).
        if name.startswith(("interact_incense_", "marker_main_burner", "interact_thread")):
            delete(list(o.children))
        if name == "interact_oil_tent":
            put(o, x, y, z)
        else:
            o.matrix_world = Matrix.Translation(Vector((x, y, z))) @ Matrix.Rotation(o.matrix_world.to_euler().z, 4, "Z")
    return flames, glows


def clear_under_house(keep):
    """Whatever stood on the ground under the front block (the old hunt's crates, the
    bathing corner's jars) goes for the funeral, all but the jars (they move)."""
    x0, x1, y0, y1 = FU.AREA
    struct = re.compile(r"(pillar|post|stilt|ground|beam|joist|stair|step|plinth|footing|floor|sill|brace|ladder|wall_)", re.I)
    gone = []
    for r in roots():
        if r.name in keep or r.name.startswith(("interact_jar_", "col_jar_", "spawn_", "marker_")) or struct.search(r.name):
            continue
        if any(c.name in ("funeral_under", "stilt_house", "farmstead") for c in r.users_collection):
            continue
        bb = world_box(tree(r))
        if bb is None:
            continue
        c = (bb[0] + bb[1]) / 2
        # On the ground, or hung from the joists (the stored fish traps, the yoke).
        if x0 - 0.3 < c.x < x1 + 0.3 and y0 - 0.5 < c.y < y1 + 0.5 and (bb[1].z < 2.3 or (bb[0].z > 0.3 and bb[1].z < 2.45)):
            gone.append(r)
    print("[rebuild] under-house ground cleared", delete(gone), flush=True)


def jars():
    """Four jars among the stilts under the back block, two in the rice barn (Act III)."""
    bx0, bx1, by0, by1 = FS.BARN
    spots = {"interact_jar_J1": (-6.2, 24.0, None), "interact_jar_J2": (-2.6, 28.2, None),
             "interact_jar_J3": (2.4, 24.6, None), "interact_jar_J4": (6.1, 31.8, None),
             "interact_jar_J5": (bx1 - 0.7, by0 + 1.5, 1.2), "interact_jar_J6": (bx1 - 0.65, by1 - 0.6, 1.2)}
    for name, (x, y, z) in spots.items():
        o = obj(name)
        if o is not None:
            before = o.matrix_world.copy()
            put(o, x, y, ground(x, y) if z is None else z)
            # Its collider goes with it (left behind, each stood where the jar had been).
            col = bpy.data.objects.get("col_jar_" + name.rsplit("_", 1)[1])
            if col is not None:
                col.matrix_world = o.matrix_world @ before.inverted() @ col.matrix_world


def tool_shed_things():
    """The old shed's locked door, its padlock and collider hang in the tool shed's
    doorway; the oil, the land deed and Kanha's photograph go in; the old shed goes."""
    x0, x1, y0, y1 = FS.TOOL_SHED
    g = min(ground(x, y) for x in (x0, x1) for y in (y0, y1))
    coll = bpy.data.collections["farmstead"]
    # Each thing on the ground under it: the shed stands on a slope, and the lowest corner's
    # height left the far side's things in the earth (the float audit, Nov 22).
    crate = import_model(coll, "wooden_crate_01", (x0 + 0.55, y0 + 0.75, ground(x0 + 0.55, y0 + 0.75)), rot_deg=8,
                         name="fs_toolshed_crate")
    vl.update()
    cb = world_box(list(crate.children_recursive) or [crate])
    top = cb[1].z if cb else g + 0.45
    spots = {"interact_land_deed": (x0 + 0.45, y0 + 0.7, top), "interact_kanha_photo": (x0 + 0.7, y0 + 0.85, top),
             "interact_oil_shed_1": (x0 + 0.35, y1 - 0.45, ground(x0 + 0.35, y1 - 0.45)),
             "interact_oil_shed_2": (x0 + 0.6, y1 - 0.4, ground(x0 + 0.6, y1 - 0.4))}
    for name, (x, y, z) in spots.items():
        o = obj(name)
        if o is not None:
            put(o, x, y, z)
    # The door: the old leaf turned to face south, in the opening (x0 + 0.8 .. x0 + 1.7).
    door = obj("interact_shed_door")
    if door is not None:
        vl.update()
        lo, hi = world_box(tree(door))
        c = (lo + hi) / 2
        M = Matrix.Translation(Vector((x0 + 1.25 - c.x, y0 - c.y, ground(x0 + 1.25, y0) + 0.02 - lo.z))) @ turn_about(Vector((c.x, c.y, 0)), 90)
        group = [door] + [bpy.data.objects[n] for n in ("col_shed_door", "shed_padlock") if n in bpy.data.objects]
        for o in group:
            if o.parent is None or o.parent not in group:
                o.matrix_world = M @ o.matrix_world
    vl.update()
    # The old shed (east of the house, x 8.6 .. 12.2) goes with whatever is left in it.
    keep = {"interact_shed_door", "col_shed_door", "shed_padlock"}
    gone = []
    for r in roots():
        if r.name in keep or any(c.name in ("funeral_under", "stilt_house", "farmstead", "farm_cover") for c in r.users_collection):
            continue
        bb = world_box(tree(r))
        if bb is None:
            continue
        c = (bb[0] + bb[1]) / 2
        if 8.6 < c.x < 12.2 and 12.0 < c.y < 17.2 and bb[1].z < 4.5:
            gone.append(r)
    print("[rebuild] old shed out", [r.name for r in gone][:20], delete(gone), flush=True)


def yard_cart():
    """The old ox cart east of the house, turned to stand with its shafts north along the
    yard fence instead of through it."""
    cart = bpy.data.objects.get("yard_cart")
    if cart is None:
        return
    c = cart.matrix_world.translation.copy()
    # Turned, and 0.45 m west so its shaft tips stay inside the fence at x 12.5.
    M = Matrix.Translation((-0.45, 0.0, 0.0)) @ turn_about(Vector((c.x, c.y, 0)), 62.0)
    for o in [cart] + [o for o in bpy.data.objects if o.name.startswith("col_yard_cart") and o.parent is None]:
        o.matrix_world = M @ o.matrix_world
    vl.update()
    bb = world_box(tree(cart))
    print("[rebuild] yard cart turned", [round(v, 2) for v in bb[0]], [round(v, 2) for v in bb[1]], flush=True)


def plants_out():
    """The village's own plants where the farm's buildings, fields and paths now are."""
    plant = re.compile(r"(banana|palm|tree|fern|shrub|weed|grass|bamboo|sugar|forest|leaf|litter|root|stump|rock|bark_debris|"
                       r"dry_branches|nettle|periwinkle|calathea|anthurium|pachira|moss|dead_)", re.I)
    feet = [(-10.0, 10.0, 7.5, 37.0), (-30.0, -18.0, 13.5, 25.0), (-42.5, -34.5, 34.0, 41.0), (19.5, 31.0, 18.0, 27.5),
            (30.5, 37.5, 34.0, 42.0), (-14.5, -3.5, 46.5, 56.5), (-30.0, -20.0, 43.5, 53.5), (24.5, 33.5, 1.0, 9.0),
            (30.0, 35.0, 27.0, 32.0), (-27.5, -23.5, 7.0, 11.0), (-21.0, -7.5, 17.8, 20.5)] + \
           [(x0 - 0.6, x1 + 0.6, y0 - 0.6, y1 + 0.6) for x0, x1, y0, y1 in FS.FIELDS]
    gone = []
    for r in roots():
        if not plant.search(r.name) or r.type not in ("MESH", "EMPTY") or r.name.startswith(("tpl_", "col_")):
            continue
        if any(c.name in ("funeral_under", "stilt_house", "farmstead", "farm_cover") for c in r.users_collection):
            continue
        bb = world_box(tree(r))
        if bb is None:
            continue
        c = (bb[0] + bb[1]) / 2
        # The farm's footprints, the cart track's winding way (and its verges), the yard fence's line.
        on_track = FS.track_distance(c.x, c.y) < (2.3 if bb[1].z < 1.5 else 3.2)
        on_fence = any(FS._seg_distance(c.x, c.y, *a, *b) < 0.6 for _, a, b in FS._yard_runs()) and bb[1].z < 3.0
        if any(a <= c.x <= b and d <= c.y <= e for a, b, d, e in feet) or on_track or on_fence \
                or (FS.path_distance(c.x, c.y) < 0.3 and bb[1].z < 1.5):
            gone.append(r)
    print("[rebuild] plants out", delete(gone), flush=True)


NOT_SUPPORT = re.compile(r"^(col_|ladder_|marker_|spawn_|patrol_|light_|hide_|tpl_|nav_|trigger_|occ_|interact_)")


class Supports:
    """What a thing can be set down on: every exported mesh but colliders and markers,
    found by footprint and ray-cast in its own tree, so neither the thing itself nor a
    collider lying exactly on a floor can hide the floor under it."""
    CELL = 4.0

    def __init__(self):
        from mathutils.bvhtree import BVHTree
        self.BVHTree = BVHTree
        vl.update()
        self.deps = bpy.context.evaluated_depsgraph_get()
        live = {o.original.name for o in self.deps.objects}
        skip = {c.name for c in bpy.data.collections if c.name.startswith("_") or c.name == "nature_templates"}
        self.box, self.bvh, self.grid = {}, {}, {}
        for m in bpy.data.objects:
            if (m.type == "MESH" and len(m.data.vertices) and m.name in live and not NOT_SUPPORT.match(m.name)
                    and m.users_collection and not any(c.name in skip for c in m.users_collection)):
                self.add(m)

    def add(self, m):
        pts = [m.matrix_world @ Vector(c) for c in m.bound_box]
        lo, hi = Vector(map(min, *pts)), Vector(map(max, *pts))
        self.box[m.name] = (lo, hi)
        self.bvh.pop(m.name, None)
        for i in range(int(lo.x // self.CELL), int(hi.x // self.CELL) + 1):
            for j in range(int(lo.y // self.CELL), int(hi.y // self.CELL) + 1):
                cell = self.grid.setdefault((i, j), [])
                if m.name not in cell:
                    cell.append(m.name)

    def moved(self, objs):
        for o in objs:
            if o.name in self.box:
                self.add(o)

    def _cast(self, name, origin, reach):
        t = self.bvh.get(name)
        if t is None:
            m = bpy.data.objects[name]
            t = self.bvh[name] = (self.BVHTree.FromObject(m.evaluated_get(self.deps), self.deps), m.matrix_world.copy(),
                                  m.matrix_world.inverted())
        tree_, mw, inv = t
        loc, *_ = tree_.ray_cast(inv @ origin, (inv.to_3x3() @ Vector((0, 0, -1))).normalized())
        if loc is None:
            return None
        z = (mw @ loc).z
        return z if origin.z - reach <= z <= origin.z + 1e-6 else None

    def top_under(self, objs, lift=0.05, n=9):
        """The highest surface under the footprint of `objs` (and who it is), from `lift`
        over their lowest point down to 3 m below it."""
        meshes = [o for o in objs if o.type == "MESH" and len(o.data.vertices)]
        bb = world_box(meshes)
        if bb is None:
            return None, None
        lo, hi = bb
        own = {o.name for o in objs}
        cands = set()
        for i in range(int(lo.x // self.CELL), int(hi.x // self.CELL) + 1):
            for j in range(int(lo.y // self.CELL), int(hi.y // self.CELL) + 1):
                for name in self.grid.get((i, j), ()):
                    if name in own:
                        continue
                    a, b = self.box[name]
                    if a.x <= hi.x and b.x >= lo.x and a.y <= hi.y and b.y >= lo.y and a.z <= lo.z + lift and b.z >= lo.z - 3.0:
                        cands.add(name)
        best, who = None, None
        ix, iy = min(0.02, (hi.x - lo.x) * 0.1), min(0.02, (hi.y - lo.y) * 0.1)
        for a in range(n):
            for b in range(n):
                p = Vector((lo.x + ix + (hi.x - lo.x - 2 * ix) * a / (n - 1), lo.y + iy + (hi.y - lo.y - 2 * iy) * b / (n - 1),
                            lo.z + lift))
                for name in cands:
                    z = self._cast(name, p, 3.0 + lift)
                    if z is not None and (best is None or z > best):
                        best, who = z, name
        return best, who

    def rest(self, root, sink=0.004, lift=0.05, most=1.0):
        """Sets `root` (and what hangs under it) down on the highest thing under it, or
        lifts it out of one it has sunk into by less than `lift`."""
        objs = tree(root)
        bb = world_box([o for o in objs if o.type == "MESH" and len(o.data.vertices)])
        top, who = self.top_under(objs, lift)
        if bb is None or top is None:
            return None
        dz = top - sink - bb[0].z
        if abs(dz) < 0.006 or abs(dz) > most:
            return None
        root.matrix_world = Matrix.Translation((0, 0, dz)) @ root.matrix_world
        vl.update()
        self.moved(objs)
        return round(dz, 3), who


ATTIC_KEEP = re.compile(r"^(attic_plank|attic_joist|attic_hatch_frame|attic_store_board|attic_form|dress_attic_hp_pillow_gingham"
                        r"|dress_attic_hp_cotton)")


def attic_storage(hc, sup):
    """What is set down in the attic off the plank paths stands on a loose board laid
    across two or three joists, as things are stored up there; without one it hung in
    the air over the ceiling between the joists."""
    jz = SH.ZW + 0.14
    x0 = SH.H["x0"] + 0.3
    planks = bpy.data.materials.get("M_sh_attic_planks")
    things = []
    for r in roots():
        if not r.name.startswith(("attic_", "dress_attic_")) or ATTIC_KEEP.match(r.name):
            continue
        bb = world_box(tree(r))
        if bb is None or not (jz - 0.1 < bb[0].z < jz + 0.6):
            continue
        things.append((bb[0].z, r))
    boards = []
    for _z, r in sorted(things, key=lambda t: t[0]):
        top, who = sup.top_under(tree(r))
        if top is not None and top >= jz + 0.015:
            continue   # on the planks, or on something stored there
        lo, hi = world_box(tree(r))
        bx0 = x0 + 0.6 * math.floor((lo.x - 0.05 - x0) / 0.6) - 0.06
        bx1 = x0 + 0.6 * math.ceil((hi.x + 0.05 - x0) / 0.6) + 0.06
        hx0, hx1, hy0, hy1 = SH.HATCH
        if lo.y - 0.04 < hy1 + 0.05 and hi.y + 0.04 > hy0 - 0.05:   # never over the hatch
            if lo.x >= hx1:
                bx0 = max(bx0, hx1 + 0.05)
            elif hi.x <= hx0:
                bx1 = min(bx1, hx0 - 0.05)
        b = box(f"attic_store_board_{len(boards)}", hc, bx0, bx1, lo.y - 0.04, hi.y + 0.04, jz, jz + 0.025, planks)
        boards.append(b)
    vl.update()
    for b in boards:
        sup.add(b)
    out = []
    for _z, r in sorted(things, key=lambda t: t[0]):
        d = sup.rest(r, sink=0.002, lift=0.06, most=0.6)
        if d:
            out.append((r.name, *d))
    print("[rebuild] attic boards", len(boards), "rested", out, flush=True)


# Things that were set down on a surface gone with the old house (or never there):
# the enamel pot left in mid-air on the west gallery, a rice sack over the bin.
REST = ("house_pot_enamel_01_4", "house_rice_sack_3")
PLANTS = re.compile(r"^(prop_shrub_|prop_grass_|shrub_|fern_|grass_|weed_plant|nettle_plant|periwinkle|calathea|anthurium|"
                    r"bark_debris|dry_branches|leaf_litter|moss_)")


def set_down(sup):
    out = []
    for name in REST:
        o = bpy.data.objects.get(name)
        d = o and sup.rest(o)
        if d:
            out.append((name, *d))
    # Small plants and litter left hovering over a dip (they stand on the ground: the game
    # only snaps the trees and big plants).
    n = 0
    for r in roots():
        if not PLANTS.match(r.name):
            continue
        bb = world_box(tree(r))
        if bb is None or max(bb[1].x - bb[0].x, bb[1].y - bb[0].y) > 2.5 or bb[0].z > 1.0:
            continue
        top, who = sup.top_under(tree(r), lift=0.05, n=5)
        if top is not None and 0.03 < bb[0].z - top < 0.5:
            r.matrix_world = Matrix.Translation((0, 0, top - 0.02 - bb[0].z)) @ r.matrix_world
            n += 1
    print("[rebuild] set down", out, "plants", n, flush=True)


def bath_krama(hc, m):
    """The bathing corner's krama hung over the old corner's bamboo screen, which went
    with the old house: it hangs from a peg rail on the corner's wall instead."""
    old = bpy.data.objects.get("bath_krama")
    if old is None:
        return
    mat = old.active_material
    delete([old])
    import house_props as HP
    m = dict(m)
    m["bath_krama"] = mat
    HP.peg_rail(hc, m, "bath_pegs", 5.55, 6.35, 30.63, F + 1.58, 1, np.random.default_rng(2207), hang=((0, "bath_krama", 0.55),))


def hang_under(name, dy):
    """Moves a hung thing `dy` along y and up or down until its top meets what is over it."""
    o = bpy.data.objects.get(name)
    if o is None:
        return
    o.matrix_world = Matrix.Translation((0, dy, 0)) @ o.matrix_world
    vl.update()
    lo, hi = world_box(tree(o))
    deps = bpy.context.evaluated_depsgraph_get()
    own = set(tree(o))
    p = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, hi.z - 0.1))
    for _ in range(8):
        hit, loc, _n, _i, ob, _m = sc.ray_cast(deps, p, Vector((0, 0, 1)), distance=3.0)
        if not hit:
            print("[rebuild] nothing over", name, flush=True)
            return
        if ob.original in own or NOT_SUPPORT.match(ob.original.name):
            p = loc + Vector((0, 0, 0.001))
            continue
        o.matrix_world = Matrix.Translation((0, 0, loc.z + 0.005 - hi.z)) @ o.matrix_world
        print("[rebuild] hung", name, "under", ob.original.name, round(loc.z + 0.005 - hi.z, 3), flush=True)
        return


BIG_PLANT = re.compile(r"^(fs_grove_banana_clump|fs_grove_sugar_palm|banana_|palm_)")


def plants_off_buildings():
    """No banana or palm leaves through a wall: a clump whose crown reaches into a
    building (the rice barn's east wall had three in its loft) goes."""
    # The farm's buildings (the house stands on stilts over its plants, its walls 2.5 m up).
    rooms = [FS.BARN, FS.KITCHEN, FS.SERVANTS, FS.TOOL_SHED]
    gone = []
    for r in roots():
        if not BIG_PLANT.match(r.name):
            continue
        bb = world_box(tree(r))
        if bb is None:
            continue
        lo, hi = bb
        for x0, x1, y0, y1 in rooms:
            ox = min(hi.x, x1) - max(lo.x, x0)
            oy = min(hi.y, y1) - max(lo.y, y0)
            if ox > 0.4 and oy > 0.4 and hi.z > 1.6:
                gone.append(r)
                break
    print("[rebuild] plants out of buildings", [r.name for r in gone], delete(gone), flush=True)


def spawns():
    s = obj("spawn_under_house")
    if s:
        s.location = (FU.AXIS, FU.AREA[2] - 1.2, ground(FU.AXIS, FU.AREA[2] - 1.2))
    # The rain off the back block's eave (EaveDrips.ts): its north edge now.
    for name in ("marker_eave_3_a", "marker_eave_3_b"):
        o = obj(name)
        if o:
            o.location.y = SH.B["y1"] + 0.9


def house_climbing(hc):
    """What the player climbs in the house: the rear stairs and the kept front stairs as
    ramps, the trapdoor's and the attic's ladders."""
    sx0, sx1, sy0, sy1 = SH.STAIR_HOLE
    sx = (sx0 + sx1) / 2
    FS.ramp_collider(hc, "rear_stairs", (sx, sy0 - 0.35, ground(sx, sy0 - 0.35)), (sx, sy1, F), (sx1 - sx0 - 0.08) / 2)
    st = bpy.data.objects.get("stairs_front_detailed")
    if st is not None:
        vl.update()
        pts = [st.matrix_world @ v.co for v in st.data.vertices] if st.type == "MESH" else []
        if pts:
            lo_x, hi_x = min(p.x for p in pts), max(p.x for p in pts)
            lo_y, hi_y = min(p.y for p in pts), max(p.y for p in pts)
            along_x = hi_x - lo_x >= hi_y - lo_y
            a0, a1 = (lo_x, hi_x) if along_x else (lo_y, hi_y)
            key = (lambda p: p.x) if along_x else (lambda p: p.y)
            near0 = [p.z for p in pts if key(p) < a0 + 0.3]
            near1 = [p.z for p in pts if key(p) > a1 - 0.3]
            low_end, high_end = (a0, a1) if sum(near0) / len(near0) < sum(near1) / len(near1) else (a1, a0)
            mid = (lo_y + hi_y) / 2 if along_x else (lo_x + hi_x) / 2
            half = ((hi_y - lo_y) if along_x else (hi_x - lo_x)) / 2 - 0.05
            lo_pt = (low_end, mid) if along_x else (mid, low_end)
            hi_pt = (high_end, mid) if along_x else (mid, high_end)
            FS.ramp_collider(hc, "front_stairs", (*lo_pt, ground(*lo_pt)), (*hi_pt, F), half)
            print("[rebuild] front stairs ramp", [round(v, 2) for v in lo_pt], "->", [round(v, 2) for v in hi_pt], flush=True)
    hx0, hx1, hy0, hy1 = SH.TRAP
    tx = (hx0 + hx1) / 2
    FS.ladder_volume(hc, "trapdoor", (tx, hy0 + 0.25, ground(tx, hy0 + 0.25)), (tx, hy1 - 0.05, F))
    ax0, ax1, ay0, ay1 = SH.HATCH
    FS.ladder_volume(hc, "attic", ((ax0 + ax1) / 2, ay1 + 0.55, F), ((ax0 + ax1) / 2, (ay0 + ay1) / 2, SH.ZW + 0.15))


def budget_protos():
    """Cuts the Poly Haven plants down to their budgets (village_nature.BUDGET) so every
    copy in the farm shares the light mesh. village_nature.decimate reads the evaluated
    mesh, which an object hidden in _protos doesn't have: this decimates a stand-in in a
    visible collection and remaps the prototype's users to the result."""
    protos = bpy.data.collections.get("_protos")
    if protos is None:
        return
    tmp = bpy.data.collections.new("_budget_tmp")
    sc.collection.children.link(tmp)
    done = 0
    for o in list(protos.objects):
        if o.type != "MESH":
            continue
        key = next((k for k in VN.BUDGET if o.name.startswith(k)), None)
        if key is None:
            continue
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        budget = VN.BUDGET[key]
        if tris <= budget * 1.5:
            continue
        stand = bpy.data.objects.new("_budget_stand", o.data)
        tmp.objects.link(stand)
        mod = stand.modifiers.new("decimate", "DECIMATE")
        mod.ratio = max(0.002, budget / tris)
        mod.use_collapse_triangulate = True
        vl.update()
        me = bpy.data.meshes.new_from_object(stand.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        bpy.data.objects.remove(stand, do_unlink=True)
        old = o.data
        old.user_remap(me)
        me.name = old.name + "_budget"
        done += 1
    bpy.data.collections.remove(tmp)
    print("[rebuild] plants cut to budget", done, flush=True)


# ------------------------------------------------------------------ main


def main():
    # The house's surfaces, read off the old shell before it goes.
    hm = SH.existing_materials()
    take_out()
    VN.poly_haven("bark_debris_01")      # the litter's scans in _protos before they are cut
    for model in ("shrub_02", "shrub_03", "shrub_04", "weed_plant_02", "nettle_plant", "fern_02", "calathea_orbifolia_01",
                  "periwinkle_plant", "dry_branches_medium_01"):
        VN.poly_haven(model)
    budget_protos()
    props = funeral_out()
    shell_out()

    # The new shell.
    import house_dressing as HD
    import house_new_rooms as HN
    import house_props as HP
    hc = collection("stilt_house")
    with Excluded("stilt_house"):
        SH.build(hc, hm, ground=ground)
    print("[rebuild] house objects", len(hc.objects), flush=True)
    house_climbing(hc)

    # The old rooms' things into the new rooms.
    moved, kitchen, dining, bundles = furnish_moves(skip=set(FUNERAL_MARKERS) | {"interact_door_sok", "interact_door_yaymey",
                                                                                 "col_door_sok", "door_sok_padlock"})
    print("[rebuild] moved", len(moved), "kitchen", len(kitchen), "dining (gone)", delete(dining), flush=True)
    keep_clear(bundles)
    doors(hc)
    for o in bpy.data.objects:
        if re.match(r"^(bath_(jar|dipper|dipper_handle|krama|stool|ash_pot|slat|sleeper))", o.name) and o.parent is None:
            # Into the back corner east of the washing wall, clear of the store room's wall
            # (at 11.1 the first slats ran under it).
            o.matrix_world = Matrix.Translation((1.75, 11.6, F)) @ o.matrix_world
    print("[rebuild] old dressing out", delete(o for o in bpy.data.objects if DRESS_OUT.match(o.name) and not protected(o)), flush=True)

    # The new rooms' things.
    vl.update()
    bed = next((o for o in bpy.data.objects if o.name.startswith("house_old_bed_frame")), None)
    bb = world_box(tree(bed)) if bed else None
    if bb:
        bx, by = (bb[0].x + bb[1].x) / 2, (bb[0].y + bb[1].y) / 2
        hit, loc, *_ = sc.ray_cast(bpy.context.evaluated_depsgraph_get(), Vector((bx, by, F + 0.95)), Vector((0, 0, -1)))
        kanha_bed = (bx, by, loc.z if hit else F + 0.5)
    else:
        kanha_bed = (6.6, 24.9, F + 0.5)
    m2 = HP.materials(HN.materials(hm))
    m2["paper"] = m2["ledger_page"]
    for key, name in (("rope", "M_rope"), ("mat", "M_reed_mat"), ("cushion", "M_ep1_house_cushion")):
        if bpy.data.materials.get(name):
            m2[key] = bpy.data.materials[name]
    with Excluded("stilt_house"):
        room_flames = HN.furnish(hc, m2, np.random.default_rng(77), kanha_bed)
        HD.furnish(hc, m2, np.random.default_rng(78), kanha_bed)
    hook = bpy.data.objects.get("vuthy_lantern_hook")
    if hook:
        hb = world_box(tree(hook))
        lamp = import_model(hc, "Lantern_01", ((hb[0].x + hb[1].x) / 2, (hb[0].y + hb[1].y) / 2, hb[0].z - 0.42), rot_deg=25,
                            name="vuthy_hurricane_lamp", collide=False)
        vl.update()
        lb = world_box(list(lamp.children_recursive))
        if lb:
            lamp.location.z += hb[0].z - 0.02 - lb[1].z
    house_fixes(hm)
    tidy_house(hm)
    # The user's review of Nov 24 (five screenshots): the floating lamp, the board in the
    # bedroom, the store's shelves, the tea table, the bathroom and the altar (house_refine.py).
    import house_refine as HR
    room_flames = list(room_flames) + HR.refine(hc, m2, np.random.default_rng(2411))
    house_lights(hc, room_flames, HD.LIGHTS)
    bath_krama(hc, m2)
    print("[rebuild] rooms dressed", len(hc.objects), flush=True)

    # The funeral under the house.
    clear_under_house(keep=set(FUNERAL_MARKERS))
    under_house_funeral(props)

    # The farmstead.
    fc = collection("farmstead")
    with Excluded("farmstead"):
        kitchen_glow = FS.build(fc, ground, np.random.default_rng(1932), VN.flora(), game=True)
        FS.cart_track(fc, ground)
    print("[rebuild] farmstead objects", len(fc.objects), flush=True)
    # The kitchen house's hearth, 18 W in the preview (farm_preview.py). Named for the old
    # kitchen's light, which Act III's failing lamps dim (data/desk.ts).
    for k, p in enumerate(kitchen_glow or []):
        light_marker(fc, "kitchen" if k == 0 else f"kitchen_{k}", p, 18.0, (1.0, 0.42, 0.12))
    kitchen_house_things(kitchen)
    tool_shed_things()
    jars()
    plants_out()
    spawns()
    # The old ox cart's prop post, standing alone 4 m from its cart in front of the barn gate.
    print("[rebuild] stray post out", delete([o for o in (bpy.data.objects.get("yard_cart_04"),) if o]), flush=True)
    yard_cart()
    # The user's environment pass (Nov 24): paddies over the south half, palms, big trees
    # and bananas, the yard before the house (village_fields.py), from its own generator.
    import village_fields as VF
    with Excluded("farmstead", "_protos"):
        VF.build(fc, ground, np.random.default_rng(2411), game=True)
    # The user's second review of Nov 24 (ten screenshots): the house's offerings, Sok's
    # photograph, the washing room, the bathroom and the funeral (house_review.py); the
    # weeds out, the wells, the funeral's front, the shrines, the rice and more banyans
    # (village_review.py). Each its own generator; nothing before them moves.
    import house_review as HV
    import village_review as VR
    HV.review(hc, HR.materials(m2), ground)
    VR.review(fc, ground)
    # The user's third review (Nov 25, four screenshots): the certificate behind the hall's
    # post down, a real hanging lamp where Kanha's knotted net read as a paper lamp, the
    # hall lamp on a real chain (house_polish.py).
    import house_polish as HPo
    HPo.polish(hc, HR.materials(m2))
    # Nothing left hanging in the air: the old house's stored trap that hung past the
    # veranda's edge goes under its floor; what stood on things that are gone is set down.
    hang_under("house_decay_stored_trap_2", 0.8)
    plants_off_buildings()
    sup = Supports()
    attic_storage(hc, sup)
    set_down(sup)
    # Last, when everything stands where it will: each open door leaf folded back against
    # its wall where nothing else is.
    SH.fold_clear()
    # Then the webs, into corners nothing else stands in (cobwebs.refit, Nov 25).
    import cobwebs as CW
    CW.refit()
    # The village road outside the gate (the user, Nov 25, 2026: "road along with the shop
    # and shop's poster for each shop just like driving scene"): its own collection and
    # generator, built last so nothing in the farm moves for it (village_road.py).
    import village_road as VRd
    VRd.build(collection("village_road"), ground)
    for coll in (hc, fc, bpy.data.collections["funeral_under"]):
        for o in coll.objects:
            if o.name.startswith("col_"):
                o.display_type = "WIRE"
    bpy.ops.wm.save_mainfile()
    print("[rebuild] saved", bpy.data.filepath, flush=True)


main()
