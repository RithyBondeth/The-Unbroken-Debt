"""A fuller, lived-in dressing pass over every room of Episode 1's re-planned house
(November 22, 2026): "make sure every single thing in the house is very detailed and
realistic, add more things, the pillows are like cube boxes, use colour posters
instead of white paper".

Beds made up on reed mats with real pillows under mosquito nets; triangular pillows
along the hall wall for guests; clothes on peg rails and lines; colour prints framed
and pinned in every room (the house atlas in tools/areas/studio_prints.json: the
Vessantara Jataka, the Phra Malai manuscript, colonial exhibition posters, the king's
portrait); books, cups, bottles, tins, baskets and Poly Haven pieces; written and
printed pages where blank paper was.

Every function takes the house collection, the materials dict (house_props.materials
over house_new_rooms.materials) and a numpy Generator.
"""
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

import colonial_house as CH
import house_props as HP
import stilt_house as SH
from colonial_parts import wall_print
from kit import ROOT, box, image_material, import_model, mesh_object, tube
from shrine_craft import Batch, place

FLOOR, ZW, T = SH.FLOOR, SH.ZW, SH.T
H_Y = SH.H["y1"]   # the old back wall, now inside the cross corridor
TEX = os.path.join(ROOT, "art-source", "textures", "ep1")
ATLAS = None


def _atlas_mat():
    global ATLAS
    if ATLAS is None:
        ATLAS = image_material("M_house_print_house", os.path.join(TEX, CH.PRINTS_SPEC["house"]["file"] + ".png"), rough=0.88)
    return ATLAS


def print_on(coll, m, name, item, centre, normal, width, framed=False, seed=0):
    """A colour print from the house atlas, pinned (curling a little, rusty pins) or in a
    dark wooden frame with a backing board, on the wall whose room face is at `centre`."""
    spec = CH.PRINTS_SPEC["house"]
    _, _, w, h = spec["items"][item]["rect"]
    height = width * h / w
    n = Vector(normal)
    right = Vector((0, 0, 1)).cross(n)
    c = Vector(centre)
    if framed:
        border, depth = 0.04, 0.028
        b = Batch(f"{name}_frame")
        for (du, dv, su, sv) in ((0, height / 2 + border / 2, width + 2 * border, border), (0, -height / 2 - border / 2, width + 2 * border, border),
                                 (width / 2 + border / 2, 0, border, height), (-width / 2 - border / 2, 0, border, height)):
            p = c + right * du + Vector((0, 0, dv)) + n * depth / 2
            size = (abs(right.x) * su + abs(n.x) * depth, abs(right.y) * su + abs(n.y) * depth, sv)
            b.box(m["cl_trim"], size, tuple(p), chamfer=0.006)
        p = c + n * 0.004
        b.box(m["cl_trim"], (abs(right.x) * width + abs(n.x) * 0.006, abs(right.y) * width + abs(n.y) * 0.006, height), tuple(p))
        b.build(coll)
        c = c + n * 0.012
        wall_print(name, coll, spec, item, _atlas_mat(), tuple(c), tuple(right), (0, 0, 1), width, curl=0.0, pins=None, seed=seed)
        # The cord it hangs from, up to a nail.
        top = c + Vector((0, 0, height / 2 + border))
        nail = top + Vector((0, 0, 0.16)) - n * 0.012
        tube(f"{name}_cord", coll, [tuple(top - right * width * 0.35), tuple(nail), tuple(top + right * width * 0.35)], 0.0015, m["iron"], sides=4)
    else:
        wall_print(name, coll, spec, item, _atlas_mat(), tuple(c + n * 0.002), tuple(right), (0, 0, 1), width, curl=0.014,
                   pins=m.get("brass") or m["iron"], seed=seed)


# ------------------------------------------------------------------ rooms


