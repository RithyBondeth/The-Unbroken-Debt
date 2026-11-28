"""Furnishes the bigger colonial house (colonial_house.py): a tidy, lived-in 1930s
kitchen and the rooms of the back block, the corridor, the side galleries and the
porch. Everything is a real object from the library (Poly Haven CC0 models and the
CC BY scans in art-source/library/scans) or built here at true size, and every
piece is set down on the floor, a shelf or a table, or hangs from a peg, nail or
rail. The game's own kitchen items (matches drawer, oil, betel leaves, areca nut)
are not touched; the new table and shelf are built under them.

Blender axes: X east, Y north, Z up; metres. Run inside Blender.
"""
import math
import os

import bpy
import numpy as np
from mathutils import Vector

import khmer
from kit import LIB, box, collider, cylinder, empty, mesh_object, tube
from khmer import join
from colonial_parts import against

FLOOR = 2.5
ZW = FLOOR + 2.6


def _protos_from_file():
    """Reuse the protos already in the village file instead of importing them again."""
    hidden = bpy.data.collections.get("_protos")
    if hidden is None:
        return
    for o in hidden.objects:
        if o.parent is None and o.name.startswith("proto_") and o.type == "EMPTY":
            khmer._protos.setdefault(o.name[len("proto_"):], o)


def _complete_gltf_group():
    """The glTF importer reuses an existing "glTF Material Output" group and expects all
    of its sockets; the village's own (kit.gltf_output_group) has only Occlusion, which
    breaks importing scans. Add the missing sockets to it in place: the village's
    materials keep using it for their occlusion."""
    from io_scene_gltf2.blender.com.material_helpers import create_settings_group, get_gltf_node_name
    name = get_gltf_node_name()
    group = bpy.data.node_groups.get(name)
    if group is None:
        create_settings_group(name)
        return
    have = {item.name for item in group.interface.items_tree if item.item_type == "SOCKET"}
    full = create_settings_group("_gltf_full_settings")
    for item in full.interface.items_tree:
        if item.item_type == "SOCKET" and item.name not in have:
            group.interface.new_socket(item.name, in_out=item.in_out, socket_type=item.socket_type)
    bpy.data.node_groups.remove(full)


def _scan_proto(key):
    """A library scan imported once into _protos, copied like a Poly Haven model."""
    model_id = f"scan_{key}"
    if model_id in khmer._protos:
        return model_id
    hidden = bpy.data.collections.get("_protos")
    if hidden is None:
        hidden = bpy.data.collections.new("_protos")
        bpy.context.scene.collection.children.link(hidden)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(LIB, "scans", f"{key}.glb"))
    new = [o for o in bpy.data.objects if o not in before]
    parent = empty(f"proto_{model_id}", hidden, (0, 0, 0))
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        hidden.objects.link(o)
        if o.parent is None:
            o.parent = parent
    khmer._protos[model_id] = parent
    return model_id


class Room:
    """Places props in one collection and sets each one down where it belongs."""

    def __init__(self, coll):
        self.coll = coll
        self.k = 0

    def put(self, model, at, rot=0.0, scale=1.0, wall=None, z=FLOOR, collide=False, scan=False):
        """`wall`: (axis, face, toward) to stand it flush against a wall face."""
        model_id = _scan_proto(model) if scan else model
        self.k += 1
        parent = khmer.place(self.coll, model_id, (at[0], at[1], z), rot, scale, name=f"house_{model}_{self.k}")
        if wall:
            against(parent, wall[0], wall[1], wall[2], floor_z=z)
        else:
            against(parent, None, 0, 1, floor_z=z)
        if collide:
            bpy.context.view_layer.update()
            pts = [o.matrix_world @ v.co for o in parent.children_recursive if o.type == "MESH" for v in o.data.vertices]
            xs, ys, zs = [p.x for p in pts], [p.y for p in pts], [p.z for p in pts]
            collider(f"house_{model}_{self.k}", self.coll, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))
        return parent

    def top(self, parent):
        bpy.context.view_layer.update()
        return max((o.matrix_world @ v.co).z for o in parent.children_recursive if o.type == "MESH" for v in o.data.vertices)


