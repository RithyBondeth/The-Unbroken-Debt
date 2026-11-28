"""The village road's shop interiors, dressed piece by piece (the user, Nov 25, 2026: "Inside
every single shop also even small items inside the shop should be more very detailed and
very realistic").

The driving scene's builder (taxi_roadside_details._build_detailed_shop) furnishes its shops
for a car going past: bottles are seven-sided sticks, tools are slats, the goods are plain
blocks. Here, after it has built a shop, everything small it put inside and on the veranda
is taken out (`strip`: its mesh islands, by place and size; walls, posts, doors, roofs,
signs, posters and lamps stay), the real scanned and Poly Haven props it placed are swapped
for far more detailed versions of themselves (`upgrade_props`), and each trade is furnished
again in detail (`DRESS`): shelving stocked tier by tier with labelled goods, counters,
the barber's chairs, the dentist's chair, the motorbike in for repair, the noodle cart.

Each shop's new things are one object per material (shop_goods.Kit), named
vroad_goods_<shop>_<material>, so the game can draw them only near (ActOne).
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

import shop_fixtures as F
import shop_goods as G
from shop_goods import T

ZI = 0.185       # the interior floor's top (the builder's deck at 0.14, 0.09 thick)
ZV = 0.178       # the veranda planks' top
BACK = -3.2      # the back wall's inner face

# ------------------------------------------------------------------ taking out

STRIP = ("posts", "table_wood", "krama", "hol_silk", "news", "kantel", "iron", "shade", "bulb", "fluoro", "red_props",
         "blue_props", "amber_glass", "green_glass", "white_props", "mirror", "rubber", "crt", "bamboo", "win_glow",
         "noodle_glow", "foliage", "leather_barber", "linen_towel", "deck", "walls", "concrete", "wire_local")


def _islands(me):
    """Vertex index sets of a mesh's connected pieces."""
    n = len(me.vertices)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for e in me.edges:
        a, b = find(e.vertices[0]), find(e.vertices[1])
        if a != b:
            parent[a] = b
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def _keep(lo, hi, hw, suffix):
    """Whether a piece of the builder's shop stays: structure, signs, lamps and things hung
    high, or anything not wholly inside the rooms or on the veranda."""
    ext = hi - lo
    if max(ext) >= 2.6 and (ext.z > 2.0 or lo.z < 0.15 or lo.z > 2.0):
        return True                      # walls, floors, beams, rafters
    if (lo.x > -3.22 and hi.x < -0.04 and abs(lo.y) < hw and abs(hi.y) < hw and lo.z > 1.95 and hi.z < 2.3
            and max(ext) < 0.3):
        return False                     # bottles left standing on a stripped shelf's top
    if lo.z > 2.0:
        return True                      # lamps, festoons, the ceiling's beams
    if (lo.x + hi.x) / 2 > 1.6 and max(ext) >= 1.2:
        return True                      # the veranda's railings and fascia
    if ext.z > 0.9 and ext.x < 0.12 and ext.y < 0.12:
        return True                      # posts, the downspout
    if (lo.x + hi.x) / 2 > 1.68 and ext.x < 0.08 and ext.y < 0.08:
        return True                      # the veranda railing's pickets
    if hi.x < -2.9 and ext.x < 0.12 and ext.y * ext.z > 0.4:
        return True                      # mirrors and boards flat on the back wall
    if suffix == "noodle_glow":
        return False                     # the solid glowing food cases: rebuilt in glass
    if suffix == "win_glow" and abs(lo.y) < hw - 0.2 and abs(hi.y) < hw - 0.2 and hi.x > -3.2 and lo.z > 0.3 and ext.z < 1.0:
        return False                     # glowing vitrines (the side windows' panes stay)
    inside = lo.x > -3.22 and hi.x < -0.04 and abs(lo.y) < hw - 0.03 and abs(hi.y) < hw - 0.03 and lo.z > 0.15 and hi.z < 2.32
    veranda = lo.x > 0.06 and hi.x < 2.1 and abs(lo.y) < hw - 0.03 and abs(hi.y) < hw - 0.03 and lo.z > 0.15 and hi.z < 2.32
    verge = (suffix in ("iron", "rubber", "bamboo", "blue_props", "red_props") and lo.x > 1.9 and hi.x < 3.0
             and lo.z > -0.5 and hi.z < 1.3)
    return not (inside or veranda or verge)


def strip(idx, sp):
    """Takes the builder's small furnishings out of shop `idx`; returns how many pieces went."""
    import bmesh

    hw = sp["hw"]
    gone = 0
    for suffix in STRIP:
        obj = bpy.data.objects.get(f"vroad_shop_{idx}_{suffix}")
        if obj is None or obj.type != "MESH":
            continue
        me = obj.data
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        drop = set()
        for isl in _islands(me):
            pts = co[isl]
            lo, hi = Vector(pts.min(0)), Vector(pts.max(0))
            if not _keep(lo, hi, hw, suffix):
                drop.update(isl)
                gone += 1
        if not drop:
            continue
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.verts[i] for i in drop], context="VERTS")
        bm.to_mesh(me)
        bm.free()
        if not len(me.vertices):
            bpy.data.objects.remove(obj, do_unlink=True)
    # The props it placed inside the rooms go too (the dressing places its own).
    Minv = shop_M(idx).inverted()
    for o in list(bpy.data.objects):
        if not o.name.startswith(f"vroad_shop_{idx}_") or o.type != "MESH":
            continue
        if any(o.name.startswith(f"vroad_shop_{idx}_{s}") for s in STRIP):
            continue
        p = Minv @ o.matrix_world.translation
        if -3.22 < p.x < -0.04 and abs(p.y) < hw and 0.1 < p.z < 2.2:
            bpy.data.objects.remove(o, do_unlink=True)
            gone += 1
    return gone


_SHOP_M = {}


def shop_M(idx):
    return _SHOP_M[idx]


# ------------------------------------------------------------------ real props, in detail

_TEMPLATES = {}


def ph(name, budget):
    """A Poly Haven model as a template, decimated to `budget` (the builder used ~400)."""
    import taxi_roadside_details as TRD

    key = (name, budget)
    if key not in _TEMPLATES:
        objs = TRD._load_decimated_polyhaven(name, budget, TRD.full_gltf_group, TRD.import_glb)
        for o in objs:
            o.name = f"tpl_vgoods_{name}_{budget}"
        _TEMPLATES[key] = objs
    return _TEMPLATES[key]


def scan(file, budget):
    """A scanned prop (art-source/library/scans) as templates, each part to `budget` triangles."""
    import taxi_roadside_details as TRD

    key = (file, budget)
    if key not in _TEMPLATES:
        objs = TRD._load_decimated_scan(file, 0.999, TRD.full_gltf_group, TRD.import_glb)
        for o in objs:
            weld(o)
            tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
            if tris > budget * 1.1:
                bpy.ops.object.select_all(action="DESELECT")
                o.select_set(True)
                bpy.context.view_layer.objects.active = o
                mod = o.modifiers.new("vgoods_lod", "DECIMATE")
                mod.ratio = budget / tris
                mod.use_collapse_triangulate = True
                bpy.ops.object.modifier_apply(modifier=mod.name)
            o.name = f"tpl_vgoods_{file[:-4]}_{budget}"
            o.hide_render = True
        _TEMPLATES[key] = objs
    return _TEMPLATES[key]


def weld(o, dist=1e-4):
    """Merges a scan's split vertices. Several scans are exported as loose triangles: decimated
    as they are, the clay stove fell into 6000 shards with daylight between them."""
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    seen, specks = set(), []
    for v in bm.verts:
        if v in seen:
            continue
        isl, stack = [], [v]
        seen.add(v)
        while stack:
            a = stack.pop()
            isl.append(a)
            for e in a.link_edges:
                w = e.other_vert(a)
                if w not in seen:
                    seen.add(w)
                    stack.append(w)
        if len(isl) <= 12:
            specks.extend(isl)
    if specks:
        bmesh.ops.delete(bm, geom=specks, context="VERTS")
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()


def place(coll, tpls, Mw, name):
    out = []
    for src in tpls:
        c = src.copy()
        c.data = src.data
        coll.objects.link(c)
        c.matrix_world = Mw @ src.matrix_world
        c.hide_render = False
        c.name = name
        out.append(c)
    return out


def drop_templates():
    for objs in _TEMPLATES.values():
        for o in objs:
            if o.name in bpy.data.objects:
                bpy.data.objects.remove(o, do_unlink=True)
    _TEMPLATES.clear()


PH_DETAIL = {"bananas": 2600, "wooden_table_02": 3200, "wooden_stool_01": 2400, "folding_wooden_stool": 2400,
             "painted_wooden_shelves": 3200, "vintage_cabinet_01": 3600, "ornate_mirror_01": 2400, "wooden_crate_01": 1600,
             "wicker_basket_01": 3600, "wooden_bucket_01": 2000, "pot_enamel_01": 1800, "jug_01": 1800, "oil_tin": 1600,
             "tea_set_01": 3000, "wooden_ladder_02": 1600, "vintage_oil_lamp": 2600}
# (The water jar scan is broken past welding, 1800 loose pieces: rain_jar models it instead.)
SCAN_DETAIL = {"rice_sack": 3500, "basket_deep": 4000, "clay_stove": 3500, "kettle": 2500,
               "cooking_pot": 2500, "broom": 2500, "jar_handles": 3500, "basket_round": 3500, "winnowing_tray": 3000}