def hall(coll, m, rng):
    b = Batch("dress_hall")
    # Triangular pillows along the west wall where guests sit, a long mat under them.
    # (Clear of Yay Mey's door to the south and of the narrow door by the altar to the north.)
    for k, y in enumerate((15.95, 16.5)):
        HP.triangle_pillow(b, m, place(-2.62, y, FLOOR + 0.008, rz=math.pi / 2 + rng.normal(0, 0.05)), rng=rng)
    mesh_object("dress_hall_guest_mat", coll, [(-2.93, 15.65, FLOOR + 0.004), (-1.95, 15.65, FLOOR + 0.004), (-1.95, 16.78, FLOOR + 0.004),
                                               (-2.93, 16.78, FLOOR + 0.004)], [(0, 1, 2, 3)], m.get("mat") or m["cotton"],
                uvs=[(0, 0), (1, 0), (1, 1.13), (0, 1.13)])
    # Two stools by the front door, a pair of brass spittoons and water cups on a tray.
    for k, x in enumerate((1.6, 2.35)):
        import_model(coll, "wooden_stool_01", (x, 12.0, FLOOR), rot_deg=rng.uniform(0, 90), name=f"dress_hall_stool_{k}", collide=False)
    for k in range(3):
        HP.enamel_cup(b, m, 2.55 + 0.09 * k, 13.0, FLOOR + 0.005, rng)
    b.build(coll)
    import_model(coll, "brass_pot_01", (2.62, 13.35, FLOOR), rot_deg=30, name="dress_hall_brass_pot", collide=False)
    import_model(coll, "antique_ceramic_vase_01", (0.95, 17.25, FLOOR), rot_deg=0, name="dress_hall_vase", collide=False)
    # The king's portrait between the west door and the altar, the Vessantara painting on
    # the east wall, the Phra Malai page over the front door.
    print_on(coll, m, "dress_hall_monivong", "MONIVONG1929", (-1.45, SH.ALTAR_Y - T / 2, FLOOR + 1.9), (0, -1, 0), 0.36, framed=True, seed=1)
    print_on(coll, m, "dress_hall_vj_chariot", "VJ_CHARIOT", (3.0 - T, 16.35, FLOOR + 1.65), (-1, 0, 0), 0.62, framed=True, seed=2)
    print_on(coll, m, "dress_hall_phramalai", "PHRAMALAI2", (1.75, SH.FRONT, FLOOR + 1.75), (0, 1, 0), 0.72, seed=3)


def yaymey(coll, m, rng):
    b = Batch("dress_yaymey")
    # Her mat and net along the east wall: by the west window they hid the Krasue from
    # anyone in the room (the window is its, src/episodes/ep1/data/krasue.ts).
    HP.sleeping_mat_bed(coll, b, m, -3.55, 13.35, FLOOR, math.pi / 2, rng, mat_obj=m.get("mat"), pillows=("embroidered", "floral"))
    b.build(coll)
    HP.mosquito_net(coll, m, -4.1, -3.06, 12.3, 14.4, FLOOR, FLOOR + 1.75, "dress_yaymey_net", rng)
    print_on(coll, m, "dress_yaymey_vj_jali", "VJ_JALI", (-5.4, SH.FRONT, FLOOR + 1.6), (0, 1, 0), 0.5, framed=True, seed=4)
    print_on(coll, m, "dress_yaymey_phramalai", "PHRAMALAI4", (-4.05, SH.SPLIT - T / 2, FLOOR + 1.55), (0, -1, 0), 0.3, seed=5)
    HP.peg_rail(coll, m, "dress_yaymey_pegs", -3.9, -3.2, SH.FRONT, FLOOR + 1.62, 1, rng,
                hang=((0, "pillow_triangle", 0.9), (1, "cotton", 0.7)))