def _logs(name, coll, mat, x0, y0, along_x, length, rows, per_row, r=0.045, z0=FLOOR, rng=None):
    """Split firewood stacked neatly: each row sits in the hollows of the one below."""
    logs = []
    for i in range(rows):
        n = per_row - (i % 2)
        for j in range(n):
            off = (j + 0.5 * (i % 2)) * r * 2.05
            z = z0 + r + i * r * 1.75
            jitter = rng.uniform(-0.03, 0.03) if rng is not None else 0
            if along_x:
                a = (x0 + jitter, y0 + off, z)
                b = (x0 + length + jitter, y0 + off, z)
            else:
                a = (x0 + off, y0 + jitter, z)
                b = (x0 + off, y0 + length + jitter, z)
            logs.append(tube(f"{name}_log", coll, [a, b], r * (0.85 + 0.3 * (rng.random() if rng is not None else 0.5)),
                             mat, sides=7, metres_per_v=1.0))
    return join(logs, name)


def _dust_sheet(name, coll, mat, x0, x1, y0, y1, top, floor=FLOOR, folds=9, rng=None):
    """A cotton dust sheet thrown over furniture: flat on top, falling in folds to the floor."""
    nx, ny = 18, 14
    pad = 0.06
    verts, faces = [], []
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hw, hd = (x1 - x0) / 2 + pad, (y1 - y0) / 2 + pad
    # A grid over the top that drapes down the sides: rings out from the middle.
    rings = 10
    seg = 48
    for r in range(rings + 1):
        t = r / rings
        for k in range(seg):
            a = 2 * math.pi * k / seg
            dx, dy = math.cos(a), math.sin(a)
            s = max(abs(dx) / hw, abs(dy) / hd)
            ex, ey = dx / s, dy / s  # point on the furniture's outline in this direction
            if t <= 0.6:
                f = t / 0.6
                x, y, z = cx + ex * f, cy + ey * f, top + 0.012 - 0.01 * f
            else:
                f = (t - 0.6) / 0.4
                fold = 0.035 * math.sin(folds * a + (rng.uniform(0, 6) if rng is not None else 0)) * f
                x = cx + ex * (1 + 0.06 * f) + dx * fold
                y = cy + ey * (1 + 0.06 * f) + dy * fold
                z = top + 0.002 - (top - floor - 0.004) * f ** 1.4
            verts.append((x, y, z))
    for r in range(rings):
        for k in range(seg):
            a = r * seg + k
            b = r * seg + (k + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    o = mesh_object(name, coll, verts, faces, mat, smooth=True)
    return o


def _hanging_cloth(name, coll, mat, rail, along_x, width, drop, rng):
    """A cloth folded over a rail or line: both halves hang down from it."""
    rx, ry, rz = rail
    verts, faces = [], []
    cols = 6
    for side in (-1, 1):
        base = len(verts)
        for j in range(4):
            t = j / 3
            for i in range(cols + 1):
                a = (i / cols - 0.5) * width
                wob = 0.012 * math.sin(i * 1.7 + j + side) * t
                off = side * (0.012 + 0.015 * t) + wob
                x, y = (rx + a, ry + off) if along_x else (rx + off, ry + a)
                verts.append((x, y, rz + 0.006 - drop * t * (0.85 + 0.15 * side)))
        for j in range(3):
            for i in range(cols):
                p = base + j * (cols + 1) + i
                faces.append((p, p + 1, p + cols + 2, p + cols + 1))
    o = mesh_object(name, coll, verts, faces, mat)
    o.data.materials[0].use_backface_culling = False
    return o


def _ash_mound(name, coll, mat, cx, cy, z, radius, rng, height=0.018):
    """Old ash and charcoal dust in a low, ragged heap where the fire is laid."""
    seg, rings = 28, 5
    verts, faces = [(cx, cy, z + height)], []
    edge = [radius * (0.75 + 0.35 * rng.random()) for _ in range(seg)]
    for r in range(1, rings + 1):
        t = r / rings
        for k in range(seg):
            a = 2 * math.pi * k / seg
            rr = edge[k] * t
            verts.append((cx + rr * math.cos(a), cy + rr * math.sin(a), z + 0.001 + height * (1 - t ** 1.6)))
    for k in range(seg):
        faces.append((0, 1 + k, 1 + (k + 1) % seg))
    for r in range(rings - 1):
        for k in range(seg):
            a = 1 + r * seg + k
            b = 1 + r * seg + (k + 1) % seg
            faces.append((a, a + seg, b + seg, b))
    return mesh_object(name, coll, verts, faces, mat, smooth=True)


def _floor_mat(name, coll, mat, x0, x1, y0, y1):
    """A woven reed mat lying flat on the boards, its edges bound."""
    box(name, coll, x0, x1, y0, y1, FLOOR, FLOOR + 0.005, mat)
    for k, (a, b, c, d) in enumerate(((x0, x1, y0, y0 + 0.025), (x0, x1, y1 - 0.025, y1))):
        box(f"{name}_binding_{k}", coll, a, b, c, d, FLOOR, FLOOR + 0.007, mat)


def _peg(name, coll, mat, at, normal, length=0.09):
    nx, ny = normal
    a = at
    b = (at[0] + nx * length, at[1] + ny * length, at[2] + 0.015)
    return tube(name, coll, [a, b], 0.01, mat, sides=6)


def kitchen(coll, m, rng):
    """A tidy 1930s kitchen: an earth-filled hearth box with a clay stove and pot, a
    teak work table (the game's matches drawer is in its apron), a three-tier shelf
    (the oil bottle stands on its lowest board), a water jar, firewood stacked by the
    hearth, a straw mat, baskets and a broom by the door."""
    r = Room(coll)
    # The hearth box: planks round a bed of packed earth and ash.
    x0, x1, y0, y1, hz = -5.8, -4.6, 11.7, 12.6, FLOOR + 0.42
    for name, b in (("s", (x0, x1, y0, y0 + 0.04)), ("n", (x0, x1, y1 - 0.04, y1)),
                    ("w", (x0, x0 + 0.04, y0, y1)), ("e", (x1 - 0.04, x1, y0, y1))):
        box(f"kitchen_hearth_box_{name}", coll, *b, FLOOR, hz, m["cl_trim"], edge=0.006)
    box("kitchen_hearth_earth", coll, x0 + 0.04, x1 - 0.04, y0 + 0.04, y1 - 0.04, FLOOR, hz - 0.03, m["earth"])
    _ash_mound("kitchen_hearth_ash", coll, m["ash"], -5.2, 12.15, hz - 0.03, 0.24, rng)
    collider("kitchen_hearth", coll, x0, x1, y0, y1, FLOOR, hz)
    # Three fired-clay hearth supports (the Khmer way) hold the cooking pot over the fire.
    for k in range(3):
        a = math.radians(90 + 120 * k)
        hx, hy = -5.2 + 0.13 * math.cos(a), 12.15 + 0.13 * math.sin(a)
        prof = [(0.065, 0.0), (0.06, 0.04), (0.045, 0.11), (0.032, 0.15), (0.0, 0.158)]
        from kit import lathe
        lathe(f"kitchen_hearth_support_{k}", coll, prof, hx, hy, hz - 0.03, m["clay"], segments=12)
    pot = r.put("cooking_pot", (-5.2, 12.15), -30, scale=0.75, z=hz - 0.03 + 0.12, scan=True)
    r.put("kettle", (-4.82, 12.42), 140, z=hz - 0.03, scan=True)
    _logs("kitchen_hearth_wood", coll, m["logs"], -5.72, 11.78, True, 0.22, 1, 3, r=0.028, z0=hz - 0.03, rng=rng)
    # Firewood stacked along the west wall under the window, split ends outward.
    _logs("kitchen_firewood", coll, m["logs"], -5.9, 12.7, False, 0.62, 4, 4, r=0.042, rng=rng)
    # The work table, its top where the betel leaves and the areca bowl already lie.
    tx0, tx1, ty0, ty1, tz = -5.0, -3.6, 13.2, 14.2, FLOOR + 0.75
    box("kitchen_table_top", coll, tx0 - 0.03, tx1 + 0.03, ty0 - 0.0, ty1 + 0.03, tz - 0.05, tz, m["cl_trim"], edge=0.008)
    for name, b in (("s_w", (tx0 + 0.04, -4.05, ty0 + 0.02, ty0 + 0.045)), ("s_e", (-3.65, tx1 - 0.04, ty0 + 0.02, ty0 + 0.045)),
                    ("n", (tx0 + 0.04, tx1 - 0.04, ty1 - 0.045, ty1 - 0.02)),
                    ("w", (tx0 + 0.02, tx0 + 0.045, ty0 + 0.04, ty1 - 0.04)), ("e", (tx1 - 0.045, tx1 - 0.02, ty0 + 0.04, ty1 - 0.04))):
        box(f"kitchen_table_apron_{name}", coll, *b, tz - 0.17, tz - 0.05, m["cl_trim"])
    # The drawer's carcass behind the game's drawer front.
    box("kitchen_table_drawer_box", coll, -4.02, -3.68, ty0 + 0.02, ty0 + 0.45, tz - 0.16, tz - 0.05, m["cl_trim"])
    for lx in (tx0 + 0.02, tx1 - 0.07):
        for ly in (ty0 + 0.02, ty1 - 0.07):
            box(f"kitchen_table_leg", coll, lx, lx + 0.05, ly, ly + 0.05, FLOOR, tz - 0.05, m["cl_trim"], edge=0.005)
    box("kitchen_table_stretcher", coll, tx0 + 0.05, tx1 - 0.05, ty1 - 0.06, ty1 - 0.03, FLOOR + 0.15, FLOOR + 0.2, m["cl_trim"])
    collider("kitchen_table", coll, tx0, tx1, ty0, ty1, FLOOR, tz)
    board = r.put("wooden_cutting_board", (-4.72, 13.98), 10, z=tz)
    for k, (x, y) in enumerate(((-4.8, 13.95), (-4.66, 14.02), (-4.74, 13.9))):
        r.put("yellow_onion", (x, y), 40 * k, z=r.top(board))
    bowl = r.put("wooden_bowl_02", (-3.82, 13.55), 0, z=tz)
    for k, (x, y) in enumerate(((-3.84, 13.53), (-3.79, 13.58))):
        r.put("food_lime_01", (x, y), 60 * k, z=tz + 0.02)
    r.put("jug_01", (-3.76, 14.06), 30, z=tz)
    # The three-tier wall shelf; the oil bottle stands on its lowest board at z 3.45.
    sx0, sx1, sy0, sy1 = -5.94, -5.66, 13.38, 14.42
    for k, z in enumerate((FLOOR + 0.95, FLOOR + 1.39, FLOOR + 1.83)):
        box(f"kitchen_shelf_{k}", coll, sx0, sx1, sy0, sy1, z - 0.04, z, m["cl_trim"], edge=0.004)
        for y in (sy0 + 0.06, sy1 - 0.06):
            box(f"kitchen_shelf_bracket_{k}", coll, sx0, sx0 + 0.18, y - 0.015, y + 0.015, z - 0.2, z - 0.04, m["cl_trim"])
    r.put("ceramic_pot", (-5.8, 13.55), 0, z=FLOOR + 0.95)
    r.put("wooden_bowl_01", (-5.8, 14.25), 0, z=FLOOR + 0.95)
    r.put("pot_enamel_01", (-5.8, 13.6), 90, z=FLOOR + 1.39)
    r.put("brass_pot_01", (-5.8, 14.12), 0, z=FLOOR + 1.39)
    r.put("jar_plain", (-5.8, 13.62), 0, scale=0.7, z=FLOOR + 1.83, scan=True)
    r.put("basket_round", (-5.79, 14.12), 0, scale=0.6, z=FLOOR + 1.83, scan=True)
    # By the north wall: the water jar with its lid and dipper, a deep basket by the post.
    jar = r.put("water_jar", (-5.42, 14.1), 15, scale=0.9, collide=True, scan=True)
    jz = r.top(jar)
    cylinder("kitchen_jar_lid", coll, -5.42, 14.1, jz - 0.005, jz + 0.02, 0.2, m["cl_trim"], verts=20)
    r.put("wooden_bowl_01", (-5.4, 14.08), 30, z=jz + 0.02)
    r.put("basket_deep", (-3.36, 14.18), 0, scale=0.9, scan=True)
    # The winnowing tray hangs on a peg over the table.
    _peg("kitchen_peg_tray", coll, m["cl_trim"], (-4.3, 14.47, FLOOR + 1.85), (0, -1))
    tray = r.put("winnowing_tray", (-4.3, 14.4), 0, z=FLOOR, scan=True)
    tray.rotation_euler = (math.radians(-82), 0, 0)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ v.co for o in tray.children_recursive if o.type == "MESH" for v in o.data.vertices]
    tray.location += Vector((0, 14.465 - max(p.y for p in pts), FLOOR + 1.88 - max(p.z for p in pts)))
    # By the door: a broom against the partition, a bucket, a stool under the window, a mat.
    r.put("broom", (-3.1, 11.72), 90, wall=(0, -3.0, -1), scan=True)
    r.put("wooden_bucket_01", (-3.4, 11.86), 30)
    r.put("wooden_stool_01", (-4.2, 11.86), 15)
    _floor_mat("kitchen_mat", coll, m["mat"], -4.75, -3.9, 12.45, 13.1)
    # Ladles and a strainer on a rail on the north wall, beside the jar.
    box("kitchen_ladle_rail", coll, -5.25, -5.05, 14.43, 14.47, FLOOR + 1.55, FLOOR + 1.58, m["cl_trim"])
    for k, x in enumerate((-5.22, -5.15, -5.08)):
        r.put("wooden_spoon", (x, 14.38), 90, z=FLOOR + 1.3)


