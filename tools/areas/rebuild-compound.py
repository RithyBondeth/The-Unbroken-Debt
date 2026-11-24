"""Rebuilds Episode 1's village as the tight compound (November 20, 2026, approved from
the Cycles previews): patches art-source/blender/ep1/ep1_area_village.blend in place.

    blender -b art-source/blender/ep1/ep1_area_village.blend -P tools/areas/rebuild-compound.py

1. Takes out everything past the outer fence (the far paddies, the west yard, the east
   pond, the back garden, the road and its palms), the sugar palms and bamboo left
   inside, the old yard fence (rebuilt), litter and weeds in the lane and the yard.
2. Builds the compound (tools/areas/compound.py): the outer fence and its gate, the
   lane's fences, the house's fence, colliders along them, the tree wall outside, the
   lane's and the yard's mud with standing water, grass at the fences' feet, the bund
   through the rice to the Preah Phum.
3. Moves the player's spawn to the road outside the gate, and the pond's spirit into
   the flooded rice beside the lane (the east pond is gone).
4. Rebuilds the funeral in the hall (funeral_shroud.py, funeral_offerings.py): the
   gilt urns, florist's bouquets, flower frame and hanging lamps out; the shroud, the
   offerings, the monks' seat, the vigil's four clay incense burners; the portrait at
   a real photograph's size.
5. Settles everything that floats (compound.settle, tools/areas/ground_audit.py).

Re-running it on a rebuilt file is safe: the compound's own collections are cleared
first and the removals find nothing more to remove.
"""
import math
import os
import re
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import compound as C  # noqa: E402
import funeral_offerings as FO  # noqa: E402
import funeral_shroud as FS  # noqa: E402
import village_expansion as VE  # noqa: E402
import village_nature as VN  # noqa: E402

COLL = "compound"
HALL = "compound_hall"