def sofa_seat(name, x, default):
    """The seat height of a sofa and the line along y where its seat meets its back: rays
    down across it at `x`. Returns (seat z, back y, +1 when the back is at the high-y side)."""
    o = bpy.data.objects.get(name)
    if o is None:
        return default
    from mathutils.bvhtree import BVHTree
    # From the mesh data (the sofa's collection is out of the view layer while the rooms
    # are dressed, so the scene's ray cast cannot see it).
    verts, polys = [], []
    for c in [o] + list(o.children_recursive):
        if c.type != "MESH":
            continue
        base = len(verts)
        verts += [c.matrix_world @ v.co for v in c.data.vertices]
        polys += [[base + i for i in p.vertices] for p in c.data.polygons]
    if not polys:
        return default
    bvh = BVHTree.FromPolygons(verts, polys)
    y0, y1 = min(v.y for v in verts), max(v.y for v in verts)
    hits = []
    for k in range(41):
        y = y0 + 0.01 + (y1 - y0 - 0.02) * k / 40
        loc, *_ = bvh.ray_cast(Vector((x, y, FLOOR + 1.5)), Vector((0, 0, -1)))
        if loc is not None and loc.z > FLOOR + 0.05:
            hits.append((y, loc.z))
    seat = [z for _y, z in hits if z > FLOOR + 0.2]
    if not seat:
        return default
    sz = min(seat)
    high = [y for y, z in hits if z > sz + 0.2]
    if not high:
        return default
    side = 1 if sum(high) / len(high) > (y0 + y1) / 2 else -1
    on_seat = [y for y, z in hits if abs(z - sz) < 0.03]
    back = max(on_seat) if side > 0 else min(on_seat)
    return sz, back, side


def parlour(coll, m, rng):
    b = Batch("dress_parlour")
    # The two cushions stand on the sofa's seat leaning on its back.
    sz, back, side = sofa_seat("house_chinese_sofa_2", 4.5, (FLOOR + 0.476, 11.68, -1))
    tilt = 1.22 * side
    y = back - side * 0.085
    HP.pillow(b, m["pillow_floral"], place(4.05, y, sz + 0.19, rz=0.15) @ Matrix.Rotation(tilt + 0.03 * side, 4, "X"), L=0.42, W=0.42, H=0.13, rng=rng)
    HP.pillow(b, m["pillow_embroidered"], place(4.95, y, sz + 0.19, rz=-0.1) @ Matrix.Rotation(tilt - 0.02 * side, 4, "X"), L=0.42, W=0.42, H=0.13, rng=rng)
    b.build(coll)
    import_model(coll, "tea_set_01", (4.5, 13.35, FLOOR + 0.5), rot_deg=20, name="dress_parlour_tea", collide=False)
    lay_tea_set("dress_parlour_tea", top_of("house_chinese_tea_table_1", FLOOR + 0.5))
    import_model(coll, "mantel_clock_01", (3.25, 13.3, FLOOR + 0.66), rot_deg=90, name="dress_parlour_clock", collide=False)
    import_model(coll, "ceramic_vase_02", (3.22, 12.6, FLOOR + 0.66), rot_deg=0, name="dress_parlour_vase", collide=False)
    import_model(coll, "carved_wooden_elephant", (3.2, 13.75, FLOOR + 0.66), rot_deg=90, name="dress_parlour_elephant", collide=False)
    print_on(coll, m, "dress_parlour_cappiello", "CAPPIELLO1922", (3.65, SH.SPLIT - T / 2, FLOOR + 1.55), (0, -1, 0), 0.5, seed=6)
    print_on(coll, m, "dress_parlour_dellepiane", "DELLEPIANE1922", (5.55, SH.FRONT, FLOOR + 1.6), (0, 1, 0), 0.34, seed=7)
    print_on(coll, m, "dress_parlour_vj_return", "VJ_RETURN", (6.0 - T, 12.0, FLOOR + 1.75), (-1, 0, 0), 0.46, framed=True, seed=8)


def vuthy(coll, m, rng):
    b = Batch("dress_vuthy")
    HP.sleeping_mat_bed(coll, b, m, 4.1, 18.3, FLOOR, 0.0, rng, mat_obj=m.get("mat"), pillows=("gingham",))
    HP.books(b, m, 3.4, 3.9, 21.55, FLOOR + 0.35, 0.16, rng, toward=-1)
    b.build(coll)
    print_on(coll, m, "dress_vuthy_marseille", "MARSEILLE1906", (6.0 - T, 18.75, FLOOR + 1.55), (-1, 0, 0), 0.42, seed=9)
    HP.peg_rail(coll, m, "dress_vuthy_pegs", 5.0, 5.85, H_Y - T, FLOOR + 1.65, -1, rng,
                hang=((0, "cotton", 0.75), (1, "pillow_gingham", 0.6)))
    import_model(coll, "vintage_suitcase", (5.45, 19.15, FLOOR), rot_deg=95, name="dress_vuthy_suitcase", collide=False)