def upgrade_props(coll):
    """The builder's scanned and Poly Haven props kept on the verandas, swapped for versions of
    themselves with several times the detail (same model, same place)."""
    n = 0
    scans = {}
    for o in list(coll.objects):
        if o.type != "MESH" or not o.name.startswith("vroad_shop_") or o.name.count("_") < 3:
            continue
        rest = o.name.split("_", 3)[-1].split(".")[0]
        if rest.startswith("ph_"):
            model = rest[3:]
            if model in PH_DETAIL:
                tpl = ph(model, PH_DETAIL[model])
                if tpl:
                    o.data = tpl[0].data
                    n += 1
        elif rest == "water_jar":
            bpy.data.objects.remove(o, do_unlink=True)
            n += 1
        elif rest in SCAN_DETAIL:
            key = (o.name.split(".")[0], tuple(round(v, 3) for row in o.matrix_world for v in row))
            scans.setdefault(key, []).append(o)
    for (name, _m), objs in scans.items():
        rest = name.split("_", 3)[-1]
        tpl = scan(f"{rest}.glb", SCAN_DETAIL[rest])
        if not tpl:
            continue
        mw = objs[0].matrix_world.copy()
        for o in objs:
            bpy.data.objects.remove(o, do_unlink=True)
        place(coll, tpl, mw, name)
        n += 1
    return n


# ------------------------------------------------------------------ fixings and common things

def wall_peg(K, x, wall_y, z, inward, length=0.07):
    """A turned wooden peg driven into a side wall (its face at wall_y, `inward` +1/-1 into the
    room), for a tyre, an inner tube, a coil to hang on."""
    G.cylm(K["shop_dark_wood"], T(0, 0, 0), (x, wall_y - inward * 0.01, z), (x, wall_y + inward * length, z), 0.009, segs=8)
    G.sphere(K["shop_dark_wood"], T(0, 0, 0), (x, wall_y + inward * length, z), 0.013, 8, 5)


JAR = [(0.0, 0.0), (0.17, 0.0), (0.24, 0.06), (0.33, 0.25), (0.36, 0.42), (0.32, 0.6), (0.2, 0.74),
       (0.13, 0.78), (0.14, 0.82), (0.155, 0.85), (0.12, 0.85), (0.11, 0.8)]


def rain_jar(K, M, s=0.8, rng=None):
    """The big glazed Martaban jar (ពាង) catching the downspout's water at the veranda's
    corner: a dark brown glaze running thin at the shoulder, raised bands, the water dark in
    it, a plank lid slid half off and a coconut-shell dipper on it. (The scanned jar it
    replaces fell apart into loose glassy shards.)"""
    G.lathe(K["shop_glaze"], [(r * s, h * s) for r, h in JAR], M, segs=36)
    for z, r in ((0.25, 0.332), (0.6, 0.322)):
        G.torus(K["shop_glaze"], M, (0, 0, z * s), (0, 0, 1), r * s, 0.006, n=40, m=5)
    G.lathe(K["glaze_tan"], [(0.2 * s, 0.735 * s), (0.135 * s, 0.775 * s), (0.142 * s, 0.82 * s), (0.157 * s, 0.85 * s),
                            (0.12 * s, 0.852 * s)], M, segs=36, cap_bottom=False)
    G.lathe(K["water_dark"], [(0.0, 0.74 * s), (0.2 * s, 0.74 * s)], M, segs=24, cap_bottom=False)
    top = 0.852 * s
    L = M @ T(0.07, -0.05, top, yaw=0.4)
    G.lathe(K["shop_table_wood"], [(0.0, 0.0), (0.2 * s, 0.0), (0.2 * s, 0.022), (0.0, 0.022)], L, segs=24)
    G.boxm(K["shop_table_wood"], L, (0.0, 0.0, 0.03), (0.04, 0.3 * s, 0.016))
    D = L @ T(0.03, 0.06, 0.022, yaw=1.2)
    G.lathe(K["coconut"], [(0.0, 0.0), (0.03, 0.002), (0.055, 0.02), (0.068, 0.05), (0.07, 0.065), (0.066, 0.065),
                          (0.062, 0.05), (0.05, 0.024), (0.0, 0.008)], D, segs=16)
    G.cylm(K["shop_bamboo"], D, (0.05, 0, 0.05), (0.32, 0, 0.07), 0.009, segs=6)


def spirit_shrine(K, M):
    """The Chinese-Khmer spirit shelf by the shop door (M on the front wall's face, +x out):
    a red lacquered shelf on two brackets, its gilt-edged backboard and red paper, a little
    tiled roof on gilt columns, two electric candles glowing red, a cup of incense sticks in
    ash, a cup of water and a hand of bananas."""
    red, gold = K["plastic_red"], K["gold_paint"]
    G.boxm(red, M, (0.13, 0, 0.0), (0.26, 0.34, 0.024), bevel=0.004)
    G.boxm(gold, M, (0.258, 0, 0.0), (0.006, 0.344, 0.03))
    for y in (-0.13, 0.13):
        G.extrude_outline(K["shop_dark_wood"], M @ T(0, y, -0.012, tilt=(math.pi / 2, 0)),
                          [(0.0, 0.0), (0.2, 0.0), (0.2, -0.02), (0.02, -0.16), (0.0, -0.16)], 0.02)
    G.boxm(red, M, (0.012, 0, 0.22), (0.024, 0.34, 0.42), bevel=0.003)
    for y in (-0.165, 0.165):
        G.boxm(gold, M, (0.026, y, 0.22), (0.006, 0.012, 0.42))
    G.boxm(gold, M, (0.026, 0, 0.425), (0.006, 0.34, 0.012))
    G.wall_paper(K, M @ T(0.025, 0, 0.23, yaw=math.pi / 2), 0.14, 0.2, "shrine_paper")
    for y in (-0.15, 0.15):
        G.cylm(gold, M, (0.22, y, 0.012), (0.22, y, 0.352), 0.009, segs=8)
    for side in (-1, 1):
        G.boxm(red, M @ T(0.13, side * 0.1, 0.38, tilt=(-side * 0.45, 0)), (0, 0, 0), (0.3, 0.24, 0.016), bevel=0.003)
    G.cylm(gold, M, (-0.0, 0, 0.43), (0.28, 0, 0.43), 0.012, segs=8)
    for y in (-0.1, 0.1):
        G.lathe(K["plastic_red"], [(0.0, 0.0), (0.022, 0.0), (0.022, 0.012), (0.012, 0.016), (0.012, 0.11), (0.0, 0.11)],
                M @ T(0.15, y, 0.012), segs=12)
        G.lathe(K["led_red"], [(0.0, 0.11), (0.009, 0.112), (0.01, 0.125), (0.005, 0.14), (0.0, 0.145)], M @ T(0.15, y, 0.012),
                segs=10)
    C = M @ T(0.17, 0.0, 0.012)
    G.lathe(K["brass"], [(0.0, 0.0), (0.03, 0.0), (0.038, 0.01), (0.04, 0.045), (0.036, 0.05), (0.0, 0.05)], C, segs=16)
    G.lathe(K["paper"], [(0.0, 0.046), (0.035, 0.046), (0.0, 0.047)], C, segs=14, cap_bottom=False)
    for k in range(5):
        a = k * 1.3
        G.cylm(K["incense"], C, (math.cos(a) * 0.012, math.sin(a) * 0.012, 0.03),
               (math.cos(a) * 0.03, math.sin(a) * 0.03, 0.2 + 0.01 * k), 0.0018, segs=4)
        G.sphere(K["led_red"], C, (math.cos(a) * 0.03, math.sin(a) * 0.03, 0.2 + 0.01 * k), 0.0028, 5, 3)
    G.tumbler(K, M @ T(0.09, -0.06, 0.012), r=0.02, h=0.05, liquid="water")
    for k in range(4):
        G.cylm(K["plastic_yellow"], M, (0.08 + k * 0.012, 0.07, 0.023), (0.05 + k * 0.012, 0.13, 0.041), 0.011, 0.008, segs=8)


def shrine_at(sp):
    """Where the spirit shelf hangs on the front wall: beside the doorway, the side away
    from the barber's chairs, clear of the doorway's gate and the flank's poster."""
    door_w = 1.95
    return 0.05, (1.0 if sp["trade"] == "barber" else -1.0) * (door_w / 2 + 0.25), 1.86


def doorway_curtain(K, y0, y1, z_top=2.5, z_bottom=0.24, x0=-0.03):
    """A silk curtain on a rod across the doorway (between the jambs, behind the folded-back
    doors), gathered to one side and hung in soft folds (it was a flat blue slab)."""
    G.cylm(K["shop_iron"], T(0, 0, 0), (x0, -0.975, z_top + 0.03), (x0, 0.975, z_top + 0.03), 0.009, segs=8)
    bm = K["shop_hol_silk"]
    nu, nv = 28, 16
    rows = []
    for j in range(nv + 1):
        t = j / nv
        z = z_top - (z_top - z_bottom) * t
        row = []
        for i in range(nu + 1):
            u = i / nu
            y = y0 + (y1 - y0) * u
            folds = 0.028 * math.sin(u * math.pi * 11) * (0.6 + 0.4 * t)
            x = x0 + folds
            row.append(bm.verts.new((x, y, z)))
        rows.append(row)
    for a, b in zip(rows, rows[1:]):
        for i in range(nu):
            bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
    for i in range(0, nu + 1, 4):
        G.torus(K["shop_iron"], T(x0, y0 + (y1 - y0) * i / nu, z_top + 0.03), (0, 0, 0), (0, 1, 0), 0.016, 0.0025, n=10, m=3)


# ------------------------------------------------------------------ stocking shelves