def collection(name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    for obj in list(coll.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    return coll


def remove(objs):
    n = 0
    for obj in list(objs):
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
            n += 1
    return n


def collider(coll, name, x0, x1, y0, y1, z0=-0.6, z1=2.4, surface="teak"):
    from kit import box
    obj = box(name, coll, x0, x1, y0, y1, z0, z1)
    obj["surface"] = surface
    obj.display_type = "WIRE"
    return obj


def fence_colliders(coll):
    """Thin walls along the outer fence (the gate open), the lane's fences (open at the
    Neak Ta and the Preah Phum), and across the road outside the gate."""
    x0, x1, y0, y1 = C.OUTER
    t = 0.09
    walls = [
        ("front_w", x0, -C.GATE_HALF, y0 - t, y0 + t), ("front_e", C.GATE_HALF, x1, y0 - t, y0 + t),
        ("west", x0 - t, x0 + t, y0, y1), ("east", x1 - t, x1 + t, y0, y1), ("back", x0, x1, y1 - t, y1 + t),
        # The road outside the gate: its verges and its far end, in the trees.
        ("road_w", -4.4, -4.2, y0 - 6.5, y0), ("road_e", 4.2, 4.4, y0 - 6.5, y0), ("road_end", -4.4, 4.4, y0 - 6.7, y0 - 6.5),
    ]
    for side, x in (("w", -C.LANE_X), ("e", C.LANE_X)):
        y = C.LANE_Y[0]
        for lo, hi in sorted(C.LANE_OPEN[side]) + [(C.LANE_Y[1], C.LANE_Y[1])]:
            if lo > y:
                walls.append((f"lane_{side}_{len(walls)}", x - t, x + t, y, lo))
            y = hi
    for name, a, b, c, d in walls:
        collider(coll, f"col_compound_{name}", a, b, c, d)
    return len(walls)


def puddles(coll, ground, rng, n=14):
    """Rain standing in the lane's low spots: flat, irregular, the colour of the mud."""
    mat = bpy.data.materials.get("M_cp_puddle")
    if mat is None:
        from kit import plain
        mat = plain("M_cp_puddle", (0.035, 0.026, 0.02), rough=0.04)
    made = 0
    for _ in range(n * 3):
        if made >= n:
            break
        x, y = rng.uniform(-2.6, 2.6), rng.uniform(C.LANE_Y[0] - 5, C.LANE_Y[1] - 1)
        r = rng.uniform(0.25, 0.7)
        ring = 18
        phase = rng.uniform(0, 6)
        z = ground(x, y) + 0.016
        verts = [(x, y, z)]
        for k in range(ring):
            a = math.tau * k / ring
            rr = r * (1 + 0.25 * math.sin(a * 2 + phase) + 0.12 * math.sin(a * 5 + phase * 2))
            px, py = x + rr * math.cos(a), y + rr * 0.6 * math.sin(a)
            verts.append((px, py, max(z, ground(px, py) + 0.014)))
        faces = [(0, 1 + k, 1 + (k + 1) % ring) for k in range(ring)]
        from kit import mesh_object
        mesh_object(f"cp_puddle_{made}", coll, verts, faces, mat)
        made += 1
    return made


def ground_skins(coll, ground):
    """The lane's red laterite mud and the yard's trodden earth: photo-scanned maps,
    the game's material as exported (no Cycles-only node mixing)."""
    from kit import library_material
    lane = bpy.data.materials.get("M_cp_lane_mud") or library_material("red_dirt_mud_01", "M_cp_lane_mud", tint=(.82, .76, .72), tile=1.5)
    yard = bpy.data.materials.get("M_cp_yard_mud") or library_material("brown_mud_leaves_01", "M_cp_yard_mud", tint=(.8, .76, .72), tile=2.0)
    a = C.lane_surface(coll, ground, y0=C.LANE_Y[0] - 6.5, y1=-2.6, half=3.3, mat=lane)
    b = C.lane_surface(coll, ground, y0=-3.0, y1=9.6, half=12.8, step=0.3, name="cp_yard", mat=yard)
    return a, b


def thin_wall(placed, budget):
    """The tree wall within a triangle budget: the far trees first to go."""
    def tris(o):
        return sum(len(p.vertices) - 2 for p in o.data.polygons)
    total = sum(tris(o) for o in placed)
    if total <= budget:
        return total, 0
    x0, x1, y0, y1 = C.OUTER

    def depth(o):
        p = o.matrix_world.translation
        return max(x0 - p.x, p.x - x1, y0 - p.y, p.y - y1)
    gone = 0
    for o in sorted(placed, key=depth, reverse=True):
        if total <= budget:
            break
        total -= tris(o)
        bpy.data.objects.remove(o, do_unlink=True)
        gone += 1
    return total, gone


def hall(coll, rng):
    """The funeral in the central hall, as previewed."""
    drop = re.compile(r"^(altar_bouquet_|portrait_floral_surround|funeral_prop_0[0-3]_|lantern_cord_|lantern_flame_|"
                      r"house_dread_hall_0[23]|hall_lamp_cord|incense_burner_\d|col_incense_burner_\d)")
    gone = [o for o in bpy.data.objects if drop.match(o.name)]
    # The hurricane lamps hung over the hall (Lantern_01 copies) and the lights they gave.
    for o in bpy.data.objects:
        if any(c.name == "_protos" for c in o.users_collection):
            continue
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box] if o.type == "MESH" else [o.matrix_world.translation]
        inside = all(-3 < p.x < 3 and 11 < p.y < 22.2 for p in pts)
        if inside and o.name.startswith("Lantern_01"):
            gone.append(o)
        if inside and o.name.startswith("light_flame_") and min(p.z for p in pts) > 4.2:
            gone.append(o)
    print("hall: removed", remove(gone), flush=True)
    # The portrait at a real funeral photograph's size, on its riser.
    portrait = bpy.data.objects.get("portrait_sok")
    if portrait and abs(portrait.scale.x - 0.6) > 1e-3:
        portrait.scale = (0.6, 0.6, 0.6)
    FS.build(coll, rng)
    objs, tips, _smoke = FO.build(coll, rng)
    # A flame on every lit wick (FuneralRoom wavers flames named like step_candle_N_flame),
    # and a light for each cluster of them.
    src = bpy.data.objects["altar_candle_0_flame"]
    sp = [src.matrix_world @ Vector(c) for c in src.bound_box]
    foot = Vector((sum(p.x for p in sp) / 8, sum(p.y for p in sp) / 8, min(p.z for p in sp)))
    for k, tip in enumerate(tips):
        fl = src.copy()
        fl.parent = None
        mw = src.matrix_world.copy()
        mw.translation = src.matrix_world.translation + (tip + Vector((0, 0, 0.002)) - foot)
        fl.matrix_world = mw
        fl.name = f"step_candle_{40 + k}_flame"
        coll.objects.link(fl)
    clusters = {}
    for tip in tips:
        key = (round(tip.x / 0.9), round(tip.y / 0.9))
        clusters.setdefault(key, []).append(tip)
    from kit import empty
    for k, pts in enumerate(clusters.values()):
        c = sum(pts, Vector()) / len(pts) + Vector((0, 0, 0.06))
        empty(f"light_flame_offering_{k}", coll, tuple(c), radius=2.2, intensity=0.6 + 0.25 * len(pts))
    # The vigil's incense corners, moved where Sora can reach them, each with its burner.
    for i, (x, y, stand) in enumerate(FO.VIGIL_CORNERS):
        marker = bpy.data.objects.get(f"interact_incense_{i}")
        if marker is None:
            continue
        marker.location = (x, y, FO.FLOOR + stand + 0.25)
        bpy.context.view_layer.update()
        FO.vigil_burner(coll, marker, x, y, stand, rng)
    return len(tips)


def main():
    ground = VE.Ground()
    rng = np.random.default_rng(20)
    coll = collection(COLL)
    hall_coll = collection(HALL)

    # 1. What the compound no longer has.
    gone = C.retired(protected=("_protos", "nature_templates", COLL, HALL))
    gone += [o for o in C.lane_clutter() if o not in gone]
    # Colliders of the palms and bamboo taken out above: invisible walls otherwise.
    gone += [o for o in bpy.data.objects if re.match(r"^col_(palm|bamboo|sugar|coco)", o.name) and o not in gone]
    gone += [o for o in bpy.data.objects if o.name.startswith("cp_puddle_") and o not in gone]
    # Older passes' puddles in the lane and the yard: the game draws them as black blots.
    gone += [o for o in bpy.data.objects if re.match(r"^puddle_\d+$", o.name) and not C.outside(o, margin=0) and o not in gone]
    print("removed", remove(gone), flush=True)
    for name in ("expansion_east", "expansion_west", "expansion_north"):
        c = bpy.data.collections.get(name)
        if c is not None and not c.all_objects:
            bpy.data.collections.remove(c)

    # 2. The compound.
    C.fences(coll, ground, rng)
    C.yard_fence(coll, ground, rng)
    print("colliders", fence_colliders(coll), flush=True)
    f = VN.flora()
    wall = C.tree_wall(coll, ground, rng, f, depth=(1.5, 13.0), spacing=3.4)
    total, culled = thin_wall(wall, budget=int(os.environ.get("WALL_TRIS", 1_400_000)))
    print(f"tree wall: {len(wall) - culled} trees, {total} triangles ({culled} far ones dropped)", flush=True)
    ground_skins(coll, ground)
    # (No puddles: without reflections the game draws standing water as black holes.)
    C.preah_phum_bund(coll, ground)
    print("rice faces cut", C.cut_rice(), flush=True)
    grass = VN.poly_haven("grass_medium_01") + VN.poly_haven("grass_medium_02")
    print("verge grass", C.verges(coll, ground, rng, grass), flush=True)

    # 3. Spawn on the road outside the gate; the pond's spirit in the rice by the lane.
    spawn = bpy.data.objects.get("spawn_player")
    if spawn:
        spawn.location = (0.0, C.OUTER[2] - 2.6, ground(0.0, C.OUTER[2] - 2.6))
    spirit = bpy.data.objects.get("pond_spirit")
    if spirit:
        for ch in list(spirit.children):
            bpy.data.objects.remove(ch, do_unlink=True)
        spirit.location = (-9.0, -24.0, VN.PADDY_FLOOR)
        spirit.rotation_euler = (0, 0, math.pi)  # her back to the lane, facing out over the rice

    # 4. The funeral.
    print("offering flames", hall(hall_coll, rng), flush=True)

    # 5. Nothing floats.
    print("posts lengthened to their roof", C.meet_roof(), flush=True)
    _fails, report = C.settle((-17, -47, 21, 37), keep=(r"^sok_desk", r"^interact_", r"^door_", r"^hide_", r"^hall_shroud",
                                                         r"_cover$", r"^spawn", r"^light_"))
    print("pushed to walls", C.push_to_walls([n for n in report["left"] if C.WALL_MOUNTED.search(n)]), flush=True)
    after, _ = C.settle((-17, -47, 21, 37), keep=(r".",), quiet=True)
    print(f"floating parts left: {len(after)}", flush=True)
    for fl in after[:20]:
        print("   ", fl["gap"], fl["object"], fl["min"], flush=True)

    if os.environ.get("COMPOUND_DRY"):
        print("dry run: not saved", flush=True)
        return
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print("saved", bpy.data.filepath, flush=True)


main()
