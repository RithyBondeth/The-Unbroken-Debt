"""Rebuilds Episode 1's family house as the colonial-era teak house
(tools/areas/colonial_house.py) inside the existing village, without
regenerating anything else: the old shell (walls, windows, doors, veranda rail,
roof, gables, round posts and what was fitted to them) is removed, the two
doors the game uses keep their names and properties, and every room-side wall
face stays where it was.

    blender -b --factory-startup --python-exit-code 1 art-source/blender/ep1/ep1_area_village.blend \\
        -P tools/areas/rebuild-house-colonial.py
    npm run export -- ep1/ep1_area_village && npm run assets -- ep1/ep1_area_village.glb

Re-runnable: what it builds lives in the `house_colonial` collection and is
replaced each run; the one-time moves of older props are flagged in the file.
(--python-exit-code 1 makes Blender fail when the script does, so a broken
rebuild never flows into an export.)
"""
import math
import os
import re
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
AUDIT_AS_MODULE = True
from kit import ROOT, library_material  # noqa: E402
import weathering  # noqa: E402
from colonial_materials import OUT, colonial_materials  # noqa: E402
import colonial_house  # noqa: E402

SHELL = re.compile(
    r"^(wall_(front|back|west|east|kitchen_hall|yaymey_hall|kitchen_yaymey|sok_hall|vuthy_hall|sok_vuthy)_\d+"
    r"|col_wall_.*|batten_(front|back|west|east).*|win_.*|door_(frame|head)_.*"
    r"|door_(front_leaf_[lr]|back_leaf|vuthy_leaf)|interact_door_(yaymey|sok)"
    r"|rail_(post|brace|top|bottom|west_top|west_brace).*|col_veranda_rail(_w)?"
    r"|roof_(n|s|under_n|under_s|plate_\d+)|rafter_.*|purlin_.*|ridge_(beam|cap)|king_post_.*|tie_beam_.*"
    r"|gable.*|bargeboard_.*|barge_hook_.*|pillar_.*|footing_.*|col_pillar_.*"
    r"|house_web_\d+|house_decay_web_\d+|house_decay_(moss|roof_damage|wall_stains|post_mud)|house_decay_termite_.*"
    r"|house_detail_tied_rag_[012])(\.\d+)?$"
)


def in_house(obj):
    """By the middle of what the object shows: many meshes keep their origin at 0, 0, 0."""
    from mathutils import Vector
    if obj.type == "MESH" and len(obj.data.vertices):
        corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        x = sum(c.x for c in corners) / 8
        y = sum(c.y for c in corners) / 8
    else:
        x, y, _ = obj.matrix_world.translation
    return -9.0 < x < 10.0 and 7.0 < y < 27.0


def _move(name, delta):
    o = bpy.data.objects.get(name)
    if o is None:
        print(f"[house] missing {name}")
        return
    mw = o.matrix_world.copy()
    mw.translation += Vector(delta)
    o.matrix_world = mw


def _verts_in(name, lo, hi, delta):
    """Moves the vertices of one object that lie inside a world box (one loose part)."""
    o = bpy.data.objects.get(name)
    if o is None:
        return
    if o.data.users > 1:
        o.data = o.data.copy()
    inv = o.matrix_world.inverted()
    local = inv.to_3x3() @ Vector(delta)
    lo, hi = Vector(lo), Vector(hi)
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        if all(lo[i] - 0.005 <= w[i] <= hi[i] + 0.005 for i in range(3)):
            v.co += local


def ground_house():
    """Puts back what was floating in the house before the rebuild."""
    from mathutils import Matrix
    scene = bpy.context.scene
    if not scene.get("colonial_house_fixed"):
        _one_time_fixes(Matrix)
        scene["colonial_house_fixed"] = True
    _settle_small_things()