def loom_room(coll, m, rng):
    # Silk hung to air on a pole across the west wall, and folded lengths on a stool.
    import_model(coll, "painted_wooden_stool", (-5.45, 18.15, FLOOR), rot_deg=10, name="dress_loom_stool", collide=False)
    seat = top_of("dress_loom_stool", FLOOR + 0.405)
    b = Batch("dress_loom")
    b.tube(m["peg_wood"], [(-5.85, 16.25, FLOOR + 1.7), (-5.85, 17.95, FLOOR + 1.7)], 0.018, sides=8)
    # Two pegs out of the west wall carry the pole's ends (alone it hung in the air).
    for y in (16.3, 17.9):
        b.box(m["peg_wood"], (0.13, 0.035, 0.05), (-5.89, y, FLOOR + 1.665), chamfer=0.006)
    for k, (key, y0, y1) in enumerate((("silk", 16.3, 16.85), ("pillow_triangle", 16.95, 17.4), ("silk", 17.45, 17.9))):
        HP.hung_cloth(coll, m, m.get(key) or m["pillow_triangle"], f"dress_loom_silk_{k}", (-5.85, y0, FLOOR + 1.72), (-5.85, y1, FLOOR + 1.72), 1.05, folds=4)
    for k in range(5):
        b.box(m.get("silk") or m["pillow_triangle"], (0.38, 0.28, 0.03), (-5.45 + rng.normal(0, 0.01), 18.15 + rng.normal(0, 0.01), seat + 0.014 + 0.032 * k),
              chamfer=0.012)
    b.build(coll)


def washing(coll, m, rng):
    # White cloths drying on a cord tied wall to wall across the room's north side (a 2 mm
    # line that stopped short in mid-air left them floating), an iron hook at each end.
    # (Across the whole room it crossed the north door: it runs from the west wall to a nail
    # in the north wall short of the door.)
    z = FLOOR + 1.85
    xs, ys, sags = (-2.94, -2.0, -1.0, 0.1), (21.6, 21.64, 21.74, 21.93), (0.0, 0.035, 0.04, 0.0)
    tube("dress_wash_line", coll, [(x, y, z - s) for x, y, s in zip(xs, ys, sags)], 0.005, m.get("rope") or m["cotton"], sides=6)
    box("dress_wash_line_hook", coll, -2.94, -2.88, 21.592, 21.608, z - 0.012, z + 0.012, m["iron"])
    box("dress_wash_line_nail", coll, 0.092, 0.108, 21.9, 21.94, z - 0.008, z + 0.008, m["iron"])
    for k, x in enumerate((-2.6, -1.9, -1.15)):
        y = float(np.interp(x, xs, ys))
        top = z - float(np.interp(x, xs, sags)) + 0.005
        HP.hung_cloth(coll, m, m["cotton"], f"dress_wash_cloth_{k}", (x - 0.28, y, top), (x + 0.28, y + 0.01, top),
                      rng.uniform(0.7, 1.1), folds=5)
    import_model(coll, "wooden_bucket_01", (-0.35, 21.3, FLOOR), rot_deg=30, name="dress_wash_bucket", collide=False)
    import_model(coll, "jug_01", (2.45, 20.85, FLOOR), rot_deg=0, name="dress_wash_jug", collide=False)