def store_room(coll, m, rng):
    """Rice bin and sacks, jars, baskets, crates, tools on pegs, a ladder, rope."""
    r = Room(coll)
    # The rice bin: a lidded teak chest on feet in the north-east corner.
    bx0, bx1, by0, by1, bz = -4.45, -3.12, 26.9, 27.88, FLOOR + 0.82
    box("store_rice_bin", coll, bx0, bx1, by0, by1, FLOOR + 0.08, bz - 0.04, m["cl_trim"], edge=0.01)
    box("store_rice_bin_lid", coll, bx0 - 0.02, bx1 + 0.02, by0 - 0.02, by1 + 0.02, bz - 0.04, bz, m["cl_trim"], edge=0.008)
    for lx in (bx0 + 0.02, bx1 - 0.08):
        for ly in (by0 + 0.02, by1 - 0.08):
            box("store_rice_bin_foot", coll, lx, lx + 0.06, ly, ly + 0.06, FLOOR, FLOOR + 0.08, m["cl_trim"])
    collider("store_rice_bin", coll, bx0, bx1, by0, by1, FLOOR, bz)
    for k, (x, y, rot) in enumerate(((-4.0, 26.4, 10), (-3.5, 26.45, -20), (-3.75, 26.2, 70))):
        r.put("rice_sack", (x, y), rot, z=FLOOR if k < 2 else FLOOR + 0.3, collide=k < 2, scan=True)
    # Jars along the north wall, west of the window.
    for k, (x, kind, s) in enumerate(((-7.55, "water_jar", 0.95), (-7.0, "jar_handles", 1.0), (-4.95, "jar_plain", 1.0))):
        r.put(kind, (x, 27.55), 25 * k, scale=s, collide=True, scan=True)
    # Shelves on the west wall either side of the window.
    for name, (y0, y1) in (("s", (23.45, 24.75)), ("n", (26.05, 27.4))):
        for k, z in enumerate((FLOOR + 0.5, FLOOR + 1.05, FLOOR + 1.6)):
            box(f"store_shelf_{name}_{k}", coll, -7.94, -7.56, y0, y1, z - 0.04, z, m["cl_trim"], edge=0.004)
        for y in (y0 + 0.04, y1 - 0.08):
            box(f"store_shelf_{name}_upright", coll, -7.62, -7.56, y, y + 0.04, FLOOR, FLOOR + 1.6, m["cl_trim"])
    r.put("basket_round", (-7.75, 23.8), 0, scale=0.8, z=FLOOR + 0.5, scan=True)
    r.put("wicker_basket_01", (-7.75, 24.4), 30, z=FLOOR + 0.5)
    r.put("jar_plain", (-7.75, 23.85), 0, scale=0.8, z=FLOOR + 1.05, scan=True)
    r.put("ceramic_pot", (-7.75, 24.4), 0, z=FLOOR + 1.05)
    r.put("oil_tin", (-7.75, 24.1), 0, z=FLOOR + 1.6)
    r.put("wicker_basket_02", (-7.75, 26.5), 0, z=FLOOR + 0.5)
    r.put("basket_deep", (-7.74, 27.1), 0, scale=0.75, z=FLOOR + 0.5, scan=True)
    r.put("pot_enamel_01", (-7.75, 26.4), 0, z=FLOOR + 1.05)
    r.put("brass_pot_02", (-7.75, 27.05), 0, z=FLOOR + 1.05)
    r.put("wooden_bowl_02", (-7.75, 26.7), 0, z=FLOOR + 1.6)
    # Crates stacked by the partition, the ladder against the north wall.
    c1 = r.put("wooden_crate_01", (-3.45, 24.0), 5, collide=True)
    r.put("wooden_crate_01", (-3.45, 24.0), -8, z=r.top(c1))
    r.put("wooden_crate_01", (-3.5, 24.75), 12, collide=True)
    r.put("wooden_ladder_02", (-5.4, 27.75), 0, wall=(1, 27.94, -1))
    # Tools on pegs on the partition, winnowing trays hung beside them.
    for k, (y, model, rot) in enumerate(((25.1, "hatchet", 0), (25.45, "machete", 0))):
        _peg(f"store_peg_{k}", coll, m["cl_trim"], (-3.03, y, FLOOR + 1.5), (-1, 0))
        tool = r.put(model, (-3.1, y), 90, z=FLOOR + 1.2)
        tool.rotation_euler.x = math.radians(90)
        bpy.context.view_layer.update()
        pts = [o.matrix_world @ v.co for o in tool.children_recursive if o.type == "MESH" for v in o.data.vertices]
        tool.location += Vector((-3.035 - max(p.x for p in pts), 0, FLOOR + 1.52 - max(p.z for p in pts)))
    r.put("rusted_spade_01", (-3.2, 25.9), 90, wall=(0, -3.03, -1))
    for k, y in enumerate((26.3, 26.7)):
        _peg(f"store_tray_peg_{k}", coll, m["cl_trim"], (-3.03, y, FLOOR + 1.75), (-1, 0))
    # Coils of rope on the floor and a bundle of rolled mats in the corner.
    for k, (x, y) in enumerate(((-6.4, 24.0), (-6.25, 24.2))):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.17, minor_radius=0.03, location=(x, y, FLOOR + 0.03 + 0.055 * k))
        coil = bpy.context.active_object
        coil.name = f"store_rope_{k}"
        for c in coil.users_collection:
            c.objects.unlink(coil)
        coll.objects.link(coil)
        coil.data.materials.append(m["rope"])
    for k in range(3):
        cylinder(f"store_rolled_mat_{k}", coll, -7.6 + k * 0.17, 25.95 - 0.02 * k, FLOOR, FLOOR + 1.1, 0.075, m["mat"], verts=14)