def _one_time_fixes(Matrix):
    """Moves made once (the file remembers): a re-run must not move these twice."""
    # A family photograph hung in mid-air in the back doorway: it goes on the hall wall
    # beside Vuthy's door, facing the hall.
    frame, photo = bpy.data.objects.get("family_frame_0"), bpy.data.objects.get("family_print_0")
    if frame and photo:
        bpy.context.view_layer.update()
        pivot = frame.matrix_world.translation.copy()
        turn = Matrix.Translation(pivot) @ Matrix.Rotation(-math.pi / 2, 4, "Z") @ Matrix.Translation(-pivot)
        for o in (frame, photo):
            o.matrix_world = turn @ o.matrix_world
        bpy.context.view_layer.update()
        xs = [(frame.matrix_world @ v.co).x for v in frame.data.vertices]
        shift = Vector((2.94 - max(xs), 18.35 - pivot.y, 0.0))
        for o in (frame, photo):
            o.matrix_world.translation += shift
    _move("kanha_drawing", (0, 21.938 - 21.89, 0))
    _move("house_dread_hall_03", (2.938 - 2.92, 0, 0))
    _move("house_dread_kitchen_04", (0, 11.502 - 11.57, 0))
    # Hair hanging from the kitchen window's inside sill.
    _verts_in("house_dread_kitchen_03", (-5.84, 13.22, 2.96), (-5.73, 13.32, 3.2), (-0.09, 0, 3.25 - 3.2))
    # A stain painted on nothing in the middle of the kitchen.
    for name in ("house_dread_kitchen_14",):
        o = bpy.data.objects.get(name)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
    for o in [o for o in bpy.data.objects if o.name.startswith("house_web")]:
        bpy.data.objects.remove(o, do_unlink=True)



def _settle_small_things():
    # Wasp nests from the old back eave are indoors now, in the corridor: they go.
    _verts_in("house_decay_wasp_nests", (-9, 21.9, 3.5), (9, 23.5, 6.0), (0, 0, -60.0))
    # Small things set down onto the ground or the floor beneath them (twice: a part
    # moved in the first pass can uncover another).
    import ground_audit
    ground_audit.REGION = (-10, 7, 10, 33)
    drop = re.compile(r"^(house_decay_tile_shards|bath_ash_pot|sok_notes|puddle_\d+|house_dread_kitchen_23)$")
    for _pass in range(2):
        failures, ctx = ground_audit.audit()
        bvh, tri_part, parts = ctx["bvh"], ctx["tri_part"], ctx["parts"]
        for f in failures:
            name, _mat, pts, _tri, _vsel = parts[f["part"]]
            if not drop.match(name):
                continue
            low = pts[pts[:, 2] < pts[:, 2].min() + 0.02]
            gap = math.inf
            for v in low[:12]:
                hit = bvh.ray_cast(Vector((v[0], v[1], v[2] - 0.0005)), Vector((0, 0, -1)), 0.5)
                if hit[0] is not None and tri_part[hit[2]] != f["part"]:
                    gap = min(gap, hit[3])
            lo, hi = pts.min(0), pts.max(0)
            if gap == math.inf:
                # Nothing beneath it to rest on: a stray shard, removed.
                _verts_in(name, lo, hi, (0, 0, -50.0))
                continue
            _verts_in(name, lo, hi, (0, 0, -(gap + 0.002)))
    # Strays sent below the world are deleted outright.
    for o in bpy.data.objects:
        if o.type == "MESH" and (drop.match(o.name) or o.name == "house_decay_wasp_nests"):
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(o.data)
            gone = [v for v in bm.verts if (o.matrix_world @ v.co).z < -20]
            if gone:
                bmesh.ops.delete(bm, geom=gone, context="VERTS")
                bm.to_mesh(o.data)
            bm.free()
    after, _ = ground_audit.audit()
    print(f"[house] floating parts left in the house area: {len(after)}")
    for f in after:
        print(f"[house]   {f['object']} gap {f['gap']} at {f['min']}")


KITCHEN_JUNK = re.compile(
    r"^(house_dread_kitchen_\d+|house_dread_prop_\d+_\d+|hearth_(charcoal|firewood|firewood_end|stone)_\d+"
    r"|kitchen_hearth_(ash_\d+|earth|plank_[nesw]|scorch_[nesw])|kitchen_table(_leg_.*)?|kitchen_shelf"
    r"|col_kitchen_(hearth|table)|prop_ceramic_pot|prop_wicker_basket_02\.003|prop_wooden_bucket_01)(\.\d+)?$")


def clear_kitchen():
    """The kitchen is tidied: the rot, hair, stains, scattered junk and the old
    box-built furniture go. The game's four kitchen items (matches drawer, oil,
    betel leaves, areca nut) stay where they are; house_rooms.py refurnishes it."""
    doomed = [o.name for o in bpy.data.objects if KITCHEN_JUNK.match(o.name)]
    _delete(doomed)
    print(f"[house] kitchen: removed {len(doomed)} objects")


# The bigger house's footprint (back block, porch, rear stairs, galleries): nothing grows in it.
FOOTPRINT = [(-8.7, 21.8, 8.7, 30.0), (-8.7, 13.8, -5.9, 22.0), (5.9, 13.8, 8.7, 22.0), (1.8, 28.0, 5.6, 29.7)]
PLANTS = re.compile(r"^(forest_grass_|house_forest_(house_sedge|forest_understory)_|yard_edge_grass_)")