def corridors(coll, m, rng):
    b = Batch("dress_corridors")
    # Sandals left outside the rooms, a broom, a water jar at the cross corridor's end.
    for k, (x, y) in enumerate(((-0.45, 25.95), (0.45, 29.95), (-0.48, 24.2), (0.5, 26.2))):
        for s in (-1, 1):
            b.box(m["peg_wood"], (0.1, 0.24, 0.014), (x + 0.065 * s, y + 0.02 * s, FLOOR + 0.007), chamfer=0.005)
    HP.kerosene_tin(b, m, 7.55, 22.5, FLOOR, 0.3)
    b.build(coll)
    import_model(coll, "jug_01", (7.6, 23.05, FLOOR), rot_deg=40, name="dress_corr_jug", collide=False)
    # A krama and a work shirt left on the pegs by the cross corridor's west end.
    HP.peg_rail(coll, m, "dress_corr_pegs", -6.7, -5.3, SH.CORR - T / 2, FLOOR + 1.65, -1, rng,
                hang=((0, "pillow_gingham", 0.8), (2, "cotton", 0.7), (3, "pillow_triangle", 0.65)))
    # The Vessantara painting of Jujaka, the brahmin who takes the children, hung in the
    # long corridor; the army's return on the old back wall in the cross corridor.
    print_on(coll, m, "dress_corr_vj_jujaka", "VJ_JUJAKA", (SH.LC - T / 2, 27.05, FLOOR + 1.55), (-1, 0, 0), 0.5, framed=True, seed=10)
    print_on(coll, m, "dress_corr_ligue", "LIGUE1930", (-3.6, H_Y + 0.045, FLOOR + 1.6), (0, 1, 0), 0.62, seed=11)


LIGHTS = []   # (x, y, z) of lamps the dressing lights, for the preview to put a light in


def bedroom(coll, m, rng):
    """Sok's bedroom: his mat made up under the net at the far end, his clothes on the pegs,
    a low stool by the bed with the oil lamp he read by, his trunk, sandals by the door."""
    b = Batch("dress_bedroom")
    HP.sleeping_mat_bed(coll, b, m, -5.6, 29.15, FLOOR, 0.0, rng, mat_obj=m.get("mat"), pillows=("embroidered", "gingham"))
    for s_ in (-1, 1):
        b.box(m["peg_wood"], (0.1, 0.25, 0.014), (-1.25 + 0.07 * s_, 28.7 + 0.02 * s_, FLOOR + 0.007), chamfer=0.005)
    b.build(coll)
    HP.mosquito_net(coll, m, -6.65, -4.55, 28.6, 29.7, FLOOR, FLOOR + 1.8, "dress_bedroom_net", rng)
    HP.peg_rail(coll, m, "dress_bedroom_pegs", -6.6, -5.2, SH.ROW2 - T / 2, FLOOR + 1.65, -1, rng,
                hang=((0, "pillow_gingham", 0.85), (1, "cotton", 0.75), (2, "pillow_triangle", 0.7)))
    # Against the south wall facing into the room (along the corridor wall it showed the door its bare back).
    import_model(coll, "vintage_wooden_drawer_01", (-2.5, SH.ROW1 + T / 2 + 0.45, FLOOR), rot_deg=180, name="dress_bedroom_drawer", collide=False)
    import_model(coll, "chinese_stool", (-4.15, 28.5, FLOOR), rot_deg=10, name="dress_bedroom_stool", collide=False)
    bpy.context.view_layer.update()
    stool = bpy.data.objects.get("dress_bedroom_stool")
    pts = [o.matrix_world @ Vector(c) for o in stool.children_recursive if o.type == "MESH" for c in o.bound_box] if stool else []
    top = max(p.z for p in pts) if pts else FLOOR + 0.45
    import_model(coll, "vintage_oil_lamp", (-4.15, 28.5, top), rot_deg=0, name="dress_bedroom_lamp", collide=False)
    LIGHTS.append((-4.05, 28.5, top + 0.22))
    import_model(coll, "vintage_suitcase", (-3.0, 30.25, FLOOR), rot_deg=0, name="dress_bedroom_trunk", collide=False)