def dining_room(coll, m, rng):
    """A low table on a mat with cushions round it, a tea set and the evening's bowls,
    a cabinet, a console with a photograph, and a lamp on a chain."""
    r = Room(coll)
    cx, cy = -0.55, 25.7
    _floor_mat("dining_mat", coll, m["mat"], cx - 1.25, cx + 1.25, cy - 1.05, cy + 1.05)
    table = r.put("chinese_tea_table", (cx, cy), 0, z=FLOOR + 0.004, collide=True)
    tz = r.top(table)
    r.put("tea_set_01", (cx - 0.15, cy + 0.05), 20, z=tz)
    for k, (dx, dy) in enumerate(((0.2, -0.12), (0.3, 0.12), (-0.35, -0.15))):
        r.put("wooden_bowl_01", (cx + dx, cy + dy), 40 * k, z=tz)
    r.put("vintage_oil_lamp", (cx + 0.05, cy + 0.2), 0, z=tz)
    for k, (dx, dy) in enumerate(((0.0, -0.75), (0.0, 0.75), (-0.85, 0.0), (0.85, 0.0))):
        x, y = cx + dx, cy + dy
        box(f"dining_cushion_{k}", coll, x - 0.22, x + 0.22, y - 0.22, y + 0.22, FLOOR + 0.006, FLOOR + 0.075, m["cushion"], edge=0.025)
    r.put("vintage_cabinet_01", (-2.65, 25.4), 90, wall=(0, -2.97, 1), collide=True)
    con = r.put("chinese_console_table", (1.62, 25.6), -90, wall=(0, 1.97, -1), collide=True)
    r.put("standing_picture_frame_01", (1.72, 25.55), -90, z=r.top(con))
    r.put("brass_vase_01", (1.72, 26.0), 0, z=r.top(con))
    # A hurricane lamp hangs on a chain over the table.
    lamp = r.put("Lantern_01", (cx, cy), 0, z=FLOOR + 1.7)
    lt = r.top(lamp)
    tube("dining_lamp_chain", coll, [(cx, cy, lt - 0.01), (cx, cy, ZW - 0.02)], 0.004, m["iron"], sides=5)