def stock_tier(K, M, y0, y1, depth, kind, rng, labels=None):
    """Fills one shelf from y0 to y1 (its front edge at local x `depth`, the plank's top at
    z 0) with one kind of goods, in rows two deep, the odd one turned or missing."""
    labels = labels or []
    y = y0
    k = 0
    while y < y1:
        lab = labels[k % len(labels)] if labels else None
        if kind == "bottles":
            if rng.random() > 0.08:
                for row in (depth - 0.06, depth - 0.15):
                    G.bottle(K, M @ T(row, y + 0.035, 0, yaw=rng.uniform(-0.5, 0.5)),
                             ("sauce", "oil", "beer", "spirit")[k % 4], liquid=_LIQ.get(lab), label=lab,
                             glass="glass_amber" if lab in ("beer",) else None, fill=rng.uniform(0.75, 0.95), segs=12)
            y += 0.085
        elif kind == "small_bottles":
            for row in (depth - 0.05, depth - 0.12):
                G.bottle(K, M @ T(row, y + 0.025, 0, yaw=rng.uniform(-0.6, 0.6)), ("tonic", "medicine", "perfume")[k % 3],
                         label=lab, segs=12)
            y += 0.06
        elif kind == "tins":
            r = rng.choice([0.038, 0.042])
            h = rng.choice([0.1, 0.12, 0.08])
            for row in (depth - 0.06, depth - 0.16):
                G.tin(K, M @ T(row, y + r + 0.004, 0, yaw=rng.uniform(0, 6.283)), r, h, label=lab, segs=16)
                if rng.random() < 0.4:
                    G.tin(K, M @ T(row, y + r + 0.004, h + 0.002, yaw=rng.uniform(0, 6.283)), r, h, label=lab, segs=16)
            y += 2 * r + 0.012
        elif kind == "jars":
            G.jar(K, M @ T(depth - 0.07, y + 0.05, 0), 0.05, 0.14, label=lab,
                  contents=("sweets", "candy_b", "chili", "noodles")[k % 4], segs=14)
            y += 0.115
        elif kind == "cartons":
            face = lab or "tea_box"
            w, d, h = rng.uniform(0.08, 0.12), rng.uniform(0.06, 0.09), rng.uniform(0.12, 0.18)
            for row in (depth - 0.05, depth - 0.14):
                stackh = 0
                for s in range(int(rng.integers(1, 3))):
                    G.carton(K, M @ T(row, y + w / 2, stackh, yaw=math.pi / 2 + rng.normal(0, 0.06)), w, d, h, face)
                    stackh += h
            y += w + 0.01
        elif kind == "packets":
            face = lab or "noodles_red"
            for s in range(int(rng.integers(3, 6))):
                G.packet(K, M @ T(depth - 0.1 + rng.normal(0, 0.01), y + 0.07, s * 0.032, yaw=math.pi / 2 + rng.normal(0, 0.12)),
                         0.15, 0.12, 0.03, face)
            y += 0.16
        elif kind == "bowls":
            G.bowl_stack(K, M @ T(depth - 0.1, y + 0.08, 0), int(rng.integers(4, 8)))
            y += 0.17
        k += 1


_LIQ = {"fish_sauce": "fish_sauce", "soy_sauce": "soy", "chili": "chili", "cooking_oil": "oil", "orange": "orange",
        "beer": "beer", "rice_spirit": "water", "vinegar": "water", "soda": "water", "kerosene": "water",
        "engine_oil": "oil", "cough_syrup": "syrup", "coconut": "water", "alcohol": "water", "shampoo": "orange",
        "hair_oil": "oil", "balm": "oil", "perfume": "water", "lotion": "water"}


def stocked_shelves(K, M, rng, w, h, d, tiers, plan):
    """A shelf unit (back to local x 0) stocked from the bottom tier up by `plan`: a list of
    (kind, labels) per tier."""
    tops = F.shelf_unit(K, M, w=w, h=h, d=d, tiers=tiers)
    for z, (kind, labels) in zip(tops, plan):
        stock_tier(K, M @ T(0, 0, z + 0.001), -w / 2 + 0.05, w / 2 - 0.08, d, kind, rng, labels)
    return tops


# ------------------------------------------------------------------ the trades

def _ph_top(coll, idx, model):
    """The top (local z) and footprint centre of the builder's Poly Haven prop `model` in shop
    `idx`, if it kept one on the veranda."""
    Minv = shop_M(idx).inverted()
    for o in coll.objects:
        if o.name.startswith(f"vroad_shop_{idx}_ph_{model}"):
            pts = [Minv @ (o.matrix_world @ Vector(c)) for c in o.bound_box]
            return (max(p.z for p in pts), Vector((sum(p.x for p in pts) / 8, sum(p.y for p in pts) / 8, 0)))
    return None


def _common(K, sp, rng, calendar_at, clock_at=None, notices=()):
    """What every shop has: the calendar on its wall, a clock, its cardboard notices."""
    x, y, z, yaw = calendar_at
    G.wall_paper(K, T(x, y, z, yaw=yaw), 0.3, 0.42, "calendar")
    if clock_at:
        cx, cy, cz, cyaw, pend = clock_at
        F.wall_clock(K, T(cx, cy, cz, yaw=cyaw), r=0.13 if not pend else 0.11, pendulum=pend)
    for face, (nx, ny, nz, nyaw, w, h) in notices:
        G.wall_paper(K, T(nx, ny, nz, yaw=nyaw), w, h, face)


def dress_noodle(K, coll, idx, sp, rng, light):
    hw = sp["hw"]
    F.noodle_cart(K, T(1.12, 0.3, ZV))
    # The table on the veranda: condiments, chopsticks, a bowl with its spoon, iced tea.
    top = _ph_top(coll, idx, "wooden_table_02")
    if top:
        tz, c = top
        G.chopsticks(K, T(c.x - 0.12, c.y + 0.25, tz))
        G.jar(K, T(c.x - 0.05, c.y + 0.32, tz), 0.035, 0.09, label="chili", contents="chili")
        G.bottle(K, T(c.x + 0.05, c.y + 0.3, tz), "sauce", label="fish_sauce", segs=12)
        G.bottle(K, T(c.x + 0.12, c.y + 0.32, tz), "sauce", liquid="soy", label="soy_sauce", segs=12)
        G.bowl(K, T(c.x + 0.05, c.y - 0.15, tz), 0.085, 0.06, rim="enamel_blue", inner="rice_noodles")
        G.spoon(K, T(c.x + 0.12, c.y - 0.1, tz + 0.06, yaw=0.8))
        G.tumbler(K, T(c.x - 0.15, c.y - 0.2, tz), liquid="tea", ice=True)
        G.tumbler(K, T(c.x - 0.18, c.y + 0.02, tz), liquid="tea")
        cylm_roll(K, T(c.x - 0.02, c.y + 0.05, tz))
    # Inside: stocked shelves on the back wall, crates of soda, the ice box, a spare gas bottle.
    stocked_shelves(K, T(BACK, -1.25, ZI), rng, 1.3, 1.85, 0.38, 5,
                    [("packets", ["noodles_red", "noodles_yellow"]), ("tins", ["condensed_milk", "canned_fish"]),
                     ("bottles", ["fish_sauce", "soy_sauce", "chili"]), ("jars", ["pickles", "palm_sugar", "prahok"]),
                     ("bowls", None)])
    for k in range(3):
        F.soda_crate(K, T(BACK + 0.3, 0.95 + (k % 2) * 0.02, ZI + k * 0.27, yaw=k * 0.05), label=("orange", "soda", "beer")[k])
    F.cooler(K, T(-2.2, 1.7, ZI, yaw=0.1))
    F.lpg_cylinder(K, T(-0.6, 2.2, ZI))
    for k in range(5):
        F.stool(K, T(-0.5, -2.2, ZI + k * 0.06), key="plastic_red" if k % 2 else "plastic_blue")
    F.mat_roll(K, T(-1.0, hw - 0.56, ZI, yaw=0.0))      # (it ran out through the side wall)
    _common(K, sp, rng, (-1.0, -hw + 0.06, 1.55, math.pi), (BACK + 0.06, 0.4, 2.1, 0.0, True),
            notices=[("price_list", (-0.06, 1.4, 1.35, -math.pi / 2, 0.32, 0.44))])


def cylm_roll(K, M):
    """A roll of pink tissue paper, as every noodle table has."""
    G.lathe(K["plastic_pink"], [(0.0, 0.0), (0.05, 0.0), (0.05, 0.1), (0.018, 0.1), (0.018, 0.0)], M @ T(0, 0, 0, tilt=(math.pi / 2, 0)),
            segs=18)