def kanha(coll, m, rng, bed_top):
    """Her iron bed made up as it was, a thin mattress, her pillow. (Her mosquito net knotted
    up over it read as a white paper lamp; the user's review of Nov 25 hung a real kerosene
    lamp there instead: house_polish.py.)"""
    x, y, z = bed_top
    b = Batch("dress_kanha")
    b.grid(m["pillow_floral"], lambda u, v: (x - 0.9 + 1.8 * u, y - 0.4 + 0.8 * v,
                                             z + 0.07 * (1 - abs(2 * u - 1) ** 6) ** 0.3 * (1 - abs(2 * v - 1) ** 6) ** 0.3),
           24, 12, uv=lambda u, v: (u * 6, v * 2.6))
    HP.pillow(b, m["pillow_embroidered"], place(x - 0.7, y, z + 0.06, rz=math.pi / 2 + 0.1), L=0.5, W=0.3, H=0.12, rng=rng)
    b.build(coll)
    print_on(coll, m, "dress_kanha_vj", "VJ_KANHA", (4.35, SH.ROW1 - T / 2, FLOOR + 1.45), (0, -1, 0), 0.6, framed=True, seed=12)
    HP.peg_rail(coll, m, "dress_kanha_pegs", 5.4, 6.3, SH.ROW1 - T / 2, FLOOR + 1.3, -1, rng,
                hang=((0, "pillow_floral", 0.55, "dress"), (1, "pillow_gingham", 0.5, "dress")))
    import_model(coll, "wicker_basket_01", (1.45, 26.9, FLOOR), rot_deg=40, name="dress_kanha_basket", collide=False)


def lay_tea_set(name, table_top):
    """The Poly Haven tea set comes laid out piece by piece for display; laid for guests,
    each cup stands on a saucer and the pot and the sugar bowl on the square plate."""
    root = bpy.data.objects.get(name)
    if root is None:
        return
    bpy.context.view_layer.update()
    parts = {o.name.split(".")[0].replace("tea_set_01_", ""): o for o in root.children_recursive if o.type == "MESH"}

    def box_(o):
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])

    def put(obj, on, extra=(), dx=0.0, dy=0.0):
        if obj is None or on is None:
            return
        lo, hi = box_(obj)
        blo, bhi = box_(on)
        d = Vector(((blo.x + bhi.x) / 2 + dx - (lo.x + hi.x) / 2, (blo.y + bhi.y) / 2 + dy - (lo.y + hi.y) / 2, bhi.z - 0.002 - lo.z))
        for o in (obj, *extra):
            if o is not None:
                o.matrix_world = Matrix.Translation(d) @ o.matrix_world
        bpy.context.view_layer.update()

    put(parts.get("cup_small_01"), parts.get("saucer_circular_03"))
    put(parts.get("cup_small_02"), parts.get("saucer_circular_04"))
    put(parts.get("teapot_01"), parts.get("plate_large_square_01"), (parts.get("teapot_01_lid"),), dx=-0.04)
    put(parts.get("sugar_cup_01"), parts.get("plate_large_circular_03"), (parts.get("sugar_cup_01_lid"),))


def top_of(name, default):
    """The height of the top of a placed piece of furniture (its meshes' highest point)."""
    o = bpy.data.objects.get(name)
    if o is None:
        return default
    bpy.context.view_layer.update()
    pts = [c.matrix_world @ Vector(v) for c in [o] + list(o.children_recursive) if c.type == "MESH" for v in c.bound_box]
    return max(p.z for p in pts) if pts else default


def locked(coll, m, rng):
    b = Batch("dress_locked")
    # The bottles stand at the back of the table, behind the open ledger.
    tz = top_of("locked_table", FLOOR + 0.79)
    for k in range(5):
        HP.bottle(b, m, -3.3 + 0.07 * k, 33.25 + rng.normal(0, 0.03), tz, rng, h=rng.uniform(0.18, 0.28))
    HP.kerosene_tin(b, m, -1.35, 31.0, FLOOR, 0.2)
    b.build(coll)
    HP.papers(coll, m, -7.5, -1.3, 31.0, 33.7, FLOOR, 12, rng, name="dress_locked_papers", news=0.35)
    # Postcards and a photograph that fell from the ledgers, face up among the pages.
    from colonial_parts import wall_print
    cards = image_material("M_dress_cards", os.path.join(TEX, CH.PRINTS_SPEC["cards"]["file"] + ".png"), rough=0.9)
    for k, (item, x, y, a) in enumerate((("DIEU1662", -5.1, 31.6, 0.4), ("DIEUPROM", -2.6, 32.2, -0.7), ("THRONE1910", -6.4, 33.1, 1.9))):
        wall_print(f"dress_locked_card_{k}", coll, CH.PRINTS_SPEC["cards"], item, cards, (x, y, FLOOR + 0.004 + 0.001 * k),
                   (math.cos(a), math.sin(a), 0), (-math.sin(a), math.cos(a), 0), 0.15, curl=0.004, pins=None, seed=60 + k)
    import_model(coll, "pot_enamel_01", (-7.4, 31.1, FLOOR), rot_deg=0, name="dress_locked_basin", collide=False)