def spare_room(coll, m, rng):
    """Shut up since the funeral: the bed, a sofa and a chair under dust sheets,
    suitcases stacked, a covered mirror against the wall."""
    r = Room(coll)
    bed = r.put("old_bed_frame", (6.9, 25.0), 90, wall=(0, 7.94, -1), collide=True)
    sofa = r.put("chinese_sofa", (4.2, 27.45), 180, wall=(1, 27.94, -1), collide=True)
    chair = r.put("chinese_armchair", (2.6, 24.0), 120, collide=True)
    bpy.context.view_layer.update()
    for k, obj in enumerate((bed, sofa, chair)):
        pts = [o.matrix_world @ v.co for o in obj.children_recursive if o.type == "MESH" for v in o.data.vertices]
        xs, ys, zs = [p.x for p in pts], [p.y for p in pts], [p.z for p in pts]
        _dust_sheet(f"spare_dust_sheet_{k}", coll, m["cotton_dirty"], min(xs), max(xs), min(ys), max(ys), max(zs), rng=rng)
    s1 = r.put("vintage_suitcase", (2.5, 26.9), 90)
    r.put("vintage_suitcase", (2.5, 26.9), 80, z=r.top(s1))
    r.put("ornate_mirror_01", (7.7, 27.3), -90, wall=(0, 7.94, -1))