def dress_tv_coffee(K, coll, idx, sp, rng, light):
    hw = sp["hw"]
    ct = 1.073                     # the stall's serving counter top (the builder's)
    # The coffee: sock filter on its stand over the enamel kettle, milk tins, sugar, glasses.
    G.lathe(K["enamel_blue"], [(0.0, 0.0), (0.08, 0.0), (0.09, 0.03), (0.09, 0.14), (0.06, 0.18), (0.02, 0.19), (0.0, 0.19)],
            T(0.2, -0.75, ct), segs=20)
    G.tube(K["enamel_blue"], T(0.2, -0.75, ct), [(0.08, 0, 0.06), (0.14, 0, 0.12), (0.17, 0, 0.18)], 0.012, segs=8)
    G.cylm(K["shop_iron"], T(0.2, -0.75, ct), (-0.1, 0, 0.0), (-0.1, 0, 0.42), 0.006, segs=6)
    G.torus(K["shop_iron"], T(0.2, -0.75, ct), (0, 0, 0.4), (0, 0, 1), 0.06, 0.004, n=14, m=4)
    G.lathe(K["coffee"], [(0.0, 0.2), (0.058, 0.4), (0.06, 0.41)], T(0.2, -0.75, ct), segs=16, cap_bottom=False)
    for k, (dx, dy) in enumerate(((0.12, -0.42), (0.2, -0.32), (0.05, -0.3))):
        G.tin(K, T(dx, dy, ct, yaw=k), 0.038, 0.08, label="condensed_milk", open_top=(k == 0))
    G.jar(K, T(0.25, -0.2, ct), 0.045, 0.12, label="palm_sugar", contents="candy_b")
    for k in range(4):
        G.tumbler(K, T(0.08, -0.05 + k * 0.012, ct + k * 0.095))
    G.tumbler(K, T(0.28, 0.06, ct), liquid="iced_coffee", ice=True)
    G.tumbler(K, T(0.28, 0.18, ct), liquid="iced_coffee", ice=True)
    G.lathe(K["plastic_pink"], [(0.0, 0.0), (0.06, 0.0), (0.065, 0.3), (0.05, 0.33), (0.03, 0.34), (0.0, 0.34)], T(0.06, 0.32, ct),
            segs=18)
    G.lathe(K["plastic_white"], [(0.0, 0.34), (0.03, 0.34), (0.03, 0.39), (0.0, 0.39)], T(0.06, 0.32, ct), segs=12)
    snack_case(K, T(0.16, 0.6, ct), 0.62, 0.3, 0.26, rng, light, idx)
    G.wall_paper(K, T(0.061, -0.55, 0.62, yaw=math.pi / 2), 0.26, 0.36, "price_list")
    # The repair bench at the back: two televisions left on, showing snow; a radio, cassettes,
    # a velvet tray of watches under the lamp, the loupe and fine screwdrivers.
    bt = 0.97
    G.boxm(K["shop_table_wood"], T(BACK + 0.4, 0, bt - 0.03), (0, 0, 0), (0.78, 2.5, 0.06), bevel=0.005)
    for y in (-1.15, 1.15):
        for x in (BACK + 0.08, BACK + 0.72):
            G.boxm(K["shop_dark_wood"], T(x, y, 0), (0, 0, (bt - 0.06) / 2 + 0.09), (0.06, 0.06, bt - 0.24))
    F.crt_tv(K, T(BACK + 0.32, -0.55, bt, yaw=0.12), w=0.5)
    F.crt_tv(K, T(BACK + 0.34, 0.05, bt, yaw=-0.08), w=0.38)
    F.radio(K, T(BACK + 0.3, 0.62, bt, yaw=-0.15))
    for k in range(6):
        G.carton(K, T(BACK + 0.6, 0.98 + (k % 2) * 0.075, bt + (k // 2) * 0.016, yaw=math.pi / 2 + rng.normal(0, 0.1)),
                 0.068, 0.11, 0.016, ("cassette_a", "cassette_b")[k % 2], front_axis="z")
    G.boxm(K["velvet_red"], T(BACK + 0.62, -0.95, bt), (0, 0, 0.01), (0.22, 0.34, 0.02), bevel=0.004)
    for k in range(6):
        watch(K, T(BACK + 0.57 + (k % 2) * 0.09, -1.07 + (k // 2) * 0.11, bt + 0.02, yaw=rng.uniform(0, 6.28)))
    G.lathe(K["plastic_black"], [(0.0, 0.0), (0.016, 0.0), (0.018, 0.025), (0.014, 0.03), (0.0, 0.03)], T(BACK + 0.6, -0.55, bt), segs=14)
    for k in range(3):
        G.screwdriver(K, T(BACK + 0.66, -0.7 + k * 0.025, bt + 0.006, yaw=1.4), length=0.11, handle="plastic_black")
    desk_lamp(K, T(BACK + 0.2, -1.05, bt), light, idx)
    # The wall above: a shelf of radios and boxes, clocks being mended.
    zs = 1.45
    G.boxm(K["shop_dark_wood"], T(BACK, 0, zs), (0.12, 0, 0), (0.24, 2.4, 0.025), bevel=0.003)
    F.radio(K, T(BACK + 0.12, -0.7, zs + 0.013, yaw=0.1), w=0.36)
    F.radio(K, T(BACK + 0.12, 0.5, zs + 0.013, yaw=-0.1), w=0.3)
    for k in range(3):
        G.carton(K, T(BACK + 0.12, -0.15 + k * 0.13, zs + 0.013, yaw=math.pi / 2), 0.11, 0.18, 0.12, "watch_box")
    for k, (y, z, pend) in enumerate(((-1.6, 1.95, False), (-1.15, 2.05, True), (1.2, 1.95, False))):
        F.wall_clock(K, T(BACK + 0.06, y, z), r=0.12, pendulum=pend)
    for y, z in ((hw - 0.06, 1.8), (hw - 0.06, 1.45)):
        F.wall_clock(K, T(-1.2 + (z - 1.45) * 2, y, z, yaw=-math.pi / 2), r=0.1)
    for k in range(3):
        bz = ZI + k * 0.42
        G.boxm(K["cardboard"], T(-0.7, -1.9 + k * 0.02, bz, yaw=0.05 * k), (0, 0, 0.21), (0.5, 0.45, 0.42), bevel=0.006)
        G.wall_paper(K, T(-0.7, -1.9 + k * 0.02 - 0.228, bz + 0.24, yaw=0.05 * k), 0.16, 0.16, "beer_card" if k == 1 else "watch_box")
    _common(K, sp, rng, (-1.6, -hw + 0.06, 1.6, math.pi))


def watch(K, M):
    G.lathe(K["chrome"], [(0.0, 0.0), (0.016, 0.0), (0.018, 0.006), (0.016, 0.01), (0.0, 0.01)], M, segs=16)
    G.lathe(K["porcelain"], [(0.0, 0.0102), (0.014, 0.0102), (0.0, 0.0104)], M, segs=16, cap_bottom=False)
    for s in (-1, 1):
        G.boxm(K["leather_black"], M, (0, s * 0.04, 0.003), (0.018, 0.05, 0.003), bevel=0.001)


def desk_lamp(K, M, light, idx):
    G.lathe(K["shop_iron"], [(0.0, 0.0), (0.07, 0.0), (0.07, 0.02), (0.0, 0.025)], M, segs=16)
    G.cylm(K["shop_iron"], M, (0, 0, 0.02), (0.12, 0.05, 0.38), 0.008, segs=6)
    G.cylm(K["shop_iron"], M, (0.12, 0.05, 0.38), (0.32, 0.08, 0.3), 0.007, segs=6)
    H = M @ T(0.34, 0.08, 0.28, tilt=(0, 2.6))
    G.lathe(K["shop_enamel_green"], [(0.0, -0.02), (0.03, 0.0), (0.07, 0.07), (0.075, 0.08)], H, segs=18, cap_bottom=False)
    G.cylm(K["shop_iron"], H, (0, 0, -0.018), (0, 0, 0.03), 0.011, segs=8)
    G.sphere(K["shop_bulb"], H, (0, 0, 0.04), 0.022, 10, 6)
    light(f"vroad_desk_lamp_{idx}", M @ Vector((0.36, 0.08, 0.22)), 2.2, (1.0, 0.72, 0.42))


def snack_case(K, M, w, d, h, rng, light, idx):
    """A small glass case on the counter (front +x): sweets and snack packets under a bulb."""
    for x in (-d / 2, d / 2):
        for y in (-w / 2, w / 2):
            G.boxm(K["shop_dark_wood"], M, (x, y, h / 2), (0.018, 0.018, h))
    G.boxm(K["shop_dark_wood"], M, (0, 0, 0.008), (d, w, 0.016))
    G.boxm(K["shop_dark_wood"], M, (0, 0, h), (d + 0.02, w + 0.02, 0.016))
    for (px, py, sx, sy) in ((d / 2, 0, 0.004, w), (-d / 2, 0, 0.004, w), (0, -w / 2, d, 0.004), (0, w / 2, d, 0.004)):
        G.boxm(K["glass"], M, (px, py, h / 2), (sx, sy, h - 0.02))
    for i in range(4):
        for j in range(5):
            if rng.random() < 0.25:
                continue
            face = ("snacks", "dried_squid", "shrimp_crackers", "biscuit_box")[int(rng.integers(4))]
            G.packet(K, M @ T(-d / 2 + 0.05 + i * (d - 0.1) / 3, -w / 2 + 0.06 + j * (w - 0.12) / 4, 0.017 + rng.uniform(0, 0.01),
                              yaw=rng.normal(0, 0.3)), 0.08, 0.1, 0.02, face)
    G.cylm(K["shop_iron"], M, (0, 0, h - 0.008), (0, 0, h - 0.03), 0.01, segs=8)
    G.sphere(K["shop_bulb"], M, (0, 0, h - 0.04), 0.018, 10, 6)
    light(f"vroad_case_{idx}", M @ Vector((0, 0, h - 0.06)), 1.0, (1.0, 0.72, 0.4))


def dress_moto(K, coll, idx, sp, rng, light):
    hw = sp["hw"]
    za = 0.2                       # the oil-stained concrete apron's top
    F.motorbike(K, T(0.95, 0.45, za, yaw=0.6), paint="plastic_red")
    # The roadside petrol: a two-tier stand of litre bottles, a funnel, a jerry can.
    G.boxm(K["shop_table_wood"], T(1.6, -1.3, za), (0, 0, 0.5), (0.3, 1.1, 0.03), bevel=0.004)
    G.boxm(K["shop_table_wood"], T(1.6, -1.3, za), (0, 0, 0.9), (0.3, 1.1, 0.03), bevel=0.004)
    for y in (-0.52, 0.52):
        for x in (-0.13, 0.13):
            G.boxm(K["shop_dark_wood"], T(1.6, -1.3, za), (x, y, 0.46), (0.035, 0.035, 0.92))
    for tier, z in enumerate((0.516, 0.916)):
        for k in range(7):
            if tier == 1 and k in (2, 5):
                continue
            G.bottle(K, T(1.6 + (0.06 if k % 2 else -0.06), -1.75 + k * 0.14, za + z, yaw=rng.uniform(0, 6)), "petrol", segs=12,
                     fill=rng.uniform(0.6, 0.95))
    G.lathe(K["tinplate"], [(0.0, 0.0), (0.008, 0.0), (0.008, 0.06), (0.06, 0.16), (0.06, 0.17), (0.055, 0.17), (0.0, 0.07)],
            T(1.52, -0.86, za + 0.915), segs=16)
    G.boxm(K["plastic_yellow"], T(1.35, -2.25, za), (0, 0, 0.17), (0.18, 0.3, 0.34), bevel=0.02)
    G.cylm(K["plastic_yellow"], T(1.35, -2.25, za), (0, -0.08, 0.34), (0, 0.02, 0.4), 0.02, segs=8)
    for k in range(4):
        F.tyre(K, T(1.05, 1.66, za + k * 0.075, yaw=k))
    F.drum(K, T(0.45, -2.35, za), paint="plastic_blue")
    F.drum(K, T(0.45, 2.35, za), paint="plastic_red")
    G.lathe(K["black_paint"], [(0.0, 0.0), (0.2, 0.0), (0.22, 0.05), (0.21, 0.05), (0.19, 0.008), (0.0, 0.008)], T(0.4, -1.5, za), segs=24)
    G.lathe(K["oil"], [(0.0, 0.02), (0.19, 0.02), (0.0, 0.022)], T(0.4, -1.5, za), segs=20, cap_bottom=False)
    # The workbench on the back wall: vice, an open toolbox, spark plugs in a tin, a chain, oil.
    bt = 0.88
    G.boxm(K["shop_table_wood"], T(BACK + 0.38, 0, 0), (0, 0, bt - 0.03), (0.75, 2.6, 0.06), bevel=0.005)
    G.boxm(K["shop_table_wood"], T(BACK + 0.38, 0, 0), (0, 0, 0.36), (0.68, 2.5, 0.03))
    for y in (-1.22, 1.22):
        for x in (-0.32, 0.32):
            G.boxm(K["shop_dark_wood"], T(BACK + 0.38, y, ZI), (x, 0, (bt - 0.24) / 2), (0.07, 0.07, bt - 0.24))
    vice(K, T(BACK + 0.65, -0.95, bt))
    toolbox(K, T(BACK + 0.38, -0.3, bt, yaw=0.1))
    G.tin(K, T(BACK + 0.55, 0.2, bt), 0.05, 0.1, label="grease", open_top=True)
    for k in range(6):
        sparkplug(K, T(BACK + 0.6 + (k % 3) * 0.03, 0.42 + (k // 3) * 0.04, bt, yaw=k, tilt=(math.pi / 2, 0)))
    for k in range(3):
        G.tin(K, T(BACK + 0.2, 0.75 + k * 0.13, bt), 0.055, 0.2, label="engine_oil")
    chain_coil(K, T(BACK + 0.55, 0.95, bt))
    G.boxm(K["shop_linen_towel"], T(BACK + 0.6, 0.05, bt), (0, 0, 0.012), (0.28, 0.22, 0.02), bevel=0.008)
    # The tool board above it, every tool on its nail.
    wx = -3.16                     # the face of the builder's tool board (flush on the back wall)
    for k in range(8):
        G.cylm(K["steel"], T(wx, -0.62 + k * 0.085, 1.98), (0, 0, 0), (0.03, 0, 0.0), 0.0018, segs=4)
        G.spanner(K, T(wx + 0.004, -0.62 + k * 0.085, 1.96 - (0.06 + k * 0.01), tilt=(0, math.pi / 2)), length=0.12 + k * 0.02)
    for k in range(4):
        G.screwdriver(K, T(wx + 0.01, 0.12 + k * 0.06, 1.97, tilt=(0, math.pi / 2)),
                      handle=("plastic_yellow", "plastic_red", "plastic_blue", "plastic_yellow")[k])
    G.pliers(K, T(wx + 0.008, 0.45, 1.95, tilt=(0, math.pi / 2)))
    G.cylm(K["steel"], T(wx, 0.62, 1.975), (0, 0, 0), (0.035, 0, 0.0), 0.0018, segs=4)
    G.hammer(K, T(wx + 0.004, 0.62, 2.0, tilt=(0, -math.pi / 2)))
    # Inner tubes and two tyres on the side wall, the compressor on the floor.
    for k in range(3):
        G.torus(K["inner_tube"], T(-1.0 - k * 0.45, -hw + 0.07, 1.6, tilt=(math.pi / 2, 0)), (0, 0, 0), (0, 0, 1), 0.2, 0.02, n=24, m=6)
        wall_peg(K, -1.0 - k * 0.45, -hw + 0.05, 1.6 + 0.2 - 0.02 - 0.009, +1)
    for k in range(2):
        F.tyre(K, T(-2.3 + k * 0.5, hw - 0.052, 1.3, tilt=(math.pi / 2, 0)))
        wall_peg(K, -2.3 + k * 0.5, hw - 0.05, 1.3 + 0.215 - 0.012, -1, length=0.11)
    compressor(K, T(-1.2, -1.9, ZI, yaw=0.3))
    G.lathe(K["tinplate"], [(0.0, 0.0), (0.13, 0.0), (0.15, 0.3), (0.14, 0.3)], T(-0.6, -2.3, ZI), segs=20)
    G.boxm(K["shop_linen_towel"], T(-0.6, -2.3, ZI), (0, 0, 0.29), (0.18, 0.16, 0.05), bevel=0.02)
    _common(K, sp, rng, (-2.0, -hw + 0.06, 1.7, math.pi), (BACK + 0.06, 1.3, 2.15, 0.0, False))


def vice(K, M):
    G.boxm(K["plastic_blue"], M, (0, 0, 0.06), (0.14, 0.18, 0.1), bevel=0.012)
    G.boxm(K["plastic_blue"], M, (0.0, 0.0, 0.15), (0.06, 0.2, 0.08), bevel=0.01)
    G.boxm(K["steel"], M, (0.04, 0, 0.15), (0.06, 0.18, 0.07), bevel=0.008)
    G.cylm(K["chrome"], M, (0.08, 0, 0.13), (0.2, 0, 0.13), 0.009, segs=8)
    G.cylm(K["chrome"], M, (0.2, -0.08, 0.13), (0.2, 0.08, 0.13), 0.006, segs=6)


def toolbox(K, M):
    G.boxm(K["plastic_red"], M, (0, 0, 0.09), (0.22, 0.48, 0.18), bevel=0.008)
    for s in (-1, 1):
        G.boxm(K["plastic_red"], M @ T(s * 0.11, 0, 0.18, tilt=(0, s * 0.9)), (s * 0.06, 0, 0), (0.12, 0.47, 0.012), bevel=0.003)
    G.cylm(K["chrome"], M, (0, -0.2, 0.2), (0, 0.2, 0.2), 0.008, segs=8)
    for k in range(5):
        G.spanner(K, M @ T(-0.04 + k * 0.02, -0.1 + k * 0.04, 0.17, yaw=0.3 * k), length=0.14)


def sparkplug(K, M):
    G.lathe(K["porcelain"], [(0.0, 0.0), (0.007, 0.0), (0.009, 0.03), (0.008, 0.05), (0.0, 0.052)], M, segs=10)
    G.lathe(K["steel"], [(0.0, -0.03), (0.007, -0.03), (0.007, -0.005), (0.011, -0.004), (0.011, 0.004), (0.0, 0.004)], M, segs=6)


def chain_coil(K, M):
    for k in range(40):
        a = k * 0.35
        r = 0.07 + 0.002 * k
        G.torus(K["steel"], M @ T(math.cos(a) * r, math.sin(a) * r, 0.006 + (k % 2) * 0.004, yaw=a + math.pi / 2, tilt=(math.pi / 2 * (k % 2), 0)),
                (0, 0, 0), (0, 0, 1), 0.007, 0.002, n=8, m=3)


def compressor(K, M):
    G.lathe(K["plastic_red"], [(0.0, 0.0), (0.12, 0.02), (0.15, 0.08), (0.15, 0.5), (0.12, 0.56), (0.0, 0.58)],
            M @ T(0, 0, 0.2, tilt=(0, math.pi / 2)) @ T(0, 0, -0.29), segs=20)
    for x in (-0.2, 0.2):
        for y in (-0.1, 0.1):
            G.cylm(K["steel"], M, (x, y, 0.0), (x * 0.9, y * 0.9, 0.1), 0.01, segs=6)
    G.boxm(K["black_paint"], M, (0.05, 0, 0.42), (0.22, 0.16, 0.14), bevel=0.02)
    G.lathe(K["chrome"], [(0.0, 0.0), (0.03, 0.0), (0.03, 0.012), (0.0, 0.012)], M @ T(0.02, 0.08, 0.42, tilt=(-math.pi / 2, 0)), segs=16)
    G.tube(K["rubber"], M, [(-0.25, 0, 0.2), (-0.4, 0.1, 0.05), (-0.3, 0.3, 0.02), (0.0, 0.32, 0.02), (0.15, 0.2, 0.05)], 0.008, segs=6)


def dress_grocery(K, coll, idx, sp, rng, light):
    hw = sp["hw"]
    # Two stocked shelf units on the back wall and one down the side.
    stocked_shelves(K, T(BACK, -0.75, ZI), rng, 1.4, 1.95, 0.4, 5,
                    [("cartons", ["washing_powder", "soap", "tea_box"]), ("bottles", ["cooking_oil", "fish_sauce", "soy_sauce"]),
                     ("tins", ["condensed_milk", "canned_fish", "biscuits", "coffee"]), ("packets", ["noodles_red", "noodles_yellow"]),
                     ("cartons", ["candles", "matches", "incense"])])
    stocked_shelves(K, T(BACK, 0.75, ZI), rng, 1.4, 1.95, 0.4, 5,
                    [("bottles", ["beer", "orange", "soda"]), ("bottles", ["rice_spirit", "vinegar", "kerosene"]),
                     ("jars", ["sweets", "pickles", "palm_sugar"]), ("small_bottles", ["balm", "cough_syrup", "hair_oil"]),
                     ("tins", ["tea", "coffee", "talc"])])
    stocked_shelves(K, T(-1.9, -hw + 0.06, ZI, yaw=math.pi / 2), rng, 1.3, 1.6, 0.36, 4,
                    [("packets", ["snacks", "dried_squid", "shrimp_crackers"]), ("cartons", ["toothpaste", "medicine", "razor"]),
                     ("small_bottles", ["shampoo", "lotion", "perfume"]), ("tins", ["battery", "talc"])])
    # The counter by the door: sweets in jars along it, the balance, cigarettes under the glass,
    # the credit book and the lottery tickets.
    top, floor = F.counter(K, T(-1.45, 1.55, ZI), w=1.5, d=0.55, h=0.92)
    for k in range(5):
        G.jar(K, T(-1.38, 1.0 + k * 0.13, ZI + top), 0.05, 0.16, label=("sweets", "sweets", "pickles", "sweets", "palm_sugar")[k],
              contents=("sweets", "candy_b", "chili", "sweets", "candy_b")[k])
    F.balance_scale(K, T(-1.1, 1.9, ZI + top, yaw=0.2))
    for k in range(10):
        G.carton(K, T(-1.2 + (k % 2) * 0.08, 1.1 + (k // 2) * 0.11, ZI + floor), 0.055, 0.022, 0.088, ("cig_red", "cig_blue")[k % 2])
    for k in range(6):
        G.carton(K, T(-1.0, 1.15 + k * 0.08, ZI + floor), 0.05, 0.036, 0.016, "matches", front_axis="z")
    G.carton(K, T(-0.98, 1.6, ZI + top, yaw=0.4), 0.16, 0.22, 0.012, "notebook", front_axis="z")
    G.wall_paper(K, T(-0.06, 2.3, 1.6, yaw=-math.pi / 2), 0.44, 0.22, "no_credit")
    G.wall_paper(K, T(-0.06, 1.85, 1.55, yaw=-math.pi / 2), 0.24, 0.11, "lottery")
    # Rice sacks, baskets of onions, ginger and limes, egg trays, soda crates, kerosene.
    sack = scan("rice_sack.glb", 3500)
    for k, (x, y, yaw) in enumerate(((-2.6, 2.3, 0.3), (-2.15, 2.4, -0.4), (-2.4, 2.25, 1.2))):
        place(coll, sack, shop_M(idx) @ T(x, y, ZI + (0.25 if k == 2 else 0), yaw=yaw), f"vroad_goods_{idx}_rice_sack")
    basket = ph("wicker_basket_01", 3600)
    for k, (x, y, food) in enumerate(((-0.8, -2.2, "yellow_onion"), (-0.4, -2.3, "food_ginger_01"), (-1.2, -2.25, "food_lime_01"))):
        b = place(coll, basket, shop_M(idx) @ T(x, y, ZI, yaw=k), f"vroad_goods_{idx}_basket")
        fill_basket(coll, idx, b[0], ph(food, 500), f"vroad_goods_{idx}_{food}", rng, size=PRODUCE_SIZE[food])
    for k in range(4):
        egg_tray(K, T(-2.7, -1.9, ZI + k * 0.026, yaw=0.04 * k), full=(k == 3))
    F.soda_crate(K, T(-2.7, -2.5, ZI), label="beer")
    F.soda_crate(K, T(-2.7, -2.5, ZI + 0.27, yaw=0.1), label="soda")
    for k in range(3):
        G.bottle(K, T(-0.45 + k * 0.09, 2.6, ZI), "petrol", liquid="water", segs=12)
    # The veranda: a bamboo pole lashed between the front posts; from it, on the side away from
    # the steps (the doorway's path stays clear, the rain blind hangs on the other side), snack
    # strips and the brooms; plastic buckets stacked below. (No hung bananas: the user, Nov 26.)
    rail_z = 2.24
    G.cylm(K["shop_bamboo"], T(0, 0, 0), (RAIL_X, -hw + 0.074, rail_z), (RAIL_X, hw - 0.074, rail_z), 0.024, segs=10)
    for y in (-hw + 0.1, hw - 0.1):
        for dz in (-0.012, 0.012):
            G.torus(K["cork"], T(RAIL_X, y, rail_z + dz), (0, 0, 0), (0, 1, 0), 0.026, 0.004, n=12, m=4)
    for k, y in enumerate(np.linspace(-hw + 0.3, hw - 0.3, 9)):
        G.torus(K["shop_bamboo"], T(RAIL_X, y, rail_z), (0, 0, 0), (0, 1, 0), 0.025, 0.004, n=12, m=4)
    for y, face in ((-2.62, "noodles_yellow"), (-2.32, "snacks"), (-2.02, "shrimp_crackers"), (-1.74, "noodles_red"),
                    (-1.46, "dried_squid")):
        snack_strip(K, T(RAIL_X, y, rail_z - 0.024), rng, face)
    for k, y in enumerate((-1.22, -1.12)):
        hung_broom(K, T(RAIL_X, y, rail_z - 0.024, yaw=0.3 * k))
    for k in range(4):
        G.lathe(K[("plastic_red", "plastic_blue", "plastic_green", "plastic_yellow")[k]],
                [(0.0, 0.0), (0.12, 0.0), (0.16, 0.26), (0.165, 0.27), (0.155, 0.27), (0.11, 0.01), (0.0, 0.01)],
                T(1.55, -2.35, ZV + k * 0.05), segs=24)
    _common(K, sp, rng, (-2.4, hw - 0.06, 1.75, 0.0), (BACK + 0.06, 0.0, 2.25, 0.0, False),
            notices=[("price_list", (-0.06, -1.6, 1.5, -math.pi / 2, 0.3, 0.42))])


def egg_tray(K, M, full=True):
    G.boxm(K["cardboard"], M, (0, 0, 0.012), (0.3, 0.3, 0.024))
    for i in range(5):
        for j in range(6):
            p = (-0.12 + i * 0.06, -0.125 + j * 0.05, 0.03)
            if full:
                G.sphere(K["egg"], M, (p[0], p[1], 0.045), 0.021, 10, 7, scale=(1.0, 1.0, 1.28))


RAIL_X = 1.70     # the grocery's bamboo pole: behind the rain blind, against the posts' inner faces


def snack_strip(K, M, rng, face):
    """A strip of snack packets hung from a loop over the veranda pole (M at the pole's
    underside), their printed faces to the road and the shop, joined seal to seal."""
    G.torus(K["thread_white"], M @ T(0, 0, 0.024), (0, 0, 0), (0, 1, 0), 0.027, 0.0018, n=12, m=3)
    G.cylm(K["thread_white"], M, (0, 0, 0.0), (0, 0, -0.06), 0.002, segs=4)
    for k in range(6):
        G.packet(K, M @ T(0, 0, -0.06 - k * 0.104, yaw=math.pi / 2 + rng.normal(0, 0.06), tilt=(math.pi / 2, 0)),
                 0.1, 0.1, 0.022, face)


def hung_broom(K, M):
    """A soft-grass broom hung by a loop of string from the veranda pole (M at its underside):
    the bamboo handle, the bound grass head flaring out below."""
    G.torus(K["thread_white"], M @ T(0, 0, 0.024), (0, 0, 0), (0, 1, 0), 0.028, 0.002, n=12, m=3)
    G.cylm(K["thread_white"], M, (0, 0, 0.0), (0, 0, -0.05), 0.002, segs=4)
    G.cylm(K["shop_bamboo"], M, (0, 0, -0.05), (0, 0, -0.62), 0.013, 0.015, segs=8)
    for z in (-0.6, -0.64, -0.68):
        G.torus(K["plastic_red"], M, (0, 0, z), (0, 0, 1), 0.024, 0.004, n=12, m=4)
    G.lathe(K["bristle"], [(0.0, -0.58), (0.026, -0.6), (0.03, -0.7), (0.06, -0.85), (0.1, -0.96), (0.11, -0.98), (0.0, -0.97)],
            M @ Matrix.Diagonal((1.0, 0.45, 1.0, 1.0)), segs=18)


def local_points(idx, obj):
    """An object's vertices in shop idx's frame, as an (N, 3) array."""
    co = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    m = np.array(shop_M(idx).inverted() @ obj.matrix_world)
    return co @ m[:3, :3].T + m[:3, 3]


def local_box(idx, obj):
    """An object's box in shop idx's frame (lo, hi)."""
    co = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    m = np.array(shop_M(idx).inverted() @ obj.matrix_world)
    q = co @ m[:3, :3].T + m[:3, 3]
    return Vector(q.min(0).tolist()), Vector(q.max(0).tolist())


# Each produce scan's longest side when sold (the ginger scan came in at a third of a metre).
PRODUCE_SIZE = {"yellow_onion": 0.075, "food_ginger_01": 0.12, "food_lime_01": 0.05}


def fill_basket(coll, idx, basket, tpl, name, rng, n=11, size=None):
    """Produce heaped in a basket: each piece dropped in from above onto the basket's floor or
    the pieces already in (they were scattered at one height, some hanging in the air)."""
    if not tpl:
        return
    M = shop_M(idx)
    lo, hi = local_box(idx, basket)
    cx, cy, rad = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2, min(hi.x - lo.x, hi.y - lo.y) / 2 - 0.05
    placed = [basket]
    s = size / max(tpl[0].dimensions) if size else 1.0
    n = int(n * min(3.0, max(1.0, (1.0 / s) ** 0.5))) if size else n
    for j in range(n):
        a, d = rng.uniform(0, 6.28), rad * math.sqrt(rng.uniform(0, 1)) * (1.0 - 0.06 * j / n)
        o = place(coll, tpl, M @ T(cx + math.cos(a) * d, cy + math.sin(a) * d, hi.z + 0.25, yaw=rng.uniform(0, 6.28),
                                   tilt=(rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6)), s=s), name)[0]
        if drop_onto(o, placed, limit=0.6) <= 0.0:
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        placed.append(o)


def dress_barber(K, coll, idx, sp, rng, light):
    hw = sp["hw"]
    for y in (-0.62, 0.72):
        F.barber_chair(K, T(-1.8, y, ZI, yaw=math.pi))
        for _ in range(26):
            a, d = rng.uniform(0, 6.28), rng.uniform(0.15, 0.5)
            p = Vector((-1.8 + math.cos(a) * d, y + math.sin(a) * d, ZI + 0.001))
            G.tube(K["hair"], Matrix.Identity(4), [p, p + Vector((rng.normal(0, 0.03), rng.normal(0, 0.03), 0.0005))], 0.0012, segs=3)
    # The counter under the mirror: everything a barber keeps to hand.
    top, _f = F.counter(K, T(BACK, 0.0, ZI), w=2.5, d=0.45, h=0.9, glass_top=False)
    z = ZI + top
    for k, y in enumerate(np.linspace(-1.05, -0.55, 4)):
        G.bottle(K, T(BACK + 0.12, y, z, yaw=k), "tonic", label=("hair_oil", "balm", "hair_oil", "perfume")[k], segs=12)
    G.tin(K, T(BACK + 0.12, -0.38, z), 0.04, 0.13, label="talc")
    G.spray_bottle(K, T(BACK + 0.15, -0.2, z, yaw=1.0))
    G.shaving_brush(K, T(BACK + 0.12, 0.05, z))
    G.bowl(K, T(BACK + 0.2, 0.15, z), 0.06, 0.05, key="porcelain")
    for k in range(3):
        G.comb(K, T(BACK + 0.32, -0.9 + k * 0.05, z, yaw=0.1 * k))
    G.scissors(K, T(BACK + 0.32, -0.55, z + 0.002, yaw=0.4))
    G.scissors(K, T(BACK + 0.34, 0.45, z + 0.002, yaw=-1.0))
    G.straight_razor(K, T(BACK + 0.3, 0.2, z, yaw=0.2))
    G.clippers(K, T(BACK + 0.3, 0.7, z, yaw=-0.5))
    G.carton(K, T(BACK + 0.2, 0.9, z, yaw=math.pi / 2), 0.09, 0.05, 0.02, "razor", front_axis="z")
    for k in range(4):
        G.towel(K, T(BACK + 0.2, 1.05, z + k * 0.036, yaw=rng.normal(0, 0.04)))
    F.radio(K, T(BACK + 0.15, 0.4, ZI + 2.0, yaw=0.0), w=0.34)
    G.boxm(K["shop_dark_wood"], T(BACK, 0.4, ZI + 2.0), (0.11, 0, -0.012), (0.22, 0.6, 0.024))
    F.desk_fan(K, T(BACK + 0.18, -1.15, z, yaw=0.6))
    # The cape on its hook, the waiting bench with the day's newspaper.
    G.cylm(K["chrome"], T(-0.4, hw - 0.06, 1.7), (0, 0, 0), (0, -0.06, 0.02), 0.005, segs=6)
    G.boxm(K["plastic_white"], T(-0.4, hw - 0.112, 1.285), (0, 0, 0), (0.48, 0.02, 0.9), bevel=0.01)
    F.bench(K, T(-0.9, -hw + 0.3, ZI, yaw=math.pi / 2), w=1.3)
    G.boxm(K["shop_news"], T(-0.7, -hw + 0.3, ZI + 0.45), (0, 0, 0.004), (0.3, 0.42, 0.008), bevel=0.002)
    F.bench(K, T(1.0, -1.5, ZV, yaw=0.0), w=1.5)
    G.boxm(K["shop_news"], T(1.0, -1.3, ZV + 0.45), (0, 0, 0.004), (0.28, 0.4, 0.008), bevel=0.002)
    _common(K, sp, rng, (-1.2, hw - 0.06, 1.65, 0.0), (BACK + 0.06, -1.6, 2.1, 0.0, False),
            notices=[("price_list", (-0.06, -1.5, 1.45, -math.pi / 2, 0.3, 0.42))])


def dress_dentist(K, coll, idx, sp, rng, light):
    hw = sp["hw"]
    F.dental_chair(K, T(-1.6, 0.8, ZI, yaw=0.15))
    # The glass counter: dentures and tools in it; jars of cotton, spirit, pastes on it.
    top, floor = F.counter(K, T(-1.5, -1.5, ZI), w=1.6, d=0.55, h=0.95)
    for k in range(3):
        denture(K, T(-1.25, -2.0 + k * 0.3, ZI + floor, yaw=math.pi / 2))
    for k in range(6):
        probe(K, T(-1.08, -1.2 + k * 0.05, ZI + floor + 0.002, yaw=0.05 * k))
    z = ZI + top
    G.jar(K, T(-1.35, -2.1, z), 0.05, 0.12, contents="egg", lid="tinplate")
    G.bottle(K, T(-1.3, -1.9, z), "spirit", label="alcohol", segs=12)
    G.bottle(K, T(-1.38, -1.78, z), "medicine", label="cough_syrup", segs=12)
    for k in range(4):
        G.carton(K, T(-1.3, -1.45 + k * 0.05, z + (k // 2) * 0.03, yaw=math.pi / 2), 0.16, 0.04, 0.03, "toothpaste")
    G.carton(K, T(-1.25, -1.0, z), 0.12, 0.08, 0.06, "medicine")
    # The instrument tray on its stand by the chair.
    G.cylm(K["chrome"], T(-0.95, 1.4, ZI), (0, 0, 0), (0, 0, 0.9), 0.012, segs=8)
    G.boxm(K["porcelain"], T(-0.95, 1.4, ZI + 0.9), (0, 0, 0.01), (0.3, 0.22, 0.02), bevel=0.006)
    for k in range(5):
        probe(K, T(-1.0 + k * 0.025, 1.4, ZI + 0.922, yaw=math.pi / 2))
    G.bowl(K, T(-0.88, 1.47, ZI + 0.92), 0.04, 0.025, key="chrome")
    # The back wall: the chart of the teeth, shelves of jars and bottles.
    G.wall_paper(K, T(BACK + 0.012, -1.6, 1.65, yaw=math.pi / 2), 0.5, 0.7, "teeth_chart")
    zs = ZI + 1.25
    F.wall_shelf(K, T(BACK, -0.5, zs), w=1.1)
    for k in range(6):
        G.bottle(K, T(BACK + 0.1, -0.95 + k * 0.17, zs + 0.012), ("medicine", "tonic")[k % 2],
                 label=("cough_syrup", "alcohol", "balm")[k % 3], segs=12)
    F.wall_shelf(K, T(BACK, -0.5, zs + 0.4), w=1.1)
    for k in range(4):
        G.jar(K, T(BACK + 0.1, -0.9 + k * 0.26, zs + 0.412), 0.045, 0.11, contents=("egg", "candy_b", "egg", "candy")[k], lid="tinplate")
    F.desk_fan(K, T(-0.5, -2.6, ZI + 0.0, yaw=1.0), s=1.6)
    _common(K, sp, rng, (-0.9, hw - 0.06, 1.65, 0.0), (BACK + 0.06, 0.95, 2.35, 0.0, False))


def denture(K, M):
    """A set of dentures on the display felt: pink gum arch, white teeth."""
    for k in range(12):
        a = math.pi * (0.1 + 0.8 * k / 11)
        G.sphere(K["gum_pink"], M, (math.cos(a) * 0.04, math.sin(a) * 0.035, 0.01), 0.011, 8, 5, scale=(1, 1, 0.8))
        G.sphere(K["tooth"], M, (math.cos(a) * 0.042, math.sin(a) * 0.037, 0.02), 0.0065, 8, 5, scale=(0.8, 0.8, 1.3))


def probe(K, M):
    G.cylm(K["chrome"], M, (-0.06, 0, 0.003), (0.06, 0, 0.003), 0.0025, segs=6)
    G.tube(K["chrome"], M, [(0.06, 0, 0.003), (0.08, 0, 0.004), (0.085, 0.006, 0.004)], 0.0009, segs=3)


def dress_salon(K, coll, idx, sp, rng, light):
    hw = sp["hw"]
    F.salon_chair(K, T(-1.9, 0.0, ZI, yaw=math.pi))
    F.hood_dryer(K, T(-1.55, 1.55, ZI, yaw=math.pi + 0.4))
    top, _f = F.counter(K, T(BACK, 0.0, ZI), w=1.6, d=0.42, h=0.88, glass_top=False)
    z = ZI + top
    for k, y in enumerate(np.linspace(-0.7, -0.25, 4)):
        G.bottle(K, T(BACK + 0.12, y, z, yaw=k), ("perfume", "tonic", "perfume", "tonic")[k],
                 label=("perfume", "lotion", "perfume", "shampoo")[k], segs=12)
    G.tin(K, T(BACK + 0.13, -0.08, z), 0.045, 0.14, label="talc")
    G.lathe(K["plastic_pink"], [(0.0, 0.0), (0.04, 0.0), (0.042, 0.008), (0.0, 0.012)], T(BACK + 0.28, -0.45, z), segs=18)
    for k in range(3):
        G.comb(K, T(BACK + 0.3, 0.1 + k * 0.05, z, yaw=0.15 * k), key=("plastic_pink", "plastic_black", "plastic_red")[k])
    G.scissors(K, T(BACK + 0.3, 0.35, z + 0.002, yaw=-0.6))
    G.spray_bottle(K, T(BACK + 0.15, 0.5, z))
    for k in range(8):
        G.cylm(K[("plastic_pink", "plastic_blue")[k % 2]], T(BACK + 0.25 + (k % 4) * 0.04, 0.6 + (k // 4) * 0.05, z), (0, -0.02, 0.012),
               (0, 0.02, 0.012), 0.012, segs=10)
    for k in range(3):
        G.towel(K, T(BACK + 0.2, 0.68 - 0.02, z + 0.03 + k * 0.036), key="shop_linen_towel")
    G.carton(K, T(BACK + 0.15, -0.7, z), 0.1, 0.05, 0.16, "hair_dye")
    G.boxm(K["shop_news"], T(-1.0, -0.4, ZI + 0.0), (0, 0, 0.005), (0.28, 0.4, 0.01), bevel=0.002)
    # The tailoring corner: treadle machine, a dress form in silk, spools on the wall, bolts.
    F.sewing_machine(K, T(-1.1, -1.7, ZI, yaw=0.0))
    F.dress_form(K, T(-0.6, 1.4, ZI))
    F.wall_shelf(K, T(-2.2, -hw + 0.05, ZI + 1.35, yaw=math.pi / 2), w=0.9, d=0.14)
    for k in range(10):
        spool = ("thread_red", "thread_blue", "thread_white", "thread_yellow")[k % 4]
        G.lathe(K[spool], [(0.0, 0.0), (0.016, 0.0), (0.016, 0.005), (0.013, 0.005), (0.013, 0.045), (0.016, 0.045),
                           (0.016, 0.05), (0.0, 0.05)], T(-2.6 + k * 0.085, -hw + 0.12, ZI + 1.362), segs=12)
    for k in range(4):
        G.cylm(K[("shop_hol_silk", "shop_krama", "shop_hol_silk", "shop_krama")[k]], T(-2.65, 1.85, ZI + k * 0.1),
               (0, -0.45, 0.05), (0, 0.45, 0.05), 0.05, segs=14)
    G.carton(K, T(-1.0, -1.5, ZI + 0.768), 0.12, 0.08, 0.004, "needles", front_axis="z")
    G.scissors(K, T(-1.0, -1.85, ZI + 0.768, yaw=0.3), s=1.4)
    G.torus(K["plastic_yellow"], T(-1.05, -2.0, ZI + 0.768), (0, 0, 0.004), (0, 0, 1), 0.025, 0.004, n=14, m=4)
    F.bench(K, T(1.0, 1.15, ZV, yaw=0.0), w=1.3)
    G.boxm(K["shop_krama"], T(1.0, 1.25, ZV + 0.45), (0, 0, 0.004), (0.3, 0.45, 0.01), bevel=0.003)
    doorway_curtain(K, 0.42, 0.95)
    _common(K, sp, rng, (-1.2, hw - 0.06, 1.75, 0.0), (BACK + 0.06, -1.1, 2.15, 0.0, False))


# ------------------------------------------------------------------ resting things on things

def _world_tris(objs):
    """World-space vertices and triangles of objects, for one BVH."""
    V, F, off = [], [], 0
    for o in objs:
        me = o.data
        if not len(me.vertices):
            continue
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        mw = np.array(o.matrix_world)
        V.append(co @ mw[:3, :3].T + mw[:3, 3])
        me.calc_loop_triangles()
        t = np.empty(len(me.loop_triangles) * 3, dtype=np.int64)
        me.loop_triangles.foreach_get("vertices", t)
        F.append(t.reshape(-1, 3) + off)
        off += len(co)
    if not V:
        return None
    from mathutils.bvhtree import BVHTree

    return BVHTree.FromPolygons(np.concatenate(V).tolist(), np.concatenate(F).tolist(), all_triangles=True)


def _lowest(o, n=40):
    co = np.empty(len(o.data.vertices) * 3)
    o.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mw = np.array(o.matrix_world)
    w = co @ mw[:3, :3].T + mw[:3, 3]
    return w[np.argsort(w[:, 2])[:n]]


def drop_onto(o, supports, limit=0.4, bvh=None):
    """Lowers `o` straight down until it rests on `supports` (it may already). Returns the drop."""
    tree = bvh or _world_tris(supports)
    if tree is None:
        return 0.0
    down = Vector((0, 0, -1))
    best = None
    for v in _lowest(o):
        # From 3 cm above each low point: a hit nearer than that means it already rests on (or
        # sits a little into) something, and it stays where it is.
        hit = tree.ray_cast(Vector((v[0], v[1], v[2] + 0.03)), down, limit + 0.03)
        if hit[0] is not None:
            d = hit[3] - 0.03
            best = d if best is None else min(best, d)
    if best is not None and best > 0.003:
        o.matrix_world = Matrix.Translation((0, 0, -best)) @ o.matrix_world
        return best
    return 0.0


SETTLE_SKIP = ("ornate_mirror", "winnowing_tray", "painted_wooden_shelves", "vintage_cabinet", "wooden_ladder")


def settle(coll, idx, sp):
    """Every loose prop in and before shop idx (the Poly Haven furniture, the scans, the rice
    sacks) brought down onto whatever is under it, lowest first, so a pot sits on its stove and
    a lamp on its table (several stood a few centimetres in the air)."""
    pre = f"vroad_shop_{idx}_"
    loose = [o for o in coll.objects if o.type == "MESH" and (
        (o.name.startswith(pre + "ph_") or o.name.split(".")[0][len(pre):] in SCAN_DETAIL) and o.name.startswith(pre)
        or o.name.startswith(f"vroad_goods_{idx}_rice_sack")) and not any(k in o.name for k in SETTLE_SKIP)]
    static = [o for o in coll.objects if o.type == "MESH" and o not in loose and (
        o.name.startswith(pre) or o.name.startswith(f"vroad_goods_{idx}_")) and not o.name.startswith("vroad_goods_%d_food" % idx)]
    loose.sort(key=lambda o: _lowest(o, 1)[0][2])
    moved = 0
    for o in loose:
        if drop_onto(o, static + [x for x in loose if x is not o], limit=0.35) > 0:
            moved += 1
    return moved


def flush_on_back_wall(coll, idx):
    """The Poly Haven mirrors hung on the back wall moved back until they touch it."""
    for o in coll.objects:
        if o.name.startswith(f"vroad_shop_{idx}_ph_ornate_mirror"):
            lo, _hi = local_box(idx, o)
            dx = BACK - lo.x
            if abs(dx) > 0.002:
                M = shop_M(idx)
                o.matrix_world = M @ Matrix.Translation((dx, 0, 0)) @ M.inverted() @ o.matrix_world


DRESS = {"noodle": dress_noodle, "tv_coffee": dress_tv_coffee, "moto": dress_moto, "grocery": dress_grocery,
         "barber": dress_barber, "dentist_salon": dress_dentist, "salon": dress_salon}


def dress(coll, shops, m, light):
    """Strips and furnishes every shop of `shops` [(idx, spec, matrix)]; `light(name, world point,
    watts, colour)` adds a lamp marker. Returns (pieces taken out, triangles added)."""
    import taxi_roadside_details as TRD

    Gm = G.materials(m)
    out_n, tris = 0, 0
    for idx, sp, M in shops:
        _SHOP_M[idx] = M
        K = G.Kit(Gm)
        rng = np.random.default_rng(4100 + idx)

        def lt(name, p, watts, colour, M=M):
            light(name, M @ Vector(p), watts, colour)

        if sp["trade"] in DRESS:
            out_n += strip(idx, sp)
            DRESS[sp["trade"]](K, coll, idx, sp, rng, lt)
        rain_jar(K, T(TRD.RAIN_JAR[0], sp["hw"] - TRD.RAIN_JAR[1], ZV, yaw=0.3 * idx))
        if sp["trade"] in ("noodle", "tv_coffee", "grocery", "barber"):
            x, y, z = shrine_at(sp)
            spirit_shrine(K, T(x, y, z))
        K.emit(coll, f"vroad_goods_{idx}", M)
        tris += K.tris
    n_up = upgrade_props(coll)
    for idx, sp, M in shops:
        flush_on_back_wall(coll, idx)
        settle(coll, idx, sp)
    drop_templates()
    print(f"[shop_interiors] {out_n} crude pieces out, {tris} triangles of goods in, {n_up} props in detail", flush=True)
    return out_n, tris