def store(coll, m, rng):
    b = Batch("dress_store")
    for k, (x, y) in enumerate(((7.55, 27.75), (7.55, 28.05), (7.25, 27.75))):
        HP.kerosene_tin(b, m, x, y, FLOOR, rng.uniform(-0.2, 0.2))
    for k in range(6):
        HP.bottle(b, m, 5.2 + 0.08 * k, 30.35, FLOOR, rng, h=rng.uniform(0.22, 0.3))
    b.build(coll)
    for k, (x, y) in enumerate(((1.25, 28.0), (1.3, 30.1))):
        import_model(coll, "wicker_basket_01", (x, y, FLOOR), rot_deg=rng.uniform(0, 90), name=f"dress_store_basket_{k}", collide=False)
    import_model(coll, "wooden_crate_01", (6.3, 28.0, FLOOR), rot_deg=5, name="dress_store_crate", collide=False)


def attic(coll, m, rng):
    jz = ZW + 0.165
    # (The drawer and the bucket stand clear of the suitcases and the folding stool.)
    for k, (mid, x, y, rot, z) in enumerate((("wooden_stool_02", -1.2, 15.55, 70, 0.0), ("wooden_crate_01", 3.4, 16.5, 20, 0.0),
                                            ("vintage_wooden_drawer_01", -3.0, 16.5, 180, 0.0), ("wooden_bucket_02", 0.75, 12.75, 0, 0.0),
                                            ("wicker_basket_01", 2.55, 18.9, 30, 0.0), ("Lantern_01", -4.95, 15.6, 0, 0.0))):
        import_model(coll, mid, (x, y, jz + z), rot_deg=rot, name=f"dress_attic_{mid}_{k}", collide=False)
    # Bundles of old ledgers tied with string, and a baby's hammock cradle hung from a rafter.
    b = Batch("dress_attic")
    for k, (x, y) in enumerate(((-2.3, 16.55), (-2.0, 16.6), (-2.15, 16.58))):
        z = jz + 0.07 * k
        b.box(m["ledger"] if "ledger" in m else m["book_brown"], (0.32, 0.24, 0.07), (x, y, z + 0.035), chamfer=0.004)
        b.tube(m["cotton"], [(x, y - 0.125, z), (x, y - 0.125, z + 0.072), (x, y + 0.125, z + 0.072), (x, y + 0.125, z)], 0.002, sides=4)
    cx, cy = 1.6, 18.6
    top = ZW + 2.2
    for s in (-1, 1):
        b.tube(m["cotton"], [(cx + 0.5 * s, cy, top), (cx + 0.45 * s, cy, jz + 0.85)], 0.004, sides=4)
    b.grid(m["pillow_gingham"], lambda u, v: (cx - 0.45 + 0.9 * u, cy - 0.22 + 0.44 * v,
                                              jz + 0.85 - 0.28 * math.sin(math.pi * u) - 0.06 * math.sin(math.pi * v) ** 0.5), 16, 8,
           uv=lambda u, v: (u * 3, v * 1.5))
    b.build(coll)


def furnish(coll, m, rng, kanha_bed_top):
    hall(coll, m, rng)
    yaymey(coll, m, rng)
    parlour(coll, m, rng)
    vuthy(coll, m, rng)
    loom_room(coll, m, rng)
    washing(coll, m, rng)
    corridors(coll, m, rng)
    bedroom(coll, m, rng)
    kanha(coll, m, rng, kanha_bed_top)
    locked(coll, m, rng)
    store(coll, m, rng)
    attic(coll, m, rng)