def corridor(coll, m, rng):
    """Pegs with a krama and a shirt on the old back wall, sandals by the doors, a
    bench, a lamp bracket."""
    r = Room(coll)
    face = 22.0 + 0.032  # the old back wall's weatherboards
    for k, x in enumerate((-4.1, -3.7, 0.6, 1.0)):
        _peg(f"corridor_peg_{k}", coll, m["cl_trim"], (x, face, FLOOR + 1.6), (0, 1))
    _hanging_cloth("corridor_krama", coll, m["krama"], (-4.1, face + 0.07, FLOOR + 1.62), True, 0.3, 0.7, rng)
    _hanging_cloth("corridor_shirt", coll, m["cotton_dirty"], (0.6, face + 0.07, FLOOR + 1.62), True, 0.4, 0.62, rng)
    box("corridor_bench", coll, -7.6, -6.3, 22.12, 22.47, FLOOR + 0.42, FLOOR + 0.46, m["cl_trim"], edge=0.006)
    for x in (-7.5, -6.42):
        box("corridor_bench_leg", coll, x, x + 0.06, 22.15, 22.44, FLOOR, FLOOR + 0.42, m["cl_trim"])
    collider("corridor_bench", coll, -7.6, -6.3, 22.12, 22.47, FLOOR, FLOOR + 0.46)
    for k, (x, y, rot) in enumerate(((2.15, 22.35, 10), (2.35, 22.33, -8), (-1.3, 22.85, 95), (-1.12, 22.88, 80))):
        box(f"corridor_sandal_{k}", coll, x - 0.05, x + 0.05, y - 0.12, y + 0.12, FLOOR, FLOOR + 0.018, m["sandal"], edge=0.006)
    # An oil lamp on an iron bracket by the dining room doors.
    box("corridor_lamp_bracket", coll, -2.15, -2.05, CORRIDOR_FACE - 0.18, CORRIDOR_FACE, FLOOR + 1.7, FLOOR + 1.72, m["iron"])
    r.put("vintage_oil_lamp", (-2.1, CORRIDOR_FACE - 0.13), 0, z=FLOOR + 1.72)