def _in_footprint(x, y):
    return any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in FOOTPRINT)


def _delete(names):
    for name in names:
        o = bpy.data.objects.get(name)
        if o is None:
            continue
        kids = [c.name for c in o.children_recursive]
        bpy.data.objects.remove(o, do_unlink=True)
        for kid in kids:
            c = bpy.data.objects.get(kid)
            if c is not None:
                bpy.data.objects.remove(c, do_unlink=True)


def _shift(names, delta):
    for name in names:
        o = bpy.data.objects.get(name)
        if o is not None and o.parent is None:
            o.matrix_world.translation += Vector(delta)


def site_work():
    """One-time changes round the bigger house (the file remembers them)."""
    import bmesh
    from mathutils import Matrix
    scene = bpy.context.scene
    if scene.get("colonial_house_site_done"):
        return
    area = bpy.data.collections["ep1_area_village"]
    # Plants: bananas, shrubs, ferns and grass patches where the house now stands.
    gone = []
    for o in list(bpy.data.objects):
        if o.parent is not None:
            continue
        if o.type == "EMPTY" and re.match(r"^prop_(fern_02|pachira_aquatica_01|shrub_0\d)", o.name):
            if _in_footprint(o.location.x, o.location.y):
                gone.append(o.name)
        elif o.type == "MESH" and re.match(r"^banana_\d+$", o.name):
            c = sum((o.matrix_world @ Vector(v) for v in o.bound_box), Vector()) / 8
            if _in_footprint(c.x, c.y):
                gone.append(o.name)
    _delete(gone)
    patches = 0
    for o in [o for o in bpy.data.objects if o.type == "MESH" and PLANTS.match(o.name)]:
        if o.data.users > 1:
            o.data = o.data.copy()
        bm = bmesh.new()
        bm.from_mesh(o.data)
        mw = o.matrix_world
        # Loose parts (one plant each) whose middle lies in the footprint.
        seen, doomed = set(), []
        for v in bm.verts:
            if v in seen:
                continue
            part, stack = [], [v]
            seen.add(v)
            while stack:
                cur = stack.pop()
                part.append(cur)
                for e in cur.link_edges:
                    w = e.other_vert(cur)
                    if w not in seen:
                        seen.add(w)
                        stack.append(w)
            c = sum((mw @ p.co for p in part), Vector()) / len(part)
            if _in_footprint(c.x, c.y):
                doomed += part
        if doomed:
            bmesh.ops.delete(bm, geom=doomed, context="VERTS")
            bm.to_mesh(o.data)
            patches += 1
        bm.free()
    # The big tree that stood where the dining room is now grows beyond the back fence.
    _shift([n for n in ("tree_316", "col_tree_316")], (0.0, 34.5 - 25.18, 0.0))
    # The back fence moves out behind the porch stairs; the side fences run on to meet it.
    _shift([o.name for o in bpy.data.objects if re.match(r"^(col_)?fence_n_", o.name)], (0.0, 5.0, 0.0))
    from khmer import bamboo_fence
    fm = {"bamboo": bpy.data.materials["M_bamboo"]}
    bamboo_fence(area, fm, "fence_w_back", (-13.0, 27.0), (-13.0, 32.0))
    bamboo_fence(area, fm, "fence_e_back", (13.0, 27.0), (13.0, 32.0))
    # Rain jars stand under the new back eave; the drip markers follow the eave.
    for name, x in (("rain_jar_0", -6.7), ("rain_jar_1", 6.7)):
        for nm in (name, f"col_{name}"):
            o = bpy.data.objects.get(nm)
            if o:
                c = sum((o.matrix_world @ Vector(v) for v in o.bound_box), Vector()) / 8
                o.matrix_world.translation += Vector((x - c.x, 29.35 - c.y, 0))
    for name, x in (("marker_eave_3_a", -8.9), ("marker_eave_3_b", 8.9)):
        o = bpy.data.objects.get(name)
        if o:
            o.location = (x, 28.9, 4.35)
    # The rear stairs now climb along the back wall to the porch's east end.
    bpy.context.view_layer.update()
    stairs = bpy.data.objects.get("stairs_rear_detailed")
    col = bpy.data.objects.get("col_stairs_rear")
    if stairs:
        pts = [stairs.matrix_world @ v.co for v in stairs.data.vertices]
        top = Vector(((min(p.x for p in pts) + max(p.x for p in pts)) / 2, min(p.y for p in pts), 0))
        target = Vector((2.0, 28.75, 0))
        turn = Matrix.Translation(target) @ Matrix.Rotation(-math.pi / 2, 4, "Z") @ Matrix.Translation(-top)
        for o in (stairs, col):
            if o:
                o.matrix_world = turn @ o.matrix_world
    scene["colonial_house_site_done"] = True
    print(f"[house] site: removed {len(gone)} plants, thinned {patches} patches, moved tree, fence, jars, stairs")