CORRIDOR_FACE = 23.2 - 0.03


def galleries(coll, m, rng):
    """West: water jars, a basin on its stand, washing on a line. East: firewood,
    baskets, a stool and a broom."""
    r = Room(coll)
    for k, (y, s) in enumerate(((15.0, 0.95), (15.9, 0.85))):
        jar = r.put("water_jar", (-7.45, y), 30 * k, scale=s, collide=True, scan=True)
        jz = r.top(jar)
        cylinder(f"gallery_jar_lid_{k}", coll, -7.45, y, jz - 0.005, jz + 0.02, 0.19, m["cl_trim"], verts=20)
    r.put("wooden_bowl_01", (-7.42, 15.0), 0, z=r.top(jar) + 0.015)
    # A basin on a stand under the line.
    box("gallery_basin_stand", coll, -7.7, -7.25, 17.3, 17.75, FLOOR + 0.72, FLOOR + 0.76, m["cl_trim"], edge=0.005)
    for lx in (-7.68, -7.31):
        for ly in (17.32, 17.69):
            box("gallery_basin_leg", coll, lx, lx + 0.04, ly, ly + 0.04, FLOOR, FLOOR + 0.72, m["cl_trim"])
    r.put("pot_enamel_01", (-7.47, 17.52), 0, z=FLOOR + 0.76)
    # Washing line between two gallery posts, a sarong and a towel over it.
    line_z = FLOOR + 1.6  # tied to the gallery posts, under their beam
    tube("gallery_line", coll, [(-7.88, 18.0, line_z), (-7.88, 19.4, line_z - 0.06), (-7.88, 21.86, line_z)], 0.004, m["rope"], sides=4)
    _hanging_cloth("gallery_sarong", coll, m["cloth_red"], (-7.88, 19.0, line_z - 0.045), False, 0.7, 0.85, rng)
    _hanging_cloth("gallery_towel", coll, m["cotton_dirty"], (-7.88, 20.3, line_z - 0.04), False, 0.4, 0.5, rng)
    r.put("broom", (-6.12, 21.5), 0, wall=(0, -6.0 - 0.032, -1), scan=True)
    # East: firewood along the wall, baskets, a stool.
    _logs("gallery_firewood", coll, m["logs"], 6.06, 15.0, True, 0.65, 5, 5, r=0.045, rng=rng)
    _logs("gallery_firewood_2", coll, m["logs"], 6.06, 16.3, True, 0.6, 3, 4, r=0.045, rng=rng)
    r.put("basket_deep", (7.55, 18.8), 0, scan=True)
    r.put("basket_round", (7.6, 19.4), 20, scan=True)
    r.put("wooden_stool_02", (6.8, 20.6), 35)
    r.put("rice_sack", (7.55, 21.3), -15, scan=True)


def porch(coll, m, rng):
    """A jar for washing feet at the top of the stairs, sandals by the door, a bench."""
    r = Room(coll)
    jar = r.put("water_jar", (1.55, 29.05), 0, scale=0.8, collide=True, scan=True)
    r.put("wooden_bowl_01", (1.55, 29.05), 0, z=r.top(jar) + 0.002)
    for k, (x, y) in enumerate(((-0.62, 28.25), (-0.4, 28.22), (0.3, 28.2))):
        box(f"porch_sandal_{k}", coll, x - 0.05, x + 0.05, y - 0.12, y + 0.12, FLOOR, FLOOR + 0.018, m["sandal"], edge=0.006)
    box("porch_bench", coll, -2.85, -2.5, 28.2, 29.35, FLOOR + 0.4, FLOOR + 0.44, m["cl_trim"], edge=0.006)
    for y in (28.25, 29.25):
        box("porch_bench_leg", coll, -2.82, -2.53, y, y + 0.05, FLOOR, FLOOR + 0.4, m["cl_trim"])


def furnish(coll, m, seed=1933):
    rng = np.random.default_rng(seed)
    _complete_gltf_group()
    _protos_from_file()
    kitchen(coll, m, rng)
    store_room(coll, m, rng)
    dining_room(coll, m, rng)
    spare_room(coll, m, rng)
    corridor(coll, m, rng)
    galleries(coll, m, rng)
    porch(coll, m, rng)