def main():
    area = bpy.data.collections["ep1_area_village"]
    # Everything the rebuild makes lives in its own collection, cleared on a re-run.
    house = bpy.data.collections.get("house_colonial")
    if house is None:
        house = bpy.data.collections.new("house_colonial")
        area.children.link(house)
    # The doors the game uses keep their properties (read before anything is removed).
    props = {}
    for name in ("interact_door_yaymey", "interact_door_sok"):
        o = bpy.data.objects[name]
        props[name] = {k: o[k] for k in o.keys() if not k.startswith("_")}
    for o in list(house.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    doomed = [o for o in bpy.data.objects if SHELL.match(o.name) and (in_house(o) or o.name.startswith("col_"))
              and o.users_collection and o.users_collection[0].name == area.name]
    names = sorted(o.name for o in doomed)
    print(f"[house] removing {len(doomed)} shell objects", flush=True)
    for o in doomed:
        for child in list(o.children_recursive):
            if child.name in bpy.data.objects:
                bpy.data.objects.remove(child, do_unlink=True)
        bpy.data.objects.remove(o, do_unlink=True)
    clear_kitchen()
    site_work()
    m = colonial_materials()
    weathering.OUT = OUT
    # Old lime plaster at the foot of a house in the wet: grey, mud-splashed, green with algae.
    plinth = weathering.mouldy_plaster("T_ep1_colonial_plinth", (0.4, 0.37, 0.31), 1938, mould=1.2, algae=1.0, spall=0.9,
                                       size=1024, tile=1.0)
    plinth.name = "M_ep1_colonial_plinth"
    m["cl_plinth"] = plinth
    m["iron"] = library_material("rusty_metal", "M_ep1_house_iron", tint=(0.13, 0.11, 0.1), tile=0.5)
    m["brass"] = bpy.data.materials["M_brass"]
    m["termite"] = bpy.data.materials["M_house_detail_termite_mud"]
    m["rag"] = bpy.data.materials["M_wet_rag"]
    m["floor"] = bpy.data.materials["M_floor_boards"]
    for key, name in (("earth", "M_wet_termite_earth"), ("ash", "M_ash"), ("logs", "M_wet_bark"), ("rope", "M_rope"),
                      ("mat", "M_reed_mat"), ("cushion", "M_cushion"), ("krama", "M_krama"), ("cotton", "M_tent_cotton"),
                      ("cloth_red", "M_wet_cloth_red"), ("sandal", "M_sandal")):
        m[key] = bpy.data.materials[name]
    m["clay"] = bpy.data.materials["M_clay"]
    m["cotton_dirty"] = bpy.data.materials["M_cotton_dirty"]
    # Cushions in a dark woven silk-cotton, not the gingham picnic cloth.
    m["cushion"] = bpy.data.materials.get("M_ep1_house_cushion") or library_material(
        "quatrefoil_jacquard_fabric", "M_ep1_house_cushion", tint=(0.42, 0.16, 0.1))
    colonial_house.build(house, m, props)
    import house_rooms
    house_rooms.furnish(house, m)
    # The yantra cloths still hang over the front door and Sok's door, now in front of the fanlights.
    for name, axis, value in (("yantra_front", 1, 11.44 - 0.037), ("yantra_sok", 0, 2.94 - 0.037)):
        o = bpy.data.objects.get(name)
        if o:
            loc = list(o.matrix_world.translation)
            bpy.context.view_layer.update()
            pts = [o.matrix_world @ v.co for v in o.data.vertices]
            lo = min(p[axis] for p in pts)
            o.location[axis] += value - lo
    ground_house()
    bpy.data.orphans_purge(do_recursive=True)
    path = bpy.data.filepath
    # The new textures were loaded by absolute path; store them relative like the rest,
    # and point images saved from since-removed worktrees back at this checkout.
    if os.path.dirname(path) == os.path.join(ROOT, "art-source", "blender", "ep1"):
        from repair_image_paths import repair_image_paths
        repair_image_paths()
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print(f"[house] saved {path}; removed {len(names)}: {names[:12]} ...")


main()
